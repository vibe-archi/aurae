"""Verify release assets offline, including identical payloads and vendor binding."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import stat
import sys
import zipfile

from common import (MANIFEST, ROOTS, PackageError, check_links, check_path_set, check_versions,
                    json_bytes, json_read, render_vendor, require, safe_path, sha,
                    validate_profile, yaml_read)


def read_archive(path, platform):
    payload = {}
    prefix = ROOTS[platform]
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        check_path_set({entry.filename for entry in entries})
        require(0 < len(entries) <= 500, "Unexpected archive size")
        require(sum(e.file_size for e in entries) <= 16 * 1024 * 1024, "Archive exceeds size budget")
        seen = set()
        for entry in entries:
            safe_path(entry.filename)
            require(entry.filename.startswith(prefix) and not entry.is_dir(), "Unexpected installation path")
            require(entry.filename.casefold() not in seen, "Duplicate or case-colliding ZIP entry")
            seen.add(entry.filename.casefold())
            mode = entry.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG), "ZIP links and special files are forbidden")
            require(not entry.flag_bits & 1, "Encrypted ZIP entries are forbidden")
            payload[entry.filename[len(prefix):]] = archive.read(entry)
    return payload


def verify_payload(payload):
    require(MANIFEST in payload and "vendor.md" in payload, "Incomplete installable bundle")
    manifest = yaml_read(payload[MANIFEST])
    require(isinstance(manifest, dict), "Invalid manifest")
    expected = {}
    require(isinstance(manifest.get("files"), list), "Invalid bundle inventory")
    for entry in manifest["files"]:
        require(isinstance(entry, dict) and set(entry) == {"path", "sha256"}, "Invalid bundle inventory entry")
        path = safe_path(entry["path"])
        require(path.casefold() not in {name.casefold() for name in expected}, "Duplicate inventory entry")
        require(isinstance(entry["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), "Invalid digest")
        expected[path] = entry["sha256"]
    require(set(expected) == set(payload) - {MANIFEST}, "Bundle inventory is not exhaustive")
    for path, digest in expected.items():
        require(sha(payload[path]) == digest, f"Bundle hash mismatch: {path}")
    check_versions(payload, manifest)
    check_links(payload)
    return manifest


def verify(directory, root=None):
    directory = Path(directory)
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    info = json_read((directory / "build-info.json").read_bytes())
    require(info["format"] == "aurae-build-v1", "Unknown build metadata format")
    require(isinstance(info["agent_skill"], str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", info["agent_skill"]), "Invalid build version")
    names = {platform: f"aurae-{platform}-{info['agent_skill']}.zip" for platform in ROOTS}
    require(set(info["assets"]) == set(names.values()), "Unexpected release asset inventory")
    expected_files = set(names.values()) | {"SHA256SUMS", "build-info.json"}
    require({p.name for p in directory.iterdir()} == expected_files, "Missing or unexpected release files")
    checksums = {}
    for line in (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        require(match is not None, "Malformed checksums file")
        require(match[2] not in checksums, "Duplicate checksum entry")
        checksums[match[2]] = match[1]
    require(set(checksums) == expected_files - {"SHA256SUMS"}, "Incomplete checksums file")
    for name, digest in checksums.items():
        require(sha((directory / name).read_bytes()) == digest, f"Release hash mismatch: {name}")
    for name, digest in info["assets"].items():
        require(checksums[name] == digest, "Build metadata asset digest differs")
    schema = json_read((root / "packaging/vendor.schema.json").read_bytes())
    profile = info["resolved_vendor"]
    validate_profile(profile, schema, info["repository"])
    require(sha(json_bytes(profile)) == info["vendor_config_sha256"], "Resolved vendor digest differs")
    if info["release"]:
        require(info["source"]["dirty"] is False and isinstance(info["source"]["commit"], str) and re.fullmatch(r"[0-9a-f]{40,64}", info["source"]["commit"]), "Release is not tied to a clean Git revision")
    template = (root / "packaging/vendor.template.md").read_text(encoding="utf-8")
    expected_vendor = render_vendor(template, profile)
    bundles = []
    for platform, name in names.items():
        payload = read_archive(directory / name, platform)
        manifest = verify_payload(payload)
        require(manifest["agent_skill"] == info["agent_skill"] and manifest["aurae_methodology"] == info["aurae_methodology"], "Package version differs from build metadata")
        require(sha(payload[MANIFEST]) == info["manifest_sha256"], "Manifest identity differs")
        require(payload["vendor.md"] == expected_vendor, "Embedded vendor differs from resolved build configuration")
        bundles.append(payload)
    require(bundles[0] == bundles[1], "Platform packages do not contain the same skill")
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        info = verify(args.directory)
        print(f"PASS: Codex + Claude, exhaustive hashes, local links and vendor profile ({info['agent_skill']}).")
        return 0
    except (PackageError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

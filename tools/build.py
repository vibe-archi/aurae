"""Build complete Codex/Claude archives without mutating the source skill."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from common import (MANIFEST, ROOTS, PackageError, check_links, json_bytes, render_vendor,
                    require, resolve_profile, sha, source_payload, yaml_bytes)


def git_info(root):
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    top = git("rev-parse", "--show-toplevel")
    if not top or Path(top).resolve() != root.resolve():
        return {"commit": None, "dirty": None}
    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=all")
    return {"commit": commit, "dirty": status != ""}


def archive(path, prefix, payload):
    # Stored entries avoid platform/zlib-dependent compression. Small text-only bundle.
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as output:
        for name, data in sorted(payload.items()):
            entry = zipfile.ZipInfo(prefix + name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, data)


def build(root, output, repository, config=None, release=False):
    root = Path(root).resolve()
    payload, descriptor = source_payload(root)
    profile = resolve_profile(root, repository, config)
    vendor_template = (root / "packaging/vendor.template.md").read_text(encoding="utf-8")
    payload["vendor.md"] = render_vendor(vendor_template, profile)
    manifest = {key: value for key, value in descriptor.items() if key != "files"}
    manifest["files"] = [{"path": name, "sha256": sha(data)} for name, data in sorted(payload.items())]
    payload[MANIFEST] = yaml_bytes(manifest)
    check_links(payload)
    source = git_info(root)
    version = descriptor["agent_skill"]
    if release:
        require(source["commit"] and source["dirty"] is False, "Releases require a clean committed repository")
        tag = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", f"refs/tags/v{version}^{{commit}}"], capture_output=True, text=True)
        require(tag.returncode == 0 and tag.stdout.strip() == source["commit"], "Release tag must match package version and HEAD")
    output = Path(output).resolve() if output else root / "dist" / version
    require(output.is_relative_to(root / "dist") or output.is_relative_to(root / ".scratchpad"), "Output must be inside this repository's dist/ or .scratchpad/")
    require(not output.exists() or not any(output.iterdir()), "Output directory is not empty; never overwrite a prior build")
    output.mkdir(parents=True, exist_ok=True)
    assets = {}
    for platform, prefix in ROOTS.items():
        name = f"aurae-{platform}-{version}.zip"
        archive(output / name, prefix, payload)
        assets[name] = sha((output / name).read_bytes())
    inputs = {}
    # Fingerprint all build inputs, including tools, without machine paths or credentials.
    for directory in ("skills/aurae", "packaging", "tools"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.name != "vendor.local.json":
                inputs[path.relative_to(root).as_posix()] = sha(path.read_bytes().replace(b"\r\n", b"\n"))
    inputs["requirements-dev.txt"] = sha((root / "requirements-dev.txt").read_bytes().replace(b"\r\n", b"\n"))
    info = {"format": "aurae-build-v1", "agent_skill": version,
            "aurae_methodology": descriptor["aurae_methodology"], "repository": repository,
            "source": source, "release": release, "resolved_vendor": profile,
            "vendor_config_sha256": sha(json_bytes(profile)), "manifest_sha256": sha(payload[MANIFEST]),
            "inputs": inputs, "assets": assets}
    (output / "build-info.json").write_bytes(json_bytes(info))
    assets["build-info.json"] = sha((output / "build-info.json").read_bytes())
    (output / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name, digest in sorted(assets.items())), encoding="utf-8", newline="\n")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="Distribution owner/repository (also for local builds)")
    parser.add_argument("--vendor-config", type=Path, help="Local JSON override; mutually exclusive with AURAE_VENDOR_CONFIG")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    try:
        env = os.environ.get("AURAE_VENDOR_CONFIG")
        # GitHub represents an unset configuration variable as an empty string.
        config = env if env else None
        require(not (args.vendor_config and config is not None), "Choose one vendor configuration source")
        if args.vendor_config:
            config = args.vendor_config.read_text(encoding="utf-8")
        output = build(Path(__file__).resolve().parents[1], args.output, args.repository, config, args.release)
        print(f"Built and integrity-bound both platform packages in {output}")
        return 0
    except (PackageError, OSError, ValueError) as error:
        print(f"Build refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

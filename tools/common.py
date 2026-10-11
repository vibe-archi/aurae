"""Shared, offline package contracts. Never executes distribution instructions."""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
from pathlib import Path

import jsonschema
import yaml

MANIFEST = "aurae-skill.yaml"
ROOTS = {"codex": ".agents/skills/aurae/", "claude": ".claude/skills/aurae/"}
OFFICIAL_REPO = "vibe-archi/aurae"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


class PackageError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PackageError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate mapping key")
        result[key] = value
    return result


class UniqueLoader(yaml.SafeLoader):
    pass


def yaml_mapping(loader, node):
    return pairs((loader.construct_object(k), loader.construct_object(v)) for k, v in node.value)


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, yaml_mapping)


def yaml_read(data):
    return yaml.load(data, Loader=UniqueLoader)


def yaml_bytes(data):
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120).encode("utf-8")


def json_read(data):
    return json.loads(data, object_pairs_hook=pairs)


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def safe_path(value):
    require(isinstance(value, str) and len(value) <= 240, "Invalid package path")
    require(bool(re.fullmatch(r"[A-Za-z0-9_.\-/]+", value)), "Non-portable package path")
    parts = value.split("/")
    for part in parts:
        require(part not in ("", ".", "..") and not part.endswith((".", " ")), "Unsafe package path")
        require(not re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part), "Reserved package path")
    return value


def check_path_set(paths):
    folded = {}
    for path in paths:
        safe_path(path)
        parts = path.split("/")
        for length in range(1, len(parts) + 1):
            prefix = "/".join(parts[:length])
            require(folded.get(prefix.casefold(), prefix) == prefix, "Case-colliding package paths")
            folded[prefix.casefold()] = prefix
            require(length == len(parts) or prefix not in paths, "File/directory collision")


def validate_profile(profile, schema, repository):
    require(isinstance(repository, str) and bool(REPOSITORY.fullmatch(repository)), "Expected an owner/repository name")
    validator = jsonschema.Draft202012Validator(schema)
    error = next(iter(validator.iter_errors(profile)), None)
    require(error is None, "Invalid vendor profile (schema check failed)")
    distribution = profile["distribution"]
    require(distribution["repository"] == "https://github.com/" + repository, "Distribution repository does not match build repository")
    official = repository == OFFICIAL_REPO
    require((distribution["id"] == "aurae-official") == official, "Distribution identity does not match repository")
    require((distribution["base_agent_skill"] is None) == official, "Private distributions must record their official base version")
    require(not any(ord(c) < 32 for c in distribution["name"]), "Invalid distribution name")
    serialized = json.dumps(profile, ensure_ascii=False)
    require(not re.search(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN .*PRIVATE KEY-----)", serialized), "Possible credential in vendor profile; remove it")
    require(not any(ord(c) < 32 and c not in "\n\t" for c in profile["instructions"]), "Invalid distribution instructions")


def resolve_profile(root: Path, repository: str, config: str | None):
    profile = json_read((root / "packaging/vendor.defaults.json").read_text(encoding="utf-8"))
    schema = json_read((root / "packaging/vendor.schema.json").read_text(encoding="utf-8"))
    if config is not None:
        require(bool(config.strip()) and len(config) <= 20000, "Vendor configuration is empty or too large")
        override = json_read(config)
        require(isinstance(override, dict) and set(override) <= {"distribution", "instructions"}, "Only distribution and instructions can be overridden")
        require(set(override) >= {"distribution", "instructions"}, "Supply a complete private distribution and its instructions")
        profile.update(override)
    elif repository != OFFICIAL_REPO:
        raise PackageError("A non-official repository requires explicit AURAE_VENDOR_CONFIG")
    validate_profile(profile, schema, repository)
    return profile


def render_vendor(template: str, profile) -> bytes:
    require(template.count("{{PROFILE_YAML}}") == 1 and template.count("{{INSTRUCTIONS}}") == 1, "Invalid vendor template")
    frontmatter = {k: profile[k] for k in ("profile_version", "official", "distribution")}
    frontmatter["official"] = {k: profile["official"][k] for k in ("repository", "website")}
    frontmatter["distribution"] = {k: profile["distribution"][k] for k in ("id", "name", "repository", "base_agent_skill")}
    # One substitution pass: instructions are data, never template or shell code.
    replacements = {"PROFILE_YAML": yaml_bytes(frontmatter).decode().rstrip(), "INSTRUCTIONS": profile["instructions"]}
    return re.sub(r"\{\{(PROFILE_YAML|INSTRUCTIONS)\}\}", lambda m: replacements[m[1]], template).encode("utf-8")


def check_versions(payload, manifest):
    require(set(manifest) == {"format", "format_version", "name", "agent_skill", "aurae_methodology", "entrypoint", "files"}, "Unexpected manifest fields")
    require(manifest["format"] == "aurae-skill-bundle" and manifest["format_version"] == "1.0.0", "Unsupported bundle format")
    require(manifest["name"] == "aurae" and manifest["entrypoint"] == "SKILL.md", "Unexpected skill identity")
    for field in ("agent_skill", "aurae_methodology"):
        require(isinstance(manifest[field], str) and VERSION.fullmatch(manifest[field]), "Expected stable MAJOR.MINOR.PATCH versions")
    text = payload["references/versioning-and-releases.md"].decode("utf-8")
    release = yaml_read(re.search(r"```yaml\s*\n(.*?)\n```", text, re.S)[1])
    for field in ("agent_skill", "aurae_methodology"):
        require(release[field] == manifest[field], "Release reference and manifest versions differ")
    require(release["skill_bundle_format"] == manifest["format_version"], "Bundle format reference differs")
    skill = payload["SKILL.md"].decode("utf-8")
    require(skill.startswith("---\n"), "Skill frontmatter missing")
    header = yaml_read(skill.split("---", 2)[1])
    require(header.get("name") == "aurae" and isinstance(header.get("description"), str) and header["description"].strip(), "Invalid skill frontmatter")


def check_links(payload):
    """Validate real local Markdown file links, not examples inside code fences."""
    for path, data in payload.items():
        if not path.endswith(".md"):
            continue
        visible, fence = [], None
        for line in data.decode("utf-8").splitlines():
            marker = re.match(r"^\s*(`{3,}|~{3,})", line)
            if marker:
                token = marker[1]
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
                continue
            if fence is None:
                visible.append(line)
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", "\n".join(visible)):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            require(resolved in payload, f"Broken local link in {path}: {target}")


def source_payload(root: Path):
    source = root / "skills/aurae"
    require(not source.is_symlink() and not getattr(source.lstat(), "st_file_attributes", 0) & 0x400, "Skill root cannot be a link/junction")
    descriptor = yaml_read((source / MANIFEST).read_bytes())
    paths = descriptor["files"]
    require(isinstance(paths, list) and all(isinstance(p, str) for p in paths), "Source inventory must list paths")
    require(len(paths) == len({p.casefold() for p in paths}), "Duplicate source path")
    for path in paths:
        safe_path(path)
    check_path_set(paths)
    require("vendor.md" in paths and MANIFEST not in paths, "Source inventory must include generated vendor, not itself")
    actual = set()
    for path in source.rglob("*"):
        require(not path.is_symlink() and not getattr(path.lstat(), "st_file_attributes", 0) & 0x400, "Symlinks/junctions are forbidden in skill sources")
        if path.is_file():
            actual.add(path.relative_to(source).as_posix())
    expected = (set(paths) - {"vendor.md"}) | {MANIFEST}
    require(actual == expected, "Source inventory mismatch; do not put generated vendor or unlisted files in skills/aurae")
    payload = {path: (source / path).read_bytes().replace(b"\r\n", b"\n") for path in paths if path != "vendor.md"}
    require(all(path.endswith((".md", ".yaml")) for path in payload), "Only reviewed Markdown/YAML resources are supported")
    check_versions(payload, descriptor)
    return payload, descriptor

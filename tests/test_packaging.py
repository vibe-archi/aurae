"""Portable behavioral tests; isolated generated material stays under .scratchpad."""
import copy
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build import build
from common import (PackageError, check_links, check_path_set, json_bytes, json_read, render_vendor,
                    resolve_profile, safe_path, sha, source_payload)
from verify import read_archive, verify, verify_payload

PRIVATE = {
    "distribution": {"id": "example-engineering", "name": "Example Engineering",
                     "repository": "https://github.com/example/aurae-private", "base_agent_skill": "1.17.1"},
    "instructions": "Use the organization's approved engineering conventions.\nKeep all protected decisions."
}


class PackagingTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".scratchpad").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="packaging-test-", dir=ROOT / ".scratchpad")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def make(self, name="build", config=None, repo="vibe-archi/aurae", root=ROOT):
        return build(root, self.work / name, repo, config)

    def test_official_packages_verify_and_install(self):
        output = self.make()
        info = verify(output)
        self.assertEqual(info["resolved_vendor"]["distribution"]["id"], "aurae-official")
        for platform, destination in (("codex", ".agents"), ("claude", ".claude")):
            path = output / f"aurae-{platform}-{info['agent_skill']}.zip"
            extracted = self.work / platform
            with zipfile.ZipFile(path) as archive:
                archive.extractall(extracted)
            skill = extracted / destination / "skills/aurae"
            payload = {p.relative_to(skill).as_posix(): p.read_bytes() for p in skill.rglob("*") if p.is_file()}
            verify_payload(payload)
            self.assertEqual(set(p.name for p in extracted.iterdir()), {destination})
            self.assertNotIn(".gitignore", payload)

    def test_repeat_build_is_byte_identical(self):
        a, b = self.make("a"), self.make("b")
        self.assertEqual({p.name: p.read_bytes() for p in a.iterdir()}, {p.name: p.read_bytes() for p in b.iterdir()})

    def test_build_never_mutates_skill_sources(self):
        def snapshot():
            return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in (ROOT / "skills").rglob("*") if p.is_file()}
        before = snapshot()
        self.make()
        self.assertEqual(snapshot(), before)
        self.assertFalse((ROOT / "skills/aurae/vendor.md").exists())

    def test_private_profile_is_bound_to_both_packages(self):
        output = self.make(config=json.dumps(PRIVATE), repo="example/aurae-private")
        info = verify(output)
        self.assertEqual(info["resolved_vendor"]["instructions"], PRIVATE["instructions"])
        self.assertEqual(info["resolved_vendor"]["official"]["website"], "https://aurae.md")

    def test_missing_private_config_fails(self):
        with self.assertRaises(PackageError):
            self.make(repo="example/aurae-private")

    def test_invalid_profiles_fail_without_echoing_values(self):
        for mutation in ("wrong_repo", "official_identity", "missing_base", "unknown_key", "credential", "wrong_type"):
            config = copy.deepcopy(PRIVATE)
            if mutation == "wrong_repo": config["distribution"]["repository"] += "/other"
            if mutation == "official_identity": config["distribution"]["id"] = "aurae-official"
            if mutation == "missing_base": config["distribution"]["base_agent_skill"] = None
            if mutation == "unknown_key": config["token"] = "do-not-echo-this"
            if mutation == "credential": config["instructions"] = "ghp_" + "a" * 32
            if mutation == "wrong_type": config["instructions"] = ["bad"]
            with self.subTest(mutation=mutation), self.assertRaises(PackageError) as error:
                self.make(config=json.dumps(config), repo="example/aurae-private")
            self.assertNotIn("do-not-echo-this", str(error.exception))

    def test_json_duplicate_keys_and_empty_override_fail(self):
        for value in ("", "{}", '{"distribution": {}, "distribution": {}}'):
            with self.subTest(value=value), self.assertRaises((PackageError, ValueError)):
                resolve_profile(ROOT, "example/aurae-private", value)

    def test_template_does_not_interpret_client_content(self):
        config = copy.deepcopy(PRIVATE)
        config["instructions"] = 'Unicode é漢字; "quoted"; {{PROFILE_YAML}}; $(not-a-command)\nSecond line.'
        profile = resolve_profile(ROOT, "example/aurae-private", json.dumps(config))
        data = render_vendor((ROOT / "packaging/vendor.template.md").read_text(encoding="utf-8"), profile)
        self.assertIn(config["instructions"].encode(), data)

    def test_cannot_overwrite_previous_build(self):
        output = self.make()
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        with self.assertRaises(PackageError): self.make()
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_output_cannot_escape_generated_directories(self):
        with self.assertRaises(PackageError):
            build(ROOT, ROOT / "skills/generated", "vibe-archi/aurae")

    def test_paths_reject_traversal_windows_aliases_and_absolute_paths(self):
        for path in ("../bad", "/tmp/bad", "C:/bad", "a\\b", "a//b", "a/CON.md", "a/b.", "./a"):
            with self.subTest(path=path), self.assertRaises(PackageError): safe_path(path)

    def test_source_inventory_rejects_missing_and_extra_files(self):
        root = self.work / "source"
        shutil.copytree(ROOT / "skills", root / "skills")
        missing = root / "skills/aurae/references/interviews.md"
        content = missing.read_bytes()
        missing.unlink()
        with self.assertRaises(PackageError): source_payload(root)
        missing.write_bytes(content)
        (root / "skills/aurae/unlisted.md").write_text("Not approved", encoding="utf-8")
        with self.assertRaises(PackageError): source_payload(root)

    def test_zip_tampering_fails(self):
        output = self.make()
        path = next(output.glob("*codex*.zip"))
        path.write_bytes(path.read_bytes() + b"tampered")
        with self.assertRaises(PackageError): verify(output)

    def test_payload_hashes_and_extra_files_are_checked(self):
        output = self.make()
        payload = read_archive(next(output.glob("*codex*.zip")), "codex")
        original = payload["vendor.md"]
        payload["vendor.md"] += b"Changed instructions"
        with self.assertRaises(PackageError): verify_payload(payload)
        payload["vendor.md"] = original
        payload["extra.md"] = b"unlisted"
        with self.assertRaises(PackageError): verify_payload(payload)

    def test_build_metadata_vendor_tamper_is_detected(self):
        output = self.make()
        info = json_read((output / "build-info.json").read_bytes())
        info["resolved_vendor"]["instructions"] = "Changed after build"
        info["vendor_config_sha256"] = sha(json_bytes(info["resolved_vendor"]))
        (output / "build-info.json").write_bytes(json_bytes(info))
        assets = {**info["assets"], "build-info.json": sha((output / "build-info.json").read_bytes())}
        (output / "SHA256SUMS").write_text("".join(f"{v}  {k}\n" for k, v in sorted(assets.items())), encoding="utf-8")
        with self.assertRaises(PackageError): verify(output)

    def test_unsafe_archive_entries_fail_before_extraction(self):
        for index, (name, mode) in enumerate((("../escape", 0o100644), (".agents/skills/aurae/link", stat.S_IFLNK | 0o777), (".claude/skills/aurae/a", 0o100644))):
            path = self.work / f"unsafe-{index}.zip"
            with zipfile.ZipFile(path, "w") as archive:
                entry = zipfile.ZipInfo(name)
                entry.external_attr = mode << 16
                archive.writestr(entry, "bad")
            with self.assertRaises(PackageError): read_archive(path, "codex")

    def test_broken_local_links_fail(self):
        with self.assertRaises(PackageError):
            check_links({"SKILL.md": b"[missing](references/missing.md)"})
        check_links({"SKILL.md": b"```md\n[example](not-a-real-file.md)\n```"})

    def test_directory_case_collisions_and_file_parent_conflicts_fail(self):
        for paths in ({"references/A/x.md", "references/a/y.md"}, {"references/a", "references/a/b.md"}):
            with self.subTest(paths=paths), self.assertRaises(PackageError): check_path_set(paths)

    def test_release_without_license_requires_clean_tree_and_matching_tag(self):
        root = self.work / "release-source"
        for name in ("skills", "packaging", "tools"):
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__", "vendor.local.json"))
        for name in ("requirements-dev.txt", ".gitignore", ".gitattributes"):
            shutil.copy2(ROOT / name, root)
        def git(*args):
            return subprocess.run(["git", "-c", "init.templateDir=", "-c", "core.hooksPath=" + str(root / "no-hooks"),
                                   "-c", "commit.gpgsign=false", "-c", "user.name=Package Test",
                                   "-c", "user.email=package-test@example.invalid", "-C", str(root), *args],
                                  check=True, capture_output=True, text=True)
        git("init")
        git("add", ".")
        git("commit", "-m", "Disposable packaging fixture")
        version = source_payload(root)[1]["agent_skill"]
        git("tag", "v" + version)
        self.assertFalse((root / "LICENSE").exists())
        output = build(root, root / "dist/without-license", "vibe-archi/aurae", release=True)
        self.assertTrue(verify(output, root)["release"])
        (root / "fixture.md").write_text("Temporary release test fixture.\n", encoding="utf-8")
        git("add", "fixture.md")
        git("commit", "-m", "Advance disposable release fixture")
        with self.assertRaises(PackageError): build(root, root / "dist/stale-tag", "vibe-archi/aurae", release=True)
        # Only this disposable fixture's unshared tag is recreated for the positive case.
        git("tag", "-d", "v" + version)
        git("tag", "v" + version)
        output = build(root, root / "dist/verified", "vibe-archi/aurae", release=True)
        self.assertTrue(verify(output, root)["release"])
        (root / "uncommitted.md").write_text("Local work", encoding="utf-8")
        with self.assertRaises(PackageError): build(root, root / "dist/dirty", "vibe-archi/aurae", release=True)

    def test_uncommitted_release_is_refused(self):
        # A throwaway source tree cannot masquerade as a committed release.
        root = self.work / "uncommitted"
        for name in ("skills", "packaging", "tools"):
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "requirements-dev.txt", root)
        with self.assertRaises(PackageError):
            build(root, root / "dist", "vibe-archi/aurae", release=True)


if __name__ == "__main__":
    unittest.main()

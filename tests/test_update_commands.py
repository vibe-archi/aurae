"""Offline transactional updates: verify provenance and never overlay a skill."""
from __future__ import annotations

import hashlib
import ctypes
import json
import os
from pathlib import Path
import re
import shlex
import stat
import unittest
import zipfile

import yaml

from test_install_commands import InstallerFixture, ROOT, ROOTS, bash_path, ps_literal
from build import archive as write_archive
from common import yaml_bytes


class UpdateCommandTests(InstallerFixture, unittest.TestCase):
    old_version = "1.18.0"
    new_version = "1.19.0"
    manual_version = "1.15.0"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Keep the actual official distribution profile produced by build.py.
        # Compact old/new fixtures use the production ZIP writer and a complete
        # manifest; their smaller file sets make failure matrices inexpensive.
        with zipfile.ZipFile(cls.assets / f"aurae-codex-{cls.version}.zip") as bundle:
            vendor = bundle.read(ROOTS["codex"] + "vendor.md")
            manifest = yaml.safe_load(bundle.read(ROOTS["codex"] + "aurae-skill.yaml"))
        cls.assets = cls.work / "versioned-assets"
        cls.assets.mkdir()
        for version, exclusive in ((cls.old_version, "old-only.md"), (cls.new_version, "new-only.md")):
            payload = {
                "SKILL.md": ("---\nname: aurae\ndescription: Offline installer fixture.\n---\n\n"
                             f"# AURAE test package {version}\n").encode(),
                "vendor.md": vendor,
                "references/upgrade.md": b"# Upgrade fixture\n",
                "references/skill-recovery-and-trust.md": b"# Recovery fixture\n",
                exclusive: f"File belongs only to {version}.\n".encode(),
            }
            descriptor = dict(manifest, agent_skill=version)
            descriptor["files"] = [{"path": name, "sha256": hashlib.sha256(data).hexdigest()}
                                   for name, data in sorted(payload.items())]
            payload["aurae-skill.yaml"] = yaml_bytes(descriptor)
            output = cls.assets / version
            output.mkdir()
            for agent, prefix in ROOTS.items():
                write_archive(output / f"aurae-{agent}-{version}.zip", prefix, payload)
            cls.write_checksums(output)
        cls.version = cls.new_version

    @staticmethod
    def write_checksums(directory):
        lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                 for path in sorted(directory.glob("*.zip"))]
        (directory / "SHA256SUMS").write_text("".join(lines), encoding="utf-8", newline="\n")

    def archive(self, case, agent="codex", version=None):
        version = version or self.new_version
        return case["assets"] / version / f"aurae-{agent}-{version}.zip"

    def install_fixture(self, case, agent="codex", version=None):
        # This ZIP is generated locally above, not supplied by an external actor.
        # The update itself must still prove every installed byte against its
        # separately downloaded, checksum-verified reference package.
        with zipfile.ZipFile(self.archive(case, agent, version or self.old_version)) as bundle:
            bundle.extractall(case["project"])
        return self.target(case, agent)

    def install_manual_fixture(self, case, agent="codex", version=None, profile=False):
        """A local copy with no published reference, not a pristine release ZIP."""
        target = self.install_fixture(case, agent)
        manifest = target / "aurae-skill.yaml"
        descriptor = yaml.safe_load(manifest.read_bytes())
        descriptor["agent_skill"] = version or self.manual_version
        if not profile:
            (target / "vendor.md").unlink()
            descriptor["files"] = [entry for entry in descriptor["files"] if entry["path"] != "vendor.md"]
        manifest.write_bytes(yaml_bytes(descriptor))
        with (target / "SKILL.md").open("ab") as skill:
            skill.write(b"\nLocal notes that must be retained in the actual-copy backup.\n")
        (target / "custom-local.md").write_text("Locally added content.\n", encoding="utf-8")
        hidden = target / ".hidden-local"
        hidden.mkdir()
        (hidden / "local.txt").write_bytes(b"Hidden local content.\x00\xff")
        (target / ".hidden-file").write_bytes(b"A hidden top-level file.\n")
        (target / "empty-local-directory").mkdir()
        (hidden / "empty-directory").mkdir()
        if os.name == "nt":
            for path in (hidden, target / ".hidden-file"):
                self.assertTrue(ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x2),
                                "The Windows fixture must really have the Hidden attribute")
        return target

    def missing_manual_archive(self, agent="codex", version=None):
        version = version or self.manual_version
        return {"fail": f"{version}/aurae-{agent}-{version}.zip", "http_status": "404"}

    @staticmethod
    def snapshot(directory):
        result = {}
        for path in directory.rglob("*"):
            name = path.relative_to(directory).as_posix()
            if path.is_symlink():
                result[name] = ("link", os.readlink(path))
            elif path.is_file():
                result[name] = ("file", path.read_bytes())
            else:
                result[name] = ("directory",)
        return result

    def backups(self, case):
        state = case.get("state_root", case["directory"] / "local state")
        return sorted(state.rglob("skill.zip")) + sorted(state.rglob("previous-skill"))

    def assert_manual_backup(self, case, before):
        backups = self.backups(case)
        self.assertEqual(len(backups), 1, "Keep exactly one recoverable actual-copy backup")
        backup = backups[0]
        self.assertEqual(backup.name, "previous-skill")
        self.assertFalse(backup.is_relative_to(case["project"]))
        self.assertEqual(self.snapshot(backup), before,
                         "Backup must preserve every local byte, hidden entry and empty directory")
        self.assertTrue(any(backup.parent.glob("restore-info.*")), "Backup needs recovery instructions")
        return backup

    def assert_preserved(self, result, case, before, agent="codex", backup=False):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.snapshot(self.target(case, agent)), before)
        if not backup:
            self.assertEqual(self.backups(case), [], "Refusal before replacement must not create an upgrade backup")

    def assert_backup(self, case, agent="codex"):
        backups = self.backups(case)
        self.assertEqual(len(backups), 1, "A successful replacement must retain exactly one old-package backup")
        backup = backups[0]
        self.assertFalse(backup.is_relative_to(case["project"]), "Backups must remain outside agent auto-discovery roots")
        with zipfile.ZipFile(backup) as stored, zipfile.ZipFile(self.archive(case, agent, self.old_version)) as expected:
            stored_payload = {item.filename: stored.read(item) for item in stored.infolist() if not item.is_dir()}
            expected_payload = {item.filename: expected.read(item) for item in expected.infolist() if not item.is_dir()}
            # Both a copied official ZIP and a ZIP of just the skill directory
            # are recoverable. Compare complete bytes, independent of ZIP dates.
            prefix = ROOTS[agent]
            if stored_payload and not all(name.startswith(prefix) for name in stored_payload):
                expected_payload = {name.removeprefix(prefix): data for name, data in expected_payload.items()}
            self.assertEqual(stored_payload, expected_payload)
        self.assertTrue(any(backup.parent.glob("restore-info.*")), "Backup needs a recovery-location record")
        return backup

    def test_readme_and_guide_offer_explicit_update_commands(self):
        guide = (ROOT / "docs/install.md").read_text(encoding="utf-8")
        self.assertIn("README.md#update-an-existing-skill", guide)
        self.assertIn("-Update", guide)
        self.assertIn("--update", guide)
        for document in ("README.md",):
            text = (ROOT / document).read_text(encoding="utf-8")
            blocks = re.findall(r"```(powershell|bash)\r?\n(.*?)\r?\n```", text, re.S)
            for language in ("powershell", "bash"):
                for agent in ROOTS:
                    with self.subTest(document=document, language=language, agent=agent):
                        agent_flag = f"-Agent {agent}" if language == "powershell" else f"--agent {agent}"
                        update_flag = "-Update" if language == "powershell" else "--update"
                        matching = [body for kind, body in blocks if kind == language and agent_flag in body
                                    and update_flag in body
                                    and "https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install." in body]
                        self.assertTrue(matching, f"Missing explicit update command in {document}")
                        self.assertTrue(any(len(body.strip().splitlines()) == 1 for body in matching))

    def test_update_replaces_complete_package_and_keeps_recoverable_backup(self):
        for shell in self.shells:
            for agent in ROOTS:
                with self.subTest(shell=shell[0], agent=agent):
                    case = self.case()
                    target = self.install_fixture(case, agent)
                    result = self.run_install(shell, case, agent, update=True)
                    self.assert_installed(result, case, agent)
                    self.assertFalse((target / "old-only.md").exists(), "Updates must replace, never overlay the old tree")
                    self.assertTrue((target / "new-only.md").is_file())
                    self.assert_backup(case, agent)
                    requests = case["requests"].read_text(encoding="utf-8-sig")
                    for version in (self.old_version, self.new_version):
                        self.assertIn(f"/download/v{version}/aurae-{agent}-{version}.zip", requests)
                        self.assertIn(f"/download/v{version}/SHA256SUMS", requests)

    def test_readme_update_bootstrap_uses_latest_release(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                self.install_fixture(case)
                result = self.run_install(shell, case, update=True, bootstrap=True, version=None)
                self.assert_installed(result, case, "codex")
                self.assert_backup(case)

    def test_unpublished_115_updates_both_agents_and_backs_up_the_actual_local_tree(self):
        for shell in self.shells:
            for agent in ROOTS:
                with self.subTest(shell=shell[0], agent=agent):
                    case = self.case()
                    target = self.install_manual_fixture(case, agent)
                    before = self.snapshot(target)
                    result = self.run_install(shell, case, agent, update=True,
                                              **self.missing_manual_archive(agent))
                    self.assert_installed(result, case, agent)
                    for name in ("old-only.md", "custom-local.md", ".hidden-local", ".hidden-file", "empty-local-directory"):
                        self.assertFalse((target / name).exists(), "Update must replace, never overlay the local tree")
                    self.assert_manual_backup(case, before)
                    requests = case["requests"].read_text(encoding="utf-8-sig")
                    self.assertIn(f"/download/v{self.manual_version}/aurae-{agent}-{self.manual_version}.zip", requests)
                    self.assertNotIn(f"/download/v{self.manual_version}/SHA256SUMS", requests)
                    self.assertIn(f"/download/v{self.new_version}/SHA256SUMS", requests)

    def test_unpublished_modern_official_profile_can_use_actual_copy_backup(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_manual_fixture(case, version=self.old_version, profile=True)
                before = self.snapshot(target)
                result = self.run_install(shell, case, update=True,
                                          **self.missing_manual_archive(version=self.old_version))
                self.assert_installed(result, case, "codex")
                self.assert_manual_backup(case, before)

    def test_manual_fallback_requires_old_zip_http_404_not_transport_403_or_500(self):
        for shell in self.shells:
            for status in ("", "403", "500"):
                with self.subTest(shell=shell[0], status=status or "transport"):
                    case = self.case()
                    target = self.install_manual_fixture(case)
                    before = self.snapshot(target)
                    result = self.run_install(shell, case, update=True,
                                              fail=self.missing_manual_archive()["fail"], http_status=status)
                    self.assert_preserved(result, case, before)

    def test_manual_downgrade_is_refused_without_downloading(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_manual_fixture(case)
                before = self.snapshot(target)
                result = self.run_install(shell, case, version="1.14.0", update=True,
                                          **self.missing_manual_archive())
                self.assert_preserved(result, case, before)
                self.assertFalse(case["requests"].exists(), "Downgrade refusal must precede network requests")

    def test_missing_old_checksums_does_not_enable_manual_fallback(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_manual_fixture(case, version=self.old_version, profile=True)
                before = self.snapshot(target)
                result = self.run_install(shell, case, update=True,
                                          fail=f"{self.old_version}/SHA256SUMS", http_status="404")
                self.assert_preserved(result, case, before)

    def test_manual_private_ambiguous_and_missing_modern_profiles_are_refused(self):
        variants = ("private-id", "duplicate-distribution", "local-instructions", "missing-modern")
        for shell in self.shells:
            for variant in variants:
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    version = self.old_version if variant == "missing-modern" else self.manual_version
                    target = self.install_manual_fixture(case, version=version, profile=variant != "missing-modern")
                    if variant != "missing-modern":
                        profile = target / "vendor.md"
                        content = profile.read_text(encoding="utf-8")
                        if variant == "private-id":
                            content = content.replace("id: aurae-official", "id: private-distributor")
                        elif variant == "duplicate-distribution":
                            content = content.replace("distribution:", "distribution: {}\ndistribution:", 1)
                        else:
                            content += "\nAdditional organization-specific instructions.\n"
                        profile.write_text(content, encoding="utf-8")
                    before = self.snapshot(target)
                    result = self.run_install(shell, case, update=True,
                                              **self.missing_manual_archive(version=version))
                    self.assert_preserved(result, case, before)

    def test_malformed_manual_skill_and_manifest_are_refused(self):
        variants = ("missing-skill", "empty-skill", "missing-manifest",
                    "duplicate-version", "wrong-format", "wrong-name", "wrong-entrypoint")
        for shell in self.shells:
            for variant in variants:
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    target = self.install_manual_fixture(case)
                    skill = target / "SKILL.md"
                    manifest = target / "aurae-skill.yaml"
                    if variant == "missing-skill":
                        skill.unlink()
                    elif variant == "empty-skill":
                        skill.write_bytes(b"")
                    elif variant == "missing-manifest":
                        manifest.unlink()
                    else:
                        content = manifest.read_text(encoding="utf-8")
                        if variant == "duplicate-version":
                            content += f"agent_skill: {self.manual_version}\n"
                        elif variant == "wrong-format":
                            content = content.replace("format: aurae-skill-bundle", "format: unknown-bundle")
                        elif variant == "wrong-name":
                            content = content.replace("name: aurae", "name: unknown-skill")
                        else:
                            content = content.replace("entrypoint: SKILL.md", "entrypoint: missing.md")
                        manifest.write_text(content, encoding="utf-8")
                    before = self.snapshot(target)
                    result = self.run_install(shell, case, update=True, **self.missing_manual_archive())
                    self.assert_preserved(result, case, before)

    def test_manual_fallback_still_rejects_invalid_candidate_packages(self):
        for shell in self.shells:
            for variant in ("checksum", "missing-skill", "wrong-version"):
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    target = self.install_manual_fixture(case)
                    before = self.snapshot(target)
                    path = self.archive(case)
                    if variant == "checksum":
                        path.write_bytes(path.read_bytes() + b"corrupt")
                    else:
                        with zipfile.ZipFile(path) as bundle:
                            payload = {item.filename: bundle.read(item) for item in bundle.infolist()}
                        if variant == "missing-skill":
                            del payload[ROOTS["codex"] + "SKILL.md"]
                        else:
                            name = ROOTS["codex"] + "aurae-skill.yaml"
                            payload[name] = payload[name].replace(self.new_version.encode(), b"9.9.9")
                        path.unlink()
                        write_archive(path, "", payload)
                        self.write_checksums(path.parent)
                    result = self.run_install(shell, case, update=True, **self.missing_manual_archive())
                    self.assert_preserved(result, case, before)

    def test_update_requires_existing_installation_and_explicit_flag(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0], variant="absent"):
                case = self.case()
                self.assert_refused(self.run_install(shell, case, update=True), case)
                self.assertEqual(self.backups(case), [])
                self.assertFalse(case["requests"].exists())
            with self.subTest(shell=shell[0], variant="flag-absent"):
                case = self.case()
                target = self.install_fixture(case)
                before = self.snapshot(target)
                self.assert_preserved(self.run_install(shell, case), case, before)
                self.assertFalse(case["requests"].exists())

    def test_same_version_is_verified_noop_and_downgrade_is_refused(self):
        for shell in self.shells:
            for installed, requested in ((self.old_version, self.old_version), (self.new_version, self.old_version)):
                with self.subTest(shell=shell[0], installed=installed, requested=requested):
                    case = self.case()
                    target = self.install_fixture(case, version=installed)
                    before = self.snapshot(target)
                    result = self.run_install(shell, case, version=requested, update=True)
                    if installed == requested:
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(self.snapshot(target), before)
                        requests = case["requests"].read_text(encoding="utf-8-sig")
                        self.assertIn(f"/download/v{installed}/aurae-codex-{installed}.zip", requests)
                        self.assertIn(f"/download/v{installed}/SHA256SUMS", requests)
                    else:
                        self.assert_preserved(result, case, before)
                    self.assertEqual(self.backups(case), [])

    def test_modified_private_incomplete_or_unknown_installs_are_preserved(self):
        variants = ("edited", "private", "extra-file", "extra-directory", "missing-file", "missing-manifest", "invalid-version")
        for shell in self.shells:
            for variant in variants:
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    target = self.install_fixture(case)
                    if variant == "edited":
                        (target / "SKILL.md").write_text("Local customization\n", encoding="utf-8")
                    elif variant == "private":
                        profile = target / "vendor.md"
                        profile.write_bytes(profile.read_bytes() + b"\nPrivate distributor customization.\n")
                    elif variant == "extra-file":
                        (target / "custom.md").write_text("Keep this user file\n", encoding="utf-8")
                    elif variant == "extra-directory":
                        (target / "custom-empty-directory").mkdir()
                    elif variant == "missing-file":
                        (target / "references/upgrade.md").unlink()
                    elif variant == "missing-manifest":
                        (target / "aurae-skill.yaml").unlink()
                    else:
                        manifest = target / "aurae-skill.yaml"
                        content = manifest.read_text(encoding="utf-8").replace(f"agent_skill: {self.old_version}", "agent_skill: invalid")
                        manifest.write_text(content, encoding="utf-8")
                    before = self.snapshot(target)
                    self.assert_preserved(self.run_install(shell, case, update=True), case, before)

    def test_invalid_reference_or_candidate_download_preserves_current_copy(self):
        variants = ("old-checksum", "old-unavailable", "old-incomplete", "new-checksum", "new-incomplete", "new-unavailable")
        for shell in self.shells:
            for variant in variants:
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    target = self.install_fixture(case)
                    before = self.snapshot(target)
                    fail = ""
                    if variant in ("old-checksum", "new-checksum"):
                        version = self.old_version if variant.startswith("old-") else self.new_version
                        path = self.archive(case, version=version)
                        path.write_bytes(path.read_bytes() + b"corrupt")
                    elif variant.endswith("unavailable"):
                        version = self.old_version if variant.startswith("old-") else self.new_version
                        fail = f"{version}/aurae-codex-{version}.zip"
                    else:
                        version = self.old_version if variant.startswith("old-") else self.new_version
                        path = self.archive(case, version=version)
                        with zipfile.ZipFile(path) as bundle:
                            payload = {item.filename: bundle.read(item) for item in bundle.infolist()
                                       if not item.filename.endswith("/SKILL.md")}
                        path.unlink()
                        write_archive(path, "", payload)
                        self.write_checksums(path.parent)
                    self.assert_preserved(self.run_install(shell, case, update=True, fail=fail), case, before)

    def test_linked_files_are_not_followed_during_update(self):
        exercised = False
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_fixture(case)
                outside = case["directory"] / "outside.txt"
                outside.write_text("Outside content must survive\n", encoding="utf-8")
                try:
                    (target / "foreign.txt").symlink_to(outside)
                except (OSError, NotImplementedError):
                    continue
                exercised = True
                before = self.snapshot(target)
                self.assert_preserved(self.run_install(shell, case, update=True), case, before)
                self.assertEqual(outside.read_text(encoding="utf-8"), "Outside content must survive\n")
        if not exercised:
            self.skipTest("This host does not grant symbolic link creation")

    def promotion_failure(self, shell, case, concurrent=False, **downloads):
        target = self.target(case)
        if shell[1] == "powershell":
            # Load production definitions without running install, then
            # substitute only the filesystem rename boundary.
            override = ". " + ps_literal(ROOT / "tools/install.ps1") + " -Help | Out-Null\n"
            override += r"""
$script:auraeTestFailed = $false
function Move-AuraeDirectory {
    param([string]$Source, [string]$Destination)
    if (-not $script:auraeTestFailed -and [IO.Path]::GetFileName($Destination) -eq 'aurae' -and
        [IO.Path]::GetFileName($Source) -eq 'new' -and
        [IO.Path]::GetFileName([IO.Path]::GetDirectoryName($Source)) -like 'aurae-install-*') {
        $script:auraeTestFailed = $true
        # CONCURRENT_TARGET
        throw 'Simulated candidate promotion failure'
    }
    [IO.Directory]::Move($Source, $Destination)
}
"""
            if concurrent:
                override = override.replace("# CONCURRENT_TARGET", r"""
        [void][IO.Directory]::CreateDirectory($Destination)
        [IO.File]::WriteAllText((Join-Path $Destination 'concurrent.txt'), 'Concurrent content must survive')
""")
            override += f"Invoke-AuraeProjectInstall -SelectedAgent codex -SelectedVersion '{self.new_version}' -Updating\n"
            result = self.run_install(shell, case, update=True, ps_override=override,
                                      allow_retained_stage=concurrent, **downloads)
            self.assertIn('Simulated candidate promotion failure', result.stdout + result.stderr)
        else:
            shim = case["bin"] / "mv"
            source = r"""#!/usr/bin/env bash
set -euo pipefail
args=()
for arg in "$@"; do
  case "$arg" in -*) ;; *) args+=("$arg") ;; esac
done
source=${args[0]}
destination=${args[1]}
if [[ "$source" == */.aurae-install.*/aurae && ! -e "$AURAE_TEST_PROJECT_TARGET" &&
      ! -e "$AURAE_TEST_FAILURE_MARKER" ]]; then
  : > "$AURAE_TEST_FAILURE_MARKER"
  # CONCURRENT_TARGET
  echo 'Simulated candidate promotion failure' >&2
  exit 1
fi
if [ -x /bin/mv ]; then exec /bin/mv "$@"; fi
exec /usr/bin/mv "$@"
"""
            if concurrent:
                source = source.replace("# CONCURRENT_TARGET", r"""
  mkdir -- "$AURAE_TEST_PROJECT_TARGET"
  printf '%s' 'Concurrent content must survive' > "$AURAE_TEST_PROJECT_TARGET/concurrent.txt"
""")
            shim.write_text(source, encoding="utf-8", newline="\n")
            shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            marker = case["directory"] / "promotion-failed"
            setup = ("export AURAE_TEST_PROJECT_TARGET=" + shlex.quote(bash_path(target)) + "; "
                     + "export AURAE_TEST_FAILURE_MARKER=" + shlex.quote(bash_path(marker)) + "; ")
            result = self.run_install(shell, case, update=True, bash_setup=setup,
                                      allow_retained_stage=concurrent, **downloads)
            self.assertTrue(marker.is_file(), "The intended promotion failure must actually be injected")
        return result

    def test_failed_candidate_promotion_rolls_back_verified_original(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_fixture(case)
                before = self.snapshot(target)
                result = self.promotion_failure(shell, case)
                self.assert_preserved(result, case, before, backup=True)
                self.assert_backup(case)

    def test_backup_inside_project_is_refused_before_replacement(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                case["state_root"] = case["project"] / "backup state"
                target = self.install_fixture(case)
                before = self.snapshot(target)
                self.assert_preserved(self.run_install(shell, case, update=True), case, before)
                self.assertEqual(list(case["project"].rglob("skill.zip")), [])

    def test_manual_failed_candidate_promotion_rolls_back_actual_local_tree(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_manual_fixture(case)
                before = self.snapshot(target)
                result = self.promotion_failure(shell, case, **self.missing_manual_archive())
                self.assert_preserved(result, case, before, backup=True)
                self.assert_manual_backup(case, before)

    def test_manual_backup_inside_project_is_refused_before_replacement(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                case["state_root"] = case["project"] / "backup state"
                target = self.install_manual_fixture(case)
                before = self.snapshot(target)
                result = self.run_install(shell, case, update=True, **self.missing_manual_archive())
                self.assert_preserved(result, case, before)

    def manual_backup_fault(self, shell, case, concurrent=False):
        target = self.target(case)
        marker = case["directory"] / "backup-fault-injected"
        if shell[1] == "powershell":
            override = ". " + ps_literal(ROOT / "tools/install.ps1") + " -Help | Out-Null\n"
            override += "$script:auraeOriginalCopy = ${function:Copy-AuraeInstalledTree}\n"
            override += "function Copy-AuraeInstalledTree {\nparam([string]$Source, [string]$Destination, $Inventory)\n"
            override += "[IO.File]::WriteAllText(" + ps_literal(marker) + ", 'injected')\n"
            if concurrent:
                override += "& $script:auraeOriginalCopy -Source $Source -Destination $Destination -Inventory $Inventory\n"
                override += "[IO.File]::WriteAllText((Join-Path $Source 'concurrent-edit.md'), 'Concurrent edit must survive')\n"
            else:
                override += "throw 'Simulated actual-copy backup failure'\n"
            override += "}\n"
            override += f"Invoke-AuraeProjectInstall -SelectedAgent codex -SelectedVersion '{self.new_version}' -Updating\n"
            result = self.run_install(shell, case, update=True, ps_override=override,
                                      **self.missing_manual_archive())
        else:
            shim = case["bin"] / "cp"
            source = r"""#!/usr/bin/env bash
set -euo pipefail
destination=${!#}
case "$destination" in
  */previous-skill/|*/previous-skill)
    : > "$AURAE_TEST_FAILURE_MARKER"
    # BACKUP_FAULT
    ;;
esac
if [ -x /bin/cp ]; then exec /bin/cp "$@"; fi
exec /usr/bin/cp "$@"
"""
            if concurrent:
                injection = r"""
    if [ -x /bin/cp ]; then /bin/cp "$@"; else /usr/bin/cp "$@"; fi
    printf '%s' 'Concurrent edit must survive' > "$AURAE_TEST_PROJECT_TARGET/concurrent-edit.md"
    exit 0
"""
            else:
                injection = "echo 'Simulated actual-copy backup failure' >&2\n    exit 1"
            shim.write_text(source.replace("# BACKUP_FAULT", injection), encoding="utf-8", newline="\n")
            shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            setup = ("export AURAE_TEST_PROJECT_TARGET=" + shlex.quote(bash_path(target)) + "; "
                     + "export AURAE_TEST_FAILURE_MARKER=" + shlex.quote(bash_path(marker)) + "; ")
            result = self.run_install(shell, case, update=True, bash_setup=setup,
                                      **self.missing_manual_archive())
        self.assertTrue(marker.is_file(), "The actual-copy backup boundary must be reached")
        return result

    def test_manual_backup_failure_does_not_replace_the_current_copy(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_manual_fixture(case)
                before = self.snapshot(target)
                result = self.manual_backup_fault(shell, case)
                self.assert_preserved(result, case, before, backup=True)
                self.assertIn("Simulated actual-copy backup failure", result.stdout + result.stderr)

    def test_manual_concurrent_edit_during_backup_is_preserved_and_aborts_update(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_manual_fixture(case)
                before = self.snapshot(target)
                result = self.manual_backup_fault(shell, case, concurrent=True)
                after = dict(before, **{"concurrent-edit.md": ("file", b"Concurrent edit must survive")})
                self.assert_preserved(result, case, after, backup=True)
                # A completed pre-edit copy must remain available even though
                # detecting the concurrent edit prevented promotion.
                backups = self.backups(case)
                self.assertEqual(len(backups), 1)
                self.assertEqual(self.snapshot(backups[0]), before)

    def test_manual_blocked_rollback_preserves_concurrent_target_and_actual_old_tree(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_manual_fixture(case)
                before = self.snapshot(target)
                result = self.promotion_failure(shell, case, concurrent=True, **self.missing_manual_archive())
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.snapshot(target), {"concurrent.txt": ("file", b"Concurrent content must survive")})
                stages = list(target.parent.glob("aurae-install-*")) + list(target.parent.glob(".aurae-install.*"))
                self.assertEqual(len(stages), 1)
                previous = stages[0] / "previous"
                if shell[1] == "bash":
                    previous /= "aurae"
                self.assertEqual(self.snapshot(previous), before)
                self.assert_manual_backup(case, before)
                self.assertIn(stages[0].name, result.stdout + result.stderr)

    def test_blocked_rollback_preserves_concurrent_target_old_tree_and_backup(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.install_fixture(case)
                before = self.snapshot(target)
                result = self.promotion_failure(shell, case, concurrent=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.snapshot(target), {"concurrent.txt": ("file", b"Concurrent content must survive")},
                                 "Failed rollback must not delete or overwrite a concurrent target")
                stages = list(target.parent.glob("aurae-install-*")) + list(target.parent.glob(".aurae-install.*"))
                self.assertEqual(len(stages), 1, "Retain the displaced original for explicit manual recovery")
                previous = stages[0] / "previous"
                if shell[1] == "bash":
                    previous /= "aurae"
                self.assertEqual(self.snapshot(previous), before, "The displaced original must remain byte-complete")
                self.assert_backup(case)
                # PowerShell's console renderer wraps long paths across CLIXML
                # records; the unique retained stage must still be identified.
                self.assertIn(stages[0].name, result.stdout + result.stderr)
                self.assertIn("previous", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

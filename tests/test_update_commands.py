"""Offline transactional updates: verify provenance and never overlay a skill."""
from __future__ import annotations

import hashlib
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
    old_version = "0.1.0"
    new_version = "0.2.0"

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
        return sorted((case["directory"] / "local state").rglob("skill.zip"))

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
        variants = ("old-checksum", "old-unavailable", "new-checksum", "new-incomplete", "new-unavailable")
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
                        path = self.archive(case)
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

    def promotion_failure(self, shell, case, concurrent=False):
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
                                      allow_retained_stage=concurrent)
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
                                      allow_retained_stage=concurrent)
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

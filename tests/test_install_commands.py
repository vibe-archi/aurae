"""Exercise project installers with real bundles and offline download fixtures.

Only the network boundary is replaced. Hashing, ZIP validation, extraction and
no-overwrite checks execute the same scripts that the README offers to users.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
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
from common import ROOTS


def bash_path(path):
    """Translate only test-fixture paths for Git Bash, never use the WSL shim."""
    value = Path(path).absolute().as_posix()
    if os.name == "nt":
        return "/" + value[0].lower() + value[2:]
    return value


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


POWERSHELL_DOWNLOADS = r"""
function Invoke-RestMethod {
    [CmdletBinding()]
    param([string]$Uri, [hashtable]$Headers, [int]$TimeoutSec)
    Add-Content -LiteralPath $env:AURAE_TEST_REQUESTS -Value $Uri
    if ($Uri -eq 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.ps1') {
        if ($env:AURAE_TEST_FAIL -eq 'bootstrap') { throw 'Simulated unavailable bootstrap script' }
        return [IO.File]::ReadAllText($env:AURAE_TEST_SCRIPT)
    }
    if ($Uri -ne 'https://api.github.com/repos/vibe-archi/aurae/releases/latest') {
        throw "Unexpected API URL: $Uri"
    }
    if ($env:AURAE_TEST_FAIL -eq 'latest') { throw 'Simulated unavailable release API' }
    return @{tag_name=$env:AURAE_TEST_TAG; draft=$false; prerelease=$false}
}
function Invoke-WebRequest {
    [CmdletBinding()]
    param([string]$Uri, [string]$OutFile, [hashtable]$Headers, [switch]$UseBasicParsing, [int]$TimeoutSec)
    Add-Content -LiteralPath $env:AURAE_TEST_REQUESTS -Value $Uri
    if ($Uri -cnotmatch '^https://github\.com/vibe-archi/aurae/releases/download/v([0-9]+\.[0-9]+\.[0-9]+)/([^/]+)$') {
        throw "Unexpected download URL: $Uri"
    }
    $downloadVersion = $Matches[1]
    $name = $Matches[2]
    if ($name -notmatch '^(SHA256SUMS|aurae-(codex|claude)-[0-9]+\.[0-9]+\.[0-9]+\.zip)$') {
        throw "Unexpected download filename: $name"
    }
    if ($env:AURAE_TEST_FAIL -eq $name -or $env:AURAE_TEST_FAIL -eq "$downloadVersion/$name") { throw 'Simulated unavailable download' }
    $sourceRoot = Join-Path $env:AURAE_TEST_ASSETS $downloadVersion
    if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) { $sourceRoot = $env:AURAE_TEST_ASSETS }
    Copy-Item -LiteralPath (Join-Path $sourceRoot $name) -Destination $OutFile -ErrorAction Stop
}
"""

BASH_DOWNLOADS = r"""#!/usr/bin/env bash
set -euo pipefail
destination=''
write_format=''
url=''
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o|--output) destination=$2; shift 2 ;;
    -w|--write-out) write_format=$2; shift 2 ;;
    --) shift ;;
    -*) shift ;;
    *) url=$1; shift ;;
  esac
done
printf '%s\n' "$url" >> "$AURAE_TEST_REQUESTS"
if [ "$url" = 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.sh' ]; then
  [ "$AURAE_TEST_FAIL" != bootstrap ] || exit 22
  cat "$AURAE_TEST_SCRIPT"
  exit 0
fi
if [ "$url" = 'https://github.com/vibe-archi/aurae/releases/latest' ]; then
  [ "$AURAE_TEST_FAIL" != latest ] || exit 22
  [ "$write_format" = '%{url_effective}' ] || { echo 'Unexpected latest request' >&2; exit 90; }
  printf '%s' "$AURAE_TEST_LATEST_URL"
  exit 0
fi
release_pattern='^https://github\.com/vibe-archi/aurae/releases/download/v([0-9]+\.[0-9]+\.[0-9]+)/([^/]+)$'
[[ "$url" =~ $release_pattern ]] || { echo "Unexpected download URL: $url" >&2; exit 90; }
download_version=${BASH_REMATCH[1]}
name=${BASH_REMATCH[2]}
case "$name" in
  SHA256SUMS|aurae-codex-"$download_version".zip|aurae-claude-"$download_version".zip) ;;
  *) echo "Unexpected filename: $name" >&2; exit 90 ;;
esac
[ "$AURAE_TEST_FAIL" != "$name" ] && [ "$AURAE_TEST_FAIL" != "$download_version/$name" ] || exit 22
[ -n "$destination" ] || { echo 'Missing download destination' >&2; exit 90; }
source_root="$AURAE_TEST_ASSETS/$download_version"
[ -d "$source_root" ] || source_root=$AURAE_TEST_ASSETS
cp "$source_root/$name" "$destination"
"""


class InstallerFixture:
    @classmethod
    def setUpClass(cls):
        (ROOT / ".scratchpad").mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix="installer-tests-", dir=ROOT / ".scratchpad")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        cls.assets = build(ROOT, cls.work / "built-assets", "vibe-archi/aurae")
        cls.version = json.loads((cls.assets / "build-info.json").read_text(encoding="utf-8"))["agent_skill"]
        cls.shells = []
        for name in (("powershell", "pwsh") if os.name == "nt" else ()):
            executable = shutil.which(name)
            if executable:
                cls.shells.append((name, "powershell", executable))
        if os.name == "nt":
            candidates = [Path("C:/Program Files/Git/bin/bash.exe"),
                          Path("C:/Program Files/Git/usr/bin/bash.exe")]
            executable = next((str(path) for path in candidates if path.is_file()), None)
            # shutil.which("bash") commonly returns the unavailable WSL launcher.
        else:
            executable = shutil.which("bash")
            if not executable:
                raise AssertionError("Linux/macOS installer tests require Bash")
        if executable:
            cls.shells.append(("bash", "bash", executable))
        if not cls.shells:
            raise AssertionError("No supported installer shell is available")

    def setUp(self):
        self.case_number = 0

    def case(self):
        self.case_number += 1
        # Short fixture roots leave room for the real package's long paths on
        # Windows hosts without long-path support; the project still has spaces.
        label = hashlib.sha256(self._testMethodName.encode()).hexdigest()[:8]
        directory = self.work / label / str(self.case_number)
        assets = directory / "remote assets"
        shutil.copytree(self.assets, assets)
        project = directory / "project with spaces"
        project.mkdir()
        (project / "keep-user-file.txt").write_text("User content must remain untouched.\n", encoding="utf-8")
        downloads = directory / "temporary downloads"
        downloads.mkdir()
        mock_bin = directory / "mock bin"
        mock_bin.mkdir()
        curl = mock_bin / "curl"
        curl.write_text(BASH_DOWNLOADS, encoding="utf-8", newline="\n")
        curl.chmod(curl.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return {"directory": directory, "assets": assets, "project": project,
                "downloads": downloads, "bin": mock_bin, "requests": directory / "requests.txt"}

    def target(self, case, agent="codex"):
        return case["project"] / ROOTS[agent]

    def archive(self, case, agent="codex"):
        return case["assets"] / f"aurae-{agent}-{self.version}.zip"

    def checksums(self, case):
        lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                 for path in sorted(case["assets"].glob("*.zip"))]
        (case["assets"] / "SHA256SUMS").write_text("".join(lines), encoding="utf-8", newline="\n")

    def run_install(self, shell, case, agent="codex", version="explicit", fail="", extra=(),
                    latest_tag=None, latest_url=None, bootstrap=False, update=False,
                    ps_override="", bash_setup="", allow_retained_stage=False):
        name, kind, executable = shell
        environment = dict(os.environ, AURAE_TEST_VERSION=self.version,
                           AURAE_TEST_TAG=latest_tag or f"v{self.version}",
                           AURAE_TEST_LATEST_URL=latest_url or f"https://github.com/vibe-archi/aurae/releases/tag/v{self.version}",
                           AURAE_TEST_FAIL=fail)
        # A Python process launched by pwsh may inherit its PowerShell 7 module
        # path. Let each tested PowerShell engine discover its own stock modules.
        for key in list(environment):
            if key.lower() == "psmodulepath":
                del environment[key]
        for variable, key in (("AURAE_TEST_ASSETS", "assets"), ("AURAE_TEST_REQUESTS", "requests"),
                              ("TEMP", "downloads"), ("TMP", "downloads"), ("TMPDIR", "downloads")):
            environment[variable] = bash_path(case[key]) if kind == "bash" else str(case[key])
        state = case.get("state_root", case["directory"] / "local state")
        state.mkdir(exist_ok=True)
        for variable in ("LOCALAPPDATA", "XDG_STATE_HOME"):
            environment[variable] = bash_path(state) if kind == "bash" else str(state)
        script = ROOT / "tools" / ("install.ps1" if kind == "powershell" else "install.sh")
        environment["AURAE_TEST_SCRIPT"] = bash_path(script) if kind == "bash" else str(script)
        selected_version = self.version if version == "explicit" else version
        if kind == "powershell":
            arguments = ["-Agent", ps_literal(agent)]
            if selected_version is not None:
                arguments += ["-Version", ps_literal(selected_version)]
            if update:
                arguments.append("-Update")
            arguments += [ps_literal(value) for value in extra]
            command = ("$ErrorActionPreference = 'Stop'\n" + POWERSHELL_DOWNLOADS + "\n& "
                       + ps_literal(ROOT / "tools/install.ps1") + " " + " ".join(arguments))
            if bootstrap:
                command = "$ErrorActionPreference = 'Stop'\n" + POWERSHELL_DOWNLOADS + "\n" + self.bootstrap_command(kind, agent, update)
            if ps_override:
                command = "$ErrorActionPreference = 'Stop'\n" + POWERSHELL_DOWNLOADS + "\n" + ps_override
            encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
            command = [executable, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
        else:
            arguments = ["--agent", agent]
            if selected_version is not None:
                arguments += ["--version", selected_version]
            if update:
                arguments.append("--update")
            arguments += list(extra)
            command = ("export PATH=" + shlex.quote(bash_path(case["bin"])) + ':"$PATH"; '
                       + bash_setup + "bash " + shlex.quote(bash_path(ROOT / "tools/install.sh")) + " "
                       + " ".join(shlex.quote(value) for value in arguments))
            if bootstrap:
                command = ("export PATH=" + shlex.quote(bash_path(case["bin"])) + ':"$PATH"; '
                           + bash_setup + self.bootstrap_command(kind, agent, update))
            command = [executable, "-c", command]
        result = subprocess.run(command, cwd=case["project"], env=environment, capture_output=True,
                                encoding="utf-8", errors="replace", timeout=90)
        self.assertEqual(list(case["downloads"].iterdir()), [], "Download staging must be cleaned after success or failure")
        staging = list(case["project"].glob(".*/skills/.aurae-install*")) + list(case["project"].glob(".*/skills/aurae-install*"))
        if not allow_retained_stage:
            self.assertEqual(staging, [], "Project staging must be cleaned after success or recoverable failure")
        return result

    def bootstrap_command(self, language, agent, update=False):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        flag = f"-Agent {agent}" if language == "powershell" else f"--agent {agent}"
        blocks = re.findall(r"```(powershell|bash)\r?\n(.*?)\r?\n```", text, re.S)
        commands = [body for kind, body in blocks if kind == language and flag in body
                    and "https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install." in body
                    and bool(re.search(r"(?:-Update|--update)\b", body)) == update]
        self.assertTrue(commands, f"Missing README bootstrap command for {language}/{agent}")
        return commands[0]

    def assert_installed(self, result, case, agent):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        target = self.target(case, agent)
        with zipfile.ZipFile(self.archive(case, agent)) as archive:
            for name in ("SKILL.md", "vendor.md", "aurae-skill.yaml"):
                self.assertEqual((target / name).read_bytes(), archive.read(ROOTS[agent] + name))
        self.assertEqual((case["project"] / "keep-user-file.txt").read_text(encoding="utf-8"),
                         "User content must remain untouched.\n")

    def assert_refused(self, result, case, agent="codex"):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.target(case, agent).exists(), "A refused archive must not install a partial skill")
        self.assertEqual((case["project"] / "keep-user-file.txt").read_text(encoding="utf-8"),
                         "User content must remain untouched.\n")


class InstallCommandTests(InstallerFixture, unittest.TestCase):
    def test_readme_and_guide_offer_each_official_bootstrap_command(self):
        for filename in ("README.md", "docs/install.md"):
            text = (ROOT / filename).read_text(encoding="utf-8")
            blocks = re.findall(r"```(powershell|bash)\r?\n(.*?)\r?\n```", text, re.S)
            for language, script in (("powershell", "install.ps1"), ("bash", "install.sh")):
                url = f"https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/{script}"
                for agent in ("codex", "claude"):
                    with self.subTest(document=filename, language=language, agent=agent):
                        flag = f"-Agent {agent}" if language == "powershell" else f"--agent {agent}"
                        matching = [body for lang, body in blocks if lang == language and url in body and flag in body
                                    and not re.search(r"(?:-Update|--update)\b", body)]
                        self.assertTrue(matching, f"Missing explicit {agent} one-line command in {filename}")
                        self.assertTrue(any(len(body.strip().splitlines()) == 1 for body in matching))

    def test_explicit_version_installs_both_agents_and_preserves_existing_target(self):
        for shell in self.shells:
            for agent in ROOTS:
                with self.subTest(shell=shell[0], agent=agent):
                    case = self.case()
                    result = self.run_install(shell, case, agent)
                    self.assert_installed(result, case, agent)
                    request_count = len(case["requests"].read_text(encoding="utf-8-sig").splitlines())
                    self.assertEqual(request_count, 2, "Pinned installation should download only ZIP and checksums")
                    marker = self.target(case, agent) / "local-customization.txt"
                    marker.write_text("Keep my customization", encoding="utf-8")
                    original = (self.target(case, agent) / "SKILL.md").read_bytes()
                    retry = self.run_install(shell, case, agent)
                    self.assertNotEqual(retry.returncode, 0)
                    self.assertEqual(marker.read_text(encoding="utf-8"), "Keep my customization")
                    self.assertEqual((self.target(case, agent) / "SKILL.md").read_bytes(), original)
                    self.assertEqual(len(case["requests"].read_text(encoding="utf-8-sig").splitlines()), request_count,
                                     "Existing installation must be rejected before downloading")

    def test_readme_bootstrap_executes_and_reports_download_failure(self):
        for shell in self.shells:
            for failure in ("", "bootstrap"):
                with self.subTest(shell=shell[0], failure=failure):
                    case = self.case()
                    result = self.run_install(shell, case, version=None, fail=failure, bootstrap=True)
                    if failure:
                        self.assert_refused(result, case)
                    else:
                        self.assert_installed(result, case, "codex")

    def test_latest_release_and_prefixed_version(self):
        for shell in self.shells:
            for version, agent in ((None, "codex"), (f"v{self.version}", "claude")):
                with self.subTest(shell=shell[0], version=version, agent=agent):
                    case = self.case()
                    self.assert_installed(self.run_install(shell, case, agent, version), case, agent)
                    requests = case["requests"].read_text(encoding="utf-8-sig")
                    self.assertEqual("/releases/latest" in requests, version is None)

    def test_invalid_agent_version_and_unknown_option_fail_without_network(self):
        for shell in self.shells:
            scenarios = [("not-an-agent", "explicit", ()), ("codex", "../1.0.0", ()),
                         ("codex", "1.0.0-beta", ()),
                         ("codex", "explicit", ("-Unknown" if shell[1] == "powershell" else "--unknown",))]
            for agent, version, extra in scenarios:
                with self.subTest(shell=shell[0], agent=agent, version=version, extra=extra):
                    case = self.case()
                    result = self.run_install(shell, case, agent, version, extra=extra)
                    self.assert_refused(result, case)
                    self.assertFalse(case["requests"].exists(), "Invalid arguments must be rejected before downloads")

    def test_unavailable_download_or_latest_release_does_not_install(self):
        for shell in self.shells:
            for failure in (f"aurae-codex-{self.version}.zip", "SHA256SUMS", "latest"):
                with self.subTest(shell=shell[0], failure=failure):
                    case = self.case()
                    version = None if failure == "latest" else "explicit"
                    self.assert_refused(self.run_install(shell, case, version=version, fail=failure), case)

    def test_latest_release_must_resolve_to_official_stable_tag(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                result = self.run_install(shell, case, version=None, latest_tag="v1.0.0-beta",
                                          latest_url="https://example.invalid/releases/tag/v1.0.0")
                self.assert_refused(result, case)
                self.assertEqual(len(case["requests"].read_text(encoding="utf-8-sig").splitlines()), 1,
                                 "Invalid release metadata must not trigger package downloads")

    def test_corrupt_download_and_missing_or_duplicate_checksum_do_not_install(self):
        for shell in self.shells:
            for variant in ("corrupt", "missing", "duplicate"):
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    sums = case["assets"] / "SHA256SUMS"
                    if variant == "corrupt":
                        archive = self.archive(case)
                        archive.write_bytes(archive.read_bytes() + b"corrupt")
                    else:
                        lines = sums.read_text(encoding="utf-8").splitlines(keepends=True)
                        entry = next(line for line in lines if self.archive(case).name in line)
                        content = "".join(line for line in lines if line != entry) if variant == "missing" else "".join(lines) + entry
                        sums.write_text(content, encoding="utf-8", newline="\n")
                    self.assert_refused(self.run_install(shell, case), case)

    def malformed_archive(self, case, variant):
        path = self.archive(case)
        prefix = ROOTS["codex"]
        with zipfile.ZipFile(path) as source:
            payload = [(entry, source.read(entry)) for entry in source.infolist()]
        if variant == "missing-required":
            payload = [(entry, data) for entry, data in payload if entry.filename != prefix + "vendor.md"]
        if variant == "empty-required":
            payload = [(entry, b"" if entry.filename == prefix + "SKILL.md" else data) for entry, data in payload]
        with zipfile.ZipFile(path, "w") as archive:
            for entry, data in payload:
                archive.writestr(entry, data)
            extra = {"traversal": prefix + "../../../../escaped.txt", "absolute": "/escaped.txt",
                     "wrong-prefix": ROOTS["claude"] + "unexpected.txt", "backslash": prefix + "bad\\name.txt",
                     "case-collision": prefix + "skill.md", "file-as-parent": prefix + "SKILL.md/child.txt",
                     "symlink": prefix + "linked-file", "device": prefix + "special-file"}
            if variant in extra:
                entry = zipfile.ZipInfo(extra[variant])
                # ZipInfo normalizes Windows separators in its constructor.
                # Restore the deliberately unsafe spelling so this fixture
                # actually contains a backslash on Windows as well as Unix.
                entry.filename = extra[variant]
                entry.create_system = 3
                mode = 0o120777 if variant == "symlink" else 0o020600 if variant == "device" else 0o100644
                entry.external_attr = mode << 16
                archive.writestr(entry, "../../outside.txt" if variant == "symlink" else "Unsafe fixture")
        self.checksums(case)

    def test_verified_but_unsafe_or_incomplete_zip_is_rejected(self):
        variants = ("traversal", "absolute", "wrong-prefix", "backslash", "case-collision",
                    "file-as-parent", "symlink", "device", "missing-required", "empty-required")
        for shell in self.shells:
            for variant in variants:
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    self.malformed_archive(case, variant)
                    self.assert_refused(self.run_install(shell, case), case)
                    self.assertFalse((case["project"] / "escaped.txt").exists())
                    self.assertFalse((case["directory"] / "escaped.txt").exists())

    def test_existing_target_file_is_not_replaced(self):
        for shell in self.shells:
            with self.subTest(shell=shell[0]):
                case = self.case()
                target = self.target(case)
                target.parent.mkdir(parents=True)
                target.write_text("Existing user file", encoding="utf-8")
                result = self.run_install(shell, case)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_text(encoding="utf-8"), "Existing user file")
                self.assertFalse(case["requests"].exists())

    def test_symlinked_target_and_ancestor_are_not_followed(self):
        exercised = False
        for shell in self.shells:
            for variant in ("target", "dangling-target", "ancestor"):
                with self.subTest(shell=shell[0], variant=variant):
                    case = self.case()
                    outside = case["directory"] / "outside project"
                    outside.mkdir()
                    marker = outside / "keep.txt"
                    marker.write_text("Keep outside content", encoding="utf-8")
                    link = case["project"] / ".agents" if variant == "ancestor" else self.target(case)
                    link.parent.mkdir(parents=True, exist_ok=True)
                    destination = outside / "nonexistent" if variant == "dangling-target" else outside
                    try:
                        link.symlink_to(destination, target_is_directory=True)
                    except (OSError, NotImplementedError):
                        continue  # Windows hosts may not grant symlink creation.
                    exercised = True
                    result = self.run_install(shell, case)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(link.is_symlink())
                    self.assertEqual(list(outside.iterdir()), [marker])
                    self.assertEqual(marker.read_text(encoding="utf-8"), "Keep outside content")
                    self.assertFalse(case["requests"].exists(), "Unsafe destinations must be rejected before network access")
        if not exercised:
            self.skipTest("This host does not grant directory symlink creation")


if __name__ == "__main__":
    unittest.main()

"""Exercise the documented commands with a local fake download, never GitHub."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build import build


class InstallCommandTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".scratchpad").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="install-test-", dir=ROOT / ".scratchpad")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.assets = build(ROOT, self.work / "assets", "vibe-archi/aurae")
        self.project = self.work / "project with spaces"
        self.project.mkdir()
        self.downloads = self.work / "downloads"
        self.downloads.mkdir()
        self.env = dict(os.environ, AURAE_TEST_ASSETS=str(self.assets), TEMP=str(self.downloads), TMP=str(self.downloads), TMPDIR=str(self.downloads))
        self.guide = (ROOT / "docs/install.md").read_text(encoding="utf-8")

    def target(self, agent):
        return self.project / (".agents" if agent == "codex" else ".claude") / "skills/aurae/SKILL.md"

    def command(self, language, agent):
        command = re.search(rf"```{language}\n(.*?)\n```", self.guide, re.S)[1]
        if agent == "claude":
            command = command.replace("='codex'", "='claude'").replace("aurae_agent=codex", "aurae_agent=claude").replace(".agents/skills/aurae", ".claude/skills/aurae")
        return command

    @unittest.skipUnless(os.name == "nt", "Windows command is exercised on Windows")
    def test_powershell_install_both_agents_and_refuse_overwrite(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        self.assertIsNotNone(shell)
        # Emulate only gh's download result. The guide's hashing and extraction run unchanged.
        stub = r'''
function gh {
    $auraeArgs = @($args)
    $auraeIndex = [Array]::IndexOf($auraeArgs, '--dir')
    if($auraeIndex -lt 0){throw 'Expected a download directory'}
    Get-ChildItem -LiteralPath $env:AURAE_TEST_ASSETS -File | Copy-Item -Destination $auraeArgs[$auraeIndex + 1]
    $global:LASTEXITCODE = 0
}
'''
        for agent in ("codex", "claude"):
            command = stub + self.command("powershell", agent)
            result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", command], env=self.env, cwd=self.project, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(self.target(agent).is_file())
            before = self.target(agent).read_bytes()
            retry = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", command], env=self.env, cwd=self.project, capture_output=True, text=True)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(self.target(agent).read_bytes(), before)

    @unittest.skipUnless(os.name == "nt", "Windows command is exercised on Windows")
    def test_powershell_corrupt_download_does_not_install(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        for archive in self.assets.glob("*.zip"):
            archive.write_bytes(archive.read_bytes() + b"corrupt")
        stub = r'''
function gh {
    $auraeArgs = @($args)
    $auraeIndex = [Array]::IndexOf($auraeArgs, '--dir')
    Get-ChildItem -LiteralPath $env:AURAE_TEST_ASSETS -File | Copy-Item -Destination $auraeArgs[$auraeIndex + 1]
    $global:LASTEXITCODE = 0
}
'''
        result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", stub + self.command("powershell", "codex")], env=self.env, cwd=self.project, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.target("codex").exists())

    @unittest.skipIf(os.name == "nt", "Bash command is exercised on Linux/macOS CI")
    def test_bash_install_both_agents_and_refuse_overwrite(self):
        for executable in ("bash", "unzip", "shasum"):
            self.assertIsNotNone(shutil.which(executable), f"Missing CI prerequisite: {executable}")
        stub = '''gh() { local dest=''; while [ "$#" -gt 0 ]; do if [ "$1" = '--dir' ]; then shift; dest="$1"; fi; shift; done; cp "$AURAE_TEST_ASSETS/"* "$dest/"; }; '''
        for agent in ("codex", "claude"):
            command = stub + self.command("bash", agent)
            result = subprocess.run(["bash", "-c", command], env=self.env, cwd=self.project, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(self.target(agent).is_file())
            retry = subprocess.run(["bash", "-c", command], env=self.env, cwd=self.project, capture_output=True, text=True)
            self.assertNotEqual(retry.returncode, 0)


if __name__ == "__main__":
    unittest.main()

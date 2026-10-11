"""Run the reviewed, Markdown-embedded helper self-tests in disposable repositories."""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile

from common import PackageError, require


def main():
    root = Path(__file__).resolve().parents[1]
    scratch = root / ".scratchpad" / "helper-tests"
    scratch.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=scratch))
    references = root / "skills/aurae/references"
    sources = {
        "validator": ("workspace-validator-source.md", "AURAE_REFERENCE_VALIDATOR", "1.1.0"),
        "storage": ("git-storage-source.md", "AURAE_GIT_STORAGE_REFERENCE", "1.0.0"),
        "merge": ("git-merge-source.md", "AURAE_GIT_MERGE_REFERENCE", "1.0.0"),
    }
    files = {}
    for name, (filename, marker, version) in sources.items():
        text = (references / filename).read_text(encoding="utf-8")
        matches = re.findall(rf'(# <{marker} version="{re.escape(version)}">\n.*?\n# </{marker}>)', text, re.S)
        require(len(matches) == 1, "Missing or ambiguous reviewed helper source")
        files[name] = work / f"{name}.py"
        files[name].write_text(matches[0] + "\n", encoding="utf-8", newline="\n")
    commands = {
        "validator": [str(files["validator"]), "--self-test"],
        "storage": [str(files["storage"]), "self-test", "--scratch-root", str(work)],
        "merge": [str(files["merge"]), "--storage-source", str(files["storage"]),
                  "--validator-source", str(files["validator"]), "--scratch-root", str(work), "self-test"],
    }
    for name, args in commands.items():
        result = subprocess.run([sys.executable, "-B", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=180)
        (work / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        require(result.returncode == 0, f"{name} self-test failed; inspect {work / (name + '.log')}")
        report = json.loads(result.stdout)
        require(report.get("passed") is True, f"{name} did not report passing")
        print(f"PASS: {name} ({len(report['cases'])} cases)" if "cases" in report else f"PASS: {name}", flush=True)
    print(f"Local diagnostic reports: {work}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PackageError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Self-test failed: {error}", file=sys.stderr)
        raise SystemExit(1)

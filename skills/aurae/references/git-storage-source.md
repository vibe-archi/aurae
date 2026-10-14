# Transparent reference source

Read completely before first local materialization or adaptation, or when this source changes. The operational contract and invocation are in [git-storage-harness.md](git-storage-harness.md). Distribute this source only as Markdown; materialize runnable files solely inside ignored `.scratchpad/`.

~~~~python
# <AURAE_GIT_STORAGE_REFERENCE version="1.0.1">
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

VERSION = "1.0.1"
AURAE_REF_RE = re.compile(r"^refs/heads/aurae/[A-Za-z0-9._/-]+$")


class HarnessError(RuntimeError):
    pass


def emit(value: dict[str, Any], code: int = 0) -> int:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
    return code


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise HarnessError(f"{argv[0]} operation failed: {detail}")
    return result


def git(repo: Path, *args: str, input_text: str | None = None, check: bool = True):
    return run(["git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false", "-C", str(repo), *args], input_text=input_text, check=check)


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false", "-C", str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    if result.returncode:
        raise HarnessError("Unable to read exact Git object bytes.")
    return result.stdout


def repo_root(value: str | Path) -> Path:
    candidate = Path(value).resolve()
    result = git(candidate, "rev-parse", "--show-toplevel")
    root = Path(result.stdout.strip()).resolve()
    if not root.is_dir():
        raise HarnessError("Git repository root is unavailable.")
    return root


def inside(path: Path, parent: Path) -> bool:
    path = path.resolve()
    parent = parent.resolve()
    return path == parent or parent in path.parents


def require_inside(path: Path, parent: Path, label: str) -> None:
    if not inside(path, parent):
        raise HarnessError(f"{label} escaped its approved root.")


def remove_test_tree(path: Path, parent: Path) -> None:
    require_inside(path, parent, "Self-test cleanup")

    def make_writable(function, value, _error):
        os.chmod(value, stat.S_IWRITE)
        function(value)

    shutil.rmtree(path, onerror=make_writable)


def split_z(value: str) -> list[str]:
    return [item for item in value.split("\0") if item]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()


def optional_ref(repo: Path, ref: str) -> str | None:
    result = git(repo, "show-ref", "--verify", "--quiet", ref, check=False)
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise HarnessError("Unable to inspect the requested AURAE ref.")
    return commit_oid(repo, ref)


def commit_oid(repo: Path, value: str) -> str:
    result = git(repo, "rev-parse", "--verify", f"{value}^{{commit}}")
    return result.stdout.strip()


def validate_aurae_ref(repo: Path, ref: str) -> None:
    invalid = ".." in ref or "//" in ref or "@{" in ref or ref.endswith(("/", ".lock"))
    if invalid or not AURAE_REF_RE.fullmatch(ref):
        raise HarnessError("Only a well-formed refs/heads/aurae/* ref is allowed.")
    if git(repo, "check-ref-format", ref, check=False).returncode != 0:
        raise HarnessError("The AURAE ref is not valid for this Git version.")


def zero_oid(repo: Path) -> str:
    result = git(repo, "rev-parse", "--show-object-format", check=False)
    return "0" * (64 if result.returncode == 0 and result.stdout.strip() == "sha256" else 40)


def metadata_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized == ".aurae" or normalized.startswith(".aurae/")


def require_metadata_paths(paths: list[str], label: str) -> None:
    bad = sorted(path for path in paths if not metadata_path(path))
    if bad:
        raise HarnessError(f"{label} contains paths outside .aurae/.")


def require_metadata_tree(repo: Path, revision: str) -> None:
    paths = split_z(git(repo, "ls-tree", "-r", "--name-only", "-z", revision).stdout)
    require_metadata_paths(paths, "Metadata tree")


def metadata_entries(repo: Path, revision: str):
    entries = []
    for entry in git_bytes(repo, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = meta.split(b" ")
        path = raw_path.decode("utf-8")
        if mode not in {b"100644", b"100755"} or kind != b"blob" or not path.startswith(".aurae/"):
            raise HarnessError("Metadata tree must contain only regular files below .aurae/.")
        entries.append((path, oid.decode("ascii")))
    return sorted(entries)


def tree_fingerprint(repo: Path, revision: str) -> str:
    digest = hashlib.sha256()
    for path, oid in metadata_entries(repo, revision):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(git_bytes(repo, "cat-file", "blob", oid)).digest())
    return digest.hexdigest()


def developer_content_fingerprint(repo: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(set(split_z(git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout)))
    for relative in paths:
        path = repo / relative
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"link\0" + os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(b"file\0")
            file_hash = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    file_hash.update(block)
            digest.update(file_hash.digest())
        elif path.is_dir():
            digest.update(b"directory\0")
        else:
            digest.update(b"absent\0")
    return digest.hexdigest()


def snapshot(repo: Path) -> dict[str, Any]:
    repo = repo_root(repo)
    branch_result = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    head_result = git(repo, "rev-parse", "--verify", "HEAD", check=False)
    index_diff = git(repo, "diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv").stdout
    status = git(repo, "status", "--porcelain=v2", "-z", "--untracked-files=all").stdout
    worktrees = git(repo, "worktree", "list", "--porcelain").stdout
    return {
        "repository": str(repo),
        "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else None,
        "head": head_result.stdout.strip() if head_result.returncode == 0 else None,
        "index_sha256": sha256_text(index_diff),
        "status_sha256": sha256_text(status),
        "content_sha256": developer_content_fingerprint(repo),
        "worktrees_sha256": sha256_text(worktrees),
    }


def verify_snapshot(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    keys = ("repository", "branch", "head", "index_sha256", "status_sha256", "content_sha256", "worktrees_sha256")
    changed = [key for key in keys if expected.get(key) != actual.get(key)]
    if changed:
        raise HarnessError("Developer Git state changed: " + ", ".join(changed))


def verify_developer_during_operation(state):
    repo, candidate = Path(state["repository"]), Path(state["candidate"]).resolve()
    actual = snapshot(repo)
    blocks = git(repo, "worktree", "list", "--porcelain").stdout.split("\n\n")
    kept = []
    for block in blocks:
        first = block.splitlines()[0] if block else ""
        if first.startswith("worktree ") and Path(first[9:]).resolve() == candidate:
            continue
        kept.append(block)
    actual["worktrees_sha256"] = sha256_text("\n\n".join(kept))
    verify_snapshot(state["developer_snapshot"], actual)


def ensure_scratch(repo: Path, value: str | Path) -> Path:
    root = (repo / ".scratchpad").resolve()
    if not root.is_dir():
        raise HarnessError("Repository-root .scratchpad/ must exist before using the Harness.")
    scratch = Path(value).resolve()
    require_inside(scratch, root, "Scratch path")
    relative = scratch.relative_to(repo).as_posix()
    probe = f"{relative}/.aurae-ignore-probe"
    ignored = git(repo, "check-ignore", "-q", "--no-index", "--", probe, check=False)
    if ignored.returncode != 0:
        raise HarnessError("The selected scratch path is not ignored by Git.")
    if git(repo, "ls-files", "-z", "--", ".scratchpad").stdout:
        raise HarnessError("Scratchpad contains tracked files; resolve tracking before using the Harness.")
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def load_state(value: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(value).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("contract") != "aurae-git-storage-candidate" or data.get("version") != VERSION:
        raise HarnessError("Candidate state contract is unsupported.")
    repo = repo_root(data["repository"])
    scratch = ensure_scratch(repo, data["scratch_root"])
    require_inside(path, scratch, "Candidate state")
    candidate = Path(data["candidate"]).resolve()
    require_inside(candidate, scratch, "Candidate worktree")
    return path, data


def workspace_fingerprint(candidate: Path) -> str:
    root = candidate / ".aurae"
    if not root.is_dir():
        raise HarnessError("Candidate .aurae/ tree is missing.")
    digest = hashlib.sha256()
    files = sorted((path for path in root.rglob("*") if path.is_file() or path.is_symlink()), key=lambda path: path.relative_to(candidate).as_posix())
    for path in files:
        if path.is_symlink():
            raise HarnessError("Symlinks are not allowed in canonical AURAE metadata.")
        require_inside(path, root, "Metadata file")
        relative = path.relative_to(candidate).as_posix()
        content = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def worktree_registered(repo: Path, candidate: Path) -> bool:
    lines = git(repo, "worktree", "list", "--porcelain").stdout.splitlines()
    registered = [
        Path(line[9:]).resolve()
        for line in lines
        if line.startswith("worktree ")
    ]
    return candidate.resolve() in registered


def create_candidate(
    repo_value: str | Path,
    scratch_value: str | Path,
    *,
    publish_ref: str,
    base: str | None,
    expected_ref: str | None,
    bootstrap: bool,
) -> dict[str, Any]:
    repo = repo_root(repo_value)
    scratch = ensure_scratch(repo, scratch_value)
    validate_aurae_ref(repo, publish_ref)
    before = snapshot(repo)
    git(repo, "var", "GIT_AUTHOR_IDENT")

    current = optional_ref(repo, publish_ref)
    if bootstrap:
        if current is not None:
            raise HarnessError("Bootstrap requires an absent publication ref.")
        empty_tree = git(repo, "hash-object", "-t", "tree", "--stdin", input_text="").stdout.strip()
        base_oid = git(repo, "commit-tree", empty_tree, "-m", "AURAE metadata root").stdout.strip()
        expected_oid = None
    else:
        if base is None:
            raise HarnessError("A base commit is required.")
        base_oid = commit_oid(repo, base)
        require_metadata_tree(repo, base_oid)
        expected_oid = None if expected_ref in (None, "absent") else commit_oid(repo, expected_ref)
        if current != expected_oid:
            raise HarnessError("Publication ref does not match the expected revision.")
        if expected_oid is not None and base_oid != expected_oid:
            raise HarnessError("An existing ref must open from its exact expected revision; integrate earlier contribution commits through validated CAS.")

    candidate = scratch / f"candidate-{uuid.uuid4().hex[:12]}"
    state_path = scratch / f"{candidate.name}.state.json"
    if candidate.exists() or state_path.exists():
        raise HarnessError("Generated candidate path already exists.")

    git(repo, "worktree", "add", "--detach", str(candidate), base_oid)
    try:
        if commit_oid(candidate, "HEAD") != base_oid:
            raise HarnessError("Candidate worktree did not attach to the expected base.")
        require_metadata_tree(repo, base_oid)
        state = {
            "contract": "aurae-git-storage-candidate",
            "version": VERSION,
            "repository": str(repo),
            "scratch_root": str(scratch),
            "candidate": str(candidate),
            "publish_ref": publish_ref,
            "expected_ref": expected_oid,
            "base_commit": base_oid,
            "developer_snapshot": before,
            "validation": None,
            "new_commit": None,
            "published": False,
            "cleaned": False,
        }
        write_json(state_path, state)
        return {"ok": True, "state_file": str(state_path), "candidate": str(candidate)}
    except Exception:
        git(repo, "worktree", "remove", str(candidate), check=False)
        raise


def seal_candidate(state_value: str | Path, validation_value: str | Path) -> dict[str, Any]:
    state_path, state = load_state(state_value)
    scratch = Path(state["scratch_root"]).resolve()
    result_path = Path(validation_value).resolve()
    require_inside(result_path, scratch, "Validation result")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("valid") is not True or result.get("errors") not in (None, []):
        raise HarnessError("Workspace conformance result is not valid.")
    fingerprint = workspace_fingerprint(Path(state["candidate"]))
    binding = result.get("binding") or {}
    base_hash = tree_fingerprint(Path(state["repository"]), state["base_commit"])
    if (binding.get("version") != 1 or binding.get("mode") != "write"
            or not binding.get("validator_version")
            or binding.get("candidate_sha256") != fingerprint
            or binding.get("base_sha256") != base_hash):
        raise HarnessError("Validation report does not bind this exact candidate and expected base; run the compatible validator again.")
    verify_developer_during_operation(state)
    state["validation"] = {
        "workspace_sha256": fingerprint,
        "base_sha256": base_hash,
        "validator_version": binding["validator_version"],
        "report_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "result_file": str(result_path),
    }
    write_json(state_path, state)
    return {"ok": True, "workspace_sha256": fingerprint}


def commit_candidate(state_value: str | Path, message: str) -> dict[str, Any]:
    state_path, state = load_state(state_value)
    repo = Path(state["repository"])
    candidate = Path(state["candidate"])
    if state.get("new_commit"):
        raise HarnessError("Candidate is already committed.")
    verify_developer_during_operation(state)
    if not worktree_registered(repo, candidate):
        raise HarnessError("Candidate is not a registered Git worktree.")
    validation = state.get("validation") or {}
    if validation.get("workspace_sha256") != workspace_fingerprint(candidate):
        raise HarnessError("Candidate changed after conformance validation.")
    if commit_oid(candidate, "HEAD") != state["base_commit"]:
        raise HarnessError("Candidate HEAD moved from its expected base.")

    git(candidate, "-c", "core.autocrlf=false", "add", "-A", "--", ".aurae")
    staged = split_z(git(candidate, "diff", "--cached", "--name-only", "-z").stdout)
    if not staged:
        raise HarnessError("Candidate contains no metadata change.")
    require_metadata_paths(staged, "Staged change")
    require_metadata_paths(split_z(git(candidate, "ls-files", "-z").stdout), "Tracked tree")
    remaining = split_z(git(candidate, "diff", "--name-only", "-z").stdout)
    remaining += split_z(git(candidate, "ls-files", "--others", "--exclude-standard", "-z").stdout)
    if remaining:
        raise HarnessError("Candidate contains unstaged or untracked material.")

    tree = git(candidate, "write-tree").stdout.strip()
    if tree_fingerprint(repo, tree) != validation["workspace_sha256"]:
        raise HarnessError("Git transformed the validated bytes; preserve the candidate and use a filter-free metadata adapter.")
    new_commit = git(
        candidate,
        "commit-tree",
        tree,
        "-p",
        state["base_commit"],
        "-m",
        message,
    ).stdout.strip()
    git(candidate, "update-ref", "HEAD", new_commit, state["base_commit"])
    if git(candidate, "status", "--porcelain=v1", "-z").stdout:
        raise HarnessError("Candidate worktree is not clean after commit creation.")
    require_metadata_tree(repo, new_commit)
    state["new_commit"] = new_commit
    write_json(state_path, state)
    return {"ok": True, "commit": new_commit}


def compare_and_swap(repo: Path, ref: str, new_commit: str, expected: str | None) -> None:
    validate_aurae_ref(repo, ref)
    new_oid = commit_oid(repo, new_commit)
    require_metadata_tree(repo, new_oid)
    current = optional_ref(repo, ref)
    if current != expected:
        raise HarnessError("AURAE ref moved; reconciliation is required.")
    if expected is not None:
        ancestor = git(repo, "merge-base", "--is-ancestor", expected, new_oid, check=False)
        if ancestor.returncode != 0:
            raise HarnessError("Publication is not a descendant of the expected ref.")
    # update-ref does not protect a branch checked out in this or another worktree.
    # Refuse before mutation: detecting the changed HEAD during cleanup is too late.
    symbolic = git(repo, "symbolic-ref", "--quiet", ref, check=False)
    if symbolic.returncode == 0:
        raise HarnessError("Symbolic publication refs are unsupported; select a direct metadata ref.")
    if symbolic.returncode != 1:
        raise HarnessError("Cannot establish whether the publication ref is direct.")
    attached = git(repo, "worktree", "list", "--porcelain").stdout.splitlines()
    if ("branch " + ref).casefold() in {line.casefold() for line in attached}:
        raise HarnessError("Publication ref is checked out in a worktree; preserve it and resolve that use first.")
    git(repo, "update-ref", "--no-deref", ref, new_oid, expected or zero_oid(repo))
    if optional_ref(repo, ref) != new_oid:
        raise HarnessError("AURAE ref readback did not match the published commit.")


def publish_candidate(state_value: str | Path) -> dict[str, Any]:
    state_path, state = load_state(state_value)
    if not state.get("new_commit"):
        raise HarnessError("Candidate must be committed before publication.")
    if state.get("published"):
        raise HarnessError("Candidate is already published.")
    repo = Path(state["repository"])
    verify_developer_during_operation(state)
    if state["expected_ref"] is not None and state["base_commit"] != state["expected_ref"]:
        raise HarnessError("Publication cannot skip unvalidated intermediate history; use validated CAS.")
    validation = state.get("validation") or {}
    result_path = Path(validation.get("result_file", ""))
    if (not result_path.is_file() or hashlib.sha256(result_path.read_bytes()).hexdigest() != validation.get("report_sha256")
            or tree_fingerprint(repo, state["new_commit"]) != validation.get("workspace_sha256")
            or tree_fingerprint(repo, state["base_commit"]) != validation.get("base_sha256")):
        raise HarnessError("Committed candidate or validation proof changed; publication is blocked.")
    base = state["base_commit"]
    new_commit = state["new_commit"]
    if git(repo, "merge-base", "--is-ancestor", base, new_commit, check=False).returncode != 0:
        raise HarnessError("Candidate commit is not a descendant of its base.")
    verify_developer_during_operation(state)
    compare_and_swap(repo, state["publish_ref"], new_commit, state["expected_ref"])
    state["published"] = True
    write_json(state_path, state)
    return {"ok": True, "ref": state["publish_ref"], "commit": new_commit}


def cleanup_candidate(state_value: str | Path) -> dict[str, Any]:
    state_path, state = load_state(state_value)
    repo = Path(state["repository"])
    candidate = Path(state["candidate"])
    if state.get("cleaned"):
        raise HarnessError("Candidate is already cleaned.")
    if not worktree_registered(repo, candidate):
        raise HarnessError("Candidate worktree registration is missing; use recovery inspection.")
    if git(candidate, "status", "--porcelain=v1", "-z").stdout:
        raise HarnessError("Candidate worktree is not clean; preserve it for recovery.")
    git(repo, "worktree", "remove", str(candidate))
    if candidate.exists():
        raise HarnessError("Candidate path remains after Git worktree removal.")
    verify_snapshot(state["developer_snapshot"], snapshot(repo))
    state["cleaned"] = True
    write_json(state_path, state)
    return {"ok": True, "developer_state_unchanged": True, "state_file": str(state_path)}


def export_workspace(repo_value: str | Path, revision: str, destination_value: str | Path):
    repo = repo_root(repo_value)
    before = snapshot(repo)
    scratch = ensure_scratch(repo, repo / ".scratchpad")
    destination = Path(destination_value).resolve()
    require_inside(destination, scratch, "Export destination")
    if destination.exists():
        raise HarnessError("Export requires a new isolated destination.")
    oid = commit_oid(repo, revision)
    entries = metadata_entries(repo, oid)
    (destination / ".aurae").mkdir(parents=True)
    for relative, blob in entries:
        target = destination / relative
        require_inside(target, destination / ".aurae", "Exported artifact")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git_bytes(repo, "cat-file", "blob", blob))
    if workspace_fingerprint(destination) != tree_fingerprint(repo, oid):
        raise HarnessError("Export bytes differ from the selected Git tree; preserve for inspection.")
    verify_snapshot(before, snapshot(repo))
    return {"ok": True, "revision": oid, "workspace": str(destination / ".aurae")}


def read_artifact(repo_value: str | Path, revision: str, path: str) -> dict[str, Any]:
    repo = repo_root(repo_value)
    if not metadata_path(path) or Path(path).is_absolute() or ".." in Path(path).parts:
        raise HarnessError("Artifact path must remain below .aurae/.")
    oid = commit_oid(repo, revision)
    content = git(repo, "show", f"{oid}:{path.replace(chr(92), '/')}").stdout
    return {
        "ok": True,
        "artifact": content,
        "storage": {"backend": "git", "revision": oid, "path": path.replace("\\", "/")},
    }


def list_changes(repo_value: str | Path, left: str, right: str) -> dict[str, Any]:
    repo = repo_root(repo_value)
    left_oid = commit_oid(repo, left)
    right_oid = commit_oid(repo, right)
    output = git(
        repo,
        "diff",
        "--name-status",
        "--find-renames",
        left_oid,
        right_oid,
        "--",
        ".aurae",
    ).stdout.splitlines()
    return {"ok": True, "from": left_oid, "to": right_oid, "changes": output}


def cas_existing(repo_value: str | Path, ref: str, new: str, expected: str, validation_value: str) -> dict[str, Any]:
    repo = repo_root(repo_value)
    before = snapshot(repo)
    expected_oid = commit_oid(repo, expected)
    result_path = Path(validation_value).resolve()
    require_inside(result_path, repo / ".scratchpad", "Validation result")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    new_oid = commit_oid(repo, new)
    chain = git(repo, "rev-list", "--first-parent", "--reverse", f"{expected_oid}..{new_oid}").stdout.splitlines()
    reports = result.get("steps", [result])
    if not isinstance(reports, list) or not chain or len(chain) != len(reports):
        raise HarnessError("Fast-forward requires one validated report per first-parent transition.")
    cursor = expected_oid
    for commit, report in zip(chain, reports):
        parents = git(repo, "rev-list", "--parents", "-n", "1", commit).stdout.split()[1:]
        if parents != [cursor]:
            raise HarnessError("Reference CAS supports linear history only; preserve merged contributions for a reviewed integration adapter.")
        binding = report.get("binding") or {}
        if (report.get("valid") is not True or report.get("errors") not in (None, [])
                or binding.get("version") != 1 or binding.get("mode") != "write"
                or not binding.get("validator_version")
                or binding.get("candidate_sha256") != tree_fingerprint(repo, commit)
                or binding.get("base_sha256") != tree_fingerprint(repo, cursor)):
            raise HarnessError("Fast-forward requires validation bound to every exact parent and candidate tree.")
        cursor = commit
    verify_snapshot(before, snapshot(repo))
    compare_and_swap(repo, ref, new_oid, expected_oid)
    verify_snapshot(before, snapshot(repo))
    return {"ok": True, "ref": ref, "commit": commit_oid(repo, new)}


def self_test(scratch_value: str | Path) -> dict[str, Any]:
    outer = Path(scratch_value).resolve()
    if not outer.is_dir() or ".scratchpad" not in outer.parts:
        raise HarnessError("Self-test root must be an existing path below .scratchpad/.")
    test_root = outer / f"git-storage-self-test-{uuid.uuid4().hex[:12]}"
    repo = test_root / "repo"
    def test_report(state_path, candidate, result_path):
        # Storage-only stub: integrated qualification must use the real validator.
        _, state = load_state(state_path)
        write_json(result_path, {"valid": True, "errors": [], "warnings": [], "stats": {},
                   "binding": {"version": 1, "mode": "write", "validator_version": "storage-test-stub",
                               "candidate_sha256": workspace_fingerprint(candidate),
                               "base_sha256": tree_fingerprint(repo, state["base_commit"])}})
    try:
        repo.mkdir(parents=True)
        run(["git", "init", str(repo)])
        git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
        git(repo, "config", "user.name", "AURAE Harness Self-Test")
        git(repo, "config", "user.email", "aurae-harness@local.invalid")
        (repo / ".gitignore").write_text("/.scratchpad/\n", encoding="utf-8")
        (repo / "application.txt").write_text("developer state\n", encoding="utf-8")
        git(repo, "add", ".gitignore", "application.txt")
        git(repo, "commit", "-m", "self-test application baseline")
        scratch = repo / ".scratchpad" / "aurae-harness"
        scratch.mkdir(parents=True)
        application = repo / "application.txt"
        clean_content = application.read_bytes()
        application.write_text("dirty alpha\n", encoding="utf-8")
        dirty_before = snapshot(repo)
        application.write_text("dirty bravo\n", encoding="utf-8")
        try:
            verify_snapshot(dirty_before, snapshot(repo))
        except HarnessError:
            pass
        else:
            raise HarnessError("Changed content in an already dirty file was not detected.")
        application.write_bytes(clean_content)
        before = snapshot(repo)

        opened = create_candidate(
            repo,
            scratch,
            publish_ref="refs/heads/aurae/meta",
            base=None,
            expected_ref=None,
            bootstrap=True,
        )
        state_path = Path(opened["state_file"])
        candidate = Path(opened["candidate"])
        (candidate / ".aurae").mkdir()
        (candidate / ".aurae" / "aurae.yaml").write_text(
            "format: aurae-workspace\nformat_version: 1.0.0\nstorage_contract_version: 1.0.0\n",
            encoding="utf-8",
        )
        result_path = scratch / "valid-result.json"
        test_report(state_path, candidate, result_path)
        seal_candidate(state_path, result_path)
        first = commit_candidate(state_path, "AURAE self-test metadata bootstrap")["commit"]
        publish_candidate(state_path)
        cleanup_candidate(state_path)
        verify_snapshot(before, snapshot(repo))
        loaded = read_artifact(repo, first, ".aurae/aurae.yaml")
        if "format: aurae-workspace" not in loaded["artifact"]:
            raise HarnessError("Exact revision read failed.")

        opened = create_candidate(
            repo,
            scratch,
            publish_ref="refs/heads/aurae/meta",
            base=first,
            expected_ref=first,
            bootstrap=False,
        )
        state_path = Path(opened["state_file"])
        candidate = Path(opened["candidate"])
        (candidate / ".aurae" / "current.yaml").write_text(
            "active_auras: []\nplanned_auras: []\ncondition_alerts: []\n",
            encoding="utf-8",
        )
        try:
            seal_candidate(state_path, result_path)
        except HarnessError:
            pass
        else:
            raise HarnessError("An old validation report sealed a different candidate.")
        test_report(state_path, candidate, result_path)
        seal_candidate(state_path, result_path)
        current_path = candidate / ".aurae" / "current.yaml"
        validated_content = current_path.read_bytes()
        current_path.write_text("changed: after-validation\n", encoding="utf-8")
        try:
            commit_candidate(state_path, "must be rejected")
        except HarnessError:
            pass
        else:
            raise HarnessError("A changed candidate was committed after sealing.")
        current_path.write_bytes(validated_content)
        second = commit_candidate(state_path, "AURAE self-test metadata update")["commit"]
        conflict_detected = False
        try:
            compare_and_swap(repo, "refs/heads/aurae/meta", second, None)
        except HarnessError:
            conflict_detected = True
        if not conflict_detected:
            raise HarnessError("Compare-and-swap conflict was not detected.")
        publish_candidate(state_path)
        cleanup_candidate(state_path)
        verify_snapshot(before, snapshot(repo))
        changed = list_changes(repo, first, second)["changes"]
        if not any(".aurae/current.yaml" in item for item in changed):
            raise HarnessError("Metadata change listing failed.")

        # Both publication paths must preserve an already attached metadata tree.
        attached = scratch / "attached-metadata"
        require_inside(attached, scratch, "Self-test linked worktree")
        git(repo, "worktree", "add", str(attached), "aurae/meta")
        opened = create_candidate(repo, scratch, publish_ref="refs/heads/aurae/meta",
                                  base=second, expected_ref=second, bootstrap=False)
        state_path = Path(opened["state_file"])
        candidate = Path(opened["candidate"])
        (candidate / ".aurae" / "guard.yaml").write_text("guard: checked-out-ref\n", encoding="utf-8")
        test_report(state_path, candidate, result_path)
        seal_candidate(state_path, result_path)
        third = commit_candidate(state_path, "AURAE self-test attached-ref guard")["commit"]
        protected_before, attached_before = snapshot(repo), snapshot(attached)
        for label, operation in (
            ("publish", lambda: publish_candidate(state_path)),
            ("cas", lambda: cas_existing(repo, "refs/heads/aurae/meta", third, second, str(result_path))),
            ("current-worktree CAS", lambda: compare_and_swap(attached, "refs/heads/aurae/meta", third, second)),
            ("case-variant CAS", lambda: compare_and_swap(repo, "refs/heads/aurae/META", third,
                                                          optional_ref(repo, "refs/heads/aurae/META"))),
        ):
            try:
                operation()
            except HarnessError as exc:
                if "checked out in a worktree" not in str(exc):
                    raise HarnessError(f"{label} failed for the wrong reason: {exc}") from exc
            else:
                raise HarnessError(f"{label} changed a checked-out metadata ref.")
            if optional_ref(repo, "refs/heads/aurae/meta") != second:
                raise HarnessError("Rejected publication changed the metadata ref.")
            verify_snapshot(protected_before, snapshot(repo))
            verify_snapshot(attached_before, snapshot(attached))
            _, preserved = load_state(state_path)
            if preserved["published"] or preserved["new_commit"] != third or not candidate.is_dir():
                raise HarnessError("Rejected publication did not preserve its resumable candidate.")
        cleanup_candidate(state_path)
        # A symbolic alias must not bypass the checked-out branch protection.
        alias = "refs/heads/aurae/self-test-alias"
        git(repo, "symbolic-ref", alias, "refs/heads/aurae/meta")
        opened = create_candidate(repo, scratch, publish_ref=alias,
                                  base=second, expected_ref=second, bootstrap=False)
        alias_state = Path(opened["state_file"])
        alias_candidate = Path(opened["candidate"])
        (alias_candidate / ".aurae" / "alias-guard.yaml").write_text("guard: symbolic-ref\n", encoding="utf-8")
        alias_report = scratch / "alias-valid-result.json"
        test_report(alias_state, alias_candidate, alias_report)
        seal_candidate(alias_state, alias_report)
        alias_commit = commit_candidate(alias_state, "AURAE self-test symbolic-ref guard")["commit"]
        protected_before, attached_before = snapshot(repo), snapshot(attached)
        for label, operation in (
            ("alias publish", lambda: publish_candidate(alias_state)),
            ("alias cas", lambda: cas_existing(repo, alias, alias_commit, second, str(alias_report))),
            ("alias direct CAS", lambda: compare_and_swap(repo, alias, alias_commit, second)),
        ):
            try:
                operation()
            except HarnessError as exc:
                if "Symbolic publication refs" not in str(exc):
                    raise HarnessError(f"{label} failed for the wrong reason: {exc}") from exc
            else:
                raise HarnessError(f"{label} followed a symbolic publication ref.")
            if optional_ref(repo, "refs/heads/aurae/meta") != second or git(repo, "symbolic-ref", alias).stdout.strip() != "refs/heads/aurae/meta":
                raise HarnessError("Rejected symbolic publication changed its alias or target.")
            verify_snapshot(protected_before, snapshot(repo))
            verify_snapshot(attached_before, snapshot(attached))
            _, preserved = load_state(alias_state)
            if preserved["published"] or preserved["new_commit"] != alias_commit or not alias_candidate.is_dir():
                raise HarnessError("Rejected symbolic publication did not preserve its resumable candidate.")
        cleanup_candidate(alias_state)
        require_inside(attached, scratch, "Self-test linked worktree cleanup")
        git(repo, "worktree", "remove", str(attached))
        # A new preflight after the conflicting checkout is removed can publish
        # the same validated commit; the earlier failure did not discard it.
        cas_existing(repo, "refs/heads/aurae/meta", third, second, str(result_path))
        verify_snapshot(before, snapshot(repo))

        remove_test_tree(test_root, outer)
        return {
            "passed": True,
            "version": VERSION,
            "normal_checkout": True,
            "compare_and_swap": True,
            "developer_state_preserved": True,
            "dirty_content_change_detected": True,
            "stale_validation_rejected": True,
            "changed_candidate_rejected": True,
            "checked_out_ref_rejected_before_publication": True,
            "checked_out_publish_and_cas_preserved": True,
            "checked_out_case_variant_rejected": True,
            "symbolic_publish_and_cas_rejected": True,
            "publication_resumed_after_checkout_removal": True,
        }
    except Exception as exc:
        raise HarnessError(f"Self-test failed; preserved at {test_root}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AURAE Git Storage Harness reference.")
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("self-test")
    command.add_argument("--scratch-root", required=True)

    command = commands.add_parser("snapshot")
    command.add_argument("--repo", required=True)

    command = commands.add_parser("bootstrap")
    command.add_argument("--repo", required=True)
    command.add_argument("--scratch-root", required=True)
    command.add_argument("--publish-ref", default="refs/heads/aurae/meta")

    command = commands.add_parser("open")
    command.add_argument("--repo", required=True)
    command.add_argument("--scratch-root", required=True)
    command.add_argument("--base", required=True)
    command.add_argument("--publish-ref", required=True)
    command.add_argument("--expected-ref", required=True)

    command = commands.add_parser("seal")
    command.add_argument("--state", required=True)
    command.add_argument("--validation-result", required=True)

    command = commands.add_parser("commit")
    command.add_argument("--state", required=True)
    command.add_argument("--message", required=True)

    command = commands.add_parser("publish")
    command.add_argument("--state", required=True)

    command = commands.add_parser("cleanup")
    command.add_argument("--state", required=True)

    command = commands.add_parser("read")
    command.add_argument("--repo", required=True)
    command.add_argument("--revision", required=True)
    command.add_argument("--path", required=True)

    command = commands.add_parser("export")
    command.add_argument("--repo", required=True)
    command.add_argument("--revision", required=True)
    command.add_argument("--destination", required=True)

    command = commands.add_parser("changes")
    command.add_argument("--repo", required=True)
    command.add_argument("--left", required=True)
    command.add_argument("--right", required=True)

    command = commands.add_parser("cas")
    command.add_argument("--repo", required=True)
    command.add_argument("--ref", required=True)
    command.add_argument("--new", required=True)
    command.add_argument("--expected", required=True)
    command.add_argument("--validation-result", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "self-test":
            return emit(self_test(args.scratch_root))
        if args.command == "snapshot":
            return emit({"ok": True, "snapshot": snapshot(Path(args.repo))})
        if args.command == "bootstrap":
            return emit(create_candidate(
                args.repo,
                args.scratch_root,
                publish_ref=args.publish_ref,
                base=None,
                expected_ref=None,
                bootstrap=True,
            ))
        if args.command == "open":
            return emit(create_candidate(
                args.repo,
                args.scratch_root,
                publish_ref=args.publish_ref,
                base=args.base,
                expected_ref=args.expected_ref,
                bootstrap=False,
            ))
        if args.command == "seal":
            return emit(seal_candidate(args.state, args.validation_result))
        if args.command == "commit":
            return emit(commit_candidate(args.state, args.message))
        if args.command == "publish":
            return emit(publish_candidate(args.state))
        if args.command == "cleanup":
            return emit(cleanup_candidate(args.state))
        if args.command == "read":
            return emit(read_artifact(args.repo, args.revision, args.path))
        if args.command == "export":
            return emit(export_workspace(args.repo, args.revision, args.destination))
        if args.command == "changes":
            return emit(list_changes(args.repo, args.left, args.right))
        if args.command == "cas":
            return emit(cas_existing(args.repo, args.ref, args.new, args.expected, args.validation_result))
        raise HarnessError("Unsupported command.")
    except Exception as exc:
        return emit(
            {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}},
            2,
        )


if __name__ == "__main__":
    raise SystemExit(main())
# </AURAE_GIT_STORAGE_REFERENCE>
~~~~

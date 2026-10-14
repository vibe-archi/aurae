# Transparent metadata merge source

Read completely before materialization or requalification. Use [git-merge-harness.md](git-merge-harness.md) for the operational contract. This companion imports the separately inspected local Storage Harness and Workspace validator; distribute all three as Markdown, not executables.

~~~~python
# <AURAE_GIT_MERGE_REFERENCE version="1.0.1">
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

VERSION = "1.0.1"
MISSING = object()


class MergeError(RuntimeError):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or []


def choose(base, left, right):
    if left == right:
        return left
    if left == base:
        return right
    if right == base:
        return left
    raise MergeError("Both contributions changed this value.")


def portable_path(name):
    parts = name.split("/")
    reserved = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
    if parts[0] != ".aurae" or len(parts) < 2:
        raise MergeError("Only .aurae files can be merged.")
    if any(not p or p in {".", ".."} or p.casefold() == ".git" or p.endswith((".", " ")) or reserved.match(p)
           or any(ord(c) < 32 or c in '\\:<>"|?*' for c in p) for p in parts):
        raise MergeError("Metadata path is not safely portable: " + name)


class Engine:
    def __init__(self, storage, validator, repo, scratch):
        self.s, self.v = storage, validator
        if storage.VERSION != "1.0.1" or validator.VERSION != "1.1.1":
            raise MergeError("Use the qualified Storage 1.0.1 / Validator 1.1.1 pair or a reviewed adaptation.")
        if any(key.startswith("GIT_") and key != "GIT_PAGER" for key in os.environ):
            raise MergeError("Inherited GIT_* overrides require a clean invocation environment.")
        self.repo = storage.repo_root(repo)
        self.scratch = storage.ensure_scratch(self.repo, Path(scratch))
        if self.git("rev-parse", "--is-shallow-repository").strip() != b"false":
            raise MergeError("Complete the relevant history before merging a shallow repository.")
        configuration = self.git("config", "--list").decode("utf-8", "replace").splitlines()
        promisor_keys = {line.split("=", 1)[0] for line in configuration if re.match(r"remote\..*\.promisor=", line, re.I)}
        if any(line.lower().startswith("extensions.partialclone=") for line in configuration) or any(
                self.git("config", "--type=bool", "--get", key).strip() == b"true" for key in promisor_keys):
            raise MergeError("Partial/promisor repositories need a reviewed offline-capable adaptation.")
        if self.git("for-each-ref", "--format=%(refname)", "refs/replace").strip():
            raise MergeError("Replacement objects require an explicit history review before integration.")
        grafts = Path(self.git("rev-parse", "--git-path", "info/grafts").decode().strip())
        if not grafts.is_absolute():
            grafts = self.repo / grafts
        if grafts.exists() and grafts.stat().st_size:
            raise MergeError("Grafted history is not supported by this merge path.")
        self.operation = self.scratch / ("merge-" + uuid.uuid4().hex)
        self.operation.mkdir()
        self.trees, self.exports, self.documents, self.blobs = {}, {}, {}, {}
        self.reports = []

    def git(self, *args, data=None):
        env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1")
        env.pop("GIT_PAGER", None)
        result = subprocess.run(["git", "--no-pager", "-c", "core.hooksPath=" + os.devnull,
            "-c", "core.fsmonitor=false", "-c", "commit.gpgsign=false", "-C", str(self.repo), *args],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, shell=False)
        if result.returncode:
            raise MergeError("Git operation failed: " + result.stderr.decode("utf-8", "replace").strip())
        return result.stdout

    def oid(self, value):
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
            raise MergeError("Supply exact full commit identifiers, not mutable refs.")
        return self.git("rev-parse", "--verify", value + "^{commit}").decode().strip()

    def parents(self, revision):
        return self.git("rev-list", "--parents", "-n", "1", revision).decode().split()[1:]

    def base(self, left, right):
        bases = self.git("merge-base", "--all", left, right).decode().split()
        if len(bases) != 1:
            raise MergeError("A unique common base is required; preserve both histories for reviewed reconciliation.")
        return bases[0]

    def tree(self, revision):
        if revision not in self.trees:
            entries, folded = {}, {}
            for record in self.git("ls-tree", "-r", "-z", revision).split(b"\0"):
                if not record:
                    continue
                header, raw = record.split(b"\t", 1)
                mode, kind, oid = header.decode("ascii").split()
                path = raw.decode("utf-8")
                portable_path(path)
                if kind != "blob" or mode not in {"100644", "100755"}:
                    raise MergeError("Metadata must contain regular files, not symlinks or submodules.")
                # Include directories: a/B and A/c must not alias on Windows.
                for count in range(1, len(path.split("/")) + 1):
                    prefix = "/".join(path.split("/")[:count])
                    collision = folded.get(prefix.casefold())
                    if collision is not None and collision != prefix:
                        raise MergeError("Case-colliding metadata paths cannot be exported safely.")
                    folded[prefix.casefold()] = prefix
                entries[path] = (mode, oid)
            self.trees[revision] = entries
        return self.trees[revision]

    def blob(self, oid):
        if oid not in self.blobs:
            self.blobs[oid] = self.git("cat-file", "blob", oid)
        return self.blobs[oid]

    def unattached_ref(self, ref):
        symbolic = self.s.git(self.repo, "symbolic-ref", "--quiet", ref, check=False)
        if symbolic.returncode == 0:
            raise MergeError("Publication requires a direct ref, not a symbolic alias.")
        if symbolic.returncode != 1:
            raise MergeError("Unable to inspect publication ref type.")
        branches = self.git("worktree", "list", "--porcelain").decode("utf-8", "replace").splitlines()
        if ("branch " + ref).casefold() in {line.casefold() for line in branches}:
            raise MergeError("Publication ref is checked out in a worktree; preserve it and resolve that use first.")

    def hash_blob(self, content):
        return self.git("hash-object", "-w", "--stdin", data=content).decode().strip()

    def export(self, revision):
        if revision not in self.exports:
            root = self.operation / ("export-" + revision) / ".aurae"
            self.materialize(self.tree(revision), root)
            self.exports[revision] = root
        return self.exports[revision]

    def materialize(self, entries, root):
        self.s.require_inside(root, self.operation, "Merge export")
        if root.exists():
            raise MergeError("Merge export destination must be new.")
        root.mkdir(parents=True)
        for path, (_, oid) in sorted(entries.items()):
            portable_path(path)
            target = root.parent / path
            self.s.require_inside(target, root, "Metadata file")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.blob(oid))

    def docs(self, revision):
        if revision not in self.documents:
            self.documents[revision] = self.v.load_yaml_documents(self.export(revision))
        return self.documents[revision]

    def valid(self, result, label):
        if not result.get("valid") or result.get("errors"):
            raise MergeError("Workspace conformance failed: " + label, result.get("errors"))

    def current(self, revision):
        return next((d["data"] for d in self.docs(revision) if d["path"] == "current.yaml"), {})

    def attribution(self, base, tip, path):
        raw = self.git("log", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00", "--full-history",
                       base + ".." + tip, "--", ":(literal)" + path).decode("utf-8", "replace")
        fields, people = raw.strip().split("\0"), []
        for index in range(0, len(fields) - 4, 5):
            commit, name, email, committer, committer_email = fields[index:index + 5]
            people.append(dict(commit=commit.strip(), name=name, email=email,
                               committer=committer, committer_email=committer_email))
        return people

    def conflict(self, base, left, right, path, message):
        return {"path": path, "message": message,
                "left": {"commit": left, "contributors": self.attribution(base, left, path.split(":", 1)[0])},
                "right": {"commit": right, "contributors": self.attribution(base, right, path.split(":", 1)[0])}}

    def merge_current(self, base, left, right):
        values = [self.current(revision) for revision in (base, left, right)]
        if any(not isinstance(value, dict) for value in values):
            raise MergeError("Malformed current.yaml requires reconciliation.")
        if any(set(value) & {"active_aura", "phase", "specification_baseline", "handoff"} for value in values):
            raise MergeError("Legacy navigation fields require the existing minimal compatibility procedure.")
        result, conflicts = {}, []
        for key in sorted(set().union(*(value.keys() for value in values))):
            if key in {"active_auras", "planned_auras", "condition_alerts"}:
                continue
            a, b, c = [value.get(key, MISSING) for value in values]
            try:
                if key == "handoffs":
                    maps = [{entry["aura"]: entry for entry in value.get(key, [])} for value in values]
                    merged = {}
                    for aura in sorted(set().union(*(m.keys() for m in maps))):
                        merged[aura] = choose(*(m.get(aura, MISSING) for m in maps))
                    selected = [v for v in merged.values() if v is not MISSING]
                elif key == "updated_at" and b != c and b is not MISSING and c is not MISSING:
                    def timestamp(value):
                        parsed = value if isinstance(value, datetime.datetime) else datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                        if parsed.tzinfo is None:
                            raise MergeError("Navigation timestamps need an explicit timezone.")
                        return parsed
                    selected = max((b, c), key=timestamp)
                else:
                    # Planned order, product/intent pointers and unknown fields are not disposable.
                    selected = choose(a, b, c)
                if selected is not MISSING:
                    result[key] = selected
            except (MergeError, ValueError, TypeError):
                conflicts.append(self.conflict(base, left, right, ".aurae/current.yaml:" + key,
                    "Concurrent navigation/ordering/accepted-state changes require review."))
        return result, conflicts

    def merge_tree(self, left, right):
        base = self.base(left, right)
        maps = [self.tree(revision) for revision in (base, left, right)]
        merged, conflicts = {}, []
        current, current_conflicts = self.merge_current(base, left, right)
        conflicts.extend(current_conflicts)
        for path in sorted(set().union(*(m.keys() for m in maps))):
            if path == ".aurae/current.yaml":
                continue
            try:
                selected = choose(*(m.get(path, MISSING) for m in maps))
                if selected is not MISSING:
                    merged[path] = selected
            except MergeError:
                conflicts.append(self.conflict(base, left, right, path,
                    "Both contributions changed this artifact; no side was selected."))
        if conflicts:
            raise MergeError("Semantic reconciliation is needed before publication.", conflicts)
        # Derive only unordered indexes; preserve planned ordering and all other fields.
        yaml = __import__("yaml")
        index_root = self.operation / ("index-" + uuid.uuid4().hex) / ".aurae"
        self.materialize(merged, index_root)
        docs = self.v.load_yaml_documents(index_root)
        current["active_auras"] = sorted(d["data"]["id"] for d in docs
            if isinstance(d["data"], dict) and d["data"].get("kind") == "aura" and d["data"].get("status") == "active")
        current["condition_alerts"] = sorted(d["data"]["id"] for d in docs
            if isinstance(d["data"], dict) and d["data"].get("kind") == "assurance_condition" and d["data"].get("status") in {"open", "breached"})
        planned = {d["data"]["id"] for d in docs if isinstance(d["data"], dict)
                   and d["data"].get("kind") == "aura" and d["data"].get("status") == "planned"}
        orders = [self.current(revision).get("planned_auras", []) for revision in (base, left, right)]
        # A one-sided reorder wins over unchanged base order. On true concurrent edits,
        # retain both relative orders; reject cycles instead of silently reprioritizing work.
        if orders[1] == orders[0]:
            orders = [orders[2]]
        elif orders[2] == orders[0]:
            orders = [orders[1]]
        else:
            orders = orders[1:]
        predecessors = {ref: set() for ref in planned}
        for order in orders:
            kept = [ref for ref in order if ref in planned]
            for before, after in zip(kept, kept[1:]):
                predecessors[after].add(before)
        ordered = []
        while predecessors:
            ready = sorted(ref for ref, needs in predecessors.items() if not needs)
            if not ready:
                raise MergeError("Conflicting planned-cycle order requires review.", [self.conflict(base, left, right,
                    ".aurae/current.yaml:planned_auras", "The two planned orders cannot both be preserved.")])
            for ref in ready:
                ordered.append(ref)
                del predecessors[ref]
            for needs in predecessors.values():
                needs.difference_update(ready)
        current["planned_auras"] = ordered
        encoded = yaml.safe_dump(current, allow_unicode=True, sort_keys=True).encode("utf-8")
        modes = [m.get(".aurae/current.yaml", ("100644", None))[0] for m in maps]
        merged[".aurae/current.yaml"] = (choose(*modes), self.hash_blob(encoded))
        return base, merged

    def write_tree(self, entries):
        folders = {}
        for path, value in entries.items():
            node = folders
            for part in path.split("/")[:-1]:
                node = node.setdefault(part, {})
                if not isinstance(node, dict):
                    raise MergeError("File/directory collision in the merged tree.")
            leaf = path.split("/")[-1]
            if leaf in node:
                raise MergeError("Duplicate tree entry.")
            node[leaf] = value

        def create(node):
            records = []
            for name, item in sorted(node.items()):
                mode, kind, oid = ("040000", "tree", create(item)) if isinstance(item, dict) else (item[0], "blob", item[1])
                records.append((mode + " " + kind + " " + oid + "\t" + name).encode("utf-8") + b"\0")
            return self.git("mktree", "-z", data=b"".join(records)).decode().strip()
        tree = create(folders)
        # Reuse the complete portability and file-mode checks on the combined paths.
        if self.tree(tree) != entries:
            raise MergeError("Merged tree readback differs from the planned entries.")
        return tree

    def check_merge(self, left, right, actual=None):
        base, entries = self.merge_tree(left, right)
        tree = self.write_tree(entries)
        if actual and entries != self.tree(actual):
            raise MergeError("Historical merge contains changes outside deterministic reconciliation.")
        # This is a composition check, NOT a write proof or a new transition.
        result = self.v.validate_workspace(self.export(tree))
        self.valid(result, "composed state")
        docs = self.docs(tree)
        artifacts = {d["data"].get("id"): d["data"] for d in docs if isinstance(d["data"], dict)}
        lineage, cursor = set(), self.current(tree).get("project_baseline")
        while cursor is not None and cursor not in lineage:
            lineage.add(cursor)
            cursor = artifacts.get(cursor, {}).get("supersedes")
        for parent in (left, right):
            old_baseline = self.current(parent).get("project_baseline")
            if old_baseline and old_baseline not in lineage:
                raise MergeError("Parallel accepted product baselines require serialized integration and assurance.")
            for document in self.docs(parent):
                old = document["data"]
                if not isinstance(old, dict):
                    continue
                new = artifacts.get(old.get("id"))
                if old.get("kind") in {"product_baseline", "specification_baseline", "as_is_baseline"} and new != old:
                    raise MergeError("Merge would lose or rewrite an accepted baseline.")
                if old.get("kind") == "decision" and old.get("status") == "effective":
                    if {k: v for k, v in old.items() if k != "status"} != {k: v for k, v in (new or {}).items() if k != "status"}:
                        raise MergeError("Merge would lose or rewrite an effective decision.")
        return {"mode": "composition", "parents": [left, right], "base": base,
                "tree": tree, "candidate_sha256": self.v.workspace_fingerprint(self.export(tree)),
                "conformance": result}

    def check_history(self, left, right, anchor):
        self.valid(self.v.validate_workspace(self.export(anchor)), "common checkpoint")
        revisions = self.git("rev-list", "--topo-order", "--reverse", left, right, "^" + anchor).decode().split()
        for revision in revisions:
            parents = self.parents(revision)
            if len(parents) == 1:
                result = self.v.validate_workspace(self.export(revision), self.export(parents[0]))
                self.valid(result, revision)
                self.reports.append({"commit": revision, "parents": parents, "validation": result})
            elif len(parents) == 2:
                result = self.check_merge(*parents, actual=revision)
                self.reports.append({"commit": revision, "parents": parents, "validation": result})
            else:
                raise MergeError("Unconnected roots and octopus merges need a reviewed integration adapter.")

    def compute(self, left, right):
        left, right = self.oid(left), self.oid(right)
        anchor = self.base(left, right)
        if anchor == right:
            raise MergeError("These histories are not divergent; use the validated linear path or do nothing.")
        self.check_history(left, right, anchor)
        if anchor == left:
            if not any(len(report["parents"]) == 2 for report in self.reports):
                raise MergeError("Use the existing validated CAS path for a linear fast-forward.")
            result = self.v.validate_workspace(self.export(right))
            self.valid(result, "existing merged tip")
            tree = self.git("rev-parse", right + "^{tree}").decode().strip()
            return {"mode": "advance", "parents": [left, right], "base": left, "tree": tree,
                    "candidate_sha256": self.v.workspace_fingerprint(self.export(right)), "conformance": result}
        return self.check_merge(left, right)

    def plan(self, left, right, publish_ref):
        self.s.validate_aurae_ref(self.repo, publish_ref)
        if publish_ref == "refs/heads/aurae/skill":
            raise MergeError("Skill bundles are not project-memory merges.")
        self.unattached_ref(publish_ref)
        left, right = self.oid(left), self.oid(right)
        before = self.s.snapshot(self.repo)
        if self.s.optional_ref(self.repo, publish_ref) != left:
            raise MergeError("Publication ref moved; plan from its exact current value.")
        try:
            result = self.compute(left, right)
            candidate = self.operation / "candidate" / ".aurae"
            self.materialize(self.tree(result["tree"]), candidate)
            result.update(contract="aurae-git-merge-plan", version=VERSION, status="review_required",
                repository=str(self.repo), scratch_root=str(self.scratch), candidate=str(candidate),
                publish_ref=publish_ref, developer_snapshot=before, history=self.reports)
            path = self.operation / "plan.json"
            self.s.verify_snapshot(before, self.s.snapshot(self.repo))
            self.s.write_json(path, result)
            return {"status": "review_required", "mode": result["mode"], "plan": str(path), "candidate": str(candidate),
                    "parents": result["parents"], "candidate_sha256": result["candidate_sha256"]}
        except Exception as exc:
            self.s.verify_snapshot(before, self.s.snapshot(self.repo))
            self.s.write_json(self.operation / "blocked.json", {
                "status": "blocked", "parents": [left, right], "message": str(exc),
                "details": getattr(exc, "details", []), "history": self.reports})
            raise

    def publish(self, plan_path, review_path, message):
        plan_path, review_path = Path(plan_path).resolve(), Path(review_path).resolve()
        for path in (plan_path, review_path):
            self.s.require_inside(path, self.scratch, "Merge receipt")
        plan_bytes, review_bytes = plan_path.read_bytes(), review_path.read_bytes()
        plan, review = json.loads(plan_bytes), json.loads(review_bytes)
        if plan.get("contract") != "aurae-git-merge-plan" or plan.get("version") != VERSION:
            raise MergeError("Unsupported merge plan; preserve it and replan separately.")
        if Path(plan["repository"]).resolve() != self.repo or Path(plan["scratch_root"]).resolve() != self.scratch:
            raise MergeError("Merge plan belongs to a different repository or scratch root.")
        candidate = Path(plan["candidate"]).resolve()
        self.s.require_inside(candidate, plan_path.parent, "Planned candidate")
        self.s.verify_snapshot(plan["developer_snapshot"], self.s.snapshot(self.repo))
        ref = plan["publish_ref"]
        self.s.validate_aurae_ref(self.repo, ref)
        if ref == "refs/heads/aurae/skill":
            raise MergeError("Skill bundles are not project-memory merges.")
        self.unattached_ref(ref)
        left, right = plan["parents"]
        if self.s.optional_ref(self.repo, ref) != left:
            raise MergeError("Publication ref moved; preserve the old plan and reconcile again.")
        if review.get("result") != "pass" or not review.get("reviewer") or not review.get("summary"):
            raise MergeError("A completed semantic review is required; it is not a new product acceptance.")
        if review.get("parents") != [left, right] or review.get("candidate_sha256") != plan["candidate_sha256"]:
            raise MergeError("Semantic review does not cover these exact parents and candidate.")
        result = self.compute(left, right)  # Never trust supplied PASS reports or plan fields as a substitute.
        if any(result[key] != plan.get(key) for key in ("mode", "base", "tree", "candidate_sha256")):
            raise MergeError("Recomputed merge differs from the reviewed plan.")
        if self.v.workspace_fingerprint(candidate) != result["candidate_sha256"]:
            raise MergeError("Candidate changed after planning; no edited resolution can bypass source validation.")
        commit = right if result["mode"] == "advance" else self.git("commit-tree", result["tree"], "-p", left, "-p", right,
                          "-m", message).decode().strip()
        receipt = {"contract": "aurae-git-merge-publication", "version": VERSION,
                   "status": "prepared", "mode": result["mode"], "commit": commit,
                   "parents": self.parents(commit), "reviewed_tips": [left, right],
                   "tree": result["tree"], "publish_ref": ref,
                   "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
                   "review_sha256": hashlib.sha256(review_bytes).hexdigest()}
        receipt_path = self.operation / "publication.json"
        self.s.write_json(receipt_path, receipt)  # Recovery record precedes CAS.
        if (result["mode"] != "advance" and self.parents(commit) != [left, right]) or self.tree(commit) != self.tree(result["tree"]):
            raise MergeError("Merge commit readback failed.")
        self.s.verify_snapshot(plan["developer_snapshot"], self.s.snapshot(self.repo))
        if plan_path.read_bytes() != plan_bytes or review_path.read_bytes() != review_bytes:
            raise MergeError("Plan or semantic review changed during publication.")
        self.unattached_ref(ref)
        self.s.compare_and_swap(self.repo, ref, commit, left)
        receipt["status"] = "published_local"
        self.s.write_json(receipt_path, receipt)
        self.s.verify_snapshot(plan["developer_snapshot"], self.s.snapshot(self.repo))
        return dict(receipt, receipt=str(receipt_path))


def self_test(storage, validator, scratch_root):
    import copy
    import yaml
    from types import SimpleNamespace
    scratch_root = Path(scratch_root).resolve()
    if not scratch_root.is_dir() or ".scratchpad" not in scratch_root.parts:
        raise MergeError("Self-test needs an existing local .scratchpad directory.")
    fixture = scratch_root / ("merge-self-test-" + uuid.uuid4().hex)
    fixture.mkdir()
    repo = fixture / "repo"
    repo.mkdir()
    storage.git(repo, "init")
    storage.git(repo, "config", "user.name", "AURAE Fixture")
    storage.git(repo, "config", "user.email", "fixture@example.invalid")
    storage.git(repo, "config", "core.autocrlf", "false")
    (repo / ".gitignore").write_text("/.scratchpad/\n", encoding="utf-8")
    (repo / "app.txt").write_bytes(b"base\n")
    storage.git(repo, "add", ".gitignore", "app.txt")
    storage.git(repo, "commit", "-m", "Disposable product")
    (repo / "app.txt").write_bytes(b"staged\n")
    storage.git(repo, "add", "app.txt")
    (repo / "app.txt").write_bytes(b"unstaged\n")
    (repo / "local.txt").write_bytes(b"untracked\n")
    scratch = repo / ".scratchpad"
    scratch.mkdir()
    initial = storage.snapshot(repo)
    cases = []
    def check(name, value):
        if not value:
            raise MergeError("Self-test failed: " + name)
        cases.append({"case": name, "passed": True})
    def rejects(name, action):
        try:
            action()
        except (MergeError, storage.HarnessError):
            check(name, True)
            return
        raise MergeError("Self-test unexpectedly allowed: " + name)
    def engine():
        return Engine(storage, validator, repo, scratch)
    builder = engine()
    for version in ("1.0.0", "1.0.2"):
        rejects("unqualified_storage_" + version,
                lambda version=version: Engine(SimpleNamespace(VERSION=version), validator, repo, scratch))
    for version in ("1.1.0", "1.1.2"):
        rejects("unqualified_validator_" + version,
                lambda version=version: Engine(storage, SimpleNamespace(VERSION=version), repo, scratch))
    def commit(docs, parents, note=b"Exact bytes: \xc3\xa9\r\n", author=None):
        entries = {".aurae/" + d["path"]: ("100644", builder.hash_blob(yaml.safe_dump(d["data"], sort_keys=True).encode("utf-8"))) for d in docs}
        entries[".aurae/notes.md"] = ("100644", builder.hash_blob(note))
        tree = builder.write_tree(entries)
        args = []
        if author:
            args += ["-c", "user.name=" + author, "-c", "user.email=" + author.lower() + "@example.invalid"]
        args += ["commit-tree", tree]
        for parent in parents:
            args += ["-p", parent]
        return builder.git(*args, "-m", "Disposable metadata").decode().strip()
    def progress(docs, phase, phase_state, aura_index=2):
        docs = copy.deepcopy(docs)
        aura = docs[aura_index]["data"]
        aura["last_transition"]["from"] = copy.deepcopy(aura["last_transition"]["to"])
        aura.update(phase=phase, phase_state=phase_state)
        aura["last_transition"]["to"].update(phase=phase, phase_state=phase_state)
        return docs
    def set_ref(oid):
        builder.git("update-ref", "refs/heads/aurae/meta", oid)
    def prepare(left, right):
        set_ref(left)
        return engine().plan(left, right, "refs/heads/aurae/meta")
    def review(plan):
        path = Path(plan["plan"]).parent / "review.json"
        storage.write_json(path, {"result": "pass", "reviewer": "fixture reviewer",
            "summary": "Fixture contributions are independent; no new acceptance or code integration.",
            "parents": plan["parents"], "candidate_sha256": plan["candidate_sha256"]})
        return path
    docs = validator.fixture_documents()
    base = commit(docs, [])
    left_docs = progress(docs, "assess", "ready")
    left1 = commit(left_docs, [base], author="Jean")
    left_docs = progress(left_docs, "understand", "in_progress")
    left = commit(left_docs, [left1], author="Jean")
    right_docs = copy.deepcopy(docs)
    second = copy.deepcopy(docs[2])
    second["path"] = "auras/second.yaml"
    second["data"]["id"] = "AURA-second-change-12345678"
    second["data"]["last_transition"]["from"] = {"status": None, "phase": None, "phase_state": None}
    right_docs.append(second)
    right_docs[6]["data"]["active_auras"].append(second["data"]["id"])
    right_created = commit(right_docs, [base], author="Ahmed")
    right_docs = progress(right_docs, "assess", "ready", -1)
    right_ready = commit(right_docs, [right_created], author="Ahmed")
    right_docs = progress(right_docs, "understand", "in_progress", -1)
    right = commit(right_docs, [right_ready], author="Ahmed")
    plan = prepare(left, right)
    record = json.loads(Path(plan["plan"]).read_text(encoding="utf-8"))
    check("all_five_real_transitions_validated", len(record["history"]) == 5 and
          all(item["validation"]["binding"]["mode"] == "write" for item in record["history"]))
    check("imported_progressed_cycle_is_composition_not_creation", record["conformance"]["binding"]["mode"] == "snapshot" and
          next(d["data"] for d in engine().docs(record["tree"]) if d["path"] == "auras/second.yaml") == right_docs[-1]["data"])
    check("no_cumulative_transition", engine().docs(record["tree"])[0] is not None and
          next(d["data"] for d in engine().docs(record["tree"]) if d["path"] == "auras/active.yaml") == left_docs[2]["data"])
    review_path = review(plan)
    empty_review = review_path.parent / "missing-review.json"
    storage.write_json(empty_review, {})
    rejects("missing_review_blocks", lambda: engine().publish(plan["plan"], empty_review, "Invalid"))
    note = Path(plan["candidate"]) / "notes.md"
    exact = note.read_bytes()
    note.write_bytes(exact + b"edit")
    rejects("edited_candidate_blocks", lambda: engine().publish(plan["plan"], review_path, "Invalid"))
    note.write_bytes(exact)
    (repo / "app.txt").write_bytes(b"changed local work\n")
    rejects("developer_edit_blocks", lambda: engine().publish(plan["plan"], review_path, "Invalid"))
    (repo / "app.txt").write_bytes(b"unstaged\n")
    published = engine().publish(plan["plan"], review_path, "Merge independent cycles")
    merged = published["commit"]
    check("two_parents_preserved", builder.parents(merged) == [left, right])
    check("exact_blob_bytes_preserved", builder.blob(builder.tree(merged)[".aurae/notes.md"][1]) == exact)
    rejects("moved_ref_blocks_repeat", lambda: engine().publish(plan["plan"], review_path, "Invalid"))
    check("developer_state_unchanged", storage.snapshot(repo) == initial)
    right2_docs = copy.deepcopy(right_docs)
    right2_docs[-1]["data"]["objective"] = "Clarify the independent contribution"
    right2 = commit(right2_docs, [right], author="Ahmed")
    again = prepare(merged, right2)
    published_again = engine().publish(again["plan"], review(again), "Reconcile after an earlier merge")
    check("repeated_merge_and_shared_history", builder.parents(published_again["commit"]) == [merged, right2])
    catchup = prepare(base, published_again["commit"])
    caughtup = engine().publish(catchup["plan"], review(catchup), "Catch up existing merged history")
    check("catchup_preserves_existing_merge_commit", caughtup["mode"] == "advance" and caughtup["commit"] == published_again["commit"])
    # A source branch must genuinely create and progress the incoming cycle.
    forged = commit(right_docs, [base])
    rejects("incoming_cycle_cannot_fabricate_prior_phase", lambda: prepare(left, forged))
    # Promotion is a real source transition. The earlier conditional baseline
    # remains immutable historical truth when the resulting state is composed.
    historical_docs = validator.resolved_fixture()
    historical_base = commit(historical_docs, [])
    final_docs = validator.final_fixture()
    promoted = commit(final_docs, [historical_base])
    annotated = commit(historical_docs, [historical_base], note=b"Disjoint historical annotation\n")
    promotion_plan = prepare(annotated, promoted)
    promotion = engine().publish(promotion_plan["plan"], review(promotion_plan), "Merge accepted promotion")
    promoted_docs = {d["path"]: d["data"] for d in engine().docs(promotion["commit"])}
    check("accepted_promotion_preserves_conditional_history",
          promoted_docs["baselines/product.yaml"] == historical_docs[12]["data"] and
          promoted_docs[historical_docs[8]["path"]] == historical_docs[8]["data"] and
          promoted_docs["current.yaml"]["project_baseline"] == final_docs[-1]["data"]["id"] and
          builder.parents(promotion["commit"]) == [annotated, promoted])
    conflicting = commit(docs, [base], note=b"Jean's rule\n", author="Jean")
    conflicting2 = commit(docs, [base], note=b"Ahmed's rule\n", author="Ahmed")
    set_ref(conflicting)
    conflict_engine = engine()
    rejects("same_artifact_conflict_blocks", lambda: conflict_engine.plan(conflicting, conflicting2, "refs/heads/aurae/meta"))
    blocked = json.loads((conflict_engine.operation / "blocked.json").read_text(encoding="utf-8"))
    check("conflict_names_and_emails", blocked["details"][0]["left"]["contributors"][0]["name"] == "Jean" and
          blocked["details"][0]["right"]["contributors"][0]["email"] == "ahmed@example.invalid")
    broken_docs = copy.deepcopy(right_docs)
    broken_docs[6]["data"]["active_auras"] = []
    invalid = commit(broken_docs, [right])
    repaired = commit(right_docs, [invalid])
    rejects("invalid_intermediate_not_hidden_by_valid_tip", lambda: prepare(left, repaired))
    rejects("fast_forward_uses_existing_path", lambda: prepare(base, left))
    rejects("bundle_ref_excluded", lambda: engine().plan(left, right, "refs/heads/aurae/skill"))
    rejects("unsafe_metadata_path", lambda: portable_path(".aurae/../escape"))
    set_ref(left)
    alias = "refs/heads/aurae/alias"
    storage.git(repo, "update-ref", alias, left)
    alias_plan = engine().plan(left, right, alias)
    storage.git(repo, "symbolic-ref", alias, "refs/heads/aurae/meta")
    rejects("symbolic_ref_rejected_at_publication", lambda: engine().publish(alias_plan["plan"], review(alias_plan), "Invalid alias"))
    attached = scratch / "attached-metadata-worktree"
    storage.git(repo, "worktree", "add", str(attached), "aurae/meta")
    rejects("checked_out_ref_blocks", lambda: engine().plan(left, right, "refs/heads/aurae/meta"))
    rejects("checked_out_case_variant_blocks", lambda: engine().plan(left, right, "refs/heads/aurae/META"))
    attached_before = storage.snapshot(attached)
    rejects("symbolic_alias_to_checked_out_ref_blocks", lambda: engine().plan(left, right, alias))
    check("symbolic_alias_and_attached_target_preserved",
          storage.optional_ref(repo, "refs/heads/aurae/meta") == left and
          storage.git(repo, "symbolic-ref", "--quiet", alias).stdout.strip() == "refs/heads/aurae/meta" and
          storage.snapshot(attached) == attached_before)
    storage.require_inside(attached, scratch, "Self-test worktree")
    storage.git(repo, "worktree", "remove", str(attached))
    storage.git(repo, "config", "remote.fixture.promisor", "false")
    check("disabled_promisor_is_not_partial_clone", engine() is not None)
    storage.git(repo, "config", "remote.fixture.promisor", "true")
    rejects("active_promisor_blocks_implicit_fetch", lambda: engine())
    storage.git(repo, "config", "--unset", "remote.fixture.promisor")
    check("final_developer_state_preserved", storage.snapshot(repo) == initial)
    result = {"passed": True, "version": VERSION, "cases": cases, "fixture": str(fixture)}
    storage.write_json(fixture / "result.json", result)
    return result  # Keep this bounded fixture and report local for qualification/recovery inspection.


def load_helper(path, name):
    source = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="Reviewed, isolated, two-parent AURAE metadata merges")
    parser.add_argument("--storage-source", required=True)
    parser.add_argument("--validator-source", required=True)
    parser.add_argument("--repo")
    parser.add_argument("--scratch-root", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("self-test")
    plan = commands.add_parser("plan")
    plan.add_argument("--ours", required=True)
    plan.add_argument("--theirs", required=True)
    plan.add_argument("--publish-ref", required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("--plan", required=True)
    publish.add_argument("--review", required=True)
    publish.add_argument("--message", required=True)
    args = parser.parse_args()
    engine = None
    try:
        storage = load_helper(args.storage_source, "aurae_storage")
        validator = load_helper(args.validator_source, "aurae_validator")
        if args.command == "self-test":
            print(json.dumps(self_test(storage, validator, args.scratch_root), ensure_ascii=False, indent=2))
            return 0
        if not args.repo:
            raise MergeError("A repository is required for plan or publish.")
        engine = Engine(storage, validator, args.repo, args.scratch_root)
        result = engine.plan(args.ours, args.theirs, args.publish_ref) if args.command == "plan" else engine.publish(args.plan, args.review, args.message)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "message": str(exc), "details": getattr(exc, "details", []),
                          "operation": str(engine.operation) if engine else None}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
# </AURAE_GIT_MERGE_REFERENCE>
~~~~

"""Exercise shared-cycle structure without simulating network visibility or permissions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/aurae/references/workspace-validator-source.md"
LOGIN = "AURA-sso-login-12345678"
SESSION = "AURA-session-fix-87654321"


class SharedCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        markdown = SOURCE.read_text(encoding="utf-8")
        source = markdown.split("```python\n", 1)[1].split("\n```", 1)[0]
        cls.validator = {"__name__": "aurae_shared_cycle_validation"}
        exec(compile(source, str(SOURCE), "exec"), cls.validator)

    @staticmethod
    def current(docs):
        return next(item["data"] for item in docs if item["path"] == "current.yaml")

    @staticmethod
    def cycle(docs, aura_id):
        return next(item["data"] for item in docs if item["data"].get("id") == aura_id)

    def assert_valid(self, docs, previous):
        result = self.validator["validate_documents"](docs, previous)
        self.assertTrue(result["valid"], result["errors"])
        return result

    def starting_memory(self):
        docs = [item for item in self.validator["fixture_documents"]()
                if item["data"].get("kind") != "aura"]
        self.current(docs)["active_auras"] = []
        self.assert_valid(docs, [])
        return docs

    def open_cycle(self, previous, aura_id):
        docs = copy.deepcopy(previous)
        item = next(item for item in self.validator["fixture_documents"]()
                    if item["data"].get("kind") == "aura")
        item["path"] = f"auras/{aura_id}/aura.yaml"
        item["data"].update(id=aura_id, based_on_baseline=self.current(docs)["project_baseline"])
        docs.append(item)
        self.current(docs)["active_auras"].append(aura_id)
        self.assert_valid(docs, previous)
        return docs

    def shared_memory(self):
        first = self.open_cycle(self.starting_memory(), LOGIN)
        return self.open_cycle(first, SESSION)

    def advance(self, previous, aura_id, phase, phase_state):
        docs = copy.deepcopy(previous)
        aura = self.cycle(docs, aura_id)
        origin = {key: aura[key] for key in ("status", "phase", "phase_state")}
        aura.update(phase=phase, phase_state=phase_state)
        aura["last_transition"].update(
            {"from": origin, "to": {"status": "active", "phase": phase, "phase_state": phase_state},
             "reason": "Contribution phase checkpoint", "decision": None})
        self.assert_valid(docs, previous)
        return docs

    def test_sequential_registration_keeps_both_cycles_and_common_baseline(self):
        start = self.starting_memory()
        first = self.open_cycle(start, LOGIN)
        both = self.open_cycle(first, SESSION)
        self.assertEqual(self.current(both)["active_auras"], [LOGIN, SESSION])
        self.assertEqual(self.cycle(first, LOGIN), self.cycle(both, LOGIN))
        self.assertEqual(self.current(start)["project_baseline"], self.current(both)["project_baseline"])
        self.assertEqual([item for item in start if item["path"] != "current.yaml"],
                         [item for item in both if item["path"] != "current.yaml"
                          and item["data"].get("kind") != "aura"])
        for aura_id in (LOGIN, SESSION):
            aura = self.cycle(both, aura_id)
            self.assertEqual((aura["status"], aura["phase"], aura["phase_state"]),
                             ("active", "assess", "in_progress"))
            self.assertEqual(aura["based_on_baseline"], self.current(both)["project_baseline"])
            self.assertIsNone(aura["specification_baseline"])
            self.assertEqual(aura["implementation"]["mode"], "none")
            self.assertTrue(all(value is None for key, value in aura["implementation"].items()
                                if key != "mode"))

    def test_one_cycle_progress_does_not_advance_the_other(self):
        previous = self.shared_memory()
        ready = self.advance(previous, LOGIN, "assess", "ready")
        current = self.advance(ready, LOGIN, "understand", "in_progress")
        self.assertEqual(self.cycle(previous, SESSION), self.cycle(current, SESSION))
        self.assertEqual(self.current(previous), self.current(current))
        before = {item["path"]: item["data"] for item in previous
                  if item["data"].get("id") != LOGIN}
        after = {item["path"]: item["data"] for item in current
                 if item["data"].get("id") != LOGIN}
        self.assertEqual(before, after)

    def test_clean_closure_removes_only_its_cycle_from_active_index(self):
        previous = self.shared_memory()
        docs = copy.deepcopy(previous)
        aura = self.cycle(docs, LOGIN)
        decision = copy.deepcopy(next(item for item in docs if item["data"].get("kind") == "decision"))
        decision["path"] = "decisions/stop-sso.yaml"
        decision["data"].update(id="DEC-stop-sso-11223344", decision_type="clean_closure",
                                subject=[LOGIN], outcome="close")
        docs.append(decision)
        origin = {key: aura[key] for key in ("status", "phase", "phase_state")}
        aura.update(status="closed", phase=None, phase_state=None,
                    closure={"decision": decision["data"]["id"], "reason": "User cancelled before implementation",
                             "stable_baseline": self.current(docs)["project_baseline"]})
        aura["last_transition"].update(
            {"from": origin, "to": {"status": "closed", "phase": None, "phase_state": None},
             "decision": decision["data"]["id"], "reason": "User cancelled before implementation"})
        self.current(docs)["active_auras"].remove(LOGIN)
        self.assert_valid(docs, previous)
        self.assertEqual(self.current(docs)["active_auras"], [SESSION])
        self.assertEqual(self.cycle(docs, SESSION), self.cycle(previous, SESSION))
        self.assertEqual(aura["implementation"]["mode"], "none")
        self.assertIsNone(aura["specification_baseline"])
        self.assertEqual(self.current(docs)["project_baseline"], self.current(previous)["project_baseline"])
        self.assertEqual([item for item in docs if item["data"].get("kind") == "as_is_baseline"],
                         [item for item in previous if item["data"].get("kind") == "as_is_baseline"])
        self.assertFalse(any(item["data"].get("kind") == "product_baseline" for item in docs))
        missing_authority = copy.deepcopy(docs)
        self.cycle(missing_authority, LOGIN)["closure"]["decision"] = None
        result = self.validator["validate_documents"](missing_authority, previous)
        self.assertFalse(result["valid"])
        self.assertIn("E_DECISION_REFERENCE", {item["code"] for item in result["errors"]})

    def test_lost_active_index_entry_is_rejected(self):
        previous = self.shared_memory()
        for lost_id in (LOGIN, SESSION):
            with self.subTest(lost_id=lost_id):
                docs = copy.deepcopy(previous)
                self.current(docs)["active_auras"].remove(lost_id)
                result = self.validator["validate_documents"](docs, previous)
                self.assertFalse(result["valid"])
                self.assertIn("E_ACTIVE_AURA_INDEX", {item["code"] for item in result["errors"]})

    def test_coordination_notes_bind_bytes_without_creating_lifecycle_state(self):
        docs = self.shared_memory()
        scratch = ROOT / ".scratchpad"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="shared-cycle-notes-", dir=scratch) as directory:
            previous = Path(directory) / "previous" / ".aurae"
            candidate = Path(directory) / "candidate" / ".aurae"
            for root in (previous, candidate):
                root.mkdir(parents=True)
                for item in docs:
                    path = root / item["path"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(item["data"]), encoding="utf-8")
            validate = self.validator["validate_workspace"]
            original = validate(candidate, previous_root=previous)
            self.assertTrue(original["valid"], original["errors"])
            for relative in ("coordination.md", f"auras/{LOGIN}/coordination.md"):
                with self.subTest(path=relative):
                    note = candidate / relative
                    note.write_text("# Coordination\nShared memory: upstream aurae/meta\nVisibility: last fetch only\n",
                                    encoding="utf-8")
                    first = validate(candidate, previous_root=previous)
                    self.assertTrue(first["valid"], first["errors"])
                    note.write_text("# Coordination\nShared memory: upstream aurae/meta\nVisibility: offline; local only\n",
                                    encoding="utf-8")
                    second = validate(candidate, previous_root=previous)
                    self.assertTrue(second["valid"], second["errors"])
                    for result in (first, second):
                        self.assertEqual(original["stats"], result["stats"])
                        self.assertEqual(original["binding"]["base_sha256"], result["binding"]["base_sha256"])
                        self.assertEqual(result["binding"]["mode"], "write")
                    self.assertNotEqual(original["binding"]["candidate_sha256"], first["binding"]["candidate_sha256"])
                    self.assertNotEqual(first["binding"]["candidate_sha256"], second["binding"]["candidate_sha256"])
                    # Markdown is bound as content, not parsed as a new gate or phase.
                    self.assertEqual(self.validator["load_yaml_documents"](candidate),
                                     self.validator["load_yaml_documents"](previous))
                    original = second


if __name__ == "__main__":
    unittest.main()

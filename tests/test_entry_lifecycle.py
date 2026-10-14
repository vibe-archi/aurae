"""Exercise entry checkpoints and starting-state registration without invented cycles."""
import copy
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/aurae/references/workspace-validator-source.md"


class EntryLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        markdown = SOURCE.read_text(encoding="utf-8")
        source = markdown.split("```python\n", 1)[1].split("\n```", 1)[0]
        cls.validator = {"__name__": "aurae_entry_validation"}
        exec(compile(source, str(SOURCE), "exec"), cls.validator)

    def partial_entry(self):
        docs = [copy.deepcopy(item) for item in self.validator["fixture_documents"]()
                if item["data"].get("kind") not in {"aura", "adoption", "as_is_baseline", "decision"}]
        current = next(item["data"] for item in docs if item["path"] == "current.yaml")
        current.update(active_auras=[], planned_auras=[], handoffs=[], condition_alerts=[],
                       adoption_record=None, project_baseline=None, project_intent_baseline=None)
        docs.append({"path": "aurae.yaml", "data": {"format": "aurae-workspace",
                     "format_version": "1.0.0", "storage_contract_version": "1.0.0"}})
        return docs

    def assert_valid(self, docs, previous):
        result = self.validator["validate_documents"](docs, previous)
        self.assertTrue(result["valid"], result["errors"])
        return result

    def test_partial_entry_needs_no_cycle_or_acceptance(self):
        docs = self.partial_entry()
        before = copy.deepcopy(docs)
        self.assert_valid(docs, [])
        self.assert_valid(docs, before)
        self.assertEqual(docs, before)
        self.assertFalse(any(item["data"].get("kind") in {
            "aura", "decision", "product_baseline", "as_is_baseline", "project_intent_baseline"
        } for item in docs))

    def test_incomplete_adoption_can_pause_without_baseline(self):
        previous = self.partial_entry()
        docs = copy.deepcopy(previous)
        adoption = copy.deepcopy(self.validator["fixture_documents"]()[4])
        adoption["data"].update(status="incomplete", as_is_baseline=None,
                                acceptance_decision=None, blockers=["Starting code is not yet pinned"])
        docs.append(adoption)
        current = next(item["data"] for item in docs if item["path"] == "current.yaml")
        current["adoption_record"] = adoption["data"]["id"]
        self.assert_valid(docs, previous)
        self.assertIsNone(current["project_baseline"])
        self.assertEqual(current["handoffs"], [])

    def test_bootstrap_uses_real_starting_state_then_first_assess(self):
        previous = self.partial_entry()
        docs = self.validator["fixture_documents"]()
        intent_id = "BL-product-intent-12345678"
        intent_decision = copy.deepcopy(docs[3])
        intent_decision["path"] = "decisions/intent.yaml"
        intent_decision["data"].update(id="DEC-product-intent-12345678",
                                       decision_type="project_intent", subject=[intent_id])
        docs.append(intent_decision)
        docs.append({"path": "specifications/project-intent.yaml", "data": {
            "id": intent_id, "kind": "project_intent_baseline", "status": "accepted",
            "acceptance_decision": intent_decision["data"]["id"],
        }})
        docs[6]["data"]["project_intent_baseline"] = intent_id
        docs[2]["data"]["project_intent_baseline"] = intent_id
        start = [copy.deepcopy(item) for item in docs if item["data"].get("kind") != "aura"]
        current = next(item["data"] for item in start if item["path"] == "current.yaml")
        current["active_auras"] = []
        self.assert_valid(start, previous)
        self.assertFalse(any(item["data"].get("kind") == "product_baseline" for item in start))
        self.assert_valid(docs, start)
        aura = docs[2]["data"]
        self.assertEqual(aura["based_on_baseline"], current["project_baseline"])
        self.assertEqual(aura["project_intent_baseline"], intent_id)
        self.assertNotEqual(aura["project_intent_baseline"], aura["based_on_baseline"])
        self.assertEqual((aura["status"], aura["phase"], aura["phase_state"]),
                         ("active", "assess", "in_progress"))
        for index in (4, 5):
            docs[index]["data"]["repositories"][0]["code_commit"] = "not-a-commit"
        result = self.validator["validate_documents"](docs, previous)
        self.assertIn("E_ADOPTION_PINS", {item["code"] for item in result["errors"]})

    def test_entry_note_bytes_are_bound_without_cycle_index(self):
        docs = self.partial_entry()
        scratch = ROOT / ".scratchpad"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="entry-checkpoint-", dir=scratch) as directory:
            exported = Path(directory) / ".aurae"
            exported.mkdir()
            for item in docs:
                path = exported / item["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(item["data"]), encoding="utf-8")
            note = exported / "resume.md"
            note.write_text("# Bootstrap interview\nScope: project\nQ4 / 9: awaiting an answer\n",
                            encoding="utf-8")
            validate = self.validator["validate_workspace"]
            first = validate(exported, new_workspace=True)
            self.assertTrue(first["valid"], first["errors"])
            note.write_text("# Bootstrap interview\nScope: project\nQ4 / 9: answered; Q4.1 remains open\n",
                            encoding="utf-8")
            second = validate(exported, new_workspace=True)
            self.assertTrue(second["valid"], second["errors"])
            self.assertNotEqual(first["binding"]["candidate_sha256"],
                                second["binding"]["candidate_sha256"])
            self.assertEqual(first["stats"], second["stats"])

    def test_clean_closure_before_realize_reuses_starting_baseline(self):
        previous = self.validator["fixture_documents"]()
        self.assert_valid(previous, [])
        docs = copy.deepcopy(previous)
        aura = docs[2]["data"]
        decision = copy.deepcopy(docs[3])
        decision["path"] = "decisions/stop-contribution.yaml"
        decision["data"].update(id="DEC-stop-contribution-12345678", decision_type="clean_closure",
                                subject=[aura["id"]], outcome="close")
        docs.append(decision)
        aura["last_transition"]["from"] = copy.deepcopy(aura["last_transition"]["to"])
        aura.update(status="closed", phase=None, phase_state=None,
                    closure={"decision": decision["data"]["id"], "reason": "User cancelled before implementation",
                             "stable_baseline": docs[5]["data"]["id"]})
        aura["last_transition"].update(to={"status": "closed", "phase": None, "phase_state": None},
                                       decision=decision["data"]["id"], reason="User cancelled before implementation")
        docs[6]["data"]["active_auras"] = []
        self.assert_valid(docs, previous)
        self.assertEqual(aura["implementation"]["mode"], "none")
        self.assertIsNone(aura["implementation"]["result_code_commit"])
        self.assertIsNone(aura["specification_baseline"])
        self.assertEqual(docs[6]["data"]["project_baseline"], previous[6]["data"]["project_baseline"])
        self.assertEqual(docs[5], previous[5])
        self.assertFalse(any(item["data"].get("kind") == "product_baseline" for item in docs))
        decision["data"]["outcome"] = "accept"
        result = self.validator["validate_documents"](docs, previous)
        self.assertIn("E_DECISION_OUTCOME", {item["code"] for item in result["errors"]})

    def advance_cycle(self, previous, aura_id, phase, phase_state, additions=(), implementation=None):
        """Build and validate one real parent/child state, never a cumulative transition."""
        docs = copy.deepcopy(previous)
        docs.extend(copy.deepcopy(additions))
        aura = next(item["data"] for item in docs if item["data"].get("id") == aura_id)
        before = {key: aura[key] for key in ("status", "phase", "phase_state")}
        aura.update(phase=phase, phase_state=phase_state)
        if implementation is not None:
            aura["implementation"] = implementation
        if phase == "understand" and phase_state == "ready":
            aura["specification_baseline"] = next(item["data"]["id"] for item in additions
                if item["data"].get("kind") == "specification_baseline")
        aura["last_transition"].update(
            {"from": before, "to": {"status": "active", "phase": phase, "phase_state": phase_state},
             "reason": "Recorded phase boundary", "decision": None})
        self.assert_valid(docs, previous)
        return docs

    def complete_cycle(self, previous, aura_id, specification_items, decision, baseline):
        """Walk all gates from the existing Assess through acceptance, preserving history."""
        docs = self.advance_cycle(previous, aura_id, "assess", "ready")
        docs = self.advance_cycle(docs, aura_id, "understand", "in_progress")
        docs = self.advance_cycle(docs, aura_id, "understand", "ready", additions=specification_items)
        pin = baseline["data"]["repositories"][0]
        current_baseline_id = next(item["data"] for item in docs if item["path"] == "current.yaml")["project_baseline"]
        starting = next(item["data"] for item in docs if item["data"].get("id") == current_baseline_id)
        implementation = {"mode": "direct", "repository": pin["repository"],
                          "base_code_commit": starting["repositories"][0]["code_commit"],
                          "branch_hint": None, "result_code_commit": None}
        docs = self.advance_cycle(docs, aura_id, "realize", "in_progress", implementation=implementation)
        implementation = dict(implementation, result_code_commit=pin["code_commit"])
        docs = self.advance_cycle(docs, aura_id, "realize", "ready", implementation=implementation)
        docs = self.advance_cycle(docs, aura_id, "assure", "in_progress")
        docs = self.advance_cycle(docs, aura_id, "assure", "ready")
        previous = docs
        docs = copy.deepcopy(previous)
        docs.extend(copy.deepcopy([decision, baseline]))
        aura = next(item["data"] for item in docs if item["data"].get("id") == aura_id)
        aura["last_transition"]["from"] = copy.deepcopy(aura["last_transition"]["to"])
        aura.update(status="assured", phase=None, phase_state=None,
                    closure={"decision": decision["data"]["id"], "reason": "Accepted tested candidate",
                             "stable_baseline": baseline["data"]["id"]})
        aura["last_transition"].update(to={"status": "assured", "phase": None, "phase_state": None},
                                       decision=decision["data"]["id"], reason="Accepted tested candidate")
        current = next(item["data"] for item in docs if item["path"] == "current.yaml")
        current.update(active_auras=[], project_baseline=baseline["data"]["id"])
        self.assert_valid(docs, previous)
        return docs

    def test_recovery_appends_baseline_instead_of_rewinding_current(self):
        initial = self.validator["fixture_documents"]()
        self.assert_valid(initial, [])
        template = self.validator["assurance_fixture"]()
        accepted = self.complete_cycle(initial, initial[2]["data"]["id"],
                                       [template[index] for index in (7, 9, 10, 11)],
                                       template[8], template[12])
        rewound = copy.deepcopy(accepted)
        next(item["data"] for item in rewound if item["path"] == "current.yaml")["project_baseline"] = initial[5]["data"]["id"]
        result = self.validator["validate_documents"](rewound, accepted)
        self.assertIn("E_PRODUCT_LINEAGE", {item["code"] for item in result["errors"]})

        recovery_id = "AURA-recover-combination-12345678"
        docs = copy.deepcopy(accepted)
        recovery = copy.deepcopy(initial[2])
        recovery["path"] = "auras/recovery/aura.yaml"
        recovery["data"].update(id=recovery_id, based_on_baseline=template[12]["data"]["id"])
        docs.append(recovery)
        next(item["data"] for item in docs if item["path"] == "current.yaml")["active_auras"] = [recovery_id]
        self.assert_valid(docs, accepted)

        # Distinct restored-state evidence and decisions; the desired code pin genuinely
        # comes from the earlier baseline fixture, not from a backward metadata pointer.
        replacements = {
            initial[2]["data"]["id"]: recovery_id,
            template[7]["data"]["id"]: "DEC-recovery-spec-12345678",
            template[8]["data"]["id"]: "DEC-recovery-accepted-12345678",
            template[9]["data"]["id"]: "BEH-recovery-scope-12345678",
            template[10]["data"]["id"]: "EV-recovery-run-12345678",
            template[11]["data"]["id"]: "BL-recovery-spec-12345678",
            template[12]["data"]["id"]: "BL-restored-combination-12345678",
        }

        def renamed(value):
            if isinstance(value, str):
                return replacements.get(value, value)
            if isinstance(value, list):
                return [renamed(item) for item in value]
            if isinstance(value, dict):
                return {key: renamed(item) for key, item in value.items()}
            return value

        items = [renamed(template[index]) for index in (7, 8, 9, 10, 11, 12)]
        for item in items:
            item["path"] = "recovery/" + item["path"]
        baseline = items[5]
        baseline["data"].update(supersedes=template[12]["data"]["id"],
                                repositories=copy.deepcopy(initial[5]["data"]["repositories"]))
        restored = self.complete_cycle(docs, recovery_id, [items[index] for index in (0, 2, 3, 4)],
                                       items[1], baseline)
        old_artifacts = {item["data"].get("id"): item["data"] for item in accepted if item["data"].get("id")}
        new_artifacts = {item["data"].get("id"): item["data"] for item in restored if item["data"].get("id")}
        for artifact_id, content in old_artifacts.items():
            self.assertEqual(content, new_artifacts[artifact_id])
        current = next(item["data"] for item in restored if item["path"] == "current.yaml")
        self.assertEqual(current["project_baseline"], baseline["data"]["id"])
        self.assertEqual(baseline["data"]["supersedes"], template[12]["data"]["id"])
        self.assertEqual(baseline["data"]["repositories"], initial[5]["data"]["repositories"])


if __name__ == "__main__":
    unittest.main()

# Transparent reference source

Read completely before first local materialization or adaptation, or when this source changes. The operational contract and invocation are in [workspace-conformance.md](workspace-conformance.md). Distribute this source only as Markdown; materialize runnable files solely inside ignored `.scratchpad/`.

```python
# <AURAE_REFERENCE_VALIDATOR version="1.1.0">
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PREFIXES = (
    "PRJ", "REP", "ADOPT", "AURA", "REQ", "BEH", "IFACE", "INV",
    "ADR", "DEC", "COND", "RISK", "ORACLE", "CAP", "EV", "BL", "WS",
)
PREFIX = "(?:" + "|".join(PREFIXES) + ")"
ID_RE = re.compile(rf"^{PREFIX}-[A-Za-z0-9][A-Za-z0-9_-]*$")
SEMANTIC_ID_RE = re.compile(rf"^{PREFIX}-(?:[a-z0-9]+-)+[0-9a-f]{{8}}$")
ABSOLUTE_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|var|tmp)/)")
SECRET_KEYS = {
    "password", "passwd", "secret", "api_key", "apikey", "private_key",
    "access_token", "refresh_token", "session_cookie", "credential",
}
RISK_RANK = {"standard": 0, "medium": 1, "high": 2, "critical": 3}
PHASES = ("assess", "understand", "realize", "assure")
TERMINAL = {"assured", "rejected", "closed"}
VERSION = "1.1.0"
INDEPENDENCE = {"not_applicable": -1, "self_check": 0, "separate_review": 1, "independent_verifier": 2}


def issue(target: list[dict[str, str]], code: str, path: str, message: str) -> None:
    target.append({"code": code, "path": path, "message": message})


def walk(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            yield from walk(value[key], f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f"{path}[{index}]")


def normalize_documents(documents: list[dict[str, Any]]):
    return [
        {"path": str(item["path"]).replace("\\", "/").lstrip("./"), "data": item["data"]}
        for item in documents
    ]


def validate_documents(documents: list[dict[str, Any]], previous_documents=None) -> dict[str, Any]:
    documents = normalize_documents(documents)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    artifacts: dict[str, tuple[str, dict[str, Any]]] = {}
    by_path = {item["path"]: item["data"] for item in documents}
    previous = {
        item["data"]["id"]: item["data"]
        for item in normalize_documents(previous_documents or [])
        if isinstance(item.get("data"), dict) and isinstance(item["data"].get("id"), str)
    }

    def retained(data):
        return previous_documents is None or previous.get(data.get("id")) == data

    def adoption_gate_retained(data):
        if previous_documents is None:
            return True
        prior = previous.get(data.get("id"))
        fields = ("status", "as_is_baseline", "acceptance_decision", "repositories")
        return prior is not None and all(prior.get(key) == data.get(key) for key in fields)

    def finish():
        for values in (errors, warnings):
            values.sort(key=lambda item: (item["code"], item["path"], item["message"]))
        return {"valid": not errors, "errors": errors, "warnings": warnings,
                "stats": {"documents": len(documents), "artifacts": len(artifacts)}}

    # Malformed user data is a conformance error, not a Python exception.
    list_fields = {"active_auras", "planned_auras", "condition_alerts", "handoffs",
                   "workstreams", "depends_on", "risks", "conditions", "evidence",
                   "subject", "artifacts", "repositories", "blockers", "controls"}
    list_fields.update({"aura_activation", "operations", "criteria"})
    map_fields = {"implementation", "assurance", "closure", "last_transition",
                  "authority", "independence", "acceptance", "due", "blocks"}
    scalar_fields = {"id", "kind", "status", "phase", "phase_state", "mode", "level", "initial_level", "residual_level", "actor_type", "actor", "basis", "method", "builder", "verifier", "decision_type", "outcome", "superseded_by", "supersedes"}
    scalar_fields.update({"decision", "stable_baseline", "specification_baseline", "based_on_baseline", "project_intent_baseline", "project_baseline", "adoption_record", "source_decision", "resolution_decision", "acceptance_decision", "decision_record", "as_is_baseline"})
    scalar_fields.update({"repository", "aura", "code_commit", "base_code_commit", "result_code_commit"})
    for item in documents:
        data = item["data"]
        if not isinstance(data, dict):
            continue
        for node_path, node in walk(data, item["path"]):
            if not isinstance(node, dict):
                continue
            for key, value in node.items():
                if key in list_fields and not isinstance(value, list):
                    issue(errors, "E_FIELD_TYPE", f"{node_path}.{key}", "Expected a list.")
                if key in map_fields and not isinstance(value, dict):
                    issue(errors, "E_FIELD_TYPE", f"{node_path}.{key}", "Expected a mapping.")
                if key in scalar_fields and value is not None and not isinstance(value, str):
                    issue(errors, "E_FIELD_TYPE", f"{node_path}.{key}", "Expected text or null.")
        for key in ("active_auras", "planned_auras", "condition_alerts", "workstreams", "depends_on", "risks", "conditions"):
            value = data.get(key)
            if isinstance(value, list) and any(not isinstance(ref, str) for ref in value):
                issue(errors, "E_REFERENCE_TYPE", f"{item['path']}:{key}", "Expected artifact identifiers.")
        transition = data.get("last_transition")
        if isinstance(transition, dict):
            for key in ("from", "to"):
                if key in transition and not isinstance(transition[key], dict):
                    issue(errors, "E_FIELD_TYPE", f"{item['path']}:last_transition.{key}", "Expected a state mapping.")
    if errors:
        return finish()

    def register(artifact_id: Any, path: str, data: dict[str, Any]) -> None:
        if not isinstance(artifact_id, str) or not ID_RE.fullmatch(artifact_id):
            issue(errors, "E_ID_FORMAT", path, "Durable artifact identifier is missing or invalid.")
            return
        if artifact_id in artifacts:
            issue(errors, "E_ID_DUPLICATE", path, f"Identifier {artifact_id} is already defined.")
            return
        artifacts[artifact_id] = (path, data)
        if not SEMANTIC_ID_RE.fullmatch(artifact_id):
            issue(warnings, "W_LEGACY_ID", path, f"Identifier {artifact_id} uses a preserved legacy form.")

    for item in documents:
        path, data = item["path"], item["data"]
        if not isinstance(data, dict):
            issue(errors, "E_DOCUMENT_MAPPING", path, "A canonical YAML document must contain one mapping.")
            continue
        if "id" in data:
            register(data.get("id"), path, data)
        elif "kind" in data:
            issue(errors, "E_ID_FORMAT", path, "A durable artifact cannot omit its identifier.")
        if path.endswith("repositories.yaml"):
            for index, repository in enumerate(data.get("repositories") or []):
                if isinstance(repository, dict):
                    register(repository.get("id"), f"{path}:repositories[{index}]", repository)
        for node_path, node in walk(data, path):
            if isinstance(node, dict):
                for key, value in node.items():
                    if str(key).lower() in SECRET_KEYS and value not in (None, "", [], {}):
                        issue(errors, "E_SECRET_VALUE", f"{node_path}.{key}", "A secret-bearing key contains persisted data.")
            elif isinstance(node, str) and ABSOLUTE_PATH_RE.match(node):
                issue(warnings, "W_MACHINE_PATH", node_path, "A machine-specific absolute path requires local-only classification.")

    def resolve(ref: Any, path: str, code: str, kind: str | None = None):
        if not isinstance(ref, str) or ref not in artifacts:
            issue(errors, code, path, "Required local artifact reference does not resolve.")
            return None
        value = artifacts[ref][1]
        if kind and value.get("kind") != kind:
            issue(errors, code, path, f"Reference must resolve to kind {kind}.")
            return None
        return value

    def effective_decision(ref: Any, path: str, decision_type=None, subject=None, strict=False, outcome=None) -> bool:
        decision = resolve(ref, path, "E_DECISION_REFERENCE", "decision")
        if decision is None:
            return False
        if decision.get("status") != "effective":
            issue(errors, "E_DECISION_INEFFECTIVE", path, "Protected Decision Record is not effective.")
            return False
        authority = decision.get("authority") or {}
        provenance = authority.get("provenance") or {}
        complete = (
            authority.get("actor_type") in {"human", "agent", "external_governance"}
            and bool(authority.get("actor"))
            and authority.get("basis") in {"direct_confirmation", "project_policy", "delegated", "external_record"}
            and isinstance(provenance, dict)
            and provenance.get("method") in {"explicit_confirmation", "project_record", "storage_signature", "external_approval"}
        )
        if not complete:
            if retained(decision) and not strict:
                issue(warnings, "W_LEGACY_AUTHORITY", path, "Preserved decision lacks current authority provenance; it cannot authorize a new gate.")
            else:
                issue(errors, "E_DECISION_AUTHORITY", path, "Protected decision requires declared authority and provenance.")
        legacy = retained(decision) and not strict
        if decision_type and decision.get("decision_type") != decision_type and not (legacy and "decision_type" not in decision):
            issue(errors, "E_DECISION_TYPE", path, "Decision does not authorize this kind of commitment.")
        if subject and subject not in (decision.get("subject") or []) and not (legacy and "subject" not in decision):
            issue(errors, "E_DECISION_SUBJECT", path, "Decision does not cover the affected artifact.")
        if outcome:
            aliases = {"accepted": "accept", "approved": "accept", "conditionally_accepted": "conditional_accept", "rejected": "reject", "closed": "close"}
            actual_outcome = decision.get("outcome")
            if aliases.get(actual_outcome, actual_outcome) != outcome and not (legacy and "outcome" not in decision):
                issue(errors, "E_DECISION_OUTCOME", path, "Decision outcome does not authorize the requested state.")
        if authority.get("actor_type") == "agent":
            if authority.get("basis") not in {"delegated", "project_policy"}:
                issue(errors, "E_AGENT_AUTHORITY", path, "An agent requires bounded delegation or accepted project policy.")
            if authority.get("basis") == "delegated":
                delegation = resolve(authority.get("delegation"), path, "E_DELEGATION_REFERENCE", "decision")
                if delegation is not None and (delegation.get("status") != "effective" or delegation.get("decision_type") != "delegation" or delegation is decision):
                    issue(errors, "E_DELEGATION_INVALID", path, "Delegation must be a distinct effective delegation decision.")
        return True

    current = by_path.get("current.yaml")
    if not isinstance(current, dict):
        issue(errors, "E_CURRENT_MISSING", "current.yaml", "Canonical current.yaml is missing or invalid.")
        current = {}

    active_refs = current.get("active_auras")
    if not isinstance(active_refs, list):
        issue(errors, "E_ACTIVE_AURA_INDEX", "current.yaml:active_auras", "Active AURA index must be a list.")
        active_refs = []
    if len(active_refs) != len({json.dumps(item, sort_keys=True, default=str) for item in active_refs}):
        issue(errors, "E_ACTIVE_AURA_DUPLICATE", "current.yaml:active_auras", "Active AURA index contains duplicates.")
    for index, ref in enumerate(active_refs):
        active = resolve(ref, f"current.yaml:active_auras[{index}]", "E_ACTIVE_AURA_REFERENCE", "aura")
        if active is not None and active.get("status") != "active":
            issue(errors, "E_ACTIVE_AURA_STATUS", f"current.yaml:active_auras[{index}]", "Indexed AURA is not active.")

    loaded_active = {
        artifact_id for artifact_id, (_, data) in artifacts.items()
        if data.get("kind") == "aura" and data.get("status") == "active"
    }
    active_ref_set = {ref for ref in active_refs if isinstance(ref, str)}
    if active_ref_set != loaded_active:
        issue(errors, "E_ACTIVE_AURA_INDEX", "current.yaml:active_auras", "Active AURA index must contain every and only loaded active AURA.")

    planned_refs = current.get("planned_auras")
    if not isinstance(planned_refs, list):
        issue(errors, "E_PLANNED_AURA_INDEX", "current.yaml:planned_auras", "Planned AURA index must be a list.")
        planned_refs = []
    if len(planned_refs) != len({json.dumps(item, sort_keys=True, default=str) for item in planned_refs}):
        issue(errors, "E_PLANNED_DUPLICATE", "current.yaml:planned_auras", "Planned AURA index contains duplicates.")
    planned_ref_set = {ref for ref in planned_refs if isinstance(ref, str)}
    if active_ref_set & planned_ref_set:
        issue(errors, "E_AURA_INDEX_OVERLAP", "current.yaml", "An AURA cannot be indexed as both active and planned.")
    for index, ref in enumerate(planned_refs):
        planned = resolve(ref, f"current.yaml:planned_auras[{index}]", "E_PLANNED_AURA_REFERENCE", "aura")
        if planned is not None and planned.get("status") != "planned":
            issue(errors, "E_PLANNED_AURA_STATUS", f"current.yaml:planned_auras[{index}]", "Indexed AURA is not planned.")

    handoffs = current.get("handoffs")
    loaded_planned = {ref for ref, (_, data) in artifacts.items() if data.get("kind") == "aura" and data.get("status") == "planned"}
    if planned_ref_set != loaded_planned:
        issue(errors, "E_PLANNED_AURA_INDEX", "current.yaml:planned_auras", "Planned index must contain every and only planned AURA.")
    for key, kinds in {
        "adoption_record": {"adoption"},
        "project_intent_baseline": {"project_intent_baseline"},
        "project_baseline": {"as_is_baseline", "product_baseline"},
    }.items():
        ref = current.get(key)
        if ref is not None:
            target = resolve(ref, f"current.yaml:{key}", "E_CURRENT_REFERENCE")
            if target is not None and target.get("kind") not in kinds:
                issue(errors, "E_CURRENT_KIND", f"current.yaml:{key}", "Current pointer has an incompatible artifact kind.")

    def acyclic(field, kinds, code):
        visited, visiting = set(), set()
        def visit(ref):
            if ref in visiting:
                issue(errors, code, artifacts[ref][0], "Artifact relationships contain a cycle.")
                return
            if ref in visited or ref not in artifacts:
                return
            visiting.add(ref)
            data = artifacts[ref][1]
            links = data.get(field) or []
            if isinstance(links, str):
                links = [links]
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, str) and link in artifacts and artifacts[link][1].get("kind") in kinds:
                        visit(link)
            visiting.remove(ref)
            visited.add(ref)
        for ref, (_, data) in artifacts.items():
            if data.get("kind") in kinds:
                visit(ref)
    acyclic("depends_on", {"aura"}, "E_DEPENDENCY_CYCLE")
    acyclic("superseded_by", {"assurance_condition"}, "E_CONDITION_CYCLE")
    acyclic("supersedes", {"product_baseline"}, "E_BASELINE_CYCLE")

    def condition_resolved(ref, seen=None):
        seen = set() if seen is None else set(seen)
        if ref in seen or ref not in artifacts:
            return False
        seen.add(ref)
        condition = artifacts[ref][1]
        if condition.get("kind") != "assurance_condition":
            return False
        if condition.get("status") in {"satisfied", "waived"}:
            return True
        if condition.get("status") == "superseded":
            return condition_resolved(condition.get("superseded_by"), seen)
        return False

    if handoffs is None:
        handoffs = []
    if not isinstance(handoffs, list):
        issue(errors, "E_HANDOFF_INDEX", "current.yaml:handoffs", "Handoffs must be a list.")
        handoffs = []
    handoff_auras = []
    for index, handoff in enumerate(handoffs):
        if not isinstance(handoff, dict):
            issue(errors, "E_HANDOFF_ENTRY", f"current.yaml:handoffs[{index}]", "Handoff entry must be a mapping.")
            continue
        aura_ref = handoff.get("aura")
        handoff_auras.append(aura_ref)
        resolve(aura_ref, f"current.yaml:handoffs[{index}].aura", "E_HANDOFF_AURA_REFERENCE", "aura")
    if len(handoff_auras) != len({json.dumps(item, sort_keys=True, default=str) for item in handoff_auras}):
        issue(errors, "E_HANDOFF_DUPLICATE", "current.yaml:handoffs", "At most one current handoff may exist per AURA.")

    open_conditions = {
        artifact_id for artifact_id, (_, data) in artifacts.items()
        if data.get("kind") == "assurance_condition" and data.get("status") in {"open", "breached"}
    }
    indexed_conditions = set(current.get("condition_alerts") or [])
    if indexed_conditions != open_conditions:
        issue(errors, "E_CONDITION_ALERT_INDEX", "current.yaml:condition_alerts", "Condition alerts must exactly index open and breached conditions.")

    if previous_documents is not None:
        for ref, old in previous.items():
            new = artifacts.get(ref, (None, None))[1]
            immutable = old.get("kind") in {"product_baseline", "as_is_baseline", "specification_baseline"}
            if immutable and new != old:
                issue(errors, "E_IMMUTABLE_BASELINE", artifacts.get(ref, (ref, None))[0], "Preserve accepted baselines; create a superseding baseline instead.")
            if old.get("kind") == "decision" and old.get("status") == "effective":
                old_meaning = {key: value for key, value in old.items() if key != "status"}
                new_meaning = {key: value for key, value in (new or {}).items() if key != "status"}
                if new_meaning != old_meaning:
                    issue(errors, "E_IMMUTABLE_DECISION", artifacts.get(ref, (ref, None))[0], "Preserve effective decision meaning; record a new decision.")
            if old.get("kind") == "assurance_condition" and new is not None:
                protected = ("due", "blocks", "requirement", "responsible", "status", "superseded_by")
                changed = any(old.get(key) != new.get(key) for key in protected)
                automatic_breach = old.get("status") == "open" and new.get("status") == "breached" and all(old.get(key) == new.get(key) for key in protected if key != "status")
                if changed and not automatic_breach:
                    dtype = "risk_acceptance" if new.get("status") == "waived" else "condition_resolution"
                    effective_decision(new.get("resolution_decision"), ref, dtype, ref, strict=True)
                    decision = artifacts.get(new.get("resolution_decision"), (None, {}))[1]
                    if decision.get("outcome") not in {"accept", "accepted", "approve", "approved", "extend", "extended", "satisfied", "waived", "superseded", "reopen", "reopened", "amend", "amended"}:
                        issue(errors, "E_CONDITION_CHANGE_OUTCOME", ref, "Decision must approve the declared obligation change.")
                    if new.get("resolution_decision") == old.get("resolution_decision"):
                        issue(errors, "E_CONDITION_CHANGE_DECISION", ref, "Changing an obligation requires a new protected decision.")
        lineage, cursor = set(), current.get("project_baseline")
        while isinstance(cursor, str) and cursor not in lineage:
            lineage.add(cursor)
            cursor = artifacts.get(cursor, (None, {}))[1].get("supersedes")
        previous_current = next((item["data"] for item in normalize_documents(previous_documents) if item["path"] == "current.yaml"), {})
        previous_baseline = previous_current.get("project_baseline")
        if previous_baseline and current.get("project_baseline") != previous_baseline and previous_baseline not in lineage:
            issue(errors, "E_PRODUCT_LINEAGE", "current.yaml:project_baseline", "New integrated state must advance the previous current Product Baseline.")
        for ref, (path, data) in artifacts.items():
            if data.get("kind") == "product_baseline" and ref not in previous and ref not in lineage:
                issue(errors, "E_PRODUCT_CURRENT_INDEX", path, "New accepted Product Baseline must advance the current integrated product lineage.")

    for artifact_id, (path, data) in sorted(artifacts.items()):
        kind, status = data.get("kind"), data.get("status")

        if kind == "aura":
            legacy_terminal = status in TERMINAL and ("implementation" not in data or "depends_on" not in data)
            historical_decision = artifacts.get((data.get("closure") or {}).get("decision"), (None, {}))[1]
            legacy_provenance = bool(historical_decision) and "authority" not in historical_decision
            if status in TERMINAL and retained(data) and (legacy_terminal or legacy_provenance or (previous_documents is not None and previous.get(artifact_id) == data)):
                issue(warnings, "W_LEGACY_HISTORY", path, "Preserved completed cycle uses a legacy shape; no historical rewrite is required.")
                continue
            phase, phase_state = data.get("phase"), data.get("phase_state")
            blockers = data.get("blockers") or []
            workstreams = data.get("workstreams")
            depends_on = data.get("depends_on")
            implementation = data.get("implementation") or {}
            mode = implementation.get("mode")
            closure = data.get("closure") or {}
            if status == "active":
                resolve(current.get("project_baseline"), path, "E_ACTIVATION_BASELINE")
                resolve(data.get("based_on_baseline"), path, "E_AURA_BASELINE")

            if not isinstance(workstreams, list):
                issue(errors, "E_AURA_WORKSTREAMS", path, "AURA workstreams must be a list.")
                workstreams = []
            if len(workstreams) != len({json.dumps(item, sort_keys=True, default=str) for item in workstreams}):
                issue(errors, "E_AURA_WORKSTREAM_DUPLICATE", path, "AURA workstreams contain duplicates.")
            for index, ref in enumerate(workstreams):
                workstream = resolve(ref, f"{path}:workstreams[{index}]", "E_WORKSTREAM_REFERENCE")
                if workstream is not None and workstream.get("aura") != artifact_id:
                    issue(errors, "E_WORKSTREAM_AURA", f"{path}:workstreams[{index}]", "Workstream does not belong to this AURA.")

            if not isinstance(depends_on, list):
                issue(errors, "E_AURA_DEPENDENCIES", path, "AURA depends_on must be a list.")
                depends_on = []
            if len(depends_on) != len({json.dumps(item, sort_keys=True, default=str) for item in depends_on}):
                issue(errors, "E_AURA_DEPENDENCY_DUPLICATE", path, "AURA dependencies contain duplicates.")
            for index, ref in enumerate(depends_on):
                if ref == artifact_id:
                    issue(errors, "E_AURA_SELF_DEPENDENCY", f"{path}:depends_on[{index}]", "AURA cannot depend on itself.")
                else:
                    resolve(ref, f"{path}:depends_on[{index}]", "E_AURA_DEPENDENCY_REFERENCE", "aura")

            direct_fields = (
                implementation.get("repository"),
                implementation.get("base_code_commit"),
                implementation.get("branch_hint"),
                implementation.get("result_code_commit"),
            )
            if mode == "none":
                if any(value is not None for value in direct_fields) or workstreams:
                    issue(errors, "E_AURA_IMPLEMENTATION_NONE", path, "Implementation mode none cannot contain contribution bindings or Workstreams.")
            elif mode == "direct":
                if not implementation.get("repository") or not implementation.get("base_code_commit") or workstreams:
                    issue(errors, "E_AURA_IMPLEMENTATION_DIRECT", path, "Direct implementation requires one repository, an exact base commit, and no Workstreams.")
                elif isinstance(implementation.get("repository"), str):
                    resolve(implementation.get("repository"), f"{path}:implementation.repository", "E_AURA_REPOSITORY_REFERENCE")
            elif mode == "coordinated":
                if any(value is not None for value in direct_fields) or not workstreams:
                    issue(errors, "E_AURA_IMPLEMENTATION_COORDINATED", path, "Coordinated implementation requires Workstreams and null direct contribution fields.")
            else:
                issue(errors, "E_AURA_IMPLEMENTATION_MODE", path, "AURA implementation mode is invalid.")

            if status == "planned":
                if (
                    phase is not None or phase_state is not None or blockers or workstreams
                    or data.get("specification_baseline") is not None or mode != "none"
                ):
                    issue(errors, "E_AURA_PLANNED_STATE", path, "Planned AURA contains active lifecycle, accepted specification, or implementation state.")
                if closure:
                    issue(errors, "E_AURA_PLANNED_CLOSURE", path, "Planned AURA closure must be empty.")
            elif status == "active":
                if phase not in PHASES or phase_state not in {"in_progress", "ready", "blocked"}:
                    issue(errors, "E_AURA_ACTIVE_STATE", path, "Active AURA requires one valid phase and phase state.")
                if (phase_state == "blocked") != bool(blockers):
                    issue(errors, "E_AURA_BLOCKERS", path, "Only a blocked phase may contain active blockers, and it must contain at least one.")
                if closure:
                    issue(errors, "E_AURA_ACTIVE_CLOSURE", path, "Active AURA closure must be empty.")
            elif status == "conditionally_assured":
                conditions = [artifacts.get(ref, (None, {}))[1] for ref in data.get("conditions") or []]
                if phase is not None or phase_state is not None or blockers or not closure.get("stable_baseline"):
                    issue(errors, "E_AURA_CONDITIONAL_STATE", path, "Conditionally assured AURA must be non-active with a stable baseline.")
                if not conditions:
                    issue(errors, "E_AURA_CONDITIONAL_OBLIGATION", path, "Conditionally assured AURA must retain its conditions, including resolved obligations awaiting final approval.")
            elif status in TERMINAL:
                if phase is not None or phase_state is not None or blockers or not closure.get("stable_baseline"):
                    issue(errors, "E_AURA_TERMINAL_STATE", path, "Terminal AURA must be non-active with a stable baseline.")
            else:
                issue(errors, "E_AURA_STATUS", path, "AURA status is invalid.")
            level = (data.get("assurance") or {}).get("level")
            if level not in RISK_RANK:
                issue(errors, "E_ASSURANCE_LEVEL", path, "AURA assurance level is invalid.")
            highest = -1
            for ref in data.get("risks") or []:
                risk = resolve(ref, f"{path}:risks", "E_RISK_REFERENCE", "risk")
                if risk is not None:
                    highest = max(highest, RISK_RANK.get(risk.get("initial_level"), -1))
            if highest > RISK_RANK.get(level, -1):
                issue(errors, "E_ASSURANCE_FLOOR", path, "AURA assurance level is below its highest material initial risk.")

            transition = data.get("last_transition") or {}
            target = transition.get("to") or {}
            origin = transition.get("from") or {}
            state_tuple = lambda value: (value.get("status"), value.get("phase"), value.get("phase_state"))
            if not target or not transition.get("reason"):
                issue(errors, "E_TRANSITION_REQUIRED", path, "AURA requires a resulting state and transition reason.")
            if target and (target.get("status"), target.get("phase"), target.get("phase_state")) != (status, phase, phase_state):
                issue(errors, "E_LAST_TRANSITION_TARGET", path, "Last transition target does not match canonical AURA state.")
            old_status, old_phase, old_phase_state = state_tuple(origin)
            allowed = False
            if old_status is None:
                allowed = status == "planned" or (status == "active" and phase == "assess" and phase_state == "in_progress")
            elif old_status == "planned":
                allowed = status in {"planned", "closed", "rejected"} or (status == "active" and phase == "assess" and phase_state == "in_progress")
            elif old_status == "active":
                if status == "closed":
                    allowed = True
                elif old_phase == "assure" and old_phase_state == "ready" and status in {"assured", "conditionally_assured", "rejected"}:
                    allowed = True
                elif status == "active" and old_phase in PHASES and phase in PHASES:
                    delta = PHASES.index(phase) - PHASES.index(old_phase)
                    allowed = delta == 0 or (delta == 1 and old_phase_state == "ready" and phase_state == "in_progress")
                    if delta < 0 and phase_state == "in_progress":
                        allowed = old_phase == "realize" and phase == "understand"
                        if old_phase == "assure":
                            effective_decision(transition.get("decision"), path, "assurance", artifact_id, strict=True)
                            decision = artifacts.get(transition.get("decision"), (None, {}))[1]
                            allowed = decision.get("outcome") == "rework"
            elif old_status == "conditionally_assured":
                allowed = status in {"conditionally_assured", "assured"}
            elif old_status in TERMINAL:
                allowed = state_tuple(origin) == state_tuple(data)
            if target and not allowed:
                issue(errors, "E_TRANSITION_ILLEGAL", path, "AURA transition skips a gate or violates the lifecycle.")
            prior = previous.get(artifact_id)
            if prior and state_tuple(prior) != state_tuple(data) and state_tuple(origin) != state_tuple(prior):
                issue(errors, "E_TRANSITION_BASE", path, "Transition origin does not match the previous canonical state.")

            needs_spec = (status == "active" and (phase in {"realize", "assure"} or (phase == "understand" and phase_state == "ready"))) or status in {"assured", "conditionally_assured"}
            if needs_spec:
                specification = resolve(data.get("specification_baseline"), path, "E_GATE_SPECIFICATION", "specification_baseline")
                if specification is not None:
                    if specification.get("status") != "accepted" or specification.get("aura") != artifact_id:
                        issue(errors, "E_GATE_SPECIFICATION", path, "Accepted specification must belong to this AURA.")
                    effective_decision(specification.get("acceptance_decision"), path, "specification", specification.get("id"), strict=True, outcome="accept")
                    if not specification.get("artifacts"):
                        issue(errors, "E_SPECIFICATION_CONTENT", path, "Accepted specification requires referenced behavioral artifacts.")
            needs_candidate = (status == "active" and phase == "assure") or status in {"assured", "conditionally_assured"}
            if needs_candidate:
                if mode == "none" or (mode == "direct" and not implementation.get("result_code_commit")):
                    issue(errors, "E_GATE_CANDIDATE", path, "Assure requires an exact realization candidate.")
                if mode == "direct" and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", str(implementation.get("result_code_commit") or "")):
                    issue(errors, "E_GATE_COMMIT", path, "Candidate must reference a full immutable Git commit identifier.")
                if mode == "coordinated":
                    for ref in workstreams:
                        stream = artifacts.get(ref, (None, {}))[1]
                        if stream.get("status") not in {"integrated", "rejected"} or (stream.get("status") == "integrated" and not stream.get("result_code_commit")):
                            issue(errors, "E_GATE_WORKSTREAM", path, "Coordinated candidates require settled Workstreams and exact integrated results.")
            for ref in depends_on:
                dependency = artifacts.get(ref, (None, {}))[1]
                if status == "active" and dependency.get("status") not in {"assured", "conditionally_assured"}:
                    issue(errors, "E_DEPENDENCY_PENDING", path, "An ordering dependency must have an accepted outcome before activation.")
            if previous_documents is not None and status == "active" and (previous.get(artifact_id) or {}).get("status") != "active":
                for ref in open_conditions:
                    blocks = artifacts[ref][1].get("blocks") or {}
                    targets = blocks.get("aura_activation") or []
                    if "any" in targets or artifact_id in targets:
                        issue(errors, "E_ACTIVATION_CONDITION", path, "An unresolved condition blocks this activation.")
            for ref in data.get("conditions") or []:
                condition = resolve(ref, path, "E_CONDITION_REFERENCE", "assurance_condition")
                if condition is not None and condition.get("aura") != artifact_id:
                    issue(errors, "E_CONDITION_OWNER", path, "Condition belongs to a different AURA.")
                if status == "assured" and not condition_resolved(ref):
                    issue(errors, "E_ASSURED_OPEN_CONDITION", path, "Final assurance requires resolved condition chains.")

            if status in TERMINAL | {"conditionally_assured"}:
                dtype = "clean_closure" if status == "closed" else "assurance"
                expected_outcome = {"assured": "accept", "conditionally_assured": "conditional_accept", "rejected": "reject", "closed": "close"}[status]
                effective_decision(closure.get("decision"), f"{path}:closure.decision", dtype, artifact_id, strict=True, outcome=expected_outcome)
                baseline = resolve(closure.get("stable_baseline"), path, "E_CLOSURE_BASELINE")
                if baseline is not None and baseline.get("kind") not in {"as_is_baseline", "product_baseline"}:
                    issue(errors, "E_CLOSURE_BASELINE", path, "Closure must reference a stable product state.")
                if status in {"assured", "conditionally_assured"}:
                    decision = artifacts.get(closure.get("decision"), (None, {}))[1]
                    independence = decision.get("independence") or {}
                    needed = 0 if level == "standard" else 1 if level == "medium" else 2
                    if INDEPENDENCE.get(independence.get("required"), -1) < needed or INDEPENDENCE.get(independence.get("achieved"), -1) < needed:
                        issue(errors, "E_INDEPENDENCE", path, "Required and achieved independence must meet the assurance level.")
                    if needed > 0 and (not independence.get("builder") or not independence.get("verifier") or independence.get("builder") == independence.get("verifier")):
                        issue(errors, "E_VERIFIER_IDENTITY", path, "Separate verification requires distinct declared Builder and verifier identities.")
                    if level == "critical" and (decision.get("authority") or {}).get("actor_type") != "human":
                        issue(errors, "E_CRITICAL_AUTHORITY", path, "Critical acceptance requires an explicitly identified human authority.")
                    if not decision.get("evidence"):
                        issue(errors, "E_ASSURANCE_EVIDENCE", path, "Assurance decision requires evidence references.")
                    for ref in decision.get("evidence") or []:
                        resolve(ref, path, "E_EVIDENCE_REFERENCE")
                    outcome = "conditional_accept" if status == "conditionally_assured" else "accept"
                    if baseline is not None and (baseline.get("kind") != "product_baseline" or baseline.get("aura") != artifact_id or baseline.get("decision_record") != closure.get("decision") or baseline.get("assurance_decision") != outcome):
                        issue(errors, "E_ASSURANCE_BASELINE", path, "Outcome, cycle, decision, and Product Baseline must agree.")
                    if baseline is not None and mode == "direct":
                        pins = {pin.get("repository"): pin.get("code_commit") for pin in baseline.get("repositories") or [] if isinstance(pin, dict)}
                        if pins.get(implementation.get("repository")) != implementation.get("result_code_commit"):
                            issue(errors, "E_CANDIDATE_PIN", path, "Accepted repository pin must match the verified integration candidate.")
                    if status == "assured" and prior and prior.get("status") == "conditionally_assured":
                        old_closure = prior.get("closure") or {}
                        cursor, ancestors = closure.get("stable_baseline"), set()
                        while isinstance(cursor, str) and cursor not in ancestors:
                            ancestors.add(cursor)
                            cursor = artifacts.get(cursor, (None, {}))[1].get("supersedes")
                        if old_closure.get("stable_baseline") not in ancestors or closure.get("stable_baseline") == old_closure.get("stable_baseline") or closure.get("decision") == old_closure.get("decision"):
                            issue(errors, "E_CONDITIONAL_PROMOTION", path, "Final assurance requires a new decision and a new baseline retaining the conditional baseline in its ancestry.")

        elif kind == "risk":
            if data.get("initial_level") not in RISK_RANK:
                issue(errors, "E_RISK_LEVEL", path, "Risk initial level is invalid.")
            residual = data.get("residual_level")
            if residual is not None and residual not in RISK_RANK:
                issue(errors, "E_RISK_RESIDUAL_LEVEL", path, "Risk residual level is invalid.")

        elif kind == "assurance_condition":
            if status not in {"open", "breached", "satisfied", "waived", "superseded"}:
                issue(errors, "E_CONDITION_STATUS", path, "Condition status is invalid.")
            resolve(data.get("aura"), path, "E_CONDITION_AURA", "aura")
            effective_decision(data.get("source_decision"), path, "assurance", data.get("aura"), strict=True, outcome="conditional_accept")
            due, blocks = data.get("due") or {}, data.get("blocks") or {}
            verification = data.get("verification") or {}
            if not data.get("responsible") or not data.get("requirement") or not due.get("value") or due.get("kind") not in {"date", "event", "before_release", "before_aura_activation"}:
                issue(errors, "E_CONDITION_OBLIGATION", path, "Condition requires an owner, an observable obligation, and a due trigger.")
            if not isinstance(verification, dict) or not verification.get("criteria") or not blocks or not isinstance(blocks.get("release"), bool):
                issue(errors, "E_CONDITION_CONTRACT", path, "Condition requires verifiable criteria and explicit blocks.")
            if status == "satisfied" and not data.get("evidence"):
                issue(errors, "E_CONDITION_EVIDENCE", path, "Satisfied condition requires evidence.")
            for ref in data.get("evidence") or []:
                resolve(ref, path, "E_EVIDENCE_REFERENCE")
            if status in {"satisfied", "waived", "superseded"}:
                dtype = "risk_acceptance" if status == "waived" else "condition_resolution"
                effective_decision(data.get("resolution_decision"), f"{path}:resolution_decision", dtype, artifact_id, strict=True)
            if status == "superseded":
                resolve(data.get("superseded_by"), f"{path}:superseded_by", "E_CONDITION_SUPERSESSION", "assurance_condition")

        elif kind == "adoption":
            baseline = data.get("as_is_baseline")
            if status in {"in_progress", "incomplete"} and baseline is not None:
                issue(errors, "E_ADOPTION_PREMATURE_BASELINE", path, "Incomplete Adoption cannot own an AS-IS Baseline 0.")
            if status in {"accepted", "accepted_with_debt"}:
                initial = resolve(baseline, f"{path}:as_is_baseline", "E_ADOPTION_BASELINE", "as_is_baseline")
                effective_decision(data.get("acceptance_decision"), f"{path}:acceptance_decision", "adoption", artifact_id, strict=not adoption_gate_retained(data), outcome="accept")
                if initial is not None and (initial.get("adoption") != artifact_id or initial.get("acceptance_decision") != data.get("acceptance_decision") or initial.get("status") != status):
                    issue(errors, "E_ADOPTION_BASELINE", path, "Adoption and its AS-IS baseline must agree.")
                if current.get("adoption_record") == artifact_id:
                    cursor, seen = current.get("project_baseline"), set()
                    while isinstance(cursor, str) and cursor != baseline and cursor not in seen:
                        seen.add(cursor)
                        cursor = artifacts.get(cursor, (None, {}))[1].get("supersedes")
                    if cursor != baseline:
                        issue(errors, "E_ADOPTION_CURRENT_BASELINE", path, "Current product state must be the adopted baseline or an accepted successor of it.")
            if status == "accepted_with_debt":
                debt = data.get("assurance_debt") or []
                if not debt or any(not isinstance(item, dict) or not item.get("owner") or not item.get("priority") for item in debt):
                    issue(errors, "E_ADOPTION_DEBT", path, "Accepted-with-debt Adoption requires owned and prioritized debt.")

        elif kind == "as_is_baseline":
            if status not in {"accepted", "accepted_with_debt"}:
                issue(errors, "E_AS_IS_STATUS", path, "AS-IS Baseline 0 status is invalid.")
            adoption = resolve(data.get("adoption"), f"{path}:adoption", "E_AS_IS_ADOPTION", "adoption")
            if adoption is not None and (adoption.get("status") != status or adoption.get("as_is_baseline") != artifact_id):
                issue(errors, "E_AS_IS_ADOPTION", path, "AS-IS baseline must reference its accepted Adoption record.")
            effective_decision(data.get("acceptance_decision"), f"{path}:acceptance_decision")

        elif kind in {"specification_baseline", "project_intent_baseline"}:
            effective_decision(data.get("acceptance_decision"), f"{path}:acceptance_decision", strict=not retained(data))
            if kind == "specification_baseline":
                for item in data.get("artifacts") or []:
                    if not isinstance(item, dict) or not item.get("content_hash"):
                        issue(errors, "E_SPECIFICATION_ARTIFACT", path, "Baseline artifacts require an identifier and a content hash.")
                    else:
                        resolve(item.get("id"), path, "E_SPECIFICATION_REFERENCE")

        elif kind == "product_baseline":
            effective_decision(data.get("decision_record"), f"{path}:decision_record", strict=not retained(data))
            if data.get("assurance_decision") not in {"accept", "conditional_accept"}:
                issue(errors, "E_PRODUCT_OUTCOME", path, "Product assurance outcome is invalid.")
            if not data.get("repositories"):
                issue(errors, "E_PRODUCT_REPOSITORIES", path, "Product Baseline must pin at least one repository commit.")
            for repository in data.get("repositories") or []:
                if not isinstance(repository, dict) or not repository.get("code_commit"):
                    issue(errors, "E_PRODUCT_COMMIT", path, "Every product participant requires a code commit.")
                else:
                    resolve(repository.get("repository"), path, "E_PRODUCT_REPOSITORY")
                    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", str(repository.get("code_commit"))):
                        target = warnings if retained(data) else errors
                        issue(target, "W_LEGACY_COMMIT" if retained(data) else "E_PRODUCT_COMMIT", path, "Product pin must use a full immutable Git commit identifier for new acceptance.")
            if data.get("assurance_decision") == "conditional_accept" and not data.get("conditions"):
                issue(errors, "E_PRODUCT_CONDITIONS", path, "Conditional Product Baseline requires conditions.")
            if data.get("supersedes") is not None:
                resolve(data.get("supersedes"), path, "E_BASELINE_PREDECESSOR")
            for ref in data.get("conditions") or []:
                resolve(ref, path, "E_CONDITION_REFERENCE", "assurance_condition")
            for ref in data.get("evidence") or []:
                resolve(ref, path, "E_EVIDENCE_REFERENCE")

        elif kind == "decision" and status == "effective":
            effective_decision(artifact_id, path, strict=not retained(data))

        if kind == "as_is_baseline" or (kind == "adoption" and status in {"accepted", "accepted_with_debt"}):
            historic = adoption_gate_retained(data) if kind == "adoption" else retained(data)
            pins = data.get("repositories") or []
            pin_map = {}
            malformed = not pins
            for pin in pins:
                if not isinstance(pin, dict) or not isinstance(pin.get("repository"), str):
                    malformed = True
                    continue
                ref = pin["repository"]
                resolve(ref, path, "E_ADOPTION_REPOSITORY")
                if ref in pin_map or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", str(pin.get("code_commit") or "")):
                    malformed = True
                pin_map[ref] = pin.get("code_commit")
            if malformed:
                issue(warnings if historic else errors, "W_LEGACY_ADOPTION_PINS" if historic else "E_ADOPTION_PINS", path,
                      "New Adoption acceptance requires exact, unique repository commit pins in Adoption and AS-IS Baseline 0.")
            if kind == "adoption" and not historic:
                initial = artifacts.get(data.get("as_is_baseline"), (None, {}))[1]
                baseline_pins = {pin.get("repository"): pin.get("code_commit") for pin in initial.get("repositories") or [] if isinstance(pin, dict)}
                if pin_map != baseline_pins:
                    issue(errors, "E_ADOPTION_PINS", path, "Adoption and AS-IS Baseline 0 must pin the same starting code.")

    for item in documents:
        for node_path, node in walk(item["data"], item["path"]):
            if isinstance(node, str) and ID_RE.fullmatch(node) and node not in artifacts:
                issue(warnings, "W_UNRESOLVED_REFERENCE", node_path, f"Reference {node} is not loaded in this Workspace unit.")

    return finish()


class ConformanceInputError(RuntimeError):
    def __init__(self, path, message):
        super().__init__(message)
        self.path = path


def load_yaml_documents(root: Path) -> list[dict[str, Any]]:
    try:
        import yaml
        from yaml.constructor import ConstructorError
    except Exception as exc:
        raise RuntimeError("A safe YAML parser is unavailable; adapt the Harness or obtain approval before installing one.") from exc

    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ConstructorError("mapping", node.start_mark, f"duplicate key: {key}", key_node.start_mark)
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    documents = []
    for path in sorted(root.rglob("*.yaml")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = list(yaml.load_all(handle, Loader=UniqueKeyLoader))
        except (yaml.YAMLError, UnicodeError):
            raise ConformanceInputError(str(path), "Invalid UTF-8 YAML or duplicate mapping key.") from None
        if len(loaded) != 1:
            raise ConformanceInputError(str(path), "Expected exactly one YAML document.")
        documents.append({"path": path.relative_to(root).as_posix(), "data": loaded[0]})
    return documents


def workspace_fingerprint(root: Path) -> str:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("Workspace export must be a real directory.")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise RuntimeError("Workspace exports must not contain symlinks.")
        if root.resolve() not in path.resolve().parents:
            raise RuntimeError("Workspace path escapes its export root.")
        if path.is_file():
            relative = ".aurae/" + path.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def validate_workspace(root: Path, previous_root=None, new_workspace=False):
    content_hash = workspace_fingerprint(root)
    previous_hash = None
    previous_docs = None
    if previous_root is not None:
        previous_hash = workspace_fingerprint(previous_root)
        previous_docs = load_yaml_documents(previous_root)
    elif new_workspace:
        previous_hash = hashlib.sha256(b"").hexdigest()
        previous_docs = []
    documents = load_yaml_documents(root)
    result = validate_documents(documents, previous_docs)
    if workspace_fingerprint(root) != content_hash or (previous_root is not None and workspace_fingerprint(previous_root) != previous_hash):
        raise RuntimeError("Workspace changed during validation; retry from a stable export.")
    result["binding"] = {"version": 1, "validator_version": VERSION,
                         "candidate_sha256": content_hash, "base_sha256": previous_hash,
                         "mode": "write" if previous_docs is not None else "snapshot"}
    return result


def fixture_documents() -> list[dict[str, Any]]:
    project_id = "PRJ-existing-system-44444444"
    repository_id = "REP-application-repo-77777777"
    aura_id = "AURA-auth-change-66666666"
    adoption_id = "ADOPT-existing-system-11111111"
    baseline_id = "BL-existing-system-22222222"
    decision_id = "DEC-adoption-accepted-33333333"
    valid_documents = [
        {"path": "project.yaml", "data": {"id": project_id, "kind": "project"}},
        {"path": "repositories.yaml", "data": {"repositories": [
            {"id": repository_id, "name": "application", "role": "consumer_root"},
        ]}},
        {"path": "auras/active.yaml", "data": {
            "id": aura_id, "kind": "aura", "status": "active",
            "phase": "assess", "phase_state": "in_progress", "blockers": [],
            "specification_baseline": None, "depends_on": [],
            "implementation": {
                "mode": "none", "repository": None, "base_code_commit": None,
                "branch_hint": None, "result_code_commit": None,
            },
            "workstreams": [], "risks": [], "conditions": [],
            "assurance": {"level": "standard"}, "closure": {},
            "last_transition": {
                "from": {"status": "planned", "phase": None, "phase_state": None},
                "to": {"status": "active", "phase": "assess", "phase_state": "in_progress"},
            },
        }},
        {"path": "decisions/adoption.yaml", "data": {"id": decision_id, "kind": "decision", "status": "effective"}},
        {"path": "adoption.yaml", "data": {
            "id": adoption_id, "kind": "adoption", "status": "accepted",
            "as_is_baseline": baseline_id, "acceptance_decision": decision_id,
        }},
        {"path": "baselines/as-is.yaml", "data": {
            "id": baseline_id, "kind": "as_is_baseline", "status": "accepted",
            "adoption": adoption_id, "acceptance_decision": decision_id,
        }},
        {"path": "current.yaml", "data": {
            "active_auras": [aura_id], "planned_auras": [], "condition_alerts": [],
            "handoffs": [], "adoption_record": adoption_id, "project_baseline": baseline_id,
        }},
    ]
    valid_documents[2]["data"]["last_transition"].update(reason="Start bounded contribution", at="2026-09-06T00:00:00Z")
    valid_documents[2]["data"]["based_on_baseline"] = baseline_id
    for index in (4, 5):
        valid_documents[index]["data"]["repositories"] = [{"repository": repository_id, "code_commit": "a" * 40}]
    valid_documents[3]["data"].update(
        decision_type="adoption", subject=[adoption_id], outcome="accept",
        authority={"actor_type": "human", "actor": "project-owner", "basis": "direct_confirmation",
                   "provenance": {"method": "explicit_confirmation"}},
    )
    return valid_documents


def assurance_fixture():
    docs = fixture_documents()
    aura = docs[2]["data"]
    aura_id = aura["id"]
    spec_id, decision_id = "BL-behavior-spec-88888888", "DEC-cycle-assurance-99999999"
    product_id, spec_decision = "BL-accepted-product-aaaaaaaa", "DEC-spec-accepted-bbbbbbbb"
    evidence_id, behavior_id = "EV-behavior-run-cccccccc", "BEH-bounded-change-dddddddd"
    for ref, dtype, subject in ((spec_decision, "specification", spec_id), (decision_id, "assurance", aura_id)):
        decision = copy.deepcopy(docs[3]["data"])
        decision.update(id=ref, decision_type=dtype, subject=[subject], evidence=[evidence_id],
                        independence={"required": "self_check", "achieved": "self_check", "builder": "builder", "verifier": "builder"})
        docs.append({"path": f"decisions/{ref}.yaml", "data": decision})
    docs.extend([
        {"path": "specifications/behavior.yaml", "data": {"id": behavior_id, "kind": "behavior", "status": "accepted"}},
        {"path": "evidence/manifests/run.yaml", "data": {"id": evidence_id, "kind": "oracle_run", "result": "pass"}},
        {"path": "baselines/spec.yaml", "data": {"id": spec_id, "kind": "specification_baseline", "status": "accepted", "aura": aura_id,
          "artifacts": [{"id": behavior_id, "content_hash": "f" * 64}], "acceptance_decision": spec_decision}},
        {"path": "baselines/product.yaml", "data": {"id": product_id, "kind": "product_baseline", "aura": aura_id,
          "repositories": [{"repository": docs[1]["data"]["repositories"][0]["id"], "code_commit": "b" * 40}],
          "assurance_decision": "accept", "decision_record": decision_id, "conditions": [], "evidence": [evidence_id], "supersedes": docs[5]["data"]["id"]}},
    ])
    aura.update(status="assured", phase=None, phase_state=None, specification_baseline=spec_id,
                implementation={"mode": "direct", "repository": docs[1]["data"]["repositories"][0]["id"], "base_code_commit": "a" * 40, "result_code_commit": "b" * 40},
                closure={"decision": decision_id, "stable_baseline": product_id, "reason": "Behavior verified"})
    aura["last_transition"].update(
        {"from": {"status": "active", "phase": "assure", "phase_state": "ready"},
         "to": {"status": "assured", "phase": None, "phase_state": None}, "decision": decision_id})
    docs[6]["data"].update(active_auras=[], project_baseline=product_id)
    return docs


def conditional_fixture():
    docs = assurance_fixture()
    aura = docs[2]["data"]
    condition_id = "COND-check-deployment-12345678"
    aura.update(status="conditionally_assured", conditions=[condition_id])
    aura["last_transition"]["to"]["status"] = "conditionally_assured"
    docs[8]["data"]["outcome"] = "conditional_accept"
    docs[12]["data"].update(assurance_decision="conditional_accept", conditions=[condition_id])
    docs[6]["data"]["condition_alerts"] = [condition_id]
    docs.append({"path": "conditions/deployment.yaml", "data": {
        "id": condition_id, "kind": "assurance_condition", "aura": aura["id"],
        "status": "open", "requirement": "Observe release smoke pass", "responsible": "owner",
        "source_decision": docs[8]["data"]["id"],
        "due": {"kind": "before_release", "value": "v2"},
        "blocks": {"release": True, "aura_activation": ["any"], "operations": []},
        "verification": {"criteria": ["smoke passes"]},
        "evidence": [], "resolution_decision": None, "superseded_by": None,
    }})
    return docs


def resolved_fixture():
    docs = conditional_fixture()
    condition = docs[13]["data"]
    resolution = copy.deepcopy(docs[8])
    resolution["path"] = "decisions/resolution.yaml"
    resolution["data"].update(id="DEC-condition-resolved-12345678",
        decision_type="condition_resolution", subject=[condition["id"]], outcome="satisfied")
    docs.append(resolution)
    condition.update(status="satisfied", resolution_decision=resolution["data"]["id"],
        evidence=[docs[10]["data"]["id"]])
    docs[6]["data"]["condition_alerts"] = []
    return docs


def final_fixture():
    docs = resolved_fixture()
    aura = docs[2]["data"]
    decision = copy.deepcopy(docs[8])
    baseline = copy.deepcopy(docs[12])
    decision["path"] = "decisions/final.yaml"
    decision["data"].update(id="DEC-final-assurance-12345678", outcome="accept")
    baseline["path"] = "baselines/final.yaml"
    baseline["data"].update(id="BL-final-product-12345678", assurance_decision="accept",
        decision_record=decision["data"]["id"], supersedes=docs[12]["data"]["id"])
    aura["last_transition"]["from"] = copy.deepcopy(aura["last_transition"]["to"])
    aura["last_transition"]["to"]["status"] = "assured"
    aura["last_transition"]["decision"] = decision["data"]["id"]
    aura.update(status="assured", closure={"decision": decision["data"]["id"],
        "stable_baseline": baseline["data"]["id"], "reason": "All obligations verified"})
    docs[6]["data"]["project_baseline"] = baseline["data"]["id"]
    docs.extend([decision, baseline])
    return docs


def ready_prior(docs):
    prior = copy.deepcopy(docs)
    aura = prior[2]["data"]
    aura.update(status="active", phase="assure", phase_state="ready", conditions=[], closure={})
    aura["last_transition"].update({
        "from": {"status": "active", "phase": "assure", "phase_state": "in_progress"},
        "to": {"status": "active", "phase": "assure", "phase_state": "ready"}, "decision": None})
    prior[6]["data"].update(active_auras=[aura["id"]],
        project_baseline=prior[5]["data"]["id"], condition_alerts=[])
    excluded = {"baselines/product.yaml", "decisions/DEC-cycle-assurance-99999999.yaml"}
    return [item for item in prior if item["path"] not in excluded
            and item["data"].get("kind") != "assurance_condition"]


def self_test() -> dict[str, Any]:
    results = []
    def check(name, docs, expected=(), prior=None):
        result = validate_documents(docs, prior)
        codes = {item["code"] for item in result["errors"]}
        passed = set(expected).issubset(codes) if expected else result["valid"]
        results.append({"case": name, "passed": passed, "errors": sorted(codes)})
    check("accepted_adoption", fixture_documents())
    check("accepted_product_after_adoption", assurance_fixture())
    for phase in ("realize", "assure"):
        docs = fixture_documents()
        aura = docs[2]["data"]
        aura["phase"] = phase
        aura["last_transition"]["to"]["phase"] = phase
        check(f"skip_to_{phase}_without_specification", docs, ["E_TRANSITION_ILLEGAL", "E_GATE_SPECIFICATION"])
    docs = assurance_fixture()
    docs[2]["data"]["assurance"]["level"] = "critical"
    docs[8]["data"]["authority"] = {}
    check("critical_without_authority_or_independence", docs, ["E_DECISION_AUTHORITY", "E_INDEPENDENCE", "E_CRITICAL_AUTHORITY"])
    docs = fixture_documents()
    docs[6]["data"]["project_baseline"] = "BL-missing-product-12345678"
    check("missing_current_baseline", docs, ["E_CURRENT_REFERENCE"])
    docs = fixture_documents()
    docs[6]["data"]["condition_alerts"] = [{"wrong": "type"}]
    check("malformed_alerts", docs, ["E_REFERENCE_TYPE"])
    docs = fixture_documents()
    aura = docs[2]["data"]
    aura.update(status="planned", phase=None, phase_state=None)
    aura["last_transition"]["to"].update(status="planned", phase=None, phase_state=None)
    docs[6]["data"]["active_auras"] = []
    check("unindexed_preparation", docs, ["E_PLANNED_AURA_INDEX"])
    docs = fixture_documents()
    other = copy.deepcopy(docs[2]); other["path"] = "auras/other.yaml"; other["data"]["id"] = "AURA-other-change-12345678"
    docs[2]["data"]["depends_on"] = [other["data"]["id"]]
    other["data"]["depends_on"] = [docs[2]["data"]["id"]]
    docs.append(other); docs[6]["data"]["active_auras"].append(other["data"]["id"])
    check("cyclic_dependencies", docs, ["E_DEPENDENCY_CYCLE"])
    docs = fixture_documents()
    old = copy.deepcopy(docs[2]); old["path"] = "auras/history.yaml"
    old["data"].update(id="AURA-old-cycle-12345678", status="closed", phase=None, phase_state=None)
    for key in ("implementation", "depends_on", "last_transition"):
        old["data"].pop(key)
    docs.append(old)
    check("legacy_history_read", docs)
    check("legacy_history_unchanged_write", docs, prior=copy.deepcopy(docs))
    check("new_legacy_shaped_record_not_exempt", docs, ["E_AURA_IMPLEMENTATION_MODE"], prior=fixture_documents())
    docs = fixture_documents(); prior = copy.deepcopy(docs)
    docs[2]["data"]["phase"] = "understand"
    docs[2]["data"]["last_transition"].update({"from": {"status": "active", "phase": "assess", "phase_state": "ready"}, "to": {"status": "active", "phase": "understand", "phase_state": "in_progress"}})
    check("forged_previous_state", docs, ["E_TRANSITION_BASE"], prior=prior)
    check("conditional_acceptance", conditional_fixture(), prior=ready_prior(conditional_fixture()))
    check("last_condition_resolved_awaiting_decision", resolved_fixture(), prior=conditional_fixture())
    check("conditional_promotion_preserves_baseline", final_fixture(), prior=resolved_fixture())
    docs = final_fixture()
    docs[-1]["data"]["supersedes"] = docs[5]["data"]["id"]
    check("promotion_cannot_skip_conditional_baseline", docs, ["E_PRODUCT_LINEAGE"], prior=resolved_fixture())
    docs = assurance_fixture()
    docs[12]["data"]["repositories"] = []
    check("product_requires_code_pins", docs, ["E_PRODUCT_REPOSITORIES"], prior=ready_prior(assurance_fixture()))
    docs = assurance_fixture()
    docs[12]["data"]["repositories"][0]["code_commit"] = "c" * 40
    check("product_matches_candidate", docs, ["E_CANDIDATE_PIN"], prior=ready_prior(assurance_fixture()))
    docs = conditional_fixture()
    docs[8]["data"]["outcome"] = "reject"
    check("condition_source_is_acceptance", docs, ["E_DECISION_OUTCOME"])
    docs = resolved_fixture()
    docs[-1]["data"]["decision_type"] = "specification"
    check("condition_resolution_type", docs, ["E_DECISION_TYPE"], prior=conditional_fixture())
    docs = conditional_fixture()
    docs[13]["data"]["due"]["value"] = "v3"
    check("condition_extension_requires_decision", docs, ["E_CONDITION_CHANGE_DECISION"], prior=conditional_fixture())
    docs = assurance_fixture()
    docs[12]["data"]["evidence"] = []
    check("accepted_baseline_is_immutable", docs, ["E_IMMUTABLE_BASELINE"], prior=assurance_fixture())
    docs = fixture_documents()
    for index in (4, 5):
        docs[index]["data"].pop("repositories")
    check("new_adoption_requires_exact_pins", docs, ["E_ADOPTION_PINS"], prior=[])
    docs = fixture_documents()
    docs[3]["data"] = {key: value for key, value in docs[3]["data"].items() if key in {"id", "kind", "status"}}
    docs[3]["data"]["accepted_by"] = "historic owner"
    prior = copy.deepcopy(docs)
    docs[4]["data"]["unknowns"] = ["Historical note clarified"]
    check("legacy_adoption_annotation_preserves_gate", docs, prior=prior)
    return {"passed": all(item["passed"] for item in results), "cases": results}

def emit(result: dict[str, Any], exit_code: int) -> int:
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an exported AURAE Workspace.")
    parser.add_argument("workspace", nargs="?", help="Path to the exported .aurae directory")
    parser.add_argument("--self-test", action="store_true")
    previous_options = parser.add_mutually_exclusive_group()
    previous_options.add_argument("--previous-workspace", help="Exact exported .aurae tree of the expected base commit")
    previous_options.add_argument("--new-workspace", action="store_true", help="Validate initialization against an empty metadata tree")
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
        return emit(result, 0 if result["passed"] else 2)
    if not args.workspace:
        return emit({"valid": False, "errors": [{"code": "E_RUNTIME_ARGUMENT", "path": "$", "message": "Workspace path is required."}], "warnings": [], "stats": {}}, 2)
    try:
        previous_root = Path(args.previous_workspace).resolve() if args.previous_workspace else None
        result = validate_workspace(Path(args.workspace).resolve(), previous_root, args.new_workspace)
        return emit(result, 0 if result["valid"] else 1)
    except ConformanceInputError as exc:
        return emit({"valid": False, "errors": [{"code": "E_YAML_INPUT", "path": exc.path, "message": str(exc)}], "warnings": [], "stats": {}}, 1)
    except Exception as exc:
        return emit({"valid": False, "errors": [{"code": "E_RUNTIME", "path": "$", "message": str(exc)}], "warnings": [], "stats": {}}, 2)


if __name__ == "__main__":
    raise SystemExit(main())
# </AURAE_REFERENCE_VALIDATOR>
```

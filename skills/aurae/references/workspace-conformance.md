# Workspace conformance validator

## Purpose

This reference distributes transparent validator source without shipping an executable, binary, encoded payload, or runnable file. The normative contract is the behavior and result format below. The Python source is a reference implementation that an agent may materialize or adapt locally after inspecting the environment.

The validator checks structural and cross-artifact invariants. It does not decide whether user intent is correct, evidence is persuasive, a risk is acceptable, or a protected decision has legitimate meaning.

## Local materialization protocol

Before accepting, resuming, committing, or integrating a Workspace:

1. Read the format descriptor and apply [format-compatibility-and-migrations.md](format-compatibility-and-migrations.md) before using the current validator against a different or uncertain format.
2. Read this reference completely.
3. Inspect available runtimes and YAML parsers. Do not install or download anything without user approval.
4. Reuse a qualified local copy under the identity checks in Reference source below. Otherwise read the linked source completely and copy only its block into `.scratchpad/aurae/shared/harnesses/workspace-conformance/aurae_validate.py`, or translate it to an available local runtime while preserving the contract.
5. Keep the materialized file ignored and do not mark it executable. Invoke it explicitly through its runtime.
6. Run `--self-test` for first use or after a source, adaptation, runtime or parser change; an unchanged qualified copy may reuse its matching passing self-test record. Reject or repair the local Harness if the test fails. Every requested Workspace validation still runs against the current exact inputs.
7. Export the complete current or candidate `.aurae/` tree into an isolated path under `.scratchpad/`. Use the Storage Harness `export` command for exact committed bytes, without checkout filters or line-ending conversion.
8. For a read-only check, validate the tree without a previous-state option. For a write, pass `--previous-workspace <exact-parent-export/.aurae>`; use `--new-workspace` only for an empty metadata root. Exit code `0` means no blocking error, `1` means conformance errors (including malformed YAML), and `2` means the validator Harness or runtime failed.
9. Treat errors as blocking for the AURAE operation they affect. Do not use current-format conformance errors as a reason to rewrite unrelated history or block unrelated product work.
10. Re-run validation after integration and whenever the documented source, format version, parser, or local adaptation changes.

The validator must be read-only, offline, deterministic for identical inputs, and silent about secret values. A local adaptation must pass the same self-test and preserve the JSON result shape.

## Result contract

Write one JSON object to standard output:

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "stats": {
    "documents": 0,
    "artifacts": 0
  },
  "binding": {
    "version": 1,
    "validator_version": "1.1.1",
    "candidate_sha256": "<sha256-of-exact-candidate-files>",
    "base_sha256": null,
    "mode": "snapshot"
  }
}
```

Every issue contains `code`, `path`, and `message`. Sort issues by those fields. Never include a detected secret value in an issue.

`mode: write` includes the exact previous-tree fingerprint; an empty metadata root uses SHA-256 of empty bytes. The Storage Harness checks both fingerprints before sealing and checks the committed Git blobs again before publication. A snapshot result cannot authorize a write. The binding prevents accidental stale-report reuse; it is not an authenticated attestation against a malicious local process.

For a linear integration containing several commits, validate each consecutive parent/child pair and supply the resulting reports in order to the Storage Harness `cas` command. Do not compare only the final state to a much older canonical state: `last_transition` correctly refers to its real preceding transition. Do not fabricate a cumulative transition or silently skip an intermediate gate. Reviewed multi-parent reconciliation needs an adapter that validates the incoming histories and the merged result; the reference CAS intentionally supports linear history only.

Blocking checks in the MVP:

- every YAML document parses as one mapping and contains no duplicate key;
- durable identifiers are syntactically valid and unique;
- `current.yaml` indexes every active AURA, planned AURAs, AURA-scoped handoffs, condition alerts, Adoption Record, and baselines coherently;
- AURA status, phase, phase state, blockers, closure, transition ordering, specification entry gates, exact candidate pins, and assurance floor are coherent;
- dependency and supersession graphs have no cycles, and activation-order dependencies are satisfied;
- accepted Adoption states and Baseline 0 agree, new acceptances pin exact repository commits, and current product state may advance through their accepted successors;
- conditional assurance records, alerts, resolution decisions, and supersession links are coherent;
- new gates reference effective decisions of the right type, subject, and outcome, with declared authority, evidence, and verification independence appropriate to the assurance level;
- write validation preserves accepted baselines and decision meaning, distinguishes unchanged historical records from new gates, and requires a new decision and baseline for final conditional promotion;
- a cycle absent from the exact previous tree has a null creation origin and enters only a permitted initial state; an asserted prior phase cannot replace actual persisted history;
- every newly accepted Product Baseline agrees with its owning accepted cycle, assurance decision, conditions and evidence; an unrelated effective decision cannot authorize product acceptance;
- coordinated Assure may use exactly pinned `ready` lanes in an isolated combined candidate, while successful final closure still requires `integrated` or `rejected` lanes;
- obvious secret-bearing keys do not contain persisted values.

Unresolved general references and machine-specific paths are warnings because federated or external Workspaces may make them legitimate. A required local pointer named by `current.yaml`, a gate, a baseline, or a condition remains a blocking error.

These checks do not authenticate a decision maker, establish delegation scope, prove that evidence actually passed, verify specification hashes against product code, or establish Capability Readiness. Nor does a syntactically complete Git identifier prove that the commit exists in its owning repository. The agent and relevant verification/Storage Harness must still check these semantic and operational gates before proceeding. A `valid: true` result is conformance evidence, not product assurance.

## Reference source

The source intentionally performs no network access, subprocess execution, dynamic loading, or mutation.

The complete unchanged implementation and its self-tests are in [workspace-validator-source.md](workspace-validator-source.md). Read that source completely before first materialization, adaptation, or use after a source change.

For routine use, reuse a previously inspected local copy only after confirming it matches the packaged source (or its reviewed adaptation) and has a passing self-test for the current runtime/parser/Git environment. If identity, provenance, test status, or context is missing, reload the source and rerun the self-test. A readable source split never permits skipping validation or weakening the operational contract.


## Adaptation rules

An adaptation may change language, parser, or invocation, but not the result contract, exit-code meaning, blocking checks, read-only behavior, or self-test expectations. Add platform-specific checks only when they do not weaken the common contract.

When a parser or runtime is unavailable, report a Harness limitation. Do not reinterpret YAML with ad hoc text matching, silently skip checks, install packages without approval, or treat an agent's visual inspection as deterministic validation.

# Format compatibility and minimal migrations

## Purpose

Keep evolving AURAE skills able to work with existing project memory without rewriting history or blocking the project for format housekeeping. Prefer understanding and preservation over conversion.

This protocol concerns AURAE metadata, not application-code or data migrations.

## Negotiate before interpreting

Read `.aurae/aurae.yaml` before the rest of the Workspace and compare `format`, `format_version`, and `storage_contract_version` with the native contract in [versioning-and-releases.md](versioning-and-releases.md). Do not infer compatibility from a version number alone or from the agent product currently in use.

Classify the Workspace unit as one of:

- `native_writable` — the active structures and Storage Contract are understood and can be preserved on write;
- `legacy_readable` — older material can be interpreted reliably, but only the live surface may need adaptation before a canonical write;
- `unknown_read_only` — a newer, unsupported, or ambiguous contract may be inspected, but canonical AURAE mutation and gate claims that depend on it must stop;
- `recovery_required` — the descriptor is missing, malformed, or contradicts the stored state, so preserve the data and enter bounded recovery.

An incompatible AURAE operation does not automatically block unrelated product work. Continue safe read-only inspection or work against an already confirmed baseline when its meaning remains reliable. Do not pass an affected AURAE gate or publish an assurance claim until its state is understood.

## Prefer compatibility over migration

Use the least disruptive option in this order:

1. Interpret clear natural-language content and legacy fields without changing them.
2. Apply safe defaults only when their meaning is unambiguous and no accepted decision changes.
3. Preserve unknown fields verbatim while updating a known live record.
4. Add a current clarification or compatibility note that references the old artifact.
5. Migrate the smallest live surface only when the preceding options cannot support reliable work.

Never invent intent, risk acceptance, authority, evidence, or gate outcomes. When an ambiguity affects a protected decision, material risk, or gate, ask one plain-language question. For a non-blocking ambiguity, preserve it as an explicit inference, assumption, warning, or debt rather than rewriting its source.

## Live migration boundary

The default migration boundary is the current live frontier:

- `.aurae/aurae.yaml` when its write contract must advance;
- `.aurae/current.yaml` only for directly affected navigation, active-AURA, planned-AURA, and handoff fields;
- each active AURA whose current operation needs the new contract, plus artifacts created or changed for it;
- a planned AURA only when its dependencies or preparation are directly affected;
- the smallest shared index or referenced artifact required to keep those records coherent.

Do not migrate completed, rejected, or cleanly closed AURAs merely because their shape is old. Do not rewrite their baselines, decisions, risks, evidence, identifiers, filenames, ordering, wording, or source commits. If a live AURA depends on an older artifact, interpret it in place whenever possible. When clarification is necessary, append a new current record that cites the original instead of modifying the historical fact.

The Workspace descriptor states the current native write contract; it is not a claim that every historical artifact has been normalized to that version. A current validator or compatibility adapter must tolerate preserved legacy history that is not part of the live write surface, while still enforcing references and safety properties needed by current work.

Use snapshot validation for read-only interpretation and write validation against an exact previous Git export before publication. An unchanged historical terminal cycle may produce a compatibility warning without being requalified against modern gates. This is not an exemption for a newly inserted or changed legacy-shaped cycle, a new acceptance, or an unresolved pointer needed by live work. Updating descriptive knowledge on an Adoption Record does not re-enact its unchanged acceptance; changing its acceptance status, baseline, decision, or repository pins does require current checks. Never fill missing historical authority with a guessed identity.

Keep accepted baselines and the meaning of effective decisions immutable. Record a new superseding baseline or decision when accepted meaning changes. For an adopted project, its AS-IS Baseline 0 remains the historical starting point while `current.yaml.project_baseline` advances through accepted Product Baselines; do not reset the current product pointer to Baseline 0.

## Minimal projection from 0.1 to 1.0

When a live Workspace written under format `0.1.0` must become writable under `1.0.0`, project only its live frontier:

- replace scalar `current.active_aura` with `current.active_auras`, preserving the referenced active AURA when present;
- keep `current.planned_auras` and make it disjoint from `active_auras`;
- remove or ignore the global `current.specification_baseline`; each AURA continues to own its accepted Specification Baseline;
- project a singular handoff into `current.handoffs` and scope it to the affected AURA;
- replace a live `predecessor` relation with `depends_on` only on directly affected active or planned AURAs;
- add `implementation.mode` to each affected live AURA: use `none` before Realize or after a pre-implementation closure, `direct` for one repository contribution, and `coordinated` only when existing Workstreams form inseparable lanes of one outcome;
- preserve legacy Workstream records and references; do not invent Workstreams for ordinary direct AURAs.

Finish the current atomic operation before applying this projection. Apply it at the next safe checkpoint, or immediately before the first canonical write that needs concurrent active AURAs or a direct AURA contribution ref. Do not reopen a completed phase or rewrite completed history.

## When a migration is justified

Migrate only when at least one of these is true:

- an affected active AURA or current navigation state cannot be interpreted reliably;
- a required canonical write cannot preserve a coherent current state;
- an affected gate or assurance decision cannot be evaluated safely;
- the Storage Contract cannot perform the required operation without a compatible live descriptor.

A version difference, optional missing field, style change, renamed recommendation, new default, or opportunity to tidy old files is not sufficient justification.

Lossless, mechanical, narrowly scoped compatibility work does not require a protected user decision. Obtain and preserve explicit authority when the proposed transformation would change protected meaning, discard information, broaden scope, rename durable identifiers, alter accepted evidence, or affect a risk or gate. A broad or historical rewrite is outside the default protocol and always requires explicit user approval.

## Safe migration procedure

1. Capture the developer-state and canonical-ref preflight snapshots.
2. Read old content tolerantly and document only material inferences or ambiguities.
3. Prepare a compatibility projection or candidate under ignored `.scratchpad/` from the exact canonical base.
4. Finish any atomic operation already in progress, then apply the smallest semantic change inside the live migration boundary; avoid mass formatting and path churn.
5. Verify that untouched legacy fields and references are preserved, then validate the complete candidate with the appropriate current Harness.
6. Commit through compare-and-swap as a new descendant of the canonical ref. Never amend, rebase, replace, or force-push history.
7. Verify the canonical readback and the unchanged developer branch, `HEAD`, index, and working tree.

If any step fails, leave the canonical ref unchanged. Git history is the recovery baseline; do not create a second permanent backup tree. Use a concise migration note or Decision Record only when it preserves material provenance or a protected interpretation, not for every mechanical field addition.

## Multiple repositories and agents

Negotiate compatibility independently for each Workspace unit. The consumer/root may orchestrate one or more AURAs while a dependency remains legacy-readable or external. Migrate a dependency only when an integrated outcome requires a canonical change in that dependency; do not synchronize format upgrades across repositories for consistency alone. Concurrent AURAs may therefore operate across native-writable and legacy-readable units as long as every canonical write respects the local unit's negotiated contract.

An older agent encountering a format it cannot safely preserve must keep that Workspace unit read-only. A newer agent must preserve unknown legacy material and must not use its current conventions as permission to modernize accepted history.

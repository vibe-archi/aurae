# Workspace and artifact model

## Contents

1. Logical Workspace
2. Storage scopes
3. Canonical tree
4. Recommended project-facing layout
5. Artifact rules
6. Workspace conformance
7. Format compatibility
8. Minimal schemas
9. Baselines and resumability
10. Local-only state

## Logical Workspace

Treat AURAE memory as a logical, federated Workspace. A physical `.aurae/` tree can live in a Git metadata branch, an adjacent local store, or a combination of project and repository stores. The Git-backed tree is the MVP default.

Compose, do not concatenate, multiple Workspace units:

```text
Logical AURAE Workspace
= consumer/root project AURAE memory
+ AURAE-native dependency memories
+ descriptors for external dependencies
```

Preserve the source and scope of every artifact. Never let a local artifact silently override a project artifact or the reverse.

## Storage scopes

Use one of these `workspace_kind` values:

- `project` — cross-repository product intent, orchestration, integration, and global baselines;
- `repository` — knowledge and assurance owned by one repository;
- `combined` — a consumer/root repository that holds both its local and project orchestration state.

Prefer `combined` for a single application repository that naturally owns the assembled product.

Authority rules:

- Let the repository Workspace own repository-local implementation knowledge.
- Let the consumer/root Workspace own cross-repository intended behavior, composition, integration Oracles, and product acceptance.
- Let a dependency without AURAE remain external; store only the consumer's assumptions, contracts, references, Harnesses, and evidence about it.
- Block on contradictory claims. Do not resolve them through path precedence.

## Canonical tree

Store the following tree on the canonical metadata branch. Create directories only when needed.

```text
.aurae/
├── aurae.yaml
├── project.yaml
├── repositories.yaml
├── current.yaml
├── resume.md                  # optional pre-cycle Bootstrap/Adoption checkpoint
├── adoption.yaml
├── specifications/
│   ├── project-intent.yaml
│   ├── requirements/
│   ├── behaviors/
│   ├── interfaces/
│   └── invariants/
├── decisions/
├── risks/
├── auras/
│   └── <aura-id>/
│       ├── aura.yaml
│       ├── specification.yaml
│       ├── resume.md              # optional explicit pause/handoff context
│       ├── workstreams/
│       ├── conditions/
│       └── assurance.yaml
├── oracles/
│   ├── definitions/
│   └── suites/
├── capabilities/
│   ├── contracts/
│   └── harnesses/
├── evidence/
│   └── manifests/
└── baselines/
```

Use stable, predictable paths. Keep one canonical file per artifact. Let Git commits carry revisions; do not create `r001`, `r002`, and similar revision files.

Use YAML for compact structured state. Use Markdown only when narrative content materially improves human review. Keep generated indexes disposable and clearly marked; never make them the source of truth.

## Recommended project-facing layout

Read [project-layout.md](project-layout.md) before recommending or changing Oracle-test/documentation paths or maintaining a changelog. It owns the adaptable directory layouts, human-readable changelog rules, and ignored temporary-work conventions.

## Artifact rules

Give every durable artifact a stable, human-readable, locally generatable identifier. Use this default format:

```text
<PREFIX>-<semantic-slug>-<8-character-suffix>

AURA-sso-login-rollout-4fd21a8c
REQ-sso-session-renewal-9a62c7e1
INV-session-token-never-logged-2c8d14ef
RISK-sso-auth-secure-storage-87d638af
ORACLE-sso-login-success-6ab94e20
CAP-browser-login-observation-a4e91c62
EV-sso-regression-run-c6f83210
DEC-sso-specification-acceptance-b7812e4c
COND-sso-session-review-due-8b42d1e7
ADOPT-existing-platform-baseline-6f1a2c9d
```

Use established prefixes such as `PRJ`, `REP`, `ADOPT`, `AURA`, `REQ`, `BEH`, `IFACE`, `INV`, `ADR`, `DEC`, `COND`, `RISK`, `ORACLE`, `CAP`, `EV`, `BL`, and `WS`.

Build identifiers as follows:

- derive the semantic slug from two to six stable keywords that identify the artifact's subject, behavior, decision, or risk;
- normalize it to lowercase ASCII kebab-case using only `a-z`, `0-9`, and single hyphens;
- keep the slug concise, preferably no more than 48 characters, and shorten it at a word boundary;
- append eight lowercase hexadecimal characters generated from a collision-resistant random source or UUID/ULID;
- check the complete identifier against every loaded unit of the logical Workspace and regenerate the suffix if it already exists;
- never use a sequential number alone as the uniqueness mechanism;
- keep the identifier immutable after creation, even when the artifact title or wording evolves;
- never include secrets, personal data, credentials, machine-specific paths, or other sensitive values in the slug.

Treat the same identifier attached to different artifacts during composition or synchronization as a blocking conflict. Existing opaque prefixed identifiers remain valid and must not be silently renamed. Migrate them only when the user explicitly requests it; update filenames and every reference together in one canonical metadata commit, preserve an old-to-new mapping, and validate that no reference became orphaned.

In the minimal schemas below, `<id>` is shorthand for `<semantic-slug>-<8-character-suffix>` or for a valid legacy identifier.

Every persisted artifact must include:

- `id`;
- `kind`;
- `scope` and owning project/repository;
- `status`;
- provenance or creator context;
- relevant relationships.

When an artifact is read from canonical storage, return a derived envelope alongside it:

```yaml
artifact: <canonical-artifact-content>
storage:
  backend: git
  revision: <commit>
  path: <canonical-path>
```

The `storage` envelope is contextual provenance, not part of the persisted artifact. Never store an artifact's containing commit or equivalent revision inside that artifact. Use the backend-neutral term `storage_revision`; for the Git backend its value is the commit that supplied the artifact.

Do not require every artifact type in every AURA. At minimum, an AURA needs an objective, scope, phase, risks appropriate to the change, a Specification Baseline before Realize, a direct implementation binding or optional workstream references during Realize, and an assurance decision before acceptance.

Keep interview drafts, raw exploration, and question queues out of accepted project truth until validated. For an explicit pause/handoff, preserve the necessary non-sensitive queue and answers in the durable working-context document defined by [pause-and-resume.md](pause-and-resume.md). Its faithful recording does not validate draft intent, accept a gate or grant authority. Promote validated conclusions into their normal canonical artifacts; never use the note as a competing specification or lifecycle source.

## Workspace conformance

Treat the schemas in this reference and the lifecycle rules as normative. Use [workspace-conformance.md](workspace-conformance.md) to materialize a local validator Harness, run its self-test, and validate a complete exported Workspace before canonical writes, integration, and resume. Structural conformance does not replace human judgment about intent, risk, evidence quality, or protected decisions.

Do not store the materialized validator in the project or AURAE metadata branch. Keep it in ignored `.scratchpad/` and regenerate or revalidate it when the documented source or local runtime changes.

## Minimal schemas

### Format descriptor

```yaml
format: aurae-workspace
format_version: 1.0.0
methodology: Agentic Unified Risk-Aware Engineering
storage_contract_version: 1.0.0
```

`format_version` identifies the native write contract for the current live Workspace state. It does not require historical AURAs or artifacts to be rewritten into that shape. `storage_contract_version` identifies the Storage Harness behavior expected for safe reads, writes, and synchronization.

Read and apply [format-compatibility-and-migrations.md](format-compatibility-and-migrations.md) before interpreting a different version or changing legacy material. Version numbers are signals, not sufficient evidence of compatibility by themselves. Preserve unknown fields and old natural-language content whenever they do not prevent reliable current work.

### Project

```yaml
id: PRJ-<id>
kind: project
name: example
workspace_kind: combined
orchestration_root: REP-<id>
intent_baseline: BL-<id>
created_at: <ISO-8601>
```

### Adoption Record

Use one current Adoption Record to register the understood starting state. For an existing project this is the Adoption gate; Bootstrap reuses the same technical record and AS-IS Baseline 0 for its explicitly identified empty/setup-only starting repository under [project entry](project-entry.md#bootstrap). This does not turn setup into product assurance or require an existing product. Keep earlier states in Git history.

```yaml
id: ADOPT-<id>
kind: adoption
scope: project | repository
owner: <project-or-repository-id>
status: in_progress | incomplete | accepted | accepted_with_debt
repositories:
  - repository: REP-<id>
    code_commit: <git-commit>
    git_history: usable | shallow | absent | unknown
coverage:
  entrypoints: [<portable path or artifact ID>]
  critical_behaviors: [BEH-<id>]
  boundaries: [IFACE-<id> | INV-<id> | RISK-<id>]
  verification: [ORACLE-<id> | CAP-<id> | EV-<id>]
documentation:
  - repository: REP-<id>
    state: coherent | missing | fragmented | poorly_structured | unverified
    existing_paths: [<portable path>]
    proposed_mapping: [<portable path or mapping>]
    reconstruction_aura: AURA-<id> | null
changelogs:
  - repository: REP-<id>
    state: coherent | unverified | missing | reconstruction_proposed | reconstruction_approved | historical_draft | future_only
    path: <portable path> | null
unknowns: [<artifact-id-or-brief-item>]
assurance_debt:
  - item: <artifact-id-or-brief-item>
    owner: <stable project identity>
    priority: immediate | next | later
    target_aura: AURA-<id> | null
blockers: [<artifact-id-or-brief-item>]
as_is_baseline: BL-<id> | null
acceptance_decision: DEC-<id> | null
updated_at: <ISO-8601>
```

`in_progress` and `incomplete` require `as_is_baseline: null`. `accepted` and `accepted_with_debt` require an effective protected acceptance decision and an exact AS-IS Baseline 0. Documentation absence is Assurance Debt unless it prevents critical understanding or safe bounded work, in which case it is a gate blocker.

### AS-IS Baseline 0

```yaml
id: BL-<id>
kind: as_is_baseline
adoption: ADOPT-<id>
status: accepted | accepted_with_debt
repositories:
  - repository: REP-<id>
    code_commit: <git-commit>
critical_behaviors: [BEH-<id>]
boundaries: [IFACE-<id> | INV-<id>]
risks: [RISK-<id>]
verification: [ORACLE-<id> | CAP-<id> | EV-<id>]
unknowns: [<artifact-id-or-brief-item>]
assurance_debt:
  - item: <artifact-id-or-brief-item>
    owner: <stable project identity>
    priority: immediate | next | later
    target_aura: AURA-<id> | null
acceptance_decision: DEC-<id>
created_at: <ISO-8601>
```

This baseline is reproducible evidence of the understood starting state, not an assurance claim about the product. For Bootstrap, pin the approved initial code commit and state explicitly that product behavior does not yet exist; do not invent tests or assurance evidence for it. `accepted_with_debt` requires every material gap to be bounded and prioritized; any gap that prevents safe work in the stated scope keeps the starting-state record `incomplete`.

### Project Intent Baseline

```yaml
id: BL-<id>
kind: project_intent_baseline
project: PRJ-<id>
status: accepted
vision: <brief product direction>
intended_users: [<user-or-audience>]
scope:
  includes: [<important outcome-or-boundary>]
  excludes: [<explicit non-goal>]
major_capabilities: [<high-level capability>]
system_boundaries: [<system-or-dependency boundary>]
constraints: [<cross-cutting constraint>]
invariants: [INV-<id>]
risks: [RISK-<id>]
assumptions: [<important open assumption>]
assurance_priorities: [<quality-or-risk priority>]
acceptance_decision: DEC-<id>
```

Keep this baseline global and concise. It defines direction, not every feature or implementation detail. Revise it through a new accepted Git state when the global intent materially changes; do not create revision-suffixed files.

### Repository registry

```yaml
repositories:
  - id: REP-<id>
    name: application
    role: consumer_root
    location_hint: .
    aurae_mode: native
  - id: REP-<id>
    name: calculation-library
    role: dependency
    location_hint: ../calculation-library
    aurae_mode: native | external
```

Treat `location_hint` as local-only unless it is a portable relative workspace convention. Never synchronize a developer-specific absolute path.

### Current state

```yaml
active_auras: [AURA-<id>]
planned_auras: [AURA-<id>]
condition_alerts: [COND-<id>]
adoption_record: ADOPT-<id> | null
project_intent_baseline: BL-<id> | null
project_baseline: BL-<id> | null
handoffs:
  - aura: AURA-<id>
    state: ready
    gate_readiness: incomplete | ready
    open_items: [<artifact-id-or-brief-item>]
    next_action: <brief action>
updated_at: <ISO-8601>
```

Keep `active_auras` as an unordered set-like list containing every and only AURA whose canonical status is `active`. Resolve each lifecycle and Specification Baseline from its AURA artifact; `current.yaml` is a navigation index and must not duplicate phases or a global specification baseline. Keep `planned_auras` disjoint from `active_auras`; order planned entries only when the user expressed an intended sequence. `condition_alerts` contains exactly the `open` or `breached` conditions, and `adoption_record` resolves the current starting-state registration without duplicating it. On its accepted gate, update `adoption_record` and `project_baseline` atomically; `project_baseline` names AS-IS Baseline 0 until the first accepted delivery, then the latest accepted integrated Product Baseline. An `incomplete` gate must not set a new baseline. Scope every handoff to one AURA and keep at most one current handoff entry per AURA. Treat legacy `active_aura`, `specification_baseline`, `phase`, and singular `handoff` fields through the compatibility contract; never guess their plural projection when it is ambiguous.

### AURA

```yaml
id: AURA-<id>
kind: aura
title: <short title>
scope: project | repository
owner: <project-or-repository-id>
status: planned | active | conditionally_assured | assured | rejected | closed
phase: assess | understand | realize | assure | null
phase_state: in_progress | ready | blocked | null
blockers: [<artifact-id-or-brief-item>]
objective: <validated objective>
assurance:
  level: standard | medium | high | critical
  derived_from: [RISK-<id>]
  rationale: [<brief classification reason>]
risks: [RISK-<id>]
conditions: [COND-<id>]
project_intent_baseline: BL-<id>
based_on_baseline: BL-<id>
specification_baseline: BL-<id> | null
depends_on: [AURA-<id>]
preparation:
  state: none | outline | specification_prepared | ready_for_revalidation
  confirmed_artifacts: [<artifact-id>]
  open_engineering_work: [<artifact-id-or-brief-item>]
  activation_blockers: [<artifact-id-or-brief-item>]
implementation:
  mode: none | direct | coordinated
  repository: REP-<id> | null
  base_code_commit: <git-commit> | null
  branch_hint: <optional branch> | null
  result_code_commit: <git-commit> | null
workstreams: [WS-<id>]
last_transition:
  from:
    status: planned | active | conditionally_assured | assured | rejected | closed | null
    phase: assess | understand | realize | assure | null
    phase_state: in_progress | ready | blocked | null
  to:
    status: planned | active | conditionally_assured | assured | rejected | closed
    phase: assess | understand | realize | assure | null
    phase_state: in_progress | ready | blocked | null
  decision: DEC-<id> | null
  reason: <brief reason>
  at: <ISO-8601>
closure:
  decision: DEC-<id> | null
  reason: <brief reason> | null
  stable_baseline: BL-<id> | null
```

For a planned AURA, keep `phase`, `phase_state`, and `specification_baseline` null, `blockers` and `workstreams` empty, set `implementation.mode: none` with null implementation fields, and use `preparation.activation_blockers` for conditions that prevent activation. `preparation.state` describes how far its provisional definition has progressed without implying that the AURA is active or that Understand has passed. Bind `based_on_baseline` to the exact Product Baseline used during preparation and list only genuine ordering dependencies in `depends_on`. A user request for the “next” AURA normally creates such a dependency; independent parallel work leaves the list empty.

Use the AURA artifact as the only canonical lifecycle source. Validate state according to [lifecycle-and-interaction.md](lifecycle-and-interaction.md#canonical-aura-state-machine). Keep `closure` empty for `planned` and `active` AURAs. For `conditionally_assured`, populate `closure`, clear `phase`, `phase_state`, and active blockers, remove only this AURA from `current.yaml.active_auras`, and retain at least one Condition Record. Once every condition is resolved, the cycle may remain conditionally assured pending a new protected final decision; the alert index contains only open or breached obligations. Populate `closure` for `assured`, `rejected`, or `closed` AURAs with the decision, reason, and reproducible stable baseline left by the cycle. Persist `last_transition` atomically with the new state; Git history supplies older transitions.

Use `implementation.mode: direct` for the normal one-AURA/one-contribution case. It requires one repository and an exact base commit; `branch_hint` is optional and mutable, while commit references are durable. Set the result commit when a candidate exists. Use `implementation.mode: coordinated` only with one or more optional Workstreams, and keep the direct repository and commit fields null. Use `none` before implementation begins or when an AURA closes before Realize. A branch may be renamed, rebased, or deleted without changing the AURA identity.

Set `assurance.level` to at least the highest `initial_level` among the AURA's material risks. It may be raised when the combined context requires more rigor, but never lowered below that floor. Keep `derived_from` empty only when no separate Risk Record is required, and summarize the standard risk judgment in `rationale`.

### Risk Record

Create a durable Risk Record for every `medium`, `high`, or `critical` risk. Keep a `standard` risk inline unless durable ownership, reuse, or decision history adds value.

```yaml
id: RISK-<id>
kind: risk
scope: project | repository | aura
owner: <project-or-repository-id>
status: open | controlled | accepted | realized | retired
scenario: <what could happen and why it matters>
initial_level: standard | medium | high | critical
classification_reasons: [<credible consequence, floor, or aggravating factor>]
risk_owner: <responsible authority>
controls: [<requirement, invariant, Oracle, capability, or decision ID>]
evidence: [EV-<id>]
residual_level: standard | medium | high | critical | null
residual_reasons: [<brief evidence-backed reason>]
acceptance:
  decision: pending | accepted | conditionally_accepted | rework | retired
  decision_record: DEC-<id> | null
  conditions: [COND-<id>]
```

Do not set or lower `residual_level` from planned controls alone. Every material risk must ultimately link to an implemented control with evidence or to an explicit acceptance decision. A Builder must not silently accept a critical residual risk.

### Decision Record

Create a Decision Record for every protected decision. Keep ordinary reversible technical choices inline unless preserving them reduces meaningful uncertainty.

```yaml
id: DEC-<id>
kind: decision
scope: project | repository | aura
owner: <project-or-repository-id>
status: proposed | effective | superseded | withdrawn
decision_type: project_intent | adoption | specification | architecture | security | compliance | risk_acceptance | assurance | condition_resolution | clean_closure | delegation | other
subject: [<artifact-id>]
outcome: <brief accepted, rejected, or proposed outcome>
authority:
  actor_type: human | agent | external_governance
  actor: <stable project identity>
  basis: direct_confirmation | project_policy | delegated | external_record
  delegation: DEC-<id> | null
  provenance:
    method: explicit_confirmation | project_record | storage_signature | external_approval
    reference: <portable external or prior reference> | null
independence:
  required: not_applicable | self_check | separate_review | independent_verifier
  achieved: not_applicable | self_check | separate_review | independent_verifier
  builder: <stable participant identity> | null
  verifier: <stable participant identity> | null
evidence: [<artifact-id>]
decided_at: <ISO-8601>
```

Do not treat Git author or committer identity as proof of authority. A Decision Record preserves declared provenance; storage signatures or external approvals provide stronger authenticity only when the project requires them. For `storage_signature`, verify the signature from the derived storage envelope and never persist the containing commit or revision in the Decision Record. For a new protected decision, do not rely on a legacy free-form `accepted_by` field without obtaining and recording sufficient current authority.

### Condition Record

Create one durable Condition Record for each obligation attached to a conditional assurance decision. Store it under `.aurae/auras/<aura-id>/conditions/<condition-id>.yaml`.

```yaml
id: COND-<id>
kind: assurance_condition
scope: aura
owner: <project-or-repository-id>
aura: AURA-<id>
status: open | satisfied | breached | waived | superseded
requirement: <observable outcome that must be achieved>
responsible: <stable participant or project identity>
source_decision: DEC-<id>
source_risks: [RISK-<id>]
due:
  kind: date | event | before_release | before_aura_activation
  value: <ISO-8601 date, event, or AURA-id>
blocks:
  release: true | false
  aura_activation: [AURA-<id> | any]
  operations: [<portable operation>]
verification:
  criteria: [<observable acceptance criterion>]
  oracles: [ORACLE-<id>]
  capabilities: [CAP-<id>]
evidence: [EV-<id>]
resolution_decision: DEC-<id> | null
superseded_by: COND-<id> | null
resolved_at: <ISO-8601> | null
```

An `open` or `breached` condition must appear in `current.yaml.condition_alerts`. `satisfied` requires sufficient verification evidence. `waived` and `superseded` require an effective protected Decision Record; a waiver is a risk-acceptance decision. A breach does not rewrite the baseline: its blocks remain effective until an explicit protected response decision. Changing a deadline or trigger is also protected.

### Specification Baseline

```yaml
id: BL-<id>
kind: specification_baseline
aura: AURA-<id>
status: accepted
artifacts:
  - id: REQ-<id>
    content_hash: <hash>
  - id: ORACLE-<id>
    content_hash: <hash>
acceptance_decision: DEC-<id>
```

### Workstream

A Workstream is optional. Create it only when one AURA requires several coordinated implementation lanes that cannot be integrated and assured independently. An independently integrable and assurable lane is another AURA, optionally linked through `depends_on`. A direct AURA must not create a ceremonial Workstream merely to mirror its branch.

```yaml
id: WS-<id>
aura: AURA-<id>
repository: REP-<id>
status: active | stale | ready | integrated | rejected
based_on_specification: BL-<id>
base_code_commit: <git-commit>
branch_hint: <optional branch>
result_code_commit: <git-commit> | null
```

Every Workstream belongs to exactly one coordinated AURA and one repository. Its branch hint is advisory; exact commits and its Specification Baseline binding are authoritative. All Workstreams of an AURA must be `integrated` or `rejected` before that AURA can close.

While the AURA is active in Assure, an included Workstream may remain `ready` with exact base/result commits and the accepted Specification Baseline binding. Record the stable combined candidate and its inputs in existing evidence/narrative context under the integration contract; lane pins alone do not prove actual assembly. `integrated` means landed in the intended destination, not merely included in an isolated test candidate. For several lanes in one repository, the accepted combined commit may contain distinct lane commits; verify that inclusion through Git rather than requiring their hashes to be identical. Successful final closure still requires every included lane to be integrated.

### Product Baseline

```yaml
id: BL-<id>
kind: product_baseline
aura: AURA-<id>
repositories:
  - repository: REP-<id>
    code_commit: <git-commit>
    aurae_revision: <storage-revision> | null
assurance_decision: accept | conditional_accept
decision_record: DEC-<id>
conditions: [COND-<id>]
evidence: [EV-<id>]
supersedes: BL-<id> | null
created_at: <ISO-8601>
```

`conditional_accept` requires a non-empty `conditions` list. A superseded condition must name its replacement, whose chain must end in conditions that are satisfied or validly waived before final assurance. Final promotion to `assured` creates a new Product Baseline with current evidence and a new protected decision; it may pin the same code commits, but its `supersedes` ancestry must retain the conditional baseline. Never mutate the earlier conditional Product Baseline or change the original decision's meaning.

Concurrent AURAs may start from the same `based_on_baseline`, but acceptance remains serialized into the integrated product history. Immediately before assurance, reconcile the AURA candidate with `current.yaml.project_baseline`. The new Product Baseline must pin the exact accepted integration commits and set `supersedes` to the latest Product Baseline it actually advances, not merely to the baseline from which development began.

When introducing a Product Baseline, its owning AURA, closure, effective assurance decision, declared outcome, conditions and evidence must agree in that write. An Adoption decision or another cycle's acceptance cannot substitute for its own assurance decision. Preserve prior accepted baselines unchanged when a later decision promotes conditional assurance; their original decision and conditions remain historical facts, not assertions about the owner's newest closure.

Persist `aurae_revision` only for another Workspace state that is already published and known before this Product Baseline is committed. Derive the containing Workspace's own revision from the Storage Harness read envelope; do not store it in the Product Baseline.

## Planned, concurrent, and dependent AURAs

Allow multiple active and planned AURAs in a logical Workspace. A planned AURA may hold confirmed requirements, behaviors, assumptions, initial risks, acceptance outcomes, dependencies, and proposed Oracles as durable preparation. Do not give it an accepted Specification Baseline, implementation binding, Workstreams, or Realize activity until activation.

Before activation, compare every prepared artifact with the current Product Baseline, declared dependency outcomes, and materially overlapping active AURAs. Mark impacted preparation stale, record the reason, and finish Understand again when a landed or concurrent change affects relevant behavior, interface, invariant, risk, dependency, Oracle, capability, or integration path. Promote an independent AURA from a stable reproducible product state without waiting for unrelated active AURAs. Preserve a blocker when a dependency, condition, or overlap makes safe realization or assurance ambiguous.

A handoff checkpoint must be sufficient for a new agent to resume without chat history. Persist or reference:

- the user's confirmed intent and expected behavior;
- the selected active or planned AURA and its exact state;
- accepted Project Intent, Specification, and product baselines where they exist;
- open risks, assumptions, questions, deviations, and activation blockers;
- required capabilities and current readiness;
- exact repository and metadata references;
- one concise next action.

Store the durable facts in their normal artifacts. Keep only a compact index in `current.yaml`; do not create a second narrative source of truth.

When a cycle has an explicit pause point, its scoped handoff entry references the stable `resume.md` path through `open_items` or `next_action`. The note retains interview/work continuity as of an observed revision; current cycle state and accepted artifacts take precedence over an older note. One latest note per cycle is sufficient; Git retains older versions. See [pause-and-resume.md](pause-and-resume.md) for completeness, provenance and the non-destructive resume procedure.

Before a cycle exists, an actual Bootstrap/Adoption interview may instead use the fixed `.aurae/resume.md` project-scoped narrative checkpoint under that same contract. Do not insert an `aura: null` handoff, invent a cycle or accept a baseline to save it. A partial Workspace may have empty active/planned indexes and null baseline pointers; this is incomplete entry, not completed Bootstrap/Adoption. Once entry is complete, the old entry note cannot override current accepted state or a cycle's own checkpoint.

## Baselines and resumability

Make every accepted baseline reproducible through exact code commits, known dependency AURAE storage revisions, the containing Workspace revision derived at read time, artifact hashes, and environment qualifications where relevant.

On resume:

1. Read `.aurae/aurae.yaml` and `.aurae/current.yaml` from the canonical metadata ref.
2. Resolve the current starting-state record and AS-IS Baseline when applicable, Project Intent Baseline, all indexed active and planned AURAs, open or breached condition alerts, and scoped handoffs. For an interrupted entry interview, inspect `.aurae/resume.md` before requiring a cycle and follow its pause/resume contract; do not restart completed entry from an older note.
3. For unfinished entry work, resume its actual stage under the entry checkpoint contract; the following cycle-specific steps apply only when resuming a cycle. Select the relevant AURA from the user's intent, an explicit identifier, or an unambiguous visible branch or commit binding. Ask one plain-language question only when several candidates remain materially plausible.
4. Resolve that AURA's canonical status, phase, phase state, blockers, Specification Baseline, dependencies, direct implementation or optional Workstreams, and handoff.
5. Compare its registered repositories and exact commits with visible Git state, then identify stale, missing, divergent, overlapping, or locally unavailable participants.
6. Report the selected phase, important mismatch, relevant dependency or handoff, and next action briefly.

If an AURA references an older Project Intent Baseline, mark it stale only when the newer global intent materially contradicts its scope, assumptions, or expected outcome.

Do not rewrite history to hide a rejected or rolled-back AURA. Record the later decision and reference the superseded baseline.

## Local-only state

Read [project-layout.md](project-layout.md#local-only-state) before creating temporary AI content. Canonical state, accepted specifications, required source and the only copy of required evidence must never depend on disposable scratch storage.

# Portable Oracle catalog

Read when creating or materially updating durable Oracle tests, or adopting existing tests. This contract applies **with or without an Oracle Lab dashboard**. It describes project-facing execution files, not a new canonical Workspace schema, Oracle form, phase or assurance level. Follow [oracles-capabilities-and-assurance.md](oracles-capabilities-and-assurance.md) for test meaning, selection, health and evidence.

## Layout and discovery

Use the project's approved Oracle root: propose `oracle-tests/` when there is no coherent equivalent; preserve a mapped existing root otherwise. Follow [project-layout.md](project-layout.md) before creating top-level folders or restructuring. The default unit is:

```text
oracle-tests/
├── scenarios/<category>/<scenario>/
│   ├── oracle.json        # portable catalog entry
│   ├── run.<extension>    # scripted mode only, or a thin existing-runner adapter
│   └── expected.json     # only when an exact JSON baseline is appropriate
├── harnesses/            # reusable project adapters
├── scripts/              # shared durable entry points when needed
└── data/                 # shared fixtures/expected data when needed
```

Create only needed files. A descriptor may instead sit beside an established scenario, or in an additive catalog that references a reviewed adapter. Record the chosen discovery roots and mapping once. Discover descriptors and categories from data; adding a valid Oracle must not require editing HTML, CSS or UI JavaScript. Do not create the optional `harnesses/lab/` just to make tests compatible.

Store raw results, terminal transcripts, captures and runner sessions under the repository's ignored `.scratchpad/oracle-lab/` (or an equivalent scoped scratch area), **not** beside tracked tests. Required implementations, fixtures and approved expectations remain durable. Promote indispensable evidence under the existing evidence policy before accepting work.

## Descriptor v1

Use UTF-8 `oracle.json` with these common fields:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1`; version of this project-facing catalog only |
| `id` | Existing canonical `ORACLE-…` identifier; use the semantic ID rules for a new Oracle |
| `title`, `category` | Short human-readable name and product area |
| `description` | Behavior being verified, not an assurance claim |
| `criterion` | Explicit observable success criterion; include forbidden effects where material |
| `form` | Existing form: `deterministic`, `agentic_execution`, `agentic_judgment`, `characterization` or `metamorphic` |
| `mode` | `script` or `manual`, as defined below |
| `prerequisites` | Plain-language environment, safe data and relevant permissions needed to execute |

`id` links this execution entry to canonical Oracle intent; it does not duplicate the accepted requirement or suite definition. Preserve known extra fields when adapting an existing descriptor. Unknown versions, duplicate IDs, conflicting mappings or ambiguous expectations are not runnable by guessing: report the affected entries and preserve other usable tests.

### Script mode

Use `script` only when execution and verdict can run without agent judgment or interaction. It does not mean “contains a prompt”. Prefer deterministic assertions, controlled inputs and explicit seeds/tolerances where relevant; never update a baseline automatically to match a failing output.

Add `script` (a descriptor-relative entry point) and, when used, `baseline` (a descriptor-relative approved expectation). Declare a runner-specific timeout when needed. Paths must stay within the approved catalog boundary; the reference Python adapter confines both to the Oracle root. For tests elsewhere, use a small reviewed adapter rather than relaxing confinement or moving their files. Keep commands in trusted project code/configuration, not user-editable command strings sent by the UI.

The packaged starter supports Python and exact JSON comparison. Other project runtimes, property/metamorphic assertions, tolerances or existing test frameworks need a qualified adapter; the catalog convention does not force a language or exact JSON comparison on all Oracles. A runner must reject unsupported forms/adapters rather than execute a prompt or silently change semantics.

```json
{
  "schema_version": 1,
  "id": "ORACLE-csv-row-preservation-a19d40",
  "title": "Export every selected row",
  "category": "Exports",
  "description": "Export a known selection and inspect the generated CSV.",
  "criterion": "All three selected rows appear once, with the expected columns and order.",
  "form": "deterministic",
  "mode": "script",
  "prerequisites": "Local test dataset; no production credentials or customer data.",
  "script": "run.py",
  "baseline": "expected.json",
  "timeout_seconds": 60
}
```

### Manual mode

Use `manual` for guided human execution in the UI, including scenarios normally carried out by an agent with tools or a browser. Display the full scenario/prompt as inert text and the `steps` array, whose entries contain `action` and `expected`. Include setup and cleanup in the prerequisites/steps where needed. No checkbox may imply that this scenario can run automatically with the scripted batch.

The dashboard does **not** invoke Codex, Claude, another agent, a model API or a browser-operating agent runner. Opening a scenario only displays its instructions. The user performs the steps and records observations; if an agent executes it outside the dashboard, record that actual executor separately in the normal evidence. A human substitution does not change the Oracle's canonical form or automatically satisfy an independence or judgment requirement.

```json
{
  "schema_version": 1,
  "id": "ORACLE-signout-session-revocation-b70e32",
  "title": "Sign out securely",
  "category": "Authentication",
  "description": "Check that signing out removes access to private content.",
  "criterion": "Private content remains inaccessible after sign-out, including browser Back and a direct URL.",
  "form": "agentic_execution",
  "mode": "manual",
  "prerequisites": "Use the local test app and a disposable signed-in account.",
  "steps": [
    {"action": "Sign out.", "expected": "The sign-in page appears."},
    {"action": "Go Back, then open a known private URL.", "expected": "No private content is exposed; signing in is required."}
  ]
}
```

## Execution and result boundary

Keep the descriptor independent of the UI. Each scripted entry must also run through a documented terminal/CI entry point; validate its invocation, prerequisites, observations and failure classification before using it. The optional interface consumes the same catalog and results, not a second set of tests.

The reference adapter streams newline-delimited JSON events: `{"type":"log","message":"…"}`, one `{"type":"result","actual":…}` on normal completion, or `{"type":"blocked","message":"…"}` when a prerequisite prevents verification. It compares the structured result with the reviewed JSON baseline. Successful process exit alone is not an Oracle pass; missing, malformed or duplicate results, invalid adapters and process errors cannot become a product verdict. Do not mix blocked and result events or change a test expectation based on runner output. Other adapters may use the project's native protocol while returning equivalent classified observations.

Keep run ID, timestamps, tested code revision/dirty state, environment, actual executor, descriptor/expectation identity and result provenance available to the evidence adapter. Old or unselected results remain historical, never current coverage. A changed candidate or expectation invalidates affected applicability, not historical observations. UI presentation may summarize but must not hide a failure, blocker or uncertainty.

Canonical Oracle outcomes remain `pass / fail / blocked / inconclusive / error`. UI states `idle`, `queued`, `running`, `cancelled` and an unfinished manual walkthrough are execution states, **not** new canonical verdicts. A cancellation/incomplete walkthrough cannot count as a pass or fulfill coverage; describe the gap and classify it under the existing assurance contract. A dashboard save/export never writes canonical acceptance, waives a gate or merges code.

## Existing tests and older AURAE versions

During Adoption, an upgrade review or a request to expose existing tests:

1. Inventory relevant tests, runners/CI entry points, fixtures, baselines and existing Oracle IDs without changing them. Distinguish behavior-level Oracles from unit tests; a unit-test folder is not automatically an Oracle suite.
2. Prefer reuse in place. Add only a descriptor or thin adapter where the existing behavior, assertions and invocation are understood. Keep paths, IDs, test commands, CI wiring, baselines and historical evidence intact. Do not bulk-convert old tests or force the recommended folder name.
3. Show the smallest proposed mapping when a migration is needed. **At the slightest unresolved doubt** about test meaning, baseline authority, runner compatibility, permissions, data, side effects, path changes or result equivalence, ask the user one focused question before changing that entry. Recommend keeping it unchanged while deciding. Generic Auto cannot silently resolve this uncertainty: under `none`, preserve the entry and report the blocked migration without asking.
4. Qualify an unambiguous additive adapter with the same safe fixture/candidate: compare old and new invocations, observations, verdicts and relevant side effects, including a negative/control case where feasible. Do not run destructive, costly or external tests merely to prove compatibility without the appropriate permission. If equivalence cannot be established, leave the original path working and the new entry unqualified/blocked.
5. Apply only the authorized affected entries at a safe boundary. Keep in-progress tests/phases and accepted history unchanged; defer earlier-phase implications under [upgrade.md](upgrade.md). Preserve unknown metadata and reversible source changes. Roll back only the added adapter/descriptor if needed, not the existing suite or user work.

No dashboard request is needed to use this format for new or materially updated Oracles. Conversely, catalog readiness, Bootstrap, Adoption, Auto or a skill upgrade never implies a request to create a dashboard. Read [oracle-lab.md](oracle-lab.md) only when that interface is explicitly requested.

# Multi-repository orchestration

## Contents

1. Consumer-root model
2. Participant modes
3. Cross-repository AURA
4. Federated reads
5. Multi-repository baseline
6. Repositories without AURAE
7. When to introduce a separate root

## Consumer-root model

Use the application or product repository that assembles the system as the default AURAE orchestration root. Avoid a separate coordination layer when one consumer naturally owns product behavior and acceptance.

```text
Consumer application AURAE
├── application repository lane
├── display library lane
└── calculation library lane
```

Let the consumer/root `.aurae` memory use `workspace_kind: combined`. Store both application-local knowledge and cross-repository orchestration there, with explicit artifact scopes.

The consumer is authoritative for the assembled product claim, not for every general-purpose policy or release decision of its libraries.

## Participant modes

Register each repository as:

- `native` — it has compatible AURAE metadata and can supply local baselines, contracts, Oracles, and evidence;
- `external` — it has no AURAE metadata, so the consumer records its version, assumed contracts, integration Harness, Oracles, and evidence;
- `unavailable` — it is referenced but not present locally; permit read-only planning, but block realization or assurance that requires it.

Keep local checkout paths outside canonical metadata. Synchronize repository IDs, remote identities when appropriate, dependency roles, expected revisions, and portable contract references.

Ensure each writable participant repository has its own ignored root `.scratchpad/`. Do not create one in a read-only external dependency; keep temporary work for that dependency under the consumer/root scratchpad instead.

## Cross-repository AURA

Open one project-scoped AURA when one product outcome spans several repositories and its repository changes cannot be integrated and assured independently. Use optional repository Workstreams as coordinated implementation lanes inside that AURA. When repository outcomes are independently integrable and assurable, create separate AURAs and declare `depends_on` only where a real ordering or baseline dependency exists. Do not duplicate AURAs for the same inseparable product decision.

During Assess, identify affected repositories, ownership, dependency order, release constraints, and integration risk.

During Understand:

- define the cross-repository expected behavior;
- baseline affected interfaces and invariants;
- identify local and integration Oracles;
- identify required repository access and Harnesses;
- decide which repository owns each implementation change;
- publish one project Specification Baseline.

During Realize, bind the project-scoped AURA to coordinated repository Workstreams, or bind each independently assurable AURA directly to its repository contribution. Let coordinated lanes proceed against the exact shared baseline and let separate AURAs advance according to their declared dependencies. Respect each repository's own contribution and review rules. Maintain the root changelog of every writable repository changed. Record the assembled product effect in the consumer/root changelog when notable, without duplicating dependency internals or modifying read-only external dependencies.

During Assure, require appropriate repository-local evidence plus consumer-level integration and regression Oracles. Let the consumer/root authority decide whether the assembled combination is accepted.

Product acceptance does not authorize each repository's code merge. Apply [the integration contract](collaborative-workstreams-and-git-reconciliation.md#integrate-and-close-safely) with explicit user-approved source/target scope for every affected repository; targets may differ. A clear approval can cover the enumerated cross-repository plan, but never implies all repositories use `main`. If only some integrations succeed, preserve those results and report the remaining work without claiming an atomic merge or a completed product baseline.

## Federated reads

Do not copy a native dependency's full AURAE memory into the consumer. Reference exact artifacts and their published storage revisions:

```text
aurae://<repository-id>/<artifact-kind>/<artifact-id>@<storage-revision>
```

Resolve only the artifacts needed for the selected active AURA. Treat the dependency repository as authoritative for its local artifacts and the consumer as authoritative for product composition.

If a referenced artifact is missing or its commit is unavailable, report the product baseline as non-reproducible and block assurance that relies on it.

## Multi-repository baseline

Git cannot atomically commit several repositories. Create transactional meaning through an immutable manifest that references exact available commits:

```yaml
id: BL-<id>
kind: product_baseline
repositories:
  - repository: REP-app
    code_commit: <commit>
    aurae_revision: <storage-revision>
  - repository: REP-display
    code_commit: <commit>
    aurae_revision: <storage-revision> | null
  - repository: REP-calculation
    code_commit: <commit>
    aurae_revision: <storage-revision> | null
assurance_decision: accept
```

Persist an `aurae_revision` only for another Workspace state that is already published and known before this manifest is committed. Derive the containing Workspace's own revision from the Storage Harness read envelope rather than storing a self-reference. In the Git backend, an AURAE storage revision is a commit.

Publish the manifest only after every referenced revision is available, required metadata is synchronized, and cross-repository assurance passes. Roll back by selecting the previous manifest; do not rewrite the history of the rejected combination.

## Repositories without AURAE

Do not require a dependency to adopt AURAE.

For an external participant, keep a compact descriptor in the consumer/root Workspace:

```yaml
id: REP-<id>
aurae_mode: external
revision: <code-commit-or-version>
contracts: [<consumer-owned-contract>]
capabilities: [CAP-<id>]
oracles: [ORACLE-<id>]
assurance_owner: consumer
```

Treat it as a black or grey box according to available access. Build a local Harness to inspect, build, execute, or test it. Store resulting evidence in the consumer's AURAE memory. Do not write `.aurae` metadata into the external repository unless its owner explicitly adopts the method.

## When to introduce a separate root

Add a separate project Workspace only when no repository naturally owns the assembled outcome, for example:

- several applications share one coordinated release;
- a platform spans independently governed products;
- the consumer repository cannot hold program-level decisions;
- a release train needs authority above any individual repo.

Keep the same contracts and federation model. Change only the orchestration root. Do not introduce peer-to-peer consensus between repositories; use peer discovery and references with explicit authority instead.

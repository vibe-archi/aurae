# Project-facing layout and local temporary work

Read before creating temporary AI work, recommending or restructuring Oracle-test/documentation folders, or maintaining a changelog. These project-facing paths are separate from canonical metadata schemas in [workspace-and-artifacts.md](workspace-and-artifacts.md).

## Recommended project-facing layout

Treat the following paths as default proposals, not mandatory AURAE storage. During Bootstrap or Adoption, inspect the repository before proposing them. Reuse a clear existing convention and record its mapping instead of creating a parallel structure. Suggest restructuring only when it materially improves discoverability, ownership, or execution; present the proposed mapping at a key moment and wait for user confirmation before creating top-level directories or moving or renaming existing content.

Create only directories that have current content or an accepted near-term purpose. Do not generate empty trees merely to match the recommendation.

### Durable Oracle Tests

When durable, project-managed Oracle implementations are useful and no equivalent convention exists, recommend:

```text
oracle-tests/
├── README.md
├── scenarios/<category>/<scenario>/
│   └── oracle.json
├── suites/
├── harnesses/
├── scripts/
├── data/
│   ├── fixtures/
│   └── expected/
└── config/
```

Use the parts as follows:

- `README.md` — scope, prerequisites, execution entry points, and the mapping to AURAE Oracle and Capability identifiers;
- `scenarios/` — behavior-level scenarios grouped by product area or user capability; new or materially updated durable Oracles include a discoverable `oracle.json` under [oracle-catalog.md](oracle-catalog.md), even when no dashboard is requested;
- `suites/` — optional project-runner groupings when the execution technology needs them;
- `harnesses/` — stable, reusable project adapters that implement Capability Contracts;
- `scripts/` — durable setup, execution, and maintenance entry points shared across scenarios;
- `data/fixtures/` — stable, non-secret inputs required to reproduce scenarios;
- `data/expected/` — reviewed expected outputs or approved golden references;
- `config/` — Oracle-specific configuration only when it does not belong in an existing project configuration location.

Keep behavioral intent and canonical suite definitions in `.aurae/oracles/`. Link project files to their `ORACLE-<id>` or `CAP-<id>` instead of duplicating that intent. Keep generated scripts, transformed data, logs, captures, traces, raw results, caches, sessions, and transient Harness files in `.scratchpad/`. Keep compact evidence manifests in `.aurae/evidence/manifests/`.

If the project already uses a clear equivalent such as `tests/e2e/`, `tests/system/`, or another established test tree, propose mapping AURAE Oracles into it rather than introducing `oracle-tests/`. Follow the project's test framework and language conventions when they improve integration.

The path proposal is adaptable; the portable catalog contract applies to new or materially updated durable Oracles regardless of UI use. Preserve old suites in place and use additive descriptors/adapters only after resolving compatibility; involve the user at any unresolved migration doubt under [oracle-catalog.md](oracle-catalog.md#existing-tests-and-older-aurae-versions). Do not create an empty catalog or bulk-rewrite historical tests.

An Oracle Lab is optional and requires an explicit user request. Only then consider `harnesses/lab/` and [oracle-lab.md](oracle-lab.md); Bootstrap, Adoption, Auto and the presence of test templates never imply that request.

### Documentation

When a project has no coherent documentation root, recommend:

```text
docs/
├── README.md
├── archi/
├── contrib/
├── user/
└── install/
```

Use the parts as follows:

- `README.md` — optional index that directs each audience to the right section;
- `archi/` — high-level architecture, system boundaries, and interactions between services or modules;
- `contrib/` — internal design and codebase guidance for people maintaining or extending the project;
- `user/` — product usage guidance, including end-user guides for applications and consumer-developer guides for libraries;
- `install/` — installation, deployment, infrastructure, migration, or environment procedures when they are non-trivial.

Omit irrelevant sections. Keep concise setup instructions in the project's established entry point when a dedicated `install/` section would add no value. When an existing `docs/` tree is coherent, use it. When it mixes audiences or has become difficult to navigate, propose a concrete restructuring and ask for confirmation before changing paths.

During Adoption, record whether documentation is coherent, missing, fragmented, poorly structured, or unverified. When reconstruction is useful, present the proposed audience-to-path mapping before changing files and state that delivery will occur through an AURA. The approved mapping becomes an input to that AURA's specification, not permission to draft unchecked content during Adoption.

Treat documentation claims as assurance claims. In the documentation AURA, define the validation capability and Oracle for every material executable or behavioral claim. Run commands, examples, installation or deployment steps, and user workflows in a representative environment when feasible; corroborate architectural descriptions against code, configuration, tests, and runtime observation. Mark limitations explicitly instead of presenting unverified statements as fact.

### Changelog

Maintain `CHANGELOG.md` at the root of every writable repository changed during Realize. Use the repository's coherent established format when one exists. Otherwise use a Keep a Changelog 1.1.0-compatible structure:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- <new user- or maintainer-relevant capability>

### Changed
- <meaningful update to existing behavior>

### Fixed
- <observable problem that was corrected>

## [1.2.0] - 2026-08-26
```

Keep the newest version first and use ISO `YYYY-MM-DD` release dates. Use `Unreleased` until the project's release workflow supplies a version; never invent one. When a release version and date are confirmed, move its entries into the versioned section and retain a fresh `Unreleased` section at the top. Group only non-empty entries under `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, or `Security` as applicable.

Write each entry as a concise outcome and, when useful, its effect on users or maintainers. Do not dump Git commits, enumerate implementation files, expose internal AURAE identifiers, or include technical detail that is unnecessary to understand what changed. Mention breaking changes, deprecations, removals, and security-relevant changes clearly without disclosing unsafe exploit detail.

For multiple repositories, maintain the changelog owned by each changed repository. Also describe the integrated product effect in the consumer/root changelog when it is notable there, without copying dependency implementation details. Do not modify the changelog of a read-only external dependency.

When adopting a repository with no changelog and usable local Git history, propose reconstruction from Git. Treat the result as a curated historical draft rather than a transcription, disclose incomplete history, and obtain user confirmation before publishing reconstructed entries. Without usable history, propose a future-facing changelog and never fabricate historical versions or dates.

## Local-only state

Ensure every repository where the agent creates or executes temporary material contains a `.scratchpad/` directory at its root. Ensure the repository-root `.gitignore` contains this explicit anchored rule:

```gitignore
/.scratchpad/
```

Verify the rule with Git rather than trusting text alone. If `.scratchpad/` is already tracked, adding the ignore rule is insufficient: preserve its files, inform the user, and ask one question before removing those paths from Git tracking.

For the narrowly scoped pre-Git interview export in [pause-and-resume.md](pause-and-resume.md), Git may be unavailable or the repository not yet initialized. Still add the explicit root ignore rule, but record Git-ignore/tracking verification as pending rather than claiming it passed. Do not initialize Git merely to perform this check. Verify it once Git storage becomes available, before promoting the export or publishing anything; until then the export remains non-sensitive, provisional and local-only.

Use `.scratchpad/` as the only repository-local location for disposable AI work. Keep it understandable through stable high-level categories, scope ordinary work directly by AURA, and add a Workstream level only when the AURA actually uses optional Workstreams:

```text
.scratchpad/
├── ABOUT.md
├── aurae/
│   ├── shared/
│   │   ├── harnesses/
│   │   ├── fixtures/
│   │   └── cache/
│   └── auras/
│       └── <aura-id>/
│           ├── scripts/
│           ├── captures/
│           ├── artifacts/
│           ├── logs/
│           ├── tmp/
│           └── workstreams/
│               └── <workstream-id>/
└── other clearly named task areas when needed
```

Create only the directories needed for current work. Put a short `ABOUT.md` in a new scratchpad explaining that the directory is local, disposable, ignored by Git, and not required to build or operate the project.

Suitable scratchpad content includes:

- generated test and diagnostic scripts;
- screenshots, videos, browser traces, and temporary exports;
- experiments, calculations, and transformed fixtures;
- temporary worktrees, Harness runtime files, and generated adapters;
- raw logs, caches, locks, sessions, and intermediate artifacts.

Never store canonical AURAE memory, accepted specifications, required product code, durable decisions, or the only copy of acceptance evidence in `.scratchpad/`. Before accepting an AURA, promote any indispensable result to its durable project, AURAE, or evidence location and record its manifest.

Do not place secrets in `.scratchpad/` merely because it is ignored. Avoid persisting them; when unavoidable, follow the project's secret-handling policy and minimize lifetime.

If the agent only reads an external repository and lacks authority to modify it, keep related temporary work under the consumer/root repository's scratchpad instead of changing the external repository.

Synchronize only compact manifests, hashes, portable references, stable Harness contracts, accepted engineering knowledge, evidence summaries, and explicitly requested non-sensitive pause/handoff context under [pause-and-resume.md](pause-and-resume.md). The durable resume point belongs in Git-backed metadata, not disposable scratch; provisional interview content remains labeled as such and never becomes accepted intent merely through synchronization.

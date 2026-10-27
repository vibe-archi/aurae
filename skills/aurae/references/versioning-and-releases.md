# AURAE versioning and releases

## Purpose

Version the methodology and its operational components independently so that an updated skill does not imply a project-memory migration. Keep project Workspaces agent-agnostic: persist the Workspace format and Storage Contract versions, not the brand or release of the agent that wrote them.

## Current release manifest

This block is the canonical release manifest for the skill package:

```yaml
release_status: unreleased
release_date: null
aurae_methodology: 1.5.0
agent_skill: 1.18.3
skill_bundle_format: 1.0.0
workspace_format: 1.0.0
storage_contract: 1.0.0
workspace_conformance_validator: 1.1.1
git_storage_harness: 1.0.1
git_merge_harness: 1.0.1
```

The source markers in [workspace-validator-source.md](workspace-validator-source.md) and [git-storage-source.md](git-storage-source.md) must match their manifest entries. Their usage contracts remain in [workspace-conformance.md](workspace-conformance.md) and [git-storage-harness.md](git-storage-harness.md). The format descriptor documented in [workspace-and-artifacts.md](workspace-and-artifacts.md) must match `workspace_format` and `storage_contract`. The `format_version`, `agent_skill`, and `aurae_methodology` values in `aurae-skill.yaml` must match `skill_bundle_format` and the corresponding release entries above.

Skill 1.18.3 retains methodology 1.5.0 and clarifies task-descriptive naming for lanes and subagents: at most four meaningful words, an optional numeric suffix and consistent readable labels in conversation. Host IDs and canonical identifiers remain unchanged. Apply the [release impact ledger](upgrade.md#release-impact-ledger) without restarting delegates or interrupting the current phase. Workspace, Storage Contract, bundle format, validator and Git helpers are unchanged; no migration, helper refresh or historical rewriting is required.

The build still generates [vendor.md](../vendor.md) from a reviewed distribution profile before hashing the complete bundle. Install the built package, not the incomplete manufacturing source. Local-first upgrade and the absence of online release checking are unchanged.

The `git_merge_harness` entry must match the source marker in [git-merge-source.md](git-merge-source.md); its usage contract is [git-merge-harness.md](git-merge-harness.md). Load and qualify the companion only when divergent integration is needed.

## Component meanings

- `aurae_methodology` versions the meaning of AURA phases, gates, authority, risk, assurance, and protected decisions.
- `agent_skill` versions this distributable skill package and its instructions within its established distribution. It is the single package-version field; private distributions use their own series and record the known upstream base in `vendor.md` rather than duplicating a client-version field. Versions from different distributions are not directly ordered.
- `skill_bundle_format` versions the manifest and validation contract for the installable snapshot stored on `aurae/skill`.
- `workspace_format` versions the current native write shape and interpretation of persisted `.aurae` memory.
- `storage_contract` versions the required behavior for reads, isolated writes, synchronization, concurrency, and recovery.
- `workspace_conformance_validator` versions the transparent validator source and its result contract.
- `git_storage_harness` versions the transparent Git Storage Harness source and its command contract.
- `git_merge_harness` versions the optional transparent divergent-integration companion and its plan/review/publication contract.

Do not persist `agent_skill`, validator, or Harness versions in ordinary project artifacts. They describe the tool package used for an operation, not product truth. Record them only in the skill recovery manifest, local Harness manifests, or compact evidence when exact tooling materially affects an assurance claim.

## Version policy

Use `MAJOR.MINOR.PATCH` consistently, including before AURAE 1.0:

- increment `PATCH` for compatible corrections, clarifications, or implementation fixes;
- increment `MINOR` for additive behavior that existing valid consumers can safely preserve or ignore;
- increment `MAJOR` when an existing consumer cannot safely interpret, preserve, or execute the changed contract.

Version each component according to what actually changed:

- changing skill wording or routing increments `agent_skill`, but not the Workspace format;
- changing `vendor.md` or packaged client instructions also increments that distribution's `agent_skill` and regenerates the exhaustive manifest; profile identity is part of the package, not an unchecked overlay;
- changing the recovery bundle's required manifest fields, path rules, digest rules, or installability contract increments `skill_bundle_format`;
- changing a persisted field or its meaning increments `workspace_format`;
- changing compare-and-swap, isolation, synchronization, or recovery guarantees increments `storage_contract`;
- changing validator or Harness source behavior increments its own version;
- changing the meaning of a phase, gate, authority decision, or assurance outcome increments `aurae_methodology`.

A single release may increment several components. Do not keep versions numerically aligned merely for convenience.

## Compatibility and migration

A newer `agent_skill` alone never justifies migration. Negotiate the stored `workspace_format` and `storage_contract` through [format-compatibility-and-migrations.md](format-compatibility-and-migrations.md). Preserve old AURAs in their accepted form and migrate only the live frontier when strictly necessary.

Use [upgrade.md](upgrade.md) for `/AURAE upgrade`, installed-package freshness checks, and phase-safe impact handling. Its release impact ledger must describe every existing-project consequence introduced by a new component version.

An updated validator or Harness may be used with an unchanged Workspace format when its contract remains compatible. A breaking validator or Harness contract requires the corresponding major version change and must not silently replace an older required implementation during an in-progress operation.

## Release procedure

Before publishing or handing off a new skill release:

1. classify which components changed and why;
2. update only their manifest entries and matching source markers or format descriptors;
3. add a concise entry to the release impact ledger for every change that can affect existing work;
4. confirm that no unnecessary Workspace migration is implied;
5. validate the skill structure and all local Markdown links;
6. materialize and run the validator, core Storage and merge companion self-tests from their Markdown sources;
7. generate and validate `aurae-skill.yaml`, including the exhaustive package file list and SHA-256 digests for `vendor.md` and any packaged client references; retain client adaptations and verify the intended distribution instead of replacing them with official defaults;
8. preserve the release through an immutable Git commit or package revision, then publish project recovery snapshots through the isolated `aurae/skill` procedure; never rewrite an already shared release.

Keep release notes concise and focused on behavior, compatibility, and migration impact. Git history may carry detailed file changes; do not duplicate it into project AURAE memory.

# Git storage and synchronization

## Contents

1. Storage model
2. Portable skill recovery branch
3. Storage Contract
4. Repository initialization
5. Harness construction
6. Safety preflight
7. Compatibility and migration writes
8. Canonical and contribution writes
9. Remote synchronization
10. Conflicts and concurrency
11. Specification synchronization
12. Handoff through a clone
13. Recovery
14. Changelog reconstruction

## Storage model

Use Git as a versioned metadata store without placing `.aurae/` in the developer's normal working tree.

Default refs:

```text
refs/heads/aurae/meta
refs/heads/aurae/aura/<aura-id>
refs/heads/aurae/ws/<aura-id>/<workstream-id>  # optional
refs/heads/aurae/skill                          # installable recovery bundle
```

Create `aurae/meta` as a metadata-only root when possible. Its tree contains `.aurae/` and no application files. Use the AURA contribution ref for ordinary branch-specific progress. Create Workstream refs only for coordinated lanes inside one AURA. Base every contribution ref on the exact canonical metadata commit from which it started. Keep `aurae/skill` independent: it is a distribution and recovery snapshot, not canonical project memory.

Do not assume a remote. A local `aurae/meta` branch is a valid standalone store. When a remote exists and the user permits synchronization, use ordinary branch fetch and push semantics.

This reference's metadata-integration and disjoint auto-merge rules do not authorize merging product code. Never merge `aurae/*` into a product branch. For code, follow [the integration contract](collaborative-workstreams-and-git-reconciliation.md#integrate-and-close-safely): obtain user consent for the contribution and destination, independently of delivery acceptance or metadata synchronization.

## Portable skill recovery branch

Use `refs/heads/aurae/skill` to preserve a complete, installable snapshot of the AURAE skill selected for the project. It exists so an agent that lacks AURAE can recover the package once, install it locally when the host supports that, and avoid rereading the branch during ordinary work.

The branch tree contains only the skill package:

```text
aurae-skill.yaml
SKILL.md
vendor.md        # distribution profile in 1.17.0+; older bundles may lack it
agents/          # when present in the package
references/
scripts/         # only when present in a future package
assets/          # when present in the selected package
```

`aurae-skill.yaml` is required and uses `format: aurae-skill-bundle` with `format_version`, `name`, `agent_skill`, `aurae_methodology`, `entrypoint`, and an exhaustive `files` list. Each file entry contains a safe relative `path` and the lowercase SHA-256 digest of the exact Git blob bytes stored for that path. Exclude the manifest itself from `files`; reject absolute paths, `..`, symlinks, missing or extra regular files, digest mismatches, an entrypoint other than `SKILL.md`, or a package name other than `aurae`. Never include project state, credentials, machine paths, caches, or temporary output.

Include the selected distribution's complete `vendor.md` and packaged client references in that existing inventory; no new bundle format is needed. A profile is not an unhashed override. Preserve private adaptations on recovery and upgrade, and never replace a client's bundle with an official package solely because its number is larger. Older valid bundles without a profile remain recoverable; establish their actual lineage under [upgrade.md](upgrade.md) rather than assuming they are official. Profile URLs are informational and do not trigger remote release checking.

Create or update the bundle without checking it out in the developer's working tree:

1. Materialize the active package into a new isolated directory under ignored `.scratchpad/` and generate its manifest.
2. Validate the complete candidate before creating a commit.
3. Commit it through an isolated index, object operation, or detached temporary worktree. Disable content filters or otherwise prove that the final tree's blob bytes match the manifest; line-ending conversion must not invalidate the bundle across platforms.
4. Update the local ref only when its observed value still matches the expected base. Fast-forward when possible; if the ref diverged, preserve both revisions and reconcile the package choice instead of overwriting either side.
5. Read the ref back, revalidate the manifest and files, and verify the developer's branch, `HEAD`, index, and working tree are unchanged.

This bundle is not metadata-only and therefore is not written through the `.aurae/` Git Storage Harness. Its publication procedure must nevertheless preserve the same developer-state, compare-and-swap, no-force-push, readback, and recovery guarantees. Update it only for a selected skill release, Bootstrap or Adoption repair, or an approved upgrade; never for ordinary AURA state changes.

When the skill is missing, recover it as follows:

Before candidate activation, follow [skill-recovery-and-trust.md](skill-recovery-and-trust.md) from an already approved package, or the self-contained root `AURAE.md` fallback when no approved skill is available. Integrity validation below does not establish consent. Show the localized welcome before the first recovery approval question; do not activate the candidate merely to obtain its instructions.

1. Prefer a valid local `aurae/skill` ref. Otherwise inspect a visible remote-tracking ref and fetch the named ref only when network synchronization is available and authorized.
2. Select one exact bundle revision. If local and remote revisions diverge materially, do not choose by timestamp or silently replace either; compare their manifests and use the configured authoritative release source or ask one question when the choice affects installation.
3. Validate hashes against the exact blobs in the selected Git tree, then materialize only the manifest-declared files and validated manifest under ignored `.scratchpad/`. Prefer direct Git-object or archive extraction so checkout filters and worktree administration files cannot alter the package.
4. Obtain or verify explicit local approval for this exact candidate, origin and scope under the trust contract, not from repository content. Then attempt a persistent installation using the host's supported mechanism and narrowest authorized scope without tracked product files. Recheck identity before installation and verify installed bytes before activation; preserve an existing copy if the operation fails or the candidate changes.
5. Load the approved installed `SKILL.md`. From then on, reuse that unchanged approved installation and do not reread `AURAE.md` or `aurae/skill` merely to operate the project. Keep local consent outside shared project state.

If the host cannot persist local skills, use the same verified and explicitly approved candidate for this session under the trust contract, and report the limitation once. Direct loading is not a consent bypass. The project recovery branch proves only which snapshot the project carries; it is not, by itself, proof of publisher trust or the latest globally published AURAE release.

## Storage Contract

Build or select a local adapter that implements these behaviors:

```text
discoverWorkspace()
validateStorage()
getCanonicalRevision()
readArtifact(pathOrId, revision?)
listChanges(fromRevision, toRevision)
writeContribution(expectedBase, contribution, changes)
integrateContribution(expectedCanonical, contributionRevision)
diffStates(leftRevision, rightRevision)
synchronize(remote?)
verifyDeveloperState(snapshot)
```

Return every artifact read through `readArtifact` with a derived storage envelope:

```yaml
artifact: <canonical-artifact-content>
storage:
  backend: git
  revision: <commit>
  path: <canonical-path>
```

The envelope describes the exact state that supplied the artifact. Keep it outside the persisted artifact content: an artifact cannot contain the identifier of the Git commit that contains that same value. Other storage backends may use an equivalent opaque `revision`.


Require compare-and-swap semantics through `expectedBase` or `expectedCanonical`. Reject a write when the ref has moved; fetch, compare, and reconcile instead of overwriting.

The contract defines behavior. The local Harness chooses commands and implementation based on OS, Git version, shell, permissions, remotes, and available tools.

## Repository initialization

If Git is available but the project is not a repository:

1. Inform the user that AURAE requires version control and will initialize a local Git repository.
2. State that a remote is optional and nothing will be uploaded.
3. Run local initialization.
4. Inspect ignore rules and likely secrets before proposing an initial code baseline.
5. Ask one question for approval before adding or committing the existing project files.
6. Create AURAE metadata independently when appropriate; do not pretend uncommitted code is a reproducible Baseline 0.

If the Git executable is absent, do not install it silently. Ask one approval question after explaining why it is required.

## Harness construction

Prefer the smallest safe implementation supported by the environment:

1. A temporary Git worktree dedicated to the metadata ref.
2. A temporary Git index plus plumbing commands when validated and justified.
3. An existing project adapter that passes the full conformance preflight.

Never access the metadata branch by switching the developer's working tree.

For a temporary worktree:

- prefer a clearly scoped path under the repository's ignored `.scratchpad/aurae/` tree when Git supports and validates that layout; otherwise use an approved external temporary directory and record the exception locally;
- record its exact path locally;
- attach only the metadata ref or a detached expected base;
- perform edits and commits there;
- verify the resulting tree contains only the intended metadata changes;
- remove the worktree through Git after validating the target path;
- run `git worktree prune` only when appropriate and non-destructive.

For the reference `publish`/`cas` paths, use detached candidates. Immediately before updating a ref, reject it if checked out in any registered worktree; do not detach, remove or alter that worktree automatically. An alternative adapter using an attached metadata worktree must explicitly qualify equivalent preservation behavior instead of bypassing this guard. The same pre-publication check applies to the recovery-bundle ref.

Do not distribute a project-specific Harness as a methodology invariant. Reuse, adapt, or construct it locally. Store its stable contract and compact manifest in AURAE memory; keep machine-specific implementation and secrets local unless the project intentionally versions a reusable engineering tool.

The preferred MVP Git adapter's usage contract is in [git-storage-harness.md](git-storage-harness.md), which links to its complete readable Markdown source. Read the usage contract completely before building, adapting, testing, or using the adapter, and follow its source-inspection and qualified-local-copy reuse rules. Materialize it under ignored `.scratchpad/`, never mark it executable, and accept it only after its self-test passes. It uses a normal checkout in an isolated detached worktree and deliberately forbids `--no-checkout`.

The Workspace conformance validator's usage and result contract is in [workspace-conformance.md](workspace-conformance.md), which links to its complete readable Markdown source. Read the contract completely and follow its source-inspection and qualified-local-copy reuse rules. Materialize or adapt it under ignored `.scratchpad/`, invoke it through an available runtime without marking it executable, and accept it only after its self-test passes. Do not install a missing runtime or parser dependency without user approval.

## Safety preflight

Capture this developer-state snapshot before each metadata mutation:

```text
repository root
current symbolic branch or detached state
HEAD commit
index tree or staged diff fingerprint
working tree status fingerprint
actual content fingerprint of tracked and nonignored untracked files
active worktrees
canonical AURAE ref
remote AURAE ref when configured
```

Validate before use:

- Git repository ownership and resolved paths;
- required Git commands and version behavior;
- read access to canonical metadata;
- temporary location writability;
- ability to create and remove a disposable metadata worktree or index;
- commit identity availability, using repository-local configuration if explicitly supplied;
- remote permissions only when synchronization is requested.

After every operation, prove that the original branch, `HEAD`, index fingerprint, status, and actual file-content fingerprint are unchanged. Git status alone cannot detect a second edit to an already modified file. Exclude ignored disposable scratch content; snapshot each affected repository separately. Check again immediately before publication. On a mismatch, stop the affected metadata operation and preserve both states; do not automatically restore the developer's files.

Forbid the Harness from invoking destructive commands in the developer's working tree, including `reset`, `clean`, automatic stashing, and checkout-based branch replacement.

## Compatibility and migration writes

Read [format-compatibility-and-migrations.md](format-compatibility-and-migrations.md) before a format migration. Treat the canonical ref and its Git history as immutable evidence: never amend, rebase, replace, or force-push earlier AURAE commits to make them look current.

Prepare a migration from an exact canonical base in isolated ignored storage. Produce the smallest semantic diff that makes the affected active AURAs' live state usable. Leave completed historical AURAs and their baselines, decisions, evidence, identifiers, paths, and wording unchanged. Update a shared index or referenced artifact only when the live frontier cannot remain coherent without it.

Validate the candidate and its preserved references before a compare-and-swap canonical commit. If preparation or validation fails, leave the canonical ref unchanged. Record a new protected Decision Record only when the migration changes the meaning of protected intent, risk, acceptance, authority, or a gate; ordinary lossless compatibility work needs no ceremonial artifact beyond its Git commit and useful provenance.

## Canonical and contribution writes

Write accepted shared knowledge to `aurae/meta` through a controlled integration operation. Write ordinary branch-specific proposals and progress to `aurae/aura/<aura-id>`. Use `aurae/ws/<aura-id>/<workstream-id>` only when that AURA explicitly uses coordinated Workstreams. Initial Bootstrap/Adoption state and its pre-cycle checkpoint use the canonical ref through the same isolated validation and compare-and-swap workflow; no invented cycle or contribution ref is required.

Use this sequence:

1. Read the expected canonical commit.
2. Create or refresh a contribution from that exact commit.
3. Apply only the intended `.aurae/` changes.
4. Run the self-tested Workspace conformance Harness against the complete candidate state and its exact preceding Git tree. Use raw blob exports and write-mode validation, not a snapshot result. Stop on blocking conformance errors, and separately verify semantic gates, capabilities, actual code references, and changed-path scope that structural validation cannot prove.
5. Commit with the AURA identifier and the Workstream identifier only when one exists. For pre-cycle entry work, identify the real project and entry operation instead.
6. Re-read the canonical ref.
7. If unchanged, integrate through a fast-forward or reviewed metadata merge.
8. If changed, stop integration and reconcile.
9. Verify developer state.

Bind validation to both exact trees, preserve the report locally, and verify the final committed blobs still match before publication. The ordinary isolated write path must start from the ref's expected value. For a linear contribution with several commits, validate every consecutive parent/child transition and use the reference Harness's ordered `steps` receipt for compare-and-swap integration. A final-state-only comparison must not invent a skipped transition or turn historical acceptance into a new decision.

For divergent two-parent integration, prefer the packaged [git-merge-harness.md](git-merge-harness.md) companion rather than the linear `cas` or a newly invented script. It preserves the common base and both histories, validates transitions along their actual parents, composes disjoint artifacts and navigation, checks the combined state and binds the reviewed merge to exact parents/tree before compare-and-swap. The agent still compares the intended changes semantically and verifies authority, evidence and integrated code. New lifecycle changes or decisions belong in normal validated source writes, not a manually edited merge candidate. Unsupported multi-parent histories or semantic resolutions require a reviewed adapter providing these same guarantees. Preserve original transitions instead of fabricating a cumulative `last_transition`; retain immutable baselines/decisions and serialize integrated product acceptance. If no path proves the guarantees, stop only integration and keep both contributions available. Never use a snapshot report or unvalidated plumbing to bypass a blocker.

Protect compare-and-swap records:

- each AURA's phase transition and lifecycle state;
- the shared active- and planned-AURA indexes and dependency relations;
- each accepted Specification Baseline;
- each final assurance decision;
- the serialized integrated Product Baseline.

Allow contributors to add proposed risks, decisions, deviations, Oracle definitions, direct AURA results, and optional Workstream results without directly publishing those protected records. Unrelated contribution refs may advance concurrently; shared canonical integration still uses compare-and-swap.

## Remote synchronization

Treat synchronization as optional.

When no remote exists, keep local refs and report that collaboration backup is not configured. Do not present this as an error.

When a remote exists:

1. Fetch the canonical AURAE ref without changing the working tree.
2. Compare local canonical, remote canonical, and each contribution's expected base.
3. Fast-forward when local is strictly behind and no unpublished local canonical commit exists.
4. Push only a descendant of the observed remote ref.
5. Push ordinary contributions under their AURA refs when review is required; push optional Workstream refs only for coordinated lanes.
6. Never force-push.
7. Read back the remote ref and verify the expected commit.

Do not assume the code branch and metadata branch are pushed together. Record both commit identities and verify their availability before publishing a cross-repository baseline.

Synchronize `aurae/skill` independently from project memory. Publish it only after validating the bundle and when remote synchronization is authorized. A clone-ready handoff for a recipient who may not already have AURAE requires the selected bundle ref to be pushed and read back, but receiving that ref never authorizes automatic replacement of an existing local installation.

## Conflicts and concurrency

Use four mechanisms to reduce conflicts:

- stable files whose revision is carried by Git;
- separate AURA contribution refs, with optional Workstream refs only when needed;
- append or merge proposals before publishing accepted state;
- compare-and-swap integration for lifecycle indexes, gates, and baselines.

On divergence:

1. Preserve both states.
2. Compute a semantic diff of affected artifacts.
3. Trace every material conflicting side to its visible Git commits. Identify the contributor with the author name and email recorded by Git. Mention the committer or merge provenance only when it changes the interpretation, such as a merge, cherry-pick, bot, or delegated commit.
4. Auto-merge only disjoint changes that preserve identifiers, references, and scope.
5. Never auto-resolve conflicting requirements, decisions, risk acceptance, Oracle expectations, or gate outcomes.
6. Before asking for judgment, present a compact conflict brief: the affected subject, the meaning of each competing change, the contributor or contributors Git associates with each side, and any attribution uncertainty. For a complex conflict, group information by decision-relevant issue rather than dumping commits or raw diffs.
7. Ask one decision question that lets the user compare further, contact an associated contributor, or resolve the conflict now when they hold the required authority.

Present attribution directly, for example `Jean (jean.k@company.com): changed the session-expiration rule`. If history is shallow, rewritten, merged, shared by several contributors, or otherwise inconclusive, state the uncertainty in one short sentence and show a short commit or AURA reference only when needed to disambiguate. Do not add routine disclaimers about identity or authority to the conflict message. Check authority separately and mention it only when resolving the conflict would make a protected decision.
Avoid frequently regenerated monolithic indexes. Rebuild disposable indexes after integration rather than merging them as sources of truth.

## Specification synchronization

Bind every AURA contribution to its immutable Specification Baseline identifier and the storage revision returned when that baseline was read. Bind each optional Workstream to the same AURA baseline plus its own expected contribution base. In the Git backend, these derived revisions are exact metadata commits.

When a new Specification Baseline is accepted for an AURA:

1. Identify its direct contribution and optional Workstreams based on the superseded baseline.
2. Evaluate impact through changed requirements, contracts, invariants, risks, and Oracles.
3. Mark affected contribution state `stale`.
4. Do not let it integrate until the AURA acknowledges or rebases onto the new specification.
5. Permit unaffected concurrent AURAs and unaffected Workstreams to continue when traceability proves no impact.

Developers propose specification changes from the AURA contribution or an optional Workstream. They do not silently rewrite the accepted baseline. Return only the affected AURA to Understand for validation and synchronization.

## Handoff through a clone

A canonical local checkpoint is enough to resume on the same machine. Do not claim that another person can resume from a fresh clone until the required shared refs are available from the remote they will clone.

For `/AURAE pause`, first apply [pause-and-resume.md](pause-and-resume.md): save the actual interrupted interview/work context as a durable, explicitly provisional handoff note. The command includes committing that metadata and using already authorized synchronization, not implicitly staging or committing product files. Keep local success distinct from remote availability, including when a push fails or code needed for resume is still uncommitted.

When the user chooses a clone-based handoff:

1. Persist the handoff checkpoint to canonical `aurae/meta` without changing the developer's working tree.
2. Identify every code commit, AURAE commit, relevant active or planned AURA, contribution ref, and selected `aurae/skill` bundle required by the next action.
3. If synchronization has not already been authorized, explain briefly that handoff requires publishing these refs and ask one approval question before pushing.
4. Push only descendant refs through the normal remote-synchronization rules; never force-push.
5. Read back the remote refs and verify that every required code and canonical AURAE commit is reachable. Push an AURA contribution ref when unfinished direct state is required; push a Workstream ref only for an unfinished coordinated lane. Push and verify `aurae/skill` when the handoff must remain recoverable without a preinstalled skill.
6. Report whether the checkpoint is `local_only` or `clone_ready`. Do not describe local-only state as transferable through an ordinary clone.

On the receiving clone, use an already approved unchanged AURAE skill when available. Otherwise follow root `AURAE.md` to show the welcome before recovery consent, then install or session-load the exact verified and locally approved bundle. Another contributor's approval does not transfer through the clone. Then discover and validate the remote AURAE ref without switching the developer's working tree. Load the canonical checkpoint, select the AURA from explicit intent or unambiguous Git binding, verify referenced code commits and repositories, classify missing or divergent state, and present only that AURA's phase, gate readiness, important blockers, relevant dependencies, and next action. For unfinished initial entry with no cycle, discover `.aurae/resume.md` and resume its actual Bootstrap/Adoption stage instead of requiring an AURA. Never require the previous conversation transcript or restart Adoption merely for skill recovery.

If no remote exists, preserve the local checkpoint and state that clone-based handoff is not configured. Do not create a remote or upload data without user approval.

## Recovery

On interruption, orphaned temporary worktree, failed push, or partial metadata operation:

1. Preserve the developer's working tree.
2. Inspect refs and reflogs before changing anything.
3. Determine whether the new metadata commit exists and whether any canonical ref points to it.
4. Resume or discard only the isolated temporary operation.
5. Never delete an ambiguous ref or worktree without resolving its exact path and ownership.
6. Record a recovery note if the event affects confidence in the AURAE state.
7. Re-run the full Harness preflight before continuing.

## Changelog reconstruction

Attempt reconstruction only after the user approves it and usable local Git history exists. Use read-only Git inspection and preserve the developer's branch, `HEAD`, index, and working tree.

1. Inspect local release tags, annotated tag messages, version files, merge history, commit subjects, and existing release notes.
2. Prefer tag-to-tag ranges and confirmed release dates. Treat commit messages as evidence, not ready-made changelog entries.
3. Group notable outcomes by version using the project's established versioning policy. Do not invent versions, dates, behavior, or impact.
4. Corroborate claimed outcomes with available code, tests, version files, release material, or documentation. Do not infer user-visible behavior from a commit subject alone.
5. Draft the reconstructed sections under `.scratchpad/` and mark uncertain or incomplete periods explicitly.
6. Summarize additions, fixes, changes, deprecations, removals, and security-relevant outcomes in human-readable language.
7. Present the draft's coverage and limitations briefly, then ask one confirmation question before writing historical entries to the root `CHANGELOG.md`.

If the path is not a repository, history is shallow, tags are absent, or relevant commits are unavailable, report the limitation and record whether reconstruction is impossible or partial. Do not fetch a remote solely for reconstruction without user approval. Never use an unedited `git log` as the changelog, invent historical entries, or imply that incomplete evidence is complete.

# Git Storage Harness reference

## Purpose

This reference distributes transparent, cross-platform source for the MVP Git Storage Harness without shipping an executable, binary, encoded payload, or project-specific tool. The normative contract remains [git-storage-and-sync.md](git-storage-and-sync.md); this source is the preferred implementation when Python 3.9 or newer and Git are already available.

The implementation uses only the Python standard library and Git. It invokes no shell or network command itself and never switches the developer's working tree, uses `--no-checkout`, rewrites history, or force-pushes. Candidate metadata is checked out normally in a detached worktree below the repository's ignored `.scratchpad/`. Hooks and fsmonitor are disabled for its Git invocations. Inspect inherited Git attributes and filters before using a checkout-based adapter: externally configured filters may execute commands and are not made safe merely by this source. Use a validated filter-free object/index adapter when necessary.

## Local materialization protocol

1. Read this reference and [git-storage-and-sync.md](git-storage-and-sync.md) completely.
2. Confirm that Git and a suitable Python runtime already exist. Do not install either without user approval.
3. Reuse a qualified local copy under the identity checks in Reference source below. Otherwise read the linked source completely and copy only its block into `.scratchpad/aurae/shared/harnesses/git-storage/aurae_git_storage.py`. Do not mark it executable.
4. Run `python aurae_git_storage.py self-test --scratch-root <an-existing-.scratchpad-path>` for first use or after a source, adaptation, runtime or Git change; an unchanged qualified copy may reuse its matching passing self-test record. Repository preflight and each operation's safety checks remain mandatory.
5. Reject or adapt the local Harness when the self-test fails. Keep failed self-test material for diagnosis.
6. Run `snapshot` before the first repository operation. The mutation commands also capture and later verify this state.
7. Use `export --repo <repo> --revision <base-commit> --destination <new-scratch-directory>` to obtain the exact previous `.aurae/` tree. Run the compatible Workspace conformance validator on the candidate with `--previous-workspace <export/.aurae>` (or `--new-workspace` for bootstrap) and save its JSON result inside this operation's scratch root.
8. Run `seal`, then `commit`, `publish`, and finally `cleanup`. Do not publish an unsealed candidate.
9. If publication fails, preserve the candidate and its state file for recovery; never retry against a moved ref without reconciling.

The Harness creates no remote and performs no fetch or push. Apply the approval and synchronization rules in [git-storage-and-sync.md](git-storage-and-sync.md) for remote operations.

## Operation mapping

The commands map to the Storage Contract as follows:

- `snapshot` and `cleanup` implement developer-state preservation checks;
- `read` and `changes` provide exact revision reads and diffs;
- `export` materializes exact Git blob bytes in a new isolated scratch directory; use it for validation, not the text-oriented `read` output;
- `open` creates a candidate from an exact metadata commit;
- `bootstrap` creates an unpublished candidate from an empty metadata-only root;
- `seal` requires a successful write-mode conformance result bound to the exact candidate and previous tree;
- `commit` creates a detached metadata commit without running Git commit hooks;
- `publish` updates the intended AURAE ref through compare-and-swap;
- `cas` fast-forwards an existing AURAE ref through a fully validated linear chain, using `--validation-result`.

For a new direct AURA contribution ref, use the canonical commit as `--base`, `refs/heads/aurae/aura/<aura-id>` as `--publish-ref`, and `absent` as `--expected-ref`. Use the same mapping with an optional Workstream ref only for a coordinated lane. For an existing ref, `--base` must equal `--expected-ref`; use validated `cas` to integrate an already advanced contribution instead of skipping its intermediate commits through `open`.

Harness `1.0.1` is paired with validator `1.1.1` or a tested compatible adaptation. Its local sealing/CAS protocol replaces `0.1.0`; the persisted Workspace and Storage Contract remain `1.0.0`. Refresh materialized helpers together at a safe checkpoint, rerun their self-tests, and preserve any in-progress old candidate rather than deleting it or silently interpreting its state file with the new engine.

For a single-commit fast-forward, pass its validator report directly. For several commits, export and validate each child against its immediate parent, then store `{"steps": [<first-report>, <next-report>, ...]}` in an ignored local JSON file. `cas` verifies each report against the exact Git parent/child blobs and requires a complete, contiguous, non-merge chain from `--expected` to `--new`. Missing, reordered, or stale reports cannot publish. Never replace `last_transition` with a fictional cumulative transition.

This core provides local isolated writes and linear fast-forwards. On divergence, use the packaged [git-merge-harness.md](git-merge-harness.md) companion for reviewed, deterministic two-parent integration; it validates both actual histories, rebuilds navigation and publishes through compare-and-swap. The companion also checks compatible earlier merges in those histories. Unsupported semantic resolutions still follow the reviewed-adapter procedure in [git-storage-and-sync.md](git-storage-and-sync.md). Neither helper is a remote client. Do not force publication or substitute a read-only snapshot report.

Developer preservation includes the actual bytes of tracked and nonignored untracked regular files, as well as branch, HEAD, index, status, symlink targets, and worktree registration. Ignored scratch content is excluded; nested repositories require their own snapshots. Check before sealing, committing, and publishing, and again after cleanup. A mismatch stops the operation without restoring or discarding the developer's changes.

Both `publish` and linear `cas` refuse a publication ref checked out in any registered worktree before updating it. Compare ref names case-insensitively for this guard, conservatively including case-only variants on case-sensitive systems. Symbolic publication aliases are also rejected rather than followed: use a direct metadata ref. Preserve the ref, attached worktree and candidate; resolve that checkout separately without automatically switching or removing user work. Revalidate the current repository state before retrying. Prefer detached candidates; do not rely on a post-publication preservation error to protect an attached metadata branch.

Sealing records the report digest and both tree fingerprints. Commit creation must produce the same blob bytes even with line-ending settings or attributes; otherwise preserve the candidate and adapt the storage path. Publication rechecks the committed bytes and the unchanged report. This is stale-proof protection for a cooperating local workflow, not authentication against malicious report or state-file forgery.

## Reference source

The complete unchanged implementation and its self-tests are in [git-storage-source.md](git-storage-source.md). Read that source completely before first materialization, adaptation, or use after a source change.

For routine use, reuse a previously inspected local copy only after confirming it matches the packaged source (or its reviewed adaptation) and has a passing self-test for the current runtime/parser/Git environment. If identity, provenance, test status, or context is missing, reload the source and rerun the self-test. A readable source split never permits skipping validation or weakening the operational contract.


## Adaptation rules

An adaptation may change language, argument syntax, or local runtime, but it must preserve:

- ordinary checkout only inside the isolated candidate worktree;
- strict containment below an ignored scratch root;
- metadata-only trees and changes;
- a successful write-mode conformance result sealed to the exact candidate and previous tree, with the committed bytes and report rechecked before publication;
- compare-and-swap publication with readback;
- no network activity, force operation, developer-tree branch switch, reset, clean, or stash;
- developer branch, `HEAD`, index, actual tracked/nonignored file content, status, and worktree-list verification before publication and after cleanup;
- a self-test that covers bootstrap, exact reads, normal candidate checkout, commit creation, conflict rejection, publication, cleanup, and unchanged developer state.

Do not weaken a failed safety check to make a platform pass. Preserve the isolated candidate and report a Harness limitation. Use an approved external temporary root only through an explicit adaptation that provides equivalent path-containment and cleanup guarantees.

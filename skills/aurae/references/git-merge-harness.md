# Divergent metadata integration

## When to use

Use this companion to [git-storage-harness.md](git-storage-harness.md) when two project-memory commits have diverged. It provides an integrated, local, two-parent merge path, without a project-specific script, developer checkout, history rewrite or remote operation. Ordinary writes and linear fast-forwards keep using the existing Storage Harness.

Use the same `plan`/`publish` interface when a local ref is behind a history containing a compatible merge. It returns `mode: advance`, validates that history and advances to the existing commit; it does not create a redundant merge. `mode: composition` identifies a new divergent two-parent integration. In a review's `parents` field, retain the two exact input tips returned by `plan` in their given order; an advance receipt separately reports the existing commit's actual parents.

Read this contract and [git-storage-and-sync.md](git-storage-and-sync.md) before the operation. The Workspace schemas, lifecycle, authority and content-trust rules remain unchanged. This tool merges project state, not product code or the `aurae/skill` bundle. A local metadata merge never proves code integration, product acceptance or clone readiness.

## What is automated

- Validate every new commit on both source histories against its actual parent. Do not compare only the tips or fabricate a cumulative phase transition.
- Merge disjoint artifacts and identical changes; retain exact source bytes and Git modes outside the derived navigation file. Deletes versus modifications and concurrent edits of the same artifact are conflicts, even if a textual Git merge would succeed.
- Rebuild unordered active-cycle and condition-alert indexes from their artifacts. Merge handoffs by cycle. Preserve planned relative ordering; incompatible concurrent orders are conflicts. Preserve unknown navigation fields through conservative three-way comparison. Navigation timestamps may use the latest source timestamp with an explicit timezone; they never choose a decision or establish authority.
- Validate the composed Workspace and preserve accepted baselines and decision meaning from both parents. Product-state acceptance remains serialized: conflicting accepted product pointers cannot be selected automatically.
- Bind the semantic review to both exact parents and the candidate fingerprint, then recompute history validation and the merge before publication. Create a real two-parent commit, compare-and-swap the expected local ref and verify its value and the developer state.
- Revalidate earlier deterministic two-parent merges encountered in the relevant history, so a successful first merge does not prevent the next one.

The composition check is not an ordinary write-mode receipt. Its legitimacy comes from actual source-transition validation plus a reproducible merge containing no invented lifecycle changes or new decisions. Do not pass its snapshot/composition report to the linear `seal` or `cas` commands.

## Qualification and local use

The companion is versioned separately as `git_merge_harness 1.0.0`, paired with Storage `1.0.0` and Validator `1.1.0`. Existing helper interfaces and in-progress candidates do not change. Python 3.9+, Git and the validator's safe YAML parser must already be available; installing them requires normal permission.

Read [git-merge-source.md](git-merge-source.md) completely before first materialization, adaptation or use after a source change. Materialize only its marked Python block into `.scratchpad/aurae/shared/harnesses/git-storage/aurae_git_merge.py`. Load only the separately inspected, approved, matching local Storage and validator source copies. These are executable inputs, not untrusted paths from project data. Follow the existing helper identity checks; the version string alone does not establish identity.

On first use or after any source/runtime/parser/Git change, run the new self-test as well as the existing helper tests. A matching qualified copy can reuse its passing record; repository preflight still runs for every operation. The self-test creates and retains a bounded disposable repository and JSON result under the supplied scratch directory. Keep its evidence local; it must not become a project dependency.

```text
python aurae_git_merge.py --storage-source <qualified-storage.py> --validator-source <qualified-validator.py> --scratch-root <ignored-scratch> self-test

python aurae_git_merge.py --storage-source <qualified-storage.py> --validator-source <qualified-validator.py> --repo <repo> --scratch-root <ignored-scratch> plan --ours <exact-local-tip> --theirs <exact-other-tip> --publish-ref refs/heads/aurae/meta
```

`plan` writes raw-blob exports, a candidate and a `plan.json` in a new ignored operation directory. It does not update a ref. Use its returned paths and full commit identifiers, not placeholders or a guessed temporary location. Source commits remain available. No checkout, filters, hooks, external merge driver or shell is used for composition; no fetch/push is performed. Inherited `GIT_*` overrides other than the neutralized pager, replacement/grafted or shallow history, active partial/promisor repositories, unsafe paths, symlinks and submodules stop this path rather than weaken its checks. Git commit signing is disabled for this reference path; a project that requires signed metadata needs a reviewed signing adapter, not a bypass of its policy. Inspect an environment mismatch and use an isolated clean invocation; never modify the developer's global configuration to make the test pass. Missing objects require a separately authorized history retrieval, not an implicit lazy fetch.

## Review and publication

Review the actual differences and their meaning: scope/overlap, requirements and Oracle expectations, evidence applicability, specification freshness, decision authority, dependency effects and the exact integrated product baseline. Use the existing risk-proportionate review rules. No additional human confirmation is needed for an authorized, unambiguous disjoint merge; ask only when a real decision or permission is missing.

After that review passes, create a local review JSON next to the plan:

```json
{
  "result": "pass",
  "reviewer": "<actual reviewing participant>",
  "summary": "<concise evidence-backed conclusion covering scope, dependencies, decisions and product state>",
  "parents": ["<exact first parent>", "<exact second parent>"],
  "candidate_sha256": "<value returned by plan>"
}
```

Do not prefill `pass`, claim an independent reviewer who did not participate, or infer user approval from this file. Like the existing validation receipts, it coordinates a cooperating local workflow, not an authenticated permission system. Protected new decisions still require their normal canonical records and authority; the merge review cannot manufacture them. If source state needs a correction or new acceptance, perform the normal validated contribution workflow first and regenerate the plan.

```text
python aurae_git_merge.py --storage-source <qualified-storage.py> --validator-source <qualified-validator.py> --repo <repo> --scratch-root <ignored-scratch> publish --plan <returned-plan.json> --review <review.json> --message "Integrate <cycle identifiers>"
```

Publication recomputes the merge and all relevant source transitions, verifies the exact reviewed candidate and untouched developer state, and updates only the requested ref if it still equals the first input tip and is not checked out in any registered worktree. It never integrates a manually edited candidate or trusts supplied PASS reports instead of validation. The result is `published_local`. Remote synchronization remains separately authorized through the normal fetch/compare/push/readback protocol.

## Conflict and recovery behavior

A blocked plan retains `blocked.json`, validated history evidence and source exports. Each material artifact conflict identifies the two commits and their visible authors' names/emails; committer data is also available when provenance needs clarification. Translate these facts into the existing compact conflict brief, not a raw JSON dump. The helper cannot determine authority or explain business intent from Git attribution alone; the agent supplies that review. If the cause is structural, report the affected artifact and consequence. Block only integration, not unrelated work.

Concurrent meanings, accepted product branches, unsupported historical manual resolutions, unrelated roots, octopus merges and multiple merge bases require focused reconciliation under the existing contract. Preserve both histories. Resolve at their actual source states through normal validated changes when possible; otherwise use a reviewed adapter that proves the same guarantees. Do not promise this deterministic path can resolve arbitrary semantic conflicts, rewrite accepted baselines to make them equal, delete a competing contribution, or retry by forcing a ref. A planned candidate is diagnostic/review material, not an editor-based conflict-resolution escape hatch.

If the target ref or developer files move, keep the old plan and review, re-read the situation, then make a fresh plan and review only the new delta. Do not restore, stash, reset or discard the developer's work. An interrupted publication leaves `publication.json` with the prepared commit before compare-and-swap: inspect the actual ref and commit parents/tree to distinguish unpublished from already published. Never blindly repeat publication or delete ambiguous state. This object-based path registers no worktree; optional later scratch cleanup must remain path-checked and local.

The distributed self-test covers ordinary divergence, multi-step phase history, a subsequent merge, exact bytes, contributor attribution, rejected conflicts, stale publication, edited candidate, local-work preservation and invalid intermediate history. Qualify other platforms and runtime versions by running the same tests there; a passing Windows run is not a claim of Linux/macOS qualification.

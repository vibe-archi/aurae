# Collaborative AURAs, optional workstreams, and Git reconciliation

## Purpose

Keep parallel development understandable without turning AURAE into project-management ceremony. An AURA is the risk-aware envelope for one coherent contribution that can be integrated and assured as a unit. Git remains the source of truth for code that actually exists; AURAE preserves intent, risk, specification, coordination, and assurance.

Use this contract when naming or dispatching lanes/subagents, whenever product code changes, several AURAs may be active, or visible Git history may contain contributions made without AURAE.

## Core invariants

- Allow several active AURAs in one logical Workspace.
- A direct AURA normally represents one coherent repository contribution and needs no Workstream.
- A Workstream is an optional implementation lane inside one AURA, not a mandatory wrapper around a branch, prompt, fix, file, or commit.
- If a lane can be integrated and assured independently, model it as another AURA and declare any dependency.
- Git history is the source of truth for actual code contributions. AURAE records what the contribution intends, which baseline it uses, what risks it carries, and whether it is assured.
- Use configured Git author and committer identity for attribution automatically. Git identity is not proof of authority for specifications, risk acceptance, assurance, or release.
- Before asking a user to resolve a complex collaboration conflict, identify each material side with the contributor name and email visible in Git, summarize the differing changes, and disclose uncertain attribution briefly. This lets the recipient decide whether to contact the contributor or proceed.
- Contributors who do not use AURAE remain first-class contributors. Reconcile their visible commits without requiring them to adopt the methodology.
- AURAE can inspect only locally visible commits and refs. Never claim that no parallel work exists on another machine or an unfetched remote.
- An assured AURA covers only the exact repository commits pinned by its Product Baseline.

## Name lanes and subagents

Before dispatching a lane or subagent, choose a short name that describes its actual task, including for read-only probes, documentation and independent verification. Apply this to every delegation, whether or not it uses a formal Workstream; naming alone does not create one.

- Use one to four meaningful words, preferably lowercase and hyphen-separated: `probe-srv-data`, `code-fix-bugs`, `arch-write-docs`, or `verify-login-errors`. Favor an action and its concrete subject over a generic role or obscure abbreviation.
- Add a short numeric suffix only when needed to distinguish otherwise identical names, for example `probe-srv-data-2`. The suffix does not count toward the four-word limit; it supplements rather than replaces the task description. Keep names unambiguous among active delegates.
- Set the host's task/name/label field when available. If it requires another syntax, adapt the separator (for example `probe_srv_data`) without losing meaning. If the host assigns a fixed opaque ID, keep a local association with the readable name and continue using the real ID for tool calls.
- Reuse the readable name in progress, questions, results and handoffs: “`probe-srv-data` is finishing its checks”, not “S4 is finishing”; “`arch-write-docs` needs clarification”, not “B8 has a question”. Pass the name to the delegate so its reports use it consistently. Keep ordinary sentences in the user's language and avoid extra status messages merely to announce names.
- Keep the name stable for the same task. For an already-running delegate with an opaque name, use a readable display alias without restarting it. Never rename canonical AURA/Workstream IDs, Git refs or historical records to enforce this presentation rule. Transient host-ID mappings remain local; this adds no required schema field or registry.

## Bind the AURA to the contribution

Before the first product-code change during Realize:

1. Load the selected AURA, its accepted Specification Baseline, its starting Product Baseline, and the latest visible active AURAs.
2. Select the AURA from explicit user intent or an unambiguous branch or commit binding. Ask one question only when several active AURAs remain plausible.
3. For the ordinary case, set `implementation.mode: direct`, bind one repository and exact base commit, and record the branch as a mutable hint when useful.
4. Read the configured Git identity and use it for resulting commits without asking the developer to repeat it.
5. Publish branch-specific AURAE progress to the AURA contribution ref when collaborative synchronization is available and authorized.
6. Keep machine, session, execution, and transient ownership details local under `.scratchpad/`.

An AURA may begin Assess or Understand before a code branch exists. The branch becomes relevant when Realize begins. Renaming, rebasing, or deleting a branch never changes the AURA identity; update exact commit bindings and preserve Git history.

Read-only inspection, explanation, and temporary experimentation inside `.scratchpad/` do not require an implementation binding.

## Coordinate concurrent AURAs

Before activation, implementation, integration, and assurance, compare the affected repositories, contracts, interfaces, invariants, data, risks, tests, and integration paths of visible active AURAs.

Classify the relationship:

- **independent** — each AURA can proceed and be assured without relying on the other;
- **dependent** — record `depends_on` when the required outcome must exist before activation; keep only that dependent AURA planned until the prerequisite has an acceptable Product Baseline and no applicable condition blocks activation;
- **coordinated overlap** — both may proceed, but define the integration order and revalidation points;
- **conflicting** — block only the affected work until intent or ownership is clarified.

Do not create a global lock merely because another AURA is active. When another AURA lands first, reconcile the candidate against the latest Product Baseline. Continue after focused revalidation when the contribution remains compatible; return the affected AURA to Understand when behavior, assumptions, risks, interfaces, Oracles, or acceptance outcomes materially changed.

## Use Workstreams only when needed

Create optional Workstreams only when one AURA needs several implementation lanes that must converge before one assurance decision, for example:

- coordinated changes across several repositories;
- frontend and backend branches that cannot deliver the accepted behavior separately;
- several contributors working on inseparable parts of one integration candidate; or
- an explicit sequencing boundary inside one cross-repository product decision.

Keep `implementation.mode: coordinated` for such an AURA, leave its direct repository and commit fields null, and bind every Workstream to the same accepted Specification Baseline.

Do not create a Workstream for the ordinary one-AURA/one-branch case. Do not split by prompt, commit, file, or small follow-up. If a proposed Workstream gains its own specification, material risk, Oracles, independent integration outcome, or assurance decision, promote it to an AURA.

Synchronize optional Workstreams only at meaningful points: creation, material scope or dependency change, overlap discovery, pause, blocker, handoff, readiness, integration, or rejection.

## Reconcile visible Git history

At meaningful synchronization, integration, assurance, and closure points:

1. Identify the AURA's starting Product Baseline, direct base commit or Workstream bases, and intended integration target.
2. Refresh relevant remote refs only when network synchronization is available and already authorized.
3. Inspect visible commits and merges since the baseline and since the last reconciled target.
4. Match commits to direct AURA bindings and optional Workstreams, then isolate unmatched changes.
5. Group coherent unmatched commits by ancestry, branch, author or committer, affected scope, and observed purpose. Keep the classification provisional and local until understood.
6. Inspect the actual diff and behavior. Git attribution helps discovery but never replaces technical review. When a material conflict requires user judgment, trace and present the contributor provenance of each competing side before asking the decision question.
7. If an unmatched contribution is independently integrable and assurable, create or link an AURA. If it is an inseparable lane of an existing coordinated AURA, link or create an optional Workstream. Never imply that its author used AURAE.
8. Reassess affected risks, tests, documentation, interfaces, contracts, baselines, and integration order.
9. If a contribution contradicts or materially extends accepted behavior, block only the affected AURA and return it to Understand before integration or assurance.

A branch name alone is only a signal. Local-only commits on another machine and unfetched remote refs remain invisible.

## Integrate and close safely

### Integrate before independent verification

For several branches or implementation lanes in one cycle, or parallel cycles contributing to the same delivery, assemble all included code into a stable integration candidate before starting the final independent-agent campaign. A collection of separate branch passes is not verification of their combination. Each unmerged branch receives its normal technical, unit and relevant behavioral checks from its host Builder only; do not dispatch an independent agent per branch and call that final assurance.

This does not waive repository-mandated reviews or CI; distinguish them from AURAE's final campaign. For a single contribution already based on the observed target, including a verified fast-forward candidate, its exact commit may be the combined candidate; do not manufacture a merge commit merely for ceremony.

Identify the bounded delivery set and integration order from intended behavior and material overlap. Include every contribution needed for its acceptance, including relevant manual changes, resolve conflicts, and run host checks on the combined result. For parallel cycles, a shared campaign may supply evidence to each included cycle's claims while their specifications, decisions and closure records remain distinct. Do not wait for unrelated cycles outside that delivery set or invent a global lock.

The candidate must contain the actual merged code, not a proposed merge, aggregate branch reports, or mocked integration. It may be prepared as an isolated Git merge result without advancing a destination product branch, so final verification does not require shipping unverified work to `main` or `dev`. Bind all inputs, the intended target snapshot and the combined result to exact commits; record cross-repository commits and actual consumer dependency wiring when one tree cannot contain the delivery. An isolated candidate is not a claim that product integration or promotion has already occurred. If preparing it would modify a product branch, obtain the consent below first.

Hold the candidate fixed during the campaign. If fixes or another included contribution change it, the host reassembles and checks the combination before independent re-verification. A changed source/target or conflict resolution invalidates affected evidence; an older branch pass cannot establish the new result. Reuse unaffected observations only with explicit candidate/environment provenance. After authorized landing, reconcile the actual target against the tested candidate and independently reverify material differences; never carry a pass across a later merge by assumption. If initial assembly is outstanding, retain Realize / ready or the actual blocker. For an already-active Assure campaign, preserve its phase and follow the normal rework/upgrade rules; never claim a final integrated verdict on separate branches.

### Confirm product-code integration

Acceptance of a delivery and permission to merge its code are distinct decisions. Passing tests, an assurance recommendation, "accept and close", a branch convention, or generic Auto delegation never authorizes a product-branch merge. This applies to fast-forwards, squash integration, cherry-picks used to land the contribution, and automated/PR merges as well as ordinary merge commits. Synchronizing `aurae/*` metadata is a separate operation and grants no code-integration permission.

Before changing a destination code branch, ask one focused question offering the relevant existing target branches, another user-specified branch, or postponement. Resolve this during candidate assembly if that assembly needs a product-branch mutation; otherwise resolve it during acceptance before landing the tested candidate. Name the source contribution and intended destination; distinguish local integration from a remote/PR action when relevant. Recommend a target only from established project practice. Never silently choose `main`, the default branch, or the currently checked-out branch. An earlier target preference is not permission to merge now. Reuse an explicit, still-applicable user instruction authorizing this contribution's merge into that target; do not repeat an already answered permission question.

Keep this question separate from the protected assurance decision; a positive answer to either is not an answer to the other. If the user explicitly gives both decisions together, preserve each within its stated scope. A target-and-consent question can come first at the acceptance boundary so the exact integration result can be prepared and verified before final assurance acceptance. If the user already accepted the tested delivery, record that acceptance without inventing permission to merge or repeating an unchanged decision.

Inspect the actual target ref and repository contribution rules. If the name is ambiguous or the branch is absent, clarify the destination or obtain explicit creation intent rather than silently normalizing a name, creating a branch, or falling back to `main`. Honor required PR/review/CI paths; permission to merge locally is not permission to push, create/merge a remote PR, release, deploy, delete branches, or bypass protections. Ask only for the missing authority needed by the chosen path.

Auto retains this boundary: only an explicit applicable user merge authorization resolves it, not a self-interview recommendation. Under `blocked-only`, ask when integration is the next necessary action; under `none`, leave the contribution unmerged and report the missing authorization as a resumable next action without a question. Preserve any explicit instruction to confirm again at acceptance.

### Verify the actual result and target

Prepare and verify the stable combined candidate as described above, without advancing the destination branch just to run tests. Bind the chosen source, observed destination and resulting candidate to exact commits. Before landing an accepted delivery, reconcile visible concurrent changes and verify that required evidence and the acceptance decision cover the actual result. Explicitly authorized preparatory integration remains unassured and must not be represented as acceptance, release or deployment. A different target, changed source/target, conflict resolution, or squash/rebase result requires focused reconciliation and current evidence, not an assumption that an earlier branch test covers it. Reuse still-valid evidence with explicit provenance; repeat only affected checks, preserving the normal risk and independence floor. Return to Understand only for a material change of intent or risk, not merely a branch choice.

Immediately before an authorized merge, recheck source and destination refs, the approval's scope, and any required checks. If they changed, stop that mutation, reassess and renew consent when the contribution, target or material consequences changed; do not apply stale approval to a different result. Preserve unrelated work and use the repository's approved integration mechanism. Read back the resulting ref before claiming success. If code integration succeeded but metadata publication failed, retain the actual result and resume recording it; do not merge again or undo product code automatically.

### Deferral, baselines and closure

No phase, cycle identity, or assurance level depends on the target being `main`. Integration into `dev`, `release/...`, or another user-confirmed target can complete the cycle when its baseline and other closure gates are satisfied. Later promotion to `main` is not implied: it requires its own authorization and assessment of the actual combined changes; a distinct contribution or material additional work is framed by the normal cycle rules.

If merging is postponed or its permission is unresolved, retain the tested candidate, any scoped acceptance, and the next action. Keep `active / assure / ready` while the evidence remains sufficient; use `in_progress` for remaining verification or `blocked` for a real blocking condition. Do not finalize `assured` or `conditionally_assured`, advance `current.yaml.project_baseline`, mark a Workstream integrated into the destination, or imply that the destination contains the work merely because the delivery was accepted. This does not block unrelated cycles; a dependent cycle still needs its genuinely required integrated baseline. An explicit abandonment uses the existing clean-closure/rejection rules, not a fictional successful merge.

If read-only reconciliation proves the contribution is already present in the intended target (for example through a manual merge), record and verify the actual result without asking permission to repeat a completed operation. If work was intentionally performed directly on that target, there may be no separate merge: explain this briefly and apply normal candidate/acceptance gates. Neither case grants unrelated commit, push or publication permissions.

Persist the source/candidate, destination repository and ref, observed target commit, user consent or deferral with its source, relevant acceptance/evidence references, actual integration result and next action in existing decision/narrative context and the scoped handoff. Use exact commits for truth and branch names for destination intent; a renamed branch is not an interchangeable destination. No new required schema field or lifecycle status is introduced. The structural validator cannot establish merge consent or actual target membership; verify those separately. On resume, reuse applicable decisions, inspect whether integration already happened, and never convert a pause, "resume", or silence into merge permission.

### Closure checks

For successful delivery (`assured` or `conditionally_assured`):

- account for every visible change in that AURA's candidate integration range;
- require its direct result commit to be known, or every optional Workstream to be `integrated` or `rejected` with the reason preserved;
- do not block closure merely because an unrelated AURA remains active;
- reconcile against the latest accepted Product Baseline and classify every relevant concurrent change;
- rerun affected gates and risk-selected positive and negative tests after the integrated candidate is stable;
- when independent-agent verification is selected or required, perform it on that combined candidate, not on still-separate branches; account for material differences introduced by later landing;
- apply the confirmation and deferral rules above; candidate preparation alone is not an authorized merge into a product branch;
- record `closure.stable_baseline` and publish a Product Baseline that pins each repository's exact accepted integration commit; and
- immediately before canonical publication, verify that the target code refs and AURAE refs still match the assessed state.

For abandonment or rejection (`closed` or `rejected`), do not use successful-delivery checks to manufacture an accepted result:

- preserve the explicit reason and protected clean-closure or rejection decision;
- account for the actual direct contribution or each coordinated lane: retained unmerged work, excluded/rejected work, and anything already integrated; do not delete code or mark an unmerged lane integrated to settle the cycle;
- reference the existing reproducible AS-IS Baseline 0 or accepted Product Baseline that the project actually retains in `closure.stable_baseline`; leave `current.yaml.project_baseline` unchanged when no accepted product change occurred;
- before Realize, `implementation.mode: none`, no result commit and no accepted Specification Baseline are legitimate; no Assure campaign or new Product Baseline is required merely to stop;
- if work already changed an integration target or live environment, verify the state actually left behind. A pointer to an older baseline is not a restoration. Obtain the necessary authority and qualify recovery before claiming a clean stable outcome; preserve the unresolved work as a blocker otherwise.

Both paths preserve unrelated cycles, accepted history, outstanding obligations and the developer's work. Closing a cycle does not waive an existing condition or authorize a merge, revert, deployment or branch deletion.

If newer commits appear after closure, keep the completed AURA valid only for its recorded Product Baseline. The newer project state requires reconciliation or another AURA; never rewrite the completed history.

## Record shapes

A direct AURA uses its own implementation binding:

```yaml
id: AURA-session-stability-8f2c9a41
kind: aura
status: active
phase: realize
specification_baseline: BL-session-specification-4a12f3c9
depends_on: []
implementation:
  mode: direct
  repository: REP-application-7b91de20
  base_code_commit: 7e41c2a
  branch_hint: fix/session-stability
  result_code_commit: null
workstreams: []
```

A coordinated AURA may reference normal Workstream records:

```yaml
id: WS-session-api-2c619a7e
aura: AURA-session-stability-8f2c9a41
repository: REP-api-41fd82c0
status: active
based_on_specification: BL-session-specification-4a12f3c9
base_code_commit: 6bc91ef
branch_hint: feature/session-api
result_code_commit: null
```

Git already preserves author and committer attribution. Show that visible name and email when they help resolve a conflict, but do not copy them into redundant contributor records in canonical AURAE memory.

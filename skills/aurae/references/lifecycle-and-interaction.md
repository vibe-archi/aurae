# Cycle lifecycle, risk, and authority

Read before creating, preparing, activating, resuming, transitioning, assuring or closing a cycle, classifying risk, or making a protected decision. This file owns phase gates, state transitions, risk classification, and decision authority. Read [interviews.md](interviews.md) for question selection/cadence, [project-entry.md](project-entry.md) for Bootstrap/Adoption, [status-views-and-voice.md](status-views-and-voice.md) for rendering, and [oracles-capabilities-and-assurance.md](oracles-capabilities-and-assurance.md) before designing or running verification.

## AURA phase contracts

### Phase-entry visibility and ordering

Every active cycle must be visible before phase-specific work begins. For cycle creation, resume, and every accepted transition:

1. satisfy the applicable entry conditions or previous phase gate;
2. persist the canonical state with the selected AURA, current `phase`, and `phase_state`;
3. render the compact vertical AURA progress view from that state;
4. only then perform work specific to the current phase.

Do not replace the progress view with prose such as “preparing Realize” or reveal a transition only after commands have run. Auto mode changes who answers routine questions; it does not make phases silent. Even when Assess or Understand is brief and internally resolved, show the cycle at creation and show each accepted phase transition before beginning the next phase's work.

Repository, Git, runtime, storage, and documentation inspection genuinely required to establish Bootstrap or Adoption may occur before the first cycle. Do not hide contribution-specific feasibility probes, Oracle preparation, implementation, or assurance activity inside that pre-cycle work. On resume, load and validate the recorded state first, show the resumed phase, then continue its work.

### Assess

Entry: a proposed objective, problem, risk, or meaningful change.

Infer the request's reach from the stated intent and available project evidence. Do not ask the user to label it as minor, major, local, architectural, or another methodology category. A bounded correction or behavior adjustment remains inside its AURA; broader impact changes the depth and scope of the same interview.

Produce enough to answer:

- Why does this AURA exist?
- What outcome would matter?
- What may be affected, including shared architecture, data contracts, public interfaces, documentation, or other active AURAs?
- What could go wrong?
- Is a separate AURA justified?

Exit only when scope, priority, important risks, and the next commitment are clear enough. Outcomes: `proceed`, `reconsider`, or `stop`. Mark the phase `ready` only for `proceed`; keep it in progress for reconsideration, or close the AURA cleanly for `stop`.

### Understand

Entry: an accepted Assess outcome.

Produce enough to answer:

- What observable behavior is intended?
- What constraints and invariants apply?
- What interfaces or decisions must change?
- Which fundamental specifications or project-facing documents, if any, must reflect the result?
- How will the intended behavior and regressions be verified?
- What capabilities are needed to build and verify it?
- Are those capabilities ready?

Allow inspection, experiments, prototypes isolated from production, fixtures, Oracle preparation, and Harness construction. Forbid intentional product behavior change.

Exit only with:

- user-validated intent;
- explicit remaining assumptions;
- defined acceptance outcomes and relevant Oracles;
- acceptable unresolved uncertainty;
- validated Capability Readiness;
- an accepted Specification Baseline.

In Auto mode, preserve the same exit conditions. Treat the user's explicit source instruction as validation of the behavior it clearly states, then resolve the remaining interview queue internally through evidence-backed recommendations and bounded delegation. Auto mode suppresses the request for routine answers; it does not suppress the questions, Specification Baseline, Capability Readiness, or Understand gate.

As the interview converges, infer whether the result remains bounded or materially affects shared foundations. For a bounded bug fix or behavior adjustment, keep the interview and documentation work within the smallest useful scope. When architecture, data models or contracts, public interfaces, cross-scope behavior, or assumptions used by other AURAs are materially affected, include the relevant fundamental specifications and project-facing documentation in this AURA's acceptance outcomes. Before leaving Understand, tell the user briefly which artifacts must be updated and which other AURAs, if any, require focused revalidation. Do not burden unaffected AURAs or documents.

Revise the Project Intent Baseline only when the business direction, global objectives, or project boundaries change. Architecture or data evolution alone normally updates the affected specifications and documentation, then becomes part of the next accepted Product Baseline.

If the user chooses handoff before all these conditions are met, remain in Understand and record the unmet conditions. If they choose handoff after all conditions are met, set the phase state to `ready` without performing the transition on their behalf.

### Realize

Entry: an accepted Specification Baseline and ready capabilities.

Implement the intended change, run technical checks continuously, and record deviations. For the ordinary case, bind the AURA directly to one coherent repository contribution through its exact base commit, optional branch hint, and eventual result commit. The branch name aids discovery; commits and baselines carry durable truth.

Do not create a workstream for a direct contribution. Create optional workstreams only when the same AURA needs several coordinated implementation lanes—such as multiple repositories, branches, or contributors—that cannot be integrated and assured independently. If a lane can be integrated and assured on its own, represent it as another AURA and declare any dependency instead. Bind every direct implementation and optional workstream to the exact Specification Baseline and code base it uses.

Maintain the root `CHANGELOG.md` of every writable repository changed by the AURA. Add notable user- or maintainer-relevant additions, fixes, and changes to `Unreleased` as coherent outcomes become clear. Write for humans, not as a commit diary: omit low-level implementation mechanics, internal AURAE bookkeeping, and routine changes with no meaningful effect.

Update every fundamental specification and project-facing architecture, data, interface, contributor, installation, or user document included in the accepted Specification Baseline as part of the same AURA contribution. Reuse the project's coherent documentation structure. Do not create a separate documentation AURA merely because the implementation has broad impact.

If a discovery changes intended behavior, a public contract, an invariant, or material risk, stop only the affected realization, return that AURA to Understand, revise its specification, invalidate its candidate, and resynchronize any optional workstreams.

Exit when the direct implementation or coordinated workstreams form one coherent candidate that is integrated or ready for integration, technical checks pass at the chosen rigor, changelogs reflect the notable outcomes, and deviations are resolved or explicitly carried into Assure. Then set the Realize phase state to `ready`.

### Assure

Entry: a coherent realization candidate and healthy verification capabilities. For final independent-agent verification, the actual combined candidate must already be stable under [integration before independent verification](collaborative-workstreams-and-git-reconciliation.md#integrate-before-independent-verification); host checks on individual branches do not satisfy this condition. Isolated candidate assembly need not advance `main`, `dev` or another product branch.

Before entering or delegating this phase, follow [assurance-participation.md](assurance-participation.md): ask whether the human, an independent agent, or both should verify, unless an explicit applicable choice or valid Auto delegation already resolves it. Explain that personal testing comes with concise build/run instructions and expected scenarios. Preserve Realize / ready until the arrangement and entry conditions are established; the choice does not accept the product.

Human verification may be primary rather than merely supplemental when its coverage and actual independence meet the assurance contract. Provide the human's test instructions at entry, record each participant's results and awaited feedback, and notify the user when an independent agent finishes. Keep Assure / in_progress while selected verification or feedback remains incomplete; one participant's pass never completes the other participant's work.

Run Harness preflight first. Execute new Oracles, impact-selected regression Oracles, and critical baseline Oracles. Evaluate evidence against the Specification Baseline and residual risks. When fundamental specifications or documentation changed, verify their material claims against the realized behavior, contracts, and repository evidence. Confirm that affected concurrent AURAs were revalidated or marked stale while unrelated AURAs remained undisturbed.

Apply [independent-agent verification discipline](oracles-capabilities-and-assurance.md#independent-agent-verification-discipline) to findings and rework. The verifier reports; the host routes unrelated issues, obtains approval for scope expansion and owns repairs. Repeated serious failures after repair require causal analysis before another repair batch, using existing rework transitions rather than an endless Assure loop. Persistent problems may lead to a human-approved conditional outcome and scoped stabilization cycles only when the conditional-assurance gates remain satisfied.

Before requesting the protected assurance decision, present a concise decision brief in this order:

1. **Delivered outcome** — explain what was implemented and what the product, user, operator, or maintainer can now do or rely on. Prefer observable behavior and meaningful contracts over files, commands, or internal mechanisms.
2. **Verification** — summarize the evidence that most directly supports that outcome, including important positive and negative behavior. Test counts and coverage may support the summary, but must not lead it.
3. **Material residual risks** — for each material risk, state its level and plain-language name, what could still happen, the condition or environment in which it could happen, the credible consequence, why uncertainty remains, and the current containment or limitation when one exists. Never present only a label such as `initialization: medium`.
4. **Qualified scope** — state the environments, variants, integrations, recovery modes, or other boundaries that were and were not qualified when they matter to the decision.
5. **Personal test path** — for a functionally testable result, retain the concise validated instructions provided to selected human testers, without asking them to repeat completed work. If no human testing was selected, offer an optional personal check before deciding. Show the necessary build/install/start/open actions, normally two to four main steps, and observable expected results; link fuller validated instructions when necessary. Use a safe authorized environment. If no responsible path exists, state the limitation when relevant instead of inventing one.
6. **Proposed outcome** — propose acceptance, conditional acceptance, rework, or rejection from the delivered outcome, evidence, residual risks, and qualified scope, not from passing test counts alone. Present any justified recommendation in the standard question format after the choices.

Treat a candidate as functionally testable when the user can safely exercise a meaningful delivered behavior through a supported interface such as an application, UI, CLI, API, service, package, library example, or local workflow without reconstructing the verifier's Harness. Do not force the section for an internal-only change with no distinct behavior the user can reasonably exercise.

Keep the delivered outcome short—normally two to six bullets for a complex contribution—and show only decision-relevant evidence and risks. Keep the optional self-test path to one concise command or action plus at most four short steps; do not turn the decision brief into installation documentation. Validate the shown path against the realized candidate and qualified environment before presenting it. Keep commit hashes, storage revisions, exhaustive test lists, and raw logs in canonical state and reveal them only when requested or necessary to disambiguate the candidate. Do not request acceptance until the decision maker can understand both what they would accept and the practical meaning of every material residual risk.

Only after the selected assurance work and feedback are complete may the human decide from the assurance brief or request an additional optional personal test. This later choice is not acceptance, rejection, rework, conditional assurance, or a new independence level. Keep active / assure / ready while existing evidence remains sufficient, preserving the candidate, instructions and pending decision. These extra observations are supplemental; investigate unexpected behavior and revalidate affected evidence if the candidate or environment changed. Do not apply this ready-state exception to human feedback already required by the selected participation plan: that remains in progress until accounted for.

Outcomes:

- `accept` — establish a new baseline;
- `conditional_accept` — establish a reproducible conditional Product Baseline, create Condition Records, clear active work, and set the AURA to `conditionally_assured`;
- `rework` — return to the relevant phase;
- `reject` — do not integrate the outcome; retain learning and evidence.

`test_first` is an interaction choice, not an assurance outcome. It leaves the protected decision pending and preserves `active / assure / ready`.

Acceptance does not authorize a code merge. Resolve the source, user-confirmed destination and merge permission separately under [the integration contract](collaborative-workstreams-and-git-reconciliation.md#integrate-and-close-safely), before any preparatory product-branch merge or, for an isolated test candidate, before landing it during acceptance. `main` has no special lifecycle status: another approved target can supply the accepted integrated Product Baseline. If merging is deferred, retain the tested candidate and any scoped acceptance without finalizing the cycle or advancing the integrated baseline. Recheck evidence against the actual integration result before final closure; a branch choice alone does not restart the cycle.

Do not let the Builder self-approve beyond the independence permitted by risk. Follow the protected-decision and authority contract below.

Set the Assure phase state to ready only when all selected participants' reports are accounted for, the evidence, residual-risk assessment and required authority are sufficient for the final decision, the decision brief can be supported from canonical state, and the personal test instructions shown have been validated or carry an explicit material limitation. A missing required verification capability or result prevents readiness; an unavailable optional extra check does not erase otherwise sufficient evidence.

## Canonical AURA state machine

A stable starting/product state means the reproducible AS-IS Baseline 0 before the first delivery, or a later accepted Product Baseline. It is distinct from the Project Intent Baseline, which describes direction and cannot stand in for code. Bootstrap establishes that starting state through [project entry](project-entry.md#bootstrap), not through a fictitious first assurance decision.

Represent lifecycle with four separate fields:

- `status` — `planned`, `active`, `conditionally_assured`, `assured`, `rejected`, or `closed`;
- `phase` — `assess`, `understand`, `realize`, `assure`, or `null`;
- `phase_state` — `in_progress`, `ready`, `blocked`, or `null`;
- `blockers` — the unresolved conditions preventing progress in the current phase.

Enforce these combinations:

- a `planned` AURA has `phase: null`, `phase_state: null`, `implementation.mode: none`, no workstream, and may keep dependencies plus preparation blockers under `preparation.activation_blockers`;
- an `active` AURA has exactly one non-null phase and a non-null phase state;
- `phase_state: blocked` requires at least one blocker and preserves both `status: active` and the current phase; `blockers` must be empty for every other phase state;
- `phase_state: ready` means the current phase exit conditions are satisfied but the next transition has not yet occurred;
- `conditionally_assured` is non-active, has `phase: null`, `phase_state: null`, no active phase blockers, a closure decision, a stable conditional Product Baseline, and at least one Condition Record; all conditions may be resolved while the final protected assurance decision is still pending;
- `assured`, `rejected`, and `closed` are terminal statuses with `phase: null`, `phase_state: null`, no unresolved active blocker, and a recorded closure decision and stable product baseline.

Allow only these forward transitions:

```text
planned              -> active / assess / in_progress
planned              -> closed | rejected  # protected cancellation, no implementation
assess / ready       -> active / understand / in_progress
understand / ready   -> active / realize / in_progress
realize / ready      -> active / assure / in_progress
assure / ready       -> conditionally_assured | assured | rejected
conditionally_assured -> assured
active               -> closed
```

Allow an active phase to move to `blocked` without losing its position. After every blocker is cleared, restore `in_progress` or `ready` according to the gate evidence. A material specification change found in Realize returns explicitly to Understand. An Assure `rework` decision may return to the relevant earlier phase with `phase_state: in_progress`. In both cases invalidate downstream readiness and the affected realization candidate, preserve accepted baselines, and publish a superseding Specification Baseline when needed rather than editing the earlier baseline.

Validate these gates before a transition:

- activation requires a stable current Product Baseline, satisfied declared dependencies, no applicable blocking condition, preparation revalidation when applicable, and classification of material overlap with other active AURAs; unrelated active AURAs do not block activation;
- Assess to Understand requires confirmed scope, material-risk classification, assurance level, and a `proceed` decision;
- Understand to Realize requires user-validated intent, an accepted Specification Baseline, defined verification, ready capabilities, and identification of any fundamental specifications, project-facing documents, or concurrent AURAs materially affected by the change;
- Realize to Assure requires a coherent realization candidate, required technical checks, current changelogs, updated in-scope fundamental documentation, and resolved or explicit deviations;
- final independent-agent dispatch additionally requires the stable combined candidate, accepted scope/comparison baseline and report-only finding/rework boundaries; separate branch checks cannot substitute for this campaign;
- Assure may move to an outcome only after the Harness is healthy, required Oracle results and evidence are current, residual risks have dispositions, achieved independence is recorded, the decision maker has received an understandable delivered-outcome and residual-risk brief, and the protected assurance Decision Record is effective.
- A conditional outcome additionally requires at least one complete Condition Record with a responsible owner, due trigger, declared blocks, and verifiable completion criteria.
- `conditionally_assured -> assured` requires every condition to be `satisfied`, validly `waived`, or validly `superseded` by obligations that are themselves resolved, plus a new protected assurance decision and a superseding Product Baseline. The code commits may stay identical, but the evidence and decision must be current.
- clean closure requires an explicit reason and decision, an accounted direct contribution or settled optional workstreams, and the reproducible starting or accepted product baseline actually left behind. It does not require a new Product Baseline, a result commit or passing Assure for abandoned work; follow the distinct [closure checks](collaborative-workstreams-and-git-reconciliation.md#closure-checks).

Persist the transition, its resulting state, and the corresponding `current.yaml` index update together. Add the AURA to `active_auras` on activation and remove only that AURA on a terminal transition or entry to `conditionally_assured`; preserve every unrelated active entry. Update planned membership atomically. Record the previous state, resulting state, decision or reason, time, and relevant evidence or baseline reference. Let Git retain full history; do not create a second transition log. On read, resume, and before mutation, treat an invalid combination, illegal transition, or index mismatch as a blocking state divergence.

## Conditional assurance

A condition is a durable obligation attached to a conditional assurance decision. Its status is one of:

- `open` — not yet fulfilled and not overdue;
- `satisfied` — verified by sufficient evidence;
- `breached` — its date or event trigger passed without satisfaction;
- `waived` — deliberately accepted without satisfaction through a protected risk-acceptance decision;
- `superseded` — replaced through a protected decision by another explicit condition or outcome.

Index every `open` or `breached` condition in `current.yaml.condition_alerts`, and enforce the operations declared in its `blocks`. A breached trigger may be detected and recorded automatically, but the condition stays visible and blocking until a protected decision remediates, extends, supersedes, or waives it. Extending a deadline, changing a trigger, waiving, superseding, or finally resolving a condition is a protected decision. Update Condition Records through new canonical commits, preserve their prior Git history, and never mutate an earlier conditional Product Baseline.

When the last obligation is resolved, remove it from the alert index but retain the cycle's `conditionally_assured` status and original closure until the final decision. Promotion records a new assurance decision and a new Product Baseline that preserves the conditional baseline in its ancestry; do not retrofit `accept` into the original conditional decision or baseline. If other cycles advanced the integrated product meanwhile, supersede the latest integrated baseline and retain the original conditional baseline transitively.

For persistent defects after structured rework, use the [bounded-exit rule](oracles-capabilities-and-assurance.md#persistent-problems-and-a-bounded-exit). A planned stabilization cycle is a follow-up, not evidence that an obligation is satisfied. Explicit human risk acceptance, a stable qualified candidate, required verification/independence and complete Condition Records remain necessary; an uncontrolled hazard, missing indispensable evidence or failed non-waivable criterion still blocks conditional acceptance. Keep known failures visible and release/operation restrictions effective until the conditions are resolved.

## Preparing concurrent and dependent AURAs

When AURAE is invoked, treat phrases such as `cycle`, `development cycle`, `iteration`, `next cycle`, and `next iteration` as referring to an AURA unless the context clearly identifies a sprint, release, loop, or another distinct construct. Use **cycle** by default in conversation even when the user did not choose a term. Use **AURA** visibly only in the formal Assess–Understand–Realize–Assure progress card, when the user already uses it, or when explaining the canonical construct. Preserve `AURA` in canonical state.

Allow multiple active and planned AURAs in one logical Workspace. Each AURA frames one coherent contribution that can be integrated and assured as a unit. When the user asks to prepare another cycle:

1. Create or select a `planned` AURA and record the Product Baseline against which preparation occurs.
2. Preserve confirmed intent, expected behaviors, acceptance outcomes, initial risks, assumptions, proposed Oracles, and remaining engineering work through the adaptive low-load interview protocol.
3. Record `depends_on` only for outcomes that must land first. When the user says “next”, treat the relevant current AURA as a dependency unless they clearly request independent parallel work.
4. Keep the Specification Baseline unset. The preparation is durable and reviewable, but provisional until activation-time revalidation.
5. Keep `implementation.mode: none`, create no workstreams, change no product behavior, and do not enter Realize while the AURA remains planned.

Before promoting a planned AURA to `active`:

- verify the current reproducible Product Baseline;
- resolve every declared dependency to an acceptable Product Baseline or an explicit decision that removes the dependency;
- treat `depends_on` as an activation-order dependency, not merely an integration-order hint; independent work and safely coordinated overlap can proceed concurrently without inventing such a dependency;
- enforce every open or breached Condition Record whose blocks apply to this activation;
- compare scope, affected contracts, repositories, and integration paths with other active AURAs;
- allow independent or safely coordinated overlap to proceed, but preserve a blocker when concurrent work would make intent, integration, or assurance ambiguous;
- revalidate the prepared specification against current Product and Project Intent Baselines, marking impacted preparation stale when behavior, assumptions, risks, interfaces, Oracles, or acceptance outcomes changed; and
- obtain remaining confirmation, then publish its Specification Baseline only after every Understand exit condition is met.

Activation of one AURA does not reserve the entire Workspace or block unrelated contributions. Dependencies and conflicts constrain only the affected AURAs. If priorities change, revise, reorder, or reject planned AURAs while preserving decision history.

## Risk classification and proportionate depth

Scale work by credible failure consequences, exposure, uncertainty, detectability, and reversibility, not by code size. Use one qualitative scale for risks and the assurance they require:

- `standard` — local, limited, well understood, readily reversible, and observable through existing checks; no sensitive boundary, public contract, or critical component is materially changed;
- `medium` — user-visible or cross-module behavior whose failure would cause meaningful but contained and recoverable harm;
- `high` — a serious security, data, availability, compatibility, operational, or cross-repository consequence is credible, the blast radius may be broad, or recovery is difficult;
- `critical` — a catastrophic, systemic, or irreversible consequence is credible, such as massive data loss, major compromise, broken isolation, critical unavailability, or inability to restore a safe state.

Classify each credible risk scenario as follows:

1. State what could happen and why it matters.
2. Select the level matching the most severe credible consequence; do not average several risks or assign a numeric score.
3. Apply these minimum floors when the condition is material to the change:
   - a public contract, protocol, or coordinated multi-repository behavior is at least `medium`;
   - an authentication, authorization, secret, privacy, or hard-to-reverse data boundary change is at least `high`;
   - a credible irreversible or systemic consequence is `critical`.
4. Raise the level by one step, up to `critical`, when a material aggravating factor exists: high uncertainty, no representative Oracle, failure that is difficult to detect before production, an undemonstrated rollback, an uncontrolled dependency, or impact across several products or teams.
5. Record concise classification reasons so another agent or human can reproduce the judgment.

Keep `initial_level` and `residual_level` distinct. The highest material `initial_level` sets the AURA's minimum assurance level and cannot be reduced by planned controls. Set or lower `residual_level` only after controls exist and their evidence is available. Criticality reflects credible consequence, not complexity alone.

Create a durable Risk Record for every `medium`, `high`, or `critical` risk, and for a `standard` risk only when its ownership, reuse, or decision history is worth preserving. A standard AURA with no material risk may keep a brief risk summary without creating a separate artifact.

For `standard` work, a short intent statement, one behavioral expectation, technical checks, and one relevant Oracle may suffice. Assess and Understand may therefore be brief for a simple contribution, while their decisions remain explicit and resumable. Increase specification depth, adversarial coverage, evidence strength, independence, and human authority with the assurance level as defined in [oracles-capabilities-and-assurance.md](oracles-capabilities-and-assurance.md#assurance-levels).

Never omit a control solely because producing it feels administrative. Never create it solely because a checklist names it.

## Authority, protected decisions, and independence

Treat these decisions as protected:

- accepting or materially revising the Project Intent Baseline;
- accepting an AS-IS Baseline 0 at the Adoption gate or Bootstrap starting-state registration;
- accepting a Specification Baseline that commits user intent;
- accepting a significant architecture, security, compliance, or hard-to-reverse data decision;
- accepting a material residual risk;
- accepting, conditionally accepting, rejecting, or cleanly closing an AURA;
- extending, waiving, superseding, or finally resolving an assurance condition;
- granting, changing, or revoking decision authority.

An agent may prepare evidence, recommend an outcome, and record a proposal. It may finalize a protected decision only when an applicable project policy or accepted delegation explicitly grants that authority. Human authority remains mandatory for product intent, material-risk acceptance, important commitments, and every critical assurance decision.

Do not infer authority from a person's job title, vocabulary, repository access, or Git author identity. Ask about authority only when a protected decision is ready and the basis is not already established. Ask one plain-language question, then record the answer without requiring the person to adopt a role label.

Use one of these authority bases:

- `direct_confirmation` — the person explicitly confirms their authority for this decision;
- `project_policy` — accepted project governance grants the authority;
- `delegated` — an earlier protected Decision Record grants a bounded authority;
- `external_record` — an identified external governance decision supplies the authority.

Git author and committer fields provide useful provenance but do not authenticate authority. Signed commits or external approval systems are optional in the MVP unless project policy requires them. Never describe an unsigned Decision Record as cryptographically authenticated.

Require this minimum verification independence:

- `standard` — `self_check`; the Builder may also verify;
- `medium` — `separate_review`; a deliberate review distinct from implementation by another agent or human;
- `high` — `independent_verifier`; the verifier must not have implemented the affected change;
- `critical` — `independent_verifier` plus an explicitly identified human authority for acceptance.

Record both required and achieved independence, together with Builder and verifier identities when applicable. Use stable project identities or concise agent/session labels, not machine paths or sensitive personal data. Block Assure when achieved independence is below the required level.

Persist the accepted Decision Record before, or atomically with, the baseline or lifecycle transition that depends on it. Keep a free-form legacy `accepted_by` value as historical provenance, but do not reuse it as sufficient authority for a new protected decision.

## Decisions and transitions

Record the current phase and every accepted transition. For an Assure decision, use the complete outcome-first brief and optional human-test contract in [Assure](#assure), then the question protocol in [interviews.md](interviews.md). For other protected decisions, state the proposed commitment, supporting evidence, practical risks and scope, then ask one plain-language question with legitimate choices and an advisory recommendation when justified. Structural checks never replace judgment about meaning and risk.

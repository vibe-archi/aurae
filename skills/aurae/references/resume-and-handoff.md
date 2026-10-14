# Resume, inspect, persist, and hand off

Read for an entry/cycle resume, project-state inspection, checkpoint, handoff, or completion claim. A read-only question does not authorize a new cycle or metadata writes. Read [workspace-and-artifacts.md](workspace-and-artifacts.md), [lifecycle-and-interaction.md](lifecycle-and-interaction.md), and the Storage/validation contracts before relying on canonical state. Read [interviews.md](interviews.md) only if a question is needed and [status-views-and-voice.md](status-views-and-voice.md) before presenting the result.

## Persist and resume

For `/AURAE pause`, `/AURAE resume`, or equivalent explicit save-and-resume intent, read [pause-and-resume.md](pause-and-resume.md). It owns the durable cycle or pre-cycle entry checkpoint, interview queue, local/clone-ready distinction and resume-event handling. On an ordinary new-session resume, consult an existing linked cycle checkpoint or fixed `.aurae/resume.md` entry note when it supplies the interrupted work; absence is not permission to invent old questions or restart entry or a cycle. A pause is not a new lifecycle status or phase. An unavailable Git store permits only the owner's explicitly limited provisional export, not a durable-save claim.

- Validate the current Workspace on resume and every complete candidate Workspace before canonical commit or integration. Conformance errors block mutation; classify and resolve or explicitly retain warnings.
- Persist state atomically at phase transitions, accepted specification changes, AURA contribution and optional-workstream synchronization points, clean closure, and assurance decisions.
- An explicit pause also persists a complete resumable working checkpoint immediately at the nearest safe operation boundary, including mid-interview; it does not wait for a phase or specification to finish. Confirm success only after stored-state readback. Keep the checkpoint after resume and never roll back newer saved progress from it.
- Persist a resumable handoff when requested: confirmed intent, gate readiness, accepted baselines, open risks and questions, Capability Readiness, exact code and AURAE references, and the next action.
- Before yielding for selected Assure testing, preserve the participation choice and its source, exact candidate/environment, assigned checks and instructions, received human/agent observations, pending feedback and whether the agent's completion was already reported. On resume reconcile current evidence without dispatching a duplicate verifier or treating silence as a passed test; follow [assurance-participation.md](assurance-participation.md).
- Preserve integrated-candidate provenance, finding dispositions, serious-failure/repair history, any causal analysis and stabilization obligations under [verification discipline](oracles-capabilities-and-assurance.md#independent-agent-verification-discipline). A new session or verifier must not reset a repeated-failure loop, silently fix unrelated findings, or treat planned repairs as completed evidence.
- Preserve delivery acceptance separately from code-merge permission, the source and intended destination, deferral or consent provenance, and any actual integration result. On resume, inspect the refs and reuse only still-applicable authorization; never repeat a completed merge or treat resume as consent. Follow [the integration contract](collaborative-workstreams-and-git-reconciliation.md#integrate-and-close-safely).
- When Auto mode has a durable scope, preserve its source instruction, scope, question policy, end condition, and delegation boundaries in existing cycle, decision, specification, or handoff context so another agent can resume it without inventing authority or adding a new schema.
- Preserve material upgrade follow-ups in existing open-work, debt, risk, condition, or blocker structures at the next safe canonical write. A disposable local upgrade report must never be the only copy of an obligation that affects a gate or handoff.
- Record semantic history: why, expected behavior, risk, decision, verification, evidence, and referenced code commits.
- Keep accepted state canonical and immutable through Git history; revise with new commits rather than revision-suffixed files.
- On cycle resume, identify the AURA from the user's intent and visible Git binding when possible. Report only that AURA's phase, last accepted baseline, important blockers, open or breached condition alerts, material implementation drift, optional stale workstreams or dependent preparation, and next action. For pre-cycle entry, report its actual stage and next question instead. Do not require the previous conversation history.
- Display a compact AURAE Status View only at key moments. Do not repeat it after routine questions, artifact updates, commands, or tests.
- If stored state conflicts with the repository, stop mutation, preserve both versions, classify the divergence, and ask one question only if a human decision is required.

For a clone-based handoff, also follow [git-storage-and-sync.md](git-storage-and-sync.md#handoff-through-a-clone); a local checkpoint is not clone-ready until all required code, metadata and recovery refs are remotely available.

## Minimum completion conditions

Before calling an operation complete, check the applicable conditions below; do not run unrelated setup or verification solely because it appears in this list. The owning contracts define the details:

- the developer's original Git state remains intact;
- the documented Git Storage Harness was materialized only in ignored local storage, passed its self-test, and preserved the developer's Git state;
- AURAE metadata is readable and structurally valid;
- format compatibility was assessed before interpretation or mutation, and any migration preserved history while changing only the smallest live surface required by the affected AURAs;
- the documented Workspace validator was materialized only in ignored local storage, passed its self-test, and reported no blocking conformance error for the accepted state;
- all written refs descend from their expected base;
- no secret or machine-local state was synchronized;
- every active repository has an ignored `.scratchpad/`, and temporary AI output was kept inside it;
- a completed Bootstrap has an accepted Project Intent Baseline and an exact approved starting-state AS-IS Baseline 0, registered through the existing technical Adoption record; a paused initial interview with null pointers is valid unfinished work, not completed Bootstrap;
- an adopted project has an Adoption Record whose gate is `accepted` or `accepted_with_debt`, plus an exact reproducible AS-IS Baseline 0; an `incomplete` gate is never presented as a baseline;
- adoption records documentation and changelog condition for every writable repository, together with owned and prioritized assurance debt, unknowns, and gate blockers;
- any planned documentation reconstruction identifies its proposed structure, validation capabilities, and owning AURA before documentation is written;
- every repository explicitly bootstrapped or adopted with AURAE has a root `AURAE.md` recovery entrypoint with the welcome-before-consent fallback and an applicable agent instruction file that references it when no approved usable skill is available, or records the user's decision not to modify an existing instruction file;
- every such repository has a validated local `aurae/skill` recovery bundle matching the packaged skill snapshot selected during Bootstrap or Adoption; a clone-ready handoff also verifies that this ref is available from the receiving remote;
- every active AURA is indexed, the selected contribution and its Specification Baseline are unambiguous, and concurrent AURAs have no unclassified material overlap;
- every AURA state combination and recorded transition is valid, and every terminal AURA identifies the stable baseline it leaves behind;
- every planned AURA is clearly non-active and records its preparation baseline, declared dependencies, open engineering work, and activation blockers;
- every repository changed during Realize has an up-to-date root `CHANGELOG.md`;
- every fundamental specification or project-facing document affected by the AURA was updated and verified against the realized behavior, and only dependent or materially impacted concurrent AURAs were marked for focused revalidation;
- every direct AURA implementation and optional workstream references exact code commits and the applicable AURAE storage revisions;
- assurance claims link to Oracles and evidence;
- before an Assure decision, the user received a plain-language summary of the delivered behavior and a concrete explanation of every material residual risk, not only technical evidence or severity labels;
- the Assure participation choice was resolved before its campaign, selected human testers received concise practical instructions, independent-agent completion was reported, and all selected feedback is accounted for before readiness; any later optional extra test is distinct from pending selected verification;
- unit tests and Oracles created or materially changed for the AURA cover credible negative behavior, or the assurance evidence explains briefly why no meaningful negative case applies;
- every protected decision has a Decision Record with sufficient authority provenance;
- every product-code integration had explicit applicable user authorization for its contribution and destination; an accepted but unmerged candidate is reported as pending, not a completed integrated cycle;
- achieved verification independence meets or exceeds the AURA's required level;
- every conditional Product Baseline references at least one complete Condition Record with an owner, due trigger, declared blocks, and verification criteria;
- `current.yaml.condition_alerts` indexes exactly the open or breached conditions, and their declared blocks are enforced;
- promotion from `conditionally_assured` to `assured` has a new protected assurance decision and a superseding Product Baseline;
- every material risk has a durable Risk Record, a justified classification, and either an evidenced control or an explicit acceptance decision;
- the AURA assurance level is not lower than its highest material initial risk;
- an Upgrade AURAE operation leaves the active phase and accepted baselines unchanged, reports the version source honestly, and makes every material deferred impact visible at the next safe boundary;
- the user receives a concise outcome and next action.

Apply delivery/evidence/integration conditions to successful delivery, not to an abandoned or rejected contribution. Clean closure instead requires its protected decision, an accounted contribution and the existing stable starting or accepted product state actually left behind under [closure checks](collaborative-workstreams-and-git-reconciliation.md#closure-checks). It must not fabricate an implementation, assurance pass or new Product Baseline just to satisfy this checklist. A pause similarly saves unfinished work without claiming its gate passed.

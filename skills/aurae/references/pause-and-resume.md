# Pause and resume a cycle

## Intent and boundaries

Interpret `/AURAE pause` and `/AURAE resume` case-insensitively as skill operations, not as shell commands or a promise of host-native commands. Tolerate harmless spacing around `/` and `AURAE`. Recognize clear natural-language equivalents such as “pause this cycle and save where we are” or “resume the interrupted interview.” Use `resume`, not `continue`, in advertised command examples. A question about these commands is read-only, not an invocation.

Use this reference with [resume-and-handoff.md](resume-and-handoff.md), [interviews.md](interviews.md) for an interview, and the normal Storage and conformance contracts before writes. These operations create no cycle, phase, assurance outcome or global project lock. They do not bootstrap this folder, switch product branches, accept provisional specifications, restart a completed cycle, or suspend unrelated contributions. Select the cycle from explicit intent and unambiguous project/Git context; ask one question only if several targets remain plausible. If no cycle exists, state that limitation rather than inventing one for the command. A planned cycle may be paused in preparation without being activated.

This is an explicit checkpoint, not continuous autosave. A sudden stop without a completed checkpoint can lose conversation-only progress; never promise recovery of answers the agent could not save. Do not require a Git commit or a visible notice after every ordinary interview answer.

## One durable point per cycle

Use one stable narrative document at `.aurae/auras/<aura-id>/resume.md` on the metadata refs, not in the product tree or `.scratchpad/`. Reuse a coherent existing equivalent and link its exact portable path from that cycle's entry in `current.yaml.handoffs`; never maintain competing copies. Keep one handoff entry per cycle, preserving other cycles' entries. Its `gate_readiness` is the actual gate readiness, not a claim that a readable checkpoint passed the phase.

Use the existing artifact identity/provenance rules: one stable semantic ID (for example `RESUME-session-persistence-<8-hex>`), kind `resume_checkpoint`, scope `aura`, owning cycle and project/repository, author/source and time, and a record status `ready` or `resumed`. These describe the note, never the cycle's `status` or `phase_state`. The note is optional Markdown handoff context under the current Workspace contract, not a new mandatory YAML shape.

The cycle artifact remains the lifecycle authority. Reference accepted intent/specification/product baselines and Decision Records rather than cloning them into an alternative truth. A phase recorded in this note is explicitly the phase observed at checkpoint time; it never overrides newer canonical state. Record the exact metadata revision observed before saving and exact available code commits. Derive the checkpoint's containing revision from its Storage envelope; never embed its own containing commit.

The durable payload must contain enough context for a fresh conversation without the old chat:

- objective and bounded scope; relevant accepted artifacts, confirmed answers, open assumptions, unresolved decisions and material blockers;
- the selected cycle, observed phase/preparation and gate readiness, completed work, remaining work and one exact next action;
- code/repository references needed to reproduce the work, and any uncommitted/unshared code, missing dependency or required local resource that limits portability;
- interview purpose, language, one-at-a-time/batching preference, announced total, original question IDs and ordering, current question or batch, all received answers with source and confirmed/inferred/provisional distinction, discussion follow-ups and every remaining question already identified;
- any still-applicable Auto source instruction, scope, question policy, end condition and authority boundaries, with explicit mention if Auto was ended or suspended separately.

Preserve enough actual question/choice wording and answer meaning to resume exactly; a topic-only list or “4/9 completed” is insufficient. Keep numbers stable, including follow-ups and removed/deferred items, and distinguish `asked`, `answered`, `validated`, `deferred` and `planned`. A response of `discuss` remains unresolved and its individual follow-up precedes a new batch. If only topics had been formulated, label them as topics to formulate, not as previously asked questions. Do not invent missing questions or answers to fill a queue.

Saving draft answers and remaining questions validates their faithful recording, not their product acceptance. Keep them explicitly labeled working context. Do not persist secrets, credentials, hidden reasoning, full transcripts, machine-specific paths or raw logs. Preserve portable references and necessary non-sensitive conclusions instead. If omitted sensitive/local material is necessary to continue, record that dependency without the secret and do not claim a self-contained handoff.

### Compact document outline

Adapt wording to the user's language; retain these distinctions rather than filling empty ceremonial sections:

```markdown
# Resume point — <cycle title>

ID: RESUME-<semantic-slug>-<8-hex>
Kind: resume_checkpoint
Scope: aura
Owner: <AURA-id>; project/repository: <existing IDs>
Record status: ready
Recorded by/source: <actual participant and pause request>; at: <ISO-8601>
Observed metadata revision: <exact preceding commit>
Observed cycle state: <status / phase / phase_state, or planned preparation>
Gate readiness: <incomplete or ready, with relevant pending decision>

## Context and references
<Objective; accepted artifact references; confirmed outcomes; open assumptions>

## Interview
Purpose/language/style: <actual values>
Main total: <announced total>
Current item: <Q4 / 9 awaiting answer, or Q4.1 / 9 requiring discussion>
<For EVERY identified main question and follow-up: original ID, question/choices
or clearly labeled unformulated topic, status, answer if received, answer source
and confirmation status. Preserve previous labels and remaining order.>

## Work and portability
<Completed/remaining work; exact code refs; uncommitted or unshared dependencies>
<Applicable Auto instruction and limits, or ordinary interaction>

## Next action
<The precise pending question, decision, or safe work item>

## Resume record
Not resumed yet.
```

On a verified material resumption, keep the recorded payload and record who resumed, when, and the exact prior checkpoint revision under `Resume record`; set only the note's record status to `resumed`. Keep this compact record for the most recent actual resumption, with earlier events preserved by Git. A genuinely new handoff after another session ended may warrant a new event; repeating the command in the same ongoing session does not. Use actual known participant context without collecting extra identity data solely for this note. A resume marker documents an event; it is neither authenticated authority nor an exclusive distributed lock.

## `/AURAE pause`

1. Stop initiating new work for the selected cycle. Reach the nearest safe operation boundary, not the end of the phase or interview. Settle or safely stop only controlled work that would make this checkpoint inconsistent; preserve interrupted tests as incomplete, never passing. Do not claim other agents/processes stopped unless verified.
2. Read the existing cycle, handoff and checkpoint at their exact revisions. Combine current confirmed conversation context with saved facts; preserve unresolved contradictions rather than choosing silently. Account for an answer received immediately before the pause. In Auto, pause also stops autonomous progression even if its earlier scope said to continue until a milestone.
3. Write the complete checkpoint and its scoped handoff entry atomically through the validated isolated metadata workflow. Ordinary branch-specific progress uses its contribution ref. Integrate the handoff into `aurae/meta` through the normal reviewed path so another session can discover it without guessing a branch. Preserve cycle phase, phase state, transitions, accepted baselines, indexes of active/planned cycles and other handoffs. Updating handoff context is not gate acceptance.
4. Validate the complete Workspace against the exact preceding tree and separately verify checkpoint completeness: every received answer accounted for, stable labels, unresolved discussions, exact next item, matching cycle and references, and truthful code portability. The generic validator checks Workspace shape and the Storage Harness binds exact Markdown bytes; neither automatically proves the interview transcript was recorded faithfully. Commit, read back the actual stored document and verify developer state before confirming success. If canonical integration is blocked, retain the contribution checkpoint and name the unresolved discovery/integration limitation; do not call it a completed canonical pause.
5. If a remote is configured and synchronization is already authorized for this scope, synchronize the necessary metadata and existing required code/recovery refs now, using [Git clone handoff](git-storage-and-sync.md#handoff-through-a-clone). Authorization need not be requested again at every pause. Otherwise keep the completed local checkpoint and ask one permission question only when remote transfer is wanted and questions are permitted; in Auto `none`, report the missing permission without asking. Do not add a remote, push unrelated refs or stage/commit product files implicitly.
6. Verify the remote refs and reachability before claiming `clone_ready`. If code needed for resume is uncommitted, an essential dependency is missing, or a required resource exists only locally, preserve it untouched and say which part remains local; offer an explicitly scoped code checkpoint when useful. A push failure or conflict leaves the local checkpoint intact and the pause `local_only`, not lost and not clone-ready. Once the pause result is reported, do not continue the interview, implementation or Auto work until a new resume instruction.

Keep the result short: cycle/phase, precise next question/action, and `local_only` or verified `clone_ready`, expressed in plain language. For example:

> **Point de reprise enregistré**
>
> ✔️ Understand — réponses Q1 à Q3 conservées.  
> 🟣 Q4 / 9 attend ta réponse.  
> ✔️ Reprise disponible dans une nouvelle conversation sur ce dépôt local.  
> ➡ **Pour reprendre : `/AURAE resume`.**

If no durable metadata commit could be created, state that the pause could not be durably saved and preserve available local work. If a contribution commit exists but canonical integration failed, report that saved contribution and the discovery/integration limitation. If only remote transfer failed, report the usable local checkpoint and the failed transfer. Never report a successful save from an in-memory summary or an uncommitted temporary export.

## `/AURAE resume`

1. Use the approved current skill, normal memory discovery, and conformance checks; recover a missing skill only through the existing consent protocol. Do not repeat Bootstrap/Adoption or its introduction for an ordinary resume. Read canonical state, the selected cycle's handoff, the checkpoint at an exact revision, and any explicitly linked contribution required for unfinished state. Fetch only when authorized. Do not assume a different conversation has the old chat or `.scratchpad/` files.
2. Compare the checkpoint with newer saved cycle state, accepted baselines, conditions, code and contribution history. Reuse later confirmed progress. If a question was answered or a gate was crossed since the checkpoint, do not repeat or reverse it. If work has become stale, reconsider only the affected items with normal numbering and gate rules. Conflicting answers or incompatible histories require focused reconciliation, not timestamp precedence or restoring the old snapshot. Never reopen a completed cycle merely because an older pause note exists.
3. Check for a visible competing resumption or contribution on this same cycle. A `resumed` note alone can be an old event, not proof of a live agent. Reconcile actual newer progress; if overlapping live ownership remains materially ambiguous, ask one focused question (or report the blocker under Auto `none`). Do not overwrite a newer checkpoint, take over unrelated work or claim visibility of unsynchronized/offline agents.
4. Preserve and atomically record the resume event through the normal expected-revision write, only after determining a safe resume point. A moved ref requires rereading and reconciliation; never overwrite it from the earlier note. If the record is already resumed and there is no new checkpoint or material resumption event to record, reuse it rather than manufacturing another commit. Repeating `resume` must not replay completed questions or side effects. A failed resume write leaves the earlier checkpoint usable and must be reported before advancing the interview or mutable cycle work.
5. Display the normal compact phase view with the actual current phase before phase-specific work. For an interview, briefly restore the queue context and next original ID; apply the user's current question policy. An unanswered Q4 / 9 resumes at Q4; an answered Q4 resumes at Q5 only if no Q4 follow-up or earlier discussion remains unresolved. Present the retained question/choices naturally, not the complete saved queue.
6. Continue only the selected cycle within current authority. Resume a paused Auto scope only if its original instruction is still available/applicable, its end condition is unmet, and the user has not separately ended it. Missing or expired delegation never comes from the checkpoint's own assertion. Under Auto `none`, unresolved authority or essential missing context produces a concise resumable blocker, not a question or invented answer.

If no checkpoint exists, use the normal last recorded cycle state and explicitly distinguish that best-effort resume from exact interview recovery. Ask only for essential missing context, never fabricate the previous Q4/9, restart Adoption, or silently promote draft answers. If canonical state is unavailable or invalid, preserve local evidence and stop only unsafe continuation through the normal recovery contract.

## After resumption

Do not delete or consume the checkpoint merely because `resume` was called. Keep it as the last durable recovery point and retain its answers, unresolved items and resume provenance. Its recorded phase is historical context, not a second lifecycle authority. The next explicit pause refreshes that same stable document and ID from the latest reconciled state, sets its record status back to `ready` and its resume record to “Not resumed yet,” and makes it the new reference point. Git preserves earlier payloads and resume events without revision-suffixed files or new branches. Normal accepted progress/checkpoints may refresh the relevant handoff context as needed without rewriting accepted history.

A crash after resumption can recover only progress actually saved since the previous pause. Do not present `record status: resumed` as proof that later conversation answers were persisted. Keep this limitation clear when relevant, not as a repeated warning after each question.

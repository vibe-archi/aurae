# Assure participation and test feedback

Read when Realize is ready, before starting or delegating Assure, and when collecting or resuming verification feedback. Use [lifecycle-and-interaction.md](lifecycle-and-interaction.md) for gates and independence, [oracles-capabilities-and-assurance.md](oracles-capabilities-and-assurance.md) for coverage/evidence, and [status-views-and-voice.md](status-views-and-voice.md) for presentation.

## Choose who verifies

After implementation and internal technical checks finish, briefly explain what is ready and ask one question before the Assure campaign starts: does the user want to test personally, delegate to an independent agent, or do both? State at that moment that personal testing comes with concise build/run instructions and a scenario showing what to check. Reuse an explicit still-applicable choice already made for this cycle; do not ask it again merely because a conversation resumed. A generic instruction to implement is not a choice to delegate assurance.

Use the user's language, the ordinary question layout or an equivalent native interface, and a custom-answer path. For example:

The implementation and internal checks are complete. If you test personally, I will provide the build/start instructions and the steps and expected results to check.

**How would you like to verify this delivery?**

> - **Test it myself** — I will run the checks and report what I observe.
> - **Delegate to an independent agent** — the agent verifies the delivery and reports back.
> - **Both** — I test it too, and we combine both sets of results.
> - Discuss another arrangement.

Give a brief recommendation only when justified. Recommend independent-agent verification when it meets the required coverage and reduces the user's workload; recommend both when human use materially complements the automated checks, not as a universal extra obligation. Explain only a genuine feasibility or independence limitation before treating the chosen arrangement as workable.

Keep the cycle at Realize / ready while this choice is pending. Choosing participants is neither passing Assure nor accepting the product. Once the choice and entry conditions are satisfied, persist Assure / in_progress and show the normal phase view before starting its work.

### Auto mode

Use [autonomous-mode.md](autonomous-mode.md) when valid scoped delegation already covers this routine choice: reuse an explicit participation choice, otherwise select independent-agent verification within that authority and state it briefly rather than asking a suppressed question. Never assign the human testing work under Auto without their expressed intent. An explicit request to test personally or use both remains pending until its feedback arrives; Auto does not answer for the human. A specific instruction to ask at this boundary overrides an earlier generic Auto preference. If required authority or capability is missing, apply the current question policy without inventing permission.

## What each choice means

- **Human:** the human is the designated verifier and takes responsibility for performing and reporting the assigned checks. The engineering agent provides the candidate, scenarios, safe setup and evidence support; it does not silently substitute an independent agent. Human-executed checks can supply required Oracle evidence when their observations, reproducibility and coverage support the claims.
- **Independent agent:** delegate to an actual agent distinct from the Builder, with the exact candidate, accepted expectations, selected positive/negative Oracles, relevant journeys, environment and required evidence. The Builder's internal test run or a new persona in the same response is not that independent verification.
- **Both:** the agent performs the required independent campaign while the human follows an agreed practical test path. Both reports are expected. They may run in parallel only when their environments/data are isolated or coordinated so neither changes the other's candidate or invalidates observations.

The choice changes who verifies, not the risk, required coverage, evidence quality or authority to accept. A human can meet the independence requirement if actually independent of the implementation; a person's identity alone does not make their own implementation review independent. If human-only cannot meet a required capability or independence level, explain that concrete gap and agree the smallest adequate arrangement. Do not bypass it because the user says they take responsibility, nor categorically require an AI verifier when a suitable human can fulfill the contract.

Do not infer production access, paid operations, external publication or installation permissions from any choice. If delegation is unavailable, report it and preserve the chosen plan; use an authorized handoff or discuss another arrangement rather than claiming an agent is running.

## Give the human a usable test path

For human or both, deliver the instructions at Assure entry, before waiting for human results, not only in the final acceptance brief:

- identify the delivery and any prerequisite necessary to exercise it safely;
- provide the minimal validated compile/install/start/open commands or actions, as needed, with the relevant working directory or supported entry point;
- show a short scenario, normally two to four main steps, with concrete expected observations and relevant negative behavior; include UI actions when the journey uses a UI;
- state how to report success, unexpected behavior, or an inability to run a step.

Keep the visible guide concise and link validated existing instructions or the selected scenario list when human-only coverage requires more. Do not shrink mandatory coverage to fit four lines, substitute a smoke check for a required full journey, or assign irrelevant setup. For both, avoid asking the human to duplicate the entire independent campaign unless that duplication addresses a real risk.

Verify the instructions against the exact candidate and a representative authorized environment before presenting them as validated. Setup checks by the Builder do not count as the independent verdict. If only part of the path can be checked locally, disclose the limitation and establish the receiving environment's readiness rather than inventing a tested command. For internal-only work, offer an applicable build/test/review path; if none is feasible for this user, explain that instead of fabricating UI steps. More detail remains available on request.

## Collect, combine and notify

Persist the agreed plan and required feedback before yielding or delegating. Use the existing cycle assurance context, linked narrative artifacts, evidence manifests and scoped handoff; no new required Workspace field or lifecycle status is needed. Preserve:

- cycle, exact candidate and environment, selected participants and source of the choice;
- each participant's assigned coverage and instruction/scenario references;
- what is running, what feedback is still awaited, actual results received and their source;
- unresolved differences, evidence limitations and the next action.

Use existing identity/provenance rules for any new narrative artifact. Keep canonical context and necessary evidence out of disposable scratch storage. The generic Workspace validator does not prove feedback completeness or human independence; check those semantics before claiming readiness.

When an independent agent finishes, notify the user promptly with its actual outcome and meaningful limits, whether it passed, found defects, was blocked or could not conclude. Do this even if human testing is still pending. Say whose result is complete, not that all assurance is finished. Consolidate a completion already reported in this conversation; do not send duplicate notices on routine resume.

- **Agent finishes first, human expected:** preserve its report, say that the human feedback is still awaited, and invite that feedback with one focused question when questions are allowed. Do not ask for final acceptance yet.
- **Human finishes first, agent expected:** save the observations, investigate material defects, and await the agent's result. Do not close from the human report alone.
- **Human-only:** await the human's actual observations; do not invent an absent agent report.
- **All selected results received:** combine them into one concise evidence-backed assessment before the final assurance decision. If only the agent was selected, its completion notice may lead directly into that decision brief once the other gates are met.

Use available host wait/completion mechanisms for an actual running verifier. If the session cannot receive completion events or survive a yield, persist the pending handoff and explain how results will be retrieved on resume; do not promise an unsupported background notification. Do not busy-poll a human, create recurring reminders or duplicate agents merely to wait.

Preserve attribution and distinguish reported human observations from directly observed agent evidence. Link actual checks to the relevant requirements/Oracles; a bare approval is not proof that all assigned tests ran. Ask only for essential missing scope or observations. Partial feedback remains partial. Do not average away contradictions, erase a human failure because an agent passed, or double-count the same run copied into two reports. Investigate differences against candidate, environment and scenario; classify defects and arrange focused rework/reverification.

If a fix changes the candidate or a relevant environment changes while someone tests, retain old reports with their original scope, refresh instructions and request/run the affected checks on the new candidate. Do not mix stale human results with fresh agent results as though they verify one delivery.

## Waiting and decision boundaries

During selected human/agent testing or while feedback remains incomplete, keep active / assure / in_progress; use blocked only for an actual blocker under the lifecycle contract. Waiting for a selected tester is not a new global status and does not suspend unrelated cycles. Do not advance to ready or acceptance because the other participant passed, time elapsed, the user stayed silent or a resume command was received.

The user may explicitly change participation or stop their personal testing. Record the change, retain received observations and reassess remaining coverage and independence. Silence or a vague acceptance is not an implicit removal of expected feedback. A changed plan never erases a reported defect or waives an indispensable check.

Once every selected report is accounted for, discrepancies are resolved or handled through the normal risk/condition process, and the evidence meets the assurance floor, set Assure / ready and present the ordinary delivered-outcome, verification, residual-risk and acceptance brief. Test feedback and the protected product-acceptance decision remain separate.

The later optional "test it yourself before deciding" path remains available only after the selected assurance work is complete. It is an additional personal check, not a substitute for missing selected feedback. The cycle may remain Assure / ready while awaiting that extra decision-time check if existing evidence is still sufficient; a new defect or evidence gap requires reclassification and focused work. Do not make users repeat a test they already performed just to satisfy a presentation template.


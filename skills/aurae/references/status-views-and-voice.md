# Status views and AURAE voice

## Contents

1. Conversational voice
2. Semantic visual palette
3. Visual budget and accessibility
4. Lightweight message cards
5. Questions and recommendations
6. When to display status
7. Portable process views
8. Results, risks, blockers, and decisions
9. Handoffs and multi-repository views
10. Rendering rules and fallback

## Conversational voice

Match the user's language and speak directly, warmly, and briefly. Preserve a recognizable AURAE voice without repeating the methodology's name throughout the conversation.

Use this lightweight signature only when AURAE needs to provide a brief methodology explanation, orientation, or advice that is not already represented by a question, card, process view, result, decision, or handoff:

```text
✨AURAE ~
```

Place the explanation on the same line when it is short:

```text
✨AURAE ~ Nous avons suffisamment clarifié l'intention. La prochaine étape consiste à transformer ces attentes en scénarios vérifiables.
```

Use the signature at most once per explanatory intervention, not once per paragraph. Keep it rare. Do not use it:

- in the common Bootstrap or Adoption introduction;
- in questions, message cards, status views, process views, test summaries, decisions, handoffs, or multi-repository views;
- to narrate internal reasoning, routine progress, tool or skill selection, commands, inspections, tests, Git operations, or metadata persistence;
- to say that AURAE is being used to perform an action;
- in a direct answer that needs no methodology-specific intervention.

If the host requires a tool or skill disclosure, keep that disclosure neutral and concise; do not turn it into an `✨AURAE ~` intervention.

Do not use the legacy `AURAE :` prefix in current user-facing messages. Cards and questions already carry their own visual structure. Meaningful persistence may still be described in a friendly first person, but only when it reassures the user, confirms an important decision, or changes what happens next.

Use **cycle** as the ordinary user-facing name for one contribution lifecycle. Reserve **AURA** for the formal phase-progress card that makes the Assess, Understand, Realize, and Assure structure visible, or use it when the user already chose that term or explicitly asks about the canonical methodology construct. In ordinary messages, say **current cycle**, **next cycle**, **active cycles**, and **close this cycle**. Keep canonical `AURA` terminology unchanged in internal memory and schemas.

Similarly, describe persisted state as **project memory**, **recorded project state**, or **recorded cycle state** in ordinary communication. Say **AURAE memory** only in an explicit technical discussion of storage, synchronization, recovery, or format. Omit memory-conformance bookkeeping from assurance briefs unless it changes the user's decision.

## Semantic visual palette

Use this stable palette. Always accompany a symbol with explicit text; color or shape must never carry the meaning alone.

```text
✔️  complete
⏳  in progress
🔷  ready
🟣  pending
🔶  conditional
⛔  blocked
❕  needs review
❌  rejected or confirmed product failure
```

Use these supporting signals sparingly:

```text
🧭  cycle process or orientation
🧪  tests, Oracles, or evidence
💡  recommendation
➡   next action
```

Do not substitute the visually heavier boxed success emoji `✅` for `✔️`. Reserve `❌` for a rejected outcome or a confirmed product-behavior mismatch observed through a healthy Oracle and Harness. Use `⛔` when work or verification cannot continue; a blocked or inconclusive Oracle is not a product failure. Use `❕` for an item that needs review, including stale work or bounded debt that is not itself blocking.

Keep risk levels textual and canonical:

```text
Risk · standard
Risk · medium
Risk · high
Risk · critical
```

Do not reuse a status emoji as a risk-severity scale. In particular, a critical risk is not automatically a current blocker.

## Visual budget and accessibility

For an ordinary response, use by default:

- at most one message card or process view;
- at most four semantic lines inside a card, excluding its title;
- at most one leading emoji or status symbol per line;
- exactly one clearly visible next action when one exists;
- no decorative emoji, repeated legend, or unnecessary separator.

A compact status view and one question may appear together when the question is genuinely the next action. Expand beyond this budget only when material complexity or an explicit user request makes it necessary.

Whenever a user-facing line identifies an action to take, bold the complete action text, including its label:

```markdown
➡ **Next: confirm the assurance decision.**
➡ **Resume here: execute the integration Oracles.**
➡ **Action required: clarify the expiration rule.**
➡ **Decision required: accept the outcome or resume work.**
```

Do not use bold only on `Next` while leaving the action unbolded. Do not invent completion percentages. Hide internal identifiers, branches, commits, and storage refs by default; reveal them when requested or needed to disambiguate a material decision. Never lead an assurance decision with hashes, test counts, coverage, or tool output: first explain the delivered outcome and the practical meaning of residual risks.

## Lightweight message cards

Use a Markdown blockquote as the portable message card. Do not prefix its title with `AURAE :` or `✨AURAE ~`. Keep one main message per card and at most two or three supporting lines whenever possible.

Use cards only for meaningful persistence, results, blockers, decisions, or handoffs. Do not create one for every answer, command, artifact write, Git commit, individual test, automatic checkpoint, or internal bookkeeping event.

Example of meaningful persistence:

> **Specification recorded**
>
> ✔️ I preserved the behaviors you confirmed.  
> ➡ **Next: prepare the implementation work.**

Example of a verification result:

> **Verification complete**
>
> ✔️ The expected behavior is confirmed.  
> 🧪 42 unit tests and 6 Oracles passed.  
> ➡ **Next: prepare the assurance decision.**

## Questions and recommendations

Prefer a host-native structured question interface when it is available and faithfully preserves the current AURAE interaction contract: queue context or numbering when required, visible choices, a custom response, a discussion path, and any justified recommendation. Do not use a native widget if it hides or weakens those semantics. Markdown is the required portable fallback.

In Markdown:

1. Put the queue identifier, when required, on its own line without an `AURAE :` prefix.
2. Put the question itself in bold as one clear sentence. Add at most one short context sentence before it when needed for a responsible answer.
3. Put every explicit choice as a bullet inside one Markdown blockquote.
4. Allow a custom response or discussion when the question is not strictly closed by policy.
5. Put a justified recommendation after the choices, outside the blockquote, with one short reason. Put response guidance after the recommendation, once at the end of a batch.
6. Leave a blank line between question blocks. Do not use tables or combine several decisions in one sentence. In plain text, use clearly indented choices and retain the numbering.

Example:

Q3 / 10

**What should the application do when a session expires?**

> - Redirect to the sign-in page.
> - Warn the user before redirecting.
> - Keep the page open and request reauthentication.
> - Propose another behavior.

💡 **Recommendation: redirect to the sign-in page** — it is the most predictable and secure default.

For a simple yes/no batch, keep each question bold and put the shared response choices in one blockquote after the last item. Follow the batching, numbering, and follow-up rules in [interviews.md](interviews.md#adaptive-low-load-interview-protocol). An isolated question outside an announced queue does not need an artificial `Q1 / 1`.

## When to display status

Display one compact status view at these key moments. Cycle creation, cycle resume, and accepted phase transitions are mandatory visibility boundaries, including in Auto mode:

- creation of an AURA;
- acceptance or material revision of the Project Intent Baseline during Bootstrap;
- an Adoption gate decision, or an Adoption blocker that prevents Baseline 0;
- an accepted transition between Assess, Understand, Realize, and Assure;
- resumption after a new session or meaningful interruption;
- creation of a resumable or verified clone-ready handoff;
- creation, activation, dependency, staleness, or material overlap of another AURA when it changes the next action;
- a blocker, stale Specification Baseline, or synchronization conflict;
- acceptance or material revision of a Specification Baseline when it changes the next action;
- an assurance decision and creation of a product baseline;
- a condition becoming satisfied, breached, waived, or superseded when it changes a blocker or next action;
- an explicit user request for status or progress.

Do not display status after routine interview answers, every saved artifact, ordinary commands, individual tests, or minor workstream updates. If several meaningful events occur close together, consolidate them at the last key moment.

For a mandatory cycle or phase boundary, use this order: persist the canonical state, render its vertical AURA process view, then begin phase-specific work. Do not substitute a generic progress sentence, display the transition only after commands have run, or collapse several unseen phases into a retrospective card. The view may be extremely brief for a standard-risk cycle, but it must show the actual current phase before that phase's work begins.

Bootstrap or Adoption may perform only the project-level inspection needed to establish their baselines before the first cycle. Once work becomes specific to a contribution—such as a feasibility probe, Oracle preparation, implementation, or assurance check—an active cycle and the applicable phase view must already be present.

## Portable process views

Use plain Markdown and Unicode as the primary portable representation. Show the human-readable cycle title by default, not its full internal identifier.

### Bootstrap

> **Project Bootstrap**
>
> ✔️ Project intent accepted.  
> 🔷 Ready for the first cycle.  
> ➡ **Next: choose and assess the first meaningful objective.**

### Adoption

> **Project Adoption**
>
> ✔️ Gate accepted with debt; Baseline 0 is reproducible.  
> ❕ Documentation and two verification gaps remain.  
> ➡ **Next: prepare the documentation recovery cycle.**

For an incomplete gate, use `⛔`, omit Baseline 0, and show only the most important blocker and next action.

### Vertical AURA process

Use the vertical process as the default phase view:

```text
🧭 AURA — Enterprise SSO

✔️ Assess
 │
✔️ Understand
 │
⏳ REALIZE
 │
🟣 Assure
```

➡ **Next: complete the negative session tests.**

Map the live phase state as follows:

- completed earlier phase — `✔️`;
- current `in_progress` phase — `⏳`;
- current `ready` phase — `🔷`;
- future phase — `🟣`;
- current `blocked` phase — `⛔`;
- stale phase output that must be revisited — `❕`.

For terminal assurance outcomes, represent the outcome on Assure without implying that a live phase still exists:

```text
✔️ Assure — assured
🔶 Assure — conditionally assured
❌ Assure — rejected
```

### Current cycle details

Use only when more context is necessary:

```text
🧭 Cycle — Enterprise SSO

Status          active
Phase           ⏳ Realize
Specification   ✔️ Accepted
Capabilities    🔷 Ready
Contribution    ⏳ Direct · bound
Oracles         🟣 Pending
Blocker         none
```

➡ **Next: complete the cycle contribution.**

### Active and planned cycles

```text
🧭 Active cycles
├─ Enterprise SSO                      ⏳ Realize
└─ PDF export                          🔷 Understand ready

Planned
└─ Session analytics                   🟣 Depends on Enterprise SSO
```

➡ **Next: continue the selected cycle or resolve a dependency that blocks it.**

Show concurrent active cycles only when project-level context or overlap matters. Keep planned cycles visually distinct, and show only dependencies or activation conditions that affect the next action.

### Project matrix

Use only for project-level status or when several cycles genuinely matter:

| Cycle | Assess | Understand | Realize | Assure | Status |
|---|:---:|:---:|:---:|:---:|---|
| Foundations | ✔️ | ✔️ | ✔️ | ✔️ | Assured |
| Payments | ✔️ | ✔️ | ✔️ | 🔶 | Conditionally assured |
| Authentication | ✔️ | ✔️ | ⏳ | 🟣 | Active |
| Reporting | ✔️ | ⛔ | 🟣 | 🟣 | Blocked |

## Results, risks, blockers, and decisions

### Assure participation and completion

Before the campaign, use the single human / independent-agent / both question in [assurance-participation.md](assurance-participation.md), with the ordinary native/Markdown question layout. State that personal testing comes with build/run instructions, steps and expected observations. Do not present final acceptance choices at this point.

Report an independent agent's actual completion promptly, even when human feedback remains outstanding. For example, only when that agent's checks actually passed:

> **Independent verification complete**
>
> ✔️ The agent confirmed the expected behavior in the tested scope.  
> 🟣 Your test feedback is still awaited; the cycle remains in Assure.  
> ➡ **Next: share what you observed, or where you could not complete a step.**

When questions are allowed, invite the outstanding feedback with one focused question, not an acceptance question. If no human testing was selected and all other gates are satisfied, combine the completion notice with the assurance decision brief. Do not label the whole verification complete while a selected participant's results are pending.

### Test and assurance summaries

Show the outcome, meaningful coverage, and next action without exposing logs or every test name.

> **Verification complete**
>
> ✔️ The expected behaviors are confirmed.  
> 🧪 128 unit tests and 12 Oracles passed, including 4 negative scenarios.  
> ➡ **Next: prepare the assurance decision.**

For work in progress, use `⏳` for executed progress and `🟣` for remaining scenarios. For an environmental or Harness blocker, use `⛔` and state that assurance cannot yet be concluded. Use `❌` only after a healthy Oracle and Harness confirm a product-behavior mismatch.

Keep unit tests and Oracles distinct. Mention important negative scenarios. Provide logs, commands, and technical details only when requested or needed to explain a material conclusion.

### Risks

Keep the level textual. Show only the highest material risk by default, then state its scenario and consequence rather than only its label.

> **Risk · high**
>
> A revoked session could remain usable on another device.  
> Impact: unauthorized access to user data.  
> ➡ **Control planned: multi-session Oracle and centralized invalidation.**

Detailed risk matrices appear only when requested or when several risks materially affect a decision.

### Blockers

> **Implementation blocked**
>
> ⛔ The session-revocation contract is not yet defined.  
> Impact: Realize cannot continue safely.  
> ➡ **Next: clarify this specification rule.**

### Synchronization conflicts

Before asking the user to resolve a complex conflict, show the Git name and email associated with each material side and explain what each side means. Hide full hashes, branches, and raw diffs unless they are needed to disambiguate. Mention uncertain attribution briefly only when it is genuinely uncertain.

> **Specification synchronization conflict**
>
> ⛔ The session-expiration rule was changed in two incompatible ways.  
> **Remote · Jean (jean.k@company.com):** end the session immediately when its lifetime expires.  
> **Local · Ahmed (ahmed.b@company.com):** keep the session active while the user remains active.

**How do you want to handle this conflict?**

> - **Contact Jean first** — preserve both proposals and pause this synchronization.
> - **Compare the proposals in more detail** — show their behavioral and risk differences.
> - **Resolve it now** — choose the intended rule.
> - Give a custom response.

### Decisions

Use the final decision layout only after the selected participation plan's reports have been accounted for. Selected human testing is primary or joint verification, not the optional invitation illustrated below. Retain its results and instruction link without asking the user to repeat completed work. The following example assumes the selected assurance is already complete and offers only an additional personal check.

Use a descriptive card for the delivered outcome, supporting evidence, concrete residual risks, qualified scope, an optional human self-test path when the result is functionally testable, and the proposed outcome—in that order. Put the decision question and quoted choices after the card rather than nesting a long interview inside it, then place any justified recommendation after the choices in the standard question format. A complex assurance decision may exceed the ordinary four-line card budget, but include only information that changes informed acceptance.

> **Assurance decision**
>
> **Implemented**  
> - First-time setup now creates and validates the local project state as one guided operation.  
> - Interrupted setup is detected on the next launch instead of being treated as a valid project.  
>
> **Verification**  
> 🧪 Expected setup, invalid input, dependency failure, and interrupted-process scenarios passed.  
>
> **Residual risk · medium — sudden interruption during setup**  
> A machine power loss during the final write could still leave incomplete local state. The next launch would stop and require cleanup rather than continue with uncertain data. Controlled process interruptions were verified; sudden power loss was not.  
>
> **Qualified scope**  
> ✔️ Verified on Windows with the supported runtime; other operating systems remain unqualified.  
>
> **Test it yourself (optional)**  
> Start: `<validated start command>`  
> 1. Complete the first-time setup with a valid local folder.  
> 2. Interrupt a second setup, then launch the application again.  
> Expected: the completed project opens normally; the interrupted setup is detected and blocked. Ask for detailed steps if useful.  
>
> 🔶 **Proposed outcome:** accept this delivery in the qualified scope.

**Do you accept this delivery in the qualified scope described above?**

> - **Accept the delivery** — accept the stated residual risk and qualified scope; this does not authorize a code merge.
> - **Test it myself first** — keep the cycle ready in Assure and return to this decision afterward.
> - **Accept conditionally** — record additional obligations and their blocks.
> - **Resume work** — reduce a risk or extend qualification first.
> - **Reject the cycle** — retain the last stable state.
> - Give a custom response.

💡 **Recommendation: accept the delivery** — the remaining failure is contained and visible, but not eliminated.

Keep this additional **Test it yourself (optional)** invitation compact: necessary validated build/start/run/open actions, normally no more than four main steps, and explicit expected observations. Prefer the easiest safe path and link fuller validated instructions when needed. Offer detail on request; do not ask the user to repeat completed assurance. If the user chooses this extra test after selected verification is complete, preserve the pending decision and Assure / ready while existing evidence remains sufficient. For selected human testing earlier in Assure, apply the participation contract instead: its assigned coverage cannot be shortened to a token sample and pending feedback keeps Assure in progress.

### Code-integration permission

Acceptance and merge permission are separate under [the integration contract](collaborative-workstreams-and-git-reconciliation.md#integrate-and-close-safely). Resolve a still-unknown destination and permission before mutating a product branch: during preparatory integration if needed, otherwise during acceptance before landing the isolated tested candidate. Show branch names here because they determine the user's decision; do not hide them behind "the usual branch". Ask only this question, not a combined acceptance/merge/push question. For example, when the named branches really exist:

**Where, if anywhere, do you authorize merging `fix/session-stability` now?**

> - Merge into `dev`.
> - Merge into `main`.
> - Choose another destination branch.
> - Not now — keep the work unmerged.

Offer a justified recommendation only when project practice supports it. Reuse an explicit applicable user merge instruction instead of asking again; an earlier target preference alone is not that instruction. If merging is postponed, say "Delivery verified; integration postponed" and give the next action, not "cycle closed". A successful merge notice names the actual destination and says whether it was local or published; it never implies a push or promotion to `main` that did not happen. Do not mark the cycle complete until its baseline and closure gates are satisfied.

## Handoffs and multi-repository views

### Handoff

> **Handoff ready**
>
> ✔️ The specification and decisions are recorded.  
> ⏳ The current cycle is in Realize.  
> ❕ The calculation library still needs integration.  
> ➡ **Resume here: execute the integration Oracles.**

Keep exact Git refs in canonical handoff state, but show them only when requested or required to disambiguate the resume point.

### Multi-repository cycle

Show the consumer or root application first when it naturally orchestrates the product. Keep one line per participating repository and omit unrelated repositories.

```text
🧭 Cycle — New calculation format

Application · orchestrator        ⏳ Realize
├─ Display library                ✔️ Complete
└─ Calculation library            ⛔ Blocked

Integration Oracles               🟣 Pending
```

➡ **Next: unblock the calculation library.**

When all repositories are ready, use `🔷` and make integration the next action. Keep planned cycles visually separate from active repository work.

## Rendering rules and fallback

- Generate every view from current AURAE memory; never maintain it as a second source of truth.
- Render project status from the active- and planned-AURA indexes, and render phase and `phase_state` from the selected AURA's canonical fields. A blocked phase does not change an active AURA's global status.
- Prefer the vertical process view. Use a compact horizontal variant only when it is clearly more readable in the host and retains the same labels.
- Keep the default status to one process view plus at most one material state line and one bold next action.
- Summarize open or breached conditions only when they affect a blocker, handoff, decision, or next action.
- Expand to detailed cards, matrices, or multi-repository trees only when complexity or an explicit request justifies it.
- Never rely on color, an emoji, or alignment alone. The accompanying text must preserve meaning on narrow screens and for assistive technology.
- Use Mermaid only as an optional enhancement when requested or clearly useful. Always retain an equivalent text view.
- Keep generated status artifacts disposable in `.scratchpad/` unless the project explicitly publishes a report.

When Unicode or Markdown is not rendered reliably, use a plain-text fallback in the user's language:

```text
[AURA] Enterprise SSO

[OK] Assess
 |
[OK] Understand
 |
[IN PROGRESS] Realize
 |
[PENDING] Assure

[NEXT] Complete the negative session tests.
```

In a plain-text environment where bold is unavailable, the uppercase `[NEXT]`, `[RESUME HERE]`, `[ACTION REQUIRED]`, or `[DECISION REQUIRED]` label replaces Markdown bold while retaining prominence.

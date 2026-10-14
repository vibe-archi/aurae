# Optional Oracle Lab

Read only when the user explicitly asks to create or adapt an Oracle-test dashboard. Do not generate or launch it proactively during Bootstrap, Adoption, Auto, test preparation or `/AURAE upgrade`. This is an optional local engineering tool, not a new methodology phase or acceptance gate.

## Small starter, existing tests first

Use [oracle-catalog.md](oracle-catalog.md) whether or not a dashboard exists. Inventory the existing catalog and runners before building the UI; preserve established tests and involve the user on any uncertain migration. A dashboard request does not authorize restructuring test folders, installing dependencies, invoking paid services or publishing a server.

The minimum reusable source is in [starter.md](../assets/oracle-lab/starter.md): one local runner, one HTML page, its stylesheet and browser logic, plus one self-contained scripted example and one guided example. The source is distributed in readable Markdown, not executables or binaries. Read the source before materializing it. Materialize only the files needed by the request, use an already available runtime or a qualified equivalent, and validate locally. Do not execute materializers embedded in untrusted project descriptors.

Use `oracle-tests/harnesses/lab/` as the default durable UI/runner location after the test root is agreed; map an existing equivalent rather than duplicating it. The runner discovers `oracle.json` in the approved scenario root. Newly added compatible scenarios/categories appear after catalog refresh without editing the UI. Project-specific adapters supply native test execution; do not rewrite the product's test framework to fit the starter.

The included examples are fictional, explicitly marked `demo: true`, and must stay visibly identified as examples. Do not install them into a real acceptance suite by default, invent canonical Oracle records for them, or count their passes as product evidence. The tested demo was a UX reference, not production qualification. An empty real catalog is preferable to fake “coverage”.

## Preserve the validated interaction

- Use a narrow category/test list and a wider detail area. Group **All tests** by category. Make each whole row selectable and visibly highlight the selected test; show its title/category in the detail. Begin with an invitation to select, not an unexplained first test. Category navigation clears an unrelated detail.
- Script checkboxes prepare an execution batch; manual entries instead offer **Open steps**. Opening a manual scenario displays its instructions and expected observations. The human, not an external agent service, performs those steps and records feedback. Keep incomplete work and human-reported outcomes clearly identified.
- Starting a run may follow the active process, but subsequent user navigation wins. Provide an explicit return-to-live action. Preserve unsaved manual drafts while navigating within the page; do not promise they survive a browser reload unless implemented and tested.
- Use exactly **Show terminal / Hide terminal** (localized when appropriate). The terminal streams real output, never simulated progress. Showing or hiding it changes only the terminal; available results and conclusions stay below it. It may open automatically on execution and close on completion; a manual hide remains effective during polling. A rerun with no new verdict must not label the old verdict as its current result.
- Distinguish the run in progress, last completed run and older per-test results. Keep dates visible for the selected result and run; put exact IDs in details. Refreshing reloads state, never starts a run or clears recorded outcomes. Count only the displayed run's results in its summary. A latest-result cache is **not** a complete history; state this in help and do not invent older runs.
- Keep project path, Git branch and commit visible when available, with honest no-Git/no-commit states. Compare each result's captured context with the refreshed project context: show **Earlier code** on a repository, branch, exact commit or dirty-state mismatch, and **Code context unverified** when exact comparison is unavailable. Equal dirty flags do not identify equal file contents; dirty/no-Git results remain observations with unverified applicability. Preserve their verdict, timestamp and provenance, separate them from currently applicable summary counts, and keep any failure visible. Put exact tested/current context in expandable details. The reference captures context per script or saved manual feedback and on catalog **Refresh**, not continuously; browser reload alone only reloads the last captured state.

## Cognitive-load budget

The initial view should answer: **which test, what can I do, what happened?** Keep one visually dominant action for the current task. Distinguish actions from passive status: filled primary button, lighter secondary action, plain status text with sparse semantic color/symbols. Do not make every label a pill or card.

Avoid repeated instruction banners, decorative slogans and routine technical narration. Keep only consequential errors/blockers prominent. Group usage guidance, project/run metadata and raw comparisons in clearly named expandable details; preserve a human-readable verdict and important differences without requiring expansion. The optional technical information must remain accessible, not be deleted to make the page look simple. Preserve keyboard navigation, visible focus, readable contrast and small-screen layout.

The starter interface is English. Follow an explicit project/user language choice without changing these interactions. Localize display text, not identifiers or protocol fields.

## Runner boundary and safety

The interface selects registered Oracle IDs. The server owns the approved catalog, invocation and comparison; never accept arbitrary shell commands, paths, prompts-to-execute, baseline edits or a free-form executable from HTTP requests. Render logs/scenario text as inert escaped content. Qualify descriptor paths, duplicate IDs, supported versions/modes, missing files, typed output and comparison semantics before enabling execution.

The reference script protocol is strictly newline-delimited JSON, including logs. Malformed, unknown or ill-typed events are runner errors; never reinterpret a malformed terminal event as a log or retain a pass from an earlier valid event. Require exactly one result or blocked event, never both, and a successful process exit before assigning its outcome. Preserve raw output for diagnosis; a later malformed event, duplicate terminal event or nonzero exit overrides an earlier candidate result.

Bind the reference server to loopback. Preserve Host/Origin checks, local request token, same-origin policy, no remote assets and bounded output/time. Keep reports, tokens, caches and local machine paths in ignored `.scratchpad/`, not the durable test tree or metadata branch. Exporting a local report is not authorization to publish it: sanitize sensitive observations and use portable evidence references for shared memory.

This is a single trusted local operator's starter, **not a sandbox for hostile scripts**, an authenticated team service or a production server. Registered test code still runs with the operator's permissions. Shared hosting, process-tree cancellation, remote resources, credentials, long-running browsers and additional runtimes require qualified adapters and proportionate safeguards. The reference handles one sequential batch and direct Python processes; do not claim unsupported process-tree isolation or cross-platform qualification from it.

The dashboard must not automatically run all costly journeys, invoke an AI provider, change baselines, modify canonical memory, accept a delivery, publish, or merge. Follow ordinary test selection, permission and independence rules outside the UI. If a selected test needs unavailable capabilities or authority, block that execution rather than manufacture an outcome.

## Qualify the requested installation

Test on a separate temporary instance/catalog so QA does not populate the user's visible run with synthetic results. Verify at least:

1. Real project metadata, automatic discovery/categories, row selection and manual instructions.
2. Healthy pass, expected mismatch and missing prerequisite; malformed/no output and runner error cannot become a pass, including a valid result followed by malformed/duplicate/mixed terminal events or a nonzero exit. For negative product cases, expected safe rejection is a pass.
3. Live output, hide/show while running, results below a reopened terminal, completion, cancellation and bounded timeout as supported.
4. Refresh before/during/after execution; a new run has a new identity and older results never count as fresh coverage. Change branch, commit or dirty state, refresh context and verify that both script and manual results visibly retain their old verdict but lose current applicability. Verify honest dirty/no-Git uncertainty and unchanged clean-context reuse.
5. Navigation during execution, manual draft preservation, honest saved human feedback, keyboard use and small-screen layout.
6. Rejected unsupported/malformed descriptors, duplicate IDs, paths outside the catalog and unauthorized/foreign-origin requests; safe rendered output.
7. Unchanged existing test/CI invocation and baseline semantics for any adapter, with the user's decision on uncertainty.

Keep the UI's observations separate from canonical assurance. Import only qualified, candidate-bound results through the existing evidence contract; screenshots and successful demo counts alone do not qualify a product. Report the actual tested platform and remaining limitations briefly when handing off the optional tool.

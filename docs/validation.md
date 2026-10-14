# Local packaging validation — 2026-10-11

Scope: the initial repository preparation and development packages for skill 1.17.1.
Environment exercised: Windows, Python 3.11.2, PyYAML 6.0.2 and jsonschema 4.26.0.

## Results

- 22 automated tests passed; 1 Bash-specific test was skipped on Windows.
- Both ZIPs were built, extracted and verified. Their skill payloads are identical;
  only the agent installation prefix differs.
- Repeated builds produced byte-identical assets. The source skill was not mutated.
- Official and simulated private distributions passed. Invalid profiles, missing
  private configuration, unsafe paths, tampering and output replacement were rejected.
- A disposable Git repository exercised release-build checks: matching tag, clean
  tree and successful builds without a license file. No actual GitHub release was created.
- The documented PowerShell commands installed both packages with a local simulated
  download, rejected corruption and refused to overwrite existing installations.
- The embedded validator passed 25 cases; the Storage Harness passed its self-test;
  the merge companion passed 21 cases, using only disposable repositories.
- The skill-creator structural validator accepted the extracted Codex skill.
- Workflow YAML parsed successfully; generated paths are ignored by local Git.

## Preservation

The originally installed skill remains 1.17.0 and passes its existing exhaustive
manifest validation. In the new source copy, operational instructions and helper
implementations are preserved, apart from LF normalization. Only version/release
notes and the manufacturing manifest differ. The generated profile remains part of
each complete installed bundle, not a runtime override.

## Not yet demonstrated

The GitHub-hosted CI matrix, actual release publication, authenticated private asset
download, Bash installation on Linux/macOS and live skill discovery in both agent
applications have not been exercised in this local preparation. The configured CI
matrix will run the platform-appropriate tests after the repository is published.

The local ZIPs are development builds with no source commit, not published release
artifacts. A reviewed release commit and explicitly authorized tag publication
remain necessary before the first release. License selection is deferred and is not
a prerequisite for publication or builds.

## Independent assurance rules validation — 2026-10-14

Scope: skill 1.18.0 and methodology 1.5.0, prepared locally as development versions.
The earlier report above describes its own historical preparation, not the current
publication status of 1.17.1.

- The automated suite passed 22 tests; 1 Bash-specific test was skipped on Windows.
  Installation fixtures use the generated build version while exercising the
  documented commands; corrupt archives must fail specifically on checksum mismatch.
- Both development ZIPs were built and verified, including exhaustive file hashes,
  reference links, distribution profile and matching platform payloads. The extracted
  Codex skill also passed structural validation.
- An independent, read-only agent evaluated the final extracted package against
  eight decision exercises: unrelated versus in-scope defects; merged multi-branch
  candidates; repeated serious findings after repairs; admissible conditional
  closure; unsafe residual defects in Auto mode; human-only assurance; changed merge
  targets; and an upgrade during an ongoing verification. No actionable contradiction
  was found on these paths. These exercises do not guarantee every future execution.
- The evaluated skill manifest SHA-256 is
  `92b09fb9482f6f77949272a1bcea2f889a6e55b27960b7fd5370a94f9fd13445`.
  The skill payload was not changed after this evaluation.
- Workspace schemas and embedded helper implementations remain unchanged. Their
  dedicated runtime self-tests were not rerun for this instruction-only update.
- No live project workflow, hosted CI, commit, tag or remote publication was performed
  for this update. The installed skill and the private-distribution checkout remain unchanged.

## Consistency corrections 1–4 — 2026-10-14

Scope: development skill 1.18.1, methodology 1.5.0, Validator 1.1.1,
Storage 1.0.1 and merge companion 1.0.1. Only the first four findings of the
consistency review are addressed: accepted-product binding, genuine cycle
creation, coordinated pre-landing assurance and metadata-ref preservation.
The remaining review findings are deferred. Persisted formats are unchanged.

- The final automated suite passed 24 tests; 1 Bash-specific test was skipped
  on Windows. Both complete development archives were built and verified;
  the extracted Codex skill passed structural validation.
- The final helper set passed 76 validator cases, the real-Git Storage self-test
  and 32 merge cases. Reports are local under
  `.scratchpad/helper-tests/run-k7kcoog6/`. Git environment overrides were removed
  only from the test subprocess, without modifying global configuration.
- Independent validator review passed 26 additional exercises, including a
  same-ID non-cycle that must not manufacture prior phase history or bypass
  activation conditions. Acceptance, coordinated delivery and historical
  conditional-to-final promotion remained valid on the tested paths.
- Independent Storage review exercised dirty developer/metadata worktrees,
  direct and symbolic publication paths, missing-direct-ref bootstrap, refusal
  without mutation, normal publication and recovery using the preserved commit.
  Its final focused Windows case-alias retest confirmed preservation when
  `aurae/META` resolves the checked-out `aurae/meta` ref. The final packaged
  self-test then passed with all direct, symbolic and case-variant guards.
- Cross-review of the merge companion confirmed actual parent-child history
  validation and snapshot-only composition, without fabricated transitions or
  rewriting historical conditional baselines.

Final reviewed source SHA-256 digests:

- Validator: `5774a015fc6b548c5af09b8f8f54e5b000ac8e0c2e1927471a79dab080a2b592`
- Storage: `faff561fc897f81a76e304636bb981e69fb4ecb7f944976e8c4a637827f2436b`
- Merge: `cb871b11b41705a8215b5e7761b6e09ce5c1278914176a98d2b08bbeeaf407b7`

The final development package manifest digest is
`aa8db09a1323c91c505d71c22993446b4cb9d8f6c33ee878a84460503ae08eb7`;
archives are in `.scratchpad/review-fixes-1.18.1-final/`.

Limits: exercised on Windows with Python 3.11.2 and Git 2.49.0.windows.1,
not Linux/macOS or hosted CI. Structural validation does not prove that product
commits contain the claimed work or that evidence is truthful. The Storage
review's binding stubs do not replace semantic Workspace validation; the
integrated merge suite uses the real validator. Ref preflight is not an atomic
lock against unrelated external checkout changes. No actual project adoption,
product merge, installation, commit, tag or remote publication was performed.
The installed skill remains 1.17.0; the private-distribution checkout is unchanged.

## Consistency corrections 5–10 — 2026-10-14

Scope: development skill 1.18.2, methodology 1.5.0. Completes the remaining
review findings: reproducible Bootstrap starting state, initial-interview
checkpoints, non-delivery closure, append-only multi-repository restoration,
strict Oracle Lab output and visible result/code-context applicability.
Workspace, Storage Contract, bundle format and helper sources are unchanged
from the preceding 1.18.1 qualification; no migration is required.

- The automated suite passed 36 tests; one Bash-specific test was skipped on
  Windows. Six new entry/lifecycle tests exercise the actual validator with
  partial entry, AS-IS starting-state registration, Markdown byte binding,
  clean closure before Realize and a recovery cycle with separate validated
  phase transitions. They also reject invalid pins, wrong closure outcomes
  and backward baseline pointers while preserving accepted history.
- Six Oracle Lab tests exercise the materialized starter, including real
  subprocess output and the actual JavaScript with inert DOM boundaries.
  Malformed events before or after a valid result, duplicate/mixed terminal
  events, unknown or ill-typed events, missing results and nonzero exits cannot
  produce a pass. Healthy pass, mismatch and prerequisite block remain distinct.
  Script/manual context capture, stale/uncertain result notices, separate
  current counts and retained historical failures are covered.
- Independent forward review exercised five scenarios: entry pause/resume at
  Q4/9, including missing Git; existing code without an approved initial commit;
  abandonment in Assess; restoring an older multi-repository combination with
  a missing/offline participant and unrelated edits; and an obsolete entry
  checkpoint after accepted progress. One pre-Git ignore-verification ambiguity
  was corrected and independently rechecked against the final package. No
  further blocking contradiction was found on these paths.
- Independent real-browser smoke testing passed in Chrome 154 on Windows x64,
  using a disposable Git fixture and port 57585. It covered grouped categories,
  selection, live terminal/hide/reopen with results retained, navigation during
  execution, manual draft/feedback, distinct run identity, reload without rerun,
  refreshed commit changes and dirty-context notices, and a 390px layout without
  horizontal overflow. The console had no errors or warnings. Screenshots remain
  local in `.scratchpad/oracle-browser-20261014-ep1/`; that server was stopped
  and its port verified closed. The existing demo on port 8765 was untouched.
- Both complete Codex/Claude development ZIPs passed integrity, manifest,
  distribution and local-link checks. The extracted final Codex package passed
  the skill-creator structural validator. Independent review confirmed the
  final pre-Git/resume wording matches the reviewed sources after LF normalization.
- The unchanged helper set passed 76 validator cases, the real-Git Storage
  self-test and all 32 merge cases. The aggregate runner's merge attempt exceeded
  its 180-second limit; a separate unchanged-source retry with a 360-second limit
  completed successfully in about 291 seconds. This is a test-duration limitation,
  not a passed first attempt. Validator/Storage reports remain under
  `.scratchpad/helper-tests/run-n_34knke/`; the successful merge report is
  `merge-self-test-d500ee57a70f4257b4ea85be4fd4a68a/result.json` beneath it.
- Every normalized final build input was rechecked against its recorded hash;
  the tested package still matches the current skill sources.

Final package manifest SHA-256:
`7fa2c6054b04005f9da2dbb2b4f47851709bf528630567e581a512f053441e31`.
Development archives: `.scratchpad/review-followup-1.18.2-final/`.

Limits: validation was local on Windows, Python 3.11.2, Node 24.18.0 and Git
2.49.0.windows.1, not hosted CI or Linux/macOS. Entry/recovery fixtures verify
schema and transition semantics, not actual product commit contents, faithful
interview capture or environment restoration. Browser fixtures are not product
assurance; exhaustive accessibility, cancellation and cross-platform UI testing
remain outside this patch's qualification. Code context is refreshed explicitly,
not continuously monitored; dirty/no-Git observations remain unverified for
exact-code applicability. No real project adoption/recovery, source-repository
commit, tag, remote publication, installation or private-distribution change was performed.

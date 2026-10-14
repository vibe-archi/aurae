# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.18.2] - 2026-10-15

### Fixed

- Prevent premature product acceptance and invented prior cycle phases in new project-memory writes.
- Allow coordinated deliveries to be independently verified before their final, authorized merge.
- Refuse memory publication before it can disturb a branch open in another Git worktree.
- Clarify the reproducible starting state for new projects and preserve interrupted
  initial interviews before a development cycle exists.
- Allow clean cancellation without pretending a delivery occurred; preserve history
  when restoring a previous multi-repository combination.
- Reject malformed Oracle Lab output even after a valid result, and distinguish
  results tied to earlier or unverified code from currently applicable results.
- Allow the complete Git merge self-test sufficient bounded time on slower hosts.

### Changed

- Independent agents report defects without repairing the product; unrelated findings
  are proposed for a suitable future cycle, the backlog, or an explicitly approved scope increase.
- Final independent verification covers the stable, merged delivery; branch-level
  checks remain with the host agent, and product-branch merges still require permission.
- Repeated serious failures trigger root-cause analysis before further repairs.
- Persistent defects can be brought to the human for conditional closure and scoped
  stabilization work, without hiding failures or bypassing required assurance.

## [1.17.1] - 2026-10-11

### Added

- Ready-to-extract, project-local skill packages for Codex and Claude Code.
- Client distribution profiles generated during the build, with preserved official origins.
- Automated package checks and GitHub release preparation for public and private repositories.
- Installation and private-distribution guides.

### Changed

- Packaged skill 1.17.1 for reproducible distribution without changing the methodology,
  project-memory format or existing engineering workflows.
- Deferred license selection without blocking repository publication or package builds.

Earlier methodology changes remain documented in the skill's release impact ledger.
This packaging repository does not reconstruct or invent historical release dates.

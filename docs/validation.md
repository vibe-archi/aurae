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

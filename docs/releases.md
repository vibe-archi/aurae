# Release workflow

## Before the first publication

1. Confirm the intended publication scope. No license file is included at this stage;
   its absence does not block publication or builds.
2. Review the source and the packaging tools. Configure the intended GitHub remote.
3. Protect `main` and version tags; configure required reviewers on the `release`
   GitHub environment if publication should require a human approval.
4. For a client repository, set the reviewed `AURAE_VENDOR_CONFIG` repository variable.
5. Run CI on Linux, Windows and macOS. A local Windows pass alone does not qualify the
   other platforms. Tag only a commit whose required CI checks passed.

The workflows use full commit pins for official GitHub actions, read-only build jobs
and a separate publishing job with `contents: write`. Pull requests neither publish
nor receive the client profile variable. Review and update action pins periodically.

## Prepare a release

1. Update `agent_skill` in `skills/aurae/aurae-skill.yaml` and the canonical release
   block in `skills/aurae/references/versioning-and-releases.md` together. The initial
   prepared version is **1.17.1**. Change other components only when their contracts change.
2. Add the minimal compatibility impact to `references/upgrade.md`. Record changes
   in `CHANGELOG.md`; move them from Unreleased to the confirmed version/date when releasing.
   Update the release reference's status/date at that point, not before.
3. Review and commit the intended changes. Run the tests and a local build/verification.
4. After explicit publication approval, create and push the matching `vMAJOR.MINOR.PATCH`
   tag to the intended repository. This is the remote publishing action; a local build
   never creates a commit, tag, push or release.

The tag workflow runs package tests and all three embedded helper self-tests, resolves
the profile once, builds both archives, verifies them and uploads the verified files
for the publishing job. Publishing creates a draft with its assets before making it
visible. An existing release causes failure; assets are never silently replaced.
If a failure leaves a draft, inspect it before any manual recovery. Do not delete a
published release or move its tag to rerun with different content.

## Release assets

```text
aurae-codex-1.17.1.zip
aurae-claude-1.17.1.zip
SHA256SUMS
build-info.json
```

Each archive contains only the complete skill below its agent-specific project path.
`build-info.json` includes the resolved vendor profile, source commit and build-input
hashes. Its own digest is in `SHA256SUMS`; it does not attempt to hash itself.
ZIPs have fixed entry ordering, timestamps, permissions and uncompressed storage for
byte-stable output across supported platforms. The input dependency versions are pinned.

Checksums prove integrity against a trusted reference, **not publisher authenticity**.
Obtain both from a trusted release and review the package before activation. Signing
or attestations are possible future additions, not claims made by this first version.

## Commands for maintainers

```sh
python -B -m unittest discover -s tests -v
python -B tools/selftest.py
python -B tools/build.py --repository vibe-archi/aurae --output .scratchpad/release-check
python -B tools/verify.py .scratchpad/release-check
```

`--release` additionally requires a clean committed Git checkout, a matching version
tag pointing at HEAD. A license file is not required.
Development builds report missing commit/dirty state honestly and cannot be mistaken
for release-qualified output in `build-info.json`.

Helper test repositories, materialized Python and logs remain under `.scratchpad/`.
They do not alter the developer's code branches or global Git configuration. Inspect
failed fixtures there; do not weaken a helper's safety check merely to pass CI.

References: [GitHub Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use)
and [GitHub CLI release creation](https://cli.github.com/manual/gh_release_create).

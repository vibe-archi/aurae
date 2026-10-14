# Private distributions

Use the same repository structure and workflows in a private GitHub repository.
Keep the skill in `skills/aurae/`; add reviewed company-wide references there when
needed and list them in its source `aurae-skill.yaml`. Product-specific instructions
belong in the consuming project, not the organization-wide distribution.

## Configure the build

Create the repository Actions **variable** `AURAE_VENDOR_CONFIG` with a JSON object:

```json
{
  "distribution": {
    "id": "example-engineering",
    "name": "Example Engineering",
    "repository": "https://github.com/example/aurae-private",
    "base_agent_skill": "1.18.2"
  },
  "instructions": "Use the organization's approved engineering conventions.\nKeep all protected decisions."
}
```

Replace the example identity and repository. Keep the ID stable. Record the actual
official version used as the base, not the numerically largest available version.
The distribution repository must match the repository executing the release workflow.
A fork without configuration fails instead of producing an official-looking package.

The builder resolves **tracked defaults + this complete distribution override**, then
validates against `packaging/vendor.schema.json`. Official origin URLs cannot be
overridden by this variable. The resulting `vendor.md` is generated only in packages,
before their exhaustive file hashes are calculated. Both platforms receive one exact profile.

This first version supports GitHub.com public/private repositories. GitHub Enterprise
and other hosts need an explicit schema/workflow adaptation; they are not silently accepted.

For local builds, put the same JSON in ignored `packaging/vendor.local.json`:

```sh
python -B tools/build.py --repository example/aurae-private --vendor-config packaging/vendor.local.json
python -B tools/verify.py dist/1.18.2
```

The local file and a non-empty `AURAE_VENDOR_CONFIG` environment variable are mutually
exclusive. Only `distribution` and `instructions` are accepted override keys. Text is
rendered as content, never evaluated as shell commands or template expressions.

## Versioning and traceability

Use your own `agent_skill` version series. Update it in the source descriptor and the
canonical release block in `references/versioning-and-releases.md`; keep them equal.
Add client changes to the release impact ledger. Do not compare version numbers
across different distribution IDs as if they were one release series.

Every profile or instruction change requires a new package version and tag. GitHub
variables can change without a Git commit, so `build-info.json` freezes the exact
resolved profile, source revision, input hashes and package hashes with each release.
To reproduce a private release, check out that revision and use its archived profile's
`distribution` and `instructions` as the override—not today's repository variable.

The same Git tag must never produce a replacement published package. The workflow
refuses an existing release; it does not use `--clobber` or rewrite tags. Enable GitHub
immutable releases and protect `v*` tags where available for server-side enforcement.

## Confidentiality and trust

**The variable is not a secret. Everything embedded in `vendor.md` and `build-info.json`
is readable by anyone with access to the package.** Never put credentials, access
tokens, personal data or machine paths there. The builder catches some obvious token
formats; it is not a comprehensive secret scanner. Review the resulting profile.

Keep the repository, release assets and workflow artifacts private. Package privacy
does not replace review or activation consent. Client instructions cannot waive AURAE's
protected decisions, safety boundaries or required evidence. They do not enable online upgrades.

Consumers install from your private releases using their existing authorized GitHub
CLI session. No token belongs in a URL or command example. See [installation](install.md).

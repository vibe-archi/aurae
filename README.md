# AURAE

The skill that brings **Agentic Unified Risk-Aware Engineering** to your projects:
a collaborative human–AI methodology for reliable, robust and maintainable software,
with risk-proportionate checks and less cognitive load.

Work progresses through **Assess → Understand → Realize → Assure**. Humans stay at
the center of important decisions and retain an understanding of their project,
including AI-generated code.

Official sources: [aurae.md](https://aurae.md) · [GitHub](https://github.com/vibe-archi/aurae).

## Install in a project

Download the matching ZIP from a trusted, published release and extract it at your
project root. No Node.js, npx, Python or plugin marketplace is needed to use the skill.

| Agent | Release archive | Installed location |
|---|---|---|
| Codex | `aurae-codex-<version>.zip` | `.agents/skills/aurae/` |
| Claude Code | `aurae-claude-<version>.zip` | `.claude/skills/aurae/` |

Review the publisher and package before enabling it. Start a new agent session after
installation. Ask it to use AURAE to adopt your project or start your next cycle.
Installation alone does not initialize project memory, modify code or authorize a push.

**Keep the complete installed folder in your project, including `vendor.md` and
`aurae-skill.yaml`.** Do not copy this manufacturing repository's vendor ignore rule
into a consumer project. Preserve LF bytes when committing installed packages;
see [installation and upgrades](docs/install.md), including one-line first installs.

The source under `skills/aurae/` is deliberately incomplete: the build generates the
vendor profile and final integrity manifest. Install a release ZIP, not a raw-source
GitHub skill shortcut. Global installation and plugin packaging are outside this version.

## Build and verify

For contributors only: Python 3.11+ and Git are required.

```sh
python -m pip install -r requirements-dev.txt
python -B -m unittest discover -s tests -v
python -B tools/selftest.py
python -B tools/build.py --repository vibe-archi/aurae --output dist/local-check
python -B tools/verify.py dist/local-check
```

These commands create local development packages, not a published release. Reusing a
non-empty output directory is refused; use a fresh directory under `.scratchpad/` or
`dist/` for another build. The installed skill itself needs neither build dependencies
nor executable helpers: its existing helper sources remain distributed as Markdown.

## Repository layout

```text
skills/aurae/         One source skill, resources and source build descriptor
packaging/           Vendor template, official defaults and validation schema
tools/               Offline build, verification and helper self-tests
tests/               Positive and negative packaging tests
docs/                Installation, private distributions and release instructions
.github/workflows/   Cross-platform checks and tag-triggered releases
dist/                Generated ZIPs, checksums and build information (ignored)
.scratchpad/         Disposable local test work (ignored)
```

Codex and Claude archives contain the same complete skill. Only their installation
prefix differs. All files are explicitly inventoried; unrelated repository content
is excluded. Builds use stable ordering, LF text and fixed ZIP metadata.

## Private distributions and releases

- [Private distributions](docs/private-distributions.md): configure a client-specific
  identity and instructions using `AURAE_VENDOR_CONFIG`; keep official origins visible.
- [Release workflow](docs/releases.md): a version tag builds, verifies and publishes
  both ZIPs, their checksums and the exact resolved build profile.

`/AURAE upgrade` remains local-first. Installing a newer package and bringing project
memory forward are separate operations. Automatic online release checking is not implemented.

## Publication status and license

Version tags trigger package validation and publication. Download available packages
from [GitHub Releases](https://github.com/vibe-archi/aurae/releases).
No license file is included at this stage. License selection is deferred and does
not block repository publication or package builds.

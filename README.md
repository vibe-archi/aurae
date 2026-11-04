# AURAE

The skill that brings **Agentic Unified Risk-Aware Engineering** to your projects:
a collaborative human–AI methodology for reliable, robust and maintainable software,
with risk-proportionate checks and less cognitive load.

Work progresses through **Assess → Understand → Realize → Assure**. Humans stay at
the center of important decisions and retain an understanding of their project,
including AI-generated code.

Official sources: [aurae.md](https://aurae.md) · [GitHub](https://github.com/vibe-archi/aurae).

## Working with pstack

AURAE includes an isolated [pstack/poteto integration](skills/aurae/integrations/pstack/INTEGRATION.md).
A lightweight [index](skills/aurae/integrations/index.md) checks local availability;
without a match, the integration is not loaded and normal AURAE work is unchanged.
When detected, its explicit block is added to the project's effective agent instructions
under the normal consent rules. The integration does not install pstack or
enable an autonomous mode automatically. Explicit AURAE Auto and poteto can be used
together while retaining cycle gates, scoped permissions and independent assurance.
The instructions are portable across hosts; actual tools and protection mechanisms
are checked locally, not assumed identical or universally enforced.

## Install in a project

**Open a terminal at your project root, then run the command for your agent.**
The installer downloads the latest published official release, checks its SHA-256,
and installs only in this project. First installation refuses to overwrite an
existing skill; use the explicit [update mode](#update-an-existing-skill) below.

### Windows — PowerShell

Codex:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.ps1' -ErrorAction Stop))) -Agent codex
```

Claude Code:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.ps1' -ErrorAction Stop))) -Agent claude
```

### Linux / macOS — Bash

Codex:

```bash
(set -o pipefail; curl -fsSL https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.sh | bash -s -- --agent codex)
```

Claude Code:

```bash
(set -o pipefail; curl -fsSL https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.sh | bash -s -- --agent claude)
```

These commands execute the official installer. You can inspect
[PowerShell](tools/install.ps1) or [Bash](tools/install.sh) first, or
[download and extract a release manually](docs/install.md#manual-installation).
Windows needs PowerShell 5.1+; Linux/macOS needs Bash, `curl`, `unzip`, `awk`, and
`sha256sum` or `shasum`. No GitHub CLI, Node.js, npx, Python or plugin marketplace is needed.

| Agent | Release archive | Installed location |
|---|---|---|
| Codex | `aurae-codex-<version>.zip` | `.agents/skills/aurae/` |
| Claude Code | `aurae-claude-<version>.zip` | `.claude/skills/aurae/` |

Review the publisher and package before enabling it. **Start a new agent session after
installation.**
Ask it to use AURAE to adopt your project or start your next cycle.
Installation alone does not initialize project memory, modify code or authorize a push.

**Keep the complete installed folder in your project, including `vendor.md` and
`aurae-skill.yaml`.** Do not copy this manufacturing repository's vendor ignore rule
into a consumer project. Preserve LF bytes when committing installed packages;
see [installation and upgrades](docs/install.md), including version selection and
private distributions. The quick installers above target the official public distribution only.

The source under `skills/aurae/` is deliberately incomplete: the build generates the
vendor profile and final integrity manifest. Install a release ZIP, not a raw-source
GitHub skill shortcut. Global installation and plugin packaging are outside this version.

## Update an existing skill

Pause or finish your agent's work, then run the matching command at your project root.
Add **`-Update`** on Windows or **`--update`** on Linux/macOS:

### Windows — PowerShell

Codex:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.ps1' -ErrorAction Stop))) -Agent codex -Update
```

Claude Code:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.ps1' -ErrorAction Stop))) -Agent claude -Update
```

### Linux / macOS — Bash

Codex:

```bash
(set -o pipefail; curl -fsSL https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.sh | bash -s -- --agent codex --update)
```

Claude Code:

```bash
(set -o pipefail; curl -fsSL https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.sh | bash -s -- --agent claude --update)
```

An unchanged official installation is checked against its original published package.
If the old archive was never published, update mode can also replace a recognized
local copy, including older manual installations, after backing up its actual files.
Local additions are kept in that backup, not merged into the new skill. Private or
ambiguous distribution profiles remain protected.

The new package is verified before replacement, and a recoverable backup is retained
outside the project at the printed path. An already-current official copy is left
alone; downgrades and edits to an available published package are refused. If
replacement fails, the installer attempts to restore the old folder.

**Start a new agent session, then run `/AURAE upgrade`** to bring the project's memory
forward. The installer itself does not change project memory, code or Git settings.
See [update safeguards and recovery](docs/install.md#upgrading-an-existing-installation).

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
tools/               Public installers, offline build, verification and self-tests
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

`/AURAE upgrade` remains local-first and does not check online for releases.
Downloading a package with the installer and bringing project memory forward are
separate operations.

## Publication status and license

Version tags trigger package validation and publication. Download available packages
from [GitHub Releases](https://github.com/vibe-archi/aurae/releases).
No license file is included at this stage. License selection is deferred and does
not block repository publication or package builds.

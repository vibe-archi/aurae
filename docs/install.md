# Project-local installation

Install a **built release ZIP**, not the repository's raw `skills/aurae` directory.
The latter is a manufacturing source: it has no generated vendor profile and no
installable manifest. Use the optional official installer below, or download and
extract a release manually. Neither method needs npm or a global skill installation.

Codex reads project skills under `.agents/skills/` ([official documentation](https://learn.chatgpt.com/docs/build-skills)).
Claude Code reads `.claude/skills/` ([official documentation](https://code.claude.com/docs/en/skills)).
The ZIPs already contain these paths. Run installation from the intended project root.

## One-line first installation

Open a terminal **at the intended project root**. No existing Git repository or
`.scratchpad` folder is needed. These commands execute a script from the official
public repository and install the latest published release, not unreleased source.

### Windows — PowerShell

Requires Windows PowerShell 5.1 or newer. For Codex:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.ps1' -ErrorAction Stop))) -Agent codex
```

For Claude Code:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.ps1' -ErrorAction Stop))) -Agent claude
```

### Linux / macOS — Bash

Requires Bash, `curl`, `unzip`, `awk`, and either `sha256sum` or `shasum`. For Codex:

```bash
(set -o pipefail; curl -fsSL https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.sh | bash -s -- --agent codex)
```

For Claude Code:

```bash
(set -o pipefail; curl -fsSL https://raw.githubusercontent.com/vibe-archi/aurae/main/tools/install.sh | bash -s -- --agent claude)
```

The installer resolves a release once, downloads its ZIP and `SHA256SUMS` from that
same tag, and checks the archive before extracting it. It rejects unexpected paths,
unsafe archive entries and symbolic-link/junction destinations. It stages the complete
skill before placing it in `.agents/skills/aurae/` (Codex) or `.claude/skills/aurae/`
(Claude Code). Temporary download/staging folders are removed after the attempt.

Without the explicit update option, an existing skill is never overwritten: use
the [upgrade procedure](#upgrading-an-existing-installation).
Installation does not edit AGENTS.md, CLAUDE.md, Git configuration, project memory,
or a global installation. Start a new agent session, then ask it to use AURAE.

### Choose a version or inspect the installer

Append `-Version 1.18.2` to the PowerShell command, or add `--version 1.18.2` before
the closing `)` in the Bash command, replacing the example with a published version.
This pins the **package**; the commands still fetch the current installer from `main`.
To pin or review the installer too, download it from a trusted exact repository
revision, inspect it, and run the saved script from your project root.

The scripts are [tools/install.ps1](../tools/install.ps1) and
[tools/install.sh](../tools/install.sh). They require no GitHub sign-in, `gh`,
Node.js or Python. They support the official public distribution only; private
distributions use the manual/authenticated path below in this iteration.

The remote script is executable code: review its publisher before running it.
A SHA-256 match checks download integrity, not independent publisher authenticity.
If release discovery is unavailable or rate-limited, choose a known published version
explicitly or use a browser download. Failed downloads do not install a skill.

## Manual installation

1. Select an existing version from your trusted repository's GitHub Releases.
2. Download its `aurae-codex-<version>.zip` or `aurae-claude-<version>.zip` and `SHA256SUMS`.
3. Compare the archive's SHA-256 with the matching entry before extraction.
4. If the target skill folder already exists, follow the upgrade procedure below;
   do not extract over it. Otherwise extract the ZIP at the project root.
5. Review the installed profile/instructions, then start a new agent session.

Do not use a destination whose `.agents`/`.claude` or `skills` ancestors are symbolic
links or junctions. Use only the expected archive from the trusted publisher; checksums
are an integrity check, not an independent proof of who published it.

For private repositories, sign in to GitHub CLI through its normal authentication
flow with access to that repository, or download in an authenticated browser. Do not
run the official quick installer for a private distribution: it always selects the
official public package. For example, adapt the repository and published version in:

```sh
gh release download v1.18.2 --repo YOUR-ORG/aurae --pattern aurae-codex-1.18.2.zip --pattern SHA256SUMS --dir aurae-download
```

Select the `claude` ZIP instead when appropriate, and use a new download directory
outside the project or inside its ignored `.scratchpad/`. Then follow the checksum
and extraction steps above. Never put credentials in command text. The new public
installers do not change private distribution behavior.

## Sharing through the project

Commit the complete installed skill when it should travel with project clones.
**Do not ignore the installed `vendor.md`.** The ignore rule in AURAE's manufacturing
repository applies only there. The generated profile and manifest belong together.

Preserve LF text bytes, especially on Windows with Git automatic line-ending conversion.
After reviewing the existing `.gitattributes`, add the applicable rule if needed:

```gitattributes
.agents/skills/aurae/** text eol=lf
.claude/skills/aurae/** text eol=lf
```

Do not replace the project's existing attributes or silently remove its filters.
Revalidate the package after checkout if a project uses content filters. AURAE also
supports a separate `aurae/skill` recovery branch after adoption; this installation
step does not create or publish it. Each recipient retains their local approval duties.

## Upgrading an existing installation

### Update an existing installation

Pause or finish the running agent's work first. From the same project root, add
`-Update` to the PowerShell command or `--update` before the closing `)` in the Bash
command. The [README has all four ready-to-copy update commands](../README.md#update-an-existing-skill).
Combine the update option with `-Version` / `--version` to choose a particular
published version instead of the latest release. An existing installation is required;
without one, use the normal first-installation command.
On Linux/macOS, update mode also uses the standard `find`, `diff`, and `cp` commands.

The updater checks the installed version and looks for its original official ZIP:

- When available, it verifies the archive and compares the complete installed contents
  with it, not just the locally editable manifest. Missing, added or edited files stop
  the operation without replacing the skill.
- If that old archive returns HTTP 404, the update can proceed from a recognized local
  installation without an extra option. It backs up the actual local folder, including
  additional files, hidden files and empty directories. Those additions are preserved
  for recovery; they are not merged into the new skill.

This fallback requires a readable AURAE bundle manifest and nonempty `SKILL.md`.
If `vendor.md` exists, it must match the verified target's official profile (ignoring
line-ending differences). A missing vendor profile is accepted only for legacy
versions older than 1.17.0, before distribution profiles were introduced. This is
compatibility checking, not proof of the local copy's origin. Private, customized or
ambiguous profiles, linked paths and unrecognized installations are refused.

Only a missing **old archive** permits this fallback. Network failures, access errors,
missing checksums and corrupt archives still stop the update. The target release must
always be fully verified. There is no force-overwrite option or automatic merge of
local adaptations; use the manual procedure below when a check refuses an update.

An already-current official copy is left unchanged, without creating a backup. A
requested older version is refused. For a newer version, the new package is verified
and staged before the installed folder is changed. Recovery information and either
the verified original `skill.zip`, or a checked snapshot of the actual local folder
named `previous-skill/`, are retained outside the project:

- Windows: `%LOCALAPPDATA%/AURAE/skill-backups/`.
- Linux/macOS: `${XDG_STATE_HOME:-$HOME/.local/state}/aurae/skill-backups/`.

The actual unique backup path is printed. These are recovery backups, not additional
discoverable skills; they are not automatically deleted or committed to the project.
An unsafe or project-local backup location is refused. Temporary download and staging
folders are separate from these retained backups.

The old folder is moved aside and the complete new folder takes its place; removed
files do not survive as they would with ZIP overlays. The updater rechecks the old
contents before replacement and refuses to overwrite a newly appeared target. On a
detected promotion failure it attempts to put the old folder back. If restoration is
blocked, it retains the recovery material and reports its location rather than deleting
the last usable copy. This is not a guarantee of uninterrupted access or power-loss atomicity;
do not run an agent or another updater against the same skill during replacement.

After success, **start a new agent session and run `/AURAE upgrade`**. Replacing the
skill and adapting the project's Git-backed memory are separate operations. The updater
does not edit code, project memory, Git configuration, or a global skill installation.

To recover manually, stop the agent and preserve any newer/customized installation.
For a `skill.zip` backup, extract it into a separate directory; for a `previous-skill/`
backup, use that complete folder. Review it, then restore the complete skill folder
to the original agent location. Follow the recovery information next to the backup;
never overlay an installed folder with older files.

### Private or customized installations and manual recovery

Download and verify the new package into a separate directory. Compare its version,
distribution and instructions against the installed copy. Keep private adaptations;
an official release with a larger number is not an upgrade of a client distribution.

After approval, back up or preserve the old complete folder and replace it as a whole.
Do not overlay ZIPs: removed reference files would otherwise survive and invalidate
the exhaustive manifest. Restart the agent, then ask for `/AURAE upgrade` to refresh
the project's recorded bundle from the approved local skill. The active phase stays
intact; earlier-phase consequences are deferred to a safe boundary.

`/AURAE upgrade` does not check GitHub for updates and does not grant remote push or
product-code merge permission. An explicitly run installer/update command downloads
the selected package; it does not authorize those project operations.

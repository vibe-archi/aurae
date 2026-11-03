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

### Update an unchanged official installation

Pause or finish the running agent's work first. From the same project root, add
`-Update` to the PowerShell command or `--update` before the closing `)` in the Bash
command. The [README has all four ready-to-copy update commands](../README.md#update-an-existing-skill).
Combine the update option with `-Version` / `--version` to choose a particular
published version instead of the latest release. An existing installation is required;
without one, use the normal first-installation command.
On Linux/macOS, update mode also uses the standard `find`, `diff`, and `cp` commands.

The updater checks the installed version and downloads its original official ZIP
and checksums. It compares the complete installed contents with that verified package,
not just the locally editable manifest. Missing, added or edited files, linked paths,
private profiles and unrecognized installations stop the operation without replacing
the skill. If the original release cannot be verified, use the manual procedure below.
There is no force-overwrite option and no automatic merge of local adaptations.

An already-current official copy is left unchanged, without creating a backup. A
requested older version is refused. For a newer version, the new package is verified
and staged before the installed folder is changed. A verified copy of the original
release ZIP and recovery information are retained outside the project:

- Windows: `%LOCALAPPDATA%/AURAE/skill-backups/`.
- Linux/macOS: `${XDG_STATE_HOME:-$HOME/.local/state}/aurae/skill-backups/`.

The actual unique backup path is printed. These are recovery archives, not additional
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

To recover manually, stop the agent, preserve any newer/customized installation,
and extract the retained verified ZIP into a separate directory. Review it, then
restore the complete skill folder to the original agent location. Follow the recovery
information next to the backup; never overlay an installed folder with an older ZIP.

### Private, customized or older installations

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

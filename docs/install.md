# Project-local installation

Install a **built release ZIP**, not the repository's raw `skills/aurae` directory.
The latter is a manufacturing source: it has no generated vendor profile and no
installable manifest. There is no installer to execute and no npm dependency.

Codex reads project skills under `.agents/skills/` ([official documentation](https://learn.chatgpt.com/docs/build-skills)).
Claude Code reads `.claude/skills/` ([official documentation](https://code.claude.com/docs/en/skills)).
The ZIPs already contain these paths. Run installation from the intended project root.

## Download and extract

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
flow with access to that repository. The same download command works without putting
credentials in command text. Browser download also works when signed in.

## One-line first installation

These commands are templates for **after a release has actually been published**.
`1.17.1` is the initially prepared version, not a release currently guaranteed to exist.
They refuse an existing skill folder, check the downloaded ZIP and leave the temporary
download directory available for inspection. They do not modify AGENTS.md, CLAUDE.md,
Git configuration or any global skill installation.

### Windows PowerShell

Requires `gh`, `Get-FileHash` and `Expand-Archive`. In the project root, for Codex:

```powershell
& { $ErrorActionPreference='Stop'; $auraeVersion='1.17.1'; $auraeRepo='vibe-archi/aurae'; $auraeAgent='codex'; $auraeTarget='.agents/skills/aurae'; if(Test-Path -LiteralPath $auraeTarget){throw 'AURAE already exists: use the upgrade procedure'}; $auraeTemp=Join-Path ([IO.Path]::GetTempPath()) ('aurae-'+[guid]::NewGuid()); New-Item -ItemType Directory -Path $auraeTemp | Out-Null; $auraeZip="aurae-$auraeAgent-$auraeVersion.zip"; gh release download "v$auraeVersion" --repo $auraeRepo --pattern $auraeZip --pattern SHA256SUMS --dir $auraeTemp; if($LASTEXITCODE -ne 0){throw 'Download failed'}; $auraeLines=@(Get-Content -LiteralPath (Join-Path $auraeTemp 'SHA256SUMS') | Where-Object {$_ -match ('^[0-9a-f]{64}  '+[regex]::Escape($auraeZip)+'$')}); if($auraeLines.Count -ne 1){throw 'Missing or ambiguous checksum'}; if((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $auraeTemp $auraeZip)).Hash -ne $auraeLines[0].Substring(0,64)){throw 'Checksum mismatch'}; Expand-Archive -LiteralPath (Join-Path $auraeTemp $auraeZip) -DestinationPath .; Write-Output "Installed locally. Downloads retained at $auraeTemp" }
```

For Claude, change `$auraeAgent` to `claude` and `$auraeTarget` to `.claude/skills/aurae`.
For a private distribution, change `$auraeRepo` and `$auraeVersion` to that client's
repository and a published version. No other change is required.

### macOS / Linux (Bash)

Requires `gh`, `unzip` and `shasum` (Perl's SHA utility). For Codex:

```bash
(set -euo pipefail; aurae_version=1.17.1; aurae_repo=vibe-archi/aurae; aurae_agent=codex; aurae_target=.agents/skills/aurae; test ! -e "$aurae_target" || { echo 'AURAE already exists: use the upgrade procedure' >&2; exit 1; }; aurae_tmp=$(mktemp -d); aurae_zip="aurae-$aurae_agent-$aurae_version.zip"; gh release download "v$aurae_version" --repo "$aurae_repo" --pattern "$aurae_zip" --pattern SHA256SUMS --dir "$aurae_tmp"; (cd "$aurae_tmp"; grep -F "  $aurae_zip" SHA256SUMS | shasum -a 256 -c -); unzip -n "$aurae_tmp/$aurae_zip" -d .; printf 'Installed locally. Downloads retained at %s\n' "$aurae_tmp")
```

For Claude, change `aurae_agent=claude` and `aurae_target=.claude/skills/aurae`.
For a private distribution, change `aurae_repo` and `aurae_version`.
The temporary directory is outside the project; no pre-existing `.scratchpad` is needed.

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

Download and verify the new package into a separate directory. Compare its version,
distribution and instructions against the installed copy. Keep private adaptations;
an official release with a larger number is not an upgrade of a client distribution.

After approval, back up or preserve the old complete folder and replace it as a whole.
Do not overlay ZIPs: removed reference files would otherwise survive and invalidate
the exhaustive manifest. Restart the agent, then ask for `/AURAE upgrade` to refresh
the project's recorded bundle from the approved local skill. The active phase stays
intact; earlier-phase consequences are deferred to a safe boundary.

This command does not check GitHub for updates and does not grant remote push or
product-code merge permission. The user explicitly downloads a chosen package first.

# Project-local installation or conservative update from official AURAE releases.
# Compatible with Windows PowerShell 5.1 and PowerShell 7; no Git/gh/npm required.
[CmdletBinding()]
param(
    [ValidateSet('codex', 'claude')]
    [string]$Agent,
    [string]$Version,
    [switch]$Update,
    [switch]$Help
)

function Get-AuraePathEntry {
    param([string]$Path)
    $fullPath = [IO.Path]::GetFullPath($Path)
    $parentPath = [IO.Path]::GetDirectoryName($fullPath)
    if (-not $parentPath) {
        return Get-Item -LiteralPath $fullPath -Force -ErrorAction Stop
    }
    if (-not [IO.Directory]::Exists($parentPath)) { return $null }
    # Enumerating the parent also detects dangling links, unlike Test-Path.
    $leaf = [IO.Path]::GetFileName($fullPath)
    # Materialize this small lookup before returning: an early return from the
    # lazy .NET Framework iterator can retain a directory handle and prevent
    # the later whole-directory rename on Windows PowerShell 5.1.
    foreach ($entry in ([IO.DirectoryInfo]$parentPath).GetFileSystemInfos()) {
        if ([string]::Equals($entry.Name, $leaf, [StringComparison]::OrdinalIgnoreCase)) {
            return $entry
        }
    }
    return $null
}

function Assert-AuraeDirectoryPath {
    param([string]$Path, [switch]$AllowMissing)
    $fullPath = [IO.Path]::GetFullPath($Path)
    $root = [IO.Path]::GetPathRoot($fullPath)
    $paths = @($root)
    $current = $root
    foreach ($part in ($fullPath.Substring($root.Length) -split '[\\/]')) {
        if ($part.Length -eq 0) { continue }
        $current = Join-Path $current $part
        $paths += $current
    }
    foreach ($directory in $paths) {
        $entry = Get-AuraePathEntry $directory
        if ($null -eq $entry) {
            if ($AllowMissing) { continue }
            throw "Directory does not exist: $directory"
        }
        if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Refusing a symbolic link or junction in the installation path: $directory"
        }
        if (($entry.Attributes -band [IO.FileAttributes]::Directory) -eq 0) {
            throw "Expected a directory in the installation path: $directory"
        }
    }
}

function Assert-AuraeDestination {
    param([string]$Parent, [string]$Target)
    Assert-AuraeDirectoryPath -Path $Parent -AllowMissing
    if ($null -ne (Get-AuraePathEntry $Target)) {
        throw "AURAE already exists at $Target. Use the documented upgrade procedure; this installer never overwrites an existing path."
    }
}

function Remove-AuraeOwnedDirectory {
    param([string]$Path, [string]$Parent, [string]$Leaf)
    if (-not $Path) { return }
    $expected = [IO.Path]::GetFullPath((Join-Path $Parent $Leaf))
    if (-not [string]::Equals([IO.Path]::GetFullPath($Path), $expected, [StringComparison]::OrdinalIgnoreCase) -or
        $Leaf -notmatch '^aurae-install-[0-9a-f]{32}$') {
        throw 'Temporary cleanup path failed ownership validation.'
    }
    $entry = Get-AuraePathEntry $expected
    if ($null -eq $entry) { return }
    Assert-AuraeDirectoryPath -Path $expected
    # Never recursively delete a tree that has acquired a link/junction.
    $pending = New-Object 'Collections.Generic.Stack[string]'
    $pending.Push($expected)
    while ($pending.Count -gt 0) {
        foreach ($child in ([IO.DirectoryInfo]$pending.Pop()).EnumerateFileSystemInfos()) {
            if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Temporary cleanup refused a link or junction: $($child.FullName)"
            }
            if (($child.Attributes -band [IO.FileAttributes]::Directory) -ne 0) {
                $pending.Push($child.FullName)
            }
        }
    }
    Remove-Item -LiteralPath $expected -Recurse -Force -ErrorAction Stop
}

function Expand-AuraeCheckedArchive {
    param([string]$ZipPath, [string]$Prefix, [string]$Stage)
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $paths = New-Object 'Collections.Generic.Dictionary[string,bool]' ([StringComparer]::OrdinalIgnoreCase)
        $spellings = New-Object 'Collections.Generic.Dictionary[string,string]' ([StringComparer]::OrdinalIgnoreCase)
        $required = @('SKILL.md', 'vendor.md', 'aurae-skill.yaml')
        $found = New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
        [long]$totalBytes = 0
        if ($archive.Entries.Count -eq 0 -or $archive.Entries.Count -gt 10000) {
            throw 'The archive is empty or exceeds the supported entry limit.'
        }
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName
            if (-not $name.StartsWith($Prefix, [StringComparison]::Ordinal) -or
                $name -notmatch '^[A-Za-z0-9_./-]+$' -or $name.Length -gt 300) {
                throw "Unexpected or unsafe archive path: $name"
            }
            $directory = $name.EndsWith('/', [StringComparison]::Ordinal)
            $relative = $name.Substring($Prefix.Length)
            if ($directory -and $relative.Length -gt 0) { $relative = $relative.Substring(0, $relative.Length - 1) }
            if ($relative.Length -eq 0 -and -not $directory) { throw "Invalid archive root: $name" }
            $spelling = ''
            foreach ($part in ($relative -split '/')) {
                if ($relative.Length -eq 0) { break }
                if ($part.Length -eq 0 -or $part -eq '.' -or $part -eq '..' -or
                    $part.EndsWith('.') -or $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') {
                    throw "Unsafe archive path segment: $name"
                }
                $spelling = if ($spelling.Length -eq 0) { $part } else { "$spelling/$part" }
                if ($spellings.ContainsKey($spelling)) {
                    if ($spellings[$spelling] -cne $spelling) { throw "Case-colliding archive path: $name" }
                } else {
                    $spellings.Add($spelling, $spelling)
                }
            }
            if ($paths.ContainsKey($relative)) { throw "Duplicate or case-colliding archive path: $name" }
            $paths.Add($relative, $directory)
            [long]$attributes = [long]$entry.ExternalAttributes -band 4294967295L
            $unixType = ($attributes -shr 16) -band 61440
            if (($attributes -band 1024) -ne 0 -or
                ($unixType -ne 0 -and $unixType -ne 32768 -and $unixType -ne 16384) -or
                ($unixType -eq 16384 -and -not $directory) -or
                ($unixType -eq 32768 -and $directory) -or
                (($attributes -band 16) -ne 0 -and -not $directory)) {
                throw "Archive links or special entries are not permitted: $name"
            }
            if ($entry.Length -gt 67108864 -or ($directory -and $entry.Length -ne 0)) {
                throw "Unsupported archive entry size: $name"
            }
            $totalBytes += $entry.Length
            if ($totalBytes -gt 268435456) { throw 'The archive exceeds the supported unpacked size.' }
            if (-not $directory -and $required -ccontains $relative -and $entry.Length -gt 0) {
                [void]$found.Add($relative)
            }
        }
        foreach ($name in $paths.Keys) {
            $parts = $name -split '/'
            for ($i = 1; $i -lt $parts.Count; $i++) {
                $ancestor = $parts[0..($i - 1)] -join '/'
                if ($paths.ContainsKey($ancestor) -and -not $paths[$ancestor]) {
                    throw "Archive file/directory collision: $name"
                }
            }
        }
        foreach ($name in $required) {
            if (-not $found.Contains($name)) { throw "The release archive is missing a required nonempty file: $name" }
        }
        # Only after the complete entry list passes validation do any files extract.
        [void][IO.Directory]::CreateDirectory($Stage)
        $stagePrefix = [IO.Path]::GetFullPath($Stage) + [IO.Path]::DirectorySeparatorChar
        foreach ($entry in $archive.Entries) {
            $relative = $entry.FullName.Substring($Prefix.Length).TrimEnd('/')
            if ($relative.Length -eq 0) { continue }
            $destination = [IO.Path]::GetFullPath((Join-Path $Stage $relative))
            if (-not $destination.StartsWith($stagePrefix, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Archive extraction escaped its owned staging directory.'
            }
            if ($entry.FullName.EndsWith('/')) {
                [void][IO.Directory]::CreateDirectory($destination)
                continue
            }
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination))
            $inputStream = $entry.Open()
            try {
                $outputStream = [IO.File]::Open($destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
                try {
                    $buffer = New-Object byte[] 65536
                    [long]$written = 0
                    while (($count = $inputStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                        $written += $count
                        if ($written -gt $entry.Length) { throw 'An archive entry expanded beyond its declared size.' }
                        $outputStream.Write($buffer, 0, $count)
                    }
                } finally { $outputStream.Dispose() }
            } finally { $inputStream.Dispose() }
            if (([IO.FileInfo]$destination).Length -ne $entry.Length) { throw 'Extracted file length does not match the archive.' }
        }
    } finally { $archive.Dispose() }
}

function Get-AuraeTreeInventory {
    param([string]$Root)
    Assert-AuraeDirectoryPath -Path $Root
    $inventory = New-Object 'Collections.Generic.SortedDictionary[string,string]' ([StringComparer]::Ordinal)
    $pending = New-Object 'Collections.Generic.Stack[string]'
    $pending.Push($Root)
    while ($pending.Count -gt 0) {
        foreach ($entry in ([IO.DirectoryInfo]$pending.Pop()).EnumerateFileSystemInfos()) {
            if (($entry.Attributes -band ([IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Device)) -ne 0) {
                throw "An installed file or directory is a link, junction or special entry: $($entry.FullName)"
            }
            $relative = $entry.FullName.Substring($Root.Length + 1).Replace('\', '/')
            if (($entry.Attributes -band [IO.FileAttributes]::Directory) -ne 0) {
                $inventory.Add($relative, 'directory')
                $pending.Push($entry.FullName)
            } else {
                $inventory.Add($relative, 'file:' + (Get-FileHash -LiteralPath $entry.FullName -Algorithm SHA256).Hash)
            }
        }
    }
    return ,$inventory
}

function Assert-AuraeInventoryMatches {
    param($Expected, $Actual, [string]$Message)
    if ($Expected.Count -ne $Actual.Count) { throw $Message }
    foreach ($key in $Expected.Keys) {
        if (-not $Actual.ContainsKey($key) -or $Actual[$key] -cne $Expected[$key]) { throw $Message }
    }
}

function Get-AuraeInstalledVersion {
    param([string]$Target)
    $skill = Get-AuraePathEntry (Join-Path $Target 'SKILL.md')
    if ($null -eq $skill -or ($skill.Attributes -band ([IO.FileAttributes]::Directory -bor [IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Device)) -ne 0 -or
        $skill.Length -eq 0) {
        throw 'Update requires a regular, nonempty installed SKILL.md.'
    }
    $manifestPath = Join-Path $Target 'aurae-skill.yaml'
    $manifest = Get-AuraePathEntry $manifestPath
    if ($null -eq $manifest -or ($manifest.Attributes -band ([IO.FileAttributes]::Directory -bor [IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Device)) -ne 0 -or
        $manifest.Length -gt 1048576) {
        throw 'Update requires a regular, supported installed aurae-skill.yaml manifest.'
    }
    # Read a literal scalar from the generated format; never execute/interpret YAML.
    $content = [IO.File]::ReadAllText($manifestPath)
    $keys = [regex]::Matches($content, '(?m)^(?:agent_skill|''agent_skill''|"agent_skill")[ \t]*:')
    $values = [regex]::Matches($content, '(?m)^agent_skill: ((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))\r?$')
    $formatKeys = [regex]::Matches($content, '(?m)^(?:format|''format''|"format")[ \t]*:')
    $nameKeys = [regex]::Matches($content, '(?m)^(?:name|''name''|"name")[ \t]*:')
    $entrypointKeys = [regex]::Matches($content, '(?m)^(?:entrypoint|''entrypoint''|"entrypoint")[ \t]*:')
    if ($keys.Count -ne 1 -or $values.Count -ne 1 -or $formatKeys.Count -ne 1 -or $nameKeys.Count -ne 1 -or
        $content -cnotmatch '(?m)^format: aurae-skill-bundle\r?$' -or $content -cnotmatch '(?m)^name: aurae\r?$' -or
        $entrypointKeys.Count -gt 1 -or ($entrypointKeys.Count -eq 1 -and $content -cnotmatch '(?m)^entrypoint: SKILL[.]md\r?$')) {
        throw 'Unsupported installed manifest. Review this installation manually before replacing it.'
    }
    return $values[0].Groups[1].Value
}

function Get-AuraeOfficialPackage {
    param([string]$SelectedAgent, [string]$SelectedVersion, [string]$Prefix, [string]$Directory, [switch]$AllowMissingArchive)
    [void][IO.Directory]::CreateDirectory($Directory)
    $archiveName = "aurae-$SelectedAgent-$SelectedVersion.zip"
    $baseUrl = "https://github.com/vibe-archi/aurae/releases/download/v$SelectedVersion"
    $zipPath = Join-Path $Directory $archiveName
    $checksumsPath = Join-Path $Directory 'SHA256SUMS'
    Write-Host "Downloading AURAE $SelectedVersion for $SelectedAgent from the official release..."
    try {
        Invoke-WebRequest -Uri "$baseUrl/$archiveName" -OutFile $zipPath -UseBasicParsing -Headers @{ 'User-Agent' = 'AURAE-project-installer' } -TimeoutSec 60 -ErrorAction Stop | Out-Null
    } catch {
        # Windows PowerShell exposes HttpWebResponse; PowerShell 7 exposes
        # HttpResponseMessage. Both carry StatusCode. Never infer a 404 from text.
        if ($AllowMissingArchive -and $null -ne $_.Exception.Response -and
            [int]$_.Exception.Response.StatusCode -eq 404) { return $null }
        throw
    }
    Invoke-WebRequest -Uri "$baseUrl/SHA256SUMS" -OutFile $checksumsPath -UseBasicParsing -Headers @{ 'User-Agent' = 'AURAE-project-installer' } -TimeoutSec 60 -ErrorAction Stop | Out-Null
    $pattern = '^([0-9A-Fa-f]{64})  ' + [regex]::Escape($archiveName) + '$'
    $checksums = @()
    foreach ($line in [IO.File]::ReadAllLines($checksumsPath)) {
        $match = [regex]::Match($line, $pattern)
        if ($match.Success) { $checksums += $match.Groups[1].Value }
    }
    if ($checksums.Count -ne 1) { throw 'The release has no unique exact checksum entry for the requested archive.' }
    if ((Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash -ine $checksums[0]) {
        throw 'Archive checksum mismatch. Nothing has been installed or replaced.'
    }
    $stage = Join-Path $Directory 'validated-skill'
    Expand-AuraeCheckedArchive -ZipPath $zipPath -Prefix $Prefix -Stage $stage
    if ((Get-AuraeInstalledVersion -Target $stage) -cne $SelectedVersion) {
        throw 'The downloaded package manifest does not match its requested release version.'
    }
    return [pscustomobject]@{ Zip = $zipPath; Stage = $stage; Sha256 = $checksums[0] }
}

function Assert-AuraeLocalFallbackIdentity {
    param([string]$Target, [string]$InstalledVersion, [string]$OfficialStage)
    # Recognize only the generated scalar header, not arbitrary YAML, aliases,
    # documents or quoted/indented identities that could be interpreted differently.
    $seen = New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    $inventoryStarted = $false
    foreach ($line in [IO.File]::ReadAllLines((Join-Path $Target 'aurae-skill.yaml'))) {
        if ($line -match '^\s*$' -or $line.StartsWith('#')) { continue }
        if ($line.StartsWith('- ') -or $line -match '^\s') {
            if ($inventoryStarted) { continue }
            throw 'The local manifest has an unsupported or ambiguous AURAE identity.'
        }
        if ($inventoryStarted -or $line -cnotmatch '^([a-z_]+):' -or -not $seen.Add($Matches[1])) {
            throw 'The local manifest has an unsupported or ambiguous AURAE identity.'
        }
        $key = $Matches[1]
        $valid = switch -CaseSensitive ($key) {
            'format' { $line -ceq 'format: aurae-skill-bundle' }
            'name' { $line -ceq 'name: aurae' }
            'agent_skill' { $line -ceq "agent_skill: $InstalledVersion" }
            'entrypoint' { $line -ceq 'entrypoint: SKILL.md' }
            'format_version' { $line -cmatch '^format_version: [0-9]+\.[0-9]+\.[0-9]+$' }
            'aurae_methodology' { $line -cmatch '^aurae_methodology: [0-9]+\.[0-9]+\.[0-9]+$' }
            'files' {
                $inventoryStarted = $true
                $line -ceq 'files:' -or $line -ceq 'files: []'
            }
            default { $false }
        }
        if (-not $valid) { throw 'The local manifest has an unsupported or ambiguous AURAE identity.' }
    }
    if (-not $seen.Contains('format') -or -not $seen.Contains('name') -or -not $seen.Contains('agent_skill')) {
        throw 'The local manifest has an unsupported or ambiguous AURAE identity.'
    }
    # A missing profile is supported only before the profile's introduction.
    $vendorPath = Join-Path $Target 'vendor.md'
    $vendor = Get-AuraePathEntry $vendorPath
    if ($null -eq $vendor) {
        if ([version]$InstalledVersion -lt [version]'1.17.0') { return }
        throw 'The installed modern bundle has no vendor.md profile. Its distribution is ambiguous; nothing was replaced.'
    }
    if (($vendor.Attributes -band ([IO.FileAttributes]::Directory -bor [IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Device)) -ne 0 -or
        $vendor.Length -eq 0 -or $vendor.Length -gt 1048576) {
        throw 'The installed vendor.md is not a regular supported profile. Nothing was replaced.'
    }
    # Literal comparison is deliberately conservative. Do not parse/execute
    # profile instructions or accept a copied official header over private text.
    # Only CRLF/LF differences in this generated Markdown file are insignificant.
    $utf8 = New-Object Text.UTF8Encoding $false, $true
    $installedProfile = $utf8.GetString([IO.File]::ReadAllBytes($vendorPath)).Replace("`r`n", "`n")
    $officialProfile = $utf8.GetString([IO.File]::ReadAllBytes((Join-Path $OfficialStage 'vendor.md'))).Replace("`r`n", "`n")
    if (-not [string]::Equals($installedProfile, $officialProfile, [StringComparison]::Ordinal)) {
        throw 'The installed vendor.md does not match the canonical official profile (private, adapted or ambiguous distribution). Nothing was replaced; preserve and review this installation manually.'
    }
}

function Move-AuraeDirectory {
    param([string]$Source, [string]$Destination)
    # No force/overlay. A small wrapper also permits transaction fault testing.
    [IO.Directory]::Move($Source, $Destination)
}

function Copy-AuraeInstalledTree {
    param([string]$Source, [string]$Destination, $Inventory)
    Assert-AuraeDirectoryPath -Path $Source
    Assert-AuraeDirectoryPath -Path ([IO.Path]::GetDirectoryName($Destination))
    if ($null -ne (Get-AuraePathEntry $Destination)) { throw "Backup destination already exists: $Destination" }
    [void][IO.Directory]::CreateDirectory($Destination)
    # Use the validated complete inventory, not a wildcard: hidden files and
    # empty directories belong to the backup, even if absent from the manifest.
    foreach ($relative in $Inventory.Keys) {
        $sourcePath = Join-Path $Source $relative
        $destinationPath = Join-Path $Destination $relative
        if ($Inventory[$relative] -eq 'directory') {
            Assert-AuraeDirectoryPath -Path $sourcePath
            [void][IO.Directory]::CreateDirectory($destinationPath)
            Assert-AuraeDirectoryPath -Path $destinationPath
        } else {
            Assert-AuraeDirectoryPath -Path ([IO.Path]::GetDirectoryName($sourcePath))
            $entry = Get-AuraePathEntry $sourcePath
            if ($null -eq $entry -or ($entry.Attributes -band ([IO.FileAttributes]::Directory -bor [IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Device)) -ne 0) {
                throw "The installed file changed before backup: $sourcePath"
            }
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destinationPath))
            Assert-AuraeDirectoryPath -Path ([IO.Path]::GetDirectoryName($destinationPath))
            [IO.File]::Copy($sourcePath, $destinationPath, $false)
        }
    }
    Assert-AuraeInventoryMatches -Expected $Inventory -Actual (Get-AuraeTreeInventory -Root $Destination) -Message 'The local backup failed inventory verification. Nothing was replaced.'
    Assert-AuraeInventoryMatches -Expected $Inventory -Actual (Get-AuraeTreeInventory -Root $Source) -Message 'The installed skill changed while being backed up. Nothing was replaced.'
}

function Save-AuraeUpdateBackup {
    param([string]$Project, [string]$Target, [string]$SelectedAgent, [string]$OldVersion, [string]$NewVersion, $Package, $Inventory)
    $dataRoot = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($dataRoot)) { $dataRoot = [Environment]::GetFolderPath('LocalApplicationData') }
    $absolutePattern = if ([IO.Path]::DirectorySeparatorChar -eq '\') { '^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+(?:[\\/]|$))' } else { '^/' }
    if ([string]::IsNullOrWhiteSpace($dataRoot) -or $dataRoot -notmatch $absolutePattern) {
        throw 'Update requires an absolute local application-data directory for its durable backup.'
    }
    $backupParent = [IO.Path]::GetFullPath((Join-Path (Join-Path $dataRoot 'AURAE') 'skill-backups'))
    $projectPrefix = $Project.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (($backupParent + [IO.Path]::DirectorySeparatorChar).StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        $backupParent -match '(?i)[\\/]\.(?:agents|claude|codex)[\\/]skills(?:[\\/]|$)') {
        throw 'The durable backup must be outside the project and its skill discovery paths.'
    }
    Assert-AuraeDirectoryPath -Path $backupParent -AllowMissing
    [void][IO.Directory]::CreateDirectory($backupParent)
    Assert-AuraeDirectoryPath -Path $backupParent
    $backup = Join-Path $backupParent ([guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $backup -ErrorAction Stop | Out-Null
    Assert-AuraeDirectoryPath -Path $backup
    $info = [ordered]@{
        project = $Project; target = $Target; agent = $SelectedAgent
        old_version = $OldVersion; new_version = $NewVersion
        created_utc = [DateTime]::UtcNow.ToString('o')
    }
    if ($null -ne $Package) {
        $archive = Join-Path $backup 'skill.zip'
        # The live tree was proven identical to this checksum-verified official ZIP.
        [IO.File]::Copy($Package.Zip, $archive, $false)
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ine $Package.Sha256) {
            throw "The durable backup failed verification: $backup"
        }
        $info['backup_kind'] = 'official-archive'
        $info['sha256'] = $Package.Sha256
        $info['restore'] = 'Stop agent sessions. Preserve or move aside the current aurae folder; do not overlay it. Verify skill.zip with the recorded SHA-256, then extract it at the recorded project root. Restart the agent. No Git history or AURAE project memory is changed by restoring this skill archive.'
    } else {
        $previousSkill = Join-Path $backup 'previous-skill'
        Copy-AuraeInstalledTree -Source $Target -Destination $previousSkill -Inventory $Inventory
        Assert-AuraeInventoryMatches -Expected $Inventory -Actual (Get-AuraeTreeInventory -Root $previousSkill) -Message 'The local backup failed its final inventory verification. Nothing was replaced.'
        Assert-AuraeInventoryMatches -Expected $Inventory -Actual (Get-AuraeTreeInventory -Root $Target) -Message 'The installed skill changed while being backed up. Nothing was replaced.'
        [IO.File]::WriteAllText((Join-Path $backup 'inventory.json'), ($Inventory | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
        $info['backup_kind'] = 'local-tree'
        $info['reference_archive'] = 'HTTP 404; official provenance was not established from a published archive.'
        $info['inventory'] = 'inventory.json'
        $info['restore'] = 'Stop agent sessions. Preserve or move aside the current aurae folder; do not overlay it. Verify every file SHA-256 and directory in previous-skill against inventory.json, then copy the entire previous-skill directory to the recorded target, including hidden files and empty directories. Restart the agent. No Git history or AURAE project memory is changed by restoring this local skill tree.'
    }
    [IO.File]::WriteAllText((Join-Path $backup 'restore-info.json'), ($info | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
    Write-Host "Backup retained at $backup"
    return $backup
}

function Invoke-AuraeProjectInstall {
    param([string]$SelectedAgent, [string]$SelectedVersion, [switch]$Updating)
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    $temporary = $null
    $promotion = $null
    $temporaryOwned = $false
    $promotionOwned = $false
    $recoverPrevious = $false
    $previousTls = [Net.ServicePointManager]::SecurityProtocol
    try {
        if (-not $SelectedAgent) { throw 'Specify -Agent codex or -Agent claude. Use -Help for usage.' }
        $SelectedAgent = $SelectedAgent.ToLowerInvariant()
        if ($SelectedVersion -and $SelectedVersion -cnotmatch '^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') {
            throw 'Version must be a published release number such as 1.19.0 or v1.19.0.'
        }
        if ((Get-Location).Provider.Name -ne 'FileSystem') { throw 'Run this installer from a filesystem project directory.' }
        $project = [IO.Path]::GetFullPath((Get-Location).ProviderPath)
        $agentDirectory = if ($SelectedAgent -eq 'codex') { '.agents' } else { '.claude' }
        $skillParent = Join-Path (Join-Path $project $agentDirectory) 'skills'
        $target = Join-Path $skillParent 'aurae'
        if ($Updating) {
            Assert-AuraeDirectoryPath -Path $target
            $installedInventory = Get-AuraeTreeInventory -Root $target
            $installedVersion = Get-AuraeInstalledVersion -Target $target
        } else {
            Assert-AuraeDestination -Parent $skillParent -Target $target
        }
        # TLS 1.2 support for older Windows PowerShell sessions; restored on return.
        [Net.ServicePointManager]::SecurityProtocol = $previousTls -bor [Net.SecurityProtocolType]::Tls12
        $headers = @{ 'User-Agent' = 'AURAE-project-installer'; 'Accept' = 'application/vnd.github+json' }
        if (-not $SelectedVersion) {
            $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/vibe-archi/aurae/releases/latest' -Headers $headers -TimeoutSec 60 -ErrorAction Stop
            if ($null -eq $release -or $release.draft -ne $false -or $release.prerelease -ne $false -or
                $release.tag_name -cnotmatch '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') {
                throw 'GitHub did not return a supported published stable release.'
            }
            $SelectedVersion = $release.tag_name.Substring(1)
        } else {
            $SelectedVersion = $SelectedVersion.TrimStart('v')
        }
        if ($Updating -and ([version]$SelectedVersion -lt [version]$installedVersion)) {
            throw "Refusing to downgrade AURAE $installedVersion to $SelectedVersion. Use a separately reviewed manual restoration if intended."
        }
        $temporaryParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
        Assert-AuraeDirectoryPath -Path $temporaryParent
        $temporaryLeaf = 'aurae-install-' + [guid]::NewGuid().ToString('N')
        $temporary = Join-Path $temporaryParent $temporaryLeaf
        New-Item -ItemType Directory -Path $temporary -ErrorAction Stop | Out-Null
        $temporaryOwned = $true
        $package = Get-AuraeOfficialPackage -SelectedAgent $SelectedAgent -SelectedVersion $SelectedVersion -Prefix "$agentDirectory/skills/aurae/" -Directory (Join-Path $temporary 'selected')
        $stage = $package.Stage
        if ($Updating) {
            $originalPackage = $package
            if ($installedVersion -ne $SelectedVersion) {
                $originalPackage = Get-AuraeOfficialPackage -SelectedAgent $SelectedAgent -SelectedVersion $installedVersion -Prefix "$agentDirectory/skills/aurae/" -Directory (Join-Path $temporary 'installed-release') -AllowMissingArchive
            }
            if ($null -ne $originalPackage) {
                $officialInventory = Get-AuraeTreeInventory -Root $originalPackage.Stage
                Assert-AuraeInventoryMatches -Expected $officialInventory -Actual $installedInventory -Message 'The installed skill differs from its official published release (local changes, private profile, missing or additional files). Nothing was replaced. Review and preserve these adaptations manually.'
            } else {
                Write-Warning "The reference archive for installed AURAE $installedVersion returned HTTP 404. Checking this local/manual installation for a verified local-backup update; this does not establish its official provenance."
                Assert-AuraeLocalFallbackIdentity -Target $target -InstalledVersion $installedVersion -OfficialStage $stage
            }
            Assert-AuraeInventoryMatches -Expected $installedInventory -Actual (Get-AuraeTreeInventory -Root $target) -Message 'The installed skill changed during validation. Nothing was replaced; retry after edits have finished.'
            if ($installedVersion -eq $SelectedVersion) {
                Write-Host "AURAE $SelectedVersion is already installed and matches the official release. Nothing changed."
                return
            }
            $backup = Save-AuraeUpdateBackup -Project $project -Target $target -SelectedAgent $SelectedAgent -OldVersion $installedVersion -NewVersion $SelectedVersion -Package $originalPackage -Inventory $installedInventory
        } else {
            Assert-AuraeDestination -Parent $skillParent -Target $target
        }
        [void][IO.Directory]::CreateDirectory($skillParent)
        Assert-AuraeDirectoryPath -Path $skillParent
        # A short-lived sibling permits a complete rename even across temp/project volumes.
        $promotionLeaf = 'aurae-install-' + [guid]::NewGuid().ToString('N')
        $promotion = Join-Path $skillParent $promotionLeaf
        New-Item -ItemType Directory -Path $promotion -ErrorAction Stop | Out-Null
        $promotionOwned = $true
        $newSkill = Join-Path $promotion 'new'
        [void][IO.Directory]::CreateDirectory($newSkill)
        foreach ($directory in ([IO.DirectoryInfo]$stage).EnumerateDirectories('*', [IO.SearchOption]::AllDirectories)) {
            $relative = $directory.FullName.Substring($stage.Length + 1)
            [void][IO.Directory]::CreateDirectory((Join-Path $newSkill $relative))
        }
        foreach ($file in ([IO.DirectoryInfo]$stage).EnumerateFiles('*', [IO.SearchOption]::AllDirectories)) {
            $relative = $file.FullName.Substring($stage.Length + 1)
            $destination = Join-Path $newSkill $relative
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination))
            [IO.File]::Copy($file.FullName, $destination, $false)
        }
        Assert-AuraeDirectoryPath -Path $promotion
        Assert-AuraeInventoryMatches -Expected (Get-AuraeTreeInventory -Root $stage) -Actual (Get-AuraeTreeInventory -Root $newSkill) -Message 'The copied package did not pass its final integrity check. Nothing was replaced.'
        if ($Updating) {
            Assert-AuraeInventoryMatches -Expected $installedInventory -Actual (Get-AuraeTreeInventory -Root $target) -Message 'The installed skill changed during update preparation. Nothing was replaced; the backup remains available.'
            $previous = Join-Path $promotion 'previous'
            # Arm recovery before the first rename, including interruption between commands.
            $recoverPrevious = $true
            try {
                Move-AuraeDirectory -Source $target -Destination $previous
            } catch {
                if ($null -ne (Get-AuraePathEntry $previous)) {
                    $promotionOwned = $false
                    $recoverPrevious = $false
                    throw "Could not confirm the first update rename. Preserve and inspect $previous and $target; durable backup: $backup. $($_.Exception.Message)"
                }
                $recoverPrevious = $false
                throw
            }
            try {
                Assert-AuraeInventoryMatches -Expected $installedInventory -Actual (Get-AuraeTreeInventory -Root $previous) -Message 'The installed skill changed just before replacement. Restoring it instead of updating.'
                Assert-AuraeDestination -Parent $skillParent -Target $target
                Move-AuraeDirectory -Source $newSkill -Destination $target
                $recoverPrevious = $false
            } catch {
                $promotionError = $_.Exception.Message
                try {
                    Assert-AuraeDestination -Parent $skillParent -Target $target
                    Move-AuraeDirectory -Source $previous -Destination $target
                    $recoverPrevious = $false
                } catch {
                    # The old live tree must survive even if rollback is prevented.
                    $promotionOwned = $false
                    $recoverPrevious = $false
                    throw "Update failed: $promotionError. Automatic restoration also failed: $($_.Exception.Message). Previous files retained at $previous; durable backup at $backup. Do not delete these recovery files."
                }
                throw "Update failed; the previous skill was restored. $promotionError. Durable backup: $backup"
            }
            Write-Host "Updated AURAE $installedVersion to $SelectedVersion locally at $target"
            Write-Host "The complete previous installation is retained at $backup"
        } else {
            Assert-AuraeDestination -Parent $skillParent -Target $target
            Move-AuraeDirectory -Source $newSkill -Destination $target
            Write-Host "Installed AURAE $SelectedVersion locally at $target"
        }
        Write-Host 'Start a new agent session to load the skill. No global installation or Git settings were changed.'
        if ($Updating) { Write-Host 'Then ask for /AURAE upgrade to update the project memory from the approved local skill.' }
    } finally {
        [Net.ServicePointManager]::SecurityProtocol = $previousTls
        if ($recoverPrevious) {
            # Cancellation may bypass catch blocks. Never delete a displaced old tree.
            $promotionOwned = $false
            try {
                if ($null -ne (Get-AuraePathEntry $previous)) {
                    Assert-AuraeDirectoryPath -Path $previous
                    Assert-AuraeDestination -Parent $skillParent -Target $target
                    Move-AuraeDirectory -Source $previous -Destination $target
                    Write-Warning 'The interrupted update restored the previous installation.'
                }
                $promotionOwned = $true
            } catch {
                Write-Warning "Interrupted update recovery requires inspection. Previous files: $previous; backup: $backup. $($_.Exception.Message)"
            }
        }
        if ($promotionOwned) {
            try { Remove-AuraeOwnedDirectory -Path $promotion -Parent $skillParent -Leaf $promotionLeaf }
            catch { Write-Warning "Could not safely clean the temporary install directory: $promotion. $($_.Exception.Message)" }
        }
        if ($temporaryOwned) {
            try { Remove-AuraeOwnedDirectory -Path $temporary -Parent $temporaryParent -Leaf $temporaryLeaf }
            catch { Write-Warning "Could not safely clean the temporary download directory: $temporary. $($_.Exception.Message)" }
        }
    }
}

if ($Help) {
    Write-Output @'
Usage: install.ps1 -Agent codex|claude [-Version 1.19.0] [-Update]

Run from your project root. Downloads the latest published stable official release
(or the explicit version) and installs only into .agents/skills/aurae for Codex or
.claude/skills/aurae for Claude Code. First install refuses existing installations.
-Update verifies the target release and keeps a durable backup outside the project.
Published originals must match their full release. Only an old-archive HTTP 404
permits a recognized local/manual installation, backed up as its complete local tree.
Private/ambiguous profiles and downgrades are refused; profiles missing before
1.17.0 are supported. No additional migration flag is needed.
Same-version updates are a verified no-op. Linked paths are always refused.
Requires PowerShell 5.1+ and access to public GitHub HTTPS; no gh, npm, or Git needed.
'@
    return
}

# Keep the only task invocation last: definitions are inert until parsing completes.
if ($PSBoundParameters.ContainsKey('Version') -and [string]::IsNullOrWhiteSpace($Version)) {
    throw 'Version cannot be empty; omit -Version to select the latest published stable release.'
}
Invoke-AuraeProjectInstall -SelectedAgent $Agent -SelectedVersion $Version -Updating:$Update

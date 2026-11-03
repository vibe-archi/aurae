# First project-local installation from an official published AURAE release.
# Compatible with Windows PowerShell 5.1 and PowerShell 7; no Git/gh/npm required.
[CmdletBinding()]
param(
    [ValidateSet('codex', 'claude')]
    [string]$Agent,
    [string]$Version,
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
    foreach ($entry in ([IO.DirectoryInfo]$parentPath).EnumerateFileSystemInfos()) {
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

function Invoke-AuraeProjectInstall {
    param([string]$SelectedAgent, [string]$SelectedVersion)
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    $temporary = $null
    $promotion = $null
    $temporaryOwned = $false
    $promotionOwned = $false
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
        Assert-AuraeDestination -Parent $skillParent -Target $target
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
        $tag = "v$SelectedVersion"
        $archiveName = "aurae-$SelectedAgent-$SelectedVersion.zip"
        $baseUrl = "https://github.com/vibe-archi/aurae/releases/download/$tag"
        $temporaryParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
        Assert-AuraeDirectoryPath -Path $temporaryParent
        $temporaryLeaf = 'aurae-install-' + [guid]::NewGuid().ToString('N')
        $temporary = Join-Path $temporaryParent $temporaryLeaf
        New-Item -ItemType Directory -Path $temporary -ErrorAction Stop | Out-Null
        $temporaryOwned = $true
        $zipPath = Join-Path $temporary $archiveName
        $checksumsPath = Join-Path $temporary 'SHA256SUMS'
        Write-Host "Downloading AURAE $SelectedVersion for $SelectedAgent from the official release..."
        Invoke-WebRequest -Uri "$baseUrl/$archiveName" -OutFile $zipPath -UseBasicParsing -Headers @{ 'User-Agent' = 'AURAE-project-installer' } -TimeoutSec 60 -ErrorAction Stop | Out-Null
        Invoke-WebRequest -Uri "$baseUrl/SHA256SUMS" -OutFile $checksumsPath -UseBasicParsing -Headers @{ 'User-Agent' = 'AURAE-project-installer' } -TimeoutSec 60 -ErrorAction Stop | Out-Null
        $checksumPattern = '^([0-9A-Fa-f]{64})  ' + [regex]::Escape($archiveName) + '$'
        $checksumMatches = @()
        foreach ($line in [IO.File]::ReadAllLines($checksumsPath)) {
            $match = [regex]::Match($line, $checksumPattern)
            if ($match.Success) { $checksumMatches += $match.Groups[1].Value }
        }
        if ($checksumMatches.Count -ne 1) { throw 'The release has no unique exact checksum entry for the requested archive.' }
        if ((Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash -ine $checksumMatches[0]) {
            throw 'Archive checksum mismatch. Nothing has been installed.'
        }
        $stage = Join-Path $temporary 'validated-skill'
        Expand-AuraeCheckedArchive -ZipPath $zipPath -Prefix "$agentDirectory/skills/aurae/" -Stage $stage
        Assert-AuraeDestination -Parent $skillParent -Target $target
        [void][IO.Directory]::CreateDirectory($skillParent)
        Assert-AuraeDirectoryPath -Path $skillParent
        # A short-lived sibling permits a complete rename even across temp/project volumes.
        $promotionLeaf = 'aurae-install-' + [guid]::NewGuid().ToString('N')
        $promotion = Join-Path $skillParent $promotionLeaf
        New-Item -ItemType Directory -Path $promotion -ErrorAction Stop | Out-Null
        $promotionOwned = $true
        foreach ($directory in ([IO.DirectoryInfo]$stage).EnumerateDirectories('*', [IO.SearchOption]::AllDirectories)) {
            $relative = $directory.FullName.Substring($stage.Length + 1)
            [void][IO.Directory]::CreateDirectory((Join-Path $promotion $relative))
        }
        foreach ($file in ([IO.DirectoryInfo]$stage).EnumerateFiles('*', [IO.SearchOption]::AllDirectories)) {
            $relative = $file.FullName.Substring($stage.Length + 1)
            $destination = Join-Path $promotion $relative
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination))
            [IO.File]::Copy($file.FullName, $destination, $false)
        }
        Assert-AuraeDestination -Parent $skillParent -Target $target
        Assert-AuraeDirectoryPath -Path $promotion
        # Directory.Move refuses an existing target; never overlay or force a move.
        [IO.Directory]::Move($promotion, $target)
        $promotionOwned = $false
        Write-Host "Installed AURAE $SelectedVersion locally at $target"
        Write-Host 'Start a new agent session to load the skill. No global installation or Git settings were changed.'
    } finally {
        [Net.ServicePointManager]::SecurityProtocol = $previousTls
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
Usage: install.ps1 -Agent codex|claude [-Version 1.19.0]

Run from your project root. Downloads the latest published stable official release
(or the explicit version) and installs only into .agents/skills/aurae for Codex or
.claude/skills/aurae for Claude Code. Refuses existing installations and linked paths.
Requires PowerShell 5.1+ and access to public GitHub HTTPS; no gh, npm, or Git needed.
'@
    return
}

# Keep the only task invocation last: definitions are inert until parsing completes.
if ($PSBoundParameters.ContainsKey('Version') -and [string]::IsNullOrWhiteSpace($Version)) {
    throw 'Version cannot be empty; omit -Version to select the latest published stable release.'
}
Invoke-AuraeProjectInstall -SelectedAgent $Agent -SelectedVersion $Version

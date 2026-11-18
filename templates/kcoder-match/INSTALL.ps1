# ASCII-only for Windows PowerShell 5.1 and PowerShell 7.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$ProjectPath,
    [switch]$VerifyOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$sourceRoot = (Resolve-Path -LiteralPath $PSScriptRoot).ProviderPath
$project = Get-Item -LiteralPath $ProjectPath -Force
if (-not $project.PSIsContainer) { throw 'ProjectPath must be an existing directory.' }
$projectRoot = $project.FullName
if ($sourceRoot.TrimEnd([char[]]'\/') -eq $projectRoot.TrimEnd([char[]]'\/')) {
    throw 'Source and destination must differ. Extract the package outside the project.'
}
$manifestPath = Join-Path $sourceRoot 'MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.schemaVersion -ne 1) { throw 'Unsupported manifest version.' }
$seen = @{}
foreach ($entry in $manifest.files) {
    $relative = [string]$entry.path
    if ([string]::IsNullOrWhiteSpace($relative) -or $relative -match '(^/|\\|:|(^|/)\.\.(/|$)|(^|/)\.(/|$))') {
        throw "Unsafe manifest path: $relative"
    }
    if ($seen.ContainsKey($relative)) { throw "Duplicate manifest path: $relative" }
    $seen[$relative] = $true
    $file = Join-Path $sourceRoot $relative
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing source: $relative" }
    $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne [string]$entry.sha256) { throw "Source hash mismatch: $relative" }
}
$payload = @(
    'AGENTS.md',
    'docs/PROJECT.md',
    'docs/TASKS.md',
    'docs/EVIDENCE.md',
    'THIRD_PARTY_NOTICES.md',
    '.kcoder/skills/cp29-debug/SKILL.md',
    '.kcoder/skills/cp29-innovation/SKILL.md',
    '.kcoder/skills/cp29-delivery/SKILL.md'
)
# Check all conflicts before writing anything. Existing different files need manual merging.
$conflicts = @()
foreach ($relative in $payload) {
    if (-not $seen.ContainsKey($relative)) { throw "Payload absent from manifest: $relative" }
    $destination = Join-Path $projectRoot $relative
    $parent = Split-Path -Parent $destination
    while ($parent -and $parent.Length -ge $projectRoot.Length) {
        if (Test-Path -LiteralPath $parent) {
            $item = Get-Item -LiteralPath $parent -Force
            if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw "Invalid or redirected destination parent: $parent"
            }
        }
        if ($parent -eq $projectRoot) { break }
        $parent = Split-Path -Parent $parent
    }
    if (Test-Path -LiteralPath $destination) {
        $item = Get-Item -LiteralPath $destination -Force
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Destination must be a regular file: $destination"
        }
        $sourceHash = (Get-FileHash -LiteralPath (Join-Path $sourceRoot $relative) -Algorithm SHA256).Hash
        if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $sourceHash) {
            $conflicts += $relative
        }
    }
}
if ($conflicts.Count -gt 0) { throw ('Merge manually; no files written. Conflicts: ' + ($conflicts -join ', ')) }
if ($VerifyOnly) {
    Write-Output 'PASS: package hashes and destination conflicts checked; no files written.'
    return
}
foreach ($relative in $payload) {
    $destination = Join-Path $projectRoot $relative
    if (Test-Path -LiteralPath $destination) { Write-Output "UNCHANGED: $relative"; continue }
    if ($PSCmdlet.ShouldProcess($destination, 'Copy new project configuration file')) {
        $parent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        # Atomic no-overwrite check in File.Copy also protects files created after preflight.
        [IO.File]::Copy((Join-Path $sourceRoot $relative), $destination, $false)
        $a = (Get-FileHash -LiteralPath (Join-Path $sourceRoot $relative) -Algorithm SHA256).Hash
        $b = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($a -ne $b) { throw "Post-copy hash mismatch: $relative" }
        Write-Output "COPIED: $relative"
    }
}
Write-Output 'File phase finished. No model, skill activation, approval, pairing or runtime settings changed.'
Write-Output 'Next: open the target project in KCoder, check the skill catalog, enable only intended skills, and start a NEW conversation.'

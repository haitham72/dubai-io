<#
.SYNOPSIS
Stop local Supabase containers cleanly (preserving volume unless -NoBackup is passed).
#>
[CmdletBinding()]
param(
    [switch]$NoBackup
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location -LiteralPath $repoRoot

$argsList = @('--yes', 'supabase@2.121.0', 'stop')
if ($NoBackup) {
    $argsList += '--no-backup'
}

& npx.cmd @argsList
exit $LASTEXITCODE

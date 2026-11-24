<#
.SYNOPSIS
Apply an entry's own *.sql files into its own PostgreSQL schema inside local Supabase (D12).
.DESCRIPTION
Never touches supabase/migrations/. Creates the target schema if missing and executes sorted
*.sql files wrapped in `SET search_path TO <schema>, extensions, public;` inside the running
local Supabase Postgres container.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('community', 'messenger', 'shared')]
    [string]$Entry,

    [string]$Schema = '',
    [string]$SqlDir = '',
    [string]$Container = 'supabase_db_dubai-io'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path

if (-not $Schema) {
    $Schema = switch ($Entry) {
        'community' { 'community' }
        'messenger' { 'messenger' }
        'shared'    { 'dubaiio' }
    }
}

if ($Schema -notmatch '^[a-z][a-z0-9_]{0,62}$') {
    throw "Invalid PostgreSQL schema identifier '$Schema'. Must match ^[a-z][a-z0-9_]{0,62}$."
}

if (-not $SqlDir) {
    $SqlDir = switch ($Entry) {
        'community' { Join-Path $repoRoot 'apps\community\supabase' }
        'messenger' { Join-Path $repoRoot 'apps\messenger\supabase' }
        'shared'    { Join-Path $PSScriptRoot 'sql' }
    }
}

$resolvedDir = [System.IO.Path]::GetFullPath($SqlDir)
$frozenMigrations = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'supabase\migrations'))
if ($resolvedDir.StartsWith($frozenMigrations, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to read from frozen supabase/migrations/: $resolvedDir"
}

$running = docker ps --filter "name=^/${Container}$" --format '{{.Names}}'
if ($LASTEXITCODE -ne 0 -or -not $running) {
    throw "Local Supabase database container '$Container' is not running. Run start.ps1 first."
}

Write-Host "Ensuring schema '$Schema' exists in container '$Container' ..."
$createSql = "CREATE SCHEMA IF NOT EXISTS $Schema;"
$createSql | docker exec -i $Container psql -U postgres -d postgres -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path -LiteralPath $resolvedDir)) {
    Write-Host "SQL directory does not exist yet ($resolvedDir); schema '$Schema' is ready (0 SQL files applied)."
    exit 0
}

$files = @(Get-ChildItem -LiteralPath $resolvedDir -Filter '*.sql' -File | Sort-Object Name)
if ($files.Count -eq 0) {
    Write-Host "No *.sql files found in $resolvedDir; schema '$Schema' is ready (0 SQL files applied)."
    exit 0
}

foreach ($file in $files) {
    Write-Host "Applying $($file.Name) into schema '$Schema' ..."
    $body = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
    $wrapped = "SET search_path TO $Schema, extensions, public;`n$body"
    $wrapped | docker exec -i $Container psql -U postgres -d postgres -v ON_ERROR_STOP=1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Applied $($files.Count) SQL file(s) from $resolvedDir into schema '$Schema'."

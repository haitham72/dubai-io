<#
.SYNOPSIS
Start local Supabase in Docker using the repo's unedited supabase/config.toml (D12).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
Set-Location -LiteralPath $repoRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop CLI ('docker') was not found on PATH."
}
docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker daemon is not running. Start Docker Desktop first."
}
if (-not (Get-Command npx.cmd -ErrorAction SilentlyContinue)) {
    throw "Node.js ('npx.cmd') was not found on PATH; required to run pinned supabase@2.121.0."
}

Write-Host "Starting local Supabase (supabase@2.121.0) in $repoRoot ..."
npx.cmd --yes supabase@2.121.0 start
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Applying existing base migrations (read-only supabase/migrations/) ..."
npx.cmd --yes supabase@2.121.0 migration up --local
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$health = Invoke-RestMethod -Uri "http://127.0.0.1:15421/auth/v1/health" -TimeoutSec 10
Write-Host "GoTrue Auth healthy: $($health.name) $($health.version)"
Write-Host "API/Auth: http://127.0.0.1:15421 | Postgres 17: postgresql://postgres:postgres@127.0.0.1:15422/postgres | Studio: http://127.0.0.1:15423"
Write-Host "Run 'npx.cmd --yes supabase@2.121.0 status -o env' to read local keys into your current shell."

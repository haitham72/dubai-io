param(
    [switch]$KeepInfra
)

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$MemCompose = Join-Path $RepoRoot "apps\memory\docker-compose.yml"
$PidsFile = Join-Path $PSScriptRoot ".pids.json"

Write-Host "=== Stopping Dubai-io Stack (preserving Postgres volume) ==="

if (Test-Path $PidsFile) {
    try {
        $pids = Get-Content $PidsFile -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($prop in $pids.PSObject.Properties) {
            $procId = $prop.Value
            if ($procId) {
                $p = Get-Process -Id ([int]$procId) -ErrorAction SilentlyContinue
                if ($p) {
                    Write-Host "Stopping $($prop.Name) (pid=$procId)..."
                    & taskkill /PID $procId /T /F 2>$null | Out-Null
                }
            }
        }
    } catch {}
    Remove-Item $PidsFile -Force -ErrorAction SilentlyContinue
}

if ($KeepInfra) {
    Write-Host "Stopping memory api, worker-p0, worker-p1, beat (keeping postgres/rabbitmq/redis)..."
    & docker compose -f $MemCompose stop api worker-p0 worker-p1 beat | Out-Null
} else {
    Write-Host "Stopping all temporal-memory containers (volumes preserved)..."
    & docker compose -f $MemCompose stop | Out-Null
}

Write-Host "Stopped cleanly."

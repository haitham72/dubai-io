param(
    [switch]$KeepInfra
)

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$MemCompose = Join-Path $RepoRoot "apps\memory\docker-compose.yml"
$PidsFile = Join-Path $PSScriptRoot ".pids.json"

Write-Host "=== Stopping Dubai-io Stack (preserving Postgres volume) ==="

# Never stop containers while another agent holds the Docker lock: check every 2 minutes, up to 60 minutes, then skip.
$lock = if ($env:DUBAI_DOCKER_LOCK) { $env:DUBAI_DOCKER_LOCK } else {
    Join-Path (Split-Path -Parent $RepoRoot) "contest-memory\apps\memory\upgrade\reports\DOCKER_LOCK"
}
$lockDeadline = (Get-Date).AddMinutes(60)
$dockerSkipped = $false
while (Test-Path $lock) {
    if ((Get-Date) -ge $lockDeadline) { $dockerSkipped = $true; break }
    Write-Host "DOCKER_LOCK present; waiting 2 minutes before touching Docker..."
    Start-Sleep -Seconds 120
}

if (Test-Path $PidsFile) {
    try {
        $pids = Get-Content $PidsFile -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($prop in $pids.PSObject.Properties) {
            $procId = $prop.Value
            if ($procId) {
                $p = Get-Process -Id ([int]$procId) -ErrorAction SilentlyContinue
                if ($p) {
                    Write-Host "Stopping $($prop.Name) (pid=$procId) [PID file entry]..."
                    & taskkill /PID $procId /T /F 2>$null | Out-Null
                }
            }
        }
    } catch {}
    Remove-Item $PidsFile -Force -ErrorAction SilentlyContinue
}

if ($dockerSkipped) {
    Write-Host "DOCKER_LOCK still present after 60 minutes: app processes stopped, Docker containers left untouched."
} elseif ($KeepInfra) {
    Write-Host "Stopping memory api, worker-p0, worker-p1, beat (keeping postgres/rabbitmq/redis)..."
    & docker compose -f $MemCompose stop api worker-p0 worker-p1 beat | Out-Null
} else {
    Write-Host "Stopping all temporal-memory containers (volumes preserved)..."
    & docker compose -f $MemCompose stop | Out-Null
}

Write-Host "Stopped cleanly."

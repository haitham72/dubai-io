param(
    [int]$WebPort = 8082,
    [int]$ExpoPort = 8081,
    [int]$ApiPort = 8000,
    [int]$MemoryPort = 8040,
    [switch]$AllowStoppedDesktop
)

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$MemCompose = Join-Path $RepoRoot "apps\memory\docker-compose.yml"
$PidsFile = Join-Path $PSScriptRoot ".pids.json"

function Get-LanIp {
    try {
        $configs = Get-NetIPConfiguration | Where-Object {
            $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" -and
            $_.InterfaceAlias -notmatch "vEthernet|WSL|Docker|Loopback"
        }
        foreach ($cfg in $configs) {
            foreach ($addr in $cfg.IPv4Address) {
                if ($addr.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)') {
                    return $addr.IPAddress
                }
            }
        }
    } catch {}
    return "127.0.0.1"
}

function Test-Http([string]$Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Test-Port([int]$Port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $iar = $c.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(500, $false)
        if ($ok) { $c.EndConnect($iar); $c.Close(); return $true }
        $c.Close()
        return $false
    } catch {
        return $false
    }
}

$lanIp = Get-LanIp
$rows = New-Object System.Collections.Generic.List[object]
$anyRed = $false

function Add-Row([string]$Component, [bool]$Ok, [string]$Detail) {
    if (-not $Ok) { $script:anyRed = $true }
    $rows.Add([PSCustomObject]@{
        Component = $Component
        Status    = if ($Ok) { "GREEN" } else { "RED" }
        Detail    = $Detail
    })
}

# 1. Containers
$containers = @("postgres", "rabbitmq", "redis", "api", "worker-p0", "worker-p1", "beat")
$psJson = & docker compose -f $MemCompose ps --format json 2>$null
$cMap = @{}
foreach ($line in $psJson) {
    if (-not $line) { continue }
    try {
        $obj = $line | ConvertFrom-Json
        $cMap[$obj.Service] = $obj
    } catch {}
}
foreach ($svc in $containers) {
    $info = $cMap[$svc]
    if ($null -eq $info) {
        Add-Row "container:$svc" $false "not running"
    } else {
        $healthy = ($info.State -eq "running") -and ((-not $info.Health) -or ($info.Health -eq "healthy"))
        Add-Row "container:$svc" $healthy "$($info.State) ($($info.Health))"
    }
}

# 2. HTTP endpoints
$memOk = Test-Http "http://127.0.0.1:$MemoryPort/health"
Add-Row "memory-api:$MemoryPort" $memOk "http://localhost:$MemoryPort/health"

$apiOk = Test-Http "http://127.0.0.1:$ApiPort/api/health"
Add-Row "apps/api:$ApiPort" $apiOk "http://localhost:$ApiPort/api/health"

$webOk = Test-Http "http://127.0.0.1:$WebPort/"
Add-Row "website:$WebPort" $webOk "http://localhost:$WebPort"

$expoOk = Test-Port $ExpoPort
Add-Row "expo-lan:$ExpoPort" $expoOk "exp://${lanIp}:$ExpoPort"

# 3. Queue depth
$qDepth = "unknown"
$qOk = $false
try {
    $rawCount = (& docker compose -f $MemCompose exec -T postgres psql -U tm -d tm -t -A -c "SELECT count(*) FROM jobs WHERE state IN ('queued','leased')" 2>$null)
    if ($LASTEXITCODE -eq 0 -and $rawCount) {
        $qDepth = ($rawCount | Select-Object -Last 1).Trim()
        $qOk = $true
    }
} catch {}
Add-Row "queue-depth" $qOk "pending/leased jobs=$qDepth"

# 4. Active LLM runner
$lmOk = $false
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 2
    $lmOk = $true
} catch {}
$claudeCmd = Get-Command "claude" -ErrorAction SilentlyContinue
if (-not $claudeCmd -and (Test-Path "$env:USERPROFILE\.local\bin\claude.exe")) {
    $claudeCmd = Get-Item "$env:USERPROFILE\.local\bin\claude.exe"
}
$runnerOk = $lmOk -or ($null -ne $claudeCmd)
$runnerDesc = if ($lmOk) { "LM Studio (:1234) + claude -p (Haiku)" } elseif ($claudeCmd) { "claude -p (Haiku, medium effort)" } else { "none found" }
Add-Row "llm-runner" $runnerOk $runnerDesc

# 5. Desktop process
$deskOk = $false
$deskDetail = "stopped"
if (Test-Path $PidsFile) {
    try {
        $pids = Get-Content $PidsFile -Raw | ConvertFrom-Json
        if ($pids.desktop -and (Get-Process -Id ([int]$pids.desktop) -ErrorAction SilentlyContinue)) {
            $deskOk = $true
            $deskDetail = "pid=$($pids.desktop)"
        }
    } catch {}
}
if ($AllowStoppedDesktop) {
    $rows.Add([PSCustomObject]@{ Component = "desktop"; Status = if ($deskOk) { "GREEN" } else { "SKIP" }; Detail = $deskDetail })
} else {
    Add-Row "desktop" $deskOk $deskDetail
}

# Print formatted table with color
Write-Host ""
Write-Host ("=== Dubai-io Stack Health (LAN IP: {0}) ===" -f $lanIp)
foreach ($r in $rows) {
    $color = if ($r.Status -eq "GREEN") { "Green" } elseif ($r.Status -eq "SKIP") { "Yellow" } else { "Red" }
    Write-Host ("[{0,-5}] {1,-22} {2}" -f $r.Status, $r.Component, $r.Detail) -ForegroundColor $color
}
Write-Host ""

if ($anyRed) { exit 1 } else { exit 0 }

param(
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
$containers = @("postgres", "rabbitmq", "redis", "api")
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

# 1b. Docker worker/beat containers must NOT run (host workers own the queues; no double consumers).
foreach ($svc in @("worker-p0", "worker-p1", "beat")) {
    $info = $cMap[$svc]
    $running = ($null -ne $info) -and ($info.State -eq "running")
    Add-Row "no-docker:$svc" (-not $running) $(if ($running) { "RUNNING in Docker: run stop-all/start-all" } else { "not running (good)" })
}

# 1c. Host claude CLI (version only, no auth details) and host Celery workers / beat
$claudeCmd = Get-Command "claude" -ErrorAction SilentlyContinue
$claudePath = if ($claudeCmd) { if ($claudeCmd.Source) { $claudeCmd.Source } else { $claudeCmd.Path } } elseif (Test-Path "$env:USERPROFILE\.local\bin\claude.exe") { "$env:USERPROFILE\.local\bin\claude.exe" } else { $null }
if ($claudePath) {
    $ver = (& $claudePath --version 2>$null | Select-Object -First 1)
    Add-Row "host-claude-cli" ([bool]$ver) "$ver"
} else {
    Add-Row "host-claude-cli" $false "claude CLI not found"
}
$MemDir = Join-Path $RepoRoot "apps\memory"
$MemPy = $null
foreach ($cand in @((Join-Path $MemDir ".venv\Scripts\python.exe"),
        (Join-Path (Split-Path -Parent $RepoRoot) "contest-memory\apps\memory\.venv\Scripts\python.exe"),
        (Join-Path $RepoRoot "apps\api\.venv\Scripts\python.exe"),
        (Join-Path (Split-Path -Parent $RepoRoot) "contest\apps\api\.venv\Scripts\python.exe"))) {
    if (Test-Path $cand) { $MemPy = $cand; break }
}
foreach ($q in @(@{n="p0"; label="worker-p0 (mem.p0)"}, @{n="p1"; label="worker-p1 (mem.p1,mem.p3)"})) {
    $ok = $false; $detail = "no python venv"
    if ($MemPy) {
        $oldPp = $env:PYTHONPATH; $env:PYTHONPATH = (Join-Path $MemDir "src")
        try {
            $out = (& $MemPy -m celery -A temporal_memory.queue.celery_app inspect --timeout=4 --destination="$($q.n)@w" ping 2>&1) -join " "
            $ok = ($out -match "pong")
            $detail = if ($ok) { "host worker $($q.n)@w answers ping" } else { "no pong from $($q.n)@w" }
        } catch { $detail = "inspect failed" } finally { $env:PYTHONPATH = $oldPp }
    }
    Add-Row "host:$($q.label)" $ok $detail
}
$beats = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -match "temporal_memory\.queue\.celery_app" -and $_.CommandLine -match "\sbeat\s" -and $_.Name -match "python"
})
# the venv launcher and the real interpreter both match: count distinct parents-or-self roots
$beatRoots = @($beats | Where-Object { -not ($beats.ProcessId -contains $_.ParentProcessId) })
Add-Row "host:beat (exactly 1)" ($beatRoots.Count -eq 1) "$($beatRoots.Count) beat process(es)"

# 2. HTTP endpoints
$memOk = Test-Http "http://127.0.0.1:$MemoryPort/health"
Add-Row "memory-api:$MemoryPort" $memOk "http://localhost:$MemoryPort/health"

# 2a'. Semantic model loaded (start-all warms it; green only when the embedder is in memory, or semantic is off).
$semOk = $false; $semDetail = "memory API not reachable"
try {
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:$MemoryPort/health" -TimeoutSec 3
    $sm = $h.semantic
    if ($sm -and -not $sm.enabled) { $semOk = $true; $semDetail = "semantic recall disabled (TM_SEMANTIC=0)" }
    elseif ($sm -and $sm.loaded) { $semOk = $true; $semDetail = "bge-m3 loaded" }
    else { $semDetail = "model not loaded (first start downloads ~570 MB): run start-all" }
} catch {}
Add-Row "memory-semantic-model" $semOk $semDetail

# 2a. The memory image must match apps/memory (E6 FAIL 3): start-all records the source hash and the running image id.
. (Join-Path $PSScriptRoot "memory-image.ps1")
$imgOk = $false; $imgDetail = "no marker: run start-all"
$ImageMarker = Join-Path $PSScriptRoot ".memory-image.json"
if (Test-Path $ImageMarker) {
    try {
        $mk = Get-Content $ImageMarker -Raw | ConvertFrom-Json
        $curHash = Get-MemorySourceHash (Join-Path $RepoRoot "apps\memory")
        $runId = Get-MemoryApiContainerImageId $MemCompose
        if ($mk.src_hash -ne $curHash) { $imgDetail = "apps/memory changed since the image was built: run start-all" }
        elseif (-not $runId -or $runId -ne $mk.image_id) { $imgDetail = "the running api container is not the image start-all built: run start-all" }
        else { $imgOk = $true; $imgDetail = "image matches apps/memory source" }
    } catch { $imgDetail = "marker unreadable" }
}
Add-Row "memory-image-current" $imgOk $imgDetail

# 2b. Owner provisioning ready, without creating data: POST /v1/owners with the admin token and an EMPTY body. The
#     memory API authorizes first, so 422 = token accepted (nothing created); 401/403 = token rejected.
$provOk = $false; $provDetail = "memory admin token missing"
$envFile = Join-Path $RepoRoot "apps\memory\.env"
$adminTok = $null
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile -Encoding UTF8) { if ($line -match '^\s*TM_ADMIN_TOKEN=(.+)$') { $adminTok = $matches[1].Trim() } }
}
if ($adminTok) {
    $code = 0
    try {
        $null = Invoke-WebRequest -Method Post -Uri "http://127.0.0.1:$MemoryPort/v1/owners" -Headers @{ Authorization = "Bearer $adminTok" } `
            -ContentType "application/json" -Body "{}" -UseBasicParsing -TimeoutSec 5
        $code = 200
    } catch { if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode } }
    $memAccepts = ($code -eq 422)
    $AdminMarker = Join-Path $PSScriptRoot ".admin-token-passed.json"
    $apiHas = $false
    if (Test-Path $AdminMarker) {
        try {
            $am = Get-Content $AdminMarker -Raw | ConvertFrom-Json
            $apiHas = ($am.apps_api -and (Get-Process -Id ([int]$am.apps_api) -ErrorAction SilentlyContinue))
        } catch {}
    }
    $provOk = ($memAccepts -and [bool]$apiHas)
    $provDetail = if ($provOk) { "memory accepts the admin token (http 422 on empty body, nothing created); apps/api was started with it" }
        elseif (-not $memAccepts) { "memory API rejected the admin token (http $code): restart the memory api via start-all" }
        else { "apps/api was not started by start-all with TM_ADMIN_TOKEN: stop-all then start-all" }
}
Add-Row "owner-provisioning-ready" $provOk $provDetail

$apiOk = Test-Http "http://127.0.0.1:$ApiPort/api/health"
Add-Row "apps/api:$ApiPort" $apiOk "http://localhost:$ApiPort/api/health"

$webOk = Test-Http "http://127.0.0.1:$ExpoPort/status"
Add-Row "website:$ExpoPort" $webOk "http://localhost:$ExpoPort"

$expoOk = Test-Port $ExpoPort
Add-Row "expo-lan:$ExpoPort" $expoOk "exp://${lanIp}:$ExpoPort"

# 2b. Community + Messenger (E5): API up, shared identity, real http memory backend; website up
foreach ($e in @(@{n="community"; api=8060; web=3060}, @{n="messenger"; api=8070; web=5173})) {
    $st = $null
    try { $st = Invoke-RestMethod -Uri "http://127.0.0.1:$($e.api)/api/shared/status" -TimeoutSec 3 } catch {}
    Add-Row "$($e.n)-api:$($e.api)" ($null -ne $st) $(if ($st) { "http://localhost:$($e.api)" } else { "not answering" })
    Add-Row "$($e.n)-memory" ($null -ne $st -and $st.memory_backend -eq "http" -and $st.identity_shared -and $st.memory_bridge) $(if ($st) { "backend=$($st.memory_backend) identity_shared=$($st.identity_shared) bridge=$($st.memory_bridge)" } else { "n/a" })
    Add-Row "$($e.n)-website:$($e.web)" (Test-Http "http://127.0.0.1:$($e.web)/") "http://localhost:$($e.web)  (LAN http://${lanIp}:$($e.web))"
}

$lanOk = ($lanIp -ne "127.0.0.1")
Add-Row "lan-ip" $lanOk $lanIp

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

# Per-queue depth (RabbitMQ)
try {
    $qs = (& docker compose -f $MemCompose exec -T rabbitmq rabbitmqctl list_queues name messages -q 2>$null) | Where-Object { $_ -match "^mem\." }
    $qd = ($qs | ForEach-Object { ($_ -split "\s+") -join "=" }) -join " "
    Add-Row "queue-depth-rabbit" ($LASTEXITCODE -eq 0) $(if ($qd) { $qd } else { "no mem.* queues yet" })
} catch { Add-Row "queue-depth-rabbit" $false "unavailable" }

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

# Dubai-io one-command dev stack. Ports: memory API 8040, apps/api 8000, Expo (web + LAN dev server) 8081.
# Never uses 8766/8767/8768 (taken by other tools). Never adds a firewall rule (README documents the command).
param(
    [switch]$NoDesktop,
    [switch]$Rebuild,
    [int]$ExpoPort = 8081,
    [int]$ApiPort = 8000,
    [int]$MemoryPort = 8040
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogsDir = Join-Path $PSScriptRoot "logs"
$PidsFile = Join-Path $PSScriptRoot ".pids.json"
$MemDir = Join-Path $RepoRoot "apps\memory"
$MemCompose = Join-Path $MemDir "docker-compose.yml"
$MemEnv = Join-Path $MemDir ".env"
$MemEnvExample = Join-Path $MemDir ".env.example"
$ApiDir = Join-Path $RepoRoot "apps\api"
$ApiEnv = Join-Path $ApiDir ".env"
$ApiPy = Join-Path $ApiDir ".venv\Scripts\python.exe"
if (-not (Test-Path $ApiPy)) {
    $SiblingPy = Join-Path (Split-Path -Parent $RepoRoot) "contest\apps\api\.venv\Scripts\python.exe"
    if (Test-Path $SiblingPy) { $ApiPy = $SiblingPy }
}
$MobileDir = Join-Path $RepoRoot "apps\mobile"
$DesktopDir = Join-Path $RepoRoot "apps\desktop"
# npm ci (not install): honours package-lock.json and never rewrites it. Re-run when node_modules is missing or older
# than the lock file (e.g. after a merge that added dependencies).
function Ensure-NodeModules([string]$Dir, [string]$Label) {
    $lock = Join-Path $Dir "package-lock.json"
    $marker = Join-Path $Dir "node_modules\.package-lock.json"
    $stale = (-not (Test-Path $marker)) -or ((Test-Path $lock) -and ((Get-Item $lock).LastWriteTime -gt (Get-Item $marker).LastWriteTime))
    if ($stale) {
        Write-Host "[setup] npm ci in $Label..."
        Push-Location $Dir
        try {
            & npm.cmd ci --no-audit --no-fund | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "npm ci failed in $Label" }
        } finally { Pop-Location }
    }
}
Ensure-NodeModules $MobileDir "apps/mobile"
Ensure-NodeModules $DesktopDir "apps/desktop"

# Memory engine inside the apps/api venv (E1 item 6): apps/api mounts the memory bridge in-process and needs
# json-repair, celery, redis and the temporal_memory package. Editable install from the checkout that owns the venv.
if (Test-Path $ApiPy) {
    & $ApiPy -c "import temporal_memory, json_repair, celery, redis" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $VenvApiDir = (Resolve-Path (Join-Path (Split-Path -Parent $ApiPy) "..\..")).Path
        $MemPkgDir = (Resolve-Path (Join-Path $VenvApiDir "..\memory")).Path
        Write-Host "[setup] Installing the memory engine into the apps/api venv (pip install -e apps/memory)..."
        & $ApiPy -m pip install --quiet -e $MemPkgDir
        if ($LASTEXITCODE -ne 0) { throw "pip install -e apps/memory failed" }
    }
    & $ApiPy -m pip check | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Warning "pip check reports conflicts in the apps/api venv; run it by hand to see them" }
}
$DesktopOutDir = Join-Path $env:LOCALAPPDATA "Dubai-io\desktop-dist"

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

function New-SecretToken {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([Convert]::ToBase64String($bytes)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Read-EnvMap([string]$Path) {
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    foreach ($line in Get-Content $Path -Encoding UTF8) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $map[$matches[1]] = $matches[2]
        }
    }
    return $map
}

function Upsert-EnvFile([string]$Path, [hashtable]$Updates) {
    $lines = @()
    if (Test-Path $Path) {
        $lines = @(Get-Content $Path -Encoding UTF8)
    }
    $seen = @{}
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($line in $lines) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $k = $matches[1]
            if ($Updates.ContainsKey($k)) {
                $out.Add("$k=$($Updates[$k])")
                $seen[$k] = $true
                continue
            }
        }
        $out.Add($line)
    }
    foreach ($k in $Updates.Keys) {
        if (-not $seen.ContainsKey($k)) {
            $out.Add("$k=$($Updates[$k])")
        }
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($Path, $out, $utf8NoBom)
}

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
        $fallback = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {
            $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)' -and
            $_.InterfaceAlias -notmatch "vEthernet|WSL|Docker|Loopback"
        } | Select-Object -First 1 -ExpandProperty IPAddress
        if ($fallback) { return $fallback }
    } catch {}
    return "127.0.0.1"
}

function Test-HttpOk([string]$Url, [int]$TimeoutSec = 3) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Test-PortOpen([int]$Port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(500, $false)
        if ($ok) { $client.EndConnect($iar); $client.Close(); return $true }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

function Load-Pids {
    if (Test-Path $PidsFile) {
        try {
            $raw = Get-Content $PidsFile -Raw -Encoding UTF8 | ConvertFrom-Json
            $h = @{}
            foreach ($p in $raw.PSObject.Properties) { $h[$p.Name] = $p.Value }
            return $h
        } catch {}
    }
    return @{}
}

function Save-Pids([hashtable]$Pids) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($PidsFile, ($Pids | ConvertTo-Json -Depth 4), $utf8NoBom)
}

function Is-Alive($Id) {
    if (-not $Id) { return $false }
    return ($null -ne (Get-Process -Id ([int]$Id) -ErrorAction SilentlyContinue))
}

function Wait-DockerLock {
    # Another agent may be running database tests. While the lock file exists do not touch containers:
    # check every 2 minutes for up to 60 minutes, then skip this cycle (exit 3).
    $lock = if ($env:DUBAI_DOCKER_LOCK) { $env:DUBAI_DOCKER_LOCK } else {
        Join-Path (Split-Path -Parent $RepoRoot) "contest-memory\apps\memory\upgrade\reports\DOCKER_LOCK"
    }
    $deadline = (Get-Date).AddMinutes(60)
    while (Test-Path $lock) {
        if ((Get-Date) -ge $deadline) {
            Write-Host "DOCKER_LOCK still present after 60 minutes ($lock). Skipping this cycle."
            exit 3
        }
        Write-Host "DOCKER_LOCK present; waiting 2 minutes before touching Docker..."
        Start-Sleep -Seconds 120
    }
}

$lanIp = Get-LanIp
$pids = Load-Pids

Write-Host "=== Dubai-io Stack Startup (LAN IP: $lanIp) ==="

# 1. LLM Runner Detection (LM Studio :1234 vs claude -p subscription)
$lmOk = $false
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 2
    $lmOk = $true
} catch {}
$claudeCmd = Get-Command "claude" -ErrorAction SilentlyContinue
if (-not $claudeCmd -and (Test-Path "$env:USERPROFILE\.local\bin\claude.exe")) {
    $claudeCmd = Get-Item "$env:USERPROFILE\.local\bin\claude.exe"
}
if ($lmOk) {
    $activeRunner = "LM Studio Qwen (:1234, owner-device first) + claude -p (Haiku, medium effort)"
} elseif ($claudeCmd) {
    $activeRunner = "claude -p subscription (Haiku, medium effort)"
} else {
    $activeRunner = "WARNING: neither LM Studio (:1234) nor claude CLI detected"
}
Write-Host "[1/6] LLM runner: $activeRunner"

# 2. Memory .env (never prints values) & Docker Compose
if (-not (Test-Path $MemEnv) -and (Test-Path $MemEnvExample)) {
    Copy-Item $MemEnvExample $MemEnv
}
$memMap = Read-EnvMap $MemEnv
$memUpdates = @{
    "TM_AGENT_CLI_CMD" = 'claude -p --model {model} --effort medium --output-format json --tools "" --disable-slash-commands'
    "TM_CLOUD_MODEL"   = "claude-haiku-4-5-20251001"
}
if (-not $memMap["TM_ADMIN_TOKEN"] -or -not $memMap["TM_ADMIN_TOKEN"].Trim()) {
    $memUpdates["TM_ADMIN_TOKEN"] = New-SecretToken
}
if (-not $memMap["TM_WORKER_RUNNER"]) {
    $memUpdates["TM_WORKER_RUNNER"] = if ($lmOk) { "lmstudio" } else { "agent-cli" }
}
Upsert-EnvFile $MemEnv $memUpdates
$memAdminToken = (Read-EnvMap $MemEnv)["TM_ADMIN_TOKEN"]

Wait-DockerLock
Write-Host "[2/6] Starting temporal_memory infra (postgres, rabbitmq, redis)..."
& docker compose -f $MemCompose up -d postgres rabbitmq redis | Out-Null
if ($LASTEXITCODE -ne 0) { throw "docker compose infra failed" }

$infraDeadline = (Get-Date).AddSeconds(90)
do {
    $pgReady = (& docker compose -f $MemCompose exec -T postgres pg_isready -h 127.0.0.1 -U tm -d tm 2>$null)
    $pgOk = ($LASTEXITCODE -eq 0)
    $rbOk = Test-PortOpen 5682
    $rdOk = Test-PortOpen 6390
    if ($pgOk -and $rbOk -and $rdOk) { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $infraDeadline)
if (-not ($pgOk -and $rbOk -and $rdOk)) { throw "Memory infra failed health wait" }

$apiImage = (& docker images -q temporal-memory-api 2>$null)
if ($Rebuild -or -not $apiImage) {
    Write-Host "[2/6] Building & starting memory api, worker-p0, worker-p1, beat..."
    & docker compose -f $MemCompose up -d --build api worker-p0 worker-p1 beat | Out-Null
} else {
    Write-Host "[2/6] Starting memory api, worker-p0, worker-p1, beat..."
    & docker compose -f $MemCompose up -d api worker-p0 worker-p1 beat | Out-Null
}
if ($LASTEXITCODE -ne 0) { throw "docker compose memory services failed" }

$memDeadline = (Get-Date).AddSeconds(120)
while (-not (Test-HttpOk "http://127.0.0.1:$MemoryPort/health") -and (Get-Date) -lt $memDeadline) {
    Start-Sleep -Seconds 2
}
if (-not (Test-HttpOk "http://127.0.0.1:$MemoryPort/health")) {
    throw "Memory API :$MemoryPort/health did not become ready"
}

# 3. Service token for apps/api -> memory. Created through the memory API admin flow ONLY when TM_SERVICE_TOKEN is
#    missing from apps/api/.env; appended without printing; no other line of that file is ever modified.
Write-Host "[3/6] Checking the apps/api memory service token..."
$apiMap = Read-EnvMap $ApiEnv
$svcToken = $apiMap["TM_SERVICE_TOKEN"]
if (-not $svcToken -or -not $svcToken.Trim()) {
    $minted = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$MemoryPort/v1/tokens" `
        -Headers @{ Authorization = "Bearer $memAdminToken" } -ContentType "application/json" `
        -Body '{"role":"admin","label":"api-bridge"}' -TimeoutSec 10
    $svcToken = [string]$minted.token
    $prefix = ""
    if ((Test-Path $ApiEnv) -and ((Get-Item $ApiEnv).Length -gt 0)) {
        $raw = [System.IO.File]::ReadAllText($ApiEnv)
        if (-not $raw.EndsWith("`n")) { $prefix = "`n" }
    }
    [System.IO.File]::AppendAllText($ApiEnv, "${prefix}TM_SERVICE_TOKEN=$svcToken`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "      minted and appended TM_SERVICE_TOKEN to apps/api/.env (value not shown)"
} else {
    Write-Host "      TM_SERVICE_TOKEN already present in apps/api/.env"
}

# 4. Start apps/api on :8000 (idempotent)
Write-Host "[4/6] Ensuring apps/api on :$ApiPort..."
if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/health")) {
    if (-not (Test-Path $ApiPy)) { throw "apps/api virtualenv missing at $ApiPy" }
    # Process environment for the api child only (wins over .env; the file is not rewritten).
    $env:MEMORY_BRIDGE_BACKEND = "http"
    $env:TM_BASE_URL = "http://localhost:$MemoryPort"
    $env:PUBLIC_API_BASE_URL = "http://${lanIp}:$ApiPort"
    if (-not $apiMap["TM_SERVICE_TOKEN"]) { $env:TM_SERVICE_TOKEN = $svcToken }
    $apiOut = Join-Path $LogsDir "api.out.log"
    $apiErr = Join-Path $LogsDir "api.err.log"
    $proc = Start-Process -FilePath $ApiPy `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$ApiPort") `
        -WorkingDirectory $ApiDir -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr `
        -WindowStyle Hidden -PassThru
    $pids["apps_api"] = $proc.Id
    Remove-Item Env:MEMORY_BRIDGE_BACKEND, Env:TM_BASE_URL, Env:PUBLIC_API_BASE_URL, Env:TM_SERVICE_TOKEN -ErrorAction SilentlyContinue
    $apiDeadline = (Get-Date).AddSeconds(45)
    while (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/health") -and (Get-Date) -lt $apiDeadline) {
        Start-Sleep -Seconds 1
    }
    if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/health")) {
        throw "apps/api failed to respond on :$ApiPort/api/health (check $apiErr)"
    }
}

# 5. Expo dev server on :8081: serves the website (web bundle, E2 return_to = http://localhost:8081/connect)
#    and the LAN dev server the iPhone connects to (Expo Go / dev client), from ONE process.
Write-Host "[5/6] Ensuring Expo (web + iPhone LAN) on :$ExpoPort..."
if (-not (Test-PortOpen $ExpoPort)) {
    $expoOut = Join-Path $LogsDir "expo.out.log"
    $expoErr = Join-Path $LogsDir "expo.err.log"
    Remove-Item $expoOut, $expoErr -Force -ErrorAction SilentlyContinue
    $cmdArgs = "/c set CI=1&& set EXPO_NO_TELEMETRY=1&& set EXPO_PUBLIC_API_URL=http://localhost:$ApiPort&& npx.cmd expo start --host lan --port $ExpoPort"
    $expoProc = Start-Process -FilePath "cmd.exe" -ArgumentList @($cmdArgs) `
        -WorkingDirectory $MobileDir -RedirectStandardOutput $expoOut -RedirectStandardError $expoErr `
        -WindowStyle Hidden -PassThru
    $pids["expo"] = $expoProc.Id
    $expoDeadline = (Get-Date).AddSeconds(90)
    while (-not (Test-HttpOk "http://127.0.0.1:$ExpoPort/status" 2) -and (Get-Date) -lt $expoDeadline) {
        Start-Sleep -Seconds 2
    }
}
if (-not (Test-HttpOk "http://127.0.0.1:$ExpoPort/status" 3)) {
    Write-Warning "Expo did not answer on :$ExpoPort (see scripts\dev\logs\expo.err.log)"
}

# 6. Desktop app (apps/desktop)
if (-not $NoDesktop -and -not (Is-Alive $pids["desktop"])) {
    Write-Host "[6/6] Starting apps/desktop dev window..."
    New-Item -ItemType Directory -Path $DesktopOutDir -Force | Out-Null
    Push-Location $DesktopDir
    try {
        & npx.cmd tsc -p tsconfig.main.json --noEmit false --outDir $DesktopOutDir | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $entryJs = Join-Path $DesktopOutDir "electron\main\index.js"
            $electronExe = Join-Path $DesktopDir "node_modules\electron\dist\electron.exe"
            if (Test-Path $electronExe) {
                $deskProc = Start-Process -FilePath "cmd.exe" `
                    -ArgumentList @("/c", "set DUBAI_DESKTOP_BOOT=1&& `"$electronExe`" `"$entryJs`"") `
                    -WorkingDirectory $DesktopDir `
                    -RedirectStandardOutput (Join-Path $LogsDir "desktop.out.log") `
                    -RedirectStandardError (Join-Path $LogsDir "desktop.err.log") `
                    -WindowStyle Hidden -PassThru
                $pids["desktop"] = $deskProc.Id
            }
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[6/6] Desktop skipped or already running."
}

Save-Pids $pids

# Firewall: never changed by this script. Report what is missing so the founder can run the documented command.
$missingFw = @()
foreach ($p in @($ApiPort, $ExpoPort)) {
    $ruleExists = Get-NetFirewallRule -Direction Inbound -Enabled True -Action Allow -ErrorAction SilentlyContinue |
        Get-NetFirewallPortFilter -ErrorAction SilentlyContinue |
        Where-Object { $_.Protocol -eq "TCP" -and ($_.LocalPort -eq "$p" -or $_.LocalPort -eq "Any") }
    if (-not $ruleExists) { $missingFw += $p }
}

Write-Host ""
Write-Host "Website URL  : http://localhost:$ExpoPort   (Expo web; Connect screen at /connect)"
Write-Host "API URL      : http://localhost:$ApiPort  (LAN: http://${lanIp}:$ApiPort)"
Write-Host "Memory API   : http://localhost:$MemoryPort"
Write-Host "iPhone Expo  : exp://${lanIp}:$ExpoPort   (scan the QR below in Expo Go)"
# Expo prints no QR in CI mode, so render one from the exp:// URL with the qrcode package already in apps/mobile.
Push-Location $MobileDir
try {
    $qrText = & node.exe -e "require('qrcode').toString(process.argv[1],{type:'terminal',small:true},function(e,s){if(!e)console.log(s)})" "exp://${lanIp}:$ExpoPort" 2>$null
    foreach ($l in $qrText) { Write-Host $l }
} catch {} finally { Pop-Location }
Write-Host "LLM runner   : $activeRunner"
if ($missingFw.Count -gt 0) {
    Write-Host "Firewall (NOT changed by this script): if the phone cannot connect, run once in an elevated PowerShell:"
    foreach ($p in $missingFw) {
        Write-Host "  netsh advfirewall firewall add rule name=`"Dubai-io Dev TCP $p`" dir=in action=allow protocol=TCP localport=$p profile=private"
    }
}
Write-Host "=== Done. Run scripts\dev\health.ps1 to verify. ==="

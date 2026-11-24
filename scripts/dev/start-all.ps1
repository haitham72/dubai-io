param(
    [switch]$NoDesktop,
    [switch]$Rebuild,
    [switch]$AddFirewall,
    [int]$WebPort = 8082,
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
if (-not (Test-Path (Join-Path $MobileDir "node_modules"))) {
    Write-Host "[setup] Installing apps/mobile node_modules..."
    Push-Location $MobileDir; try { & npm.cmd install --no-audit --no-fund | Out-Null } finally { Pop-Location }
}
if (-not (Test-Path (Join-Path $DesktopDir "node_modules"))) {
    Write-Host "[setup] Installing apps/desktop node_modules..."
    Push-Location $DesktopDir; try { & npm.cmd install --no-audit --no-fund | Out-Null } finally { Pop-Location }
}
$WebOutDir = Join-Path $env:LOCALAPPDATA "Dubai-io\expo-web"
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

# 3. Provision bridge token into apps/api/.env without printing it
Write-Host "[3/6] Provisioning apps/api bridge config (secret kept in .env)..."
$apiMap = Read-EnvMap $ApiEnv
$existingSvc = $apiMap["TM_SERVICE_TOKEN"]
$svcValid = $false
if ($existingSvc -and $existingSvc.Trim()) {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:$MemoryPort/v1/owners/__health_probe__/vault/subjects" `
            -Headers @{ Authorization = "Bearer $($existingSvc.Trim())" } -TimeoutSec 3
        $svcValid = $true
    } catch {
        if ($_.Exception.Response -and ([int]$_.Exception.Response.StatusCode -eq 200)) { $svcValid = $true }
    }
}
if (-not $svcValid) {
    $tokBody = '{"role":"admin","label":"api-bridge"}'
    $minted = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$MemoryPort/v1/tokens" `
        -Headers @{ Authorization = "Bearer $memAdminToken"; "Content-Type" = "application/json" } `
        -Body $tokBody -TimeoutSec 5
    $existingSvc = [string]$minted.token
}
Upsert-EnvFile $ApiEnv @{
    "MEMORY_BRIDGE_BACKEND" = "http"
    "TM_BASE_URL"           = "http://localhost:$MemoryPort"
    "TM_SERVICE_TOKEN"      = $existingSvc
    "TM_ADMIN_TOKEN"        = $memAdminToken
}

# 4. Start apps/api on :8000 (idempotent)
Write-Host "[4/6] Ensuring apps/api on :$ApiPort..."
if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/health")) {
    if (-not (Test-Path $ApiPy)) { throw "apps/api virtualenv missing at $ApiPy" }
    $apiOut = Join-Path $LogsDir "api.out.log"
    $apiErr = Join-Path $LogsDir "api.err.log"
    $proc = Start-Process -FilePath $ApiPy `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$ApiPort") `
        -WorkingDirectory $ApiDir -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr `
        -WindowStyle Hidden -PassThru
    $pids["apps_api"] = $proc.Id
    $apiDeadline = (Get-Date).AddSeconds(45)
    while (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/health") -and (Get-Date) -lt $apiDeadline) {
        Start-Sleep -Seconds 1
    }
    if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/health")) {
        throw "apps/api failed to respond on :$ApiPort/api/health (check $apiErr)"
    }
}

# 5. Start Website (Expo web on fixed port 8082) + iPhone Expo Go LAN (:8081)
Write-Host "[5/6] Ensuring Website (:$WebPort) & Expo Go LAN (:$ExpoPort)..."
if (-not (Test-HttpOk "http://127.0.0.1:$WebPort/")) {
    if ($Rebuild -or -not (Test-Path (Join-Path $WebOutDir "index.html"))) {
        New-Item -ItemType Directory -Path $WebOutDir -Force | Out-Null
        Push-Location $MobileDir
        try {
            $env:EXPO_PUBLIC_API_URL = "http://localhost:$ApiPort"
            & npx.cmd expo export --platform web --output-dir $WebOutDir | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "expo export --platform web failed" }
        } finally {
            Pop-Location
        }
    }
    $webServerJs = @"
const http = require('http');
const fs = require('fs');
const path = require('path');
const root = process.env.WEB_ROOT;
const port = Number(process.env.WEB_PORT || 8082);
const mime = {'.html':'text/html; charset=utf-8','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.ico':'image/x-icon','.ttf':'font/ttf'};
http.createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  let file = path.join(root, urlPath === '/' ? 'index.html' : urlPath);
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    const htmlCandidate = file + '.html';
    file = fs.existsSync(htmlCandidate) ? htmlCandidate : path.join(root, 'index.html');
  }
  const ext = path.extname(file).toLowerCase();
  res.writeHead(200, {'Content-Type': mime[ext] || 'application/octet-stream', 'Cache-Control': 'no-cache'});
  fs.createReadStream(file).pipe(res);
}).listen(port, '127.0.0.1');
"@
    $webServerPath = Join-Path $LogsDir "serve-web.cjs"
    [System.IO.File]::WriteAllText($webServerPath, $webServerJs, (New-Object System.Text.UTF8Encoding($false)))
    $psiWeb = Start-Process -FilePath "cmd.exe" `
        -ArgumentList @("/c", "set WEB_ROOT=$WebOutDir&& set WEB_PORT=$WebPort&& node `"$webServerPath`"") `
        -WorkingDirectory $MobileDir `
        -RedirectStandardOutput (Join-Path $LogsDir "web.out.log") `
        -RedirectStandardError (Join-Path $LogsDir "web.err.log") `
        -WindowStyle Hidden -PassThru
    $pids["expo_web"] = $psiWeb.Id
    $webDeadline = (Get-Date).AddSeconds(20)
    while (-not (Test-HttpOk "http://127.0.0.1:$WebPort/") -and (Get-Date) -lt $webDeadline) {
        Start-Sleep -Milliseconds 500
    }
}

if (-not (Test-PortOpen $ExpoPort)) {
    $expoOut = Join-Path $LogsDir "expo-lan.out.log"
    $expoErr = Join-Path $LogsDir "expo-lan.err.log"
    $cmdArgs = "/c set EXPO_PUBLIC_API_URL=http://${lanIp}:$ApiPort&& npx.cmd expo start --host lan --port $ExpoPort"
    $expoProc = Start-Process -FilePath "cmd.exe" -ArgumentList @($cmdArgs) `
        -WorkingDirectory $MobileDir -RedirectStandardOutput $expoOut -RedirectStandardError $expoErr `
        -WindowStyle Hidden -PassThru
    $pids["expo_lan"] = $expoProc.Id
    $expoDeadline = (Get-Date).AddSeconds(35)
    while (-not (Test-PortOpen $ExpoPort) -and (Get-Date) -lt $expoDeadline) {
        Start-Sleep -Seconds 1
    }
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

# Firewall check (never mutate silently without -AddFirewall)
$portsNeeded = @($ApiPort, $ExpoPort, $WebPort)
$missingFw = @()
foreach ($p in $portsNeeded) {
    $ruleExists = Get-NetFirewallRule -Direction Inbound -Enabled True -ErrorAction SilentlyContinue |
        Get-NetFirewallPortFilter -ErrorAction SilentlyContinue |
        Where-Object { $_.Protocol -eq "TCP" -and $_.LocalPort -eq "$p" }
    if (-not $ruleExists) { $missingFw += $p }
}
if ($missingFw.Count -gt 0 -and $AddFirewall) {
    $confirm = Read-Host "Add Windows Firewall inbound TCP allow rules for ports $($missingFw -join ', ')? [y/N]"
    if ($confirm -match '^[Yy]') {
        foreach ($p in $missingFw) {
            netsh advfirewall firewall add rule name="Dubai-io Dev TCP $p" dir=in action=allow protocol=TCP localport=$p | Out-Null
        }
    }
}

Write-Host ""
Write-Host "Website URL  : http://localhost:$WebPort"
Write-Host "API URL      : http://localhost:$ApiPort  (LAN: http://${lanIp}:$ApiPort)"
Write-Host "Memory API   : http://localhost:$MemoryPort"
Write-Host "iPhone Expo  : exp://${lanIp}:$ExpoPort  (scan QR in Expo Go or run npx expo start in apps/mobile)"
if ($missingFw.Count -gt 0) {
    Write-Host "Firewall hint: run elevated if phone cannot connect:"
    foreach ($p in $missingFw) {
        Write-Host "  netsh advfirewall firewall add rule name=`"Dubai-io Dev TCP $p`" dir=in action=allow protocol=TCP localport=$p"
    }
}
Write-Host "=== Done. Run scripts\dev\health.ps1 to verify. ==="

<#
.SYNOPSIS
  Start Messenger API (:8070) and Vite web app (:5173) bound for LAN access,
  configure MESSENGER_ALLOWED_ORIGINS for WebSocket origin verification,
  check Windows Firewall TCP 5173 / 8070, and print Expo Go + Electron commands.
#>
[CmdletBinding()]
param(
  [string]$LanIp = "",
  [switch]$CheckOnly,
  [switch]$ConfigureFirewall,
  [switch]$LaunchDesktop,
  [switch]$LaunchExpo
)

$ErrorActionPreference = "Stop"

function Resolve-LanIpv4 {
  try {
    $candidates = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
      Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.AddressState -eq "Preferred" -and
        $_.InterfaceAlias -notmatch "Loopback|vEthernet|WSL|Hyper-V|Docker|VMware|VirtualBox"
      } |
      Sort-Object -Property InterfaceMetric
    if ($candidates -and $candidates.Count -gt 0) {
      return $candidates[0].IPAddress
    }
  } catch {
    # Fallback below when Get-NetIPAddress is unavailable.
  }

  $fallback = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
    Where-Object {
      $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
      $_.IPAddressToString -notlike "127.*" -and
      $_.IPAddressToString -notlike "169.254.*"
    } |
    Select-Object -First 1
  if ($fallback) {
    return $fallback.IPAddressToString
  }
  return "127.0.0.1"
}

function Test-IsAdministrator {
  try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  } catch {
    return $false
  }
}

function Test-TcpPortFirewallRule {
  param([int]$Port)
  try {
    $filters = Get-NetFirewallPortFilter -Protocol TCP -ErrorAction Stop |
      Where-Object { $_.LocalPort -eq "$Port" }
    foreach ($f in $filters) {
      $rule = Get-NetFirewallRule -AssociatedNetFirewallPortFilter $f -ErrorAction SilentlyContinue |
        Where-Object { $_.Direction -eq "Inbound" -and $_.Action -eq "Allow" -and $_.Enabled -eq "True" }
      if ($rule) { return $true }
    }
    return $false
  } catch {
    return $null
  }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$messengerRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent $messengerRoot)
$apiRoot = Join-Path $repoRoot "apps\api"
$mobileRoot = Join-Path $messengerRoot "mobile"
$desktopRoot = Join-Path $messengerRoot "desktop"

if (-not $LanIp) {
  $LanIp = Resolve-LanIpv4
}

$originList = [System.Collections.Generic.List[string]]::new()
foreach ($origin in @(
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://${LanIp}:5173",
  "http://localhost:4173",
  "http://127.0.0.1:4173",
  "http://${LanIp}:4173"
)) {
  if (-not $originList.Contains($origin)) {
    $originList.Add($origin)
  }
}

if ($env:MESSENGER_TUNNEL_URL) {
  $tunnelOrigin = $env:MESSENGER_TUNNEL_URL.Trim().TrimEnd("/")
  if ($tunnelOrigin -and -not $originList.Contains($tunnelOrigin)) {
    $originList.Add($tunnelOrigin)
  }
}

$env:MESSENGER_ALLOWED_ORIGINS = ($originList -join ",")
$env:MESSENGER_API_URL = "http://127.0.0.1:8070"

Write-Host "=== Messenger Shells Environment ===" -ForegroundColor Cyan
Write-Host "LAN IPv4                : $LanIp"
Write-Host "MESSENGER_API_URL       : $env:MESSENGER_API_URL"
Write-Host "MESSENGER_ALLOWED_ORIGINS: $env:MESSENGER_ALLOWED_ORIGINS"
Write-Host ""

$isAdmin = Test-IsAdministrator
foreach ($port in @(5173, 8070)) {
  $hasRule = Test-TcpPortFirewallRule -Port $port
  if ($hasRule -eq $true) {
    Write-Host "[Firewall] TCP $port inbound Allow rule detected." -ForegroundColor Green
  } else {
    $ruleName = "Messenger Dev TCP $port"
    $netshCmd = "netsh advfirewall firewall add rule name=`"$ruleName`" dir=in action=allow protocol=TCP localport=$port"
    if ($ConfigureFirewall -and $isAdmin) {
      Write-Host "[Firewall] Adding inbound Allow rule for TCP $port..." -ForegroundColor Yellow
      Invoke-Expression $netshCmd | Out-Null
    } else {
      Write-Host "[Firewall] Inbound TCP $port rule not confirmed (Admin=$isAdmin). To allow LAN iPhone access, run in an elevated PowerShell:" -ForegroundColor Yellow
      Write-Host "  $netshCmd"
    }
  }
}

Write-Host ""
Write-Host "=== Mobile (iPhone Expo Go) ===" -ForegroundColor Cyan
Write-Host "  cd `"$mobileRoot`""
Write-Host "  `$env:EXPO_PUBLIC_MESSENGER_URL = `"http://${LanIp}:5173`""
Write-Host "  npx expo start"
Write-Host ""
Write-Host "=== Desktop (Electron) ===" -ForegroundColor Cyan
Write-Host "  cd `"$desktopRoot`""
Write-Host "  `$env:MESSENGER_URL = `"http://localhost:5173`""
Write-Host "  npm start"
Write-Host ""

if ($CheckOnly) {
  Write-Host "[CheckOnly] Preflight complete; no background servers started." -ForegroundColor Green
  exit 0
}

$venvPython = Join-Path $apiRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Starting Messenger API on 0.0.0.0:8070..." -ForegroundColor Cyan
$apiProc = Start-Process -FilePath $pythonExe `
  -ArgumentList @("-m", "uvicorn", "app.messenger.server:app", "--host", "0.0.0.0", "--port", "8070") `
  -WorkingDirectory $apiRoot `
  -PassThru

Write-Host "Starting Messenger Vite dev server on 0.0.0.0:5173..." -ForegroundColor Cyan
$viteProc = Start-Process -FilePath "npx.cmd" `
  -ArgumentList @("vite", "--host", "0.0.0.0", "--port", "5173") `
  -WorkingDirectory $messengerRoot `
  -PassThru

if ($LaunchDesktop) {
  Write-Host "Launching Messenger Electron desktop shell..." -ForegroundColor Cyan
  $env:MESSENGER_URL = "http://localhost:5173"
  Start-Process -FilePath "npm.cmd" `
    -ArgumentList @("start") `
    -WorkingDirectory $desktopRoot | Out-Null
}

if ($LaunchExpo) {
  Write-Host "Launching Expo Go dev server (QR code)..." -ForegroundColor Cyan
  $env:EXPO_PUBLIC_MESSENGER_URL = "http://${LanIp}:5173"
  Start-Process -FilePath "npx.cmd" `
    -ArgumentList @("expo", "start") `
    -WorkingDirectory $mobileRoot | Out-Null
}

Write-Host ""
Write-Host "API PID: $($apiProc.Id) | Vite PID: $($viteProc.Id)" -ForegroundColor Green
Write-Host "Press Ctrl+C or stop those PIDs when done."

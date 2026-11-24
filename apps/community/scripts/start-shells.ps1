<#
.SYNOPSIS
  Starts the Dubai-io Community web server for LAN access, ensures Windows Firewall TCP 3060,
  optionally launches the Electron desktop shell, and prints/starts the Expo Go QR shell.

.PARAMETER CheckOnly
  Prints the detected LAN IPv4, firewall status, Expo Go URLs, and launch commands without starting processes.

.PARAMETER NoDesktop
  Skips launching the Electron desktop shell.

.PARAMETER NoExpo
  Skips starting the Expo CLI dev server in the foreground.

.PARAMETER Port
  Community web server port (default: 3060).
#>
[CmdletBinding()]
param(
  [switch]$CheckOnly,
  [switch]$NoDesktop,
  [switch]$NoExpo,
  [int]$Port = 3060
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$CommunityRoot = Split-Path -Parent $PSScriptRoot
$MobileDir = Join-Path $CommunityRoot "mobile"
$DesktopDir = Join-Path $CommunityRoot "desktop"
$PortableExe = Join-Path $DesktopDir "dist\Dubai-io-Community-0.1.0-win-x64.exe"
$FirewallRuleName = "Dubai-io Community Dev $Port"
$NetshAddCommand = "netsh advfirewall firewall add rule name=`"$FirewallRuleName`" dir=in action=allow protocol=TCP localport=$Port"

function Get-PrimaryLanIPv4 {
  $candidates = @()
  try {
    $routes = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue |
      Sort-Object -Property RouteMetric, InterfaceMetric
    foreach ($route in $routes) {
      $ips = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue |
        Where-Object {
          $_.IPAddress -notlike "127.*" -and
          $_.IPAddress -notlike "169.254.*" -and
          $_.InterfaceAlias -notmatch "vEthernet|WSL|Hyper-V|VMware|VirtualBox|Loopback"
        }
      foreach ($ip in $ips) {
        $candidates += $ip.IPAddress
      }
    }
  } catch {
    # Fallback below for systems without NetTCPIP cmdlets.
  }

  if ($candidates.Count -eq 0) {
    $fallback = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
      Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.AddressState -eq "Preferred" -and
        $_.InterfaceAlias -notmatch "vEthernet|WSL|Hyper-V|VMware|VirtualBox|Loopback"
      } |
      Select-Object -First 1 -ExpandProperty IPAddress
    if ($fallback) {
      return $fallback
    }
  } else {
    return $candidates[0]
  }

  return "127.0.0.1"
}

function Test-IsAdministrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-FirewallPortOpen {
  param([int]$LocalPort)
  try {
    $rules = Get-NetFirewallRule -Direction Inbound -Enabled True -Action Allow -ErrorAction SilentlyContinue
    foreach ($rule in $rules) {
      $portFilter = $rule | Get-NetFirewallPortFilter -ErrorAction SilentlyContinue
      if ($portFilter -and $portFilter.Protocol -eq "TCP" -and ($portFilter.LocalPort -contains "$LocalPort" -or $portFilter.LocalPort -eq "$LocalPort")) {
        return $true
      }
    }
  } catch {
    # Ignore query errors on restricted shells.
  }
  return $false
}

function Ensure-FirewallRule {
  param([int]$LocalPort)
  if (Test-FirewallPortOpen -LocalPort $LocalPort) {
    Write-Host "[OK] Windows Firewall inbound TCP $LocalPort is allowed." -ForegroundColor Green
    return
  }

  if ($CheckOnly) {
    Write-Host "[WARN] No enabled inbound TCP $LocalPort firewall rule detected." -ForegroundColor Yellow
    Write-Host "       Run in an elevated PowerShell/CMD if your iPhone cannot connect:" -ForegroundColor Yellow
    Write-Host "       $NetshAddCommand" -ForegroundColor Cyan
    return
  }

  if (Test-IsAdministrator) {
    Write-Host "[INFO] Adding Windows Firewall inbound rule for TCP $LocalPort..." -ForegroundColor Cyan
    & netsh advfirewall firewall add rule name="$FirewallRuleName" dir=in action=allow protocol=TCP localport=$LocalPort | Out-Null
    Write-Host "[OK] Added firewall rule '$FirewallRuleName'." -ForegroundColor Green
  } else {
    Write-Host "[WARN] Not running as Administrator; cannot create firewall rule automatically." -ForegroundColor Yellow
    Write-Host "       If Expo Go on iPhone times out, run this once as Administrator:" -ForegroundColor Yellow
    Write-Host "       $NetshAddCommand" -ForegroundColor Cyan
  }
}

function Test-PortListening {
  param([int]$LocalPort)
  try {
    $conn = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
  } catch {
    return $false
  }
}

$LanIp = Get-PrimaryLanIPv4
$LanCommunityUrl = "http://${LanIp}:${Port}"
$LocalCommunityUrl = "http://localhost:${Port}"
$ExpoGoUrl = "exp://${LanIp}:8081"

Write-Host ""
Write-Host "=== Dubai-io Community Shells ===" -ForegroundColor Cyan
Write-Host "Detected LAN IPv4   : $LanIp"
Write-Host "Community LAN URL   : $LanCommunityUrl"
Write-Host "Web dev command     : npm run dev -- -H 0.0.0.0 -p $Port  (in $CommunityRoot)"
Write-Host "Expo Go URL         : $ExpoGoUrl"
Write-Host "Expo env override   : EXPO_PUBLIC_COMMUNITY_URL=$LanCommunityUrl"
Write-Host "Desktop start cmd   : cd `"$DesktopDir`"; npm start"
if (Test-Path $PortableExe) {
  Write-Host "Desktop portable exe: $PortableExe"
}
Write-Host ""

Ensure-FirewallRule -LocalPort $Port

if ($CheckOnly) {
  Write-Host "[CHECK] Dry check complete. Re-run without -CheckOnly to launch." -ForegroundColor Green
  exit 0
}

if (-not (Test-PortListening -LocalPort $Port)) {
  Write-Host "[INFO] Starting Community web server on 0.0.0.0:$Port..." -ForegroundColor Cyan
  Start-Process powershell -WorkingDirectory $CommunityRoot -ArgumentList @(
    "-NoExit",
    "-Command",
    "npm run dev -- -H 0.0.0.0 -p $Port"
  ) | Out-Null

  $deadline = (Get-Date).AddSeconds(25)
  while ((Get-Date) -lt $deadline) {
    if (Test-PortListening -LocalPort $Port) {
      break
    }
    Start-Sleep -Milliseconds 500
  }
} else {
  Write-Host "[OK] Community web server is already listening on port $Port." -ForegroundColor Green
}

if (-not $NoDesktop) {
  if (Test-Path $PortableExe) {
    Write-Host "[INFO] Launching portable desktop shell ($PortableExe)..." -ForegroundColor Cyan
    Start-Process $PortableExe | Out-Null
  } else {
    Write-Host "[INFO] Launching Electron desktop shell..." -ForegroundColor Cyan
    Start-Process powershell -WorkingDirectory $DesktopDir -ArgumentList @(
      "-NoExit",
      "-Command",
      "`$env:COMMUNITY_URL='$LocalCommunityUrl'; npm start"
    ) | Out-Null
  }
}

if (-not $NoExpo) {
  Write-Host "[INFO] Starting Expo Go server (scan the QR code in Expo Go on your iPhone)..." -ForegroundColor Cyan
  Push-Location $MobileDir
  try {
    $env:EXPO_PUBLIC_COMMUNITY_URL = $LanCommunityUrl
    npx expo start
  } finally {
    Pop-Location
  }
}

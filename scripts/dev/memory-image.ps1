# Shared by start-all.ps1 and health.ps1 (dot-sourced). Detects a stale memory Docker image: the hash of everything the
# Dockerfile copies (pyproject.toml, README.md, src/, Dockerfile) is recorded at build time next to the image id.
function Get-MemorySourceHash([string]$MemDir) {
    $files = @()
    foreach ($f in @("Dockerfile", "pyproject.toml", "README.md")) {
        $p = Join-Path $MemDir $f
        if (Test-Path $p) { $files += Get-Item $p }
    }
    $files += Get-ChildItem (Join-Path $MemDir "src") -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '__pycache__|\.pyc$|\.egg-info' }
    $sb = New-Object System.Text.StringBuilder
    foreach ($f in ($files | Sort-Object FullName)) {
        $rel = $f.FullName.Substring($MemDir.Length)
        [void]$sb.Append($rel).Append(':').Append((Get-FileHash $f.FullName -Algorithm SHA256).Hash).Append("`n")
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($sb.ToString())))).Replace('-', '') } finally { $sha.Dispose() }
}
function Get-MemoryApiContainerImageId([string]$MemCompose) {
    $cid = (& docker compose -f $MemCompose ps -q api 2>$null | Select-Object -First 1)
    if (-not $cid) { return $null }
    return (& docker inspect $cid --format '{{.Image}}' 2>$null | Select-Object -First 1)
}

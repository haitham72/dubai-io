param(
    [string]$Commit = "HEAD",
    [string]$MemWorktree = "",
    [string]$Py = "",
    [string]$OutDir = "",
    [switch]$SkipS2,
    [string]$Only = ""
)

$ErrorActionPreference = "Stop"
$AccDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppMemDir = Split-Path -Parent $AccDir
$RepoRoot = Split-Path -Parent (Split-Path -Parent $AppMemDir)

if (-not $MemWorktree) {
    $MemWorktree = (git -C $AccDir rev-parse --show-toplevel).Trim()
}
if (-not $Py) {
    $defaultPy = Join-Path $AppMemDir ".venv\Scripts\python.exe"
    if (Test-Path $defaultPy) {
        $Py = $defaultPy
    } else {
        $siblingPy = Join-Path (Split-Path -Parent $RepoRoot) "contest-memory\apps\memory\.venv\Scripts\python.exe"
        if (Test-Path $siblingPy) {
            $Py = $siblingPy
        } else {
            $Py = "python"
        }
    }
}

$TargetSha = (git -C $MemWorktree rev-parse --short $Commit).Trim()
if (-not $TargetSha) { throw "Cannot resolve commit $Commit" }
$HeadSha = (git -C $MemWorktree rev-parse --short HEAD).Trim()

$Timestamp = Get-Date -Format "yyyyMMdd-HHmm"
if (-not $OutDir) {
    $OutDir = Join-Path $AccDir "results\$Timestamp"
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$TempSrcRoot = $null
$SrcPath = Join-Path $MemWorktree "apps\memory\src"
if ($TargetSha -ne $HeadSha) {
    $TempSrcRoot = Join-Path $env:TEMP "acc_src_$TargetSha`_$([guid]::NewGuid().ToString('N').Substring(0,8))"
    New-Item -ItemType Directory -Path $TempSrcRoot -Force | Out-Null
    $tar = Join-Path $TempSrcRoot "src.tar"
    git -C $MemWorktree archive --format=tar --output=$tar $TargetSha apps/memory/src
    tar -xf $tar -C $TempSrcRoot
    $SrcPath = Join-Path $TempSrcRoot "apps\memory\src"
}

$env:PYTHONPATH = "$SrcPath;$AccDir"
$env:PYTHONUNBUFFERED = "1"

$onlySet = @()
if ($Only) {
    $onlySet = $Only.Split(",") | ForEach-Object { $_.Trim().ToUpperInvariant() } | Where-Object { $_ }
}

try {
    Write-Host "=== Acceptance Harness: commit=$TargetSha worktree=$MemWorktree out=$OutDir ==="
    & $Py "$AccDir\cleanup_t1_schemas.py"

    $suites = @(
        @{ Name = "S7"; Script = "s7_traps.py" },
        @{ Name = "S2"; Script = "s2_extract_cost.py" },
        @{ Name = "S1"; Script = "s1_retrieval.py" },
        @{ Name = "S3"; Script = "s3_forget.py" },
        @{ Name = "S4"; Script = "s4_bridge_pg.py" },
        @{ Name = "S5"; Script = "s5_rule9.py" },
        @{ Name = "S6"; Script = "s6_graph.py" },
        @{ Name = "S8"; Script = "s8_places_topics.py" },
        @{ Name = "S9"; Script = "s9_why_story.py" },
        @{ Name = "S10"; Script = "s10_hybrid_ablation.py" }
    )

    foreach ($s in $suites) {
        if ($onlySet.Count -gt 0 -and ($onlySet -notcontains $s.Name.ToUpperInvariant())) { continue }
        if ($SkipS2 -and ($s.Name -eq "S2")) { continue }
        Write-Host "`n--- Running $($s.Name) ($($s.Script)) ---"
        & $Py "$AccDir\$($s.Script)" $OutDir
        if ($LASTEXITCODE -ne 0) {
            throw "Suite $($s.Name) crashed with exit code $LASTEXITCODE"
        }
    }

    Write-Host "`n--- Generating REPORT.md ---"
    & $Py "$AccDir\generate_report.py" $OutDir $TargetSha

    # Verify zero leftover acc_* / t2b_tn_* / smoke_* schemas
    @'
import os, psycopg
dsn = os.environ.get("TM_TEST_DATABASE_URL", "postgresql://tm:tm@localhost:5442/tm")
conn = psycopg.connect(dsn)
bad = [r[0] for r in conn.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'acc_%' OR schema_name LIKE 't2b_tn_%' OR schema_name LIKE 'smoke_%'").fetchall()]
conn.close()
print("LEFTOVER_SCHEMAS:", bad)
raise SystemExit(1 if bad else 0)
'@ | & $Py -
}
finally {
    if ($TempSrcRoot -and (Test-Path $TempSrcRoot)) {
        Remove-Item -Recurse -Force $TempSrcRoot
    }
}

param([switch]$UseCachedImages)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if ($UseCachedImages) {
    # CLI-supported version files; pin exact image tags, never relabel old images as new.
    $imageVersions = [ordered]@{
        'postgres-version' = @('supabase/postgres','17.11.0.002')
        'rest-version' = @('supabase/postgrest','v16.4')
        'gotrue-version' = @('supabase/gotrue','v2.197.0')
        'storage-version' = @('supabase/storage-api','v1.79.28')
        'edge-runtime-version' = @('supabase/edge-runtime','v1.77.1')
        'realtime-version' = @('supabase/realtime','v2.140.3')
        'studio-version' = @('supabase/studio','2026.09.28-sha-5e59b60')
        'pgmeta-version' = @('supabase/postgres-meta','v0.99.0')
    }
    foreach ($entry in $imageVersions.GetEnumerator()) {
        $imageName = 'public.ecr.aws/' + $entry.Value[0] + ':' + $entry.Value[1]
        docker image inspect $imageName --format '{{.Id}}' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Required cached image is missing: $imageName" }
    }
    New-Item -ItemType Directory -Force -Path 'supabase/.temp' | Out-Null
    foreach ($entry in $imageVersions.GetEnumerator()) {
        [IO.File]::WriteAllText((Join-Path $projectRoot ('supabase/.temp/' + $entry.Key)), $entry.Value[1])
    }
}
npx.cmd --yes supabase@2.121.0 start
exit $LASTEXITCODE

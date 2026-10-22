<#
.SYNOPSIS
  Write <run>\gameplay.mp4 (the dataset's Gameplay/ file) for runs recorded before record.ps1 made it, or redo it.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File gameplay-mp4.ps1 tower-defense -Commit ff5f1ee
  powershell -ExecutionPolicy Bypass -File gameplay-mp4.ps1 <game> -RunId <run id> -Force

  Valid = validation.json status ok or warn and no INVALID file (ok_video_only runs have no aligned audio: skipped).
  -Commit takes one or more build-commit prefixes (metadata.json build.commit). Video is stream-copied from video.mkv,
  system_audio.mka is encoded to AAC and aligned with the bundle's own clock offsets (see Export-GameplayMp4 in
  common.ps1). Adds `gameplay_mp4` to metadata.json and the file to manifest.json. CPU only, below-normal priority.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [string[]]$Commit,
    [string[]]$RunId,
    [switch]$Force
)
. (Join-Path $PSScriptRoot 'common.ps1')
Set-BelowNormalPriority
$root = Join-Path $RecordingsRoot $Game
$done = 0; $failed = 0; $skipped = 0
foreach ($d in @(Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne '_stills' -and (-not $RunId -or $_.Name -in $RunId) } | Sort-Object Name)) {
    $v = Read-JsonFile (Join-Path $d.FullName 'validation.json')
    $m = Read-JsonFile (Join-Path $d.FullName 'metadata.json')
    if (-not $v -or -not $m -or $v.status -notin @('ok', 'warn') -or (Test-Path (Join-Path $d.FullName 'INVALID'))) { continue }
    if ($Commit -and -not @($Commit | Where-Object { "$($m.build.commit)".StartsWith($_) }).Count) { continue }
    if (-not $Force -and (Test-Path (Join-Path $d.FullName 'gameplay.mp4'))) { $skipped++; continue }
    $sa = $m.system_audio
    $audioStart = if ($sa -and $sa.aligned -eq $true) { $sa.start_offset_ns } else { $null }
    $r = Export-GameplayMp4 $d.FullName $m.video_start_offset_ns $audioStart
    if ($r.error) { Write-Step "$($d.Name): WARNING gameplay.mp4 not written: $($r.error)"; $failed++; continue }
    $m | Add-Member -Force NoteProperty gameplay_mp4 $r
    Write-JsonFile (Join-Path $d.FullName 'metadata.json') $m
    $manPath = Join-Path $d.FullName 'manifest.json'
    $man = Read-JsonFile $manPath
    if ($man) {
        $files = [ordered]@{}
        foreach ($p in $man.files.PSObject.Properties) { $files[$p.Name] = $p.Value }
        foreach ($rel in 'metadata.json', 'gameplay.mp4') {
            $f = Get-Item (Join-Path $d.FullName $rel)
            $files[$rel] = [ordered]@{ sha256 = (Get-FileSha256 $f.FullName); bytes = $f.Length }
        }
        $man.files = $files
        Write-JsonFile $manPath $man
    }
    Write-Step ("{0}: gameplay.mp4 {1:N1} s, {2:N1} MB, audio offset {3} s" -f $d.Name, $r.duration_s, ($r.bytes / 1MB), $r.audio_offset_s)
    $done++
}
Write-Step "$Game : $done written, $failed failed, $skipped already had one"
if ($failed) { exit 1 }

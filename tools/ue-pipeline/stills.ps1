<#
.SYNOPSIS
  Extract README stills from recorded runs that record.ps1 recorded before it did this itself (or to redo them).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File stills.ps1 tower-defense                       # every valid run without stills
  powershell -ExecutionPolicy Bypass -File stills.ps1 tower-defense -RunId tower-defense_S1_20261011-185719_s300082845 -Force

  Valid = validation.json status ok, warn or ok_video_only and no INVALID file. Writes <run>\stills\NN.jpg and
  recordings\<game>\_stills\<run_id>_NN.jpg, adds `stills` to metadata.json and the files to manifest.json.
  CPU decode only (no GPU slot needed).
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [string[]]$RunId,
    [int]$Count = 8,
    [switch]$Force
)
. (Join-Path $PSScriptRoot 'common.ps1')
$root = Join-Path $RecordingsRoot $Game
$dirs = @(Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '_*' -and (-not $RunId -or $_.Name -in $RunId) })
foreach ($d in $dirs) {
    $v = Read-JsonFile (Join-Path $d.FullName 'validation.json')
    if (-not $v -or $v.status -notin @('ok', 'warn', 'ok_video_only') -or (Test-Path (Join-Path $d.FullName 'INVALID'))) { continue }
    if (-not $Force -and (Test-Path (Join-Path $d.FullName 'stills\01.jpg'))) { continue }
    $s = Export-RunStills $d.FullName $d.Name (Join-Path $root '_stills') $Count
    if ($s.error) { Write-Step "$($d.Name): WARNING stills not extracted: $($s.error)"; continue }
    $mPath = Join-Path $d.FullName 'metadata.json'
    $m = Read-JsonFile $mPath
    if ($m) { $m | Add-Member -Force NoteProperty stills $s; Write-JsonFile $mPath $m }
    # Refresh the manifest entries for metadata.json and the stills (other entries untouched).
    $manPath = Join-Path $d.FullName 'manifest.json'
    $man = Read-JsonFile $manPath
    if ($man) {
        $files = [ordered]@{}
        foreach ($p in $man.files.PSObject.Properties) { if ($p.Name -notlike 'stills/*') { $files[$p.Name] = $p.Value } }
        foreach ($rel in @('metadata.json') + @($s.files | ForEach-Object { $_.file })) {
            $f = Get-Item (Join-Path $d.FullName $rel.Replace('/', '\'))
            $files[$rel] = [ordered]@{ sha256 = (Get-FileSha256 $f.FullName); bytes = $f.Length }
        }
        $man.files = $files
        Write-JsonFile $manPath $man
    }
    Write-Step "$($d.Name): $($s.count) stills"
}

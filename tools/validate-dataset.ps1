<#
.SYNOPSIS
  Check a dataset delivery against dataset layout v1.1 (docs/dataset-layout-v1.json, the machine-readable copy of the
  spec in docs/game-deliverable.md): a delivery folder, a game repo's Dataset\ folder, or a <game>.zip.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\validate-dataset.ps1 %GF_ROOT%\games\<game>\Dataset.pending.zip
  powershell -ExecutionPolicy Bypass -File tools\validate-dataset.ps1 %GF_ROOT%\games\<game>\Dataset
  ... -NoHash      # skip the sha256 check of every file (sizes are still checked)

  Prints one verdict line, then the findings ("  x" = error, "  !" = note):
    VALID    everything in the spec is present and correct (manifest status "complete")
    PENDING  correct, but ReplayScripts/ is not there yet (manifest status "pending")
    INVALID  anything else
  Exit code 0 for VALID, 1 for PENDING, 2 for INVALID. The content scan (names, account name, e-mail addresses) is
  package-game.ps1 -Rescan <folder>; run both before a review.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Path,
    [switch]$RepoDataset,          # the folder is a game repo's Dataset\ (default: when the folder is named Dataset)
    [switch]$NoHash,
    [string]$SpecFile              # default: ..\docs\dataset-layout-v1.json next to this script
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
if (-not $SpecFile) { $SpecFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\docs\dataset-layout-v1.json' }
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$L = Get-Content $SpecFile -Raw -Encoding UTF8 | ConvertFrom-Json
$errors = New-Object System.Collections.ArrayList; $notes = New-Object System.Collections.ArrayList
function E([string]$m) { [void]$errors.Add($m) }
function N([string]$m) { [void]$notes.Add($m) }
function Get-Prop($o, [string]$n) { if ($null -eq $o) { return $null }; $p = $o.PSObject.Properties[$n]; if ($p) { $p.Value } else { $null } }

# ---- a uniform view of the delivery: relative paths (with sizes), file reader, hasher ----------------------------------
$full = (Resolve-Path $Path).Path
$isZip = $full -match '\.zip$'
$zip = $null; $files = @{}; $entryOf = @{}   # rel path -> bytes / zip entry
if ($isZip) {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($full)
    $tops = @($zip.Entries | ForEach-Object { ($_.FullName -split '/')[0] } | Sort-Object -Unique)
    if ($tops.Count -ne 1) { E "the zip must have one top folder, found: $($tops -join ', ')" }
    $top = $tops[0]
    foreach ($e in $zip.Entries) { if ($e.FullName.EndsWith('/')) { continue }; $rel = $e.FullName.Substring($top.Length + 1); $files[$rel] = $e.Length; $entryOf[$rel] = $e }
} else {
    $top = Split-Path $full -Leaf
    foreach ($f in Get-ChildItem $full -Recurse -File -Force) { $files[$f.FullName.Substring($full.Length + 1).Replace('\', '/')] = $f.Length }
}
if (-not $PSBoundParameters.ContainsKey('RepoDataset')) { $RepoDataset = (-not $isZip) -and ($top -eq $L.names.repo_folder) }
function Read-Text([string]$rel) {
    if ($isZip) { $s = $entryOf[$rel].Open(); try { (New-Object System.IO.StreamReader($s, [Text.Encoding]::UTF8)).ReadToEnd() } finally { $s.Dispose() } }
    else { [IO.File]::ReadAllText((Join-Path $full $rel), [Text.Encoding]::UTF8) }
}
function Get-Sha([string]$rel) {
    $h = [Security.Cryptography.SHA256]::Create()
    $s = if ($isZip) { $entryOf[$rel].Open() } else { [IO.File]::OpenRead((Join-Path $full $rel)) }
    try { -join ($h.ComputeHash($s) | ForEach-Object { $_.ToString('x2') }) } finally { $s.Dispose(); $h.Dispose() }
}

# ---- manifest ----------------------------------------------------------------------------------------------------------
$man = $null
if (-not $files.ContainsKey('manifest.json')) { E 'manifest.json is missing' }
else {
    try { $man = Read-Text 'manifest.json' | ConvertFrom-Json } catch { E "manifest.json is not valid JSON: $($_.Exception.Message)" }
}
# The spec follows the delivery's own layout version unless -SpecFile names one (v1.1 deliveries stay valid as v1.1).
if (-not $PSBoundParameters.ContainsKey('SpecFile') -and $man -and (Get-Prop $man 'layout') -eq 'dataset-layout/v1.2') {
    $SpecFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..\docs\dataset-layout-v1.2.json'
    $L = Get-Content $SpecFile -Raw -Encoding UTF8 | ConvertFrom-Json
}
$unlisted = Get-Prop (Get-Prop $L 'unlisted_allowed') 'prefix'   # v1.2: History/lfs/objects/ (content-addressed, not in files[])
$game = $null; $status = $null
if ($man) {
    foreach ($k in $L.manifest.required_keys) { if ($null -eq $man.PSObject.Properties[$k]) { E "manifest.json has no '$k'" } }
    if ((Get-Prop $man 'layout') -ne $L.manifest.layout_value) { E "manifest.json layout is '$(Get-Prop $man 'layout')', not '$($L.manifest.layout_value)'" }
    $status = Get-Prop $man 'status'; if ($status -notin $L.manifest.status_values) { E "manifest.json status '$status' is not one of $($L.manifest.status_values -join ', ')" }
    $variant = Get-Prop $man 'variant'; if ($variant -notin $L.manifest.variant_values) { E "manifest.json variant '$variant' is not one of $($L.manifest.variant_values -join ', ')" }
    if ($RepoDataset -and $variant -ne 'repo-dataset') { E "a repo Dataset folder must have variant 'repo-dataset', not '$variant'" }
    if (-not $RepoDataset -and $variant -eq 'repo-dataset') { E 'variant repo-dataset outside a repo Dataset folder' }
    $game = Get-Prop $man 'game'
}
if (-not $game) { $game = $top -replace '_nostore$', '' }

# ---- top level ---------------------------------------------------------------------------------------------------------
$topNames = @($files.Keys | ForEach-Object { ($_ -split '/')[0] } | Sort-Object -Unique)
$known = @{}; foreach ($en in $L.entries) { $known[$en.name] = $en }
$extraOk = if ($RepoDataset) { @($L.repo_dataset_extra_allowed) } else { @() }
foreach ($n in $topNames) { if (-not $known.ContainsKey($n) -and $extraOk -notcontains $n) { E "unexpected top-level entry '$n'" } }
$missingPending = New-Object System.Collections.ArrayList
foreach ($en in $L.entries) {
    $present = if ($en.kind -eq 'file') { $files.ContainsKey($en.name) } else { [bool]($files.Keys | Where-Object { $_.StartsWith("$($en.name)/") } | Select-Object -First 1) }
    if ($RepoDataset -and -not $en.in_repo_dataset) { if ($present) { E "$($en.name) must not be in a repo Dataset folder" }; continue }
    if (-not $present) {
        if ((Get-Prop $en 'pending_allowed') -and $status -eq 'pending') { [void]$missingPending.Add($en.name) }
        else { E "$($en.name)$(if ($en.kind -eq 'dir') { '/' }) is missing" }
    }
}
if ($man) {
    $declared = @(@(Get-Prop $man 'pending') | Where-Object { $_ } | Where-Object { $_ -is [string] } | ForEach-Object { $_.TrimEnd('/') })
    foreach ($m in $missingPending) { if ($declared -notcontains $m) { E "$m is missing but not listed in manifest.json pending" } }
    if ($status -eq 'complete' -and $declared.Count) { E "status complete but pending lists $($declared -join ', ')" }
    if ($status -eq 'complete') {
        # COMPLETE needs a passing creation-replay verification, in the manifest and in ReplayScripts/Verification/report.json
        $rv = Get-Prop $man 'replay_verification'
        if (-not $rv -or -not (Get-Prop $rv 'pass')) { E 'status complete but manifest.json replay_verification is missing or not pass' }
        $vrel = 'ReplayScripts/Verification/report.json'
        if (-not $files.ContainsKey($vrel)) { E "status complete but $vrel is missing" }
        else {
            $vd = (Read-Text $vrel | ConvertFrom-Json).verdict
            if (-not $vd -or -not $vd.pass) { E "status complete but $vrel verdict is not PASS" }
        }
    }
    if ($status -eq 'pending' -and $missingPending.Count -eq 0) { N 'status is pending although every entry is present' }
}

# ---- per-entry rules ---------------------------------------------------------------------------------------------------
foreach ($en in $L.entries) {
    if ($en.kind -ne 'dir' -or ($RepoDataset -and -not $en.in_repo_dataset)) { continue }
    $inside = @($files.Keys | Where-Object { $_.StartsWith("$($en.name)/") })
    if (-not $inside.Count) { continue }
    $pat = Get-Prop $en 'only_files_matching'
    if ($pat) {
        $rx = $pat.Replace('<game>', [regex]::Escape($game))
        foreach ($f in $inside) { $leaf = $f.Substring($en.name.Length + 1); if ($leaf -match '/' -or $leaf -notmatch $rx) { E "$f does not belong in $($en.name)/ (allowed: $pat, no subfolders)" } }
        if (Get-Prop $en 'scenario_numbers') {
            # a subset of the game's scenarios is fine (user decision 2026-10-12); numbers must be 1+ and distinct
            $nums = @($inside | ForEach-Object { if (($_.Substring($en.name.Length + 1)) -match $rx) { [int]$Matches[1] } } | Sort-Object)
            if (@($nums | Where-Object { $_ -lt 1 }).Count -or @($nums | Sort-Object -Unique).Count -ne $nums.Count) { E "$($en.name)/ scenario numbers must be distinct and 1 or more: $($nums -join ', ')" }
        }
    }
    foreach ($m in @(Get-Prop $en 'must_contain')) { if ($m -and -not ($inside | Where-Object { ($_ -split '/')[-1] -like $m })) { E "$($en.name)/ has no $m" } }
    foreach ($m in @(Get-Prop $en 'forbid')) { if ($m) { $bad = @($inside | Where-Object { ($_ -split '/')[-1] -like $m }); if ($bad.Count) { E "$($en.name)/ contains $($bad.Count) $m file(s), e.g. $($bad[0])" } } }
}
if (-not $RepoDataset -and -not ($files.Keys | Where-Object { $_ -match '^UEProject/[^/]+\.uproject$' })) { E 'UEProject/ has no .uproject at its root' }

# ---- manifest scenarios and files --------------------------------------------------------------------------------------
if ($man) {
    $vids = @($files.Keys | Where-Object { $_ -like 'Gameplay/*.mp4' } | Sort-Object)
    $msc = @(Get-Prop $man 'scenarios')
    if ($msc.Count -ne $vids.Count) { E "manifest.json lists $($msc.Count) scenarios, Gameplay/ has $($vids.Count) videos" }
    foreach ($s in $msc) { if (-not $files.ContainsKey($s.file)) { E "manifest.json scenario file $($s.file) is missing" } }
    $listed = @{}; foreach ($f in @(Get-Prop $man 'files')) { $listed[$f.path] = $f }
    foreach ($rel in @($files.Keys)) {
        if ($rel -eq 'manifest.json' -or ($RepoDataset -and $rel -eq '.gitattributes')) { continue }
        if ($unlisted -and $rel.StartsWith($unlisted)) { continue }
        if (-not $listed.ContainsKey($rel)) { E "$rel is not in manifest.json"; continue }
        if ([long]$listed[$rel].bytes -ne [long]$files[$rel]) { E "${rel}: size $($files[$rel]) differs from manifest.json ($($listed[$rel].bytes))" }
    }
    foreach ($rel in @($listed.Keys)) { if (-not $files.ContainsKey($rel)) { E "manifest.json lists $rel, which is not there" } }
    if (-not $NoHash) {
        $bad = 0
        foreach ($rel in @($listed.Keys | Where-Object { $files.ContainsKey($_) })) { if ((Get-Sha $rel) -ne $listed[$rel].sha256) { $bad++; if ($bad -le 5) { E "${rel}: sha256 differs from manifest.json" } } }
        if ($bad -gt 5) { E "... $($bad - 5) more sha256 mismatches" }
    }
    $t = Get-Prop $man 'totals'; if ($t -and [int]$t.files -ne $listed.Count) { E "manifest.json totals.files $($t.files) but $($listed.Count) entries" }
}

# ---- README --------------------------------------------------------------------------------------------------------------
if ($files.ContainsKey('README.md')) {
    $rd = Read-Text 'README.md'
    $heads = @([regex]::Matches($rd, '(?m)^##\s+(.+?)\s*$') | ForEach-Object { $_.Groups[1].Value })
    $want = @($L.readme.sections_in_order); $pos = -1
    foreach ($w in $want) { $i = [array]::IndexOf($heads, $w); if ($i -lt 0) { E "README.md has no '## $w' section" } elseif ($i -lt $pos) { E "README.md section '## $w' is out of order" } else { $pos = $i } }
    $links = @([regex]::Matches($rd, '\]\((Screenshots/[^)\s]+)\)') | ForEach-Object { [uri]::UnescapeDataString($_.Groups[1].Value) } | Sort-Object -Unique)
    foreach ($lk in $links) { if (-not $files.ContainsKey($lk)) { E "README.md links $lk, which is not there" } }   # not $l: PowerShell names ignore case, $l is $L
    if ($L.readme.must_link_every_screenshot) { foreach ($s in @($files.Keys | Where-Object { $_ -like 'Screenshots/*' })) { if ($links -notcontains $s) { E "README.md does not show $s" } } }
    foreach ($v in @($files.Keys | Where-Object { $_ -like 'Gameplay/*.mp4' })) { if ($rd -notmatch [regex]::Escape($v)) { E "README.md does not list $v" } }
    if ($status -eq 'pending' -and $rd -notmatch '(?i)pending') { E 'README.md does not say the delivery is pending' }
}

# ---- gameplay videos (ffprobe) -----------------------------------------------------------------------------------------
$ffprobe = $null
try { . (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'ue-pipeline\common.ps1'); $ffprobe = Find-FFprobe } catch { }   # the pinned ffmpeg of this machine
if (-not $ffprobe) { $ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue | ForEach-Object Source | Select-Object -First 1 }
if (-not $ffprobe) { N 'ffprobe not found: gameplay videos not probed' }
else {
    $tmp = $null
    foreach ($v in @($files.Keys | Where-Object { $_ -like 'Gameplay/*.mp4' } | Sort-Object)) {
        $p = if ($isZip) { if (-not $tmp) { $tmp = Join-Path $env:TEMP "validate-dataset-$PID"; New-Item -ItemType Directory -Force $tmp | Out-Null }
            $x = Join-Path $tmp ($v -split '/')[-1]; [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entryOf[$v], $x, $true); $x } else { Join-Path $full $v }
        $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $j = $null; try { $j = & $ffprobe -v error -show_entries 'stream=codec_type,codec_name,width,height:format=format_name,duration' -of json $p 2>$null | Out-String | ConvertFrom-Json } catch { }
        $ErrorActionPreference = $old
        if (-not $j -or -not (Get-Prop $j 'format')) { E "$v cannot be read as a video"; if ($isZip) { Remove-Item -Force $p }; continue }
        $vs = @($j.streams | Where-Object codec_type -eq 'video'); $as = @($j.streams | Where-Object codec_type -eq 'audio')
        $g = $L.gameplay_video
        if ($j.format.format_name -notmatch 'mp4') { E "$v is not an mp4 ($($j.format.format_name))" }
        if ($vs.Count -ne 1 -or $vs[0].codec_name -ne $g.video_codec -or [int]$vs[0].width -ne $g.width -or [int]$vs[0].height -ne $g.height) { E "$v video is not $($g.video_codec) $($g.width)x$($g.height): $(@($vs | ForEach-Object { "$($_.codec_name) $($_.width)x$($_.height)" }) -join ', ')" }
        if ($g.audio_required -and ($as.Count -lt 1 -or $as[0].codec_name -ne $g.audio_codec)) { E "$v has no $($g.audio_codec) audio" }
        N ("{0}: {1:N1} s, {2} {3}x{4} + {5}" -f $v, [double]$j.format.duration, $vs[0].codec_name, $vs[0].width, $vs[0].height, $(if ($as.Count) { $as[0].codec_name } else { 'no audio' }))
        if ($isZip) { Remove-Item -Force $p }
    }
    if ($tmp) { Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue }
}
if ($zip) { $zip.Dispose() }

# ---- verdict -----------------------------------------------------------------------------------------------------------
$verdict = if ($errors.Count) { 'INVALID' } elseif ($missingPending.Count -or $status -eq 'pending') { 'PENDING' } else { 'VALID' }
Write-Host ("{0}  {1}  ({2}, layout {3}, {4} files{5})" -f $verdict, $full, $(if ($RepoDataset) { 'repo Dataset' } elseif ($isZip) { 'zip' } else { 'folder' }), $L.schema, $files.Count, $(if ($missingPending.Count) { "; pending: $($missingPending -join ', ')" } else { '' }))
foreach ($e in $errors) { Write-Host "  x $e" }
foreach ($n in $notes) { Write-Host "  ! $n" }
exit $(if ($verdict -eq 'VALID') { 0 } elseif ($verdict -eq 'PENDING') { 1 } else { 2 })

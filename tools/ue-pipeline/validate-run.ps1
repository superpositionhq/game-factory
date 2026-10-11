<#
.SYNOPSIS
  Check one AutoPlay RecordDir against docs/autoplay-contract.md (no video needed). For game sessions testing by hand.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File validate-run.ps1 C:\Users\Xiang\Work\games\stealth\Saved\AutoPlay\20261011-120000
#>
param([Parameter(Mandatory = $true, Position = 0)][string]$Dir)

. (Join-Path $PSScriptRoot 'common.ps1')
Add-Type -AssemblyName System.Web.Extensions
$ser = New-Object System.Web.Script.Serialization.JavaScriptSerializer
$ser.MaxJsonLength = 64MB
$problems = New-Object System.Collections.ArrayList
$notes = New-Object System.Collections.ArrayList

function Read-Rows([string]$Name, [string]$KindField) {
    $path = Join-Path $Dir $Name
    $r = @{ rows = 0; bad = 0; backwards = 0; kinds = @{}; first = $null }
    if (-not (Test-Path $path)) { [void]$problems.Add("missing $Name"); return $r }
    $prev = 0
    foreach ($line in [System.IO.File]::ReadLines($path)) {
        if ($line.Trim() -eq '') { continue }
        $r.rows++
        try { $o = $ser.DeserializeObject($line) } catch { $r.bad++; continue }
        if ($null -eq $r.first) { $r.first = $o }
        foreach ($f in 't_ns', 'qpc', 'frame') { if (-not $o.ContainsKey($f)) { [void]$problems.Add("${Name} row $($r.rows) has no $f"); break } }
        if ([long]$o['t_ns'] -lt $prev) { $r.backwards++ }
        $prev = [long]$o['t_ns']
        $k = "$($o[$KindField])"
        if ($r.kinds.ContainsKey($k)) { $r.kinds[$k]++ } else { $r.kinds[$k] = 1 }
    }
    if ($r.bad) { [void]$problems.Add("$Name has $($r.bad) unparseable lines") }
    if ($r.backwards) { [void]$problems.Add("$Name t_ns goes backwards $($r.backwards) times") }
    return $r
}

$inputs = Read-Rows 'inputs.jsonl' 'type'
$telemetry = Read-Rows 'telemetry.jsonl' 'event'
if (-not $inputs.kinds.ContainsKey('inject')) { [void]$problems.Add('inputs.jsonl has no inject rows') }
# v1.3 writes scenario_start/scenario_end, v1/v1.2 level_start/level_end; either is accepted.
foreach ($e in 'run_start', 'scenario_start|level_start', 'scenario_end|level_end', 'run_end') { if (-not @($e -split '\|' | Where-Object { $telemetry.kinds.ContainsKey($_) }).Count) { [void]$problems.Add("telemetry.jsonl has no $e") } }
foreach ($e in 'score', 'state') { if (-not $telemetry.kinds.ContainsKey($e)) { [void]$notes.Add("telemetry has no '$e' events (required for all games)") } }

$outcome = Read-JsonFile (Join-Path $Dir 'outcome.json')
if ($outcome) { $v = if ($outcome.PSObject.Properties.Name -contains 'autoplay_version') { $outcome.autoplay_version } elseif ($outcome.PSObject.Properties.Name -contains 'contract_version') { $outcome.contract_version } else { '?' }; [void]$notes.Add("AutoPlay drop-in version $v (1 = v1, 2 = v1.2, 3 = v1.3, 4 = v1.4)") }
if (-not $outcome) { [void]$problems.Add('missing outcome.json') }
else {
    if ($outcome.result -notin @('win', 'lose', 'timeout', 'abort')) { [void]$problems.Add("outcome.result is '$($outcome.result)'") }
    if ($outcome.go_timed_out) { [void]$notes.Add('go_timed_out is true (expected when testing by hand with -GoTimeout)') }
    if ($outcome.duration_s -gt 0) { [void]$notes.Add(("scenario {5} ({6}) ran {0:N1} s at {1:N1} fps, {2} injected inputs, result {3}, score {4}" -f $outcome.duration_s, ($outcome.frames / $outcome.duration_s), $outcome.inputs_injected, $outcome.result, $outcome.score, $(if ($outcome.PSObject.Properties.Name -contains 'scenario') { $outcome.scenario } else { $outcome.level }), $(if ($outcome.PSObject.Properties.Name -contains 'scenario_name') { $outcome.scenario_name } else { $outcome.level_name }))) }
}
$clock = Read-JsonFile (Join-Path $Dir 'clock.json')
if (-not $clock) { [void]$problems.Add('missing clock.json') }
else {
    $labels = @($clock.samples | ForEach-Object { $_.label })
    foreach ($l in 'start', 'go', 'audio_start', 'audio_stop', 'end') { if ($l -notin $labels) { [void]$problems.Add("clock.json has no '$l' sample") } }
}
$wav = Join-Path $Dir 'audio.wav'
if (-not (Test-Path $wav)) { [void]$problems.Add('missing audio.wav') }
else {
    $ffmpeg = Find-FFmpeg
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $vol = & $ffmpeg -hide_banner -nostats -i $wav -af volumedetect -f null - 2>&1 | ForEach-Object { "$_" }
    $ErrorActionPreference = $eap
    $max = $vol | Select-String 'max_volume: (\S+) dB' | Select-Object -First 1
    $dur = $vol | Select-String 'Duration: (\d+):(\d+):([\d\.]+)' | Select-Object -First 1
    if ($dur) { $s = [int]$dur.Matches[0].Groups[1].Value * 3600 + [int]$dur.Matches[0].Groups[2].Value * 60 + [double]$dur.Matches[0].Groups[3].Value; [void]$notes.Add(("audio.wav {0:N1} s, max volume {1} dB" -f $s, $(if ($max) { $max.Matches[0].Groups[1].Value } else { '?' }))) }
    $clockFile = Join-Path $Dir 'audio_clock.jsonl'
    if (Test-Path $clockFile) {
        # v1.4: per-buffer audio clock; the WAV must span first buffer -> last buffer on the wall clock.
        $rows = @(foreach ($l in [System.IO.File]::ReadLines($clockFile)) { if ($l -match '"frame":(\d+),"frames":(\d+),"qpc":\d+,"t_ns":(\d+),"silence_before":(\d+),.*"rate":(\d+)') { [pscustomobject]@{ f = [long]$matches[1]; n = [long]$matches[2]; t = [long]$matches[3]; s = [long]$matches[4]; r = [double]$matches[5] } } })
        if ($rows.Count -eq 0) { [void]$problems.Add('audio_clock.jsonl has no rows') }
        else {
            $r0 = $rows[0]; $rn = $rows[$rows.Count - 1]
            $maxDrift = 0.0; foreach ($r in $rows) { $d = [math]::Abs((($r.t - $r0.t) / 1e9 - ($r.f - $r0.f) / $r0.r) * 1000); if ($d -gt $maxDrift) { $maxDrift = $d } }
            $gapsN = @($rows | Where-Object { $_.s -gt 0 }).Count; $silS = (($rows | ForEach-Object { $_.s }) | Measure-Object -Sum).Sum / $r0.r
            [void]$notes.Add(("audio_clock: {0} buffers, {1} render stalls filled ({2:N2} s silence), max drift {3:N0} ms" -f $rows.Count, $gapsN, $silS, $maxDrift))
            if ($maxDrift -gt 250) { [void]$problems.Add("audio_clock drift up to $([math]::Round($maxDrift)) ms: system_audio would be unaligned") }
        }
    } elseif ($dur) { [void]$notes.Add('no audio_clock.jsonl (drop-in older than v1.4): audio is end-anchored; render stalls would leave it unaligned') }
    if (-not $max -or $max.Matches[0].Groups[1].Value -eq '-inf' -or [double]$max.Matches[0].Groups[1].Value -lt -60) { [void]$notes.Add('audio.wav is silent: check au.DisableAppVolume / that the game plays sounds') }
}

[void]$notes.Add("inputs: $($inputs.rows) rows $(($inputs.kinds.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ' ')")
[void]$notes.Add("telemetry: $($telemetry.rows) rows $(($telemetry.kinds.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ' ')")
$status = if ($problems.Count) { 'FAIL' } else { 'PASS' }
Write-Host "$status $Dir"
foreach ($p in $problems) { Write-Host "  problem: $p" }
foreach ($n in $notes) { Write-Host "  note: $n" }
if ($problems.Count) { exit 1 }

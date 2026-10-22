<#
.SYNOPSIS
  Measure how well video and audio line up with the QPC clock in a recorded bundle, using sync markers: a game
  telemetry event (default "jump") that coincides with a white square in the top-left corner of the frame and a
  beep. The pipeline test project (games\_pipeline-test) emits these; real games don't need to.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File sync-check.ps1 %GF_ROOT%\recordings\_pipeline-test\<run-id>
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$RunDir,
    [string]$Event = 'jump'
)

. (Join-Path $PSScriptRoot 'common.ps1')
$ffmpeg = Find-FFmpeg
$meta = Read-JsonFile (Join-Path $RunDir 'metadata.json')
$tmp = Join-Path $env:TEMP ("sync-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $tmp | Out-Null

try {
    $events = @(foreach ($line in [System.IO.File]::ReadLines((Join-Path $RunDir 'telemetry.jsonl'))) {
        if ($line -match "`"event`":`"$Event`"" -and $line -match '"t_ns":(\d+)') { [long]$matches[1] }
    })

    # Video: mean brightness of the marker square per frame.
    $gray = Join-Path $tmp 'marker.gray'
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & $ffmpeg -hide_banner -loglevel error -i (Join-Path $RunDir 'video.mkv') -vf 'crop=32:32:16:16,scale=1:1:flags=area,format=gray' -f rawvideo $gray 2>&1 | Out-Null
    $ErrorActionPreference = $eap
    $bytes = [System.IO.File]::ReadAllBytes($gray)
    $videoEdges = @(for ($k = 1; $k -lt $bytes.Length; $k++) { if ($bytes[$k] -gt 128 -and $bytes[$k - 1] -le 128) { $k } })
    $v0 = [long]$meta.video_start_offset_ns
    $videoEdgeNs = @($videoEdges | ForEach-Object { $v0 + [long]($_ * 1e9 / 60) })

    # Audio: onsets in the game's master-submix recording (mono mix, 48 kHz).
    $pcm = Join-Path $tmp 'audio.s16'
    $ErrorActionPreference = 'Continue'
    & $ffmpeg -hide_banner -loglevel error -i (Join-Path $RunDir 'raw\audio.wav') -ac 1 -ar 48000 -f s16le $pcm 2>&1 | Out-Null
    $ErrorActionPreference = $eap
    $raw = [System.IO.File]::ReadAllBytes($pcm)
    $a0 = [long]$meta.system_audio.start_offset_ns
    $audioEdgeNs = New-Object System.Collections.ArrayList
    $quiet = 0
    for ($s = 0; $s -lt $raw.Length / 2; $s++) {
        $v = [math]::Abs([int][BitConverter]::ToInt16($raw, $s * 2))
        if ($v -gt 2000) {
            if ($quiet -gt 2400) { [void]$audioEdgeNs.Add($a0 + [long]($s * 1e9 / 48000)) }   # after >= 50 ms of quiet
            $quiet = 0
        } else { $quiet++ }
    }

    function Measure-Lag([long[]]$EventNs, [long[]]$EdgeNs, [string]$Name) {
        $lags = @(foreach ($e in $EventNs) {
            $next = $EdgeNs | Where-Object { $_ -ge $e - 50000000 } | Select-Object -First 1   # allow 50 ms early
            if ($null -ne $next -and ($next - $e) -lt 500000000) { ($next - $e) / 1e6 }
        })
        if ($lags.Count -eq 0) { return [ordered]@{ signal = $Name; matched = 0; events = $EventNs.Count; edges = $EdgeNs.Count } }
        $s = $lags | Measure-Object -Average -Minimum -Maximum
        return [ordered]@{ signal = $Name; events = $EventNs.Count; edges = $EdgeNs.Count; matched = $lags.Count
            lag_ms_mean = [math]::Round($s.Average, 1); lag_ms_min = [math]::Round($s.Minimum, 1); lag_ms_max = [math]::Round($s.Maximum, 1) }
    }
    # Frame code: 10 cells of 32x32 at the top-right hold GFrameCounter % 1024 (bit 0 leftmost).
    $codeRaw = Join-Path $tmp 'code.gray'
    $ErrorActionPreference = 'Continue'
    & $ffmpeg -hide_banner -loglevel error -i (Join-Path $RunDir 'video.mkv') -vf 'crop=320:32:1600:0,scale=10:1:flags=area,format=gray' -f rawvideo $codeRaw 2>&1 | Out-Null
    $ErrorActionPreference = $eap
    $cb = [System.IO.File]::ReadAllBytes($codeRaw)
    $frameTime = @{}   # game frame -> first t_ns seen in inputs.jsonl (the bot injects every frame)
    foreach ($line in [System.IO.File]::ReadLines((Join-Path $RunDir 'inputs.jsonl'))) {
        if ($line -match '"t_ns":(\d+),"qpc":\d+,"frame":(\d+)') { $f = [long]$matches[2]; if (-not $frameTime.ContainsKey($f)) { $frameTime[$f] = [long]$matches[1] } }
    }
    $frameCode = $null
    if ($frameTime.Count -gt 0) {
        $byCode = @{}
        foreach ($f in ($frameTime.Keys | Sort-Object)) { $c = [int]($f % 1024); if (-not $byCode.ContainsKey($c)) { $byCode[$c] = New-Object System.Collections.ArrayList }; [void]$byCode[$c].Add($f) }
        $lags = New-Object System.Collections.ArrayList
        $repeats = 0; $skipped = 0; $traced = 0; $prevF = $null
        for ($k = 0; $k -lt $cb.Length / 10; $k++) {
            $code = 0
            for ($b = 0; $b -lt 10; $b++) { if ($cb[$k * 10 + $b] -gt 128) { $code = $code -bor (1 -shl $b) } }
            $vt = $v0 + [long]($k * 1e9 / 60)
            # The game frame with this code whose game time is closest before the video time.
            $cand = $null
            if ($byCode.ContainsKey($code)) { foreach ($f in $byCode[$code]) { if ($frameTime[$f] -le $vt + 20000000) { $cand = $f } } }
            if ($null -eq $cand -or ($vt - $frameTime[$cand]) -gt 300000000) { $prevF = $null; continue }
            $traced++
            [void]$lags.Add(($vt - $frameTime[$cand]) / 1e6)
            if ($null -ne $prevF) { if ($cand -eq $prevF) { $repeats++ } elseif ($cand -gt $prevF + 1) { $skipped += $cand - $prevF - 1 } }
            $prevF = $cand
        }
        if ($traced -gt 0) {
            $sorted = @($lags | Sort-Object)
            $frameCode = [ordered]@{ video_frames = $cb.Length / 10; traced = $traced; repeated = $repeats; skipped_game_frames = $skipped
                lag_ms_mean = [math]::Round(($sorted | Measure-Object -Average).Average, 1); lag_ms_p5 = [math]::Round($sorted[[int]($sorted.Count * 0.05)], 1)
                lag_ms_p95 = [math]::Round($sorted[[int]($sorted.Count * 0.95)], 1) }
        }
    }

    $report = [ordered]@{
        run = Split-Path $RunDir -Leaf
        video = Measure-Lag $events $videoEdgeNs 'video marker (white square)'
        audio = Measure-Lag $events @($audioEdgeNs) 'audio marker (880 Hz beep)'
        frame_code = $frameCode
    }
    Write-JsonFile (Join-Path $RunDir 'sync_check.json') $report
    $report | ConvertTo-Json -Depth 5
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

<#
.SYNOPSIS
  Record AutoPlay runs of a packaged game: launch with the contract flags, capture the window with ffmpeg,
  validate, and write one gameplay bundle per run. See docs/ue-pipeline.md and docs/autoplay-contract.md.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File record.ps1 stealth -Build C:\Users\Xiang\Work\builds\stealth\a1b2c3d4 -Level 1 -Runs 3
  powershell -ExecutionPolicy Bypass -File record.ps1 stealth -Build latest -Level 2 -Runs 1 -Skill 0.5 -Seed 42

  Bundle: recordings\<game>\<run-id>\ video.mkv, system_audio.mka, inputs.jsonl, telemetry.jsonl, outcome.json,
  metadata.json, validation.json, manifest.json, raw\ (the game's RecordDir, ffmpeg log). Failed runs are kept and
  marked (validation.json status "failed", FAILED file). One row per run in .recording\<game>\runs.jsonl.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [Parameter(Mandatory = $true)][string]$Build,
    [Alias('Level')][int]$Scenario = 1,   # a scenario: start state + win/lose condition (a level, chapter, race stage, start setup)
    [int]$Runs = 1,
    [double]$Skill = -1,
    [long]$Seed = -1,
    [int]$MaxSeconds = 600,
    [ValidateSet('auto', 'gfxcapture', 'ddagrab', 'gdigrab-region', 'gdigrab-window')][string]$Capture = 'auto',
    [switch]$NoStablePath,
    [double]$IdleMinutes = 5,   # user's decision: record only after this long without keyboard/mouse input (0 = don't wait)
    [int]$MaxVramInUseMB = 8192,   # before launch, wait while more VRAM than this is in use by other processes (nvidia-smi total)
    [int]$OutputIndex = 0,
    [int]$CaptureRate = 240,
    [string]$ExtraArgs = ''
)

. (Join-Path $PSScriptRoot 'common.ps1')
[void][UePipeline.Win]::MakeDpiAware()   # physical pixels for window rects (the display runs at 150 %)

$info = Get-GameInfo $Game
# Coordinator override for one drain (e.g. "record now, don't wait for idle"): builds\_queue\_idle-override.txt
# {"idle_minutes": 0, ...}. Applies when -IdleMinutes isn't given; pipeline.ps1 retires it when the queue is empty.
$idleOverride = Read-JsonFile (Join-Path $BuildsRoot '_queue\_idle-override.txt')   # .txt: the drainer reads *.json as requests
if ($idleOverride -and -not $PSBoundParameters.ContainsKey('IdleMinutes')) {
    $IdleMinutes = [double]$idleOverride.idle_minutes
    Write-Step "idle wait override in effect: $IdleMinutes min ($($idleOverride.reason))"
}
if ($Build -eq 'latest') {
    $Build = (Get-ChildItem (Join-Path $BuildsRoot $Game) -Directory | Where-Object { $_.Name -notlike '_*' -and (Test-Path (Join-Path $_.FullName 'build_info.json')) } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
    if (-not $Build) { throw "no packaged build of $Game under $BuildsRoot\$Game" }
}
$buildInfo = Read-JsonFile (Join-Path $Build 'build_info.json')
if (-not $buildInfo -or -not $buildInfo.packaged) { throw "$Build has no packaged build_info.json (run build.ps1 -Package)" }
# AutoPlay drop-in version decides the output-dir flag: v1 reads -RecordDir, v2 (contract v1.2) reads -OutputDir.
$autoplayVersion = if ($buildInfo.PSObject.Properties.Name -contains 'autoplay_version' -and $buildInfo.autoplay_version) { [int]$buildInfo.autoplay_version } else { $null }
if (-not $autoplayVersion) {
    # Builds made before build.ps1 recorded it: the private clone is still at (or near) that commit.
    $h = Get-ChildItem (Join-Path (Join-Path (Join-Path $BuildsRoot '_src') $Game) 'Source') -Recurse -Filter AutoPlaySubsystem.h -File -ErrorAction SilentlyContinue | Select-Object -First 1
    $autoplayVersion = if ($h -and ((Get-Content $h.FullName -Raw) -match 'ContractVersion\s*=\s*(\d+)')) { [int]$matches[1] } else { 1 }
}
$outDirFlag = if ($autoplayVersion -ge 2) { 'OutputDir' } else { 'RecordDir' }
$scenarioFlag = if ($autoplayVersion -ge 3) { 'Scenario' } else { 'Level' }   # v1.3 renamed level -> scenario

# Outcome/telemetry keys changed in v1.3 (scenario_*); older games write level_*.
function Get-OutcomeValue($Outcome, [string]$NewKey, [string]$OldKey) {
    if (-not $Outcome) { return $null }
    $names = $Outcome.PSObject.Properties.Name
    if ($names -contains $NewKey) { return $Outcome.$NewKey }
    if ($names -contains $OldKey) { return $Outcome.$OldKey }
    return $null
}
# Launch the real binary, not the bootstrap stub, so the PID we hold owns the window.
$buildConfig = if ($buildInfo.PSObject.Properties.Name -contains 'config' -and $buildInfo.config) { $buildInfo.config } else { 'Development' }
$exeName = if ($buildConfig -eq 'Development') { "$($info.ProjectName).exe" } else { "$($info.ProjectName)-Win64-$buildConfig.exe" }
$exe = Join-Path $Build "Windows\$($info.ProjectName)\Binaries\Win64\$exeName"
if (-not (Test-Path $exe)) { $exe = $buildInfo.exe_path }

# Cooked-content sanity check: a pipeline build much smaller than the game's own packaged build usually means store
# content (git-ignored Fab/Marketplace packs) was missing from the cook. Reference = largest of the game's own outputs.
# Per Content\Paks folder (one packaged build each); the largest one under $Dir, since a folder may hold several builds.
function Get-CookedMB([string]$Dir) {
    if (-not (Test-Path $Dir)) { return 0 }
    $best = 0
    foreach ($p in @(Get-ChildItem $Dir -Recurse -Directory -Filter Paks -ErrorAction SilentlyContinue)) {
        $sum = 0; foreach ($f in @(Get-ChildItem $p.FullName -Recurse -File -Include *.pak, *.ucas, *.utoc -ErrorAction SilentlyContinue)) { $sum += $f.Length }
        if ($sum -gt $best) { $best = $sum }
    }
    [math]::Round($best / 1MB, 1)
}
$contentCheck = [ordered]@{ build_mb = (Get-CookedMB (Join-Path $Build 'Windows')); reference_mb = 0; reference = $null; ratio = $null; status = 'no_reference' }
$refDirs = @(Get-ChildItem $info.Dir -Directory -Filter 'Packaged*' -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }) +
    @((Join-Path $info.Dir 'Saved\StagedBuilds'), (Join-Path (Join-Path $WorkRoot 'deliverables') $Game))
foreach ($d in $refDirs) { $mb = Get-CookedMB $d; if ($mb -gt $contentCheck.reference_mb) { $contentCheck.reference_mb = $mb; $contentCheck.reference = $d } }
if ($contentCheck.reference_mb -gt 0) {
    $contentCheck.ratio = [math]::Round($contentCheck.build_mb / $contentCheck.reference_mb, 2)
    $contentCheck.status = if ($contentCheck.ratio -lt 0.7) { 'much_smaller' } else { 'ok' }
    $msg = "cooked content: this build {0:N1} MB vs the game's own build {1:N1} MB ({2}) = {3:P0}" -f $contentCheck.build_mb, $contentCheck.reference_mb, $contentCheck.reference, $contentCheck.ratio
    if ($contentCheck.status -eq 'much_smaller') {
        Write-Host ''
        Write-Host ('!' * 100) -ForegroundColor Red
        Write-Host "WARNING: $msg" -ForegroundColor Red
        Write-Host "WARNING: the pipeline build is much smaller than the game's own build: store content (git-ignored Content dirs) may be missing. Check build_info.json hydrated_content." -ForegroundColor Red
        Write-Host ('!' * 100) -ForegroundColor Red
        Write-Host ''
        Write-HeavyLog 'content_warning' "record $Game" @{ message = $msg }
    } else { Write-Step $msg }
} else { Write-Step ("cooked content: this build {0:N1} MB (no packaged build of the game itself to compare with)" -f $contentCheck.build_mb) }
$ffmpeg = Find-FFmpeg
$ffprobe = Find-FFprobe
$ffmpegVersion = (Invoke-Native $ffmpeg @('-hide_banner', '-version') | Select-Object -First 1)
$qpcFreq = [UePipeline.Win]::QpcFrequency()
# NVENC when this ffmpeg + driver pair can open it (ffmpeg 9 needs driver >= 610), else libx264 on the CPU.
$eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
# Encoder preference: NVENC (RTX 4080), then AMF on the Ryzen's integrated Radeon, then libx264 on the CPU.
$Encoder = 'libx264'
foreach ($enc in 'h264_nvenc', 'h264_amf') {
    & $ffmpeg -hide_banner -loglevel error -f lavfi -i 'color=c=black:s=256x256:r=60' -t 0.1 -c:v $enc -f null - 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $Encoder = $enc; break }
}
$ErrorActionPreference = $eap
Write-Step "ffmpeg: $ffmpeg ($ffmpegVersion), encoder $Encoder"
$skillCycle = @(1.0, 0.75, 0.5, 0.25)
$rng = New-Object System.Random

# ---------------------------------------------------------------------------------------------------------------------

function Start-Capture([string]$Mode, [int[]]$Rect, [string]$Title, [string]$VideoPath, [string]$LogPath, [string]$ProgressPath, [IntPtr]$Hwnd) {
    $x, $y, $w, $h = $Rect
    switch ($Mode) {
        'gfxcapture' {
            # Windows.Graphics.Capture of the game window itself (client area): other windows, dialogs, the cursor and
            # window moves never reach the video, so the game needs no topmost and the user can keep working.
            $capIn = "-f lavfi -i `"gfxcapture=hwnd=$($Hwnd.ToInt64()):capture_cursor=0:capture_border=0:display_border=0:max_framerate=120,showinfo`""
        }
        'ddagrab' {
            # Zero-copy: D3D11 frames straight into NVENC. showinfo on hardware frames costs nothing (no pixel access)
            # and gives one timestamped log line per captured frame for the start-time estimate.
            $capIn = "-f lavfi -i `"ddagrab=output_idx=${OutputIndex}:framerate=${CaptureRate}:dup_frames=0:offset_x=${x}:offset_y=${y}:video_size=${w}x${h}:draw_mouse=0,showinfo`""
        }
        'gdigrab-region' {
            $capIn = "-f gdigrab -framerate 60 -draw_mouse 0 -offset_x $x -offset_y $y -video_size ${w}x${h} -i desktop -vf showinfo"
        }
        'gdigrab-window' {
            $capIn = "-f gdigrab -framerate 60 -draw_mouse 0 -i `"title=$Title`" -vf showinfo"
        }
    }
    $tags = '-color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -fps_mode cfr -r 60 -an'
    if ($Encoder -eq 'h264_nvenc') {
        $encode = "-c:v h264_nvenc -preset p5 -tune hq -rc vbr -cq 19 -b:v 0 -maxrate 60M -bufsize 120M -g 120 -bf 0 $tags"
        if ($Mode -notin @('ddagrab', 'gfxcapture')) { $encode = "-pix_fmt yuv420p $encode" }   # ddagrab: D3D11 frames go to NVENC as they are
    } else {
        # AMF / libx264 take system-memory frames: pick the 60 fps grid first (fps filter, no pixel access), so only 60
        # frames a second are downloaded from the GPU and converted with an explicit BT.709 matrix.
        $pix = if ($Encoder -eq 'h264_amf') { 'nv12' } else { 'yuv420p' }
        $conv = "scale=out_color_matrix=bt709:out_range=tv,format=$pix"
        if ($Mode -in @('ddagrab', 'gfxcapture')) { $capIn = $capIn.TrimEnd('"') + ",fps=60,hwdownload,format=bgra,$conv" + '"' }
        else { $capIn += ",$conv" }
        $encode = if ($Encoder -eq 'h264_amf') { "-c:v h264_amf -quality quality -rc cqp -qp_i 18 -qp_p 20 -g 120 -bf 0 $tags" }
                   else { "-c:v libx264 -preset ultrafast -crf 17 -g 120 -bf 0 -pix_fmt yuv420p $tags" }
    }
    $ffArgs = "-hide_banner -loglevel +datetime+level+info -stats_period 1 -progress `"$ProgressPath`" -y $capIn $encode `"$VideoPath`""
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'cmd.exe'
    $psi.Arguments = "/d /s /c `"`"$ffmpeg`" $ffArgs 2> `"$LogPath`"`""
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardInput = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    return [pscustomobject]@{ Process = $p; Command = "ffmpeg $ffArgs"; Mode = $Mode }
}

function Stop-Capture($Cap, [int]$TimeoutMs = 15000) {
    if ($Cap.Process.HasExited) { return }
    try { $Cap.Process.StandardInput.Write('q'); $Cap.Process.StandardInput.Flush() } catch { }
    if (-not $Cap.Process.WaitForExit($TimeoutMs)) {
        & taskkill.exe /T /F /PID $Cap.Process.Id 2>&1 | Out-Null   # cmd and its ffmpeg child
        [void]$Cap.Process.WaitForExit(5000)
    }
}

function Get-CapturedFrameCount([string]$LogPath) {
    if (-not (Test-Path $LogPath)) { return 0 }
    try {
        $fs = [System.IO.File]::Open($LogPath, 'Open', 'Read', 'ReadWrite')
        $text = (New-Object System.IO.StreamReader($fs)).ReadToEnd(); $fs.Dispose()
        return ([regex]::Matches($text, 'Parsed_showinfo.*?\] \[info\] n:')).Count
    } catch { return 0 }
}

function Get-VideoStart([string]$LogPath, $ClockSamples) {
    # First captured frame's wall time = min over frames of (log time - pts), plus half a millisecond for the log's
    # truncation to ms. ffmpeg logs local time from av_gettime (GetSystemTimePreciseAsFileTime); map it to QPC with
    # the pipeline's QPC/UTC pairs.
    $best = [long]::MaxValue; $n = 0
    foreach ($line in [System.IO.File]::ReadLines($LogPath)) {
        if ($line -match '^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) \[Parsed_showinfo[^\]]*\] \[info\] n:\s*(\d+) pts:\s*(-?\d+)') {
            $local = [datetime]::ParseExact($matches[1], 'yyyy-MM-dd HH:mm:ss.fff', [Globalization.CultureInfo]::InvariantCulture, 'AssumeLocal')
            $unixNs = ($local.ToUniversalTime().Ticks - 621355968000000000) * 100
            $d = $unixNs - [long]$matches[3] * 1000   # wall time of frame 0 implied by this frame (pts is in us)
            if ($d -lt $best) { $best = $d }
            $n++
            if ($n -ge 1800) { break }   # first 30 s are plenty
        }
    }
    if ($n -eq 0) { return $null }
    $firstUnixNs = $best + 500000
    # Map unix ns -> QPC ns through the pipeline clock pair nearest in time.
    $pair = $ClockSamples | Sort-Object { [math]::Abs($_.unix_ns - $firstUnixNs) } | Select-Object -First 1
    $tNs = $pair.t_ns + ($firstUnixNs - $pair.unix_ns)
    return [pscustomobject]@{ t_ns = $tNs; unix_ns = $firstUnixNs; frames_used = $n; clock_pair = $pair.label; uncertainty_ms = 1.5 }
}

function Get-InputGaps([string]$LogPath, [long]$FromUs = 0, [long]$ToUs = [long]::MaxValue) {
    # Capture input timing from showinfo: count, rate, and frames missing in gaps longer than 25 ms.
    $prev = $null; $n = 0; $missed = 0; $gaps = 0; $first = $null
    foreach ($line in [System.IO.File]::ReadLines($LogPath)) {
        if ($line -match 'Parsed_showinfo[^\]]*\] \[info\] n:\s*\d+ pts:\s*(\d+)') {
            $pts = [long]$matches[1]
            if ($pts -lt $FromUs -or $pts -gt $ToUs) { continue }
            $n++
            if ($null -eq $first) { $first = $pts }
            if ($null -ne $prev -and ($pts - $prev) -gt 25000) { $gaps++; $missed += [math]::Round(($pts - $prev) / 16666.7) - 1 }
            $prev = $pts
        }
    }
    if ($n -lt 2) { return $null }
    $span = ($prev - $first) / 1e6
    return [ordered]@{ frames = $n; span_s = [math]::Round($span, 3); rate_fps = [math]::Round($n / $span, 1); gaps_over_25ms = $gaps
        missed_60fps_frames = $missed; missed_pct = [math]::Round(100.0 * $missed / ($span * 60), 2) }
}

function Find-GpuCrash([string]$RawDir, [datetime]$Since) {
    # Evidence of a D3D12 device loss / GPU hang or crash from this run: the game log (Development builds) and crash
    # reports written since the run started (Saved\Crashes next to the exe, or %LOCALAPPDATA%\<Project> for Shipping).
    $pattern = '(?i)DXGI_ERROR_DEVICE_(REMOVED|HUNG|RESET)|GPU crash|GPU hang|device (lost|removed)|Device Removed|breadcrumb|D3D12.{0,40}(TDR|hung|lost)'
    $files = New-Object System.Collections.ArrayList
    if (Test-Path (Join-Path $RawDir 'game.log')) { [void]$files.Add((Join-Path $RawDir 'game.log')) }
    $windowsDir = Split-Path (Split-Path (Split-Path (Split-Path $exe)))   # ...\Windows\<Project>\Binaries\Win64\x.exe
    foreach ($d in @((Join-Path $windowsDir "$($info.ProjectName)\Saved\Crashes"), (Join-Path $env:LOCALAPPDATA "$($info.ProjectName)\Saved\Crashes"))) {
        if (Test-Path $d) {
            Get-ChildItem $d -Recurse -File -Include *.log, *.xml, *.runtime-xml, *.txt -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTime -ge $Since } | ForEach-Object { [void]$files.Add($_.FullName) }
        }
    }
    foreach ($f in $files) {
        $hit = Select-String -LiteralPath $f -Pattern $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { return "$(Split-Path $f -Leaf): $($hit.Line.Trim().Substring(0, [Math]::Min(200, $hit.Line.Trim().Length)))" }
    }
    return $null
}

function Read-Progress([string]$Path) {
    $vals = @{}
    if (Test-Path $Path) {
        foreach ($l in Get-Content $Path) { if ($l -match '^(\w+)=(.*)$') { $vals[$matches[1]] = $matches[2].Trim() } }
    }
    return $vals
}

function Test-Jsonl([string]$Path) {
    # Parses every line; returns counts per type/event, first/last t_ns, monotonicity.
    $ser = New-Object System.Web.Script.Serialization.JavaScriptSerializer
    $ser.MaxJsonLength = 64MB
    $r = [ordered]@{ lines = 0; bad_lines = 0; non_monotonic = 0; first_t_ns = $null; last_t_ns = $null; counts = @{} }
    if (-not (Test-Path $Path)) { return $null }
    $prev = 0
    foreach ($line in [System.IO.File]::ReadLines($Path)) {
        if ($line.Trim() -eq '') { continue }
        $r.lines++
        try { $o = $ser.DeserializeObject($line) } catch { $r.bad_lines++; continue }
        $t = [long]$o['t_ns']
        if ($t -lt $prev) { $r.non_monotonic++ }
        $prev = $t
        if ($null -eq $r.first_t_ns) { $r.first_t_ns = $t }
        $r.last_t_ns = $t
        $k = if ($o.ContainsKey('type')) { $o['type'] } else { $o['event'] }
        if ($r.counts.ContainsKey($k)) { $r.counts[$k]++ } else { $r.counts[$k] = 1 }
    }
    return $r
}

function Get-AudioStats([string]$WavPath) {
    if (-not (Test-Path $WavPath)) { return $null }
    $probe = Invoke-Native $ffprobe @('-v', 'error', '-show_entries', 'stream=sample_rate,channels,duration', '-of', 'json', $WavPath) | Out-String | ConvertFrom-Json
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $vol = & $ffmpeg -hide_banner -nostats -i $WavPath -af volumedetect -f null - 2>&1 | ForEach-Object { "$_" }
    $ErrorActionPreference = $eap
    $mean = ($vol | Select-String 'mean_volume: (-?[\d\.]+|-inf) dB' | Select-Object -First 1)
    $max = ($vol | Select-String 'max_volume: (-?[\d\.]+|-inf) dB' | Select-Object -First 1)
    $s = $probe.streams[0]
    return [ordered]@{
        sample_rate = [int]$s.sample_rate; channels = [int]$s.channels; duration_s = [double]$s.duration
        mean_volume_db = $(if ($mean -and $mean.Matches[0].Groups[1].Value -ne '-inf') { [double]$mean.Matches[0].Groups[1].Value } else { $null })
        max_volume_db = $(if ($max -and $max.Matches[0].Groups[1].Value -ne '-inf') { [double]$max.Matches[0].Groups[1].Value } else { $null })
    }
}

Add-Type -AssemblyName System.Web.Extensions

# ---------------------------------------------------------------------------------------------------------------------

# Run from a stable copy (builds\<game>\_run): Windows Firewall asks once per program path because UE's trace
# runtime listens on a TCP port in Development builds; a fixed path means one prompt per game, not one per build.
if (-not $NoStablePath) {
    $runRoot = Join-Path (Join-Path $BuildsRoot $Game) '_run'
    Enter-PipelineLock "stage $Game run copy"
    try {
        Write-Step "mirroring $Build\Windows -> $runRoot\Windows"
        & robocopy.exe (Join-Path $Build 'Windows') (Join-Path $runRoot 'Windows') /MIR /NJH /NJS /NP /NFL /NDL /R:2 /W:2 | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
        Copy-Item (Join-Path $Build 'build_info.json') (Join-Path $runRoot 'build_info.json') -Force
    } finally { Exit-PipelineLock }
    $exe = Join-Path $runRoot "Windows\$($info.ProjectName)\Binaries\Win64\$exeName"
}

# First run of this exe path: Windows Firewall will ask about UE's trace listener. Trigger that prompt now, off-screen,
# while the user may still be at the machine, instead of in the middle of an unattended run (where it blocks capture).
if ($buildConfig -ne 'Shipping' -and @(Get-NetFirewallApplicationFilter -Program $exe -ErrorAction SilentlyContinue).Count -eq 0) {   # Shipping has no trace listener
    Write-Step "no Windows Firewall rule for $exe yet: starting it off-screen for 20 s so the one-time prompt appears now"
    $pfSlot = Enter-GpuSlot "firewall pre-flight $Game" -Recording   # it renders (off-screen): GPU job
    try {
        $pf = Start-Process $exe -ArgumentList '-RenderOffScreen', '-nosound', '-nosplash' -PassThru -WindowStyle Hidden
        Start-Sleep -Seconds 20
        & taskkill.exe /T /F /PID $pf.Id 2>&1 | Out-Null
    } finally { Exit-GpuSlot $pfSlot }
    $t = (Get-Date).AddMinutes(30)
    while (@(Get-NetFirewallApplicationFilter -Program $exe -ErrorAction SilentlyContinue).Count -eq 0 -and (Get-Date) -lt $t) {
        Write-Step 'waiting for the Windows Firewall prompt to be answered (Allow or Cancel both work)'
        Start-Sleep -Seconds 60
    }
}

$results = New-Object System.Collections.ArrayList
$gpuRetried = @{}
for ($i = 0; $i -lt $Runs; $i++) {
    $runSeed = if ($Seed -ge 0) { $Seed + $i } else { $rng.Next(1, [int]::MaxValue) }
    $runSkill = if ($Skill -ge 0) { $Skill } else { $skillCycle[$i % $skillCycle.Count] }
    $runId = '{0}_S{1}_{2}_s{3}' -f $Game, $Scenario, (Get-Date -Format 'yyyyMMdd-HHmmss'), $runSeed
    $runDir = Join-Path (Join-Path $RecordingsRoot $Game) $runId
    $rawDir = Join-Path $runDir 'raw'
    New-Item -ItemType Directory -Force $rawDir | Out-Null
    $videoPath = Join-Path $runDir 'video.mkv'
    $ffLog = Join-Path $rawDir 'ffmpeg.log'
    $ffProgress = Join-Path $rawDir 'ffmpeg_progress.txt'
    $clock = New-Object System.Collections.ArrayList
    $problems = New-Object System.Collections.ArrayList
    $warnings = New-Object System.Collections.ArrayList
    $proc = $null; $cap = $null; $hwnd = [IntPtr]::Zero; $rect = $null
    $gameExit = $null; $killed = $false; $windowMoved = $false; $captureMode = $null; $privacyStop = $null
    $coverFirst = $null; $coverWhat = ''; $coverCount = 0
    $tStart = Get-Date
    # Display refresh: at 159 Hz a 60 fps capture repeats/skips game frames; the user switches to 120 Hz (or 60) for recording.
    $vc = Get-CimInstance Win32_VideoController | Where-Object { $_.CurrentRefreshRate -gt 1 -and $_.CurrentHorizontalResolution -gt 0 } | Select-Object -First 1
    $refreshHz = if ($vc) { [int]$vc.CurrentRefreshRate } else { $null }
    $displayMode = if ($vc) { "$($vc.CurrentHorizontalResolution)x$($vc.CurrentVerticalResolution) @ $refreshHz Hz ($($vc.Name))" } else { $null }
    if ($refreshHz -notin @(60, 120)) { [void]$warnings.Add("display refresh is $refreshHz Hz, expected 60 or 120 (60 fps capture will repeat/skip game frames)") }
    if ($contentCheck.status -eq 'much_smaller') { [void]$warnings.Add("cooked content $($contentCheck.build_mb) MB is only $([math]::Round($contentCheck.ratio * 100)) % of the game's own build ($($contentCheck.reference_mb) MB): store content may be missing") }

    # Screen capture needs the window untouched for minutes: wait until the user is away (and the session unlocked).
    # Keep the display on from now on: waiting for 5 idle minutes otherwise runs into the power plan's dim/off timer,
    # and Windows' dim overlay (Shell_SystemDim) then covers the game. Doesn't affect the idle measurement (input only).
    [UePipeline.Win]::KeepDisplayOn($true)
    # Then the GPU to ourselves: the machine-wide GPU slot (one GPU job at a time; not enough VRAM for two) and little
    # VRAM in use by others. If the user came back while we waited for those, give the slot back and wait again.
    $gpuSlot = $null; $vramOk = $true
    while ($true) {
        if ($IdleMinutes -gt 0) {
            $said = $false
            while ([UePipeline.Win]::IdleMs() -lt $IdleMinutes * 60000 -or (Get-Process LogonUI -ErrorAction SilentlyContinue)) {
                [UePipeline.Win]::KeepDisplayOn($true)   # refresh while waiting
                if (-not $said) { Write-Step "waiting until the user has been idle for $IdleMinutes min (and the session is unlocked)"; $said = $true }
                Start-Sleep -Seconds 15
            }
            if ($said) { Write-Step 'user idle' }
        }
        $gpuSlot = Enter-GpuSlot "record $Game $runId" -Recording
        $vramOk = Wait-VramFree "record $Game $runId" $MaxVramInUseMB
        if ($IdleMinutes -le 0 -or [UePipeline.Win]::IdleMs() -ge $IdleMinutes * 60000) { break }
        Write-Step 'user came back while waiting for the GPU: releasing the GPU slot and waiting again'
        Exit-GpuSlot $gpuSlot; $gpuSlot = $null
    }
    Write-Step "GPU slot held; $(Get-VramUsedMB) MB VRAM in use before launch"
    Enter-PipelineLock "record $Game $runId"
    [UePipeline.Win]::KeepDisplayOn($true)
    try {
        Write-Step "run $($i + 1)/$Runs $runId (skill $runSkill, seed $runSeed)"
        if (-not $vramOk) { throw "more than $MaxVramInUseMB MB VRAM stayed in use by other processes for 120 min; not launching" }
        [void]$clock.Add((Get-ClockSample 'record_start'))
        $gameArgs = "-AutoPlay -$scenarioFlag=$Scenario -Seed=$runSeed -Skill=$runSkill -${outDirFlag}=`"$rawDir`" -MaxSeconds=$MaxSeconds " +
                    "-BuildCommit=$($buildInfo.commit) -RunId=$runId -GoTimeout=300 -windowed -ResX=1920 -ResY=1080 -WinX=200 -WinY=150 " +
                    "-ini:Engine:[/Script/Engine.UserInterfaceSettings]:bAllowHighDPIInGameMode=True " +
                    "-nosplash -abslog=`"$rawDir\game.log`" $ExtraArgs"
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $exe; $psi.Arguments = $gameArgs; $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true   # Development builds log to raw\game.log (-abslog); Shipping writes none
        $psi.WorkingDirectory = Split-Path $exe
        $proc = [System.Diagnostics.Process]::Start($psi)
        $proc.BeginOutputReadLine(); $proc.BeginErrorReadLine()   # drain and discard
        try { $proc.PriorityClass = 'AboveNormal' } catch { }

        # ---- wait for ready.json, find the window ----
        $deadline = (Get-Date).AddSeconds(180)
        while (-not (Test-Path (Join-Path $rawDir 'ready.json'))) {
            if ($proc.HasExited) { throw "game exited (code $($proc.ExitCode)) before ready" }
            if ((Get-Date) -gt $deadline) { throw 'no ready.json within 180 s' }
            Start-Sleep -Milliseconds 200
        }
        $ready = Read-JsonFile (Join-Path $rawDir 'ready.json')
        $hwnd = [UePipeline.Win]::FindWindowOfPid([uint32]$ready.pid, '[AutoPlay]')
        if ($hwnd -eq [IntPtr]::Zero) { $hwnd = [UePipeline.Win]::FindWindowOfPid([uint32]$ready.pid, $null) }
        if ($hwnd -eq [IntPtr]::Zero) { throw "no visible window for pid $($ready.pid)" }
        $title = [UePipeline.Win]::Title($hwnd)
        # Games re-center their window; put it at a fixed spot near the top-left of the primary screen.
        [void][UePipeline.Win]::MoveClientTo($hwnd, 40, 80)
        Start-Sleep -Milliseconds 300
        $rect = [UePipeline.Win]::ClientRectOnScreen($hwnd)
        $screen = [UePipeline.Win]::PrimaryScreenSize()
        Write-Step "window '$title' client $($rect -join ',') on screen $($screen -join 'x')"
        if ($rect[2] -ne 1920 -or $rect[3] -ne 1080) { throw "client area is $($rect[2])x$($rect[3]), expected 1920x1080" }
        if ($rect[0] -lt 0 -or $rect[1] -lt 0 -or $rect[0] + 1920 -gt $screen[0] -or $rect[1] + 1080 -gt $screen[1]) { throw "window not fully on the primary screen: $($rect -join ',')" }

        # ---- start capture (ddagrab, falling back to gdigrab) ----
        # gfxcapture is opt-in only: in tests it delivered ~6 frames/s for an unfocused window and its timestamps did
        # not fit the start-time estimate. ddagrab (topmost window + privacy guard) is the default.
        $modes = if ($Capture -eq 'auto') { @('ddagrab', 'gdigrab-region') } else { @($Capture) }
        if ($modes[0] -ne 'gfxcapture') {
            # A first-run Windows Firewall prompt (or anything else) on top of the game would trip the privacy guard:
            # wait for the client area to be clear (the game waits for 'go' up to -GoTimeout=300).
            [void][UePipeline.Win]::SetTopmost($hwnd, $true)
            $t = (Get-Date).AddSeconds(240); $said = $false
            while (-not [UePipeline.Win]::IsClientUncovered($hwnd) -and (Get-Date) -lt $t) {
                if (-not $said) { Write-Step 'game window is covered (Windows Firewall prompt for a new program path?): waiting for it to clear'; $said = $true }
                Start-Sleep -Milliseconds 500
            }
            if (-not [UePipeline.Win]::IsClientUncovered($hwnd)) { throw "game window stayed covered for 240 s by $([UePipeline.Win]::CoveringWindow($hwnd)); not recording" }
        }
        foreach ($m in $modes) {
            # Screen-region modes record whatever is on screen there: keep the game on top. gfxcapture doesn't need it.
            [void][UePipeline.Win]::SetTopmost($hwnd, ($m -ne 'gfxcapture'))
            # One set of files per attempt: a failed attempt's ffmpeg must never block the next attempt's files.
            $videoPath = Join-Path $runDir "video.$m.mkv"
            $ffLog = Join-Path $rawDir "ffmpeg-$m.log"
            $ffProgress = Join-Path $rawDir "ffmpeg_progress-$m.txt"
            [void]$clock.Add((Get-ClockSample "capture_start_$m"))
            $cap = Start-Capture $m $rect $title $videoPath $ffLog $ffProgress $hwnd
            try { Get-CimInstance Win32_Process -Filter "ParentProcessId=$($cap.Process.Id)" | ForEach-Object { (Get-Process -Id $_.ProcessId).PriorityClass = 'AboveNormal' } } catch { }
            $t = (Get-Date).AddSeconds(10)
            while ((Get-CapturedFrameCount $ffLog) -lt 30 -and -not $cap.Process.HasExited -and (Get-Date) -lt $t) { Start-Sleep -Milliseconds 100 }
            if ((Get-CapturedFrameCount $ffLog) -ge 30 -and -not $cap.Process.HasExited) { $captureMode = $m; break }
            [void]$warnings.Add("capture mode $m failed: $((Get-Content $ffLog -Tail 3 -ErrorAction SilentlyContinue) -join ' | ')")
            Stop-Capture $cap 3000
            if (Test-Path $videoPath) { Move-Item -Force $videoPath (Join-Path $rawDir "failed-attempt-$m.mkv") }
            $cap = $null
        }
        if (-not $cap) { throw 'no capture mode worked' }
        Write-Step "capturing with $captureMode"

        # ---- go ----
        [void]$clock.Add((Get-ClockSample 'go_written'))
        [System.IO.File]::WriteAllText((Join-Path $rawDir 'go'), (Get-IsoNow), $Utf8NoBom)

        # ---- wait for the run to end: outcome.json appears while the window is still up ----
        $deadline = (Get-Date).AddSeconds($MaxSeconds + 90)
        $outcomePath = Join-Path $rawDir 'outcome.json'
        while (-not (Test-Path $outcomePath) -and -not $proc.HasExited) {
            if ((Get-Date) -gt $deadline) { $killed = $true; [void]$problems.Add("timeout: killed after $($MaxSeconds + 90) s"); break }
            if ($cap.Process.HasExited) { [void]$problems.Add('ffmpeg exited during the run'); break }
            $now = [UePipeline.Win]::ClientRectOnScreen($hwnd)
            if ($now -and ($now[2] -ne 1920 -or $now[3] -ne 1080)) { [void]$problems.Add("game window client area changed to $($now[2])x$($now[3])"); break }
            if ([UePipeline.Win]::IsIconic($hwnd)) { [void]$problems.Add('game window was minimized (no frames)'); break }
            if ($now -and ($now[0] -ne $rect[0] -or $now[1] -ne $rect[1])) {
                if (-not $windowMoved) {
                    # Who moved it? A held mouse button means a user drag; otherwise the game (e.g. a resolution apply,
                    # which re-centers UE windows) or another program.
                    Add-JsonLine (Join-Path $rawDir 'window.jsonl') ([ordered]@{ event = 'moved'; t_ns = (Get-ClockSample 'x').t_ns
                        from = $rect; to = $now; mouse_button_down = [UePipeline.Win]::MouseButtonDown() })
                }
                $windowMoved = $true
            }
            $covered = ($captureMode -ne 'gfxcapture') -and -not [UePipeline.Win]::IsClientUncovered($hwnd)
            if ($covered) {
                if (-not $coverFirst) { $coverFirst = Get-ClockSample 'privacy_first_seen'; $coverWhat = [UePipeline.Win]::CoveringWindow($hwnd) }
                $coverCount++
            } else { $coverFirst = $null; $coverCount = 0 }
            if ($captureMode -ne 'gfxcapture' -and ($windowMoved -or $coverCount -ge 3)) {
                # Privacy guard: a screen-region capture would now record other windows (moved window, or something
                # on top for ~0.3 s; shorter blips are tooltips/ghost windows). Stop; the video is cut to 0.5 s before
                # the first sighting below.
                $privacyStop = if ($coverFirst) { $coverFirst } else { Get-ClockSample 'privacy_stop' }
                $cover = if ($windowMoved) { '' } else { $coverWhat }
                Stop-Capture $cap
                [void]$problems.Add($(if ($windowMoved) { 'game window moved during screen-region capture: capture stopped' } else { "another window covered the game during screen-region capture: capture stopped ($cover)" }))
                $killed = $true
                break
            }
            Start-Sleep -Milliseconds 100
        }
        Stop-Capture $cap   # before the window closes: never capture what is behind it
        [void]$clock.Add((Get-ClockSample 'capture_stopped'))
        $final = Join-Path $runDir 'video.mkv'
        if (Test-Path $videoPath) { Move-Item -Force $videoPath $final }
        $videoPath = $final
        if ($windowMoved -and $captureMode -eq 'gfxcapture') { [void]$warnings.Add('game window was moved during the run (window capture follows it)') }

        if ($killed) {
            $proc.Kill(); $proc.WaitForExit(10000) | Out-Null
        } elseif (-not $proc.WaitForExit(60000)) {
            [void]$problems.Add('game did not quit within 60 s after outcome.json'); $proc.Kill(); $killed = $true
        }
        $gameExit = $proc.ExitCode
        if (-not $killed -and $gameExit -ne 0) { [void]$problems.Add("game exit code $gameExit") }
    } catch {
        [void]$problems.Add("run error: $($_.Exception.Message)")
        Write-Step "ERROR: $($_.Exception.Message)"
        if ($cap) { Stop-Capture $cap }
        if ($proc -and -not $proc.HasExited) { $proc.Kill(); $killed = $true; [void]$proc.WaitForExit(15000) }
    } finally {
        if ($hwnd -ne [IntPtr]::Zero -and [UePipeline.Win]::IsWindow($hwnd)) { [void][UePipeline.Win]::SetTopmost($hwnd, $false) }
        [void]$clock.Add((Get-ClockSample 'record_end'))
        [UePipeline.Win]::KeepDisplayOn($false)
        Exit-PipelineLock
        Exit-GpuSlot $gpuSlot
    }

    # ---- post-process (light work, outside the lock) ----
    if ((Split-Path $videoPath -Leaf) -ne 'video.mkv' -and (Test-Path $videoPath)) {   # run error mid-capture
        Move-Item -Force $videoPath (Join-Path $runDir 'video.mkv')
    }
    $videoPath = Join-Path $runDir 'video.mkv'
    $outcome = Read-JsonFile (Join-Path $rawDir 'outcome.json')
    $gameClock = Read-JsonFile (Join-Path $rawDir 'clock.json')
    foreach ($f in 'inputs.jsonl', 'telemetry.jsonl', 'outcome.json') {
        $src = Join-Path $rawDir $f
        if (Test-Path $src) {
            try { Copy-Item $src (Join-Path $runDir $f) -Force } catch { [void]$problems.Add("could not copy ${f}: $($_.Exception.Message)") }
        } else { [void]$problems.Add("missing $f") }
    }
    if (-not $gameClock) { [void]$problems.Add('missing clock.json') }

    $audio = Get-AudioStats (Join-Path $rawDir 'audio.wav')
    if ($audio) {
        $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        & $ffmpeg -hide_banner -loglevel error -y -i (Join-Path $rawDir 'audio.wav') -c:a flac (Join-Path $runDir 'system_audio.mka') 2>&1 | Out-Null
        $ErrorActionPreference = $eap
    } else { [void]$problems.Add('missing audio.wav') }

    $videoStart = $null; $probe = $null
    if ($captureMode -and (Test-Path $videoPath)) {
        $videoStart = Get-VideoStart $ffLog $clock
        if ($privacyStop -and $videoStart) {
            # Keep only what was recorded at least 0.5 s before the guard fired.
            $keep = [math]::Max(0, ($privacyStop.t_ns - $videoStart.t_ns) / 1e9 - 0.5)
            $cut = Join-Path $runDir 'video.cut.mkv'
            $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
            & $ffmpeg -hide_banner -loglevel error -y -i $videoPath -t $keep -c copy $cut 2>&1 | Out-Null
            $ErrorActionPreference = $eap
            if (Test-Path $cut) { Move-Item -Force $cut $videoPath; [void]$warnings.Add("video cut to $([math]::Round($keep, 1)) s (privacy guard)") }
            else {
                Move-Item -Force $videoPath (Join-Path $runDir 'video.UNTRIMMED-may-show-other-windows.mkv')
                [void]$problems.Add('could not cut the video before the privacy stop: delete video.UNTRIMMED-may-show-other-windows.mkv')
            }
        }
        $probe = Invoke-Native $ffprobe @('-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=codec_name,profile,pix_fmt,width,height,avg_frame_rate,nb_read_packets:format=duration', '-of', 'json', $videoPath) | Out-String | ConvertFrom-Json
    } elseif (-not $captureMode) { } else { [void]$problems.Add('missing video.mkv') }
    $progress = Read-Progress $ffProgress

    # ---- validation ----
    $inputs = Test-Jsonl (Join-Path $runDir 'inputs.jsonl')
    $telemetry = Test-Jsonl (Join-Path $runDir 'telemetry.jsonl')
    $checks = [ordered]@{}
    $gs = @{}; if ($gameClock) { foreach ($s in $gameClock.samples) { $gs[$s.label] = $s } }

    if ($outcome) {
        $checks.outcome = [ordered]@{ ok = ($outcome.result -in @('win', 'lose', 'timeout', 'abort')); result = $outcome.result; score = $outcome.score; duration_s = $outcome.duration_s }
        if (-not $checks.outcome.ok) { [void]$problems.Add("bad outcome.result '$($outcome.result)'") }
        if ($outcome.result -eq 'abort') { [void]$warnings.Add('run ended with abort') }
        if ($outcome.go_timed_out) { [void]$problems.Add('game never saw the go file') }
    } else { [void]$problems.Add('no outcome.json') }

    if ($inputs) {
        $injects = 0; if ($inputs.counts.ContainsKey('inject')) { $injects = $inputs.counts['inject'] }
        $checks.inputs = [ordered]@{ ok = ($injects -gt 0 -and $inputs.bad_lines -eq 0 -and $inputs.non_monotonic -eq 0); lines = $inputs.lines; injects = $injects; bad_lines = $inputs.bad_lines; non_monotonic = $inputs.non_monotonic; counts = $inputs.counts }
        if ($injects -eq 0) { [void]$problems.Add('no injected inputs') }
        if ($inputs.bad_lines -gt 0) { [void]$problems.Add("inputs.jsonl has $($inputs.bad_lines) unparseable lines") }
        if ($inputs.non_monotonic -gt 0) { [void]$problems.Add("inputs.jsonl t_ns goes backwards $($inputs.non_monotonic) times") }
    }
    if ($telemetry) {
        $missingEvents = @(@('run_start', 'scenario_start|level_start', 'scenario_end|level_end', 'run_end') | Where-Object { $alts = $_ -split '\|'; -not @($alts | Where-Object { $telemetry.counts.ContainsKey($_) }).Count })
        $checks.telemetry = [ordered]@{ ok = ($missingEvents.Count -eq 0 -and $telemetry.bad_lines -eq 0); lines = $telemetry.lines; missing = @($missingEvents); counts = $telemetry.counts }
        foreach ($e in $missingEvents) { [void]$problems.Add("telemetry has no $e") }
        if ($telemetry.bad_lines -gt 0) { [void]$problems.Add("telemetry.jsonl has $($telemetry.bad_lines) unparseable lines") }
    }

    # Audio clock: UE's StartRecording is queued to the audio thread (starts late by an unknown amount, ~0.1 s while
    # the level loads), StopRecording is synchronous. So the WAV is anchored at its end: start = audio_stop - duration.
    $audioStartNs = $null; $audioAligned = $null; $audioAnchor = $null; $audioClockInfo = $null
    $audioClockPath = Join-Path $rawDir 'audio_clock.jsonl'
    if ($audio -and (Test-Path $audioClockPath)) {
        # v1.4: the drop-in writes the WAV itself and logs every rendered buffer (WAV frame index -> QPC), filling render
        # stalls with silence, so the WAV is sample-accurate to wall time. Frame 0 is at the first row's t_ns.
        $rows = @(foreach ($l in [System.IO.File]::ReadLines($audioClockPath)) { if ($l -match '"frame":(\d+),"frames":(\d+),"qpc":\d+,"t_ns":(\d+),"silence_before":(\d+)') { [pscustomobject]@{ f = [long]$matches[1]; n = [long]$matches[2]; t = [long]$matches[3]; s = [long]$matches[4] } } })
        if ($rows.Count -gt 0) {
            $sr = [double]$audio.sample_rate
            $first = $rows[0]; $last = $rows[$rows.Count - 1]
            $audioStartNs = $first.t - [long]($first.f / $sr * 1e9)
            $spanS = ($last.t - $first.t) / 1e9 + $last.n / $sr
            $silenceS = ((@($rows | ForEach-Object { $_.s }) | Measure-Object -Sum).Sum) / $sr
            $gaps = @($rows | Where-Object { $_.s -gt 0 }).Count
            # Drift: WAV position of each buffer vs its wall time since frame 0 (should stay within ~2 buffers).
            $maxDriftMs = 0.0
            foreach ($r in $rows) { $d = [math]::Abs((($r.t - $audioStartNs) / 1e9 - $r.f / $sr) * 1000); if ($d -gt $maxDriftMs) { $maxDriftMs = $d } }
            $audioAligned = ($maxDriftMs -le 250 -and [math]::Abs($audio.duration_s - $spanS) -le 0.25)
            $audioAnchor = 'audio_clock.jsonl (per-buffer QPC; render stalls filled with silence)'
            $audioClockInfo = [ordered]@{ buffers = $rows.Count; gaps_filled = $gaps; silence_inserted_s = [math]::Round($silenceS, 3); max_drift_ms = [math]::Round($maxDriftMs, 1); span_s = [math]::Round($spanS, 3) }
            $silent = ($null -eq $audio.max_volume_db) -or ($audio.max_volume_db -lt -60)
            $checks.audio = [ordered]@{ ok = $audioAligned; aligned = $audioAligned; anchor = 'audio_clock'; duration_s = $audio.duration_s; clock = $audioClockInfo; silent = $silent; stats = $audio }
            if ($gaps -gt 0) { [void]$warnings.Add("audio render stalled $gaps times; $([math]::Round($silenceS, 2)) s of silence inserted to keep alignment") }
            if (-not $audioAligned) { [void]$warnings.Add("system_audio unaligned: drift up to $([math]::Round($maxDriftMs)) ms vs audio_clock") }
            if ($silent) { [void]$warnings.Add('audio is silent (max volume below -60 dB)') }
        }
    }
    if ($audio -and $null -eq $audioAligned) {
        $startLagMs = $null
        if ($gs.ContainsKey('audio_start') -and $gs.ContainsKey('audio_stop')) {
            $audioStartNs = [long]$gs['audio_stop'].t_ns - [long]([double]$audio.duration_s * 1e9)
            $startLagMs = [math]::Round(($audioStartNs - [long]$gs['audio_start'].t_ns) / 1e6, 1)
        }
        $silent = ($null -eq $audio.max_volume_db) -or ($audio.max_volume_db -lt -60)
        # Normal lag is ~0.1-0.2 s (StartRecording queued to the audio thread). Seconds of missing audio mean the mixer
        # stalled or swapped devices mid-run (e.g. the user changed the audio device), so end-anchoring can't align it.
        # A start late by up to the scenario's load time (go -> scenario_start; the audio thread is busy) is fine.
        $loadMs = 0
        $goQ = Get-OutcomeValue $outcome 'go_qpc' 'go_qpc'; $ssQ = Get-OutcomeValue $outcome 'scenario_start_qpc' 'level_start_qpc'
        if ($goQ -and $ssQ -and [long]$ssQ -gt [long]$goQ) { $loadMs = ([long]$ssQ - [long]$goQ) * 1000.0 / $qpcFreq }
        $lagOk = ($null -ne $startLagMs -and $startLagMs -ge -30 -and $startLagMs -le $loadMs + 1500)
        $audioAligned = $lagOk; $audioAnchor = 'end: audio_stop clock sample minus WAV duration'
        $checks.audio = [ordered]@{ ok = $lagOk; aligned = $lagOk; anchor = 'end'; duration_s = $audio.duration_s; start_lag_ms = $startLagMs; silent = $silent; stats = $audio }
        # Not a run failure (coordinator's rule): video, inputs and telemetry stay valid; system_audio is marked unaligned.
        if (-not $lagOk) { [void]$warnings.Add("audio_gap: $([math]::Round($startLagMs / 1000, 1)) s of audio missing (expected ~0.1-0.2 s + load $([math]::Round($loadMs / 1000, 1)) s): the mixer stalled, system_audio is unaligned; video/inputs/telemetry unaffected") }
        if ($silent) { [void]$warnings.Add('audio is silent (max volume below -60 dB)') }
    }

    if ($probe) {
        $vdur = [double]$probe.format.duration
        $frames = [int]$probe.streams[0].nb_read_packets
        $dup = [int]$progress['dup_frames']; $drop = [int]$progress['drop_frames']
        $capSpan = $null; $cover = $null
        if ($videoStart) {
            $stopNs = ($clock | Where-Object { $_.label -eq 'capture_stopped' } | Select-Object -First 1).t_ns
            $capSpan = ($stopNs - $videoStart.t_ns) / 1e9
            $videoEndNs = $videoStart.t_ns + [long]($vdur * 1e9)
            if ($outcome) {
                $levelStartNs = Convert-QpcToNs ([long](Get-OutcomeValue $outcome 'scenario_start_qpc' 'level_start_qpc')) $qpcFreq
                $levelEndNs = Convert-QpcToNs ([long](Get-OutcomeValue $outcome 'scenario_end_qpc' 'level_end_qpc')) $qpcFreq
                $cover = ($videoStart.t_ns -lt $levelStartNs -and $videoEndNs -gt $levelEndNs)
                if (-not $cover) { [void]$problems.Add('video does not cover the scenario (start..end)') }
            }
        } else { [void]$problems.Add('could not estimate video start time from ffmpeg log') }
        # ddagrab runs event-driven (dup_frames=0): every desktop update is an input frame (up to the display rate),
        # so drops are surplus samples; dups are 60 fps slots with no new desktop image (holes). Input gaps > 25 ms are
        # stretches where the desktop (the game) did not update for more than 1.5 frames.
        $dupPct = if ($frames -gt 0) { [math]::Round(100.0 * $dup / $frames, 2) } else { 100 }
        $gaps = if ($videoStart -and $outcome) {
            Get-InputGaps $ffLog ([long]((Convert-QpcToNs ([long](Get-OutcomeValue $outcome 'scenario_start_qpc' 'level_start_qpc')) $qpcFreq) - $videoStart.t_ns) / 1000) ([long]((Convert-QpcToNs ([long](Get-OutcomeValue $outcome 'scenario_end_qpc' 'level_end_qpc')) $qpcFreq) - $videoStart.t_ns) / 1000)
        } else { Get-InputGaps $ffLog }
        $durDiff = if ($null -ne $capSpan) { [math]::Round($vdur - $capSpan, 3) } else { $null }
        $checks.video = [ordered]@{
            ok = ($frames -gt 0 -and $dupPct -le 1.0 -and $null -ne $durDiff -and $durDiff -lt 0.5 -and $cover -ne $false)
            codec = $probe.streams[0].codec_name; profile = $probe.streams[0].profile; pix_fmt = $probe.streams[0].pix_fmt
            width = $probe.streams[0].width; height = $probe.streams[0].height; avg_frame_rate = $probe.streams[0].avg_frame_rate
            duration_s = $vdur; frames = $frames; dup_frames = $dup; dup_pct = $dupPct; surplus_input_frames_dropped = $drop; input = $gaps
            capture_span_s = $capSpan; duration_diff_s = $durDiff; covers_scenario = $cover
        }
        if ($probe.streams[0].width -ne 1920 -or $probe.streams[0].height -ne 1080) { [void]$problems.Add("video is $($probe.streams[0].width)x$($probe.streams[0].height)") }
        if ($dupPct -gt 5.0) { [void]$problems.Add("ffmpeg duplicated $dupPct % of output frames (no new image)") }
        elseif ($dupPct -gt 1.0) { [void]$warnings.Add("ffmpeg duplicated $dupPct % of output frames (no new image)") }
        if ($gaps -and $gaps.missed_pct -gt 2.0) { [void]$warnings.Add("capture input had gaps worth $($gaps.missed_pct) % of frames") }
        # Longer than the span means the start-time estimate is wrong; shorter means no new desktop images arrived
        # before the stop (event-driven capture cannot extend past its last image); level coverage is checked separately.
        if ($null -ne $durDiff -and $durDiff -ge 0.5) { [void]$problems.Add("video duration $vdur s exceeds capture span $capSpan s (clock mismatch)") }
        # Ending before the capture stopped is normal when the result screen is static: event-driven ddagrab gets no new
        # desktop images, and ffmpeg only sees the stop request once something on screen changes. What matters is that the
        # video covers scenario_start..scenario_end (checked above as covers_scenario).
        if ($outcome -and $outcome.run_duration_s -and $outcome.frames) {
            $gameFps = [math]::Round($outcome.frames / $outcome.run_duration_s, 2)
            $checks.video.game_fps = $gameFps
            if ($gameFps -lt 55) { [void]$warnings.Add("game averaged $gameFps fps (cap 60)") }
        }
    }

    $status = if ($problems.Count -gt 0) { 'failed' } elseif ($audioAligned -eq $false) { 'ok_video_only' } elseif ($warnings.Count -gt 0) { 'warn' } else { 'ok' }
    # A run that ended without an outcome because the GPU device was lost (UE 5.3 Lumen + VSM on async compute, see
    # Known issues) is classified separately and retried once.
    if ($status -eq 'failed' -and -not $outcome) {
        $gpu = Find-GpuCrash $rawDir $tStart
        if ($gpu) { $status = 'gpu_crash'; $problems.Insert(0, "gpu_crash: $gpu") }
    }

    # ---- metadata, manifest ----
    $videoStartNs = if ($videoStart) { $videoStart.t_ns } else { $null }
    $metadata = [ordered]@{
        schema = 'superposition.ue-autoplay-bundle/v1'
        lab_bundle_schema = 3
        run_id = $runId; game = $Game; project = $info.ProjectName
        scenario = $Scenario; scenario_name = (Get-OutcomeValue $outcome 'scenario_name' 'level_name')
        seed = $runSeed; skill = $runSkill; max_seconds = $MaxSeconds
        result = $(if ($outcome) { $outcome.result } else { $null }); score = $(if ($outcome) { $outcome.score } else { $null })
        player = [ordered]@{ kind = 'bot'; name = 'autoplay'; input_injection = 'UE Enhanced Input (InjectInputForAction)' }
        build = [ordered]@{ commit = $buildInfo.commit; short_sha = $buildInfo.short_sha; config = $buildConfig; path = $Build; exe = $exe; autoplay_version = $autoplayVersion; output_dir_flag = "-$outDirFlag"; hydrated_content = $(if ($buildInfo.PSObject.Properties.Name -contains 'hydrated_content') { @($buildInfo.hydrated_content) } else { $null }); content_check = $contentCheck }
        clock = [ordered]@{
            source = 'QueryPerformanceCounter'; qpc_frequency = $qpcFreq; t_ns_definition = 'qpc * 1e9 / qpc_frequency'
            samples = @(@($(if ($gameClock) { $gameClock.samples | ForEach-Object { $_ | Add-Member -NotePropertyName source -NotePropertyValue 'game' -PassThru -Force } })) + @($clock))
        }
        video = [ordered]@{
            file = 'video.mkv'; codec = 'h264'; encoder = $Encoder; width = 1920; height = 1080; fps = 60; cfr = $true; audio = $false
            capture = $captureMode; capture_rect = $rect; window_title = $(if ($hwnd -ne [IntPtr]::Zero) { [UePipeline.Win]::Title($hwnd) } else { $null })
            ffmpeg_command = $(if ($cap) { $cap.Command } else { $null }); ffmpeg_version = $ffmpegVersion
            start_estimate = $videoStart
        }
        video_start_offset_ns = $videoStartNs
        video_start_offset_definition = 't_ns of video frame 0 on the QPC ns clock of inputs.jsonl / telemetry.jsonl: video_time_s = (t_ns - video_start_offset_ns) / 1e9'
        system_audio = [ordered]@{ file = 'system_audio.mka'; codec = 'flac'; source = $(if ($audioClockInfo) { 'UE master submix (AutoPlay buffer listener, v1.4)' } else { 'UE master submix (StartRecordingOutput)' }); start_offset_ns = $audioStartNs; start_anchor = $audioAnchor; aligned = $audioAligned; clock = $audioClockInfo; stats = $audio }
        microphone = $null
        machine = [ordered]@{ cpu = 'AMD Ryzen 7 7700X'; gpu = 'NVIDIA GeForce RTX 4080'; display = $displayMode; display_refresh_hz = $refreshHz; os = [Environment]::OSVersion.VersionString }
        created_utc = (Get-Date).ToUniversalTime().ToString('o')
        status = $status
    }
    Write-JsonFile (Join-Path $runDir 'metadata.json') $metadata
    $validation = [ordered]@{ run_id = $runId; status = $status; problems = @($problems); warnings = @($warnings); checks = $checks; game_exit_code = $gameExit; killed = $killed }
    Write-JsonFile (Join-Path $runDir 'validation.json') $validation
    if ($status -in @('failed', 'gpu_crash')) { [System.IO.File]::WriteAllText((Join-Path $runDir 'FAILED'), (($problems -join "`n") + "`n"), $Utf8NoBom) }

    $files = [ordered]@{}
    foreach ($f in Get-ChildItem $runDir -Recurse -File | Where-Object { $_.Name -ne 'manifest.json' } | Sort-Object FullName) {
        $rel = $f.FullName.Substring($runDir.Length + 1).Replace('\', '/')
        $files[$rel] = [ordered]@{ sha256 = (Get-FileSha256 $f.FullName); bytes = $f.Length }
    }
    Write-JsonFile (Join-Path $runDir 'manifest.json') ([ordered]@{ schema = 'superposition.manifest/v1'; run_id = $runId; files = $files })

    $tEnd = Get-Date
    $row = [ordered]@{
        schema = 'superposition.ue-run/v1'; run_id = $runId; game = $Game; scenario = $Scenario; scenario_name = (Get-OutcomeValue $outcome 'scenario_name' 'level_name'); seed = $runSeed; skill = $runSkill
        build_commit = $buildInfo.commit; build_path = $Build; status = $status
        result = $metadata.result; score = $metadata.score; duration_s = $(if ($outcome) { $outcome.duration_s } else { $null })
        start = $tStart.ToString('o'); end = $tEnd.ToString('o'); wall_s = [math]::Round(($tEnd - $tStart).TotalSeconds, 1)
        capture = $captureMode; video_start_offset_ns = $videoStartNs
        dup_pct = $(if ($checks.Contains('video')) { $checks.video.dup_pct } else { $null })
        problems = @($problems); warnings = @($warnings); bundle = $runDir
    }
    Add-JsonLine (Join-Path $info.LogDir 'runs.jsonl') $row
    Write-Step ("{0}: {1} ({2}){3}" -f $runId, $status, $metadata.result, $(if ($problems.Count) { ' - ' + ($problems -join '; ') } else { '' }))
    [void]$results.Add($row)
    if ($status -eq 'gpu_crash' -and -not $gpuRetried.ContainsKey($i)) {
        $gpuRetried[$i] = $true
        Write-Step 'GPU crash (device lost): retrying this run once'
        $i--
    }
}
$results
if (@($results | Where-Object { $_.status -in @('failed', 'gpu_crash') }).Count -gt 0) { exit 1 }


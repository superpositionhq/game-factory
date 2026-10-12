<#
.SYNOPSIS
  Queue runner: build -> package -> smoke -> record N runs per scenario -> validate. See docs/ue-pipeline.md.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 stealth -Runs 3            # scenarios from the milestone tag
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 stealth -Scenarios 1,2 -Commit HEAD   (-Levels still works)
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 -Nightly                    # every game with a milestone/autoplay-* tag
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 -DrainQueue                 # requests written by enqueue.ps1

  Scenarios default to 1..n where milestone/autoplay-<n> ("scenarios 1..n are ready") is the newest such tag reachable
  from the commit; the commit defaults to the game's current branch tip (HEAD). Without -Force, scenarios that already have -Runs good runs
  (status ok/warn) of that commit are skipped, so a nightly run over an unchanged game does nothing.
  One summary row per invocation and game in .recording\<game>\pipeline.jsonl.
#>
param(
    [Parameter(Position = 0)][string]$Game,
    [int]$Runs = 3,
    [Alias('Levels')][string[]]$Scenarios,   # "1,2" from powershell -File arrives as one string; split below
    [string]$Commit = 'HEAD',
    [int]$MaxSeconds = 600,
    [switch]$Force,
    [switch]$Nightly,
    [switch]$DrainQueue
)

. (Join-Path $PSScriptRoot 'common.ps1')
$QueueDir = Join-Path $BuildsRoot '_queue'
if ($Nightly -or $DrainQueue) {
    # Unattended: keep a transcript (Task Scheduler / hidden drainer have no console anyone reads).
    $logs = Join-Path $BuildsRoot '_logs'
    New-Item -ItemType Directory -Force $logs | Out-Null
    Start-Transcript -Path (Join-Path $logs ('{0}-{1}.log' -f $(if ($Nightly) { 'nightly' } else { 'queue' }), (Get-Date -Format 'yyyyMMdd-HHmmss'))) | Out-Null
}

function Get-MilestoneScenarios([string]$Dir, [string]$Rev) {
    $tag = Invoke-Git $Dir @('describe', '--tags', '--abbrev=0', '--match', 'milestone/autoplay-*', $Rev) -AllowFail
    if ($LASTEXITCODE -ne 0 -or -not $tag) { return $null }
    $tag = "$tag".Trim()
    if ($tag -match 'milestone/autoplay-(\d+)$') { return [pscustomobject]@{ Tag = $tag; Scenarios = @(1..[int]$matches[1]) } }
    return $null
}

function Get-GoodRunCount([string]$GameSlug, [string]$Sha, [int]$Scenario) {
    $path = Join-Path (Join-Path $LogRoot $GameSlug) 'runs.jsonl'
    if (-not (Test-Path $path)) { return 0 }
    # runs.jsonl also holds event rows (mark-invalid.ps1: event "invalidated", no build_commit); invalidated runs don't count.
    $rows = @(foreach ($line in [System.IO.File]::ReadLines($path)) { try { $line | ConvertFrom-Json } catch { } })
    $invalid = @($rows | Where-Object { $_.PSObject.Properties.Name -contains 'event' -and $_.event -eq 'invalidated' } | ForEach-Object { $_.run_id })
    $n = 0
    foreach ($r in $rows) {
        $names = $r.PSObject.Properties.Name
        if ($names -notcontains 'build_commit' -or $names -notcontains 'status') { continue }
        if ($names -contains 'run_id' -and $r.run_id -in $invalid) { continue }
        if ($r.build_commit -eq $Sha -and $(if ($names -contains 'scenario') { $r.scenario } elseif ($names -contains 'level') { $r.level } else { $null }) -eq $Scenario -and $r.status -in @('ok', 'warn')) { $n++ }
    }
    return $n
}

function Test-SessionLocked {
    # Desktop Duplication cannot see a locked (secure) desktop; LogonUI runs while the session is locked.
    return [bool](Get-Process LogonUI -ErrorAction SilentlyContinue)
}

function Invoke-GamePipeline([string]$GameSlug, [int]$RunCount, [int[]]$ScenarioList, [string]$Rev, [string]$Trigger) {
    $info = Get-GameInfo $GameSlug
    $t0 = Get-Date
    $summary = [ordered]@{
        schema = 'superposition.ue-pipeline/v1'; game = $GameSlug; trigger = $Trigger; requested = $Rev
        start = $t0.ToString('o'); status = 'ok'; note = ''; build = $null; scenarios = @(); runs = @()
    }
    try {
        $sha = (Invoke-Git $info.Dir @('rev-parse', '--verify', "$Rev^{commit}")).Trim()
        $summary.commit = $sha
        if (-not $ScenarioList -or $ScenarioList.Count -eq 0) {
            $m = Get-MilestoneScenarios $info.Dir $sha
            if (-not $m) { $summary.status = 'skipped'; $summary.note = 'no milestone/autoplay-* tag reachable'; return $summary }
            $ScenarioList = $m.Scenarios; $summary.milestone = $m.Tag
        }
        $summary.scenarios = $ScenarioList
        $todo = @(foreach ($l in $ScenarioList) {
            $have = if ($Force) { 0 } else { Get-GoodRunCount $GameSlug $sha $l }
            if ($have -lt $RunCount) { [pscustomobject]@{ Scenario = $l; Runs = $RunCount - $have } }
        })
        if ($todo.Count -eq 0) { $summary.status = 'skipped'; $summary.note = "every scenario already has $RunCount good runs of $($sha.Substring(0, 8))"; return $summary }

        Write-Step "== $GameSlug $($sha.Substring(0, 8)): build + package + smoke"
        $build = & (Join-Path $PSScriptRoot 'build.ps1') $GameSlug -Commit $sha -Package -Smoke | Select-Object -Last 1
        $summary.build = [ordered]@{ status = $build.status; short_sha = $build.short_sha; output = $build.output_path; smoke = $build.smoke.status }
        if ($build.status -ne 'ok') { $summary.status = 'failed'; $summary.note = "build failed: $($build.error_excerpt)"; return $summary }

        foreach ($t in $todo) {
            if (Test-SessionLocked) { $summary.status = 'failed'; $summary.note = 'session locked: capture impossible'; break }
            Write-Step "== $GameSlug scenario $($t.Scenario): $($t.Runs) runs"
            $rows = & (Join-Path $PSScriptRoot 'record.ps1') $GameSlug -Build $build.output_path -Scenario $t.Scenario -Runs $t.Runs -MaxSeconds $MaxSeconds
            foreach ($r in @($rows | Where-Object { $_ -and $_.Contains('run_id') })) {
                $summary.runs += [ordered]@{ run_id = $r.run_id; scenario = $r.scenario; status = $r.status; result = $r.result }
            }
        }
        if (@($summary.runs | Where-Object { $_.status -in @('failed', 'gpu_crash') }).Count -gt 0 -and $summary.status -eq 'ok') { $summary.status = 'partial' }
    } catch {
        $summary.status = 'failed'; $summary.note = $_.Exception.Message
    } finally {
        $summary.end = (Get-Date).ToString('o')
        $summary.duration_s = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
        Add-JsonLine (Join-Path $info.LogDir 'pipeline.jsonl') $summary
        Write-Step "== $GameSlug pipeline: $($summary.status) $($summary.note)"
    }
    return $summary
}

# ---------------------------------------------------------------------------------------------------------------------

if ($DrainQueue) {
    # One drainer at a time (separate from the heavy-job lock, which build/record take per step).
    New-Item -ItemType Directory -Force (Join-Path $QueueDir 'done') | Out-Null
    try { $drainLock = [System.IO.File]::Open((Join-Path $QueueDir '_drainer.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch [System.IO.IOException] { Write-Step 'another queue drainer is running'; return }
    # This process keeps the pipeline.ps1/common.ps1 it started with (build.ps1/record.ps1 are re-read per call): when
    # either changes, hand over to a fresh drainer between jobs instead of running stale code.
    $codeFiles = @((Join-Path $PSScriptRoot 'pipeline.ps1'), (Join-Path $PSScriptRoot 'common.ps1'))
    $codeStamp = ($codeFiles | ForEach-Object { (Get-Item $_).LastWriteTimeUtc } | Measure-Object -Maximum).Maximum
    $handOver = $false
    try {
        while ($true) {
            if ((($codeFiles | ForEach-Object { (Get-Item $_).LastWriteTimeUtc } | Measure-Object -Maximum).Maximum) -gt $codeStamp) { $handOver = $true; break }
            $next = Get-ChildItem $QueueDir -Filter *.json -File | Where-Object { $_.Name -notlike '_*' } | Sort-Object Name | Select-Object -First 1
            if (-not $next) {
                # Queue empty: an idle-wait override (_idle-override.txt) stays (the user's standing "record now" is one),
                # unless it says "one_drain": true; that one is retired so idle waiting is the default again.
                $ov = Join-Path $QueueDir '_idle-override.txt'
                $ovData = if (Test-Path $ov) { Read-JsonFile $ov } else { $null }
                if ($ovData -and $ovData.PSObject.Properties.Name -contains 'one_drain' -and $ovData.one_drain -eq $true) {
                    Move-Item -Force $ov (Join-Path (Join-Path $QueueDir 'done') ("_idle-override-retired-{0}.txt" -f (Get-Date -Format 'yyyyMMdd-HHmmss')))
                    Write-Step 'queue empty: one-drain idle-wait override retired'
                }
                break
            }
            $req = Read-JsonFile $next.FullName
            # Recording priority for the whole job and the gap to the next one (see Start-RecordingWantsGpuHold).
            Start-RecordingWantsGpuHold "queue job $($next.Name)"
            $names = $req.PSObject.Properties.Name
            $levelsReq = if ($names -contains 'scenarios' -and $req.scenarios) { [int[]]$req.scenarios } elseif ($names -contains 'levels' -and $req.levels) { [int[]]$req.levels } else { $null }
            $res = Invoke-GamePipeline $req.game ([int]$req.runs) $levelsReq $req.commit "queue:$($req.requested_by)"
            $req | Add-Member -NotePropertyName result -NotePropertyValue $res -Force
            Write-JsonFile (Join-Path (Join-Path $QueueDir 'done') $next.Name) $req
            Remove-Item $next.FullName
        }
    } finally {
        # On hand-over the flag stays (under a minute old); the next drainer takes it over.
        if (-not $handOver) { Stop-RecordingWantsGpuHold }
        $drainLock.Dispose()
    }
    if ($handOver) {
        Write-Step 'pipeline code changed: handing the queue over to a fresh drainer'
        Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-DrainQueue') | Out-Null
    }
    return
}

if ($Nightly) {
    $games = Get-ChildItem $GamesRoot -Directory | Where-Object { $_.Name -notlike '_*' -and (Test-Path (Join-Path $_.FullName '.git')) }
    $results = foreach ($g in $games) {
        if (-not (Get-MilestoneScenarios $g.FullName 'HEAD')) { Write-Step "$($g.Name): no milestone/autoplay-* tag, skipped"; continue }
        Invoke-GamePipeline $g.Name $Runs $null 'HEAD' 'nightly'
    }
    $results
    return
}

if (-not $Game) { throw 'give a game, -Nightly or -DrainQueue' }
$scenarioList = @($Scenarios | ForEach-Object { $_ -split ',' } | Where-Object { $_ } | ForEach-Object { [int]$_ })
Invoke-GamePipeline $Game $Runs $scenarioList $Commit 'manual'

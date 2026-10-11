<#
.SYNOPSIS
  Queue runner: build -> package -> smoke -> record N runs per level -> validate. See docs/ue-pipeline.md.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 stealth -Runs 3            # levels from the milestone tag
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 stealth -Levels 1,2 -Commit HEAD
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 -Nightly                    # every game with a milestone/autoplay-* tag
  powershell -ExecutionPolicy Bypass -File pipeline.ps1 -DrainQueue                 # requests written by enqueue.ps1

  Levels default to 1..n where milestone/autoplay-<n> is the newest such tag reachable from the commit; the commit
  defaults to the game's current branch tip (HEAD). Without -Force, levels that already have -Runs good runs
  (status ok/warn) of that commit are skipped, so a nightly run over an unchanged game does nothing.
  One summary row per invocation and game in .recording\<game>\pipeline.jsonl.
#>
param(
    [Parameter(Position = 0)][string]$Game,
    [int]$Runs = 3,
    [int[]]$Levels,
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

function Get-MilestoneLevels([string]$Dir, [string]$Rev) {
    $tag = Invoke-Git $Dir @('describe', '--tags', '--abbrev=0', '--match', 'milestone/autoplay-*', $Rev) -AllowFail
    if ($LASTEXITCODE -ne 0 -or -not $tag) { return $null }
    $tag = "$tag".Trim()
    if ($tag -match 'milestone/autoplay-(\d+)$') { return [pscustomobject]@{ Tag = $tag; Levels = @(1..[int]$matches[1]) } }
    return $null
}

function Get-GoodRunCount([string]$GameSlug, [string]$Sha, [int]$Level) {
    $path = Join-Path (Join-Path $LogRoot $GameSlug) 'runs.jsonl'
    if (-not (Test-Path $path)) { return 0 }
    $n = 0
    foreach ($line in [System.IO.File]::ReadLines($path)) {
        try { $r = $line | ConvertFrom-Json } catch { continue }
        if ($r.build_commit -eq $Sha -and $r.level -eq $Level -and $r.status -in @('ok', 'warn')) { $n++ }
    }
    return $n
}

function Test-SessionLocked {
    # Desktop Duplication cannot see a locked (secure) desktop; LogonUI runs while the session is locked.
    return [bool](Get-Process LogonUI -ErrorAction SilentlyContinue)
}

function Invoke-GamePipeline([string]$GameSlug, [int]$RunCount, [int[]]$LevelList, [string]$Rev, [string]$Trigger) {
    $info = Get-GameInfo $GameSlug
    $t0 = Get-Date
    $summary = [ordered]@{
        schema = 'superposition.ue-pipeline/v1'; game = $GameSlug; trigger = $Trigger; requested = $Rev
        start = $t0.ToString('o'); status = 'ok'; note = ''; build = $null; levels = @(); runs = @()
    }
    try {
        $sha = (Invoke-Git $info.Dir @('rev-parse', '--verify', "$Rev^{commit}")).Trim()
        $summary.commit = $sha
        if (-not $LevelList -or $LevelList.Count -eq 0) {
            $m = Get-MilestoneLevels $info.Dir $sha
            if (-not $m) { $summary.status = 'skipped'; $summary.note = 'no milestone/autoplay-* tag reachable'; return $summary }
            $LevelList = $m.Levels; $summary.milestone = $m.Tag
        }
        $summary.levels = $LevelList
        $todo = @(foreach ($l in $LevelList) {
            $have = if ($Force) { 0 } else { Get-GoodRunCount $GameSlug $sha $l }
            if ($have -lt $RunCount) { [pscustomobject]@{ Level = $l; Runs = $RunCount - $have } }
        })
        if ($todo.Count -eq 0) { $summary.status = 'skipped'; $summary.note = "every level already has $RunCount good runs of $($sha.Substring(0, 8))"; return $summary }

        Write-Step "== $GameSlug $($sha.Substring(0, 8)): build + package + smoke"
        $build = & (Join-Path $PSScriptRoot 'build.ps1') $GameSlug -Commit $sha -Package -Smoke | Select-Object -Last 1
        $summary.build = [ordered]@{ status = $build.status; short_sha = $build.short_sha; output = $build.output_path; smoke = $build.smoke.status }
        if ($build.status -ne 'ok') { $summary.status = 'failed'; $summary.note = "build failed: $($build.error_excerpt)"; return $summary }

        foreach ($t in $todo) {
            if (Test-SessionLocked) { $summary.status = 'failed'; $summary.note = 'session locked: capture impossible'; break }
            Write-Step "== $GameSlug level $($t.Level): $($t.Runs) runs"
            $rows = & (Join-Path $PSScriptRoot 'record.ps1') $GameSlug -Build $build.output_path -Level $t.Level -Runs $t.Runs -MaxSeconds $MaxSeconds
            foreach ($r in @($rows | Where-Object { $_ -and $_.Contains('run_id') })) {
                $summary.runs += [ordered]@{ run_id = $r.run_id; level = $r.level; status = $r.status; result = $r.result }
            }
        }
        if (@($summary.runs | Where-Object { $_.status -eq 'failed' }).Count -gt 0 -and $summary.status -eq 'ok') { $summary.status = 'partial' }
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
    try {
        while ($true) {
            $next = Get-ChildItem $QueueDir -Filter *.json -File | Sort-Object Name | Select-Object -First 1
            if (-not $next) { break }
            $req = Read-JsonFile $next.FullName
            $levelsReq = if ($req.levels) { [int[]]$req.levels } else { $null }
            $res = Invoke-GamePipeline $req.game ([int]$req.runs) $levelsReq $req.commit "queue:$($req.requested_by)"
            $req | Add-Member -NotePropertyName result -NotePropertyValue $res -Force
            Write-JsonFile (Join-Path (Join-Path $QueueDir 'done') $next.Name) $req
            Remove-Item $next.FullName
        }
    } finally { $drainLock.Dispose() }
    return
}

if ($Nightly) {
    $games = Get-ChildItem $GamesRoot -Directory | Where-Object { $_.Name -notlike '_*' -and (Test-Path (Join-Path $_.FullName '.git')) }
    $results = foreach ($g in $games) {
        if (-not (Get-MilestoneLevels $g.FullName 'HEAD')) { Write-Step "$($g.Name): no milestone/autoplay-* tag, skipped"; continue }
        Invoke-GamePipeline $g.Name $Runs $null 'HEAD' 'nightly'
    }
    $results
    return
}

if (-not $Game) { throw 'give a game, -Nightly or -DrainQueue' }
Invoke-GamePipeline $Game $Runs $Levels $Commit 'manual'

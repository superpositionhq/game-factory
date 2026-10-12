<#
.SYNOPSIS
  Queue a pipeline run for a game and return at once (for game sessions). A hidden drainer process works through
  the queue one request at a time; results land in builds\_queue\done\ and .recording\<game>\pipeline.jsonl.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File %GF_ROOT%\game-factory\tools\ue-pipeline\enqueue.ps1 stealth -Runs 2
  powershell -ExecutionPolicy Bypass -File ...\enqueue.ps1 stealth -Scenarios 1 -Runs 1 -Commit HEAD -RequestedBy ue-stealth
  ... -MaxSeconds "1=300,2=600,3=900"     # per-scenario AutoPlay time limit (s); a plain number applies to every
                                          # scenario; unlisted scenarios keep the default 600
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [int]$Runs = 2,
    [Alias('Levels')][string[]]$Scenarios,   # "1,2" from powershell -File arrives as one string
    [string]$Commit = 'HEAD',
    [string]$RequestedBy = 'unknown',
    [string]$MaxSeconds,   # "900" or "1=300,3=900" (see pipeline.ps1 -MaxSeconds)
    [switch]$Force   # queue anyway although the requester is not the coordinator
)

. (Join-Path $PSScriptRoot 'common.ps1')
# The coordinator owns the queue (user's decision 2026-10-11: one GPU recording at a time, coordinator orders them).
if ($RequestedBy -ne 'coordinator' -and -not $Force) {
    Write-Host ''
    Write-Host '!!! NOT QUEUED: only the coordinator queues recordings now (-RequestedBy coordinator).' -ForegroundColor Red
    Write-Host "!!! Ask the coordinating session to queue $Game (commit $Commit, scenarios $($Scenarios -join ','), runs $Runs)." -ForegroundColor Red
    Write-Host '!!! (-Force queues anyway; it is logged with your -RequestedBy.)' -ForegroundColor Red
    exit 2
}
$info = Get-GameInfo $Game
$maxMap = ConvertTo-MaxSecondsMap $MaxSeconds   # validates now, so a typo fails here and not in the drainer
$sha = (Invoke-Git $info.Dir @('rev-parse', '--verify', "$Commit^{commit}")).Trim()   # pin the commit now
$queue = Join-Path $BuildsRoot '_queue'
New-Item -ItemType Directory -Force $queue | Out-Null
$name = '{0}-{1}-{2}.json' -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'), $Game, $sha.Substring(0, 8)
$req = [ordered]@{ game = $Game; commit = $sha; runs = $Runs; scenarios = @($Scenarios | ForEach-Object { $_ -split ',' } | Where-Object { $_ } | ForEach-Object { [int]$_ }); requested_by = $RequestedBy; requested_at = (Get-IsoNow) }
if ($MaxSeconds) { $req.max_seconds = $maxMap }
Write-JsonFile (Join-Path $queue $name) $req

if (Test-Path (Join-Path $queue '_paused.txt')) {
    Write-Step "queued $name, but the queue is PAUSED ($((Get-Content (Join-Path $queue '_paused.txt') -TotalCount 1))); it starts when _paused.txt is removed and a drainer runs"
    exit 0
}
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
    "`"$(Join-Path $PSScriptRoot 'pipeline.ps1')`"", '-DrainQueue')
Write-Step "queued $name (builds\_queue); results: .recording\$Game\pipeline.jsonl and builds\_queue\done\$name"

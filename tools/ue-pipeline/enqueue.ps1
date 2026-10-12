<#
.SYNOPSIS
  Queue a pipeline run for a game and return at once (for game sessions). A hidden drainer process works through
  the queue one request at a time; results land in builds\_queue\done\ and .recording\<game>\pipeline.jsonl.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File %GF_ROOT%\game-factory\tools\ue-pipeline\enqueue.ps1 stealth -Runs 2
  powershell -ExecutionPolicy Bypass -File ...\enqueue.ps1 stealth -Scenarios 1 -Runs 1 -Commit HEAD -RequestedBy ue-stealth
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [int]$Runs = 2,
    [Alias('Levels')][string[]]$Scenarios,   # "1,2" from powershell -File arrives as one string
    [string]$Commit = 'HEAD',
    [string]$RequestedBy = 'unknown',
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
$sha = (Invoke-Git $info.Dir @('rev-parse', '--verify', "$Commit^{commit}")).Trim()   # pin the commit now
$queue = Join-Path $BuildsRoot '_queue'
New-Item -ItemType Directory -Force $queue | Out-Null
$name = '{0}-{1}-{2}.json' -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'), $Game, $sha.Substring(0, 8)
$req = [ordered]@{ game = $Game; commit = $sha; runs = $Runs; scenarios = @($Scenarios | ForEach-Object { $_ -split ',' } | Where-Object { $_ } | ForEach-Object { [int]$_ }); requested_by = $RequestedBy; requested_at = (Get-IsoNow) }
Write-JsonFile (Join-Path $queue $name) $req

Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
    "`"$(Join-Path $PSScriptRoot 'pipeline.ps1')`"", '-DrainQueue')
Write-Step "queued $name (builds\_queue); results: .recording\$Game\pipeline.jsonl and builds\_queue\done\$name"

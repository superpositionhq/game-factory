<#
.SYNOPSIS
  Queue a pipeline run for a game and return at once (for game sessions). A hidden drainer process works through
  the queue one request at a time; results land in builds\_queue\done\ and .recording\<game>\pipeline.jsonl.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\Users\Xiang\Work\game-factory\tools\ue-pipeline\enqueue.ps1 stealth -Runs 2
  powershell -ExecutionPolicy Bypass -File ...\enqueue.ps1 stealth -Levels 1 -Runs 1 -Commit HEAD -RequestedBy ue-stealth
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [int]$Runs = 2,
    [int[]]$Levels,
    [string]$Commit = 'HEAD',
    [string]$RequestedBy = 'unknown'
)

. (Join-Path $PSScriptRoot 'common.ps1')
$info = Get-GameInfo $Game
$sha = (Invoke-Git $info.Dir @('rev-parse', '--verify', "$Commit^{commit}")).Trim()   # pin the commit now
$queue = Join-Path $BuildsRoot '_queue'
New-Item -ItemType Directory -Force $queue | Out-Null
$name = '{0}-{1}-{2}.json' -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'), $Game, $sha.Substring(0, 8)
$req = [ordered]@{ game = $Game; commit = $sha; runs = $Runs; levels = $Levels; requested_by = $RequestedBy; requested_at = (Get-IsoNow) }
Write-JsonFile (Join-Path $queue $name) $req

Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
    "`"$(Join-Path $PSScriptRoot 'pipeline.ps1')`"", '-DrainQueue')
Write-Step "queued $name (builds\_queue); results: .recording\$Game\pipeline.jsonl and builds\_queue\done\$name"

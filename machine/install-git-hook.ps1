<#
.SYNOPSIS
  Add the commit recorder and the live creation replay to a game repo's post-commit hook (idempotent).
.DESCRIPTION
  Appends one line to <repo>\.git\hooks\post-commit that runs <hooks dir>\record-commit.ps1, which writes every new
  commit to <root>\.recording\<repo name>\commits.jsonl. Git LFS's own post-commit lines stay first: when the hook does
  not exist yet, `git lfs update` creates it before the line is appended. A repo whose hook already calls
  record-commit.ps1 is left alone (pass -Force to rewrite the line, e.g. after moving the hooks dir). A second line runs
  this checkout's tools\ue-replay\live-hook.ps1, which does nothing unless the repo's ReplayConfig.json has "live": true
  (docs/ue-replay.md, "Live replay"); it is added to hooks that lack it.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File machine\install-git-hook.ps1 %GF_ROOT%\games\stealth
#>
param(
    [Parameter(Mandatory = $true)][string]$Repo,
    [string]$HooksDir = (Join-Path $env:USERPROFILE '.claude\hooks'),   # where bootstrap.ps1 installed record-commit.ps1
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path -LiteralPath $Repo).Path
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) { throw "not a git repo (no .git): $Repo" }
$hookPath = (& git -C $Repo rev-parse --git-path hooks/post-commit)
if (-not [IO.Path]::IsPathRooted($hookPath)) { $hookPath = Join-Path $Repo $hookPath }
$hookPath = [IO.Path]::GetFullPath($hookPath)
New-Item -ItemType Directory -Force (Split-Path $hookPath) | Out-Null

$usesLfs = (Test-Path -LiteralPath (Join-Path $Repo '.gitattributes')) -and
    ((Get-Content -LiteralPath (Join-Path $Repo '.gitattributes') -Raw) -match 'filter=lfs')
if (-not (Test-Path -LiteralPath $hookPath) -and $usesLfs) {
    & git -C $Repo lfs update 2>&1 | Out-Null   # writes LFS's pre-push / post-checkout / post-commit / post-merge hooks
}

$script = ($HooksDir -replace '\\', '/').TrimEnd('/') + '/record-commit.ps1'
$line = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`" `"`$(pwd -W 2>/dev/null || pwd)`" >/dev/null 2>&1 || true"
$marker = '# recording: append this commit to <root>/.recording/<repo>/commits.jsonl (machine/install-git-hook.ps1)'

# The live creation replay (tools/ue-replay/live-hook.ps1) runs only for a repo whose ReplayConfig.json has "live": true;
# its output (the replay's findings for the game session) is meant to be seen, so it is not silenced.
$liveHook = ((Split-Path $PSScriptRoot -Parent) -replace '\\', '/') + '/tools/ue-replay/live-hook.ps1'
$liveLine = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$liveHook`" `"`$(pwd -W 2>/dev/null || pwd)`" || true"
$liveMarker = '# live replay: per-commit creation replay when ReplayConfig.json has "live": true (machine/install-git-hook.ps1)'

$text = if (Test-Path -LiteralPath $hookPath) { [IO.File]::ReadAllText($hookPath) } else { "#!/bin/sh`n" }
$text = $text -replace "`r`n", "`n"
$hasRec = $text -match 'record-commit\.ps1'
$hasLive = $text -match 'live-hook\.ps1'
if ($hasRec -and $hasLive -and -not $Force) { Write-Host "post-commit already records commits and starts the live replay: $hookPath"; return }
if ($Force) {
    # drop the old recorder and live-replay lines (and their comments), keep everything else
    $text = (($text -split "`n") | Where-Object { $_ -notmatch 'record-commit\.ps1|live-hook\.ps1' -and $_ -notmatch '^# .*recording|^# live replay' }) -join "`n"
    $hasRec = $false; $hasLive = $false
}
if (-not $text.EndsWith("`n")) { $text += "`n" }
if (-not $hasRec) { $text += "$marker`n$line`n" }
if (-not $hasLive) { $text += "$liveMarker`n$liveLine`n" }
[IO.File]::WriteAllText($hookPath, $text, (New-Object Text.UTF8Encoding($false)))
Write-Host "post-commit records commits via $script and starts the live replay via $liveHook : $hookPath"

<#
.SYNOPSIS
  post-commit hook of a live game: show the creation replay's last findings once, start the per-commit replay job.
.DESCRIPTION
  Installed by machine/install-git-hook.ps1. Does nothing unless the repo's ReplayConfig.json has "live": true, and
  nothing for a commit on the orphan `tasks` branch (the game's tasks are not part of the replayed history).
  Returns at once: the job (`ue_replay.py live --game <slug>`, docs/ue-replay.md section 3) runs detached at
  below-normal priority, takes engine slots only through ue-heavy.ps1 -Low, and catches up with every commit made
  while it runs. Its findings land in <work_root>\work\live\feedback.md; this hook prints them at the next commit.
  Python: $env:GF_PYTHON, else python on PATH, else the py launcher.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File <root>\game-factory\tools\ue-replay\live-hook.ps1 <root>\games\<slug>
#>
param([Parameter(Mandatory = $true)][string]$Repo)
$ErrorActionPreference = 'Stop'
try {
    if ((git -C $Repo symbolic-ref --short -q HEAD) -eq 'tasks') { exit 0 }   # the tasks branch is not game history
    $cfgPath = Join-Path $Repo 'ReplayConfig.json'
    if (-not (Test-Path -LiteralPath $cfgPath)) { exit 0 }
    $cfg = [IO.File]::ReadAllText($cfgPath) | ConvertFrom-Json
    if (-not ($cfg.PSObject.Properties['live'] -and $cfg.live)) { exit 0 }
    $gf = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent      # the game-factory checkout
    . (Join-Path $gf 'machine\lib\gf-root.ps1')
    $root = Get-GFRoot
    $workRoot = ([string]$cfg.work_root).Replace('{root}', $root).Replace('/', '\')
    $live = Join-Path $workRoot 'work\live'
    New-Item -ItemType Directory -Force $live | Out-Null

    # 1. the last finished job's findings, once
    $fb = Join-Path $live 'feedback.md'
    $shown = Join-Path $live 'feedback.shown'
    if ((Test-Path -LiteralPath $fb) -and (-not (Test-Path -LiteralPath $shown) -or
            (Get-Item -LiteralPath $fb).LastWriteTime -gt (Get-Item -LiteralPath $shown).LastWriteTime)) {
        $lines = @(Get-Content -LiteralPath $fb -Encoding UTF8)
        Write-Host ("[replay] " + ($lines[0] -replace '^#\s*', ''))
        $lines | Select-Object -Skip 1 | Where-Object { $_ -match '^- ' } | Select-Object -First 12 | ForEach-Object { Write-Host "  $_" }
        Write-Host "  (all of it: $fb)"
        Set-Content -LiteralPath $shown -Value (Get-Date -Format o) -Encoding ASCII
    }

    # 2. start the job unless one runs (it takes the new commit before it exits)
    $lock = Join-Path $live 'lock'
    if (Test-Path -LiteralPath $lock) {
        try { $owner = [int](([IO.File]::ReadAllText($lock) | ConvertFrom-Json).pid) } catch { $owner = 0 }
        if ($owner -and (Get-Process -Id $owner -ErrorAction SilentlyContinue)) { exit 0 }
    }
    $py = $env:GF_PYTHON
    if (-not $py) { $c = Get-Command python -ErrorAction SilentlyContinue; if ($c) { $py = $c.Source } }
    $pyArgs = @()
    if (-not $py) { $c = Get-Command py -ErrorAction SilentlyContinue; if ($c) { $py = $c.Source; $pyArgs = @('-3') } }
    if (-not $py) { Write-Host '[replay] no Python found (set GF_PYTHON): live replay not started'; exit 0 }
    $script = Join-Path $PSScriptRoot 'ue_replay.py'
    $log = Join-Path $live 'job.log'
    $argLine = (($pyArgs + @('-I', '-B', "`"$script`"", 'live', '--game', "`"$cfgPath`"", '--log', "`"$log`"")) -join ' ')
    $p = Start-Process -FilePath $py -ArgumentList $argLine -WindowStyle Hidden -PassThru
    try { $p.PriorityClass = [Diagnostics.ProcessPriorityClass]::BelowNormal } catch { }
} catch {
    Write-Host "[replay] live hook: $($_.Exception.Message)"
}
exit 0

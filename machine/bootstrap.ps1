<#
.SYNOPSIS
  Set up a Windows machine for game-factory sessions (idempotent: run it again any time; it only changes what differs).
.DESCRIPTION
  1. Machine root and config: writes %USERPROFILE%\.game-factory\config.json (root, ueb, engine, and the job slots
     heavy_slots / gpu_slots computed from the hardware by lib\gf-root.ps1 Get-GFComputedSlots, recorded in slots_auto;
     values set by hand stay unless -Force) and creates the Work layout under the root (games, builds\_queue,
     builds\_logs, recordings, .recording, deliverables, asset-library, tools) plus <ueb>\src and <ueb>\tmp.
  2. Tools: <root>\tools\ue-heavy.ps1 (+ gf-root.ps1), <root>\tools\asset-scout\, and the pinned ffmpeg
     (machine\get-ffmpeg.ps1, downloaded and SHA-256 verified, never committed).
  3. Claude Code: the recording hooks into <ClaudeDir>\hooks\, their entries merged into <ClaudeDir>\settings.json
     (backup settings.json.bak-<time> first; other settings and hooks are kept), the repo's skills into
     <ClaudeDir>\skills\, and <root>\CLAUDE.md importing game-factory\CLAUDE.md (sessions start in the root).
  4. Git: git-lfs filters (git lfs install --skip-repo), gh login check, the commit recorder in every
     <root>\games\*\.git (machine\install-git-hook.ps1); -CloneGames clones every <Org>/game-* repo first.
  Any file it replaces is copied to a backup first (<root>\tools\_backup\<time>\, <ClaudeDir>\hooks\_backup\<time>\,
  <ClaudeDir>\skills\_backup\<time>\). It never pushes, never changes Windows settings and never signs in for you.
  Then run machine\check.ps1. Manual steps (Epic/Fab sign-in, gh login, display sleep): docs\new-machine.md.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File machine\bootstrap.ps1
  powershell -ExecutionPolicy Bypass -File machine\bootstrap.ps1 -Root D:\Work -CloneGames
  # scratch test that leaves the real profile alone:
  powershell -ExecutionPolicy Bypass -File machine\bootstrap.ps1 -Root C:\gf-test\Work -Ueb C:\gf-test\UEB `
      -ClaudeDir C:\gf-test\home\.claude -ConfigPath C:\gf-test\home\.game-factory\config.json -FfmpegArchive <.7z>
#>
param(
    [string]$Root,                                              # default: GF_ROOT / existing config / %USERPROFILE%\Work
    [string]$Ueb,                                               # default: config / C:\UEB
    [string]$Engine,                                            # default: config / C:\Program Files\Epic Games\UE_5.7 (new games)
    [string]$ClaudeDir = (Join-Path $env:USERPROFILE '.claude'),
    [string]$ConfigPath,                                        # default: GF_CONFIG / %USERPROFILE%\.game-factory\config.json
    [string]$FfmpegArchive,                                     # a downloaded ffmpeg-8.1.2-full_build.7z (still verified)
    [switch]$SkipFfmpeg,
    [switch]$CloneGames,
    [string]$Org = 'superpositionhq',
    [switch]$Force                                              # also replace heavy_slots / gpu_slots someone set by hand
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'lib\gf-root.ps1')
if ($ConfigPath) { $env:GF_CONFIG = $ConfigPath }
if ($Root) { $env:GF_ROOT = $Root }      # this process (and the scripts it starts) use the chosen root
$cfg = Get-GFConfig
$Root = $cfg.root
if (-not $Ueb) { $Ueb = $cfg.ueb }
if (-not $Engine) { $Engine = $cfg.engine }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$utf8 = New-Object Text.UTF8Encoding($false)
$report = New-Object Collections.Generic.List[object]

function Note([string]$Status, [string]$What, [string]$Detail = '') {
    $report.Add([pscustomobject]@{ status = $Status; what = $What; detail = $Detail })
    $color = @{ ok = 'DarkGray'; added = 'Green'; changed = 'Cyan'; warn = 'Yellow'; skip = 'DarkGray' }[$Status]
    Write-Host ("  [{0,-7}] {1}{2}" -f $Status, $What, $(if ($Detail) { " - $Detail" } else { '' })) -ForegroundColor $color
}

function Get-Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }

# Copy $Src to $Dst unless identical; a different existing $Dst goes to $BackupDir first.
function Sync-File([string]$Src, [string]$Dst, [string]$BackupDir, [string]$What) {
    New-Item -ItemType Directory -Force (Split-Path $Dst) | Out-Null
    if (Test-Path -LiteralPath $Dst) {
        if ((Get-Hash $Src) -eq (Get-Hash $Dst)) { Note ok $What; return }
        New-Item -ItemType Directory -Force $BackupDir | Out-Null
        Copy-Item -LiteralPath $Dst (Join-Path $BackupDir (Split-Path $Dst -Leaf)) -Force
        Copy-Item -LiteralPath $Src $Dst -Force
        Note changed $What "previous copy in $BackupDir"
    } else {
        Copy-Item -LiteralPath $Src $Dst -Force
        Note added $What
    }
}

function Sync-Dir([string]$SrcDir, [string]$DstDir, [string]$BackupDir, [string]$What) {
    $files = Get-ChildItem -LiteralPath $SrcDir -Recurse -File | Where-Object { $_.FullName -notmatch '\\__pycache__\\' }
    $before = $report.Count
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($SrcDir.TrimEnd('\').Length + 1)
        Sync-File $f.FullName (Join-Path $DstDir $rel) (Join-Path $BackupDir (Split-Path $rel)) "$What\$rel"
    }
    # collapse unchanged per-file rows into one line
    $rows = @($report.GetRange($before, $report.Count - $before))
    if (@($rows | Where-Object { $_.status -ne 'ok' }).Count -eq 0) {
        $report.RemoveRange($before, $report.Count - $before)
        Note ok $What "$($rows.Count) files up to date"
    }
}

function Write-JsonFile([string]$Path, $Object) {
    New-Item -ItemType Directory -Force (Split-Path $Path) | Out-Null
    [IO.File]::WriteAllText($Path, ($Object | ConvertTo-Json -Depth 32) + "`n", $utf8)
}

Write-Host "game-factory bootstrap: root $Root, repo $repo, Claude dir $ClaudeDir"

# --- 1. config + layout -------------------------------------------------------------------------------------------
Write-Host "1. config and layout"
$cfgPath = Get-GFConfigPath
$want = [ordered]@{ root = $Root; ueb = $Ueb; engine = $Engine; record_extra_projects = @($cfg.record_extra_projects) }
$have = if (Test-Path -LiteralPath $cfgPath) { [IO.File]::ReadAllText($cfgPath) | ConvertFrom-Json } else { $null }
$same = $have -and ($have.root -eq $want.root) -and ($have.ueb -eq $want.ueb) -and ($have.engine -eq $want.engine) -and
    ((@($have.record_extra_projects) -join '|') -eq (@($want.record_extra_projects) -join '|'))
if ($same) { Note ok "config $cfgPath" }
else {
    if ($have) {
        foreach ($p in $have.PSObject.Properties) { if (-not $want.Contains($p.Name)) { $want[$p.Name] = $p.Value } }   # keep extra keys
        Copy-Item -LiteralPath $cfgPath "$cfgPath.bak-$stamp"
    }
    Write-JsonFile $cfgPath $want
    Note $(if ($have) { 'changed' } else { 'added' }) "config $cfgPath" "root=$Root ueb=$Ueb"
}
# Job slots from the hardware (lib\gf-root.ps1 Get-GFComputedSlots; ue-heavy.ps1 and the pipeline read the config).
# The computed values are recorded in slots_auto; a heavy_slots / gpu_slots that differs from it was set by hand and
# stays unless -Force.
$hw = Get-GFHardware
$calc = Get-GFComputedSlots $hw
$now = [IO.File]::ReadAllText($cfgPath) | ConvertFrom-Json
$auto = if ($now.PSObject.Properties['slots_auto']) { $now.slots_auto } else { $null }
$next = [ordered]@{}
foreach ($p in $now.PSObject.Properties) { $next[$p.Name] = $p.Value }
$kept = @()
foreach ($k in 'heavy_slots', 'gpu_slots') {
    $cur = if ($now.PSObject.Properties[$k]) { [int]$now.$k } else { 0 }
    $byHand = $cur -gt 0 -and -not ($auto -and $auto.PSObject.Properties[$k] -and [int]$auto.$k -eq $cur)
    if ($byHand -and -not $Force) { $kept += "$k=$cur (set by hand; computed $($calc.$k))"; continue }
    $next[$k] = $calc.$k
}
$next['slots_auto'] = [ordered]@{
    heavy_slots = $calc.heavy_slots; gpu_slots = $calc.gpu_slots
    basis = "logical cores $($hw.logical_cores), RAM $($hw.ram_gb) GB, commit limit $($hw.commit_gb) GB, $($hw.gpu_count) NVIDIA GPU(s), largest $($hw.vram_mb) MB VRAM"
}
$before = ($now | ConvertTo-Json -Depth 32 -Compress)
$after = ([pscustomobject]$next | ConvertTo-Json -Depth 32 -Compress)
if ($before -ne $after) {
    Copy-Item -LiteralPath $cfgPath "$cfgPath.bak-$stamp" -Force
    Write-JsonFile $cfgPath $next
    Note changed 'job slots' ("heavy_slots={0} gpu_slots={1} ({2})" -f $next['heavy_slots'], $next['gpu_slots'], $next['slots_auto'].basis)
} else { Note ok 'job slots' ("heavy_slots={0} gpu_slots={1}" -f $next['heavy_slots'], $next['gpu_slots']) }
if ($kept) { Note warn 'job slots set by hand' (($kept -join '; ') + '; -Force replaces them') }

$dirs = @('games', 'builds', 'builds\_queue', 'builds\_logs', 'recordings', '.recording', 'deliverables', 'asset-library', 'tools') |
    ForEach-Object { Join-Path $Root $_ }
$dirs += @((Join-Path $Ueb 'src'), (Join-Path $Ueb 'tmp'))
$new = @($dirs | Where-Object { -not (Test-Path -LiteralPath $_) })
foreach ($d in $new) { New-Item -ItemType Directory -Force $d | Out-Null }
Note $(if ($new.Count) { 'added' } else { 'ok' }) 'Work layout' $(if ($new.Count) { "created $($new.Count) folder(s)" } else { "$($dirs.Count) folders present" })
$expectedRepo = Join-Path $Root 'game-factory'
if ([IO.Path]::GetFullPath($repo).TrimEnd('\') -ne $expectedRepo) {
    Note warn 'repo location' "this clone is $repo; docs and briefs assume $expectedRepo (clone it there, or keep this and expect path notes to differ)"
} else { Note ok 'repo location' $repo }

# --- 2. tools ------------------------------------------------------------------------------------------------------
Write-Host "2. tools"
$toolsBackup = Join-Path $Root "tools\_backup\$stamp"
Sync-File (Join-Path $PSScriptRoot 'tools\ue-heavy.ps1') (Join-Path $Root 'tools\ue-heavy.ps1') $toolsBackup 'tools\ue-heavy.ps1'
Sync-File (Join-Path $PSScriptRoot 'lib\gf-root.ps1') (Join-Path $Root 'tools\gf-root.ps1') $toolsBackup 'tools\gf-root.ps1'
Sync-Dir (Join-Path $PSScriptRoot 'asset-scout') (Join-Path $Root 'tools\asset-scout') (Join-Path $toolsBackup 'asset-scout') 'tools\asset-scout'
Sync-File (Join-Path $PSScriptRoot 'lib\gfroot.py') (Join-Path $Root 'tools\asset-scout\gfroot.py') (Join-Path $toolsBackup 'asset-scout') 'tools\asset-scout\gfroot.py'
if ($SkipFfmpeg) { Note skip 'ffmpeg' '-SkipFfmpeg' }
else {
    $fa = @{ Root = $Root }; if ($FfmpegArchive) { $fa.Archive = $FfmpegArchive }
    $had = Test-Path -LiteralPath (Join-Path $Root 'tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe')
    $out = @(& (Join-Path $PSScriptRoot 'get-ffmpeg.ps1') @fa 6>&1)
    Note $(if ($had) { 'ok' } else { 'added' }) 'ffmpeg 8.1.2 (pinned, SHA-256 verified)' ([string]($out | Select-Object -Last 1))
}

# --- 3. Claude Code: hooks, settings, skills, CLAUDE.md --------------------------------------------------------------
Write-Host "3. Claude Code"
$hooksDir = Join-Path $ClaudeDir 'hooks'
$hooksBackup = Join-Path $hooksDir "_backup\$stamp"
foreach ($f in 'record-action.ps1', 'record-commit.ps1') {
    Sync-File (Join-Path $PSScriptRoot "hooks\$f") (Join-Path $hooksDir $f) $hooksBackup "hooks\$f"
}
Sync-File (Join-Path $PSScriptRoot 'lib\gf-root.ps1') (Join-Path $hooksDir 'gf-root.ps1') $hooksBackup 'hooks\gf-root.ps1'
$excl = Join-Path $hooksDir 'recording-exclude.txt'
if (Test-Path -LiteralPath $excl) { Note ok 'hooks\recording-exclude.txt' 'kept as is' }
else { Copy-Item (Join-Path $PSScriptRoot 'hooks\recording-exclude.txt') $excl; Note added 'hooks\recording-exclude.txt' 'add the coordinator session id to it' }
$map = Join-Path $hooksDir 'recording-sessions.json'
if (Test-Path -LiteralPath $map) { Note ok 'hooks\recording-sessions.json' 'kept as is' }
else { [IO.File]::WriteAllText($map, '{}', $utf8); Note added 'hooks\recording-sessions.json' }

# settings.json: add or update the three recording hooks; everything else stays.
$settingsPath = Join-Path $ClaudeDir 'settings.json'
$fragText = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'hooks\settings-hooks.json')).Replace('{{HOOKS_DIR}}', ($hooksDir -replace '\\', '/'))
$frag = $fragText | ConvertFrom-Json
$settings = if (Test-Path -LiteralPath $settingsPath) { [IO.File]::ReadAllText($settingsPath) | ConvertFrom-Json } else { New-Object psobject }
if (-not $settings) { $settings = New-Object psobject }
$changed = $false
if (-not ($settings.PSObject.Properties.Name -contains 'hooks')) { $settings | Add-Member hooks (New-Object psobject); $changed = $true }
foreach ($ev in $frag.hooks.PSObject.Properties) {
    $wantGroup = @($ev.Value)[0]
    $wantCmd = @($wantGroup.hooks)[0].command
    if (-not ($settings.hooks.PSObject.Properties.Name -contains $ev.Name)) { $settings.hooks | Add-Member $ev.Name @() }
    $groups = @($settings.hooks.($ev.Name))
    $found = $false
    foreach ($g in $groups) {
        foreach ($h in @($g.hooks)) {
            if ([string]$h.command -match 'record-action\.ps1') {
                $found = $true
                if ($h.command -ne $wantCmd) { $h.command = $wantCmd; $changed = $true }
            }
        }
    }
    if (-not $found) { $groups += $wantGroup; $changed = $true }
    $settings.hooks.($ev.Name) = [object[]]$groups
}
if ($changed) {
    if (Test-Path -LiteralPath $settingsPath) { Copy-Item -LiteralPath $settingsPath "$settingsPath.bak-$stamp" }
    Write-JsonFile $settingsPath $settings
    Note changed "settings.json hooks" "PostToolUse/PostToolUseFailure/Stop -> $hooksDir\record-action.ps1 (backup .bak-$stamp)"
} else { Note ok 'settings.json hooks' }

$skillsSrc = Join-Path $repo '.claude\skills'
foreach ($s in Get-ChildItem -LiteralPath $skillsSrc -Directory) {
    Sync-Dir $s.FullName (Join-Path $ClaudeDir "skills\$($s.Name)") (Join-Path $ClaudeDir "skills\_backup\$stamp\$($s.Name)") "skills\$($s.Name)"
}

# <root>\CLAUDE.md: sessions start in the root, so it imports the repo's CLAUDE.md.
$rootMd = Join-Path $Root 'CLAUDE.md'
$importPath = if ([IO.Path]::GetFullPath($repo).TrimEnd('\') -eq $expectedRepo) { 'game-factory/CLAUDE.md' } else { ($repo -replace '\\', '/') + '/CLAUDE.md' }
$importLine = "@$importPath"
if (-not (Test-Path -LiteralPath $rootMd)) {
    [IO.File]::WriteAllText($rootMd, "# Work root`n`nEvery session on this machine follows the game-factory rules and skills:`n`n$importLine`n", $utf8)
    Note added "$rootMd" "imports $importPath"
} elseif ([IO.File]::ReadAllText($rootMd) -match [regex]::Escape($importLine)) { Note ok "$rootMd" }
else {
    Copy-Item -LiteralPath $rootMd "$rootMd.bak-$stamp"
    [IO.File]::AppendAllText($rootMd, "`n$importLine`n", $utf8)
    Note changed "$rootMd" "appended $importLine (backup .bak-$stamp)"
}

# --- 4. git, LFS, gh, game repos --------------------------------------------------------------------------------------
Write-Host "4. git"
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) { Note warn 'git' 'not installed: winget install Git.Git, then run bootstrap again' }
else {
    $lfs = (& git lfs version 2>$null)
    if (-not $lfs) { Note warn 'git-lfs' 'not installed (ships with Git for Windows; else winget install GitHub.GitLFS)' }
    elseif (-not (& git config --get filter.lfs.process 2>$null)) {   # global or system scope
        & git lfs install --skip-repo | Out-Null
        Note changed 'git-lfs' "filters installed globally ($lfs)"
    } else { Note ok 'git-lfs' "$lfs" }
}
$gh = Get-Command gh -ErrorAction SilentlyContinue
$ghOk = $false
if (-not $gh) { Note warn 'gh' 'not installed: winget install GitHub.cli, then gh auth login' }
else {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & gh auth status 2>&1 | Out-Null
    $ghOk = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $old
    if (-not $ghOk) { Note warn 'gh auth' 'not logged in: run gh auth login (manual, see docs/new-machine.md)' }
    else { Note ok 'gh auth' }
}

if ($CloneGames) {
    if (-not $ghOk) { Note warn 'clone games' 'needs gh logged in' }
    else {
        $names = @(& gh repo list $Org --limit 200 --json name --jq '.[].name' | Where-Object { $_ -match '^game-.' -and $_ -ne 'game-factory' })
        foreach ($n in $names) {
            $slug = $n.Substring(5)
            $dst = Join-Path $Root "games\$slug"
            if (Test-Path -LiteralPath (Join-Path $dst '.git')) { Note ok "games\$slug" 'already cloned'; continue }
            Write-Host "  cloning $Org/$n (LFS content included; can take a while)..."
            & git clone --quiet "https://github.com/$Org/$n.git" $dst
            if ($LASTEXITCODE -ne 0) { Note warn "games\$slug" "git clone failed ($LASTEXITCODE)" } else { Note added "games\$slug" "from $Org/$n" }
        }
    }
}
# _-prefixed folders (e.g. _pipeline-test) are tool test projects, not game data: no commit recorder.
$gameRepos = @(Get-ChildItem -LiteralPath (Join-Path $Root 'games') -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notlike '_*' -and (Test-Path -LiteralPath (Join-Path $_.FullName '.git')) })
foreach ($g in $gameRepos) {
    $msg = & (Join-Path $PSScriptRoot 'install-git-hook.ps1') -Repo $g.FullName -HooksDir $hooksDir 6>&1 | Out-String
    Note $(if ($msg -match 'already') { 'ok' } else { 'added' }) "games\$($g.Name) post-commit recorder"
}
if (-not $gameRepos.Count) { Note skip 'game repos' "none under $Root\games yet (new-game.ps1 or -CloneGames)" }

# --- summary ----------------------------------------------------------------------------------------------------------
$warn = @($report | Where-Object status -eq 'warn')
$chg = @($report | Where-Object { $_.status -in 'added', 'changed' })
Write-Host ""
Write-Host ("bootstrap done: {0} change(s), {1} warning(s). Next: powershell -ExecutionPolicy Bypass -File `"{2}`"" -f $chg.Count, $warn.Count, (Join-Path $PSScriptRoot 'check.ps1'))

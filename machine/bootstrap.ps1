<#
.SYNOPSIS
  Set up a Windows machine for game-factory sessions (idempotent: run it again any time; it only changes what differs).
.DESCRIPTION
  1. Machine root and config: writes %USERPROFILE%\.game-factory\config.json (root, ueb, engine, and the job slots
     heavy_slots / gpu_slots computed from the hardware by lib\gf-root.ps1 Get-GFComputedSlots, recorded in slots_auto;
     values set by hand stay unless -Force) and creates the Work layout under the root (games, builds\_queue,
     builds\_logs, recordings, .recording, deliverables, asset-library, tools) plus <ueb>\src and <ueb>\tmp.
  2. Tools: <root>\tools\ue-heavy.ps1 (+ gf-root.ps1) and the pinned ffmpeg
     (machine\get-ffmpeg.ps1, downloaded and SHA-256 verified, never committed).
  3. Coding agents (-Agent claude|codex|both; default: the config's "agents", else the ones installed, else both;
     written to the config): the recording hooks into the hooks dir (config "hooks_dir": ~\.claude\hooks on machines
     set up before Codex support, else ~\.game-factory\hooks), their entries merged into each agent's settings
     (Claude Code: <ClaudeDir>\settings.json; Codex: <CodexDir>\hooks.json plus the trust entries in config.toml; a backup
     .bak-<time> first; other settings and hooks are kept; before adding or changing them it prints what they record
     and asks, -Yes skips the question, a non-interactive run without -Yes leaves them out), the repo's skills (skills\)
     into each agent's personal skills folder (<ClaudeDir>\skills\, ~\.agents\skills\), and the root instructions
     (Claude Code: <root>\CLAUDE.md importing game-factory\CLAUDE.md; Codex: <root>\AGENTS.md naming game-factory\AGENTS.md;
     sessions start in the root).
  4. Git: git-lfs filters (git lfs install --skip-repo), gh login check, the commit recorder in every
     <root>\games\*\.git (machine\install-git-hook.ps1); -CloneGames clones every <org>/game-* repo first.
  The GitHub organisation (or user) that owns game-factory and the game repos is "github_org" in the config: -Org sets
  it, else the config's value is kept, else bootstrap asks (non-interactive runs warn and leave it unset).
  Any file it replaces is copied to a backup first (<root>\tools\_backup\<time>\, <hooks dir>\_backup\<time>\,
  <skills folder>\_backup\<time>\). It never pushes, never changes Windows settings and never signs in for you.
  Then run machine\check.ps1. Manual steps (Epic/Fab sign-in, gh login, display sleep): docs\new-machine.md.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File machine\bootstrap.ps1
  powershell -ExecutionPolicy Bypass -File machine\bootstrap.ps1 -Root D:\Work -CloneGames
  # scratch test that leaves the real profile alone:
  powershell -ExecutionPolicy Bypass -File machine\bootstrap.ps1 -Root C:\gf-test\Work -Ueb C:\gf-test\UEB `
      -ClaudeDir C:\gf-test\home\.claude -CodexDir C:\gf-test\home\.codex -AgentsSkillsDir C:\gf-test\home\.agents\skills `
      -HooksDir C:\gf-test\home\.game-factory\hooks -ConfigPath C:\gf-test\home\.game-factory\config.json -Agent both -FfmpegArchive <.7z>
#>
param(
    [string]$Root,                                              # default: GF_ROOT / existing config / %USERPROFILE%\Work
    [string]$Ueb,                                               # default: config / C:\UEB
    [string]$Engine,                                            # default: config / C:\Program Files\Epic Games\UE_5.7 (new games)
    [ValidateSet('auto', 'claude', 'codex', 'both')][string]$Agent = 'auto',   # which coding agents to wire up
    [string]$ClaudeDir = (Join-Path $env:USERPROFILE '.claude'),
    [string]$CodexDir,                                          # default: CODEX_HOME / %USERPROFILE%\.codex
    [string]$AgentsSkillsDir = (Join-Path $env:USERPROFILE '.agents\skills'),   # Codex's personal skills folder
    [string]$HooksDir,                                          # default: config hooks_dir (lib\gf-root.ps1 Get-GFHooksDir)
    [string]$ConfigPath,                                        # default: GF_CONFIG / %USERPROFILE%\.game-factory\config.json
    [string]$FfmpegArchive,                                     # a downloaded ffmpeg-8.1.2-full_build.7z (still verified)
    [switch]$SkipFfmpeg,
    [switch]$CloneGames,
    [string]$Org,                                               # GitHub org/user of the game repos -> config github_org
    [switch]$Force,                                             # also replace heavy_slots / gpu_slots someone set by hand
    [switch]$Yes                                                # install the recording hooks without asking
)
$hooksDeclined = $false
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'lib\gf-root.ps1')
. (Join-Path $PSScriptRoot 'lib\codex-hooks.ps1')
if ($ConfigPath) { $env:GF_CONFIG = $ConfigPath }
if ($Root) { $env:GF_ROOT = $Root }      # this process (and the scripts it starts) use the chosen root
$cfg = Get-GFConfig
$Root = $cfg.root
if (-not $Ueb) { $Ueb = $cfg.ueb }
if (-not $Engine) { $Engine = $cfg.engine }
if (-not $CodexDir) { $CodexDir = Get-GFCodexHome }
if (-not $HooksDir) { $HooksDir = Get-GFHooksDir $cfg }
$HooksDir = [IO.Path]::GetFullPath($HooksDir)
$Agents = switch ($Agent) { 'claude' { @('claude') } 'codex' { @('codex') } 'both' { @('claude', 'codex') } default { @(Get-GFAgents $cfg) } }
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

Write-Host "game-factory bootstrap: root $Root, repo $repo, agents $($Agents -join ' + '), hooks dir $HooksDir"

# --- 1. config + layout -------------------------------------------------------------------------------------------
Write-Host "1. config and layout"
$cfgPath = Get-GFConfigPath
if (-not $Org) { $Org = Get-GFOrg $cfg }
if (-not $Org -and [Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
    $Org = (Read-Host 'GitHub organisation (or user) that owns game-factory and the game-<slug> repos').Trim()
}
$want = [ordered]@{ root = $Root; ueb = $Ueb; engine = $Engine; record_extra_projects = @($cfg.record_extra_projects)
    agents = @($Agents); hooks_dir = $HooksDir }
if ($Org) { $want['github_org'] = $Org }
$have = if (Test-Path -LiteralPath $cfgPath) { [IO.File]::ReadAllText($cfgPath) | ConvertFrom-Json } else { $null }
$same = $have -and ($have.root -eq $want.root) -and ($have.ueb -eq $want.ueb) -and ($have.engine -eq $want.engine) -and
    ((@($have.record_extra_projects) -join '|') -eq (@($want.record_extra_projects) -join '|')) -and
    ((@($have.agents) -join '|') -eq (@($want.agents) -join '|')) -and ($have.hooks_dir -eq $want.hooks_dir) -and
    (-not $Org -or ($have.PSObject.Properties['github_org'] -and $have.github_org -eq $Org))
if ($same) { Note ok "config $cfgPath" }
else {
    if ($have) {
        foreach ($p in $have.PSObject.Properties) { if (-not $want.Contains($p.Name)) { $want[$p.Name] = $p.Value } }   # keep extra keys
        Copy-Item -LiteralPath $cfgPath "$cfgPath.bak-$stamp"
    }
    Write-JsonFile $cfgPath $want
    Note $(if ($have) { 'changed' } else { 'added' }) "config $cfgPath" "root=$Root ueb=$Ueb github_org=$Org agents=$($Agents -join ',') hooks_dir=$HooksDir"
}
if (-not $Org) { Note warn 'github_org' 'not set: run bootstrap.ps1 -Org <GitHub org or user> (new-game.ps1, -CloneGames and check.ps1 need it)' }
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
if ($SkipFfmpeg) { Note skip 'ffmpeg' '-SkipFfmpeg' }
else {
    $fa = @{ Root = $Root }; if ($FfmpegArchive) { $fa.Archive = $FfmpegArchive }
    $had = Test-Path -LiteralPath (Join-Path $Root 'tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe')
    $out = @(& (Join-Path $PSScriptRoot 'get-ffmpeg.ps1') @fa 6>&1)
    Note $(if ($had) { 'ok' } else { 'added' }) 'ffmpeg 8.1.2 (pinned, SHA-256 verified)' ([string]($out | Select-Object -Last 1))
}

# --- 3. coding agents: recording hooks, skills, root instructions ---------------------------------------------------
# One copy of the recording hooks (the hooks dir) serves every agent; each selected agent gets the hook entries, the
# skills and the root instructions file it reads.
Write-Host "3. coding agents ($($Agents -join ', '))"
$hooksDir = $HooksDir
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

# Merge a hook fragment ({{HOOKS_DIR}} filled in) into a parsed settings/hooks object: every handler whose command runs
# record-action.ps1 becomes the fragment's handler for that event, a missing one is added; everything else stays.
# Returns $true when something changed.
function Merge-RecordingHooks($Target, $Frag) {
    $changed = $false
    if (-not ($Target.PSObject.Properties.Name -contains 'hooks')) { $Target | Add-Member hooks (New-Object psobject); $changed = $true }
    foreach ($ev in $Frag.hooks.PSObject.Properties) {
        $wantGroup = @($ev.Value)[0]
        $want = @($wantGroup.hooks)[0]
        if (-not ($Target.hooks.PSObject.Properties.Name -contains $ev.Name)) { $Target.hooks | Add-Member $ev.Name @() }
        $groups = @($Target.hooks.($ev.Name))
        $found = $false
        foreach ($g in $groups) {
            $hs = @($g.hooks)
            for ($i = 0; $i -lt $hs.Count; $i++) {
                if ([string]$hs[$i].command -match 'record-action\.ps1') {
                    $found = $true
                    if (($hs[$i] | ConvertTo-Json -Compress) -ne ($want | ConvertTo-Json -Compress)) { $hs[$i] = $want; $changed = $true }
                }
            }
            $g.hooks = [object[]]$hs
        }
        if (-not $found) { $groups += $wantGroup; $changed = $true }
        $Target.hooks.($ev.Name) = [object[]]$groups
    }
    return $changed
}
function Read-JsonOrEmpty([string]$Path) {
    $o = if (Test-Path -LiteralPath $Path) { [IO.File]::ReadAllText($Path) | ConvertFrom-Json } else { $null }
    if (-not $o) { $o = New-Object psobject }
    return $o
}
$hooksSlash = ($hooksDir -replace '\\', '/')

# Claude Code: ~\.claude\settings.json gets PostToolUse, PostToolUseFailure and Stop.
$claudeChanged = $false
if ($Agents -contains 'claude') {
    $settingsPath = Join-Path $ClaudeDir 'settings.json'
    $settings = Read-JsonOrEmpty $settingsPath
    $frag = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'hooks\settings-hooks.json')).Replace('{{HOOKS_DIR}}', $hooksSlash) | ConvertFrom-Json
    $claudeChanged = Merge-RecordingHooks $settings $frag
}
# Codex: ~\.codex\hooks.json gets PostToolUse and Stop (Codex has no PostToolUseFailure), and config.toml the trust
# entries for exactly those handlers (machine/lib/codex-hooks.ps1: Codex skips an untrusted hook silently).
$codexChanged = $false; $codexTrustChanged = $false; $codexTrust = @()
if ($Agents -contains 'codex') {
    $codexHooksPath = Join-Path $CodexDir 'hooks.json'
    $codexToml = Join-Path $CodexDir 'config.toml'
    $codexHooks = Read-JsonOrEmpty $codexHooksPath
    $cfrag = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'hooks\codex-hooks.json')).Replace('{{HOOKS_DIR}}', $hooksSlash) | ConvertFrom-Json
    $codexChanged = Merge-RecordingHooks $codexHooks $cfrag
    # The key holds the hooks.json path as Codex prints it. With CODEX_HOME set, Codex canonicalizes the folder, which on
    # Windows can add the \\?\ prefix: both spellings are trusted then (an unused entry does nothing).
    $codexTrust = @(Get-GFCodexHookTrust $codexHooksPath $codexHooks)
    if ($env:CODEX_HOME -and $codexHooksPath -match '^[A-Za-z]:\\') {
        $codexTrust += @($codexTrust | ForEach-Object { [pscustomobject]@{ event = $_.event; key = "\\?\$($_.key)"; hash = $_.hash } })
    }
    $have = Get-GFCodexTrustState $codexToml
    $codexTrustChanged = @($codexTrust | Where-Object { $have[$_.key] -ne $_.hash }).Count -gt 0
}

if (($claudeChanged -or $codexChanged -or $codexTrustChanged) -and -not $Yes) {
    # Say plainly what the hooks do before wiring them into every session of the chosen agents on this Windows account.
    Write-Host ""
    Write-Host "  About to add the game-factory recording hooks (a backup .bak-$stamp of each file is kept):" -ForegroundColor Yellow
    if ($claudeChanged) { Write-Host "    - Claude Code: PostToolUse, PostToolUseFailure and Stop in $ClaudeDir\settings.json" }
    if ($codexChanged -or $codexTrustChanged) { Write-Host "    - Codex: PostToolUse and Stop in $CodexDir\hooks.json, marked trusted in $CodexDir\config.toml" }
    Write-Host "    They run $hooksDir\record-action.ps1 after every tool call of every session of that agent on this account."
    Write-Host "    - A session that works on a game (a tool call naming $Root\games\<slug>) has every tool call recorded"
    Write-Host "      (command, file paths, inputs, results, times) to $Root\.recording\<slug>\actions.jsonl, including its"
    Write-Host "      earlier calls, imported from its transcript; at the end of each turn its uncommitted work is committed as WIP."
    Write-Host "    - Each game repo's post-commit hook records commits to $Root\.recording\<slug>\commits.jsonl."
    Write-Host "    - Sessions that never touch a game folder are not recorded; session ids in hooks\recording-exclude.txt never are."
    Write-Host "    These records become the game-creation dataset. Remove the entries from those files to stop recording."
    $ok = $false
    if ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) { $ok = (Read-Host '  Install the recording hooks? [y/N]') -match '^(y|yes)$' }
    if (-not $ok) {
        $hooksDeclined = $true
        if ($claudeChanged) { Note warn 'Claude Code hooks' 'not installed (declined or non-interactive; -Yes installs them without asking)' }
        if ($codexChanged -or $codexTrustChanged) { Note warn 'Codex hooks' 'not installed (declined or non-interactive; -Yes installs them without asking)' }
        $claudeChanged = $false; $codexChanged = $false; $codexTrustChanged = $false
    }
}
if ($claudeChanged) {
    if (Test-Path -LiteralPath $settingsPath) { Copy-Item -LiteralPath $settingsPath "$settingsPath.bak-$stamp" }
    Write-JsonFile $settingsPath $settings
    Note changed 'Claude Code hooks' "settings.json PostToolUse/PostToolUseFailure/Stop -> $hooksDir\record-action.ps1 (backup .bak-$stamp)"
} elseif ($Agents -contains 'claude' -and -not $hooksDeclined) { Note ok 'Claude Code hooks' }
if ($codexChanged) {
    if (Test-Path -LiteralPath $codexHooksPath) { Copy-Item -LiteralPath $codexHooksPath "$codexHooksPath.bak-$stamp" }
    Write-JsonFile $codexHooksPath $codexHooks
    Note changed 'Codex hooks' "hooks.json PostToolUse/Stop -> $hooksDir\record-action.ps1 -Agent codex (backup .bak-$stamp)"
} elseif ($Agents -contains 'codex' -and -not $hooksDeclined) { Note ok 'Codex hooks' }
if ($codexTrustChanged) {
    if (Test-Path -LiteralPath $codexToml) { Copy-Item -LiteralPath $codexToml "$codexToml.bak-$stamp" }
    Set-GFCodexTrustState $codexToml $codexTrust
    Note changed 'Codex hook trust' "config.toml [hooks.state] for $(@($codexTrust).Count) handler(s) (backup .bak-$stamp; check with /hooks in Codex)"
} elseif ($Agents -contains 'codex' -and -not $hooksDeclined) { Note ok 'Codex hook trust' }

# Skills: one source (<repo>\skills\<name>\SKILL.md), copied to where each agent looks for personal skills
# (Claude Code: ~\.claude\skills; Codex: ~\.agents\skills). Copies, not links: links need Developer Mode on Windows.
$skillsSrc = Join-Path $repo 'skills'
$skillDirs = @()
if ($Agents -contains 'claude') { $skillDirs += , @('Claude Code', (Join-Path $ClaudeDir 'skills')) }
if ($Agents -contains 'codex') { $skillDirs += , @('Codex', $AgentsSkillsDir) }
foreach ($sd in $skillDirs) {
    foreach ($s in Get-ChildItem -LiteralPath $skillsSrc -Directory) {
        Sync-Dir $s.FullName (Join-Path $sd[1] $s.Name) (Join-Path $sd[1] "_backup\$stamp\$($s.Name)") "$($sd[0]) skills\$($s.Name)"
    }
}

# Root instructions: sessions start in the root. Claude Code reads <root>\CLAUDE.md (it imports the repo's CLAUDE.md,
# which imports AGENTS.md); Codex reads <root>\AGENTS.md (no imports: it names the repo's AGENTS.md to read first).
$inRoot = [IO.Path]::GetFullPath($repo).TrimEnd('\') -eq $expectedRepo
function Set-RootFile([string]$Path, [string]$Line, [string]$NewText) {
    if (-not (Test-Path -LiteralPath $Path)) {
        [IO.File]::WriteAllText($Path, $NewText, $utf8)
        Note added "$Path" $Line
    } elseif ([IO.File]::ReadAllText($Path) -match [regex]::Escape($Line)) { Note ok "$Path" }
    else {
        Copy-Item -LiteralPath $Path "$Path.bak-$stamp"
        [IO.File]::AppendAllText($Path, "`n$Line`n", $utf8)
        Note changed "$Path" "appended $Line (backup .bak-$stamp)"
    }
}
if ($Agents -contains 'claude') {
    $importPath = if ($inRoot) { 'game-factory/CLAUDE.md' } else { ($repo -replace '\\', '/') + '/CLAUDE.md' }
    Set-RootFile (Join-Path $Root 'CLAUDE.md') "@$importPath" "# Work root`n`nEvery session on this machine follows the game-factory rules and skills:`n`n@$importPath`n"
}
if ($Agents -contains 'codex') {
    $agentsPath = Join-Path $repo 'AGENTS.md'
    $line = "Before anything else, read $agentsPath and follow it (rules, skills, priorities)."
    Set-RootFile (Join-Path $Root 'AGENTS.md') $line ("# Work root`n`nEvery session on this machine follows the game-factory rules and skills.`n$line`n" +
        "The skills it names (commit-always, game-session, write-tasks) are installed in $AgentsSkillsDir.`n")
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
    elseif (-not $Org) { Note warn 'clone games' 'needs github_org (-Org)' }
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

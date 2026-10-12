<#
.SYNOPSIS
  Check that this machine can run game-factory sessions; prints a PASS / WARN / FAIL report. Read-only.
.DESCRIPTION
  Toolchain: UE 5.3, MSVC 14.44, Windows SDK, .NET Framework 4.8.1 SDK, git + Git LFS, gh (logged in, can see the
  org's repos), Python. Recording: NVIDIA driver >= 617 (NVENC with the pinned ffmpeg), refresh rate, display sleep
  off, the pinned ffmpeg. Space: free disk on the root's drive. Content: the asset library against
  docs/asset-library.md and docs/asset-library-fab-ue.tsv. Setup done by bootstrap.ps1: config, ue-heavy.ps1, hooks
  in settings.json, skills, root CLAUDE.md. Optional: Unity 2022.3.10f1 (LiaoZhai replay only).
  Exit code = number of FAILs. -Json writes the report as JSON too.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File machine\check.ps1
  powershell -ExecutionPolicy Bypass -File machine\check.ps1 -Root C:\gf-test\Work -ClaudeDir C:\gf-test\home\.claude -Json C:\gf-test\check.json
#>
param(
    [string]$Root,
    [string]$ClaudeDir = (Join-Path $env:USERPROFILE '.claude'),
    [string]$ConfigPath,
    [string]$Org = 'superpositionhq',
    [int]$MinFreeGB = 300,          # WARN below this, FAIL below a third of it
    [int]$MinDriver = 617,
    [string]$Json
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot 'lib\gf-root.ps1')
if ($ConfigPath) { $env:GF_CONFIG = $ConfigPath }
if ($Root) { $env:GF_ROOT = $Root }
$cfg = Get-GFConfig
$Root = $cfg.root
$results = New-Object Collections.Generic.List[object]

function Add-Result([string]$Status, [string]$Check, [string]$Detail, [string]$Fix = '') {
    $results.Add([pscustomobject]@{ status = $Status; check = $Check; detail = $Detail; fix = $Fix })
}
function Try-Check([string]$Check, [scriptblock]$Body) {
    try { & $Body } catch { Add-Result FAIL $Check "check errored: $($_.Exception.Message)" }
}
function Run([string]$Exe, [string[]]$ArgList) {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $out = & $Exe @ArgList 2>&1 | ForEach-Object { "$_" }; return [pscustomobject]@{ code = $LASTEXITCODE; out = ($out -join "`n") } }
    catch { return [pscustomobject]@{ code = -1; out = $_.Exception.Message } }
    finally { $ErrorActionPreference = $old }
}

# --- toolchain ------------------------------------------------------------------------------------------------------
Try-Check 'Unreal Engine 5.3' {
    $ver = Join-Path $cfg.engine 'Engine\Build\Build.version'
    $ed = Join-Path $cfg.engine 'Engine\Binaries\Win64\UnrealEditor.exe'
    if (-not (Test-Path $ver) -or -not (Test-Path $ed)) { Add-Result FAIL 'Unreal Engine 5.3' "not found at $($cfg.engine)" 'Epic Games Launcher > Unreal Engine > Library > install 5.3 (or set "engine" in the config)'; return }
    $v = Get-Content $ver -Raw | ConvertFrom-Json
    if ($v.MajorVersion -eq 5 -and $v.MinorVersion -eq 3) { Add-Result PASS 'Unreal Engine 5.3' "5.3.$($v.PatchVersion) at $($cfg.engine)" }
    else { Add-Result FAIL 'Unreal Engine 5.3' "found $($v.MajorVersion).$($v.MinorVersion) at $($cfg.engine)" 'install 5.3 exactly; the games and the AutoPlay drop-in target 5.3' }
}

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
Try-Check 'MSVC 14.44' {
    $installs = if (Test-Path $vswhere) { @(& $vswhere -all -products '*' -property installationPath) } else { @() }
    $msvc = @($installs | ForEach-Object { Get-ChildItem (Join-Path $_ 'VC\Tools\MSVC') -Directory -ErrorAction SilentlyContinue } | Select-Object -ExpandProperty Name)
    $hit = @($msvc | Where-Object { $_ -like '14.44.*' })
    if ($hit) { Add-Result PASS 'MSVC 14.44' ("{0} (all: {1})" -f $hit[0], ($msvc -join ', ')) }
    else { Add-Result FAIL 'MSVC 14.44' $(if ($msvc) { "found $($msvc -join ', ')" } else { 'no Visual Studio / Build Tools C++ toolset' }) 'VS 2022 Build Tools with "Desktop development with C++" (MSVC v143 14.44); Target.cs needs bOverrideBuildEnvironment + PLATFORM_HAS_ASAN_INCLUDE=0' }
}
Try-Check 'Windows SDK' {
    $inc = "${env:ProgramFiles(x86)}\Windows Kits\10\Include"
    $sdks = @(Get-ChildItem $inc -Directory -ErrorAction SilentlyContinue | Where-Object Name -like '10.0.*' | Select-Object -ExpandProperty Name)
    if ($sdks) { Add-Result PASS 'Windows SDK' ($sdks -join ', ') } else { Add-Result FAIL 'Windows SDK' 'none under Windows Kits\10\Include' 'add a Windows 11 SDK in the VS Installer' }
}
Try-Check '.NET Framework 4.8.1 SDK' {
    $sdk = "${env:ProgramFiles(x86)}\Windows Kits\NETFXSDK\4.8.1"
    $ref = "${env:ProgramFiles(x86)}\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8.1"
    if ((Test-Path $sdk) -and (Test-Path $ref)) { Add-Result PASS '.NET Framework 4.8.1 SDK' 'NETFXSDK\4.8.1 + targeting pack' }
    else { Add-Result FAIL '.NET Framework 4.8.1 SDK' "missing: $(@($sdk, $ref | Where-Object { -not (Test-Path $_) }) -join '; ')" 'winget install Microsoft.DotNet.Framework.DeveloperPack_4 (UBT editor targets fail without NetFxSDK: SwarmInterface)' }
}
Try-Check 'git' {
    $r = Run git @('--version')
    if ($r.code -eq 0) { Add-Result PASS 'git' $r.out } else { Add-Result FAIL 'git' 'not found' 'winget install Git.Git' }
}
Try-Check 'Git LFS' {
    $r = Run git @('lfs', 'version')
    if ($r.code -ne 0) { Add-Result FAIL 'Git LFS' 'git lfs not found' 'winget install GitHub.GitLFS'; return }
    $f = Run git @('config', '--get', 'filter.lfs.process')   # global or system (Git for Windows sets it system-wide)
    if ($f.out) { Add-Result PASS 'Git LFS' ($r.out -split "`n")[0] } else { Add-Result FAIL 'Git LFS' 'installed but filters not set up' 'git lfs install --skip-repo (bootstrap.ps1 does this)' }
}
Try-Check 'GitHub CLI' {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { Add-Result FAIL 'GitHub CLI' 'gh not found' 'winget install GitHub.cli'; return }
    $login = Run gh @('api', 'user', '--jq', '.login')
    if ($login.code -ne 0) { Add-Result FAIL 'GitHub CLI' 'not logged in' 'gh auth login (GitHub.com, HTTPS, browser)'; return }
    $v = Run gh @('repo', 'view', "$Org/game-factory", '--json', 'name,visibility', '--jq', '.visibility')
    if ($v.code -ne 0) { Add-Result FAIL "GitHub access to $Org" "logged in as $($login.out), but cannot see $Org/game-factory" "ask an $Org owner to add the account (needs repo create rights for game-<slug> repos)"; return }
    $m = Run gh @('api', "user/memberships/orgs/$Org", '--jq', '.role + " " + .state')
    $role = if ($m.code -eq 0) { $m.out } else { 'membership not readable (token lacks read:org)' }
    $n = Run gh @('repo', 'list', $Org, '--limit', '200', '--json', 'name', '--jq', '.[].name')
    $games = @(($n.out -split "`n") | Where-Object { $_ -match '^game-' -and $_ -ne 'game-factory' }).Count
    Add-Result PASS "GitHub access to $Org" "logged in as $($login.out); org role: $role; game-* repos visible: $games"
}
Try-Check 'Python' {
    $py = Get-Command python -ErrorAction SilentlyContinue | Where-Object { $_.Source -notmatch 'WindowsApps' } | Select-Object -First 1
    $cmd = if ($py) { $py.Source } elseif (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { $null }
    if (-not $cmd) { Add-Result FAIL 'Python' 'no python.exe (the Microsoft Store stub does not count)' 'winget install Python.Python.3.12 (asset-scout tools; UE has its own Python for editor scripts)'; return }
    $r = Run $cmd @('-c', 'import sys; print(sys.version.split()[0])')
    if ($r.code -eq 0 -and $r.out -match '^3\.(\d+)' -and [int]$Matches[1] -ge 10) { Add-Result PASS 'Python' "$($r.out) ($cmd)" }
    else { Add-Result FAIL 'Python' "unusable: $($r.out)" 'install Python 3.10+' }
}

# --- recording hardware / display ------------------------------------------------------------------------------------
Try-Check "NVIDIA driver >= $MinDriver" {
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $smi) { Add-Result FAIL "NVIDIA driver >= $MinDriver" 'nvidia-smi not found (no NVIDIA GPU/driver)' 'recording uses NVENC; install an NVIDIA GPU driver'; return }
    $r = Run $smi.Source @('--query-gpu=name,driver_version,memory.total', '--format=csv,noheader')
    $first = ($r.out -split "`n")[0]
    $parts = $first -split ',\s*'
    $drv = [double]($parts[1] -replace '[^\d.]', '')
    if ($drv -ge $MinDriver) { Add-Result PASS "NVIDIA driver >= $MinDriver" $first }
    else { Add-Result FAIL "NVIDIA driver >= $MinDriver" $first "update the driver (ffmpeg 8.1.2 NVENC needs >= 610; the pipeline was verified on 617.42)" }
}
Try-Check 'Display refresh rate' {
    $rates = @(Get-CimInstance Win32_VideoController | Where-Object { $_.CurrentRefreshRate } | ForEach-Object { "$($_.Name): $($_.CurrentHorizontalResolution)x$($_.CurrentVerticalResolution) @ $($_.CurrentRefreshRate) Hz" })
    $max = (@(Get-CimInstance Win32_VideoController | ForEach-Object { [int]$_.CurrentRefreshRate }) | Measure-Object -Maximum).Maximum
    if ($max -ge 120) { Add-Result PASS 'Display refresh rate' ($rates -join '; ') }
    elseif ($max -ge 60) { Add-Result WARN 'Display refresh rate' ($rates -join '; ') 'recordings are 60 fps CFR; the pipeline was tuned on a 120 Hz display (Settings > Display > Advanced display)' }
    else { Add-Result FAIL 'Display refresh rate' $(if ($rates) { $rates -join '; ' } else { 'no active display' }) 'recording captures the desktop at 60 fps: needs a display at >= 60 Hz' }
}
function Get-PowerAc([string]$Sub, [string]$Setting) {
    $r = Run powercfg @('/query', 'SCHEME_CURRENT', $Sub, $Setting)
    $hex = [regex]::Matches($r.out, '0x[0-9a-fA-F]{8}') | ForEach-Object { $_.Value }
    if ($hex.Count -lt 2) { return $null }
    return [Convert]::ToInt32($hex[-2], 16)   # the last two are the AC and DC current values
}
Try-Check 'Display sleep off' {
    $ac = Get-PowerAc 'SUB_VIDEO' 'VIDEOIDLE'
    if ($null -eq $ac) { Add-Result WARN 'Display sleep off' 'could not read powercfg' ; return }
    if ($ac -eq 0) { Add-Result PASS 'Display sleep off' 'turn off display after: never (AC)' }
    # The recorder keeps the display on during a run and wakes it before launch, but a display that went to sleep
    # during a long build has already cost a recording (Desktop Duplication delivers no frames); "never" is the safe setting.
    else { Add-Result WARN 'Display sleep off' "display turns off after $([int]($ac/60)) min (AC)" 'powercfg /change monitor-timeout-ac 0 (Settings > System > Power > Screen: Never)' }
}
Try-Check 'System sleep off' {
    $ac = Get-PowerAc 'SUB_SLEEP' 'STANDBYIDLE'
    if ($null -eq $ac) { Add-Result WARN 'System sleep off' 'could not read powercfg'; return }
    if ($ac -eq 0) { Add-Result PASS 'System sleep off' 'sleep after: never (AC)' }
    else { Add-Result WARN 'System sleep off' "PC sleeps after $([int]($ac/60)) min (AC)" 'powercfg /change standby-timeout-ac 0 (overnight queues and long builds)' }
}
Try-Check 'Free disk' {
    $drive = (Split-Path -Qualifier $Root).TrimEnd(':')
    $d = Get-PSDrive -Name $drive
    $gb = [math]::Round($d.Free / 1GB)
    if ($gb -ge $MinFreeGB) { Add-Result PASS 'Free disk' "$gb GB free on ${drive}:" }
    elseif ($gb -ge [int]($MinFreeGB / 3)) { Add-Result WARN 'Free disk' "$gb GB free on ${drive}: (want $MinFreeGB)" 'game repos with LFS are 3-16 GB each, the asset library ~160 GB, builds and recordings grow' }
    else { Add-Result FAIL 'Free disk' "$gb GB free on ${drive}:" "free space; under $([int]($MinFreeGB/3)) GB builds and packaging fail" }
}
Try-Check 'Memory' {
    $gb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
    if ($gb -ge 30) { Add-Result PASS 'Memory' "$gb GB" } else { Add-Result WARN 'Memory' "$gb GB" 'the 3-slot ue-heavy limit was sized for 32 GB; lower -Slots on smaller machines' }
}
Try-Check 'Long paths' {
    $v = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
    if ($v -eq 1) { Add-Result PASS 'Long paths' 'LongPathsEnabled=1' } else { Add-Result WARN 'Long paths' 'LongPathsEnabled is off' 'optional: Fab packs nest deeply; keep the root short (e.g. C:\Work) or enable long paths as admin' }
}

# --- pinned ffmpeg ---------------------------------------------------------------------------------------------------
Try-Check 'ffmpeg 8.1.2 (pinned)' {
    $exe = Join-Path $Root 'tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe'
    $arc = Join-Path $Root 'tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build.7z'
    if (-not (Test-Path $exe)) { Add-Result FAIL 'ffmpeg 8.1.2 (pinned)' "missing $exe" 'machine\get-ffmpeg.ps1'; return }
    $ok = (Test-Path $arc) -and ((Get-FileHash $arc -Algorithm SHA256).Hash -eq '0FFF188997A499B5382E0F66E845D4556C48C54F0113EBED4853D556DBDD7059')
    $nv = Run $exe @('-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=256x256:r=60', '-t', '0.1', '-c:v', 'h264_nvenc', '-f', 'null', '-')
    $enc = if ($nv.code -eq 0) { 'h264_nvenc opens' } else { 'h264_nvenc does NOT open (recordings fall back to libx264)' }
    if ($ok) { Add-Result $(if ($nv.code -eq 0) { 'PASS' } else { 'WARN' }) 'ffmpeg 8.1.2 (pinned)' "archive SHA-256 verified; $enc" }
    else { Add-Result WARN 'ffmpeg 8.1.2 (pinned)' "ffmpeg.exe present but the archive is missing or does not match the pin; $enc" 'machine\get-ffmpeg.ps1 -Force' }
}

# --- setup done by bootstrap.ps1 ---------------------------------------------------------------------------------------
Try-Check 'Config' {
    $p = Get-GFConfigPath
    if (Test-Path $p) { Add-Result PASS 'Config' "$p (root $Root)" }
    elseif ($Root -eq (Join-Path $env:USERPROFILE 'Work')) { Add-Result WARN 'Config' "no $p; using the default root $Root" 'machine\bootstrap.ps1 writes it' }
    else { Add-Result FAIL 'Config' "no $p" 'machine\bootstrap.ps1' }
}
Try-Check 'Work layout' {
    $missing = @('games', 'builds\_queue', 'recordings', '.recording', 'deliverables', 'asset-library', 'tools') | Where-Object { -not (Test-Path (Join-Path $Root $_)) }
    $ueb = @((Join-Path $cfg.ueb 'src'), (Join-Path $cfg.ueb 'tmp')) | Where-Object { -not (Test-Path $_) }
    if (-not $missing -and -not $ueb) { Add-Result PASS 'Work layout' "$Root + $($cfg.ueb)" } else { Add-Result FAIL 'Work layout' "missing: $(@($missing) + @($ueb) -join ', ')" 'machine\bootstrap.ps1' }
}
Try-Check 'game-factory clone' {
    $exp = Join-Path $Root 'game-factory'
    if ([IO.Path]::GetFullPath($repo).TrimEnd('\') -eq $exp) { Add-Result PASS 'game-factory clone' $repo }
    else { Add-Result WARN 'game-factory clone' "running from $repo, briefs and docs assume $exp" "git clone https://github.com/$Org/game-factory $exp" }
}
function Same-File([string]$A, [string]$B) { (Test-Path $A) -and (Test-Path $B) -and ((Get-FileHash $A).Hash -eq (Get-FileHash $B).Hash) }
Try-Check 'ue-heavy.ps1' {
    $dst = Join-Path $Root 'tools\ue-heavy.ps1'
    if (Same-File (Join-Path $PSScriptRoot 'tools\ue-heavy.ps1') $dst) { Add-Result PASS 'ue-heavy.ps1' $dst }
    elseif (Test-Path $dst) { Add-Result WARN 'ue-heavy.ps1' "$dst differs from the repo copy" 'machine\bootstrap.ps1 (keeps a backup)' }
    else { Add-Result FAIL 'ue-heavy.ps1' "missing $dst" 'machine\bootstrap.ps1' }
}
Try-Check 'Recording hooks' {
    $hd = Join-Path $ClaudeDir 'hooks'
    $files = @('record-action.ps1', 'record-commit.ps1')
    $diff = @($files | Where-Object { -not (Same-File (Join-Path $PSScriptRoot "hooks\$_") (Join-Path $hd $_)) })
    $lib = Test-Path (Join-Path $hd 'gf-root.ps1')
    $sp = Join-Path $ClaudeDir 'settings.json'
    $wired = @()
    if (Test-Path $sp) {
        $s = [IO.File]::ReadAllText($sp) | ConvertFrom-Json
        foreach ($ev in 'PostToolUse', 'PostToolUseFailure', 'Stop') {
            $cmds = @($s.hooks.$ev | ForEach-Object { $_.hooks } | ForEach-Object { [string]$_.command })
            if ($cmds -match 'record-action\.ps1') { $wired += $ev }
        }
    }
    $absent = @($files | Where-Object { -not (Test-Path (Join-Path $hd $_)) })
    if (-not $diff -and $lib -and $wired.Count -eq 3) { Add-Result PASS 'Recording hooks' "$hd; settings.json wires PostToolUse, PostToolUseFailure, Stop" }
    elseif (-not $absent -and $wired.Count -eq 3) {
        Add-Result WARN 'Recording hooks' "installed and wired, but older than the repo copy ($($diff -join ', ')$(if (-not $lib) { ', no gf-root.ps1' }))" 'machine\bootstrap.ps1 (backs up the old copies)'
    } else { Add-Result FAIL 'Recording hooks' ("{0}{1}settings.json wires: {2}" -f $(if ($diff) { "differs/missing: $($diff -join ', '); " } else { '' }), $(if (-not $lib) { 'no gf-root.ps1; ' } else { '' }), $(if ($wired) { $wired -join ', ' } else { 'none' })) 'machine\bootstrap.ps1' }
}
Try-Check 'Skills' {
    $names = @(Get-ChildItem (Join-Path $repo '.claude\skills') -Directory | Select-Object -ExpandProperty Name)
    $bad = @($names | Where-Object { -not (Same-File (Join-Path $repo ".claude\skills\$_\SKILL.md") (Join-Path $ClaudeDir "skills\$_\SKILL.md")) })
    if (-not $bad) { Add-Result PASS 'Skills' ($names -join ', ') } else { Add-Result FAIL 'Skills' "missing or outdated in ${ClaudeDir}\skills: $($bad -join ', ')" 'machine\bootstrap.ps1' }
}
Try-Check 'Root CLAUDE.md' {
    $p = Join-Path $Root 'CLAUDE.md'
    if ((Test-Path $p) -and ((Get-Content $p -Raw) -match '@.*game-factory/CLAUDE\.md|@.*/CLAUDE\.md')) { Add-Result PASS 'Root CLAUDE.md' "$p imports the repo CLAUDE.md" }
    else { Add-Result FAIL 'Root CLAUDE.md' "$p missing or not importing game-factory/CLAUDE.md" 'machine\bootstrap.ps1' }
}
Try-Check 'Game repos record commits' {
    # _-prefixed folders (e.g. _pipeline-test) are tool test projects, not game data
    $repos = @(Get-ChildItem (Join-Path $Root 'games') -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike '_*' -and (Test-Path (Join-Path $_.FullName '.git')) })
    if (-not $repos) { Add-Result PASS 'Game repos record commits' 'no game repos yet'; return }
    $missing = @($repos | Where-Object {
        $h = Join-Path $_.FullName '.git\hooks\post-commit'
        -not ((Test-Path $h) -and ((Get-Content $h -Raw) -match 'record-commit\.ps1'))
    } | Select-Object -ExpandProperty Name)
    if (-not $missing) { Add-Result PASS 'Game repos record commits' "$($repos.Count) repo(s)" } else { Add-Result FAIL 'Game repos record commits' "no recorder in: $($missing -join ', ')" 'machine\install-git-hook.ps1 <repo> (bootstrap.ps1 does all)' }
}

# --- content ---------------------------------------------------------------------------------------------------------
Try-Check 'Asset library (Fab packs)' {
    $lib = Join-Path $Root 'asset-library'
    $paths = New-Object Collections.Generic.List[string]
    # docs/asset-library.md: the Path column of the "On disk now" tables; a bare name inherits the previous one's folder
    $src = '^(fab|fab-ue|polyhaven|ambientcg|kenney|gameicons|fonts|opengameart)\\'
    foreach ($line in Get-Content (Join-Path $repo 'docs\asset-library.md')) {
        if ($line -notmatch '^\|' -or $line -match '^\|\s*-') { continue }
        $cells = $line.Split('|')
        if ($cells.Count -lt 4) { continue }
        $prefix = $null
        foreach ($m in [regex]::Matches($cells[2], '`([^`]+)`')) {
            $t = $m.Groups[1].Value.Trim().TrimEnd('\')
            if ($t -match '\.\.\.|<|\*|^-|\s') { continue }
            if ($t -match $src) { $prefix = $Matches[1]; $paths.Add($t) }
            elseif ($prefix -and $t -match '^[A-Za-z0-9_.-]+$') { $paths.Add("$prefix\$t") }
        }
    }
    # docs/asset-library-fab-ue.tsv: the Unreal-format Fab packs (fabue.py rebuilds them from Fab's manifests)
    $tsv = Join-Path $repo 'docs\asset-library-fab-ue.tsv'
    if (Test-Path $tsv) { Import-Csv $tsv -Delimiter "`t" | Where-Object { $_.result -eq 'ok' } | ForEach-Object { $paths.Add("fab-ue\$($_.slug)") } }
    $all = @($paths | Sort-Object -Unique)
    $missing = @($all | Where-Object { -not (Test-Path (Join-Path $lib $_)) })
    $have = $all.Count - $missing.Count
    $detail = "$have of $($all.Count) packs present in $lib"
    if ($missing.Count -eq 0) { Add-Result PASS 'Asset library (Fab packs)' $detail }
    elseif ($have -ge $all.Count / 2) { Add-Result WARN 'Asset library (Fab packs)' "$detail; missing e.g. $(($missing | Select-Object -First 6) -join ', ')" 'asset-scout session re-downloads them (Fab sign-in in the browser pane first); game repos already carry the packs they use' }
    else { Add-Result FAIL 'Asset library (Fab packs)' "$detail; missing e.g. $(($missing | Select-Object -First 6) -join ', ')" 'sign in to fab.com with the account that owns the packs, then spawn the asset-scout helper (docs/briefs/helpers/asset-scout.md)' }
}

# --- optional ---------------------------------------------------------------------------------------------------------
Try-Check 'Unity 2022.3.10f1 (optional)' {
    $u = "$env:ProgramFiles\Unity\Hub\Editor\2022.3.10f1\Editor\Unity.exe"
    if (Test-Path $u) { Add-Result PASS 'Unity 2022.3.10f1 (optional)' $u }
    else { Add-Result WARN 'Unity 2022.3.10f1 (optional)' 'not installed (only the LiaoZhai Unity replay needs it)' 'Unity Hub > Installs > Install Editor > Archive > 2022.3.10f1' }
}

# --- report ------------------------------------------------------------------------------------------------------------
$colors = @{ PASS = 'Green'; WARN = 'Yellow'; FAIL = 'Red' }
Write-Host ""
Write-Host "game-factory machine check  (root $Root, Claude dir $ClaudeDir)"
foreach ($r in $results) {
    Write-Host ("  {0}  {1,-30} {2}" -f $r.status, $r.check, $r.detail) -ForegroundColor $colors[$r.status]
    if ($r.status -ne 'PASS' -and $r.fix) { Write-Host ("        fix: {0}" -f $r.fix) -ForegroundColor DarkGray }
}
$nFail = @($results | Where-Object status -eq 'FAIL').Count
$nWarn = @($results | Where-Object status -eq 'WARN').Count
Write-Host ("{0} checks: {1} PASS, {2} WARN, {3} FAIL" -f $results.Count, ($results.Count - $nFail - $nWarn), $nWarn, $nFail)
if ($Json) {
    $obj = [ordered]@{ time = (Get-Date).ToString('o'); root = $Root; claude_dir = $ClaudeDir; fail = $nFail; warn = $nWarn; results = $results }
    [IO.File]::WriteAllText($Json, ($obj | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding($false)))
}
exit $nFail

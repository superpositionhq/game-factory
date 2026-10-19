<#
.SYNOPSIS
  One entry point for a clean Windows 11 PC: from nothing to building games. Idempotent and resumable: run it again
  after any manual step (or reboot) and it continues where it stopped.
.DESCRIPTION
  1. Hardware precheck against the stated minimums (below).
  2. Software through winget (asks once, lists what is missing; winget accepts each package's licence):
     Git (+ Git LFS), GitHub CLI, Python 3.12, VS 2022 Build Tools (C++ workload: MSVC 14.44, Windows 11 SDK 22621),
     .NET Framework 4.8.1 Developer Pack, 7-Zip, Epic Games Launcher, the Codex CLI when Codex is one of the agents,
     and the Claude desktop app (optional) when Claude Code is.
  3. Windows settings, each asked first: long paths (admin, one UAC prompt) and no sleep while plugged in (display and
     PC; powercfg on the current power plan).
  4. GitHub sign-in (gh auth login in the browser) and git user.name / user.email; Codex sign-in (codex login in the
     browser) when Codex is one of the agents.
  5. game-factory: cloned into <root>\game-factory when this script runs from outside a clone, then
     machine\bootstrap.ps1 (config, tools, hooks after its own question, skills; -CloneGames when you say so) and
     machine\check.ps1.
  6. What cannot be scripted (Epic sign-in + UE 5.7 in the Launcher, NVIDIA driver, Fab sign-in, Claude Code sign-in):
     exact steps, detected on the next run.
  The coding agent: -Agent claude (Claude Code), codex (OpenAI Codex CLI) or both; asked on the first run (remembered),
  passed on to bootstrap.ps1, which wires the recording hooks, skills and root instructions into each.
  Ends with a PASS / TODO list. Log: <root>\.setup\setup.log; answers: <root>\.setup\state.json (not asked again).

  Minimums: Windows 11; 8 logical cores and 16 GB RAM (32 GB recommended: job slots scale with RAM); 300 GB free on
  the root's drive (150 GB at the very least; game repos with their store packs are 3-16 GB each, builds and the
  asset library grow); a DirectX 12 GPU for the editor. Recording gameplay wants an NVIDIA GPU (8 GB+ VRAM, driver
  610+, NVENC); without one it falls back to slower encoders.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File setup.ps1 -Org <org>
  powershell -ExecutionPolicy Bypass -File setup.ps1 -Org <org> -Agent codex
  powershell -ExecutionPolicy Bypass -File setup.ps1 -Org <org> -Root D:\Work -CloneGames
  # dry run against a scratch root (installs, Windows settings, sign-ins and game clones are only reported):
  powershell -ExecutionPolicy Bypass -File machine\setup.ps1 -Org <org> -DryRun -Root C:\gf-test\Work `
      -ClaudeDir C:\gf-test\home\.claude -CodexDir C:\gf-test\home\.codex -AgentsSkillsDir C:\gf-test\home\.agents\skills `
      -HooksDir C:\gf-test\home\.game-factory\hooks -ConfigPath C:\gf-test\home\.game-factory\config.json -Agent both
#>
param(
    [string]$Root,                     # default: the config's root, else asked (%USERPROFILE%\Work offered)
    [string]$Org,                      # GitHub org/user that owns game-factory and the game repos (config github_org)
    [switch]$CloneGames,               # also clone every <org>/game-* repo (asked when not given)
    [switch]$Yes,                      # answer yes to every question (installs, settings, hooks)
    [switch]$DryRun,                   # no installs, Windows settings, sign-ins or game clones (bootstrap still writes the
                                       # config, root and Claude dir it is given: use it with a scratch -Root/-ClaudeDir/-ConfigPath)
    [string]$RepoUrl,                  # where to clone game-factory from (default https://github.com/<org>/game-factory)
    [ValidateSet('', 'claude', 'codex', 'both')][string]$Agent = '',   # the coding agent(s); asked when not given
    [string]$ClaudeDir = (Join-Path $env:USERPROFILE '.claude'),
    [string]$CodexDir,                 # default: CODEX_HOME / %USERPROFILE%\.codex
    [string]$AgentsSkillsDir,          # default: %USERPROFILE%\.agents\skills (Codex's personal skills)
    [string]$HooksDir,                 # default: the config's hooks_dir
    [string]$ConfigPath,
    [switch]$SkipFfmpeg
)
$ErrorActionPreference = 'Stop'
$items = New-Object Collections.Generic.List[object]
function Item([string]$Status, [string]$What, [string]$Detail = '', [string]$Todo = '') {
    $items.Add([pscustomobject]@{ status = $Status; what = $What; detail = $Detail; todo = $Todo })
    $c = @{ PASS = 'Green'; TODO = 'Yellow'; INFO = 'DarkGray'; SKIP = 'DarkGray' }[$Status]
    Write-Host ("  [{0}] {1}{2}" -f $Status, $What, $(if ($Detail) { " - $Detail" } else { '' })) -ForegroundColor $c
}
$interactive = [Environment]::UserInteractive -and -not [Console]::IsInputRedirected
function Ask([string]$Question, [bool]$Default = $false) {
    if ($Yes) { return $true }
    if (-not $interactive) { return $false }
    $hint = if ($Default) { '[Y/n]' } else { '[y/N]' }
    $a = (Read-Host "  $Question $hint").Trim()
    if (-not $a) { return $Default }
    return ($a -match '^(y|yes)$')
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Has([string]$Cmd) { [bool](Get-Command $Cmd -ErrorAction SilentlyContinue) }
function Quiet([scriptblock]$Body) {
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $out = & $Body 2>&1 | ForEach-Object { "$_" }; return [pscustomobject]@{ code = $LASTEXITCODE; out = ($out -join "`n") } }
    catch { return [pscustomobject]@{ code = -1; out = $_.Exception.Message } }
    finally { $ErrorActionPreference = $old }
}

# --- where things go -------------------------------------------------------------------------------------------------
if ($ConfigPath) { $env:GF_CONFIG = $ConfigPath }
$cfgFile = if ($env:GF_CONFIG) { $env:GF_CONFIG } else { Join-Path $env:USERPROFILE '.game-factory\config.json' }
$cfgNow = if (Test-Path -LiteralPath $cfgFile) { [IO.File]::ReadAllText($cfgFile) | ConvertFrom-Json } else { $null }
if (-not $Root -and $env:GF_ROOT) { $Root = $env:GF_ROOT }
if (-not $Root -and $cfgNow -and $cfgNow.root) { $Root = [string]$cfgNow.root }
if (-not $Root) {
    $def = Join-Path $env:USERPROFILE 'Work'
    $Root = if ($interactive -and -not $Yes) { $r = (Read-Host "  Machine root for game-factory, games, builds and recordings [$def]").Trim(); if ($r) { $r } else { $def } } else { $def }
}
$Root = [IO.Path]::GetFullPath($Root.TrimEnd('\'))
$setupDir = Join-Path $Root '.setup'
New-Item -ItemType Directory -Force $setupDir | Out-Null
$statePath = Join-Path $setupDir 'state.json'
$state = if (Test-Path -LiteralPath $statePath) { [IO.File]::ReadAllText($statePath) | ConvertFrom-Json } else { [pscustomobject]@{} }
function Save-State([string]$Key, $Value) {
    if ($state.PSObject.Properties[$Key]) { $state.$Key = $Value } else { $state | Add-Member $Key $Value }
    [IO.File]::WriteAllText($statePath, ($state | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding($false)))
}
function Get-State([string]$Key) { if ($state.PSObject.Properties[$Key]) { return $state.$Key } return $null }
try { Start-Transcript -Path (Join-Path $setupDir 'setup.log') -Append | Out-Null } catch { }
Write-Host "game-factory setup: root $Root$(if ($DryRun) { ' (dry run: nothing is installed or changed outside the root)' })"

if (-not $Org -and $cfgNow -and $cfgNow.PSObject.Properties['github_org']) { $Org = [string]$cfgNow.github_org }
if (-not $Org) { $Org = Get-State 'org' }
if (-not $Org -and $interactive) { $Org = (Read-Host '  GitHub organisation (or user) that owns game-factory and the game-<slug> repos').Trim() }
if ($Org) { Save-State 'org' $Org }

# Which coding agent(s): -Agent, else the previous answer, else the config's "agents", else asked (Claude Code, Codex
# or both); a non-interactive run without an answer takes what is installed (bootstrap.ps1 -Agent auto).
if (-not $Agent) { $Agent = [string](Get-State 'agent') }
if (-not $Agent -and $cfgNow -and $cfgNow.PSObject.Properties['agents'] -and @($cfgNow.agents).Count) {
    $Agent = if (@($cfgNow.agents).Count -ge 2) { 'both' } else { [string]@($cfgNow.agents)[0] }
}
if (-not $Agent -and $interactive -and -not $Yes) {
    $a = (Read-Host '  Coding agent: claude (Claude Code), codex (OpenAI Codex CLI) or both [claude]').Trim().ToLower()
    $Agent = if ($a -in 'codex', 'both') { $a } else { 'claude' }
}
if ($Agent) { Save-State 'agent' $Agent }
$useClaude = $Agent -in '', 'claude', 'both'
$useCodex = $Agent -in 'codex', 'both'
Write-Host "  agent: $(if ($Agent) { $Agent } else { 'auto (what is installed)' })"

# --- 1. hardware -------------------------------------------------------------------------------------------------------
Write-Host "1. hardware (minimums: Windows 11, 8 threads, 16 GB RAM, 300 GB free; NVIDIA for recording)"
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
if ($build -ge 22000) { Item PASS 'Windows' "$($os.Caption) build $build" } else { Item TODO 'Windows' "$($os.Caption) build $build" 'Windows 11 is required (UE 5.7 toolchain, ddagrab capture)' }
$cs = Get-CimInstance Win32_ComputerSystem
$ram = [math]::Round($cs.TotalPhysicalMemory / 1GB)
$cores = [int]$cs.NumberOfLogicalProcessors
if ($cores -ge 8) { Item PASS 'CPU' "$cores logical cores" } else { Item TODO 'CPU' "$cores logical cores" 'at least 8 logical cores (UE builds are slow and the job limiter allows one job)' }
if ($ram -ge 32) { Item PASS 'Memory' "$ram GB" } elseif ($ram -ge 16) { Item PASS 'Memory' "$ram GB (32 GB recommended; fewer parallel jobs)" } else { Item TODO 'Memory' "$ram GB" 'at least 16 GB RAM (32 GB recommended)' }
$drive = (Split-Path -Qualifier $Root).TrimEnd(':')
$free = [math]::Round((Get-PSDrive -Name $drive).Free / 1GB)
if ($free -ge 300) { Item PASS 'Free disk' "$free GB on ${drive}:" }
elseif ($free -ge 150) { Item PASS 'Free disk' "$free GB on ${drive}: (300 GB recommended)" }
else { Item TODO 'Free disk' "$free GB on ${drive}:" "free space or pick a roomier drive (-Root <drive>:\Work): at least 150 GB, 300 GB recommended" }
$gpus = @(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch 'Microsoft Basic|Remote|Virtual' })
$nv = @($gpus | Where-Object { $_.Name -match 'NVIDIA' })
Item $(if ($gpus) { 'PASS' } else { 'TODO' }) 'GPU' $(if ($gpus) { ($gpus.Name -join ', ') } else { 'no display adapter found' }) 'a DirectX 12 GPU for the Unreal editor'
if (-not $nv) { Item INFO 'NVIDIA GPU' 'none: building works; recording falls back to AMF / CPU encoding (slower)' }

# --- 2. software -----------------------------------------------------------------------------------------------------
Write-Host "2. software (winget)"
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
function Get-VsInstall { if (Test-Path $vswhere) { @(& $vswhere -all -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath) | Select-Object -First 1 } }
function Test-Msvc1444 { $vs = Get-VsInstall; [bool]($vs -and (Get-ChildItem (Join-Path $vs 'VC\Tools\MSVC') -Directory -Filter '14.44.*' -ErrorAction SilentlyContinue)) }
function Test-Sdk22621 { Test-Path "${env:ProgramFiles(x86)}\Windows Kits\10\Include\10.0.22621.0" }
function Test-NetFx481 { (Test-Path "${env:ProgramFiles(x86)}\Windows Kits\NETFXSDK\4.8.1") -and (Test-Path "${env:ProgramFiles(x86)}\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8.1") }
function Test-Python { foreach ($c in @('py -3.12', 'python')) { $r = Quiet { Invoke-Expression "$c -c `"import sys; print(sys.version_info[1])`"" }; if ($r.code -eq 0 -and $r.out -match '^\d+$' -and [int]$r.out -ge 10) { return $true } }; return $false }
$vsAdd = '--add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621 --includeRecommended'
$packages = @(
    @{ id = 'Git.Git'; name = 'Git'; test = { Has git } },
    @{ id = 'GitHub.GitLFS'; name = 'Git LFS'; test = { (Has git) -and (Quiet { git lfs version }).code -eq 0 } },
    @{ id = 'GitHub.cli'; name = 'GitHub CLI'; test = { Has gh } },
    @{ id = 'Python.Python.3.12'; name = 'Python 3.12'; test = { Test-Python } },
    @{ id = 'Microsoft.VisualStudio.2022.BuildTools'; name = 'VS 2022 Build Tools (C++, MSVC 14.44, Windows 11 SDK 22621)'; test = { [bool](Get-VsInstall) -and (Test-Msvc1444) -and (Test-Sdk22621) }
       override = "--wait --quiet --norestart --nocache $vsAdd" },
    @{ id = 'Microsoft.DotNet.Framework.DeveloperPack_4'; name = '.NET Framework 4.8.1 Developer Pack'; test = { Test-NetFx481 } },
    @{ id = '7zip.7zip'; name = '7-Zip'; test = { (Has 7z) -or (Test-Path "$env:ProgramFiles\7-Zip\7z.exe") } },
    @{ id = 'EpicGames.EpicGamesLauncher'; name = 'Epic Games Launcher'; test = { (Test-Path "${env:ProgramFiles(x86)}\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe") -or (Test-Path "$env:ProgramFiles\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe") } },
    @{ id = 'Anthropic.Claude'; name = 'Claude desktop app (optional: Code tab, coordinator mode)'; optional = $true; agent = 'claude'; test = { (Test-Path "$env:LOCALAPPDATA\AnthropicClaude\claude.exe") -or [bool](Get-AppxPackage -Name '*Claude*' -ErrorAction SilentlyContinue) } },
    @{ id = 'OpenAI.Codex'; name = 'Codex CLI (OpenAI)'; agent = 'codex'; test = { Has codex } }
)
$packages = @($packages | Where-Object { -not $_.agent -or ($_.agent -eq 'claude' -and $useClaude) -or ($_.agent -eq 'codex' -and $useCodex) })
$missing = @($packages | Where-Object { -not (& $_.test) })
foreach ($p in $packages) { if ($missing -notcontains $p) { Item PASS $p.name 'installed' } }
if ($missing) {
    $hasWinget = Has winget
    if (-not $hasWinget) { Item TODO 'winget' 'not found' 'install "App Installer" from the Microsoft Store, then run setup again' }
    Write-Host ("  missing: " + (($missing | ForEach-Object { $_.name }) -join '; '))
    $want = @($missing | Where-Object { -not $_.optional })
    $opt = @($missing | Where-Object { $_.optional })
    $go = $hasWinget -and -not $DryRun -and $want -and (Ask "Install these with winget (accepting each package's licence; some show a UAC prompt)?" $true)
    $goOpt = $hasWinget -and -not $DryRun -and $opt -and (Ask "Also install: $(($opt | ForEach-Object { $_.name }) -join ', ')?" $false)
    foreach ($p in $missing) {
        $run = if ($p.optional) { $goOpt } else { $go }
        if (-not $run) { Item TODO $p.name $(if ($DryRun) { 'missing (dry run)' } else { 'missing' }) "winget install -e --id $($p.id)"; continue }
        # A Build Tools install that lacks components: the VS Installer adds them (winget would see it as installed).
        $vs = if ($p.id -like '*BuildTools') { Get-VsInstall } else { $null }
        if ($vs) {
            Write-Host "  adding C++ components to $vs (UAC prompt)..."
            $inst = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\setup.exe"
            Start-Process $inst -ArgumentList "modify --installPath `"$vs`" $vsAdd --quiet --norestart --wait" -Verb RunAs -Wait
        } else {
            Write-Host "  winget install $($p.id) ..."
            $wa = @('install', '-e', '--id', $p.id, '--accept-package-agreements', '--accept-source-agreements', '--silent')
            if ($p.override) { $wa += @('--override', $p.override) }
            & winget @wa | Out-Host
        }
        Refresh-Path
        if (& $p.test) { Item PASS $p.name 'installed now' } else { Item TODO $p.name 'install did not complete' "winget install -e --id $($p.id) (or re-run setup; a reboot may be needed)" }
    }
}
if (Has git) {
    if (-not (Quiet { git config --get filter.lfs.process }).out) { if (-not $DryRun) { Quiet { git lfs install --skip-repo } | Out-Null } }
}

# --- 3. Windows settings ------------------------------------------------------------------------------------------------
Write-Host "3. Windows settings"
$lp = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
if ($lp -eq 1) { Item PASS 'Long paths' 'enabled' }
elseif ($DryRun -or (Get-State 'long_paths') -eq 'declined') { Item TODO 'Long paths' 'off' 'optional: as admin, Set-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem LongPathsEnabled 1 (store packs nest deeply)' }
elseif (Ask 'Enable Windows long paths (store packs nest deeply; one UAC prompt)?' $true) {
    Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile', '-Command', "Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1 -Type DWord"
    $lp = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
    if ($lp -eq 1) { Item PASS 'Long paths' 'enabled now' } else { Item TODO 'Long paths' 'still off' 'run setup again and accept the UAC prompt' }
} else { Save-State 'long_paths' 'declined'; Item SKIP 'Long paths' 'declined (keep the root short, e.g. C:\Work)' }
function Get-AcMinutes([string]$Sub, [string]$Setting) {
    $r = Quiet { powercfg /query SCHEME_CURRENT $Sub $Setting }
    $hex = @([regex]::Matches($r.out, '0x[0-9a-fA-F]{8}') | ForEach-Object { $_.Value })
    if ($hex.Count -lt 2) { return $null }; return [int]([Convert]::ToInt32($hex[-2], 16) / 60)
}
$sleep = Get-AcMinutes 'SUB_SLEEP' 'STANDBYIDLE'; $disp = Get-AcMinutes 'SUB_VIDEO' 'VIDEOIDLE'
if ($sleep -eq 0 -and $disp -eq 0) { Item PASS 'No sleep while plugged in' 'PC and display: never (AC)' }
elseif ($DryRun -or (Get-State 'power') -eq 'declined') { Item TODO 'No sleep while plugged in' "PC sleeps after $sleep min, display after $disp min (AC)" 'powercfg /change standby-timeout-ac 0; powercfg /change monitor-timeout-ac 0' }
elseif (Ask "Set the PC and display to never sleep while plugged in (long builds, overnight queues; now $sleep / $disp min)?" $true) {
    Quiet { powercfg /change standby-timeout-ac 0 } | Out-Null; Quiet { powercfg /change monitor-timeout-ac 0 } | Out-Null
    Item PASS 'No sleep while plugged in' 'set (AC: never)'
} else { Save-State 'power' 'declined'; Item SKIP 'No sleep while plugged in' 'declined' }

# --- 4. GitHub sign-in and git identity ------------------------------------------------------------------------------
Write-Host "4. GitHub and git"
$ghOk = $false
if (Has gh) {
    $ghOk = (Quiet { gh auth status }).code -eq 0
    if (-not $ghOk -and -not $DryRun -and $interactive) {
        Write-Host '  GitHub sign-in: a browser page opens; sign in with the account that is a member of the org.'
        & gh auth login --hostname github.com --git-protocol https --web
        $ghOk = (Quiet { gh auth status }).code -eq 0
    }
    if ($ghOk) { if (-not $DryRun) { Quiet { gh auth setup-git } | Out-Null }; Item PASS 'GitHub sign-in' (Quiet { gh api user --jq .login }).out }
    else { Item TODO 'GitHub sign-in' 'not signed in' 'gh auth login --web (then run setup again)' }
} else { Item TODO 'GitHub sign-in' 'needs the GitHub CLI' 'install it (step 2), then run setup again' }
if (Has git) {
    foreach ($k in 'user.name', 'user.email') {
        $v = (Quiet { git config --global --get $k }).out
        if (-not $v -and -not $DryRun -and $interactive -and -not $Yes) { $v = (Read-Host "  git $k (for your commits)").Trim(); if ($v) { Quiet { git config --global $k $v } | Out-Null } }
        if ($v) { Item PASS "git $k" $v } else { Item TODO "git $k" 'not set' "git config --global $k `"<value>`"" }
    }
}
if ($useCodex) {
    # Codex sign-in: `codex login status` exits 0 when signed in (ChatGPT account or API key).
    if (-not (Has codex)) { Item TODO 'Codex sign-in' 'needs the Codex CLI' 'install it (step 2), then run setup again' }
    else {
        $cxOk = (Quiet { codex login status }).code -eq 0
        if (-not $cxOk -and -not $DryRun -and $interactive) {
            Write-Host '  Codex sign-in: a browser page opens; sign in with the ChatGPT account (or the API key) you were given.'
            & codex login
            $cxOk = (Quiet { codex login status }).code -eq 0
        }
        if ($cxOk) { Item PASS 'Codex sign-in' ((Quiet { codex login status }).out -split "`n")[0] }
        else { Item TODO 'Codex sign-in' 'not signed in' 'codex login (or codex login --device-auth), then run setup again' }
    }
}
if (-not $Org) { Item TODO 'GitHub org' 'not set' 'run setup again with -Org <org> (the organisation or user that owns game-factory)' }
elseif ($ghOk) {
    $see = (Quiet { gh repo view "$Org/game-factory" --json name }).code -eq 0
    if ($see) { Item PASS 'GitHub org' "$Org/game-factory visible" } else { Item TODO 'GitHub org' "cannot see $Org/game-factory" "ask an owner of $Org to add your account (with rights to create private repos)" }
}

# --- 5. game-factory, bootstrap, check ---------------------------------------------------------------------------------
Write-Host "5. game-factory"
$here = Split-Path $PSScriptRoot -Parent
$inClone = (Test-Path (Join-Path $here 'machine\bootstrap.ps1')) -and (Test-Path (Join-Path $here '.git'))
$repo = if ($inClone) { $here } else { Join-Path $Root 'game-factory' }
if (-not (Test-Path (Join-Path $repo 'machine\bootstrap.ps1'))) {
    $src = if ($RepoUrl) { $RepoUrl } elseif ($Org) { "https://github.com/$Org/game-factory.git" } else { $null }
    if (-not $src -or -not (Has git) -or ($src -like 'https://github.com/*' -and -not $ghOk)) { Item TODO 'game-factory clone' "not at $repo" 'needs git, GitHub sign-in and the org (steps above); then run setup again' }
    elseif ($DryRun -and -not $RepoUrl) { Item TODO 'game-factory clone' "would clone $src into $repo (dry run)" '' }
    else {
        Write-Host "  cloning $src into $repo ..."
        $r = Quiet { git clone --quiet $src $repo }
        if ($r.code -eq 0) { Item PASS 'game-factory clone' $repo } else { Item TODO 'game-factory clone' "git clone failed: $($r.out)" "git clone $src $repo" }
    }
} else { Item PASS 'game-factory clone' $repo }
$bootstrapOk = $false
if (Test-Path (Join-Path $repo 'machine\bootstrap.ps1')) {
    $clone = $CloneGames.IsPresent
    if (-not $clone) {
        $prev = Get-State 'clone_games'
        if ($null -ne $prev) { $clone = [bool]$prev }
        elseif ($interactive -and -not $DryRun) {
            $clone = Ask "Clone every $Org/game-* repo into $Root\games now (each brings its store packs; 3-16 GB each)?" $false
            Save-State 'clone_games' $clone
        }
    }
    $ba = [ordered]@{ Root = $Root; ClaudeDir = $ClaudeDir }
    if ($Agent) { $ba.Agent = $Agent }
    if ($CodexDir) { $ba.CodexDir = $CodexDir }
    if ($AgentsSkillsDir) { $ba.AgentsSkillsDir = $AgentsSkillsDir }
    if ($HooksDir) { $ba.HooksDir = $HooksDir }
    if ($Org) { $ba.Org = $Org }
    if ($env:GF_CONFIG) { $ba.ConfigPath = $env:GF_CONFIG }
    if ($Yes) { $ba.Yes = $true }
    if ($clone -and -not $DryRun) { $ba.CloneGames = $true }
    if ($SkipFfmpeg) { $ba.SkipFfmpeg = $true }
    Write-Host "  machine\bootstrap.ps1 ..."
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'machine\bootstrap.ps1') @(foreach ($k in $ba.Keys) { if ($ba[$k] -is [bool]) { "-$k" } else { "-$k"; $ba[$k] } })
    $bootstrapOk = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $old
    if ($bootstrapOk) { Item PASS 'bootstrap.ps1' 'done (its warnings are above)' } else { Item TODO 'bootstrap.ps1' "exit $LASTEXITCODE" 'read the bootstrap output above, fix, run setup again' }
}

# --- 6. what cannot be scripted -------------------------------------------------------------------------------------------
Write-Host "6. sign-ins and installs only you can do"
$engine = if ($cfgNow -and $cfgNow.engine) { [string]$cfgNow.engine } else { 'C:\Program Files\Epic Games\UE_5.7' }
$cfgNew = if (Test-Path -LiteralPath $cfgFile) { [IO.File]::ReadAllText($cfgFile) | ConvertFrom-Json } else { $null }
if ($cfgNew -and $cfgNew.engine) { $engine = [string]$cfgNew.engine }
$bv = Join-Path $engine 'Engine\Build\Build.version'
$ue = if (Test-Path $bv) { [IO.File]::ReadAllText($bv) | ConvertFrom-Json } else { $null }
if ($ue -and $ue.MajorVersion -eq 5 -and $ue.MinorVersion -eq 7) { Item PASS 'Unreal Engine 5.7' "5.7.$($ue.PatchVersion) at $engine" }
else {
    Item TODO 'Unreal Engine 5.7' "not at $engine" ("open the Epic Games Launcher, sign in (create an Epic account if needed), Unreal Engine > Library > " +
        "Engine Versions > + > 5.7 > Install, location $(Split-Path $engine -Parent) (about 60 GB; the default options are enough). Then run setup again.")
}
if ($nv) {
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    $drv = if ($smi) { [double](((Quiet { & $smi.Source --query-gpu=driver_version --format=csv,noheader }).out -split "`n")[0] -replace '[^\d.]', '') } else { 0 }
    if ($drv -ge 610) { Item PASS 'NVIDIA driver' "$drv" } else { Item TODO 'NVIDIA driver' $(if ($drv) { "$drv" } else { 'nvidia-smi not found' }) 'install the current Game Ready or Studio driver (610 or newer) from nvidia.com/drivers or the NVIDIA app, then run setup again' }
}
Item INFO 'Fab sign-in' 'only to download store packs for a NEW game: sign in at fab.com (Epic account) in the browser the asset-scout session uses; cloned games already carry their packs'
if ($useClaude) { Item INFO 'Claude Code sign-in' 'run claude once (or open the desktop app) and sign in with your account; not detectable' }
Item INFO 'First session' "start Claude Code (claude) or Codex (codex) in $Root and paste the brief (docs/new-machine.md, 'The first session')"


# --- check + summary -----------------------------------------------------------------------------------------------------
$check = Join-Path $repo 'machine\check.ps1'
if (Test-Path $check) {
    Write-Host "7. machine\check.ps1"
    $json = Join-Path $setupDir 'check.json'
    $ca = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $check, '-Root', $Root, '-ClaudeDir', $ClaudeDir, '-Json', $json)
    if ($CodexDir) { $ca += @('-CodexDir', $CodexDir) }
    if ($AgentsSkillsDir) { $ca += @('-AgentsSkillsDir', $AgentsSkillsDir) }
    if ($HooksDir) { $ca += @('-HooksDir', $HooksDir) }
    if ($env:GF_CONFIG) { $ca += @('-ConfigPath', $env:GF_CONFIG) }
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    & powershell @ca | Out-Null
    $ErrorActionPreference = $old
    if (Test-Path $json) {
        $cr = [IO.File]::ReadAllText($json) | ConvertFrom-Json
        # check.ps1 rows that setup already reported above (same subject under setup's name)
        $same = @{ 'Unreal Engine 5.7' = 'Unreal Engine 5.7'; 'Long paths' = 'Long paths'; 'System sleep off' = 'No sleep while plugged in'
                   'Display sleep off' = 'No sleep while plugged in'; 'GitHub CLI' = 'GitHub sign-in'; 'NVIDIA driver >= 610' = 'NVIDIA driver'; 'Memory' = 'Memory'
                   'Codex' = 'Codex sign-in' }
        $known = @($items | ForEach-Object { $_.what })
        foreach ($r in $cr.results) {
            if ($r.status -eq 'PASS') { continue }
            if ($same.ContainsKey($r.check) -and $known -contains $same[$r.check]) { continue }
            $st = if ($r.status -eq 'FAIL') { 'TODO' } else { 'INFO' }
            Item $st "check: $($r.check)" $r.detail $r.fix
        }
        Item $(if ($cr.fail -eq 0) { 'PASS' } else { 'TODO' }) 'check.ps1' "$($cr.fail) FAIL, $($cr.warn) WARN (full report: $json)"
    }
}
Write-Host ""
Write-Host "game-factory setup summary (root $Root)"
$todo = @($items | Where-Object status -eq 'TODO')
foreach ($i in $items | Where-Object { $_.status -in 'PASS', 'TODO' }) {
    Write-Host ("  {0}  {1,-36} {2}" -f $i.status, $i.what, $i.detail) -ForegroundColor $(if ($i.status -eq 'PASS') { 'Green' } else { 'Yellow' })
    if ($i.status -eq 'TODO' -and $i.todo) { Write-Host ("        -> {0}" -f $i.todo) -ForegroundColor DarkGray }
}
foreach ($i in $items | Where-Object status -eq 'INFO') { Write-Host ("  note  {0}: {1}{2}" -f $i.what, $i.detail, $(if ($i.todo) { " ($($i.todo))" } else { '' })) -ForegroundColor DarkGray }
Write-Host ""
if ($todo) { Write-Host "$($todo.Count) TODO. Do them, then run setup again: it picks up where it stopped. Log: $setupDir\setup.log" -ForegroundColor Yellow }
else { Write-Host "Ready. Next: the first session (docs/new-machine.md, 'First session'). Log: $setupDir\setup.log" -ForegroundColor Green }
[IO.File]::WriteAllText((Join-Path $setupDir 'summary.json'), ([ordered]@{ time = (Get-Date).ToString('o'); root = $Root; todo = $todo.Count; items = $items } | ConvertTo-Json -Depth 4), (New-Object Text.UTF8Encoding($false)))
try { Stop-Transcript | Out-Null } catch { }
exit $todo.Count

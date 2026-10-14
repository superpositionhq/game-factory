# Machine root for game-factory tooling. Dot-source it; Windows PowerShell 5.1 compatible.
#
# Everything machine-specific hangs off one root (the "Work" folder holding games\, builds\, recordings\, .recording\,
# deliverables\, asset-library\, tools\ and the game-factory clone). Resolution order:
#   1. $env:GF_ROOT
#   2. "root" in the config file: $env:GF_CONFIG, else %USERPROFILE%\.game-factory\config.json (bootstrap.ps1 writes it)
#   3. %USERPROFILE%\Work (the original machine's layout)
# The same config file also holds "ueb" (private build clones, outside the user profile so the user name is not compiled
# into Shipping exes), "engine" (the UE root new games use; Get-GFEngine picks each project's own), optional "engines"
# ({"5.3": "<UE root>", ...}) and "record_extra_projects" (top-level folders under the root that the recording hooks
# treat as projects besides games\<slug>). Installed copies of the hooks and ue-heavy.ps1 carry a copy of this file
# next to them.

function Get-GFConfigPath {
    if ($env:GF_CONFIG) { return $env:GF_CONFIG }
    return (Join-Path $env:USERPROFILE '.game-factory\config.json')
}

function Get-GFConfig {
    $cfg = [ordered]@{
        root                  = (Join-Path $env:USERPROFILE 'Work')
        ueb                   = 'C:\UEB'
        engine                = 'C:\Program Files\Epic Games\UE_5.7'
        record_extra_projects = @()
    }
    $path = Get-GFConfigPath
    if (Test-Path -LiteralPath $path) {
        $json = [IO.File]::ReadAllText($path) | ConvertFrom-Json
        foreach ($p in $json.PSObject.Properties) { $cfg[$p.Name] = $p.Value }
    }
    if ($env:GF_ROOT) { $cfg.root = $env:GF_ROOT }
    foreach ($k in 'root', 'ueb', 'engine') {
        $v = ([string]$cfg[$k]).TrimEnd('\', '/')
        if ($v -match '^[A-Za-z]:$') { $v += '\' }
        $cfg[$k] = [IO.Path]::GetFullPath($v)
    }
    $cfg.record_extra_projects = @($cfg.record_extra_projects | Where-Object { $_ })
    return [pscustomobject]$cfg
}

function Get-GFRoot { return (Get-GFConfig).root }

# The UE root for a project: its .uproject's EngineAssociation ("5.3", "5.7", ...) picks the install, so a game made on
# an older engine keeps building, recording and replaying on it. Order: "engines" in the config, then the UE_<version>
# folder next to "engine", then the Epic Games Launcher's registry entry, then "engine". $Project is a .uproject or the
# folder holding one; without one, or without a version-number association, the answer is "engine".
function Get-GFEngine([string]$Project, $Cfg = (Get-GFConfig)) {
    $assoc = ''
    if ($Project) {
        $up = if ($Project -like '*.uproject') { $Project } else {
            Get-ChildItem -LiteralPath $Project -Filter *.uproject -File -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
        }
        if ($up -and (Test-Path -LiteralPath $up)) { $assoc = [string]([IO.File]::ReadAllText($up) | ConvertFrom-Json).EngineAssociation }
    }
    return (Get-GFEngineForVersion $assoc $Cfg)
}

# The UE root for an engine version ("5.3"): the same order as Get-GFEngine; "engine" when nothing else names one.
function Get-GFEngineForVersion([string]$Version, $Cfg = (Get-GFConfig)) {
    if ($Version -notmatch '^\d+\.\d+$') { return $Cfg.engine }
    if ($Cfg.PSObject.Properties['engines'] -and $Cfg.engines -and $Cfg.engines.PSObject.Properties[$Version]) {
        return [IO.Path]::GetFullPath(([string]$Cfg.engines.$Version).TrimEnd('\', '/'))
    }
    $sibling = Join-Path (Split-Path $Cfg.engine -Parent) "UE_$Version"
    if (Test-Path -LiteralPath (Join-Path $sibling 'Engine\Binaries\Win64')) { return $sibling }
    $reg = Get-ItemProperty -LiteralPath "HKLM:\SOFTWARE\EpicGames\Unreal Engine\$Version" -ErrorAction SilentlyContinue
    if ($reg -and $reg.PSObject.Properties['InstalledDirectory'] -and $reg.InstalledDirectory) { return $reg.InstalledDirectory.TrimEnd('\') }
    return $Cfg.engine
}

# Output root for packages, dataset zips and their staging folders: $env:GF_OUT, else "out" in the config file, else
# <root>\deliverables. Point it at a roomy drive (packages and zips run to tens of GB per game).
function Get-GFOut {
    if ($env:GF_OUT) { return [IO.Path]::GetFullPath($env:GF_OUT.TrimEnd('\', '/')) }
    $cfg = Get-GFConfig
    if ($cfg.PSObject.Properties['out'] -and $cfg.out) { return [IO.Path]::GetFullPath(([string]$cfg.out).TrimEnd('\', '/')) }
    return (Join-Path $cfg.root 'deliverables')
}

# Refuse to start a disk-heavy job (packaging, creation replay) when the drive holding $Path has less than the floor
# free: $env:GF_MIN_FREE_GB, else "min_free_gb" in the config file, else 50. A full disk mid-job corrupts the result.
function Assert-GFFreeSpace([string]$Path, [string]$What = 'this job') {
    $min = 50
    $cfg = Get-GFConfig
    if ($cfg.PSObject.Properties['min_free_gb'] -and $cfg.min_free_gb) { $min = [double]$cfg.min_free_gb }
    if ($env:GF_MIN_FREE_GB) { $min = [double]$env:GF_MIN_FREE_GB }
    $full = [IO.Path]::GetFullPath($Path)
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($full))
    $free = [math]::Round($drive.AvailableFreeSpace / 1GB, 1)
    if ($free -lt $min) {
        throw ("{0}: only {1} GB free on {2} (floor {3} GB; GF_MIN_FREE_GB / min_free_gb). Free space or point GF_OUT / work_root at another drive." -f $What, $free, $drive.Name, $min)
    }
    return $free
}

# Regex matching a path under the root in the spellings tool calls use: C:\a\b, C:/a/b, /c/a/b (Git Bash), /mnt/c/a/b.
# Append the part after the root yourself, e.g. (Get-GFRootPattern) + '[\\/]+games[\\/]+([A-Za-z0-9_-]+)'.
function Get-GFRootPattern([string]$Root = (Get-GFRoot)) {
    $full = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $drive = $full.Substring(0, 1)
    $rest = @($full.Substring(2).Split('\') | Where-Object { $_ } | ForEach-Object { [regex]::Escape($_) })
    $head = "(?:$drive`:|/$drive|/mnt/$drive)"
    if ($rest.Count -eq 0) { return "(?i)$head" }
    return "(?i)$head[\\/]+" + ($rest -join '[\\/]+')
}

# Machine-wide job slots (ue-heavy.ps1, tools/ue-pipeline/common.ps1). Config keys win: heavy_slots (general slots:
# builds, cooks, headless editor runs; GPU jobs hold one too), gpu_slots (concurrent rendering jobs; a recording takes
# all of them), gpu_vram_limit_mb (a GPU job starts only while less VRAM than this is in use; default half the VRAM).
# Without them the slots are computed from the hardware (bootstrap.ps1 writes the computed values to the config):
#   heavy_slots = clamp(1..8, min(floor((RAM GB - 6) / 6), floor(logical cores / 4), floor((commit limit GB - 6) / 8)))
#                 (~6 GB per heavy Unreal process, 6 GB kept for the desktop and the sessions)
#   gpu_slots   = clamp(1..4, min(floor(VRAM GB of the largest NVIDIA GPU / 4), heavy_slots - 1)); 1 without nvidia-smi
#                 (~4 GB per renderer; one general slot always left for compiles)
function Get-GFHardware {
    $cs = Get-CimInstance Win32_ComputerSystem
    $os = Get-CimInstance Win32_OperatingSystem
    $vram = @()
    try {
        $out = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null
        $vram = @($out | ForEach-Object { "$_".Trim() } | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ })
    } catch { }
    [pscustomobject]@{
        logical_cores = [int]$cs.NumberOfLogicalProcessors
        ram_gb        = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
        commit_gb     = [math]::Round($os.TotalVirtualMemorySize / 1MB, 1)
        gpu_count     = $vram.Count
        vram_mb       = $(if ($vram.Count) { ($vram | Measure-Object -Maximum).Maximum } else { 0 })
    }
}

function Get-GFComputedSlots($Hw = (Get-GFHardware)) {
    $heavy = [math]::Min([math]::Floor(($Hw.ram_gb - 6) / 6), [math]::Floor($Hw.logical_cores / 4))
    $heavy = [math]::Min($heavy, [math]::Floor(($Hw.commit_gb - 6) / 8))
    $heavy = [int][math]::Max(1, [math]::Min(8, $heavy))
    $gpu = if ($Hw.vram_mb -gt 0) { [math]::Min([math]::Floor($Hw.vram_mb / 1024 / 4), $heavy - 1) } else { 1 }
    $gpu = [int][math]::Max(1, [math]::Min(4, $gpu))
    [pscustomobject]@{ heavy_slots = $heavy; gpu_slots = $gpu; hardware = $Hw }
}

# The slots in effect and where each comes from: 'config' (set by hand), 'config (bootstrap)' (written by bootstrap.ps1
# from the formula, recorded in slots_auto), or 'computed' (no config key: the formula at run time).
function Get-GFSlotPlan($Cfg = (Get-GFConfig)) {
    $auto = if ($Cfg.PSObject.Properties['slots_auto']) { $Cfg.slots_auto } else { $null }
    $computed = $null
    $plan = [ordered]@{}
    foreach ($k in 'heavy_slots', 'gpu_slots') {
        if ($Cfg.PSObject.Properties[$k] -and [int]$Cfg.$k -gt 0) {
            $plan[$k] = [int]$Cfg.$k
            $plan["${k}_source"] = if ($auto -and $auto.PSObject.Properties[$k] -and [int]$auto.$k -eq [int]$Cfg.$k) { 'config (bootstrap)' } else { 'config' }
        } else {
            if (-not $computed) { $computed = Get-GFComputedSlots }
            $plan[$k] = $computed.$k
            $plan["${k}_source"] = 'computed'
        }
    }
    $plan['gpu_vram_limit_mb'] = if ($Cfg.PSObject.Properties['gpu_vram_limit_mb'] -and [int]$Cfg.gpu_vram_limit_mb -gt 0) { [int]$Cfg.gpu_vram_limit_mb } else { 0 }
    [pscustomobject]$plan
}

# ---- machine-wide job slots: one named mutex per slot (ue-heavy.ps1, tools/ue-pipeline/common.ps1) -----------------------
# A slot is the mutex Global\ue-heavy-slot-<n> (general) or Global\ue-gpu-slot-<n> (GPU), n < heavy_slots / gpu_slots.
# Unlike a counted semaphore nothing leaks: a holder that dies without releasing (killed job, crashed UAT) leaves its
# mutex "abandoned", and the next taker gets it. The count is the config's at every call, so a new heavy_slots or
# gpu_slots takes effect at once. A mutex belongs to the thread that took it: take and release it in the same script.
function Get-GFSlotMutexes([ValidateSet('heavy', 'gpu')][string]$Kind, [int]$Count) {
    $prefix = if ($Kind -eq 'gpu') { 'Global\ue-gpu-slot-' } else { 'Global\ue-heavy-slot-' }
    , @(for ($i = 0; $i -lt $Count; $i++) { New-Object Threading.Mutex($false, "$prefix$i") })
}

# Take a mutex within TimeoutMs; an abandoned one (its holder died) is taken over. $true when held.
function Enter-GFMutex($Mutex, [int]$TimeoutMs = 0) {
    try { return [bool]$Mutex.WaitOne($TimeoutMs) }
    catch {
        $e = $_.Exception
        while ($e -and -not ($e -is [Threading.AbandonedMutexException])) { $e = $e.InnerException }
        if ($e) { return $true }
        throw
    }
}

# One free slot among indices From..Count-1 (Skip: indices this script already holds), without waiting; -1 if none.
function Enter-GFSlot($Mutexes, [int]$From = 0, [int[]]$Skip = @()) {
    for ($i = [math]::Max(0, $From); $i -lt $Mutexes.Count; $i++) {
        if ($Skip -contains $i) { continue }
        if (Enter-GFMutex $Mutexes[$i] 0) { return $i }
    }
    return -1
}

function Exit-GFSlot($Mutexes, [int]$Index) {
    if ($Index -ge 0 -and $Index -lt $Mutexes.Count) { try { $Mutexes[$Index].ReleaseMutex() } catch { } }
}

# Jobs still holding a slot of the old counted semaphores (Global\ue-heavy-jobs-v2 / Global\ue-gpu-jobs-v2, before the
# per-slot mutexes): live processes whose last row in the heavy-jobs log is a 'start' without a "slot" field, plus, for
# the GPU, old GPU waiters (they held a GPU slot while waiting for a general one). New jobs leave that many slots
# unused until those jobs end, so the switch never runs more jobs than the counts allow. @{heavy=n; gpu=n}
function Get-GFLegacySlotHolders([string]$Log) {
    $last = @{}
    try { $lines = Get-Content -LiteralPath $Log -Tail 800 -ErrorAction Stop } catch { return @{ heavy = 0; gpu = 0 } }
    foreach ($l in $lines) {
        try { $r = $l | ConvertFrom-Json } catch { continue }
        if ($r.pid) { $last[[int]$r.pid] = $r }
    }
    $heavy = 0; $gpu = 0
    foreach ($p in $last.Keys) {
        $r = $last[$p]
        if ($r.PSObject.Properties['slot'] -or $r.PSObject.Properties['slots']) { continue }   # a per-slot-mutex job
        if ($r.event -notin @('start', 'wait')) { continue }
        if (-not (Get-Process -Id $p -ErrorAction SilentlyContinue)) { continue }
        if ($r.event -eq 'start') { $heavy++; if ($r.gpu) { $gpu++ } }
        elseif ($r.gpu) { $gpu++ }
    }
    @{ heavy = $heavy; gpu = $gpu }
}

# Run one heavy Unreal job (UBT build, RunUAT, UnrealEditor-Cmd, shader-heavy editor run) under a
# machine-wide limit so the parallel game sessions don't exhaust CPU/RAM. Waits for a free slot.
#   & <root>\tools\ue-heavy.ps1 -Label "TowerDefense editor build" -- "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" TowerDefenseEditor Win64 Development -Project=...
# Exit code is the job's. Waits/acquire/release are appended to <root>\.recording\_heavy-jobs.jsonl.
# <root> is the machine root (machine/lib/gf-root.ps1); machine/bootstrap.ps1 installs this file as <root>\tools\ue-heavy.ps1
# with a copy of gf-root.ps1 next to it.
#
# Slot model (docs/ue-pipeline.md, "Machine-wide slots"):
# - Slots are named mutexes, one per slot (gf-root.ps1 Get-GFSlotMutexes): a job killed before it releases leaves its
#   mutex abandoned and the next job takes it over, so no slot leaks (the counted semaphores of before leaked one per
#   killed job). Jobs started before the change are counted from the log and their number of slots stays unused until
#   they end (Get-GFLegacySlotHolders). Counts are read at every call, so a config change applies at once.
# - General slots (Global\ue-heavy-slot-<n>): every job takes one. Count: "heavy_slots" in the machine config, else the
#   hardware formula in gf-root.ps1 Get-GFComputedSlots (bootstrap.ps1 writes it to the config).
# - GPU slots (Global\ue-gpu-slot-<n>): jobs that render (editor GUI, -game, packaged games; not -nullrhi/-nographics)
#   take one together with a general slot, never one while waiting for the other. Count: "gpu_slots", else the formula.
# - VRAM guard: a GPU job starts only while the GPU's used VRAM is under "gpu_vram_limit_mb" (default half the VRAM) and
#   no other GPU job started in the last 60 s (a new renderer's VRAM shows only once it has loaded); otherwise it gives
#   the slot back and looks again every 30 s (logged as vram_wait).
# - Recordings are exclusive: the recorder takes every GPU slot (tools/ue-pipeline/common.ps1 Enter-GpuSlot -Recording),
#   and while it waits (builds\_queue\_recording-wants-gpu fresh) new GPU jobs hold back or hand their slot back.
# - -Low (background work such as the live creation replay): one low job machine-wide; it takes a general slot only
#   while no other job waits for one and another slot stays free; its process runs below normal priority.
[CmdletBinding(PositionalBinding = $false)]
param(
  [string]$Label = 'ue job',
  [int]$Slots = 0,   # 0: "heavy_slots" in the machine config, else the hardware formula (gf-root.ps1 Get-GFComputedSlots)
  [switch]$Gpu,   # force the GPU slot (auto-detected for editor GUI, -game, packaged games)
  [switch]$Low,   # background work (the live per-commit replay): yields to every other job, one at a time, below-normal priority
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$Command
)
$ErrorActionPreference = 'Continue'
if ($Command.Count -and $Command[0] -eq '--') { $Command = $Command[1..($Command.Count - 1)] }
# PowerShell splits an unquoted `-Project=C:/x.uproject` passed to a script into `-Project=C:` and
# `/x.uproject` (it reads `-Name:` as parameter syntax); glue such pairs back together.
$joined = New-Object Collections.Generic.List[string]
for ($i = 0; $i -lt $Command.Count; $i++) {
  if ($Command[$i] -match '^-[^\s=]+=[A-Za-z]:$' -and $i + 1 -lt $Command.Count -and $Command[$i + 1] -match '^[\\/]') {
    $joined.Add($Command[$i] + $Command[$i + 1]); $i++
  } else { $joined.Add($Command[$i]) }
}
$Command = $joined.ToArray()
if (-not $Command) { Write-Error 'usage: ue-heavy.ps1 -Label <text> -- <exe> <args...>'; exit 2 }
# gf-root.ps1 sits next to the installed copy, or in ..\lib in the repo.
$gfLib = @((Join-Path $PSScriptRoot 'gf-root.ps1'), (Join-Path $PSScriptRoot '..\lib\gf-root.ps1')) | Where-Object { Test-Path $_ } | Select-Object -First 1
$gfRoot = if ($gfLib) { . $gfLib; Get-GFRoot } elseif ($env:GF_ROOT) { $env:GF_ROOT } else { Join-Path $env:USERPROFILE 'Work' }
$plan = if ($gfLib -and (Get-Command Get-GFSlotPlan -ErrorAction SilentlyContinue)) { Get-GFSlotPlan } else { $null }
if ($Slots -le 0) {
  $Slots = if ($plan) { $plan.heavy_slots } else {
    $cores = (@(Get-CimInstance Win32_Processor) | Measure-Object -Property NumberOfCores -Sum).Sum
    [math]::Max(1, [math]::Min(6, [int][math]::Round($cores / 3)))   # an older gf-root.ps1 next to this copy
  }
}
$log = Join-Path $gfRoot '.recording\_heavy-jobs.jsonl'
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
function Log($event, $extra) {
  $row = [ordered]@{ time = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz'); event = $event; label = $Label; pid = $PID; cwd = (Get-Location).Path }
  if ($extra) { foreach ($k in $extra.Keys) { $row[$k] = $extra[$k] } }
  # Several jobs log at once: serialise appends with a named mutex and retry on a transient sharing violation.
  $line = ($row | ConvertTo-Json -Compress) + "`n"
  $m = New-Object Threading.Mutex($false, 'Global\ue-heavy-log')
  [void]$m.WaitOne(10000)
  try {
    for ($i = 0; $i -lt 5; $i++) {
      try { [IO.File]::AppendAllText($log, $line, (New-Object Text.UTF8Encoding($false))); break }
      catch [IO.IOException] { Start-Sleep -Milliseconds (50 * ($i + 1)) }
    }
  } finally { $m.ReleaseMutex() }
}
if (-not (Get-Command Get-GFSlotMutexes -ErrorAction SilentlyContinue)) {
  Write-Error "ue-heavy: $gfLib has no per-slot mutexes (Get-GFSlotMutexes): install machine\lib\gf-root.ps1 next to this script (machine\bootstrap.ps1)"
  exit 2
}
$heavyM = Get-GFSlotMutexes heavy $Slots
$cmdText = $Command -join ' '
$isGpu = $Gpu -or ($Command[0] -match '(?i)UnrealEditor\.exe$|-Shipping\.exe$') -or
  ($cmdText -match '(?i)(^|\s)-game(\s|$)|-AllowCommandletRendering') -or
  ($Command[0] -match '(?i)\\Packaged\\.*\.exe$')
if ($cmdText -match '(?i)-nullrhi|-nographics') { $isGpu = $false }
$gpuSlots = if ($plan) { [math]::Min(8, [int]$plan.gpu_slots) } else { 1 }
$vramLimit = if ($plan) { [int]$plan.gpu_vram_limit_mb } else { 0 }
$gpuM = if ($isGpu) { Get-GFSlotMutexes gpu $gpuSlots } else { $null }
$heavyIdx = -1; $gpuIdx = -1; $lowHeld = $false
function Get-VramMB([string]$What) {
  try { $v = & nvidia-smi "--query-gpu=memory.$What" --format=csv,noheader,nounits 2>$null | Select-Object -First 1 } catch { $v = $null }
  if ("$v".Trim() -match '^\d+$') { return [int]"$v".Trim() } else { return $null }
}
if ($isGpu -and $vramLimit -le 0) { $tot = Get-VramMB 'total'; $vramLimit = if ($tot) { [int]($tot / 2) } else { 8192 } }
$t0 = Get-Date
# "slots":"mutex" marks this script's rows (Get-GFLegacySlotHolders tells them from jobs of the old semaphores)
Log 'wait' @{ command = $cmdText; gpu = [bool]$isGpu; low = [bool]$Low; slots = 'mutex' }
$flag = Join-Path $gfRoot 'builds\_queue\_recording-wants-gpu'
function Test-RecordingWaits { (Test-Path $flag) -and ((Get-Date) - (Get-Item $flag).LastWriteTime).TotalMinutes -lt 20 }
# A GPU job that started in the last minute has not loaded yet: its VRAM does not show, so wait for it to settle.
function Test-VramBusy {
  $script:vramUsed = Get-VramMB 'used'
  $script:vramRecent = $false
  try {
    foreach ($l in (Get-Content -LiteralPath $log -Tail 200 -ErrorAction Stop)) {
      if ($l -notmatch '"event":"start"' -or $l -notmatch '"gpu":true') { continue }
      $r = $l | ConvertFrom-Json
      if ($r.pid -ne $PID -and ((Get-Date) - [datetime]$r.time).TotalSeconds -lt 60) { $script:vramRecent = $true }
    }
  } catch { }
  $script:vramRecent -or ($null -ne $script:vramUsed -and $script:vramUsed -gt $vramLimit)
}
if ($gpuM) {
  # GPU jobs take a GPU slot and a general slot together or not at all: holding the GPU slot while waiting for a
  # general one blocked every other GPU job and left the GPU idle. Recordings have priority: while the recorder has
  # flagged that it waits for the GPU (a fresh _recording-wants-gpu file; one over 20 min old is ignored), session
  # GPU jobs hold back. VRAM guard: start only while the GPU's used VRAM is under the limit (per-process VRAM is not
  # available under WDDM) and no GPU job started in the last minute.
  $nextNote = Get-Date; $nextVramLog = Get-Date
  while ($true) {
    if (Test-RecordingWaits) {
      if ((Get-Date) -ge $nextNote) { Write-Host "[ue-heavy] a recording is waiting for the GPU; holding back since $($t0.ToString('HH:mm:ss'))..."; $nextNote = (Get-Date).AddMinutes(1) }
      Start-Sleep -Seconds 15; continue
    }
    $legacy = Get-GFLegacySlotHolders $log
    $gpuIdx = Enter-GFSlot $gpuM $legacy.gpu
    if ($gpuIdx -ge 0) {
      if (Test-VramBusy) {
        Exit-GFSlot $gpuM $gpuIdx; $gpuIdx = -1
        if ((Get-Date) -ge $nextVramLog) {
          Write-Host "[ue-heavy] $vramUsed MB VRAM in use (limit $vramLimit MB)$(if ($vramRecent) { ', a GPU job started under a minute ago' }): waiting..."
          Log 'vram_wait' @{ gpu = $true; vram_used_mb = $vramUsed; limit_mb = $vramLimit; settling = $vramRecent; slots = 'mutex' }
          $nextVramLog = (Get-Date).AddMinutes(5)
        }
        Start-Sleep -Seconds 30; continue
      }
      $heavyIdx = Enter-GFSlot $heavyM $legacy.heavy
      if ($heavyIdx -ge 0) { break }
      Exit-GFSlot $gpuM $gpuIdx; $gpuIdx = -1
    }
    if ((Get-Date) -ge $nextNote) { Write-Host "[ue-heavy] waiting for a GPU slot ($gpuSlots) and a general slot ($Slots) together since $($t0.ToString('HH:mm:ss'))..."; $nextNote = (Get-Date).AddMinutes(1) }
    Start-Sleep -Seconds 3
  }
}
function Test-OthersWaiting {
  # jobs whose last logged event is 'wait' and whose process still runs (any copy of this script logs the same events)
  $last = @{}
  try { $lines = Get-Content -LiteralPath $log -Tail 400 -ErrorAction Stop } catch { return $false }
  foreach ($l in $lines) {
    try { $r = $l | ConvertFrom-Json } catch { continue }
    # (other low-priority jobs wait for this one, and GPU jobs wait for the GPU slot, not a general one: neither counts;
    # a GPU job that gets the GPU still finds the general slot a low job always leaves free)
    if ($r.pid -and $r.pid -ne $PID) { $last[[int]$r.pid] = if ($r.low -or ($r.event -eq 'wait' -and $r.gpu)) { 'other' } else { $r.event } }
  }
  foreach ($p in $last.Keys) {
    if ($last[$p] -eq 'wait' -and (Get-Process -Id $p -ErrorAction SilentlyContinue)) { return $true }
  }
  return $false
}
$lowM = $null
if ($Low) {
  # Low-priority work never makes another job wait: one low job machine-wide (a mutex, so a killed one does not block
  # the next), and it takes a general slot only while nobody else is waiting and another slot would still be free.
  $lowM = New-Object Threading.Mutex($false, 'Global\ue-heavy-low-slot')
  while (-not (Enter-GFMutex $lowM 60000)) { Write-Host "[ue-heavy] low priority: another low-priority job runs; waiting..." }
  $lowHeld = $true
  while ($true) {
    if (-not (Test-OthersWaiting)) {
      $legacy = Get-GFLegacySlotHolders $log
      $heavyIdx = Enter-GFSlot $heavyM $legacy.heavy
      if ($heavyIdx -ge 0) {
        if ($Slots -lt 2) { break }
        $spare = Enter-GFSlot $heavyM $legacy.heavy @($heavyIdx)
        if ($spare -ge 0) { Exit-GFSlot $heavyM $spare; break }
        Exit-GFSlot $heavyM $heavyIdx; $heavyIdx = -1
      }
    }
    Start-Sleep -Seconds 20
  }
} elseif ($heavyIdx -lt 0) {
  $nextNote = Get-Date
  while ($true) {
    $legacy = Get-GFLegacySlotHolders $log
    $heavyIdx = Enter-GFSlot $heavyM $legacy.heavy
    if ($heavyIdx -ge 0) { break }
    if ((Get-Date) -ge $nextNote) {
      Write-Host "[ue-heavy] waiting for a free slot ($Slots max$(if ($legacy.heavy) { ", $($legacy.heavy) held by jobs started before the per-slot mutexes" })) since $($t0.ToString('HH:mm:ss'))..."
      $nextNote = (Get-Date).AddMinutes(1)
    }
    Start-Sleep -Seconds 3
  }
}
Log 'start' @{ waited_s = [int]((Get-Date) - $t0).TotalSeconds; gpu = [bool]$isGpu; low = [bool]$Low; slot = $heavyIdx; gpu_slot = $(if ($isGpu) { $gpuIdx } else { $null }); vram_used_mb = $(if ($isGpu) { Get-VramMB 'used' } else { $null }) }
$t1 = Get-Date
# Start the process directly and wait for it: `& exe` returns at once for GUI-subsystem programs
# (UnrealEditor.exe -game), which would release the slot while the job still runs. Arguments are
# re-quoted the way UE parses them: -Key="value with spaces" keeps the quotes after '=' (PowerShell
# strips them, and quoting the whole token would make UE read only the first word).
function Quote-Arg([string]$a) {
  if ($a -notmatch '[\s"]') { return $a }
  $m = [regex]::Match($a, '^(-?[^=\s"]+=)(.*)$')
  if ($m.Success) { return $m.Groups[1].Value + '"' + $m.Groups[2].Value.Replace('"', '\"') + '"' }
  return '"' + $a.Replace('"', '\"') + '"'
}
$code = $null
try {
  $exe = $Command[0]
  $argLine = (@($Command | Select-Object -Skip 1) | ForEach-Object { Quote-Arg $_ }) -join ' '
  if ($exe -match '\.(bat|cmd)$') { $argLine = "/c `"`"$exe`" $argLine`""; $exe = "$env:ComSpec" }
  Write-Verbose "exe=[$exe] args=[$argLine]"
  $psi = New-Object Diagnostics.ProcessStartInfo $exe, $argLine
  $psi.UseShellExecute = $false
  $proc = [Diagnostics.Process]::Start($psi)
  if ($Low) { try { $proc.PriorityClass = [Diagnostics.ProcessPriorityClass]::BelowNormal } catch { } }
  $proc.WaitForExit()
  $code = $proc.ExitCode
} finally {
  if ($gpuM) { Exit-GFSlot $gpuM $gpuIdx }
  Exit-GFSlot $heavyM $heavyIdx
  if ($lowHeld) { try { $lowM.ReleaseMutex() } catch { } }
  Log 'end' @{ exit_code = $code; duration_s = [int]((Get-Date) - $t1).TotalSeconds; slots = 'mutex' }
}
exit $code


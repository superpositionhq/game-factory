# Run one heavy Unreal job (UBT build, RunUAT, UnrealEditor-Cmd, shader-heavy editor run) under a
# machine-wide limit so the parallel game sessions don't exhaust CPU/RAM. Waits for a free slot.
#   & <root>\tools\ue-heavy.ps1 -Label "TowerDefense editor build" -- "C:\Program Files\Epic Games\UE_5.3\Engine\Build\BatchFiles\Build.bat" TowerDefenseEditor Win64 Development -Project=...
# Exit code is the job's. Waits/acquire/release are appended to <root>\.recording\_heavy-jobs.jsonl.
# <root> is the machine root (machine/lib/gf-root.ps1); machine/bootstrap.ps1 installs this file as <root>\tools\ue-heavy.ps1
# with a copy of gf-root.ps1 next to it.
#
# Slot model (docs/ue-pipeline.md, "Machine-wide slots"):
# - General slots (Global\ue-heavy-jobs-v2): every job takes one. Count: "heavy_slots" in the machine config, else the
#   hardware formula in gf-root.ps1 Get-GFComputedSlots (bootstrap.ps1 writes it to the config).
# - GPU slots (Global\ue-gpu-jobs-v2): jobs that render (editor GUI, -game, packaged games; not -nullrhi/-nographics) take
#   one FIRST, then a general slot. Count: "gpu_slots", else the same formula.
# - VRAM guard: a GPU job starts only while the GPU's used VRAM is under "gpu_vram_limit_mb" (default half the VRAM) and
#   no other GPU job started in the last 60 s (a new renderer's VRAM shows only once it has loaded); otherwise it gives
#   the slot back and looks again every 30 s (logged as vram_wait).
# - Recordings are exclusive: the recorder takes every GPU slot (tools/ue-pipeline/common.ps1 Enter-GpuSlot -Recording),
#   and while it waits (builds\_queue\_recording-wants-gpu fresh) new GPU jobs hold back or hand their slot back.
# - -Low (background work such as the live creation replay): one low job machine-wide; it takes a general slot only
#   while no other job waits for one and another slot stays free; its process runs below normal priority.
# A named semaphore keeps the count it was created with while any process holds it: a new count takes effect once every
# job holding it has ended (or under a new name; the "-v2" names date from such a change).
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
$sem = New-Object Threading.Semaphore($Slots, $Slots, 'Global\ue-heavy-jobs-v2')
$cmdText = $Command -join ' '
$isGpu = $Gpu -or ($Command[0] -match '(?i)UnrealEditor\.exe$|-Shipping\.exe$') -or
  ($cmdText -match '(?i)(^|\s)-game(\s|$)|-AllowCommandletRendering') -or
  ($Command[0] -match '(?i)\\Packaged\\.*\.exe$')
if ($cmdText -match '(?i)-nullrhi|-nographics') { $isGpu = $false }
$gpuSlots = if ($plan) { [math]::Min(8, [int]$plan.gpu_slots) } else { 1 }
$vramLimit = if ($plan) { [int]$plan.gpu_vram_limit_mb } else { 0 }
$gpuSem = if ($isGpu) { New-Object Threading.Semaphore($gpuSlots, $gpuSlots, 'Global\ue-gpu-jobs-v2') } else { $null }
function Get-VramMB([string]$What) {
  try { $v = & nvidia-smi "--query-gpu=memory.$What" --format=csv,noheader,nounits 2>$null | Select-Object -First 1 } catch { $v = $null }
  if ("$v".Trim() -match '^\d+$') { return [int]"$v".Trim() } else { return $null }
}
if ($isGpu -and $vramLimit -le 0) { $tot = Get-VramMB 'total'; $vramLimit = if ($tot) { [int]($tot / 2) } else { 8192 } }
$t0 = Get-Date
Log 'wait' @{ command = $cmdText; gpu = [bool]$isGpu; low = [bool]$Low }
# GPU jobs get the GPU slot FIRST and only then a general slot, so a job queued behind a recording doesn't sit on
# one of the general (compile) slots the whole time.
if ($gpuSem) {
  # Recordings have priority: while the pipeline has flagged that it is waiting for the GPU (a fresh
  # _recording-wants-gpu file, refreshed by the recorder), session GPU jobs hold back so they don't take the
  # slot first. A stale flag (over 20 min old) is ignored.
  $flag = Join-Path $gfRoot 'builds\_queue\_recording-wants-gpu'
  while ((Test-Path $flag) -and ((Get-Date) - (Get-Item $flag).LastWriteTime).TotalMinutes -lt 20) {
    Write-Host "[ue-heavy] a recording is waiting for the GPU; holding back since $($t0.ToString('HH:mm:ss'))..."
    Start-Sleep -Seconds 15
  }
  $nextVramLog = Get-Date
  while ($true) {
    while (-not $gpuSem.WaitOne(60000)) { Write-Host "[ue-heavy] waiting for a GPU slot ($gpuSlots max; a recording takes all) since $($t0.ToString('HH:mm:ss'))..." }
    # A recording may have started waiting while we were queued: give the slot back and let it go first.
    if ((Test-Path $flag) -and ((Get-Date) - (Get-Item $flag).LastWriteTime).TotalMinutes -lt 20) {
      [void]$gpuSem.Release()
      Write-Host "[ue-heavy] a recording is waiting for the GPU; yielding the slot..."
      Start-Sleep -Seconds 20
      continue
    }
    # VRAM guard: start only while less than the limit is in use (per-process VRAM is not available under WDDM, so
    # this is the GPU's total); otherwise hand the slot back and look again.
    # A GPU job that started in the last minute has not loaded yet: its VRAM does not show, so wait for it to settle.
    $used = Get-VramMB 'used'
    $recent = $false
    try {
      foreach ($l in (Get-Content -LiteralPath $log -Tail 200 -ErrorAction Stop)) {
        if ($l -notmatch '"event":"start"' -or $l -notmatch '"gpu":true') { continue }
        $r = $l | ConvertFrom-Json
        if ($r.pid -ne $PID -and ((Get-Date) - [datetime]$r.time).TotalSeconds -lt 60) { $recent = $true }
      }
    } catch { }
    if ($recent -or ($null -ne $used -and $used -gt $vramLimit)) {
      [void]$gpuSem.Release()
      if ((Get-Date) -ge $nextVramLog) {
        Write-Host "[ue-heavy] $used MB VRAM in use (limit $vramLimit MB)$(if ($recent) { ', a GPU job started under a minute ago' }): waiting..."
        Log 'vram_wait' @{ gpu = $true; vram_used_mb = $used; limit_mb = $vramLimit; settling = $recent }
        $nextVramLog = (Get-Date).AddMinutes(5)
      }
      Start-Sleep -Seconds 30
      continue
    }
    break
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
$lowSem = $null
if ($Low) {
  # Low-priority work never makes another job wait: one low job machine-wide, and it takes a slot only while nobody
  # else is waiting and another slot would still be free for the next normal job.
  $lowSem = New-Object Threading.Semaphore(1, 1, 'Global\ue-heavy-low')
  while (-not $lowSem.WaitOne(60000)) { Write-Host "[ue-heavy] low priority: another low-priority job runs; waiting..." }
  while ($true) {
    if (-not (Test-OthersWaiting) -and $sem.WaitOne(0)) {
      if ($Slots -lt 2) { break }
      if ($sem.WaitOne(0)) { [void]$sem.Release(); break }
      [void]$sem.Release()
    }
    Start-Sleep -Seconds 20
  }
} else {
  while (-not $sem.WaitOne(60000)) { Write-Host "[ue-heavy] waiting for a free slot ($Slots max) since $($t0.ToString('HH:mm:ss'))..." }
}
Log 'start' @{ waited_s = [int]((Get-Date) - $t0).TotalSeconds; gpu = [bool]$isGpu; low = [bool]$Low; vram_used_mb = $(if ($isGpu) { Get-VramMB 'used' } else { $null }) }
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
  if ($gpuSem) { [void]$gpuSem.Release() }
  [void]$sem.Release()
  if ($lowSem) { [void]$lowSem.Release() }
  Log 'end' @{ exit_code = $code; duration_s = [int]((Get-Date) - $t1).TotalSeconds }
}
exit $code


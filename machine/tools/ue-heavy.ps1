# Run one heavy Unreal job (UBT build, RunUAT, UnrealEditor-Cmd, shader-heavy editor run) under a
# machine-wide limit so the parallel game sessions don't exhaust CPU/RAM. Waits for a free slot.
#   & <root>\tools\ue-heavy.ps1 -Label "TowerDefense editor build" -- "C:\Program Files\Epic Games\UE_5.3\Engine\Build\BatchFiles\Build.bat" TowerDefenseEditor Win64 Development -Project=...
# Exit code is the job's. Waits/acquire/release are appended to <root>\.recording\_heavy-jobs.jsonl.
# <root> is the machine root (machine/lib/gf-root.ps1); machine/bootstrap.ps1 installs this file as <root>\tools\ue-heavy.ps1.
[CmdletBinding(PositionalBinding = $false)]
param(
  [string]$Label = 'ue job',
  [int]$Slots = 3,
  [switch]$Gpu,   # force the GPU slot (auto-detected for editor GUI, -game, packaged games)
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
$sem = New-Object Threading.Semaphore($Slots, $Slots, 'Global\ue-heavy-jobs')
# GPU jobs (a rendering editor, -game runs, packaged games) also take the single machine-wide GPU slot, which
# the recording pipeline holds for the whole of a recording: 16 GB of VRAM does not fit several at once.
$cmdText = $Command -join ' '
$isGpu = $Gpu -or ($Command[0] -match '(?i)UnrealEditor\.exe$|-Shipping\.exe$') -or
  ($cmdText -match '(?i)(^|\s)-game(\s|$)|-AllowCommandletRendering') -or
  ($Command[0] -match '(?i)\\Packaged\\.*\.exe$')
if ($cmdText -match '(?i)-nullrhi|-nographics') { $isGpu = $false }
$gpuSem = if ($isGpu) { New-Object Threading.Semaphore(1, 1, 'Global\ue-gpu-jobs') } else { $null }
$t0 = Get-Date
Log 'wait' @{ command = $cmdText; gpu = [bool]$isGpu }
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
  while ($true) {
    while (-not $gpuSem.WaitOne(60000)) { Write-Host "[ue-heavy] waiting for the GPU slot (a recording or another GPU job is running) since $($t0.ToString('HH:mm:ss'))..." }
    # A recording may have started waiting while we were queued: give the slot back and let it go first.
    if ((Test-Path $flag) -and ((Get-Date) - (Get-Item $flag).LastWriteTime).TotalMinutes -lt 20) {
      [void]$gpuSem.Release()
      Write-Host "[ue-heavy] a recording is waiting for the GPU; yielding the slot..."
      Start-Sleep -Seconds 20
      continue
    }
    break
  }
}
while (-not $sem.WaitOne(60000)) { Write-Host "[ue-heavy] waiting for a free slot ($Slots max) since $($t0.ToString('HH:mm:ss'))..." }
Log 'start' @{ waited_s = [int]((Get-Date) - $t0).TotalSeconds; gpu = [bool]$isGpu }
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
  $proc.WaitForExit()
  $code = $proc.ExitCode
} finally {
  if ($gpuSem) { [void]$gpuSem.Release() }
  [void]$sem.Release()
  Log 'end' @{ exit_code = $code; duration_s = [int]((Get-Date) - $t1).TotalSeconds }
}
exit $code


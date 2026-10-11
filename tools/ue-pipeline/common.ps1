# Shared helpers for build.ps1 / record.ps1 / pipeline.ps1. Dot-source it. Windows PowerShell 5.1 compatible.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2

$script:WorkRoot      = 'C:\Users\Xiang\Work'
$script:GamesRoot     = Join-Path $WorkRoot 'games'
$script:BuildsRoot    = Join-Path $WorkRoot 'builds'
$script:RecordingsRoot = Join-Path $WorkRoot 'recordings'
$script:LogRoot       = Join-Path $WorkRoot '.recording'
$script:EngineRoot    = 'C:\Program Files\Epic Games\UE_5.3'
$script:LockPath      = Join-Path $BuildsRoot '_pipeline.lock'
$script:Utf8NoBom     = New-Object System.Text.UTF8Encoding $false

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Message)
}

function Get-IsoNow { (Get-Date).ToString('o') }

function Add-JsonLine([string]$Path, $Object) {
    $dir = Split-Path $Path -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
    $line = ($Object | ConvertTo-Json -Compress -Depth 12) + "`n"
    [System.IO.File]::AppendAllText($Path, $line, $Utf8NoBom)
}

function Write-JsonFile([string]$Path, $Object) {
    [System.IO.File]::WriteAllText($Path, ($Object | ConvertTo-Json -Depth 12) + "`n", $Utf8NoBom)
}

function Read-JsonFile([string]$Path) {
    if (-not (Test-Path $Path)) { return $null }
    return [System.IO.File]::ReadAllText($Path, $Utf8NoBom) | ConvertFrom-Json
}

# ---- one heavy job at a time ---------------------------------------------------------------------------------------
# An exclusively opened lock file: the OS releases it if the process dies, and it works across sessions
# (Task Scheduler, other terminals). Holder details are in _pipeline.lock.json.

$script:LockStream = $null

function Enter-PipelineLock([string]$Job, [int]$TimeoutMinutes = 720) {
    if (-not (Test-Path $BuildsRoot)) { New-Item -ItemType Directory -Force $BuildsRoot | Out-Null }
    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $announced = $false
    while ($true) {
        try {
            $script:LockStream = [System.IO.File]::Open($LockPath, 'OpenOrCreate', 'ReadWrite', 'None')
            Write-JsonFile "$LockPath.json" ([ordered]@{ pid = $PID; job = $Job; since = (Get-IsoNow); host = $env:COMPUTERNAME })
            return
        } catch [System.IO.IOException] {
            if (-not $announced) {
                $holder = Read-JsonFile "$LockPath.json"
                Write-Step "waiting for the pipeline lock (held by: $(if ($holder) { "$($holder.job), pid $($holder.pid), since $($holder.since)" } else { 'unknown' }))"
                $announced = $true
            }
            if ((Get-Date) -gt $deadline) { throw "timed out waiting for the pipeline lock $LockPath" }
            Start-Sleep -Seconds 5
        }
    }
}

function Exit-PipelineLock {
    if ($script:LockStream) {
        $script:LockStream.Dispose()
        $script:LockStream = $null
        Remove-Item "$LockPath.json" -ErrorAction SilentlyContinue
    }
}

# ---- games ----------------------------------------------------------------------------------------------------------

function Get-GameInfo([string]$Game) {
    $dir = Join-Path $GamesRoot $Game
    if (-not (Test-Path $dir)) { throw "no game directory $dir" }
    $uproject = @(Get-ChildItem $dir -Filter *.uproject -File)
    if ($uproject.Count -ne 1) { throw "expected one .uproject in $dir, found $($uproject.Count)" }
    $name = [System.IO.Path]::GetFileNameWithoutExtension($uproject[0].Name)
    return [pscustomobject]@{
        Slug = $Game; Dir = $dir; ProjectName = $name; UProjectName = $uproject[0].Name
        LogDir = (Join-Path $LogRoot $Game)
    }
}

function Find-Target([string]$ProjectDir, [string]$Type) {
    # Returns the target name whose Target.cs declares Type = TargetType.<Type>.
    foreach ($f in Get-ChildItem (Join-Path $ProjectDir 'Source') -Filter *.Target.cs -File) {
        if ((Get-Content $f.FullName -Raw) -match "TargetType\.$Type\b") { return $f.Name -replace '\.Target\.cs$', '' }
    }
    return $null
}

function Invoke-Git([string]$Dir, [string[]]$GitArgs, [switch]$AllowFail) {
    # PowerShell 5.1 turns native stderr into terminating errors under 'Stop'; run git under 'Continue'.
    $eap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & git -C $Dir @GitArgs 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $eap }
    if ($code -ne 0 -and -not $AllowFail) { throw "git $($GitArgs -join ' ') failed in ${Dir}: $($out -join ' ')" }
    return $out
}

# ---- processes ------------------------------------------------------------------------------------------------------

function Write-HeavyLog([string]$Event, [string]$Label, $Extra) {
    $row = [ordered]@{ time = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffzzz'); event = $Event; label = $Label; pid = $PID; cwd = (Get-Location).Path }
    if ($Extra) { foreach ($k in $Extra.Keys) { $row[$k] = $Extra[$k] } }
    try { Add-JsonLine (Join-Path $LogRoot '_heavy-jobs.jsonl') $row } catch { }   # shared file; never fail a build over it
}

function Invoke-Logged([string]$Exe, [string]$Arguments, [string]$LogPath, [string]$WorkDir = $null, [string]$HeavyLabel = $null) {
    # Runs Exe with stdout+stderr to LogPath, returns the exit code. Child inherits our (below-normal) priority.
    # With -HeavyLabel the job holds a slot of the machine-wide limiter every game session uses
    # (Global\ue-heavy-jobs, 3 slots, Work\tools\ue-heavy.ps1); taken here rather than through that script so the
    # exact command line survives (its PowerShell re-quoting would split -ExecCmds="...").
    $sem = $null
    if ($HeavyLabel) {
        $sem = New-Object System.Threading.Semaphore(3, 3, 'Global\ue-heavy-jobs')
        $t0 = Get-Date
        Write-HeavyLog 'wait' $HeavyLabel @{ command = "`"$Exe`" $Arguments" }
        while (-not $sem.WaitOne(60000)) { Write-Step "[ue-heavy] waiting for a free slot since $($t0.ToString('HH:mm:ss'))" }
        Write-HeavyLog 'start' $HeavyLabel @{ waited_s = [int]((Get-Date) - $t0).TotalSeconds }
    }
    $t1 = Get-Date
    $code = -1
    try {
        $code = Invoke-LoggedProcess $Exe $Arguments $LogPath $WorkDir
    } finally {
        if ($sem) {
            [void]$sem.Release(); $sem.Dispose()
            Write-HeavyLog 'end' $HeavyLabel @{ exit_code = $code; duration_s = [int]((Get-Date) - $t1).TotalSeconds }
        }
    }
    return $code
}

# ---- the machine-wide GPU slot (one GPU job at a time: not enough VRAM for two) ----------------------------------------
# Same semaphore Work\tools\ue-heavy.ps1 takes for every rendering job (editor GUI, -game, packaged games, Unity).

function Enter-GpuSlot([string]$Label) {
    $sem = New-Object System.Threading.Semaphore(1, 1, 'Global\ue-gpu-jobs')
    $t0 = Get-Date
    Write-HeavyLog 'wait' $Label @{ gpu = $true }
    $said = $false
    while (-not $sem.WaitOne(60000)) {
        if (-not $said) { Write-Step "[gpu] waiting for the GPU slot (another recording or GPU job is running) since $($t0.ToString('HH:mm:ss'))"; $said = $true }
    }
    Write-HeavyLog 'start' $Label @{ gpu = $true; waited_s = [int]((Get-Date) - $t0).TotalSeconds }
    return [pscustomobject]@{ Sem = $sem; Label = $Label; Since = Get-Date }
}

function Exit-GpuSlot($Slot) {
    if (-not $Slot) { return }
    try { [void]$Slot.Sem.Release() } catch { }
    $Slot.Sem.Dispose()
    Write-HeavyLog 'end' $Slot.Label @{ gpu = $true; duration_s = [int]((Get-Date) - $Slot.Since).TotalSeconds }
}

function Get-VramUsedMB {
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { $v = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null | Select-Object -First 1 } finally { $ErrorActionPreference = $eap }
    if ("$v".Trim() -match '^\d+$') { return [int]"$v".Trim() } else { return $null }
}

function Wait-VramFree([string]$Label, [int]$MaxUsedMB = 4096, [int]$MaxMinutes = 120) {
    # Per-process VRAM is N/A under WDDM, so this uses the total in use before our game starts (desktop ~2-4 GB).
    # Returns $true when below the limit, $false after MaxMinutes.
    $t0 = Get-Date; $next = $t0
    while ($true) {
        $used = Get-VramUsedMB
        if ($null -eq $used -or $used -le $MaxUsedMB) {
            if ((Get-Date) -gt $t0.AddSeconds(5)) { Write-HeavyLog 'vram_ok' $Label @{ gpu = $true; vram_used_mb = $used; waited_s = [int]((Get-Date) - $t0).TotalSeconds } }
            return $true
        }
        if ((Get-Date) -ge $next) {
            $heavy = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '(?i)^UnrealEditor|-Shipping$|^Unity$|^ffmpeg$' -or $_.Path -match '(?i)\\Binaries\\Win64\\' } | ForEach-Object { "$($_.ProcessName)($($_.Id))" } | Select-Object -First 8)
            Write-Step "[gpu] $used MB VRAM in use (limit $MaxUsedMB MB before launch): waiting. GPU-heavy processes: $(if ($heavy.Count) { $heavy -join ', ' } else { 'none recognised' })"
            Write-HeavyLog 'vram_wait' $Label @{ gpu = $true; vram_used_mb = $used; limit_mb = $MaxUsedMB; processes = ($heavy -join ', ') }
            $next = (Get-Date).AddMinutes(5)
        }
        if ((Get-Date) -gt $t0.AddMinutes($MaxMinutes)) { return $false }
        Start-Sleep -Seconds 30
    }
}

function Invoke-LoggedProcess([string]$Exe, [string]$Arguments, [string]$LogPath, [string]$WorkDir) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'cmd.exe'
    $psi.Arguments = "/d /s /c `"`"$Exe`" $Arguments > `"$LogPath`" 2>&1`""
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    if ($WorkDir) { $psi.WorkingDirectory = $WorkDir }
    $p = [System.Diagnostics.Process]::Start($psi)
    $p.WaitForExit()
    return $p.ExitCode
}

function Get-ErrorExcerpt([string]$LogPath, [int]$MaxLines = 25) {
    if (-not (Test-Path $LogPath)) { return '' }
    $pattern = '(\berror\b\s*[A-Z]{1,3}\d+|: error|: fatal|Error: |LogInit: Error|ERROR:|BUILD FAILED|AutomationTool exiting with ExitCode=[1-9]|Unhandled Exception|Assertion failed|Fatal error)'
    $lines = @(Select-String -Path $LogPath -Pattern $pattern -CaseSensitive:$false | Select-Object -First $MaxLines | ForEach-Object { $_.Line.Trim() })
    if ($lines.Count -eq 0) { $lines = @(Get-Content $LogPath -Tail 15) }
    $text = ($lines -join "`n")
    if ($text.Length -gt 4000) { $text = $text.Substring(0, 4000) }
    return $text
}

function Set-BelowNormalPriority {
    try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch { }
}

function Find-FFmpeg {
    # Order: $env:UE_PIPELINE_FFMPEG, a pinned copy in Work\tools\ffmpeg-*\bin, PATH, the winget package.
    if ($env:UE_PIPELINE_FFMPEG -and (Test-Path $env:UE_PIPELINE_FFMPEG)) { return $env:UE_PIPELINE_FFMPEG }
    # Pinned by the user's choice: gyan.dev ffmpeg 8.1.2 full build (SHA-256 in docs/ue-pipeline.md). Its NVENC needs driver >= 610 (installed: 617.42).
    $pinned = Join-Path $WorkRoot 'tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe'
    if (Test-Path $pinned) { return $pinned }
    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $pkg = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    $hit = Get-ChildItem $pkg -Directory -Filter 'Gyan.FFmpeg*' -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ChildItem $_.FullName -Recurse -Filter ffmpeg.exe -File } | Select-Object -First 1
    if ($hit) { return $hit.FullName }
    throw 'ffmpeg not found (winget install Gyan.FFmpeg)'
}

function Find-FFprobe {
    $ff = Find-FFmpeg
    $probe = Join-Path (Split-Path $ff) 'ffprobe.exe'
    if (Test-Path $probe) { return $probe }
    throw "ffprobe not found next to $ff"
}

# ---- Win32: windows, DPI, QPC/UTC clock pairs ------------------------------------------------------------------------

if (-not ('UePipeline.Win' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
namespace UePipeline {
public static class Win {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr v);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder sb, int n);
    [DllImport("user32.dll")] static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool ClientToScreen(IntPtr h, ref POINT p);
    [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] static extern int GetSystemMetrics(int i);
    [DllImport("kernel32.dll")] static extern void GetSystemTimePreciseAsFileTime(out long ft);
    [DllImport("kernel32.dll")] static extern bool QueryPerformanceCounter(out long c);
    [DllImport("kernel32.dll")] static extern bool QueryPerformanceFrequency(out long f);

    public static bool MakeDpiAware() { return SetProcessDpiAwarenessContext(new IntPtr(-4)); } // per-monitor v2

    public static IntPtr FindWindowOfPid(uint pid, string titleContains) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((h, l) => {
            uint p; GetWindowThreadProcessId(h, out p);
            if (p != pid || !IsWindowVisible(h)) return true;
            var sb = new StringBuilder(512); GetWindowText(h, sb, 512);
            if (titleContains == null || sb.ToString().Contains(titleContains)) { found = h; return false; }
            return true;
        }, IntPtr.Zero);
        return found;
    }
    public static string Title(IntPtr h) { var sb = new StringBuilder(512); GetWindowText(h, sb, 512); return sb.ToString(); }
    /// <summary>Client area in physical screen pixels: x, y, width, height.</summary>
    public static int[] ClientRectOnScreen(IntPtr h) {
        RECT r; if (!GetClientRect(h, out r)) return null;
        POINT p = new POINT(); if (!ClientToScreen(h, ref p)) return null;
        return new int[] { p.X, p.Y, r.Right - r.Left, r.Bottom - r.Top };
    }
    public static bool SetTopmost(IntPtr h, bool on) {
        // SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
        return SetWindowPos(h, new IntPtr(on ? -1 : -2), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010);
    }
    public static int[] PrimaryScreenSize() { return new int[] { GetSystemMetrics(0), GetSystemMetrics(1) }; }
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(POINT p);
    [DllImport("user32.dll")] static extern IntPtr GetAncestor(IntPtr h, uint flags);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
    /// <summary>True when a 5x5 grid of points over the client area all hit this window (nothing covers it).</summary>
    public static bool IsClientUncovered(IntPtr h) {
        int[] c = ClientRectOnScreen(h); if (c == null) return false;
        for (int i = 0; i < 5; i++) for (int j = 0; j < 5; j++) {
            POINT p = new POINT(); p.X = c[0] + 4 + (c[2] - 8) * i / 4; p.Y = c[1] + 4 + (c[3] - 8) * j / 4;
            if (GetAncestor(WindowFromPoint(p), 2) != h) return false;   // GA_ROOT
        }
        return true;
    }
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder sb, int n);
    [DllImport("user32.dll")] static extern short GetAsyncKeyState(int vk);
    [StructLayout(LayoutKind.Sequential)] struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }
    [DllImport("user32.dll")] static extern bool GetLastInputInfo(ref LASTINPUTINFO lii);
    [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);
    /// <summary>Milliseconds since the last real keyboard/mouse input in this session (injected UE input doesn't count).</summary>
    public static uint IdleMs() { var l = new LASTINPUTINFO(); l.cbSize = 8; GetLastInputInfo(ref l); return (uint)Environment.TickCount - l.dwTime; }
    /// <summary>Keep the display and system awake while recording (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED); false = release.</summary>
    public static void KeepDisplayOn(bool on) { SetThreadExecutionState(on ? 0x80000003u : 0x80000000u); }
    /// <summary>True while the left or right mouse button is held (a window move then is most likely a user drag).</summary>
    public static bool MouseButtonDown() { return (GetAsyncKeyState(0x01) & 0x8000) != 0 || (GetAsyncKeyState(0x02) & 0x8000) != 0; }
    /// <summary>Describes the first window found over the client area ("" when uncovered): title, class, process id.</summary>
    public static string CoveringWindow(IntPtr h) {
        int[] c = ClientRectOnScreen(h); if (c == null) return "no client rect";
        for (int i = 0; i < 5; i++) for (int j = 0; j < 5; j++) {
            POINT p = new POINT(); p.X = c[0] + 4 + (c[2] - 8) * i / 4; p.Y = c[1] + 4 + (c[3] - 8) * j / 4;
            IntPtr root = GetAncestor(WindowFromPoint(p), 2);
            if (root != h) {
                uint pid; GetWindowThreadProcessId(root, out pid);
                var cls = new StringBuilder(256); GetClassName(root, cls, 256);
                string exe = "?"; try { exe = System.Diagnostics.Process.GetProcessById((int)pid).ProcessName; } catch { }
                return "'" + Title(root) + "' class " + cls.ToString() + " process " + exe + " (pid " + pid + ") at " + p.X + "," + p.Y;
            }
        }
        return "";
    }
    /// <summary>Move the window so its client area's top-left lands at (x, y); size and z-order unchanged.</summary>
    public static bool MoveClientTo(IntPtr h, int x, int y) {
        RECT w; if (!GetWindowRect(h, out w)) return false;
        int[] c = ClientRectOnScreen(h); if (c == null) return false;
        return SetWindowPos(h, IntPtr.Zero, w.Left + (x - c[0]), w.Top + (y - c[1]), 0, 0, 0x0001 | 0x0004 | 0x0010);   // NOSIZE|NOZORDER|NOACTIVATE
    }
    public static long QpcFrequency() { long f; QueryPerformanceFrequency(out f); return f; }
    public static long Qpc() { long c; QueryPerformanceCounter(out c); return c; }
    /// <summary>QPC before, UTC as FILETIME (100 ns since 1601), QPC after.</summary>
    public static long[] ClockPair() { long q0, q1, ft; QueryPerformanceCounter(out q0); GetSystemTimePreciseAsFileTime(out ft); QueryPerformanceCounter(out q1); return new long[] { q0, ft, q1 }; }
}
}
'@
}

function Get-ClockSample([string]$Label) {
    $pair = [UePipeline.Win]::ClockPair()
    $f = [UePipeline.Win]::QpcFrequency()
    $utc = [DateTime]::FromFileTimeUtc($pair[1])
    $unixNs = ($pair[1] - 116444736000000000) * 100
    return [ordered]@{
        label = $Label; source = 'pipeline'; qpc = $pair[0]; qpc_after = $pair[2]; t_ns = (Convert-QpcToNs $pair[0] $f)
        unix_ns = $unixNs; utc = $utc.ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
    }
}

function Convert-QpcToNs([long]$Qpc, [long]$Freq) {
    return [long]([math]::Floor($Qpc / $Freq)) * 1000000000 + [long](($Qpc % $Freq) * 1000000000 / $Freq)
}

function Get-FileSha256([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -Path $Path).Hash.ToLowerInvariant()
}

function Invoke-Native([string]$Exe, [string[]]$NativeArgs) {
    # Runs a native tool capturing stdout only; stderr is discarded without tripping ErrorActionPreference=Stop.
    $eap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { return (& $Exe @NativeArgs 2>$null) } finally { $ErrorActionPreference = $eap }
}

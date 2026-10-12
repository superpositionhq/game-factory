<#
.SYNOPSIS
  Turn a finished game package (tools\package-game.ps1 output, already scrubbed and scanned) into the pilot delivery
  whose top level mirrors the vendor samples (samples\island_explore, parkour, robofootball), plus the game repo's
  Dataset\ folder. Format: docs/game-deliverable.md, section "Pilot delivery".

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\package-pilot.ps1 liaozhai-night `
      -Package C:\Users\Xiang\Work\deliverables\liaozhai-night\liaozhai-night_2cf1aa21 -Version 1.1.2
  ... -ReplayVideo <dir>\replay.mp4 -ReplayScripts <dir>\ReplayScripts      # once the replay session delivers them

  Output: deliverables\pilot\<game>\<game>\ + <game>.zip, and <game>_nostore\ + <game>_nostore.zip (from the package's
  _nostore twin). While replay.mp4 or ReplayScripts\ is missing, the zips are named <game>.pending.zip /
  <game>_nostore.pending.zip and the delivery carries PENDING.txt, a README banner and status "pending" in
  manifest.json and delivery-layout.json. Writes <repo>\Dataset\ (the delivery minus UEProject\ and Build\, LFS
  patterns in Dataset\.gitattributes); never commits.

  Top level: README.md, git.log, workflow.jsonl, play.mp4, replay.mp4, UEProject\, ReplayScripts\ (sample layout), then
  Gameplay\, Build\, History\, Screenshots\, Package\ (StoreContent.tsv, scrub-report.json), manifest.json,
  delivery-layout.json. Everything from the package is linked, not changed; ReplayScripts\ is scrubbed with the package
  rules (package-game.ps1 -ScrubDir); the result is rescanned (package-game.ps1 -Rescan) before it is zipped.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [Parameter(Mandatory = $true)][string]$Package,      # the full package folder (its _nostore twin is used for the second zip)
    [string]$Version,
    [string]$ReplayVideo,
    [string]$ReplayScripts,
    [string]$OutRoot = 'C:\Users\Xiang\Work\deliverables\pilot',
    [switch]$NoDataset,
    [switch]$NoZip,
    [switch]$RebuildPlay
)

. (Join-Path $PSScriptRoot 'ue-pipeline\common.ps1')
$t0 = Get-Date
$tool = Join-Path $PSScriptRoot 'package-game.ps1'
$cs = @'
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
namespace Pilot {
public class F { public string Path; public long Bytes; public string Sha256; }
public static class T {
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateHardLink(string lpFileName, string lpExistingFileName, IntPtr lpSecurityAttributes);
    // Hard-links (same volume) or copies every file of src into dst; returns the number of files.
    public static int LinkTree(string src, string dst, bool copy) {
        src = Path.GetFullPath(src).TrimEnd('\\') + "\\"; int n = 0;
        foreach (string f in Directory.EnumerateFiles(src, "*", SearchOption.AllDirectories)) {
            string d = Path.Combine(dst, f.Substring(src.Length)); Directory.CreateDirectory(Path.GetDirectoryName(d));
            if (copy || !CreateHardLink(d, f, IntPtr.Zero)) File.Copy(f, d, true);
            n++;
        }
        return n;
    }
    public static void LinkFile(string src, string dst, bool copy) {
        Directory.CreateDirectory(Path.GetDirectoryName(dst));
        if (File.Exists(dst)) File.Delete(dst);
        if (copy || !CreateHardLink(dst, src, IntPtr.Zero)) File.Copy(src, dst, true);
    }
    public static string HashFile(string p) { using (var h = new SHA256Cng()) using (var s = new FileStream(p, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20)) { var b = h.ComputeHash(s); var sb = new StringBuilder(); foreach (var x in b) sb.Append(x.ToString("x2")); return sb.ToString(); } }
    public static List<F> HashAll(string root) {
        root = Path.GetFullPath(root).TrimEnd('\\') + "\\"; var r = new List<F>();
        foreach (string f in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)) { var x = new F(); x.Path = f.Substring(root.Length).Replace('\\', '/'); x.Bytes = new FileInfo(f).Length; r.Add(x); }
        Parallel.ForEach(r, new ParallelOptions { MaxDegreeOfParallelism = 6 }, x => { x.Sha256 = HashFile(root + x.Path.Replace('/', '\\')); });
        r.Sort((a, b) => string.CompareOrdinal(a.Path, b.Path)); return r;
    }
    static readonly HashSet<string> Stored = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ".mkv", ".mka", ".mp4", ".mov", ".pak", ".ucas", ".utoc", ".zip", ".png", ".jpg", ".jpeg", ".flac" };
    public static int Zip(string srcDir, string zipPath, string baseName) {
        string root = Path.GetFullPath(srcDir).TrimEnd('\\') + "\\";
        var files = new List<string>(Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)); files.Sort(StringComparer.Ordinal);
        if (File.Exists(zipPath)) File.Delete(zipPath);
        using (var fs = new FileStream(zipPath, FileMode.CreateNew, FileAccess.ReadWrite))
        using (var za = new ZipArchive(fs, ZipArchiveMode.Create)) {
            foreach (string full in files) {
                var e = za.CreateEntry(baseName + "/" + full.Substring(root.Length).Replace('\\', '/'), Stored.Contains(Path.GetExtension(full)) ? CompressionLevel.NoCompression : CompressionLevel.Fastest);
                e.LastWriteTime = File.GetLastWriteTime(full);
                using (var es = e.Open()) using (var s = new FileStream(full, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20)) s.CopyTo(es, 1 << 20);
            }
        }
        using (var za = ZipFile.OpenRead(zipPath)) return za.Entries.Count;
    }
}
}
'@
if (-not ('Pilot.T' -as [type])) {
    Add-Type -TypeDefinition $cs -Language CSharp -ReferencedAssemblies @('System', 'System.Core',
        [System.Reflection.Assembly]::Load('System.IO.Compression, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089').Location,
        [System.Reflection.Assembly]::Load('System.IO.Compression.FileSystem, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089').Location)
}
function Write-Utf8([string]$Path, [string]$Text) { [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom) }
function Get-Prop($o, [string]$n) { if ($null -eq $o) { return $null }; $p = $o.PSObject.Properties[$n]; if ($p) { $p.Value } else { $null } }
function Format-Bytes([double]$b) { if ($b -ge 1GB) { '{0:N2} GB' -f ($b / 1GB) } elseif ($b -ge 1MB) { '{0:N1} MB' -f ($b / 1MB) } else { '{0:N0} KB' -f ($b / 1KB) } }
function Get-MdSection([string]$Text, [string]$Heading) {
    $lines = $Text -split "`r?`n"; $out = New-Object System.Collections.ArrayList; $in = $false
    foreach ($l in $lines) { if ($l -match '^##\s+(.*)$') { if ($in) { break }; $in = ($Matches[1] -match $Heading); continue }; if ($in) { [void]$out.Add($l) } }
    return (($out -join "`n").Trim())
}

$pkg = (Resolve-Path $Package).Path
$pkgNo = "$pkg`_nostore"; if (-not (Test-Path $pkgNo)) { $pkgNo = $null }
$man = Get-Content (Join-Path $pkg 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$sha = $man.commit; $short = $sha.Substring(0, 8)
$info = Get-GameInfo $Game
$outDir = Join-Path $OutRoot $Game
New-Item -ItemType Directory -Force $outDir | Out-Null
$haveReplay = [bool]($ReplayVideo -and (Test-Path $ReplayVideo) -and $ReplayScripts -and (Test-Path $ReplayScripts))
$status = if ($haveReplay) { 'complete' } else { 'pending' }
Write-Step "pilot $Game @ $short ($status)  from $pkg"

# ---- play.mp4: the scenario recordings in order, each with its own audio offset, joined by plain cuts ----------------
$playPath = Join-Path $outDir 'play.mp4'
$runs = @(Get-ChildItem (Join-Path $pkg 'Gameplay') -Directory | ForEach-Object {
        $m = Get-Content (Join-Path $_.FullName 'metadata.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $v = Get-Content (Join-Path $_.FullName 'validation.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $sc = Get-Prop $m 'scenario'; if ($null -eq $sc) { $sc = Get-Prop $m 'level' }
        [pscustomobject]@{ dir = $_.FullName; name = $_.Name; scenario = [int]$sc; scenario_name = (Get-Prop $m 'scenario_name'); dur = [double]$v.checks.video.duration_s
            offset = (([double]$m.system_audio.start_offset_ns - [double]$m.video_start_offset_ns) / 1e9); result = $m.result }
    } | Sort-Object scenario, name)
if ($runs.Count -eq 0) { throw "no gameplay runs in $pkg" }
if ($RebuildPlay -or -not (Test-Path $playPath)) {
    $ff = Find-FFmpeg
    $in = New-Object System.Collections.ArrayList; $fc = New-Object System.Text.StringBuilder; $cat = ''
    for ($i = 0; $i -lt $runs.Count; $i++) {
        $r = $runs[$i]
        [void]$in.AddRange(@('-i', (Join-Path $r.dir 'video.mkv'), '-i', (Join-Path $r.dir 'system_audio.mka')))
        $vi = 2 * $i; $ai = 2 * $i + 1; $d = $r.dur.ToString('0.000', [Globalization.CultureInfo]::InvariantCulture)
        $shift = if ($r.offset -ge 0) { "adelay=$([int][math]::Round($r.offset * 1000)):all=1," } else { "atrim=start=$((-$r.offset).ToString('0.000', [Globalization.CultureInfo]::InvariantCulture)),asetpts=PTS-STARTPTS," }
        [void]$fc.Append("[${vi}:v]scale=1920:1080:flags=lanczos,fps=60,format=yuv420p,setsar=1,trim=0:$d,setpts=PTS-STARTPTS[v$i];")
        [void]$fc.Append("[${ai}:a]aformat=sample_rates=48000:channel_layouts=stereo,${shift}apad,atrim=0:$d,asetpts=PTS-STARTPTS[a$i];")
        $cat += "[v$i][a$i]"
    }
    [void]$fc.Append("${cat}concat=n=$($runs.Count):v=1:a=1[v][a]")
    $args2 = @('-hide_banner', '-loglevel', 'error', '-y') + $in + @('-filter_complex', $fc.ToString(), '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', "$playPath.tmp.mp4")
    Write-Step "encoding play.mp4 from $($runs.Count) runs ($([math]::Round(($runs | Measure-Object dur -Sum).Sum)) s)"
    $p = Start-Process -FilePath $ff -ArgumentList ($args2 | ForEach-Object { if ($_ -match '[\s;\[\]]') { '"' + $_ + '"' } else { $_ } }) -NoNewWindow -PassThru -Wait -RedirectStandardError "$playPath.log"
    if ($p.ExitCode -ne 0) { throw "ffmpeg failed ($($p.ExitCode)): $(Get-Content "$playPath.log" -Raw)" }
    Move-Item -Force "$playPath.tmp.mp4" $playPath
}
$playSha = [Pilot.T]::HashFile($playPath)

# ---- one delivery folder per variant ---------------------------------------------------------------------------------
$pkgReadme = Get-Content (Join-Path $pkg 'README.md') -Raw -Encoding UTF8
function New-Delivery([string]$Src, [string]$Name, [string]$Dest, [bool]$Dataset) {
    if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
    New-Item -ItemType Directory -Force $Dest | Out-Null
    $copy = $Dataset   # the repo folder gets real copies; deliveries are hard links into the verified package
    foreach ($f in 'git.log', 'workflow.jsonl') { [Pilot.T]::LinkFile((Join-Path $Src $f), (Join-Path $Dest $f), $copy) }
    [Pilot.T]::LinkFile($playPath, (Join-Path $Dest 'play.mp4'), $copy)
    if ($haveReplay) { [Pilot.T]::LinkFile((Resolve-Path $ReplayVideo).Path, (Join-Path $Dest 'replay.mp4'), $true) }
    $dirs = if ($Dataset) { @('Gameplay', 'History', 'Screenshots') } else { @('UEProject', 'Gameplay', 'Build', 'History', 'Screenshots') }
    foreach ($d in $dirs) { if (Test-Path (Join-Path $Src $d)) { $null = [Pilot.T]::LinkTree((Join-Path $Src $d), (Join-Path $Dest $d), $copy) } }
    New-Item -ItemType Directory -Force (Join-Path $Dest 'Package') | Out-Null
    foreach ($f in 'StoreContent.tsv', 'scrub-report.json') { if (Test-Path (Join-Path $Src $f)) { [Pilot.T]::LinkFile((Join-Path $Src $f), (Join-Path $Dest "Package\$f"), $copy) } }
    if ($haveReplay) {
        $rs = Join-Path $Dest 'ReplayScripts'
        $null = [Pilot.T]::LinkTree((Resolve-Path $ReplayScripts).Path, $rs, $true)   # a copy: it is scrubbed in place
        & powershell -NoProfile -ExecutionPolicy Bypass -File $tool $Game -ScrubDir $rs | Out-Host
        Move-Item -Force "$rs.scrub.json" (Join-Path $Dest 'Package\replay-scrub.json')
    }
}
$variants = @(@{ src = $pkg; name = $Game; nostore = $false })
if ($pkgNo) { $variants += @{ src = $pkgNo; name = "${Game}_nostore"; nostore = $true } }

foreach ($v in $variants) {
    $dest = Join-Path $outDir $v.name
    Write-Step "assembling $dest"
    New-Delivery $v.src $v.name $dest $false
}
$dsDir = Join-Path $info.Dir 'Dataset'
if (-not $NoDataset) { Write-Step "writing $dsDir"; New-Delivery $pkg 'Dataset' $dsDir $true }

# ---- README, delivery-layout.json, manifest.json, scan, zip ------------------------------------------------------------
$title = if ($pkgReadme -match '(?m)^#\s+(.+)$') { $Matches[1].Trim() } else { $info.ProjectName }
$hero = if ($pkgReadme -match '!\[[^\]]*\]\((Screenshots/[^)]+)\)') { $Matches[1] } else { $null }
$exe = Get-Prop $man.build 'exe'
function Write-Docs([string]$Dest, [string]$Variant, [bool]$Dataset) {
    $sb = New-Object System.Text.StringBuilder; function A([string]$s = '') { [void]$sb.Append($s + "`n") }
    A "# $title"; A ''
    if ($hero) { A "![$title]($hero)"; A '' }
    if ($status -ne 'complete') {
        A '> **Pending:** `replay.mp4` and `ReplayScripts/` (the replay of the creation process) are not in this delivery yet.'
        A '> Everything else is final. This delivery is replaced by the complete one when they land.'
        A ''
    }
    A "$(if ($Version) { "Version $Version, " })commit ``$short``. $(if ($Dataset) { 'This folder is the delivery dataset kept with the project: the repository itself is the Unreal project, and the packaged build is left out (rebuild it from the project).' } else { "Variant: $(if ($Variant -eq 'nostore') { 'without store content (the store packs listed in `Package/StoreContent.tsv` are left out of `UEProject/`)' } else { 'with store content' })." })"
    A ''
    A '## Requirements'; A ''
    A '- 64-bit Windows 10/11 and a DirectX 12 GPU.'
    A "- Unreal Engine $($man.engine) with Visual Studio 2022 (C++ game development) to open the project$(if (-not $Dataset) { '; none to play the packaged build' })."
    A '- Python 3.11+ for the creation replay (see `ReplayScripts/`).'
    A ''
    A '## Package contents'; A ''
    if (-not $Dataset) { A '- `UEProject/` — the completed game project, at the commit above.' }
    A ('- `ReplayScripts/` — replay of the creation process from the recorded editor operations.' + $(if ($status -ne 'complete') { ' *(pending)*' } else { '' }))
    A '- `workflow.jsonl` — Unreal editor operations and parameters, one row per operation, recorded when it happened.'
    A '- `git.log` — every commit with its message and full diff (binary files as path and sha256).'
    A "- ``play.mp4`` — the recorded playing test: the game's $($runs.Count) scenarios in order, played through, with the game audio."
    A ('- `replay.mp4` — the recorded Unreal editor replay.' + $(if ($status -ne 'complete') { ' *(pending)*' } else { '' }))
    A ''
    A 'Additional data, in its own folders:'; A ''
    A '- `Gameplay/` — one folder per recorded run: video, game audio, every input, telemetry, outcome, clock data and validation (`Gameplay/summary.md`).'
    if (-not $Dataset) { A "- ``Build/`` — the packaged Windows Shipping build$(if ($exe) { " (``Build/$exe``)" })." }
    A '- `History/` — logs of the creation sessions: every tool call, commit, build and recorded run.'
    A '- `Screenshots/` — the images in this README.'
    A '- `Package/` — `StoreContent.tsv` (store-content files with their sha256) and `scrub-report.json` (what was rewritten before delivery).'
    A '- `manifest.json` — path, size and sha256 of every file; `delivery-layout.json` — how the parts fit together.'
    A ''
    A 'Keep these files and folders together.'; A ''
    A '## Play the game'; A ''
    if (-not $Dataset) { A "Run ``Build/$exe`` (no installation), or open ``UEProject/$($info.UProjectName)`` with Unreal Engine $($man.engine) and click **Play**."; A '' }
    else { A "Open ``$($info.UProjectName)`` in the repository root with Unreal Engine $($man.engine) and click **Play**."; A '' }
    $play = Get-MdSection $pkgReadme '^Play'; if ($play) { A (($play -split "`n" | Where-Object { $_ -notmatch 'Build/|Windows 10/11' }) -join "`n").Trim(); A '' }
    A '## Replay the creation process'; A ''
    if ($status -eq 'complete') { A 'See `ReplayScripts/README.md` for the command and options; the supplied project is left unchanged.' } else { A '`ReplayScripts/` is pending.' }
    A ''
    A '## Scenarios'; A ''
    A '`play.mp4` plays these recorded runs in this order (cuts between them, nothing added); each run is in `Gameplay/`.'; A ''
    A '| # | Scenario | Run | Result | Length |'; A '|---|---|---|---|---|'
    foreach ($r in $runs) { A "| $($r.scenario) | $($r.scenario_name) | ``$($r.name)`` | $($r.result) | $([math]::Round($r.dur, 1)) s |" }
    A ''
    $s = Get-MdSection $pkgReadme '^Scenarios'
    if ($s -and $s -notmatch 'documents no scenario table') { A (($s -split "`n" | Where-Object { $_ -notmatch '^Recorded runs of these scenarios' }) -join "`n").Trim(); A '' }
    foreach ($h in @('What is observed', 'Assets and licences', 'Store content')) {
        $s = Get-MdSection $pkgReadme $h; if ($s) { A "## $(if ($h -eq 'What is observed') { 'What is observed and what is derived' } else { $h })"; A ''; A $s; A '' }
    }
    A '## Integrity'; A ''
    A '`manifest.json` lists every file with its size and sha256 (read it as UTF-8).'
    Write-Utf8 (Join-Path $Dest 'README.md') $sb.ToString()
    $layout = [ordered]@{
        schema = 'game-delivery-layout/v1'; game = $Game; title = $title; version = $Version; commit = $sha; status = $status
        variant = $(if ($Dataset) { 'dataset (repository folder: no UEProject/, no Build/)' } elseif ($Variant -eq 'nostore') { 'without store content' } else { 'with store content' })
        ue_project = $(if ($Dataset) { '..' } else { 'UEProject/' }); replay_scripts = 'ReplayScripts/'
        git_log = 'git.log'; workflow = 'workflow.jsonl'; play_video = 'play.mp4'; replay_video = 'replay.mp4'
        git_log_sha256 = [Pilot.T]::HashFile((Join-Path $Dest 'git.log')); workflow_sha256 = [Pilot.T]::HashFile((Join-Path $Dest 'workflow.jsonl'))
        play_video_sha256 = $playSha; replay_video_sha256 = $(if ($haveReplay) { [Pilot.T]::HashFile((Join-Path $Dest 'replay.mp4')) } else { $null })
        play_video_runs = @($runs | ForEach-Object { [ordered]@{ run = $_.name; scenario = $_.scenario; seconds = $_.dur; audio_offset_s = [math]::Round($_.offset, 3) } })
        pending = $(if ($haveReplay) { @() } else { @('replay.mp4', 'ReplayScripts/') })
        extras = [ordered]@{ gameplay = 'Gameplay/'; build = $(if ($Dataset) { $null } else { 'Build/' }); history = 'History/'; screenshots = 'Screenshots/'; package = 'Package/'; manifest = 'manifest.json' }
    }
    Write-JsonFile (Join-Path $Dest 'delivery-layout.json') $layout
    if ($status -ne 'complete') { Write-Utf8 (Join-Path $Dest 'PENDING.txt') "Pending: replay.mp4 and ReplayScripts/ (creation replay). Do not hand out as final.`n" }
    $all = [Pilot.T]::HashAll($Dest) | Where-Object { $_.Path -ne 'manifest.json' }
    Write-JsonFile (Join-Path $Dest 'manifest.json') ([ordered]@{ delivery = (Split-Path $Dest -Leaf); game = $Game; version = $Version; commit = $sha; status = $status; created = (Get-IsoNow)
            source_package = (Split-Path $pkg -Leaf); totals = [ordered]@{ files = @($all).Count; bytes = [long](($all | Measure-Object Bytes -Sum).Sum) }
            files = @($all | ForEach-Object { [ordered]@{ path = $_.Path; bytes = $_.Bytes; sha256 = $_.Sha256 } }) })
}
$results = New-Object System.Collections.ArrayList
foreach ($v in $variants) {
    $dest = Join-Path $outDir $v.name
    Write-Docs $dest $(if ($v.nostore) { 'nostore' } else { 'full' }) $false
    [void]$results.Add(@{ dest = $dest; name = $v.name })
}
if (-not $NoDataset) {
    Write-Docs $dsDir 'dataset' $true
    $lfs = @('*.mp4', '*.mkv', '*.mka', '*.wav', '*.flac', '*.jpg', '*.jpeg', '*.png', '*.zip') | ForEach-Object { "$_ filter=lfs diff=lfs merge=lfs -text" }
    Write-Utf8 (Join-Path $dsDir '.gitattributes') (($lfs -join "`n") + "`n")
    [void]$results.Add(@{ dest = $dsDir; name = 'Dataset' })
}
$fail = $false
foreach ($r in $results) {
    $o = & powershell -NoProfile -ExecutionPolicy Bypass -File $tool $Game -Rescan $r.dest 2>&1
    $verdict = @($o | Where-Object { $_ -match '^(PASS|FAIL)' })[0]
    Write-Host "  rescan $($r.name): $verdict"
    if ($verdict -notmatch '^PASS') { $fail = $true; $o | Where-Object { $_ -match 'blocking' } | Write-Host }
    Move-Item -Force "$($r.dest).rescan-hits.tsv" (Join-Path $outDir "$($r.name).rescan-hits.tsv") -ErrorAction SilentlyContinue
}
if ($fail) { throw 'a delivery failed the rescan: nothing zipped' }
if (-not $NoZip) {
    foreach ($r in ($results | Where-Object { $_.name -ne 'Dataset' })) {
        foreach ($old in @("$($r.name).zip", "$($r.name).pending.zip")) { $p = Join-Path $outDir $old; if (Test-Path $p) { Remove-Item -Force $p } }
        $zip = Join-Path $outDir "$($r.name)$(if ($status -ne 'complete') { '.pending' }).zip"
        Write-Step "zipping $zip"
        $n = [Pilot.T]::Zip($r.dest, $zip, $r.name)
        $files = @(Get-ChildItem $r.dest -Recurse -File).Count
        if ($n -ne $files) { throw "zip $zip has $n entries, expected $files" }
        $r.zip = $zip; $r.zip_bytes = (Get-Item $zip).Length
    }
}
Write-Host ''
Write-Host "$($status.ToUpper())  $Game @ $short" -ForegroundColor $(if ($status -eq 'complete') { 'Green' } else { 'Yellow' })
foreach ($r in $results) {
    $b = (Get-ChildItem $r.dest -Recurse -File | Measure-Object Length -Sum).Sum
    Write-Host ("  {0,-24} {1,10}  {2}{3}" -f $r.name, (Format-Bytes $b), $r.dest, $(if ($r["zip"]) { "  ->  $($r["zip"]) ($(Format-Bytes $r["zip_bytes"]))" }))
}
Write-Host "  play.mp4 $(Format-Bytes (Get-Item $playPath).Length), $($runs.Count) scenarios; $([math]::Round(((Get-Date) - $t0).TotalMinutes, 1)) min"

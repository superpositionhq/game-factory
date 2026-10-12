<#
.SYNOPSIS
  Build the dataset layout v1 delivery (docs/game-deliverable.md, "Dataset layout v1"; docs/dataset-layout-v1.json) of
  one game from its finished package (tools\package-game.ps1 output, already scrubbed and scanned), and the game repo's
  Dataset\ folder. Usually run through package-game.ps1 -Dataset; nothing here is per game except the data.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\package-dataset.ps1 liaozhai-night `
      -Package %GF_ROOT%\deliverables\liaozhai-night\liaozhai-night_2cf1aa21 -Version 1.1.2
  ... -ReplayVideo <file>\replay.mp4 -ReplayScripts <dir>\ReplayScripts      # once the replay session delivers them

  Output: deliverables\dataset\<game>\<game>\ + <game>.zip and <game>_nostore\ + <game>_nostore.zip (from the
  package's _nostore twin); <game>.pending.zip / <game>_nostore.pending.zip while replay.mp4 or ReplayScripts\ is
  missing (manifest status "pending", README banner). Reports next to the zips: <name>.store-content.tsv,
  <name>.scrub-report.json, <name>.rescan-hits.tsv. Writes <repo>\Dataset\ (no UEProject\, no Build\, LFS patterns in
  Dataset\.gitattributes); never commits. Every delivery is rescanned (package-game.ps1 -Rescan) and validated
  (validate-dataset.ps1) before anything is zipped.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [Parameter(Mandatory = $true)][string]$Package,      # the full package folder; its _nostore twin, if present, gives the second zip
    [string]$Version,
    [string]$ReplayVideo,
    [string]$ReplayScripts,
    [string]$OutRoot,               # default <root>\deliverables\dataset (root: machine/lib/gf-root.ps1)
    [switch]$NoDataset,
    [switch]$NoZip,
    [switch]$RebuildVideos
)

. (Join-Path $PSScriptRoot 'ue-pipeline\common.ps1')
if (-not $OutRoot) { $OutRoot = Join-Path $WorkRoot 'deliverables\dataset' }
$t0 = Get-Date
$tool = Join-Path $PSScriptRoot 'package-game.ps1'
$validator = Join-Path $PSScriptRoot 'validate-dataset.ps1'
$cs = @'
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
namespace DatasetV1 {
public class F { public string Path; public long Bytes; public string Sha256; }
public static class T {
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateHardLink(string lpFileName, string lpExistingFileName, IntPtr lpSecurityAttributes);
    public static int LinkTree(string src, string dst, bool copy, string skipExt) {
        src = Path.GetFullPath(src).TrimEnd('\\') + "\\"; int n = 0;
        foreach (string f in Directory.EnumerateFiles(src, "*", SearchOption.AllDirectories)) {
            if (!string.IsNullOrEmpty(skipExt) && f.EndsWith(skipExt, StringComparison.OrdinalIgnoreCase)) continue;   // PowerShell passes $null as ""
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
if (-not ('DatasetV1.T' -as [type])) {
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
$inv = [Globalization.CultureInfo]::InvariantCulture

$pkg = (Resolve-Path $Package).Path
$pkgNo = "$pkg`_nostore"; if (-not (Test-Path $pkgNo)) { $pkgNo = $null }
$man = Get-Content (Join-Path $pkg 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$sha = $man.commit; $short = $sha.Substring(0, 8)
$info = Get-GameInfo $Game
$outDir = Join-Path $OutRoot $Game
New-Item -ItemType Directory -Force $outDir | Out-Null
# One run per game at a time: two runs write the same folders (an open handle; the OS releases it if the run dies).
$lockPath = Join-Path $outDir '_dataset.lock'
try { $script:Lock = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None') }
catch [System.IO.IOException] { throw "another package-dataset run for $Game is in progress ($lockPath is held); wait for it to finish" }
$haveReplay = [bool]($ReplayVideo -and (Test-Path $ReplayVideo) -and $ReplayScripts -and (Test-Path $ReplayScripts))
$status = if ($haveReplay) { 'complete' } else { 'pending' }
$pending = if ($haveReplay) { @() } else { @('replay.mp4', 'ReplayScripts/') }
Write-Step "dataset v1: $Game @ $short ($status)  from $pkg"

# ---- Gameplay/<game>_S<n>.mp4: one video per scenario of the release version, game audio muxed ------------------------
# The package's runs are those of the packaged commit (package-game.ps1 -OnlyCommitRuns). One per scenario: an ok run
# before a warn run, then the latest.
$runs = @(Get-ChildItem (Join-Path $pkg 'Gameplay') -Directory | ForEach-Object {
        $m = Get-Content (Join-Path $_.FullName 'metadata.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $v = Get-Content (Join-Path $_.FullName 'validation.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $sc = Get-Prop $m 'scenario'; if ($null -eq $sc) { $sc = Get-Prop $m 'level' }
        [pscustomobject]@{ dir = $_.FullName; name = $_.Name; scenario = [int]$sc; scenario_name = (Get-Prop $m 'scenario_name'); dur = [double]$v.checks.video.duration_s
            offset = (([double]$m.system_audio.start_offset_ns - [double]$m.video_start_offset_ns) / 1e9); result = $m.result; status = $v.status; build = $m.build.commit }
    })
if ($runs.Count -eq 0) { throw "no gameplay runs in $pkg" }
$other = @($runs | Where-Object { $_.build -ne $sha })
if ($other.Count) { throw "the package has runs of other commits ($(@($other | ForEach-Object name) -join ', ')): package it with -OnlyCommitRuns" }
$scen = @($runs | Group-Object scenario | Sort-Object { [int]$_.Name } | ForEach-Object {
        $_.Group | Sort-Object @{ e = { if ($_.status -eq 'ok') { 0 } else { 1 } } }, @{ e = { $_.name }; Descending = $true } | Select-Object -First 1 })
$vidDir = Join-Path $outDir '_videos'; New-Item -ItemType Directory -Force $vidDir | Out-Null
$ff = Find-FFmpeg
# Preferred source: the run's own gameplay.mp4 (record.ps1 / gameplay-mp4.ps1: video.mkv's H.264 stream copied + the
# system audio as AAC, aligned on the QPC clock), hard-linked as is. The libx264 re-encode below is the fallback for
# runs recorded before gameplay.mp4 existed.
function Test-GameplayMp4([string]$Path) {
    try {
        $j = (Invoke-Native (Find-FFprobe) @('-v', 'error', '-show_entries', 'stream=codec_type,codec_name,width,height', '-of', 'json', $Path)) -join "`n" | ConvertFrom-Json
        $v = @($j.streams | Where-Object { $_.codec_type -eq 'video' }); $au = @($j.streams | Where-Object { $_.codec_type -eq 'audio' })
        return ($v.Count -eq 1 -and $v[0].codec_name -eq 'h264' -and [int]$v[0].width -eq 1920 -and [int]$v[0].height -eq 1080 -and $au.Count -eq 1 -and $au[0].codec_name -eq 'aac')
    } catch { return $false }
}
foreach ($r in $scen) {
    $out = Join-Path $vidDir "$($Game)_S$($r.scenario).mp4"
    $tag = Join-Path $vidDir "$($Game)_S$($r.scenario).source"
    $gm = @((Join-Path $r.dir 'gameplay.mp4'), (Join-Path (Join-Path (Join-Path $RecordingsRoot $Game) $r.name) 'gameplay.mp4')) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($gm -and -not (Test-GameplayMp4 $gm)) { Write-Step "WARNING: $gm is not h264 1920x1080 + aac: re-encoding instead"; $gm = $null }
    $srcTag = if ($gm) { "$($r.name) gameplay.mp4" } else { $r.name }
    if (-not $RebuildVideos -and (Test-Path $out) -and (Test-Path $tag) -and ((Get-Content $tag -Raw).Trim() -eq $srcTag)) { continue }
    if ($gm) {
        [DatasetV1.T]::LinkFile($gm, $out, $false)
        Write-Utf8 $tag $srcTag
        Write-Step "$(Split-Path $out -Leaf) from $($r.name)\gameplay.mp4 (stream copy, no re-encode; audio offset $([math]::Round($r.offset, 3)) s)"
        continue
    }
    $d = $r.dur.ToString('0.000', $inv)
    $shift = if ($r.offset -ge 0) { "adelay=$([int][math]::Round($r.offset * 1000)):all=1," } else { "atrim=start=$((-$r.offset).ToString('0.000', $inv)),asetpts=PTS-STARTPTS," }
    $fc = "[0:v]scale=1920:1080:flags=lanczos,fps=60,format=yuv420p,setsar=1,trim=0:$d,setpts=PTS-STARTPTS[v];[1:a]aformat=sample_rates=48000:channel_layouts=stereo,${shift}apad,atrim=0:$d,asetpts=PTS-STARTPTS[a]"
    $a = @('-hide_banner', '-loglevel', 'error', '-y', '-i', (Join-Path $r.dir 'video.mkv'), '-i', (Join-Path $r.dir 'system_audio.mka'), '-filter_complex', $fc,
        '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
        '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', "$out.tmp.mp4")
    Write-Step "encoding $(Split-Path $out -Leaf) from $($r.name) ($([math]::Round($r.dur)) s, audio offset $([math]::Round($r.offset, 3)) s)"
    $p = Start-Process -FilePath $ff -ArgumentList ($a | ForEach-Object { if ($_ -match '[\s;\[\]]') { '"' + $_ + '"' } else { $_ } }) -NoNewWindow -PassThru -Wait -RedirectStandardError "$out.log"
    if ($p.ExitCode -ne 0) { throw "ffmpeg failed for $out ($($p.ExitCode)): $(Get-Content "$out.log" -Raw)" }
    Move-Item -Force "$out.tmp.mp4" $out
    Write-Utf8 $tag $r.name
}

# ---- deliveries ------------------------------------------------------------------------------------------------------
$pkgReadme = Get-Content (Join-Path $pkg 'README.md') -Raw -Encoding UTF8
$title = if ($pkgReadme -match '(?m)^#\s+(.+)$') { $Matches[1].Trim() } else { $info.ProjectName }
$exe = Get-Prop $man.build 'exe'
# Link (or copy) a whole folder and prove it arrived: the destination must hold exactly the source's files (minus
# $SkipExt). A delivery once came out without UEProject\ and Screenshots\ while Build\ was fine and nothing complained
# (siege-catapult 577814b1, 2026-10-12 01:12); a missing or short tree now stops the run here.
function Copy-TreeChecked([string]$From, [string]$To, [bool]$Copy, [string]$SkipExt, [string]$What) {
    if (-not (Test-Path -LiteralPath $From -PathType Container)) { throw "the package has no $What folder ($From)" }
    $expected = @(Get-ChildItem -LiteralPath $From -Recurse -File -Force | Where-Object { -not $SkipExt -or -not $_.Name.EndsWith($SkipExt, [StringComparison]::OrdinalIgnoreCase) }).Count
    if ($expected -eq 0) { throw "$What in the package is empty ($From)" }
    $n = [DatasetV1.T]::LinkTree($From, $To, $Copy, $SkipExt)
    $got = @(Get-ChildItem -LiteralPath $To -Recurse -File -Force -ErrorAction SilentlyContinue).Count
    if ($n -ne $expected -or $got -ne $expected) { throw "$What arrived incomplete in ${To}: $got files (linked $n), the package has $expected" }
    return $n
}

function New-Delivery([string]$Src, [string]$Dest, [string]$Variant) {
    $repo = $Variant -eq 'repo-dataset'
    if (Test-Path $Dest) { Get-ChildItem $Dest -Force | Where-Object { $_.Name -ne '.gitattributes' } | Remove-Item -Recurse -Force }
    New-Item -ItemType Directory -Force $Dest | Out-Null
    $copy = $repo   # the repo folder gets real copies; deliveries are hard links into the verified package
    foreach ($f in 'git.log', 'workflow.jsonl') { [DatasetV1.T]::LinkFile((Join-Path $Src $f), (Join-Path $Dest $f), $copy) }
    foreach ($r in $scen) { [DatasetV1.T]::LinkFile((Join-Path $vidDir "$($Game)_S$($r.scenario).mp4"), (Join-Path $Dest "Gameplay\$($Game)_S$($r.scenario).mp4"), $copy) }
    $null = Copy-TreeChecked (Join-Path $Src 'Screenshots') (Join-Path $Dest 'Screenshots') $copy '' 'Screenshots/'   # required by layout v1
    if (-not $repo) {
        $null = Copy-TreeChecked (Join-Path $Src 'UEProject') (Join-Path $Dest 'UEProject') $false '' 'UEProject/'
        $null = Copy-TreeChecked (Join-Path $Src 'Build') (Join-Path $Dest 'Build') $false '.pdb' 'Build/'
    }
    if ($haveReplay) {
        [DatasetV1.T]::LinkFile((Resolve-Path $ReplayVideo).Path, (Join-Path $Dest 'replay.mp4'), $true)
        $rs = Join-Path $Dest 'ReplayScripts'
        $null = [DatasetV1.T]::LinkTree((Resolve-Path $ReplayScripts).Path, $rs, $true, '.pdb')   # a copy: scrubbed in place
        & powershell -NoProfile -ExecutionPolicy Bypass -File $tool $Game -ScrubDir $rs | Out-Host
        Move-Item -Force "$rs.scrub.json" (Join-Path $outDir "$(Split-Path $Dest -Leaf).replay-scrub.json")
    }
    Write-Readme $Dest $Variant
    if ($repo) {
        $lfs = @('*.mp4', '*.mkv', '*.mka', '*.wav', '*.flac', '*.jpg', '*.jpeg', '*.png', '*.webp', '*.zip') | ForEach-Object { "$_ filter=lfs diff=lfs merge=lfs -text" }
        Write-Utf8 (Join-Path $Dest '.gitattributes') (($lfs -join "`n") + "`n")
    }
    $all = @([DatasetV1.T]::HashAll($Dest) | Where-Object { $_.Path -ne 'manifest.json' -and $_.Path -ne '.gitattributes' })
    Write-JsonFile (Join-Path $Dest 'manifest.json') ([ordered]@{
            layout = 'dataset-layout/v1'; game = $Game; title = $title; version = $Version; commit = $sha; status = $status; variant = $Variant
            pending = $pending; created = (Get-IsoNow); source_package = (Split-Path $Src -Leaf)
            build = $(if ($repo) { $null } else { [ordered]@{ config = $man.build.config; commit = $man.build.commit; exe = $exe; source = $man.build.source } })
            scenarios = @($scen | ForEach-Object { [ordered]@{ file = "Gameplay/$($Game)_S$($_.scenario).mp4"; scenario = $_.scenario; name = $_.scenario_name; result = $_.result
                        seconds = [math]::Round($_.dur, 3); source_run = $_.name; audio_offset_s = [math]::Round($_.offset, 3) } })
            totals = [ordered]@{ files = $all.Count; bytes = [long](($all | Measure-Object Bytes -Sum).Sum) }
            files = @($all | ForEach-Object { [ordered]@{ path = $_.Path; bytes = $_.Bytes; sha256 = $_.Sha256 } })
        })
}

# README template (docs/game-deliverable.md, "README template")
function Write-Readme([string]$Dest, [string]$Variant) {
    $repo = $Variant -eq 'repo-dataset'
    $shots = @(Get-ChildItem (Join-Path $Dest 'Screenshots') -File -ErrorAction SilentlyContinue | Sort-Object Name)
    $sb = New-Object System.Text.StringBuilder; function A([string]$s = '') { [void]$sb.Append($s + "`n") }
    A "# $title"; A ''
    if ($shots.Count) { A "![$title](Screenshots/$($shots[0].Name))"; A '' }
    if ($status -ne 'complete') {
        A '> **Pending:** `replay.mp4` and `ReplayScripts/` (the replay of the creation process) are not in this delivery yet;'
        A '> everything else is final. This delivery is replaced by the complete one when they land.'
        A ''
    }
    $vline = "$(if ($Version) { "Version $Version, " })commit ``$short``."
    if ($repo) { $vline += ' This folder is the dataset kept with the project: the repository itself is the Unreal project, and the packaged build is left out (build it from the project).' }
    elseif ($Variant -eq 'nostore') { $vline += ' Variant without store content: the store packs listed under Store content below are not in `UEProject/`.' }
    A $vline; A ''
    A '## Requirements'; A ''
    A '- 64-bit Windows 10/11 and a DirectX 12 GPU.'
    A "- Unreal Engine $($man.engine) and Visual Studio 2022 (C++ game development) to open the project$(if (-not $repo) { '; nothing to play the packaged build' })."
    A '- Python 3.11+ for the creation replay.'
    A ''
    A '## Package contents'; A ''
    if (-not $repo) { A '- `UEProject/` — the completed game project at the commit above.' }
    A ('- `ReplayScripts/` — replay of the creation process from the recorded editor operations.' + $(if ($status -ne 'complete') { ' *(pending)*' } else { '' }))
    A '- `workflow.jsonl` — editor operations and parameters, one row per operation, written when it happened.'
    A '- `git.log` — every commit with its message and full diff (binary files as path and sha256).'
    A ('- `replay.mp4` — the recorded editor replay.' + $(if ($status -ne 'complete') { ' *(pending)*' } else { '' }))
    A "- ``Gameplay/`` — one video per scenario of this version ($($scen.Count)), played through with the game audio."
    if (-not $repo) { A "- ``Build/`` — the packaged Windows Shipping build$(if ($exe) { " (``Build/$exe``)" })." }
    A '- `Screenshots/` — the images in this README.'
    A '- `manifest.json` — path, size and sha256 of every file, and the release metadata.'
    A ''; A 'Keep these files and folders together.'; A ''
    A '## Play the game'; A ''
    if (-not $repo) { A "Run ``Build/$exe`` (no installation), or open ``UEProject/$($info.UProjectName)`` with Unreal Engine $($man.engine) and click **Play**." }
    else { A "Open ``$($info.UProjectName)`` in the repository root with Unreal Engine $($man.engine) and click **Play**." }
    A ''
    $play = Get-MdSection $pkgReadme '^Play'; if ($play) { A (($play -split "`n" | Where-Object { $_ -notmatch 'Build/|Windows 10/11' }) -join "`n").Trim(); A '' }
    A '## Replay the creation process'; A ''
    if ($status -eq 'complete') { A 'See `ReplayScripts/README.md` for the command and its options; the supplied project is not changed.' } else { A '`ReplayScripts/` is pending.' }
    A ''
    A '## Scenarios'; A ''
    A '| Video | # | Scenario | Result | Length |'; A '|---|---|---|---|---|'
    foreach ($r in $scen) { A "| ``Gameplay/$($Game)_S$($r.scenario).mp4`` | $($r.scenario) | $($r.scenario_name) | $($r.result) | $([math]::Round($r.dur, 1)) s |" }
    A ''
    $s = Get-MdSection $pkgReadme '^Scenarios'
    if ($s -and $s -notmatch 'documents no scenario table') { A (($s -split "`n" | Where-Object { $_ -notmatch 'Gameplay/' }) -join "`n").Trim(); A '' }
    A '## Screenshots'; A ''
    foreach ($f in $shots) { A "![$($f.BaseName)](Screenshots/$($f.Name))"; A '' }
    A '## Assets and licences'; A ''
    $l = Get-MdSection $pkgReadme '^Assets and licences'; if ($l) { A ($l -replace '`UEProject/assets\.manifest\.json`', $(if ($repo) { '`assets.manifest.json` (repository root)' } else { '`UEProject/assets.manifest.json`' })); A '' }
    $st = Get-MdSection $pkgReadme '^Store content'
    if ($st) { A '### Store content'; A ''; A (($st -split "`n" | Where-Object { $_ -notmatch 'StoreContent\.tsv' }) -join "`n").Trim(); A '' }
    A '## Integrity'; A ''
    A '`manifest.json` lists every file with its size and sha256. Check with PowerShell (read it as UTF-8):'; A ''
    A '```'
    A '$m = Get-Content manifest.json -Raw -Encoding UTF8 | ConvertFrom-Json'
    A '$m.files | ? { (Get-FileHash -Algorithm SHA256 -LiteralPath $_.path).Hash -ne $_.sha256 } | % path   # prints nothing when all match'
    A '```'
    Write-Utf8 (Join-Path $Dest 'README.md') $sb.ToString()
}

$results = New-Object System.Collections.ArrayList
$variants = @(@{ src = $pkg; name = $Game; variant = 'full' })
if ($pkgNo) { $variants += @{ src = $pkgNo; name = "$($Game)_nostore"; variant = 'nostore' } }
foreach ($v in $variants) {
    $dest = Join-Path $outDir $v.name; Write-Step "assembling $dest"
    New-Delivery $v.src $dest $v.variant
    foreach ($f in @(@('StoreContent.tsv', 'store-content.tsv'), @('scrub-report.json', 'scrub-report.json'))) {
        if (Test-Path (Join-Path $v.src $f[0])) { Copy-Item -Force (Join-Path $v.src $f[0]) (Join-Path $outDir "$($v.name).$($f[1])") }
    }
    [void]$results.Add(@{ dest = $dest; name = $v.name; repo = $false })
}
$dsDir = Join-Path $info.Dir 'Dataset'
if (-not $NoDataset) { Write-Step "writing $dsDir"; New-Delivery $pkg $dsDir 'repo-dataset'; [void]$results.Add(@{ dest = $dsDir; name = 'Dataset'; repo = $true }) }

# ---- scan + validate, then zip ---------------------------------------------------------------------------------------
$fail = $false
foreach ($r in $results) {
    $o = & powershell -NoProfile -ExecutionPolicy Bypass -File $tool $Game -Rescan $r.dest 2>&1
    $verdict = @($o | Where-Object { $_ -match '^(PASS|FAIL)' })[0]
    Move-Item -Force "$($r.dest).rescan-hits.tsv" (Join-Path $outDir "$($r.name).rescan-hits.tsv") -ErrorAction SilentlyContinue
    $va = @('-Path', $r.dest); if ($r.repo) { $va += '-RepoDataset' }
    $vo = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator @va 2>&1
    $vv = @($vo | Where-Object { $_ -match '^(VALID|PENDING|INVALID)' })[0]
    Write-Host "  $($r.name): scan $($verdict -replace '\s+\S+$', '') | layout $vv"
    if ($verdict -notmatch '^PASS' -or $vv -notmatch '^(VALID|PENDING)') { $fail = $true; $vo | Where-Object { $_ -match '^\s+(x|!)' } | Write-Host }
}
if ($fail) { throw 'a delivery failed the scan or the layout check: nothing zipped' }
if (-not $NoZip) {
    foreach ($r in ($results | Where-Object { -not $_.repo })) {
        foreach ($old in @("$($r.name).zip", "$($r.name).pending.zip")) { $p = Join-Path $outDir $old; if (Test-Path $p) { Remove-Item -Force $p } }
        $zip = Join-Path $outDir "$($r.name)$(if ($status -ne 'complete') { '.pending' }).zip"
        Write-Step "zipping $zip"
        $n = [DatasetV1.T]::Zip($r.dest, $zip, $Game)
        $files = @(Get-ChildItem $r.dest -Recurse -File).Count
        if ($n -ne $files) { throw "zip $zip has $n entries, expected $files" }
        $r['zip'] = $zip; $r['zip_bytes'] = (Get-Item $zip).Length
    }
}
Write-Host ''
Write-Host "$($status.ToUpper())  $Game @ $short$(if ($Version) { " ($Version)" })" -ForegroundColor $(if ($status -eq 'complete') { 'Green' } else { 'Yellow' })
foreach ($r in $results) {
    $b = (Get-ChildItem $r.dest -Recurse -File | Measure-Object Length -Sum).Sum
    Write-Host ("  {0,-24} {1,10}  {2}{3}" -f $r.name, (Format-Bytes $b), $r.dest, $(if ($r['zip']) { "  ->  $($r['zip']) ($(Format-Bytes $r['zip_bytes']))" }))
}
Write-Host "  $($scen.Count) scenario videos; $([math]::Round(((Get-Date) - $t0).TotalMinutes, 1)) min"

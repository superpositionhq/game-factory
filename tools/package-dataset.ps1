<#
.SYNOPSIS
  Build the dataset layout v1.1 delivery (docs/game-deliverable.md, "Dataset layout v1.1"; docs/dataset-layout-v1.json) of
  one game from its finished package (tools\package-game.ps1 output, already scrubbed and scanned), and the game repo's
  Dataset\ folder. Usually run through package-game.ps1 -Dataset; nothing here is per game except the data.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\package-dataset.ps1 <game> `
      -Package %GF_ROOT%\deliverables\<game>\<game>_<sha8> -Version <version>
  ... -ReplayScripts <dir>\ReplayScripts      # once the creation replay is verified (ue_replay.py package: READY)

  Output, all in the game's own folder <repo>\ (git-ignored): <repo>\Dataset.zip, the full dataset (always with store
  content; top folder <game>/), or Dataset.pending.zip while ReplayScripts\ is missing (manifest status "pending",
  README banner); scratch in <repo>\.dataset\: the unpacked delivery <game>\, _videos\ and reports
  (<game>.store-content.tsv, .scrub-report.json, .rescan-hits.tsv). Writes <repo>\Dataset\ (no UEProject\, no Build\, LFS patterns in
  Dataset\.gitattributes); never commits. Every delivery is rescanned (package-game.ps1 -Rescan) and validated
  (validate-dataset.ps1) before anything is zipped.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [string]$Package,               # the full package folder (with store content); not with -Rescrub
    [switch]$Rescrub,               # re-scrub the existing <repo>\Dataset.zip (and with -AlsoRepoDataset the committed Dataset\) in place: current scrub rules for text, same-length session patches for binaries
    [switch]$AlsoRepoDataset,
    [string]$Version,
    [string]$ReplayScripts,
    [string]$OutRoot,               # default: the game's folder (Dataset.zip + .dataset\); a path puts both under <path>\<game>\ (tests)
    [switch]$NoDataset,
    [switch]$NoZip,
    [switch]$RebuildVideos
)

. (Join-Path $PSScriptRoot 'ue-pipeline\common.ps1')
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
    // -Rescrub: the build machine's session ids (known uuids) and session folder names inside any file, ASCII and
    // UTF-16LE, replaced by same-length neutral bytes (binary assets keep their layout, like scrub-import-paths does).
    public class Hit { public string Path; public int Uuids; public int Words; }
    static readonly string[] Words = { "scratchpad", "Scratchpad", "SCRATCHPAD", "side-session-notes", "Side-Session-Notes" };
    static readonly string[] WordRepl = { "scratchdir", "Scratchdir", "SCRATCHDIR", "session-notes-path", "Session-Notes-Path" };
    static bool Hex(byte c) { return (c >= 48 && c <= 57) || (c >= 97 && c <= 102) || (c >= 65 && c <= 70); }
    // a uuid (8-4-4-4-12) that starts at i with stride w (1 = ASCII, 2 = UTF-16LE)
    static string UuidAt(byte[] b, int i, int w) {
        if (i < 0 || i + 36 * w > b.Length) return null;
        var sb = new StringBuilder(36);
        for (int k = 0; k < 36; k++) {
            byte c = b[i + k * w]; if (w == 2 && b[i + k * w + 1] != 0) return null;
            if (k == 8 || k == 13 || k == 18 || k == 23) { if (c != 45) return null; } else if (!Hex(c)) return null;
            sb.Append((char)c);
        }
        return sb.ToString().ToLowerInvariant();
    }
    static int PutAscii(byte[] b, int i, int w, string s) { for (int k = 0; k < s.Length; k++) { b[i + k * w] = (byte)s[k]; if (w == 2) b[i + k * w + 1] = 0; } return s.Length; }
    static bool WordAt(byte[] b, int i, int w, string s) {
        if (i + s.Length * w > b.Length) return false;
        for (int k = 0; k < s.Length; k++) { if (b[i + k * w] != (byte)s[k] || (w == 2 && b[i + k * w + 1] != 0)) return false; }
        return true;
    }
    public static List<Hit> SessionScan(string root, string[] sessionIds, string skipExts, bool patch) {
        root = Path.GetFullPath(root).TrimEnd('\\') + "\\";
        var ids = new HashSet<string>(sessionIds, StringComparer.OrdinalIgnoreCase);
        var skip = new HashSet<string>((skipExts ?? "").Split(';'), StringComparer.OrdinalIgnoreCase);
        var hits = new List<Hit>(); var lk = new object();
        var files = new List<string>(Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories));
        Parallel.ForEach(files, new ParallelOptions { MaxDegreeOfParallelism = 6 }, f => {
            if (skip.Contains(Path.GetExtension(f))) return;
            byte[] b = File.ReadAllBytes(f); int nu = 0, nw = 0;
            for (int i = 0; i < b.Length; i++) {
                byte c = b[i];
                if (c == 45) {   // '-': the end of a uuid's first group, ASCII (i-8) or UTF-16LE (i-16)
                    foreach (int w in new[] { 1, 2 }) {
                        string u = UuidAt(b, i - 8 * w, w);
                        if (u != null && ids.Contains(u)) { nu++; if (patch) PutAscii(b, i - 8 * w, w, "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"); }
                    }
                } else if (c == 115 || c == 83) {   // s / S
                    for (int k = 0; k < Words.Length; k++)
                        foreach (int w in new[] { 1, 2 })
                            if (WordAt(b, i, w, Words[k])) { nw++; if (patch) PutAscii(b, i, w, WordRepl[k]); }
                }
            }
            if (nu + nw > 0) {
                if (patch) File.WriteAllBytes(f, b);
                lock (lk) hits.Add(new Hit { Path = f.Substring(root.Length).Replace('\\', '/'), Uuids = nu, Words = nw });
            }
        });
        hits.Sort((x, y) => string.CompareOrdinal(x.Path, y.Path));
        return hits;
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

# ---- -Rescrub: an existing Dataset.zip (no package or build needed) ---------------------------------------------------
# Extract to <repo>\.dataset\rescrub\, apply package-game's current scrub rules to every text file (-ScrubDir), patch
# the build machine's session ids and session folder names in every other file (same length), refresh manifest.json
# entries of changed files, check (session scan = 0, leak scan, layout), zip under a temporary name and swap it in.
function Get-SessionIds {
    $ids = New-Object System.Collections.Generic.HashSet[string]
    foreach ($act in @(Get-ChildItem (Join-Path $WorkRoot '.recording') -Filter actions.jsonl -Recurse -File -ErrorAction SilentlyContinue)) {
        foreach ($m in (Select-String -LiteralPath $act.FullName -AllMatches -Pattern '"session_id":\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"|Temp[\\/]{1,2}[^\\/"]+[\\/]{1,2}[^\\/"]+[\\/]{1,2}([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})').Matches) {
            foreach ($g in 1, 2) { if ($m.Groups[$g].Success) { [void]$ids.Add($m.Groups[$g].Value.ToLower()) } }
        }
    }
    return [string[]]@($ids)
}
function Invoke-SessionRescrub([string]$Dir, [string[]]$Ids, [string]$What) {
    $t0 = (Get-Date).AddSeconds(-2)
    Write-Step "$What`: text scrub (package-game -ScrubDir)"
    $o = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'package-game.ps1') $Game -ScrubDir $Dir 2>&1
    $o | Select-Object -Last 2 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "text scrub of $Dir failed" }
    # -ScrubDir writes <dir>.scrub.json next to the folder: for the repo's Dataset\ that is the repo root. Reports live
    # in the ignored scratch folder only.
    $sj = "$Dir.scrub.json"
    if (Test-Path -LiteralPath $sj) { Move-Item -Force -LiteralPath $sj -Destination (Join-Path $scratch "$(Split-Path $Dir -Leaf).rescrub-scrub.json") }
    # media and packed data are skipped; so are executables and libraries (third-party code may hold such words for its
    # own reasons; patching them could change behaviour): the patch is for assets' recorded import paths and logs
    $skip = '.mp4;.mkv;.mka;.wav;.flac;.ogg;.mp3;.png;.jpg;.jpeg;.pak;.ucas;.utoc;.zip;.dll;.exe;.pdb;.sys;.so;.dylib;.lib;.a;.o'
    $p = [DatasetV1.T]::SessionScan($Dir, $Ids, $skip, $true)
    Write-Step "$What`: binary session patches in $($p.Count) file(s)$(if ($p.Count) { ': ' + (($p | Select-Object -First 6 | ForEach-Object { "$($_.Path) ($($_.Uuids)+$($_.Words))" }) -join ', ') })"
    # manifest.json: refresh the entries of every file changed above
    $manPath = Join-Path $Dir 'manifest.json'
    if (Test-Path $manPath) {
        $man = Get-Content $manPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $changed = 0
        foreach ($e in @($man.files)) {
            $fp = Join-Path $Dir ($e.path -replace '/', '\')
            if ((Test-Path -LiteralPath $fp) -and (Get-Item -LiteralPath $fp).LastWriteTime -ge $t0) {
                $e.bytes = (Get-Item -LiteralPath $fp).Length; $e.sha256 = [DatasetV1.T]::HashFile($fp); $changed++
            }
        }
        if ($man.PSObject.Properties['totals']) { $man.totals.bytes = [long](@($man.files) | Measure-Object -Property bytes -Sum).Sum }
        Write-JsonFile $manPath $man
        Write-Step "$What`: manifest entries refreshed: $changed"
    }
    $left = [DatasetV1.T]::SessionScan($Dir, $Ids, $skip, $false)
    $nl = 0; foreach ($h in @($left)) { if ($h) { $nl += $h.Uuids + $h.Words } }
    Write-Step "$What`: session scan after: $nl"
    if ($nl) { throw "session traces left in $What`: $(($left | ForEach-Object { $_.Path }) -join ', ')" }
}
if ($Rescrub) {
    $info = Get-GameInfo $Game
    $zipPath = Join-Path $info.Dir 'Dataset.zip'
    if (-not (Test-Path -LiteralPath $zipPath)) { throw "no $zipPath to rescrub" }
    $scratch = Join-Path $info.Dir '.dataset'
    $work = Join-Path $scratch 'rescrub'
    [void](Assert-GFFreeSpace $info.Dir 'package-dataset -Rescrub')
    if (Test-Path $work) { Remove-Item -Recurse -Force $work }
    New-Item -ItemType Directory -Force $work | Out-Null
    $ids = Get-SessionIds
    Write-Step "rescrub $Game ($($ids.Count) session ids known): extracting $zipPath"
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $work)
    $top = Join-Path $work $Game
    if (-not (Test-Path $top)) { throw "the zip has no top folder $Game/" }
    Invoke-SessionRescrub $top $ids 'Dataset.zip'
    $leak = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'ue-pipeline\leak-scan.ps1') $top 2>&1
    Write-Step "leak scan: $(@($leak)[-1])"
    $val = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'validate-dataset.ps1') $top 2>&1
    $vline = @($val | Where-Object { $_ -match '^(VALID|PENDING|INVALID)' })[0]
    Write-Step "layout: $vline"
    if ($vline -notmatch '^(VALID|PENDING)') { $val | Where-Object { $_ -match '^\s+x' } | Write-Host; throw 'the rescrubbed delivery fails the layout check: Dataset.zip left as it was' }
    $tmpZip = Join-Path $scratch 'Dataset.zip.partial'
    Write-Step "zipping $tmpZip"
    $n = [DatasetV1.T]::Zip($top, $tmpZip, $Game)
    $files = @(Get-ChildItem $top -Recurse -File).Count
    if ($n -ne $files) { throw "zip has $n entries, expected $files" }
    Remove-Item -Force -LiteralPath $zipPath
    Move-Item -LiteralPath $tmpZip -Destination $zipPath
    Write-Step "swapped in $zipPath ($(Format-Bytes (Get-Item $zipPath).Length))"
    if ($AlsoRepoDataset) {
        $ds = Join-Path $info.Dir 'Dataset'
        if (Test-Path $ds) { Invoke-SessionRescrub $ds $ids 'repo Dataset\' }
        $st = @(& git -C $info.Dir status --porcelain -- Dataset)
        Write-Step "repo Dataset\: $(if ($st.Count) { "$($st.Count) changed path(s): commit Dataset/ in $($info.Dir)" } else { 'unchanged' })"
    }
    Remove-Item -Recurse -Force $work
    exit 0
}
if (-not $Package) { throw '-Package is required (unless -Rescrub)' }

$pkg = (Resolve-Path $Package).Path
$pkgNo = $null   # no _nostore variant any more (user decision 2026-10-12: always with store content, no _nostore variant)
$man = Get-Content (Join-Path $pkg 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$sha = $man.commit; $short = $sha.Substring(0, 8)
$info = Get-GameInfo $Game
# Everything lives in the game's own folder (user decision 2026-10-12): the full dataset zip is <game>\Dataset.zip
# (Dataset.pending.zip while ReplayScripts\ is missing); the unpacked delivery, videos and reports are scratch in
# <game>\.dataset\. Both are git-ignored (template .gitignore; added to .git/info/exclude below if a repo lacks it).
$outDir = if ($OutRoot) { Join-Path $OutRoot $Game } else { Join-Path $info.Dir '.dataset' }
$zipDir = if ($OutRoot) { $outDir } else { $info.Dir }
New-Item -ItemType Directory -Force $outDir | Out-Null
[void](Assert-GFFreeSpace $zipDir 'package-dataset')
if (-not $OutRoot) {
    $exclude = Join-Path $info.Dir '.git\info\exclude'
    foreach ($pat in '/Dataset.zip', '/Dataset.pending.zip', '/.dataset/') {
        $probe = $pat.Trim('/')
        & git -C $info.Dir check-ignore -q -- $probe 2>$null
        if ($LASTEXITCODE -ne 0) {
            Add-Content -LiteralPath $exclude -Value $pat -Encoding ascii
            Write-Step "added $pat to $exclude (the repo's .gitignore lacks it; commit it there)"
        }
    }
}
# One run per game at a time: two runs write the same folders (an open handle; the OS releases it if the run dies).
$lockPath = Join-Path $outDir '_dataset.lock'
try { $script:Lock = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None') }
catch [System.IO.IOException] { throw "another package-dataset run for $Game is in progress ($lockPath is held); wait for it to finish" }
$haveReplay = [bool]($ReplayScripts -and (Test-Path $ReplayScripts))
# A dataset is COMPLETE only with a passing creation-replay verification (ReplayScripts/Verification/report.json,
# verdict.pass; tools/ue-replay/verify.py): no verification, no COMPLETE.
$verdict = $null
if ($haveReplay) {
    $vr = Join-Path $ReplayScripts 'Verification\report.json'
    if (-not (Test-Path $vr)) { throw "ReplayScripts has no Verification\report.json: run ue_replay.py verify, then package" }
    $verdict = (Get-Content -Raw -Encoding UTF8 $vr | ConvertFrom-Json).verdict
    if (-not $verdict -or -not $verdict.pass) { throw "the creation replay's verification is not PASS ($vr): no COMPLETE dataset from it" }
}
$replayVerification = if ($verdict) {
    [ordered]@{ pass = [bool]$verdict.pass; report = 'ReplayScripts/Verification/report.md'
        criteria = @($verdict.criteria | ForEach-Object { [ordered]@{ id = $_.id; text = $_.text; result = $_.result; pass = [bool]$_.pass } })
        exclusions = @($verdict.exclusions.PSObject.Properties | ForEach-Object {
                $e = $_.Value
                if ($e -is [System.Array] -or $e -is [string]) { [ordered]@{ id = $_.Name; what = 'git-ignored extra files'; count = @($e).Count } }
                elseif ($e.PSObject.Properties.Name -contains 'maps') { [ordered]@{ id = $_.Name; what = $e.what; count = @($e.maps).Count; maps = @($e.maps) } }
                else { [ordered]@{ id = $_.Name; what = $e.what; count = $e.count } } }) }
} else { $null }
$status = if ($haveReplay) { 'complete' } else { 'pending' }
$pending = if ($haveReplay) { @() } else { @('ReplayScripts/') }
Write-Step "dataset v1: $Game @ $short ($status)  from $pkg"

# ---- Gameplay/<game>_S<n>.mp4: one video per scenario of the release version, game audio muxed ------------------------
# The package's runs are those of the packaged commit (package-game.ps1 -OnlyCommitRuns). One per scenario: the FIRST
# valid run (validation ok or warn), by time. The result (win/lose/timeout) is metadata, never a selection criterion.
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
        $_.Group | Sort-Object name | Select-Object -First 1 })   # run names start with the scenario and the start time
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
# $SkipExt). A delivery once came out without UEProject\ and Screenshots\ while Build\ was fine and nothing complained;
# a missing or short tree now stops the run here.
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
            layout = 'dataset-layout/v1.1'; game = $Game; title = $title; version = $Version; commit = $sha; status = $status; variant = $Variant
            pending = $(if ($pending) { [System.Collections.ArrayList]@($pending) } else { New-Object System.Collections.ArrayList }); created = (Get-IsoNow); source_package = (Split-Path $Src -Leaf)
            replay_verification = $replayVerification
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
        A '> **Pending:** `ReplayScripts/` (the replay of the creation process) is not in this delivery yet;'
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
    if ($status -eq 'complete') {
        A 'See `ReplayScripts/README.md` for the command and its options; the supplied project is not changed.'; A ''
        A ('The replay was run end to end, headless, from these scripts and verified against the release commit: **' +
           $(if ($replayVerification.pass) { 'PASS' } else { 'FAIL' }) + '** (`ReplayScripts/Verification/report.md`).'); A ''
        A '| Pass criterion | Result | Pass |'; A '|---|---|---|'
        foreach ($c in $replayVerification.criteria) { A "| $($c.text) | $($c.result) | $(if ($c.pass) { 'yes' } else { 'no' }) |" }
        A ''; A 'Known differences that are not content (normalised or not compared, listed explicitly):'; A ''
        foreach ($e in $replayVerification.exclusions) {
            $extra = if ($e.Contains('maps') -and $e.maps.Count) { ': ' + (($e.maps | ForEach-Object { ($_ -split '/')[-1] }) -join ', ') } else { '' }
            A "- ``$($e.id)`` ($($e.count)): $($e.what)$extra"
        }
    } else { A '`ReplayScripts/` is pending.' }
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
    $rhSrc = "$($r.dest).rescan-hits.tsv"; $rhDst = Join-Path $outDir "$($r.name).rescan-hits.tsv"
    if ([IO.Path]::GetFullPath($rhSrc) -ne [IO.Path]::GetFullPath($rhDst)) {
        Move-Item -Force $rhSrc $rhDst -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $rhSrc) { throw "could not move $rhSrc into $outDir (it would sit in the repo root)" }
    }
    $va = @('-Path', $r.dest); if ($r.repo) { $va += '-RepoDataset' }
    $vo = & powershell -NoProfile -ExecutionPolicy Bypass -File $validator @va 2>&1
    $vv = @($vo | Where-Object { $_ -match '^(VALID|PENDING|INVALID)' })[0]
    Write-Host "  $($r.name): scan $($verdict -replace '\s+\S+$', '') | layout $vv"
    if ($verdict -notmatch '^PASS' -or $vv -notmatch '^(VALID|PENDING)') { $fail = $true; $vo | Where-Object { $_ -match '^\s+(x|!)' } | Write-Host }
}
if ($fail) { throw 'a delivery failed the scan or the layout check: nothing zipped' }
if (-not $NoZip) {
    foreach ($r in ($results | Where-Object { -not $_.repo })) {
        # one name for every game: <game>\Dataset.zip (top folder inside stays <game>/)
        $zbase = if ($OutRoot) { $r.name } else { 'Dataset' }
        $zip = Join-Path $zipDir "$zbase$(if ($status -ne 'complete') { '.pending' }).zip"
        # written under a temporary name and swapped in only when complete: the old zip stays usable until then
        $tmpZip = Join-Path $outDir "$zbase.zip.partial"   # in the ignored scratch folder (same volume: a rename)
        if (Test-Path $tmpZip) { Remove-Item -Force $tmpZip }
        Write-Step "zipping $zip"
        $n = [DatasetV1.T]::Zip($r.dest, $tmpZip, $Game)
        $files = @(Get-ChildItem $r.dest -Recurse -File).Count
        if ($n -ne $files) { throw "zip $tmpZip has $n entries, expected $files" }
        foreach ($old in @("$zbase.zip", "$zbase.pending.zip")) { $p = Join-Path $zipDir $old; if (Test-Path $p) { Remove-Item -Force $p } }
        Move-Item -LiteralPath $tmpZip -Destination $zip
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

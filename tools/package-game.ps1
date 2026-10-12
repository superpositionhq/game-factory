<#
.SYNOPSIS
  Assemble one game into a deliverable folder + zip under %GF_ROOT%\deliverables\<game>\.
  Read-only on the game repo, its .recording logs, recordings and builds. Format: docs/game-deliverable.md.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\package-game.ps1 tower-defense -Commit milestone
  powershell -ExecutionPolicy Bypass -File tools\package-game.ps1 tower-defense -DryRun      # store split, build, gameplay; writes nothing
  powershell -ExecutionPolicy Bypass -File tools\package-game.ps1 tower-defense -Commit fefda00 -Build C:\...\builds\tower-defense\fefda000-shipping

  Output: deliverables\<game>\<game>_<sha8>\ and the same name .zip. Contents:
    UEProject\        the repo tree at the commit (git blobs + Git LFS objects from the repo's local LFS store; never
                      downloads), without Binaries/Intermediate/Saved/DerivedDataCache. Store (Fab) content kept out of
                      git is added from the game's working tree. Always with store content (no _nostore variant).
    StoreContent.tsv  every store-content file: included or dropped, path, bytes, sha256, source, why it counts as store content
    workflow.jsonl    workflow.jsonl at the commit
    git.log           every commit up to the commit, oldest first: message, anonymised author/date, full text diff;
                      binary and LFS files as path + sha256 + bytes
    History\          commits/actions/builds/runs.jsonl from .recording\<game>\, limited to the commit's lineage
    Gameplay\         every validated (ok|warn, no FAILED) gameplay bundle whose build commit is in the lineage + summary
    Build\            the packaged Shipping build: newest pipeline build in the lineage, else the game session's own
                      Packaged\Windows Shipping package tied to a commit by its build.package workflow row (stated, not
                      verified); -Build overrides; -AllowDevelopmentBuild accepts a Development pipeline build
    README.md         generated from the project's README/Docs, assets.manifest.json and the package itself
    scrub-report.json what the deliverable scrub changed: counts per rule, files touched, binary findings (no original values)
    manifest.json     path, bytes, sha256 of every file (after the scrub)

  Scrub (package copy only; the repo, .recording and recordings are never written): every text file gets, in order,
  agent trailer lines removed, the agent identity -> dev, the names Superposition / game-factory replaced (scrub-history
  defaults), git author names/handles -> dev_NN, the account user name (incl. in user paths) -> dev, e-mail addresses ->
  <redacted-email>, other agent/provider mentions -> agent/provider. Then every file is rescanned: it refuses (exit 2,
  nothing published, hits in deliverables\<game>\<name>.refused-hits.tsv) on any remaining hit in a path or text file,
  or any blocked term in a binary (ASCII or UTF-16). One exception: the short terms (claude, opus) inside the
  compressed audio/video stream payload of .mp4/.mkv/.mka/.wav are random bytes and are listed, not refused
  (allowed-stream in <name>.allowlisted.tsv, file + offset + term); container metadata, tags, chapters, subtitle
  tracks and file names still refuse. Binaries are never edited; user name / agent findings in binaries
  are listed in scrub-report.json. Other user-folder paths are reported in deliverables\<game>\<name>.leaks.tsv.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [string]$Commit = 'HEAD',       # a rev, or 'milestone': the commit of the highest milestone/autoplay-<n> tag (HEAD without one)
    [switch]$WithoutStoreContent,   # retired: refused (user decision 2026-10-12: always with store content, no _nostore variant)
    [string]$Build,                 # packaged build dir (holding Windows\ or the exe); default: newest pipeline build in the lineage
    [string]$BuildCommit,           # with -Build for a dir without build_info.json: the commit it was built from (stated, unverified)
    [switch]$AllowDevelopmentBuild, # use a Development pipeline build when no Shipping build exists in the lineage
    [switch]$IncludePdb,
    [string]$PlayNote,
    [string]$Version,
    [switch]$PendingCleanBuild,     # allow a build with the account name compiled in: the package is marked "pending clean build", not final               # release version for README and manifest.json (e.g. 1.0); the tag release/<v> is named when it points at the commit              # extra sentence for the README's Play section (e.g. a launch requirement of the build)
    [switch]$NoScrub,               # diagnostics only: skip the deliverable scrub (the scan then refuses)
    [string[]]$StoreFolders = @(),  # extra paths (relative to the project) that count as store content
    [string[]]$ExcludeRuns = @(),   # gameplay run ids to leave out although they validated (e.g. superseded recordings)
    [switch]$OnlyCommitRuns,
    [ValidateSet('auto', 'repo', 'stills')][string]$Screenshots = 'auto',   # auto: the project's docs/screenshots/, else stills of the packaged runs        # only runs played on a build of the packaged commit itself (not of earlier commits)
    [string[]]$ExcludeSessions = @(), # session ids whose actions.jsonl rows are not creation work (packager sessions are left out anyway)
    [string]$RepoPath,              # package this clone (e.g. a scrubbed copy) instead of games\<game>
    [string]$OutRoot,               # default GF_OUT, else <root>\deliverables (machine/lib/gf-root.ps1 Get-GFOut)
    [ValidateSet('Fastest', 'Optimal', 'NoCompression')][string]$ZipLevel = 'Fastest',
    [switch]$NoZip,
    [switch]$Force,
    [switch]$KeepRefused,
    [switch]$DryRun,                # print the store-content split, build and gameplay selection; write nothing
    [string]$Rescan,                # an existing package folder: check it against the current rules, write <dir>.rescan-hits.tsv; changes nothing
    [string]$ScrubDir,              # a folder joining a delivery: apply the scrub rules to its text files in place (<dir>.scrub.json)
    [switch]$Dataset,               # after packaging, build the dataset layout v1.1 delivery (package-dataset.ps1); see the end of this file
    [string]$ReplayScripts          # with -Dataset: ReplayScripts\ from the replay session
)

. (Join-Path $PSScriptRoot 'ue-pipeline\common.ps1')
if (-not $OutRoot) { $OutRoot = Get-GFOut }   # GF_OUT / config "out", else <root>\deliverables
# scrub-in-place and rescan write next to nothing: no free-space floor for them
if (-not $ScrubDir -and -not $Rescan) { [void](Assert-GFFreeSpace $OutRoot 'package-game') }
$ToolVersion = 1
$t0 = Get-Date

# ---------------------------------------------------------------------------------------------------------------------
# C# helpers: tree export, copying, hashing, scanning, scrubbing, git.log, zip (PowerShell 5.1 is too slow for 10+ GB)
# ---------------------------------------------------------------------------------------------------------------------
$cs = @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace GameDeliverable {

public class PkgFile {
    public string Path; public long Bytes; public string Sha256; public string Source; public string Store; public string Note;
}

public class Hit { public string Path; public string Kind; public long Where; public string Text; }
public class ScrubResult { public string Path; public int[] Counts; }

public class StoreMatcher {
    Dictionary<string, string> exact = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    List<KeyValuePair<Regex, string>> globs = new List<KeyValuePair<Regex, string>>();
    public int Count { get { return exact.Count + globs.Count; } }
    public void Add(string pattern, string why) {
        string p = pattern.Replace('\\', '/').Trim().TrimEnd('/');
        while (p.StartsWith("./")) p = p.Substring(2);
        if (p.Length == 0) return;
        if (p.IndexOf('*') >= 0 || p.IndexOf('?') >= 0) {
            string rx = "^" + Regex.Escape(p).Replace("\\*", "[^/]*").Replace("\\?", "[^/]") + "(/.*)?$";
            globs.Add(new KeyValuePair<Regex, string>(new Regex(rx, RegexOptions.IgnoreCase), why));
        } else if (!exact.ContainsKey(p)) exact[p] = why;
    }
    // A path is store content when a directory in it is named Fab, or it (or its object path without extension, or one
    // of its parent folders) was added.
    public string Match(string path) {
        string[] parts = path.Split('/');
        for (int i = 0; i < parts.Length - 1; i++)
            if (string.Equals(parts[i], "Fab", StringComparison.OrdinalIgnoreCase)) return "folder named Fab (" + string.Join("/", parts, 0, i + 1) + ")";
        string r;
        if (exact.TryGetValue(path, out r)) return r;
        int dot = path.LastIndexOf('.'), slash = path.LastIndexOf('/');
        string noext = dot > slash ? path.Substring(0, dot) : null;
        if (noext != null && exact.TryGetValue(noext, out r)) return r;
        int idx = path.IndexOf('/');
        while (idx > 0) { if (exact.TryGetValue(path.Substring(0, idx), out r)) return r; idx = path.IndexOf('/', idx + 1); }
        foreach (var g in globs) { if (g.Key.IsMatch(path) || (noext != null && g.Key.IsMatch(noext))) return g.Value; }
        return null;
    }
}

public class GitBatch : IDisposable {
    Process p; Stream outS; Stream inS;
    public GitBatch(string git, string repo) {
        var psi = new ProcessStartInfo(git, "-C \"" + repo + "\" cat-file --batch");
        psi.UseShellExecute = false; psi.RedirectStandardInput = true; psi.RedirectStandardOutput = true; psi.CreateNoWindow = true;
        p = Process.Start(psi); outS = new BufferedStream(p.StandardOutput.BaseStream, 1 << 20); inS = p.StandardInput.BaseStream;
        // .NET may already have written a UTF-8 BOM to stdin (console code page 65001): send a throwaway first line.
        inS.WriteByte((byte)'\n'); inS.Flush(); ReadHeader();
    }
    string ReadHeader() {
        var ms = new MemoryStream(); int b;
        while ((b = outS.ReadByte()) >= 0 && b != '\n') ms.WriteByte((byte)b);
        if (b < 0 && ms.Length == 0) return null;
        return Encoding.UTF8.GetString(ms.ToArray());
    }
    // Returns null when the object is missing. spec: an object id or "<rev>:<path>".
    public byte[] Read(string spec, out string type) {
        byte[] q = Encoding.UTF8.GetBytes(spec + "\n"); inS.Write(q, 0, q.Length); inS.Flush();
        string h = ReadHeader(); if (h == null) throw new IOException("git cat-file --batch ended");
        string[] parts = h.Split(' ');
        if (parts.Length < 3) { type = "missing"; return null; }
        type = parts[1]; long size = long.Parse(parts[2]);
        byte[] data = new byte[size]; int off = 0;
        while (off < size) { int n = outS.Read(data, off, (int)Math.Min(size - off, 1 << 20)); if (n <= 0) throw new IOException("short read from git cat-file"); off += n; }
        outS.ReadByte();
        return data;
    }
    public void Dispose() { try { inS.Close(); p.WaitForExit(15000); } catch { } }
}

public static class Tools {
    static readonly Encoding Latin1 = Encoding.GetEncoding(28591);
    public static string Git = "git";

    public static bool ContainsAscii(string path, string needle) {
        byte[] n = Encoding.ASCII.GetBytes(needle); byte[] d = File.ReadAllBytes(path);
        for (int i = 0; i + n.Length <= d.Length; i++) {
            if (d[i] != n[0]) continue;
            int k = 1; while (k < n.Length && d[i + k] == n[k]) k++;
            if (k == n.Length) return true;
        }
        return false;
    }

    public static string Sha(byte[] data) { using (var h = new SHA256Cng()) return Hex(h.ComputeHash(data)); }
    public static string Hex(byte[] b) { var sb = new StringBuilder(b.Length * 2); foreach (byte x in b) sb.Append(x.ToString("x2")); return sb.ToString(); }
    public static string HashFile(string path) {
        using (var h = new SHA256Cng()) using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20)) return Hex(h.ComputeHash(fs));
    }

    public static byte[] RunGit(string repo, string args, out string stderr) {
        var psi = new ProcessStartInfo(Git, "-C \"" + repo + "\" " + args);
        psi.UseShellExecute = false; psi.RedirectStandardOutput = true; psi.RedirectStandardError = true; psi.CreateNoWindow = true;
        var p = Process.Start(psi); var err = new StringBuilder();
        p.ErrorDataReceived += (s, e) => { if (e.Data != null) lock (err) err.AppendLine(e.Data); };
        p.BeginErrorReadLine();
        var ms = new MemoryStream(); p.StandardOutput.BaseStream.CopyTo(ms); p.WaitForExit();
        stderr = err.ToString();
        if (p.ExitCode != 0) throw new Exception("git " + args + " failed: " + stderr);
        return ms.ToArray();
    }

    public static string ReadBlobText(string repo, string spec) {
        using (var gb = new GitBatch(Git, repo)) { string t; byte[] d = gb.Read(spec, out t); if (d == null || t != "blob") return null; return Encoding.UTF8.GetString(d); }
    }
    public static bool WriteBlob(string repo, string spec, string dst) {
        using (var gb = new GitBatch(Git, repo)) { string t; byte[] d = gb.Read(spec, out t); if (d == null || t != "blob") return false; File.WriteAllBytes(dst, d); return true; }
    }

    static bool IsExcluded(string path, string[] excludeTop) {
        string top = path.Split('/')[0];
        foreach (var e in excludeTop) if (string.Equals(top, e, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    // Writes the tree of `commit` to outDir. Git LFS pointers are replaced by the object from lfsDir (the repo's own store).
    public static List<PkgFile> ClassifyTree(string repo, string commit, StoreMatcher store) {
        string err; byte[] lst = RunGit(repo, "ls-tree -r -z -l --full-tree " + commit, out err);
        var result = new List<PkgFile>(); int start = 0;
        for (int i = 0; i < lst.Length; i++) {
            if (lst[i] != 0) continue;
            string entry = Encoding.UTF8.GetString(lst, start, i - start); start = i + 1;
            int tab = entry.IndexOf('\t'); string[] meta = entry.Substring(0, tab).Split(new char[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
            if (meta[1] != "blob") continue;
            var f = new PkgFile(); f.Path = entry.Substring(tab + 1); f.Store = store.Match(f.Path); f.Source = "git"; long.TryParse(meta[3], out f.Bytes);
            result.Add(f);
        }
        return result;
    }

    public static List<PkgFile> ExportTree(string repo, string commit, string outDir, StoreMatcher store, bool includeStore,
                                           string lfsDir, string[] excludeTop, List<PkgFile> dropped, List<string> problems) {
        string err; byte[] lst = RunGit(repo, "ls-tree -r -z --full-tree " + commit, out err);
        var result = new List<PkgFile>();
        byte[] magic = Encoding.ASCII.GetBytes("version https://git-lfs.github.com/spec/");
        using (var gb = new GitBatch(Git, repo)) {
            int start = 0;
            for (int i = 0; i < lst.Length; i++) {
                if (lst[i] != 0) continue;
                string entry = Encoding.UTF8.GetString(lst, start, i - start); start = i + 1;
                int tab = entry.IndexOf('\t'); string[] meta = entry.Substring(0, tab).Split(' '); string path = entry.Substring(tab + 1);
                string mode = meta[0], type = meta[1], oid = meta[2];
                if (IsExcluded(path, excludeTop)) { problems.Add("note: tracked path left out (build output folder): " + path); continue; }
                if (type == "commit") { problems.Add("note: submodule left out: " + path); continue; }
                if (type != "blob") continue;
                string t; byte[] data = gb.Read(oid, out t);
                if (data == null) { problems.Add("error: missing git object " + oid + " for " + path); continue; }
                var f = new PkgFile(); f.Path = path; f.Source = "git"; f.Store = store.Match(path);
                string lfsOid = null; long lfsSize = -1;
                if (data.Length < 1024 && data.Length > magic.Length) {
                    bool m = true; for (int k = 0; k < magic.Length; k++) if (data[k] != magic[k]) { m = false; break; }
                    if (m) {
                        foreach (string ln in Encoding.ASCII.GetString(data).Split('\n')) {
                            if (ln.StartsWith("oid sha256:")) lfsOid = ln.Substring(11).Trim();
                            else if (ln.StartsWith("size ")) lfsSize = long.Parse(ln.Substring(5).Trim());
                        }
                    }
                }
                if (lfsOid != null) { f.Source = "git-lfs"; f.Bytes = lfsSize; f.Sha256 = lfsOid; }
                else { f.Bytes = data.Length; f.Sha256 = Sha(data); }
                if (mode == "120000") f.Note = "symlink, stored as a file holding its target";
                if (f.Store != null && !includeStore) { dropped.Add(f); continue; }
                string dst = Path.Combine(outDir, path.Replace('/', '\\'));
                if (dst.Length >= 260) { problems.Add("error: path too long for Windows (" + dst.Length + " chars): " + dst); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(dst));
                if (lfsOid != null) {
                    string src = Path.Combine(lfsDir, lfsOid.Substring(0, 2), lfsOid.Substring(2, 2), lfsOid);
                    if (!File.Exists(src)) { problems.Add("error: Git LFS object " + lfsOid + " not in the local store, for " + path); continue; }
                    if (new FileInfo(src).Length != lfsSize) { problems.Add("error: Git LFS object " + lfsOid + " has the wrong size, for " + path); continue; }
                    File.Copy(src, dst, true);
                } else File.WriteAllBytes(dst, data);
                result.Add(f);
            }
        }
        return result;
    }

    // Lists (and with copy=true copies) every file under srcDir. rel paths get relPrefix ("Content/Foo/").
    public static List<PkgFile> CopyTree(string srcDir, string dstDir, string relPrefix, string[] skipExt, bool copy, bool hash,
                                         string source, string store, List<string> problems) {
        var result = new List<PkgFile>();
        var skip = new HashSet<string>(skipExt, StringComparer.OrdinalIgnoreCase);
        string root = Path.GetFullPath(srcDir).TrimEnd('\\') + "\\";
        foreach (string full in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)) {
            if (skip.Contains(Path.GetExtension(full))) continue;
            string rel = full.Substring(root.Length);
            var f = new PkgFile(); f.Path = relPrefix + rel.Replace('\\', '/'); f.Bytes = new FileInfo(full).Length; f.Source = source; f.Store = store;
            if (copy) {
                string dst = Path.Combine(dstDir, rel);
                if (dst.Length >= 260) { problems.Add("error: path too long for Windows (" + dst.Length + " chars): " + dst); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(dst));
                File.Copy(full, dst, true);
            }
            result.Add(f);
        }
        if (hash) Parallel.ForEach(result, new ParallelOptions { MaxDegreeOfParallelism = 6 }, f => {
            f.Sha256 = HashFile(Path.Combine(root, f.Path.Substring(relPrefix.Length).Replace('/', '\\')));
        });
        return result;
    }

    public static List<PkgFile> HashAll(string root) {
        root = Path.GetFullPath(root).TrimEnd('\\') + "\\";
        var result = new List<PkgFile>();
        foreach (string full in Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)) {
            var f = new PkgFile(); f.Path = full.Substring(root.Length).Replace('\\', '/'); f.Bytes = new FileInfo(full).Length; result.Add(f);
        }
        Parallel.ForEach(result, new ParallelOptions { MaxDegreeOfParallelism = 6 }, f => { f.Sha256 = HashFile(root + f.Path.Replace('/', '\\')); });
        result.Sort((a, b) => string.CompareOrdinal(a.Path, b.Path));
        return result;
    }

    // Formats that are binary even when their first 8 KB hold no NUL byte (Radiance .hdr starts with a text header).
    static readonly HashSet<string> BinaryExt = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {
        ".hdr", ".exr", ".bmp", ".png", ".jpg", ".jpeg", ".tga", ".dds", ".psd", ".tif", ".tiff", ".fbx", ".glb", ".uasset", ".umap",
        ".wav", ".ogg", ".mp3", ".flac", ".mkv", ".mka", ".mp4", ".pak", ".ucas", ".utoc", ".exe", ".dll", ".zip", ".7z", ".ttf", ".otf", ".bin" };
    public static bool IsText(string path) {
        if (BinaryExt.Contains(Path.GetExtension(path))) return false;
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read)) {
            byte[] b = new byte[8000]; int n = fs.Read(b, 0, b.Length);
            if (n >= 2 && ((b[0] == 0xFF && b[1] == 0xFE) || (b[0] == 0xFE && b[1] == 0xFF))) return true;
            for (int i = 0; i < n; i++) if (b[i] == 0) return false;
            return true;
        }
    }

    static string DecodeText(byte[] d) {
        if (d.Length >= 2 && d[0] == 0xFF && d[1] == 0xFE) return Encoding.Unicode.GetString(d);
        if (d.Length >= 2 && d[0] == 0xFE && d[1] == 0xFF) return Encoding.BigEndianUnicode.GetString(d);
        return Encoding.UTF8.GetString(d);
    }

    // Text files: every match of `banned` (the enforced pattern) is a hit; `leak` matches are collected separately.
    // Binary files: ASCII and UTF-16LE search for each needle; kind "binary-*" when its refuse flag is set, else
    // "binary-info-*" (reported only); Text = the needle's category. File paths are matched against `banned` too.
    // allow: a match whose surrounding word (letters, digits, _ . / : -) matches it is recorded as "allowed-*" instead of a
    // hit (the Opus audio codec in engine binaries and media); null = nothing allowed.
    public static Regex Allow = null;       // text files
    public static Regex AllowBin = null;    // binary files (adds bare codec names)
    // "opus" is four letters and turns up inside ordinary words and compressed bytes (stOPUSing, Octopus, base64), so it
    // counts only as a word of its own: starting at a non-letter or a lower->upper camel boundary, not followed by a
    // lowercase letter. Every other needle counts as any case-insensitive substring.
    static bool IsUpper(int c) { return c >= 'A' && c <= 'Z'; }
    static bool IsLower(int c) { return c >= 'a' && c <= 'z'; }
    // ...and only spelled the way a word is written (opus, Opus, OPUS): random bytes give oPuS, OpUs, ...
    static bool OpusToken(int prev, int c0, int c1, int c2, int c3, int next) {
        bool lower = IsLower(c0) && IsLower(c1) && IsLower(c2) && IsLower(c3);
        bool cap = IsUpper(c0) && IsLower(c1) && IsLower(c2) && IsLower(c3);
        bool upper = IsUpper(c0) && IsUpper(c1) && IsUpper(c2) && IsUpper(c3);
        if (!(lower || cap || upper)) return false;
        bool start = prev < 0 || !(IsUpper(prev) || IsLower(prev)) || (IsLower(prev) && c0 == 'O');
        return start && !IsLower(next);
    }
    // In binaries a string is a run of printable characters: count the run around a hit (ASCII bytes, or UTF-16 code
    // units with a zero high byte). Compressed data seldom holds 8 printable bytes in a row; compiled-in strings do.
    static bool Printable(int c) { return c >= 0x20 && c <= 0x7E; }
    static int PrintRun(byte[] b, int at, int n, int len, bool wide) {
        int step = wide ? 2 : 1, run = wide ? n / 2 : n;
        for (int p = at - step; p >= 0 && run < 64; p -= step) { if (!Printable(b[p]) || (wide && b[p + 1] != 0)) break; run++; }
        for (int p = at + n; p + (wide ? 1 : 0) < len && run < 64; p += step) { if (!Printable(b[p]) || (wide && b[p + 1] != 0)) break; run++; }
        return run;
    }
    static readonly Regex WordCh = new Regex(@"[A-Za-z0-9_./:\-]");
    static readonly Regex EscLead = new Regex(@"^(?:u[0-9a-fA-F]{4}|[nrtfb])");
    static string WordAt(string s, int at, int len) {
        int a = at; while (a > 0 && at - a < 40 && WordCh.IsMatch(s[a - 1].ToString())) a--;
        int z = at + len; while (z < s.Length && z - at - len < 40 && WordCh.IsMatch(s[z].ToString())) z++;
        string w = s.Substring(a, z - a);
        if (a > 0 && s[a - 1] == '\\') { var m = EscLead.Match(w); if (m.Success && m.Length < at - a + 1) w = w.Substring(m.Length); }   // after a JSON escape (\n, <)
        return w;
    }
    // UE's locale ids zh_<name> / zh-<name> contain the account name; they stay allowed when glued into a locale table
    public static string LocaleNeedle = null;
    static bool LocaleHit(string s, int at, int len) {
        return LocaleNeedle != null && len == LocaleNeedle.Length && at >= 3 && string.Equals(s.Substring(at, len), LocaleNeedle, StringComparison.OrdinalIgnoreCase)
            && (s[at - 3] == 'z' || s[at - 3] == 'Z') && (s[at - 2] == 'h' || s[at - 2] == 'H') && (s[at - 1] == '_' || s[at - 1] == '-');
    }
    public static List<Hit> Scan(string root, IList<string> rels, Regex banned, Regex leak, List<Hit> leaks, int maxPerFile,
                                 string[] needles, bool[] refuse, string[] category) {
        root = Path.GetFullPath(root).TrimEnd('\\') + "\\";
        var hits = new List<Hit>();
        var asc = new List<byte[]>(); var u16 = new List<byte[]>(); var first = new bool[256];
        foreach (string n in needles) {
            byte[] a = Encoding.ASCII.GetBytes(n.ToLowerInvariant()); asc.Add(a); u16.Add(Encoding.Unicode.GetBytes(n.ToLowerInvariant())); first[a[0]] = true;
        }
        Parallel.ForEach(rels, new ParallelOptions { MaxDegreeOfParallelism = 6 }, rel => {
            var mine = new List<Hit>(); var myLeaks = new List<Hit>();
            if (banned.IsMatch(rel)) { var h = new Hit(); h.Path = rel; h.Kind = "path"; h.Text = rel; mine.Add(h); }
            string full = root + rel.Replace('/', '\\');
            var fi = new FileInfo(full);
            if (fi.Length > 0 && fi.Length < (256L << 20) && IsText(full)) {
                string text = DecodeText(File.ReadAllBytes(full));
                long line = 1; int pos = 0, found = 0;
                while (pos <= text.Length) {
                    int nl = text.IndexOf('\n', pos); if (nl < 0) nl = text.Length;
                    string s = text.Substring(pos, nl - pos);
                    foreach (Match m in banned.Matches(s)) {
                        if (m.Length == 4 && string.Equals(m.Value, "opus", StringComparison.OrdinalIgnoreCase)
                            && !OpusToken(m.Index > 0 ? s[m.Index - 1] : -1, s[m.Index], s[m.Index + 1], s[m.Index + 2], s[m.Index + 3],
                                          m.Index + 4 < s.Length ? s[m.Index + 4] : -1)) continue;
                        if (LocaleHit(s, m.Index, m.Length)) { var lh = new Hit(); lh.Path = rel; lh.Kind = "allowed-text"; lh.Where = line; lh.Text = "zh_" + m.Value; mine.Add(lh); continue; }
                        if (Allow != null) {
                            string w = WordAt(s, m.Index, m.Length);
                            if (Allow.IsMatch(w)) { var ah = new Hit(); ah.Path = rel; ah.Kind = "allowed-text"; ah.Where = line; ah.Text = w; mine.Add(ah); continue; }
                        }
                        if (found++ < maxPerFile) { var h = new Hit(); h.Path = rel; h.Kind = "text"; h.Where = line; h.Text = Snip(s, m.Index, m.Length); mine.Add(h); }
                    }
                    if (leak != null) foreach (Match m in leak.Matches(s)) { var h = new Hit(); h.Path = rel; h.Kind = "leak"; h.Where = line; h.Text = m.Value; myLeaks.Add(h); }
                    pos = nl + 1; line++;
                }
                if (found > maxPerFile) { var h = new Hit(); h.Path = rel; h.Kind = "text-more"; h.Where = found; h.Text = (found - maxPerFile) + " more"; mine.Add(h); }
            } else if (fi.Length > 0 && needles.Length > 0) {
                ScanBinary(full, rel, asc, u16, first, refuse, category, mine, maxPerFile);
            }
            lock (hits) { hits.AddRange(mine); leaks.AddRange(myLeaks); }
        });
        hits.Sort((a, b) => { int c = string.CompareOrdinal(a.Path, b.Path); return c != 0 ? c : a.Where.CompareTo(b.Where); });
        return hits;
    }

    static string Snip(string s, int at, int len) {
        int a = Math.Max(0, at - 60), b = Math.Min(s.Length, at + len + 60);
        return s.Substring(a, b - a).Replace("\t", " ").Replace("\r", "");
    }

    static void ScanBinary(string full, string rel, List<byte[]> asc, List<byte[]> u16, bool[] first, bool[] refuse, string[] category,
                           List<Hit> hits, int maxPerFile) {
        const int Chunk = 4 << 20, Overlap = 64;
        byte[] buf = new byte[Chunk + Overlap]; int carry = 0; long baseOff = 0; int found = 0, streamHits = 0;
        List<long[]> payload = StreamTerms.Count > 0 ? MediaPayload(full) : null;
        var streamOk = new bool[asc.Count];
        for (int k = 0; k < asc.Count; k++) streamOk[k] = StreamTerms.Contains(Encoding.ASCII.GetString(asc[k]));
        using (var fs = new FileStream(full, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20)) {
            while (true) {
                int n = fs.Read(buf, carry, Chunk); if (n <= 0) break;
                int len = carry + n;
                for (int i = 0; i < len; i++) {
                    byte c = buf[i]; if (c >= 'A' && c <= 'Z') c = (byte)(c + 32);
                    if (!first[c]) continue;
                    for (int k = 0; k < asc.Count; k++) {
                        string kind = refuse[k] ? "binary" : "binary-info";
                        bool a8 = Eq(buf, i, len, asc[k], false), a16 = !a8 && Eq(buf, i, len, u16[k], true);
                        if (!a8 && !a16) continue;
                        if (asc[k].Length == 4 && asc[k][0] == 'o' && asc[k][1] == 'p' && asc[k][2] == 'u' && asc[k][3] == 's') {
                            int prev, next, st = a8 ? 1 : 2;
                            if (a8) { prev = i > 0 ? buf[i - 1] : -1; next = i + 4 < len ? buf[i + 4] : -1; }
                            else { prev = (i >= 2 && buf[i - 1] == 0) ? buf[i - 2] : -1; next = (i + 9 < len && buf[i + 9] == 0) ? buf[i + 8] : -1; }
                            if (!OpusToken(prev, buf[i], buf[i + st], buf[i + 2 * st], buf[i + 3 * st], next)) continue;
                            if (PrintRun(buf, i, a8 ? 4 : 8, len, !a8) < 8) continue;
                        }
                        if (LocaleNeedle != null && category[k] == "username") {   // zh_<name> / zh-<name> locale ids, also glued in locale tables
                            int st2 = a8 ? 1 : 2; int p3 = i - 3 * st2;
                            if (p3 >= 0 && (buf[p3] | 0x20) == 'z' && (buf[p3 + st2] | 0x20) == 'h' && (buf[p3 + 2 * st2] == '_' || buf[p3 + 2 * st2] == '-')
                                && (a8 || (buf[p3 + 1] == 0 && buf[p3 + st2 + 1] == 0 && buf[p3 + 2 * st2 + 1] == 0))) {
                                AddAllowed(hits, rel, (a8 ? "allowed-ascii" : "allowed-utf16"), baseOff + i, category[k] + ":zh_" + LocaleNeedle); continue;
                            }
                        }
                        // the word around the hit, decoded the same way it was found
                        string w = a8 ? BinWord8(buf, i, asc[k].Length, len) : BinWord16(buf, i, u16[k].Length, len);
                        if (AllowBin != null && AllowBin.IsMatch(w)) { AddAllowed(hits, rel, (a8 ? "allowed-ascii" : "allowed-utf16"), baseOff + i, category[k] + ":" + w); continue; }
                        if (payload != null && streamOk[k] && streamHits < MaxStreamHitsPerFile
                            && InRanges(payload, baseOff + i, baseOff + i + (a8 ? asc[k].Length : u16[k].Length))) {
                            bool dup = false; foreach (var x in hits) if (x.Where == baseOff + i) { dup = true; break; }
                            if (!dup) { var sh = new Hit(); sh.Path = rel; sh.Kind = "allowed-stream" + (a8 ? "-ascii" : "-utf16"); sh.Where = baseOff + i;
                                        sh.Text = category[k] + ":" + Encoding.ASCII.GetString(asc[k]) + " in " + w; hits.Add(sh); streamHits++; }
                            continue;
                        }
                        Add(hits, rel, kind + (a8 ? "-ascii" : "-utf16"), baseOff + i, category[k] + ":" + w, ref found);
                    }
                    if (found >= maxPerFile) return;
                }
                if (len > Overlap) { Buffer.BlockCopy(buf, len - Overlap, buf, 0, Overlap); baseOff += len - Overlap; carry = Overlap; }
                else { carry = len; }
                // the overlap region is scanned twice; Add() drops duplicates by offset
            }
        }
    }
    static bool Eq(byte[] buf, int i, int len, byte[] needle, bool wide) {
        if (i + needle.Length > len) return false;
        for (int k = 0; k < needle.Length; k++) {
            byte c = buf[i + k];
            if (wide) { if ((k & 1) == 1) { if (c != 0) return false; continue; } }
            if (c >= 'A' && c <= 'Z') c = (byte)(c + 32);
            byte want = needle[k]; if (want >= 'A' && want <= 'Z') want = (byte)(want + 32);
            if (c != want) return false;
        }
        return true;
    }
    static bool IsWordByte(byte c) { return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '.' || c == '/' || c == ':' || c == '-'; }
    static string BinWord8(byte[] b, int at, int n, int len) {
        int a = at; while (a > 0 && at - a < 40 && IsWordByte(b[a - 1])) a--;
        int z = at + n; while (z < len && z - at - n < 40 && IsWordByte(b[z])) z++;
        return Encoding.ASCII.GetString(b, a, z - a);
    }
    static string BinWord16(byte[] b, int at, int n, int len) {
        int a = at; while (a >= 2 && at - a < 80 && b[a - 1] == 0 && IsWordByte(b[a - 2])) a -= 2;
        int z = at + n; while (z + 1 < len && z - at - n < 80 && b[z + 1] == 0 && IsWordByte(b[z])) z += 2;
        return Encoding.Unicode.GetString(b, a, z - a);
    }
    // allowed hits: kept for the report (one per offset), never counted against maxPerFile, capped at 200 per file
    static void AddAllowed(List<Hit> hits, string rel, string kind, long off, string text) {
        int n = 0; foreach (var x in hits) { if (x.Where == off) return; if (x.Kind.StartsWith("allowed")) n++; }
        if (n >= 200) return;
        var h = new Hit(); h.Path = rel; h.Kind = kind; h.Where = off; h.Text = text; hits.Add(h);
    }
    static void Add(List<Hit> hits, string rel, string kind, long off, string cat, ref int found) {
        foreach (var x in hits) if (x.Path == rel && x.Where == off) return;
        var h = new Hit(); h.Path = rel; h.Kind = kind; h.Where = off; h.Text = cat; hits.Add(h); found++;
    }

    // ---- compressed media payloads (user rule, 2026-10-12) ----
    // Inside the compressed audio/video stream payload of .mp4/.mkv/.mka/.wav, a hit on one of StreamTerms (the short
    // blocked terms) is random bytes, not text: it is recorded as "allowed-stream-*" with file, offset and term (in
    // <name>.allowlisted.tsv) instead of refusing. Container metadata, tags, chapters, subtitle/other tracks and file
    // names are outside the payload ranges and still refuse; every other term refuses everywhere.
    public static HashSet<string> StreamTerms = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
    const int MaxStreamHitsPerFile = 1000;   // beyond this a file's stream hits refuse again (not random any more)
    static readonly HashSet<string> MediaExt = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ".mp4", ".mkv", ".mka", ".wav" };
    static bool InRanges(List<long[]> r, long a, long b) {   // [a, b) inside one range; r sorted by start
        int lo = 0, hi = r.Count - 1;
        while (lo <= hi) { int m = (lo + hi) >> 1; if (r[m][0] <= a) lo = m + 1; else hi = m - 1; }
        return hi >= 0 && b <= r[hi][1];
    }
    // Byte ranges [start, end) of the stream payload, or null when the file is not a media file this understands (then
    // nothing is relaxed). MP4: mdat contents, only when every track is video or audio (hdlr vide/soun). Matroska: the
    // frame data of SimpleBlock/Block elements of video (1) and audio (2) tracks. WAV: the data chunk.
    public static List<long[]> MediaPayload(string full) {
        if (!MediaExt.Contains(Path.GetExtension(full))) return null;
        try {
            using (var fs = new FileStream(full, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 16)) {
                string ext = Path.GetExtension(full).ToLowerInvariant();
                var r = ext == ".mp4" ? Mp4Payload(fs) : ext == ".wav" ? WavPayload(fs) : MkvPayload(fs);
                if (r != null) r.Sort((x, y) => x[0].CompareTo(y[0]));
                return r;
            }
        } catch (Exception) { return null; }
    }
    static byte[] ReadAt(FileStream fs, long off, int n) {
        var b = new byte[n]; fs.Position = off; int got = 0;
        while (got < n) { int k = fs.Read(b, got, n - got); if (k <= 0) return null; got += k; }
        return b;
    }
    static uint BE32(byte[] b, int i) { return (uint)(b[i] << 24 | b[i + 1] << 16 | b[i + 2] << 8 | b[i + 3]); }
    static List<long[]> Mp4Payload(FileStream fs) {
        long len = fs.Length, pos = 0; var mdat = new List<long[]>(); byte[] moov = null;
        while (pos + 8 <= len) {
            byte[] h = ReadAt(fs, pos, 8); if (h == null) return null;
            long size = BE32(h, 0); string type = Encoding.ASCII.GetString(h, 4, 4); int hl = 8;
            if (size == 1) { byte[] x = ReadAt(fs, pos + 8, 8); if (x == null) return null; size = (long)((ulong)BE32(x, 0) << 32 | BE32(x, 4)); hl = 16; }
            else if (size == 0) size = len - pos;
            if (size < hl || pos + size > len) return null;
            if (type == "mdat") mdat.Add(new long[] { pos + hl, pos + size });
            else if (type == "moov") { if (size > (256L << 20) || moov != null) return null; moov = ReadAt(fs, pos + hl, (int)(size - hl)); }
            pos += size;
        }
        if (moov == null || mdat.Count == 0) return null;
        var handlers = new List<string>(); Mp4Handlers(moov, 0, moov.Length, handlers);
        if (handlers.Count == 0) return null;
        foreach (string t in handlers) if (t != "vide" && t != "soun") return null;
        return mdat;
    }
    static void Mp4Handlers(byte[] b, int start, int end, List<string> outp) {   // moov > trak > mdia > hdlr
        int p = start;
        while (p + 8 <= end) {
            long size = BE32(b, p); string type = Encoding.ASCII.GetString(b, p + 4, 4);
            if (size < 8 || p + size > end) { outp.Add("?"); return; }
            if (type == "trak" || type == "mdia") Mp4Handlers(b, p + 8, p + (int)size, outp);
            else if (type == "hdlr" && size >= 20) outp.Add(Encoding.ASCII.GetString(b, p + 16, 4));
            p += (int)size;
        }
    }
    static List<long[]> WavPayload(FileStream fs) {
        byte[] h = ReadAt(fs, 0, 12);
        if (h == null || Encoding.ASCII.GetString(h, 0, 4) != "RIFF" || Encoding.ASCII.GetString(h, 8, 4) != "WAVE") return null;
        long pos = 12, len = fs.Length; var r = new List<long[]>();
        while (pos + 8 <= len) {
            byte[] c = ReadAt(fs, pos, 8); if (c == null) return null;
            long size = BitConverter.ToUInt32(c, 4); string id = Encoding.ASCII.GetString(c, 0, 4);
            long end = Math.Min(len, pos + 8 + size);
            if (id == "data") r.Add(new long[] { pos + 8, end });
            pos = end + (size & 1);
        }
        return r.Count > 0 ? r : null;
    }
    // EBML variable-length integers: an element id keeps its marker bit, a size drops it; all value bits set = unknown size
    static long Vint(FileStream fs, long pos, bool keepMarker, out int n, out bool unknown) {
        n = 0; unknown = false; fs.Position = pos; int b0 = fs.ReadByte(); if (b0 <= 0) return -1;
        int mask = 0x80; n = 1; while ((b0 & mask) == 0) { mask >>= 1; n++; }
        if (n > 8) return -1;
        long v = keepMarker ? b0 : (b0 & (mask - 1)); bool ones = (b0 & (mask - 1)) == mask - 1;
        for (int i = 1; i < n; i++) { int b = fs.ReadByte(); if (b < 0) return -1; v = v * 256 + b; if (b != 0xFF) ones = false; }
        unknown = !keepMarker && ones; return v;
    }
    static readonly HashSet<long> ClusterChildren = new HashSet<long> { 0xE7, 0xA3, 0xA0, 0xA7, 0xAB, 0x5854, 0xBF, 0xEC };
    static List<long[]> MkvPayload(FileStream fs) {
        long len = fs.Length; int n, n2; bool unk;
        long id = Vint(fs, 0, true, out n, out unk); if (id != 0x1A45DFA3) return null;
        long sz = Vint(fs, n, false, out n2, out unk); if (sz < 0 || unk) return null;
        long pos = n + n2 + sz;
        id = Vint(fs, pos, true, out n, out unk); if (id != 0x18538067) return null;
        sz = Vint(fs, pos + n, false, out n2, out unk); if (sz < 0) return null;
        long segStart = pos + n + n2, segEnd = unk ? len : Math.Min(len, segStart + sz);
        var types = new Dictionary<long, long>(); var blocks = new List<long[]>();   // {start, end, track}
        Ebml(fs, segStart, segEnd, 0, types, blocks);
        var r = new List<long[]>();
        foreach (var b in blocks) { long t; if (types.TryGetValue(b[2], out t) && (t == 1 || t == 2)) r.Add(new long[] { b[0], b[1] }); }
        return r.Count > 0 ? r : null;
    }
    // level 0 = Segment children, 1 = Tracks / Cluster children, 2 = TrackEntry / BlockGroup children
    static long Ebml(FileStream fs, long pos, long end, int level, Dictionary<long, long> types, List<long[]> blocks,
                     long parent = 0, long[] entry = null) {
        while (pos < end) {
            int n, n2; bool unk;
            long id = Vint(fs, pos, true, out n, out unk); if (id < 0) return pos;
            if (parent == 0x1F43B675 && !ClusterChildren.Contains(id)) return pos;   // an unknown-size Cluster ends here
            long sz = Vint(fs, pos + n, false, out n2, out unk); if (sz < 0) return pos;
            long ds = pos + n + n2, de = unk ? end : Math.Min(end, ds + sz);
            if (id == 0x1654AE6B || id == 0x1F43B675 || id == 0xA0) {        // Tracks, Cluster, BlockGroup
                long stop = Ebml(fs, ds, de, level + 1, types, blocks, id);
                if (unk) de = stop;
            } else if (id == 0xAE) {                                         // TrackEntry
                var e = new long[] { -1, -1 }; Ebml(fs, ds, de, level + 1, types, blocks, id, e);
                if (e[0] >= 0) types[e[0]] = e[1];
            } else if (entry != null && (id == 0xD7 || id == 0x83) && sz <= 8) {   // TrackNumber, TrackType
                fs.Position = ds; long v = 0; for (int i = 0; i < sz; i++) v = v * 256 + fs.ReadByte();
                entry[id == 0xD7 ? 0 : 1] = v;
            } else if (id == 0xA3 || id == 0xA1) {                           // SimpleBlock, Block
                int tn; bool tu; long track = Vint(fs, ds, false, out tn, out tu);
                if (track >= 0 && ds + tn + 3 <= de) blocks.Add(new long[] { ds + tn + 3, de, track });
            }
            if (unk && !(id == 0x1F43B675)) return de;   // unknown size elsewhere: give up on the rest
            pos = de;
        }
        return pos;
    }

    // Rewrites every text file with the rules (regex -> literal text), in order, keeping each file's encoding. Scopes:
    // "all"; "json" (.json/.jsonl only: rules for JSON-escaped text); "lines" (other text files except git.log).
    // Returns the files changed with the number of replacements per rule.
    // hints[i]: a literal the rule cannot match without (case-insensitive); the regex is skipped when it is absent.
    // <base64 omitted, N bytes, sha256 first 16 hex of the decoded bytes (or of the text when it does not decode)>
    static string Base64Placeholder(string b64) {
        byte[] data;
        try { data = Convert.FromBase64String(b64.Length % 4 == 0 ? b64 : b64.Substring(0, b64.Length - b64.Length % 4)); }
        catch (FormatException) { data = Encoding.ASCII.GetBytes(b64); }
        string h;
        using (var sha = System.Security.Cryptography.SHA256.Create()) { h = BitConverter.ToString(sha.ComputeHash(data)).Replace("-", "").ToLowerInvariant(); }
        return "<base64 omitted, " + data.Length + " bytes, sha256 " + h.Substring(0, 16) + ">";
    }

    public static List<ScrubResult> ScrubAll(string root, IList<string> rels, string[] patterns, string[] reps, string[] scopes, string[] hints) {
        root = Path.GetFullPath(root).TrimEnd('\\') + "\\";
        var rx = new Regex[patterns.Length];
        for (int i = 0; i < patterns.Length; i++) rx[i] = new Regex(patterns[i], RegexOptions.Compiled);
        var res = new List<ScrubResult>();
        Parallel.ForEach(rels, new ParallelOptions { MaxDegreeOfParallelism = 6 }, rel => {
            string full = root + rel.Replace('/', '\\');
            var fi = new FileInfo(full);
            if (fi.Length == 0 || fi.Length >= (256L << 20) || !IsText(full)) return;
            string ext = Path.GetExtension(full).ToLowerInvariant(); bool json = ext == ".json" || ext == ".jsonl";
            byte[] d = File.ReadAllBytes(full);
            Encoding enc = (d.Length >= 2 && d[0] == 0xFF && d[1] == 0xFE) ? Encoding.Unicode
                         : (d.Length >= 2 && d[0] == 0xFE && d[1] == 0xFF) ? Encoding.BigEndianUnicode : Latin1;  // Latin-1 round-trips UTF-8 bytes
            string s = enc.GetString(d); int[] counts = new int[patterns.Length]; bool any = false;
            for (int i = 0; i < patterns.Length; i++) {
                if (scopes[i] == "json" && !json) continue;
                if (scopes[i] == "lines" && (json || rel == "git.log")) continue;
                if (scopes[i] == "logs" && !(json || rel == "git.log" || rel.StartsWith("History/"))) continue;
                if (!string.IsNullOrEmpty(hints[i]) && s.IndexOf(hints[i], StringComparison.OrdinalIgnoreCase) < 0) continue;
                int c = 0; string rep = reps[i];
                // a replacement with group references (${1}) is expanded; others are literal text
                s = rx[i].Replace(s, m => { c++; return rep == "<<BASE64>>" ? Base64Placeholder(m.Value) : (rep.IndexOf('$') >= 0 ? m.Result(rep) : rep); });
                counts[i] = c; if (c > 0) any = true;
            }
            if (any) { File.WriteAllBytes(full, enc.GetBytes(s)); var r = new ScrubResult(); r.Path = rel; r.Counts = counts; lock (res) res.Add(r); }
        });
        res.Sort((a, b) => string.CompareOrdinal(a.Path, b.Path));
        return res;
    }

    // ---- git.log ----
    static string ReadLineLF(Stream s, StringBuilder sb) {
        sb.Length = 0; int b; bool any = false;
        while ((b = s.ReadByte()) >= 0) { any = true; if (b == '\n') return sb.ToString(); sb.Append((char)b); }
        return any ? sb.ToString() : null;   // Latin-1: one char per byte, CR kept
    }

    public static int TrailersRemoved = 0;
    public static int WriteGitLog(string repo, string commit, string outFile, string header, Dictionary<string, string> authors, List<string> problems) {
        string fmt = "commit %H%nParents: %P%nAuthor: %an <%ae>%nAuthorDate: %aI%nCommitter: %cn <%ce>%nCommitDate: %cI%n%n%w(0,4,4)%B";
        string args = "-C \"" + repo + "\" -c core.quotepath=off -c diff.renameLimit=20000 log --reverse --topo-order --no-color --no-textconv --no-ext-diff --full-index -M --diff-merges=first-parent -p \"--format=" + fmt + "\" " + commit;
        var psi = new ProcessStartInfo(Git, args);
        psi.UseShellExecute = false; psi.RedirectStandardOutput = true; psi.RedirectStandardError = true; psi.CreateNoWindow = true;
        var p = Process.Start(psi); var err = new StringBuilder();
        p.ErrorDataReceived += (s, e) => { if (e.Data != null) lock (err) err.AppendLine(e.Data); };
        p.BeginErrorReadLine();
        var r = new BufferedStream(p.StandardOutput.BaseStream, 1 << 20);
        int commits = 0;
        using (var gb = new GitBatch(Git, repo))
        using (var w = new StreamWriter(outFile, false, Latin1, 1 << 20)) {
            w.NewLine = "\n"; w.Write(header);
            var section = new List<string>(); bool inHeader = false, inMessage = false; var sb = new StringBuilder(); string line;
            var trailer = new Regex(@"^\s*(Co-Authored-By:\s*Claude\b|.*Generated with \[?Claude Code\b)", RegexOptions.IgnoreCase);
            while ((line = ReadLineLF(r, sb)) != null) {
                if (line.Length == 47 && line.StartsWith("commit ")) { Flush(section, w, gb); commits++; inHeader = true; inMessage = false; w.WriteLine(line); continue; }
                if (inHeader) {
                    if (line.Length == 0) { inHeader = false; inMessage = true; }
                    else if (line.StartsWith("Author: ") || line.StartsWith("Committer: ")) {
                        int sp = line.IndexOf(": "); string who = line.Substring(sp + 2);
                        int lt = who.LastIndexOf(" <"); if (lt > 0) who = who.Substring(0, lt);   // identities by name
                        string anon; if (!authors.TryGetValue(who, out anon)) { anon = "dev_" + (authors.Count + 1).ToString("00"); authors[who] = anon; }
                        line = line.Substring(0, sp + 2) + anon;
                    }
                    w.WriteLine(line); continue;
                }
                if (inMessage && trailer.IsMatch(line)) { TrailersRemoved++; continue; }   // agent trailer lines of commit messages
                if (line.StartsWith("diff --git ")) { inMessage = false; Flush(section, w, gb); section.Add(line); continue; }
                if (section.Count > 0) section.Add(line); else w.WriteLine(line);
            }
            Flush(section, w, gb);
        }
        p.WaitForExit();
        if (p.ExitCode != 0) throw new Exception("git log failed: " + err);
        return commits;
    }

    static string SectionPath(List<string> sec) {
        foreach (var l in sec) if (l.StartsWith("rename to ")) return l.Substring(10).TrimEnd('\r');
        foreach (var l in sec) if (l.StartsWith("+++ b/")) return l.Substring(6).TrimEnd('\r', '\t');
        foreach (var l in sec) if (l.StartsWith("--- a/")) return l.Substring(6).TrimEnd('\r', '\t');
        string s = sec[0].Substring(11);
        if ((s.Length - 1) % 2 == 0) { int h = (s.Length - 1) / 2; string a = s.Substring(0, h), b = s.Substring(h + 1); if (a.Length > 2 && a.Substring(2) == b.Substring(2)) return b.Substring(2); }
        return s;
    }

    static string Desc(string sha, long bytes) { return sha == null ? "(none)" : "sha256 " + sha + " (" + bytes + " bytes)"; }

    static string BlobDesc(GitBatch gb, string oid) {
        if (oid == null || oid.Trim('0').Length == 0) return "(none)";
        string t; byte[] d = gb.Read(oid, out t); if (d == null) return "(blob " + oid + " missing)";
        return Desc(Sha(d), d.Length);
    }

    static void Flush(List<string> sec, StreamWriter w, GitBatch gb) {
        if (sec.Count == 0) return;
        string path = SectionPath(sec);
        bool lfs = false, allPtr = true, inHunk = false; int hunks = 0;
        string oldOid = null, newOid = null; long oldSize = -1, newSize = -1;
        foreach (var l in sec) {
            if (l.StartsWith("@@")) { inHunk = true; hunks++; continue; }
            if (!inHunk || l.Length == 0) continue;
            char c = l[0]; string body = l.Substring(1).TrimEnd('\r');
            if (c == '\\') continue;
            if (c != ' ' && c != '+' && c != '-') { allPtr = false; continue; }
            if (body.StartsWith("version https://git-lfs.github.com/spec/")) lfs = true;
            else if (body.StartsWith("oid sha256:")) { string o = body.Substring(11); if (c != '+') oldOid = o; if (c != '-') newOid = o; }
            else if (body.StartsWith("size ")) { long z; long.TryParse(body.Substring(5), out z); if (c != '+') oldSize = z; if (c != '-') newSize = z; }
            else allPtr = false;
        }
        if (lfs && allPtr && hunks > 0) {
            foreach (var l in sec) {
                if (l.StartsWith("index ") || l.StartsWith("--- ") || l.StartsWith("+++ ") || l.StartsWith("@@")) break;
                w.WriteLine(l);
            }
            w.WriteLine("Git LFS file " + path + ": " + Desc(oldOid, oldSize) + " -> " + Desc(newOid, newSize));
            for (int i = sec.Count - 1; i >= 0 && sec[i].Length == 0; i--) w.WriteLine("");
        } else {
            string a = null, b = null;
            foreach (var l in sec) { var m = Regex.Match(l, "^index ([0-9a-f]+)\\.\\.([0-9a-f]+)"); if (m.Success) { a = m.Groups[1].Value; b = m.Groups[2].Value; break; } }
            foreach (var l in sec) {
                if (l.StartsWith("Binary files ") && l.TrimEnd('\r').EndsWith(" differ"))
                    w.WriteLine("Binary file " + path + ": " + BlobDesc(gb, a) + " -> " + BlobDesc(gb, b));
                else w.WriteLine(l);
            }
        }
        sec.Clear();
    }

    // ---- zip ----
    static readonly HashSet<string> Stored = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {
        ".mkv", ".mka", ".mp4", ".mov", ".pak", ".ucas", ".utoc", ".zip", ".7z", ".gz", ".png", ".jpg", ".jpeg", ".flac", ".ogg", ".mp3" };
    public static int Zip(string srcDir, string zipPath, string baseName, string level) {
        CompressionLevel cl = level == "Optimal" ? CompressionLevel.Optimal : level == "NoCompression" ? CompressionLevel.NoCompression : CompressionLevel.Fastest;
        string root = Path.GetFullPath(srcDir).TrimEnd('\\') + "\\";
        var files = new List<string>(Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories));
        files.Sort(StringComparer.Ordinal);
        using (var fs = new FileStream(zipPath, FileMode.CreateNew, FileAccess.ReadWrite))
        using (var za = new ZipArchive(fs, ZipArchiveMode.Create)) {
            foreach (string full in files) {
                string rel = full.Substring(root.Length).Replace('\\', '/');
                var e = za.CreateEntry(baseName + "/" + rel, Stored.Contains(Path.GetExtension(full)) ? CompressionLevel.NoCompression : cl);
                e.LastWriteTime = File.GetLastWriteTime(full);
                using (var es = e.Open()) using (var src = new FileStream(full, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20)) src.CopyTo(es, 1 << 20);
            }
        }
        using (var za = ZipFile.OpenRead(zipPath)) return za.Entries.Count;
    }
}
}
'@
if (-not ('GameDeliverable.Tools' -as [type])) {
    $refs = @('System', 'System.Core',
        [System.Reflection.Assembly]::Load('System.IO.Compression, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089').Location,
        [System.Reflection.Assembly]::Load('System.IO.Compression.FileSystem, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089').Location)
    Add-Type -TypeDefinition $cs -ReferencedAssemblies $refs -Language CSharp
}
[GameDeliverable.Tools]::Git = (Get-Command git -CommandType Application | Select-Object -First 1).Source

# ---------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------
function Get-Prop($Obj, [string]$Name) {
    if ($null -eq $Obj -or -not ($Obj -is [psobject])) { return $null }
    $p = $Obj.PSObject.Properties[$Name]; if ($p) { return $p.Value } else { return $null }
}
function Write-Utf8([string]$Path, [string]$Text) { [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom) }
function Format-Bytes([double]$b) {
    if ($b -ge 1GB) { return '{0:N2} GB' -f ($b / 1GB) }; if ($b -ge 1MB) { return '{0:N1} MB' -f ($b / 1MB) }
    if ($b -ge 1KB) { return '{0:N0} KB' -f ($b / 1KB) }; return "$b B"
}
function Get-MdSection([string]$Text, [string]$HeadingRegex) {
    # The section under the first heading (any level) matching the regex, up to the next heading of the same or higher level.
    if (-not $Text) { return $null }
    $lines = $Text -split "`r?`n"; $out = New-Object System.Collections.ArrayList; $level = 0
    foreach ($l in $lines) {
        if ($level -eq 0) { if ($l -match '^(#+)\s+(.*)$') { $lv = $Matches[1].Length; if ($Matches[2] -match $HeadingRegex) { $level = $lv } }; continue }
        if ($l -match '^(#+)\s' -and $Matches[1].Length -le $level) { break }
        [void]$out.Add($l)
    }
    if ($level -eq 0) { return $null }
    return (($out -join "`n").Trim())
}
function Shift-Headings([string]$Text, [int]$By) {
    $pad = '#' * $By
    return (($Text -split "`r?`n" | ForEach-Object { if ($_ -match '^#+\s') { $pad + $_ } else { $_ } }) -join "`n")
}
function Expand-Braces([string]$s) {
    if ($s -match '^(.*?)\{([^{}]*)\}(.*)$') { $pre = $Matches[1]; $alts = $Matches[2] -split ','; $post = $Matches[3]
        return @($alts | ForEach-Object { Expand-Braces ($pre + $_.Trim() + $post) }) }
    return @($s)
}
function ConvertTo-ProjectPath([string]$p) {
    $p = $p.Trim().Replace('\', '/')
    if ($p -match '^/Game/(.*)$') { return 'Content/' + $Matches[1] }
    if ($p -match '^/(Engine|Script)/') { return $null }
    if ($p -match '^[A-Za-z]:/' -or $p -match '^https?:') { return $null }
    return $p.TrimStart('/')
}
$script:ManifestStore = New-Object System.Collections.ArrayList
function Find-ManifestStore($Node, [string]$Where) {
    # Every object in assets.manifest.json whose licence is a store licence (Fab Standard / Marketplace) or whose
    # origin/source is Fab contributes its folder/file/path fields as store content.
    if ($Node -is [array]) { foreach ($x in $Node) { Find-ManifestStore $x $Where }; return }
    if (-not ($Node -is [System.Management.Automation.PSCustomObject])) { return }
    $lic = $null; foreach ($k in 'licence', 'license') { $v = Get-Prop $Node $k; if ($v) { $lic = if ($v -is [string]) { $v } else { ($v | ConvertTo-Json -Compress -Depth 4) } } }
    $origin = $null; foreach ($k in 'origin', 'source') { $v = Get-Prop $Node $k; if ($v -is [string]) { $origin = $v } }
    if (($lic -and $lic -match '(?i)fab standard|marketplace') -or ($origin -and $origin -match '(?i)^fab\b')) {
        foreach ($k in 'folder', 'copied_to', 'file', 'path', 'ue_assets', 'ue_path', 'installed_to') {
            foreach ($v in @(Get-Prop $Node $k)) {
                if (-not ($v -is [string])) { continue }
                foreach ($exp in (Expand-Braces $v)) { foreach ($e in ($exp -split ',\s+')) {
                    $pp = ConvertTo-ProjectPath $e
                    if ($pp) { [void]$script:ManifestStore.Add([pscustomobject]@{ path = $pp; why = "assets.manifest.json: $(if ($lic) { $lic } else { "origin $origin" })" }) }
                } }
            }
        }
    }
    foreach ($p in $Node.PSObject.Properties) { if ($p.Value -is [System.Management.Automation.PSCustomObject] -or $p.Value -is [array]) { Find-ManifestStore $p.Value $Where } }
}

# ---- deliverable scrub: applied to the package copy only, in this order; then everything is rescanned ----------------
# Scopes: all | json (.json/.jsonl, JSON-escaped forms) | lines (other text files except git.log, whose commit-message
# trailers WriteGitLog drops). Rule ids are what scrub-report.json counts; descriptions never quote the original values.
$UserName = if ($env:USERNAME) { $env:USERNAME } else { [Environment]::UserName }
if (-not $UserName) { throw 'cannot tell the Windows user name (USERNAME unset): the scrub needs it' }
# start of a word, also right after a JSON escape such as \n (whose letter would otherwise hide the boundary)
$WordStart = '(?:(?<=\\[nrtfb])|(?<=\\u[0-9a-fA-F]{4})|(?<![A-Za-z0-9_]))'
$UserRx = "$WordStart$([regex]::Escape($UserName))(?![A-Za-z0-9_])"
$MachineName = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { [Environment]::MachineName }
# enforcement: the account name as any substring (only the allowlisted exact tokens pass)
$UserAnyRx = [regex]::Escape($UserName)
$EmailRx = '(?:(?<=\\u[0-9a-fA-F]{4})|(?<=\\[nrtfb"/])|(?<![A-Za-z0-9._%+\\-]))(?!(?:git@(?:github|gitlab|bitbucket)\.(?:com|org)|noreply@github\.com)\b)' +
    '[A-Za-z0-9._%+-]+@(?!(?:[A-Za-z0-9-]+\.)*(?:example\.(?:com|org|net)|invalid|test|localhost)\b)(?:[A-Za-z0-9-]+\.)+' +
    '(?!(?:png|jpe?g|tga|gif|svg|webp|exr|hdr|bmp|dds|uasset|umap|wav|ogg|mp3|flac|fbx|glb|gltf|obj|json|jsonl|txt|md|ini|py|ps1|sh|cpp|h|cs|bin|zip)\b)[A-Za-z]{2,}\b'
$RuleText = [ordered]@{
    'agent-trailer'  = 'agent co-author and generated-with trailer lines removed'
    'agent-identity' = 'agent identity (name + no-reply address) replaced by a neutral dev identity'
    'banned-name'    = 'studio and tooling names replaced (same default rules as ue-pipeline\scrub-history.ps1)'
    'git-identity'   = 'git author/committer names and handles replaced by dev_NN'
    'username'       = 'account user name, including inside user paths, replaced by dev'
    'email'          = 'e-mail addresses (other than example/placeholder ones) replaced by <redacted-email>'
    'agent-mention'  = 'remaining agent/provider mentions neutralised (agent, provider)'
    'base64-payload' = 'base64 runs of 256+ characters in shipped logs (screenshots, binary payloads in tool responses) replaced by <base64 omitted, N bytes, sha256 ...>'
    'session-path'   = 'the build machine''s per-session folders (temp scratch/task folders, shared notes folder) and session ids replaced by neutral names (session, session/notes)'
}
$RulesHead = @(
    # first: payloads go before any word rule could touch them (a random user-name match inside base64 included)
    @{ id = 'base64-payload'; scope = 'logs'; match = '(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{256,}={0,2}(?![A-Za-z0-9+/=])'; replace = '<<BASE64>>' },
    @{ id = 'agent-trailer'; scope = 'lines'; match = '(?im)^[ \t]*Co-Authored-By:[ \t]*Claude[^\r\n]*\r?\n?'; replace = '' },
    @{ id = 'agent-trailer'; scope = 'lines'; match = '(?im)^[^\r\n]*Generated with \[?Claude Code\b[^\r\n]*\r?\n?'; replace = '' },
    @{ id = 'agent-trailer'; scope = 'json'; match = '(?i)(?:\\r)?(?:\\n)*Co-Authored-By:[ \t]*Claude(?:[^"\\]|\\u003[cCeE])*'; replace = '' },
    # anchored at a \n escape run or the string's opening quote (an unanchored lazy prefix is quadratic on long strings)
    @{ id = 'agent-trailer'; scope = 'json'; match = '(?i)(?:(?:\\r)?(?:\\n)+|(?<="))(?:[^"\\]|\\u[0-9a-fA-F]{4})*?Generated with \[?Claude Code\b(?:[^"\\]|\\u003[cCeE])*'; replace = '' },
    @{ id = 'agent-identity'; scope = 'all'; match = 'Claude \(agent\)'; replace = 'dev' },
    @{ id = 'agent-identity'; scope = 'all'; match = '(?i)\bClaude(?: (?:Opus|Sonnet|Haiku|Fable)(?: [0-9.]+)?)?(?=[ ]*(?:<|\\u003[cC])noreply@anthropic\.com)'; replace = 'dev' },
    @{ id = 'agent-identity'; scope = 'all'; match = '(?i)noreply@anthropic\.com'; replace = 'dev@example.invalid' },
    @{ id = 'banned-name'; scope = 'all'; match = '(?i)superposition\.(?=[a-z0-9_-]+/v?\d)'; replace = '' },
    @{ id = 'banned-name'; scope = 'all'; match = 'SUPERPOSITION'; replace = 'STUDIO' }, @{ id = 'banned-name'; scope = 'all'; match = 'Superposition'; replace = 'Studio' },
    @{ id = 'banned-name'; scope = 'all'; match = '(?i)superposition'; replace = 'studio' },
    @{ id = 'banned-name'; scope = 'all'; match = 'GAME-FACTORY'; replace = 'STUDIO-TOOLS' }, @{ id = 'banned-name'; scope = 'all'; match = 'Game-Factory'; replace = 'Studio-Tools' },
    @{ id = 'banned-name'; scope = 'all'; match = '(?i)game_factory'; replace = 'studio_tools' }, @{ id = 'banned-name'; scope = 'all'; match = 'GameFactory'; replace = 'StudioTools' },
    @{ id = 'banned-name'; scope = 'all'; match = '(?i)gamefactory'; replace = 'studiotools' }, @{ id = 'banned-name'; scope = 'all'; match = '(?i)game-factory'; replace = 'studio-tools' }
)
# the session ids of this game's recording wherever they stand alone (other uuids, e.g. Fab listing ids, stay)
$SessionIdRule = @()
$sessAct = Join-Path $WorkRoot ".recording\$Game\actions.jsonl"
if (Test-Path -LiteralPath $sessAct) {
    $sessIds = @(Select-String -LiteralPath $sessAct -Pattern '"session_id":\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"' -AllMatches |
        ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value.ToLower() } | Sort-Object -Unique)
    if ($sessIds.Count) {
        $SessionIdRule = @(@{ id = 'session-path'; scope = 'all'; replace = 'session'
            match = '(?i)\b(?:' + (($sessIds | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')\b' })
    }
}
# (git-identity rules are added once git.log has numbered the identities)
$RulesTail = @(
    # the build machine's per-session folders and ids (same names as tools/ue-replay SESSION_PATH_RULES): before the
    # user-name rules, which only rename the profile part of these paths. Separators: / \ or JSON-escaped \\.
    @{ id = 'session-path'; scope = 'all'; match = '(?i)(AppData[\\/]+Local[\\/]+Temp([\\/]+))[^\\/\s''"]+[\\/]+[^\\/\s''"]+[\\/]+[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:([\\/]+)scratc[h]pad(?![\w-]))?'; replace = '${1}session${3}SCRATCH_DIR' },
    # a session folder cut short (recorded commands are kept to 2000 characters): Temp/<tool>/<project>/<uuid start> at a string end
    @{ id = 'session-path'; scope = 'all'; match = '(?i)(AppData[\\/]+Local[\\/]+Temp[\\/]+)[^\\/\s''"]+[\\/]+[^\\/\s''"]+[\\/]+[0-9a-f]{8}(?:-[0-9a-f]{0,12}){0,4}(?=\\?"|''|$)'; replace = '${1}session' },
    @{ id = 'session-path'; scope = 'all'; match = '(?<=session[\\/]+)SCRATCH_DIR'; replace = 'scratch' },
    @{ id = 'session-path'; scope = 'all'; match = 'SCRATCH_DIR'; replace = '' },
    @{ id = 'session-path'; scope = 'all'; match = '(?i)(AppData([\\/]+)Roaming\2)[^\\/\s''"]+\2side-sessio[n]-notes\2local_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'; replace = '${1}session${2}notes' },
    @{ id = 'session-path'; scope = 'all'; match = '(?i)\blocal[_][0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'; replace = 'session' },
    @{ id = 'session-path'; scope = 'all'; match = '(?i)side-sessio[n]-notes'; replace = 'session-notes' },
    # repair of 8671b2a's output (its replacements were written literally, e.g. ${1}session${2}notes): rescrubbed zips
    @{ id = 'session-path'; scope = 'all'; match = '\$\{1\}session\$\{2\}notes(?=(\\\\|[\\/]))'; replace = 'AppData${1}Roaming${1}session${1}notes' },
    @{ id = 'session-path'; scope = 'all'; match = '\$\{1\}session\$\{3\}(?=(\\\\|[\\/]))'; replace = 'AppData${1}Local${1}Temp${1}session' },
    @{ id = 'session-path'; scope = 'all'; match = '(?i)scratc[h]pad'; replace = 'scratch' },
    @{ id = 'username'; scope = 'all'; match = "(?i)$([regex]::Escape($MachineName))"; replace = 'dev-pc' },   # the machine name contains it
    @{ id = 'username'; scope = 'all'; match = "(?i)(?<=users[\\/:0-9]{0,6})$([regex]::Escape($UserName))"; replace = 'dev' },   # paths that lost their separators (C:UsersNameWork...) or use a regex backreference (Users\1Name\1Work)
    @{ id = 'username'; scope = 'all'; match = "(?i)$UserRx"; replace = 'dev' },
    @{ id = 'email'; scope = 'all'; match = $EmailRx; replace = '<redacted-email>' },
    @{ id = 'agent-mention'; scope = 'all'; match = '(?i)\bclaude[-_ ]code\b'; replace = 'agent-tool' },
    @{ id = 'agent-mention'; scope = 'all'; match = '(?i)\bclaude[-_ ]?(?:opus|sonnet|haiku|fable|instant)(?:[-_ ]?[0-9]+(?:[._-][0-9]+)*)?[\w.-]*'; replace = 'agent-model' },
    @{ id = 'agent-mention'; scope = 'all'; match = '(?i)\bopus[-_ ]?[0-9]+(?:\.[0-9]+)*\b'; replace = 'agent-model' },
    # the word opus on its own in prose, any case (quoted policy text "Agent/Provider/Opus", "agent or opus or ..."; also
    # "the Opus audio codec", which the rescan would block too); codec identifiers (libopus, opus_*, AudioFormatOPUS) stay
    @{ id = 'agent-mention'; scope = 'all'; match = '(?:(?<=\\u00[0-9a-fA-F]{2})|(?<![\w.-]))(?<!audio/)OPUS(?![\w.-]|/\d)'; replace = 'MODEL' },
    @{ id = 'agent-mention'; scope = 'all'; match = '(?:(?<=\\u00[0-9a-fA-F]{2})|(?<![\w.-]))(?<!audio/)Opus(?![\w.-]|/\d)'; replace = 'Model' },
    @{ id = 'agent-mention'; scope = 'all'; match = '(?i)(?:(?<=\\u00[0-9a-fA-F]{2})|(?<![\w.-]))(?<!audio/)opus(?![\w.-]|/\d)'; replace = 'model' },
    @{ id = 'agent-mention'; scope = 'all'; match = 'CLAUDE'; replace = 'AGENT' }, @{ id = 'agent-mention'; scope = 'all'; match = 'Claude'; replace = 'Agent' },
    @{ id = 'agent-mention'; scope = 'all'; match = '(?i)claude'; replace = 'agent' },
    @{ id = 'agent-mention'; scope = 'all'; match = 'ANTHROPIC'; replace = 'PROVIDER' }, @{ id = 'agent-mention'; scope = 'all'; match = 'Anthropic'; replace = 'Provider' },
    @{ id = 'agent-mention'; scope = 'all'; match = '(?i)anthropic'; replace = 'provider' }
)
# the recording's session ids right after the session-path rules (which need the uuid inside a path to recognise it)
$RulesTail = @($RulesTail | Where-Object { $_.id -eq 'session-path' }) + @($SessionIdRule) + @($RulesTail | Where-Object { $_.id -ne 'session-path' })
$BannedPattern = 'superposition|game[-_]?factory'
# Binary needles (ASCII + UTF-16LE, case-insensitive). The agent/provider names block like the two names (user rule);
# the account name in binaries is reported (and blocks inside Build/, checked separately).
$BinNeedles = @('superposition', 'game-factory', 'game_factory', 'gamefactory', $UserName, 'claude', 'anthropic', 'opus')
$BinRefuse = @($true, $true, $true, $true, $true, $true, $true, $true)   # the account name blocks anywhere too (user rule)
$BinCats = @('banned-name', 'banned-name', 'banned-name', 'banned-name', 'username', 'agent-name', 'agent-name', 'agent-name')
# Exact allowlist, matched against the whole word around a hit (letters, digits, _ . / : -). Only forms seen in the
# packages' engine binaries (Opus audio codec inside the EOS SDK / WebRTC and the engine) and UE's locale ids.
$OpusCodec = @(
    '(?:^|.*/)third_party/opus/.*',                                   # codec source paths
    'libopus(?:file|enc|dec)?(?:\.(?:dll|lib|so|a|h))?', 'opus(?:file|enc|dec)(?:\.(?:dll|lib|so|a|h))?',
    'opus_[a-z][a-z0-9_]*', 'OPUS_[A-Z][A-Z0-9_]*',                   # C API symbols and constants
    '\w*WebRtcOpus_\w+', 'WebRTC-[\w-]*Opus[\w-]*', 'OpusCustom\w*',
    '\w*Audio(?:En|De)coder\w*Opus\w*', '\w*Opus(?:Impl|Config|Decoder|Encoder|AudioInfo|Format|Codec|Header|Head|Tags|File)\w*',
    '[\w./-]*opus[\w.-]*\.(?:c|cc|cpp|h)',                            # codec source file names
    'opus/\d+(?:/\d+)?', 'audio/opus', 'A_OPUS',
    'AudioFormatOpus[\w.]*'                                           # UE's Opus audio format key in SoundWave data (AudioFormatOPUS.LastCompileMethod)
)
$Locale = @('zh[-_]xiang',                                           # UE's Xiang Chinese locale ids
    'wuxiangshan[\w.]*')                                              # 无相山 (WuXiangShan), a place name in game content, and asset names built on it (WuXiangShanBoss1, ...)
# the word may carry other segments joined by : or / (C++ scopes, paths): one segment must be an allowed form
$OpusAllowText = '(?i)^(?:[\w./:-]*?[:/])?(?:' + (($OpusCodec + $Locale) -join '|') + ')(?:[:/.][\w./:-]*)?$'
$OpusAllowBin = $OpusAllowText + '|(?i)^(?:[\w./:-]*?/)?opus$'   # binaries: also the bare codec name, exactly
# Reviewed exceptions (tools\package-reviewed-hits.tsv): single binary hits judged by a person to be data, not text,
# keyed by the file's sha256 + byte offset + word, so another file or another version of it still blocks.
$Reviewed = @{}
$ReviewedPath = Join-Path $PSScriptRoot 'package-reviewed-hits.tsv'
if (Test-Path $ReviewedPath) { foreach ($r in (Import-Csv $ReviewedPath -Delimiter "`t")) { $Reviewed["$($r.sha256)`t$($r.offset)"] = $r.word } }
function Set-ReviewedHits($HitList, [string]$Root) {
    $cache = @{}
    foreach ($h in $HitList) {
        if ($h.Kind -notlike 'binary-*' -or $h.Kind -like 'binary-info*') { continue }
        $full = Join-Path $Root $h.Path.Replace('/', '\')
        if (-not $cache.ContainsKey($full)) { $cache[$full] = [GameDeliverable.Tools]::HashFile($full) }
        $k = "$($cache[$full])`t$($h.Where)"
        if ($Reviewed.ContainsKey($k) -and $h.Text -ceq ((($h.Text -split ':', 2)[0]) + ':' + $Reviewed[$k])) { $h.Kind = 'allowed-reviewed' }
    }
}
[GameDeliverable.Tools]::Allow = New-Object System.Text.RegularExpressions.Regex($OpusAllowText)
[GameDeliverable.Tools]::LocaleNeedle = $UserName
[GameDeliverable.Tools]::AllowBin = New-Object System.Text.RegularExpressions.Regex($OpusAllowBin)
# Short terms that random compressed bytes can spell: relaxed inside media stream payloads only (user rule, 2026-10-12).
# Long terms (user name, anthropic, superposition, game-factory) stay blocking everywhere.
foreach ($t in @('claude', 'opus')) { [void][GameDeliverable.Tools]::StreamTerms.Add($t) }
$Banned = New-Object System.Text.RegularExpressions.Regex($BannedPattern, 'IgnoreCase')

# ---------------------------------------------------------------------------------------------------------------------
# resolve inputs
# ---------------------------------------------------------------------------------------------------------------------
$info = Get-GameInfo $Game
$repo = if ($RepoPath) { (Resolve-Path $RepoPath).Path } else { $info.Dir }

# -Rescan <package dir>: check an existing package against the current rules (names, agent/provider names with the
# Opus-codec allowlist, account name, e-mail addresses, git identity names) without changing it.
if ($Rescan) {
    $pkg = (Resolve-Path $Rescan).Path
    $terms = @(Invoke-Git $repo @('log', '--all', '--format=%an%n%cn') | ForEach-Object { "$_".Trim() } | Where-Object { $_ -and $_ -notmatch '(?i)^(claude|agent|dev_\d+)$' } | Sort-Object -Unique)
    $parts = @($BannedPattern, 'claude', 'anthropic', 'opus', $UserAnyRx, $EmailRx) + @($terms | ForEach-Object { "$WordStart$([regex]::Escape($_))(?![A-Za-z0-9])" })
    $rx = New-Object System.Text.RegularExpressions.Regex(($parts -join '|'), 'IgnoreCase')
    $rels = [string[]]@(Get-ChildItem $pkg -Recurse -File | ForEach-Object { $_.FullName.Substring($pkg.Length + 1).Replace('\', '/') })
    $lk = New-Object 'System.Collections.Generic.List[GameDeliverable.Hit]'
    $all = @([GameDeliverable.Tools]::Scan($pkg, $rels, $rx, $null, $lk, 20, [string[]]$BinNeedles, [bool[]]$BinRefuse, [string[]]$BinCats))
    Set-ReviewedHits $all $pkg
    $block = @($all | Where-Object { $_.Kind -notlike 'binary-info*' -and $_.Kind -notlike 'allowed*' })
    $buildUser = @()   # (the account name now blocks anywhere; it is part of $block)
    $byCat = $block | Group-Object { "$(if ($_.Kind -like 'binary-*') { ($_.Text -split ':', 2)[0] } else { $_.Kind }) in $(($_.Path -split '/')[0])" } | Sort-Object Count -Descending
    Write-Host "  blocking by category/area: $(@($byCat | ForEach-Object { "$($_.Count)x $($_.Name) ($(@($_.Group | ForEach-Object Path | Sort-Object -Unique).Count) files)" }) -join '; ')"
    $allowed = @($all | Where-Object { $_.Kind -like 'allowed*' })
    $out = "$pkg.rescan-hits.tsv"
    $t = New-Object System.Text.StringBuilder; [void]$t.Append("path`tkind`tline_or_offset`ttext`n")
    foreach ($h in ($block + $buildUser + $allowed)) { [void]$t.Append("$($h.Path)`t$(if ($buildUser -contains $h) { 'build-username' } else { $h.Kind })`t$($h.Where)`t$($h.Text)`n") }
    Write-Utf8 $out $t.ToString()
    $fail = $block.Count -or $buildUser.Count
    Write-Host "$(if ($fail) { 'FAIL' } else { 'PASS' })  $pkg"
    Write-Host "  blocking: $($block.Count) hit(s) in $(@($block | ForEach-Object Path | Sort-Object -Unique).Count) file(s)$(if ($block) { ': ' + ((@($block | Group-Object { $_.Kind + ' ' + $_.Text.Substring(0, [Math]::Min(40, $_.Text.Length)) } | Sort-Object Count -Descending | Select-Object -First 8 | ForEach-Object { "$($_.Count)x $($_.Name)" })) -join '; ') })"
    Write-Host "  account name in Build/: $($buildUser.Count) hit(s) in $(@($buildUser | ForEach-Object Path | Sort-Object -Unique).Count) file(s)"
    Write-Host "  allowlisted: $($allowed.Count) hit(s), $(@($allowed | Group-Object Text).Count) distinct words, $(@($allowed | Where-Object Kind -like 'allowed-stream*').Count) in media stream payloads (all in the tsv)"
    Write-Host "  all hits: $out"
    exit $(if ($fail) { 2 } else { 0 })
}

# -ScrubDir <dir>: apply the package scrub rules in place to every text file of a folder that is going into a delivery
# (e.g. ReplayScripts/ from the replay session); prints the counts per rule. Git identities are numbered dev_NN by first
# appearance in the repo's history, as in git.log.
if ($ScrubDir) {
    $sd = (Resolve-Path $ScrubDir).Path
    $ids = New-Object System.Collections.ArrayList; $seen = @{}
    foreach ($line in (Invoke-Git $repo @('log', '--all', '--reverse', '--topo-order', '--format=%an%x09%ae%n%cn%x09%ce'))) {
        $parts = "$line" -split "`t"; if ($parts.Count -lt 2) { continue }
        $nm = $parts[0].Trim(); if ($nm -match '(?i)^(claude|agent|dev_\d+)$') { continue }
        if (-not $seen.ContainsKey($nm)) { $seen[$nm] = 'dev_' + ($seen.Count + 1).ToString('00') }
        $dev = $seen[$nm]; [void]$ids.Add(@($nm, $dev))
        foreach ($w in ($nm -split '[^A-Za-z0-9]+')) { if ($w.Length -ge 4 -and $w -notmatch '(?i)^(claude|anthropic|agent|users?|admin|root|dev|noreply|github|unknown)$') { [void]$ids.Add(@($w, $dev)) } }
        $local = ($parts[1].Trim() -split '@')[0]; if ($local -match '\+') { $local = ($local -split '\+')[-1] }
        if ($local.Length -ge 4) { [void]$ids.Add(@($local, $dev)) }
    }
    function Get-IdRx([string]$t) { $e = [regex]::Escape($t); if ($t -match '\d' -and $t.Length -ge 5) { "(?i)$WordStart$e[A-Za-z0-9]*" } else { "(?i)$WordStart$e(?![A-Za-z0-9])" } }
    $rules = @($RulesHead) + @($ids | Sort-Object { - $_[0].Length } | ForEach-Object { @{ id = 'git-identity'; scope = 'all'; match = (Get-IdRx $_[0]); replace = $_[1] } }) + @($RulesTail)
    $rels = [string[]]@(Get-ChildItem $sd -Recurse -File | ForEach-Object { $_.FullName.Substring($sd.Length + 1).Replace('\', '/') })
    $res = [GameDeliverable.Tools]::ScrubAll($sd, $rels, [string[]]@($rules | ForEach-Object { $_.match }), [string[]]@($rules | ForEach-Object { $_.replace }),
        [string[]]@($rules | ForEach-Object { $_.scope }), [string[]]@($rules | ForEach-Object { '' }))
    $tot = @{}; foreach ($r in $res) { for ($i = 0; $i -lt $rules.Count; $i++) { if ($r.Counts[$i]) { $tot[$rules[$i].id] = [int]$tot[$rules[$i].id] + $r.Counts[$i] } } }
    Write-Host "scrubbed $($res.Count) of $($rels.Count) files in $sd$(if ($tot.Count) { ': ' + ((@($tot.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name) $($_.Value)" })) -join ', ') })"
    Write-JsonFile "$sd.scrub.json" ([ordered]@{ dir = $sd; files = $rels.Count; touched = $res.Count; replacements = $tot })
    exit 0
}

if ($Commit -eq 'milestone') {
    $tags = @(Invoke-Git $repo @('tag', '-l', 'milestone/autoplay-*') | ForEach-Object { "$_".Trim() } | Where-Object { $_ -match '^milestone/autoplay-(\d+)$' } |
        Sort-Object { [int]($_ -replace '^milestone/autoplay-', '') } -Descending)
    $Commit = if ($tags.Count) { $tags[0] } else { 'HEAD' }
    Write-Step "commit: $Commit"
}
$sha = @(Invoke-Git $repo @('rev-parse', '--verify', "$Commit^{commit}"))[0].Trim()
$short = $sha.Substring(0, 8)
$releaseTag = $null
if ($Version) {
    $rt = "release/$Version"
    $rts = @(Invoke-Git $repo @('rev-parse', '--verify', '-q', "$rt^{commit}") -AllowFail)
    if ($rts.Count -and "$($rts[0])".Trim() -eq $sha) { $releaseTag = $rt }
}
$commitTime = @(Invoke-Git $repo @('show', '-s', '--format=%cI', $sha))[0].Trim()
$commitSubject = @(Invoke-Git $repo @('show', '-s', '--format=%s', $sha))[0].Trim()
$lineageList = @(Invoke-Git $repo @('rev-list', $sha) | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$lineage = @{}; for ($i = 0; $i -lt $lineageList.Count; $i++) { $lineage[$lineageList[$i]] = $i }   # 0 = the commit itself
$gitDir = @(Invoke-Git $repo @('rev-parse', '--path-format=absolute', '--git-common-dir'))[0].Trim()
$lfsDir = Join-Path $gitDir 'lfs\objects'
if ($WithoutStoreContent) { throw "-WithoutStoreContent is retired: datasets and packages are always built with store content (user decision 2026-10-12: always with store content, no _nostore variant)" }
$variant = if ($WithoutStoreContent) { 'nostore' } else { 'full' }
$name = "${Game}_$short$(if ($WithoutStoreContent) { '_nostore' })"
$gameOut = Join-Path $OutRoot $Game
$final = Join-Path $gameOut $name
$stage = "$final.partial"
$zipPath = "$final.zip"
New-Item -ItemType Directory -Force $gameOut | Out-Null
$problems = New-Object 'System.Collections.Generic.List[string]'
$warnings = New-Object System.Collections.ArrayList
Write-Step "package $Game @ $short ($variant)  repo $repo  ->  $final$(if ($DryRun) { '  (dry run)' })"

# Store packs kept out of git: folders under Content/ that are git-ignored in the game's working tree and not tracked
# at the commit (tower-defense Content/<Pack>/, another game's Content/Fab/). The full variant copies them from the
# working tree, and the build must have been cooked with them: a pipeline build from a clean clone has none.
$matcher = New-Object GameDeliverable.StoreMatcher
$manifestText = [GameDeliverable.Tools]::ReadBlobText($repo, "${sha}:assets.manifest.json")
$assetsManifest = $null
if ($manifestText) {
    $assetsManifest = $manifestText | ConvertFrom-Json
    Find-ManifestStore $assetsManifest ''
    foreach ($e in $script:ManifestStore) { $matcher.Add($e.path, $e.why) }
}
foreach ($f in $StoreFolders) { $matcher.Add($f, '-StoreFolders') }
$trackedTop = @{}; foreach ($d in (Invoke-Git $repo @('ls-tree', '-d', '--name-only', $sha, 'Content/'))) { $trackedTop[$d.Trim()] = 1 }
$untrackedStore = New-Object System.Collections.ArrayList
$contentDir = Join-Path $info.Dir 'Content'
if (Test-Path $contentDir) {
    foreach ($d in Get-ChildItem $contentDir -Directory) {
        $rel = "Content/$($d.Name)"
        if ($trackedTop.ContainsKey($rel)) { continue }
        # store when git-ignored now, or when the commit's manifest calls it store content (the working tree's .gitignore
        # may have changed since the commit, e.g. once the packs were committed later)
        $null = Invoke-Git $info.Dir @('check-ignore', '-q', "$rel/") -AllowFail
        if ($LASTEXITCODE -eq 0 -or $matcher.Match("$rel/x")) { [void]$untrackedStore.Add([pscustomobject]@{ rel = $rel; dir = $d.FullName; why = $null }) }
    }
}
# pack folder names to look for in a build's .utoc/.pak directory index (Content/Fab/<Pack> -> <Pack>)
$packNames = @(foreach ($u in $untrackedStore) {
        if ((Split-Path $u.dir -Leaf) -ieq 'Fab') { Get-ChildItem $u.dir -Directory | ForEach-Object Name } else { Split-Path $u.dir -Leaf } })
function Test-StoreArt([string]$root) {
    $idx = @(Get-ChildItem $root -Recurse -File -Include *.utoc, *.pak -ErrorAction SilentlyContinue | Where-Object { $_.Length -lt 256MB } | ForEach-Object FullName)
    $found = @($packNames | Where-Object { $n = $_; @($idx | Where-Object { [GameDeliverable.Tools]::ContainsAscii($_, $n) }).Count -gt 0 })
    return [pscustomobject]@{ found = $found; missing = @($packNames | Where-Object { $found -notcontains $_ }) }
}

# Never copy a pipeline build of this game while build.ps1 is writing one (it holds the pipeline lock as "build <game> <sha>").
$lockInfo = Read-JsonFile (Join-Path $BuildsRoot '_pipeline.lock.json')
$lockJob = Get-Prop $lockInfo 'job'; $lockPid = Get-Prop $lockInfo 'pid'
if ($lockJob -match "^build $([regex]::Escape($Game)) " -and $lockPid -and (Get-Process -Id $lockPid -ErrorAction SilentlyContinue)) {
    throw "the pipeline is building $Game right now ($lockJob, pid $lockPid); package after it finishes"
}

# Build: given, else the newest packaged pipeline build of the lineage (Shipping unless -AllowDevelopmentBuild).
$buildSel = $null; $buildCands = @()
if ($Build) {
    $bd = (Resolve-Path $Build).Path; $bi = Read-JsonFile (Join-Path $bd 'build_info.json')
    $root = if (Test-Path (Join-Path $bd 'Windows')) { Join-Path $bd 'Windows' } else { $bd }
    $bc = Get-Prop $bi 'commit'
    if (-not $bc -and $BuildCommit) { $bc = @(Invoke-Git $repo @('rev-parse', '--verify', "$BuildCommit^{commit}"))[0].Trim() }
    if ($bc -and -not $lineage.ContainsKey($bc)) { throw "-Build: commit $bc is not in the lineage of $short" }
    $cfg = Get-Prop $bi 'config'
    if (-not $cfg) { $cfg = if (Get-ChildItem $root -Recurse -Filter '*-Shipping.exe' -File -ErrorAction SilentlyContinue | Select-Object -First 1) { 'Shipping' } else { 'Development' } }
    $buildSel = [pscustomobject]@{ root = $root; commit = $bc; config = $cfg; info = $bi; source = 'given with -Build' }
} else {
    $bRoot = Join-Path $BuildsRoot $Game
    if (Test-Path $bRoot) {
        foreach ($d in Get-ChildItem $bRoot -Directory | Where-Object { $_.Name -notlike '_*' }) {
            $bi = Read-JsonFile (Join-Path $d.FullName 'build_info.json'); $bc = Get-Prop $bi 'commit'
            if (-not $bi -or (Get-Prop $bi 'status') -ne 'ok' -or -not (Get-Prop $bi 'packaged') -or -not $bc -or -not $lineage.ContainsKey($bc)) { continue }
            if (-not (Test-Path (Join-Path $d.FullName 'Windows'))) { continue }
            if ($packNames.Count -and (Test-StoreArt (Join-Path $d.FullName 'Windows')).found.Count -eq 0) {
                [void]$warnings.Add("pipeline build $($d.Name) not used: none of the git-ignored store packs is cooked into it (built from a clean clone)"); continue
            }
            $cfg = Get-Prop $bi 'config'; if (-not $cfg) { $cfg = 'Development' }
            $buildCands += [pscustomobject]@{ root = (Join-Path $d.FullName 'Windows'); commit = $bc; config = $cfg; info = $bi; source = "pipeline build $($d.Name)"; age = $lineage[$bc] }
        }
    }
    $buildSel = $buildCands | Where-Object { $_.config -eq 'Shipping' } | Sort-Object age | Select-Object -First 1
    if (-not $buildSel) {
        # The game session's own Shipping package (Packaged\Windows): its commit is the one in the newest successful
        # build.package row of the working tree's workflow.jsonl, if that row was written within 20 min of the exe
        # (so the folder is that package) and the commit is in the lineage. Stated by the log, not verified.
        $pk = Join-Path $info.Dir 'Packaged\Windows'
        $shipExe = if (Test-Path $pk) { Get-ChildItem $pk -Recurse -Filter '*-Shipping.exe' -File -ErrorAction SilentlyContinue | Select-Object -First 1 }
        $wfLive = Join-Path $info.Dir 'workflow.jsonl'
        if ($shipExe -and (Test-Path $wfLive)) {
            $row = $null
            # games name the row differently (build.package, package.exit / package.result, package.build): any *package*
            # row for a Shipping target that succeeded (result ok or exit_code 0)
            foreach ($l in [System.IO.File]::ReadAllLines($wfLive, $Utf8NoBom)) {
                if ($l -match '"op":\s*"[^"]*package[^"]*"' -and $l -match '"(target|config)":\s*"[^"]*Shipping' -and ($l -match '"result":\s*"ok"' -or $l -match '"exit_code":\s*0\b')) { $row = $l }
            }
            if ($row) {
                $r = $row | ConvertFrom-Json; $rc = Get-Prop (Get-Prop $r 'source') 'commit'; $rt = [DateTimeOffset]::Parse((Get-Prop $r 'time'))
                $full = if ($rc) { @(Invoke-Git $repo @('rev-parse', '--verify', "$rc^{commit}") -AllowFail)[0].Trim() } else { $null }
                $gap = [math]::Abs(($rt.UtcDateTime - $shipExe.LastWriteTimeUtc).TotalMinutes)
                if ($full -and $lineage.ContainsKey($full) -and $gap -le 20) {
                    $buildSel = [pscustomobject]@{ root = $pk; commit = $full; config = 'Shipping'; info = $null; age = $lineage[$full]
                        source = "game session package Packaged\Windows (workflow row $(Get-Prop $r 'id'))" }
                } else { [void]$warnings.Add("Packaged\Windows Shipping package not used: newest build.package row commit $rc, $([math]::Round($gap)) min from the exe, in lineage: $([bool]($full -and $lineage.ContainsKey($full)))") }
            }
        }
    }
    if (-not $buildSel -and $AllowDevelopmentBuild) { $buildSel = $buildCands | Sort-Object age | Select-Object -First 1 }
}
$buildMsg = "no packaged Shipping build of $Game in the lineage of $short under $(Join-Path $BuildsRoot $Game) (found: $(if ($buildCands) { ($buildCands | ForEach-Object { "$($_.source) $($_.config)" }) -join ', ' } else { 'none' })). Build one (ue-pipeline\build.ps1 $Game -Commit $short -Package), or pass -Build <dir> or -AllowDevelopmentBuild."
$storeArt = $null
if ($buildSel -and $packNames.Count) {
    $storeArt = Test-StoreArt $buildSel.root
    if ($storeArt.found.Count -eq 0) {
        $msg = "Build $($buildSel.root) has none of the git-ignored store packs cooked in ($($packNames -join ', ')): it was built without the art"
        if ($DryRun) { [void]$warnings.Add($msg) } else { throw $msg }
    }
    if ($storeArt.missing.Count) { [void]$warnings.Add("store packs not named in the build's pak index (unused by cooked maps?): $($storeArt.missing -join ', ')") }
}
if ($buildSel) {
    if ($buildSel.config -ne 'Shipping') { [void]$warnings.Add("Build/ is a $($buildSel.config) build, not Shipping") }
    if ($buildSel.commit -and $buildSel.commit -ne $sha) { [void]$warnings.Add("Build/ was built from $($buildSel.commit.Substring(0,8)), an earlier commit than $short") }
    if (-not $buildSel.commit) { [void]$warnings.Add('Build/ commit unknown (no build_info.json; state it with -BuildCommit)') }
} elseif (-not $DryRun) { throw $buildMsg }

# Gameplay: validated bundles (ok|warn, no FAILED marker) played on a build of the lineage.
$ExcludeRunIds = @($ExcludeRuns | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$selectedRuns = New-Object System.Collections.ArrayList; $skippedRuns = New-Object System.Collections.ArrayList
$recDir = Join-Path $RecordingsRoot $Game
if (Test-Path $recDir) {
    foreach ($b in Get-ChildItem $recDir -Directory | Where-Object { $_.Name -notlike '_*' } | Sort-Object Name) {   # _stills etc. are not runs
        $meta = Read-JsonFile (Join-Path $b.FullName 'metadata.json'); $val = Read-JsonFile (Join-Path $b.FullName 'validation.json')
        $bsha = Get-Prop (Get-Prop $meta 'build') 'commit'; $vstat = Get-Prop $val 'status'
        $why = $null
        if ($ExcludeRunIds -contains $b.Name) { $why = 'left out with -ExcludeRuns' }
        elseif (Test-Path (Join-Path $b.FullName 'FAILED')) { $why = 'FAILED' }
        elseif (-not $meta -or -not $val) { $why = 'no metadata/validation' }
        elseif ($vstat -notin @('ok', 'warn')) { $why = "validation $vstat" }
        elseif (-not $bsha -or -not $lineage.ContainsKey($bsha)) { $why = 'build not in the lineage' }
        elseif ($OnlyCommitRuns -and $bsha -ne $sha) { $why = 'played on an earlier commit (-OnlyCommitRuns)' }
        if ($why) { [void]$skippedRuns.Add([pscustomobject]@{ run = $b.Name; why = $why }) }
        else { [void]$selectedRuns.Add([pscustomobject]@{ dir = $b; meta = $meta; val = $val; sha = $bsha; status = $vstat }) }
    }
}

if (-not $DryRun) {
    foreach ($p in @($final, $stage, "$final.refused", $zipPath)) {
        if (Test-Path $p) { if ($Force) { Remove-Item -Recurse -Force $p } else { throw "$p exists (use -Force to replace it)" } }
    }
    New-Item -ItemType Directory -Force $stage | Out-Null
}

# ---------------------------------------------------------------------------------------------------------------------
# store content: what counts
# ---------------------------------------------------------------------------------------------------------------------
# (manifest rules, $matcher and $untrackedStore were set up before the build selection)
foreach ($u in $untrackedStore) {
    $why = $matcher.Match("$($u.rel)/x"); if (-not $why) { $why = 'git-ignored folder under Content/ (store pack kept out of git)' }
    $u.why = $why; $matcher.Add($u.rel, $why)
}
Write-Step "store content rules: $($matcher.Count) manifest/param paths + folders named Fab; untracked store folders: $(@($untrackedStore | ForEach-Object { $_.rel }) -join ', ')"

if ($DryRun) {
    $tree = [GameDeliverable.Tools]::ClassifyTree($repo, $sha, $matcher)
    $st = @($tree | Where-Object { $_.Store })
    Write-Host "tracked files at $short`: $($tree.Count), of which store content: $($st.Count)"
    $st | Group-Object { $p = $_.Path -split '/'; if ($p.Count -ge 3 -and $p[1] -ieq 'Fab') { ($p[0..2] -join '/') } elseif ($p.Count -ge 2) { ($p[0..1] -join '/') } else { $p[0] } } |
        Sort-Object Name | ForEach-Object { Write-Host ("  {0,6}  {1,-48} {2}" -f $_.Count, $_.Name, $_.Group[0].Store) }
    foreach ($u in $untrackedStore) {
        $n = @(Get-ChildItem $u.dir -Recurse -File).Count
        Write-Host ("  {0,6}  {1,-48} {2} [working tree, untracked]" -f $n, $u.rel, $u.why)
    }
    Write-Host "build: $(if ($buildSel) { "$($buildSel.source) $($buildSel.config) $($buildSel.commit)" } else { "NONE - $buildMsg" })"
    Write-Host "gameplay: $($selectedRuns.Count) bundle(s) $(@($selectedRuns | ForEach-Object { $_.dir.Name }) -join ', '); not included: $(@($skippedRuns | ForEach-Object { "$($_.run) ($($_.why))" }) -join ', ')"
    foreach ($w in $warnings) { Write-Host "warning: $w" }
    exit 0
}

# ---------------------------------------------------------------------------------------------------------------------
# UEProject
# ---------------------------------------------------------------------------------------------------------------------
$ueDir = Join-Path $stage 'UEProject'
New-Item -ItemType Directory -Force $ueDir | Out-Null
$dropped = New-Object 'System.Collections.Generic.List[GameDeliverable.PkgFile]'
Write-Step 'exporting the tree at the commit (git + local Git LFS store)'
$exported = [GameDeliverable.Tools]::ExportTree($repo, $sha, $ueDir, $matcher, (-not $WithoutStoreContent), $lfsDir,
    [string[]]@('Binaries', 'Intermediate', 'Saved', 'DerivedDataCache'), $dropped, $problems)
$storeRows = New-Object System.Collections.ArrayList
foreach ($f in $exported) { if ($f.Store) { [void]$storeRows.Add([pscustomobject]@{ status = 'included'; f = $f }) } }
foreach ($f in $dropped) { [void]$storeRows.Add([pscustomobject]@{ status = 'dropped'; f = $f }) }
foreach ($u in $untrackedStore) {
    if ($WithoutStoreContent) {
        Write-Step "listing (dropped) $($u.rel) from the working tree"
        $rows = [GameDeliverable.Tools]::CopyTree($u.dir, '', "$($u.rel)/", [string[]]@(), $false, $true, 'working-tree', $u.why, $problems)
        foreach ($f in $rows) { [void]$storeRows.Add([pscustomobject]@{ status = 'dropped'; f = $f }) }
    } else {
        Write-Step "copying $($u.rel) from the working tree (not versioned in git)"
        $rows = [GameDeliverable.Tools]::CopyTree($u.dir, (Join-Path $ueDir ($u.rel.Replace('/', '\'))), "$($u.rel)/", [string[]]@(), $true, $true, 'working-tree', $u.why, $problems)
        foreach ($f in $rows) { [void]$storeRows.Add([pscustomobject]@{ status = 'included'; f = $f }) }
    }
}
$storeTsv = New-Object System.Text.StringBuilder
[void]$storeTsv.Append("status`tpath`tbytes`tsha256`tsource`twhy`n")
foreach ($r in ($storeRows | Sort-Object { $_.f.Path })) {
    [void]$storeTsv.Append("$($r.status)`tUEProject/$($r.f.Path)`t$($r.f.Bytes)`t$($r.f.Sha256)`t$($r.f.Source)`t$($r.f.Store)`n")
}
Write-Utf8 (Join-Path $stage 'StoreContent.tsv') $storeTsv.ToString()
$storeByFolder = $storeRows | Group-Object { $p = $_.f.Path -split '/'; if ($p.Count -ge 3 -and $p[1] -ieq 'Fab') { ($p[0..2] -join '/') } elseif ($p.Count -ge 2) { ($p[0..1] -join '/') } else { $p[0] } } |
    ForEach-Object { [pscustomobject]@{ folder = $_.Name; files = $_.Count; bytes = ($_.Group | ForEach-Object { $_.f.Bytes } | Measure-Object -Sum).Sum
        status = (@($_.Group | ForEach-Object { $_.status } | Sort-Object -Unique) -join '+'); source = (@($_.Group | ForEach-Object { $_.f.Source } | Sort-Object -Unique) -join '+')
        why = (@($_.Group | ForEach-Object { $_.f.Store } | Sort-Object -Unique) | Select-Object -First 1) } } | Sort-Object folder

# ---------------------------------------------------------------------------------------------------------------------
# workflow.jsonl, git.log
# ---------------------------------------------------------------------------------------------------------------------
if (-not [GameDeliverable.Tools]::WriteBlob($repo, "${sha}:workflow.jsonl", (Join-Path $stage 'workflow.jsonl'))) {
    $problems.Add('error: no workflow.jsonl at the commit')
}
Write-Step 'writing git.log'
$authors = New-Object 'System.Collections.Generic.Dictionary[string,string]'
$glHeader = "GIT-LOG 1`n# Project $($info.ProjectName) ($Game): the original git history up to commit $sha, oldest first.`n" +
    "# Recorded as it happened (not reconstructed). Authors and committers are anonymised as dev_NN.`n" +
    "# Text changes are full unified diffs; binary files and Git LFS files are given as path + sha256 + bytes (old -> new).`n`n"
$commitCount = [GameDeliverable.Tools]::WriteGitLog($repo, $sha, (Join-Path $stage 'git.log'), $glHeader, $authors, $problems)

# ---------------------------------------------------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------------------------------------------------
$histDir = Join-Path $stage 'History'; New-Item -ItemType Directory -Force $histDir | Out-Null
$commitDto = [DateTimeOffset]::Parse($commitTime)
$histStats = [ordered]@{}
# actions.jsonl rows of sessions that are not creation work: packaging sessions (their tool calls get logged under the
# game when their working directory is inside it), i.e. sessions whose rows here are mostly about this packager (over a
# quarter of them name it; a builder that only reads about it or mentions it keeps its history), plus -ExcludeSessions.
$skipSessions = @{}; foreach ($x in @($ExcludeSessions | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })) { $skipSessions[$x] = 'given' }
$actSrc = Join-Path $info.LogDir 'actions.jsonl'
if (Test-Path $actSrc) {
    $sesRows = @{}; $sesPkg = @{}
    foreach ($line in [System.IO.File]::ReadAllLines($actSrc, $Utf8NoBom)) {
        if ($line -notmatch '"session_id"\s*:\s*"([^"]+)"') { continue }
        $sid = $Matches[1]; $sesRows[$sid] = 1 + [int]$sesRows[$sid]
        if ($line -match 'package-game\.ps1') { $sesPkg[$sid] = 1 + [int]$sesPkg[$sid] }
    }
    foreach ($sid in $sesPkg.Keys) { if (-not $skipSessions.ContainsKey($sid) -and $sesPkg[$sid] / $sesRows[$sid] -gt 0.25) { $skipSessions[$sid] = 'packaging session' } }
}
foreach ($h in @(
        @{ file = 'commits.jsonl'; rx = '"sha"\s*:\s*"([0-9a-f]{40})"'; kind = 'commit' },
        @{ file = 'actions.jsonl'; rx = '"time"\s*:\s*"([^"]+)"'; kind = 'time' },
        @{ file = 'builds.jsonl'; rx = '"commit"\s*:\s*"([0-9a-f]{40})"'; kind = 'commit' },
        @{ file = 'runs.jsonl'; rx = '"build_commit"\s*:\s*"([0-9a-f]{40})"'; kind = 'commit' })) {
    $src = Join-Path $info.LogDir $h.file
    if (-not (Test-Path $src)) { [void]$warnings.Add("History/$($h.file): not found in .recording"); continue }
    $kept = New-Object System.Collections.Generic.List[string]; $total = 0
    foreach ($line in [System.IO.File]::ReadAllLines($src, $Utf8NoBom)) {
        if (-not $line.Trim()) { continue }
        $total++; $m = [regex]::Match($line, $h.rx); if (-not $m.Success) { continue }
        if ($h.file -eq 'actions.jsonl' -and $skipSessions.Count -and $line -match '"session_id"\s*:\s*"([^"]+)"' -and $skipSessions.ContainsKey($Matches[1])) { continue }
        if ($h.kind -eq 'commit') { if ($lineage.ContainsKey($m.Groups[1].Value)) { $kept.Add($line) } }
        else { $dt = [DateTimeOffset]::MinValue; if ([DateTimeOffset]::TryParse($m.Groups[1].Value, [ref]$dt) -and $dt -le $commitDto) { $kept.Add($line) } }
    }
    Write-Utf8 (Join-Path $histDir $h.file) ((($kept -join "`n") + $(if ($kept.Count) { "`n" } else { '' })))
    $histStats[$h.file] = [ordered]@{ rows = $kept.Count; source_rows = $total }
    if ($h.file -eq 'actions.jsonl') { $histStats[$h.file].sessions_left_out = $skipSessions.Count }
}

# ---------------------------------------------------------------------------------------------------------------------
# Gameplay
# ---------------------------------------------------------------------------------------------------------------------
$gpDir = Join-Path $stage 'Gameplay'; New-Item -ItemType Directory -Force $gpDir | Out-Null
$runs = New-Object System.Collections.ArrayList
foreach ($sel in $selectedRuns) {
        $b = $sel.dir; $meta = $sel.meta; $val = $sel.val; $bsha = $sel.sha; $vstat = $sel.status
        Write-Step "gameplay bundle $($b.Name)"
        $null = [GameDeliverable.Tools]::CopyTree($b.FullName, (Join-Path $gpDir $b.Name), '', [string[]]@(), $true, $false, 'recording', $null, $problems)
        $out = Read-JsonFile (Join-Path $b.FullName 'outcome.json')
        $scen = Get-Prop $meta 'scenario'; if ($null -eq $scen) { $scen = Get-Prop $meta 'level' }
        $sname = Get-Prop $meta 'scenario_name'; if (-not $sname) { $sname = Get-Prop $meta 'level_name' }
        $vv = Get-Prop (Get-Prop $val 'checks') 'video'
        [void]$runs.Add([pscustomobject][ordered]@{
                run_id = $b.Name; scenario = $scen; scenario_name = $sname; seed = (Get-Prop $meta 'seed'); skill = (Get-Prop $meta 'skill')
                result = (Get-Prop $meta 'result'); score = (Get-Prop $meta 'score'); duration_s = (Get-Prop $out 'duration_s')
                video_s = (Get-Prop $vv 'duration_s'); game_fps = (Get-Prop $vv 'game_fps'); inputs_injected = (Get-Prop $out 'inputs_injected')
                build_commit = $bsha; build_config = (Get-Prop (Get-Prop $meta 'build') 'config'); validation = $vstat
                store_art_in_build = $(if (-not $packNames.Count) { 'n/a' } else {
                        $bp = Get-Prop (Get-Prop $meta 'build') 'path'
                        if ($bp -and (Test-Path $bp)) { if ((Test-StoreArt $bp).found.Count) { 'yes' } else { 'no' } } else { 'unknown' } })
                warnings = @(Get-Prop $val 'warnings') -join '; '; extra = (Get-Prop $out 'extra')
            })
}
$gpMd = New-Object System.Text.StringBuilder
[void]$gpMd.Append("# Gameplay recordings`n`nEach folder is one AutoPlay run: the game played by its in-game bot through Enhanced Input, recorded with`n")
[void]$gpMd.Append("video (1920x1080, 60 fps), game audio, every injected input and the game's telemetry on one clock. Only runs that`n")
[void]$gpMd.Append("passed validation (``validation.json`` status ok or warn) and were played on a build of this project's history are included.`n`n")
if ($runs.Count) {
    if ($packNames.Count) {
        [void]$gpMd.Append("The store packs of this project are kept outside git. **Store art in build** says whether the build a run was played on had them cooked in;`n")
        [void]$gpMd.Append("``no`` means a build made from a clean checkout, so the video shows the game without that art (it differs from ``Build/``).`n`n")
    }
    [void]$gpMd.Append("| Run | Scenario | Seed | Skill | Result | Score | Duration (s) | Video (s) | Game fps | Inputs | Build | Store art in build | Validation |`n|---|---|---|---|---|---|---|---|---|---|---|---|---|`n")
    foreach ($r in $runs) {
        [void]$gpMd.Append("| ``$($r.run_id)`` | $($r.scenario) $($r.scenario_name) | $($r.seed) | $($r.skill) | $($r.result) | $($r.score) | $(if ($r.duration_s) { '{0:N1}' -f [double]$r.duration_s }) | $(if ($r.video_s) { '{0:N1}' -f [double]$r.video_s }) | $($r.game_fps) | $($r.inputs_injected) | $($r.build_commit.Substring(0,8)) $($r.build_config) | $($r.store_art_in_build) | $($r.validation)$(if ($r.warnings) { ": $($r.warnings)" }) |`n")
    }
} else { [void]$gpMd.Append("No validated run exists yet for this commit lineage.`n") }
if ($skippedRuns.Count) {
    [void]$gpMd.Append("`nNot included: $($skippedRuns.Count) run(s) ($(@($skippedRuns | Group-Object why | ForEach-Object { "$($_.Count) $($_.Name)" }) -join ', ')).`n")
}
[void]$gpMd.Append("`nFiles per run: ``video.mkv``, ``system_audio.mka``, ``inputs.jsonl``, ``telemetry.jsonl``, ``outcome.json``, ``metadata.json``")
[void]$gpMd.Append(" (clock samples, ``video_start_offset_ns``: video_time_s = (t_ns - video_start_offset_ns) / 1e9), ``validation.json``, ``manifest.json``, ``raw/`` (the game's own output folder).`n")
Write-Utf8 (Join-Path $gpDir 'summary.md') $gpMd.ToString()
Write-JsonFile (Join-Path $gpDir 'summary.json') ([ordered]@{ runs = @($runs); not_included = @($skippedRuns) })

# ---------------------------------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------------------------------
$buildDir = Join-Path $stage 'Build'; New-Item -ItemType Directory -Force $buildDir | Out-Null
Write-Step "build: $($buildSel.source), $($buildSel.config), commit $($buildSel.commit)"
$skipExt = if ($IncludePdb) { [string[]]@() } else { [string[]]@('.pdb') }
$null = [GameDeliverable.Tools]::CopyTree($buildSel.root, $buildDir, '', $skipExt, $true, $false, 'build', $null, $problems)
$exe = Get-ChildItem $buildDir -Filter *.exe -File | Select-Object -First 1
$buildInfo = [ordered]@{
    project = $info.ProjectName; config = $buildSel.config; commit = $buildSel.commit
    commit_verified = [bool](Get-Prop $buildSel.info 'commit'); source = $buildSel.source
    built_start = (Get-Prop $buildSel.info 'start'); built_end = (Get-Prop $buildSel.info 'end'); exe = $(if ($exe) { $exe.Name })
    debug_symbols = [bool]$IncludePdb
    store_packs_outside_git = $(if ($storeArt) { [ordered]@{ cooked = @($storeArt.found); not_in_pak_index = @($storeArt.missing) } } else { $null })
}
Write-JsonFile (Join-Path $buildDir 'build_info.json') $buildInfo
# The account name compiled into the build (source paths in the exe) is a blocker; -PendingCleanBuild produces a package
# marked "pending clean build" (README + manifest) until the build is redone from a root without it.
$buildRels = [string[]]@(Get-ChildItem $buildDir -Recurse -File | ForEach-Object { 'Build/' + $_.FullName.Substring($buildDir.Length + 1).Replace('\', '/') })
$bl = New-Object 'System.Collections.Generic.List[GameDeliverable.Hit]'
$buildUserHits = @([GameDeliverable.Tools]::Scan($stage, $buildRels, (New-Object System.Text.RegularExpressions.Regex('(?!)')), $null, $bl, 20,
        [string[]]@($UserName), [bool[]]@($false), [string[]]@('username')) | Where-Object { $_.Kind -like 'binary*' })
$pendingClean = $false
if ($buildUserHits.Count) {
    $files = @($buildUserHits | ForEach-Object Path | Sort-Object -Unique)
    if (-not $PendingCleanBuild) {
        Remove-Item -Recurse -Force $stage
        throw "Build/ has the account name compiled in ($($buildUserHits.Count) hits in $($files.Count) files, e.g. $($files[0])): rebuild from a root without it, or pass -PendingCleanBuild for a package marked as pending"
    }
    $pendingClean = $true
    [void]$warnings.Add("PENDING CLEAN BUILD: Build/ has the account name compiled in ($($files.Count) files); package marked as not final")
}

# ---------------------------------------------------------------------------------------------------------------------
# Screenshots: the project's docs/screenshots/ at the commit, else 3-4 stills of the gameplay runs in this package
# (recordings\<game>\_stills\<run>_NN.jpg; stills of runs left out may show old art, so never those)
# ---------------------------------------------------------------------------------------------------------------------
$shots = New-Object System.Collections.ArrayList   # { file, caption }
$shotDir = Join-Path $stage 'Screenshots'
$shotSource = $null
$repoShots = @(Get-ChildItem $ueDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -in @('docs', 'Docs') } |
        ForEach-Object { Join-Path $_.FullName 'screenshots' } | Where-Object { Test-Path $_ } |
        ForEach-Object { Get-ChildItem $_ -File | Where-Object { $_.Extension -match '^\.(png|jpe?g|webp|gif)$' } } | Sort-Object Name)
# Preferred: the images the project's own README.md shows (in README order, alt text as caption; any folder or case,
# e.g. Docs/screenshots/), then everything in docs/screenshots/, then stills.
$readmeShots = New-Object System.Collections.ArrayList
$readmePath = Join-Path $ueDir 'README.md'
if (Test-Path $readmePath) {
    $rt = [System.IO.File]::ReadAllText($readmePath, $Utf8NoBom)
    $refs = @([regex]::Matches($rt, '!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)') | ForEach-Object { [pscustomobject]@{ alt = $_.Groups[1].Value; path = $_.Groups[2].Value } }) +
            @([regex]::Matches($rt, '<img\b[^>]*\bsrc\s*=\s*"([^"]+)"[^>]*>') | ForEach-Object { $alt = [regex]::Match($_.Value, '\balt\s*=\s*"([^"]*)"').Groups[1].Value; [pscustomobject]@{ alt = $alt; path = $_.Groups[1].Value } })
    foreach ($ref in $refs) {
        $rel = [uri]::UnescapeDataString(($ref.path -split '[?#]')[0]).TrimStart('.', '/').Replace('/', '\')
        if ($rel -match '^[a-z]+:' -or $rel -notmatch '\.(png|jpe?g|webp|gif)$') { continue }   # URLs and non-images
        $full = Join-Path $ueDir $rel
        if ((Test-Path -LiteralPath $full) -and -not ($readmeShots | Where-Object { $_.f.FullName -eq (Get-Item -LiteralPath $full).FullName })) {
            [void]$readmeShots.Add([pscustomobject]@{ f = (Get-Item -LiteralPath $full); alt = $ref.alt.Trim() })
        }
    }
}
if ($Screenshots -eq 'stills') { $repoShots = @(); $readmeShots.Clear() }
if ($readmeShots.Count) {
    New-Item -ItemType Directory -Force $shotDir | Out-Null
    foreach ($s in $readmeShots) {
        Copy-Item $s.f.FullName (Join-Path $shotDir $s.f.Name) -Force
        $cap = if ($s.alt) { $s.alt } else { ($s.f.BaseName -replace '^\d+[-_ ]*', '' -replace '[-_]+', ' ').Trim() }
        [void]$shots.Add([pscustomobject]@{ file = $s.f.Name; caption = $(if ($cap) { $cap } else { $s.f.BaseName }) })
    }
    $shotSource = "the images in the project's README.md"
} elseif ($repoShots.Count) {
    New-Item -ItemType Directory -Force $shotDir | Out-Null
    foreach ($f in $repoShots) {
        Copy-Item $f.FullName (Join-Path $shotDir $f.Name)
        $cap = ($f.BaseName -replace '^\d+[-_ ]*', '' -replace '[-_]+', ' ').Trim()
        [void]$shots.Add([pscustomobject]@{ file = $f.Name; caption = $(if ($cap) { $cap } else { $f.BaseName }) })
    }
    $shotSource = "the project's $(Split-Path (Split-Path $repoShots[0].DirectoryName -Parent) -Leaf)/screenshots/"
} elseif ($Screenshots -ne 'repo') {
    $stillDir = Join-Path $recDir '_stills'
    $perRun = @(foreach ($r in $runs) {
            $fr = @(Get-ChildItem $stillDir -File -Filter "$($r.run_id)_*.jpg" -ErrorAction SilentlyContinue | Sort-Object Name)
            if ($fr.Count) { [pscustomobject]@{ run = $r; frames = $fr } } })
    $picked = New-Object System.Collections.ArrayList
    foreach ($pos in @(0.5, 0.25, 0.75, 0.1)) {   # round robin over the runs: middle frame first, then quarter points
        foreach ($p in $perRun) {
            if ($picked.Count -ge 4) { break }
            $f = $p.frames[[math]::Min($p.frames.Count - 1, [int][math]::Floor($pos * $p.frames.Count))]
            if (-not ($picked | Where-Object { $_.f.FullName -eq $f.FullName })) { [void]$picked.Add([pscustomobject]@{ f = $f; r = $p.run }) }
        }
    }
    if ($picked.Count) {
        New-Item -ItemType Directory -Force $shotDir | Out-Null
        foreach ($p in $picked) {
            Copy-Item $p.f.FullName (Join-Path $shotDir $p.f.Name)
            $n = $p.f.BaseName.Substring($p.r.run_id.Length).TrimStart('_')
            [void]$shots.Add([pscustomobject]@{ file = $p.f.Name; caption = "Scenario $($p.r.scenario) $($p.r.scenario_name), frame $n of run ``$($p.r.run_id)``" })
        }
        $shotSource = 'frames of the gameplay recordings in `Gameplay/`'
    }
}
if ($shots.Count) { Write-Step "screenshots: $($shots.Count) from $shotSource" } else { [void]$warnings.Add('no screenshots: no docs/screenshots/ in the project and no stills of the runs in this package') }

# ---------------------------------------------------------------------------------------------------------------------
# README.md
# ---------------------------------------------------------------------------------------------------------------------
function Read-StageText([string]$rel) { $p = Join-Path $ueDir $rel; if (Test-Path $p) { return [System.IO.File]::ReadAllText($p, $Utf8NoBom) } else { return $null } }
$gameReadme = Read-StageText 'README.md'
$docTexts = @(); foreach ($d in @(Get-ChildItem (Join-Path $ueDir 'Docs') -Filter *.md -File -ErrorAction SilentlyContinue)) { $docTexts += [System.IO.File]::ReadAllText($d.FullName, $Utf8NoBom) }
$allDocs = @($gameReadme) + $docTexts | Where-Object { $_ }
$title = $info.ProjectName; $intro = $null
if ($gameReadme) {
    if ($gameReadme -match '(?m)^#\s+(.+)$') { $title = $Matches[1].Trim() }
    $intro = (($gameReadme -split '(?m)^##\s')[0] -replace '(?m)^#\s+.*$', '').Trim()
}
$uproj = (Get-Content (Join-Path $ueDir $info.UProjectName) -Raw) | ConvertFrom-Json
$engine = Get-Prop $uproj 'EngineAssociation'
$playSec = $null; $scenSec = $null
foreach ($t in $allDocs) { if (-not $playSec) { $playSec = Get-MdSection $t '^(Play|How to play|Controls)\b' } }
foreach ($t in $allDocs) { if (-not $scenSec) { $scenSec = Get-MdSection $t '^Scenarios\b' } }
$notices = Read-StageText 'Docs/ThirdPartyNotices.md'
if (-not $notices) { foreach ($t in $allDocs) { if (-not $notices) { $notices = Get-MdSection $t '(?i)licen[cs]e|third.party|credits' } } }
$credits = @(Get-Prop $assetsManifest 'credits_required')

$wfRows = 0; $wfOps = @{}; $wfStatus = @{}; $wfReason = @{}; $wfFirst = $null; $wfLast = $null
$wfPath = Join-Path $stage 'workflow.jsonl'
if (Test-Path $wfPath) {
    foreach ($line in [System.IO.File]::ReadAllLines($wfPath, $Utf8NoBom)) {
        if (-not $line.Trim()) { continue }
        try { $row = $line | ConvertFrom-Json } catch { continue }
        $wfRows++
        $op = Get-Prop $row 'op'; if ($op) { $wfOps[$op] = 1 + [int]$wfOps[$op] }
        $st = Get-Prop $row 'status'; if (-not $st) { $st = '(none)' }; $wfStatus[$st] = 1 + [int]$wfStatus[$st]
        $rs = Get-Prop $row 'reason_source'; if (-not $rs) { $rs = '(none)' }; $wfReason[$rs] = 1 + [int]$wfReason[$rs]
        $tm = Get-Prop $row 'time'; if ($tm) { if (-not $wfFirst) { $wfFirst = $tm }; $wfLast = $tm }
    }
}
$fmtCounts = { param($h) (@($h.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "$($_.Key) $($_.Value)" }) -join ', ') }
$topOps = (@($wfOps.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 12 | ForEach-Object { "``$($_.Key)`` $($_.Value)" }) -join ', ')

$sizeOf = { param($dir) $s = (Get-ChildItem $dir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; if ($s) { [double]$s } else { 0 } }
$sb = New-Object System.Text.StringBuilder
function A([string]$s = '') { [void]$sb.Append($s + "`n") }
A "# $title"
A ''
if ($shots.Count) { A "![$title]($('Screenshots/' + $shots[0].file))"; A '' }
if ($Version) { A "**Version $Version**$(if ($releaseTag) { " (tag ``$releaseTag``)" })$(if ($pendingClean) { ', pending clean build' })."; A '' }
if ($pendingClean) {
    A '> **Pending clean build: not final.** The executable in `Build/` was compiled on a machine path that is to be removed;'
    A '> this package will be replaced by one with a clean rebuild of the same commit. Source, history and recordings are unaffected.'
    A ''
}
A "Unreal Engine $engine project ``$($info.ProjectName)``, packaged at commit ``$short`` ($commitTime, ""$commitSubject"")."
A "Variant: **$(if ($WithoutStoreContent) { 'without store content' } else { 'with store content' })** (see Store content below)."
A ''
if ($intro) { A $intro; A '' }
if ($shots.Count) {
    A '## Screenshots'
    A ''
    A "From $shotSource."
    A ''
    foreach ($s in $shots) { A "![$($s.caption -replace '[\[\]`]', '')](Screenshots/$($s.file))"; A "*$($s.caption)*"; A '' }
}
A '## Contents'
A ''
A '| Path | What |'
A '|---|---|'
A "| ``UEProject/`` | the project at commit ``$short``, as committed (no Binaries, Intermediate, Saved, DerivedDataCache)$(if ($WithoutStoreContent) { '; store content removed' }) |"
A "| ``workflow.jsonl`` | the creation log: $wfRows operations, one row each, written when the operation happened |"
A "| ``git.log`` | $commitCount commits, oldest first, with message, anonymised author, dates and full diff |"
A '| `History/` | machine logs of the creation sessions: `actions.jsonl` (every tool call of the builder), `commits.jsonl`, `builds.jsonl`, `runs.jsonl` |'
A "| ``Gameplay/`` | $($runs.Count) validated gameplay recording(s); table in ``Gameplay/summary.md`` |"
A "| ``Build/`` | the packaged Windows $($buildSel.config) build$(if ($exe) { " (``Build/$($exe.Name)``)" }), built from commit ``$(if ($buildSel.commit) { $buildSel.commit.Substring(0,8) } else { 'unknown' })``$(if (-not $buildInfo.commit_verified) { ' (as stated by the build log)' }); ``Build/build_info.json`` |"
if ($shots.Count) { A "| ``Screenshots/`` | $($shots.Count) image(s) shown in this README, from $shotSource |" }
A '| `StoreContent.tsv` | every store-content file of the project: included or dropped, path, bytes, sha256, why it is store content |'
A '| `scrub-report.json` | what was rewritten in this copy before packaging (studio names, user paths, e-mail addresses, agent identities): counts per rule and the files touched |'
A '| `manifest.json` | path, bytes and sha256 of every file in this package |'
A ''
A '## Play'
A ''
A "Windows 10/11 64-bit, DirectX 12 GPU. Run ``Build/$(if ($exe) { $exe.Name } else { '<Project>.exe' })``. No installation needed."
if ($PlayNote) { A ''; A $PlayNote }
A ''
if ($playSec) {   # the project's own play notes, minus lines about its local Packaged/ folder or packaging scripts
    $playSec = (($playSec -split "`n") | Where-Object { $_ -notmatch 'Packaged[/\\]|package[_\w]*\.(sh|ps1|bat)' }) -join "`n"
    A (Shift-Headings $playSec.Trim() 1); A ''
}
A '## Open the project'
A ''
A "1. Install Unreal Engine $engine (Epic Games Launcher) and Visual Studio 2022 with the C++ game development workload."
A "2. Open ``UEProject/$($info.UProjectName)`` and let the editor build the C++ module (or build ``$($info.ProjectName)Editor Win64 Development`` from the generated solution)."
if ($WithoutStoreContent) {
    A '3. This variant has no store content: assets from the store folders listed below are missing until they are added from your own'
    A '   copies of the packs, unchanged, at the same paths (`StoreContent.tsv` gives every file with its sha256). Without them the'
    A '   project opens, but maps that use them show missing references.'
}
A ''
A '## Scenarios'
A ''
if ($scenSec) { A (Shift-Headings $scenSec 1) } else { A 'The project documents no scenario table.' }
A ''
A 'Recorded runs of these scenarios are in `Gameplay/` (see `Gameplay/summary.md`).'
A ''
A '## What is observed and what is derived'
A ''
A '| Data | Observed (recorded when it happened) | Derived (computed afterwards) |'
A '|---|---|---|'
A "| ``workflow.jsonl`` | every row: the builder logged each operation as it ran, with its time ($wfFirst to $wfLast); statuses: $(& $fmtCounts $wfStatus); reason sources: $(& $fmtCounts $wfReason) | nothing; copied from the commit |"
A '| `git.log` | commits, messages, dates, file contents | diffs (computed by git), sha256 of binary files, anonymised author names |'
A "| ``History/`` | rows written by the recording hooks and the build/record pipeline at the time | rows are limited to this commit's lineage (actions up to $commitTime) |"
A '| `Gameplay/*/` | video, audio, inputs, telemetry, outcome, clock samples | `metadata.json` estimates (video start offset), `validation.json`, `summary.md` |'
A '| `UEProject/`, `Build/` | the committed project; the packaged build | nothing |'
A '| `README.md`, `manifest.json`, `StoreContent.tsv` | | written by the packaging step from the project''s own docs and files |'
A ''
A "Operation kinds in ``workflow.jsonl`` ($($wfOps.Count)), most frequent: $topOps."
A ''
A '## Assets and licences'
A ''
if ($credits) { A 'Required credits:'; A ''; foreach ($c in $credits) { A "- $c" }; A '' }
if ($notices) { A (Shift-Headings (($notices -replace '(?m)\A#\s+.*$', '').Trim()) 1); A '' }
if (Test-Path (Join-Path $ueDir 'assets.manifest.json')) { A '`UEProject/assets.manifest.json` gives the source and licence of every asset.'; A '' }
A '## Store content'
A ''
A 'Packs from the Fab store under the Fab Standard License may ship inside a packaged game but not as source files.'
A 'They are listed here and file by file in `StoreContent.tsv`.'
A ''
if ($storeByFolder) {
    A '| Folder | Files | Size | In this package | From | Licence / why |'
    A '|---|---|---|---|---|---|'
    foreach ($s in $storeByFolder) { A "| ``$($s.folder)`` | $($s.files) | $(Format-Bytes $s.bytes) | $($s.status) | $($s.source) | $($s.why -replace '\|', '/') |" }
} else { A 'The project has no store content.' }
A ''
A '## Integrity'
A ''
A '`manifest.json` lists every file with its size and sha256. Verify with PowerShell:'
A ''
A '```'
A '$m = Get-Content manifest.json -Raw -Encoding UTF8 | ConvertFrom-Json'
A '$m.files | ? { (Get-FileHash -Algorithm SHA256 $_.path).Hash -ne $_.sha256 } | % path   # prints nothing when all files match'
A '```'
Write-Utf8 (Join-Path $stage 'README.md') $sb.ToString()

# ---------------------------------------------------------------------------------------------------------------------
# scrub (package copy only), then scan everything: names, user name, e-mails, agent mentions, git identities
# ---------------------------------------------------------------------------------------------------------------------
function Get-Rels { @(Get-ChildItem $stage -Recurse -File | ForEach-Object { $_.FullName.Substring($stage.Length + 1).Replace('\', '/') }) }
# git identities -> dev_NN (numbered by git.log): full names, name words of 4+ letters, e-mail handles
$identityTerms = New-Object System.Collections.ArrayList
$skipWords = @('claude', 'anthropic', 'agent', 'user', 'users', 'admin', 'root', 'dev', 'noreply', 'github', 'unknown')
foreach ($line in (Invoke-Git $repo @('log', '--format=%an%x09%ae%n%cn%x09%ce', $sha) | Sort-Object -Unique)) {
    $parts = "$line" -split "`t"; if ($parts.Count -lt 2) { continue }
    $nm = $parts[0].Trim(); $em = $parts[1].Trim(); if (-not $authors.ContainsKey($nm)) { continue }
    $dev = $authors[$nm]
    if ($nm -notmatch '(?i)^(claude|agent|dev_\d+)$') { [void]$identityTerms.Add(@($nm, $dev)) }
    foreach ($w in ($nm -split '[^A-Za-z0-9]+')) { if ($w.Length -ge 4 -and $skipWords -notcontains $w.ToLowerInvariant()) { [void]$identityTerms.Add(@($w, $dev)) } }
    $local = ($em -split '@')[0]; if ($local -match '\+') { $local = ($local -split '\+')[-1] }
    if ($local.Length -ge 4 -and $skipWords -notcontains $local.ToLowerInvariant()) { [void]$identityTerms.Add(@($local, $dev)) }
}
# A term with a digit is a handle (e.g. a name spelled with 0 for o): it also takes the letters/digits glued to it,
# which catches account names built on it; plain words match as whole words only.
function Get-IdentityRx([string]$t) {
    $e = [regex]::Escape($t)
    if ($t -match '\d' -and $t.Length -ge 5) { return "(?i)$WordStart$e[A-Za-z0-9]*" }
    return "(?i)$WordStart$e(?![A-Za-z0-9])"
}
$idRules = @($identityTerms | Sort-Object { - $_[0].Length } | ForEach-Object { @{ id = 'git-identity'; scope = 'all'; match = (Get-IdentityRx $_[0]); replace = $_[1] } })
$Rules = @($RulesHead) + $idRules + @($RulesTail)
$enforcedParts = @($BannedPattern, 'claude', 'anthropic', 'opus', $UserAnyRx, $EmailRx) +
    @($identityTerms | ForEach-Object { (Get-IdentityRx $_[0]) -replace '^\(\?i\)', '' })
$Enforced = New-Object System.Text.RegularExpressions.Regex(($enforcedParts -join '|'), 'IgnoreCase')
$needles = $BinNeedles; $refuse = $BinRefuse; $cats = $BinCats
# reported only (outside the package): any other user-folder paths
$leakRx = New-Object System.Text.RegularExpressions.Regex(('[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}(?!dev\b)[^\\/"\s]+|/Users/(?!dev\b)[^/"\s]+|/home/[^/"\s]+|[A-Za-z0-9._-]*' + [regex]::Escape($UserName) + '[A-Za-z0-9._-]*'), 'IgnoreCase')

$scrubReport = [ordered]@{ schema = 'scrub-report/1'; applied = (-not $NoScrub) }
$touched = @{}
if (-not $NoScrub) {
    Write-Step "scrubbing every text file of the package ($($Rules.Count) rules)"
    $hints = [string[]]@($Rules | ForEach-Object {
            $m = $_.match
            switch ($_.id) {
                'agent-trailer' { if ($m -match 'Co-Authored') { 'co-authored-by' } else { 'generated with' } }
                'banned-name' { if ($m -match '(?i)superposition') { 'superposition' } else { 'factory' } }
                'username' { $UserName }
                'email' { '@' }
                'git-identity' { '' }
                'session-path' { '' }   # no single word marks these files (the profile name may already be gone)
                default {
                    if ($m -match '(?i)anthropic' -and $m -notmatch '(?i)claude') { 'anthropic' }
                    elseif ($m -match '(?i)opus' -and $m -notmatch '(?i)claude') { 'opus' } else { 'claude' } }
            } })
    $res = [GameDeliverable.Tools]::ScrubAll($stage, [string[]](Get-Rels), [string[]]@($Rules | ForEach-Object { $_.match }),
        [string[]]@($Rules | ForEach-Object { $_.replace }), [string[]]@($Rules | ForEach-Object { $_.scope }), $hints)
    $perRule = [ordered]@{}; foreach ($k in $RuleText.Keys) { $perRule[$k] = [ordered]@{ id = $k; description = $RuleText[$k]; replacements = 0; files = 0 } }
    $filesOut = New-Object System.Collections.ArrayList
    foreach ($r in $res) {
        $byId = [ordered]@{}
        for ($i = 0; $i -lt $Rules.Count; $i++) { if ($r.Counts[$i]) { $byId[$Rules[$i].id] = [int]$byId[$Rules[$i].id] + $r.Counts[$i] } }
        foreach ($k in $byId.Keys) { $perRule[$k].replacements += $byId[$k]; $perRule[$k].files++ }
        $touched[$r.Path] = 1
        [void]$filesOut.Add([ordered]@{ path = $r.Path; replacements = $byId })
    }
    $tr = [GameDeliverable.Tools]::TrailersRemoved
    $perRule['agent-trailer'].replacements += $tr
    if ($tr) { $touched['git.log'] = 1 }
    # Gameplay bundle manifests: refresh the entries of rewritten files.
    foreach ($bm in Get-ChildItem $gpDir -Recurse -Filter manifest.json -File) {
        $bdir = $bm.DirectoryName; $relDir = $bdir.Substring($stage.Length + 1).Replace('\', '/')
        $mj = Read-JsonFile $bm.FullName; $files = Get-Prop $mj 'files'; if (-not $files) { continue }
        $changed = $false
        foreach ($p in $files.PSObject.Properties) {
            if ($touched.ContainsKey("$relDir/$($p.Name)")) {
                $fp = Join-Path $bdir $p.Name.Replace('/', '\'); $p.Value.sha256 = [GameDeliverable.Tools]::HashFile($fp); $p.Value.bytes = (Get-Item $fp).Length; $changed = $true
            }
        }
        if ($changed) { Write-JsonFile $bm.FullName $mj; $touched["$relDir/manifest.json"] = 1 }
    }
    $scrubReport.rules = @($perRule.Values)
    $scrubReport.git_log = [ordered]@{ commit_message_trailer_lines_removed = $tr; identities_numbered = $authors.Count }
    $scrubReport.files_touched_count = $touched.Count
    $scrubReport.files_touched = @($filesOut)
    $scrubReport.gameplay_manifests = 'entries of rewritten bundle files carry the new bytes and sha256'
    Write-Step "scrubbed $($touched.Count) files: $(@($perRule.Values | Where-Object { $_.replacements } | ForEach-Object { "$($_.id) $($_.replacements)" }) -join ', ')"
}
Write-Step 'scanning every file (paths, text; binaries ASCII/UTF-16)'
$leaks = New-Object 'System.Collections.Generic.List[GameDeliverable.Hit]'
$scan = [GameDeliverable.Tools]::Scan($stage, [string[]](Get-Rels), $Enforced, $leakRx, $leaks, 20, [string[]]$needles, [bool[]]$refuse, [string[]]$cats)
Set-ReviewedHits $scan $stage
$hits = @($scan | Where-Object { $_.Kind -notlike 'binary-info*' -and $_.Kind -notlike 'allowed*' })
if ($pendingClean) {   # -PendingCleanBuild tolerates the account name inside Build/ only (marked as pending); elsewhere it blocks
    $hits = @($hits | Where-Object { -not ($_.Kind -like 'binary-*' -and $_.Text -like 'username:*' -and $_.Path -like 'Build/*') })
}
$binInfo = @($scan | Where-Object { $_.Kind -like 'binary-info*' })
$allowedHits = @($scan | Where-Object { $_.Kind -like 'allowed*' })
# Counts only inside the package (the words themselves would put the terms into its text); the full list goes next to
# the package for review: <name>.allowlisted.tsv.
$scrubReport.allowlisted_hits = [ordered]@{
    note     = 'audio codec symbols and engine locale ids allowed by an exact allowlist, short terms inside compressed media stream payloads, plus reviewed exceptions; every other hit blocks'
    total    = $allowedHits.Count
    reviewed = @($allowedHits | Where-Object Kind -eq 'allowed-reviewed').Count
    media_stream = @($allowedHits | Where-Object Kind -like 'allowed-stream*').Count
    files    = @($allowedHits | ForEach-Object Path | Sort-Object -Unique).Count
    in_build = @($allowedHits | Where-Object { $_.Path -like 'Build/*' }).Count
}
$alTsv = Join-Path $gameOut "$name.allowlisted.tsv"
$asb = New-Object System.Text.StringBuilder; [void]$asb.Append("path`tkind`tline_or_offset`tword`n")
foreach ($h in ($allowedHits | Sort-Object Path, Where)) { [void]$asb.Append("$($h.Path)`t$($h.Kind)`t$($h.Where)`t$(($h.Text -split ':', 2)[-1])`n") }
Write-Utf8 $alTsv $asb.ToString()
$scrubReport.binary_files_with_findings = @($binInfo | Group-Object Path | ForEach-Object { [ordered]@{ path = $_.Name
            categories = @($_.Group | ForEach-Object { ($_.Text -split ':', 2)[0] } | Sort-Object -Unique); encodings = @($_.Group | ForEach-Object { $_.Kind -replace '^binary-info-', '' } | Sort-Object -Unique)
            hits = $_.Count; capped = ($_.Count -ge 20) } })
$scrubReport.binary_note = 'binary files are never edited; findings are listed by category only (username, agent-name)'
$scrubReport.verification = [ordered]@{ text_and_path_hits_after_scrub = @($hits | Where-Object { $_.Kind -notlike 'binary*' }).Count
    binary_banned_name_hits = @($hits | Where-Object { $_.Kind -like 'binary*' }).Count; binary_files_reported = @($scrubReport.binary_files_with_findings).Count }
Write-JsonFile (Join-Path $stage 'scrub-report.json') $scrubReport
$leakTsv = Join-Path $gameOut "$name.leaks.tsv"
$leakSummary = $leaks | Group-Object { $_.Text.ToLowerInvariant() } | Sort-Object Count -Descending
$lsb = New-Object System.Text.StringBuilder; [void]$lsb.Append("count`tfiles`tvalue`texample_file`n")
foreach ($g in $leakSummary) { [void]$lsb.Append("$($g.Count)`t$(@($g.Group | ForEach-Object Path | Sort-Object -Unique).Count)`t$($g.Name)`t$($g.Group[0].Path)`n") }
foreach ($g in ($binInfo | Group-Object { ($_.Text -split ':', 2)[0] })) { [void]$lsb.Append("$($g.Count)`t$(@($g.Group | ForEach-Object Path | Sort-Object -Unique).Count)`tbinary:$($g.Name)`t$($g.Group[0].Path)`n") }
Write-Utf8 $leakTsv $lsb.ToString()

$errors = @($problems | Where-Object { $_ -like 'error:*' })
if ($hits.Count -or $errors.Count) {
    $hitTsv = Join-Path $gameOut "$name.refused-hits.tsv"
    $hsb = New-Object System.Text.StringBuilder; [void]$hsb.Append("path`tkind`tline_or_offset`ttext`n")
    foreach ($h in $hits) { [void]$hsb.Append("$($h.Path)`t$($h.Kind)`t$($h.Where)`t$($h.Text)`n") }
    foreach ($e in $errors) { [void]$hsb.Append("-`terror`t-`t$e`n") }
    Write-Utf8 $hitTsv $hsb.ToString()
    $byFile = $hits | Group-Object Path | Sort-Object Count -Descending
    Write-Host ''
    Write-Host "REFUSED: $($hits.Count) hit(s) in $(@($byFile).Count) file(s)$(if ($errors.Count) { ", $($errors.Count) error(s)" }). Nothing was published." -ForegroundColor Red
    foreach ($g in ($byFile | Select-Object -First 25)) {
        $k = @($g.Group | ForEach-Object Kind | Sort-Object -Unique) -join ','
        $eg = ($g.Group[0].Text) -replace '\s+', ' '; if ($eg.Length -gt 100) { $eg = $eg.Substring(0, 100) }
        Write-Host ("  {0,5}  {1,-14} {2}  e.g. {3}" -f $g.Count, $k, $g.Name, $eg)
    }
    if (@($byFile).Count -gt 25) { Write-Host "  ... $(@($byFile).Count - 25) more files" }
    foreach ($e in ($errors | Select-Object -First 10)) { Write-Host "  $e" }
    Write-Host "  all hits: $hitTsv"
    Write-Host "  sizes (staged): $(@('UEProject','Build','Gameplay','History') | ForEach-Object { "$_ $(Format-Bytes (& $sizeOf (Join-Path $stage $_)))" })"
    if ($KeepRefused) { Rename-Item $stage (Split-Path "$final.refused" -Leaf); Write-Host "  staged output kept at $final.refused" }
    else { Remove-Item -Recurse -Force $stage }
    exit 2
}

# ---------------------------------------------------------------------------------------------------------------------
# manifest.json, publish, zip
# ---------------------------------------------------------------------------------------------------------------------
Write-Step 'hashing every file for manifest.json'
$all = [GameDeliverable.Tools]::HashAll($stage)
$byPath = New-Object 'System.Collections.Generic.Dictionary[string,string]'
foreach ($f in $all) { $byPath[$f.Path] = $f.Sha256 }
foreach ($f in $exported) {   # git blobs and Git LFS objects must arrive unchanged (unless scrubbed)
    $k = "UEProject/$($f.Path)"
    if (-not $touched.ContainsKey($k) -and $byPath.ContainsKey($k) -and $byPath[$k] -ne $f.Sha256) { throw "sha256 mismatch after export: $($f.Path)" }
}
$sections = [ordered]@{}
foreach ($f in $all) { $top = ($f.Path -split '/')[0]; if ($f.Path -notmatch '/') { $top = '(top level)' }; $sections[$top] = [long]$sections[$top] + $f.Bytes }
$manifest = [ordered]@{
    package = $name; game = $Game; project = $info.ProjectName; engine = $engine
    version = $(if ($Version) { $Version } else { $null }); release_tag = $releaseTag
    status = $(if ($pendingClean) { 'pending clean build' } else { 'complete' })
    screenshots = @($shots | ForEach-Object { "Screenshots/$($_.file)" })
    commit = $sha; commit_time = $commitTime; commits = $commitCount; variant = $variant
    created = (Get-IsoNow); tool_version = $ToolVersion
    store_content = [ordered]@{ included_files = @($storeRows | Where-Object status -eq 'included').Count; dropped_files = @($storeRows | Where-Object status -eq 'dropped').Count
        dropped_bytes = [long](($storeRows | Where-Object status -eq 'dropped' | ForEach-Object { $_.f.Bytes } | Measure-Object -Sum).Sum) }
    build = $buildInfo; gameplay_runs = @($runs | ForEach-Object run_id); history = $histStats
    scrub = [ordered]@{ applied = (-not $NoScrub); files_touched = $touched.Count; report = 'scrub-report.json' }
    totals = [ordered]@{ files = $all.Count; bytes = [long](($all | Measure-Object Bytes -Sum).Sum) }
    files = @($all | ForEach-Object { [ordered]@{ path = $_.Path; bytes = $_.Bytes; sha256 = $_.Sha256 } })
}
Write-JsonFile (Join-Path $stage 'manifest.json') $manifest
# (scrub-report.json lists the words allowed in binaries, so it is checked with the binary allowlist)
$textAllow = [GameDeliverable.Tools]::Allow; [GameDeliverable.Tools]::Allow = [GameDeliverable.Tools]::AllowBin
$mHits = @([GameDeliverable.Tools]::Scan($stage, [string[]]@('manifest.json', 'scrub-report.json'), $Enforced, $null, $leaks, 5, [string[]]@(), [bool[]]@(), [string[]]@()) |
        Where-Object { $_.Kind -notlike 'allowed*' })
[GameDeliverable.Tools]::Allow = $textAllow
if ($mHits.Count) { Remove-Item -Recurse -Force $stage; throw "manifest.json contains a banned name: $($mHits[0].Text)" }
for ($try = 1; ; $try++) {   # a virus scanner or indexer may still hold a just-written file for a moment
    try { Rename-Item $stage (Split-Path $final -Leaf) -ErrorAction Stop; break }
    catch { if ($try -ge 20) { throw "could not rename $stage to $final after $try tries: $($_.Exception.Message)" }; Start-Sleep -Seconds 3 }
}
$zipBytes = $null; $zipEntries = $null
if (-not $NoZip) {
    Write-Step "zipping ($ZipLevel)"
    $zipEntries = [GameDeliverable.Tools]::Zip($final, $zipPath, $name, $ZipLevel)
    if ($zipEntries -ne ($all.Count + 1)) { throw "zip has $zipEntries entries, expected $($all.Count + 1)" }
    $zipBytes = (Get-Item $zipPath).Length
}
$folderBytes = $manifest.totals.bytes + (Get-Item (Join-Path $final 'manifest.json')).Length
Add-JsonLine (Join-Path $gameOut 'package-log.jsonl') ([ordered]@{
        time = (Get-IsoNow); package = $name; commit = $sha; variant = $variant; status = $manifest.status; version = $Version; folder = $final; folder_bytes = $folderBytes
        zip = $(if ($zipBytes) { $zipPath }); zip_bytes = $zipBytes; files = $all.Count + 1; sections = $sections
        store_dropped_files = $manifest.store_content.dropped_files; gameplay_runs = $runs.Count; build = "$($buildSel.source) $($buildSel.config)"
        scrubbed_files = $touched.Count; warnings = @($warnings); notes = @($problems); leaks_tsv = $leakTsv; duration_s = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    })
Write-Host ''
Write-Host "OK  $final" -ForegroundColor Green
foreach ($k in $sections.Keys) { Write-Host ("  {0,-20} {1,12}" -f $k, (Format-Bytes $sections[$k])) }
Write-Host ("  {0,-20} {1,12}  ({2} files)" -f 'folder total', (Format-Bytes $folderBytes), ($all.Count + 1))
if ($zipBytes) { Write-Host ("  {0,-20} {1,12}  {2}" -f 'zip', (Format-Bytes $zipBytes), $zipPath) }
Write-Host "  store content: $($manifest.store_content.included_files) files included, $($manifest.store_content.dropped_files) dropped ($(Format-Bytes $manifest.store_content.dropped_bytes))"
foreach ($w in $warnings) { Write-Host "  warning: $w" -ForegroundColor Yellow }
foreach ($p in ($problems | Select-Object -First 10)) { Write-Host "  $p" }
Write-Host "  leak scan (not enforced): $($leaks.Count) finding(s), $(@($leakSummary).Count) distinct value(s) -> $leakTsv"
Write-Host "  $([math]::Round(((Get-Date) - $t0).TotalMinutes, 1)) min"

# -Dataset: build the dataset layout v1.1 delivery (tools\package-dataset.ps1) from this package.
# (always with store content).
if ($Dataset) {
    $fullPkg = if ($WithoutStoreContent) { $final -replace '_nostore$', '' } else { $final }
    if (-not (Test-Path $fullPkg)) { throw "-Dataset needs the full package $fullPkg (package without -WithoutStoreContent first)" }
    $da = @($Game, '-Package', $fullPkg); if ($Version) { $da += @('-Version', $Version) }
    if ($ReplayScripts) { $da += @('-ReplayScripts', $ReplayScripts) }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'package-dataset.ps1') @da
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
}

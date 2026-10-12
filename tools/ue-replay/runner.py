"""prepare / run / dump / status for the Unreal creation replay (see docs/ue-replay.md).

The replay project is a private clone of the game repo (objects shared, Git LFS reading the game's own store), checked
out at the first commit. `run` walks the ledger's windows: inputs from the commit, script texts as they were when each
script ran, initial-asset drops and shell steps at their recorded positions, an editor build when the code changed,
every editor-script run headless through ue-heavy.ps1, then the boundary check. Resumable: work/state.json; a
work/STOP file pauses it cleanly between steps.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

import ue_replay

HEAVY = os.path.join(ue_replay.machine_root(), "tools", "ue-heavy.ps1")   # GF_ROOT, the machine config, else ~/Work
HERE = os.path.dirname(os.path.abspath(__file__))
DUMP = os.path.join(HERE, "editor", "ue_dump.py").replace("\\", "/")


# ------------------------------------------------------------------------------------------------ helpers
def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def jappend(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def git(repo, *args, check=True, binary=False, env=None, inp=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", "-c", "core.autocrlf=false"] + list(args),
                       capture_output=True, env=e, input=inp)
    if check and r.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args[:3]), r.stderr.decode("utf-8", "replace")[-800:]))
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def heavy_script():
    """ue-heavy.ps1 and its extra switches. GF_HEAVY_LOW=1 (the live per-commit replay): low priority, -Low, which the
    installed copy may not know yet; this checkout's machine/tools copy shares its machine-wide slots."""
    if os.environ.get("GF_HEAVY_LOW") != "1":
        return HEAVY, ""
    for p in (HEAVY, os.path.join(HERE, "..", "..", "machine", "tools", "ue-heavy.ps1")):
        try:
            if "[switch]$Low" in open(p, encoding="utf-8-sig").read():
                return os.path.abspath(p), " -Low"
        except OSError:
            pass
    return HEAVY, ""


def heavy(label, argv, log_path=None, env=None):
    """Run one engine process through ue-heavy.ps1 (machine-wide slots); returns (exit code, seconds)."""
    script, extra = heavy_script()
    cmd = "& %s -Label %s%s -- %s; exit $LASTEXITCODE" % (ps_quote(script), ps_quote(label), extra, " ".join(ps_quote(a) for a in argv))
    e = dict(os.environ)
    if env:
        e.update(env)
    t0 = time.time()
    out = open(log_path + ".console", "wb") if log_path else subprocess.DEVNULL
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                           stdout=out, stderr=subprocess.STDOUT, env=e)
    finally:
        if log_path:
            out.close()
    return r.returncode, round(time.time() - t0, 1)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1_file(p):
    with open(p, "rb") as f:
        data = f.read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def scan(root, sub="Content"):
    """{repo path: (size, mtime_ns)} of every file under root/sub."""
    out = {}
    base = os.path.join(root, sub)
    for dp, _, files in os.walk(base):
        for fn in files:
            fp = os.path.join(dp, fn)
            st = os.stat(fp)
            out[os.path.relpath(fp, root).replace("\\", "/")] = (st.st_size, st.st_mtime_ns)
    return out


def diff_scan(a, b):
    added = sorted(p for p in b if p not in a)
    deleted = sorted(p for p in a if p not in b)
    changed = sorted(p for p in b if p in a and a[p] != b[p])
    return added, changed, deleted


def tree_ids(repo, sha, prefix=""):
    """{path: ('lfs', sha256) | ('git', sha1)} for files of a commit (LFS pointers resolved to their oid)."""
    out = {}
    small = []
    for line in git(repo, "ls-tree", "-r", "-l", sha, "--", prefix or ".").splitlines():
        meta, path = line.split("\t", 1)
        mode, typ, oid, size = meta.split()
        if typ != "blob":
            continue
        out[path] = ("git", oid)
        if size != "-" and int(size) < 300:
            small.append((path, oid))
    if small:
        data = git(repo, "cat-file", "--batch", inp="\n".join(o for _, o in small).encode() + b"\n", binary=True)
        pos = 0
        for path, oid in small:
            nl = data.index(b"\n", pos)
            hdr = data[pos:nl].split()
            n = int(hdr[2])
            body = data[nl + 1:nl + 1 + n]
            pos = nl + 1 + n + 1
            if body.startswith(b"version https://git-lfs.github.com/spec/v1"):
                for ln in body.split(b"\n"):
                    if ln.startswith(b"oid sha256:"):
                        out[path] = ("lfs", ln[len(b"oid sha256:"):].decode())
    return out


def file_matches(fp, ident):
    if not os.path.exists(fp):
        return False
    kind, oid = ident
    return (sha256_file(fp) if kind == "lfs" else git_blob_sha1_file(fp)) == oid


# ------------------------------------------------------------------------------------------------ paths
class Ctx:
    def __init__(self, cfg):
        self.cfg = cfg
        self.repo = cfg["repo"]
        self.proj = cfg["project_dir"]
        self.work = cfg["work_dir"]
        self.uproject = os.path.join(self.proj, cfg["uproject"])
        self.engine = cfg["engine"]
        self.editor_cmd = os.path.join(self.engine, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe")
        self.ledger = jload(os.path.join(self.work, "ledger.json"))
        self.state_path = os.path.join(self.work, "state.json")
        self.state = jload(self.state_path, {"window": 0, "done": [], "built": None, "provenance": {}})
        self.logs = os.path.join(self.work, "logs")
        os.makedirs(self.logs, exist_ok=True)

    def save(self):
        jdump(self.state_path, self.state)

    def p(self, rel):
        return os.path.join(self.proj, rel)


# ------------------------------------------------------------------------------------------------ prepare
def clone_at(cfg, dest, sha):
    if os.path.exists(os.path.join(dest, ".git")):
        return False
    repo = cfg["repo"]
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", repo, dest], check=True)
    for k, v in (("core.autocrlf", "false"), ("core.eol", "lf"), ("lfs.storage", repo.replace("\\", "/") + "/.git/lfs"),
                 ("lfs.fetchrecentalways", "false"), ("remote.origin.url", repo.replace("\\", "/"))):
        git(dest, "config", k, v)
    git(dest, "checkout", "-q", "--detach", sha)
    return True


def external_dir(ctx, e):
    return os.path.join(ctx.work, "external", e["id"])


def build_externals(ctx):
    """External sources with a "rebuild" recipe (the builder unpacked library archives into a scratch folder that no
    longer exists): {"unzip": [{"zip": "<glob>", "to": "<subdir>", "exclude": ["*Cavity*", ...]}]} rebuilds the folder
    under work/external/<id>/; runs whose env names the recorded folder get this one (map_external_env)."""
    import fnmatch
    import glob
    import zipfile
    for e in ctx.cfg.get("external_sources", []):
        rb = e.get("rebuild")
        if not rb:
            continue
        d = external_dir(ctx, e)
        if os.path.isdir(d):
            continue
        tmp = d + ".partial"
        shutil.rmtree(tmp, ignore_errors=True)
        n = 0
        for u in rb.get("unzip", []):
            zips = sorted(glob.glob(u["zip"]))
            if not zips:
                sys.exit("external source %s: no archive matches %s" % (e["id"], u["zip"]))
            for z in zips:
                with zipfile.ZipFile(z) as zf:
                    for m in zf.namelist():
                        if m.endswith("/") or any(fnmatch.fnmatch(m, x) for x in u.get("exclude", [])):
                            continue
                        zf.extract(m, os.path.join(tmp, u.get("to", "")))
                        n += 1
        os.replace(tmp, d)
        print("external source %s rebuilt: %d files -> %s" % (e["id"], n, d))


def external_target(ctx, e):
    """Where an external source is on this machine: its rebuilt folder, else its settings path."""
    return (external_dir(ctx, e) if e.get("rebuild") else e.get("path") or "").replace("\\", "/")


def map_external_env(ctx, env):
    """Env values naming an external source's recorded location (settings "recorded": a template with {home}/{root}/*,
    as the recording has it on the machine the game was built on) point at the source on this machine."""
    for e in ctx.cfg.get("external_sources", []):
        if not e.get("recorded"):
            continue
        rx = ue_replay.recorded_path_regex(e["recorded"])
        loc = external_target(ctx, e)
        for k, v in env.items():
            m = rx.match(v)
            if m:
                env[k] = loc + v[m.end():].replace("\\", "/")
    return env


def remap_script_paths(ctx):
    """External sources with "remap_scripts": recorded scripts that open the recorded location by an absolute path
    (island: import_art_v1.py reads the scout's path map from a notes folder) get this machine's location for the run.
    Returns [(file, original bytes)] to put back after the run (files outside Content are compared byte for byte)."""
    srcs = [(ue_replay.recorded_path_regex(e["recorded"]), external_target(ctx, e))
            for e in ctx.cfg.get("external_sources", []) if e.get("remap_scripts") and e.get("recorded")]
    if not srcs:
        return []
    changed = []
    for dp, dns, fns in os.walk(ctx.p("Scripts")):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dp, fn)
            with open(fp, "rb") as f:
                b = f.read()
            t = b.decode("utf-8", "replace")
            t2 = t
            for rx, loc in srcs:
                t2 = rx.sub(lambda m: loc, t2)
            if t2 != t:
                with open(fp, "wb") as f:
                    f.write(t2.encode("utf-8"))
                changed.append((fp, b))
    return changed


def cmd_prepare(cfg, a):
    ctx = Ctx(cfg)
    if ctx.ledger is None:
        sys.exit("run `ledger` first")
    first = ctx.ledger["first"]
    t0 = time.time()
    made = clone_at(cfg, ctx.proj, first)
    st = git(ctx.proj, "status", "--short")
    print("project %s at %s (%s, %.0f s); status: %s" % (ctx.proj, first[:10], "cloned" if made else "exists",
                                                          time.time() - t0, st.strip() or "clean"))
    if made or not ctx.state.get("provenance"):
        prov = {p: "git:" + first[:10] for p in scan(ctx.proj)}
        ctx.state["provenance"] = prov
        ctx.save()
    build_externals(ctx)
    manifest = initial_assets_manifest(cfg, ctx)
    jdump(os.path.join(ctx.work, "initial-assets.manifest.json"), manifest)
    print("initial assets: %d files, %.2f GB" % (manifest["counts"]["files"], manifest["counts"]["bytes"] / 1e9))


def initial_assets_manifest(cfg, ctx):
    """Store packs dropped in and external source files the scripts read, with sha256 per file."""
    files = []
    for d in cfg.get("asset_drops", []):
        for it in d["items"]:
            if it.get("from_git"):
                ref = it.get("ref") or ctx.ledger["final"]
                for fp, size, sha in git_tree_files(cfg["repo"], ref, it["from_git"]):
                    files.append({"role": "store_pack", "drop": d["id"], "pack": it.get("pack"), "path": fp, "bytes": size,
                                  "sha256": sha, "source": "commit %s (git/LFS)" % ref[:10]})
                continue
            if os.path.isfile(it["from"]):
                files.append({"role": "store_pack", "drop": d["id"], "pack": it.get("pack"), "path": it["to"],
                              "bytes": os.path.getsize(it["from"]), "sha256": sha256_file(it["from"])})
                continue
            for dp, _, fns in os.walk(it["from"]):
                for fn in fns:
                    fp = os.path.join(dp, fn)
                    rel = os.path.relpath(fp, it["from"]).replace("\\", "/")
                    files.append({"role": "store_pack", "drop": d["id"], "pack": it.get("pack"), "path": it["to"] + "/" + rel,
                                  "bytes": os.path.getsize(fp), "sha256": sha256_file(fp)})
    ext = []
    for e in cfg.get("external_sources", []):
        ext.append({"id": e["id"], "role": e["role"], "root": "<external:%s>" % e["id"],
                    **({"rebuild": e["rebuild"]} if e.get("rebuild") else {})})
        d = external_dir(ctx, e)
        if e.get("rebuild") and os.path.isdir(d):
            for dp, _, fns in os.walk(d):
                for fn in fns:
                    fp = os.path.join(dp, fn)
                    files.append({"role": "external_source", "source": e["id"],
                                  "path": "<external:%s>/%s" % (e["id"], os.path.relpath(fp, d).replace("\\", "/")),
                                  "bytes": os.path.getsize(fp), "sha256": sha256_file(fp)})
    return {"schema": "ue-replay.initial-assets/v1", "game": cfg["game"], "first_commit": ctx.ledger["first"],
            "drops": [{k: v for k, v in d.items() if k != "match"} for d in cfg.get("asset_drops", [])],
            "external_sources": ext, "files": files,
            "counts": {"files": len(files), "bytes": sum(f["bytes"] for f in files)}}


# ------------------------------------------------------------------------------------------------ steps
def apply_inputs(ctx, w):
    """Files outside Content/ as the commit has them (adds/modifies via checkout, deletes removed)."""
    am = [x["path"] for x in w["inputs"] if x["status"] in "AMT" and x["path"] != "workflow.jsonl"]
    dl = [x["path"] for x in w["inputs"] if x["status"] == "D"]
    if am:
        git(ctx.proj, "checkout", w["sha"], "--pathspec-from-file=-", inp="\n".join(am).encode("utf-8"))
        fix_lfs_pointers(ctx, am)
    for p in dl:
        fp = ctx.p(p)
        if os.path.exists(fp):
            os.remove(fp)
    # workflow.jsonl: the commit's version (scripts append to it; their rows are cut out per run)
    if any(x["path"] == "workflow.jsonl" for x in w["inputs"]):
        data = git(ctx.proj, "show", "%s:workflow.jsonl" % w["sha"], binary=True)
        with open(ctx.p("workflow.jsonl"), "wb") as f:
            f.write(data)
    return len(am), len(dl)


def code_changed(w):
    return any(x["path"].startswith(("Source/", "Plugins/")) or x["path"].endswith((".uproject", ".Build.cs", ".Target.cs"))
               for x in w["inputs"])


def apply_run_code(ctx, w, want):
    """Make the project's code files what the run needs: the ledger's run-time texts (want: path -> blob sha256 or
    "absent") over the window's commit; files an earlier run changed and this one does not go back to the commit.
    Returns True when a file changed (the editor must be rebuilt)."""
    have = ctx.state.get("code_applied") or {}
    if want == have:
        return False
    in_tree = None
    for p in sorted(set(have) | set(want)):
        fp = ctx.p(p)
        if p in want:
            if want[p] == "absent":
                if os.path.exists(fp):
                    os.remove(fp)
            else:
                with open(os.path.join(ctx.work, "blobs", want[p]), "rb") as f:
                    data = f.read()
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                with open(fp, "wb") as f:
                    f.write(data)
        else:
            if in_tree is None:
                in_tree = set(git(ctx.proj, "ls-tree", "-r", "--name-only", w["sha"]).splitlines())
            if p in in_tree:
                git(ctx.proj, "checkout", w["sha"], "--", p)
            elif os.path.exists(fp):
                os.remove(fp)
    ctx.state["code_applied"] = dict(want)
    ctx.state["code_dirty"] = True
    ctx.save()
    return True


def build_editor(ctx, label):
    cfg = ctx.cfg
    log = os.path.join(ctx.logs, "build_%s.log" % label)
    bat = os.path.join(ctx.logs, "build_%s.bat" % label)
    # UBT's own log goes to a file of this build (-Log=): the default %LOCALAPPDATA%\UnrealBuildTool\Log.txt is shared
    # by every UBT on the machine, and a second build starting while one runs fails moving it ("being used by another
    # process"; rts-command w10)
    ubt_log = os.path.join(ctx.logs, "ubt_%s.txt" % label)
    with open(bat, "w", encoding="utf-8") as f:
        f.write('@echo off\r\ncall "%s\\Engine\\Build\\BatchFiles\\Build.bat" %s Win64 Development -Project="%s" -WaitMutex '
                '-NoHotReloadFromIDE -Log="%s" > "%s" 2>&1\r\nexit /b %%ERRORLEVEL%%\r\n' % (
                    cfg["engine"].replace("/", "\\"), cfg["editor_target"], ctx.uproject.replace("/", "\\"), ubt_log, log))
    code, secs = heavy("ue-replay %s build %s" % (cfg["game"], label), [bat])
    if code != 0 and "being used by another process" in open(log, encoding="utf-8", errors="replace").read():
        # a file another build holds (UBT logs, makefiles): once more after a pause
        time.sleep(60)
        os.replace(log, log[:-4] + ".locked.log")
        code, secs2 = heavy("ue-replay %s build %s (retry)" % (cfg["game"], label), [bat])
        secs += secs2
    return code, secs, log


def materialize_scripts(ctx, run):
    """Script files as they stood when the run started (ledger texts); unknown ones keep the commit's version."""
    n = 0
    for p, h in run["texts"].items():
        src = os.path.join(ctx.work, "blobs", h)
        with open(src, "rb") as f:
            data = f.read()
        fp = ctx.p(p)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "wb") as f:
            f.write(data)
        n += 1
    # files the recording cannot rebuild at this point (e.g. after a perl -i edit) get the window's commit text; left
    # alone they kept whatever an earlier run of the window had written (stealth: build_level_L01.py imported the
    # pre-perl level_kit.py, whose spawn() fails, and L01 got 16 of its 150 actors)
    sha = run.get("window_sha") or ctx.state.get("window_sha")
    for p in run.get("unknown") or []:
        if not sha:
            break
        try:
            data = git(ctx.proj, "show", "%s:%s" % (sha, p), binary=True)
        except Exception:
            continue
        fp = ctx.p(p)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "wb") as f:
            f.write(data)
        n += 1
    return n


def external_script(ctx, run):
    """A script outside the game repo (e.g. a pipeline tool): its version at the run time from its own git history."""
    path = run["script"]
    d = os.path.dirname(path)
    top = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        return path, "current_file"
    top = top.stdout.strip()
    rel = os.path.relpath(path, top).replace("\\", "/")
    sha = git(top, "log", "-1", "--format=%H", "--before=" + run["start"], "--", rel).strip()
    if not sha:
        return path, "current_file"
    data = git(top, "show", "%s:%s" % (sha, rel), binary=True)
    out = os.path.join(ctx.work, "external", sha[:10], os.path.basename(rel))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    return out.replace("\\", "/"), "%s@%s" % (rel, sha[:10])


def run_editor_script(ctx, run):
    cfg = ctx.cfg
    if run["script"].startswith("Scripts/") or not os.path.isabs(run["script"]):
        script = ctx.p(run["script"]).replace("\\", "/")
        version = run["script_version"]
    else:
        script, version = external_script(ctx, run)
    env = {k: v.replace("{project}", ctx.proj) for k, v in cfg.get("script_env", {}).items()}
    # values the builder's shell expanded ($USERPROFILE, %USERPROFILE%, ...) as the recording machine had them
    env.update({k: os.path.expandvars(v) for k, v in (run.get("env") or {}).items()})
    build_externals(ctx)
    map_external_env(ctx, env)
    if run.get("reason") and cfg.get("reason_env"):
        env[cfg["reason_env"]] = run["reason"]
    if cfg.get("args_env") and run.get("via_wrapper"):
        # the game's wrapper hands its extra arguments to the script in an environment variable (rally: RR_ARGS)
        env[cfg["args_env"]] = run.get("args") or ""
        run = dict(run, args="")
    log = os.path.join(ctx.logs, "runs", "%s_%s.log" % (run["id"], os.path.splitext(os.path.basename(run["script"]))[0]))
    os.makedirs(os.path.dirname(log), exist_ok=True)
    if run.get("mode") not in (None, "", "commandlet"):   # "editor", or a wrapper's own name for it (e.g. "gui")
        # the builder ran it in a full (headless) editor, not the commandlet: -ExecutePythonScript, quits when done
        argv = [ctx.editor_cmd, ctx.uproject, "-ExecutePythonScript=%s" % script] + cfg.get("editor_args", [])
        if not any(x.lower() == "-nullrhi" for x in argv):
            argv.append("-nullrhi")
        argv.append("-abslog=" + log)
    else:
        sarg = "-script=%s%s" % (script, (" " + run["args"]) if run.get("args") else "")
        argv = [ctx.editor_cmd, ctx.uproject, "-run=pythonscript", sarg] + cfg.get("editor_args", []) + ["-abslog=" + log]
    code, secs = heavy("ue-replay %s %s %s" % (cfg["game"], run["id"], os.path.basename(run["script"])), argv, env=env)
    return code, secs, log, version


def engine_crashed(log):
    """The editor process died on an engine assertion/critical error (not a Python exception in the script)."""
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            t = f.read()
    except OSError:
        return False
    return "=== Critical error: ===" in t or "appError called" in t


def wf_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [l for l in f.read().splitlines() if l.strip()]


def dump_maps(ctx, maps, out, assets=False, t3d=True, label="dump", project=None, packages=None):
    """Structure dump through the editor; packages: only these assets (a list of package names), maps: a list or "all"."""
    proj = project or ctx.proj
    up = os.path.join(proj, ctx.cfg["uproject"])
    log = os.path.join(ctx.logs, "%s.log" % label)
    sarg = "-script=%s --out %s --roots %s --map-roots %s --maps %s --assets %s --t3d %s --module %s" % (
        DUMP, out.replace("\\", "/"), ",".join(ctx.cfg.get("content_roots", ["/Game"])),
        ",".join(ctx.cfg.get("map_roots", ctx.cfg.get("content_roots", ["/Game"]))), (",".join(maps) or "none") if isinstance(maps, list) else maps,
        "1" if assets else "0", "1" if t3d else "0", ctx.cfg.get("module", os.path.splitext(ctx.cfg["uproject"])[0]))
    if packages is not None:
        lst = out.rstrip("/\\") + ".packages.txt"
        os.makedirs(os.path.dirname(lst), exist_ok=True)
        with open(lst, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(p + "\n" for p in packages))
        sarg += " --packages %s" % lst.replace("\\", "/")
    argv = [ctx.editor_cmd, up, "-run=pythonscript", sarg] + ctx.cfg.get("editor_args", []) + ["-abslog=" + log]
    return heavy("ue-replay %s %s" % (ctx.cfg["game"], label), argv)


def host_python(ctx, step):
    """shell step 'host-python script args...': a builder's host-side Python script (not an editor script) run in the
    replay project with the engine's Python, cwd under the project (e.g. stealth's prune_apply.py deleting pack files).
    The script must address the project relative to itself or its cwd; one that names the live game repo is refused."""
    cwd = ctx.p(step.get("cwd", ""))
    script = os.path.join(cwd, step["argv"][1])
    text = open(script, encoding="utf-8", errors="replace").read()
    live = ctx.cfg["repo"].replace("\\", "/").lower()
    if live in text.replace("\\\\", "/").replace("\\", "/").lower():
        raise SystemExit("host-python %s names the live game repo; refusing" % step["argv"][1])
    py = os.path.join(ctx.engine, "Engine", "Binaries", "ThirdParty", "Python3", "Win64", "python.exe")
    r = subprocess.run([py, script] + list(step["argv"][2:]), cwd=cwd, capture_output=True, text=True, errors="replace")
    with open(os.path.join(ctx.logs, "host_%s.log" % os.path.splitext(os.path.basename(script))[0]), "a", encoding="utf-8") as f:
        f.write(r.stdout + r.stderr)
    if r.returncode:
        print("   host-python %s exit %s" % (step["argv"][1], r.returncode), flush=True)
    return r.returncode


def delete_paths(ctx, step):
    """shell step 'delete path...' (an rm of files the builder removed by hand, e.g. maps that no longer load), under
    cwd; paths stay inside the replay project."""
    cwd = ctx.p(step.get("cwd", ""))
    n = 0
    for rel in step["argv"][1:]:
        p = os.path.normpath(os.path.join(cwd, rel))
        if not os.path.normcase(p).startswith(os.path.normcase(os.path.normpath(ctx.proj)) + os.sep):
            raise SystemExit("shell delete outside the replay project: " + rel)
        if os.path.isdir(p):
            shutil.rmtree(p)
            n += 1
        elif os.path.exists(p):
            os.remove(p)
            n += 1
    return n


def move_merge(ctx, step):
    """shell step 'move-merge src dst' (cp -rn src/. dst/ && rm -rf src) under cwd."""
    cwd = ctx.p(step.get("cwd", ""))
    src, dst = os.path.join(cwd, step["argv"][1]), os.path.join(cwd, step["argv"][2])
    moved = 0
    if os.path.isdir(src):
        for dp, _, fns in os.walk(src):
            for fn in fns:
                s = os.path.join(dp, fn)
                d = os.path.join(dst, os.path.relpath(s, src))
                if not os.path.exists(d):
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(s, d)
                    moved += 1
        shutil.rmtree(src)
    return moved


def git_tree_files(repo, sha, path):
    """(path, bytes, sha256) of every file under path at sha; Git LFS pointers give the object's own size and oid."""
    out = []
    lines = [l for l in git(repo, "ls-tree", "-r", sha, "--", path).splitlines() if l.strip()]
    ids = [(l.split("\t", 1)[1], l.split()[2]) for l in lines]
    if not ids:
        return out
    r = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], input=("\n".join(i for _, i in ids) + "\n").encode(),
                       capture_output=True)
    data, pos = r.stdout, 0
    for fp, oid in ids:
        nl = data.index(b"\n", pos)
        size = int(data[pos:nl].split()[2])
        body = data[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
        m = re.match(rb"version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)", body)
        if m:
            out.append((fp, int(m.group(2)), m.group(1).decode()))
        else:
            out.append((fp, size, hashlib.sha256(body).hexdigest()))
    return out


LFS_PTR = re.compile(rb"version https://git-lfs.github.com/spec/v1\r?\noid sha256:([0-9a-f]{64})\r?\nsize (\d+)")


def fix_lfs_pointers(ctx, paths):
    """Files a checkout/restore left as Git LFS pointer text, replaced by the object from the game's LFS store. Happens when
    the project's .gitattributes (an earlier commit's) does not yet mark the extension as LFS: island's *.jpeg / *.tga
    pack sources restored from the final commit stayed pointers, so their texture imports failed."""
    store = None
    n = 0
    for rel in paths:
        root = ctx.p(rel)
        files = [root] if os.path.isfile(root) else [os.path.join(dp, f) for dp, _, fs in os.walk(root) for f in fs]
        for fp in files:
            try:
                if os.path.getsize(fp) > 1024:
                    continue
                with open(fp, "rb") as f:
                    m = LFS_PTR.match(f.read())
            except OSError:
                continue
            if not m:
                continue
            if store is None:
                store = (git(ctx.proj, "config", "--get", "lfs.storage").strip() or os.path.join(ctx.proj, ".git", "lfs"))
            oid = m.group(1).decode()
            obj = os.path.join(store, "objects", oid[:2], oid[2:4], oid)
            if not os.path.exists(obj):
                sys.exit("LFS object %s for %s is not in %s" % (oid, fp, store))
            shutil.copyfile(obj, fp)
            n += 1
    return n


def drop_assets(ctx, d):
    n = 0
    for it in d["items"]:
        if it.get("from_git"):
            # the pack exactly as the game committed it (e.g. a fetch script that filtered the files), restored from the
            # final commit into the working tree at the moment the builder copied it in; LFS objects from the game's store
            ref = git(ctx.proj, "rev-parse", it.get("ref") or ctx.ledger["final"]).strip()   # ref: e.g. the commit that first added the pack
            git(ctx.proj, "restore", "--source=" + ref, "--worktree", "--", it["from_git"])
            fix_lfs_pointers(ctx, [it["from_git"]])
            n += len(git(ctx.proj, "ls-tree", "-r", "--name-only", ref, "--", it["from_git"]).splitlines())
            continue
        dst = ctx.p(it["to"])
        if os.path.isfile(it["from"]):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(it["from"], dst)
            n += 1
            continue
        for dp, _, fns in os.walk(it["from"]):
            for fn in fns:
                s = os.path.join(dp, fn)
                t = os.path.join(dst, os.path.relpath(s, it["from"]))
                os.makedirs(os.path.dirname(t), exist_ok=True)
                shutil.copy2(s, t)
                n += 1
    return n


def note_outputs(ctx, before, after, tag):
    added, changed, deleted = diff_scan(before, after)
    prov = ctx.state["provenance"]
    for p in added + changed:
        prov[p] = tag
    for p in deleted:
        prov.pop(p, None)
    return {"added": added, "changed": changed, "deleted": deleted}


# ------------------------------------------------------------------------------------------------ boundary
def boundary(ctx, w):
    """Window check against the commit: content set and identity, fallbacks for content no replayed step produced."""
    ids = tree_ids(ctx.proj, w["sha"], "Content")
    prov = ctx.state["provenance"]
    res = {"fallback": [], "deleted": [], "already_deleted": [], "exact": [], "differs": [], "kept_replay": []}
    for x in w["content"]:
        p = x["path"]
        fp = ctx.p(p)
        if x["status"] == "D":
            if os.path.exists(fp):
                os.remove(fp)
                res["deleted"].append(p)
            else:
                res["already_deleted"].append(p)
            prov.pop(p, None)
            continue
        src = prov.get(p, "")
        if not os.path.exists(fp) or src.startswith(("git:", "fallback:")) or not src:
            git(ctx.proj, "checkout", w["sha"], "--", p)
            fix_lfs_pointers(ctx, [p])
            prov[p] = "fallback:" + w["sha"][:10]
            res["fallback"].append({"path": p, "reason": "missing" if not src else "not produced by a replayed step (%s)" % src})
            continue
        (res["exact"] if file_matches(fp, ids[p]) else res["differs"]).append({"path": p, "by": src})
    # content set: what the commit tree has vs what the project has
    have = set(p for p in scan(ctx.proj))
    want = set(ids)
    res["missing"] = sorted(want - have)
    res["extra"] = sorted(have - want)
    # inputs back to the commit (reconstructed script texts included)
    am = [x["path"] for x in w["inputs"] if x["status"] in "AMT"]
    for r in w["runs"]:
        am += [p for p in r["texts"] if p not in am]
    in_tree = set(git(ctx.proj, "ls-tree", "-r", "--name-only", w["sha"]).splitlines())
    am = [p for p in am if p in in_tree and p != "workflow.jsonl"]
    if am:
        git(ctx.proj, "checkout", w["sha"], "--pathspec-from-file=-", inp="\n".join(am).encode("utf-8"))
        fix_lfs_pointers(ctx, am)
    return res


# ------------------------------------------------------------------------------------------------ run
def cmd_run(cfg, a):
    ctx = Ctx(cfg)
    led = ctx.ledger
    wins = led["windows"]
    last = a.until if a.until is not None else len(wins) - 1
    runs_log = os.path.join(ctx.work, "runs.jsonl")
    win_log = os.path.join(ctx.work, "windows.jsonl")
    rows_dir = os.path.join(ctx.work, "rows")
    os.makedirs(rows_dir, exist_ok=True)
    for i in range(ctx.state["window"] + 1, last + 1):
        w = wins[i]
        t_w = time.time()
        print("== window %02d %s %s" % (i, w["sha"][:7], w["subject"][:70]), flush=True)
        done = set(ctx.state["done"])
        sid = "w%02d.inputs" % i
        if sid not in done:
            n_am, n_d = apply_inputs(ctx, w)
            ctx.state["done"].append(sid)
            ctx.save()
            print("   inputs: %d written, %d deleted" % (n_am, n_d), flush=True)
        if code_changed(w):
            ctx.state["code_dirty"] = True
            ctx.save()
        # order of the recorded tool calls (each call's end time), then position inside the call; estimated start
        # times can invert two runs of one command (a duration is printed for one and not the other)
        steps = [("run", (r["time"], r.get("pos", -1), k), r) for k, r in enumerate(w["runs"])] + \
                [("drop", (d["time"], -2, 0), d) for d in w["drops"]] + \
                [("shell", (s["time"], s.get("pos", -1) if s.get("pos", -1) >= 0 else -1, 0), s) for s in w["shell"]]
        steps.sort(key=lambda s: s[1])
        wf_path = ctx.p("workflow.jsonl")
        for kind, t, s in steps:
            sid = "w%02d.%s.%s" % (i, kind, s.get("id") or s.get("argv", ["?"])[0] + t[0][11:19])
            if sid in set(ctx.state["done"]):
                continue
            # Clean pause between steps (no engine process running): create work/STOP; delete it and run again to
            # resume from state.json. Killing the runner instead loses the record of the step in flight.
            if os.path.exists(os.path.join(ctx.work, "STOP")):
                print("   STOP file found: paused before %s (state saved; delete work/STOP and run again to resume)" % sid, flush=True)
                return 3
            rec = {"window": i, "commit": w["sha"], "kind": kind, "step": sid, "time_original": t[0], "start": now()}
            before = scan(ctx.proj)
            if kind == "drop":
                rec["files"] = drop_assets(ctx, s)
                rec["outputs"] = note_outputs(ctx, before, scan(ctx.proj), "drop:" + s["id"])
                rec["outputs"] = {k: len(v) for k, v in rec["outputs"].items()}
            elif kind == "shell":
                rec["files"] = (move_merge(ctx, s) if s["argv"][0] == "move-merge" else
                                delete_paths(ctx, s) if s["argv"][0] == "delete" else
                                host_python(ctx, s) if s["argv"][0] == "host-python" else 0)
                rec["outputs"] = {k: len(v) for k, v in note_outputs(ctx, before, scan(ctx.proj), "shell:" + sid).items()}
            else:
                r = s
                rec.update({"run": r["id"], "script": r["script"], "readonly": r["readonly"], "exit_code_original": r["exit_code"],
                            "rows_original": r["rows"]})
                # (an exit code, even 127, means the run happened: the wrapper printed it after the editor exited)
                not_run = (r.get("not_run") or
                           ("no wrapper row and no exit code: the original command stopped before this run"
                            if r.get("wrapper_rows") == 0 and r.get("exit_code") is None else None))
                if not_run and not a.force:
                    rec["skipped"] = not_run
                    print("   %s %-38s skipped: %s" % (r["id"], os.path.basename(r["script"]), not_run), flush=True)
                    jappend(runs_log, rec)
                    ctx.state["done"].append(sid)
                    ctx.save()
                    continue
                if r["readonly"] and not a.force:
                    rec["skipped"] = "read-only"
                    jappend(runs_log, rec)
                    ctx.state["done"].append(sid)
                    ctx.save()
                    continue
                # the C++ as it stood when the run started (ledger "code"), unless that text did not build before
                want = (r.get("code") or {}) if cfg.get("code_at_run_time", True) else {}
                if want and json.dumps(want, sort_keys=True) in ctx.state.get("code_failed", []):
                    want = {}
                    rec["code_at_run_time"] = "commit code (the run-time code did not build)"
                if apply_run_code(ctx, w, want):
                    rec["code_at_run_time"] = rec.get("code_at_run_time") or (
                        "%d file(s) as at the run's start" % len(want) if want else "commit code again")
                if ctx.state.get("code_dirty") or ctx.state.get("built") is None:
                    code, secs, log = build_editor(ctx, "w%02d_%s" % (i, r["id"]))
                    jappend(runs_log, {"window": i, "kind": "build", "step": "w%02d.build.%s" % (i, r["id"]), "exit_code": code,
                                       "seconds": secs, "code_files": len(want), "log": os.path.relpath(log, ctx.work)})
                    print("   build: exit %s (%.0f s)%s" % (code, secs, " with %d run-time code file(s)" % len(want) if want else ""), flush=True)
                    if code != 0 and want:
                        # the code the builder had at that moment does not compile here (an edit between two of their
                        # builds): this run gets the commit's code, as before code_at_run_time
                        ctx.state.setdefault("code_failed", []).append(json.dumps(want, sort_keys=True))
                        rec["code_at_run_time"] = "commit code (the run-time code did not build: %s)" % os.path.relpath(log, ctx.work)
                        apply_run_code(ctx, w, {})
                        code, secs2, log = build_editor(ctx, "w%02d_%s_commit" % (i, r["id"]))
                        jappend(runs_log, {"window": i, "kind": "build", "step": "w%02d.build.%s.commit" % (i, r["id"]),
                                           "exit_code": code, "seconds": secs2, "log": os.path.relpath(log, ctx.work)})
                        print("   build with the commit's code: exit %s (%.0f s)" % (code, secs2), flush=True)
                    if code != 0:
                        sys.exit("editor build failed in window %d, see %s" % (i, log))
                    ctx.state["built"] = w["sha"]
                    ctx.state["code_dirty"] = False
                    ctx.save()
                rec["materialized"] = materialize_scripts(ctx, dict(r, window_sha=w["sha"]))
                remapped = remap_script_paths(ctx)
                if remapped:
                    rec["script_paths_remapped"] = sorted(os.path.relpath(p, ctx.proj).replace("\\", "/") for p, _ in remapped)
                rows_before = wf_rows(wf_path)
                try:
                    code, secs, log, version = run_editor_script(ctx, r)
                finally:
                    for fp, b in remapped:   # the scripts as recorded again
                        with open(fp, "wb") as f:
                            f.write(b)
                rows_after = wf_rows(wf_path)
                new_rows = rows_after[len(rows_before):] if rows_after[:len(rows_before)] == rows_before else rows_after
                retried = 0
                while retried < 1 and len(new_rows) < len(r.get("rows") or []) and engine_crashed(log):
                    # the engine itself crashed (async loader assertions are not deterministic: horror's dress_props hit
                    # "Detachment inconsistency" once and ran clean the next time) before the script logged what the
                    # original did: run it once more, keeping the crash log
                    retried += 1
                    os.replace(log, log[:-4] + ".crash%d.log" % retried)
                    print("   %s engine crashed after %d/%d rows: retry %d" % (r["id"], len(new_rows), len(r["rows"]), retried), flush=True)
                    with open(wf_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write("".join(l + "\n" for l in rows_before))
                    remapped = remap_script_paths(ctx)
                    try:
                        code, secs2, log, version = run_editor_script(ctx, r)
                    finally:
                        for fp, b in remapped:
                            with open(fp, "wb") as f:
                                f.write(b)
                    secs += secs2
                    rows_after = wf_rows(wf_path)
                    new_rows = rows_after[len(rows_before):] if rows_after[:len(rows_before)] == rows_before else rows_after
                if retried:
                    rec["retried_after_engine_crash"] = retried
                with open(os.path.join(rows_dir, r["id"] + ".jsonl"), "w", encoding="utf-8", newline="\n") as f:
                    f.write("".join(l + "\n" for l in new_rows))
                with open(wf_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write("".join(l + "\n" for l in rows_before))
                outs = note_outputs(ctx, before, scan(ctx.proj), "run:" + r["id"])
                maps = sorted(set(p for p in outs["added"] + outs["changed"] if p.endswith(".umap")))
                rec.update({"exit_code": code, "seconds": secs, "version": version, "rows_replayed": len(new_rows),
                            "log": os.path.relpath(log, ctx.work), "outputs": outs, "maps_changed": maps})
                if maps:
                    pkgs = ["/Game/" + m[len("Content/"):-len(".umap")] for m in maps]
                    out = os.path.join(ctx.work, "mapdumps", r["id"])
                    dcode, dsecs = dump_maps(ctx, pkgs, out, label="mapdump_" + r["id"])
                    rec["map_dump"] = {"exit_code": dcode, "seconds": dsecs, "dir": os.path.relpath(out, ctx.work)}
                print("   %s %-38s exit %s (orig %s) %5.0f s  rows %d/%d  +%d ~%d -%d%s" % (
                    r["id"], os.path.basename(r["script"])[:38], code, r["exit_code"], secs, len(new_rows), len(r["rows"]),
                    len(outs["added"]), len(outs["changed"]), len(outs["deleted"]), ("  maps " + ",".join(os.path.basename(m) for m in maps)) if maps else ""),
                    flush=True)
            rec["end"] = now()
            jappend(runs_log, rec)
            ctx.state["done"].append(sid)
            ctx.save()
        # boundary (code files a run had at their earlier text go back to the commit first)
        apply_run_code(ctx, w, {})
        res = boundary(ctx, w)
        summ = {"window": i, "commit": w["sha"], "subject": w["subject"], "time": now(), "seconds": round(time.time() - t_w, 1),
                "runs": len(w["runs"]), "reconstruction": {"checks": len(w["reconstruction"]),
                                                           "match": sum(1 for c in w["reconstruction"] if c["match"])},
                "content": {k: (len(v) if isinstance(v, list) else v) for k, v in res.items()}, "detail": res}
        jappend(win_log, summ)
        print("   boundary: content %s" % json.dumps(summ["content"]), flush=True)
        ctx.state["window"] = i
        ctx.state["done"] = []
        ctx.save()


def cmd_status(cfg, a):
    ctx = Ctx(cfg)
    print(json.dumps({k: v for k, v in ctx.state.items() if k != "provenance"}, indent=1))
    prov = ctx.state.get("provenance", {})
    kinds = {}
    for v in prov.values():
        k = v.split(":")[0]
        kinds[k] = kinds.get(k, 0) + 1
    print("provenance:", kinds)


def cmd_dump(cfg, a):
    ctx = Ctx(cfg)
    proj = cfg["truth_dir"] if a.which == "truth" else ctx.proj
    out = os.path.join(ctx.work, "dump-" + a.which)
    if os.path.exists(out):
        shutil.rmtree(out)
    maps = a.only or ",".join(cfg.get("map_list", [])) or "all"
    code, secs = dump_maps(ctx, maps, out, assets=True, label="dump_" + a.which, project=proj)
    print("dump %s: exit %s (%.0f s) -> %s" % (a.which, code, secs, out))

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
import shutil
import subprocess
import sys
import time

HEAVY = os.path.join(os.environ.get("GF_ROOT") or os.path.join(os.path.expanduser("~"), "Work"), "tools", "ue-heavy.ps1")
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


def heavy(label, argv, log_path=None, env=None):
    """Run one engine process through ue-heavy.ps1 (machine-wide slots); returns (exit code, seconds)."""
    cmd = "& %s -Label %s -- %s; exit $LASTEXITCODE" % (ps_quote(HEAVY), ps_quote(label), " ".join(ps_quote(a) for a in argv))
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
    manifest = initial_assets_manifest(cfg, ctx)
    jdump(os.path.join(ctx.work, "initial-assets.manifest.json"), manifest)
    print("initial assets: %d files, %.2f GB" % (manifest["counts"]["files"], manifest["counts"]["bytes"] / 1e9))


def initial_assets_manifest(cfg, ctx):
    """Store packs dropped in and external source files the scripts read, with sha256 per file."""
    files = []
    for d in cfg.get("asset_drops", []):
        for it in d["items"]:
            for dp, _, fns in os.walk(it["from"]):
                for fn in fns:
                    fp = os.path.join(dp, fn)
                    rel = os.path.relpath(fp, it["from"]).replace("\\", "/")
                    files.append({"role": "store_pack", "drop": d["id"], "pack": it.get("pack"), "path": it["to"] + "/" + rel,
                                  "bytes": os.path.getsize(fp), "sha256": sha256_file(fp)})
    ext = []
    for e in cfg.get("external_sources", []):
        ext.append({"id": e["id"], "role": e["role"], "root": "<external:%s>" % e["id"]})
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


def build_editor(ctx, label):
    cfg = ctx.cfg
    log = os.path.join(ctx.logs, "build_%s.log" % label)
    bat = os.path.join(ctx.logs, "build_%s.bat" % label)
    with open(bat, "w", encoding="utf-8") as f:
        f.write('@echo off\r\ncall "%s\\Engine\\Build\\BatchFiles\\Build.bat" %s Win64 Development -Project="%s" -WaitMutex '
                '-NoHotReloadFromIDE > "%s" 2>&1\r\nexit /b %%ERRORLEVEL%%\r\n' % (cfg["engine"].replace("/", "\\"), cfg["editor_target"],
                                                                                 ctx.uproject.replace("/", "\\"), log))
    code, secs = heavy("ue-replay %s build %s" % (cfg["game"], label), [bat])
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
    env.update(run.get("env") or {})
    if run.get("reason") and cfg.get("reason_env"):
        env[cfg["reason_env"]] = run["reason"]
    log = os.path.join(ctx.logs, "runs", "%s_%s.log" % (run["id"], os.path.splitext(os.path.basename(run["script"]))[0]))
    os.makedirs(os.path.dirname(log), exist_ok=True)
    if run.get("mode") == "editor":
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


def wf_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [l for l in f.read().splitlines() if l.strip()]


def dump_maps(ctx, maps, out, assets=False, t3d=True, label="dump", project=None):
    proj = project or ctx.proj
    up = os.path.join(proj, ctx.cfg["uproject"])
    log = os.path.join(ctx.logs, "%s.log" % label)
    sarg = "-script=%s --out %s --roots %s --map-roots %s --maps %s --assets %s --t3d %s --module %s" % (
        DUMP, out.replace("\\", "/"), ",".join(ctx.cfg.get("content_roots", ["/Game"])),
        ",".join(ctx.cfg.get("map_roots", ctx.cfg.get("content_roots", ["/Game"]))), ",".join(maps) if isinstance(maps, list) else maps,
        "1" if assets else "0", "1" if t3d else "0", ctx.cfg.get("module", os.path.splitext(ctx.cfg["uproject"])[0]))
    argv = [ctx.editor_cmd, up, "-run=pythonscript", sarg] + ctx.cfg.get("editor_args", []) + ["-abslog=" + log]
    return heavy("ue-replay %s %s" % (ctx.cfg["game"], label), argv)


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


def drop_assets(ctx, d):
    n = 0
    for it in d["items"]:
        dst = ctx.p(it["to"])
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
        steps = [("run", (r["time"], k), r) for k, r in enumerate(w["runs"])] + \
                [("drop", (d["time"], -1), d) for d in w["drops"]] + [("shell", (s["time"], -1), s) for s in w["shell"]]
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
                rec["files"] = move_merge(ctx, s) if s["argv"][0] == "move-merge" else 0
                rec["outputs"] = {k: len(v) for k, v in note_outputs(ctx, before, scan(ctx.proj), "shell:" + sid).items()}
            else:
                r = s
                rec.update({"run": r["id"], "script": r["script"], "readonly": r["readonly"], "exit_code_original": r["exit_code"],
                            "rows_original": r["rows"]})
                if r["readonly"] and not a.force:
                    rec["skipped"] = "read-only"
                    jappend(runs_log, rec)
                    ctx.state["done"].append(sid)
                    ctx.save()
                    continue
                if ctx.state.get("code_dirty") or ctx.state.get("built") is None:
                    code, secs, log = build_editor(ctx, "w%02d" % i)
                    jappend(runs_log, {"window": i, "kind": "build", "step": "w%02d.build" % i, "exit_code": code, "seconds": secs,
                                       "log": os.path.relpath(log, ctx.work)})
                    print("   build: exit %s (%.0f s)" % (code, secs), flush=True)
                    if code != 0:
                        sys.exit("editor build failed in window %d, see %s" % (i, log))
                    ctx.state["built"] = w["sha"]
                    ctx.state["code_dirty"] = False
                    ctx.save()
                rec["materialized"] = materialize_scripts(ctx, r)
                rows_before = wf_rows(wf_path)
                code, secs, log, version = run_editor_script(ctx, r)
                rows_after = wf_rows(wf_path)
                new_rows = rows_after[len(rows_before):] if rows_after[:len(rows_before)] == rows_before else rows_after
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
        # boundary
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

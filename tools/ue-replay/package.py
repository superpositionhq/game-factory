"""package: assemble the replay deliverable (docs/ue-replay.md, 2.6) for the dataset packager.

Output: <root>/deliverables/_replay/<game>/<final sha8>/
  ReplayScripts/            the replay tooling (unchanged; it runs outside the game-factory checkout), the game's
                            settings, ledger, initial-assets manifest, reconstructed script texts, verification
  verification.json         summary: windows, verify report
  READY                     written last, only when every window was replayed and the verification verdict is PASS
                            (verify.py pass criteria; the packager waits for it)

There is no video: the dataset carries the replay scripts only (layout v1.1). Unscrubbed: tools/package-dataset.ps1
-ReplayScripts <...>/ReplayScripts copies and scrubs it (package-game.ps1 -ScrubDir). --force assembles an incomplete
copy without READY (for checks only).
"""
import datetime
import hashlib
import json
import os
import shutil

import runner
import ue_replay

HERE = os.path.dirname(os.path.abspath(__file__))
# record.py / editor/ue_world_replay.py (the optional editor timelapse) are not part of the dataset
TOOLS = ["ue_replay.py", "runner.py", "ledger.py", "derive.py", "verify.py", "shellfx.py", "package.py", "live.py"]
EDITOR = ["ue_dump.py"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def total_windows(led):
    """Windows to replay: the ledger's list starts with window 0, the first commit itself."""
    return (led.get("counts") or {}).get("windows", max(0, len(led.get("windows", [])) - 1))


def copytree(src, dst, skip_ext=()):
    n = 0
    for root, _dirs, files in os.walk(src):
        for fn in files:
            if fn.lower().endswith(skip_ext):
                continue
            s = os.path.join(root, fn)
            d = os.path.join(dst, os.path.relpath(s, src))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n


def readme(cfg, led, state, parts, report):
    win_total = total_windows(led) if led else 0
    ver = os.path.basename(cfg.get("engine", "").rstrip("/\\")).replace("UE_", "") or "5.7"   # the game's own engine
    lines = [
        "# ReplayScripts: creation replay of %s" % cfg["game"], "",
        "Replays how the game was built, from its git history, the builder's recorded actions and `workflow.jsonl`,",
        "in an isolated copy of the project, and checks the result against the final commit. The supplied project is",
        "not changed.", "",
        "## What is observed and what is derived", "",
        "- Observed: the commits (code, scripts, config, source art), the exact script texts at the moment they ran",
        "  (rebuilt from the recorded writes and edits, `Blobs/`), the editor-script runs in their original order with",
        "  their workflow rows, and the store packs copied in (`initial-assets.manifest.json`).",
        "- Verified: the replayed project against the final commit (`Verification/`: report, per-window checks, JSON",
        "  structure dumps of both projects).", "",
        "## How to replay", "",
        "Requirements: Windows, Unreal Engine %s, Visual Studio 2022 (C++), Python 3.11+, git with Git LFS, and the game" % ver,
        "repository. Set the machine root (`GF_ROOT`) and point `game.json` at the repository, then:", "",
        "```",
        "python ue_replay.py ledger  --game game.json   # windows, runs, script texts",
        "python ue_replay.py prepare --game game.json   # isolated project at the first commit + truth project",
        "python ue_replay.py run     --game game.json   # every window headless; resumable",
        "python ue_replay.py verify  --game game.json   # final state vs the final commit",
        "```", "",
        "## Results", "",
        "- Windows replayed: %d of %d (first commit `%s`, final `%s`)." % (state.get("window", 0), win_total,
                                                                           (led or {}).get("first", "?")[:8], (led or {}).get("final", "?")[:8]),
    ]
    if report:
        summ = report.get("summary") or {k: v for k, v in report.items() if not isinstance(v, (list, dict))}
        lines.append("- Verification (`Verification/report.md`): " + ", ".join("%s %s" % (k, v) for k, v in list(summ.items())[:12]) + ".")
    missing = [k for k, v in parts.items() if not v]
    if missing:
        lines.append("- Not included yet: " + ", ".join(missing) + ".")
    if report:
        import verify
        lines += [""] + verify.render_deviations(report.get("deviations") or [])
    return "\n".join(lines) + "\n"


def cmd_package(cfg, a):
    ctx = runner.Ctx(cfg)
    led = ctx.ledger
    if not led:
        raise SystemExit("no ledger: run `ue_replay.py ledger` first")
    work = ctx.work
    final = led["final"]
    out = os.path.join(ue_replay.out_root(), "_replay", cfg["game"], final[:8]).replace("/", os.sep)
    rs = os.path.join(out, "ReplayScripts")
    src = {
        "windows complete": ctx.state.get("window", 0) >= total_windows(led) > 0,
        "Verification/report.json": os.path.isfile(os.path.join(work, "Verification", "report.json")),
        "verification PASS": bool((runner.jload(os.path.join(work, "Verification", "report.json"), {}) or {}).get("verdict", {}).get("pass")),
    }
    complete = all(src.values())
    for k, v in src.items():
        print("  %-36s %s" % (k, "ok" if v else "MISSING"))
    if not complete and not a.force:
        raise SystemExit("incomplete: nothing written (--force assembles a copy without READY, for checks)")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(rs, "editor"))
    for f in TOOLS:
        shutil.copy2(os.path.join(HERE, f), os.path.join(rs, f))
    for f in EDITOR:
        shutil.copy2(os.path.join(HERE, "editor", f), os.path.join(rs, "editor", f))
    shutil.copy2(cfg["_path"], os.path.join(rs, "game.json"))   # unexpanded: {root} placeholders, no machine paths
    # The derived world ops (world-ops.jsonl, one T3D block per actor, ~1 GB) and the T3D map exports only fed the
    # optional editor video; they are not needed to replay or verify, so they stay out of ReplayScripts/.
    for name, dst in (("ledger.json", "ledger.json"), ("initial-assets.manifest.json", "initial-assets.manifest.json")):
        if os.path.isfile(os.path.join(work, name)):
            shutil.copy2(os.path.join(work, name), os.path.join(rs, dst))
    nblobs = copytree(os.path.join(work, "blobs"), os.path.join(rs, "Blobs")) if os.path.isdir(os.path.join(work, "blobs")) else 0
    vdir = os.path.join(rs, "Verification")
    os.makedirs(vdir)
    for name in ("report.md", "report.json"):
        p = os.path.join(work, "Verification", name)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(vdir, name))
    if os.path.isfile(os.path.join(work, "windows.jsonl")):
        shutil.copy2(os.path.join(work, "windows.jsonl"), os.path.join(vdir, "windows.jsonl"))
    for d in ("dump-replay", "dump-truth"):
        if os.path.isdir(os.path.join(work, d)):
            copytree(os.path.join(work, d), os.path.join(vdir, d), skip_ext=(".t3d",))
    report = runner.jload(os.path.join(work, "Verification", "report.json"), None)
    with open(os.path.join(rs, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(readme(cfg, led, ctx.state, src, report))
    # the build machine's per-session folders and ids in the recorded data become neutral names (ue_replay.
    # SESSION_PATH_RULES); the settings templates still match them, so a replay from this folder works the same
    neutral = {}
    sids = ue_replay.recording_session_ids(cfg)
    for dp, _, fns in os.walk(rs):
        for fn in fns:
            if not fn.lower().endswith((".json", ".jsonl", ".md", ".py", ".txt", ".tsv", ".csv", ".ini", ".sh", ".ps1")):
                continue
            fp = os.path.join(dp, fn)
            with open(fp, "rb") as f:
                b = f.read()
            t = b.decode("utf-8", "surrogateescape")
            t2, c = ue_replay.neutral_session_paths(t, sids)
            if c:
                with open(fp, "wb") as f:
                    f.write(t2.encode("utf-8", "surrogateescape"))
                for k, v in c.items():
                    neutral[k] = neutral.get(k, 0) + v
    summary = {
        "schema": "ue-replay.package/v1", "game": cfg["game"], "first_commit": led.get("first"), "final_commit": final,
        "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "complete": complete, "parts": src,
        "windows": {"done": ctx.state.get("window", 0), "total": total_windows(led)}, "blobs": nblobs,
        "verdict": (report or {}).get("verdict"), "verify": report, "session_paths_neutralised": neutral,
    }
    runner.jdump(os.path.join(out, "verification.json"), summary)
    if complete:
        with open(os.path.join(out, "READY"), "w", encoding="utf-8", newline="\n") as f:
            f.write(summary["created"] + "\n")
    print("%s %s -> %s" % ("READY" if complete else "INCOMPLETE (no READY)", cfg["game"], out))
    return 0 if complete else 1


def cmd_clean(cfg, a):
    """Free the disk a finished replay holds: the replay project, the truth project and the work files the package
    copied (dumps, blobs, rows, logs). Only after `package` wrote READY for the settings' final commit; lists what it
    would remove unless --yes is given. The ledger, state and verification report stay in work/."""
    final = runner.Ctx(cfg).ledger["final"]
    out = os.path.join(ue_replay.out_root(), "_replay", cfg["game"], final[:8])
    if not os.path.exists(os.path.join(out, "READY")):
        raise SystemExit("no READY replay package at %s: nothing removed" % out)
    work = cfg["work_dir"]
    targets = [cfg["project_dir"], cfg["truth_dir"]] + [os.path.join(work, d) for d in
                                                         ("blobs", "rows", "logs", "mapdumps", "dump-replay", "dump-truth")]
    targets = [t for t in targets if os.path.exists(t)]
    total = 0
    for t in targets:
        size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(t) for f in fs)
        total += size
        print("  %-8s %7.2f GB  %s" % ("remove" if a.yes else "would rm", size / 1e9, t))
        if a.yes:
            def writable(fn, p, _exc):   # git objects are read-only on Windows
                os.chmod(p, 0o666)
                fn(p)
            shutil.rmtree(t, onerror=writable)
    print("%s %.2f GB for %s" % ("freed" if a.yes else "would free (add --yes)", total / 1e9, cfg["game"]))

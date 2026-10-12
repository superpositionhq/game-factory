"""package: assemble the replay deliverable (docs/ue-replay.md, 2.6) for the dataset packager.

Output: <root>/deliverables/_replay/<game>/<final sha8>/
  ReplayScripts/            the replay tooling (unchanged; it runs outside the game-factory checkout), the game's
                            settings, ledger, world ops, initial-assets manifest, reconstructed script texts, verification
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

HERE = os.path.dirname(os.path.abspath(__file__))
# record.py / editor/ue_world_replay.py (the optional editor timelapse) are not part of the dataset
TOOLS = ["ue_replay.py", "runner.py", "ledger.py", "derive.py", "verify.py", "shellfx.py", "package.py"]
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


def copytree(src, dst):
    n = 0
    for root, _dirs, files in os.walk(src):
        for fn in files:
            s = os.path.join(root, fn)
            d = os.path.join(dst, os.path.relpath(s, src))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n


def readme(cfg, led, state, parts, report):
    win_total = total_windows(led) if led else 0
    lines = [
        "# ReplayScripts: creation replay of %s" % cfg["game"], "",
        "Replays how the game was built, from its git history, the builder's recorded actions and `workflow.jsonl`,",
        "in an isolated copy of the project, and checks the result against the final commit. The supplied project is",
        "not changed.", "",
        "## What is observed and what is derived", "",
        "- Observed: the commits (code, scripts, config, source art), the exact script texts at the moment they ran",
        "  (rebuilt from the recorded writes and edits, `Blobs/`), the editor-script runs in their original order with",
        "  their workflow rows, and the store packs copied in (`initial-assets.manifest.json`).",
        "- Derived: `workflow.replay.jsonl`, one op per actor (`ue.level.create`, `ue.actor.spawn`, `ue.actor.update`,",
        "  `ue.actor.remove`, `ue.level.save`), from map exports after each replayed run (included when derived).", "",
        "## How to replay", "",
        "Requirements: Windows, Unreal Engine 5.3, Visual Studio 2022 (C++), Python 3.11+, git with Git LFS, and the game",
        "repository. Set the machine root (`GF_ROOT`) and point `game.json` at the repository, then:", "",
        "```",
        "python ue_replay.py ledger  --game game.json   # windows, runs, script texts",
        "python ue_replay.py prepare --game game.json   # isolated project at the first commit + truth project",
        "python ue_replay.py run     --game game.json   # every window headless; resumable",
        "python ue_replay.py verify  --game game.json   # final state vs the final commit",
        "python ue_replay.py derive  --game game.json   # world-building ops from the map exports",
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
    return "\n".join(lines) + "\n"


def cmd_package(cfg, a):
    ctx = runner.Ctx(cfg)
    led = ctx.ledger
    if not led:
        raise SystemExit("no ledger: run `ue_replay.py ledger` first")
    work = ctx.work
    final = led["final"]
    out = os.path.join(cfg["root"], "deliverables", "_replay", cfg["game"], final[:8]).replace("/", os.sep)
    rs = os.path.join(out, "ReplayScripts")
    src = {
        "windows complete": ctx.state.get("window", 0) >= total_windows(led) > 0,
        "Verification/report.json": os.path.isfile(os.path.join(work, "Verification", "report.json")),
        "verification PASS": bool((runner.jload(os.path.join(work, "Verification", "report.json"), {}) or {}).get("verdict", {}).get("pass")),
    }
    complete = all(src.values())   # the world ops (derive) are included when present, but not required
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
    for name, dst in (("ledger.json", "ledger.json"), ("initial-assets.manifest.json", "initial-assets.manifest.json"),
                      ("world-ops.jsonl", "workflow.replay.jsonl")):
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
            copytree(os.path.join(work, d), os.path.join(vdir, d))
    report = runner.jload(os.path.join(work, "Verification", "report.json"), None)
    with open(os.path.join(rs, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(readme(cfg, led, ctx.state, src, report))
    summary = {
        "schema": "ue-replay.package/v1", "game": cfg["game"], "first_commit": led.get("first"), "final_commit": final,
        "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "complete": complete, "parts": src,
        "windows": {"done": ctx.state.get("window", 0), "total": total_windows(led)}, "blobs": nblobs,
        "world_ops": os.path.isfile(os.path.join(rs, "workflow.replay.jsonl")),
        "verdict": (report or {}).get("verdict"), "verify": report,
    }
    runner.jdump(os.path.join(out, "verification.json"), summary)
    if complete:
        with open(os.path.join(out, "READY"), "w", encoding="utf-8", newline="\n") as f:
            f.write(summary["created"] + "\n")
    print("%s %s -> %s" % ("READY" if complete else "INCOMPLETE (no READY)", cfg["game"], out))
    return 0 if complete else 1

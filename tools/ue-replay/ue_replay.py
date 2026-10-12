"""Unreal creation replay: rebuild a Track B game from its first commit by re-running what its builder ran.

  python ue_replay.py ledger  --game games/liaozhai-night.json        windows, runs, script texts -> work/ledger.json
  python ue_replay.py prepare --game ...                             isolated project at the first commit (+ truth)
  python ue_replay.py run     --game ... [--until <window>]          execute the plan (resumable)
  python ue_replay.py dump    --game ... --which replay|truth        structure dump (maps, assets) through the editor
  python ue_replay.py verify  --game ...                             final state vs the final commit
  python ue_replay.py derive  --game ...                             world ops from the per-run map exports
  python ue_replay.py record  --game ...                             visible world replay + capture (GPU job)
  python ue_replay.py status  --game ...

See docs/ue-replay.md. Every engine process runs through <root>/tools/ue-heavy.ps1 (machine root: machine/lib/gfroot.py).
Game settings may use {root} for the machine root.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "machine", "lib"))


def machine_root():
    try:
        import gfroot
        r = gfroot.root()
    except ImportError:  # outside the game-factory checkout (a delivered ReplayScripts/): env GF_ROOT or ~/Work
        r = os.environ.get("GF_ROOT") or os.path.join(os.path.expanduser("~"), "Work")
    return r.replace("\\", "/")


def expand(v, root):
    if isinstance(v, str):
        return v.replace("{root}", root)
    if isinstance(v, list):
        return [expand(x, root) for x in v]
    if isinstance(v, dict):
        return {k: expand(x, root) for k, x in v.items()}
    return v


def load_cfg(path):
    p = path if os.path.isabs(path) else os.path.join(HERE, path)
    with open(p, encoding="utf-8") as f:
        cfg = expand(json.load(f), machine_root())
    cfg["root"] = machine_root()
    cfg["_path"] = p
    w = cfg["work_root"]
    cfg.setdefault("project_dir", os.path.join(w, "project"))
    cfg.setdefault("truth_dir", os.path.join(w, "truth"))
    cfg.setdefault("work_dir", os.path.join(w, "work"))
    os.makedirs(cfg["work_dir"], exist_ok=True)
    return cfg


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def cmd_ledger(cfg, a):
    import ledger
    led, blobs = ledger.build(cfg)
    bd = os.path.join(cfg["work_dir"], "blobs")
    os.makedirs(bd, exist_ok=True)
    for h, b in blobs.items():
        p = os.path.join(bd, h)
        if not os.path.exists(p):
            with open(p, "wb") as f:
                f.write(b)
    write_json(os.path.join(cfg["work_dir"], "ledger.json"), led)
    print(json.dumps(led["counts"], indent=1))
    if a.verbose:
        for w in led["windows"][1:]:
            print("== %02d %s %s %s" % (w["index"], w["sha"][:7], w["time"][11:19], w["subject"][:70]))
            print("   inputs %d, content %d, events %s, reconstruction %d/%d" % (
                len(w["inputs"]), len(w["content"]), w["events"],
                sum(1 for c in w["reconstruction"] if c["match"]), len(w["reconstruction"])))
            for d in w["drops"]:
                print("   drop", d["id"], d["time"][11:19])
            for s in w["shell"]:
                print("   shell", s["argv"], s["time"][11:19])
            for r in w["runs"]:
                print("   %s %s %-40s %-20s ro=%d ec=%s rows=%d unknown=%s" % (
                    r["id"], r["start"][11:19], r["script"][-40:], r["script_version"], r["readonly"], r["exit_code"],
                    len(r["rows"]), ",".join(os.path.basename(u) for u in r["unknown"])))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command")
    ap.add_argument("--game", required=True)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--until", type=int, default=None)
    ap.add_argument("--which", default="replay")
    ap.add_argument("--only", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_cfg(a.game)
    fn = globals().get("cmd_" + a.command)
    if fn is None:
        import importlib
        for mod in ("runner", "verify", "derive", "record"):
            fn = getattr(importlib.import_module(mod), "cmd_" + a.command, None)
            if fn:
                break
    if fn is None:
        ap.error("unknown command " + a.command)
    return fn(cfg, a)


if __name__ == "__main__":
    sys.exit(main() or 0)

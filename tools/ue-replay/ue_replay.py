"""Unreal creation replay: rebuild a game from its first commit by re-running what its builder ran.

  python ue_replay.py ledger  --game <game>                           windows, runs, script texts -> work/ledger.json
  python ue_replay.py prepare --game ...                             isolated project at the first commit (+ truth)
  python ue_replay.py run     --game ... [--until <window>]          execute the plan (resumable)
  python ue_replay.py dump    --game ... --which replay|truth        structure dump (maps, assets) through the editor
  python ue_replay.py verify  --game ...                             final state vs the final commit
  python ue_replay.py derive  --game ...                             world ops from the per-run map exports
  python ue_replay.py record  --game ...                             visible world replay + capture (GPU job)
  python ue_replay.py status  --game ...
  python ue_replay.py package --game ... [--force]                     deliverables/_replay/<game>/<sha8>/ (READY when complete)

See docs/ue-replay.md. Every engine process runs through <root>/tools/ue-heavy.ps1 (machine root: machine/lib/gfroot.py).
--game is a game slug (its settings are <root>/games/<slug>/ReplayConfig.json, kept in the game's own repo) or a path to a
settings file (e.g. a delivered ReplayScripts/game.json). Settings may use {root} for the machine root.
"""
import argparse
import json
import os
import re
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


def out_root():
    """Where packages go: machine/lib/gfroot.out() (env GF_OUT, config "out", else <root>/deliverables)."""
    try:
        import gfroot
        return gfroot.out().replace("\\", "/")
    except ImportError:
        return (os.environ.get("GF_OUT") or machine_root() + "/deliverables").replace("\\", "/")


def check_free(path, what):
    """Stop before a disk-heavy step when the drive is below the free-space floor (env GF_MIN_FREE_GB, default 50 GB)."""
    try:
        import gfroot
        return gfroot.check_free(path, what)
    except ImportError:
        import shutil
        p = os.path.abspath(path)
        while not os.path.exists(p) and os.path.dirname(p) != p:
            p = os.path.dirname(p)
        free, floor = shutil.disk_usage(p).free / 2 ** 30, float(os.environ.get("GF_MIN_FREE_GB") or 50)
        if free < floor:
            sys.exit("%s: only %.1f GB free (floor %.0f GB, GF_MIN_FREE_GB)" % (what, free, floor))
        return free


# Settings keys that describe what the RECORDING says (commands and paths of the machine the game was built on), not
# places on this machine: they stay templates and are matched with recorded_regex().
RECORDED_KEYS = ("match", "recorded")


def expand(v, root):
    if isinstance(v, str):
        return v.replace("{root}", root).replace("{home}", os.path.expanduser("~").replace("\\", "/"))
    if isinstance(v, list):
        return [expand(x, root) for x in v]
    if isinstance(v, dict):
        return {k: (x if k in RECORDED_KEYS else expand(x, root)) for k, x in v.items()}
    return v


def recorded_regex(template):
    """A settings template for text in the recording, as a regex that matches it on any machine: {home} = any user
    profile (C:/Users/<name>, C:\\Users\\<name>, /c/Users/<name>), {root} = any path prefix, * = one path component (in
    "recorded" paths only), "/" = either slash; everything else literal."""
    out, i = [], 0
    while i < len(template):
        if template.startswith("{home}", i):
            out.append(r"(?:[A-Za-z]:|/[A-Za-z])[\\/]+Users[\\/]+[^\\/\s'\"]+")
            i += 6
        elif template.startswith("{root}", i):
            out.append(r"(?:[A-Za-z]:|/[A-Za-z])(?:[\\/]+[^\\/\s'\"]+)*?")
            i += 6
        else:
            out.append(re.escape(template[i]))
            i += 1
    return re.compile("".join(out), re.I)


def recorded_path_regex(template):
    """recorded_regex for a path: also * = one path component and / = any separator (/, \\, or an escaped \\\\)."""
    sep = r"(?:/|\\{1,2})+"
    out, i = [], 0
    while i < len(template):
        if template.startswith("{home}", i):
            out.append(r"(?:[A-Za-z]:|/[A-Za-z])%sUsers%s[^\\/\s'\"]+" % (sep, sep))
            i += 6
        elif template.startswith("{root}", i):
            out.append(r"(?:[A-Za-z]:|/[A-Za-z])(?:%s[^\\/\s'\"]+)*?" % sep)
            i += 6
        elif template.startswith("/**/", i):   # any number of components (also none)
            out.append(r"(?:%s[^\\/\s'\"]+)*?%s" % (sep, sep))
            i += 4
        elif template[i] == "/":
            out.append(sep)
            i += 1
        elif template[i] == "*":
            out.append(r"[^\\/\s'\"]*")
            i += 1
        else:
            out.append(re.escape(template[i]))
            i += 1
    return re.compile("".join(out), re.I)


# Packaged copies of recorded data (ReplayScripts: ledger, script blobs, settings, reports) name the build machine's
# per-session folders; those names are noise for a buyer and identify the session. They become neutral names that the
# settings templates ({home}/AppData/Local/Temp/**/..., {home}/AppData/Roaming/**/...) still match.
_SEP = r"([\\/]{1,2})"
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SESSION_PATH_RULES = [
    # Temp/<tool>/<project-dir>/<session uuid>[/scratch-pad] (scratch, tasks, shell-snapshots ...) -> Temp/session[/scratch]
    ("session_temp", re.compile(r"(?i)(?P<head>AppData(?P<s>[\\/]{1,2})Local(?P=s)Temp(?P=s))[^\\/\s'\"]+(?P=s)"
                                r"[^\\/\s'\"]+(?P=s)%s(?P<pad>(?P=s)scratc[h]pad(?![\w-]))?" % _UUID),
     lambda m: m.group("head") + "session" + ((m.group("s") + "scratch") if m.group("pad") else "")),
    ("session_notes", re.compile(r"(?i)(AppData)%s(Roaming)%s[^\\/\s'\"]+%sside-sessio[n]-notes%slocal[_][0-9a-f]{8}-[0-9a-f]{4}-"
                                 r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" % ((_SEP,) * 4)),
     lambda m: "%s%s%s%ssession%snotes" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(4))),
    ("session_id", re.compile(r"\blocal[_]%s\b" % _UUID), lambda m: "session"),
]


def neutral_session_paths(text, session_ids=()):
    """(new text, {rule: count}) with the build machine's session folders and ids replaced (SESSION_PATH_RULES), and
    the given session uuids (the recording's own session_id values) wherever they still stand alone. Other uuids
    (Fab listing ids, asset guids) are content and stay."""
    counts = {}
    for rid, rx, f in SESSION_PATH_RULES:
        text, n = rx.subn(f, text)
        if n:
            counts[rid] = n
    if session_ids:
        rx = re.compile(r"(?i)\b(?:%s)\b" % "|".join(re.escape(s) for s in session_ids))
        text, n = rx.subn("session", text)
        if n:
            counts["session_uuid"] = n
    return text, counts


def recording_session_ids(cfg):
    """The session uuids in a game's recording (actions.jsonl session_id), and the uuids of any Temp session folder the
    recorded commands name: the ids neutral_session_paths replaces."""
    ids = set()
    p = os.path.join(cfg.get("recording", ""), "actions.jsonl")
    if os.path.isfile(p):
        rx = re.compile(r"(?i)Temp[\\/]{1,2}[^\\/\s'\"]+[\\/]{1,2}[^\\/\s'\"]+[\\/]{1,2}(%s)" % _UUID)
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    a = json.loads(line)
                except ValueError:
                    continue
                if a.get("session_id"):
                    ids.add(str(a["session_id"]).lower())
                ids.update(m.group(1).lower() for m in rx.finditer(line))
    return sorted(i for i in ids if re.fullmatch(_UUID, i))


def has_recorded(match, text):
    """Where the settings' match string occurs in a recorded command: a plain substring, or with {home}/{root} any
    machine's path. Returns the start index or -1."""
    if "{home}" not in match and "{root}" not in match:
        return text.find(match)
    m = recorded_regex(match).search(text)
    return m.start() if m else -1


def resolve_cfg(game):
    """The settings file for --game: an existing path (absolute, or relative to the cwd or to this folder), else the
    game repo's ReplayConfig.json under the machine root."""
    for cand in (game, os.path.join(HERE, game)):
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    p = os.path.join(machine_root(), "games", game, "ReplayConfig.json")
    if os.path.isfile(p):
        return p
    raise SystemExit("no replay settings for %r: expected %s (in the game's repo) or a path to a settings file" % (game, p))


def load_cfg(path):
    p = resolve_cfg(path)
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
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load_cfg(a.game)
    fn = globals().get("cmd_" + a.command)
    if fn is None:
        import importlib
        for mod in ("runner", "verify", "derive", "record", "package"):
            fn = getattr(importlib.import_module(mod), "cmd_" + a.command, None)
            if fn:
                break
    if fn is None:
        ap.error("unknown command " + a.command)
    # disk-heavy steps refuse to start on a nearly full drive (a disk that filled mid-run corrupted a replay once)
    if a.command in ("prepare", "run", "dump"):
        check_free(cfg["work_root"], "ue_replay " + a.command)
    elif a.command == "package":
        check_free(out_root(), "ue_replay package")
    return fn(cfg, a)


if __name__ == "__main__":
    sys.exit(main() or 0)

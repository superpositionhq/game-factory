"""derive: world-building ops from the map exports taken after each replayed script run (docs/ue-replay.md, 3.5).

For every run that changed a map, its export (work/mapdumps/<run>/maps/<map>.json + .t3d) is compared with the map's
previous export:
  - the run created the map anew (it logged level.create / level.build for it, or no actor survived by name):
    ue.level.create, then ue.actor.spawn for every actor in the order the script spawned them, then ue.level.save
  - otherwise: ue.actor.spawn for new actors, ue.actor.remove for gone ones, ue.actor.update for changed ones
Each actor op carries the actor's T3D block (the editor's copy/paste text). Ops are written in the vendor field set
(id, chapter, op, target, params, reason, depends_on, source, expected, presentation) with
status "derived_from_replayed_script_run"; reasons are the builder's own workflow rows of that run.
"""
import collections
import json
import math
import os
import re

import runner

SKIP_CLASSES = ("/Script/Engine.WorldSettings", "/Script/NavigationSystem.RecastNavMesh", "/Script/Engine.AbstractNavData",
                "/Script/Engine.Brush", "/Script/Engine.DefaultPhysicsVolume", "/Script/Engine.GameplayDebuggerPlayerManager",
                "/Script/Engine.LevelBounds", "/Script/Engine.WorldDataLayers", "/Script/Engine.WorldPartitionMiniMap")
BEGIN = re.compile(r"^(\s*)Begin Actor Class=(\S+) Name=(\S+)")


def parse_t3d(path):
    """[(name, class, block)] for the top-level actors of a level T3D export."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    i = 0
    while i < len(lines):
        m = BEGIN.match(lines[i])
        if m:
            ind = m.group(1)
            j = i + 1
            while j < len(lines) and not (lines[j].startswith(ind + "End Actor") and len(lines[j]) - len(lines[j].lstrip()) == len(ind)):
                j += 1
            out.append((m.group(3).strip('"'), m.group(2), "\n".join(lines[i:j + 1])))
            i = j + 1
        else:
            i += 1
    return out


def camera_for(locs):
    """A view that frames a group of actor locations from the front-left, looking down."""
    if not locs:
        return None
    xs, ys, zs = zip(*locs)
    cx, cy, cz = sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs)
    ext = max(max(xs) - min(xs), max(ys) - min(ys), 400.0)
    dist = min(max(ext * 1.1, 900.0), 12000.0)
    pitch, yaw = -32.0, 55.0
    r = math.radians(yaw)
    back = (math.cos(r) * dist * 0.85, math.sin(r) * dist * 0.85)
    return {"location": [round(cx - back[0], 1), round(cy - back[1], 1), round(cz + dist * 0.55, 1)], "pitch": pitch, "yaw": yaw}


def ops_for_map_state(mapname, dump, t3d_path, prev, created, ctx_src, seq, reason, chapter):
    """Ops turning `prev` (previous export or None) into `dump` (this export)."""
    blocks = {n: (c, b) for n, c, b in parse_t3d(t3d_path)} if os.path.exists(t3d_path) else {}
    actors = {a["name"]: a for a in dump["actors"]}
    order = [n for n in dump.get("level_order", []) if n in actors and actors[n]["class"] not in SKIP_CLASSES]
    ops = []

    def op(kind, target, params, extra=None):
        seq[0] += 1
        o = {"schema": "ue-replay.world-op/v1", "id": "WOP%05d" % seq[0], "chapter": chapter, "op": kind, "target": target,
             "params": params, "reason": reason, "status": "derived_from_replayed_script_run", "source": ctx_src}
        if extra:
            o.update(extra)
        ops.append(o)
        return o

    groups = collections.OrderedDict()
    for n in order:
        groups.setdefault(actors[n]["folder"] or "(root)", []).append(n)
    cams = {g: camera_for([actors[n]["location"] for n in ns]) for g, ns in groups.items()}

    def spawn(n, kind="ue.actor.spawn"):
        a = actors[n]
        blk = blocks.get(n, (None, None))[1]
        g = a["folder"] or "(root)"
        size = len(groups.get(g, [])) or 1
        hold = max(0.03, min(0.25, 6.0 / size))  # a group of any size takes 1-6 s on screen
        spawn_spec = {"class": a["class"], "label": a["label"], "folder": a["folder"], "location": a["location"],
                      "rotation": a["rotation"], "scale": a["scale"], "components": a.get("components", [])}
        return op(kind, mapname, {"label": a["label"], "class": a["class"], "folder": a["folder"], "location": a["location"],
                                  "rotation": a["rotation"], "scale": a["scale"], "t3d": blk, "spawn": spawn_spec},
                  {"group": "%s|%s" % (mapname, g), "camera": cams.get(g), "hold": hold,
                   "expected": {"label": a["label"], "class": a["class"], "location": a["location"]},
                   "presentation": {"camera": "frame_group", "group": g, "hold_seconds": hold}})

    if created or prev is None:
        # each build gets its own level (map name + run id), so a replay never deletes a level it has open
        op("ue.level.create", mapname, {"map": mapname, "as": "%s__%s" % (mapname, ctx_src.get("run", "x"))},
           {"hold": 1.5, "presentation": {"hold_seconds": 1.5}})
        for n in order:
            spawn(n)
    else:
        pa = {a["name"]: a for a in prev["actors"]}
        view = lambda a: json.dumps({k: a.get(k) for k in ("class", "label", "folder", "location", "rotation", "scale", "components", "props", "ppv")}, sort_keys=True)
        for n in order:
            if n not in pa:
                spawn(n)
            elif view(pa[n]) != view(actors[n]):
                spawn(n, "ue.actor.update")
        for n, a in pa.items():
            if n not in actors and a["class"] not in SKIP_CLASSES:
                op("ue.actor.remove", mapname, {"label": a["label"], "name": n}, {"hold": 0.05})
    op("ue.level.save", mapname, {}, {"hold": 0.8, "expected": {"actors": len(order)}})
    return ops


def cmd_derive(cfg, a):
    ctx = runner.Ctx(cfg)
    led = ctx.ledger
    runs, ran = {}, {}
    with open(os.path.join(ctx.work, "runs.jsonl"), encoding="utf-8") as f:
        for l in f:
            r = json.loads(l)
            if r.get("run") and not r.get("skipped"):
                ran[r["run"]] = r
            if r.get("run") and r.get("map_dump"):
                runs[r["run"]] = r
    orig_rows = {}
    with open(os.path.join(cfg["truth_dir"], "workflow.jsonl"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                x = json.loads(l)
                orig_rows[x["id"]] = x
    seq = [0]
    out = []
    last = {}
    for w in led["windows"]:
        for run in w["runs"]:
            rr = runs.get(run["id"])
            rows = [orig_rows[i] for i in run["rows"] if i in orig_rows]
            if not rr:
                if run["id"] in ran:
                    # a run that changed no map: one caption on screen (what ran, what it logged)
                    ops_n = collections.Counter(x["op"] for x in rows)
                    seq[0] += 1
                    out.append({"schema": "ue-replay.world-op/v1", "id": "WOP%05d" % seq[0], "chapter": "other", "op": "ui.caption",
                                "target": run["script"], "params": {"rows": dict(ops_n), "exit_code": ran[run["id"]].get("exit_code")},
                                "reason": rows[0]["reason"] if rows else None, "status": "derived_from_replayed_script_run",
                                "source": {"run": run["id"], "script": run["script"], "commit": w["sha"], "commit_subject": w["subject"],
                                           "workflow_rows": run["rows"][:50], "time_original": run["start"]},
                                "hold": 0.7, "presentation": {"hold_seconds": 0.7}})
                continue
            rep_rows = []
            rp = os.path.join(ctx.work, "rows", run["id"] + ".jsonl")
            if os.path.exists(rp):
                rep_rows = [json.loads(l) for l in open(rp, encoding="utf-8") if l.strip()]
            created_maps = set(x["target"] for x in rows + rep_rows if x["op"] in ("level.create", "level.build") and x.get("status") == "observed")
            reason = next((x["reason"] for x in rows if x["op"] in ("level.create", "level.build")), None) or \
                (rows[0]["reason"] if rows else None)
            src = {"run": run["id"], "script": run["script"], "commit": w["sha"], "commit_subject": w["subject"],
                   "workflow_rows": run["rows"][:50], "time_original": run["start"]}
            md = os.path.join(ctx.work, rr["map_dump"]["dir"], "maps")
            for m in rr["maps_changed"]:
                pkg = "/Game/" + m[len("Content/"):-len(".umap")]
                rel = pkg.replace("/Game/", "").replace("/", "__")
                jp = os.path.join(md, rel + ".json")
                if not os.path.exists(jp):
                    continue
                d = runner.jload(jp)
                prev = last.get(pkg)
                created = pkg in created_maps or prev is None or not (set(a["name"] for a in d["actors"]) & set(a["name"] for a in prev["actors"]))
                out += ops_for_map_state(pkg, d, os.path.join(md, rel + ".t3d"), prev, created, src, seq, reason,
                                         chapter=pkg.rsplit("/", 1)[-1])
                last[pkg] = d
    path = os.path.join(ctx.work, "world-ops.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    c = collections.Counter(o["op"] for o in out)
    print("world ops: %d %s -> %s" % (len(out), dict(c), path))


def ops_from_dump(dump_json, t3d, out_path, prefix_map=None):
    """Test helper: ops that rebuild one exported map from scratch."""
    d = runner.jload(dump_json)
    seq = [0]
    ops = ops_for_map_state(prefix_map or d["map"], d, t3d, None, True, {"test": dump_json}, seq, None, chapter="test")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for o in ops:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    return len(ops)

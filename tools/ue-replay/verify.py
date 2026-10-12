"""verify: the replayed project against the final commit (docs/ue-replay.md, 2.4).

  files      every tracked file: identical bytes (sha256 for LFS objects, git blob id otherwise), differs, missing; extras
  assets     dump-replay/assets.json vs dump-truth/assets.json: class and per-class digest per package
  maps       per map: actors matched by class + label + folder (then nearest position); transform, components, settings,
             game-class properties compared; references to other actors compared by their labels
  rows       each replayed script run's workflow rows vs the original run's rows (op, target, status, params)
Writes work/Verification/report.json and report.md.
"""
import collections
import json
import math
import os
import re

import runner

IGNORED_DIRS = ("Binaries/", "Intermediate/", "Saved/", "DerivedDataCache/", ".git/", ".vs/", "Build/", "Packaged/")
TOL = 0.011


def close(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-4, abs_tol=TOL)
        except (TypeError, ValueError):
            return a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    return a == b


def diff_keys(a, b, prefix=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(prefix + k)
            elif not close(a[k], b[k]):
                if isinstance(a[k], dict) and isinstance(b[k], dict):
                    out += diff_keys(a[k], b[k], prefix + k + ".")
                else:
                    out.append(prefix + k)
    elif not close(a, b):
        out.append(prefix.rstrip(".") or "value")
    return out


# ------------------------------------------------------------------------------------------------ files
def verify_files(ctx, final):
    ids = runner.tree_ids(ctx.proj, final)
    have = {}
    for dp, dns, fns in os.walk(ctx.proj):
        rel_d = os.path.relpath(dp, ctx.proj).replace("\\", "/")
        if rel_d != "." and (rel_d + "/").startswith(IGNORED_DIRS):
            dns[:] = []
            continue
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), ctx.proj).replace("\\", "/")
            have[rel] = os.path.join(dp, fn)
    res = {"content": collections.Counter(), "other": collections.Counter(), "differs": [], "missing": [], "extra": []}
    for p, ident in ids.items():
        cat = "content" if p.startswith("Content/") else "other"
        if p not in have:
            res[cat]["missing"] += 1
            res["missing"].append(p)
        elif runner.file_matches(have[p], ident):
            res[cat]["identical"] += 1
        else:
            res[cat]["differs"] += 1
            res["differs"].append(p)
    for p in have:
        if p not in ids:
            res["extra"].append(p)
    res["content"] = dict(res["content"])
    res["other"] = dict(res["other"])
    return res


# ------------------------------------------------------------------------------------------------ assets
def verify_assets(rep, tru):
    a = {(x["package"], x["name"]): x for x in rep["assets"]}
    b = {(x["package"], x["name"]): x for x in tru["assets"]}
    by_class = collections.defaultdict(collections.Counter)
    diffs = []
    for k, t in b.items():
        cls = t["class"]
        if k not in a:
            by_class[cls]["missing"] += 1
            diffs.append({"asset": k[0], "class": cls, "result": "missing"})
            continue
        r = a[k]
        if r["class"] != cls:
            by_class[cls]["class_differs"] += 1
            diffs.append({"asset": k[0], "class": cls, "result": "class", "replay_class": r["class"]})
            continue
        dk = diff_keys(r.get("digest", {}), t.get("digest", {}))
        if dk:
            by_class[cls]["differs"] += 1
            diffs.append({"asset": k[0], "class": cls, "result": "differs", "keys": dk[:20]})
        else:
            by_class[cls]["same"] += 1
    for k, r in a.items():
        if k not in b:
            by_class[r["class"]]["extra"] += 1
            diffs.append({"asset": k[0], "class": r["class"], "result": "extra"})
    total = collections.Counter()
    for c in by_class.values():
        total.update(c)
    return {"total": dict(total), "by_class": {k: dict(v) for k, v in sorted(by_class.items())}, "diffs": diffs}


# ------------------------------------------------------------------------------------------------ maps
REF = re.compile(r"(/Game/[^\"' ]+\.[^:\"' ]+:PersistentLevel\.)([A-Za-z0-9_]+)")


def normalize_refs(obj, names):
    """Actor references (…:PersistentLevel.StaticMeshActor_12) by label, so spawn-name counters don't matter."""
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    s = REF.sub(lambda m: "<actor:%s>" % names.get(m.group(2).split(".")[0], m.group(2)) + ("" if "." not in m.group(2) else ""), s)
    return json.loads(s)


def actor_view(x, names):
    v = {k: x.get(k) for k in ("class", "label", "folder", "location", "rotation", "scale", "tags", "hidden", "attach_parent", "ppv")}
    comps = []
    for c in x.get("components", []):
        c = dict(c)
        c.pop("name", None)  # component instance names (…_0, …_1) depend on creation counters
        comps.append(c)
    comps.sort(key=lambda c: json.dumps(c, sort_keys=True))
    v["components"] = comps
    if "props" in x:
        p = {k: val for k, val in x["props"].items() if k not in ("root_component",)}
        v["props"] = p
    return normalize_refs(v, names)


def match_actors(ra, ta):
    """Pairs (replay, truth): same class + label + folder; within a group, nearest location first."""
    groups = collections.defaultdict(lambda: ([], []))
    for x in ra:
        groups[(x["class"], x["label"], x["folder"])][0].append(x)
    for x in ta:
        groups[(x["class"], x["label"], x["folder"])][1].append(x)
    pairs, missing, extra = [], [], []
    for key, (rs, ts) in groups.items():
        rs = list(rs)
        for t in ts:
            if not rs:
                missing.append(t)
                continue
            best = min(rs, key=lambda r: sum((a - b) ** 2 for a, b in zip(r["location"], t["location"])))
            rs.remove(best)
            pairs.append((best, t))
        extra += rs
    return pairs, missing, extra


def verify_map(rep, tru):
    rn = {x["name"]: x["label"] for x in rep["actors"]}
    tn = {x["name"]: x["label"] for x in tru["actors"]}
    pairs, missing, extra = match_actors(rep["actors"], tru["actors"])
    exact, differs = 0, []
    field_counts = collections.Counter()
    for r, t in pairs:
        dk = diff_keys(actor_view(r, rn), actor_view(t, tn))
        if dk:
            differs.append({"label": t["label"], "class": t["class"].rsplit(".", 1)[-1], "fields": dk[:12]})
            for k in dk:
                field_counts[k.split(".")[0]] += 1
        else:
            exact += 1
    return {"truth_actors": len(tru["actors"]), "replay_actors": len(rep["actors"]), "matched": len(pairs), "identical": exact,
            "differs": len(differs), "missing": len(missing), "extra": len(extra),
            "differing_fields": dict(field_counts.most_common()),
            "world_settings_same": close(rep.get("world_settings"), tru.get("world_settings")),
            "detail": {"differs": differs[:200], "missing": [(x["class"].rsplit(".", 1)[-1], x["label"]) for x in missing][:200],
                       "extra": [(x["class"].rsplit(".", 1)[-1], x["label"]) for x in extra][:200]}}


# ------------------------------------------------------------------------------------------------ rows
def mask(v, roots):
    s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    for r in roots:
        s = s.replace(r, "<project>").replace(r.replace("/", "\\\\"), "<project>")
    s = re.sub(r"\d+\.\d{3,}", lambda m: "%.2f" % float(m.group(0)), s)
    return json.loads(s)


def verify_rows(ctx, ledger):
    orig = {}
    with open(os.path.join(ctx.cfg["truth_dir"], "workflow.jsonl"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                r = json.loads(l)
                orig[r["id"]] = r
    roots = [ctx.proj.replace("\\", "/"), ctx.cfg["repo"].replace("\\", "/")]
    out = []
    totals = collections.Counter()
    for w in ledger["windows"]:
        for run in w["runs"]:
            p = os.path.join(ctx.work, "rows", run["id"] + ".jsonl")
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as f:
                rep = [json.loads(l) for l in f if l.strip()]
            org = [orig[i] for i in run["rows"] if i in orig]
            key = lambda r: (r.get("op"), r.get("target"), r.get("status"))
            same_ops = [key(r) for r in rep] == [key(r) for r in org]
            same_params = same_ops and all(mask(a.get("params"), roots) == mask(b.get("params"), roots) for a, b in zip(rep, org))
            res = "identical" if same_params else ("same_ops" if same_ops else "different")
            if not org and not rep:
                res = "none_logged"
            totals[res] += 1
            out.append({"run": run["id"], "script": run["script"], "result": res, "replayed": len(rep), "original": len(org),
                        "replayed_ops": [key(r) for r in rep][:30], "original_ops": [key(r) for r in org][:30]})
    return {"totals": dict(totals), "runs": out}


# ------------------------------------------------------------------------------------------------ report
def cmd_verify(cfg, a):
    ctx = runner.Ctx(cfg)
    final = ctx.ledger["final"]
    vdir = os.path.join(ctx.work, "Verification")
    os.makedirs(vdir, exist_ok=True)
    rep_d, tru_d = os.path.join(ctx.work, "dump-replay"), os.path.join(ctx.work, "dump-truth")
    report = {"schema": "ue-replay.verification/v1", "game": cfg["game"], "final_commit": final, "time": runner.now()}
    report["files"] = verify_files(ctx, final)
    if os.path.exists(os.path.join(rep_d, "assets.json")) and os.path.exists(os.path.join(tru_d, "assets.json")):
        report["assets"] = verify_assets(runner.jload(os.path.join(rep_d, "assets.json")), runner.jload(os.path.join(tru_d, "assets.json")))
        maps, excluded = {}, []
        roots = [r.rstrip("/") + "/" for r in cfg.get("map_roots", [])]
        for fn in sorted(os.listdir(os.path.join(tru_d, "maps"))):
            if not fn.endswith(".json"):
                continue
            t = runner.jload(os.path.join(tru_d, "maps", fn))
            # Only the game's own maps: store packs ship demo/showcase levels the builder never made (settings map_roots).
            if roots and t["map"].startswith("/Game/") and not any(t["map"].startswith(r) for r in roots):
                excluded.append(t["map"])
                continue
            rp = os.path.join(rep_d, "maps", fn)
            maps[t["map"]] = verify_map(runner.jload(rp), t) if os.path.exists(rp) else {"result": "map missing in replay"}
        report["maps"] = maps
        report["maps_excluded"] = {"reason": "outside the game's map roots %s: demo/showcase levels shipped inside store packs, "
                                             "not built by the game's creator" % cfg.get("map_roots", []), "maps": excluded}
    report["rows"] = verify_rows(ctx, ctx.ledger)
    report["windows"] = [json.loads(l) for l in open(os.path.join(ctx.work, "windows.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(ctx.work, "windows.jsonl")) else []
    for w in report["windows"]:
        w.pop("detail", None)
    runner.jdump(os.path.join(vdir, "report.json"), report)
    md = render_md(report, ctx)
    with open(os.path.join(vdir, "report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(md[:6000])


def render_md(r, ctx):
    L = ["# Replay verification: %s at %s" % (r["game"], r["final_commit"][:10]), ""]
    f = r["files"]
    L += ["## Files against the final commit", "",
          "| | identical | differs | missing |", "|---|---:|---:|---:|",
          "| outside Content/ | %d | %d | %d |" % (f["other"].get("identical", 0), f["other"].get("differs", 0), f["other"].get("missing", 0)),
          "| Content/ | %d | %d | %d |" % (f["content"].get("identical", 0), f["content"].get("differs", 0), f["content"].get("missing", 0)),
          "", "Files in the replay project that the commit does not have: %d." % len(f["extra"]), ""]
    if "assets" in r:
        t = r["assets"]["total"]
        L += ["## Assets (structure dump)", "",
              "Same class and digest: %d; differs: %d; missing: %d; extra: %d." % (t.get("same", 0), t.get("differs", 0), t.get("missing", 0), t.get("extra", 0)), "",
              "| class | same | differs | missing | extra |", "|---|---:|---:|---:|---:|"]
        for c, v in r["assets"]["by_class"].items():
            L.append("| %s | %d | %d | %d | %d |" % (c, v.get("same", 0), v.get("differs", 0), v.get("missing", 0), v.get("extra", 0)))
        L += ["", "## Maps (actor structure)", "",
              "| map | actors (truth / replay) | matched | identical | differs | missing | extra | fields that differ |",
              "|---|---|---:|---:|---:|---:|---:|---|"]
        ex = r.get("maps_excluded") or {}
        if ex.get("maps"):
            L.insert(len(L) - 2, "Not compared (%d): %s." % (len(ex["maps"]), ex["reason"]))
            L.insert(len(L) - 2, "")
        for m, v in r["maps"].items():
            if "truth_actors" not in v:
                L.append("| %s | %s | | | | | | |" % (m, v.get("result")))
                continue
            L.append("| %s | %d / %d | %d | %d | %d | %d | %d | %s |" % (
                m.rsplit("/", 1)[-1], v["truth_actors"], v["replay_actors"], v["matched"], v["identical"], v["differs"], v["missing"],
                v["extra"], ", ".join("%s %d" % kv for kv in list(v["differing_fields"].items())[:6])))
    rt = r["rows"]["totals"]
    L += ["", "## Script runs: workflow rows replayed vs original", "",
          ", ".join("%s %d" % kv for kv in sorted(rt.items())), ""]
    if r["windows"]:
        L += ["## Windows", "", "| # | commit | runs | seconds | fallback | exact | differs | missing | extra |", "|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
        for w in r["windows"]:
            c = w["content"]
            L.append("| %d | %s | %d | %.0f | %d | %d | %d | %d | %d |" % (w["window"], w["commit"][:7], w["runs"], w["seconds"], c.get("fallback", 0),
                                                                  c.get("exact", 0), c.get("differs", 0), c.get("missing", 0), c.get("extra", 0)))
    return "\n".join(L) + "\n"

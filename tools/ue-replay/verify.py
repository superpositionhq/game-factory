"""verify: the replayed project against the final commit (docs/ue-replay.md, 2.4).

  files      every tracked file: identical bytes (sha256 for LFS objects, git blob id otherwise), differs, missing; extras
  assets     dump-replay/assets.json vs dump-truth/assets.json: class and per-class digest per package
  maps       per map: actors matched by class + label + folder (then nearest position); transform, components, settings,
             game-class properties compared; references to other actors compared by their labels
  rows       each replayed script run's workflow rows vs the original run's rows (op, target, status, params)
  verdict    PASS / FAIL against the criteria below; the dataset is COMPLETE only with PASS
Writes work/Verification/report.json and report.md.

Pass criteria (all must hold; docs/ue-replay.md 2.4):
  1. every tracked file outside Content/ is byte-identical to the final commit, none missing, no extra files except
     git-ignored ones (e.g. __pycache__);
  2. every asset of the final commit exists in the replay with the same class and the same structure digest;
  3. every game map (settings map_roots) has the same actors (matched by class, label, folder) with the same
     transform, components and properties, and the same world settings.
Known differences that are not content are normalised before comparing, counted and listed in the report
(NORMALISE); Content/ bytes are not compared for the verdict (Unreal writes random GUIDs into every saved package).
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


# Known non-content differences, normalised before comparing (each counted in the report):
NORMALISE = [
    ("guid", "random GUIDs Unreal writes on save (ExpressionGUID, Guid=...)",
     lambda s: re.sub(r"(?i)(guid=)[0-9a-f]{32}", r"\1<guid>", s)),
    ("loc_key", "random localization keys Unreal generates for text properties (NSLOCTEXT(\"\", \"<32 hex>\", ...))",
     lambda s: re.sub(r'NSLOCTEXT\(\\"([^"\\]*)\\", \\"[0-9A-Fa-f]{32}\\"', r'NSLOCTEXT(\\"\1\\", \\"<key>\\"', s)),
    ("memory_address", "memory addresses in printed object values (delegates: '(0x00000801...)')",
     lambda s: re.sub(r"\(0x[0-9A-Fa-f]+\)", "(0x)", s)),
]


def add_project_path_rule(cfg):
    """Absolute paths under the project folder (import sources: FontFace source_filename, texture import data) name the
    folder the editor ran in: the game repo for truth, the replay project for the replay, and the original user's
    profile (or its scrubbed form). Compared as <project>/... ; counted as project_path."""
    if any(r[0] == "project_path" for r in NORMALISE):
        return
    pats = []
    for root in (cfg.get("repo"), cfg.get("project_dir"), cfg.get("truth_dir")):
        if not root:
            continue
        parts = [p for p in root.replace("\\", "/").split("/") if p]
        rx = []
        for i, p in enumerate(parts):
            # the profile folder after Users/ may hold any (or a scrubbed) user name
            rx.append(r"[^/\\\"]+" if i > 0 and parts[i - 1].lower() == "users" else re.escape(p))
        pats.append(r"(?:/|\\\\)+".join(rx))
    big = re.compile("(?i)(?:%s)(?=/|\\\\)" % "|".join(pats))
    # a whole string value naming a file inside the project, absolute ("C:\\...\\RawAssets\\x.ttf") or project-relative
    # ("RawAssets/x.ttf", as the import-path scrub rewrites it): both as "RawAssets/x.ttf"
    whole = re.compile(r'"<project>((?:(?:/|\\\\)+[^"/\\]+)+)"')

    def rule(s):
        s = big.sub("<project>", s)
        return whole.sub(lambda m: '"' + re.sub(r"(?:/|\\\\)+", "/", m.group(1)).lstrip("/") + '"', s)
    NORMALISE.append(("project_path", "paths into the folder the editor ran in (game repo vs replay project, user "
                      "profile name; absolute or project-relative) in import-source fields", rule))


DROP_KEYS = {
    "tags.Compressed Size (KB)": ("derived_compression_size", "AnimSequence compressed size: derived data of the "
                                  "compression codec run, not authored content"),
}


def norm_with(obj, rules):
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    for _, _, f in rules:
        s = f(s)
    return json.loads(s)


def tolerant_diff(a, b, counts):
    """diff_keys after the known non-content differences are taken out; counts[rule] += 1 for each rule that removed
    a difference."""
    dk = diff_keys(a, b)
    if not dk:
        return []
    for k in list(dk):
        if k in DROP_KEYS:
            dk.remove(k)
            counts[DROP_KEYS[k][0]] += 1
    if not dk:
        return []
    na, nb = norm_with(a, NORMALISE), norm_with(b, NORMALISE)
    rest = [k for k in diff_keys(na, nb) if k not in DROP_KEYS]
    if len(rest) < len(dk):
        # attribute to the first rule that alone removes some difference
        for rid, _, f in NORMALISE:
            if len([k for k in diff_keys(norm_with(a, [(rid, "", f)]), norm_with(b, [(rid, "", f)])) if k not in DROP_KEYS]) < len(dk):
                counts[rid] += 1
    return rest


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
def verify_assets(rep, tru, counts=None):
    counts = counts if counts is not None else collections.Counter()
    a = {(x["package"], x["name"]): x for x in rep["assets"]}
    b = {(x["package"], x["name"]): x for x in tru["assets"]}
    by_class = collections.defaultdict(collections.Counter)
    diffs, load_err = [], []
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
        if r.get("error") or t.get("error"):
            # an asset that cannot be loaded: equal only when it fails the same way on both sides
            dk = [] if r.get("error") == t.get("error") else ["error"]
            if not dk:
                counts["asset_load_error_both"] += 1
                load_err.append({"asset": k[0], "class": cls, "error": t.get("error")})
        else:
            dk = tolerant_diff(r.get("digest", {}), t.get("digest", {}), counts)
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
    return {"total": dict(total), "by_class": {k: dict(v) for k, v in sorted(by_class.items())}, "diffs": diffs,
            "load_error_both": load_err}


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


def verify_map(rep, tru, counts=None):
    counts = counts if counts is not None else collections.Counter()
    rn = {x["name"]: x["label"] for x in rep["actors"]}
    tn = {x["name"]: x["label"] for x in tru["actors"]}
    pairs, missing, extra = match_actors(rep["actors"], tru["actors"])
    exact, differs = 0, []
    field_counts = collections.Counter()
    for r, t in pairs:
        dk = tolerant_diff(actor_view(r, rn), actor_view(t, tn), counts)
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


# ------------------------------------------------------------------------------------------------ verdict
def verdict(report, ctx, counts):
    f = report["files"]
    extra = f.get("extra", [])
    ignored = set()
    if extra:
        try:
            out = runner.git(ctx.proj, "check-ignore", "--stdin", inp=("\n".join(extra) + "\n").encode("utf-8"), check=False)
            ignored = set(l.strip() for l in (out or "").splitlines() if l.strip())
        except Exception:
            ignored = set()
    extra_real = [p for p in extra if p not in ignored]
    other_missing = [p for p in f.get("missing", []) if not p.startswith("Content/")]
    other_diff = [p for p in f.get("differs", []) if not p.startswith("Content/")]
    crit = []
    crit.append({"id": "files", "text": "every tracked file outside Content/ byte-identical; none missing; no extra files except git-ignored ones",
                 "pass": not other_missing and not other_diff and not extra_real,
                 "result": "%d identical, %d differ, %d missing; %d extra (%d git-ignored)" % (
                     f["other"].get("identical", 0), len(other_diff), len(other_missing), len(extra), len(ignored)),
                 "failures": (other_diff + other_missing + extra_real)[:50]})
    if "assets" in report:
        t = report["assets"]["total"]
        bad = [d for d in report["assets"]["diffs"]]
        crit.append({"id": "assets", "text": "every asset of the final commit present with the same class and structure digest",
                     "pass": not bad, "result": "%d same, %d differ, %d missing, %d extra, %d class changed" % (
                         t.get("same", 0), t.get("differs", 0), t.get("missing", 0), t.get("extra", 0), t.get("class_differs", 0)),
                     "failures": [(d["asset"], d["result"], d.get("keys")) for d in bad][:50]})
        mfail, msum = [], []
        for m, v in report["maps"].items():
            if "truth_actors" not in v:
                mfail.append((m, v.get("result")))
                continue
            ok = v["missing"] == 0 and v["extra"] == 0 and v["differs"] == 0 and v["world_settings_same"]
            msum.append("%s %d/%d" % (m.rsplit("/", 1)[-1], v["identical"], v["truth_actors"]))
            if not ok:
                mfail.append((m, "differs %d, missing %d, extra %d, world settings %s" % (v["differs"], v["missing"], v["extra"],
                                                                                          "same" if v["world_settings_same"] else "differ")))
        crit.append({"id": "maps", "text": "every game map: same actors (class, label, folder) with the same transform, components, "
                                           "properties and world settings", "pass": not mfail and bool(report["maps"]),
                     "result": "; ".join(msum) or "no maps", "failures": mfail[:50]})
    else:
        crit.append({"id": "assets", "text": "structure dumps of replay and truth", "pass": False, "result": "no structure dumps",
                     "failures": ["run dump --which replay and --which truth"]})
    exclusions = {
        "content_bytes": {"what": "Content/ .uasset/.umap bytes: Unreal writes a random PersistentGuid into every saved package; "
                                  "compared by structure instead (criteria assets, maps)",
                          "count": f["content"].get("differs", 0)},
        "maps_not_compared": {"what": (report.get("maps_excluded") or {}).get("reason", ""),
                              "maps": (report.get("maps_excluded") or {}).get("maps", [])},
        "git_ignored_extra_files": sorted(ignored),
    }
    if ctx.cfg.get("dump_exclusions"):
        # folders left out of the structure dump (settings dump_exclusions: loading them crashes the editor, in the
        # final commit too); their files are still compared byte for byte under criterion files / Content bytes
        exclusions["structure_dump_excluded"] = {"what": "; ".join("%s: %s" % (d["path"], d["reason"]) for d in ctx.cfg["dump_exclusions"]),
                                                 "count": len(ctx.cfg["dump_exclusions"])}
    for rid, what, _ in NORMALISE:
        exclusions[rid] = {"what": what, "count": counts.get(rid, 0)}
    for k, (rid, what) in DROP_KEYS.items():
        exclusions[rid] = {"what": what + " (key %s)" % k, "count": counts.get(rid, 0)}
    if counts.get("asset_load_error_both"):
        exclusions["asset_load_error_both"] = {"what": "assets that fail to load the same way in truth and replay (the "
                                               "final commit's own content): compared by class and error only",
                                               "count": counts["asset_load_error_both"]}
    rows = report.get("rows", {}).get("totals", {})
    return {"pass": all(c["pass"] for c in crit), "criteria": crit, "exclusions": exclusions,
            "informational": {"workflow_rows_per_run": rows,
                              "note": "row comparison is informational: rows carry times, ids and per-run counts"}}


# ------------------------------------------------------------------------------------------------ report
def deviations(ctx, report):
    """Every place the replay departs from the raw recording, for buyers: what, which runs/items, which commit, why."""
    cfg, led = ctx.cfg, ctx.ledger
    runs = [dict(r, _w=w) for w in led["windows"] for r in w["runs"]]
    out = []

    def add(kind, what, items, reason=None):
        if items:
            out.append({"kind": kind, "what": what, "items": items, **({"reason": reason} if reason else {})})

    for u in cfg.get("use_commit_text", []):
        hit = [r for r in runs if r["script"] == u["script"] and r["_w"]["index"] in u.get("windows", [r["_w"]["index"]])]
        add("commit_text_substituted", "script text taken from the commit instead of the recorded edits",
            [{"script": u["script"], "window": w, "commit": next(r["_w"]["sha"] for r in hit if r["_w"]["index"] == w),
              "runs": [r["id"] for r in hit if r["_w"]["index"] == w]} for w in sorted(set(r["_w"]["index"] for r in hit))],
            u.get("reason"))
    forced = set((u["script"], wi) for u in cfg.get("use_commit_text", []) for wi in u.get("windows", []))
    other = [r for r in runs if r.get("script_version") == "unknown_use_commit" and (r["script"], r["_w"]["index"]) not in forced]
    add("commit_text_unrebuildable", "script text the recording could not rebuild (e.g. perl -i edits, edits outside "
        "the recording): the window's commit text is used", [{"script": r["script"], "window": r["_w"]["index"],
                                                              "commit": r["_w"]["sha"], "run": r["id"]} for r in other])
    ro_scripts = set(cfg.get("not_readonly", []))
    add("readonly_script_replayed", "scripts a read-only pattern matches, replayed because a later run reads what they write",
        [{"script": r["script"], "run": r["id"], "reason": next((n.get("reason") for n in cfg.get("not_readonly_runs", [])
                                                                 if n.get("tool_use_id") == r.get("action_tool_use_id")), "settings not_readonly")}
         for r in runs if not r.get("readonly") and (os.path.basename(r["script"]) in ro_scripts or
                                                     any(n.get("tool_use_id") == r.get("action_tool_use_id") for n in cfg.get("not_readonly_runs", [])))])
    add("runs_not_replayed", "runs listed in the recording that never started (settings not_run, or the wrapper logged no start)",
        [{"script": r["script"], "run": r["id"], "reason": r.get("not_run") or "no wrapper row and no exit code: the command stopped before it"}
         for r in runs if r.get("not_run") or (r.get("via_wrapper") and r.get("wrapper_rows") == 0 and r.get("exit_code") is None)])
    add("readonly_runs_skipped", "probes/checks (settings readonly_patterns) listed but not replayed",
        [{"script": r["script"], "run": r["id"]} for r in runs if r.get("readonly")])
    add("shell_steps", "shell commands of the builder replayed from settings (delete, move-merge, host-python), each matched "
        "to its recorded command", [{"match": s["match"], "argv": s["argv"], "reason": s.get("reason")} for s in cfg.get("shell_replay", [])])
    add("asset_drops", "store packs and downloads restored into the project where the builder copied them in",
        [{"id": d["id"], "packs": [it.get("pack") or it.get("to") for it in d["items"]], "reason": d.get("reason")} for d in cfg.get("asset_drops", [])])
    add("external_sources_rebuilt", "external source folders rebuilt from library archives (the builder's scratch folder is gone)",
        [{"id": e["id"], "rebuild": e["rebuild"], "reason": e.get("role")} for e in cfg.get("external_sources", []) if e.get("rebuild")])
    retried = [json.loads(l) for l in open(os.path.join(ctx.work, "runs.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(ctx.work, "runs.jsonl")) else []
    add("script_paths_remapped", "absolute paths in the builder's scripts to a file outside the project (on the machine "
        "the game was built on) pointed at its copy on this machine for the run, then put back",
        [{"source": e["id"], "recorded": e["recorded"], "copy": e.get("path") or "rebuilt",
          "runs": [x.get("run") for x in retried if x.get("script_paths_remapped")]}
         for e in cfg.get("external_sources", []) if e.get("remap_scripts")
         and any(x.get("script_paths_remapped") for x in retried)], None)
    add("code_at_run_time", "runs replayed with the C++ as it stood when they started (the window's commit has later "
        "code; the editor is rebuilt between runs)",
        [{"run": x.get("run"), "script": x.get("script"), "code": x["code_at_run_time"]} for x in retried
         if x.get("code_at_run_time") and not str(x["code_at_run_time"]).startswith("commit code")])
    add("code_at_run_time_not_buildable", "runs whose run-time C++ did not compile here: they got the window's commit code",
        [{"run": x.get("run"), "script": x.get("script"), "detail": x["code_at_run_time"]} for x in retried
         if str(x.get("code_at_run_time") or "").startswith("commit code (")])
    add("code_at_run_time_unknown", "runs whose C++ at that moment the recording cannot rebuild (a shell edit it cannot "
        "follow): they got the window's commit code", [{"run": r["id"], "script": r["script"], "files": r["code_unknown"]}
                                                      for r in runs if r.get("code_unknown") and not r.get("readonly")])
    add("runs_retried_after_engine_crash", "runs the engine crashed in before the script finished, run once more",
        [{"run": x.get("run"), "script": x.get("script"), "retries": x["retried_after_engine_crash"]} for x in retried if x.get("retried_after_engine_crash")])
    add("structure_dump_excluded", "folders left out of the structure dump (loading them crashes the editor, in the final commit too)",
        cfg.get("dump_exclusions", []))
    add("assets_failing_to_load", "assets that fail to load the same way in both projects (compared by class and error only)",
        (report.get("assets") or {}).get("load_error_both", []))
    return out


def cmd_report(cfg, a):
    """Refresh an existing verification report without verifying again (the replay project may be gone): recompute
    the deviations from the current settings and re-render report.md. Verdict, criteria and counts stay as verified."""
    ctx = runner.Ctx(cfg)
    vdir = os.path.join(ctx.work, "Verification")
    report = runner.jload(os.path.join(vdir, "report.json"), None)
    if not report:
        raise SystemExit("no Verification/report.json to refresh: run verify")
    add_project_path_rule(cfg)
    report["deviations"] = deviations(ctx, report)
    report["report_refreshed"] = runner.now()
    runner.jdump(os.path.join(vdir, "report.json"), report)
    with open(os.path.join(vdir, "report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(render_md(report, ctx))
    print("report refreshed: %d deviation kinds; verdict %s (as verified %s)" % (
        len(report["deviations"]), "PASS" if report["verdict"]["pass"] else "FAIL", report.get("time")))
    print("VERDICT: %s" % ("PASS" if report["verdict"]["pass"] else "FAIL"))
    return 0 if report["verdict"]["pass"] else 1


def cmd_verify(cfg, a):
    ctx = runner.Ctx(cfg)
    final = ctx.ledger["final"]
    add_project_path_rule(cfg)
    vdir = os.path.join(ctx.work, "Verification")
    os.makedirs(vdir, exist_ok=True)
    rep_d, tru_d = os.path.join(ctx.work, "dump-replay"), os.path.join(ctx.work, "dump-truth")
    report = {"schema": "ue-replay.verification/v1", "game": cfg["game"], "final_commit": final, "time": runner.now()}
    report["files"] = verify_files(ctx, final)
    counts = collections.Counter()
    if os.path.exists(os.path.join(rep_d, "assets.json")) and os.path.exists(os.path.join(tru_d, "assets.json")):
        report["assets"] = verify_assets(runner.jload(os.path.join(rep_d, "assets.json")), runner.jload(os.path.join(tru_d, "assets.json")), counts)
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
            maps[t["map"]] = verify_map(runner.jload(rp), t, counts) if os.path.exists(rp) else {"result": "map missing in replay"}
        report["maps"] = maps
        report["maps_excluded"] = {"reason": "outside the game's map roots %s: demo/showcase levels shipped inside store packs, "
                                             "not built by the game's creator" % cfg.get("map_roots", []), "maps": excluded}
    report["rows"] = verify_rows(ctx, ctx.ledger)
    report["windows"] = [json.loads(l) for l in open(os.path.join(ctx.work, "windows.jsonl"), encoding="utf-8")] \
        if os.path.exists(os.path.join(ctx.work, "windows.jsonl")) else []
    for w in report["windows"]:
        w.pop("detail", None)
    report["verdict"] = verdict(report, ctx, counts)
    report["deviations"] = deviations(ctx, report)
    runner.jdump(os.path.join(vdir, "report.json"), report)
    md = render_md(report, ctx)
    with open(os.path.join(vdir, "report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(md[:6000])
    print("VERDICT: %s" % ("PASS" if report["verdict"]["pass"] else "FAIL"))
    return 0 if report["verdict"]["pass"] else 1


def render_deviations(devs):
    """Markdown: every place the replay departs from the raw recording (also used by package.py's README)."""
    L = ["## Deviations from the recording", ""]
    if not devs:
        return L + ["None: every step was replayed from the recording as recorded.", ""]
    L += ["Everything below is done from the game's replay settings (`game.json`) rather than straight from the recorded",
          "actions; each entry says why.", ""]
    for d in devs:
        L.append("### %s (%d)" % (d["kind"], len(d["items"])))
        L += ["", d["what"] + (". Why: " + d["reason"] if d.get("reason") else "."), ""]
        for it in d["items"][:60]:
            if isinstance(it, dict):
                L.append("- " + "; ".join("%s: %s" % (k, ", ".join(map(str, v)) if isinstance(v, list) else
                                                      (v[:12] if k == "commit" and isinstance(v, str) else v))
                                          for k, v in it.items() if v not in (None, "", [])))
            else:
                L.append("- %s" % it)
        if len(d["items"]) > 60:
            L.append("- ... %d more (report.json)" % (len(d["items"]) - 60))
        L.append("")
    return L


def render_md(r, ctx):
    L = ["# Replay verification: %s at %s" % (r["game"], r["final_commit"][:10]), ""]
    v = r.get("verdict")
    if v:
        L += ["## Verdict: %s" % ("PASS" if v["pass"] else "FAIL"), "", "| criterion | result | pass |", "|---|---|---|"]
        for c in v["criteria"]:
            L.append("| %s | %s | %s |" % (c["text"], c["result"], "yes" if c["pass"] else "**no**"))
        L += ["", "Known differences that are not content (normalised or not compared):", ""]
        for k, e in v["exclusions"].items():
            if isinstance(e, dict):
                L.append("- %s: %s%s" % (k, e.get("what", ""), (" (%d)" % e["count"]) if "count" in e else
                                         (" (%d maps: %s)" % (len(e.get("maps", [])), ", ".join(m.rsplit("/", 1)[-1] for m in e.get("maps", []))))))
            else:
                L.append("- %s: %d file(s)" % (k, len(e)))
        L.append("")
    L += render_deviations(r.get("deviations") or [])
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

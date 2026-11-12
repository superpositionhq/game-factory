"""Tasks as the checker reads them: GameTask JSON (docs/schemas/game-task.schema.json) from a game repo's orphan `tasks`
branch (`tasks`, else `origin/tasks`: Tasks/<name>.json), checked against the schema and the rules the schema can't
say (tools/validate-game.py), and their checks with the schema's defaults filled in, so the rest of the checker reads
plain dicts: every check has `required`, `weight` and `needs`; a probe's measure has every optional field (None when
unset, `of` "count"); points, selections and task plays have their defaults (an actor point's `offset`, a teleport's
`yaw`)."""

import hashlib
import importlib.util
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
REFS = ("tasks", "origin/tasks")  # where a game's tasks live (validate-game.py TASKS_REFS)
STILL_WORKS = "still_works"  # the milestone of what a task must leave working (write-tasks section 5)
RUNTIME = ("pawn", "camera", "actors", "widgets", "components", "pieces", "screen", "light", "grading", "spawns", "log",
           "audio", "ground", "ui", "drawn", "world")
SAMPLED = ("pawn", "camera", "actors", "widgets", "components", "pieces", "screen", "light", "grading", "spawns",
           "audio", "ground", "ui", "drawn", "world")
AUDIO_STARTED = ("started", "started_audible")  # counted per sample's interval, summed by default (as spawns)
AUDIO_NAMED = ("sounds", "repeats")  # read from the names of the sounds that started (probes._heard_names)
WHOLE_SCREEN = [0.0, 0.0, 1.0, 1.0]
ANGLE_PREFIXES = ("rel_yaw:", "world_yaw:", "world_pitch:", "world_roll:")
ZERO = [0.0, 0.0, 0.0]
_validator = None


def validator():
    """tools/validate-game.py as a module (its JSON Schema subset and the task rules beyond the schema)."""
    global _validator
    if _validator is None:
        spec = importlib.util.spec_from_file_location("validate_game", os.path.join(TOOLS, "validate-game.py"))
        _validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_validator)
    return _validator


def problems(task):
    """What makes `task` (a dict) unreadable for the checker: schema errors and the rules beyond the schema."""
    v = validator()
    found = list(v.check_schema(task, v.SCHEMAS["game-task"]))
    if not found:
        found += v.task_semantic_errors(task)
    return found


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def tasks_ref(repo):
    """The repo's tasks branch (`tasks`, else `origin/tasks`), or None."""
    return next((r for r in REFS if git(repo, "rev-parse", "--verify", "-q", r + "^{commit}").returncode == 0), None)


def read_tasks(repo):
    """(ref, {name: (task dict or None, raw bytes, why unreadable or None)}) of every Tasks/<name>.json on the tasks
    branch."""
    ref = tasks_ref(repo)
    if ref is None:
        return None, {}
    listing = git(repo, "-c", "core.quotepath=off", "ls-tree", "--name-only", ref + ":Tasks").stdout
    out = {}
    for name in listing.decode("utf-8", "replace").splitlines():
        if not name.endswith(".json"):
            continue
        stem = name[:-len(".json")]
        shown = git(repo, "show", f"{ref}:Tasks/{name}")
        if shown.returncode != 0:
            out[stem] = (None, b"", f"cannot read Tasks/{name} on {ref}")
            continue
        try:
            data = json.loads(shown.stdout.decode("utf-8-sig"))
        except ValueError as e:
            out[stem] = (None, shown.stdout, f"Tasks/{name} is not JSON ({e})")
            continue
        out[stem] = (data, shown.stdout, None)
    return ref, out


def digest(raw):
    """The task file's sha256 (a result names the version of the task it checked)."""
    return hashlib.sha256(raw).hexdigest()


# -- defaults -----------------------------------------------------------------------------------------------------------


def _floats(values):
    return [float(v) for v in values]


def point(p):
    """A point with its defaults: {"xyz"}, {"pawn", "offset"}, {"camera", "forward"}, {"actor", "offset"}."""
    if "xyz" in p:
        return {"xyz": _floats(p["xyz"])}
    if "pawn" in p:
        return {"pawn": True, "offset": _floats(p.get("offset", ZERO))}
    if "camera" in p:
        return {"camera": True, "forward": float(p.get("forward", 0.0))}
    return {"actor": select(p["actor"]), "offset": _floats(p.get("offset", ZERO))}


def near(n):
    """A `near` with its point filled in, its radius and its height band (`z_min`, `z_max` as numbers, `z_relative`)
    only where set, as written."""
    out = {"point": point(n["point"]), "radius": float(n["radius"])}
    for k in ("z_min", "z_max"):
        if n.get(k) is not None:
            out[k] = float(n[k])
    if n.get("z_relative") is not None:
        out["z_relative"] = n["z_relative"]
    return out


def line(n):
    """A drawn measure's `line`: its two points filled in and its radius."""
    return {"from": point(n["from"]), "to": point(n["to"]), "radius": float(n["radius"])}


def select(s):
    """An actor, widget or component selection as written, without unset keys, its `near`, `owner` and `has` filled
    in."""
    out = {}
    for k, v in s.items():
        if v is None:
            continue
        if k == "near":
            out[k] = near(v)
        elif k in ("owner", "has"):
            out[k] = select(v)
        else:
            out[k] = v
    return out


def measure(m):
    """A probe's measure with every optional field: window, at, agg, to_angle, to_axis (None when unset), `of`
    ("count") for selections, `field` ("count") for the log, `to` and `point` with their defaults, a pieces measure's
    `select` ({} when unset), a screen measure's `rect` (the whole frame when unset), an audio measure's `select` ({}
    when unset), a ground measure's `xy`, `box`, `select` (None when unset) and `grid` (8), and a ui measure's `select`
    ({} when unset), `of` ("count") and `match` (None), and a drawn measure's `near` and `line` (None when unset)."""
    out = dict(m)
    kind = out["probe"]
    if kind in SAMPLED:
        for k in ("window", "at", "agg", "to_angle", "to_axis"):
            out.setdefault(k, None)
        if kind in ("actors", "widgets", "components"):
            out.setdefault("of", "count")
            out.setdefault("match", None)
            out["select"] = select(out["select"])
        if kind == "pawn":
            out["to"] = point(out["to"]) if out.get("to") is not None else None
        if kind == "light":
            out["point"] = point(out["point"])
        if kind == "pieces":
            out["select"] = select(out.get("select") or {})
        if kind == "screen":
            out["rect"] = _floats(out.get("rect") or WHOLE_SCREEN)
        if kind == "audio":
            out["select"] = select(out.get("select") or {})
        if kind == "ui":
            out.setdefault("of", "count")
            out.setdefault("match", None)
            out["select"] = select(out.get("select") or {})
        if kind == "ground":
            out["xy"] = _floats(out["xy"]) if out.get("xy") is not None else None
            out["box"] = _floats(out["box"]) if out.get("box") is not None else None
            out["grid"] = int(out.get("grid", 8))
            out["select"] = select(out["select"]) if out.get("select") is not None else None
        if kind == "drawn":
            out["near"] = near(out["near"]) if out.get("near") is not None else None
            out["line"] = line(out["line"]) if out.get("line") is not None else None
    elif kind == "asset":
        for k in ("asset", "map", "select", "match", "to_angle", "to_axis"):
            out.setdefault(k, None)
        out.setdefault("of", "count")
        if out["select"] is not None:
            out["select"] = select(out["select"])
    elif kind == "log":
        out.setdefault("field", "count")
    return out


def inputs(rows):
    """A task play's inputs as the plugin reads them: keys, axes, clicks, cursor moves, teleports (`yaw` 0 when
    unset: a teleport always turns the pawn), teleports next to an actor (`distance` 200 and `offset` 0 when unset,
    `face` only when set), either with `hold` only when set, waits in real time, named shots, map travels, view
    turns, wheel notches, mouse movement, and the stages of a contact (docs/task-probes.md, section 1.3): an actor
    pinned (`front` and `at` only when set), the engine's damage call, a start-named property set."""
    out = []
    for r in rows or []:
        row = {"t": float(r["t"])}
        if "teleport_to" in r:
            row.update(teleport_to=select(r["teleport_to"]), distance=float(r.get("distance", 200.0)),
                       offset=_floats(r.get("offset", ZERO)))
            if r.get("face") is not None:
                row["face"] = point(r["face"])
        elif "teleport" in r:
            row.update(teleport=_floats(r["teleport"]), yaw=float(r.get("yaw", 0.0)))
        elif "wait" in r:
            row.update(wait=float(r["wait"]))
        elif "shot" in r:
            row.update(shot=r["shot"])
        elif "map" in r:
            row.update(map=r["map"])
        elif "view" in r:
            row.update(view=_floats(r["view"]))
        elif "pin" in r:
            row.update(pin=select(r["pin"]), hold=float(r["hold"]), offset=_floats(r.get("offset", ZERO)))
            if r.get("front") is not None:
                row["front"] = float(r["front"])
            if r.get("at") is not None:
                row["at"] = point(r["at"])
        elif "damage" in r:
            row.update(damage=float(r["damage"]), to=select(r["to"]))
            if r.get("from") is not None:
                row["from"] = select(r["from"])
        elif "set" in r:
            row.update(set=r["set"], on=select(r["on"]), value=r["value"], all=bool(r.get("all", False)))
        elif "wheel" in r:
            row.update(wheel=int(r["wheel"]))
        elif "move" in r:
            row.update(move=_floats(r["move"]))
            if r.get("over") is not None:
                row["over"] = float(r["over"])
        elif "cursor" in r:
            row.update(cursor=_floats(r["cursor"]))
        elif "widget" in r:
            row.update(widget=r["widget"], click=True)
        elif "axis" in r:
            row.update(key=r["key"], axis=float(r["axis"]))
        else:
            row.update(key=r["key"], press=bool(r["press"]))
        if r.get("hold") is not None and ("teleport" in r or "teleport_to" in r):
            row["hold"] = float(r["hold"])
        out.append(row)
    return out


def waited(p):
    """The real seconds a play's waits add to it (0 for the checker's own plays)."""
    return sum(i["wait"] for i in p["inputs"] if "wait" in i) if isinstance(p, dict) else 0.0


def play(p):
    """A check's play: "look", "drive", "editor", "trace", or a task play with its defaults (inputs, map, args,
    every)."""
    if isinstance(p, str):
        return p
    return {"name": p["name"], "seconds": int(p["seconds"]), "inputs": inputs(p.get("inputs")), "map": p.get("map"),
            "args": list(p.get("args") or []), "every": float(p["every"]) if p.get("every") is not None else None}


def check(c):
    """A check with `required` (True), `weight` (1) and `needs` ([]); a probe's play and measure with their
    defaults."""
    out = dict(c)
    out.setdefault("required", True)
    out.setdefault("weight", 1)
    out.setdefault("needs", [])
    if out.get("kind") == "build":
        out.setdefault("fails_at_start", False)
    if out.get("kind") == "boot":
        out.setdefault("seconds", 60)
    if out.get("kind") == "file_exists":
        out.setdefault("min_count", 1)
    if out.get("kind") == "probe":
        out["play"] = play(out["play"])
        out["measure"] = measure(out["measure"])
    return out


def checks(task):
    """Every check of `task`, in order, each with its milestone's name: [(group, check)]."""
    return [(m["name"], check(c)) for m in task["milestones"] for c in m["checks"]]


def play_name(c):
    return c["play"] if isinstance(c["play"], str) else c["play"]["name"]


def relative(c):
    """How a probe's threshold depends on the start: "calibrate", "start" (start_times / start_plus) or None."""
    expect = c["expect"]
    if "calibrate" in expect:
        return "calibrate"
    return "start" if "start_times" in expect or "start_plus" in expect else None


def is_angle(field, turn=None):
    """Whether a measure's field is an angle (degrees, normalised to (-180, 180]): yaw, pitch, roll, rel_yaw:,
    world_yaw:, world_pitch:, world_roll:, and a reflected property (prop:) a probe compares with to_angle / to_axis."""
    return field in ("yaw", "pitch", "roll") or field.startswith(ANGLE_PREFIXES) or \
        (turn is not None and field.startswith("prop:"))


def fails_at_start(task):
    """The task's build check that says its start doesn't build (making it build is the task), or None."""
    return next((c for _, c in checks(task) if c["kind"] == "build" and c["fails_at_start"]), None)


def gating(task):
    """The names of the task's required probes (trace probes never gate)."""
    return {c["name"] for _, c in checks(task) if c["kind"] == "probe" and c["required"]
            and c["measure"]["probe"] != "trace"}


def still_works(task):
    """The names of the required probes of the task's still_works milestone."""
    required = gating(task)
    return {c["name"] for group, c in checks(task) if group == STILL_WORKS and c["name"] in required}

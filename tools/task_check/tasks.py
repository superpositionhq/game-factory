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
RUNTIME = ("pawn", "camera", "actors", "widgets", "components", "light", "grading", "spawns", "log")
SAMPLED = ("pawn", "camera", "actors", "widgets", "components", "light", "grading", "spawns")
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


def select(s):
    """An actor, widget or component selection as written, without unset keys, its `near` and `owner` filled in."""
    out = {}
    for k, v in s.items():
        if v is None:
            continue
        if k == "near":
            out[k] = {"point": point(v["point"]), "radius": float(v["radius"])}
        elif k == "owner":
            out[k] = select(v)
        else:
            out[k] = v
    return out


def measure(m):
    """A probe's measure with every optional field: window, at, agg, to_angle, to_axis (None when unset), `of`
    ("count") for selections, `field` ("count") for the log, `to` and `point` with their defaults."""
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
    """A task play's inputs as the plugin reads them: keys, axes, clicks, cursor moves, and teleports (`yaw` 0 when
    unset: a teleport always turns the pawn)."""
    out = []
    for r in rows or []:
        row = {"t": float(r["t"])}
        if "teleport" in r:
            row.update(teleport=_floats(r["teleport"]), yaw=float(r.get("yaw", 0.0)))
        elif "cursor" in r:
            row.update(cursor=_floats(r["cursor"]))
        elif "widget" in r:
            row.update(widget=r["widget"], click=True)
        elif "axis" in r:
            row.update(key=r["key"], axis=float(r["axis"]))
        else:
            row.update(key=r["key"], press=bool(r["press"]))
        out.append(row)
    return out


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
    """Whether a measure's field is an angle (degrees, normalised to (-180, 180]): yaw, pitch, roll, rel_yaw:, and a
    reflected property (prop:) a probe compares with to_angle / to_axis."""
    return field in ("yaw", "pitch", "roll") or field.startswith("rel_yaw:") or \
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

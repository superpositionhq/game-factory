"""Shared test helpers: tasks built from dicts, fake plays and a fake project (no Unreal)."""

import json
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from task_check import check, tasks, unreal  # noqa: E402

SEED = {"game": "metro-runner", "commit": "a" * 40, "reference": "b" * 40, "kind": "bug_fix"}
NO_FIX = {"game": "metro-runner", "commit": "a" * 40, "kind": "feature"}


def probe(name="hero_on_ground", play="look", measure=None, expect=None, **extra):
    return {"kind": "probe", "name": name, "describe": "The hero stands on the ground.", "play": play,
            "measure": measure or {"probe": "pawn", "field": "z", "window": [3, 18], "agg": "min"},
            "expect": expect or {"op": ">=", "value": 0}, **extra}


def task_with(*checks, seed=SEED, milestones=None):
    task = {"name": "probe-task", "title": "Probe", "instruction": "Keep the hero on the ground.", "seed": dict(seed),
            "milestones": milestones or [{"name": "graded", "checks": list(checks)}]}
    found = tasks.problems(task)
    if found:
        raise ValueError("; ".join(found))
    return task


def measure_of(data):
    return tasks.measure(data)


def first_check(task):
    return tasks.checks(task)[0][1]


def checked(name, kind, passed, detail="ok"):
    return {"name": name, "kind": kind, "passed": passed, "detail": detail}


def record(*checks):
    return {"checks": list(checks)}


def measuring(z, occluded=0, crash=False, seconds=41):
    """A play answer whose pawn stands at height `z` and whose actors query answers one row at `z`."""

    def play(seconds_, shots, queries):
        if crash:
            return None, "Fatal error: boom\n"
        found = {"format": "game-probe/1", "ended": "time", "seconds": float(seconds_), "map": "L", "inputs_sent": 0,
                 "screenshots": [], "track": [[i * 0.5, 0.0, 0.0, float(z)] for i in range(seconds)],
                 "camera": [], "measures": {}}
        for q in (queries or {}).get("queries", []):
            rows = [{"name": "Tower_1", "z": z}] if q["kind"] == "actors" else None
            value = {"occluded": occluded, "pawn_on_screen": 1} if q["kind"] == "camera" else None
            found["measures"][q["id"]] = [{"t": i * 0.5, **({"rows": rows} if rows else {"value": value})}
                                          for i in range(seconds)]
        return found, "LogInit: ready\n"

    return play


class FakeProject:
    """A scratch project whose build exits `build_exit` and whose plays answer `answer(seconds, shots, queries)` with
    (probe dict or None, log). Records its plays and editor scripts."""

    def __init__(self, answer=None, build_exit=0, editor=None, folder="."):
        self.answer, self.build_exit, self.editor = answer, build_exit, editor
        self.folder = __import__("pathlib").Path(folder)
        self.plays, self.builds, self.scripts, self.files = [], 0, [], {}

    def build(self, timeout):
        self.builds += 1
        return unreal.Result(self.build_exit, "error C2065" if self.build_exit else "built", 1.0)

    def play(self, seconds, shots, timeout, map=None, inputs=None, queries=None, args=(), every=None):
        self.plays.append({"seconds": seconds, "shots": shots, "map": map, "inputs": inputs, "queries": queries,
                           "args": list(args), "every": every})
        probe, log = self.answer(seconds, shots, queries) if self.answer else (None, "")
        files = {"probe.json": json.dumps(probe).encode()} if probe is not None else {}
        return unreal.Played(0, False, "", 1.0, probe, log, files)

    def editor_python(self, script, timeout):
        self.scripts.append(script)
        return self.editor(script, timeout)

    def read(self, relative):
        return self.files.get(relative)


def side(name, project, task):
    return check.Side(name, project, task, 60, 60, None, lambda *a: None)


def ran(output, exit_code=0):
    return unreal.Result(exit_code, output, 1.0)

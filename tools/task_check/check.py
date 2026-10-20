"""One task checked end to end (docs/task-check.md).

1. The task is read and validated (tasks.problems); its start (seed.commit) and reference (seed.reference) are
   materialized into a scratch folder outside the repo, each with the TaskProbe plugin (seeds.py).
2. The start is built first. A start that doesn't build makes the task INVALID, unless a build check says it doesn't
   (`fails_at_start`): then not building is the start failing the task, and the start is never played.
3. With a reference, the reference is checked as a solution would be: its checks in the task's order (a check whose
   `needs` failed isn't run and fails), build, boot, log_absent, file_exists and every probe against its threshold. A
   calibrated or start-relative threshold measures the start (its plays, played once) and, calibrated, the reference.
4. The start is checked on its probes (and on a `fails_at_start` build check).
5. verdict.verdict decides VALID or INVALID from the two sides' check rows.

The plays a probe names: "look", the idle play (20 s, no input, 6 screenshots); "drive", the scripted drive (22 s: W
1-6 s, D 6-8 s, W 8-13 s with a jump at 9 s, A 13-15 s, W 15-21 s; 8 screenshots); a task play (its own seconds, inputs,
map, args and sampling; 2 screenshots); "editor", one headless editor pass per side over every asset measure. Each is
played once per side, with the plugin's queries for every probe it serves. A boot check plays boot_<seconds>s (2
screenshots, no queries). Judges, trace probes and packaging are never part of a task check."""

import json
import re
import secrets
import time
from pathlib import Path

from . import FORMAT, probes, seeds, tasks, unreal, verdict

DRIVE = [{"t": 1.0, "key": "W", "press": True}, {"t": 6.0, "key": "W", "press": False},
         {"t": 6.0, "key": "D", "press": True}, {"t": 8.0, "key": "D", "press": False},
         {"t": 8.0, "key": "W", "press": True}, {"t": 9.0, "key": "SpaceBar", "press": True},
         {"t": 9.3, "key": "SpaceBar", "press": False}, {"t": 13.0, "key": "W", "press": False},
         {"t": 13.0, "key": "A", "press": True}, {"t": 15.0, "key": "A", "press": False},
         {"t": 15.0, "key": "W", "press": True}, {"t": 21.0, "key": "W", "press": False}]
PLAYS = {"look": (20, 6, None), "drive": (22, 8, DRIVE)}  # seconds, screenshots, inputs
JUDGES = ("judge", "code_judge", "actions_judge")
NOT_JUDGED = "not asked: judges never decide a task check"
SKIP = {"Binaries", "Intermediate", "Saved", "DerivedDataCache", ".git", ".vs"}  # left out of file_exists


def fatal(log):
    return bool(re.search(unreal.FATAL, log or ""))


class Side:
    """One side of a check ("start" or "reference"): its scratch project, built once, each play played once.
    `evidence`: where each play's probe.json, screenshots and log are kept (None: not kept)."""

    def __init__(self, name, project, task, timeout, build_timeout, evidence=None, log=print):
        self.name, self.project, self.task = name, project, task
        self.timeout, self.build_timeout = timeout, build_timeout
        self.evidence, self.log = evidence, log
        self.plan = probes.plan(task)
        self._build = None
        self.played = {}  # play name -> unreal.Played
        self._editor = None

    # -- the build ---------------------------------------------------------------------------------------------------

    def build(self):
        if self._build is None:
            self.log(f"  {self.name}: building")
            self._build = self.project.build(self.build_timeout)
            self.log(f"  {self.name}: {'built' if self._build.exit_code == 0 else 'build FAILED'} "
                     f"({self._build.seconds:.0f} s)")
            if self.evidence is not None and self._build.exit_code != 0:
                self._keep("build", {"build.log": self._build.output.encode("utf-8")})
        return self._build

    def built(self):
        return self.build().exit_code == 0

    def why_unbuilt(self):
        r = self.build()
        what = "the game as the task started" if self.name == "start" else "the reference game"
        return f"{what} didn't build ({'timed out' if r.timed_out else f'exit {r.exit_code}'})"

    # -- plays ---------------------------------------------------------------------------------------------------------

    def _keep(self, name, files):
        folder = Path(self.evidence) / self.name / name
        folder.mkdir(parents=True, exist_ok=True)
        for f, data in files.items():
            (folder / f).write_bytes(data)

    def _play(self, name, seconds, shots, inputs=None, map=None, queries=None, args=(), every=None):
        if name not in self.played:
            self.log(f"  {self.name}: playing {name} ({seconds} s)")
            found = self.project.play(seconds, shots, self.timeout, map=map or self.task.get("play_map"),
                                      inputs=inputs, queries=queries, args=args, every=every)
            self.played[name] = found
            if self.evidence is not None:
                self._keep(name, {**found.files, "play.log": found.log.encode("utf-8"),
                                  "output.txt": found.output.encode("utf-8")})
        return self.played[name]

    def boot(self, seconds):
        """The boot play of `seconds`: {ok, crashed, timed_out, log}."""
        p = self._play(f"boot_{seconds}s", seconds, 2)
        crashed = fatal(p.log)
        return {"ok": p.probe is not None and p.probe.get("ended") == "time" and not crashed, "crashed": crashed,
                "timed_out": p.timed_out, "log": p.log}

    def probe_play(self, play):
        """The play a probe names ("look", "drive", a task play), played once with the queries of every probe it
        serves."""
        name = play if isinstance(play, str) else play["name"]
        every = None if isinstance(play, str) else play["every"]
        queries = probes.query_file(self.plan.get(name, []), every)
        if isinstance(play, str):
            seconds, shots, inputs = PLAYS[play]
            return self._play(name, seconds, shots, inputs, queries=queries)
        return self._play(f"play_{name}", play["seconds"], 2, play["inputs"] or None, map=play["map"],
                          queries=queries, args=play["args"], every=every)

    def editor(self):
        """(the editor pass's results {measure id: result} or None; why none): one pass over every asset measure."""
        if self._editor is None:
            if not self.built():
                self._editor = None, "the project didn't build, so the editor couldn't open it"
            else:
                self.log(f"  {self.name}: editor pass")
                nonce = secrets.token_hex(16)
                ran = self.project.editor_python(probes.editor_script(probes.editor_items(self.task), nonce),
                                                 self.timeout)
                results = probes.editor_results(ran.output, self.project.read(probes.EDITOR_FILE), nonce)
                why = None if results is not None else \
                    f"the editor pass gave no result (exit {ran.exit_code}{', timed out' if ran.timed_out else ''})"
                if self.evidence is not None:
                    self._keep("editor", {"output.txt": ran.output.encode("utf-8")})
                self._editor = results, why
        return self._editor

    def value(self, check):
        """(probe `check`'s number on this side, or None; why none)."""
        measure = check["measure"]
        if measure["probe"] == "asset":
            results, why = self.editor()
            if results is None:
                return None, why
            return probes.reduce_asset(measure, results.get(probes.editor_id(measure)))
        if not self.built():
            return None, f"{self.why_unbuilt()}, so it wasn't played"
        p = self.probe_play(check["play"])
        return probes.measured(measure, p.probe, p.log)


class Grade:
    """The checks of one side as a solution's grade would run them. `mode` "reference": every check but judges, trace
    probes and packaging; "start": its probes and a `fails_at_start` build check. Thresholds are shared between the two
    grades (`thresholds`)."""

    def __init__(self, task, mode, start, reference, thresholds):
        self.task, self.mode, self.start, self.reference = task, mode, start, reference
        self.side = reference if mode == "reference" else start
        self.thresholds = thresholds
        self.measured = {}

    def threshold(self, check):
        if check["name"] not in self.thresholds:
            try:
                self.thresholds[check["name"]] = verdict.make_threshold(
                    check, lambda: self.start.value(check),
                    lambda: self.reference.value(check) if self.reference else (None, "the task has no reference"))
            except verdict.Uncalibrated as exc:
                self.thresholds[check["name"]] = exc
        found = self.thresholds[check["name"]]
        if isinstance(found, verdict.Uncalibrated):
            raise found
        return found

    def probe_check(self, check):
        try:
            limit, start, fix = self.threshold(check)
        except verdict.Uncalibrated as exc:
            value, _ = self.side.value(check)
            self.measured[check["name"]] = {"value": value, "threshold": None, "start": exc.start, "fix": exc.fix}
            return False, f"uncalibrated: {exc}"
        value, why = self.side.value(check)
        self.measured[check["name"]] = {"value": value, "threshold": limit, "start": start, "fix": fix}
        passed = value is not None and verdict.passes(value, check["expect"]["op"], limit)
        return passed, verdict.describe(check, value, limit, start, fix, why)

    def check(self, check):
        kind = check["kind"]
        if kind in JUDGES:
            return True, NOT_JUDGED
        if kind == "probe" and check["measure"]["probe"] == "trace":
            return True, "not asked: a trace probe reads an agent's own calls"
        if self.mode == "start":
            if kind == "build" and check["fails_at_start"]:
                return (True, "the start built") if self.start.built() else (False, self.start.why_unbuilt())
            if kind != "probe":
                return True, "not asked: the start is checked on its probes"
            return self.probe_check(check)
        side = self.side
        if kind == "build":
            r = side.build()
            return r.exit_code == 0, "built" if r.exit_code == 0 else \
                f"build failed ({'timed out' if r.timed_out else f'exit {r.exit_code}'})"
        if kind == "boot":
            if not side.built():
                return False, f"{side.why_unbuilt()}, so it wasn't played"
            p = side.boot(check["seconds"])
            if p["ok"]:
                return True, f"ran {check['seconds']} s with no crash or fatal error"
            return False, "crashed" if p["crashed"] else ("timed out" if p["timed_out"] else "didn't finish its run")
        if kind == "log_absent":
            if not side.built():
                return False, f"{side.why_unbuilt()}, so it wasn't played"
            hits = [line for line in side.boot(60)["log"].splitlines() if re.search(check["pattern"], line)]
            return not hits, f"{len(hits)} matching log line(s)" + (f": {hits[0][:200]}" if hits else "")
        if kind == "file_exists":
            root = side.project.folder
            found = [p for p in root.glob(check["glob"]) if p.is_file()
                     and not SKIP.intersection(p.relative_to(root).parts)]
            return len(found) >= check["min_count"], f"{len(found)} file(s) match"
        if kind == "package":
            return True, "not asked: a task check never packages the game"
        if kind == "probe":
            return self.probe_check(check)
        raise ValueError(f"no check kind {kind}")

    def run(self):
        """{"checks": [{name, kind, passed, required, detail, group}], "probes": {name: {value, threshold, start,
        fix}}}."""
        rows, passed = [], {}
        for group, check in tasks.checks(self.task):
            missing = [n for n in check["needs"] if not passed.get(n)]
            if missing:
                ok, detail = False, f"not run: needs {missing[0]}"
            else:
                try:
                    ok, detail = self.check(check)
                except (OSError, RuntimeError, ValueError) as exc:
                    ok, detail = False, f"the checker failed ({type(exc).__name__}: {str(exc)[:200]})"
            passed[check["name"]] = bool(ok)
            rows.append({"name": check["name"], "kind": check["kind"], "passed": bool(ok),
                         "required": check["required"], "detail": str(detail)[:700], "group": group})
        return {"checks": rows, "probes": self.measured}


def start_unbuilt(task, why):
    """The start's grade when it doesn't build and the task says so: that build check failed, nothing else run."""
    group, build = next((g, c) for g, c in tasks.checks(task) if c["kind"] == "build" and c["fails_at_start"])
    return {"checks": [{"name": build["name"], "kind": "build", "passed": False, "required": build["required"],
                        "detail": str(why)[:700], "group": group}], "probes": {}}


def probe_values(task, reference, start):
    """{probe: {group, required, op, expect, start, reference, threshold, start_passed, reference_passed}} from the two
    grades' measures (trace probes left out)."""

    def passed(grade, name):
        return next((r["passed"] for r in (grade or {}).get("checks", []) if r["name"] == name), None)

    out = {}
    for group, check in tasks.checks(task):
        if check["kind"] != "probe" or check["measure"]["probe"] == "trace":
            continue
        name = check["name"]
        ref = ((reference or {}).get("probes") or {}).get(name) or {}
        own = ((start or {}).get("probes") or {}).get(name) or {}
        out[name] = {"group": group, "required": check["required"], "op": check["expect"]["op"],
                     "expect": check["expect"], "start": own.get("value", ref.get("start")),
                     "reference": ref.get("value") if reference else None,
                     "threshold": ref.get("threshold", own.get("threshold")),
                     "start_passed": passed(start, name), "reference_passed": passed(reference, name) if reference
                     else None}
    return out


def check_task(repo, task, raw, scratch, out_dir, keep=False, direct=False, timeout=1800, build_timeout=3600,
               log=print, clock=time.time):
    """Check one task (a dict read from `repo`'s tasks branch, its file's bytes `raw`): its result (written to
    <out_dir>/<name>.json, its plays' files under <out_dir>/<name>/)."""
    started = clock()
    name = task.get("name", "?")
    result = {"format": FORMAT, "task": name, "game": (task.get("seed") or {}).get("game"),
              "task_sha256": tasks.digest(raw), "verdict": None, "reasons": [], "notes": [], "start": None,
              "reference": None, "probes": {}, "start_checks": [], "reference_checks": [],
              "evidence": f"{name}/", "at": None, "seconds": None}

    def finish(state, reasons, notes=()):
        result.update(verdict=state, reasons=list(reasons), notes=list(notes), seconds=round(clock() - started, 1),
                      at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / f"{name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    found = tasks.problems(task)
    if found:
        return finish("INVALID", [f"the task doesn't validate: {p}" for p in found[:5]])
    seed = task["seed"]
    evidence = Path(out_dir) / name
    seeds.remove(evidence)
    scratch = Path(scratch)
    sides = {}
    try:
        for side, commit in (("start", seed["commit"]), ("reference", seed.get("reference"))):
            if commit is None:
                continue
            try:
                sha = seeds.resolve(repo, commit)
            except RuntimeError:
                return finish("INVALID", [f"seed.{'commit' if side == 'start' else 'reference'} {commit[:12]} isn't a "
                                          f"commit of {Path(repo).name} (fetch it, or fix the task)"])
            folder = scratch / side
            log(f"  {side}: materializing {sha[:12]} into {folder}")
            made = seeds.materialize(repo, sha, folder)
            try:
                seeds.add_probe(folder)
            except seeds.WrongEngine as exc:
                return finish("INVALID", [f"{side}: {exc}"])
            machine = unreal.Machine.for_project(folder, direct)
            project = unreal.Project(folder, machine, f"{name} {side}")
            sides[side] = Side(side, project, task, timeout, build_timeout, evidence, log)
            result[side] = {"commit": sha, "files": made["files"], "lfs_linked": made["linked"],
                            "lfs_copied": made["copied"], "overlaid": made["overlaid"], "engine": str(machine.engine),
                            "slots": "ue-heavy" if machine.ue_heavy else "direct"}
        start, reference = sides["start"], sides.get("reference")
        build = tasks.fails_at_start(task)
        if not start.built():
            result["start"]["built"] = False
            if build is None:
                return finish("INVALID", [f"start doesn't build: {start.why_unbuilt()}"])
        else:
            result["start"]["built"] = True
        thresholds = {}
        ref_grade = None
        if reference is not None:
            ref_grade = Grade(task, "reference", start, reference, thresholds).run()
            result["reference"]["built"] = reference.built()
        if build is not None and not start.built():
            start_grade = start_unbuilt(task, start.why_unbuilt())
        else:
            start_grade = Grade(task, "start", start, reference, thresholds).run()
        valid, why, notes = verdict.verdict(task, ref_grade, start_grade)
        result.update(probes=probe_values(task, ref_grade, start_grade), start_checks=start_grade["checks"],
                      reference_checks=ref_grade["checks"] if ref_grade else [])
        return finish("VALID" if valid else "INVALID", why, notes)
    except (OSError, RuntimeError, ValueError) as exc:
        return finish("ERROR", [f"the checker couldn't check it: {type(exc).__name__}: {str(exc)[:400]}"])
    finally:
        if not keep:
            seeds.remove(scratch)

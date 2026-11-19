"""One task checked end to end (docs/task-check.md).

1. The task is read and validated (tasks.problems); its start (seed.commit) and reference (seed.reference) are
   materialized into a scratch folder outside the repo, each with the TaskProbe plugin (seeds.py).
2. The start is built first. A start that doesn't build makes the task INVALID, unless a build check says it doesn't
   (`fails_at_start`): then not building is the start failing the task, and the start is never played.
3. With a reference, the reference is checked as a solution would be: its checks in the task's order (a check whose
   `needs` failed isn't run and fails), build, boot, log_absent, file_exists and every probe against its threshold. A
   calibrated or start-relative threshold measures the start (its plays, played once) and, calibrated, the reference.
4. The start is checked on its probes (and on a `fails_at_start` build check).
   On either side a probe of a task play whose inputs didn't land (probe.json `inputs_missed`) fails, and is a task
   error when the reference's play missed one too; a probe whose selector reads nothing in the reference's play is a
   task error (Grade.landing, Grade.unreadable), as the cloud grader makes them.
5. verdict.verdict decides VALID or INVALID from the two sides' check rows and task errors.

A run of several tasks shares one scratch copy per commit (Builds): a commit that is one task's start and another's
reference, or two tasks' start, is materialized and built once and kept until the last task that needs it is done.
The copy is the commit exactly as committed either way, so sharing it changes no result.

The plays a probe names: "look", the idle play (20 s, no input, 6 screenshots); "drive", the scripted drive (22 s: W
1-6 s, D 6-8 s, W 8-13 s with a jump at 9 s, A 13-15 s, W 15-21 s; 8 screenshots); a task play (its own seconds, inputs,
map, args and sampling; 2 screenshots, or the most a judge check showing it asks); "editor", one headless editor pass per side over every asset measure. Each is
played once per side, with the plugin's queries for every probe it serves; a task play whose `after` names other task
plays is played after them on the same side (they run first, a failed one too), as the Lab's grader plays it. A boot check plays boot_<seconds>s (2
screenshots, no queries). Every task's boot is a 60 s idle play and "look" is the first 20 s of the same idle game, so
when no look probe reads the log, a side that boots (the reference; a start is never booted) plays one 60 s idle play
with look's queries for both (Side.idle): the boot check reads it whole, and look reads its first 20 s only
(first_seconds), one game launch instead of two. Judges, trace probes and packaging never decide a task check: a
`judge` check's plays are played on both sides and the screenshots its judge would see are saved under
<name>/judge-shots/<check>/ (judges.py) for whoever runs the check to look at and answer (`judge_shots`). A `seen`
probe (text the Lab's visual model reads from a named shot) is read by the task's writer instead: its crops are saved
under <name>/seen-shots/<check>/ (seen.py), and once the writer has answered, their answer is the probe's measure on
each side; until then the probe measures nothing, and a task with a required one isn't VALID."""

import json
import math
import re
import secrets
import time
from pathlib import Path

from . import FORMAT, judges, probes, seeds, seen, tasks, unreal, verdict
from .digest import canonical_digest

DRIVE = [{"t": 1.0, "key": "W", "press": True}, {"t": 6.0, "key": "W", "press": False},
         {"t": 6.0, "key": "D", "press": True}, {"t": 8.0, "key": "D", "press": False},
         {"t": 8.0, "key": "W", "press": True}, {"t": 9.0, "key": "SpaceBar", "press": True},
         {"t": 9.3, "key": "SpaceBar", "press": False}, {"t": 13.0, "key": "W", "press": False},
         {"t": 13.0, "key": "A", "press": True}, {"t": 15.0, "key": "A", "press": False},
         {"t": 15.0, "key": "W", "press": True}, {"t": 21.0, "key": "W", "press": False}]
PLAYS = {"look": (20, 6, None), "drive": (22, 8, DRIVE)}  # seconds, screenshots, inputs
# seconds a play may run past its own seconds (boot, shader compiles) when that is longer than --timeout: a task play
# may last up to 1200 s (validate-game.py PLAY_SECONDS)
PLAY_MARGIN = 600
# A mobile game's drive (docs/task-probes.md, section 1.1): the same route by touch, a left thumb pushing where a virtual
# stick usually is (down at its middle, over to a side, held there) and a right thumb's tap for the jump.
STICK = [0.15, 0.75]


def _push(t, to, held):
    return {"t": t, "drag": [STICK, to], "over": 0.2, "hold": held - 0.3, "finger": 0}


MOBILE_DRIVE = [_push(1.0, [0.15, 0.6], 5.0), _push(6.0, [0.25, 0.75], 2.0), _push(8.0, [0.15, 0.6], 5.0),
                {"t": 9.0, "tap": [0.85, 0.75], "finger": 1}, _push(13.0, [0.05, 0.75], 2.0),
                _push(15.0, [0.15, 0.6], 6.0)]


def own_play(play, project):
    """The checker's own play `play` ("look", "drive") on `project`: (seconds, screenshots, inputs); a mobile game's
    drive is by touch."""
    seconds, shots, inputs = PLAYS[play]
    mobile = getattr(project, "mobile", None)
    return seconds, shots, MOBILE_DRIVE if play == "drive" and mobile is not None and mobile() else inputs


JUDGES = ("judge", "code_judge", "actions_judge")   # actions_judge: retired, still skipped in older tasks
NOT_JUDGED = "not asked: judges never decide a task check"
SKIP = {"Binaries", "Intermediate", "Saved", "DerivedDataCache", ".git", ".vs"}  # left out of file_exists


def session(first, named):
    """What a continuing play's first session (play `named`, an unreal.Played) left for it: {play, clean, text,
    saved}. Clean: it ran its time out, or the game quit by its own action (the probe ended at the game's shutdown,
    exit 0, no crash), so the game's own save-on-quit ran; saved: the files it wrote under Saved."""
    probe = first.probe or {}
    crashed = fatal(first.log)
    ok = first.probe is not None and probe.get("ended") == "time" and not crashed
    clean = ok or (probe.get("ended") == "shutdown" and first.exit_code == 0 and not crashed and not first.timed_out)
    text = "timed out" if first.timed_out else "crashed" if crashed else "wrote no probe file" if first.probe is None \
        else f"ended by {probe.get('ended')} at {probes.fmt(probes.ended(probe))} s, exit {first.exit_code}"
    return {"play": named, "clean": bool(clean), "text": text, "saved": first.saved}


def session_unclean(found):
    """Why a continuing play's first session (session) didn't end cleanly, or None."""
    if found["clean"]:
        return None
    return f"its first session (play {found['play']}) did not end cleanly ({found['text']}), so the game never " \
           "quit as a player's game does and nothing it should have saved can be trusted"


def session_empty(found):
    """Why a continuing play's first session (session) left nothing to load: it wrote no file under the game's Saved
    folder; None when it wrote one, or the listing can't tell."""
    if not found["clean"] or found["saved"] != []:
        return None
    return f"its first session (play {found['play']}) wrote nothing under the game's Saved folder, so the " \
           "relaunched game had nothing to load"


def fatal(log):
    return bool(re.search(unreal.FATAL, log or ""))


def first_seconds(probe, seconds):
    """`probe` (a play's probe.json) as a play of only its first `seconds` would have written it: rows and samples after
    that dropped, its length cut to them."""
    if not isinstance(probe, dict):
        return probe
    cut = dict(probe)
    for name in ("track", "camera"):
        rows = probe.get(name)
        if isinstance(rows, list):
            cut[name] = [r for r in rows if not (isinstance(r, list) and r and isinstance(r[0], int | float)
                                                 and r[0] > seconds + 1e-6)]
    if isinstance(probe.get("measures"), dict):
        cut["measures"] = {q: [s for s in samples if not (isinstance(s, dict) and isinstance(s.get("t"), int | float)
                                                          and s["t"] > seconds + 1e-6)] if isinstance(samples, list)
                           else samples for q, samples in probe["measures"].items()}
    length = probe.get("seconds")
    if isinstance(length, int | float) and not isinstance(length, bool) and length >= seconds - 1e-6:
        cut["seconds"], cut["ended"] = float(seconds), "time"
    return cut


class Built:
    """A scratch project shared by every task of a run whose start or reference is its commit: built at most once,
    played as often as the tasks ask (each task's plays carry its own queries)."""

    def __init__(self, project):
        self.project = project
        self._build = None

    def has_built(self):
        return self._build is not None

    def build(self, timeout):
        if self._build is None:
            self._build = self.project.build(timeout)
        return self._build

    def __getattr__(self, name):
        return getattr(self.project, name)


class Builds:
    """The scratch copies of one run, one per commit under `scratch`, each a Built. `get` materializes and adds the
    TaskProbe plugin on first use; `release` deletes a copy no later task needs; `close` deletes them all."""

    def __init__(self, repo, scratch, direct=False, log=print):
        self.repo, self.scratch, self.direct, self.log = repo, Path(scratch), direct, log
        self.copies = {}  # sha -> (Built, info) or the seeds.WrongEngine its plugin refused

    def get(self, sha, needed=()):
        """(Built, info) for commit `sha`; raises seeds.WrongEngine for a project that isn't UE 5.7. When the disk is
        below the machine's floor, copies other than `needed` (this task's commits) are deleted first."""
        if sha in self.copies:
            self.log(f"  {sha[:12]}: reusing the copy already made in this run")
        else:
            self._room(set(needed) | {sha})
            folder = self.scratch / sha[:12]
            self.log(f"  {sha[:12]}: materializing into {folder}")
            made = seeds.materialize(self.repo, sha, folder)
            try:
                seeds.add_probe(folder)
            except seeds.WrongEngine as exc:
                self.copies[sha] = exc
            else:
                machine = unreal.Machine.for_project(folder, self.direct)
                self.copies[sha] = (Built(unreal.Project(folder, machine, sha[:12])),
                                    {"files": made["files"], "lfs_linked": made["linked"],
                                     "lfs_copied": made["copied"], "engine": str(machine.engine),
                                     "slots": "ue-heavy" if machine.ue_heavy else "direct"})
        found = self.copies[sha]
        if isinstance(found, Exception):
            raise found
        return found

    def _room(self, needed):
        try:
            unreal.gfroot.check_free(str(self.scratch), "task check")
            return
        except SystemExit:
            for sha in [s for s in self.copies if s not in needed]:
                self.log(f"  {sha[:12]}: low on disk, deleting its copy (a later task rebuilds it)")
                self.release(sha)
        unreal.gfroot.check_free(str(self.scratch), "task check")

    def release(self, sha):
        if self.copies.pop(sha, None) is not None:
            seeds.remove(self.scratch / sha[:12])

    def close(self):
        self.copies.clear()
        seeds.remove(self.scratch)


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
        self.sessions = {}  # a continuing task play's name -> what its first session left (session)
        self._editor = None
        self.crops = {}  # a seen check's name -> its crops on this side (seen.crops)
        # what the writer answered for seen checks (seen.kept), set by the task check; None: no answer is read here (a
        # task try), so seen checks are not asked
        self.answers = None
        self.watching = None  # the one play shown in a window on this side (watch_play), by the name _play gets

    # -- the build ---------------------------------------------------------------------------------------------------

    def build(self):
        if self._build is None:
            again = getattr(self.project, "has_built", lambda: False)()
            if not again:
                self.log(f"  {self.name}: building")
            self._build = self.project.build(self.build_timeout)
            waited = getattr(self._build, "waited", 0.0)
            self.log(f"  {self.name}: {'built' if self._build.exit_code == 0 else 'build FAILED'} "
                     f"({self._build.seconds:.0f} s{', built earlier in this run' if again else ''}"
                     f"{f', {waited:.0f} s of it waiting for a machine slot' if waited >= 1 and not again else ''})")
            if self.evidence is not None and self._build.exit_code != 0:
                self._keep("build", {"build.log": self._build.output.encode("utf-8")})
        return self._build

    def built(self):
        return self.build().exit_code == 0

    def why_unbuilt(self):
        r = self.build()
        what = {"start": "the game as the task started", "reference": "the reference game"}.get(
            self.name, f"the agent's game ({self.name})")
        return f"{what} didn't build ({'timed out' if r.timed_out else f'exit {r.exit_code}'})"

    # -- plays ---------------------------------------------------------------------------------------------------------

    def _keep(self, name, files):
        folder = Path(self.evidence) / self.name / name
        folder.mkdir(parents=True, exist_ok=True)
        for f, data in files.items():
            (folder / f).write_bytes(data)

    def _play(self, name, seconds, shots, inputs=None, map=None, queries=None, args=(), every=None, waits=0.0,
              session=False, fresh=False, attended=False):
        """A play, once per name; `waits`: the real seconds its waits add (a task play's), which its timeout gets on
        top, and a long play at least its own seconds and PLAY_MARGIN; `session`: a continuing play's first session,
        played on a cleared save (unreal.Project.play); `fresh`: a task play marked `fresh`, played on a cleared save
        too; `attended`: a task play marked `attended`, launched without -unattended."""
        if name not in self.played:
            self.log(f"  {self.name}: playing {name} ({seconds} s" + (f", {waits:g} s waiting" if waits else "") + ")")
            found = self.project.play(seconds, shots, max(self.timeout, seconds + PLAY_MARGIN) + math.ceil(waits),
                                      map=map or self.task.get("play_map"),
                                      inputs=inputs, queries=queries, args=args, every=every,
                                      **({"session": True} if session else {}), **({"fresh": True} if fresh else {}),
                                      **({"attended": True} if attended else {}),
                                      **({"watch": True} if name == self.watching else {}))
            self.played[name] = found
            waited = getattr(found, "waited", 0.0)
            self.log(f"  {self.name}: played {name} in {found.seconds:.0f} s"
                     + (f" ({waited:.0f} s of it waiting for a machine slot)" if waited >= 1 else ""))
            if self.evidence is not None:
                self._keep(name, {**found.files, "play.log": found.log.encode("utf-8"),
                                  "output.txt": found.output.encode("utf-8")})
        return self.played[name]

    def judge_plays(self, check):
        """{play name: (probe dict or None, {file: bytes})} of every play judge check `check` is shown on this side:
        its own task plays (the probes' own when they name the same play, which is the same play), else the idle play
        and the drive, each played whole (never the boot cut to look's seconds, whose screenshots span the boot)."""
        out = {}
        for play, _, _ in judges.plays(check):
            if isinstance(play, str):
                seconds, shots, inputs = own_play(play, self.project)
                p = self._play(play, seconds, shots, inputs, queries=probes.query_file(self.plan.get(play, [])))
            else:
                p = self.probe_play(play)
            out[play if isinstance(play, str) else play["name"]] = (p.probe, p.files)
        return out

    def idle(self, seconds):
        """Whether the boot play of `seconds` also serves "look": look is the first part of the same idle game, so one
        play does when the boot is at least as long and no look probe reads the play's log (a log covers the whole
        play, so it can't be cut to look's seconds)."""
        return "look" in self.plan and seconds >= PLAYS["look"][0] and not any(
            tasks.play_name(c) == "look" and c["measure"]["probe"] == "log" for c in probes.probes(self.task))

    def boot(self, seconds):
        """The boot play of `seconds`: {ok, crashed, timed_out, log}."""
        if self.idle(seconds) and "look" not in self.played:
            p = self._play(f"boot_{seconds}s", seconds, PLAYS["look"][1],
                           queries=probes.query_file(self.plan["look"]))
        else:
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
            seconds, shots, inputs = own_play(play, self.project)
            booted = next((b for b in self.boots() if play == "look" and self.idle(b)
                           and f"boot_{b}s" in self.played), None)
            if booted is not None:
                p = self.played[f"boot_{booted}s"]
                return unreal.Played(p.exit_code, p.timed_out, p.output, p.seconds, first_seconds(p.probe, seconds),
                                     p.log, p.files)
            return self._play(name, seconds, shots, inputs, queries=queries)
        # every play it names in `after` played on this copy first, and ended, a failed one too (docs/task-probes.md
        # 1.1): a side's plays share the copy's Saved folder, so a play that reads a save another writes finds it
        named = tasks.task_plays(self.task)
        for before in play.get("after") or ():
            self.probe_play(named[before])
        # a play that `continues` another's session is played after a first session of its own: the game's save state
        # cleared, the play it names played (evidence play_<name>-first, never a reading of that play) and quit, then
        # this play launched as a new process on the copy (docs/task-probes.md 1.1)
        # the play it continues may itself continue another: the sessions are played earliest first, the first on a
        # cleared save, each later one launched on what the one before left; the session said is the last one, unclean
        # when any did not end cleanly (the earliest such named)
        if play.get("continues") and name not in self.sessions:
            chain, why = tasks.validator().session_chain(named, name)
            if why:
                raise ValueError(why)
            unclean, said = None, None
            for i, first in enumerate(chain):
                last = i == len(chain) - 1
                ended = self._play(f"play_{name}-first" if last else f"play_{name}-first-{len(chain) - i}",
                                   first["seconds"], 1, first["inputs"] or None, map=first["map"],
                                   args=first["args"], every=first["every"], waits=tasks.waited(first),
                                   session=i == 0, attended=first.get("attended") is True)
                said = session(ended, first["name"])
                unclean = unclean or (None if said["clean"] else said)
            self.sessions[name] = said if unclean is None else {**said, "clean": False, "play": unclean["play"],
                                                                "text": unclean["text"]}
        shots = judges.play_shots(self.task).get(name, 2)  # as the grader plays it: a judge showing it asks more
        if self.watching == f"play_{name}":
            shots = max(shots, WATCH_SHOTS)  # a watched play leaves a strip of pictures to look at afterwards
        # a `fresh` play starts from a cleared save: what earlier plays of the side saved never changes its start
        return self._play(f"play_{name}", play["seconds"], shots, play["inputs"] or None, map=play["map"],
                          queries=queries, args=play["args"], every=every, waits=tasks.waited(play),
                          fresh=play.get("fresh") is True, attended=play.get("attended") is True)

    def carried(self, play):
        """Why a continuing task play's readings can't stand on the reference, or None: its first session didn't end
        cleanly, or wrote nothing under Saved (the task's own fix then carries nothing over). On any other side the
        play is read as it measured, as the cloud grader reads it: its threshold made from the start's reading, and its
        check failed by Grade.landing when the first session didn't end cleanly."""
        found = None if isinstance(play, str) else self.sessions.get(play["name"])
        if found is None or self.name != "reference":
            return None
        why = session_unclean(found) or session_empty(found)
        return why and f"in the reference's play {play['name']}, {why}: the task's own fix carries nothing over " \
                       "to the next session"

    def unclean(self, play):
        """Why a continuing task play's first session on this side didn't end cleanly, or None."""
        found = None if isinstance(play, str) else self.sessions.get(play["name"])
        return session_unclean(found) if found is not None else None

    def boots(self):
        """The boot plays this task's checks run (seconds): its boot checks, and 60 s for a log_absent check."""
        found = []
        for _, check in tasks.checks(self.task):
            seconds = check.get("seconds") if check["kind"] == "boot" else 60 if check["kind"] == "log_absent" else None
            if seconds is not None and seconds not in found:
                found.append(seconds)
        return found

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

    def shot_size(self):
        """The size the Lab keeps this side's play shots within: a mobile game's (its phone size halved, 960x540 or
        540x960), else None (a desktop play's are taken at that size already)."""
        mobile = getattr(self.project, "mobile", None)
        held = mobile() if callable(mobile) else None
        return None if held is None else (unreal.SHOT_SIZE if held == "landscape" else unreal.SHOT_SIZE[::-1])

    def seen_crops(self, check):
        """{shot: (crop or None, why none)} of seen check `check` on this side (seen.crops): its task play, played once
        (the probes' own), each named shot cropped as the Lab crops it."""
        name = check["name"]
        if name not in self.crops:
            measure, play = check["measure"], check["play"]
            if not self.built():
                why = f"{self.why_unbuilt()}, so it wasn't played"
                self.crops[name] = {s: (None, why) for s in seen.shots(measure)}
            else:
                p = self.probe_play(play)
                carried = self.carried(play)
                ended = "wrote no probe file" if p.probe is None else f"ended at {probes.fmt(probes.ended(p.probe))} s"
                self.crops[name] = seen.crops(measure, {} if carried else p.files, lambda s: carried or (
                    f"play {play['name']} took no shot named {s} (it {ended})"), self.shot_size())
        return self.crops[name]

    def value(self, check):
        """(probe `check`'s number on this side, or None; why none)."""
        measure = check["measure"]
        if measure["probe"] == "asset":
            results, why = self.editor()
            if results is None:
                return None, why
            return probes.reduce_asset(measure, results.get(probes.editor_id(measure)))
        if measure["probe"] == "seen":
            found = self.seen_crops(check)
            missing = next((why for _, why in found.values() if why), None)
            if missing:
                return None, missing
            return seen.read(check, self.name, found, (self.answers or {}).get(check["name"]))
        if not self.built():
            return None, f"{self.why_unbuilt()}, so it wasn't played"
        play = check["play"]
        p = self.probe_play(play)
        carried = self.carried(play)
        if carried:
            return None, carried
        value, why = probes.measured(measure, p.probe, p.log)
        if value is None and why and why.startswith("no samples in the window"):  # the play's map not loaded: said so
            own = None if isinstance(play, str) else play
            travels = bool(own) and any("map" in i for i in own["inputs"])
            why = probes.map_unloaded(p.probe, (own and own["map"]) or self.task.get("play_map"), travels) or why
        return value, why


class Grade:
    """The checks of one side as a solution's grade would run them. `mode` "reference": every check but judges, trace
    probes and packaging, of the reference or of `side` (an agent's game, task-try.py); "start": its probes and a
    `fails_at_start` build check. Thresholds are shared between the grades (`thresholds`)."""

    def __init__(self, task, mode, start, reference, thresholds, side=None):
        self.task, self.mode, self.start, self.reference = task, mode, start, reference
        self.side = side or (reference if mode == "reference" else start)  # `side`: an agent's game graded as a solution
        self.thresholds = thresholds
        self.measured = {}
        self.task_errors = {}  # check -> why no version of the game can pass it (task_error)
        self.uncalibrated = {}  # probe -> why no threshold can be made for it: the cloud grades no run of the task

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
        if seen.is_seen(check):  # a trusted side's reading that the Lab makes a task error
            broken = self.seen_untrusted(check)
            if broken:
                return self.task_error(check, broken)
        try:
            limit, start, fix = self.threshold(check)
        except verdict.Uncalibrated as exc:
            value, _ = self.side.value(check)
            self.measured[check["name"]] = {"value": value, "threshold": None, "start": exc.start, "fix": exc.fix}
            broken = self.unreadable(check)
            if broken:
                return self.task_error(check, broken)
            if not (seen.is_seen(check) and seen.unanswered(str(exc))):  # (a seen check waits for its answers)
                self.uncalibrated[check["name"]] = str(exc)
            return False, f"uncalibrated: {exc}"
        value, why = self.side.value(check)
        self.measured[check["name"]] = {"value": value, "threshold": limit, "start": start, "fix": fix}
        landed = self.landing(check["play"])
        if landed:  # what it measured is of a play that didn't do what the task says
            broken, said = landed
            return self.task_error(check, broken) if broken else (False, f"{check['describe']} | {said}")
        passed = value is not None and verdict.passes(value, check["expect"]["op"], limit)
        # a selector that matched nothing in the graded play: the game's doing, or the task's when the reference's play
        # matches nothing either (a 0 of nothing that passes is an answer, never checked: probes.zero_when_none)
        if self.read_nothing(check, self.side) and (not passed or not probes.zero_when_none(check["measure"])):
            broken = self.unreadable(check, limit)
            if broken:
                return self.task_error(check, broken)
        return passed, verdict.describe(check, value, limit, start, fix, why)

    # -- the cloud grader's task errors: a check no version of the game can pass ---------------------------------------

    def seen_untrusted(self, check):
        """Why seen check `check` is a task error by the writer's answer on a side the Lab reads as trusted (seen.
        untrusted): the reference, and the start when the threshold is relative to it; None when neither is."""
        trusted = [s for s in (self.reference, self.start if tasks.relative(check) else None)
                   if s is not None and s.answers is not None and s.built()]
        for side in trusted:
            why = seen.untrusted(check, side.name, side.seen_crops(check), side.answers.get(check["name"]))
            if why:
                return why
        return None

    def task_error(self, check, why):
        """(False, its detail) of a check no version of the game can pass: the task's fault, kept in task_errors (a
        task with one is INVALID: verdict.verdict)."""
        self.task_errors[check["name"]] = why
        return False, f"{verdict.TASK_ERROR}: {check['describe']} | {why}"

    @staticmethod
    def finished(p):
        """Whether a play ran its whole time (no crash, no early end)."""
        return p.probe is not None and p.probe.get("ended") == "time" and not fatal(p.log)

    def landing(self, play):
        """None when task play `play`'s inputs all landed on the graded side (or it can't say, or `play` is look, drive
        or editor); else (why it is a task error, or None; the check's detail when it isn't): a missed input fails the
        check as the graded game's, unless the reference's play missed one too (reference_unlanded)."""
        if isinstance(play, str) or not self.side.built():
            return None
        found = self.side.probe_play(play)
        if self.side is self.reference and self.reference.carried(play):  # the task's own fix carries nothing over
            return self.reference.carried(play), None
        unclean = self.side.unclean(play)
        if unclean:
            broken = self.reference_unlanded(play)
            return (broken, None) if broken else (None, f"the play's {unclean.removeprefix('its ')}")
        rows = probes.missed(found.probe)
        if not rows:
            return None
        broken = self.reference_unlanded(play)
        if broken:
            return broken, None
        return None, f"the play's input did not land: {probes.missed_text(rows)}"

    def reference_unlanded(self, play):
        """Why task play `play` can't be driven even on the task's own fix (its reference play, which finished its run,
        missed an input), or None."""
        ref = self.reference
        if isinstance(play, str) or ref is None or not ref.built():
            return None
        found = ref.probe_play(play)
        carried = ref.carried(play)
        if carried:
            return carried
        rows = probes.missed(found.probe) if self.finished(found) else None
        if not rows:
            return None
        return f"in the reference's play {play['name']}, an input did not land ({probes.missed_text(rows)}): the " \
               "task's own fix can't be driven by its play"

    def read_nothing(self, check, side):
        """Why probe `check`'s selector read nothing in its whole play on `side` (probes.reads_nothing), or None."""
        if check["measure"]["probe"] not in probes.SELECTING or not side.built():
            return None
        return probes.reads_nothing(check["measure"], side.probe_play(check["play"]).probe)

    def unreadable(self, check, limit=None):
        """Why no version of the game can pass probe `check` (a task error), or None: its selector reads nothing in the
        reference's play of it (a play that finished its run); for a measure that reads 0 of no match
        (probes.zero_when_none), unless 0 passes its threshold `limit`. None when the task has no reference."""
        ref = self.reference
        if ref is None or check["measure"]["probe"] not in probes.SELECTING or not ref.built():
            return None
        play = ref.probe_play(check["play"])
        why = probes.reads_nothing(check["measure"], play.probe) if self.finished(play) else None
        if why is None or (probes.zero_when_none(check["measure"]) and limit is not None
                           and verdict.passes(0.0, check["expect"]["op"], limit)):
            return None
        name = tasks.play_name(check)
        said = "the task's own fix fails it" if probes.zero_when_none(check["measure"]) else \
            "the check reads nothing even on the task's own fix"
        return f"in the reference's {name if name in ('look', 'drive') else 'play ' + name}, {why}: {said}"

    def check(self, check):
        kind = check["kind"]
        if kind in JUDGES:
            return True, NOT_JUDGED
        if kind == "probe" and check["measure"]["probe"] == "trace":
            return True, "not asked: trace probes are retired: remove it"
        if seen.is_seen(check) and self.side.answers is None:
            return True, seen.NOT_READ
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
                         "required": check["required"], "weight": check["weight"], "detail": str(detail)[:700],
                         "group": group})
        return {"checks": rows, "probes": self.measured, "task_errors": self.task_errors,
                "uncalibrated": self.uncalibrated}


WATCH_SHOTS = 12  # the screenshots a watched play saves, spread over it


def watchable(task):
    """The plays of `task` a person can be shown: the checker's own "look" and "drive", and its task plays."""
    return ["look", "drive", *tasks.task_plays(task)]


def watch_play(repo, task, side_name, play_name, scratch, out_dir, direct=False, timeout=1800, build_timeout=3600,
               log=print, builds=None, announce=None):
    """Show a person one play of `task` on one side ("start" or "reference"): that side built, the plays it comes
    after played as always (offscreen), then `play_name` in a window at the game's own speed. Nothing is graded and no
    result is written: a watched play runs without the fixed step a check's play has, so its readings are not the
    check's. Its screenshots, probe.json and log are kept under <out_dir>/<task>/watch/<side>/. Returns {ok, why,
    task, side, play, seconds, ended, crashed, evidence}; `announce` is called just before the window opens."""
    name = task.get("name", "?")
    found = {"ok": False, "why": None, "task": name, "side": side_name, "play": play_name, "seconds": None,
             "ended": None, "crashed": False, "evidence": None}

    def stop(why):
        found["why"] = why
        return found

    wrong = tasks.problems(task)
    if wrong:
        return stop(f"the task doesn't validate: {wrong[0]}")
    names = watchable(task)
    if play_name not in names:
        return stop(f"no play {play_name}: this task's plays are {', '.join(names)}")
    commit = task["seed"].get("commit" if side_name == "start" else "reference")
    if commit is None:
        return stop("the task has no seed.reference to show")
    try:
        sha = seeds.resolve(repo, commit)
    except RuntimeError:
        return stop(f"{commit[:12]} isn't a commit of {Path(repo).name}")
    own = builds is None
    if own:
        builds = Builds(repo, scratch, direct, log)
    try:
        try:
            project, _ = builds.get(sha, [sha])
        except seeds.WrongEngine as exc:
            return stop(f"{side_name}: {exc}")
        evidence = Path(out_dir) / name / "watch"
        seeds.remove(evidence / side_name)
        side = Side(side_name, project, task, timeout, build_timeout, evidence, log)
        if not side.built():
            return stop(side.why_unbuilt())
        own_one = play_name in PLAYS
        play = play_name if own_one else tasks.task_plays(task)[play_name]
        side.watching = play_name if own_one else f"play_{play_name}"
        seconds = PLAYS[play_name][0] if own_one else play["seconds"]
        log(f"  {side_name}: the game window opens now and plays {play_name} for {seconds} s of game time; "
            "nothing in it is measured for the check")
        if announce is not None:
            announce()
        if own_one:  # played here, so it is never the boot's first seconds reused
            s, shots, inputs = own_play(play_name, project)
            p = side._play(play_name, s, max(shots, WATCH_SHOTS), inputs,
                           queries=probes.query_file(side.plan.get(play_name, [])))
        else:
            p = side.probe_play(play)
        found.update(ok=p.probe is not None and not fatal(p.log), seconds=round(p.seconds, 1),
                     ended=(p.probe or {}).get("ended"), crashed=bool(fatal(p.log)),
                     evidence=f"{name}/watch/{side_name}/{side.watching}/")
        if not found["ok"]:
            found["why"] = "the play crashed" if found["crashed"] else "the play ended without a probe.json"
        return found
    finally:
        if own:
            builds.close()


def start_unbuilt(task, why):
    """The start's grade when it doesn't build and the task says so: that build check failed, nothing else run."""
    group, build = next((g, c) for g, c in tasks.checks(task) if c["kind"] == "build" and c["fails_at_start"])
    return {"checks": [{"name": build["name"], "kind": "build", "passed": False, "required": build["required"],
                        "weight": build["weight"], "detail": str(why)[:700], "group": group}], "probes": {}}


def save_judge_shots(task, sides, folder, where="", blind=False, log=print, rng=None):
    """Play every `judge` check's plays on `sides` ({folder name: Side}, a side that didn't build left out with a note)
    and save the screenshots its judge would see under <folder>/<check>/ (judges.save), with the blind copy when
    `blind`. Nothing is asked of a model: {check: record}, each "answer needed", its `folder` named as `where` (the
    folder's place in the results) and the check's name."""
    out = {}
    for found in judges.judges(task):
        played, notes = {}, []
        for label, side in sides.items():
            if not side.built():
                notes.append(f"{label}: no screenshots, {side.why_unbuilt()}")
                continue
            try:
                played[label] = side.judge_plays(found)
            except (OSError, RuntimeError, ValueError) as exc:
                notes.append(f"{label}: the plays failed ({type(exc).__name__}: {str(exc)[:200]})")
        record = judges.save(task, found, played, folder, blind=blind, notes=notes, rng=rng)
        record["folder"] = f"{where}{found['name']}/"
        log(f"  {judges.line(found['name'], record)}")
        out[found["name"]] = record
    return out


def save_seen_shots(task, sides, folder, where="", held=None, log=print, rng=None):
    """Save every `seen` check's crops of `sides` ({folder name: Side}, a side that didn't build noted) under
    <folder>/<check>/ (seen.save), each with its blind copy and the answers `held` (seen.kept) still stand for:
    {check: record}, its `folder` named as `where` and the check's name."""
    out = {}
    for found in seen.checks(task):
        crops, notes = {}, []
        for label, side in sides.items():
            try:
                crops[label] = side.seen_crops(found)
            except (OSError, RuntimeError, ValueError) as exc:
                notes.append(f"{label}: the play failed ({type(exc).__name__}: {str(exc)[:200]})")
        record = seen.save(task, found, crops, folder, (held or {}).get(found["name"]), rng, notes)
        record["folder"] = f"{where}{found['name']}/"
        log(f"  {seen.line(found['name'], record)}")
        out[found["name"]] = record
    return out


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


def task_maps(task):
    """The maps the task's plays open: its play_map and every task play's own map."""
    found = [task.get("play_map")] + [p["map"] for p in probes.task_plays(task).values()]
    return sorted({m.split("?", 1)[0] for m in found if m})


def map_gaps(repo, sha, task):
    """{map: {"missing": [/Game packages it names that the commit lacks], "names": how many it names}} of the maps the
    task plays, for those that miss any (a store pack committed only later, say). The checker never fills them in: a
    task is built exactly as committed."""
    out = {}
    for name in task_maps(task):
        found = seeds.missing_packages(repo, sha, name)
        if found and found[0]:
            out[name] = {"missing": found[0], "names": found[1]}
    return out


def gap_notes(result):
    """A note per side and map whose packages the commit lacks."""
    notes = []
    for side in ("start", "reference"):
        for name, gap in ((result.get(side) or {}).get("missing_packages") or {}).items():
            notes.append(f"{side}: {name} names {len(gap['missing'])} of its {gap['names']} /Game packages that the "
                         f"commit doesn't have (e.g. {gap['missing'][0]}): they load as missing; commit them with the "
                         "task's commit or pick a commit that has them")
    return notes


def check_task(repo, task, raw, scratch, out_dir, keep=False, direct=False, timeout=1800, build_timeout=3600,
               log=print, clock=time.time, builds=None, judge_shots=True):
    """Check one task (a dict read from `repo`'s tasks branch, its file's bytes `raw`): its result (written to
    <out_dir>/<name>.json, its plays' files under <out_dir>/<name>/). `builds`: a run's shared copies (Builds), which
    the run deletes; without it the task gets its own under `scratch`, deleted when it is done unless `keep`.
    `judge_shots`: each `judge` check's screenshots of the start and the reference saved under
    <out_dir>/<name>/judge-shots/ for a person to answer (the verdict never waits on them). Each `seen` check's crops
    are saved under <out_dir>/<name>/seen-shots/, and the answers an earlier check's folder holds are read first."""
    started = clock()
    name = task.get("name", "?")
    result = {"format": FORMAT, "task": name, "game": (task.get("seed") or {}).get("game"),
              "task_sha256": tasks.digest(raw), "task_digest": canonical_digest(task),
              "verdict": None, "reasons": [], "notes": [], "start": None,
              "reference": None, "probes": {}, "start_checks": [], "reference_checks": [], "judges": {}, "seen": {},
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
    held = seen.kept(evidence / "seen-shots")  # the writer's answers outlive the evidence they were given for
    seeds.remove(evidence)
    own = builds is None
    if own:
        builds = Builds(repo, scratch, direct, log)
    sides = {}
    try:
        shas = {}
        for side, commit in (("start", seed["commit"]), ("reference", seed.get("reference"))):
            if commit is None:
                continue
            try:
                shas[side] = seeds.resolve(repo, commit)
            except RuntimeError:
                return finish("INVALID", [f"seed.{'commit' if side == 'start' else 'reference'} {commit[:12]} isn't a "
                                          f"commit of {Path(repo).name} (fetch it, or fix the task)"])
        for side, sha in shas.items():
            try:
                project, info = builds.get(sha, shas.values())
            except seeds.WrongEngine as exc:
                return finish("INVALID", [f"{side}: {exc}"])
            sides[side] = Side(side, project, task, timeout, build_timeout, evidence, log)
            sides[side].answers = held
            result[side] = {"commit": sha, **info, "missing_packages": map_gaps(repo, sha, task)}
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
        notes += gap_notes(result)
        if judge_shots and judges.judges(task):
            shown = {label: s for label, s in (("start", start), ("reference", reference)) if s is not None}
            result["judges"] = save_judge_shots(task, shown, evidence / "judge-shots", f"{name}/judge-shots/",
                                                blind=True, log=log)
            notes += [judges.line(n, r) for n, r in result["judges"].items()]
        if seen.checks(task):  # a start that doesn't build by design is never played, so it has nothing to read
            shown = {label: s for label, s in (("start", start), ("reference", reference)) if s is not None
                     and not (label == "start" and build is not None and not start.built())}
            result["seen"] = save_seen_shots(task, shown, evidence / "seen-shots", f"{name}/seen-shots/", held, log=log)
            notes += [seen.line(n, r) for n, r in result["seen"].items()]
            # a seen check gates as a probe does, so the task isn't VALID until both sides are answered (an unanswered
            # start would otherwise read as the start failing it)
            # an optional one too: the Lab's reading of it can still be a task error, which only the answer shows
            waiting = [seen.line(c["name"], result["seen"][c["name"]]) for c in seen.checks(task)
                       if result["seen"][c["name"]]["status"] != seen.ANSWERED]
            valid, why = valid and not waiting, why + waiting
        result.update(probes=probe_values(task, ref_grade, start_grade), start_checks=start_grade["checks"],
                      reference_checks=ref_grade["checks"] if ref_grade else [])
        return finish("VALID" if valid else "INVALID", why, notes)
    except (OSError, RuntimeError, ValueError) as exc:
        return finish("ERROR", [f"the checker couldn't check it: {type(exc).__name__}: {str(exc)[:400]}"])
    finally:
        if own and not keep:
            builds.close()

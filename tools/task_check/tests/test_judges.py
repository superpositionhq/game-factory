"""A judge check's screenshots saved for a person to answer: which ones the cloud's judge is shown (evenly spaced plus
named, 20 at most), where they are saved, the blind copy, and the --no-judge-shots flag. Unreal is faked."""

import contextlib
import io
import json
import random
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import FakeProject, measuring, probe, side, task_with
from test_check import make_game

from task_check import check, cli, judges, trial, unreal

RUBRIC = [{"key": "door_open", "criterion": "The door stands open.", "required": True},
          {"key": "lit", "criterion": "The room is lit.", "weight": 2}]


def play(name="open_door", seconds=10, shots=(), **extra):
    inputs = [{"t": 1.0, "key": "E", "press": True}, {"t": 1.2, "key": "E", "press": False}]
    inputs += [{"t": 2.0 + i, "shot": s} for i, s in enumerate(shots)]
    return {"name": name, "seconds": seconds, "inputs": inputs, **extra}


def judge(name="door_looks_open", plays=None, **extra):
    found = {"kind": "judge", "name": name, "question": "Does the door open?", "rubric": RUBRIC, **extra}
    if plays is not None:
        found["plays"] = plays
    return found


class Shooting(FakeProject):
    """A fake project whose plays also write their screenshots: shot_NN.png, and shot_<name>.png per `shot` input."""

    def play(self, seconds, shots, timeout, map=None, inputs=None, queries=None, args=(), every=None):
        self.plays.append({"seconds": seconds, "shots": shots, "map": map, "inputs": inputs, "queries": queries,
                           "args": list(args), "every": every})
        named = [f"shot_{i['shot']}.png" for i in inputs or [] if "shot" in i]
        even = [f"shot_{i:02d}.png" for i in range(shots)]
        probe, log = (self.answer or measuring(0))(seconds, shots, queries)
        probe["screenshots"] = even[:1] + named + even[1:]  # a named one taken between the first two even ones
        files = {"probe.json": json.dumps(probe).encode(),
                 **{n: f"{self.folder.name}:{seconds}:{n}".encode() for n in even + named}}
        return unreal.Played(0, False, "", 1.0, probe, log, files)


class Selection(unittest.TestCase):
    def test_the_evenly_spaced_ones_are_picked_evenly_and_every_named_one_kept_in_order(self):
        names = [f"shot_{i:02d}.png" for i in range(10)]
        names.insert(3, "shot_door.png")
        self.assertEqual(judges.chosen(names, 5), ["shot_01.png", "shot_door.png", "shot_03.png", "shot_05.png",
                                                   "shot_07.png", "shot_09.png"])
        self.assertEqual(judges.chosen(names[:3], 5), names[:3], "fewer than asked: all of them")

    def test_the_plugin_takes_them_at_the_middle_of_each_slice(self):
        self.assertEqual(judges.even_times(20, 4), [2.5, 7.5, 12.5, 17.5])
        self.assertEqual(judges.spread(list(range(8)), 4), [1, 3, 5, 7])

    def test_a_side_shows_twenty_at_most(self):
        check_ = judges.judge(judge(plays=[play(f"p{i}", shots=["a", "b"]) for i in range(4)], shots=5))
        played = {f"p{i}": ({"screenshots": [f"shot_{j:02d}.png" for j in range(5)] + ["shot_a.png", "shot_b.png"]},
                            {f"shot_{j:02d}.png": b"x" for j in range(5)} | {"shot_a.png": b"x", "shot_b.png": b"x"})
                  for i in range(4)}
        rows = judges.selection(check_, played)
        self.assertEqual([len(p) for _, _, p in rows], [7, 7, 6, 0])
        self.assertEqual(rows[0][2][0], ("shot_00.png", "p0_01.png"))

    def test_without_plays_a_judge_is_shown_the_idle_play_and_the_drive_whole(self):
        check_ = judges.judge(judge())
        self.assertEqual([(p, s) for p, _, s in judges.plays(check_)], [("look", None), ("drive", None)])

    def test_a_task_play_is_played_with_the_most_screenshots_a_judge_asks(self):
        task = task_with(probe(play=play()), judge("a", plays=[play()], shots=4),
                         judge("b", plays=[play()], shots=8, required=False))
        self.assertEqual(judges.play_shots(task), {"open_door": 8})
        project = Shooting(folder="start")
        s = side("start", project, task)
        s.probe_play(check.tasks.play(play()))
        self.assertEqual(project.plays[0]["shots"], 8)


class Saved(unittest.TestCase):
    def sides(self, task):
        return {name: side(name, Shooting(folder=name), task) for name in ("start", "reference")}

    def test_the_layout_the_ask_and_the_blind_copy(self):
        task = task_with(probe(play=play(shots=["door"])), judge(plays=[play(shots=["door"])], before=True))
        sides = self.sides(task)
        sides["start"].probe_play(check.tasks.play(play(shots=["door"])))  # the probe's play, made by the grade
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "probe-task" / "judge-shots"
            records = check.save_judge_shots(task, sides, folder, "probe-task/judge-shots/", blind=True,
                                             log=lambda *a: None, rng=random.Random(1))
            base = folder / "door_looks_open"
            self.assertEqual(sorted(p.name for p in (base / "start").iterdir()),
                             [f"open_door_{i:02d}.png" for i in range(1, 7)])
            self.assertEqual((base / "start" / "open_door_02.png").read_bytes(), b"start:10:shot_door.png",
                             "the named shot in the order taken")
            self.assertEqual(len(sides["start"].project.plays), 1, "the probe's own play is reused")
            key = json.loads((base / "blind" / "key.json").read_text())
            self.assertEqual(sorted(key.values()), ["reference", "start"])
            self.assertEqual(sorted(key), ["A", "B"])
            for letter, name in key.items():
                self.assertEqual([p.read_bytes() for p in sorted((base / "blind" / letter).iterdir())],
                                 [p.read_bytes() for p in sorted((base / name).iterdir())])
            ask = (base / "ask.md").read_text()
            self.assertNotIn("picture(s)", ask, "a blind ask never tells a side's picture count")
            self.assertIn("`start/`: 6 picture(s)", (base / "sides.md").read_text())
            for text in ("Does the door open?", "| door_open | yes | 1 | The door stands open. |",
                         "| lit | no | 2 | The room is lit. |", "Keep the hero on the ground.", "blind/key.json",
                         "start fails every required rubric item", "the start as BEFORE"):
                self.assertIn(text, ask)
            record = records["door_looks_open"]
            self.assertEqual(record["status"], "shots saved for start/reference, answer needed")
            self.assertEqual(record["folder"], "probe-task/judge-shots/door_looks_open/")
            self.assertEqual(judges.line("door_looks_open", record),
                             "judge door_looks_open: shots saved for start/reference, answer needed")

    def test_the_blind_copy_holds_only_pictures_both_sides_have(self):
        task = task_with(probe(), judge(before=True))
        chk = next(iter(judges.judges(task)))
        shots = lambda n: {f"shot_{i:04d}.png": f"{i}".encode() for i in range(n)}
        played = {"start": {"look": (None, shots(6)), "drive": (None, shots(5))},
                  "reference": {"look": (None, shots(6)), "drive": (None, shots(8))}}
        with tempfile.TemporaryDirectory() as tmp:
            record = judges.save(task, chk, played, tmp, blind=True, rng=random.Random(1))
            base = Path(tmp) / chk["name"]
            a, b = (sorted(p.name for p in (base / "blind" / x).iterdir()) for x in "AB")
            self.assertEqual(a, b, "both blind folders hold the same picture names")
            self.assertEqual(len(a), 6 + 5)
            self.assertTrue(any("left out of the blind copy" in n for n in record["notes"]))
            self.assertNotIn("left out", (base / "ask.md").read_text(), "side notes stay out of the blind ask")
            self.assertIn("left out of the blind copy", (base / "sides.md").read_text())

    def test_the_shared_plays_are_played_whole_not_cut_from_the_boot(self):
        task = task_with({"kind": "boot", "name": "boots", "seconds": 60}, probe(), judge())
        s = side("reference", Shooting(folder="reference"), task)
        s.boot(60)
        s.probe_play("look")
        with tempfile.TemporaryDirectory() as tmp:
            check.save_judge_shots(task, {"reference": s}, Path(tmp), log=lambda *a: None)
            saved = sorted(p.name for p in (Path(tmp) / "door_looks_open" / "reference").iterdir())
        self.assertEqual(saved, sorted([f"look_{i:02d}.png" for i in range(1, 7)]
                                       + [f"drive_{i:02d}.png" for i in range(1, 9)]))
        self.assertEqual([(p["seconds"], p["shots"]) for p in s.project.plays], [(60, 6), (20, 6), (22, 8)])

    def test_a_side_that_didnt_build_is_noted_and_no_blind_copy_is_made(self):
        task = task_with(judge())
        sides = {"start": side("start", Shooting(build_exit=6, folder="start"), task),
                 "reference": side("reference", Shooting(folder="reference"), task)}
        with tempfile.TemporaryDirectory() as tmp:
            record = check.save_judge_shots(task, sides, Path(tmp), blind=True, log=lambda *a: None)["door_looks_open"]
            self.assertFalse((Path(tmp) / "door_looks_open" / "blind").exists())
            self.assertEqual(record["status"], "shots saved for reference, answer needed")
            self.assertIn("didn't build", record["notes"][0])


class Whole(unittest.TestCase):
    def run_check(self, tmp, **kw):
        repo, start, fix, _ = make_game(tmp)
        task = task_with(probe(expect={"op": ">=", "calibrate": 0.5}), judge(reference=True))
        task["seed"] = {**task["seed"], "commit": start, "reference": fix}
        names = {start[:12]: "start", fix[:12]: "reference"}
        projects = {"start": Shooting(measuring(-500), folder="start"),
                    "reference": Shooting(measuring(100), folder="reference")}
        with mock.patch.object(unreal, "Project", lambda folder, m, label: projects[names[Path(folder).name]]), \
                mock.patch.object(unreal.Machine, "for_project",
                                  classmethod(lambda cls, p, d=False: cls(Path(p), None))), \
                mock.patch.object(unreal.gfroot, "check_free", lambda *a: 100.0):
            return check.check_task(repo, task, json.dumps(task).encode(), Path(tmp) / "scratch", Path(tmp) / "out",
                                    log=lambda *a: None, **kw)

    def test_a_task_check_saves_both_sides_and_its_verdict_doesnt_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_check(tmp)
            self.assertEqual(result["verdict"], "VALID")
            self.assertIn("judge door_looks_open: shots saved for start/reference, answer needed", result["notes"])
            base = Path(tmp) / "out" / "probe-task" / "judge-shots" / "door_looks_open"
            for folder in ("start", "reference", "blind/A", "blind/B"):
                self.assertEqual(len(list((base / folder).iterdir())), 14, folder)
            self.assertTrue((base / "ask.md").is_file())

    def test_no_judge_shots_skips_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_check(tmp, judge_shots=False)
            self.assertEqual((result["verdict"], result["judges"]), ("VALID", {}))
            self.assertFalse((Path(tmp) / "out" / "probe-task" / "judge-shots").exists())

    def test_the_progress_names_each_judge_waiting_for_an_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = {"task": "probe-task", "verdict": "VALID", "reasons": [], "seconds": 60,
                      "judges": {"door_looks_open": {"status": "shots saved for start/reference, answer needed"}}}
            cli.write_progress(tmp, 0, ["probe-task"], [result], now=60)
            self.assertIn("    judge door_looks_open: shots saved for start/reference, answer needed: "
                          "probe-task/judge-shots/door_looks_open/ask.md",
                          (Path(tmp) / "progress.txt").read_text())


class Flags(unittest.TestCase):
    def test_task_check_passes_no_judge_shots_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _, _, _ = make_game(tmp)
            path = Path(tmp) / "g-fix-x.json"
            path.write_text(json.dumps({**task_with(probe()), "name": "g-fix-x"}), encoding="utf-8")
            seen = []

            def fake(repo_, task, raw, scratch, out, **kw):
                seen.append(kw["judge_shots"])
                return {"task": task["name"], "verdict": "VALID", "reasons": []}

            with mock.patch.object(check, "check_task", fake), \
                    mock.patch.object(unreal.gfroot, "check_free", lambda *a: 100.0), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                for extra in ([], ["--no-judge-shots"]):
                    cli.main([str(repo), "--task", str(path), "--scratch", str(Path(tmp) / "s"), *extra])
            self.assertEqual(seen, [True, False])

    def test_task_try_passes_no_judge_shots_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _, _, _ = make_game(tmp)
            path = Path(tmp) / "tasks" / "Tasks" / "g-fix-x.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({**task_with(probe()), "name": "g-fix-x"}), encoding="utf-8")
            seen = []

            def fake(*a, **kw):
                seen.append(kw["judge_shots"])
                return {"task": "g-fix-x", "status": "DONE", "reasons": [], "runs": [], "solved": 0}

            with mock.patch.object(trial, "try_task", fake), mock.patch.object(shutil, "which", lambda n: n), \
                    mock.patch.object(unreal.gfroot, "check_free", lambda *a: 100.0), \
                    mock.patch.object(unreal.gfroot, "root", lambda: str(Path(tmp) / "root")), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                for extra in ([], ["--no-judge-shots"]):
                    trial.main([str(repo), "--task", str(path), "--agent", "codex", "--scratch",
                                str(Path(tmp) / "elsewhere"), *extra])
            self.assertEqual(seen, [True, False])


class Try(unittest.TestCase):
    def test_a_try_saves_the_agents_side_and_lists_the_judge_as_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, start, fix, _ = make_game(tmp)
            task = task_with(probe(expect={"op": ">=", "calibrate": 0.5}),
                             judge(plays=[play(shots=["door"])], shots=3))
            task["seed"] = {**task["seed"], "commit": start, "reference": fix}
            projects = {"start": Shooting(measuring(-500), folder="start"),
                        "reference": Shooting(measuring(100), folder="reference"),
                        "run1": Shooting(measuring(100), folder="run1")}

            def project(folder, machine, label):
                folder = Path(folder)
                return projects[folder.name if folder.name in projects else folder.parent.name]

            def agent(argv, cwd, prompt, transcript, minutes, env_extra=None):
                Path(transcript).write_text("")
                return {"exit_code": 0, "seconds": 60.0, "timed_out": False}

            with mock.patch.object(unreal, "Project", project), mock.patch.object(trial, "run_agent", agent), \
                    mock.patch.object(unreal.Machine, "for_project",
                                      classmethod(lambda cls, p, d=False: cls(Path(p), None))):
                result = trial.try_task(repo, task, json.dumps(task).encode(), Path(tmp) / "scratch",
                                        Path(tmp) / "out", "claude", "claude", places=[repo], log=lambda *a: None)
            self.assertEqual((result["status"], result["solved"]), ("DONE", 1))
            self.assertEqual(result["runs"][0]["score"], 1.0, "the number leaves judges out")
            self.assertEqual(result["judges_pending"], ["door_looks_open"])
            base = Path(tmp) / "out" / "probe-task" / "run1" / "judge-shots" / "door_looks_open"
            self.assertEqual(sorted(p.name for p in (base / "agent").iterdir()),
                             [f"open_door_{i:02d}.png" for i in range(1, 5)])
            self.assertFalse((base / "blind").exists())
            self.assertIn("before calling the task too easy or held", (base / "ask.md").read_text())
            self.assertIn("answer needed", trial.line(result))


if __name__ == "__main__":
    unittest.main()

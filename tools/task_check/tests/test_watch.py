"""A watched play (task-check.py --watch): one play of one task on one side, in a window at the game's own speed, for a
person to look at. The plays it comes after are played as always; nothing is graded; a name that is no play of the task
is refused with the names it has."""

import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import FakeProject, measuring, probe, task_with

from task_check import check, cli, unreal

MEASURE = {"probe": "pawn", "field": "z", "agg": "max"}


def play(name, seconds, after=None):
    found = {"name": name, "seconds": seconds, "inputs": [{"t": 1.0, "key": "E", "press": True}]}
    return {**found, "after": after} if after is not None else found


class Watching(FakeProject):
    """A fake project that records which of its plays were asked for in a window."""

    def play(self, *args, watch=False, **kwargs):
        found = super().play(*args, **kwargs)
        self.plays[-1]["watch"] = watch
        return found


class Copies:
    """A run's builds, as check.Builds gives them: one project for every commit."""

    def __init__(self, project):
        self.project, self.asked = project, []

    def get(self, sha, needed=()):
        self.asked.append(sha)
        return self.project, {}


class Watch(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.out, True)
        self.resolve = check.seeds.resolve
        check.seeds.resolve = lambda repo, commit: commit
        self.addCleanup(setattr, check.seeds, "resolve", self.resolve)
        self.task = task_with(probe(name="reads", play=play("reads", 20, ["writes"]), measure=MEASURE),
                              probe(name="writes", play=play("writes", 10), measure=MEASURE))

    def watch(self, project, side="reference", name="reads"):
        self.copies = Copies(project)
        return check.watch_play(".", self.task, side, name, self.out, self.out, log=lambda *a: None,
                                builds=self.copies)

    def test_only_the_named_play_is_in_a_window_after_the_plays_it_comes_after(self):
        game = Watching(measuring(0))
        found = self.watch(game)
        self.assertTrue(found["ok"], found)
        self.assertEqual([(p["seconds"], p["watch"]) for p in game.plays], [(10, False), (20, True)])
        self.assertEqual(game.plays[-1]["shots"], check.WATCH_SHOTS)
        self.assertEqual(found["evidence"], "probe-task/watch/reference/play_reads/")
        self.assertTrue((Path(self.out) / "probe-task" / "watch" / "reference" / "play_reads" / "probe.json").is_file())

    def test_the_side_asked_is_the_side_built(self):
        self.watch(Watching(measuring(0)), side="start")
        self.assertEqual(self.copies.asked, ["a" * 40])
        self.watch(Watching(measuring(0)), side="reference")
        self.assertEqual(self.copies.asked, ["b" * 40])

    def test_the_checkers_own_drive_can_be_watched(self):
        game = Watching(measuring(0))
        found = self.watch(game, name="drive")
        self.assertTrue(found["ok"], found)
        self.assertEqual([(p["seconds"], p["watch"]) for p in game.plays], [(check.PLAYS["drive"][0], True)])

    def test_a_name_that_is_no_play_of_the_task_is_refused_with_its_plays(self):
        game = Watching(measuring(0))
        found = self.watch(game, name="walks_in")
        self.assertFalse(found["ok"])
        self.assertIn("look, drive, reads, writes", found["why"])
        self.assertEqual(game.plays, [])

    def test_a_side_that_does_not_build_or_a_play_that_crashes_is_said(self):
        found = self.watch(Watching(measuring(0), build_exit=1))
        self.assertFalse(found["ok"])
        self.assertIn("didn't build", found["why"])
        found = self.watch(Watching(measuring(0, crash=True)))
        self.assertFalse(found["ok"])
        self.assertEqual(found["why"], "the play crashed")

    def test_a_check_never_asks_for_a_window(self):
        game = Watching(measuring(0))
        side = check.Side("reference", game, self.task, 60, 60, None, lambda *a: None)
        for _, c in check.tasks.checks(self.task):
            side.value(c)
        self.assertEqual([p["watch"] for p in game.plays], [False, False])

    def test_the_line_printed(self):
        self.assertEqual(cli.watch_line({"ok": True, "task": "t", "side": "reference", "play": "reads", "seconds": 21.4,
                                         "ended": "time", "evidence": "t/watch/reference/play_reads/", "why": None}),
                         "WATCHED t: reference play reads: shown for 21 s (ended by time); screenshots and probe.json "
                         "in t/watch/reference/play_reads/; nothing was graded")
        self.assertIn("not shown as asked: the play crashed",
                      cli.watch_line({"ok": False, "task": "t", "side": "start", "play": "reads", "why": "the play crashed"}))


class CommandLine(unittest.TestCase):
    """What the real project is asked for: a watched play is windowed at the game's own speed, a check's is not."""

    def argv(self, **kwargs):
        seen = {}

        class Machine:
            def editor(self):
                return "UnrealEditor.exe"

            def job(self, label, argv, cwd, timeout):
                seen["argv"] = [str(a) for a in argv]
                return unreal.Result(0, "", 1.0)

        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        (folder / "Game.uproject").write_text("{}", encoding="utf-8")
        unreal.Project(folder, Machine(), "abc").play(5, 2, 60, **kwargs)
        return seen["argv"]

    def test_a_checks_play_is_offscreen_at_a_fixed_step(self):
        argv = self.argv()
        self.assertIn("-RenderOffscreen", argv)
        self.assertIn("-fps=30", argv)
        self.assertIn("-benchmark", argv)
        self.assertNotIn("-windowed", argv)

    def test_a_watched_play_is_in_a_window_in_real_time(self):
        argv = self.argv(watch=True)
        self.assertIn("-windowed", argv)
        for flag in ("-RenderOffscreen", "-fps=30", "-benchmark"):
            self.assertNotIn(flag, argv)
        self.assertIn("-TaskProbe", argv)


if __name__ == "__main__":
    unittest.main()

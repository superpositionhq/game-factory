"""A task play's save fixtures (docs/task-probes.md 1.1): `first_on_start` plays the sessions a play continues on the
start and starts the play from the save state they left, on every side; `saves` stages the save files before the
launch (unreadable, unwritable); and the project's own staging overwrites, locks and unlocks real files."""

import os
import tempfile
import unittest
from pathlib import Path

from helpers import FakeProject, measuring, probe, side, task_with

from task_check import tasks, unreal

MEASURE = {"probe": "pawn", "field": "z", "agg": "max"}


def play(name, continues=None, **own):
    found = {"name": name, "seconds": 10, "inputs": [{"t": 1.0, "key": "E", "press": True}]}
    return {**found, **({"continues": continues} if continues else {}), **own}


OLD = [probe(name="saves_old", play=play("saves_old"), measure=MEASURE),
       probe(name="old_loads", play=play("loads_old", "saves_old", first_on_start=True), measure=MEASURE)]


class StartSaves(unittest.TestCase):
    def test_the_reference_starts_from_the_save_the_start_left(self):
        task = task_with(*OLD)
        start_project, ref_project = FakeProject(measuring(0), folder="start"), FakeProject(measuring(0), folder="ref")
        start, ref = side("start", start_project, task), side("reference", ref_project, task)
        start.start = ref.start = start
        ref.value(tasks.checks(task)[1][1])
        self.assertEqual([(p["session"], p["keep_saves"], p["saves"]) for p in start_project.plays],
                         [(True, True, None), (False, False, None)])
        self.assertEqual([p["saves"] for p in ref_project.plays], [{"Saved/SaveGames/Slot.sav": b"saved by start"}])
        said = ref.sessions["loads_old"]
        self.assertTrue(said["clean"])
        self.assertEqual(said["carried"], ["Saved/SaveGames/Slot.sav"])
        self.assertIsNone(ref.carried(tasks.task_plays(task)["loads_old"]))

    def test_a_start_that_left_no_save_is_the_tasks(self):
        task = task_with(*OLD)
        start_project = FakeProject(measuring(0), folder="start", saved=())
        start, ref = side("start", start_project, task), side("reference", FakeProject(measuring(0)), task)
        start.start = ref.start = start
        ref.value(tasks.checks(task)[1][1])
        self.assertIn("left no save state", ref.carried(tasks.task_plays(task)["loads_old"]))

    def test_a_staged_play_is_staged_and_one_with_no_save_to_spoil_says_so(self):
        task = task_with(probe(name="broken", play=play("broken", saves="unreadable"), measure=MEASURE))
        project = FakeProject(measuring(0))
        ref = side("reference", project, task)
        ref.value(tasks.checks(task)[0][1])
        self.assertEqual(project.plays[-1]["stage"], "unreadable")
        self.assertIn("none was made unreadable", ref.carried(tasks.task_plays(task)["broken"]))


class Staging(unittest.TestCase):
    def test_unreadable_overwrites_and_unwritable_locks_then_unlocks(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            project = Path(d)
            slot = project / "Saved/SaveGames/Slot.sav"
            slot.parent.mkdir(parents=True)
            slot.write_bytes(b"GVAS" + b"x" * 100)
            self.assertEqual(unreal.stage_saves(project, "unreadable"), ["Saved/SaveGames/Slot.sav"])
            self.assertEqual(len(slot.read_bytes()), 104)
            self.assertTrue(slot.read_bytes().startswith(b"TaskProbe: an unreadable save"))
            unreal.stage_saves(project, "unwritable")
            if os.name != "nt" and os.geteuid() != 0:
                with self.assertRaises(PermissionError):
                    slot.write_bytes(b"new")
                with self.assertRaises(PermissionError):
                    (slot.parent / "Other.sav").write_bytes(b"new")
            unreal.unlock_saves(project)
            slot.write_bytes(b"new")
            self.assertEqual(unreal.take_saves(project), {"Saved/SaveGames/Slot.sav": b"new"})


if __name__ == "__main__":
    unittest.main()

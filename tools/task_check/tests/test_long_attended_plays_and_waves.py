"""Plays and sounds as the Lab's game grader reads them since 1.18.0 (docs/task-probes.md 1.1, 1.4 and 2.4): a task play
may last up to 1200 s, and the checker gives a long play the time to run; a task play may be `attended`, launched
without -unattended (its first session too, when another play continues it); and the audio field `waves` counts the
different recordings the selected starts played, reading nothing when a start's recording can't be told. A click no
button takes is made on its text as shown by the plugin itself (TaskProbe::ClickText), so nothing here reads it."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import FakeProject, measuring, probe, side, task_with

from task_check import check, probes, tasks, unreal

MEASURE = {"probe": "pawn", "field": "z", "agg": "max"}


def play(name, seconds, **more):
    return {"name": name, "seconds": seconds, "inputs": [{"t": 1.0, "key": "E", "press": True}], **more}


def reading(name, of):
    return probe(name=name, play=of, measure=MEASURE)


class LongPlays(unittest.TestCase):
    def test_a_long_play_gets_at_least_its_own_seconds_and_a_margin(self):
        task = task_with(reading("late", play("dawn", 1200)), reading("soon", play("start", 20)))
        for timeout, short in ((60, 20 + check.PLAY_MARGIN), (1800, 1800)):
            project = FakeProject(measuring(5))
            s = check.Side("reference", project, task, timeout, 60, None, lambda *a: None)
            for _, c in tasks.checks(task):
                s.value(c)
            self.assertEqual([(p["seconds"], p["timeout"]) for p in project.plays],
                             [(1200, max(timeout, 1200 + check.PLAY_MARGIN)), (20, short)], timeout)


class AttendedPlays(unittest.TestCase):
    def test_an_attended_play_is_kept_and_played_attended(self):
        task = task_with(reading("menu", play("menu", 10, attended=True)), reading("other", play("other", 20)))
        self.assertTrue(tasks.task_plays(task)["menu"]["attended"])
        self.assertFalse(tasks.task_plays(task)["other"]["attended"])
        project = FakeProject(measuring(5))
        s = side("reference", project, task)
        for _, c in tasks.checks(task):
            s.value(c)
        self.assertEqual([(p["seconds"], p["attended"]) for p in project.plays], [(10, True), (20, False)])

    def test_attended_is_true_or_unset(self):
        task_with(reading("menu", play("menu", 10, attended=None)))
        for bad in (False, 1, "yes"):
            with self.assertRaises(ValueError, msg=bad):
                task_with(reading("menu", play("menu", 10, attended=bad)))

    def test_a_first_session_is_launched_as_the_play_it_plays(self):
        task = task_with(reading("kept", play("again", 10, continues="first")),
                         reading("first", play("first", 15, attended=True)))
        project = FakeProject(measuring(5))
        s = side("reference", project, task)
        s.value(tasks.checks(task)[0][1])
        self.assertEqual([(p["seconds"], p["session"], p["attended"]) for p in project.plays],
                         [(15, True, True), (10, False, False)])

    def test_the_local_runner_leaves_out_unattended_only_for_an_attended_play(self):
        for attended in (True, False):
            argv = launched(attended)
            self.assertEqual("-unattended" in argv, not attended, attended)
            self.assertIn("-TaskProbe", argv)


class Waves(unittest.TestCase):
    def heard(self, starts, **value):
        measure = tasks.measure({"probe": "audio", "field": "waves"})
        qid = probes.query_id(probes.needs(measure)[0])
        return measure, {"measures": {qid: [{"t": 0.5, "value": {"starts": starts, **value}}]}}

    def test_waves_counts_the_different_recordings_the_starts_played(self):
        measure, found = self.heard([{"t": 0.1, "sound": "Step_Cue", "named": True, "waves": ["Step_01"]},
                                     {"t": 0.2, "sound": "Step_Cue", "named": True, "waves": ["Step_02"]},
                                     {"t": 0.3, "sound": "Step_Cue", "named": True, "waves": ["Step_01"]},
                                     {"t": 0.4, "sound": "Gen", "named": False, "waves": ["Gen_Wave", "Step_02"]}])
        self.assertEqual(probes.reduce(measure, found), 3.0, "a start made at run time still names its recording")
        self.assertEqual(probes.reduce(tasks.measure({"probe": "audio", "field": "sounds"}), found), None,
                         "sounds still needs every start named")

    def test_waves_reads_nothing_when_a_starts_recording_cant_be_told(self):
        for row in ({"t": 0.1, "sound": "Step_Cue", "named": True},
                    {"t": 0.1, "sound": "Step_Cue", "named": True, "waves": []}):
            measure, found = self.heard([row])
            value, why = probes.measured(measure, found)
            self.assertIsNone(value, row)
            self.assertIn("no recording the plugin could name", why)
        measure, found = self.heard([{"t": 0.1, "waves": ["A"]}], starts_capped=True)
        self.assertIsNone(probes.reduce(measure, found), "more starts than listed can't all be told")

    def test_waves_takes_no_agg_and_is_never_an_event(self):
        with self.assertRaises(ValueError):
            task_with(probe(play=play("p", 10), measure={"probe": "audio", "field": "waves", "agg": "max"}))
        event = {"measure": {"probe": "audio", "field": "waves"}, "expect": {"op": ">=", "value": 2}}
        with self.assertRaises(ValueError):
            task_with(probe(play=play("p", 10), measure={**MEASURE, "since": event}))
        task_with(probe(play=play("p", 10), measure={"probe": "audio", "field": "waves", "window": [1, 9]},
                        expect={"op": ">=", "value": 2}))


class Machine:
    def __init__(self):
        self.argv = None

    def editor(self):
        return Path("UnrealEditor.exe")

    def job(self, label, argv, cwd, timeout):
        self.argv = [str(a) for a in argv]
        out = next(a.split("=", 1)[1] for a in self.argv if a.startswith("-TaskProbeOut="))
        (Path(out) / "probe.json").write_text(json.dumps({"track": [], "camera": [], "screenshots": []}))
        return unreal.Result(0, "", 1.0)


def launched(attended):
    """The command line of one play of a scratch copy through the local runner."""
    machine = Machine()
    with tempfile.TemporaryDirectory() as tmp:
        project = unreal.Project(tmp, machine, "game start")
        with mock.patch.object(project, "uproject", return_value=Path("Game.uproject")):
            project.play(10, 0, 60, attended=attended)
    return machine.argv


if __name__ == "__main__":
    unittest.main()

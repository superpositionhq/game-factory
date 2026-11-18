"""Clicks and plays as the Lab's game grader reads them since 1.14.0 (docs/task-probes.md 1.1 and 1.4): a click may name
its button by the on-screen text, spaces and punctuation included; an `optional` click no button matches and a
`disabled` click whose button the plugin found shown but disabled are no misses, any other click's miss stays one; a
`fresh` play starts from a cleared save and runs after no play; and an extent the plugin reads null on a matched row
reads 0."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import FakeProject, measuring, probe, side, task_with

from task_check import probes, tasks, unreal

MEASURE = {"probe": "pawn", "field": "z", "agg": "max"}
NOT_SHOWN = "no visible button matches it, UMG or Slate"
DISABLED = "a button matches it (StartButton (UButton)), shown but disabled: the click does nothing"


def play(name, seconds, inputs=None, **more):
    return {"name": name, "seconds": seconds, "inputs": inputs or [{"t": 1.0, "key": "E", "press": True}], **more}


def reading(name, of):
    return probe(name=name, play=of, measure=MEASURE)


def missed(t, target, why):
    return {"t": t, "kind": "click", "target": target, "why": why}


class Clicks(unittest.TestCase):
    def test_a_click_names_its_button_by_its_text_and_takes_its_options(self):
        clicks = [{"t": 1.0, "widget": "New expedition", "click": True, "optional": True},
                  {"t": 2.0, "widget": "Locked: Run 2!", "click": True, "disabled": True},
                  {"t": 3.0, "widget": "Start", "click": True}]
        task = task_with(reading("started", play("starts", 10, clicks)))
        self.assertEqual(tasks.task_plays(task)["starts"]["inputs"], [
            {"t": 1.0, "widget": "New expedition", "click": True, "optional": True},
            {"t": 2.0, "widget": "Locked: Run 2!", "click": True, "disabled": True},
            {"t": 3.0, "widget": "Start", "click": True}], "an option is sent only when set")
        for bad in (" leading", "", "a" * 121, "tab\there", "quote\"d"):
            with self.assertRaises(ValueError, msg=bad):
                task_with(reading("started", play("starts", 10, [{"t": 1.0, "widget": bad, "click": True}])))
        for bad in ({"optional": False}, {"disabled": 1}):
            with self.assertRaises(ValueError, msg=bad):
                task_with(reading("started", play("starts", 10, [{"t": 1.0, "widget": "Start", "click": True,
                                                                  **bad}])))

    def test_an_optional_or_disabled_click_is_excused_only_for_its_own_reason(self):
        found = {"inputs_missed": [missed(1.8, "Yes", NOT_SHOWN), missed(7.0, "StartButton", DISABLED),
                                   missed(9.0, "Back", NOT_SHOWN)]}
        sent = [{"t": 1.8, "widget": "Yes", "click": True, "optional": True},
                {"t": 7.0, "widget": "StartButton", "click": True, "disabled": True},
                {"t": 9.0, "widget": "Back", "click": True}]
        out = probes.excused(found, sent)
        self.assertEqual([r["target"] for r in out["inputs_missed"]], ["Back"], "a plain click's miss stays a miss")
        self.assertEqual([r["target"] for r in out["inputs_excused"]], ["Yes", "StartButton"])
        self.assertEqual([r["target"] for r in probes.missed(out)], ["Back"])
        wrong = [{"t": 1.8, "widget": "Yes", "click": True, "disabled": True},
                 {"t": 7.0, "widget": "StartButton", "click": True, "optional": True}]
        self.assertEqual(len(probes.excused(found, wrong)["inputs_missed"]), 3, "each option excuses its own reason")
        later = [{**sent[0], "t": 2.5}]
        self.assertEqual(len(probes.excused(found, later)["inputs_missed"]), 3, "a miss of another time stays one")
        self.assertIs(probes.excused(found, None), found)
        self.assertIs(probes.excused(None, sent), None)
        self.assertIs(probes.excused(found, [sent[2]]), found, "no click with an option: the probe as read")

    def test_a_play_reads_its_probe_with_the_allowed_misses_kept_apart(self):
        sent = [{"t": 1.8, "widget": "Yes", "click": True, "optional": True},
                {"t": 9.0, "widget": "Back", "click": True}]
        written = {"track": [], "camera": [], "screenshots": [], "seconds": 10, "inputs_sent": 2,
                   "inputs_missed": [missed(1.8, "Yes", NOT_SHOWN), missed(9.0, "Back", NOT_SHOWN)]}
        found = played(written, inputs=sent)
        self.assertEqual([r["target"] for r in found.probe["inputs_missed"]], ["Back"])
        self.assertEqual([r["target"] for r in found.probe["inputs_excused"]], ["Yes"])


class FreshPlays(unittest.TestCase):
    def test_a_fresh_play_is_played_on_a_cleared_save(self):
        task = task_with(reading("first", play("starts", 10, fresh=True)), reading("other", play("other", 20)))
        self.assertTrue(tasks.task_plays(task)["starts"]["fresh"])
        self.assertFalse(tasks.task_plays(task)["other"]["fresh"])
        project = FakeProject(measuring(5))
        s = side("reference", project, task)
        for _, c in tasks.checks(task):
            s.value(c)
        self.assertEqual([(p["seconds"], p["fresh"], p["session"]) for p in project.plays],
                         [(10, True, False), (20, False, False)])

    def test_a_fresh_play_runs_after_no_play_and_continues_no_session(self):
        for more in ({"after": ["other"]}, {"continues": "other"}):
            with self.assertRaises(ValueError) as caught:
                task_with(reading("first", play("starts", 10, fresh=True, **more)), reading("other", play("other", 20)))
            self.assertIn("starts from a cleared save (fresh), so it runs after no play and continues no session",
                          str(caught.exception))
        with self.assertRaises(ValueError):
            task_with(reading("first", play("starts", 10, fresh=False)))

    def test_the_local_runner_clears_the_save_before_a_fresh_play_only(self):
        for fresh in (True, False):
            with tempfile.TemporaryDirectory() as tmp:
                for folder in unreal.SAVES + ("Saved/Logs",):
                    (Path(tmp) / folder).mkdir(parents=True)
                    (Path(tmp) / folder / "kept.txt").write_text("x")
                played({"track": [], "camera": [], "screenshots": []}, folder=tmp, fresh=fresh)
                for folder in unreal.SAVES:
                    self.assertEqual((Path(tmp) / folder / "kept.txt").exists(), not fresh, folder)
                self.assertTrue((Path(tmp) / "Saved/Logs/kept.txt").exists(), "only the save state is cleared")


class Extents(unittest.TestCase):
    def test_a_matched_rows_null_extent_reads_zero(self):
        self.assertEqual(probes.field_of({"name": "Swarm_0", "extent_x": None}, "extent_x"), 0.0)
        self.assertIsNone(probes.field_of({"name": "Swarm_0"}, "extent_x"), "a row without the field read nothing")
        self.assertIsNone(probes.field_of({"name": "a", "speed": None}, "speed"), "only an extent")
        self.assertEqual(probes.field_of({"extent_y": 12.5}, "extent_y"), 12.5)

    def test_a_measure_of_a_null_extent_reads_zero_and_reads_something(self):
        measure = tasks.measure({"probe": "actors", "select": {"class": "Swarm"}, "field": "extent_x", "of": "max",
                                 "agg": "max"})
        qid = probes.query_id(probes.needs(measure)[0])
        rows = [{"name": "Swarm_0", "extent_x": None}]
        found = {"measures": {qid: [{"t": 0.5, "rows": rows}, {"t": 1.0, "rows": rows}]}}
        self.assertEqual([v for _, v in probes.series(measure, found)], [0.0, 0.0])
        self.assertIsNone(probes.reads_nothing(measure, found))
        none = {"measures": {qid: [{"t": 0.5, "rows": [{"name": "Swarm_0"}]}]}}
        self.assertIsNotNone(probes.reads_nothing(measure, none), "a row without the field still reads nothing")


class Machine:
    def __init__(self, written):
        self.written = written

    def editor(self):
        return Path("UnrealEditor.exe")

    def job(self, label, argv, cwd, timeout):
        out = next(a.split("=", 1)[1] for a in map(str, argv) if a.startswith("-TaskProbeOut="))
        (Path(out) / "probe.json").write_text(json.dumps(self.written))
        return unreal.Result(0, "", 1.0)


def played(written, inputs=None, folder=None, fresh=False):
    """One play of a scratch copy through the local runner, its plugin answering `written`."""
    with tempfile.TemporaryDirectory() as tmp:
        project = unreal.Project(folder or tmp, Machine(written), "game start")
        with mock.patch.object(project, "uproject", return_value=Path("Game.uproject")):
            return project.play(10, 0, 60, inputs=inputs, fresh=fresh)


if __name__ == "__main__":
    unittest.main()

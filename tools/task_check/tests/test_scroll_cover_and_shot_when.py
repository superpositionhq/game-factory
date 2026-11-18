"""Plays as the Lab's game grader reads them since 1.17.0 (docs/task-probes.md 1.1 and 1.4): a click on a button
something else is drawn over is a miss, "covered by another control", that neither `optional` nor `disabled` excuses;
a widgets measure may read `covered`; a shot may say `when`, an event the probe reads itself every frame (widgets
count or visible, actors count, x, y, z, hidden or a prop: member), handed to it as one query, and a shot whose event
never came is a missed input of kind shot_when; and a task play may last up to 300 s, every time in it up to 300 s."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import probe, task_with

from task_check import probes, tasks, unreal

EVENT = {"measure": {"probe": "widgets", "select": {"name": "ResultPanel"}, "field": "count"},
         "expect": {"op": ">=", "value": 1}}
MEASURE = {"probe": "pawn", "field": "z", "agg": "max"}
COVERED = "covered by another control"


def play(inputs, seconds=20, name="result"):
    return {"name": name, "seconds": seconds, "inputs": inputs}


def reading(inputs, seconds=20, measure=None):
    return probe(name="shown", play=play(inputs, seconds), measure=measure or MEASURE)


def missed(t, kind, target, why):
    return {"t": t, "kind": kind, "target": target, "why": why}


class ShotWhen(unittest.TestCase):
    def test_a_shots_when_is_kept_with_its_defaults_and_left_out_when_unset(self):
        task = task_with(reading([{"t": 2, "shot": "result", "when": {**EVENT, "within": 30}},
                                  {"t": 3, "shot": "plain"}]))
        tied, plain = tasks.task_plays(task)["result"]["inputs"]
        self.assertEqual(tied["when"], tasks.event({**EVENT, "within": 30}))
        self.assertNotIn("when", plain)

    def test_a_shots_when_is_handed_to_the_plugin_as_one_query_it_reads_every_frame(self):
        task = task_with(reading([{"t": 2, "shot": "result", "when": {**EVENT, "within": 30}}]))
        (row,) = probes.probe_inputs(tasks.task_plays(task)["result"]["inputs"])
        query = probes.needs(tasks.measure(EVENT["measure"]))[0]
        self.assertEqual(row["when"], {"query": {"id": probes.query_id(query), **query}, "field": "count",
                                       "of": "count", "match": None, "op": ">=", "value": 1.0, "within": 30.0})
        self.assertEqual(probes.probe_inputs([row]), [row], "a when in the plugin's form passes as it is")
        self.assertIsNone(probes.probe_inputs(None))
        open_ended = task_with(reading([{"t": 2, "shot": "result", "when": EVENT}]))
        (row,) = probes.probe_inputs(tasks.task_plays(open_ended)["result"]["inputs"])
        self.assertNotIn("within", row["when"], "no within: it may come until the play's end")

    def test_an_actors_event_names_its_field_and_reduction(self):
        event = {"measure": {"probe": "actors", "select": {"class": "Boat"}, "field": "prop:Speed", "of": "max"},
                 "expect": {"op": ">", "value": 300}}
        task = task_with(reading([{"t": 1, "shot": "fast", "when": event}]))
        (row,) = probes.probe_inputs(tasks.task_plays(task)["result"]["inputs"])
        self.assertEqual((row["when"]["query"]["kind"], row["when"]["query"]["fields"], row["when"]["field"],
                          row["when"]["of"], row["when"]["op"], row["when"]["value"]),
                         ("actors", ["prop:Speed"], "prop:Speed", "max", ">", 300.0))

    def test_the_local_runner_writes_the_plugins_form(self):
        task = task_with(reading([{"t": 2, "shot": "result", "when": EVENT}]))
        sent = tasks.task_plays(task)["result"]["inputs"]
        written = played({"track": [], "camera": [], "screenshots": []}, sent)
        self.assertEqual(written[0]["when"]["field"], "count")
        self.assertIn("query", written[0]["when"])

    def test_a_shots_event_reads_only_what_the_probe_reads_every_frame(self):
        for measure in ({"probe": "ui", "field": "count"},
                        {"probe": "widgets", "select": {"name": "W"}, "field": "text", "match": "x"},
                        {"probe": "actors", "select": {"class": "Boat"}, "field": "speed"},
                        {"probe": "actors", "select": {"class": "Boat"}, "field": "x", "to_axis": 0},
                        {"probe": "actors", "select": {"class": "Lamp", "has": {"class": "PointLight", "lit": True}},
                         "field": "count"},
                        {"probe": "widgets", "select": {"name": "W"}, "field": "count", "window": [0, 1]}):
            with self.assertRaises(ValueError, msg=measure):
                task_with(reading([{"t": 1, "shot": "s", "when": {"measure": measure,
                                                                   "expect": {"op": ">=", "value": 1}}}]))
        for measure in ({"probe": "widgets", "select": {"name": "W"}, "field": "visible"},
                        {"probe": "actors", "select": {"class": "Boat"}, "field": "hidden"},
                        {"probe": "actors", "select": {"class": "Boat"}, "field": "prop:Health", "of": "min"}):
            task_with(reading([{"t": 1, "shot": "s", "when": {"measure": measure, "expect": {"op": ">=", "value": 1}}}]))

    def test_a_shot_whose_event_never_came_is_a_missed_input(self):
        found = {"inputs_missed": [missed(2.0, probes.SHOT_WHEN, "result", probes.NEVER),
                                   missed(3.0, "shot", "plain", "could not write it")]}
        self.assertEqual([r["kind"] for r in probes.missed(found)], ["shot_when"])


class Covered(unittest.TestCase):
    def test_no_click_option_excuses_a_covered_click(self):
        found = {"inputs_missed": [missed(3.0, "click", "Buy", COVERED)]}
        sent = [{"t": 3.0, "widget": "Buy", "click": True, "optional": True, "disabled": True}]
        self.assertEqual(probes.COVERED, COVERED)
        self.assertEqual(len(probes.excused(found, sent)["inputs_missed"]), 1)

    def test_a_widget_may_be_read_covered(self):
        task = task_with(reading([{"t": 1, "key": "E", "press": True}],
                                 measure={"probe": "widgets", "select": {"name": "Buy"}, "field": "covered",
                                          "at": "end"}))
        (queries,) = probes.plan(task).values()
        self.assertEqual(queries[0]["fields"], ["covered"])


class LongPlays(unittest.TestCase):
    def test_a_play_may_last_up_to_300_s_and_no_longer(self):
        task_with(reading([{"t": 299, "shot": "late"}, {"t": 10, "teleport": [0, 0, 0], "hold": 290}], seconds=300))
        task_with(probe(name="late", play=play([{"t": 1, "key": "E", "press": True}], 300),
                        measure={"probe": "actors", "select": {"class": "Boss"}, "field": "count",
                                 "window": [200, 299]}))
        for bad in (reading([{"t": 1, "key": "E", "press": True}], seconds=301),
                    reading([{"t": 301, "key": "E", "press": True}], seconds=300),
                    reading([{"t": 1, "shot": "s", "when": {**EVENT, "within": 301}}])):
            with self.assertRaises(ValueError):
                task_with(bad)


class Machine:
    def __init__(self, written):
        self.written, self.sent = written, None

    def editor(self):
        return Path("UnrealEditor.exe")

    def job(self, label, argv, cwd, timeout):
        out = next(a.split("=", 1)[1] for a in map(str, argv) if a.startswith("-TaskProbeOut="))
        keys = next(a.split("=", 1)[1] for a in map(str, argv) if a.startswith("-TaskProbeInputs="))
        self.sent = json.loads(Path(keys).read_text(encoding="utf-8"))
        (Path(out) / "probe.json").write_text(json.dumps(self.written))
        return unreal.Result(0, "", 1.0)


def played(written, inputs):
    """The inputs file the local runner hands the plugin for one play of a scratch copy."""
    with tempfile.TemporaryDirectory() as tmp:
        machine = Machine(written)
        project = unreal.Project(tmp, machine, "game start")
        with mock.patch.object(project, "uproject", return_value=Path("Game.uproject")):
            project.play(10, 0, 60, inputs=inputs)
        return machine.sent


if __name__ == "__main__":
    unittest.main()

"""A sampled measure's `since` as the Lab's game grader reads it since 1.15.0 (docs/task-probes.md 2.1 and 3): its window and
`at` count from the first sample at which its event's measure meets its literal expect, with neither the samples from
it on are read; the play samples the event's measure with its own; an event that never comes (within `within` s when
it says) leaves no value, "its event never happened", which fails a graded check and leaves a calibrated threshold
uncalibrated on the reference; an event's measure is one sample of a sampled measure; and a task without `since` reads
and digests as before."""

import json
import unittest

from helpers import FakeProject, probe, side, task_with

from task_check import check, probes, tasks
from task_check.digest import canonical_digest

EVENT = {"measure": {"probe": "widgets", "select": {"name": "WinBanner"}, "field": "count"},
         "expect": {"op": ">=", "value": 1}}
BOAT = {"probe": "actors", "select": {"class": "Boat"}, "field": "x", "of": "max"}


def measure(**more):
    return tasks.measure({**BOAT, **more})


def probe_file(banner_from):
    """Samples every 0.5 s for 10 s: the boat's x is 10 * t; the banner shows from `banner_from` s (None: never)."""
    ts = [i * 0.5 for i in range(21)]
    boat = probes.query_id(probes.needs(measure())[0])
    banner = probes.query_id(probes.needs(tasks.measure(EVENT["measure"]))[0])
    shown = lambda t: banner_from is not None and t >= banner_from  # noqa: E731
    return {"format": "game-probe/1", "ended": "time", "seconds": 10.0, "track": [], "camera": [],
            "inputs_missed": [], "measures": {
                boat: [{"t": t, "rows": [{"name": "Boat_0", "x": 10 * t}]} for t in ts],
                banner: [{"t": t, "rows": [{"name": "WinBanner"}] if shown(t) else [], "total": 1 if shown(t) else 0}
                         for t in ts]}}


class Reading(unittest.TestCase):
    def test_a_window_counts_from_its_event(self):
        found = probe_file(4.0)
        self.assertEqual(probes.measured(measure(since=EVENT, window=[0, 1], agg="max"), found), (50.0, None),
                         "the boat's x 1 s after the banner showed at 4 s")
        self.assertEqual(probes.measured(measure(since=EVENT, at=[0.5]), found)[0], 45.0)
        self.assertEqual(probes.measured(measure(since=EVENT, agg="min"), found)[0], 40.0, "the samples from it on")
        self.assertEqual(probes.measured(measure(since=EVENT, at="end"), found)[0], 100.0)
        self.assertEqual(probes.measured(measure(window=[0, 1], agg="max"), found)[0], 10.0, "no since: as before")

    def test_an_event_that_never_comes_reads_nothing_and_says_so(self):
        value, why = probes.measured(measure(since=EVENT, window=[0, 1]), probe_file(None))
        self.assertIsNone(value)
        self.assertEqual(why, "its event never happened (its widgets count never read >= 1)")
        value, why = probes.measured(measure(since={**EVENT, "within": 3}, window=[0, 1]), probe_file(4.0))
        self.assertIsNone(value)
        self.assertTrue(why.endswith("never read >= 1 in the play's first 3 s)"), why)
        self.assertEqual(probes.measured(measure(since={**EVENT, "within": 4}, window=[0, 1], agg="max"),
                                         probe_file(4.0))[0], 50.0, "an event at `within` itself counts")

    def test_an_events_expect_is_met_as_a_threshold_is(self):
        for op, value, at in (("==", 1, 4.0), ("!=", 0, 4.0), (">", 0, 4.0), ("<", 1, 0.0), ("<=", 0, 0.0)):
            event = {**EVENT, "expect": {"op": op, "value": value}}
            self.assertEqual(probes.event_time(tasks.event(event), probe_file(4.0)), (at, None), op)

    def test_the_play_samples_the_events_measure_with_its_own(self):
        tied = probe("crossed", play={"name": "race", "seconds": 10, "inputs": [{"t": 1, "key": "W", "press": True}]},
                     measure={**BOAT, "since": EVENT, "window": [0, 1]}, expect={"op": ">=", "value": 30})
        task = task_with(tied)
        (queries,) = probes.plan(task).values()
        self.assertEqual(sorted(q["kind"] for q in queries), ["actors", "widgets"])
        self.assertEqual([q["kind"] for q in probes.all_needs(measure(since=EVENT))], ["actors", "widgets"])
        self.assertIsNone(measure()["since"])


class Grading(unittest.TestCase):
    PLAY = {"name": "race", "seconds": 10, "inputs": [{"t": 1, "key": "W", "press": True}]}

    def task(self, expect):
        return task_with(probe("crossed", play=self.PLAY, measure={**BOAT, "since": EVENT, "window": [0, 1],
                                                                    "agg": "max"}, expect=expect))

    @staticmethod
    def answering(banner_from):
        return FakeProject(lambda seconds, shots, queries: (probe_file(banner_from), "LogInit: ready\n"))

    def test_a_graded_play_whose_event_never_comes_fails_saying_so(self):
        task = self.task({"op": ">=", "value": 30})
        found = check.Grade(task, "reference", side("start", FakeProject(), task),
                            side("reference", self.answering(None), task), {}).run()
        (row,) = found["checks"]
        self.assertFalse(row["passed"])
        self.assertTrue(row["detail"].endswith(
            "measured nothing, threshold >= 30: its event never happened (its widgets count never read >= 1)"),
            row["detail"])
        passed = check.Grade(task, "reference", side("start", FakeProject(), task),
                             side("reference", self.answering(4.0), task), {}).run()
        self.assertTrue(passed["checks"][0]["passed"], passed["checks"])

    def test_a_reference_whose_event_never_comes_leaves_a_calibrated_threshold_uncalibrated(self):
        task = self.task({"op": ">=", "calibrate": 0.5})
        found = check.Grade(task, "reference", side("start", self.answering(4.0), task),
                            side("reference", self.answering(None), task), {}).run()
        (row,) = found["checks"]
        self.assertFalse(row["passed"])
        self.assertTrue(row["detail"].startswith("uncalibrated: crossed: the reference measured nothing (its event "
                                                 "never happened"), row["detail"])


class Shape(unittest.TestCase):
    def test_an_events_measure_is_one_sample_of_a_sampled_measure_against_a_literal(self):
        ok = probe("crossed", measure={**BOAT, "since": {**EVENT, "within": 30}, "window": [0, 1]})
        task_with(ok)
        bad = [
            ({**EVENT, "measure": {**EVENT["measure"], "window": [0, 2]}}, "takes no window of its own"),
            ({**EVENT, "measure": {**EVENT["measure"], "agg": "max"}}, "takes no agg of its own"),
            ({**EVENT, "measure": {"probe": "log", "pattern": "x"}}, "one the probe samples"),
            ({**EVENT, "measure": {"probe": "audio", "field": "sounds"}}, "one the probe samples"),
            ({**EVENT, "measure": {"probe": "widgets", "select": {}, "field": "count"}}, "names its class, its name"),
            ({**EVENT, "expect": {"op": ">=", "calibrate": 0.5}}, "since"),
            ({**EVENT, "within": 0}, "within"),
            ({**EVENT, "within": 121}, "within"),
            ({**EVENT, "after": 2}, "since"),
        ]
        for since, said in bad:
            with self.assertRaises(ValueError, msg=since) as caught:
                task_with(probe("crossed", measure={**BOAT, "since": since, "window": [0, 1]}))
            self.assertIn(said, str(caught.exception))
        with self.assertRaises(ValueError):  # a measure the play doesn't sample takes no since
            task_with(probe("logged", measure={"probe": "log", "pattern": "x", "since": EVENT}))

    def test_reading_a_task_leaves_its_digest(self):
        """The digest is of the task as written: filling in `since` (None when unset) never reaches it."""
        task = task_with(probe(), probe("crossed", measure={**BOAT, "since": EVENT}))
        before = canonical_digest(task)
        self.assertIsNone(tasks.checks(task)[0][1]["measure"]["since"])
        probes.plan(task)
        self.assertEqual(canonical_digest(task), before)
        self.assertNotIn("since", task["milestones"][0]["checks"][0]["measure"])

if __name__ == "__main__":
    unittest.main()

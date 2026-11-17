"""A check no version of the game can pass is a task error, as the cloud grader makes it (docs/task-check.md): a task
play whose inputs don't land on the reference, and a probe whose selector reads nothing in the reference's play. Either
makes the task INVALID, `required` or not. A missed input on the start alone fails the start's check."""

import unittest

from helpers import FakeProject, measuring, probe, side, task_with

from task_check import check, probes, tasks, verdict

PLAY = {"name": "opens", "seconds": 10, "inputs": [{"t": 1.0, "click": True, "widget": "Open"}]}
MISS = [{"t": 1.0, "kind": "click", "target": "Open", "why": "no visible button matches it, UMG or Slate"}]


def missing(z, missed=()):
    """A play answer like measuring(z) whose probe file lists `missed` in inputs_missed."""
    def play(seconds, shots, queries):
        found, log = measuring(z)(seconds, shots, queries)
        return {**found, "inputs_missed": list(missed)}, log
    return play


def matching_nothing(z):
    """A play answer like measuring(z) whose actors queries match no row in any sample."""
    def play(seconds, shots, queries):
        found, log = measuring(z)(seconds, shots, queries)
        for q in (queries or {}).get("queries", []):
            if q["kind"] == "actors":
                found["measures"][q["id"]] = [{"t": s["t"], "rows": []} for s in found["measures"][q["id"]]]
        return found, log
    return play


def graded(task, start_answer, reference_answer):
    start = side("start", FakeProject(start_answer), task)
    reference = side("reference", FakeProject(reference_answer), task)
    thresholds = {}
    ref = check.Grade(task, "reference", start, reference, thresholds).run()
    own = check.Grade(task, "start", start, reference, thresholds).run()
    return ref, own


class Landing(unittest.TestCase):
    def task(self, **over):
        return task_with(probe("opened", play=PLAY, measure={"probe": "pawn", "field": "z", "agg": "max"},
                               expect={"op": ">=", "value": 100}, **over))

    def test_an_input_the_reference_missed_is_a_task_error(self):
        for required in (True, False):
            task = self.task(required=required)
            ref, own = graded(task, missing(0), missing(120, MISS))
            self.assertIn("opened", ref["task_errors"])
            self.assertTrue(ref["checks"][0]["detail"].startswith("task error: "))
            self.assertIn("an input did not land (click Open at 1 s", ref["task_errors"]["opened"])
            valid, why, _ = verdict.verdict(task, ref, own)
            self.assertFalse(valid)
            self.assertTrue(any(w.startswith("task error in opened:") for w in why), why)

    def test_an_input_only_the_start_missed_fails_the_start(self):
        task = self.task()
        ref, own = graded(task, missing(150, MISS), missing(120))
        self.assertEqual(ref["task_errors"], {})
        self.assertTrue(ref["checks"][0]["passed"])
        row = own["checks"][0]
        self.assertFalse(row["passed"], "the start's play didn't do what the task says, whatever it measured")
        self.assertIn("the play's input did not land: click Open at 1 s", row["detail"])
        self.assertEqual(verdict.verdict(task, ref, own)[:2], (True, []))

    def test_every_input_landed(self):
        task = self.task()
        ref, own = graded(task, missing(0), missing(120))
        self.assertEqual((ref["task_errors"], own["task_errors"]), ({}, {}))
        self.assertEqual(verdict.verdict(task, ref, own)[:2], (True, []))

    def test_a_named_shot_not_written_is_no_missed_input(self):
        self.assertEqual(probes.missed({"inputs_missed": [{"t": 1, "kind": "shot", "target": "a", "why": "x"}]}), [])
        self.assertIsNone(probes.missed({}), "a probe file from before the plugin said: it can't say")


class Unreadable(unittest.TestCase):
    WALLS = {"probe": "actors", "select": {"class": "SCCastlePiece"}, "field": "z", "of": "max"}

    def test_a_selector_that_matches_nothing_on_the_reference_is_a_task_error(self):
        for required in (True, False):
            task = task_with(probe(), probe("walls", measure=self.WALLS, expect={"op": ">", "value": 100},
                                            required=required))
            ref, own = graded(task, matching_nothing(0), matching_nothing(120))
            self.assertIn("walls", ref["task_errors"])
            self.assertIn("matched nothing in 41 samples: the check reads nothing even on the task's own fix",
                          ref["task_errors"]["walls"])
            valid, why, _ = verdict.verdict(task, ref, own)
            self.assertFalse(valid)
            self.assertTrue(any(w.startswith("task error in walls:") for w in why), why)

    def test_one_that_matches_on_the_reference_is_the_starts_doing(self):
        task = task_with(probe("walls", measure=self.WALLS, expect={"op": ">", "value": 100}))
        ref, own = graded(task, matching_nothing(0), measuring(120))
        self.assertEqual((ref["task_errors"], own["task_errors"]), ({}, {}))
        self.assertFalse(own["checks"][0]["passed"])

    def test_a_count_of_nothing_is_an_answer(self):
        """A count reads 0 of no match: a task error only when 0 fails the threshold on the reference."""
        gone = {"probe": "actors", "select": {"class": "SCCastlePiece"}, "field": "count"}
        task = task_with(probe("none_left", measure=gone, expect={"op": "<=", "value": 0}))
        ref, own = graded(task, measuring(0), matching_nothing(0))
        self.assertEqual(ref["task_errors"], {})
        self.assertTrue(ref["checks"][0]["passed"])
        task = task_with(probe("some_left", measure=gone, expect={"op": ">=", "value": 1}))
        ref, own = graded(task, measuring(0), matching_nothing(0))
        self.assertIn("the task's own fix fails it", ref["task_errors"]["some_left"])

    def test_reads_nothing(self):
        measure = tasks.measure(self.WALLS)
        qid = probes.query_id(probes.needs(measure)[0])
        empty = {"measures": {qid: [{"t": 0.5, "rows": []}]}}
        self.assertIn("matched nothing in 1 samples", probes.reads_nothing(measure, empty))
        self.assertIsNone(probes.reads_nothing(measure, {"measures": {qid: [{"t": 0.5, "rows": [{"z": 1}]}]}}))
        self.assertIsNone(probes.reads_nothing(measure, {"measures": {}}), "never sampled: the play's own failure")
        self.assertIn("had a value for z", probes.reads_nothing(measure, {"measures": {qid: [{"t": 0.5,
                                                                                               "rows": [{"x": 1}]}]}}))


if __name__ == "__main__":
    unittest.main()

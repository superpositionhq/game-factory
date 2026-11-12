"""A task play's `after` (docs/task-probes.md 1.1): the plays it names are played on the same side first, a failed one
too; a task with no `after` plays in the order it always did; and a name that is no task play of the task, the play
itself or a cycle is refused."""

import unittest

from helpers import FakeProject, measuring, probe, side, task_with

from task_check import judges, tasks

MEASURE = {"probe": "pawn", "field": "z", "agg": "max"}


def play(name, seconds, after=None):
    found = {"name": name, "seconds": seconds, "inputs": [{"t": 1.0, "key": "E", "press": True}]}
    return {**found, "after": after} if after is not None else found


def reading(name, of):
    return probe(name=name, play=of, measure=MEASURE)


class PlayOrder(unittest.TestCase):
    def played(self, task, project):
        s = side("reference", project, task)
        for _, c in tasks.checks(task):
            s.value(c)
        return [p["seconds"] for p in project.plays]

    def test_a_play_runs_after_the_plays_it_names(self):
        task = task_with(reading("reads", play("reads", 20, ["writes"])), reading("writes", play("writes", 10)))
        self.assertEqual(self.played(task, FakeProject(measuring(0))), [10, 20])

    def test_with_no_after_the_plays_keep_their_order(self):
        task = task_with(reading("reads", play("reads", 20)), reading("writes", play("writes", 10)))
        self.assertEqual(self.played(task, FakeProject(measuring(0))), [20, 10])
        self.assertEqual(tasks.task_plays(task)["reads"]["after"], [])

    def test_a_play_after_a_failed_one_still_runs(self):
        task = task_with(reading("reads", play("reads", 20, ["writes"])), reading("writes", play("writes", 10)))
        crashes, fine = measuring(0, crash=True), measuring(0)
        project = FakeProject(lambda seconds, shots, queries: (crashes if seconds == 10 else fine)(seconds, shots,
                                                                                                    queries))
        s = side("reference", project, task)
        value, _ = s.value(tasks.checks(task)[0][1])
        self.assertEqual([p["seconds"] for p in project.plays], [10, 20])
        self.assertIsNotNone(value, "the dependant read what the failed play left")

    def test_a_judges_play_may_run_after_a_probes(self):
        judge = {"kind": "judge", "name": "looks_saved", "question": "Is the level kept?",
                 "rubric": [{"key": "kept", "criterion": "The level is kept."}],
                 "plays": [play("shown", 20, ["writes"])]}
        task = task_with(judge, reading("writes", play("writes", 10)))
        project = FakeProject(measuring(0))
        side("reference", project, task).judge_plays(judges.judge(tasks.checks(task)[0][1]))
        self.assertEqual([p["seconds"] for p in project.plays], [10, 20])

    def test_unknown_names_itself_and_cycles_are_refused(self):
        for checks, said in [
                ([reading("reads", play("reads", 20, ["nowhere"]))], "runs after nowhere, which is no task play"),
                ([reading("reads", play("reads", 20, ["look"]))], "runs after look, which is no task play"),
                ([reading("reads", play("reads", 20, ["reads"]))], "names itself in its after"),
                ([reading("one", play("one", 10, ["two"])), reading("two", play("two", 10, ["one"]))], "a cycle")]:
            with self.assertRaises(ValueError) as caught:
                task_with(*checks)
            self.assertIn(said, str(caught.exception))
        with self.assertRaises(ValueError):  # a check carries no after: it is a task play's alone
            task_with({**reading("reads", play("reads", 20)), "after": ["writes"]})


if __name__ == "__main__":
    unittest.main()

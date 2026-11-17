"""A task play's `after` (docs/task-probes.md 1.1): the plays it names are played on the same side first, a failed one
too; a task with no `after` plays in the order it always did; and a name that is no task play of the task, the play
itself or a cycle is refused. A task play's `continues`: it is played after a first session of its own, on a cleared
save; a first session that didn't end cleanly, or a reference's that saved nothing, gives its checks no value."""

import unittest

from helpers import FakeProject, measuring, probe, side, task_with

from task_check import judges, tasks

MEASURE = {"probe": "pawn", "field": "z", "agg": "max"}


def play(name, seconds, after=None, continues=None):
    found = {"name": name, "seconds": seconds, "inputs": [{"t": 1.0, "key": "E", "press": True}]}
    found = {**found, "continues": continues} if continues is not None else found
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


class Sessions(unittest.TestCase):
    def task(self):
        return task_with(reading("kept", play("restarted", 20, continues="earns")), reading("earned", play("earns", 10)))

    def test_a_continuing_play_runs_after_a_first_session_of_its_own(self):
        task, project = self.task(), FakeProject(measuring(5))
        s = side("reference", project, task)
        for _, c in tasks.checks(task):
            self.assertEqual(s.value(c), (5.0, None))
        self.assertEqual([(p["seconds"], p["session"]) for p in project.plays], [(10, True), (20, False), (10, False)],
                         "the first session, the play, then the named play's own reading (never the first session)")
        self.assertEqual(project.plays[0]["shots"], 1)
        self.assertEqual(sorted(s.played), ["play_earns", "play_restarted", "play_restarted-first"])
        self.assertEqual(tasks.task_plays(task)["earns"]["continues"], None)

    def test_a_first_session_that_crashed_gives_no_value(self):
        crashes, fine = measuring(0, crash=True), measuring(0)
        answer = lambda seconds, shots, queries: (crashes if seconds == 10 else fine)(seconds, shots, queries)  # noqa: E731
        task = self.task()
        for name, said in (("start", "the play's first session (play earns) did not end cleanly (crashed), so the game "
                                     "never quit as a player's game does and nothing it should have saved can be "
                                     "trusted"),
                           ("reference", "in the reference's play restarted, its first session (play earns) did not "
                                         "end cleanly (crashed), so the game never quit as a player's game does and "
                                         "nothing it should have saved can be trusted: the task's own fix carries "
                                         "nothing over to the next session")):
            self.assertEqual(side(name, FakeProject(answer), task).value(tasks.checks(task)[0][1]), (None, said))

    def test_a_game_that_quit_by_itself_ended_cleanly(self):
        def quits(seconds, shots, queries):
            found, log = measuring(3)(seconds, shots, queries)
            return ({**found, "ended": "shutdown"} if seconds == 10 else found), log

        task = self.task()
        self.assertEqual(side("reference", FakeProject(quits), task).value(tasks.checks(task)[0][1]), (3.0, None))

    def test_a_reference_whose_first_session_saved_nothing_carries_nothing_over(self):
        task = self.task()
        value, why = side("reference", FakeProject(measuring(0), saved=()), task).value(tasks.checks(task)[0][1])
        self.assertIsNone(value)
        self.assertEqual(why, "in the reference's play restarted, its first session (play earns) wrote nothing under "
                              "the game's Saved folder, so the relaunched game had nothing to load: the task's own fix "
                              "carries nothing over to the next session")
        value, why = side("start", FakeProject(measuring(0), saved=()), task).value(tasks.checks(task)[0][1])
        self.assertEqual((value, why), (0.0, None), "a start that saves nothing is read as it measured")

    def test_what_a_session_may_continue(self):
        for checks, said in [
                ([reading("a", play("a", 20, continues="a"))], "task play a continues itself"),
                ([reading("a", play("a", 20, continues="look"))], "continues look, which is no task play of the task"),
                ([reading("a", play("a", 20, continues="b")), reading("b", play("b", 10, continues="c")),
                  reading("c", play("c", 10))],
                 "task play a continues b, which itself continues a session or runs after other plays: a first session "
                 "starts from a cleared save, alone"),
                ([reading("a", play("a", 20, continues="b")), reading("b", play("b", 10, after=["c"])),
                  reading("c", play("c", 10))], "which itself continues a session or runs after other plays"),
                ([reading("a", play("a", 20, after=["c"], continues="b")), reading("b", play("b", 10)),
                  reading("c", play("c", 10))],
                 "task play a continues a session and runs after plays too: name one or the other")]:
            with self.assertRaises(ValueError) as caught:
                task_with(*checks)
            self.assertIn(said, str(caught.exception))


class SavedFiles(unittest.TestCase):
    def test_a_first_sessions_writes_are_listed_without_the_checkers_own(self):
        import os
        import tempfile
        import time
        from pathlib import Path

        from task_check import unreal

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for name in ("Saved/SaveGames/Old.sav", "Saved/SaveGames/Slot.sav", "Saved/Config/Windows/Game.ini",
                         "Saved/TaskProbe/play/probe.json", "Saved/Logs/Play.log", "Saved/Crashes/c.txt"):
                (project / name).parent.mkdir(parents=True, exist_ok=True)
                (project / name).write_text("x")
            began = time.time()
            os.utime(project / "Saved/SaveGames/Old.sav", (began - 60, began - 60))
            self.assertEqual(unreal._saved(project, began - 1),
                             ["Saved/Config/Windows/Game.ini", "Saved/SaveGames/Slot.sav"])


if __name__ == "__main__":
    unittest.main()

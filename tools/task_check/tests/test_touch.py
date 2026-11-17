"""Touches and the render reading in a task (docs/task-probes.md 1.5 and 2.21): a task play may send `tap` and `drag`
inputs, one finger's touches at least 0.1 s apart and over by the play's end; a probe may read what the renderer drew,
never in a play that also makes the probe capture. A task with neither is read as it always was."""

import unittest

from helpers import probe, task_with

MOVED = {"probe": "pawn", "field": "z", "agg": "max"}
BUDGET = {"probe": "render", "field": "draw_calls", "agg": "max"}
GLOW = {"probe": "actors", "select": {"tag": "Lamp"}, "field": "glow"}
RELATIVE = {"op": ">=", "start_plus": 1.0}


def play(inputs, seconds=10):
    return {"name": "thumbs", "seconds": seconds, "inputs": inputs}


def refused(*checks):
    with_error = None
    try:
        task_with(*checks)
    except ValueError as e:
        with_error = str(e)
    return with_error


class Touches(unittest.TestCase):
    def test_taps_and_drags_are_inputs(self):
        inputs = [{"t": 1.0, "tap": [0.5, 0.5]}, {"t": 1.0, "tap": {"widget": "FireButton"}, "hold": 0.5, "finger": 1},
                  {"t": 3.0, "drag": [{"widget": "MoveStick"}, [0.2, 0.6]], "over": 0.3, "hold": 2.0},
                  {"t": 3.5, "drag": [[0.6, 0.4], [0.7, 0.4]], "finger": 1}, {"t": 6.0, "key": "Android_Back", "press": True}]
        task_with(probe(play=play(inputs), measure=MOVED))

    def test_a_task_of_keys_alone_is_read_as_before(self):
        task_with(probe(play=play([{"t": 1.0, "key": "W", "press": True}, {"t": 2.0, "key": "W", "press": False}]),
                        measure=MOVED))

    def test_a_malformed_touch_is_refused(self):
        for bad in ({"t": 1.0, "tap": [1.5, 0.5]}, {"t": 1.0, "tap": [0.5]}, {"t": 1.0, "tap": {"widget": "a b"}},
                    {"t": 1.0, "tap": [0.5, 0.5], "finger": 10}, {"t": 1.0, "drag": [[0.5, 0.5]]},
                    {"t": 1.0, "tap": [0.5, 0.5], "over": 1.0}):
            self.assertIsNotNone(refused(probe(play=play([bad]), measure=MOVED)), bad)

    def test_a_finger_is_up_a_tenth_of_a_second_before_it_goes_down_again(self):
        for inputs in ([{"t": 1.0, "tap": [0.5, 0.5], "hold": 3.0}, {"t": 2.0, "tap": [0.1, 0.1]}],
                       [{"t": 1.0, "tap": [0.5, 0.5]}, {"t": 1.01, "tap": [0.5, 0.5]}],
                       [{"t": 1.0, "drag": [[0.1, 0.1], [0.2, 0.2]]}, {"t": 1.0001, "tap": [0.5, 0.5]}]):
            self.assertIn("less than 0.1 s after it lifts", refused(probe(play=play(inputs), measure=MOVED)) or "")
        task_with(probe(play=play([{"t": 1.0, "tap": [0.5, 0.5]}, {"t": 1.1, "tap": [0.5, 0.5]},
                                   {"t": 1.1, "tap": [0.6, 0.5], "finger": 1}]), measure=MOVED))

    def test_a_touch_is_over_by_the_plays_end(self):
        late = [{"t": 8.0, "drag": [[0.1, 0.1], [0.2, 0.2]], "over": 1.5, "hold": 1.0}]
        self.assertIn("a touch that ends after the play", refused(probe(play=play(late), measure=MOVED)) or "")


class Render(unittest.TestCase):
    def test_a_budget_is_read_with_a_literal_threshold(self):
        task_with(probe(name="budget", measure=BUDGET, expect={"op": "<=", "value": 700}))

    def test_a_render_measure_shares_no_play_with_a_capturing_reading(self):
        budget = probe(name="budget", measure=BUDGET, expect={"op": "<=", "value": 700})
        glows = probe(name="glows", measure=GLOW, expect=RELATIVE)
        self.assertIn("takes a render measure and also makes the probe capture", refused(budget, glows) or "")
        staged = play([{"t": 1.0, "teleport_to": {"has": {"lit": True}}}])
        self.assertIn("also makes the probe capture",
                      refused(probe(name="budget", play=staged, measure=BUDGET, expect={"op": "<=", "value": 700})) or "")
        task_with(budget, probe(name="glows", play="drive", measure=GLOW, expect=RELATIVE))
        task_with(glows)


class TouchesReachThePlugin(unittest.TestCase):
    """What the checker hands the plugin for a touch task (found on the studio PC, 2026-11-12: a task with a tap passed
    the validator and then stopped the checker, which read every input without a kind as a key)."""

    def test_a_tasks_touches_are_the_plugins_rows(self):
        from task_check import tasks
        inputs = [{"t": 1, "tap": {"widget": "FireButton"}}, {"t": 2, "tap": [0.5, 0.25], "hold": 0.5, "finger": 1},
                  {"t": 3, "drag": [{"widget": "MoveStick"}, [0.2, 0.6]], "over": 0.3, "hold": 2},
                  {"t": 6, "drag": [[0.6, 0.4], [0.7, 0.4]], "finger": 1}, {"t": 7, "key": "Android_Back", "press": True}]
        task = task_with(probe(play=play(inputs), measure=MOVED))
        self.assertEqual(tasks.checks(task)[0][1]["play"]["inputs"], [
            {"t": 1.0, "tap": {"widget": "FireButton"}, "finger": 0},
            {"t": 2.0, "tap": [0.5, 0.25], "finger": 1, "hold": 0.5},
            {"t": 3.0, "drag": [{"widget": "MoveStick"}, [0.2, 0.6]], "finger": 0, "over": 0.3, "hold": 2.0},
            {"t": 6.0, "drag": [[0.6, 0.4], [0.7, 0.4]], "finger": 1},
            {"t": 7.0, "key": "Android_Back", "press": True}])

    def test_a_render_reading_is_asked_of_the_plugin_and_read_back(self):
        from task_check import probes, tasks
        task = task_with(probe(name="budget", measure=BUDGET, expect={"op": "<=", "value": 700}))
        measure = tasks.checks(task)[0][1]["measure"]
        self.assertEqual(probes.needs(measure), [{"kind": "render", "fields": ["draw_calls"]}])
        qid = probes.query_id(probes.needs(measure)[0])
        played = {"measures": {qid: [{"t": 0.5, "value": {"draw_calls": 310}}, {"t": 1.0, "value": {"draw_calls": 742}}]}}
        self.assertEqual(probes.series(measure, played), [(0.5, 310.0), (1.0, 742.0)])

    def test_a_mobile_games_drive_is_by_touch_and_a_desktop_games_by_keys(self):
        from types import SimpleNamespace

        from task_check import check
        phone, desk, fake = (SimpleNamespace(mobile=lambda: "portrait"), SimpleNamespace(mobile=lambda: None),
                             SimpleNamespace())
        self.assertEqual(check.own_play("drive", desk), check.PLAYS["drive"])
        self.assertEqual(check.own_play("drive", fake), check.PLAYS["drive"])
        self.assertEqual(check.own_play("look", phone), check.PLAYS["look"])
        seconds, shots, inputs = check.own_play("drive", phone)
        self.assertEqual((seconds, shots), check.PLAYS["drive"][:2])
        self.assertTrue(all("tap" in i or "drag" in i for i in inputs))
        task_with(probe(play={"name": "thumbs", "seconds": seconds, "inputs": inputs}, measure=MOVED))  # its own rules


class CodeJudgeFocus(unittest.TestCase):
    """A code judge may name the files its question is about, as the Lab's grader takes it."""

    @staticmethod
    def judge(**more):
        return {"kind": "code_judge", "name": "fixed_at_its_cause", "required": False, "question": "Is it fixed at its cause?",
                "rubric": [{"key": "cause", "criterion": "The cause is fixed."}], **more}

    def test_a_focus_of_project_file_globs_is_taken(self):
        task_with(probe(measure=MOVED), self.judge(focus=["Source/*", "Scripts/make_data.py"]))
        task_with(probe(measure=MOVED), self.judge())

    def test_a_focus_outside_the_project_or_too_long_is_refused(self):
        for bad in (["/etc/passwd"], ["../other/*"], ["Source/*"] * 9, "Source/*"):
            self.assertIsNotNone(refused(probe(measure=MOVED), self.judge(focus=bad)), bad)


if __name__ == "__main__":
    unittest.main()

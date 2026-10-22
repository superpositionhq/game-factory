"""The task check's rules: thresholds and the VALID/INVALID verdict from the two sides' check rows."""

import unittest

from helpers import NO_FIX, SEED, checked, first_check, probe, record, task_with

from task_check import verdict


def broken_start_task(*checks, seed=SEED):
    """A task whose start doesn't build: making it build is the task."""
    return task_with(milestones=[{"name": "builds", "checks": [{"kind": "build", "name": "editor_builds",
                                                                "fails_at_start": True}]},
                                 {"name": "graded", "checks": [{"kind": "boot", "name": "boots_clean", "seconds": 60,
                                                                "needs": ["editor_builds"]}, *checks]}], seed=seed)


class Thresholds(unittest.TestCase):
    def test_literal_calibrated_and_start_relative_thresholds(self):
        self.assertEqual(verdict.threshold({"op": ">=", "value": 3}), 3.0)
        self.assertEqual(verdict.threshold({"op": ">=", "calibrate": 0.5}, -500.0, 100.0), -200.0)
        self.assertEqual(verdict.threshold({"op": ">=", "start_times": 2}, 60.0), 120.0)
        self.assertEqual(verdict.threshold({"op": ">=", "start_plus": 50}, 60.0), 110.0)

    def test_a_start_that_measures_nothing_anchors_a_calibrated_threshold_on_the_reference(self):
        self.assertEqual(verdict.threshold({"op": ">=", "calibrate": 0.5}, None, 100.0), 75.0)
        self.assertEqual(verdict.threshold({"op": "<=", "calibrate": 0.5}, None, -40.0), -30.0)
        self.assertEqual(verdict.threshold({"op": "<=", "calibrate": 0.5}, None, 40.0), 50.0)

    def test_make_threshold_refuses_what_it_cant_calibrate(self):
        check = first_check(task_with(probe(expect={"op": ">=", "calibrate": 0.5})))
        self.assertEqual(verdict.make_threshold(check, (-500.0, None), (100.0, None)), (-200.0, -500.0, 100.0))
        with self.assertRaisesRegex(verdict.Uncalibrated, "both measure 100"):
            verdict.make_threshold(check, (100.0, None), (100.0 + 1e-5, None))
        with self.assertRaisesRegex(verdict.Uncalibrated, "the reference measured nothing"):
            verdict.make_threshold(check, (0.0, None), (None, "the play wrote no probe file"))
        relative = first_check(task_with(probe(expect={"op": ">=", "start_plus": 5}), seed=NO_FIX))
        with self.assertRaisesRegex(verdict.Uncalibrated, "the start measured nothing"):
            verdict.make_threshold(relative, (None, "crashed"), (None, None))
        literal = first_check(task_with(probe()))
        asked = []
        self.assertEqual(verdict.make_threshold(literal, lambda: asked.append(1), lambda: asked.append(2)),
                         (0.0, None, None))
        self.assertEqual(asked, [], "a literal threshold measures neither side")

    def test_passes_and_equality_within_1e_9(self):
        self.assertTrue(verdict.passes(1.0 + 1e-12, "==", 1.0))
        self.assertTrue(verdict.passes(2.0, "!=", 1.0))
        self.assertFalse(verdict.passes(1.0, ">", 1.0))
        self.assertTrue(verdict.passes(1.0, ">=", 1.0))

    def test_a_detail_names_the_measure_the_threshold_and_the_sides(self):
        check = first_check(task_with(probe(expect={"op": ">=", "calibrate": 0.5})))
        self.assertEqual(verdict.describe(check, 80.0, -200.0, -500.0, 100.0),
                         "The hero stands on the ground. | measured 80, threshold >= -200 (start -500, fix 100)")
        self.assertEqual(verdict.describe(check, None, 110.0, 60.0, None, "no samples in the window"),
                         "The hero stands on the ground. | measured nothing, threshold >= 110 (start 60): no samples "
                         "in the window")


class Verdict(unittest.TestCase):
    def test_the_reference_passes_every_required_probe_and_the_start_fails_one(self):
        task = task_with(probe(), probe("extra", required=False),
                         probe("built", play="trace", required=False, measure={"probe": "trace",
                                                                               "fact": "build_ok_at_end"}))
        ref = record(checked("hero_on_ground", "probe", True), checked("extra", "probe", False, "measured 3"),
                     checked("built", "probe", True, "not asked"))
        start = record(checked("hero_on_ground", "probe", False), checked("extra", "probe", True))
        self.assertEqual(verdict.verdict(task, ref, start), (True, [], ["reference fails extra (probe): measured 3"]))
        ref["checks"][0] = checked("hero_on_ground", "probe", False, "measured -500, threshold >= 0")
        start["checks"][0] = checked("hero_on_ground", "probe", True)
        valid, why, _ = verdict.verdict(task, ref, start)
        self.assertFalse(valid)
        self.assertEqual(why, ["reference fails hero_on_ground: measured -500, threshold >= 0",
                               "start already passes every required probe"])

    def test_a_task_with_no_reference_is_checked_on_its_start_alone(self):
        task = task_with(probe(expect={"op": ">=", "start_plus": 50}), seed=NO_FIX)
        self.assertTrue(verdict.verdict(task, None, record(checked("hero_on_ground", "probe", False)))[0])
        self.assertEqual(verdict.verdict(task, None, record(checked("hero_on_ground", "probe", True)))[1],
                         ["start already passes every required probe"])

    def test_the_reference_must_build_and_boot_and_its_other_checks_are_notes(self):
        task = task_with(probe(), {"kind": "file_exists", "name": "route_left", "glob": "Tests/*.json"},
                         {"kind": "boot", "name": "boots_clean"})
        ref = record(checked("hero_on_ground", "probe", True), checked("route_left", "file_exists", False, "0 file(s)"),
                     checked("boots_clean", "boot", False, "crashed"))
        start = record(checked("hero_on_ground", "probe", False))
        valid, why, notes = verdict.verdict(task, ref, start)
        self.assertFalse(valid)
        self.assertEqual(why, ["reference fails boots_clean: crashed"])
        self.assertEqual(notes, ["reference fails route_left (file_exists): 0 file(s)"], "a deliverable never decides")

    def test_a_still_works_probe_must_hold_at_the_start(self):
        """A still-works probe that never finds what it looks for would make a start-only task look valid."""
        task = task_with(milestones=[{"name": "done", "checks": [probe("roofs")]},
                                     {"name": "still_works", "checks": [probe("hud_shown")]}], seed=NO_FIX)
        broken = record(checked("roofs", "probe", True), checked("hud_shown", "probe", False, "measured 0"))
        valid, why, _ = verdict.verdict(task, None, broken)
        self.assertFalse(valid)
        self.assertEqual(why, ["start fails still-works hud_shown: measured 0",
                               "start already passes every required probe"], "a still-works failure is no gate")
        good = record(checked("roofs", "probe", False), checked("hud_shown", "probe", True))
        self.assertEqual(verdict.verdict(task, None, good), (True, [], []))
        crashed = record(checked("roofs", "probe", False, "x | measured nothing, threshold >= 1: the play wrote no "
                                                         "probe file"),
                         checked("hud_shown", "probe", False, "x | measured nothing, threshold >= 1: no samples"))
        self.assertEqual(verdict.verdict(task, None, crashed), (True, [], []), "a start the bug crashes measures nothing")

    def test_a_still_works_probe_counts_with_a_reference_too(self):
        task = task_with(milestones=[{"name": "fixed", "checks": [probe("fixed")]},
                                     {"name": "still_works", "checks": [probe("runs")]}])
        ref = record(checked("fixed", "probe", True), checked("runs", "probe", True))
        start = record(checked("fixed", "probe", False), checked("runs", "probe", False, "measured 3"))
        self.assertEqual(verdict.verdict(task, ref, start)[1], ["start fails still-works runs: measured 3"])
        only_still = record(checked("fixed", "probe", True), checked("runs", "probe", False, "measured 3"))
        self.assertEqual(verdict.verdict(task, ref, only_still)[1], ["start fails still-works runs: measured 3",
                                                                    "start already passes every required probe"])

    def test_a_start_that_doesnt_build_by_design_is_the_start_failing_the_task(self):
        task = broken_start_task(probe("roofs"))
        ref = record(checked("editor_builds", "build", True), checked("boots_clean", "boot", True),
                     checked("roofs", "probe", True))
        start = record(checked("editor_builds", "build", False, "the game as the task started didn't build (exit 6)"))
        self.assertEqual(verdict.verdict(task, ref, start), (True, [], []))
        builds = record(checked("editor_builds", "build", True, "the start built"), checked("roofs", "probe", False))
        self.assertEqual(verdict.verdict(task, ref, builds),
                         (False, ["start builds, though editor_builds says it doesn't (fails_at_start)"], []))

    def test_a_start_that_doesnt_build_by_design_trips_no_still_works_probe(self):
        task = task_with(milestones=[{"name": "builds", "checks": [{"kind": "build", "name": "editor_builds",
                                                                    "fails_at_start": True}]},
                                     {"name": "still_works", "checks": [probe("hud_shown")]}])
        start = record(checked("editor_builds", "build", False, "exit 6"))
        ref = record(checked("editor_builds", "build", True), checked("hud_shown", "probe", True))
        self.assertEqual(verdict.verdict(task, ref, start), (True, [], []))
        self.assertFalse(verdict.verdict(task, ref, record(checked("hud_shown", "probe", True)))[0],
                         "a start that passes everything is still no task")
        feature = task_with(milestones=task["milestones"], seed={**NO_FIX})
        self.assertEqual(verdict.verdict(feature, None, start), (True, [], []), "start-only")

    def test_a_task_whose_start_doesnt_build_never_plays_it(self):
        for check, said in [({**probe("roofs"), "expect": {"op": ">=", "calibrate": 0.5}}, "relative to the start"),
                            ({**probe("roofs"), "expect": {"op": ">=", "start_plus": 1}}, "relative to the start")]:
            with self.assertRaisesRegex(ValueError, said):
                broken_start_task(check)
            task_with(check)


if __name__ == "__main__":
    unittest.main()

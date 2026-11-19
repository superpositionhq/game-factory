"""Readings the Lab's game grader takes since 1.25.0 (docs/task-probes.md 2.16, 2.20a and 2.20b): `pad` (the force
feedback the game drives on the player's pad, every frame), `nav` (the path the game's navigation finds) and the audio
field `paused`."""

import unittest

from helpers import probe, task_with

from task_check import probes, tasks


def sampled(measure, values):
    qid = probes.query_id(probes.needs(measure)[0])
    return {"measures": {qid: [{"t": i * 0.5, "value": v} for i, v in enumerate(values)]}}


class Pad(unittest.TestCase):
    def test_rumble_reads_the_strongest_kick_and_effects_the_most_at_once(self):
        measure = tasks.measure({"probe": "pad", "field": "rumble", "window": [1, 2], "agg": "max"})
        self.assertEqual(probes.needs(measure), [{"kind": "pad", "fields": ["rumble"]}])
        found = sampled(measure, [{"rumble": 0, "effects": 0}, None, {"rumble": 0.0, "effects": 0},
                                  {"rumble": 0.8, "effects": 1}, {"rumble": 0.2, "effects": 1}])
        self.assertEqual(probes.reduce(measure, found), 0.8)
        effects = tasks.measure({"probe": "pad", "field": "effects", "agg": "max"})
        self.assertEqual(probes.reduce(effects, found), 1)

    def test_a_task_names_pad_rumble_and_nothing_else(self):
        task_with(probe(measure={"probe": "pad", "field": "rumble", "window": [1, 4], "agg": "max"},
                        expect={"op": ">", "value": 0}))
        with self.assertRaises(ValueError):
            task_with(probe(measure={"probe": "pad", "field": "vibration"}, expect={"op": ">", "value": 0}))


class Nav(unittest.TestCase):
    def test_a_path_reads_whole_and_how_far_round_it_goes(self):
        measure = tasks.measure({"probe": "nav", "from": {"xyz": [0, 0, 0]}, "to": {"actor": {"class": "Crate"}},
                                 "agent": {"class": "EnemyTank"}, "field": "detour", "at": [0.5]})
        (query,) = probes.needs(measure)
        self.assertEqual(query["kind"], "nav")
        self.assertEqual(query["to"], {"actor": {"class": "Crate"}, "offset": [0.0, 0.0, 0.0]})
        self.assertEqual(query["agent"], {"class": "EnemyTank"})
        found = sampled(measure, [None, {"found": 1, "partial": 0, "length": 3600.0, "detour": 1.2}])
        self.assertEqual(probes.reduce(measure, found), 1.2)

    def test_an_agent_is_optional_and_from_and_to_are_not(self):
        measure = tasks.measure({"probe": "nav", "from": {"pawn": True}, "to": {"xyz": [1, 2, 3]}, "field": "found"})
        self.assertNotIn("agent", probes.needs(measure)[0])
        task_with(probe(measure={"probe": "nav", "from": {"pawn": True}, "to": {"xyz": [1, 2, 3]}, "field": "found"},
                        expect={"op": "==", "value": 1}))
        with self.assertRaises(ValueError):
            task_with(probe(measure={"probe": "nav", "to": {"xyz": [1, 2, 3]}, "field": "found"},
                            expect={"op": "==", "value": 1}))


class Paused(unittest.TestCase):
    def test_paused_counts_the_paused_sounds(self):
        measure = tasks.measure({"probe": "audio", "select": {"sound": "Radio*"}, "field": "paused", "agg": "max"})
        found = sampled(measure, [{"count": 1, "audible": 1, "paused": 0}, {"count": 1, "audible": 0, "paused": 1}])
        self.assertEqual(probes.reduce(measure, found), 1)


if __name__ == "__main__":
    unittest.main()

"""Lab game grader 1.28.0's measure changes in the checker: an absence of actors or components reads 0 as an answer,
`signed` tells a heading from its opposite, and a spawns measure keeps the spawns `near` a point and counts `salvos`."""

import unittest

import helpers  # noqa: F401  (puts the tools folder on the path)

from task_check import probes, tasks

TS = [i * 0.5 for i in range(11)]


def m(**more):
    return tasks.measure(more)


class MeasureLimits(unittest.TestCase):
    def test_an_absence_of_a_combined_count_is_zero(self):
        lights = m(probe="components", select={"class": "SpotLightComponent", "owner": {"player": True}},
                   field="visible", of="count", agg="max")
        qid = probes.query_id(probes.needs(lights)[0])
        gone = {"seconds": 5.0, "measures": {qid: [{"t": t, "rows": []} for t in TS]}}
        self.assertTrue(probes.zero_of_nothing(lights, gone))
        unread = {"seconds": 5.0, "measures": {qid: [{"t": t, "rows": [{"visible": None}]} for t in TS]}}
        self.assertFalse(probes.zero_of_nothing(lights, unread))

    def test_signed(self):
        darts = m(probe="actors", select={"class": "Dart"}, field="yaw", to_angle=90)
        self.assertEqual([probes.angled(darts, v) for v in (0, 180)], [90.0, 90.0])
        self.assertEqual([probes.angled({**darts, "signed": True}, v) for v in (0, 180)], [-90.0, 90.0])

    def test_spawns_near_and_salvos(self):
        near = {"point": {"xyz": [0, 0, 400]}, "radius": 1000}
        salvos = m(probe="spawns", **{"class": "BBShell"}, field="salvos", near=near)
        places = [[1.0, 0, 0, 400], [1.0, 0, 0, 400], [2.2, 9000, 0, 10], [3.4, 0, 0, 400]]
        samples = [{"t": t, "value": {"spawned": 0, "destroyed": 0,
                                      "places": [p for p in places if (TS[i - 1] if i else -1) < p[0] <= t]}}
                   for i, t in enumerate(TS)]
        probe = {"seconds": 5.0, "track": [], "camera": [], "measures": {
            probes.query_id(probes.needs(salvos)[0]): samples}}
        self.assertEqual(probes.measured(salvos, probe)[0], 2.0)
        self.assertEqual(probes.measured({**salvos, "field": "spawned"}, probe)[0], 3.0)


if __name__ == "__main__":
    unittest.main()

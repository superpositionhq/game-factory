"""The game's mixed output as the Lab's game grader hears it since 1.26.0 (docs/task-probes.md 2.22): a `heard` measure
reads the mix's 50 ms blocks (loudness, peak, octave bands, a band's share, onsets), its play runs with sound, and an
`audio_judge` check is a judge the checker never asks."""

import unittest

from task_check import check, probes, tasks


def heard(field, **more):
    return {"probe": "heard", "field": field, **more}


def blocks(rows):
    qid = probes.query_id({"kind": "heard"})
    return {"track": [], "camera": [], "screenshots": [], "seconds": 10, "inputs_sent": 0, "measures": {qid: [
        {"t": t, "value": {"loudness": loud, "peak": loud + 3, **{f"band:{hz}": band for hz in tasks.HEARD_BANDS}}}
        for t, loud, band in rows]}}


class HeardTest(unittest.TestCase):
    def test_a_heard_measure_is_one_query_a_play_and_runs_with_sound(self):
        self.assertEqual(probes.needs(heard("loudness")), [{"kind": "heard"}])
        self.assertEqual(probes.query_id({"kind": "heard", "clips": [{"name": "w0_100", "from": 0, "to": 1}]}),
                         probes.query_id({"kind": "heard"}))
        self.assertEqual(probes.sound_flags([{"kind": "heard"}]), probes.HEARD)

    def test_onsets_count_the_sounds_that_start_and_shares_are_parts_of_the_energy(self):
        rows = [(i * 0.05, -80.0, -90.0) for i in range(10)]
        rows[4] = (0.2, -20.0, -30.0)
        rows[5] = (0.25, -20.0, -30.0)
        rows[8] = (0.4, -20.0, -30.0)
        values = [(s["t"], s["value"]) for s in next(iter(blocks(rows)["measures"].values()))]
        self.assertEqual(sum(v for _, v in probes.heard_series("onsets", values)), 2.0)
        self.assertAlmostEqual(probes.heard_series("share:63", values)[4][1], 1 / 8)
        self.assertEqual(probes.default_agg(heard("onsets")), "sum")
        self.assertEqual(probes.default_agg(heard("peak")), "mean")

    def test_an_audio_judge_is_never_asked_by_the_checker(self):
        self.assertIn("audio_judge", check.JUDGES)


if __name__ == "__main__":
    unittest.main()

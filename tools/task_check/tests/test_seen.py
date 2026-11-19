"""A `seen` probe in the local task check: the crop as the Lab crops it, the writer's answer read with the Lab's own
reduction, the crops and the blind copy saved, and answers kept across checks while their crops stay the same. Unreal
is faked; nothing asks a model."""

import json
import random
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

from helpers import FakeProject, measuring, probe, side, task_with
from test_check import make_game

from task_check import check, cli, seen, tasks, trial, unreal


def png(width, height, pixel, colour=6, interlace=0):
    """A PNG whose pixel (x, y) is `pixel(x, y)` (RGBA), each row under another filter (0 to 4), as an encoder may
    write it."""
    n = {2: 3, 6: 4}[colour]
    bpp, rows, prev = n, [], bytes(width * n)
    for y in range(height):
        line = bytes(v for x in range(width) for v in pixel(x, y)[:n])
        kind = y % 5
        out = bytearray(len(line))
        for i, v in enumerate(line):
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = [0, a, b, (a + b) >> 1, a if pa <= pb and pa <= pc else b if pb <= pc else c][kind]
            out[i] = (v - pred) & 255
        rows.append(bytes([kind]) + bytes(out))
        prev = line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return seen.SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, colour, 0, 0, interlace)) \
        + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b"")


def colour(x, y):
    return (x * 5 % 256, y * 7 % 256, (x * y) % 256, 255)


def rgb(data):
    """A PNG's pixels as [(r, g, b)] rows."""
    w, h = seen.size(data)
    rows = seen._rgb(data, (0, 0, w, h))
    return [[tuple(r[i:i + 3]) for i in range(0, len(r), 3)] for r in rows]


PLAY = {"name": "three_hits", "seconds": 10,
        "inputs": [{"t": 1.0, "key": "J", "press": True}, {"t": 1.1, "key": "J", "press": False},
                   {"t": 3.6, "shot": "combo"}, {"t": 6.0, "shot": "later"}]}


def seen_probe(name="combo_shows", measure=None, expect=None, **extra):
    return probe(name, play=PLAY, measure=dict({"probe": "seen", "shot": "combo", "rect": [0.5, 0.0, 1.0, 0.5],
                                                "read": "number"}, **(measure or {})),
                 expect=expect or {"op": ">=", "value": 3}, **extra)


class Crop(unittest.TestCase):
    def test_the_rect_rounded_outward_to_whole_pixels_unscaled(self):
        shot = png(40, 20, colour)
        found, whole = seen.crop(shot, [0.26, 0.5, 0.74, 1.0])
        self.assertFalse(whole)
        self.assertEqual(seen.size(found), (20, 10), "x 10.4 down to 10, 29.6 up to 30")
        self.assertEqual(rgb(found), [[colour(x, y)[:3] for x in range(10, 30)] for y in range(10, 20)])
        self.assertEqual(seen.box(960, 540, [0.70, 0.04, 0.98, 0.16]), (672, 21, 941, 87))

    def test_rgb_and_rgba_shots_read_alike_and_no_rect_is_the_shot_as_taken(self):
        rgba, plain = png(12, 8, colour), png(12, 8, colour, colour=2)
        self.assertEqual(seen.crop(rgba, [0, 0, 0.5, 0.5])[0], seen.crop(plain, [0, 0, 0.5, 0.5])[0])
        self.assertEqual(seen.crop(rgba, None), (rgba, False))

    def test_a_png_it_cant_read_is_kept_whole_and_no_png_is_refused(self):
        laced = png(12, 8, colour, interlace=1)
        self.assertEqual(seen.crop(laced, [0, 0, 0.5, 0.5]), (laced, True))
        with self.assertRaises(ValueError):
            seen.crop(b"not a png", None)
        with self.assertRaises(ValueError):
            seen.box(960, 540, [0.5, 0.5, 0.5, 0.6])

    def test_how_the_lab_scales_it(self):
        self.assertEqual(seen.lab_scale(269, 66), 4)    # 66 x 4 = 264, still under 360: at most 4
        self.assertEqual(seen.lab_scale(400, 180), 2)
        self.assertEqual(seen.lab_scale(960, 540), 1)


class Shrink(unittest.TestCase):
    """A mobile play's shot is kept within 960x540 (540x960 upright) before it is cropped, as the Lab keeps it: each
    new pixel the mean of the ones it covers."""

    def test_a_shot_twice_the_size_is_halved_by_averaging(self):
        shot = png(8, 4, colour)
        half = seen.shrink(shot, (4, 2))
        self.assertEqual(seen.size(half), (4, 2))
        full = rgb(shot)
        for y, row in enumerate(rgb(half)):
            for x, got in enumerate(row):
                cover = [full[2 * y + j][2 * x + i] for j in (0, 1) for i in (0, 1)]
                self.assertEqual(got, tuple(round(sum(p[c] for p in cover) / 4) for c in range(3)))

    def test_a_shot_that_fits_is_kept_and_the_crop_is_of_the_kept_size(self):
        shot = png(8, 4, colour)
        self.assertIs(seen.shrink(shot, (8, 4)), shot)
        self.assertEqual(seen.fitted(1920, 1080, (960, 540)), (960, 540))
        self.assertEqual(seen.fitted(1080, 1920, (540, 960)), (540, 960))
        found, whole = seen.crop(shot, [0.0, 0.0, 0.5, 1.0], (4, 2))
        self.assertFalse(whole)
        self.assertEqual(seen.size(found), (2, 2))


class Read(unittest.TestCase):
    def found(self, *names):
        return {n: ({"png": b"", "whole": False, "sha256": f"sha-{n}"}, None) for n in names}

    def held(self, side, lines, *names):
        return {"key": {"A": "start", "B": "reference"}, "problem": None,
                "sides": {side: {"lines": lines, "crops": {n: f"sha-{n}" for n in names}}}}

    def value(self, measure, lines, side="start", names=("combo",)):
        c = tasks.check(seen_probe(measure=measure))
        return seen.read(c, side, self.found(*names), self.held(side, lines, *names))

    def test_the_labs_reduction_on_the_writers_lines(self):
        self.assertEqual(self.value({}, ["COMBO", "  x3 "]), (3.0, None))
        self.assertEqual(self.value({}, ["SCORE 1,250"]), (1250.0, None))
        self.assertEqual(self.value({"read": "clock"}, ["TIME 1:05.5"]), (65.5, None))
        self.assertEqual(self.value({"read": "text", "match": r"COMBO\s+x3"}, ["COMBO   x3"]), (1.0, None),
                         "white space made one, as the Lab normalises a reading")
        self.assertEqual(self.value({"read": "text", "match": "COMBO"}, ["combo"]), (0.0, None))
        self.assertEqual(self.value({"read": "text", "match": "COMBO"}, []), (0.0, None), "the start may read nothing")

    def test_a_list_of_shots_is_reduced_by_its_agg(self):
        listed = {"shot": ["combo", "later"], "agg": "rises", "rect": None}
        self.assertEqual(self.value(listed, {"combo": ["1"], "later": ["4"]}, names=("combo", "later")), (1.0, None))
        self.assertEqual(self.value(dict(listed, agg="delta"), {"combo": ["1"], "later": ["4"]},
                                    names=("combo", "later")), (3.0, None))
        value, why = self.value(listed, {"combo": ["1"], "later": []}, names=("combo", "later"))
        self.assertIsNone(value, "a shot with no value gives the measure none")
        self.assertIn("nothing read as a number", why)
        value, why = self.value(listed, ["1"], names=("combo", "later"))
        self.assertIsNone(value)
        self.assertIn("{shot: [lines]} for the shots combo, later", why)

    def test_the_reference_must_read_something(self):
        value, why = self.value({}, ["COMBO"], side="reference")
        self.assertIsNone(value)
        self.assertIn("nothing the check reads was read on the reference", why)
        value, why = self.value({"read": "text", "match": "x"}, [], side="reference")
        self.assertIsNone(value)
        self.assertIn("nothing the check reads was read on the reference", why)

    def test_a_trusted_side_that_reads_nothing_or_a_question_mark_is_a_task_error(self):
        """The Lab reads the reference (and the start of a threshold relative to it) 3 times, all the same, and the
        reference must read something; a `?` stands for a reading that may not repeat (local only)."""
        c = tasks.check(seen_probe())
        found = self.found("combo")
        self.assertIn("nothing the check reads was read on the reference",
                      seen.untrusted(c, "reference", found, self.held("reference", ["COMBO"], "combo")))
        self.assertIn("holds a `?`", seen.untrusted(c, "reference", found, self.held("reference", ["x?3"], "combo")))
        self.assertIn("the start's answer holds a `?`",
                      seen.untrusted(c, "start", found, self.held("start", ["x?"], "combo")))
        self.assertIsNone(seen.untrusted(c, "reference", found, self.held("reference", ["COMBO x3"], "combo")))
        self.assertIsNone(seen.untrusted(c, "start", found, self.held("start", [], "combo")),
                          "the start may read nothing")
        self.assertIsNone(seen.untrusted(c, "reference", found, None), "unanswered: waits for the answer")

    def test_no_answer_or_another_crop_reads_nothing(self):
        c = tasks.check(seen_probe())
        self.assertEqual(seen.read(c, "start", self.found("combo"), None), (None, seen.NEEDED))
        held = self.held("start", ["3"], "combo")
        held["sides"]["start"]["crops"] = {"combo": "another"}
        self.assertEqual(seen.read(c, "start", self.found("combo"), held),
                         (None, "its crops changed since they were answered: answer needed"))
        self.assertIn("a list of lines", self.value({}, "3")[1])


class Played(FakeProject):
    """A fake project whose plays take their named shots: a picture of `seed` per side, so the two sides' crops differ."""

    def __init__(self, seed, answer=None, **kw):
        super().__init__(answer or measuring(0), **kw)
        self.seed = seed

    def play(self, seconds, shots, timeout, map=None, inputs=None, queries=None, args=(), every=None, session=False):
        found = super().play(seconds, shots, timeout, map, inputs, queries, args, every, session)
        for i in inputs or []:
            if "shot" in i:
                found.files[f"shot_{i['shot']}.png"] = png(16, 8, lambda x, y: ((x + self.seed) % 256, y, 0, 255))
        return found


class Whole(unittest.TestCase):
    def run_check(self, tmp, task, projects):
        if not (Path(tmp) / "metro-runner").exists():
            self.game = make_game(tmp)[:3]
        repo, start, fix = self.game
        task = dict(task, seed={**task["seed"], "commit": start, "reference": fix})
        names = {start[:12]: "start", fix[:12]: "reference"}
        with mock.patch.object(unreal, "Project", lambda folder, m, label: projects[names[Path(folder).name]]), \
                mock.patch.object(unreal.Machine, "for_project",
                                  classmethod(lambda cls, p, d=False: cls(Path(p), None))), \
                mock.patch.object(unreal.gfroot, "check_free", lambda *a: 100.0):
            return check.check_task(repo, task, json.dumps(task).encode(), Path(tmp) / "scratch", Path(tmp) / "out",
                                    log=lambda *a: None)

    def answer(self, tmp, start, reference):
        base = Path(tmp) / "out" / "probe-task" / "seen-shots" / "combo_shows" / "blind"
        key = json.loads((base / "key.json").read_text())
        mine = {"start": start, "reference": reference}
        (base / "answers.json").write_text(json.dumps({letter: mine[side] for letter, side in key.items()}))
        return base

    def test_crops_saved_answer_needed_then_read_from_the_answer(self):
        task = task_with(seen_probe())
        projects = lambda: {"start": Played(1, folder="start"), "reference": Played(2, folder="reference")}
        with tempfile.TemporaryDirectory() as tmp:
            first = projects()
            result = self.run_check(tmp, task, first)
            self.assertEqual(result["verdict"], "INVALID", "a required seen probe nobody has read decides nothing yet")
            self.assertIn("seen combo_shows: crops saved for start/reference, answer needed", result["notes"])
            self.assertTrue(any(r.startswith("reference fails combo_shows") for r in result["reasons"]))
            self.assertIn("seen combo_shows: crops saved for start/reference, answer needed", result["reasons"])
            self.assertEqual([p["queries"] for p in first["start"].plays], [None], "the plugin is asked nothing")
            self.assertEqual(result["seen"]["combo_shows"]["folder"], "probe-task/seen-shots/combo_shows/")
            base = Path(tmp) / "out" / "probe-task" / "seen-shots" / "combo_shows"
            for folder in ("start", "reference", "blind/A", "blind/B"):
                self.assertEqual([p.name for p in (base / folder).iterdir()], ["combo.png"], folder)
                self.assertEqual(seen.size((base / folder / "combo.png").read_bytes()), (8, 4))
            self.assertEqual(rgb((base / "start" / "combo.png").read_bytes())[0][0], (9, 0, 0), "x 8 of seed 1")
            ask = (base / "ask.md").read_text()
            for text in (seen.PROMPT, "the first number read", "cropped to rect [0.5, 0.0, 1.0, 0.5]",
                         "scales it up 4 times", '{"A": ["COMBO x3"], "B": ["COMBO x3"]}', "blind/key.json"):
                self.assertIn(text, ask)

            self.answer(tmp, ["COMBO x0"], ["COMBO", "x3"])
            again = self.run_check(tmp, task, projects())
            self.assertEqual((again["verdict"], again["reasons"]), ("VALID", []))
            self.assertIn("seen combo_shows: read from blind/answers.json", again["notes"])
            self.assertEqual((again["probes"]["combo_shows"]["start"], again["probes"]["combo_shows"]["reference"]),
                             (0.0, 3.0))
            self.assertTrue((base / "blind" / "answers.json").is_file(), "the answer is kept for the next check")

            self.answer(tmp, ["COMBO x3"], ["COMBO x3"])
            held = self.run_check(tmp, task, projects())
            self.assertEqual(held["reasons"], ["start already passes every required probe"])

            changed = {"start": Played(5, folder="start"), "reference": Played(2, folder="reference")}
            moved = self.run_check(tmp, task, changed)
            self.assertEqual((moved["verdict"], moved["reasons"]),
                             ("INVALID", ["seen combo_shows: crops saved for start/reference, answer needed"]),
                             "an unanswered start is no start that fails")
            self.assertIn("start: its crops changed since they were answered, so its answer was dropped",
                          moved["seen"]["combo_shows"]["notes"])
            kept = json.loads((base / "blind" / "answers.json").read_text())
            key = json.loads((base / "blind" / "key.json").read_text())
            self.assertEqual({key[k] for k in kept}, {"reference"}, "the reference's answer still stands")

    def test_a_reference_answer_that_reads_nothing_is_a_task_error_required_or_not(self):
        task = task_with(probe(), seen_probe(required=False))
        projects = lambda: {"start": Played(1, folder="start", answer=measuring(-5)),
                            "reference": Played(2, folder="reference", answer=measuring(5))}
        with tempfile.TemporaryDirectory() as tmp:
            first = self.run_check(tmp, task, projects())
            self.assertEqual(first["reasons"], ["seen combo_shows: crops saved for start/reference, answer needed"],
                             "an optional seen probe waits for its answer too")
            self.answer(tmp, ["COMBO x0"], ["COMBO"])
            again = self.run_check(tmp, task, projects())
            self.assertEqual(again["verdict"], "INVALID")
            self.assertEqual(len(again["reasons"]), 1)
            self.assertTrue(again["reasons"][0].startswith("task error in combo_shows: nothing the check reads was "
                                                           "read on the reference"), again["reasons"])
            self.answer(tmp, ["COMBO x0"], ["COMBO? x3"])
            unsure = self.run_check(tmp, task, projects())
            self.assertIn("holds a `?`", unsure["reasons"][0])
            self.answer(tmp, ["COMBO x0"], ["COMBO x3"])
            self.assertEqual(self.run_check(tmp, task, projects())["verdict"], "VALID")

    def test_a_shot_the_play_never_took_is_said(self):
        task = task_with(seen_probe())
        projects = {"start": FakeProject(measuring(0), folder="start"),
                    "reference": FakeProject(measuring(0), folder="reference")}
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_check(tmp, task, projects)
        record = result["seen"]["combo_shows"]
        self.assertFalse(record["blind"])
        self.assertIn("play three_hits took no shot named combo", record["notes"][0])

    def test_progress_names_a_seen_check_waiting_for_an_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = {"task": "probe-task", "verdict": "INVALID", "reasons": [], "seconds": 60,
                      "seen": {"combo_shows": {"status": "crops saved for start/reference, answer needed"},
                               "timer_shows": {"status": seen.ANSWERED}}}
            cli.write_progress(tmp, 0, ["probe-task"], [result], now=60)
            text = (Path(tmp) / "progress.txt").read_text()
            self.assertIn("    seen combo_shows: crops saved for start/reference, answer needed: "
                          "probe-task/seen-shots/combo_shows/ask.md", text)
            self.assertNotIn("timer_shows", text)
            done = json.loads((Path(tmp) / "progress.json").read_text())["done"][0]
            self.assertEqual(done["seen_pending"], ["combo_shows"])


class Try(unittest.TestCase):
    def test_a_try_asks_no_model_and_leaves_it_out_of_the_number(self):
        task = task_with(probe(), seen_probe())
        s = side("run1", Played(1, folder="run1"), task)
        grade = check.Grade(task, "reference", s, s, {}, side=s).run()
        row = next(r for r in grade["checks"] if r["name"] == "combo_shows")
        self.assertEqual((row["passed"], row["detail"]), (True, seen.NOT_READ))
        self.assertEqual(trial.score(task, {"checks": [dict(row, weight=5),
                                                       {"name": "x", "kind": "probe", "passed": False, "weight": 1,
                                                        "required": True, "group": "g"}]})["score"], 0.0)


class Saved(unittest.TestCase):
    def test_the_same_blind_copy_as_a_judges(self):
        task = task_with(seen_probe())
        c = seen.checks(task)[0]
        crop = lambda b: {"combo": ({"png": png(4, 4, lambda x, y: (b, 0, 0, 255)), "whole": False, "sha256": str(b)},
                                    None)}
        with tempfile.TemporaryDirectory() as tmp:
            record = seen.save(task, c, {"start": crop(1), "reference": crop(2)}, tmp, rng=random.Random(1))
            base = Path(tmp) / "combo_shows"
            key = json.loads((base / "blind" / "key.json").read_text())
            for letter, name in key.items():
                self.assertEqual((base / "blind" / letter / "combo.png").read_bytes(),
                                 (base / name / "combo.png").read_bytes())
            self.assertEqual(json.loads((base / "crops.json").read_text()),
                             {"start": {"combo": "1"}, "reference": {"combo": "2"}})
            self.assertEqual(record["status"], "crops saved for start/reference, answer needed")
            (base / "blind" / "answers.json").write_text("{not json")
            held = seen.kept(tmp)["combo_shows"]
            self.assertIn("answers.json can't be read", held["problem"])
            self.assertIn("blind/answers.json", seen.read(c, "start", crop(1), held)[1])
            seen.save(task, c, {"start": crop(1), "reference": crop(2)}, tmp, held)
            self.assertEqual((base / "blind" / "answers.json").read_text(), "{not json", "kept as written, to fix")
            self.assertEqual(json.loads((base / "blind" / "key.json").read_text()), key, "the same letters")

    def test_a_start_never_played_leaves_the_reference_alone_to_answer(self):
        """A start that doesn't build by design (fails_at_start) is never played: the reference's crops are answered
        alone, as A."""
        task = task_with(seen_probe())
        c = seen.checks(task)[0]
        crop = {"combo": ({"png": png(4, 4, colour), "whole": False, "sha256": "r"}, None)}
        with tempfile.TemporaryDirectory() as tmp:
            record = seen.save(task, c, {"reference": crop}, tmp)
            base = Path(tmp) / "combo_shows"
            self.assertEqual(json.loads((base / "blind" / "key.json").read_text()), {"A": "reference"})
            self.assertEqual(record["status"], "crops saved for reference, answer needed")
            self.assertIn('{"A": ["COMBO x3"]}', (base / "ask.md").read_text())
            (base / "blind" / "answers.json").write_text(json.dumps({"A": ["3"]}))
            held = seen.kept(tmp)["combo_shows"]
            self.assertEqual(seen.read(c, "reference", crop, held), (3.0, None))
            self.assertEqual(seen.save(task, c, {"reference": crop}, tmp, held)["status"], seen.ANSWERED)


if __name__ == "__main__":
    unittest.main()

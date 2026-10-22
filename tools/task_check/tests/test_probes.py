"""Probes with no Unreal: the measures' defaults, the plugin's queries, every reducer, the colour pipeline, the editor
pass's script and results."""

import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from helpers import NO_FIX, SEED, first_check, measure_of, probe, task_with

from task_check import probes, tasks

WALLS = {"class": "SCCastlePiece", "tag": "Wall"}
TRACK = [[0.0, 0, 0, 100], [0.5, 30, 40, 100], [1.0, 60, 80, 90], [1.5, 60, 80, -500]]


def m(**data):
    return measure_of(data)


def sampled(values, key="value"):
    return [{"t": i * 0.5, key: v} for i, v in enumerate(values)]


def actors_play(measure, rows):
    qid = probes.query_id(probes.needs(measure)[0])
    return {"measures": {qid: sampled(rows, "rows")}}


class Tasks(unittest.TestCase):
    def test_the_measures_defaults(self):
        found = m(probe="actors", select={"class": "BP_Wall_C"}, field="z")
        self.assertEqual((found["of"], found["agg"]), ("count", None))
        self.assertEqual(probes.default_agg(found), "last")
        self.assertEqual(probes.default_agg(m(probe="spawns", **{"class": "P"}, field="spawned")), "sum")
        self.assertEqual(m(probe="pawn", field="dist", to={"pawn": True})["to"]["offset"], [0, 0, 0])

    def test_a_task_play_teleport_turns_the_pawn_even_without_a_yaw(self):
        play = tasks.play({"name": "spot", "seconds": 8, "inputs": [{"t": 0.2, "teleport": [1, 2, 3]},
                                                                     {"t": 1, "key": "W", "press": True}]})
        self.assertEqual(play["inputs"], [{"t": 0.2, "teleport": [1.0, 2.0, 3.0], "yaw": 0.0},
                                          {"t": 1.0, "key": "W", "press": True}])
        self.assertEqual((play["map"], play["args"], play["every"]), (None, [], None))

    def test_the_checks_defaults_and_their_kinds(self):
        task = task_with(probe(), probe("b", required=False, expect={"op": ">=", "calibrate": 0.5}))
        checks = [c for _, c in tasks.checks(task)]
        self.assertEqual([(c["required"], c["weight"], c["needs"]) for c in checks], [(True, 1, []), (False, 1, [])])
        self.assertEqual([tasks.relative(c) for c in checks], [None, "calibrate"])
        self.assertEqual(tasks.gating(task), {"hero_on_ground"})

    def test_the_task_rules_beyond_the_schema_are_refused(self):
        for checks, seed, said in [
            ([probe(play="editor")], SEED, "asset measures are taken by the editor pass"),
            ([probe(play="trace")], SEED, "trace measures are read from the trace"),
            ([probe(measure={"probe": "trace", "fact": "build_ok_at_end"}, play="trace")], SEED, "never gates"),
            ([probe("a", play={"name": "fire", "seconds": 10}), probe("b", play={"name": "fire", "seconds": 12})],
             SEED, "task play fire differs"),
            ([probe(expect={"op": "==", "calibrate": 0.5})], SEED, "== and != take a literal value"),
            ([probe(expect={"op": ">=", "calibrate": 0.5})], NO_FIX, "calibrates against a reference"),
        ]:
            with self.assertRaisesRegex(ValueError, said):
                task_with(*checks, seed=seed)
        for arg in ("-TaskProbe", "-taskprobeseconds=99", "-ExecCmds=quit"):
            with self.assertRaisesRegex(ValueError, "can't set"):
                task_with(probe(play={"name": "fire", "seconds": 10, "args": [arg]}))
        task_with(probe(play={"name": "fire", "seconds": 10, "args": ["-AutoPlay", "-Scenario=2"]}))
        task_with(probe("a", play={"name": "fire", "seconds": 10}), probe("b", play={"name": "fire", "seconds": 10}))
        task_with(probe(expect={"op": ">=", "start_times": 1.3}), seed=NO_FIX)


class Queries(unittest.TestCase):
    def test_queries_are_merged_per_play_and_selection_under_stable_ids(self):
        task = task_with(
            probe("a", measure={"probe": "actors", "select": WALLS, "field": "z"}),
            probe("b", measure={"probe": "actors", "select": WALLS, "field": "prop:SpringArm.TargetArmLength"}),
            probe("c", measure={"probe": "actors", "select": WALLS, "field": "count"}),
            probe("d", measure={"probe": "camera", "field": "occluded"}),
            probe("e", measure={"probe": "camera", "field": "pawn_on_screen"}),
            probe("f", measure={"probe": "camera", "field": "pitch"}),
            probe("g", play="drive", measure={"probe": "light", "point": {"pawn": True, "offset": [0, 0, 90]},
                                              "field": "brightness"}),
            probe("h", play="drive", measure={"probe": "grading", "field": "warmth"}),
            probe("i", play="drive", measure={"probe": "pawn", "field": "dist", "to": {"actor": {"name": "Kiln*"}}}),
            probe("j", play={"name": "fire", "seconds": 10}, measure={"probe": "spawns", "class": "P",
                                                                        "field": "destroyed"}),
            probe("k", play={"name": "fire", "seconds": 10}, measure={"probe": "log", "pattern": "Ensure"}),
            probe("l", play="editor", measure={"probe": "asset", "asset": "/Game/M", "field": "prop:two_sided"}))
        plan = probes.plan(task)
        self.assertEqual(set(plan), {"look", "drive", "fire"})
        look = {q["kind"]: q for q in plan["look"]}
        self.assertEqual(len(plan["look"]), 2, "one actors query for the walls, one camera query")
        self.assertEqual(look["actors"]["fields"], ["prop:SpringArm.TargetArmLength", "z"])
        self.assertEqual(look["actors"]["select"], {"class": "SCCastlePiece", "tag": "Wall"})
        self.assertEqual(look["camera"]["fields"], ["occluded", "pawn_on_screen"])
        drive = {q["kind"]: q for q in plan["drive"]}
        self.assertEqual(drive["light"]["point"], {"pawn": True, "offset": [0.0, 0.0, 90.0]})
        self.assertEqual(drive["actors"], {"id": drive["actors"]["id"], "kind": "actors", "select": {"name": "Kiln*"},
                                           "fields": ["x", "y", "z"]})
        self.assertEqual(plan["fire"], [{"id": plan["fire"][0]["id"], "kind": "spawns", "class": "P"}])
        alone = probes.plan(task_with(probe("z", measure={"probe": "actors", "select": WALLS, "field": "hidden"})))
        self.assertEqual(alone["look"][0]["id"], look["actors"]["id"], "an id names its selection")
        self.assertEqual([q["id"] for q in plan["look"]], sorted(q["id"] for q in plan["look"]))
        self.assertEqual(probes.query_file(plan["look"]),
                         {"format": "game-probe-queries/1", "every": 0.5, "queries": plan["look"]})
        self.assertIsNone(probes.query_file([]))
        self.assertEqual(probes.plan(task_with(probe())), {"look": []}, "the track needs no query")

    def test_post_fields_are_asked_for_by_name_beside_the_colour_settings(self):
        task = task_with(probe("a", measure={"probe": "grading", "field": "post:VignetteIntensity"}),
                         probe("b", measure={"probe": "grading", "field": "post:BloomIntensity"}),
                         probe("c", measure={"probe": "grading", "field": "warmth"}),
                         probe("d", measure={"probe": "components", "select": {"class": "DecalComponent"},
                                             "field": "visible"}))
        found = {q["kind"]: q for q in probes.plan(task)["look"]}
        self.assertEqual(found["grading"]["fields"], ["post:BloomIntensity", "post:VignetteIntensity"])
        self.assertEqual(found["components"], {"id": found["components"]["id"], "kind": "components",
                                               "select": {"class": "DecalComponent"}, "fields": ["visible"]})

    def test_slate_types_and_component_names_reach_the_queries(self):
        found = probes.plan(task_with(probe(measure={"probe": "components", "select": {"class": "NiagaraComponent",
                                                                                       "name": "Rain*"},
                                                     "field": "count"})))
        self.assertTrue(any(q.get("select", {}).get("name") == "Rain*" for qs in found.values() for q in qs))


class Reducers(unittest.TestCase):
    def test_the_pawns_fields_come_from_the_track(self):
        play = {"track": TRACK}
        self.assertEqual(probes.reduce(m(probe="pawn", field="z"), play), -500, "last by default")
        self.assertEqual(probes.reduce(m(probe="pawn", field="z", agg="min", window=[0, 1]), play), 90)
        self.assertEqual(probes.reduce(m(probe="pawn", field="x", at=[0.5, 1.4]), play), 60)
        self.assertAlmostEqual(probes.reduce(m(probe="pawn", field="speed", agg="first"), play), 100.0)
        self.assertAlmostEqual(probes.reduce(m(probe="pawn", field="moved", at="end"), play),
                               (60 ** 2 + 80 ** 2 + 600 ** 2) ** 0.5)
        self.assertEqual(probes.reduce(m(probe="pawn", field="dist", to={"xyz": [0, 0, 100]}, agg="first"), play), 0)
        self.assertIsNone(probes.reduce(m(probe="pawn", field="z", window=[5, 9]), play), "no sample in the window")
        self.assertIsNone(probes.reduce(m(probe="pawn", field="z"), None), "no probe file")

    def test_a_pawns_distance_to_an_actor_reads_the_actors_query(self):
        measure = m(probe="pawn", field="dist", to={"actor": {"name": "Kiln*"}, "offset": [0, 0, 100]}, agg="min")
        (query,) = probes.plan(task_with(probe(measure={"probe": "pawn", "field": "dist", "agg": "min",
                                                        "to": {"actor": {"name": "Kiln*"},
                                                               "offset": [0, 0, 100]}})))["look"]
        rows = [[{"name": "Kiln_2", "x": 60, "y": 80, "z": 0}]] * 4
        play = {"track": TRACK, "measures": {query["id"]: sampled(rows, "rows")}}
        self.assertAlmostEqual(probes.reduce(measure, play), 10.0)
        play["measures"][query["id"]] = sampled([[]] * 4, "rows")
        self.assertIsNone(probes.reduce(measure, play), "no kiln, no distance")

    def test_the_cameras_fields_come_from_its_rows_and_its_query(self):
        camera = [[t, -700, 0, 400, -12.0, 5.0, 90.0] for t in (0.0, 0.5)]
        play = {"track": [[0.0, 0, 0, 100], [0.5, 0, 0, 100]], "camera": camera}
        self.assertAlmostEqual(probes.reduce(m(probe="camera", field="distance"), play), (700 ** 2 + 300 ** 2) ** 0.5)
        self.assertEqual(probes.reduce(m(probe="camera", field="height"), play), 300)
        self.assertEqual(probes.reduce(m(probe="camera", field="pitch"), play), -12)
        self.assertEqual(probes.reduce(m(probe="camera", field="fov"), play), 90)
        occluded = m(probe="camera", field="occluded", agg="count")
        qid = probes.query_id(probes.needs(occluded)[0])
        play["measures"] = {qid: sampled([{"occluded": True, "pawn_on_screen": 1}, {"occluded": False}])}
        self.assertEqual(probes.reduce(occluded, play), 1)
        self.assertEqual(probes.reduce(m(probe="camera", field="pawn_on_screen", agg="all"), play), 1)

    def test_actors_combine_by_of_and_samples_by_agg(self):
        rows = [[{"name": "A", "z": 0}, {"name": "B", "z": 120.0}, {"name": "C", "z": None}],
                [{"name": "A", "z": 50}, {"name": "B", "z": 130.0}]]
        expected = {"count": [1, 2], "any": [1, 1], "all": [0, 1], "min": [0, 50], "max": [120, 130],
                    "mean": [60, 90], "sum": [120, 180], "first": [0, 50]}
        for of, values in expected.items():
            for agg, want in (("first", values[0]), ("last", values[1]), ("delta", values[1] - values[0]),
                              ("sum", sum(values)), ("max", max(values))):
                measure = m(probe="actors", select={"tag": "T"}, field="z", of=of, agg=agg)
                self.assertAlmostEqual(probes.reduce(measure, actors_play(measure, rows)), want, msg=(of, agg))
        count = m(probe="actors", select={"tag": "T"}, field="count", agg="mean")
        self.assertEqual(probes.reduce(count, actors_play(count, rows)), 2.5)
        empty = m(probe="actors", select={"tag": "T"}, field="z", of="min")
        self.assertIsNone(probes.reduce(empty, actors_play(empty, [[], []])))
        named = m(probe="actors", select={"tag": "T"}, field="prop:Mesh.StaticMesh", match="SM_Tower", of="all")
        self.assertEqual(probes.reduce(named, actors_play(named, [[{"prop:Mesh.StaticMesh": "/Game/SM_Tower"},
                                                                    {"prop:Mesh.StaticMesh": "/Game/SM_Tower_B"}]])), 1)
        self.assertEqual(probes.reduce(named, actors_play(named, [[{"prop:Mesh.StaticMesh": "/Game/SM_Hut"}]])), 0)

    def test_of_defaults_to_count(self):
        """A probe that reads a field without `of` counts the rows whose value isn't 0."""
        measure = m(probe="actors", select={"tag": "T"}, field="z")
        self.assertEqual(probes.reduce(measure, actors_play(measure, [[{"z": 120.0}, {"z": 0.0}, {"z": 5.0}]])), 2)

    def test_every_agg_and_of(self):
        values = [0.0, 2.0, None, 5.0, 0.0]
        want = {"min": 0, "max": 5, "mean": 1.75, "first": 0, "last": 0, "delta": 0, "any": 1, "all": 0, "count": 2,
                "sum": 7, "range": 5, "changes": 3}
        for agg, value in want.items():
            self.assertEqual(probes.aggregate(values, agg), value, agg)
        self.assertAlmostEqual(probes.aggregate(values, "std"), 2.0463, places=4)
        self.assertIsNone(probes.aggregate([None], "sum"))
        self.assertEqual(probes.aggregate([3.0, 4.0], "all"), 1)
        self.assertEqual({of: probes.combine([3.0, 0.0, None], of) for of in
                          ("count", "any", "all", "min", "max", "mean", "sum", "first")},
                         {"count": 1, "any": 1, "all": 0, "min": 0, "max": 3, "mean": 1.5, "sum": 3, "first": 3})
        self.assertEqual((probes.combine([], "all"), probes.combine([], "count")), (0, 0))
        self.assertIsNone(probes.combine([], "max"))

    def test_widgets_light_spawns_and_the_log(self):
        ammo = m(probe="widgets", select={"class": "WBP_HUD_C", "name": "AmmoText"}, field="text",
                 match=r"^\d+ / \d+$", of="any", agg="all")
        self.assertEqual(probes.reduce(ammo, actors_play(ammo, [[{"name": "AmmoText", "text": "12 / 30"}]] * 3)), 1)
        self.assertEqual(probes.reduce(ammo, actors_play(ammo, [[{"name": "AmmoText", "text": "AMMO"}]])), 0)
        light = m(probe="light", point={"camera": True, "forward": 300}, field="brightness", agg="mean")
        qid = probes.query_id(probes.needs(light)[0])
        play = {"measures": {qid: sampled([{"illuminance": 100, "exposure": 0.5, "brightness": 50},
                                           {"illuminance": 300, "exposure": 0.5, "brightness": 150}])}}
        self.assertEqual(probes.reduce(light, play), 100)
        shots = m(probe="spawns", **{"class": "SCProjectile"}, field="spawned", window=[1, 2])
        qid = probes.query_id(probes.needs(shots)[0])
        play = {"measures": {qid: sampled([{"spawned": n, "destroyed": 0} for n in (0, 1, 1, 4, 6, 6)])}}
        self.assertEqual(probes.reduce(shots, play), 5, "spawned in (0.5, 2] s: 3 + 2")
        self.assertEqual(probes.reduce(m(probe="spawns", **{"class": "SCProjectile"}, field="spawned"), play), 6)
        log = "LogTemp: Ensure condition failed\nLogInit: ready\nLogTemp: Ensure condition failed\n"
        self.assertEqual(probes.reduce(m(probe="log", pattern="Ensure condition"), None, log), 2)

    def test_a_point_on_the_camera_follows_its_view(self):
        play = {"camera": [[0.0, 0, 0, 0, 90.0, 0.0, 90.0], [0.5, 0, 0, 0, 0.0, 90.0, 90.0]],
                "track": [[0.0, 0, 0, 0]]}
        up = probes.point_at(tasks.point({"camera": True, "forward": 100}), 0.0, play)
        for a, b in zip(up, [0, 0, 100]):
            self.assertAlmostEqual(a, b)
        side = probes.point_at(tasks.point({"camera": True, "forward": 100}), 0.5, play)
        for a, b in zip(side, [0, 100, 0]):
            self.assertAlmostEqual(a, b)
        self.assertEqual(probes.point_at(tasks.point({"pawn": True, "offset": [0, 0, 50]}), 0.1, play), [0, 0, 50])
        self.assertIsNone(probes.point_at(tasks.point({"pawn": True}), 3.0, play))

    def test_a_play_that_ended_before_the_window_fails_saying_when_it_ended(self):
        play = {"seconds": 6.0, "track": [[t * 0.5, 0, 0, 1] for t in range(13)]}
        self.assertEqual(probes.measured(m(probe="pawn", field="z", window=[10, 18]), play),
                         (None, "no samples in the window (the play ended at 6 s)"))
        self.assertEqual(probes.measured(m(probe="pawn", field="z", at=[15]), {"track": TRACK}),
                         (None, "no samples in the window (the play ended at 1.5 s)"))
        empty = m(probe="actors", select={"tag": "T"}, field="z", of="min")
        self.assertEqual(probes.measured(empty, actors_play(empty, [[]])),
                         (None, "no value in the window (nothing it selects was measured)"))

    def test_a_probe_with_no_value_says_what_the_plugin_could_not_read(self):
        measure = m(probe="actors", select={"class": "Nowhere"}, field="z", of="max")
        found = {"format": "game-probe/1", "ended": "time", "seconds": 20.0, "track": [[0.5, 0, 0, 0]], "camera": [],
                 "measures": {probes.query_id(probes.needs(measure)[0]): [{"t": 0.5, "rows": []}]},
                 "query_errors": ["q1: no class named Nowhere"]}
        value, why = probes.measured(measure, found)
        self.assertIsNone(value)
        self.assertIn("no class named Nowhere", why)


class Angles(unittest.TestCase):
    def test_angles_aggregates_and_the_new_query_kinds_reduce(self):
        self.assertEqual([probes.normal(a) for a in (270, -270, 180, -180, 540, 0)], [-90, 90, 180, 180, 180, 0])
        camera = {"camera": [[0.0, 0, 0, 0, 0.0, 270.0, 90.0], [0.5, 0, 0, 0, 0.0, -100.0, 90.0]]}
        self.assertEqual(probes.reduce(m(probe="camera", field="yaw", agg="first"), camera), -90)
        self.assertAlmostEqual(probes.reduce(m(probe="camera", field="yaw", to_angle=-90, agg="max"), camera), 10)
        turret = m(probe="actors", select={"tag": "Tank"}, field="rel_yaw:Turret", to_angle=180, of="max")
        self.assertEqual(probes.reduce(turret, actors_play(turret, [[{"rel_yaw:Turret": -170},
                                                                      {"rel_yaw:Turret": 175}]])), 10)
        self.assertEqual(probes.aggregate([1.0, 3.0, 3.0, 5.0], "range"), 4)
        self.assertAlmostEqual(probes.aggregate([1.0, 3.0, 3.0, 5.0], "std"), 2 ** 0.5)
        self.assertEqual(probes.aggregate([1.0, 1.0, 0.0, 0.0, 1.0, None], "changes"), 2)
        torches = m(probe="components", select={"class": "NiagaraComponent", "owner": {"tag": "Torch"}},
                    field="active", of="count")
        self.assertEqual(probes.reduce(torches, actors_play(torches, [[{"active": True}, {"active": False},
                                                                        {"active": 1}]])), 2)
        hint = m(probe="widgets", select={"slate": "STextBlock", "text": "^Press E"}, field="y", of="max")
        self.assertEqual(probes.reduce(hint, actors_play(hint, [[{"y": 0.9}, {"y": 0.4}]])), 0.9)
        blur = m(probe="grading", field="post:MotionBlurAmount", agg="max")
        qid = probes.query_id(probes.needs(blur)[0])
        self.assertEqual(probes.reduce(blur, {"measures": {qid: sampled([{"post:MotionBlurAmount": 0.5},
                                                                         {"post:MotionBlurAmount": 0.0}])}}), 0.5)

    def test_a_property_that_holds_an_angle_takes_to_angle_live_and_as_saved(self):
        live = m(probe="actors", select={"class": "TDGrid"}, field="prop:KitStraightYaw", to_angle=90)
        self.assertEqual((probes.angled(live, 450.0), probes.angled(live, -270.0), probes.angled(live, 0.0)),
                         (0.0, 0.0, 90.0))
        self.assertEqual(probes.angled(live, 270.0), 180.0)
        self.assertEqual(probes.angled(live, -90.0), 180.0)
        saved = m(probe="asset", map="/Game/L2", select={"name": "ChimeRack"},
                  field="prop:StaticMeshComponent.RelativeRotation.Yaw", to_angle=0, of="max")
        self.assertEqual(probes.reduce_asset(saved, {"rows": [{"name": "ChimeRack", "value": -90.0}]}), (90.0, None))
        plain = m(probe="actors", select={"class": "TDGrid"}, field="prop:KitStraightYaw")
        self.assertEqual(probes.angled(plain, 450.0), 450.0, "a property is an angle only with to_angle")

    def test_to_axis_folds_a_direction_and_its_opposite_into_one_axis(self):
        axis = m(probe="actors", select={"class": "TDGrid"}, field="prop:KitStraightYaw", to_axis=90)
        self.assertEqual({probes.angled(axis, a) for a in (90.0, -90.0, 270.0)}, {0.0})
        self.assertEqual((probes.angled(axis, 0.0), probes.angled(axis, 180.0), probes.angled(axis, 45.0)),
                         (90.0, 90.0, 45.0))


class Colour(unittest.TestCase):
    def test_the_default_grading_leaves_grey_neutral(self):
        found = probes.colour({})
        self.assertAlmostEqual(found["grey"], 0.18, places=6)
        self.assertAlmostEqual(found["cast"], 0, places=5)
        self.assertEqual((found["saturation"], found["contrast"]), (1, 1))
        other = probes.colour({"white_temp": 6500, "white_tint": 0, "sun": {"lit_color": [1, 1, 1]}})
        for k in found:
            self.assertAlmostEqual(found[k], other[k], places=6)

    def test_white_balance_and_the_key_light_warm_or_cool_the_grey(self):
        cool = probes.colour({"white_temp": 3200})
        self.assertLess(cool["warmth"], -0.5)
        self.assertGreater(cool["cast"], 0.5)
        self.assertGreater(probes.colour({"white_temp": 3200, "temperature_type": "color_temperature"})["warmth"], 0.5)
        self.assertGreater(probes.colour({"white_temp": 9000})["warmth"], 0.1)
        self.assertGreater(abs(probes.colour({"white_tint": 0.5})["tint"]), 0.05)
        sunset = probes.colour({"sun": {"color": [1, 1, 1], "lit_color": [1.0, 0.6, 0.3]},
                                "fog": {"inscattering": [0.2, 0.2, 0.9]}})
        self.assertGreater(sunset["warmth"], 0.5)
        self.assertAlmostEqual(sunset["grey"], 0.18, places=6)
        self.assertLess(probes.colour({"sun": None, "sky": {"color": [0.3, 0.5, 1.0]}})["warmth"], 0)

    def test_global_grading_settings(self):
        flat = probes.colour({"sun": {"lit_color": [1.0, 0.6, 0.3]}, "saturation": [1, 1, 1, 0]})
        self.assertAlmostEqual(flat["cast"], 0, places=9)
        self.assertEqual(flat["saturation"], 0)
        self.assertAlmostEqual(probes.colour({"gain": [1, 1, 1, 2]})["grey"], 0.36, places=5)
        self.assertAlmostEqual(probes.colour({"offset": [0, 0, 0, 0.02]})["grey"], 0.20, places=5)
        self.assertAlmostEqual(probes.colour({"gamma": [1, 1, 1, 2]})["grey"], 0.18 ** 0.5, places=5)
        self.assertGreater(probes.colour({"gain": [1.2, 1, 0.8, 1]})["warmth"], 0.3)
        contrast = probes.colour({"contrast": [1.2, 1.2, 1.2, 1]})
        self.assertAlmostEqual(contrast["contrast"], 1.2)
        self.assertAlmostEqual(contrast["grey"], 0.18, places=6, msg="contrast pivots on 0.18")
        grading = m(probe="grading", field="warmth", at="end")
        qid = probes.query_id(probes.needs(grading)[0])
        self.assertGreater(probes.reduce(grading, {"measures": {qid: sampled([{}, {"white_temp": 9000}])}}), 0.1)


# -- the editor pass ------------------------------------------------------------------------------------------------------


class _Object:
    def __init__(self, name, path="/Game/X", **props):
        self._name, self._path, self.props = name, path, props

    def get_editor_property(self, name):
        if name not in self.props:
            raise Exception(f"no {name}")
        return self.props[name]

    def get_name(self):
        return self._name

    def get_path_name(self):
        return self._path

    def get_class(self):
        return types.SimpleNamespace(get_name=lambda: type(self).__name__)


def fake_unreal(project_dir):
    """A tiny `unreal` module."""
    u = types.ModuleType("unreal")

    class EnumBase:
        def __init__(self, value):
            self.value = value

    class Name(str):
        pass

    class Text(str):
        pass

    class Object(_Object):
        pass

    class ActorComponent(Object):
        pass

    class MeshComponent(ActorComponent):
        def __init__(self, name, materials=(), **props):
            super().__init__(name, **props)
            self.materials = list(materials)

        def get_num_materials(self):
            return len(self.materials)

        def get_material(self, i):
            return self.materials[i]

    class StaticMeshComponent(MeshComponent):
        pass

    class Cls:
        def __init__(self, name, parents=()):
            self.name, self.parents = name, parents

        def get_name(self):
            return self.name

    class Actor(Object):
        def __init__(self, name, cls, tags=(), location=(0, 0, 0), components=(), **props):
            super().__init__(name, **props)
            self.cls, self.tags, self.location, self.components = cls, tags, location, list(components)

        def get_class(self):
            return self.cls

        def actor_has_tag(self, tag):
            return tag in self.tags

        def get_actor_label(self):
            return self._name + "_label"

        def get_actor_location(self):
            return types.SimpleNamespace(x=self.location[0], y=self.location[1], z=self.location[2])

        def get_components_by_class(self, cls):
            return [c for c in self.components if isinstance(c, cls)]

    class Material(Object):
        def get_base_material(self):
            return self

    class StaticMeshActor(Actor):
        @staticmethod
        def static_class():
            return Cls("StaticMeshActor")

    class StaticMeshEditorSubsystem:
        def get_simple_collision_count(self, mesh):
            return mesh.props.get("simple", 0)

    u.EnumBase, u.Name, u.Text, u.Object, u.ActorComponent = EnumBase, Name, Text, Object, ActorComponent
    u.MeshComponent, u.StaticMeshComponent, u.Actor, u.Material = MeshComponent, StaticMeshComponent, Actor, Material
    u.StaticMeshActor, u.StaticMeshEditorSubsystem, u.Cls = StaticMeshActor, StaticMeshEditorSubsystem, Cls
    u.CollisionTraceFlag = types.SimpleNamespace(CTF_USE_COMPLEX_AS_SIMPLE="complex")
    u.MathLibrary = types.SimpleNamespace(class_is_child_of=lambda own, target: target.name in
                                          (own.name, *own.parents))
    u.get_editor_subsystem = lambda cls: cls()
    u.Paths = types.SimpleNamespace(project_dir=lambda: str(project_dir))
    u.log_warning = print
    return u


def run_script(script, unreal):
    saved = sys.modules.get("unreal")
    sys.modules["unreal"] = unreal
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            exec(compile(script, "probes_editor.py", "exec"), {"__name__": "__main__"})
    finally:
        if saved is None:
            sys.modules.pop("unreal", None)
        else:
            sys.modules["unreal"] = saved
    return out.getvalue()


class Editor(unittest.TestCase):
    def test_the_editor_script_measures_assets_and_maps_and_prints_one_line(self):
        task = task_with(
            probe("road", play="editor", measure={"probe": "asset", "asset": "/Game/Materials/M_Road",
                                                   "field": "prop:TwoSided"}, expect={"op": "==", "value": 1}),
            probe("blend", play="editor", measure={"probe": "asset", "asset": "/Game/Materials/M_Road",
                                                    "field": "prop:blend_mode"}, expect={"op": "==", "value": 2}),
            probe("named", play="editor", measure={"probe": "asset", "asset": "/Game/Materials/M_Road",
                                                    "field": "prop:label", "match": "^Road"},
                  expect={"op": "==", "value": 1}),
            probe("gone", play="editor", measure={"probe": "asset", "asset": "/Game/Missing", "field": "prop:x"}),
            probe("terraces", play="editor", measure={"probe": "asset", "map": "/Game/Maps/L_Level6",
                                                       "select": {"class": "StaticMeshActor", "tag": "Terrace"},
                                                       "field": "material_default", "of": "any"},
                  expect={"op": "==", "value": 0}),
            probe("colliding", play="editor", measure={"probe": "asset", "map": "/Game/Maps/L_Level6",
                                                        "select": {"name": "Terrace*"}, "field": "mesh_collision",
                                                        "of": "all"}, expect={"op": "==", "value": 1}),
            probe("sided", play="editor", measure={"probe": "asset", "map": "/Game/Maps/L_Level6",
                                                    "select": {"tag": "Terrace", "near": {"point": {"xyz": [0, 0, 0]},
                                                                                          "radius": 100}},
                                                    "field": "material:two_sided", "of": "all"},
                  expect={"op": "==", "value": 1}),
            probe("arm", play="editor", measure={"probe": "asset", "map": "/Game/Maps/L_Level6",
                                                  "select": {"class": "StaticMeshActor"},
                                                  "field": "prop:SpringArm.TargetArmLength", "of": "max"},
                  expect={"op": ">=", "value": 500}))
        with tempfile.TemporaryDirectory() as tmp:
            unreal = fake_unreal(tmp)
            road = unreal.Material("M_Road", two_sided=True, blend_mode=unreal.EnumBase(2),
                                   label=unreal.Name("Road (wet)"))
            good = unreal.Material("M_Stone", "/Game/M_Stone", two_sided=True)
            grid = unreal.Material("WorldGridMaterial", "/Engine/EngineMaterials/WorldGridMaterial", two_sided=False)
            mesh = _Object("SM_Terrace", simple=1, body_setup=None)
            actors = [
                unreal.StaticMeshActor("Terrace_1", unreal.Cls("StaticMeshActor"), ("Terrace",), (10, 0, 0), [
                    unreal.StaticMeshComponent("Mesh", [good, good], static_mesh=mesh),
                    unreal.ActorComponent("SpringArm", target_arm_length=900.0)]),
                unreal.StaticMeshActor("Terrace_2", unreal.Cls("BP_Terrace_C", ("StaticMeshActor",)), ("Terrace",),
                                       (5000, 0, 0), [unreal.StaticMeshComponent("Mesh", [grid], static_mesh=None)]),
                unreal.Actor("Lamp", unreal.Cls("PointLight"), ("Terrace",), (0, 0, 0))]
            unreal.load_asset = {"/Game/Materials/M_Road": road}.get
            unreal.EditorLoadingAndSavingUtils = types.SimpleNamespace(
                load_map=lambda path: path if path == "/Game/Maps/L_Level6" else None)
            unreal.GameplayStatics = types.SimpleNamespace(get_all_actors_of_class=lambda world, cls: actors)
            items = probes.editor_items(task)
            self.assertEqual(len(items), 8)
            self.assertEqual([i for i, _ in items], sorted(i for i, _ in items))
            output = run_script(probes.editor_script(items, "n0nce"), unreal)
            self.assertEqual(output.count(probes.MARKER), 1)
            written = (Path(tmp) / probes.EDITOR_FILE).read_bytes()
        results = probes.editor_results("LogPython: " + output, None, "n0nce")
        self.assertEqual(results, probes.editor_results("", written, "n0nce"), "the file and the printed line agree")
        values = {c["name"]: probes.reduce_asset(c["measure"], results[probes.editor_id(c["measure"])])
                  for _, c in tasks.checks(task)}
        self.assertEqual((values["road"], values["blend"], values["named"]), ((1.0, None), (2.0, None), (1.0, None)))
        self.assertEqual(values["gone"], (None, "the editor couldn't measure it: no asset /Game/Missing"))
        self.assertEqual(values["terraces"], (1.0, None), "Terrace_2 (a Blueprint child) shows the grid material")
        self.assertEqual(values["colliding"][0], 0.0, "Terrace_2 has no mesh")
        self.assertEqual(values["sided"], (1.0, None), "only Terrace_1's two materials are within 100 cm")
        self.assertEqual(values["arm"], (900.0, None))

    def test_the_editor_results_need_the_checkers_nonce(self):
        line = json.dumps({"nonce": "mine", "measures": {"a1": {"value": 1}}})
        planted = json.dumps({"nonce": "guess", "measures": {"a1": {"value": 0}}})
        output = f"LogPython: {probes.MARKER} {line}\nLogPython: {probes.MARKER} {planted}\n"
        self.assertEqual(probes.editor_results(output, None, "mine"), {"a1": {"value": 1}})
        self.assertEqual(probes.editor_results(output, planted.encode(), "mine"), {"a1": {"value": 1}})
        self.assertIsNone(probes.editor_results("LogPython: crashed", None, "mine"))
        self.assertIsNone(probes.editor_results(f"{probes.MARKER} not json", b"nor this", "mine"))
        measure = m(probe="asset", map="/Game/L", select={"tag": "T"}, field="count")
        self.assertEqual(probes.reduce_asset(measure, {"rows": [{"name": "a", "value": 1}] * 3}), (3.0, None))
        self.assertEqual(probes.reduce_asset(measure, None), (None, "the editor pass gave nothing for it"))

    def test_an_asset_measures_id_is_its_set_fields(self):
        check = first_check(task_with(probe("road", play="editor", measure={"probe": "asset", "asset": "/Game/M",
                                                                            "field": "prop:x"})))
        (item,) = probes.editor_items(task_with(probe("road", play="editor",
                                                      measure={"probe": "asset", "asset": "/Game/M",
                                                               "field": "prop:x"})))
        self.assertEqual(item, (probes.editor_id(check["measure"]),
                                {"probe": "asset", "asset": "/Game/M", "field": "prop:x", "of": "count"}))


if __name__ == "__main__":
    unittest.main()

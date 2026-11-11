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

    def test_a_judge_check_names_its_own_plays_under_a_task_plays_rules(self):
        judge = {"kind": "judge", "name": "menu_reads", "question": "Does the upgrade menu read clearly?",
                 "required": False, "rubric": [{"key": "menu", "criterion": "The menu is on screen."}]}
        menu = {"name": "open_menu", "seconds": 6, "inputs": [{"t": 1.0, "key": "C", "press": True}]}
        plain = task_with(probe(), judge)
        self.assertNotIn("plays", plain["milestones"][0]["checks"][1], "a judge with no plays is as it was")
        task = task_with(probe(play=menu), {**judge, "plays": [menu, {"name": "second_level", "seconds": 8,
                                                                      "map": "/Game/Maps/L_Two?Scenario=2"}]})
        self.assertEqual(sorted(probes.task_plays(task)), ["open_menu"], "the checker plays what its probes name")
        self.assertEqual(first_check(task_with({**judge, "plays": [menu]}))["plays"], [menu])
        task_with({**judge, "plays": [{**menu, "name": f"play_{i}"} for i in range(4)]})
        for checks, said in [
            ([{**judge, "plays": [{**menu, "name": f"play_{i}"} for i in range(5)]}], "more than 4 item"),
            ([{**judge, "plays": [menu, menu]}], "names a play twice"),
            ([probe(play=menu), {**judge, "plays": [{**menu, "seconds": 9}]}], "task play open_menu differs"),
            ([{**judge, "plays": [{**menu, "seconds": 9}]}, probe(play=menu)], "task play open_menu differs"),
            ([{**judge, "plays": [menu]}, {**judge, "name": "again", "plays": [{**menu, "inputs": []}]}],
             "task play open_menu differs"),
            ([{**judge, "plays": [{**menu, "name": "look"}]}], "can't be named look"),
            ([{**judge, "plays": [{**menu, "inputs": [{"t": 6, "key": "C", "press": True}]}]}], "at or after its end"),
            ([{**judge, "plays": [{**menu, "args": ["-TaskProbeSeconds=99"]}]}], "can't set -TaskProbeSeconds"),
            ([{**judge, "plays": [{**menu, "inputs": [{"t": 1, "wait": 200}, {"t": 2, "wait": 200}]}]}], "waits 400 s"),
            ([{**judge, "plays": [{**menu, "inputs": [{"t": 1, "teleport_to": {
                "tag": "Ore", "near": {"point": {"pawn": True}, "radius": 500, "z_min": 5, "z_max": 1}}}]}]}],
             "z_min < z_max"),
            ([{**judge, "plays": ["look"]}], "expected object"),
            ([{**judge, "plays": [{**menu, "shots": 5}]}], "unexpected key"),
        ]:
            with self.assertRaisesRegex(ValueError, said):
                task_with(*checks)

    def test_a_screen_measure_takes_a_threshold_from_the_start_never_a_literal(self):
        screen = {"probe": "screen", "rect": [0.25, 0.25, 0.75, 0.75], "field": "luminance", "window": [10, 20]}
        with self.assertRaisesRegex(ValueError, "never a literal value"):
            task_with(probe(measure=screen, expect={"op": ">=", "value": 0.1}))
        task_with(probe(measure=screen, expect={"op": ">=", "calibrate": 0.5}))
        task_with(probe(measure=screen, expect={"op": ">=", "start_times": 1.3}), seed=NO_FIX)
        for bad in ({**screen, "rect": [0.5, 0, 1.2, 1]}, {**screen, "field": "brightness"}):
            with self.assertRaises(ValueError):
                task_with(probe(measure=bad, expect={"op": ">=", "calibrate": 0.5}))

    def test_the_new_readings_are_task_fields(self):
        pieces = {"probe": "pieces", "select": {"class": "StaticMeshComponent", "mesh": "SM_Rock*",
                                                "near": {"point": {"pawn": True}, "radius": 3000}}, "field": "count"}
        task_with(probe(measure=pieces, expect={"op": ">=", "value": 300}))
        task_with(probe(measure={"probe": "pieces", "field": "visible"}, expect={"op": ">=", "value": 1}))
        for field in ("world_yaw:LightComponent0", "world_pitch:Moon", "world_roll:Moon", "forward:Moon.z"):
            task_with(probe(measure={"probe": "actors", "select": {"tag": "Moon"}, "field": field, "of": "first"}))
        for bad in ({"probe": "pieces", "field": "instances"},
                    {"probe": "actors", "select": {"tag": "Moon"}, "field": "forward:Moon.w"}):
            with self.assertRaises(ValueError):
                task_with(probe(measure=bad))

    def test_a_pieces_triangle_threshold_comes_from_the_start_never_a_literal(self):
        forest = {"probe": "pieces", "select": {"class": "ProceduralMeshComponent"}, "at": "end"}
        for field in ("triangles", "visible_triangles"):
            dense = {**forest, "field": field}
            with self.assertRaisesRegex(ValueError, "never a literal value"):
                task_with(probe(measure=dense, expect={"op": ">=", "value": 100000}))
            task_with(probe(measure=dense, expect={"op": ">=", "calibrate": 0.5}))
            task_with(probe(measure=dense, expect={"op": ">=", "start_times": 1.5}), seed=NO_FIX)
        for field in ("count", "visible", "components", "actors"):
            task_with(probe(measure={**forest, "field": field}, expect={"op": ">=", "value": 423}))
        with self.assertRaises(ValueError):
            task_with(probe(measure={**forest, "field": "tris"}, expect={"op": ">=", "calibrate": 0.5}))


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
                "sum": 7, "range": 5, "changes": 3, "rises": 2, "falls": 1}
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


class FairReadings(unittest.TestCase):
    def test_a_count_reads_every_match_past_the_rows_cap(self):
        """The plugin keeps 200 rows a sample; a count of 389 is 389, not 200."""
        crates = m(probe="actors", select={"class": "Crate"}, field="count")
        qid = probes.query_id(probes.needs(crates)[0])
        rows = [{"name": f"Crate{i}", "count": 1} for i in range(200)]
        self.assertEqual(probes.reduce(crates, {"measures": {qid: [{"t": 0.0, "rows": rows, "total": 389}]}}), 389)
        self.assertEqual(probes.reduce(crates, {"measures": {qid: [{"t": 0.0, "rows": rows[:12]}]}}), 12)

    def test_of_reads_the_plugins_summary_of_every_match_past_the_rows_cap(self):
        rows = [{"z": 100.0, "hidden": 0} for _ in range(200)]
        full = {"z": {"n": 389, "nonzero": 388, "sum": 40000.0, "min": 0.0, "max": 900.0},
                "hidden": {"n": 389, "nonzero": 189, "sum": 189.0, "min": 0.0, "max": 1.0}}
        sample = {"t": 0.0, "rows": rows, "total": 389, "full": full}

        def read(**kw):
            measure = m(probe="actors", select={"class": "Crate"}, **kw)
            return probes.reduce(measure, {"measures": {probes.query_id(probes.needs(measure)[0]): [sample]}})

        self.assertEqual(read(field="z", of="max"), 900.0)
        self.assertEqual(read(field="z", of="min"), 0.0)
        self.assertEqual(read(field="z", of="sum"), 40000.0)
        self.assertAlmostEqual(read(field="z", of="mean"), 40000.0 / 389)
        self.assertEqual(read(field="hidden"), 189, "of defaults to count: the non-zero values of every match")
        self.assertEqual(read(field="hidden", of="any"), 1.0)
        self.assertEqual(read(field="z", of="all"), 0.0, "one crate sits at 0")
        self.assertEqual(read(field="z", of="first"), 100.0, "first is the first row")
        self.assertEqual(read(field="yaw", of="max"), None, "a field the summary lacks reads the rows (none here)")

    def test_values_read_through_match_or_an_angle_read_the_rows_alone(self):
        rows = [{"prop:Label": "Gold", "yaw": 170.0}, {"prop:Label": "Iron", "yaw": -170.0}]
        full = {"prop:Label": {"n": 0, "nonzero": 0, "sum": 0.0, "min": None, "max": None},
                "yaw": {"n": 300, "nonzero": 300, "sum": 0.0, "min": -179.0, "max": 179.0}}
        for measure, want in ((m(probe="actors", select={"class": "Ore"}, field="prop:Label", match="Gold"), 1.0),
                              (m(probe="actors", select={"class": "Ore"}, field="yaw", to_angle=180, of="max"), 10.0)):
            qid = probes.query_id(probes.needs(measure)[0])
            found = probes.reduce(measure, {"measures": {qid: [{"t": 0.0, "rows": rows, "total": 300, "full": full}]}})
            self.assertAlmostEqual(found, want)

    def test_pieces_count_placed_mesh_pieces_whatever_their_form(self):
        rocks = m(probe="pieces", select={"mesh": "SM_Rock*"}, field="count")
        self.assertEqual(rocks["agg"], None)
        (query,) = probes.needs(rocks)
        self.assertEqual(query, {"kind": "pieces", "select": {"mesh": "SM_Rock*"}})
        self.assertEqual(m(probe="pieces", field="count")["select"], {})
        value = {"count": 1450, "visible": 1400, "components": 3, "actors": 2}
        play = {"measures": {probes.query_id(query): sampled([value, {**value, "count": 1460}])}}
        self.assertEqual(probes.reduce(rocks, play), 1460)
        self.assertEqual(probes.reduce(m(probe="pieces", select={"mesh": "SM_Rock*"}, field="actors", agg="first"),
                                       play), 2)

    def test_pieces_read_the_triangles_they_hold_and_draw(self):
        """A forest merged into 3 procedural sections reads 3 pieces but every triangle it draws."""
        forest = m(probe="pieces", select={"class": "ProceduralMeshComponent"}, field="visible_triangles")
        (query,) = probes.needs(forest)
        self.assertEqual(query, {"kind": "pieces", "select": {"class": "ProceduralMeshComponent"}},
                         "one query per selection; the plugin answers every field")
        value = {"count": 3, "visible": 3, "components": 1, "actors": 1, "triangles": 960000,
                 "visible_triangles": 900000}
        play = {"measures": {probes.query_id(query): sampled([{**value, "visible_triangles": 0}, value])}}
        self.assertEqual(probes.reduce(forest, play), 900000)
        self.assertEqual(probes.reduce(m(probe="pieces", select={"class": "ProceduralMeshComponent"},
                                         field="visible_triangles", agg="first"), play), 0)
        self.assertEqual(probes.reduce(m(probe="pieces", select={"class": "ProceduralMeshComponent"},
                                         field="triangles"), play), 960000)
        self.assertEqual(probes.reduce(m(probe="pieces", select={"class": "ProceduralMeshComponent"},
                                         field="count"), play), 3, "the count reads as before")
        older = {k: v for k, v in value.items() if "triangles" not in k}
        self.assertIsNone(probes.reduce(forest, {"measures": {probes.query_id(query): sampled([older])}}),
                          "a plugin without the reading gives no value, never 0")

    def test_screen_luminance_is_sampled_like_the_other_probes(self):
        dark = m(probe="screen", field="luminance", window=[1, 1.5], agg="mean")
        self.assertEqual(dark["rect"], [0.0, 0.0, 1.0, 1.0])
        (query,) = probes.needs(m(probe="screen", rect=[0, 0.5, 1, 1], field="luma"))
        self.assertEqual(query, {"kind": "screen", "rect": [0.0, 0.5, 1.0, 1.0]})
        qid = probes.query_id(probes.needs(dark)[0])
        frames = [{"luminance": 0.5, "luma": 0.7}, None, {"luminance": 0.1, "luma": 0.3},
                  {"luminance": 0.2, "luma": 0.4}, {"luminance": 0.9, "luma": 0.9}]
        self.assertAlmostEqual(probes.reduce(dark, {"measures": {qid: sampled(frames)}}), 0.15)

    def test_a_components_world_rotation_reads_as_an_angle(self):
        moon = m(probe="actors", select={"tag": "Moon"}, field="world_yaw:LightComponent0", to_angle=-90, of="first")
        play = actors_play(moon, [[{"world_yaw:LightComponent0": 280.0}]])
        self.assertAlmostEqual(probes.reduce(moon, play), 10.0)
        self.assertTrue(all(tasks.is_angle(f) for f in ("world_yaw:Moon", "world_pitch:Moon", "world_roll:Moon")))
        self.assertFalse(tasks.is_angle("forward:Moon.z"))
        down = m(probe="actors", select={"tag": "Moon"}, field="forward:LightComponent0.z", of="first")
        self.assertEqual(probes.reduce(down, actors_play(down, [[{"forward:LightComponent0.z": -0.5}]])), -0.5)


LAMP = {"probe": "components", "select": {"class": "PointLightComponent", "owner": {"tag": "Lamp"}}, "at": "end"}
CRATE = {"probe": "actors", "select": {"tag": "Crate"}, "at": "end"}


class MoreFairReadings(unittest.TestCase):
    """docs/task-probes.md (2026-11-07): lights that are off, what is on screen, what the player hears, the ground, a
    teleport next to an actor, moving components, whole or broken."""

    def test_the_readings_a_build_chooses_take_a_threshold_from_the_start_never_a_literal(self):
        never = [{**LAMP, "field": "intensity", "of": "max"}, {**LAMP, "field": "extent_z", "of": "max"},
                 {**CRATE, "field": "spread", "of": "max"},
                 {"probe": "audio", "select": {"sound_class": "Ambience"}, "field": "volume"},
                 {"probe": "audio", "field": "max_volume"},
                 {"probe": "ground", "box": [0, 0, 5000, 5000], "grid": 16, "field": "range"}]
        for measure in never:
            with self.assertRaisesRegex(ValueError, "never a literal value"):
                task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
            task_with(probe(measure=measure, expect={"op": ">=", "calibrate": 0.5}))
            task_with(probe(measure=measure, expect={"op": ">=", "start_times": 2}), seed=NO_FIX)
        for measure in ({**LAMP, "field": "on"}, {**LAMP, "field": "simulating"},
                        {**LAMP, "field": "speed", "of": "max"}, {**LAMP, "field": "x", "of": "min"},
                        {**CRATE, "field": "simulating"}, {"probe": "audio", "field": "count"},
                        {"probe": "audio", "field": "audible"}, {"probe": "ground", "xy": [100, 200], "field": "height"},
                        {"probe": "ground", "xy": [0, 0], "field": "hit"},
                        {"probe": "ground", "box": [0, 0, 10, 10], "field": "max"},
                        {"probe": "widgets", "select": {"name": "Warn*", "visible": True}, "field": "count"}):
            task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))

    def test_the_new_readings_refuse_what_they_cant_read(self):
        for bad in ({"probe": "components", "select": {"class": "PointLightComponent"}, "field": "lumens"},
                    {"probe": "actors", "select": {"tag": "A"}, "field": "spread_x"},
                    {"probe": "audio", "select": {"sound": "Rain/*"}, "field": "count"},
                    {"probe": "audio", "field": "loudest"},
                    {"probe": "ground", "field": "height"},
                    {"probe": "ground", "xy": [0, 0], "box": [0, 0, 1, 1], "field": "height"},
                    {"probe": "ground", "xy": [0, 0], "field": "range"},
                    {"probe": "ground", "box": [0, 0, 1, 1], "field": "height"},
                    {"probe": "ground", "box": [5, 0, 1, 1], "field": "max"},
                    {"probe": "ground", "box": [0, 0, 1, 1], "grid": 64, "field": "max"},
                    {"probe": "widgets", "select": {"name": "Warn*", "visible": False}, "field": "count"}):
            with self.assertRaises(ValueError, msg=json.dumps(bad)):
                task_with(probe(measure=bad))

    def test_lights_read_on_and_their_intensity_as_components(self):
        lamp = m(**{**LAMP, "field": "on", "of": "any", "at": None})
        (query,) = probes.needs(lamp)
        self.assertEqual(query["fields"], ["on"])
        play = actors_play(lamp, [[{"name": "L", "on": 1, "intensity": 5000.0}], [{"name": "L", "on": 0,
                                                                                   "intensity": 0.0}]])
        self.assertEqual(probes.reduce(lamp, play), 0)
        bright = m(**{**LAMP, "field": "intensity", "of": "max", "at": None, "agg": "first"})
        self.assertEqual(probes.query_id(probes.needs(bright)[0]), probes.query_id(query), "one query, both fields")
        self.assertEqual(probes.reduce(bright, play), 5000.0)

    def test_a_visible_widget_select_is_its_own_query(self):
        shown = m(probe="widgets", select={"name": "Warn*", "visible": True}, field="count")
        every = m(probe="widgets", select={"name": "Warn*"}, field="count")
        self.assertEqual(probes.needs(shown)[0]["select"], {"name": "Warn*", "visible": True})
        self.assertEqual(probes.needs(every)[0]["select"], {"name": "Warn*"}, "a select without it is as it was")
        self.assertNotEqual(probes.query_id(probes.needs(shown)[0]), probes.query_id(probes.needs(every)[0]))
        self.assertEqual(probes.reduce(shown, actors_play(shown, [[{"name": "WarnVisible"}]])), 1)

    def test_what_the_player_hears_reduces_from_the_audio_samples(self):
        jungle = m(probe="audio", select={"sound_class": "SC_Jungle*", "owner": {"tag": "Zone2"}}, field="volume",
                   agg="mean")
        (query,) = probes.needs(jungle)
        self.assertEqual(query, {"kind": "audio", "select": {"sound_class": "SC_Jungle*", "owner": {"tag": "Zone2"}}})
        self.assertEqual(probes.needs(m(probe="audio", field="count"))[0], {"kind": "audio", "select": {}})
        value = {"count": 2, "audible": 1, "volume": 0.6, "max_volume": 0.5, "loudest": "Birds"}
        qid = probes.query_id(query)
        play = {"measures": {qid: sampled([value, {**value, "volume": 0.2}])}}
        self.assertAlmostEqual(probes.reduce(jungle, play), 0.4)
        self.assertIsNone(probes.reduce(jungle, {"measures": {qid: sampled([None])}}),
                          "a play with no audio device measures nothing, never 0")

    def test_the_ground_reads_a_height_and_a_relief(self):
        hill = m(probe="ground", xy=[1200, -300], field="height")
        self.assertEqual(probes.needs(hill), [{"kind": "ground", "xy": [1200.0, -300.0]}])
        relief = m(probe="ground", box=[0, 0, 8000, 8000], select={"class": "LandscapeProxy"}, field="range")
        self.assertEqual(probes.needs(relief), [{"kind": "ground", "box": [0.0, 0.0, 8000.0, 8000.0], "grid": 8,
                                                 "select": {"class": "LandscapeProxy"}}])
        qid = probes.query_id(probes.needs(relief)[0])
        self.assertEqual(probes.reduce(relief, {"measures": {qid: sampled([{"min": 0, "max": 300, "range": 300,
                                                                            "hits": 64, "points": 64}])}}), 300)
        pid = probes.query_id(probes.needs(hill)[0])
        self.assertIsNone(probes.reduce(hill, {"measures": {pid: sampled([{"height": None, "hit": 0}])}}))

    def test_a_task_play_teleports_next_to_an_actor(self):
        play = {"name": "ore", "seconds": 12, "inputs": [
            {"t": 1, "teleport_to": {"tag": "Ore"}},
            {"t": 3, "teleport_to": {"class": "OreChunk"}, "distance": 350, "offset": [0, 0, 100],
             "face": {"actor": {"tag": "Tug"}}}]}
        first, second = first_check(task_with(probe(play=play, measure={"probe": "pawn", "field": "z"})))["play"][
            "inputs"]
        self.assertEqual(first, {"t": 1.0, "teleport_to": {"tag": "Ore"}, "distance": 200.0, "offset": [0, 0, 0]})
        self.assertEqual(second["face"], {"actor": {"tag": "Tug"}, "offset": [0, 0, 0]})
        self.assertEqual((second["distance"], second["offset"]), (350.0, [0.0, 0.0, 100.0]))
        with self.assertRaises(ValueError):
            task_with(probe(play={**play, "inputs": [{"t": 1, "teleport_to": {"tag": "Ore"}, "yaw": 90}]},
                            measure={"probe": "pawn", "field": "z"}))

    def test_only_a_play_that_measures_audio_runs_with_sound(self):
        from task_check import unreal

        heard = task_with(probe(measure={"probe": "audio", "select": {"sound": "Rain*"}, "field": "count"}),
                          probe("quiet", play={"name": "quiet", "seconds": 10}, measure={"probe": "pawn", "field": "z"}))
        plays = probes.plan(heard)
        self.assertTrue(probes.hears(plays["look"]) and probes.hears(probes.query_file(plays["look"])))
        self.assertFalse(probes.hears(plays["quiet"]) or probes.hears(None))
        self.assertEqual(probes.sound_flags(None), (["-nosound"], ["-benchmark"]), "every other play as before")
        seen = []
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "Game.uproject").write_text("{}", encoding="utf-8")
            machine = types.SimpleNamespace(editor=lambda: "UnrealEditor.exe",
                                            job=lambda label, argv, cwd, timeout: seen.append(argv) or types.SimpleNamespace(
                                                exit_code=0, timed_out=False, output="", seconds=1.0, waited=0.0))
            project = unreal.Project(folder, machine, "start")
            project.play(5, 0, 60, queries=probes.query_file(plays["look"]))
            project.play(5, 0, 60)
        loud, quiet = seen
        self.assertEqual(quiet[quiet.index("-unattended"):quiet.index("-fps=30") + 1],
                         ["-unattended", "-LiveCoding=false", "-nosound", "-nosplash", "-benchmark", "-fps=30"])
        self.assertEqual(loud[loud.index("-unattended"):loud.index("-fps=30") + 1],
                         ["-unattended", "-LiveCoding=false", "-muteaudio", "-nosplash", "-UseFixedTimeStep", "-FixedSeed", "-NOINI",
                          "-noinnerexception", "-TaskProbeSound", "-fps=30"])
        with self.assertRaisesRegex(ValueError, "can't set -TaskProbeSound"):
            task_with(probe(play={"name": "x", "seconds": 5, "args": ["-TaskProbeSound"]},
                            measure={"probe": "pawn", "field": "z"}))


BOX = {"probe": "actors", "select": {"tag": "Box"}, "at": "end"}
BOX_PART = {"probe": "components", "select": {"class": "SkeletalMeshComponent", "owner": {"tag": "Box"}}, "at": "end"}


class ChangedSinceTheStart(unittest.TestCase):
    """docs/task-probes.md, sections 2.4 and 2.5: whether an object changed since the play began, so one that breaks by
    hiding a part or by animating its pieces reads as broken."""

    def test_changed_takes_a_literal_and_the_amounts_behind_it_never_do(self):
        for measure in ({**BOX, "field": "changed", "of": "any"}, {**BOX_PART, "field": "changed", "of": "any"}):
            task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
        for measure in ({**BOX, "field": "bounds_change", "of": "max"},
                        {**BOX, "field": "pose_change", "of": "max"},
                        {**BOX_PART, "field": "bounds_change", "of": "max"},
                        {**BOX_PART, "field": "pose_change", "of": "max"}):
            with self.assertRaisesRegex(ValueError, "never a literal value"):
                task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
            task_with(probe(measure=measure, expect={"op": ">=", "calibrate": 0.5}))
            task_with(probe(measure=measure, expect={"op": ">=", "start_times": 2}), seed=NO_FIX)
        for bad in ({**BOX, "field": "changed_since"}, {**BOX_PART, "field": "pose"}):
            with self.assertRaises(ValueError, msg=json.dumps(bad)):
                task_with(probe(measure=bad))

    def test_one_query_reads_changed_and_its_amounts(self):
        broken = m(**{**BOX, "field": "changed", "of": "any", "at": None})
        (query,) = probes.needs(broken)
        self.assertEqual((query["kind"], query["fields"]), ("actors", ["changed"]))
        posed = m(**{**BOX, "field": "pose_change", "of": "max", "at": None})
        self.assertEqual(probes.query_id(probes.needs(posed)[0]), probes.query_id(query), "one query, both fields")
        play = actors_play(broken, [[{"name": "Box", "changed": 0, "bounds_change": 0.0, "pose_change": 0.0}],
                                    [{"name": "Box", "changed": 1, "bounds_change": 0.0, "pose_change": 2400.0}]])
        self.assertEqual(probes.reduce(broken, play), 1)
        self.assertEqual(probes.reduce(m(**{**BOX, "field": "changed", "of": "any", "at": None, "agg": "first"}),
                                       play), 0)
        self.assertEqual(probes.reduce(posed, play), 2400.0)
        bare = m(**{**BOX, "field": "pose_change", "of": "max", "at": None})
        self.assertIsNone(probes.reduce(bare, actors_play(bare, [[{"name": "Crate", "pose_change": None}]])),
                          "no skinned mesh: no value, never 0")


GLOW_LAMP = {"probe": "actors", "select": {"tag": "Lamp"}, "at": "end"}
GLOW_BULB = {"probe": "components", "at": "end",
             "select": {"class": "StaticMeshComponent", "owner": {"tag": "Lamp"}, "mesh": "SM_Bulb*", "visible": True}}


class LitWhateverMadeTheLight(unittest.TestCase):
    """docs/task-probes.md, sections 2.4 and 2.5: one reading for whether something gives off light and how much,
    whether a build lit it with a light component or with a mesh drawn by an emissive or unlit material."""

    def test_lit_takes_a_literal_and_glow_never_does(self):
        for measure in ({**GLOW_LAMP, "field": "lit", "of": "any"}, {**GLOW_BULB, "field": "lit", "of": "any"}):
            task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
        for measure in ({**GLOW_LAMP, "field": "glow", "of": "sum"}, {**GLOW_BULB, "field": "glow", "of": "max"}):
            with self.assertRaisesRegex(ValueError, "never a literal value"):
                task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
            task_with(probe(measure=measure, expect={"op": ">=", "calibrate": 0.5}))
            task_with(probe(measure=measure, expect={"op": ">=", "start_times": 2}), seed=NO_FIX)
        for bad in ({**GLOW_LAMP, "field": "glow_sources"}, {**GLOW_LAMP, "field": "emissive"},
                    {**GLOW_BULB, "field": "glow_sources"},
                    {**GLOW_BULB, "select": {"class": "StaticMeshComponent", "visible": False}, "field": "lit"},
                    {**GLOW_BULB, "select": {"class": "StaticMeshComponent", "mesh": "Bulb/SM_Bulb"}, "field": "lit"}):
            with self.assertRaises(ValueError, msg=json.dumps(bad)):
                task_with(probe(measure=bad))

    def test_one_query_reads_lit_and_glow_over_every_kind_of_source(self):
        lit = m(**{**GLOW_LAMP, "field": "lit", "of": "any", "at": None})
        (query,) = probes.needs(lit)
        self.assertEqual((query["kind"], query["fields"]), ("actors", ["lit"]))
        glow = m(**{**GLOW_LAMP, "field": "glow", "of": "sum", "at": None})
        self.assertEqual(probes.query_id(probes.needs(glow)[0]), probes.query_id(query), "one query, both fields")
        # a light, a mesh whose emissive parameter went up, an unlit mesh and a hidden glowing mesh, as the plugin reads
        # them (glow_sources rides along for the logs)
        play = actors_play(lit, [[{"name": "Light", "lit": 1, "glow": 800.0, "glow_sources": "light"},
                                  {"name": "Param", "lit": 0, "glow": 0.0, "glow_sources": ""},
                                  {"name": "Hidden", "lit": 0, "glow": 0.0, "glow_sources": ""}],
                                 [{"name": "Light", "lit": 0, "glow": 0.0, "glow_sources": ""},
                                  {"name": "Param", "lit": 1, "glow": 24.84, "glow_sources": "emissive"},
                                  {"name": "Unlit", "lit": 1, "glow": 3.0, "glow_sources": "unlit"},
                                  {"name": "Hidden", "lit": 0, "glow": 0.0, "glow_sources": ""}]])
        self.assertEqual(probes.reduce(lit, play), 1)
        self.assertEqual(probes.reduce(m(**{**GLOW_LAMP, "field": "lit", "of": "count", "at": None}), play), 2)
        self.assertEqual(probes.reduce(glow, play), 27.84)
        first = m(**{**GLOW_LAMP, "field": "glow", "of": "sum", "at": None, "agg": "first"})
        self.assertEqual(probes.reduce(first, play), 800.0)
        bare = m(**{**GLOW_LAMP, "field": "glow", "of": "max", "at": None})
        self.assertIsNone(probes.reduce(bare, actors_play(bare, [[{"name": "Fx", "lit": None, "glow": None}]])),
                          "unread: no value, never 0")

    def test_a_component_select_by_mesh_or_drawn_is_its_own_query(self):
        bulbs = m(**{**GLOW_BULB, "field": "lit", "of": "any", "at": None})
        (query,) = probes.needs(bulbs)
        self.assertEqual(query["select"], {"class": "StaticMeshComponent", "owner": {"tag": "Lamp"}, "mesh": "SM_Bulb*",
                                           "visible": True})
        every = m(probe="components", select={"class": "StaticMeshComponent", "owner": {"tag": "Lamp"}}, field="lit",
                  of="any")
        self.assertNotEqual(probes.query_id(probes.needs(every)[0]), probes.query_id(query))


LIT_HERE = {"has": {"lit": True, "near": {"point": {"xyz": [500, 0, 100]}, "radius": 300}}}
LIT_HERE_SENT = {"has": {"lit": True, "near": {"point": {"xyz": [500.0, 0.0, 100.0]}, "radius": 300.0}}}


class ActorsByAComponent(unittest.TestCase):
    """docs/task-probes.md, section 2.4: an actor select's `has` picks actors by a component they carry (one that
    gives light, a drawn mesh near a point), whatever class or name a build gave them."""

    def test_has_works_wherever_an_actor_select_does(self):
        play = {"name": "away", "seconds": 10, "inputs": [
            {"t": 2, "teleport_to": LIT_HERE, "distance": 400},
            {"t": 4, "teleport_to": {"tag": "Prop", "has": {"class": "PointLightComponent", "visible": True}},
             "face": {"actor": {"has": {"lit": True}}}}]}
        task = task_with(
            probe("a", measure={"probe": "actors", "select": LIT_HERE, "field": "count"}),
            probe("b", play=play, measure={"probe": "pawn", "field": "dist", "to": {"actor": {"has": {"lit": True}}}}),
            probe("c", measure={"probe": "components", "select": {"class": "StaticMeshComponent",
                                                                  "owner": {"has": {"class": "PointLightComponent"}}},
                                "field": "count"}),
            probe("d", measure={"probe": "ground", "xy": [0, 0], "select": {"has": {"visible": True}},
                                "field": "height"}))
        first, second = tasks.checks(task)[1][1]["play"]["inputs"]
        self.assertEqual(first["teleport_to"], LIT_HERE_SENT)
        self.assertEqual(second["teleport_to"], {"tag": "Prop", "has": {"class": "PointLightComponent",
                                                                        "visible": True}})
        self.assertEqual(second["face"], {"actor": {"has": {"lit": True}}, "offset": [0, 0, 0]})
        found = m(probe="actors", select=LIT_HERE, field="count")
        (query,) = probes.needs(found)
        self.assertEqual(query["select"], LIT_HERE_SENT)
        owner = m(probe="components", select={"class": "StaticMeshComponent",
                                              "owner": {"has": {"class": "PointLightComponent"}}}, field="count")
        self.assertEqual(probes.needs(owner)[0]["select"]["owner"], {"has": {"class": "PointLightComponent"}})
        plain = m(probe="actors", select={"tag": "Prop"}, field="count")
        self.assertEqual(probes.needs(plain)[0]["select"], {"tag": "Prop"}, "a select without has is sent as before")
        lit = m(probe="actors", select={"tag": "Prop", "has": {"lit": True}}, field="count")
        self.assertNotEqual(probes.query_id(probes.needs(lit)[0]), probes.query_id(probes.needs(plain)[0]))
        self.assertEqual(probes.reduce(found, actors_play(found, [[{"count": 1}], [{"count": 1}] * 2])), 2)

    def test_has_refuses_what_it_cant_read(self):
        for has in ({}, {"lit": False}, {"visible": False}, {"tag": "Lamp"}, {"class": "Point Light"},
                    {"near": {"point": {"xyz": [0, 0, 0]}}}):
            with self.assertRaises(ValueError, msg=json.dumps(has)):
                task_with(probe(measure={"probe": "actors", "select": {"has": has}, "field": "count"}))
        with self.assertRaises(ValueError):
            task_with(probe(measure={"probe": "components", "select": {"class": "StaticMeshComponent",
                                                                       "has": {"lit": True}}, "field": "count"}))
        with self.assertRaisesRegex(ValueError, "takes no `has`"):
            task_with(probe(play="editor", measure={"probe": "asset", "map": "/Game/Maps/L_A",
                                                    "select": {"tag": "Lamp", "has": {"lit": True}}, "field": "count"}))


UI_TEXT = {"probe": "ui", "select": {"kind": "text"}, "field": "text", "match": r"AMMO\s*\d+", "of": "any"}
# one sample's elements as the plugin reads them: a UMG text block, a Slate text block, a canvas string and
# a canvas rect (a collapsed UMG text block is not on screen, so not a row); source and kind ride along for the logs
UI_ROWS = [{"text": "HP 75%", "x": 0.021, "y": 0.203, "w": 0.083, "h": 0.035, "source": "umg", "kind": "text"},
           {"text": "ITEMS 7", "x": 0.021, "y": 0.278, "w": 0.05, "h": 0.015, "source": "slate", "kind": "text"},
           {"text": "AMMO 30", "x": 0.042, "y": 0.225, "w": 0.106, "h": 0.033, "source": "canvas", "kind": "text"},
           {"text": None, "x": 0.042, "y": 0.296, "w": 0.208, "h": 0.03, "source": "canvas", "kind": "box"}]


class UiWhateverDrawsIt(unittest.TestCase):
    """docs/task-probes.md, section 2.18: one reading for what the UI shows on screen, whether a build drew it with
    UMG widgets, Slate widgets or on the HUD canvas."""

    def test_text_takes_match_and_every_field_a_literal(self):
        for measure in (UI_TEXT, {**UI_TEXT, "of": "count", "select": {"text": "AMMO", "rect": [0, 0, 0.5, 0.5]}},
                        {"probe": "ui", "field": "count"},
                        {"probe": "ui", "select": {"kind": "box", "rect": [0, 0.2, 0.5, 0.4]}, "field": "count"},
                        {"probe": "ui", "select": {"text": "AMMO"}, "field": "y", "of": "first"}):
            task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
        for bad, said in [({**UI_TEXT, "match": None}, "exactly when its field is text"),
                          ({"probe": "ui", "field": "count", "match": "x"}, "exactly when its field is text"),
                          ({**UI_TEXT, "match": "AMMO("}, "isn't a regular expression"),
                          ({"probe": "ui", "select": {"rect": [0.5, 0, 0.2, 1]}, "field": "count"}, "x0 < x1"),
                          ({"probe": "ui", "select": {"kind": "box", "text": "x"}, "field": "count"}, "picks text"),
                          ({"probe": "ui", "field": "source"}, "allowed"),
                          ({"probe": "ui", "field": "kind"}, "allowed"),
                          ({"probe": "ui", "select": {"kind": "line", "text": "1"}, "field": "count"}, "picks text"),
                          ({"probe": "ui", "select": {"kind": "stroke"}, "field": "count"}, ""),
                          ({"probe": "ui", "select": {"source": "canvas"}, "field": "count"}, "")]:
            with self.assertRaisesRegex(ValueError, said, msg=json.dumps(bad)):
                task_with(probe(measure=bad))

    def test_one_query_per_select_its_fields_merged(self):
        text = m(**UI_TEXT)
        (query,) = probes.needs(text)
        self.assertEqual(query, {"kind": "ui", "select": {"kind": "text"}, "fields": ["text"]})
        count = m(probe="ui", select={"kind": "text"}, field="count")
        self.assertEqual(probes.query_id(probes.needs(count)[0]), probes.query_id(query))
        self.assertEqual(m(probe="ui", field="count")["select"], {})
        boxes = m(probe="ui", select={"kind": "box", "rect": [0, 0.2, 0.5, 0.4]}, field="count")
        self.assertNotEqual(probes.query_id(probes.needs(boxes)[0]), probes.query_id(query))

    def test_umg_slate_and_canvas_read_the_same(self):
        text = m(**UI_TEXT)
        play = actors_play(text, [UI_ROWS, [r for r in UI_ROWS if r["source"] != "canvas"], None])
        self.assertEqual(probes.reduce({**text, "at": [0]}, play), 1, "the canvas string")
        self.assertEqual(probes.reduce({**text, "at": [0.5]}, play), 0, "no matching text on screen: 0")
        self.assertIsNone(probes.reduce({**text, "at": [1.0]}, play), "no frame drawn after the sample: no value")
        shown = m(**{**UI_TEXT, "match": r"HP\s*\d+%|ITEMS|AMMO", "of": "count"})
        self.assertEqual(probes.reduce({**shown, "at": [0]}, actors_play(shown, [UI_ROWS])), 3)
        place = m(probe="ui", select={"text": "AMMO"}, field="y", of="first")
        self.assertEqual(probes.reduce(place, actors_play(place, [[UI_ROWS[2]]])), 0.225)
        count = m(probe="ui", select={"kind": "box"}, field="count")
        self.assertEqual(probes.reduce(count, actors_play(count, [[UI_ROWS[3]] * 3])), 3)
        many = actors_play(count, [[{"count": 1}] * 200])
        many["measures"][probes.query_id(probes.needs(count)[0])][0]["total"] = 260
        self.assertEqual(probes.reduce(count, many), 260, "every element counts, past the rows cap")

    def test_lines_count_by_rect_and_digits_drawn_with_lines_read_as_text(self):
        # one sample as the plugin reads a canvas HUD that draws "120" in seven-segment strokes and an outlined box:
        # each stroke a line, the outline one line, and the strokes read as digits one more text element
        strokes = [{"text": None, "x": 0.104 + 0.004 * i, "y": 0.278, "w": 0.002, "h": 0.035, "source": "canvas",
                    "kind": "line"} for i in range(13)]
        outline = {"text": None, "x": 0.104, "y": 0.406, "w": 0.209, "h": 0.057, "source": "canvas", "kind": "line"}
        number = {"text": "120", "x": 0.124, "y": 0.276, "w": 0.073, "h": 0.078, "source": "canvas", "kind": "text"}
        for measure in ({"probe": "ui", "select": {"kind": "line", "rect": [0.09, 0.26, 0.2, 0.37]}, "field": "count"},
                        {"probe": "ui", "select": {"kind": "line"}, "field": "x", "of": "min"}):
            task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
        lines = m(probe="ui", select={"kind": "line", "rect": [0.09, 0.26, 0.2, 0.37]}, field="count")
        self.assertEqual(lines["select"], {"kind": "line", "rect": [0.09, 0.26, 0.2, 0.37]})
        self.assertEqual(probes.reduce(lines, actors_play(lines, [strokes])), 13)
        read = m(**{**UI_TEXT, "match": r"^120$"})
        self.assertEqual(probes.reduce(read, actors_play(read, [[number]])), 1)
        every = m(probe="ui", field="count")
        self.assertEqual(probes.reduce(every, actors_play(every, [strokes + [outline, number]])), 15)


    def test_text_read_from_the_frame_joins_the_text_elements(self):
        # a select of text in a rect also reads the frame as drawn there: one sample as the plugin reads a canvas HUD
        # that draws "125 M" with slanted lines, the line read as a text element of source "ocr"
        rect = [0.031, 0.167, 0.208, 0.259]
        read = {"text": "125 M", "x": 0.046, "y": 0.183, "w": 0.143, "h": 0.059, "source": "ocr", "kind": "text"}
        measure = {"probe": "ui", "select": {"kind": "text", "rect": rect}, "field": "text", "match": r"^125\s*M$",
                   "of": "any"}
        task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
        text = m(**measure)
        self.assertEqual(text["select"], {"kind": "text", "rect": rect})
        self.assertEqual(probes.reduce(m(**measure, at=[0]), actors_play(text, [[read], []])), 1)
        self.assertEqual(probes.reduce(m(**measure, at=[0.5]), actors_play(text, [[read], []])), 0, "nothing read: 0")
        count = m(probe="ui", select={"kind": "text", "rect": rect}, field="count")
        umg = {**UI_ROWS[0], "x": 0.042, "y": 0.556}
        self.assertEqual(probes.reduce(count, actors_play(count, [[read, umg]])), 2)
        regex = m(probe="ui", select={"text": r"\d+\s*M", "rect": rect}, field="count")
        self.assertEqual(probes.reduce(regex, actors_play(regex, [[read]])), 1)


READOUT = [0.02, 0.02, 0.3, 0.12]


def text_readout(value):
    return [{"text": f"SCORE {value}", "x": 0.05, "y": 0.04, "w": 0.01 * len(str(value)) + 0.06, "h": 0.03,
             "source": "umg", "kind": "text"}]


def line_readout(digits):
    """A readout drawn with canvas lines: one stroke per lit segment, no text read."""
    segments = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "7": "abc"}
    place = {"a": (0, 0, 0.01, 0), "b": (0.01, 0, 0, 0.01), "c": (0.01, 0.01, 0, 0.01), "d": (0, 0.02, 0.01, 0),
             "e": (0, 0.01, 0, 0.01), "f": (0, 0, 0, 0.01), "g": (0, 0.01, 0.01, 0)}
    return [{"text": None, "x": 0.05 + 0.015 * i + place[s][0], "y": 0.04 + place[s][1], "w": place[s][2],
             "h": place[s][3], "source": "canvas", "kind": "line"} for i, d in enumerate(digits) for s in segments[d]]


class UiSignature(unittest.TestCase):
    """docs/task-probes.md, section 2.18: whether what a ui select shows updates, however it is drawn."""

    def changes(self, rows, agg="changes", **extra):
        measure = m(probe="ui", select={"rect": READOUT}, field="signature", agg=agg, **extra)
        return probes.reduce(measure, actors_play(measure, rows))

    def test_takes_agg_changes_any_all_or_count(self):
        measure = {"probe": "ui", "select": {"rect": READOUT}, "field": "signature", "window": [2, 10],
                   "agg": "changes"}
        task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
        for agg in ("any", "all", "count"):
            task_with(probe(measure={**measure, "agg": agg}, expect={"op": ">=", "value": 1}))
        for agg in (None, "last", "max", "delta", "range"):
            with self.assertRaisesRegex(ValueError, "signature", msg=str(agg)):
                task_with(probe(measure={**measure, "agg": agg}))
        with self.assertRaisesRegex(ValueError, "exactly when its field is text"):
            task_with(probe(measure={**measure, "match": "x"}))
        (query,) = probes.needs(m(**measure))
        self.assertEqual(query, {"kind": "ui", "select": {"rect": READOUT}, "fields": ["h", "text", "w", "x", "y"]})
        count = m(probe="ui", select={"rect": READOUT}, field="count")
        self.assertEqual(probes.query_id(probes.needs(count)[0]), probes.query_id(query), "one select, one reading")

    def test_a_text_readout_changing_counts(self):
        rows = [text_readout(v) for v in (0, 0, 12, 12, 25, 140, 140)]
        self.assertEqual(self.changes(rows), 3)
        self.assertEqual(self.changes(rows, window=[0, 1.5]), 1)

    def test_a_line_drawn_readout_changing_counts(self):
        self.assertEqual(self.changes([line_readout(d) for d in ("10", "10", "12", "13", "13", "70")]), 3)
        self.assertEqual(self.changes([line_readout("10")] * 6), 0)

    def test_a_static_readout_never_changes(self):
        still = text_readout(120)
        self.assertEqual(self.changes([still] * 8), 0)
        jitter = [[{**still[0], "x": 0.05 + d}] for d in (0, 0.0001, -0.0001, 0.0002)]
        self.assertEqual(self.changes(jitter), 0, "geometry is read to 0.002 of the viewport")
        restyled = [still, [{**still[0], "source": "canvas"}], [{**still[0], "name": "Other"}]]
        self.assertEqual(self.changes(restyled), 0, "how a build drew it is not what it shows")
        reordered = [text_readout(1) + line_readout("1"), line_readout("1") + text_readout(1)]
        self.assertEqual(self.changes(reordered), 0, "the elements are a set")

    def test_nothing_shown_reads_zero(self):
        rows = [[], text_readout(5), [], None]
        self.assertEqual(self.changes(rows, agg="count"), 1, "samples showing something")
        self.assertEqual(self.changes(rows, agg="all"), 0)
        self.assertEqual(self.changes(rows, agg="any"), 1)
        self.assertEqual(self.changes(rows), 2, "appearing and going are changes; no frame drawn is no value")


SPOT = {"point": {"xyz": [100, 0, 50]}, "radius": 300}
SPOT_SENT = {"point": {"xyz": [100.0, 0.0, 50.0]}, "radius": 300.0}
BEAM = {"from": {"pawn": True, "offset": [0, 0, 60]}, "to": {"camera": True, "forward": 3000}, "radius": 40}


def number_rows(*texts):
    """Text elements of one sample, given right to left so reading order must be restored."""
    return [{"text": t, "x": 0.05 + 0.1 * i, "y": 0.04, "w": 0.08, "h": 0.03, "source": "ocr", "kind": "text"}
            for i, t in enumerate(texts)][::-1]


class OutcomeReadings(unittest.TestCase):
    """docs/task-probes.md, sections 1.1, 2.1, 2.4, 2.5, 2.13, 2.18 and 2.19: what is drawn in a place, how fast a
    part spins, live effects, which way a number or a clock on screen moved, an object a player can shove, a height
    band, a held teleport and a wait in real time."""

    def test_drawn_reads_a_place_near_a_point_or_along_a_line(self):
        near = [{"probe": "drawn", "near": SPOT, "field": f, "window": [2, 10], "agg": "mean"}
                for f in ("motion", "base_r", "base_g", "base_b", "base_change")]
        line = [{"probe": "drawn", "line": BEAM, "field": f, "at": "end"} for f in ("reach", "length")]
        for measure in near + line:
            with self.assertRaisesRegex(ValueError, "never a literal value"):
                task_with(probe(measure=measure, expect={"op": ">=", "value": 1}))
            task_with(probe(measure=measure, expect={"op": ">=", "start_times": 2}), seed=NO_FIX)
        task = task_with(*[probe(f"d{i}", measure=x, expect={"op": ">=", "calibrate": 0.5})
                           for i, x in enumerate(near + line)],
                         probe("shown", measure={"probe": "drawn", "near": SPOT, "field": "drawn"},
                               expect={"op": "==", "value": 1}))
        plan = probes.plan(task)["look"]
        self.assertEqual(sorted(len(q["fields"]) for q in plan), [2, 6], "one query per place, its fields merged")
        self.assertEqual(next(q for q in plan if "near" in q)["near"], SPOT_SENT)
        along = next(q for q in plan if "line" in q)["line"]
        self.assertEqual(along, {"from": {"pawn": True, "offset": [0, 0, 60]}, "to": {"camera": True,
                                                                                      "forward": 3000.0},
                                 "radius": 40.0})
        motion = m(probe="drawn", near=SPOT, field="motion", agg="mean")
        qid = probes.query_id(probes.needs(motion)[0])
        values = [{"drawn": 1, "motion": None}, {"drawn": 1, "motion": 0.2}, {"drawn": 1, "motion": 0.4}, None]
        self.assertAlmostEqual(probes.reduce(motion, {"measures": {qid: sampled(values)}}), 0.3)
        for bad in ({"probe": "drawn", "field": "drawn"}, {"probe": "drawn", "near": SPOT, "line": BEAM, "field": "drawn"},
                    {"probe": "drawn", "near": SPOT, "field": "reach"}, {"probe": "drawn", "line": BEAM, "field": "motion"},
                    {"probe": "drawn", "line": {**BEAM, "radius": 0}, "field": "reach"},
                    {"probe": "drawn", "near": SPOT, "field": "colour"}):
            with self.assertRaises(ValueError, msg=str(bad)):
                task_with(probe(measure=bad))

    def test_spin_is_a_field_of_components_and_actors_and_never_a_literal(self):
        fan = {"probe": "components", "select": {"class": "PrimitiveComponent", "near": SPOT}, "field": "spin",
               "of": "max", "agg": "mean"}
        for measure in (fan, {"probe": "actors", "select": {"tag": "Fan"}, "field": "spin", "at": "end"}):
            with self.assertRaisesRegex(ValueError, "never a literal value"):
                task_with(probe(measure=measure, expect={"op": ">=", "value": 90}))
            task_with(probe(measure=measure, expect={"op": ">=", "calibrate": 0.5}))
        turning = m(**fan)
        rows = [[{"name": "Blade", "spin": None}], [{"name": "Blade", "spin": 360.0}, {"name": "Hub", "spin": 0.0}],
                [{"name": "Blade", "spin": 720.0}]]
        self.assertEqual(probes.reduce(turning, actors_play(turning, rows)), 540)

    def test_a_components_select_takes_live_effects_with_or_without_a_class(self):
        live = {"probe": "components", "select": {"effect": True, "near": SPOT}, "field": "count", "at": "end"}
        task_with(probe(measure=live, expect={"op": "<=", "value": 3}),
                  probe("b", measure={**live, "select": {"class": "NiagaraComponent", "effect": True}}))
        (query,) = probes.needs(m(**live))
        self.assertEqual(query["select"], {"effect": True, "near": SPOT_SENT})
        for bad in ({"near": SPOT}, {"effect": False}):
            with self.assertRaises(ValueError, msg=str(bad)):
                task_with(probe(measure={**live, "select": bad}))

    def shown(self, field, samples, agg="last", **extra):
        measure = m(probe="ui", select={"kind": "text", "rect": READOUT}, field=field, agg=agg, **extra)
        return probes.reduce(measure, actors_play(measure, samples))

    def test_ui_number_reads_the_first_number_shown_in_reading_order(self):
        self.assertEqual(self.shown("number", [number_rows("SCORE", "3,450")]), 3450)
        self.assertEqual(self.shown("number", [number_rows("x3", "120")]), 3, "the first in reading order")
        self.assertEqual(self.shown("number", [number_rows("TEMP -12.5")]), -12.5)
        self.assertEqual(self.shown("number", [number_rows("LAP 2-3")]), 2, "a dash between numbers is no sign")
        self.assertIsNone(self.shown("number", [number_rows("READY")]))
        (query,) = probes.needs(m(probe="ui", select={"kind": "text", "rect": READOUT}, field="number"))
        signature = m(probe="ui", select={"kind": "text", "rect": READOUT}, field="signature", agg="changes")
        self.assertEqual(query, probes.needs(signature)[0], "one select, one query")
        with self.assertRaisesRegex(ValueError, "exactly when its field is text"):
            task_with(probe(measure={"probe": "ui", "select": {"rect": READOUT}, "field": "number", "match": "x"}))

    def test_ui_number_tells_which_way_it_moved(self):
        scores = [number_rows(f"SCORE {v}") for v in (0, 0, 10, 25, 25, 0, 5)] + [None]
        self.assertEqual(self.shown("number", scores, agg="rises"), 3)
        self.assertEqual(self.shown("number", scores, agg="falls"), 1, "a reset is a fall")
        self.assertEqual(self.shown("number", scores, agg="changes"), 4)
        task_with(probe(measure={"probe": "ui", "select": {"kind": "text", "rect": READOUT}, "field": "number",
                                 "window": [2, 10], "agg": "falls"}, expect={"op": "==", "value": 0}))

    def test_ui_clock_reads_a_timer_as_seconds_through_a_pause_and_a_retry(self):
        self.assertEqual(self.shown("clock", [number_rows("TIME 1:05.5")]), 65.5)
        self.assertEqual(self.shown("clock", [number_rows("1:02:03")]), 3723)
        self.assertEqual(self.shown("clock", [number_rows("12.5s")]), 12.5, "a plain number is seconds")
        run = [number_rows(f"0:{s:02d}") for s in (1, 2, 3)] + [number_rows("0:03")] * 4 + \
            [number_rows(f"0:{s:02d}") for s in (0, 1)]
        self.assertEqual(self.shown("clock", run, agg="range", window=[1.0, 3.0]), 0, "held through the pause")
        self.assertEqual(self.shown("clock", run, agg="falls"), 1, "reset on the retry")

    def test_has_finds_an_object_by_what_it_can_do(self):
        shovable = {"has": {"simulating": True, "movable": True, "near": {"point": {"pawn": True}, "radius": 2000}}}
        play = {"name": "shove", "seconds": 10, "inputs": [{"t": 1, "teleport_to": shovable, "distance": 150}]}
        task = task_with(probe(play=play, measure={"probe": "actors", "select": shovable, "field": "x", "at": "end"}))
        self.assertTrue(probes.plan(task)["shove"][0]["select"]["has"]["simulating"])
        with self.assertRaises(ValueError):
            task_with(probe(measure={"probe": "actors", "select": {"has": {"movable": False}}, "field": "count"}))

    def test_near_takes_a_height_band_wherever_it_works(self):
        band = {"point": {"xyz": [0, 0, 0]}, "radius": 500, "z_min": 100, "z_max": 300}
        rel = {"point": {"pawn": True}, "radius": 500, "z_min": -50, "z_relative": True}
        task = task_with(
            probe("a", measure={"probe": "actors", "select": {"near": band}, "field": "count"}),
            probe("b", measure={"probe": "components", "select": {"class": "LightComponent", "near": rel},
                                "field": "count"}),
            probe("c", measure={"probe": "pieces", "select": {"near": band}, "field": "count"}),
            probe("d", measure={"probe": "actors", "select": {"has": {"visible": True, "near": rel}},
                                "field": "count"}),
            probe("e", measure={"probe": "drawn", "near": band, "field": "drawn"}))
        sent = [json.dumps(q, sort_keys=True) for q in probes.plan(task)["look"]]
        self.assertEqual(sum('"z_max": 300.0, "z_min": 100.0' in q for q in sent), 3)
        self.assertEqual(sum('"z_relative": true' in q for q in sent), 2)
        plain = m(probe="actors", select={"near": SPOT}, field="count")
        self.assertEqual(probes.needs(plain)[0]["select"], {"near": SPOT_SENT}, "a near without a band as before")
        for bad in ({**band, "z_min": 300}, {"point": {"pawn": True}, "radius": 1, "z_relative": True}):
            with self.assertRaises(ValueError, msg=str(bad)):
                task_with(probe(measure={"probe": "actors", "select": {"near": bad}, "field": "count"}))

    def test_a_teleport_holds_and_a_play_waits_in_real_time(self):
        play = {"name": "tour", "seconds": 60, "inputs": [
            {"t": 1, "teleport": [0, 0, 100], "hold": 5}, {"t": 2, "teleport_to": {"tag": "Pad"}, "hold": 3},
            {"t": 4, "key": "Enter", "press": True}, {"t": 8, "wait": 90}, {"t": 20, "wait": 30}]}
        task = task_with(probe(play=play, measure={"probe": "pawn", "field": "z"}))
        sent = first_check(task)["play"]
        self.assertEqual(tasks.waited(sent), 120)
        self.assertEqual(sent["inputs"][0], {"t": 1.0, "teleport": [0.0, 0.0, 100.0], "yaw": 0.0, "hold": 5.0})
        self.assertEqual(sent["inputs"][3], {"t": 8.0, "wait": 90.0})
        self.assertEqual(tasks.play({"name": "tp", "seconds": 9, "inputs": [{"t": 1, "teleport": [0, 0, 0]}]})["inputs"],
                         [{"t": 1.0, "teleport": [0.0, 0.0, 0.0], "yaw": 0.0}], "sent as before")
        for bad in ([{"t": 1, "wait": 200}, {"t": 2, "wait": 150}], [{"t": 1, "wait": 0}], [{"t": 1, "wait": 301}],
                    [{"t": 1, "teleport": [0, 0, 0], "hold": 0}], [{"t": 1, "teleport": [0, 0, 0], "hold": 121}]):
            with self.assertRaises(ValueError, msg=str(bad)):
                task_with(probe(play={**play, "inputs": bad}, measure={"probe": "pawn", "field": "z"}))


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


class NamesTheStartHas(unittest.TestCase):
    """write-tasks section 5: a required probe never depends on a name only the reference has (a class, tag, map or
    asset the thread created), since another fair build names it otherwise."""

    def test_a_name_or_map_the_thread_created_is_refused_and_the_rest_pass(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            def git(*a):
                return subprocess.run(["git", "-C", d, *a], check=True, capture_output=True).stdout.decode().strip()
            git("init", "-q")
            git("config", "user.email", "t@t")
            git("config", "user.name", "t")
            (Path(d) / "Source" / "G").mkdir(parents=True)
            (Path(d) / "Content" / "Maps").mkdir(parents=True)
            (Path(d) / "Source" / "G" / "Hero.h").write_text("class AGHero {};\n")
            (Path(d) / "Content" / "Maps" / "L_Start.umap").write_bytes(b"")
            git("add", "-A")
            git("commit", "-qm", "start")
            (Path(d) / "Source" / "G" / "Turret.h").write_text('class AGTurret {}; Tags.Add("Turret");\n')
            (Path(d) / "Content" / "Maps" / "L_Yard.umap").write_bytes(b"")
            git("add", "-A")
            git("commit", "-qm", "reference")
            def check(name, measure, play="look", **extra):
                return {"kind": "probe", "name": name, "measure": measure, "play": play, **extra}
            task = {"seed": {"commit": git("rev-parse", "HEAD~1"), "reference": git("rev-parse", "HEAD")},
                    "milestones": [{"name": "done", "checks": [
                        check("turrets", {"probe": "actors", "select": {"class": "AGTurret_C"}, "field": "count"}),
                        check("tagged", {"probe": "actors", "select": {"tag": "Turret"}, "field": "count"}),
                        check("yard", {"probe": "pawn", "field": "z"},
                              play={"name": "yard", "seconds": 5, "map": "/Game/Maps/L_Yard?Scenario=1"}),
                        check("hero", {"probe": "actors", "select": {"class": "AGHero"}, "field": "count"}),
                        check("lights", {"probe": "components", "field": "count",
                                         "select": {"class": "PointLightComponent", "owner": {"class": "AGHero"}}}),
                        check("pattern", {"probe": "actors", "select": {"class": "AGTur*"}, "field": "count"}),
                        check("optional", {"probe": "actors", "select": {"class": "AGTurret"}, "field": "count"},
                              required=False)]}]}
            found = tasks.validator().reference_only_names(d, task)
        self.assertEqual(found, [("turrets", "AGTurret"), ("tagged", "Turret"), ("yard", "/Game/Maps/L_Yard")])

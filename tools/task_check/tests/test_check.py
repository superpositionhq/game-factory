"""A task checked end to end with fake Unreal: the sides' plays and builds, calibration, the grades, a whole check's
result file; a commit materialized from a real git repo; the argv a play passes to the game."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import NO_FIX, FakeProject, measuring, probe, ran, side, task_with

from task_check import check, cli, probes, seeds, tasks, unreal

WALLS = {"class": "SCCastlePiece", "tag": "Wall"}


def grade(task, mode, start, reference=None, thresholds=None):
    return check.Grade(task, mode, start, reference, {} if thresholds is None else thresholds).run()


class Grades(unittest.TestCase):
    def test_a_literal_probe_passes_on_the_measured_number_and_its_queries_reach_the_plugin(self):
        task = task_with(probe(), probe("walls", measure={"probe": "actors", "select": WALLS, "field": "z",
                                                          "of": "max"}, expect={"op": ">", "value": 100}),
                         probe("seen", measure={"probe": "camera", "field": "occluded", "agg": "any"},
                               expect={"op": "==", "value": 0}))
        game = FakeProject(measuring(120))
        found = grade(task, "reference", side("start", FakeProject(), task), side("reference", game, task))
        self.assertTrue(all(c["passed"] for c in found["checks"]), found["checks"])
        details = [c["detail"] for c in found["checks"]]
        self.assertEqual(details[0], "The hero stands on the ground. | measured 120, threshold >= 0")
        self.assertTrue(details[1].endswith("| measured 120, threshold > 100"))
        self.assertEqual(found["probes"]["walls"], {"value": 120.0, "threshold": 100.0, "start": None, "fix": None})
        (look,) = game.plays
        self.assertEqual((look["seconds"], look["shots"], look["inputs"]), (20, 6, None))
        self.assertEqual({q["kind"] for q in look["queries"]["queries"]}, {"actors", "camera"})

    def test_a_play_that_wrote_no_probe_fails_its_probes_saying_why(self):
        task = task_with(probe())
        found = grade(task, "reference", side("start", FakeProject(), task),
                      side("reference", FakeProject(measuring(0, crash=True)), task))
        self.assertFalse(found["checks"][0]["passed"])
        self.assertTrue(found["checks"][0]["detail"].endswith(
            "measured nothing, threshold >= 0: no samples in the window (the play wrote no probe file)"))

    def test_a_task_play_is_played_once_with_its_inputs_map_args_and_sampling(self):
        play = {"name": "arena", "seconds": 8, "map": "/Game/Maps/L_Arena?Scenario=2", "args": ["-AutoPlay"],
                "every": 0.25, "inputs": [{"t": 0.2, "teleport": [1, 2, 3], "yaw": 90},
                                          {"t": 1, "key": "LeftMouseButton", "press": True}]}
        task = task_with(probe("a", play=play, measure={"probe": "actors", "select": WALLS, "field": "count"},
                               expect={"op": ">=", "value": 1}),
                         probe("b", play=play, measure={"probe": "log", "pattern": "LogInit"},
                               expect={"op": "==", "value": 1}))
        game = FakeProject(measuring(5))
        found = grade(task, "reference", side("start", FakeProject(), task), side("reference", game, task))
        self.assertTrue(all(c["passed"] for c in found["checks"]), found["checks"])
        (played,) = game.plays
        self.assertEqual((played["seconds"], played["shots"], played["map"], played["args"], played["every"]),
                         (8, 2, "/Game/Maps/L_Arena?Scenario=2", ["-AutoPlay"], 0.25))
        self.assertEqual(played["queries"]["every"], 0.25)
        self.assertEqual(played["inputs"], [{"t": 0.2, "teleport": [1.0, 2.0, 3.0], "yaw": 90.0},
                                            {"t": 1.0, "key": "LeftMouseButton", "press": True}])

    def test_the_drive_plays_its_scripted_inputs_and_the_tasks_play_map(self):
        task = {**task_with(probe(play="drive")), "play_map": "/Game/Maps/L_Town?Scenario=1"}
        game = FakeProject(measuring(5))
        grade(task, "reference", side("start", FakeProject(), task), side("reference", game, task))
        self.assertEqual((game.plays[0]["seconds"], game.plays[0]["shots"], game.plays[0]["map"]),
                         (22, 8, "/Game/Maps/L_Town?Scenario=1"))
        self.assertEqual(game.plays[0]["inputs"], check.DRIVE)

    def test_a_calibrated_threshold_is_made_from_the_start_and_the_reference(self):
        task = task_with(probe(expect={"op": ">=", "calibrate": 0.5}))
        start, reference = FakeProject(measuring(-500)), FakeProject(measuring(100))
        sides, kept = (side("start", start, task), side("reference", reference, task)), {}
        ref = grade(task, "reference", *sides, kept)
        own = grade(task, "start", *sides, kept)
        self.assertEqual(ref["checks"][0]["detail"],
                         "The hero stands on the ground. | measured 100, threshold >= -200 (start -500, fix 100)")
        self.assertTrue(ref["checks"][0]["passed"])
        self.assertFalse(own["checks"][0]["passed"])
        self.assertEqual(own["probes"]["hero_on_ground"],
                         {"value": -500.0, "threshold": -200.0, "start": -500.0, "fix": 100.0})
        self.assertEqual((len(start.plays), len(reference.plays)), (1, 1), "each side played once")

    def test_a_start_and_reference_that_measure_the_same_fail_as_uncalibrated(self):
        task = task_with(probe(expect={"op": ">=", "calibrate": 0.5}),
                         probe("walls", measure={"probe": "actors", "select": WALLS, "field": "z", "of": "max"}))
        sides = (side("start", FakeProject(measuring(100)), task),
                 side("reference", FakeProject(measuring(100 + 1e-5)), task))
        found = grade(task, "reference", *sides)
        self.assertFalse(found["checks"][0]["passed"])
        self.assertTrue(found["checks"][0]["detail"].startswith(
            "uncalibrated: hero_on_ground: the start and the reference both measure 100"))
        self.assertEqual(found["probes"]["hero_on_ground"]["start"], 100.0)
        self.assertTrue(found["checks"][1]["passed"], "every other probe is still measured")

    def test_a_reference_that_measures_nothing_or_a_start_relative_start_that_measures_nothing(self):
        task = task_with(probe(expect={"op": ">=", "calibrate": 0.5}))
        found = grade(task, "reference", side("start", FakeProject(measuring(0)), task),
                      side("reference", FakeProject(measuring(0, crash=True)), task))
        self.assertIn("the reference measured nothing", found["checks"][0]["detail"])
        relative = task_with(probe(expect={"op": ">=", "start_plus": 5}), seed=NO_FIX)
        found = grade(relative, "start", side("start", FakeProject(measuring(0, crash=True)), relative))
        self.assertIn("the start measured nothing", found["checks"][0]["detail"])

    def test_a_start_that_measures_nothing_anchors_a_calibrated_threshold_on_the_reference(self):
        task = task_with(probe(expect={"op": ">=", "calibrate": 0.5}))
        found = grade(task, "reference", side("start", FakeProject(measuring(0, crash=True)), task),
                      side("reference", FakeProject(measuring(100)), task))
        self.assertTrue(found["checks"][0]["detail"].endswith("measured 100, threshold >= 75 (start nothing, fix 100)"))

    def test_a_threshold_relative_to_the_start_needs_only_the_start(self):
        task = task_with(probe(expect={"op": ">=", "start_plus": 50}),
                         probe("twice", expect={"op": ">=", "start_times": 2}), seed=NO_FIX)
        start = FakeProject(measuring(60))
        found = grade(task, "start", side("start", start, task))
        self.assertEqual([c["passed"] for c in found["checks"]], [False, False])
        self.assertTrue(found["checks"][0]["detail"].endswith("measured 60, threshold >= 110 (start 60)"))
        self.assertEqual(len(start.plays), 1, "the start played once")

    def test_needs_and_the_checks_a_start_isnt_asked(self):
        task = task_with({"kind": "build", "name": "editor_builds"},
                         {"kind": "boot", "name": "boots_clean", "seconds": 10, "needs": ["editor_builds"]},
                         {"kind": "judge", "name": "looks_right", "question": "q", "required": False,
                          "rubric": [{"key": "k", "criterion": "c"}]},
                         probe(needs=["boots_clean"]))
        broken = FakeProject(measuring(5), build_exit=6)
        found = grade(task, "reference", side("start", FakeProject(), task), side("reference", broken, task))
        self.assertEqual([(c["passed"], c["detail"]) for c in found["checks"]],
                         [(False, "build failed (exit 6)"), (False, "not run: needs editor_builds"),
                          (True, check.NOT_JUDGED), (False, "not run: needs boots_clean")])
        start = grade(task, "start", side("start", FakeProject(measuring(-5)), task))
        self.assertEqual([c["passed"] for c in start["checks"]], [True, True, True, False])
        self.assertEqual(start["checks"][0]["detail"], "not asked: the start is checked on its probes")

    def test_a_boot_and_its_log(self):
        task = task_with({"kind": "boot", "name": "boots_clean", "seconds": 10},
                         {"kind": "log_absent", "name": "no_ensures", "pattern": "Ensure"}, probe())
        found = grade(task, "reference", side("start", FakeProject(), task),
                      side("reference", FakeProject(measuring(5)), task))
        self.assertEqual([c["detail"] for c in found["checks"][:2]],
                         ["ran 10 s with no crash or fatal error", "0 matching log line(s)"])
        crashed = grade(task, "reference", side("start", FakeProject(), task),
                        side("reference", FakeProject(measuring(5, crash=True)), task))
        self.assertEqual(crashed["checks"][0]["detail"], "crashed")

    def test_editor_probes_run_one_pass_per_side_and_a_build_failure_fails_them(self):
        asset = {"probe": "asset", "asset": "/Game/Materials/M_Road", "field": "prop:two_sided"}
        task = task_with(probe("road", play="editor", measure=asset, expect={"op": "==", "value": 1}),
                         probe("road_again", play="editor", measure={**asset, "field": "prop:blend_mode"},
                               expect={"op": "==", "value": 0}))

        def editor(script, timeout):
            nonce = script.split("NONCE = ")[1].split("\n")[0].strip("'")
            ids = json.loads(eval(script.split("MEASURES = json.loads(")[1].split(")\n")[0]))
            line = json.dumps({"nonce": nonce, "measures": {i: {"value": 1} for i in ids}})
            return ran(f"LogPython: {probes.MARKER} {line}\nPython script executed successfully")

        game = FakeProject(editor=editor)
        found = grade(task, "reference", side("start", FakeProject(), task), side("reference", game, task))
        self.assertEqual([c["passed"] for c in found["checks"]], [True, False])
        self.assertEqual(len(game.scripts), 1, "one pass for both")
        broken = grade(task, "reference", side("start", FakeProject(), task),
                       side("reference", FakeProject(editor=editor, build_exit=6), task))
        self.assertTrue(broken["checks"][0]["detail"].endswith("the project didn't build, so the editor couldn't "
                                                               "open it"))
        silent = grade(task, "reference", side("start", FakeProject(), task),
                       side("reference", FakeProject(editor=lambda s, t: ran("LogPython: Error", 1)), task))
        self.assertTrue(silent["checks"][0]["detail"].endswith("the editor pass gave no result (exit 1)"))


def git(repo, *args, data=None):
    return subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True, check=True).stdout


def make_game(root, engine="5.7"):
    """A tiny game repo: main with an LFS file (its object in .git/lfs/objects), a Tasks/ folder that never reaches a
    copy, and an orphan tasks branch with one task."""
    repo = Path(root) / "metro-runner"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "dev@example.invalid")
    git(repo, "config", "user.name", "dev")
    (repo / "Metro.uproject").write_text(json.dumps({"EngineAssociation": engine}), encoding="utf-8")
    (repo / "Source").mkdir()
    (repo / "Source" / "Metro.cpp").write_text("int a;\n", encoding="utf-8")
    (repo / "Tasks").mkdir()
    (repo / "Tasks" / "x.json").write_text("{}", encoding="utf-8")
    data = b"a texture's bytes"
    import hashlib
    oid = hashlib.sha256(data).hexdigest()
    store = repo / ".git" / "lfs" / "objects" / oid[:2] / oid[2:4]
    store.mkdir(parents=True)
    (store / oid).write_bytes(data)
    (repo / "Content").mkdir()
    (repo / "Content" / "T_Wall.uasset").write_bytes(
        f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {len(data)}\n".encode())
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "start")
    start = git(repo, "rev-parse", "HEAD").decode().strip()
    (repo / "Source" / "Metro.cpp").write_text("int a = 1;\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "fix")
    fix = git(repo, "rev-parse", "HEAD").decode().strip()
    return repo, start, fix, data


class Seeds(unittest.TestCase):
    def test_a_commit_is_materialized_with_its_lfs_objects_the_plugin_and_no_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, start, fix, data = make_game(tmp)
            made = seeds.materialize(repo, start, Path(tmp) / "copy")
            copy = Path(tmp) / "copy"
            self.assertEqual((copy / "Content" / "T_Wall.uasset").read_bytes(), data)
            self.assertEqual((copy / "Source" / "Metro.cpp").read_text(encoding="utf-8"), "int a;\n")
            self.assertFalse((copy / "Tasks").exists(), "a task's answers never reach a copy")
            self.assertEqual(made["linked"] + made["copied"], 1)
            seeds.add_probe(copy)
            self.assertTrue((copy / "Plugins" / "TaskProbe" / "TaskProbe.uplugin").is_file())
            self.assertEqual(json.loads((copy / "Metro.uproject").read_text(encoding="utf-8")),
                             {"EngineAssociation": "5.7"}, "the game's own files stay as committed")
            seeds.remove(copy)
            self.assertTrue((repo / ".git" / "lfs" / "objects").is_dir())

    def test_a_maps_missing_packages_are_reported_never_filled_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, start, _, _ = make_game(tmp)
            maps = repo / "Content" / "Maps"
            maps.mkdir(parents=True)
            (maps / "L_Town.umap").write_bytes(b"\x00/Game/Packs/Rocks/SM_Rock\x00/Game/T_Wall\x00/Game/Maps/L_Town\x00")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "a map naming a pack the commit lacks")
            sha = git(repo, "rev-parse", "HEAD").decode().strip()
            self.assertEqual(seeds.missing_packages(repo, sha, "/Game/Maps/L_Town?Scenario=1"),
                             (["/Game/Packs/Rocks/SM_Rock"], 2))
            self.assertIsNone(seeds.missing_packages(repo, sha, "/Game/Maps/L_Nowhere"))
            task = {**task_with(probe()), "play_map": "/Game/Maps/L_Town?Scenario=1"}
            gaps = check.map_gaps(repo, sha, task)
            self.assertEqual(gaps, {"/Game/Maps/L_Town": {"missing": ["/Game/Packs/Rocks/SM_Rock"], "names": 2}})
            note, = check.gap_notes({"start": {"missing_packages": gaps}})
            self.assertTrue(note.startswith("start: /Game/Maps/L_Town names 1 of its 2 /Game packages"))
            seeds.materialize(repo, sha, Path(tmp) / "copy")
            self.assertFalse((Path(tmp) / "copy" / "Content" / "Packs").exists(), "nothing is added")

    def test_a_missing_lfs_object_and_another_engine_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, start, _, _ = make_game(tmp, engine="5.3")
            shutil.rmtree(repo / ".git" / "lfs")
            with self.assertRaisesRegex(FileNotFoundError, "lfs fetch"):
                seeds.materialize(repo, start, Path(tmp) / "copy")
            (Path(tmp) / "other").mkdir()
            (Path(tmp) / "other" / "Old.uproject").write_text('{"EngineAssociation": "5.3"}', encoding="utf-8")
            with self.assertRaises(seeds.WrongEngine):
                seeds.add_probe(Path(tmp) / "other")


class Whole(unittest.TestCase):
    def check(self, task, projects, tmp):
        """check_task with the scratch copies made for real and Unreal faked: `projects` {side: FakeProject}."""
        repo, start, fix, _ = make_game(tmp)
        task["seed"] = {**task["seed"], "commit": start}
        if "reference" in task["seed"]:
            task["seed"]["reference"] = fix
        raw = json.dumps(task).encode()

        def project(folder, machine, label):
            return projects[Path(folder).name]

        with mock.patch.object(unreal, "Project", project), \
                mock.patch.object(unreal.Machine, "for_project", classmethod(lambda cls, p, d=False: cls(Path(p), None))):
            return check.check_task(repo, task, raw, Path(tmp) / "scratch", Path(tmp) / "out", log=lambda *a: None)

    def test_a_valid_task_with_a_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with({"kind": "build", "name": "editor_builds"},
                             {"kind": "boot", "name": "boots_clean", "seconds": 10, "needs": ["editor_builds"]},
                             probe(expect={"op": ">=", "calibrate": 0.5}, needs=["boots_clean"]))
            result = self.check(task, {"start": FakeProject(measuring(-500)),
                                       "reference": FakeProject(measuring(100))}, tmp)
            self.assertEqual((result["verdict"], result["reasons"]), ("VALID", []))
            self.assertEqual(result["probes"]["hero_on_ground"]["start"], -500.0)
            self.assertEqual(result["probes"]["hero_on_ground"]["reference"], 100.0)
            self.assertEqual(result["probes"]["hero_on_ground"]["threshold"], -200.0)
            kept = json.loads((Path(tmp) / "out" / "probe-task.json").read_text(encoding="utf-8"))
            self.assertEqual(kept["verdict"], "VALID")
            self.assertTrue((Path(tmp) / "out" / "probe-task" / "start" / "look" / "probe.json").is_file())
            self.assertFalse((Path(tmp) / "scratch").exists(), "the scratch copies are deleted")

    def test_a_start_that_doesnt_build_or_already_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with({"kind": "build", "name": "editor_builds"}, probe())
            result = self.check(task, {"start": FakeProject(build_exit=6), "reference": FakeProject()}, tmp)
            self.assertEqual(result["reasons"], ["start doesn't build: the game as the task started didn't build "
                                                 "(exit 6)"])
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with({"kind": "build", "name": "editor_builds"}, probe(), seed=NO_FIX)
            result = self.check(task, {"start": FakeProject(measuring(10))}, tmp)
            self.assertEqual((result["verdict"], result["reasons"]),
                             ("INVALID", ["start already passes every required probe"]))

    def test_a_start_that_doesnt_build_by_design(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(milestones=[{"name": "builds", "checks": [{"kind": "build", "name": "editor_builds",
                                                                        "fails_at_start": True}]},
                                         {"name": "graded", "checks": [probe(needs=["editor_builds"])]}])
            start = FakeProject(measuring(-5), build_exit=6)
            result = self.check(task, {"start": start, "reference": FakeProject(measuring(5))}, tmp)
            self.assertEqual(result["verdict"], "VALID", result["reasons"])
            self.assertEqual(start.plays, [], "a start that doesn't build is never played")

    def test_an_unreadable_task_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = check.check_task(tmp, {"name": "x"}, b"{}", Path(tmp) / "s", Path(tmp) / "out",
                                      log=lambda *a: None)
            self.assertEqual(result["verdict"], "INVALID")
            self.assertTrue(result["reasons"][0].startswith("the task doesn't validate"))


class Plays(unittest.TestCase):
    def test_a_play_passes_the_probe_flags_and_the_queries_file(self):
        seen = {}

        def job(label, argv, cwd, timeout):
            seen["argv"] = [str(a) for a in argv]
            asked = [a for a in seen["argv"] if a.startswith("-TaskProbeQueries=")]
            seen["queries"] = json.loads(Path(asked[0].split("=", 1)[1]).read_text(encoding="utf-8")) if asked else None
            return unreal.Result(0, "", 1.0)

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Game.uproject").write_text("{}", encoding="utf-8")
            machine = unreal.Machine(Path(tmp) / "UE", None)
            machine.job = job
            project = unreal.Project(tmp, machine, "t")
            asked = probes.query_file(probes.plan(task_with(probe(measure={"probe": "grading",
                                                                           "field": "warmth"})))["look"])
            found = project.play(5, 0, 60, map="/Game/L?Scenario=1", queries=asked, args=["-AutoPlay"], every=0.25)
            self.assertEqual(seen["queries"], asked)
            self.assertNotIn("queries.json", found.files)
            argv = seen["argv"]
            self.assertTrue(argv[0].endswith("UnrealEditor.exe") and argv[2] == "/Game/L?Scenario=1")
            for flag in ("-game", "-RenderOffscreen", "-fps=30", "-TaskProbe", "-TaskProbeSeconds=5",
                         "-log=TaskProbePlay.log"):
                self.assertIn(flag, argv)
            self.assertEqual(argv[-2:], ["-TaskProbeEvery=0.25", "-AutoPlay"])
            project.play(5, 0, 60)
            self.assertIsNone(seen["queries"])
            self.assertFalse(any(a.startswith("-TaskProbeEvery") for a in seen["argv"]))

    def test_a_build_builds_unity_files_as_the_developers_checkout_does(self):
        seen = {}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Game.uproject").write_text("{}", encoding="utf-8")
            (Path(tmp) / "Source").mkdir()
            (Path(tmp) / "Source" / "GameEditor.Target.cs").write_text("", encoding="utf-8")
            machine = unreal.Machine(Path(tmp) / "UE", None)
            machine.job = lambda label, argv, cwd, timeout: seen.setdefault("argv", [str(a) for a in argv]) and \
                unreal.Result(0, "", 1.0)
            unreal.Project(tmp, machine, "t").build(60)
            self.assertEqual(seen["argv"][1:4], ["GameEditor", "Win64", "Development"])
            self.assertIn("-DisableAdaptiveUnity", seen["argv"])


class Cli(unittest.TestCase):
    def test_the_results_folder_is_git_ignored_in_the_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _, _, _ = make_game(tmp)
            cli.ignore_results(repo, repo / ".task-checks")
            self.assertEqual(subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", ".task-checks/a.json"])
                             .returncode, 0)
            self.assertEqual(git(repo, "status", "--porcelain"), b"", "no tracked file changed")
            exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
            cli.ignore_results(repo, repo / ".task-checks")
            self.assertEqual((repo / ".git" / "info" / "exclude").read_text(encoding="utf-8"), exclude, "once")

    def test_a_task_file_not_committed_yet_is_checked_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _, _, _ = make_game(tmp)
            path = Path(tmp) / "metro-runner-fix-x.json"
            path.write_text(json.dumps({**task_with(probe()), "name": "metro-runner-fix-x"}), encoding="utf-8")
            seen = []

            def fake(repo_, task, raw, scratch, out, **kw):
                seen.append(task["name"])
                return {"task": task["name"], "verdict": "VALID", "reasons": []}

            with mock.patch.object(check, "check_task", fake), \
                    mock.patch.object(unreal.gfroot, "check_free", lambda *a: 100.0), \
                    contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
                code = cli.main([str(repo), "--task", str(path), "--scratch", str(Path(tmp) / "s")])
            self.assertEqual((code, seen), (0, ["metro-runner-fix-x"]))
            self.assertEqual(out.getvalue(), "VALID   metro-runner-fix-x\n")

    def test_one_line_per_task(self):
        self.assertEqual(cli.line({"task": "a", "verdict": "VALID", "reasons": []}), "VALID   a")
        self.assertEqual(cli.line({"task": "b", "verdict": "INVALID", "reasons": ["x", "y"]}), "INVALID b: x; y")


if __name__ == "__main__":
    unittest.main()

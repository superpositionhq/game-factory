"""task-try.py's parts that need no Unreal and no harness: the brief, the command lines, the workspace, the transcript
readers and a run's score."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from unittest import mock

from helpers import FakeProject, checked, measuring, probe, task_with
from test_check import make_game

from task_check import trial, unreal


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


class Brief(unittest.TestCase):
    def test_the_brief_is_the_instruction_where_qa_plays_and_where_unreal_is(self):
        task = dict(task_with(probe()), play_map="/Game/Maps/L_Town?Scenario=2")
        text = trial.brief(task, "D:\\UE_5.7")
        self.assertTrue(text.startswith("Keep the hero on the ground."))
        self.assertIn("`/Game/Maps/L_Town?Scenario=2`", text)
        self.assertIn("`D:\\UE_5.7`", text)
        self.assertNotIn("hero_on_ground", text, "nothing of the grader's half")

    def test_the_task_limits_override_the_schemas_defaults(self):
        self.assertEqual(trial.limits_of(task_with(probe())), {"max_turns": 200, "max_minutes": 240})
        task = dict(task_with(probe()), limits={"max_turns": 400, "max_minutes": 480})
        self.assertEqual(trial.limits_of(task)["max_minutes"], 480)


class Harness(unittest.TestCase):
    def test_claude_runs_headless_with_its_turn_limit_and_no_hooks(self):
        argv = trial.agent_argv("claude", "claude.cmd", {"max_turns": 400}, "s.json", model="opus")
        self.assertEqual(argv[:2], ["claude.cmd", "-p"])
        self.assertIn("400", argv)
        self.assertEqual(argv[argv.index("--settings") + 1], "s.json")
        self.assertEqual(argv[argv.index("--model") + 1], "opus")

    def test_codex_runs_exec_with_full_access_reading_the_prompt_from_stdin(self):
        argv = trial.agent_argv("codex", "codex.cmd", {"max_turns": 400}, "s.json", extra=["-c", "x=1"])
        self.assertEqual(argv[:2], ["codex.cmd", "exec"])
        self.assertIn("danger-full-access", argv)
        self.assertEqual(argv[-3:], ["-c", "x=1", "-"])

    def test_an_unknown_agent_is_refused(self):
        with self.assertRaises(ValueError):
            trial.agent_argv("cursor", "x", {"max_turns": 1}, "s.json")

    def test_the_agent_gets_the_prompt_on_stdin_and_recording_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = ("import os,sys; print(sys.stdin.read().upper()); print(os.environ.get('GF_NO_RECORDING'))")
            out = Path(tmp) / "t.jsonl"
            ran = trial.run_agent([sys.executable, "-c", script], tmp, "fix it", out, 1)
            self.assertEqual(ran["exit_code"], 0)
            self.assertFalse(ran["timed_out"])
            self.assertEqual(out.read_text().split(), ["FIX", "IT", "1"])


class Transcript(unittest.TestCase):
    def test_usage_reads_claudes_result_and_counts_codexs_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "t.jsonl"
            f.write_text("not json\n" + json.dumps({"type": "result", "num_turns": 37, "total_cost_usd": 4.2}) + "\n")
            self.assertEqual(trial.usage("claude", f), {"turns": 37, "usd": 4.2})
            f.write_text("\n".join(json.dumps({"type": t}) for t in ("turn.started", "turn.completed",
                                                                       "turn.completed")))
            self.assertEqual(trial.usage("codex", f), {"turns": 2, "usd": None})
            self.assertEqual(trial.usage("codex", Path(tmp) / "none"), {"turns": None, "usd": None})

    def test_a_transcript_naming_the_game_repo_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "t.jsonl"
            f.write_text(json.dumps({"cmd": "git -C C:\\Work\\games\\stealth log"}))
            self.assertEqual(trial.peeked(f, ["C:\\Work\\games\\stealth", "C:\\Work\\tasks\\stealth"]),
                             ["C:\\Work\\games\\stealth"])
            f.write_text(json.dumps({"cmd": "cat c:/work/tasks/stealth/Tasks/x.json"}))
            self.assertEqual(trial.peeked(f, ["C:\\Work\\games\\stealth", "C:\\Work\\tasks\\stealth"]),
                             ["C:\\Work\\tasks\\stealth"])

    def test_a_workspace_inside_the_root_or_the_repo_is_not_outside(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(trial.outside(os.path.join(tmp, "a", "b"), [tmp]))
            self.assertTrue(trial.outside(tmp + "-other", [tmp]))


class Score(unittest.TestCase):
    def test_a_score_is_the_weighted_share_as_the_cloud_scores_it(self):
        grade = {"checks": [dict(checked("editor_builds", "build", True), required=True, group="builds", weight=0),
                            dict(checked("hud", "probe", False), required=True, group="fixed", weight=3),
                            dict(checked("camera", "probe", False), required=True, group="fixed", weight=1),
                            dict(checked("runs", "probe", True), required=True, group="still_works", weight=0)]}
        self.assertEqual(trial.score(None, grade)["score"], 0.0, "a no-op scores nothing")
        grade["checks"][1]["passed"] = True
        self.assertEqual(trial.score(None, grade)["score"], 0.75)

    def test_solved_only_when_every_required_check_passes(self):
        grade = {"checks": [dict(checked("editor_builds", "build", True), required=True, group="builds"),
                            dict(checked("hud", "probe", True), required=True, group="fixed"),
                            dict(checked("camera", "probe", False), required=True, group="fixed"),
                            dict(checked("taste", "judge", False), required=False, group="quality")]}
        self.assertEqual(trial.score(None, grade), {"solved": False, "score": 0.667, "required_passed": 2, "required": 3,
                                                    "milestones": {"builds": True, "fixed": False}})
        grade["checks"][2]["passed"] = True
        self.assertTrue(trial.score(None, grade)["solved"])


class Workspace(unittest.TestCase):
    def test_the_workspace_is_the_start_alone_in_a_fresh_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "game"
            repo.mkdir()
            git(repo, "init", "-q", "-b", "main")
            (repo / "Source").mkdir()
            (repo / "Source" / "Hero.cpp").write_text("broken")
            (repo / "Tasks").mkdir()
            (repo / "Tasks" / "t.json").write_text("{}")
            git(repo, "add", "-A")
            git(repo, "-c", "user.name=a", "-c", "user.email=a@b", "commit", "-q", "-m", "start")
            start = git(repo, "rev-parse", "HEAD")
            (repo / "Source" / "Hero.cpp").write_text("fixed")
            git(repo, "-c", "user.name=a", "-c", "user.email=a@b", "commit", "-qam", "the fix")
            dest = Path(tmp) / "ws" / "game"
            trial.workspace(repo, start, dest)
            self.assertEqual((dest / "Source" / "Hero.cpp").read_text(), "broken")
            self.assertFalse((dest / "Tasks").exists(), "no tasks reach the agent")
            self.assertEqual(git(dest, "rev-list", "--count", "HEAD"), "1", "one commit, no history")
            self.assertEqual(git(dest, "status", "--porcelain"), "")


class Whole(unittest.TestCase):
    def test_runs_graded_against_the_start_and_the_reference(self):
        """Two runs: the first leaves the game as it started, the second fixes it; Unreal and the harness faked."""
        with tempfile.TemporaryDirectory() as tmp:
            repo, start, fix, _ = make_game(tmp)
            task = task_with({"kind": "build", "name": "editor_builds"},
                             probe(expect={"op": ">=", "calibrate": 0.5}, needs=["editor_builds"]))
            task["seed"] = {**task["seed"], "commit": start, "reference": fix}
            projects = {"start": FakeProject(measuring(-500)), "reference": FakeProject(measuring(100)),
                        "run1": FakeProject(measuring(-500)), "run2": FakeProject(measuring(90))}

            def project(folder, machine, label):
                folder = Path(folder)
                return projects[folder.name if folder.name in projects else folder.parent.name]

            def agent(argv, cwd, prompt, transcript, minutes):
                Path(transcript).write_text(json.dumps({"type": "result", "num_turns": 12, "total_cost_usd": 1.5}))
                return {"exit_code": 0, "seconds": 60.0, "timed_out": False}

            with mock.patch.object(unreal, "Project", project), mock.patch.object(trial, "run_agent", agent), \
                    mock.patch.object(unreal.Machine, "for_project",
                                      classmethod(lambda cls, p, d=False: cls(Path(p), None))):
                result = trial.try_task(repo, task, json.dumps(task).encode(), Path(tmp) / "scratch",
                                        Path(tmp) / "out", "claude", "claude", runs=2, places=[repo],
                                        log=lambda *a: None)
            self.assertEqual((result["status"], result["solved"]), ("DONE", 1))
            self.assertEqual([r["solved"] for r in result["runs"]], [False, True])
            self.assertEqual(result["runs"][1]["turns"], 12)
            self.assertEqual(result["runs"][0]["milestones"], {"graded": False})
            self.assertTrue((Path(tmp) / "out" / "probe-task" / "brief.md").is_file())
            self.assertFalse((Path(tmp) / "scratch").exists(), "the workspaces are deleted")
            self.assertIn("1/2 solved", trial.line(result))

    def test_a_task_without_a_reference_is_not_tried(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = task_with(probe(), seed={"game": "metro-runner", "commit": "a" * 40, "kind": "feature"})
            result = trial.try_task(tmp, task, b"{}", Path(tmp) / "s", Path(tmp) / "out", "codex", "codex",
                                    log=lambda *a: None)
            self.assertEqual(result["status"], "ERROR")
            self.assertIn("seed.reference", result["reasons"][0])


class LongEnough(unittest.TestCase):
    def test_the_line_says_when_the_longest_run_is_too_short(self):
        run = {"required_passed": 2, "required": 3, "peeked": [], "seconds": 24.9 * 60}
        result = {"status": "DONE", "task": "t", "solved": 0, "runs": [run]}
        self.assertIn("longest run 24.9 min: under the 25-minute guide (a guide, not a requirement)", trial.line(result))
        run["seconds"] = 25 * 60
        self.assertNotIn("25-minute guide", trial.line(result))

    def test_a_run_stopped_by_its_time_limit_says_nothing_about_length(self):
        run = {"required_passed": 2, "required": 3, "peeked": [], "seconds": 10 * 60, "timed_out": True}
        result = {"status": "DONE", "task": "t", "solved": 0, "runs": [run]}
        self.assertNotIn("25-minute guide", trial.line(result))


if __name__ == "__main__":
    unittest.main()

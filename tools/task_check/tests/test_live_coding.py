"""Live Coding on this machine: a session anywhere stops every other build, so the checker switches it off where it can
and retries a build it stopped."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401  (puts the tools folder on the path)

from task_check import seeds, unreal

BLOCKED = "ERROR: " + unreal.LIVE_CODING_BLOCKED + ". Exit the editor and game"


class FakeMachine:
    """Answers each job from a list of (exit code, output), repeating the last."""

    def __init__(self, answers):
        self.answers, self.argvs = list(answers), []

    def build_bat(self):
        return Path("Build.bat")

    def job(self, label, argv, cwd, timeout):
        self.argvs.append([str(a) for a in argv])
        code, output = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return unreal.Result(code, output, 1.0)


def building(answers):
    """(the build's result, its project, the machine, the waits) for those answers."""
    machine, waits = FakeMachine(answers), []
    project = unreal.Project("scratch", machine, "game start")
    with mock.patch.object(project, "uproject", return_value=Path("Game.uproject")), \
            mock.patch.object(unreal.seeds, "editor_target", return_value="GameEditor"), \
            contextlib.redirect_stderr(io.StringIO()):
        found = project.build(60, sleep=waits.append)
    return found, project, machine, waits


class Retries(unittest.TestCase):
    def test_a_clean_build_runs_once_and_skips_the_guard(self):
        found, project, machine, waits = building([(0, "done")])
        self.assertEqual((found.exit_code, project.build_retries, waits), (0, 0, []))
        self.assertEqual(len(machine.argvs), 1)
        self.assertIn(unreal.NO_LIVE_CODING_GUARD, machine.argvs[0])

    def test_a_blocked_build_waits_and_tries_again_and_isnt_a_failure(self):
        found, project, machine, waits = building([(6, BLOCKED), (6, BLOCKED), (0, "done")])
        self.assertEqual(found.exit_code, 0)
        self.assertEqual(project.build_retries, 2)
        self.assertEqual(waits, [unreal.LIVE_CODING_RETRY_SECONDS] * 2)
        self.assertEqual(len(machine.argvs), 3)
        self.assertIn("retried 2 time(s)", found.output)

    def test_any_other_failure_counts_at_once(self):
        found, project, machine, waits = building([(6, "error C2065: undeclared"), (0, "done")])
        self.assertEqual((found.exit_code, project.build_retries, waits), (6, 0, []))
        self.assertEqual(len(machine.argvs), 1)

    def test_a_failure_after_a_retry_counts(self):
        found, project, _, _ = building([(6, BLOCKED), (6, "error C2065: undeclared")])
        self.assertEqual((found.exit_code, project.build_retries), (6, 1))
        self.assertIn("C2065", found.output)

    def test_it_gives_up_after_the_limit(self):
        found, project, _, waits = building([(6, BLOCKED)])
        self.assertEqual(found.exit_code, 6)
        self.assertEqual(sum(waits), unreal.LIVE_CODING_RETRY_LIMIT)
        self.assertEqual(project.build_retries, unreal.LIVE_CODING_RETRY_LIMIT // unreal.LIVE_CODING_RETRY_SECONDS)


class Switches(unittest.TestCase):
    def test_settings_written_for_an_agents_editor(self):
        with tempfile.TemporaryDirectory() as folder:
            path = seeds.no_live_coding(folder)
            self.assertEqual(path.relative_to(folder).as_posix(), "Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini")
            self.assertIn("[/Script/LiveCoding.LiveCodingSettings]\nbEnabled=False", path.read_text(encoding="utf-8"))

    def test_settings_keep_what_is_there(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Saved" / "Config" / "WindowsEditor" / "EditorPerProjectUserSettings.ini"
            path.parent.mkdir(parents=True)
            path.write_text("[Other]\nA=1\n", encoding="utf-8")
            seeds.no_live_coding(folder)
            self.assertIn("A=1", path.read_text(encoding="utf-8"))
            self.assertIn("bEnabled=False", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

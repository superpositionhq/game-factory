"""A mobile game's plays in the task check (docs/task-probes.md 1.1): a copy whose game has a Platform.json is played
with the engine's mobile renderer at the phone's size; a copy without one is a desktop game's, launched as always."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401  (puts the tools folder on the path)

from task_check import tasks, unreal


class FakeMachine:
    def __init__(self):
        self.argvs = []

    def editor(self):
        return Path("UnrealEditor.exe")

    def job(self, label, argv, cwd, timeout):
        self.argvs.append([str(a) for a in argv])
        return unreal.Result(0, "", 1.0)


def launched(platform=None):
    """The argument list of one play of a copy whose Platform.json holds `platform` (None: no such file)."""
    with tempfile.TemporaryDirectory() as tmp:
        if platform is not None:
            (Path(tmp) / "Platform.json").write_text(platform if isinstance(platform, str) else json.dumps(platform))
        machine = FakeMachine()
        project = unreal.Project(tmp, machine, "game start")
        with mock.patch.object(project, "uproject", return_value=Path("Game.uproject")):
            project.play(5, 2, 60)
        out = str(Path(tmp) / "Saved" / "TaskProbe" / "play")
        return [a.replace(out, "<out>") for a in machine.argvs[0]]


class MobilePlay(unittest.TestCase):
    def test_a_desktop_games_play_is_launched_as_before(self):
        self.assertEqual(launched(), [
            "UnrealEditor.exe", "Game.uproject", "-game", "-RenderOffscreen", "-ResX=960", "-ResY=540", "-unattended",
            "-LiveCoding=false", "-nosound", "-nosplash", "-benchmark", "-fps=30", "-TaskProbe", "-TaskProbeOut=<out>",
            "-TaskProbeSeconds=5", "-TaskProbeShots=2", "-log=TaskProbePlay.log"])

    def test_a_mobile_games_play_gets_the_mobile_renderer_at_the_phones_size(self):
        portrait = launched({"platform": "mobile", "orientation": "portrait"})
        self.assertEqual(portrait[2:8], ["-game", "-RenderOffscreen", "-FeatureLevelES31", "-ForceRes", "-ResX=1080",
                                         "-ResY=1920"])
        landscape = launched({"platform": "mobile", "orientation": "landscape"})
        self.assertEqual(landscape[4:8], ["-FeatureLevelES31", "-ForceRes", "-ResX=1920", "-ResY=1080"])
        self.assertEqual(portrait[8:], launched()[6:], "everything after the size is a desktop play's")

    def test_a_platform_file_that_says_neither_is_never_read_as_desktop(self):
        read = tasks.validator().read_platform
        for bad in ("not json", {"platform": "mobile"}, {"platform": "desktop", "orientation": "portrait"},
                    {"platform": "mobile", "orientation": "sideways"}, {"platform": "mobile", "orientation": "portrait", "x": 1},
                    ["mobile", "portrait"]):
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "Platform.json").write_text(bad if isinstance(bad, str) else json.dumps(bad))
                with self.assertRaises(ValueError, msg=str(bad)):
                    read(tmp)
                with self.assertRaises(ValueError, msg=str(bad)):
                    launched(bad)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(read(tmp))
            (Path(tmp) / "Platform.json").write_text('{"platform": "mobile", "orientation": "landscape"}')
            self.assertEqual(read(tmp), "landscape")


if __name__ == "__main__":
    unittest.main()

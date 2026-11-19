"""The `files` measure, as the Lab's game grader reads it since 1.24.0 (docs/task-probes.md 2.23): what the game wrote
under Saved during a task play, listed when the play ends; a {saved} folder in a play's args is the copy's own Saved."""

import io
import os
import tempfile
import time
import unittest
from pathlib import Path

from task_check import probes, unreal

TELEMETRY = (b'{"event":"header"}\n{"event":"fall","t":3}\n{"event":"restart"}\n'
             b'{"event":"scenario_end","result":"won","score":120.5}\n')
SAVE = (b"\x00\x01GVAS\x00\x05\x00\x00\x00Hour 3: ash pan 40% full\x00\xfe\xff\xff\xff"
        + "Uhr 4: Aschekasten 55 % voll — gut".encode("utf-16-le") + b"\x00\x00")


def measure(**kw):
    return {"probe": "files", "match": None, "agg": None, "size": None, **kw}


def png(flat):
    from PIL import Image

    img = Image.new("RGB", (64, 48), (10, 20, 30))
    if not flat:
        img.putpixel((3, 3), (200, 0, 0))
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


class FilesMeasure(unittest.TestCase):
    def listed(self, written, older=()):
        """unreal._game_files over a project whose Saved holds `written` {path: bytes} written after the play began
        and `older` paths written before it."""
        with tempfile.TemporaryDirectory() as root:
            project = Path(root)
            for path in older:
                (project / path).parent.mkdir(parents=True, exist_ok=True)
                (project / path).write_bytes(b"old")
                os.utime(project / path, (1, 1))
            for path, data in written.items():
                (project / path).parent.mkdir(parents=True, exist_ok=True)
                (project / path).write_bytes(data)
            began = time.time() - 60
            return unreal._game_files(project, ["Saved/**"], began)

    def test_telemetry_lines_and_score(self):
        files = self.listed({"Saved/AutoPlay/1/telemetry.jsonl": TELEMETRY, "Saved/Logs/x.log": b"fall"},
                            older=["Saved/AutoPlay/0/telemetry.jsonl"])
        glob = {"glob": "Saved/AutoPlay/*/telemetry.jsonl"}
        self.assertEqual(probes.files_value(measure(select=glob, field="count"), files), (2.0, None))
        self.assertEqual(probes.files_value(measure(select=glob, field="written"), files), (1.0, None))
        self.assertEqual(probes.files_value(measure(select=glob, field="lines", match='"event":"(fall|restart)"'),
                                            files), (2.0, None))
        score = measure(select=glob, field="number", match=r'"scenario_end".*"score":(-?[0-9.]+)')
        self.assertEqual(probes.files_value(score, files), (120.5, None))
        self.assertNotIn("Saved/Logs/x.log", [f["path"] for f in files])

    def test_save_text_and_an_untouched_save(self):
        files = self.listed({"Saved/SaveGames/Slot.sav": SAVE}, older=["Saved/SaveGames/Campaign.sav"])
        self.assertEqual(probes.files_value(measure(select={"glob": "Saved/SaveGames/Slot.sav"}, field="lines",
                                                    match=r"ash pan \d+% full"), files), (1.0, None))
        self.assertEqual(probes.files_value(measure(select={"glob": "Saved/SaveGames/Slot.sav"}, field="lines",
                                                    match="Aschekasten 55 % voll —"), files), (1.0, None))
        self.assertEqual(probes.files_value(measure(select={"glob": "Saved/SaveGames/Campaign.sav"}, field="written"),
                                            files), (0.0, None))

    def test_pictures(self):
        files = self.listed({"Saved/Plates/a.png": png(False), "Saved/Plates/b.png": png(True)})
        self.assertEqual(probes.files_value(measure(select={"glob": "Saved/Plates/*.png"}, field="pictures"), files),
                         (1.0, None))

    def test_glob(self):
        self.assertTrue(probes.glob_match("Saved/**/*.png", "Saved/x.png"))
        self.assertFalse(probes.glob_match("Saved/AutoPlay/*/t.jsonl", "Saved/AutoPlay/a/b/t.jsonl"))


if __name__ == "__main__":
    unittest.main()

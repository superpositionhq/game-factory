"""returned-tasks.py: a person's open tasks, joined from the assignments list and the tasks list by Task ID."""

import contextlib
import csv
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("returned_tasks", TOOLS / "returned-tasks.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

ASSIGNMENTS = [
    ["Task ID", "Game", "Task name", "Owner", "Status", "Lab profile"],
    ["id-1", "Hive Ascent", "hive-fix-door", "Recep Şen", "Assigned", "x"],
    ["id-2", "Hive Ascent", "hive-feat-hud", "recep şen ", "In progress", "x"],
    ["id-3", "Gravity Switch", "gravity-map", "Recep Şen", "Submitted", "x"],
    ["id-4", "Old Game", "old-task", "Recep Şen", "Assigned", "x"],
    ["id-5", "Tally Room", "tally-title", "Jane Smith", "Assigned", "x"],
    ["id-6", "Tally Room", "tally-credits", "", "Unassigned", ""],
]
TASKS = [
    ["List", "Contractor", "Email", "Game", "Task", "Task name", "Task ID", "Version", "Reason", "What is wrong",
     "Detail (internal)", "Game download link", "Tasks download link", "Links expire"],
    ["OTHERS", "Builder One", "b1@example.com", "Hive Ascent", "Fix the door", "hive-fix-door", "id-1", "4", "R",
     "Your reference solution fails one of the task's own checks.", "Check door_opens reads 0,\non the reference.",
     "https://example.com/hive.zip", "https://example.com/hive-tasks.zip", "2026-11-20 02:28 ET"],
    ["OTHERS", "Builder One", "b1@example.com", "Hive Ascent", "Add a HUD", "hive-feat-hud", "id-2", "2", "R",
     "The instruction asks for things the checks do not test.", "", "https://example.com/hive.zip",
     "https://example.com/hive-tasks.zip", "2026-11-20 02:28 ET"],
    ["OTHERS", "Builder Two", "b2@example.com", "Gravity Switch", "Map", "gravity-map", "id-3", "3", "R", "W", "D",
     "https://example.com/g.zip", "https://example.com/g-tasks.zip", "2026-11-20 02:28 ET"],
    ["OTHERS", "Builder Two", "b2@example.com", "Tally Room", "Title", "tally-title", "id-5", "1", "R", "W", "D",
     "https://example.com/t.zip", "https://example.com/t-tasks.zip", "2026-11-20 02:28 ET"],
]


def write(path, rows, bom=False):
    with open(path, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as handle:
        csv.writer(handle).writerows(rows)


class ReturnedTasks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.assignments = self.folder / "Unreal task fixes - assignments - Assignments.csv"
        self.tasks = self.folder / "Unreal tasks to fix - links.csv"
        write(self.assignments, ASSIGNMENTS, bom=True)
        write(self.tasks, TASKS)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rt.main(["--downloads", str(self.folder), *args])
        return out.getvalue()

    def test_open_tasks_are_joined_by_task_id(self):
        found = rt.collect(self.assignments, self.tasks, "Recep Şen")
        self.assertEqual([task["Task name"] for task in found["open"]], ["hive-fix-door", "hive-feat-hud"])
        first = found["open"][0]
        self.assertEqual(first["Detail"], "Check door_opens reads 0,\non the reference.")
        self.assertEqual(first["Game download link"], "https://example.com/hive.zip")
        self.assertEqual(first["Version"], "4")
        self.assertNotIn("Contractor", first)  # who built a game is never passed on
        self.assertNotIn("Email", first)
        self.assertEqual(found["closed"], {"Submitted": 1})
        self.assertEqual([task["Task name"] for task in found["gone"]], ["old-task"])

    def test_the_summary_and_one_game_in_full(self):
        summary = self.run_tool("--owner", "recep şen")
        self.assertIn("2 open task(s) in 1 game(s)", summary)
        self.assertIn("Hive Ascent: 2 task(s)  [Assigned, In progress]", summary)
        self.assertIn("no longer needed", summary)
        self.assertIn("Left out by status: 1 Submitted", summary)
        self.assertNotIn("example.com", summary)
        game = self.run_tool("--owner", "Recep Şen", "--game", "hive ascent")
        self.assertIn("Game download link: https://example.com/hive.zip", game)
        self.assertIn("Detail: none given", game)
        self.assertNotIn("Builder One", game)

    def test_the_two_files_are_told_apart_by_their_columns_and_the_newest_wins(self):
        os.utime(self.tasks, (1, 1))
        newer = self.folder / "renamed (1).csv"
        write(newer, [TASKS[0], TASKS[1]])
        write(self.folder / "something else.csv", [["a", "b"], ["1", "2"]])
        found = json.loads(self.run_tool("--owner", "Recep Şen", "--json"))
        self.assertEqual(Path(found["tasks"]).name, "renamed (1).csv")
        self.assertEqual([task["Task name"] for task in found["open"]], ["hive-fix-door"])
        self.assertEqual(len(found["gone"]), 2)

    def test_an_unknown_owner_lists_the_owners(self):
        with self.assertRaises(SystemExit) as refused:
            rt.collect(self.assignments, self.tasks, "Nobody")
        self.assertIn("Jane Smith", str(refused.exception))

    def test_a_missing_file_says_how_to_get_it(self):
        self.tasks.unlink()
        with self.assertRaises(SystemExit) as refused:
            self.run_tool("--owner", "Recep Şen")
        self.assertIn("the tasks list not found", str(refused.exception))

    def test_out_writes_the_open_tasks(self):
        target = self.folder / "mine.csv"
        self.run_tool("--owner", "Recep Şen", "--out", str(target))
        with open(target, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["Task ID"] for row in rows], ["id-1", "id-2"])
        self.assertEqual(list(rows[0]), rt.SHIPPED)


if __name__ == "__main__":
    unittest.main()

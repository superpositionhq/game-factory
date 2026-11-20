"""ue-replay ledger.py, as_claude: Antigravity's rows read as Claude Code's where their effect is known, and every
other row left as it is."""

import importlib.util
import sys
import unittest
from pathlib import Path

REPLAY = Path(__file__).resolve().parents[1] / "ue-replay"
sys.path.insert(0, str(REPLAY))
_spec = importlib.util.spec_from_file_location("ue_replay_ledger", REPLAY / "ledger.py")
ledger = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ledger)


def row(tool, inp, agent="antigravity"):
    return {"agent": agent, "event": "PostToolUse", "tool": tool, "input": inp, "time": "2026-11-20T10:00:00.000+00:00"}


class AsClaude(unittest.TestCase):
    def test_run_command_is_a_bash_command(self):
        a = ledger.as_claude(row("run_command", {"CommandLine": "ue-heavy.ps1 Scripts/build.py", "Cwd": "C:/Work"}))
        self.assertEqual(a["tool"], "Bash")
        self.assertEqual(a["input"]["command"], "ue-heavy.ps1 Scripts/build.py")
        self.assertEqual(a["input"]["Cwd"], "C:/Work", "the other arguments stay")

    def test_write_file_is_a_write_and_edit_file_an_edit(self):
        w = ledger.as_claude(row("write_file", {"Path": "C:/Work/games/g/Scripts/a.py", "Content": "x = 1\n"}))
        self.assertEqual((w["tool"], w["input"]), ("Write", {"file_path": "C:/Work/games/g/Scripts/a.py",
                                                            "content": "x = 1\n"}))
        e = ledger.as_claude(row("edit_file", {"Path": "C:/Work/games/g/Scripts/a.py", "Target": "1",
                                               "Replacement": "2", "AllowMultiple": True}))
        self.assertEqual((e["tool"], e["input"]), ("Edit", {"file_path": "C:/Work/games/g/Scripts/a.py",
                                                           "old_string": "1", "new_string": "2", "replace_all": True}))

    def test_an_append_is_an_append(self):
        a = ledger.as_claude(row("write_file", {"Path": "C:/Work/games/g/a.txt", "Content": "more", "Append": True}))
        self.assertEqual((a["tool"], a["input"]), ("Append", {"file_path": "C:/Work/games/g/a.txt", "content": "more"}))

    def test_another_file_tool_leaves_the_file_unknown(self):
        r = ledger.as_claude(row("replace_file_content", {"TargetFile": "C:/Work/games/g/b.py",
                                                          "ReplacementChunks": []}))
        self.assertEqual((r["tool"], r["input"]["file_path"], r["input"]["tool"]),
                         ("Unreplayed", "C:/Work/games/g/b.py", "replace_file_content"))

    def test_reads_and_other_agents_rows_are_unchanged(self):
        for a in (row("read_file", {"Path": "C:/Work/games/g/a.txt"}),
                  row("run_command", {"CommandLine": "dir"}, "codex"),
                  row("Write", {"file_path": "x", "content": "y"}, "claude")):
            self.assertIs(ledger.as_claude(a), a)


if __name__ == "__main__":
    unittest.main()

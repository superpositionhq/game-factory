"""ue-replay verify.py, files criterion: a tracked file is compared wherever it lives, under an ignored directory
(Build/, Binaries/, ...) too; those directories only keep untracked build output out of the extra files."""

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPLAY = Path(__file__).resolve().parents[1] / "ue-replay"
sys.path.insert(0, str(REPLAY))
_spec = importlib.util.spec_from_file_location("ue_replay_verify", REPLAY / "verify.py")
verify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify)

ICON = "Build/Windows/Application.ico"


def git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                           "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if done.returncode:
        raise AssertionError(f"git {' '.join(args)}: {done.stderr}")
    return done.stdout.strip()


def write(root, rel, data):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class FilesUnderIgnoredDirs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self._tmp.name) / "proj"
        self.proj.mkdir()
        git(self.proj, "init", "-q")
        write(self.proj, "Game.uproject", b"{}\n")
        write(self.proj, "Source/Game/Game.cpp", b"int x;\n")
        write(self.proj, ICON, b"\x00\x00\x01\x00icon-bytes")
        payload = b"large binary payload"
        oid = hashlib.sha256(payload).hexdigest()
        write(self.proj, "Build/Android/big.bin",
              f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {len(payload)}\n".encode())
        git(self.proj, "add", "-A", "-f")
        git(self.proj, "commit", "-q", "-m", "final")
        self.final = git(self.proj, "rev-parse", "HEAD")
        write(self.proj, "Build/Android/big.bin", payload)   # the replay project holds the LFS object's bytes
        self.ctx = types.SimpleNamespace(proj=str(self.proj))

    def tearDown(self):
        self._tmp.cleanup()

    def run_files(self):
        return verify.verify_files(self.ctx, self.final)

    def test_tracked_file_under_ignored_dir_identical_passes(self):
        res = self.run_files()
        self.assertEqual(res["missing"], [])
        self.assertEqual(res["differs"], [])
        self.assertEqual(res["extra"], [])
        self.assertEqual(res["other"].get("identical"), 4)

    def test_tracked_file_under_ignored_dir_absent_is_missing(self):
        (self.proj / ICON).unlink()
        res = self.run_files()
        self.assertEqual(res["missing"], [ICON])
        self.assertEqual(res["differs"], [])

    def test_tracked_file_under_ignored_dir_different_bytes_differs(self):
        write(self.proj, ICON, b"other bytes")
        write(self.proj, "Build/Android/big.bin", b"other payload")
        res = self.run_files()
        self.assertEqual(sorted(res["differs"]), ["Build/Android/big.bin", ICON])
        self.assertEqual(res["missing"], [])

    def test_untracked_files_under_ignored_dirs_are_not_extra(self):
        write(self.proj, "Build/Windows/Game.exe", b"exe")
        write(self.proj, "Binaries/Win64/Game.dll", b"dll")
        write(self.proj, "Intermediate/Build/x.obj", b"obj")
        write(self.proj, "Saved/Logs/Game.log", b"log")
        res = self.run_files()
        self.assertEqual(res["extra"], [])
        self.assertEqual(res["missing"], [])
        self.assertEqual(res["differs"], [])

    def test_untracked_file_elsewhere_is_still_extra(self):
        write(self.proj, "Source/Game/Stray.cpp", b"int y;\n")
        self.assertEqual(self.run_files()["extra"], ["Source/Game/Stray.cpp"])


if __name__ == "__main__":
    unittest.main()

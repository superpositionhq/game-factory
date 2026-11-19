"""pack-return.py: the zip a fixed game is handed back in holds only what the fix added, and applies to the delivery."""

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("pack_return", TOOLS / "pack-return.py")
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
                           "-c", "commit.gpgsign=false", *args], capture_output=True, text=True)
    if done.returncode:
        raise AssertionError(f"git {' '.join(args)}: {done.stderr}")
    return done.stdout.strip()


def commit(repo, name, text, message):
    path = Path(repo) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text if isinstance(text, bytes) else text.encode())
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def pointer(payload):
    oid = hashlib.sha256(payload).hexdigest()
    return oid, f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {len(payload)}\n".encode()


class PackReturn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        source = root / "source"
        source.mkdir()
        git(source, "init", "-q", "-b", "main")
        commit(source, ".gitignore", ".task-checks/\n", "ignore")
        commit(source, "Source/Game.cpp", "int a;\n", "game")
        git(source, "branch", "starts/fix-door")
        self.delivery = root / "delivery.bundle"
        git(source, "bundle", "create", str(self.delivery), "main", "starts/fix-door")
        self.repo = root / "the-game"
        subprocess.run(["git", "clone", "-q", str(self.delivery), str(self.repo)], check=True, capture_output=True)
        git(self.repo, "branch", "starts/fix-door", "origin/starts/fix-door")
        self.tasks = root / "the-game-tasks"
        git(self.repo, "worktree", "add", "-q", "--detach", str(self.tasks))
        git(self.tasks, "checkout", "-q", "--orphan", "tasks")
        git(self.tasks, "rm", "-rfq", ".")
        commit(self.tasks, "Tasks/fix-door.json", "{}\n", "tasks")
        self.out = root / "returns"

    def tearDown(self):
        self.tmp.cleanup()

    def fix(self):
        payload = b"new asset bytes"
        oid, text = pointer(payload)
        store = self.repo / ".git" / "lfs" / "objects" / oid[:2] / oid[2:4]
        store.mkdir(parents=True)
        (store / oid).write_bytes(payload)
        head = commit(self.repo, "Content/Door.uasset", text, "fix the door")
        git(self.repo, "branch", "-f", "starts/fix-door", "HEAD~1")
        return oid, head

    def result(self, task, verdict):
        folder = self.repo / ".task-checks"
        folder.mkdir(exist_ok=True)
        (folder / f"{task}.json").write_text(json.dumps({"verdict": verdict}), encoding="utf-8")

    def test_zip_holds_only_the_new_work_and_applies_to_the_delivery(self):
        oid, head = self.fix()
        self.result("fix-door", "VALID")
        target, summary = pr.pack(self.repo, self.out, ["fix-door"], now="20261119-1200")
        self.assertEqual(target.name, "the-game-return-20261119-1200.zip")
        with zipfile.ZipFile(target) as archive:
            names = set(archive.namelist())
            self.assertEqual(names, {
                "the-game/the-game.bundle", "the-game/return.json", "the-game/task-checks/fix-door.json",
                f"the-game/lfs/objects/{oid[:2]}/{oid[2:4]}/{oid}"})
            shipped = json.loads(archive.read("the-game/return.json"))
            archive.extract("the-game/the-game.bundle", self.tmp.name)
        self.assertEqual(shipped["format"], "game-return/1")
        self.assertEqual(shipped["branches"]["main"], head)
        self.assertEqual(shipped["changed_branches"], ["main", "tasks"])
        self.assertEqual(shipped["task_checks"], {"fix-door": "VALID"})
        self.assertEqual(summary["lfs_objects"], 1)
        # The bundle is only the new commits, so it applies to a copy of what was delivered.
        ours = Path(self.tmp.name) / "ours"
        subprocess.run(["git", "clone", "-q", str(self.delivery), str(ours)], check=True, capture_output=True)
        git(ours, "fetch", "-q", str(Path(self.tmp.name) / "the-game" / "the-game.bundle"),
            "refs/heads/main:refs/heads/returned-main", "refs/heads/tasks:refs/heads/returned-tasks")
        self.assertEqual(git(ours, "rev-parse", "returned-main"), head)
        self.assertEqual(git(ours, "show", "returned-tasks:Tasks/fix-door.json"), "{}")

    def test_uncommitted_changes_are_refused(self):
        self.fix()
        (self.tasks / "Tasks" / "fix-door.json").write_text("{\"a\": 1}\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as refused:
            pr.pack(self.repo, self.out)
        self.assertIn("uncommitted changes", str(refused.exception))

    def test_a_named_task_must_be_valid(self):
        self.fix()
        self.result("fix-door", "INVALID")
        with self.assertRaises(SystemExit) as refused:
            pr.pack(self.repo, self.out, ["fix-door"])
        self.assertIn("not VALID", str(refused.exception))
        target, summary = pr.pack(self.repo, self.out)  # unnamed, it is reported and still packed
        self.assertEqual(summary["task_checks"], {"fix-door": "INVALID"})

    def test_a_missing_lfs_object_is_refused(self):
        oid, _ = self.fix()
        (self.repo / ".git" / "lfs" / "objects" / oid[:2] / oid[2:4] / oid).unlink()
        with self.assertRaises(SystemExit) as refused:
            pr.pack(self.repo, self.out)
        self.assertIn("LFS object", str(refused.exception))

    def test_a_repo_with_no_origin_is_packed_whole(self):
        self.fix()
        git(self.repo, "remote", "remove", "origin")
        target, summary = pr.pack(self.repo, self.out)
        self.assertEqual(summary["restored_at"], {})
        self.assertEqual(summary["changed_branches"], ["main", "starts/fix-door", "tasks"])


if __name__ == "__main__":
    unittest.main()

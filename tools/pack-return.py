#!/usr/bin/env python3
"""Pack a returned game's fixes into one zip to hand back (write-tasks skill, "Handing a fixed game back").

    python tools/pack-return.py <game repo> [--task NAME ...] [--out DIR]

The zip holds only what the fix changed, so it stays small:

    <game>/<game>.bundle    the new commits of main, of every starts/<task> branch and of the tasks branch
    <game>/lfs/objects/     the LFS objects those commits added
    <game>/task-checks/     each task's latest task check result, and writer-scores.json when there is one
    <game>/return.json      what is in the zip: every branch's head, what it was restored at, each result's verdict

"New" means not in what the game was restored from (the `origin` of a repo cloned from the delivery's bundle). A repo
with no `origin` is packed whole. Refuses uncommitted changes, an LFS object that is not on this PC, and a task named
with --task whose latest result is not VALID. Reads git and writes the zip only: no build, a few seconds."""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

FORMAT = "game-return/1"
POINTER = re.compile(rb"\Aversion https://git-lfs\.github\.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize \d+\n")
POINTER_MAX = 200


def run(repo, *args, stdin=None, check=True):
    found = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args], capture_output=True,
                           input=stdin)
    if check and found.returncode:
        raise SystemExit(f"git {' '.join(args)}: {found.stderr.decode('utf-8', 'replace').strip()}")
    return found


def git(repo, *args):
    return run(repo, *args).stdout.decode("utf-8", "replace")


def heads(repo, prefix):
    """{short name: commit} of the refs under a prefix."""
    rows = git(repo, "for-each-ref", "--format=%(refname) %(objectname)", prefix).splitlines()
    return {row.split()[0][len(prefix):]: row.split()[1] for row in rows}


def worktrees(repo):
    return [Path(row[len("worktree "):]) for row in git(repo, "worktree", "list", "--porcelain").splitlines()
            if row.startswith("worktree ")]


def dirty(repo):
    """Every worktree of the repo with uncommitted changes, as (path, files)."""
    found = []
    for tree in worktrees(repo):
        if not tree.is_dir():
            continue
        rows = [row for row in git(tree, "status", "--porcelain").splitlines() if row.strip()]
        if rows:
            found.append((tree, rows))
    return found


def lfs_oids(repo, revs):
    """The LFS objects the given revisions add: every blob among their objects that is an LFS pointer."""
    listed = git(repo, "rev-list", "--objects", *revs).splitlines()
    ids = [row.split()[0] for row in listed]
    if not ids:
        return set()
    sizes = run(repo, "cat-file", "--batch-check", stdin=("\n".join(ids) + "\n").encode()).stdout.decode()
    small = [row.split()[0] for row in sizes.splitlines()
             if len(row.split()) == 3 and row.split()[1] == "blob" and int(row.split()[2]) <= POINTER_MAX]
    oids = set()
    for blob in small:
        match = POINTER.match(run(repo, "cat-file", "blob", blob).stdout)
        if match:
            oids.add(match.group(1).decode())
    return oids


def results(repo):
    """{task: verdict} of the task check results in the repo, and the files to ship."""
    folder = repo / ".task-checks"
    verdicts, files = {}, []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        files.append(path)
        if path.name == "writer-scores.json":
            continue
        try:
            verdicts[path.stem] = json.loads(path.read_text(encoding="utf-8")).get("verdict", "?")
        except (ValueError, OSError):
            verdicts[path.stem] = "unreadable"
    return verdicts, files


def pack(repo, out, tasks=(), now=None):
    """Write the return zip for the game repo and give (zip path, summary dict). Raises SystemExit on a refusal."""
    repo = Path(repo).resolve()
    if run(repo, "rev-parse", "--git-dir", check=False).returncode:
        raise SystemExit(f"{repo} is not a git repo")
    game = repo.name
    changed = dirty(repo)
    if changed:
        lines = [f"  {tree}: {len(rows)} file(s), e.g. {rows[0].strip()}" for tree, rows in changed]
        raise SystemExit("uncommitted changes, commit them first:\n" + "\n".join(lines))

    local = heads(repo, "refs/heads/")
    refs = sorted(name for name in local if name in ("main", "tasks") or name.startswith("starts/"))
    if "main" not in refs:
        raise SystemExit("the repo has no main branch")
    base = heads(repo, "refs/remotes/origin/")
    base.pop("HEAD", None)
    revs = [f"refs/heads/{name}" for name in refs] + (["--not", "--remotes=origin"] if base else [])
    moved = [name for name in refs if local[name] != base.get(name)]
    if not git(repo, "rev-list", "--max-count=1", *revs).strip():
        raise SystemExit("nothing to hand back: no branch has a commit newer than what the game was restored from")

    verdicts, result_files = results(repo)
    for task in tasks:
        if verdicts.get(task) != "VALID":
            raise SystemExit(f"task {task}: latest task check result is {verdicts.get(task, 'missing')}, not VALID")

    oids = lfs_oids(repo, revs)
    store = Path(git(repo, "rev-parse", "--git-common-dir").strip())
    store = (store if store.is_absolute() else repo / store) / "lfs" / "objects"
    missing = sorted(oid for oid in oids if not (store / oid[:2] / oid[2:4] / oid).is_file())
    if missing:
        raise SystemExit(f"{len(missing)} LFS object(s) are not on this PC (run `git lfs fetch --all`): "
                         + ", ".join(oid[:12] for oid in missing[:5]))

    now = now or time.strftime("%Y%m%d-%H%M")
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{game}-return-{now}.zip"
    summary = {
        "format": FORMAT, "game": game, "packed": now,
        "restored_at": {name: base[name] for name in sorted(base)},
        "branches": {name: local[name] for name in refs},
        "changed_branches": moved,
        "lfs_objects": len(oids),
        "task_checks": verdicts,
        "tasks_named": list(tasks),
    }
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / f"{game}.bundle"
        run(repo, "bundle", "create", str(bundle), *revs)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            archive.write(bundle, f"{game}/{game}.bundle", zipfile.ZIP_STORED)
            for oid in sorted(oids):
                archive.write(store / oid[:2] / oid[2:4] / oid, f"{game}/lfs/objects/{oid[:2]}/{oid[2:4]}/{oid}",
                              zipfile.ZIP_STORED)
            for path in result_files:
                archive.write(path, f"{game}/task-checks/{path.name}")
            archive.writestr(f"{game}/return.json", json.dumps(summary, indent=2) + "\n")
    return target, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("repo", help="the game's repo folder")
    parser.add_argument("--task", action="append", default=[], metavar="NAME",
                        help="a task this return fixes; its latest task check result must be VALID (repeatable)")
    parser.add_argument("--out", metavar="DIR", help="where the zip goes (default: a 'returns' folder beside the repo)")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    target, summary = pack(repo, args.out or repo.parent / "returns", args.task)
    print(f"{target}  ({target.stat().st_size / 1e6:.1f} MB)")
    print(f"  branches changed: {', '.join(summary['changed_branches']) or 'none'}")
    print(f"  LFS objects: {summary['lfs_objects']}")
    for task, verdict in sorted(summary["task_checks"].items()):
        print(f"  {task}: {verdict}")
    if not args.task:
        print("  no --task given: the verdicts above were not required to be VALID")
    not_valid = [task for task, verdict in summary["task_checks"].items() if verdict != "VALID"]
    if not_valid:
        print(f"  note: not VALID: {', '.join(sorted(not_valid))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

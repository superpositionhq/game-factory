"""python tools/task-check.py <game repo> [--task NAME|FILE.json ...] [--all] [--keep] [--out DIR] (docs/task-check.md)."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import check, tasks, unreal

USAGE = __doc__


def ignore_results(repo, out):
    """Make sure the results folder inside the repo is git-ignored: the game's .gitignore (templates/ue-game ignores
    /.task-checks/), else the repo's own .git/info/exclude (never a tracked file)."""
    repo, out = Path(repo).resolve(), Path(out).resolve()
    try:
        relative = out.relative_to(repo).as_posix()
    except ValueError:
        return  # outside the repo
    probe = f"{relative}/result.json"
    if subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", probe], capture_output=True).returncode == 0:
        return
    exclude = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-path", "info/exclude"], capture_output=True,
                             text=True).stdout.strip()
    if not exclude:
        return
    path = Path(exclude) if os.path.isabs(exclude) else repo / exclude
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n# the task checker's results (tools/task-check.py)\n/{relative}/\n")


def default_scratch(repo, root=None):
    """Where the scratch copies go by default: on the same volume as the repo's resolved path (junctions and links
    followed), so the copies' LFS files are hardlinks of the repo's own objects. The machine root's .task-check when
    it is on that volume, else a .task-check folder beside the repo's parent folder (beside the repo itself when that
    parent is a drive's root); never inside the repo."""
    real = Path(os.path.realpath(repo))
    root = Path(os.path.realpath(root or unreal.gfroot.root()))
    if os.path.splitdrive(str(root))[0].lower() == os.path.splitdrive(str(real))[0].lower():
        return root / ".task-check"
    parent = real.parent
    base = parent.parent if parent.parent != parent else parent
    return base / ".task-check"


def line(result):
    """The one line printed per task."""
    head = f"{result['verdict']:<7} {result['task']}"
    reasons = result["reasons"]
    return head + (": " + "; ".join(reasons) if reasons else "")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="task-check.py", description=(
        "Check a game's tasks: build the game at each task's start and reference, play both with the TaskProbe "
        "plugin, measure every probe, and say whether the task is VALID (the start fails it, the reference passes "
        "it, what still works already works). docs/task-check.md"))
    parser.add_argument("repo", help="the game's repo (its tasks are read from its tasks branch, else origin/tasks)")
    parser.add_argument("--task", action="append", default=[], metavar="NAME", help="a task on the tasks branch, or a task file (<name>.json) not committed yet (repeatable)")
    parser.add_argument("--all", action="store_true", help="check every task on the tasks branch")
    parser.add_argument("--keep", action="store_true", help="keep the scratch copies (built games) after the check")
    parser.add_argument("--out", help="where results go (default: <repo>\\.task-checks)")
    parser.add_argument("--scratch", help="where the scratch copies go (default: a .task-check folder on the repo's own drive, so LFS "
                             "files are hardlinked)")
    parser.add_argument("--direct", action="store_true",
                        help="run Unreal directly, not through the machine's ue-heavy.ps1 slots")
    parser.add_argument("--timeout", type=int, default=1800, help="seconds a play or the editor pass may run")
    parser.add_argument("--build-timeout", type=int, default=3600, help="seconds a build may run")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        parser.error(f"{repo} isn't a git repo")
    files = {}
    for given in args.task:  # a task file on disk (one being written, not committed yet)
        if given.lower().endswith(".json") and Path(given).is_file():
            raw = Path(given).read_bytes()
            try:
                data = json.loads(raw.decode("utf-8-sig"))
            except ValueError as e:
                data, why = None, f"{given} is not JSON ({e})"
            else:
                why = None if isinstance(data, dict) else f"{given} is not a task object"
            files[given] = (data if why is None else None, raw, why, str(Path(given).resolve()))
    ref, found = tasks.read_tasks(repo)
    sources = {n: (t, raw, why, ref) for n, (t, raw, why) in found.items()}
    sources.update(files)
    if ref is None and not files:
        print(f"{repo.name}: no tasks branch (neither tasks nor origin/tasks)", file=sys.stderr)
        return 2
    names = sorted(found) if args.all else args.task
    if not names:
        print(f"{repo.name}: {len(found)} task(s) on {ref}; name one with --task NAME (or --task <file>.json) or "
              "pass --all:", file=sys.stderr)
        for n in sorted(found):
            print(f"  {n}", file=sys.stderr)
        return 2
    unknown = [n for n in names if n not in sources]
    if unknown:
        print(f"{repo.name}: no task {', '.join(unknown)} on {ref or 'a tasks branch'}", file=sys.stderr)
        return 2
    out = Path(args.out).resolve() if args.out else repo / ".task-checks"
    ignore_results(repo, out)
    scratch_root = Path(args.scratch).resolve() if args.scratch else default_scratch(repo)
    unreal.gfroot.check_free(str(scratch_root), "task check")

    def log(text):
        print(text, file=sys.stderr, flush=True)

    results = []
    for name in names:
        task, raw, why, source = sources[name]
        log(f"{name}: checking ({source})")
        if task is None:
            result = {"task": name, "verdict": "INVALID", "reasons": [why]}
        else:
            tag = hashlib.sha256(f"{repo}:{name}:{time.time()}".encode()).hexdigest()[:8]
            result = check.check_task(repo, task, raw, scratch_root / tag, out, keep=args.keep, direct=args.direct,
                                      timeout=args.timeout, build_timeout=args.build_timeout, log=log)
            if args.keep:
                log(f"  kept the scratch copies in {scratch_root / tag}")
        results.append(result)
        print(line(result), flush=True)
    log(f"results: {out}")
    return 0 if all(r["verdict"] == "VALID" for r in results) else 1

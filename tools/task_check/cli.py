"""python tools/task-check.py <game repo> [--task NAME ...] [--all] [--keep] [--out DIR] (docs/task-check.md)."""

import argparse
import hashlib
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
    parser.add_argument("--task", action="append", default=[], metavar="NAME", help="a task to check (repeatable)")
    parser.add_argument("--all", action="store_true", help="check every task on the tasks branch")
    parser.add_argument("--keep", action="store_true", help="keep the scratch copies (built games) after the check")
    parser.add_argument("--out", help="where results go (default: <repo>\\.task-checks)")
    parser.add_argument("--scratch", help="where the scratch copies go (default: <machine root>\\.task-check)")
    parser.add_argument("--direct", action="store_true",
                        help="run Unreal directly, not through the machine's ue-heavy.ps1 slots")
    parser.add_argument("--timeout", type=int, default=1800, help="seconds a play or the editor pass may run")
    parser.add_argument("--build-timeout", type=int, default=3600, help="seconds a build may run")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        parser.error(f"{repo} isn't a git repo")
    ref, found = tasks.read_tasks(repo)
    if ref is None:
        print(f"{repo.name}: no tasks branch (neither tasks nor origin/tasks)", file=sys.stderr)
        return 2
    names = sorted(found) if args.all else args.task
    if not names:
        print(f"{repo.name}: {len(found)} task(s) on {ref}; name one with --task NAME or pass --all:", file=sys.stderr)
        for n in sorted(found):
            print(f"  {n}", file=sys.stderr)
        return 2
    unknown = [n for n in names if n not in found]
    if unknown:
        print(f"{repo.name}: no task {', '.join(unknown)} on {ref}", file=sys.stderr)
        return 2
    out = Path(args.out).resolve() if args.out else repo / ".task-checks"
    ignore_results(repo, out)
    scratch_root = Path(args.scratch).resolve() if args.scratch else Path(unreal.gfroot.root()) / ".task-check"
    unreal.gfroot.check_free(str(scratch_root), "task check")

    def log(text):
        print(text, file=sys.stderr, flush=True)

    results = []
    for name in names:
        task, raw, why = found[name]
        log(f"{name}: checking ({ref})")
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

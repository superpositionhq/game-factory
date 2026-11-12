"""python tools/task-check.py <game repo> [--task NAME|FILE.json ...] [--all] [--keep] [--out DIR] [--no-judge-shots]
(docs/task-check.md)."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import check, judges, seeds, tasks, unreal

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


def commits_of(repo, task):
    """The commits a task builds (its start and reference, resolved), so the run knows when a copy is last needed."""
    found = set()
    for commit in ((task or {}).get("seed") or {}).get("commit"), ((task or {}).get("seed") or {}).get("reference"):
        if isinstance(commit, str):
            try:
                found.add(seeds.resolve(repo, commit))
            except RuntimeError:
                pass
    return found


def write_progress(out, started, names, results, now=None):
    """<out>/progress.txt and progress.json: where a run stands, rewritten after every task, so whoever started it
    can leave and read it later. `results` are the finished tasks' results, in order."""
    now = time.time() if now is None else now
    names = [Path(n).stem if n.lower().endswith(".json") else n for n in names]
    done = len(results)
    lines = [f"task check: {done} of {len(names)} task(s) done, started {time.strftime('%H:%M', time.localtime(started))}, "
             f"{round((now - started) / 60)} min so far" + ("" if done < len(names) else ", finished")]
    for r in results:
        lines.append(f"  {line(r)}" + (f"  ({round(r['seconds'] / 60)} min)" if r.get("seconds") else ""))
        lines += [f"    {judges.line(n, j)}: {r['task']}/judge-shots/{n}/ask.md"
                  for n, j in (r.get("judges") or {}).items()]
    if done < len(names):
        lines.append(f"  checking {names[done]}" + (f", then {len(names) - done - 1} more" if done + 1 < len(names) else ""))
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "progress.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (Path(out) / "progress.json").write_text(json.dumps(
        {"format": "task-check-progress/1", "started": started, "updated": now, "tasks": names,
         "done": [{"task": r["task"], "verdict": r["verdict"], "reasons": r["reasons"], "seconds": r.get("seconds"),
                   "judges_pending": sorted(r.get("judges") or {})} for r in results],
         "finished": done == len(names)}, indent=2), encoding="utf-8")


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
    parser.add_argument("--no-judge-shots", dest="judge_shots", action="store_false",
                        help="don't play judge checks' plays or save their screenshots (by default each judge check's "
                             "screenshots of the start and the reference are saved under <task>/judge-shots/ to be "
                             "looked at)")
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
        print(f"{time.strftime('%H:%M:%S')} {text}", file=sys.stderr, flush=True)

    # One scratch copy per commit for the whole run: a commit several tasks start or end on is built once, and
    # deleted after the last task that needs it.
    started = time.time()
    tag = hashlib.sha256(f"{repo}:{started}".encode()).hexdigest()[:8]
    builds = check.Builds(repo, scratch_root / tag, args.direct, log)
    needs = {name: commits_of(repo, sources[name][0]) for name in names}
    results = []
    write_progress(out, started, names, results)
    try:
        for i, name in enumerate(names):
            task, raw, why, source = sources[name]
            log(f"{name}: checking ({source})")
            if task is None:
                result = {"task": name, "verdict": "INVALID", "reasons": [why]}
            else:
                result = check.check_task(repo, task, raw, scratch_root / tag, out, keep=args.keep,
                                          direct=args.direct, timeout=args.timeout, build_timeout=args.build_timeout,
                                          log=log, builds=builds, judge_shots=args.judge_shots)
                if not args.keep:
                    later = set().union(*(needs[n] for n in names[i + 1:]))
                    for sha in needs[name] - later:
                        builds.release(sha)
            results.append(result)
            print(line(result), flush=True)
            write_progress(out, started, names, results)
    finally:
        if args.keep:
            log(f"  kept the scratch copies in {scratch_root / tag}")
        else:
            builds.close()
    log(f"results: {out} (progress.txt sums up the run)")
    return 0 if all(r["verdict"] == "VALID" for r in results) else 1

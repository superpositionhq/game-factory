"""A task tried with the contractor's own coding agent, on their own computer (docs/task-try.md).

For one task and each run:
1. The game at the task's start (seed.commit) is copied into a workspace outside the machine root and the game repo,
   as the agent gets it in the cloud: every file of that commit, without Tasks/, History/ or Dataset/, in a fresh git
   repository with one commit and no history (its Git LFS objects hardlinked from the game repo's store, the files
   themselves copies, since the agent edits them).
2. The contractor's harness (Claude Code or Codex, their own subscription and login) runs headless in the workspace
   with the brief as its prompt, within the task's limits (turns where the harness has a flag, minutes always), with
   the machine's recording hooks off (GF_NO_RECORDING). Its transcript is kept.
3. The workspace is graded as a solution: TaskProbe added, built fresh, played, every check but judges, trace probes
   and packaging run against the thresholds the start and the reference give (both built and measured once for all
   runs).

The result says, per run, whether the agent solved the task (every required check passed), which milestones it
reached, its time, turns and cost when the harness reports them, and whether its transcript names the game repo or the
tasks worktree (it could have read the answer there). It is advice: the cloud's grade decides."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from . import check, seeds, tasks, unreal, verdict

FORMAT = "task-try/1"
LONG_MINUTES = 25  # a long task keeps a clean agent run going about 30 minutes; under this is too short (owner, 2026-11-05)
LIMITS = {"max_turns": 200, "max_minutes": 240}  # the schema's defaults (game-task.schema.json Limits)
BUILT = ("Binaries", "Intermediate")  # build outputs removed before a run is graded: the grade builds it fresh
NO_RECORDING = "GF_NO_RECORDING"  # machine/hooks/record-action.ps1 records nothing when it is set


def brief(task, engine):
    """The prompt: the task's instruction, where QA plays (as the cloud harness says it), and where Unreal is, since a
    local harness has no build or play tools of ours."""
    text = task["instruction"].rstrip()
    if task.get("play_map"):
        text += f"\n\nQA plays the game from `{task['play_map']}` (a map and its options)."
    text += (f"\n\nThe game is the Unreal Engine 5.7 project in the current folder. Unreal Engine 5.7 is installed at "
             f"`{engine}`. Build, run and test it yourself; leave your work in this folder.")
    return text


def agent_argv(agent, exe, limits, settings, model=None, extra=()):
    """The headless command line of `agent` ("claude" or "codex"); the prompt comes on stdin. `settings`: a Claude Code
    settings file that turns hooks off (a file, since a .cmd shim mangles JSON on its command line)."""
    if agent == "claude":
        argv = [exe, "-p", "--output-format", "stream-json", "--verbose", "--max-turns", str(limits["max_turns"]),
                "--permission-mode", "bypassPermissions", "--settings", str(settings)]
    elif agent == "codex":
        argv = [exe, "exec", "--json", "-s", "danger-full-access", "--skip-git-repo-check"]
    else:
        raise ValueError(f"no agent {agent!r} (claude or codex)")
    if model:
        argv += ["--model", model] if agent == "claude" else ["-m", model]
    argv += list(extra)
    return argv + (["-"] if agent == "codex" else [])


def limits_of(task):
    return {**LIMITS, **(task.get("limits") or {})}


def workspace(repo, sha, dest):
    """The agent's folder: the game at `sha` (copies), a fresh git repo with one commit, its LFS objects hardlinked
    from the repo's store so committing them costs no disk. {"files", "copied"}."""
    made = seeds.materialize(repo, sha, dest, link=False)
    git = lambda *a: subprocess.run(["git", "-C", str(dest), *a], capture_output=True, text=True)
    git("init", "-q", "-b", "main")
    store = Path(dest) / ".git" / "lfs" / "objects"
    for oid, stored in made["objects"].items():
        target = store / oid[:2] / oid[2:4] / oid
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            seeds.place(stored, target, True)
    git("add", "-A")
    done = git("-c", "user.name=dev", "-c", "user.email=dev@localhost", "commit", "-q", "-m", "start")
    if done.returncode != 0:
        raise RuntimeError(f"couldn't commit the workspace: {done.stderr.strip()[:300]}")
    return {"files": made["files"], "copied": made["copied"]}


def run_agent(argv, cwd, prompt, transcript, minutes, clock=time.monotonic):
    """Run the harness in `cwd` with `prompt` on stdin, its output to `transcript`; killed with its children after
    `minutes`. {"exit_code", "seconds", "timed_out"}."""
    env = dict(os.environ, **{NO_RECORDING: "1"})
    started = clock()
    with open(transcript, "wb") as out:
        proc = subprocess.Popen(argv, cwd=str(cwd), stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT,
                                env=env, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        proc.stdin.write(prompt.encode("utf-8"))
        proc.stdin.close()
        try:
            proc.wait(timeout=minutes * 60)
            timed_out = False
        except subprocess.TimeoutExpired:
            unreal._kill_tree(proc.pid)
            proc.wait()
            timed_out = True
    return {"exit_code": None if timed_out else proc.returncode, "seconds": round(clock() - started, 1),
            "timed_out": timed_out}


def usage(agent, transcript):
    """{"turns", "usd"} as the harness reports them in its transcript (None when it doesn't)."""
    turns = usd = None
    try:
        lines = Path(transcript).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {"turns": None, "usd": None}
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if agent == "claude" and event.get("type") == "result":
            turns, usd = event.get("num_turns", turns), event.get("total_cost_usd", usd)
        elif agent == "codex" and event.get("type") == "turn.completed":
            turns = (turns or 0) + 1
    return {"turns": turns, "usd": usd}


def peeked(transcript, places):
    """The `places` (the game repo, the tasks worktree) the transcript names: the agent could have read the answer."""
    try:
        text = Path(transcript).read_text(encoding="utf-8", errors="replace").lower().replace("\\\\", "\\")
    except OSError:
        return []
    found = []
    for place in places:
        forms = {str(place).lower(), str(place).lower().replace("\\", "/")}
        if any(f and f in text for f in forms):
            found.append(str(place))
    return found


def outside(path, folders):
    """Whether `path` lies outside every one of `folders`."""
    real = os.path.realpath(path).lower()
    for f in folders:
        root = os.path.realpath(f).lower().rstrip("\\/")
        if real == root or real.startswith(root + os.sep) or real.startswith(root + "/"):
            return False
    return True


def score(task, grade):
    """What a run reached: solved (every required check passed), its score (the weighted share of checks passed, as the
    cloud scores it, judges left out since a try doesn't run them), required checks passed, milestones reached."""
    rows = grade["checks"]
    weighed = [r for r in rows if r.get("kind") not in verdict.JUDGES]
    total = sum(r.get("weight", 1) for r in weighed)
    earned = sum(r.get("weight", 1) for r in weighed if r["passed"])
    required = [r for r in rows if r["required"]]
    groups = {}
    for r in required:
        groups.setdefault(r["group"], []).append(r["passed"])
    return {"solved": all(r["passed"] for r in required), "score": round(earned / total, 3) if total else 0.0,
            "required_passed": sum(r["passed"] for r in required),
            "required": len(required), "milestones": {g: all(v) for g, v in groups.items()}}


def side(name, folder, task, direct, timeout, build_timeout, evidence, log):
    seeds.add_probe(folder)
    machine = unreal.Machine.for_project(folder, direct)
    return check.Side(name, unreal.Project(folder, machine, f"{task['name']} {name}"), task, timeout, build_timeout,
                      evidence, log), machine


def try_task(repo, task, raw, scratch, out_dir, agent, exe, runs=1, model=None, extra=(), keep=False, direct=False,
             timeout=1800, build_timeout=3600, places=(), log=print, clock=time.time):
    """Try one task `runs` times with `agent`; its result (written to <out_dir>/<name>.json, each run's transcript and
    plays under <out_dir>/<name>/)."""
    started = clock()
    name = task.get("name", "?")
    evidence = Path(out_dir) / name
    result = {"format": FORMAT, "task": name, "game": (task.get("seed") or {}).get("game"),
              "task_sha256": tasks.digest(raw), "agent": agent, "model": model, "status": None, "reasons": [],
              "solved": 0, "runs": [], "limits": limits_of(task), "at": None, "seconds": None,
              "evidence": f"{name}/"}

    def finish(status, reasons=()):
        result.update(status=status, reasons=list(reasons), solved=sum(1 for r in result["runs"] if r.get("solved")),
                      seconds=round(clock() - started, 1), at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / f"{name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    found = tasks.problems(task)
    if found:
        return finish("ERROR", [f"the task doesn't validate: {p}" for p in found[:5]])
    seed = task["seed"]
    if not seed.get("reference"):
        return finish("ERROR", ["the task has no seed.reference: a try is graded against the start and the reference"])
    scratch = Path(scratch)
    seeds.remove(evidence)
    evidence.mkdir(parents=True)
    try:
        shas = {k: seeds.resolve(repo, seed[k]) for k in ("commit", "reference")}
        sides = {}
        for label, sha in (("start", shas["commit"]), ("reference", shas["reference"])):
            log(f"  {label}: materializing {sha[:12]}")
            seeds.materialize(repo, sha, scratch / label)
            sides[label], machine = side(label, scratch / label, task, direct, timeout, build_timeout, evidence, log)
        start, reference = sides["start"], sides["reference"]
        if not start.built() and tasks.fails_at_start(task) is None:
            return finish("ERROR", [f"the start doesn't build: {start.why_unbuilt()} (run task-check.py first)"])
        if not reference.built():
            return finish("ERROR", [f"the reference doesn't build: {reference.why_unbuilt()} (run task-check.py first)"])
        thresholds = {}
        prompt = brief(task, machine.engine)
        (evidence / "brief.md").write_text(prompt, encoding="utf-8")
        limits = limits_of(task)
        for i in range(1, runs + 1):
            label = f"run{i}"
            folder = scratch / label / seed["game"]
            log(f"  {label}: preparing the workspace {folder}")
            workspace(repo, shas["commit"], folder)
            transcript = evidence / label / "transcript.jsonl"
            transcript.parent.mkdir(parents=True, exist_ok=True)
            settings = evidence / "claude-settings.json"
            settings.write_text(json.dumps({"disableAllHooks": True}), encoding="utf-8")
            argv = agent_argv(agent, exe, limits, settings, model, extra)
            log(f"  {label}: {agent} working (up to {limits['max_minutes']} min)")
            ran = run_agent(argv, folder, prompt, transcript, limits["max_minutes"])
            row = {"run": i, **ran, **usage(agent, transcript), "peeked": peeked(transcript, places),
                   "workspace": str(folder) if keep else None}
            log(f"  {label}: {agent} stopped after {ran['seconds'] / 60:.0f} min"
                + (" (timed out)" if ran["timed_out"] else f" (exit {ran['exit_code']})"))
            for d in BUILT:
                seeds.remove(folder / d)
            try:
                tried, _ = side(label, folder, task, direct, timeout, build_timeout, evidence, log)
            except (seeds.WrongEngine, FileNotFoundError) as exc:  # the agent changed the engine or removed the project
                row.update(solved=False, score=0.0, required_passed=0, required=None, milestones={}, checks=[],
                           why=str(exc))
            else:
                grade = check.Grade(task, "reference", start, reference, thresholds, side=tried).run()
                row.update(score(task, grade), checks=grade["checks"])
            log(f"  {label}: {'SOLVED' if row['solved'] else 'not solved'} "
                f"({row['required_passed']}/{row['required'] or '?'} required checks)")
            result["runs"].append(row)
            if not keep:
                seeds.remove(scratch / label)
        return finish("DONE")
    except (OSError, RuntimeError, ValueError) as exc:
        return finish("ERROR", [f"the try couldn't run: {type(exc).__name__}: {str(exc)[:400]}"])
    finally:
        if not keep:
            seeds.remove(scratch)


def line(result):
    """The one line printed per task."""
    if result["status"] != "DONE":
        return f"ERROR   {result['task']}: " + "; ".join(result["reasons"])
    runs = result["runs"]
    head = f"{result['solved']}/{len(runs)} solved  {result['task']}"
    best = max((r["required_passed"] for r in runs), default=0)
    total = next((r["required"] for r in runs if r["required"]), "?")
    tail = f"  (best {best}/{total} required checks"
    peeks = sorted({p for r in runs for p in r["peeked"]})
    tail += f"; transcript names {', '.join(peeks)}: it may have read the answer)" if peeks else ")"
    times = [r["seconds"] / 60 for r in runs if r.get("seconds") is not None and not r.get("timed_out")]
    if times and max(times) < LONG_MINUTES:
        tail += f"  longest run {max(times):.1f} min: under {LONG_MINUTES} min, not long enough"
    return head + tail


def default_scratch(repo):
    """Where the workspaces go by default: a .task-try folder at the root of the repo's drive, so LFS objects hardlink
    and the agent's folder is outside the machine root (whose CLAUDE.md and AGENTS.md a harness would read) and the
    game repo."""
    real = Path(os.path.realpath(repo))
    return Path(real.anchor or "/") / ".task-try"


def main(argv=None):
    import argparse
    import hashlib
    import sys

    from . import cli

    parser = argparse.ArgumentParser(prog="task-try.py", description=(
        "Try a game's task with your own coding agent (Claude Code or Codex): the game at the task's start in a fresh "
        "workspace, the agent given the brief, its result built, played and graded against the task's probes. "
        "docs/task-try.md"))
    parser.add_argument("repo", help="the game's repo (its tasks are read from its tasks branch, else origin/tasks)")
    parser.add_argument("--task", action="append", default=[], metavar="NAME",
                        help="a task on the tasks branch, or a task file (<name>.json) not committed yet (repeatable)")
    parser.add_argument("--agent", choices=("claude", "codex"), required=True, help="the harness to run")
    parser.add_argument("--runs", type=int, default=1, help="runs per task (default 1)")
    parser.add_argument("--model", help="the model the harness uses (default: its own)")
    parser.add_argument("--agent-arg", action="append", default=[], metavar="ARG",
                        help="an extra argument for the harness (repeatable)")
    parser.add_argument("--keep", action="store_true", help="keep the workspaces and built copies after the try")
    parser.add_argument("--out", help="where results go (default: <repo>\\.task-tries)")
    parser.add_argument("--scratch", help="where workspaces go (default: <repo's drive>\\.task-try)")
    parser.add_argument("--direct", action="store_true",
                        help="run Unreal directly, not through the machine's ue-heavy.ps1 slots")
    parser.add_argument("--timeout", type=int, default=1800, help="seconds a play or the editor pass may run")
    parser.add_argument("--build-timeout", type=int, default=3600, help="seconds a build may run")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        parser.error(f"{repo} isn't a git repo")
    if not args.task:
        parser.error("name a task with --task NAME (or --task <file>.json)")
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    exe = shutil.which(args.agent)
    if exe is None:
        parser.error(f"{args.agent} isn't on PATH: install it and log in first")
    ref, found = tasks.read_tasks(repo)
    sources = {n: (t, raw, why) for n, (t, raw, why) in found.items()}
    tasks_dir = None
    for given in args.task:
        if given.lower().endswith(".json") and Path(given).is_file():
            raw = Path(given).read_bytes()
            try:
                data = json.loads(raw.decode("utf-8-sig"))
            except ValueError as e:
                data, why = None, f"{given} is not JSON ({e})"
            else:
                why = None if isinstance(data, dict) else f"{given} is not a task object"
            sources[given] = (data if why is None else None, raw, why)
            tasks_dir = Path(given).resolve().parent.parent
    unknown = [n for n in args.task if n not in sources]
    if unknown:
        parser.error(f"no task {', '.join(unknown)} on {ref or 'a tasks branch'}")
    root = Path(os.path.realpath(unreal.gfroot.root()))
    scratch_root = Path(args.scratch).resolve() if args.scratch else default_scratch(repo)
    if not outside(scratch_root, [root, repo] + ([tasks_dir] if tasks_dir else [])):
        parser.error(f"{scratch_root} is inside the machine root, the game repo or the tasks folder: the agent would "
                     "read their AGENTS.md / CLAUDE.md; pass --scratch outside them")
    out = Path(args.out).resolve() if args.out else repo / ".task-tries"
    cli.ignore_results(repo, out)
    unreal.gfroot.check_free(str(scratch_root), "task try")
    places = [repo, root / "tasks" / repo.name] + ([tasks_dir] if tasks_dir else [])

    def log(text):
        print(text, file=sys.stderr, flush=True)

    results = []
    for name in args.task:
        task, raw, why = sources[name]
        log(f"{name}: trying with {args.agent}, {args.runs} run(s)")
        if task is None:
            result = {"task": name, "status": "ERROR", "reasons": [why], "runs": [], "solved": 0}
        else:
            tag = hashlib.sha256(f"{repo}:{name}:{time.time()}".encode()).hexdigest()[:8]
            result = try_task(repo, task, raw, scratch_root / tag, out, args.agent, exe, runs=args.runs,
                              model=args.model, extra=args.agent_arg, keep=args.keep, direct=args.direct,
                              timeout=args.timeout, build_timeout=args.build_timeout, places=places, log=log)
            if args.keep:
                log(f"  kept the workspaces and built copies in {scratch_root / tag}")
        results.append(result)
        print(line(result), flush=True)
    log(f"results: {out}")
    return 0 if all(r["status"] == "DONE" for r in results) else 1

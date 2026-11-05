# Task try: run your task with your own coding agent

The task check ([task-check.md](task-check.md)) proves a task is fair: the start fails it and the reference passes.
The task try tells you whether it is hard enough. It gives the task to your own coding agent, Claude Code or Codex on
your own subscription, exactly as an agent gets it in the cloud, then grades what the agent left with the task's own
probes. Every task must be a long thread of multiple edits (write-tasks skill, section 1); if your agent solves it
easily, the task isn't done yet.

```powershell
python tools\task-try.py C:\Users\<you>\Work\games\<slug> --task <task-name> --agent claude
python tools\task-try.py C:\Users\<you>\Work\games\<slug> --task <task-name> --agent codex --runs 3
python tools\task-try.py C:\Users\<you>\Work\games\<slug> --task C:\Users\<you>\Work\tasks\<slug>\Tasks\<task-name>.json --agent claude
```

Each task prints one line, for example:

```
0/3 solved  stealth-fix-guards-lose-the-player  (best 4/7 required checks)
2/3 solved  rally-racer-corr-chase-camera  (best 7/7 required checks)
```

Options: `--runs N` (default 1), `--model M` (the harness's model; default its own), `--agent-arg ARG` (an extra
argument for the harness, repeatable), `--keep` (keep the workspaces and the built games), `--out DIR`,
`--scratch DIR`, `--direct`, `--timeout S`, `--build-timeout S` (as the task check's).

## Before you run it

- The task check says VALID (`tools/task-check.py`). The try builds the start and the reference too, but tells you
  nothing useful about a task that isn't valid.
- `claude` or `codex` is on PATH and logged in (run it once by hand). The try runs it headless: Claude Code with
  `-p --permission-mode bypassPermissions` and its hooks off, Codex with `exec -s danger-full-access`; the agent can
  run anything on your computer, as a game session can.
- Requirements as the task check's: Windows, Unreal Engine 5.7, Python 3.12, git and Git LFS with both commits' objects
  fetched. Disk: one full copy of the game per run (the agent edits it, so it can't be a hardlink), plus the start
  and the reference built once.
- Time: the agent gets the task's `limits.max_minutes` (Claude Code also its `max_turns`), then one build and the
  plays per run. A long thread can take hours per run; start it before you leave the machine.

## What it does

1. Builds and measures the start and the reference once, as the task check does, for the probes' thresholds.
2. Per run, copies the game at `seed.commit` into a workspace `<drive>:\.task-try\<id>\run<N>\<game>`: every file of
   that commit without `Tasks/`, `History/` or `Dataset/`, in a fresh git repository with one commit. The workspace is
   outside the machine root and the game repo, so the harness reads neither's `AGENTS.md` or `CLAUDE.md`.
3. Starts the harness in the workspace with the brief as its prompt: the task's instruction, the map QA plays
   (`play_map`) and where Unreal 5.7 is installed. Nothing of the grader's half. The machine's recording hooks record
   nothing for it (`GF_NO_RECORDING`), so a try never enters a game's record. Rerun `machine\bootstrap.ps1` once after
   pulling this, so the installed hooks have that switch.
4. When the agent stops (or its time runs out), removes `Binaries/` and `Intermediate/`, adds the probe plugin, builds
   and plays the agent's game and runs every check but judges, trace probes and packaging, against the thresholds of
   step 1.

Results: `<repo>\.task-tries\<task>.json` (format `task-try/1`): per run `solved` (every required check passed),
`required_passed` of `required`, `milestones` reached, `seconds`, `timed_out`, `turns` and `usd` when the harness
reports them, the `checks` rows, and `peeked`. Each run's transcript is `<task>\run<N>\transcript.jsonl`, its plays
beside it, and the brief the agent read `<task>\brief.md`.

## Reading the result

- **Longest run under 30 minutes:** not long enough, solved or not; the printed line says so. A run that hit its own
  time limit or crashed says nothing about length.
- **Solved in any run, quickly:** too easy. Extend the thread back to an earlier attempt, merge it with its
  neighbouring issues, or drop it (write-tasks section 6).
- **Never solved, but some required checks pass:** what a hard task looks like. Read the transcript: the agent should
  fail because the work is long and the cause is far away, not because the brief is missing something a player would
  know or the play map is wrong.
- **Nothing passes, not even the build:** check the agent could build at all (the transcript); an agent that never
  found the engine says nothing about the task.
- **`peeked` lists a folder:** the transcript names your game repo or tasks worktree, where the history and the
  answer are. That run doesn't count: the cloud agent can't reach them. Run it again, or from an account that can't
  read those folders.

The try is advice for you. The cloud's own runs and grade decide approval, difficulty and pay. Your agent also has your
own harness settings, skills and memory, which the cloud agent doesn't; keep them out of its way when you can.

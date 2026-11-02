#!/usr/bin/env python3
"""Try a game's tasks with your own coding agent before handing them in (docs/task-try.md).

    python tools/task-try.py <games>/<slug> --task <name> --agent claude|codex [--runs N]
    python tools/task-try.py <games>/<slug> --task <path>/Tasks/<name>.json --agent codex   # a task file not committed yet
    options: --model M, --agent-arg ARG (repeatable), --keep, --out DIR (default <repo>\\.task-tries), --scratch DIR,
             --direct, --timeout S, --build-timeout S

For each task and run: the game at the task's start in a fresh workspace without history or tasks, your harness (Claude
Code or Codex, your own login) given the brief within the task's limits, then the result built, played and graded
against the task's probes (thresholds from the start and the reference). Prints how many runs solved it and writes
<out>\\<task>.json (each run's transcript and plays under <out>\\<task>\\). Exit code 0 when every task was tried, 1
otherwise, 2 for a usage error. Standard library only (Python 3.12).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_check.trial import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

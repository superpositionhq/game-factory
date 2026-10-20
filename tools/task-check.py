#!/usr/bin/env python3
"""Check a game's tasks yourself before handing them in (docs/task-check.md).

    python tools/task-check.py <games>/<slug> --task <name> [--task <name> ...]
    python tools/task-check.py <games>/<slug> --all
    python tools/task-check.py <games>/<slug> --task <path>/Tasks/<name>.json   # a task file not committed yet
    options: --keep (keep the built scratch copies), --out DIR (default <repo>\\.task-checks), --scratch DIR,
             --direct (run Unreal without the machine's ue-heavy.ps1 slots), --timeout S, --build-timeout S

For each task: builds the game at its start (seed.commit) and its reference (seed.reference), plays both with the
TaskProbe plugin, measures every probe, prints VALID or INVALID with the reasons, and writes <out>\\<task>.json (and
each play's probe.json, screenshots and log under <out>\\<task>\\). Exit code 0 when every task is VALID, 1 otherwise,
2 for a usage error. Standard library only (Python 3.12).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_check.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

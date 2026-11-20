#!/usr/bin/env python3
"""A person's returned tasks, from the two lists we share (write-tasks skill, "Finding the person's returned tasks").

    python tools/returned-tasks.py --owner "<name>" [--game "<title>"] [--out FILE.csv]
                                   [--downloads DIR] [--assignments FILE] [--tasks FILE] [--json]

Two CSV files, each downloaded from a Google Sheet (File > Download > Comma-separated values):

    the assignments list   Task ID, Game, Task name, Owner, Status          who has which task
    the tasks list         Game, Task, Task name, Task ID, Version, What is wrong, Detail (internal),
                           Game download link, Tasks download link, Links expire   every task, with its links

The newest file of each kind in the Downloads folder is used, told apart by its columns, not its name. A task is the
person's when its Owner is their name. Its Status says whether to work on it: Assigned, In progress and Needs rework
are open; Submitted, Validating and Approved are with us (sent in, being checked, or passed), so they are left
alone; No longer needed, or a task missing from the tasks list, is dropped; Unassigned is given back. Open tasks are
matched to the tasks list by Task ID.

Without --game it prints the person's games. With --game it prints that game's open tasks in full, with both
download links. --out also writes the open tasks as a CSV; --json prints everything as JSON. Reads two files only."""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

WITH_US = {"submitted", "validating", "approved"}  # sent in: being checked or passed, so not worked on
DROPPED = {"no longer needed"}  # fixed another way or withdrawn: no work on it, even part-way through
GIVEN_BACK = {"unassigned"}  # the person handed it back
ASSIGNMENT_COLUMNS = {"task id", "owner", "status"}
TASK_COLUMNS = {"task id", "game download link", "tasks download link"}
SHIPPED = ["Game", "Task", "Task name", "Task ID", "Version", "Status", "What is wrong", "Detail",
           "Game download link", "Tasks download link", "Links expire"]


def key(name):
    return " ".join(str(name or "").replace("﻿", "").split()).lower()


def read(path):
    """The rows of a CSV as dicts keyed by lower-cased column name, and those names."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], []
    names = [key(name) for name in rows[0]]
    return [dict(zip(names, (cell.strip() for cell in row))) for row in rows[1:] if any(row)], names


def newest(folder, wanted):
    """The most recently changed CSV in the folder whose columns include the wanted ones."""
    files = sorted(Path(folder).glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files:
        try:
            if wanted <= set(read(path)[1]):
                return path
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
    return None


def detail(row):
    return row.get("detail (internal)") or row.get("detail") or ""


def collect(assignments, tasks, owner):
    """What the two lists say about one owner: their open tasks joined to the tasks list, and what was left out."""
    rows, names = read(assignments)
    if not ASSIGNMENT_COLUMNS <= set(names):
        raise SystemExit(f"{assignments}: not the assignments list (needs columns Task ID, Owner, Status)")
    listed, names = read(tasks)
    if not TASK_COLUMNS <= set(names):
        raise SystemExit(f"{tasks}: not the tasks list (needs Task ID and the two download link columns)")
    by_id = {row["task id"]: row for row in listed if row.get("task id")}

    mine = [row for row in rows if key(row.get("owner")) == key(owner)]
    if not mine:
        owners = sorted({row.get("owner", "") for row in rows if row.get("owner")}, key=str.lower)
        raise SystemExit(f"no task has the owner \"{owner}\". Owners in {Path(assignments).name}: "
                         + (", ".join(owners) or "none"))
    found = {"owner": owner, "assignments": str(assignments), "tasks": str(tasks),
             "open": [], "gone": [], "with_us": {}, "given_back": 0}
    for row in mine:
        status = row.get("status", "")
        if key(status) in WITH_US:
            found["with_us"][status] = found["with_us"].get(status, 0) + 1
            continue
        if key(status) in GIVEN_BACK:
            found["given_back"] += 1
            continue
        source = by_id.get(row.get("task id"))
        if key(status) in DROPPED or not source:
            found["gone"].append({"Game": row.get("game", ""), "Task name": row.get("task name", ""),
                                  "Task ID": row.get("task id", ""), "Status": status})
            continue
        found["open"].append({
            "Game": source.get("game", "") or row.get("game", ""), "Task": source.get("task", ""),
            "Task name": source.get("task name", "") or row.get("task name", ""), "Task ID": row["task id"],
            "Version": source.get("version", ""), "Status": status,
            "What is wrong": source.get("what is wrong", ""), "Detail": detail(source),
            "Game download link": source.get("game download link", ""),
            "Tasks download link": source.get("tasks download link", ""),
            "Links expire": source.get("links expire", "")})
    return found


def games(found):
    """[(game, its open tasks)] in the order of the tasks list."""
    grouped = {}
    for task in found["open"]:
        grouped.setdefault(task["Game"], []).append(task)
    return list(grouped.items())


def report(found, game=None):
    lines = [f"Owner: {found['owner']}",
             f"Assignments list: {found['assignments']}  (downloaded {age(found['assignments'])})",
             f"Tasks list: {found['tasks']}  (downloaded {age(found['tasks'])})", ""]
    listed = games(found)
    if game:
        chosen = [(title, tasks) for title, tasks in listed if key(title) == key(game)]
        if not chosen:
            raise SystemExit(f"no open task of {found['owner']} is in a game called \"{game}\". Their games: "
                             + (", ".join(title for title, _ in listed) or "none"))
        title, tasks = chosen[0]
        lines += [f"{title}: {len(tasks)} task(s) to fix", f"  Game download link: {tasks[0]['Game download link']}",
                  f"  Tasks download link: {tasks[0]['Tasks download link']}",
                  f"  Links expire: {tasks[0]['Links expire']}", ""]
        for task in tasks:
            lines += [f"- {task['Task name']}  (version {task['Version']}, status {task['Status'] or 'none'})",
                      f"  Task: {task['Task']}", f"  What is wrong: {task['What is wrong']}",
                      f"  Detail: {task['Detail'] or 'none given'}", f"  Task ID: {task['Task ID']}", ""]
    else:
        lines.append(f"{len(found['open'])} open task(s) in {len(listed)} game(s):")
        for title, tasks in listed:
            statuses = sorted({task["Status"] or "none" for task in tasks})
            lines.append(f"  {title}: {len(tasks)} task(s)  [{', '.join(statuses)}]")
        lines.append("")
    rework = [task for task in found["open"] if key(task["Status"]) == "needs rework"]
    if rework:
        lines.append(f"{len(rework)} task(s) came back as Needs rework: fix them in the game's folder already set up, "
                     "from the reason the person pastes in (the assignments list's Why it needs rework).")
        lines += [f"  {task['Game']}: {task['Task name']}" for task in rework]
        lines.append("")
    if found["gone"]:
        lines.append(f"{len(found['gone'])} task(s) under this name are no longer needed (marked so, or gone from "
                     "the tasks list): do no work on them, even part-way through:")
        lines += [f"  {task['Game']}: {task['Task name']}" for task in found["gone"]]
        lines.append("")
    if found["with_us"]:
        lines.append("With us, leave alone: " + ", ".join(f"{count} {status}" for status, count
                                                          in sorted(found["with_us"].items()))
                     + " (sent in and being checked or passed; a task that fails comes back as Needs rework)")
    if found["given_back"]:
        lines.append(f"Given back (Unassigned): {found['given_back']}")
    return "\n".join(lines).rstrip() + "\n"


def age(path):
    hours = (time.time() - Path(path).stat().st_mtime) / 3600
    return "under an hour ago" if hours < 1 else f"{hours:.0f} hour(s) ago"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--owner", required=True, help="the person's name, as written in the Owner column")
    parser.add_argument("--game", help="print this game's open tasks in full, with its download links")
    parser.add_argument("--downloads", default=str(Path.home() / "Downloads"), metavar="DIR",
                        help="where the two CSV files were saved (default: your Downloads folder)")
    parser.add_argument("--assignments", metavar="FILE", help="the assignments list, instead of the newest found")
    parser.add_argument("--tasks", metavar="FILE", help="the tasks list, instead of the newest found")
    parser.add_argument("--out", metavar="FILE.csv", help="also write the open tasks to this CSV")
    parser.add_argument("--json", action="store_true", help="print everything as JSON")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # a name or a title may not fit the console's own encoding
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    assignments = args.assignments or newest(args.downloads, ASSIGNMENT_COLUMNS)
    tasks = args.tasks or newest(args.downloads, TASK_COLUMNS)
    if not assignments or not tasks:
        missing = " and ".join(name for name, path in (("the assignments list", assignments),
                                                       ("the tasks list", tasks)) if not path)
        raise SystemExit(f"{missing} not found in {args.downloads}: download it from its Google Sheet as a CSV "
                         "(File > Download > Comma-separated values)")
    found = collect(assignments, tasks, args.owner)
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, SHIPPED)
            writer.writeheader()
            writer.writerows(found["open"])
    if args.json:
        print(json.dumps(found, indent=2, ensure_ascii=False))
    else:
        sys.stdout.write(report(found, args.game))
    return 0


if __name__ == "__main__":
    sys.exit(main())

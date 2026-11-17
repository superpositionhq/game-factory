#!/usr/bin/env python3
"""Stage Checks/ for package-dataset.ps1. Standard library only; no Unreal or Windows needed.

python tools/package-checks.py <game repo> <split Tasks dir> <Checks out> --commit-map <tsv>

Reads only .task-checks/<task>.json (the latest result, never an older successful run),
.task-checks/writer-scores.json, and the small blind/answers.json files. Validates the
original task on the tasks branch before binding the result to its delivered halves.
Prints {last_commit_at: {task: ISO timestamp}} for the dataset manifest.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from task_check.digest import canonical_digest, merged
from writer_checks import check_errors, score_errors

SLUG = re.compile(r"[a-z0-9][a-z0-9-]{1,62}\Z")
CHECK_NAME = re.compile(r"[a-z0-9_]{1,48}\Z")
SHA = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        raise ValueError(f"git {args[0]} failed: fetch the tasks branch and package again")
    return result.stdout.decode("utf-8-sig")


def task_ref(repo, ref=None):
    for candidate in ([ref] if ref else ["tasks", "origin/tasks"]):
        found = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "-q",
                                candidate + "^{commit}"], capture_output=True, text=True)
        if found.returncode == 0:
            return found.stdout.strip()  # freeze the branch tip for the entire operation
    raise ValueError("no tasks branch: fetch tasks before packaging")


def read_commit_map(path):
    mapping = {}
    if path:
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            parts = line.split("\t")
            if len(parts) == 2 and all(re.fullmatch(r"[0-9a-f]{40}", p) for p in parts):
                mapping[parts[0]] = parts[1]
    return mapping


def delivered_task(task, mapping):
    """Only the existing packager's full-SHA substitutions are allowed to change a checked task."""
    text = json.dumps(task, ensure_ascii=False)
    return json.loads(SHA.sub(lambda match: mapping.get(match[0], match[0]), text))


def stage(repo, tasks_dir, out, commit_map=None, tasks_ref=None):
    repo, tasks_dir, out = Path(repo), Path(tasks_dir), Path(out)
    ref = task_ref(repo, tasks_ref)
    latest = task_ref(repo)
    checks = repo / ".task-checks"
    scores = read_json(checks / "writer-scores.json")
    mapping = read_commit_map(commit_map)
    originals, results, timestamps, answers = {}, {}, {}, {}
    folders = sorted(p for p in tasks_dir.iterdir() if p.is_dir())
    if not folders:
        raise ValueError("no shipped tasks to check")
    for folder in folders:
        name = folder.name
        if not SLUG.fullmatch(name) or name == "writer-scores":
            raise ValueError(f"task name {name!r} cannot be used in Checks/")
        original = json.loads(git(repo, "show", f"{ref}:Tasks/{name}.json"))
        if not isinstance(original, dict) or original.get("name") != name:
            raise ValueError(f"{name}: not a task object with the matching name")
        current = json.loads(git(repo, "show", f"{latest}:Tasks/{name}.json"))
        if canonical_digest(current) != canonical_digest(original):
            raise ValueError(f"{name}: task changed on the tasks branch since package-game ran; package it again")
        whole = merged(read_json(folder / "task.json"), read_json(folder / "grader.json"))
        if canonical_digest(whole) != canonical_digest(delivered_task(original, mapping)):
            raise ValueError(f"{name}: delivered task differs from the checked tasks branch beyond commit mapping; "
                             "fix the source task and package again")
        timestamp = git(repo, "log", "-1", "--format=%cI", latest, "--", f"Tasks/{name}.json").strip()
        result = read_json(checks / f"{name}.json")
        problems = check_errors(original, result, timestamp)
        if problems:
            raise ValueError(f"{name}: " + "; ".join(problems))
        originals[name], timestamps[name] = original, timestamp
        # Keep task_sha256 (the original file's bytes) and all measures unchanged. The
        # canonical digest pins the halves the recipient actually gets after anonymisation.
        results[name] = dict(result, task_digest=canonical_digest(whole))
        for milestone in original.get("milestones", []):
            for check in milestone.get("checks", []):
                kind = check.get("kind")
                group = "judge-shots" if kind == "judge" else "seen-shots" if (
                    kind == "probe" and check.get("measure", {}).get("probe") == "seen") else None
                check_name = check.get("name", "")
                if group and CHECK_NAME.fullmatch(check_name):
                    relative = Path(name) / group / check_name / "blind" / "answers.json"
                    source = checks / relative
                    if source.is_file():
                        # Parse before copying: this allowlist cannot carry a log or an image.
                        if source.stat().st_size > 1024 * 1024:
                            raise ValueError(f"{name}/{check_name}: blind answers exceed 1 MiB")
                        read_json(source)
                        answers[relative] = source.read_bytes()
    problems = score_errors(originals, scores)
    if problems:
        raise ValueError("writer-scores.json: " + "; ".join(problems))
    # Validate everything before replacing the previous staging folder. The zip is
    # replaced by package-dataset only after its usual rescan and validators pass.
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name, result in results.items():
        (out / f"{name}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "writer-scores.json").write_text(json.dumps(scores, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for relative, raw in answers.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return {"last_commit_at": timestamps}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo")
    parser.add_argument("tasks_dir")
    parser.add_argument("out")
    parser.add_argument("--commit-map")
    parser.add_argument("--tasks-ref", help="the tasks commit pinned by package-game, else tasks/origin/tasks")
    args = parser.parse_args()
    try:
        metadata = stage(args.repo, args.tasks_dir, args.out, args.commit_map, args.tasks_ref)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Checks/: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(metadata))
    return 0


if __name__ == "__main__":
    sys.exit(main())

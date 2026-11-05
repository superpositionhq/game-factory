#!/usr/bin/env python3
"""A thread's own size, from the commits you say belong to it (write-tasks skill, section 6).

    python tools/thread-stats.py <game repo> <commit> [<commit> ...] [--span START..REF]

Which commits make up a thread is your judgement (a commit answers one of the thread's directions, or works on the
issues it settled); this counts them the way validate-game.py counts a task's span: commits that change the game,
game files changed, code lines added plus removed, and systems crossed. With --span it also prints the task's whole
span from seed.commit to seed.reference, so a short thread padded by another thread's work in the same stretch shows.
Reads git only: no build, a few seconds."""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("validate_game", HERE / "validate-game.py")
vg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vg)


def git(repo, *args):
    found = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *args], capture_output=True)
    if found.returncode:
        raise SystemExit(f"git {' '.join(args)}: {found.stderr.decode('utf-8', 'replace').strip()}")
    return found.stdout.decode("utf-8", "replace")


def size(numstats):
    """(game files, code lines, systems) over the numstat rows of one diff or of several commits."""
    files, lines, systems = set(), 0, set()
    for numstat in numstats:
        for row in numstat.splitlines():
            parts = row.split("\t")
            if len(parts) == 3 and vg.GAME_FILE.search(parts[2]):
                files.add(parts[2])
                systems.add(vg.thread_system(parts[2]))
        lines += vg.thread_size(numstat)[0]
    return files, lines, systems


def own(repo, commits):
    """The thread's own commits: each one's diff against its parent, summed."""
    shas = [git(repo, "rev-parse", "--verify", f"{c}^{{commit}}").strip() for c in commits]
    shas = list(dict.fromkeys(shas))
    stats = [git(repo, "show", "--numstat", "--no-renames", "--format=", sha) for sha in shas]
    game = [sha for sha, s in zip(shas, stats) if any(vg.GAME_FILE.search(r.split("\t")[-1]) for r in s.splitlines()
                                                       if r.count("\t") == 2)]
    return len(shas), len(game), *size(stats)


def span(repo, start, ref):
    """The task's span as validate-game.py measures it: the reference's diff against the start."""
    numstat = git(repo, "diff", "--numstat", "--no-renames", start, ref)
    commits = int(git(repo, "rev-list", "--count", f"{start}..{ref}", "--", *vg.GAME_PATHS).strip() or 0)
    return commits, *size([numstat])


def line(label, commits, files, lines, systems):
    return f"{label}: {commits} game commit(s), {len(files)} game file(s), {lines} code line(s), " \
           f"{len(systems)} system(s) ({', '.join(sorted(systems)) or 'none'})"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="thread-stats.py", description=__doc__.splitlines()[0])
    parser.add_argument("repo", help="the game repo")
    parser.add_argument("commits", nargs="+", help="the thread's own commits (any order)")
    parser.add_argument("--span", metavar="START..REF", help="the task's seed.commit..seed.reference, for comparison")
    args = parser.parse_args(argv)

    total, game, files, lines, systems = own(args.repo, args.commits)
    print(line(f"thread ({total} commit(s) given)", game, files, lines, systems))
    floors = [(game, vg.MIN_THREAD_COMMITS, "game commits"), (len(files), vg.MIN_THREAD_FILES, "game files"),
              (lines, vg.MIN_THREAD_CODE_LINES, "code lines"), (len(systems), vg.MIN_THREAD_SYSTEMS, "systems")]
    short = [f"{have} {what} (floor {need})" for have, need, what in floors if have < need]
    print("  below the floors on its own: " + "; ".join(short) if short else "  meets every floor on its own")
    if args.span:
        start, _, ref = args.span.partition("..")
        if not (start and ref):
            raise SystemExit("--span takes START..REF")
        s_commits, s_files, s_lines, s_systems = span(args.repo, start, ref)
        print(line("span", s_commits, s_files, s_lines, s_systems))
        if s_lines:
            print(f"  the thread's own commits are {round(100 * min(lines, s_lines) / s_lines)}% of the span's code "
                  f"lines and {len(files & s_files)} of its {len(s_files)} game files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

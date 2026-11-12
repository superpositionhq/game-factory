"""A `judge` check's screenshots, saved for a person or a local session to look at (docs/task-probes.md, 3.2).

Nothing here asks a model. The task check and the task try play each judge check's plays on their sides (check.Side,
the same plays the probes use) and save the screenshots the cloud's judge would be shown, so whoever runs the check
looks at them and answers the rubric:

- a judge with its own `plays` is shown each play's `shots` evenly spaced screenshots (taken at seconds x (i + 0.5) / N
  by the plugin; a play another judge asks more of is played with the most asked, and `shots` of them are picked
  evenly through), and every screenshot its `shot` inputs take by name, in the order taken;
- a judge with no plays is shown the shared idle play ("look", 20 s, 6 screenshots) and the drive (22 s, 8);
- a judge is shown 20 screenshots of a side at most.

`save` writes them under <folder>/<check>/<side>/<play>_<nn>.png with <folder>/<check>/ask.md (the brief, the question,
the rubric, what each picture is); with `blind`, a copy of two sides under blind/A and blind/B whose mapping is
blind/key.json, so the looker can answer before knowing which side is which."""

import json
import random
import re
import shutil
from pathlib import Path

from . import tasks

JUDGE_IMAGES = 20  # a judge check's screenshots of one side at most (the grader's own limit)
PLAY_SHOTS = 5  # a judge's screenshots of each of its own plays unless its `shots` says
SHARED = {"look": ("idle play, 20 s, no input", 20, 6), "drive": ("scripted drive, 22 s", 22, 8)}
EVEN_SHOT = re.compile(r"^shot_\d{2,3}\.png$")  # an evenly spaced screenshot; any other is one a `shot` input took
PASS, REQUIRED = 0.6, 0.5  # the judge's pass mark: weighted score at least PASS, no required item below REQUIRED
PENDING = "shots saved for {sides}, answer needed"


def judge(c):
    """A `judge` check with its defaults: `plays` (task plays with theirs), `shots`, `before`, `reference`, `route`."""
    out = dict(c)
    out["plays"] = [tasks.play(p) for p in c.get("plays") or []]
    out.setdefault("shots", PLAY_SHOTS)
    out.setdefault("before", False)
    out.setdefault("reference", False)
    out.setdefault("route", None)
    out["rubric"] = [{"key": i["key"], "criterion": i["criterion"], "required": bool(i.get("required", False)),
                      "weight": int(i.get("weight", 1))} for i in c.get("rubric") or []]
    return out


def judges(task):
    """The task's `judge` checks (not code or actions judges), in order, with their defaults."""
    return [judge(c) for _, c in tasks.checks(task) if c["kind"] == "judge"]


def play_shots(task):
    """{task play name: the evenly spaced screenshots taken of it}: the most any judge check naming it asks, so one
    play serves each (and the probes that name it)."""
    found = {}
    for c in judges(task):
        for p in c["plays"]:
            found[p["name"]] = max(found.get(p["name"], 0), c["shots"])
    return found


def plays(check):
    """What a judge check is shown of a side, in order: [(play, label, shots)], `play` "look", "drive" or a task play,
    `shots` how many of its evenly spaced screenshots (None: every one taken)."""
    if check["plays"]:
        return [(p, f"task play {p['name']}, {p['seconds']} s", check["shots"]) for p in check["plays"]]
    return [(name, label, None) for name, (label, _, _) in SHARED.items()]


def spread(items, count):
    """`count` of `items`, evenly through them and in their order (all of them when there are no more)."""
    items = list(items)
    if count is None or len(items) <= count:
        return items
    return [items[min(len(items) - 1, int((i + 0.5) * len(items) / count))] for i in range(count)]


def even_times(seconds, count):
    """When the plugin takes a play's `count` evenly spaced screenshots: at seconds x (i + 0.5) / count."""
    return [round(seconds * (i + 0.5) / count, 2) for i in range(count)]


def taken(probe, files):
    """A play's screenshots by name, in the order taken, each once and only those it wrote: the probe's list, else the
    PNG files it left (sorted)."""
    names = (probe or {}).get("screenshots") if isinstance(probe, dict) else None
    if not isinstance(names, list):
        names = sorted(n for n in files if n.lower().endswith(".png"))
    return [n for n in dict.fromkeys(n for n in names if isinstance(n, str)) if n in files]


def chosen(names, shots):
    """The screenshots of one play a judge is shown: `shots` of the evenly spaced ones (shot_NN.png), evenly through
    them, and every named one, in the order taken."""
    even = [n for n in names if EVEN_SHOT.fullmatch(n)]
    keep = set(spread(even, shots)) | {n for n in names if n not in even}
    return [n for n in names if n in keep]


def selection(check, played):
    """[(play name, label, [(file name in the play, saved name)])] of one side, 20 screenshots at most in all.
    `played`: {play name: (probe dict or None, {file: bytes})} of the plays made (a missing play shows nothing)."""
    out, left = [], JUDGE_IMAGES
    for play, label, shots in plays(check):
        name = play if isinstance(play, str) else play["name"]
        probe, files = played.get(name, (None, {}))
        picked = chosen(taken(probe, files), shots)[:left]
        left -= len(picked)
        out.append((name, label, [(n, f"{name}_{i + 1:02d}.png") for i, n in enumerate(picked)]))
    return out


def named(file):
    """A named screenshot's name (shot_<name>.png), or None for an evenly spaced one."""
    return None if EVEN_SHOT.fullmatch(file) else file[len("shot_"):-len(".png")] if file.startswith("shot_") else file


def blind_key(sides, rng=None):
    """{"A": side, "B": side} for two sides, in an order the looker can't guess."""
    order = list(sides)
    (rng or random.SystemRandom()).shuffle(order)
    return dict(zip("AB", order))


def ask_text(task, check, sides, notes=(), blind=False, saved=None):
    """ask.md: the brief, the question, the rubric, the plays and their pictures, how to answer."""
    rubric = "\n".join(f"| {i['key']} | {'yes' if i['required'] else 'no'} | {i['weight']} | "
                       f"{i['criterion'].replace('|', '/')} |" for i in check["rubric"])
    lines = [f"# Judge check {check['name']}", "",
             f"{'Required' if check.get('required', True) else 'Optional'} check, weight {check.get('weight', 1)}.",
             "", "## The brief", "", task.get("instruction", "").strip(), "", "## The question", "",
             check["question"].strip(), "", "## The rubric", "",
             f"Score each item from 0 (not at all) to 1 (fully) from what the pictures show; an item they can't show "
             f"scores 0. A side passes when its weighted score is at least {PASS} and no required item is below "
             f"{REQUIRED}.", "", "| key | required | weight | criterion |", "| --- | --- | --- | --- |", rubric, "",
             "## The pictures", ""]
    for play, label, shots in plays(check):
        name = play if isinstance(play, str) else play["name"]
        if isinstance(play, str):
            _, seconds, count = SHARED[play]
            what = f"every one of its {count} screenshots, at {', '.join(f'{t:g}' for t in even_times(seconds, count))} s"
        else:
            inputs = play["inputs"]
            names = [i["shot"] for i in inputs if "shot" in i]
            what = (f"{len(inputs)} scripted input(s)" if inputs else "no input") \
                + (f", map {play['map']}" if play["map"] else "") + (f", flags {' '.join(play['args'])}" if play["args"] else "") \
                + f"; {shots} evenly spaced screenshots, about one every {play['seconds'] / shots:.2g} s" \
                + (f", and the named ones: {', '.join(names)}" if names else "")
        lines.append(f"- `{name}_NN.png`: {label}: {what}.")
    lines += ["", "Each side's folder holds the pictures in time order, play by play."]
    if blind:  # a side's picture count or its notes would tell a blind scorer which side is which
        lines.append("Which pictures each side has, and any side's notes, are in `sides.md`: open it with the key.")
    else:
        lines += side_lines(saved)
    if check["before"] or check["reference"]:
        shown = [x for x, on in (("the start as BEFORE", check["before"]), ("the reference as REFERENCE",
                                                                             check["reference"])) if on]
        lines += ["", f"In the cloud the judge is also shown {' and '.join(shown)}, beside the developer's game, the "
                      "same plays at the same moments."]
    if check["route"]:
        lines += ["", f"In the cloud the judge also plays the developer's route file `{check['route']}` and then shows "
                      "4 of the idle play's 6 pictures. That play isn't made here."]
    lines += ["", "## How to answer", ""]
    if blind:
        lines += ["`blind/A/` and `blind/B/` hold the same pictures as two of the side folders; which is which is in "
                  "`blind/key.json`. Score every rubric item for A and for B first, each as if it were the developer's "
                  "game, then open the key.", ""]
    if set(sides) >= {"start", "reference"}:
        lines += ["The task is VALID on this check only when the start fails every required rubric item and the "
                  "reference passes every one. Write the scores of both sides in the task's notes."]
    elif "agent" in sides:
        lines += ["Score the agent's game the same way, before calling the task too easy or held: the try's own "
                  "number leaves judges out."]
    if notes and not blind:
        lines += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(lines).rstrip() + "\n"


def side_lines(saved):
    """One line per side: its pictures, by file name and what each is."""
    lines = []
    for side, rows in (saved or {}).items():
        files = [f"{s} ({'named ' + named(f) if named(f) else f})" for _, _, picked in rows for f, s in picked]
        lines.append(f"- `{side}/`: {len(files)} picture(s)" + (": " + ", ".join(files) if files else ""))
    return lines


def save(task, check, played, folder, blind=False, notes=(), rng=None):
    """Save judge check `check`'s screenshots of each side under <folder>/<check>/: `played` {side: {play name: (probe,
    files)}}. With `blind` and two sides, the blind copy. Its record: {"sides": {side: [saved names]}, "blind": whether
    there is a blind copy (its key stays in its folder), "notes", "status"}."""
    base = Path(folder) / check["name"]
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    saved, notes = {}, list(notes)
    for side, made in played.items():
        rows = selection(check, made)
        saved[side] = rows
        (base / side).mkdir()
        for name, _, picked in rows:
            files = made.get(name, (None, {}))[1]
            for f, s in picked:
                (base / side / s).write_bytes(files[f])
            if name not in made:
                notes.append(f"{side}: {name} wasn't played")
            elif not picked:
                notes.append(f"{side}: {name} took no screenshots")
    key = None
    if blind and len(saved) == 2:
        key = blind_key(saved, rng)
        # Only pictures both sides have go in: a side with fewer (a play cut short) would be told apart by its count.
        both = set.intersection(*({p.name for p in (base / side).iterdir()} for side in saved))
        for side in saved:
            only = sorted({p.name for p in (base / side).iterdir()} - both)
            if only:
                notes.append(f"{side}: {len(only)} picture(s) the other side lacks, left out of the blind copy "
                             f"({', '.join(only)})")
        for letter, side in key.items():
            (base / "blind" / letter).mkdir(parents=True)
            for name in sorted(both):
                shutil.copy2(base / side / name, base / "blind" / letter / name)
        (base / "blind" / "key.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    (base / "ask.md").write_text(ask_text(task, check, list(saved), notes, key is not None, saved), encoding="utf-8")
    if key is not None:  # what would unblind the scorer, kept beside the key
        (base / "sides.md").write_text("\n".join(["# Each side's pictures", ""] + side_lines(saved)
                                                 + (["", "## Notes", ""] + [f"- {n}" for n in notes] if notes else []))
                                       + "\n", encoding="utf-8")
    return {"sides": {s: [n for _, _, p in rows for _, n in p] for s, rows in saved.items()},
            "blind": key is not None, "notes": notes,
            "status": PENDING.format(sides="/".join(saved) or "no side")}


def line(name, record):
    """The line a run prints and keeps for one judge check."""
    return f"judge {name}: {record['status']}"

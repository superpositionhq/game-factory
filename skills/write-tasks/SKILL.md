---
name: write-tasks
description: How to write the tasks a game ships with (Tasks/ on the repo's orphan tasks branch, never on main, one GameTask JSON per task, at least 5 and up to about 10 per game, all hard but for at most one medium) so an agent can be given them in the game-creation environment: the tasks branch and its worktree, the one bar every task meets (a long thread of multiple edits from the game's real history: many commits, many files, several systems, every task medium or hard, never easy or a single fix), the four kinds as where a thread comes from, picking seed.commit (the parent of the thread's first attempt) and seed.reference (its final accepted fix), observation-only briefs, play_map, milestones and deterministic probe checks (pass/fail never by pixels; judges only for asked looks; one required probe per issue), limits, and what keeps a task gradable and unleaked. Use when a game session writes, moves or reviews tasks, and before calling a game complete.
---

# Writing a game's tasks

A game is complete when its repo's orphan `tasks` branch has `Tasks/`: tasks an LLM agent can be given on this game,
fair, checkable and not leaked. One file per task, `Tasks/<game>-<kind>-<slug>.json` (`kind`: `fix`, `corr`, `feat`,
`change`), in the task format `GameTask`
([docs/schemas/game-task.schema.json](../../../docs/schemas/game-task.schema.json), game-task/1), with `"name"` equal
to the file stem (run and grade ids depend on it; never rename a shipped task). At least 5 and up to about 10 per game, every one a
long thread of multiple edits (section 1). A game with fewer than 5 tasks is rejected, and a short task never fills the count: a game whose history does not hold 5 long threads is not ready. The tasks branch is the single source: tasks are loaded as `Tasks/*.json` from the
repos' tasks branches, and the packager ships them in the dataset split into the agent's and the grader's halves
(docs/game-format.md). Write tasks with this skill and the game-factory tools only, never with another skill
(AGENTS.md, "Only these skills").

## 0. Where tasks live: the orphan `tasks` branch

**Task work never goes into the game's history.** Tasks live on a branch `tasks` of the game repo that shares no
history with main, checked out as a git worktree **outside** the game folder (`<root>/tasks/<slug>`). The branch holds
`Tasks/<game>-<kind>-<slug>.json`, a short `README.md` (what the branch is), and optionally `tasks-workflow.jsonl`
(one row per task written, `op:"task.write"`, `target:"Tasks/<name>.json"`; never in main's `workflow.jsonl`).

Create the worktree once. When the branch does not exist yet (on origin either):

```bash
git -C <root>/games/<slug> worktree add --orphan -b tasks <root>/tasks/<slug>
```

With an older git that lacks `worktree add --orphan`:

```bash
git -C <root>/games/<slug> worktree add --detach <root>/tasks/<slug>
git -C <root>/tasks/<slug> checkout --orphan tasks
git -C <root>/tasks/<slug> rm -rf .
```

When the branch already exists on origin (another machine or session made it):

```bash
git -C <root>/games/<slug> fetch origin tasks
git -C <root>/games/<slug> worktree add <root>/tasks/<slug> tasks    # creates local tasks tracking origin/tasks
```

Then write the tasks in `<root>/tasks/<slug>/Tasks/`, commit there (`git -C <root>/tasks/<slug> commit`) and push:
`git -C <root>/tasks/<slug> push -u origin tasks` the first time, `git push` after.

- Never add `Tasks/` (or any task file) to main, never merge or cherry-pick between `tasks` and main, never point
  main's code, docs, README or `workflow.jsonl` at the tasks branch. The validator fails a repo whose main tracks
  anything under `Tasks/` or whose `tasks` branch shares history with main.
- The recording and live-replay hooks ignore commits on the `tasks` branch, and the delivered history leaves it out,
  so committing tasks costs the game's record nothing.
- Seeds (`seed.commit`, `seed.reference`) are commits of main's history (ancestors of main's head) or of the task's
  own start branch `starts/<task name>` (section 2, "Starts on the engine"); pick them in the game checkout
  (`git -C <root>/games/<slug> log`), never on the tasks branch.

Check every task after committing it on the tasks branch:
`python <GF_ROOT>/game-factory/tools/validate-game.py <GF_ROOT>/games/<slug>` (it reads the committed `tasks`
branch, else `origin/tasks`, through git: schema, the format's extra rules, name = file name, seed commits on
main or the task's `starts/<name>` branch and on UE 5.7, the branch an orphan, nothing under `Tasks/` on main). Commit tasks
as you go, like any work (commit-always skill), but on the tasks branch only. Then run the task check on all of them
in one background run (section 5, `tools/task-check.py`): only VALID tasks ship, so fix or remove every INVALID one
before the game is packaged.

## 1. The bar: long threads of multiple edits, nothing else (owner, 2026-11-02)

**The only tasks that meet our requirements are long threads of multiple edits.** A long task keeps one clean run of a
strong agent working about 25 minutes or more. That length is a guide, not a requirement (owner, 2026-11-09): what
counts is that a strong agent can't solve it easily. You
judge this in the session from the thread itself (section 6); we measure it on every submitted task. A task is a stretch of the game's
real history where its own sessions needed many commits, several attempts or several rounds of directions, touching
many files across several systems, before the outcome held. Strong agents finish a single fix, one cause in one
place, in minutes, however long the original took; such a task is worthless to us and never ships, not even as an
"easy" one. A task is `"difficulty": "hard"`, with the tag `long-thread`. At most one of a game's tasks may be
`"medium"` (a task that names no difficulty counts as medium); with two or more the game is rejected.

A thread qualifies only when all of these hold (the validator enforces the numbers, section 6):

1. **Many edits.** From `seed.commit` to `seed.reference`, at least 4 commits change the game itself (`Source/`,
   `Content/`, `Config/`, `Plugins/`, the `.uproject`), and the reference changes at least 5 game files against the
   start, with at least 100 code lines added plus removed. Status, docs and `workflow.jsonl` commits don't count.
   Assets and binary files don't count as code lines.
2. **Several systems.** The change spans at least two of: C++ (`Source/`), config (`Config/`, the `.uproject`), plugins,
   levels (`.umap`), materials and textures (`M_`, `MI_`, `MF_`, `T_`), Blueprint or UMG assets (`BP_`, `WBP_`, `ABP_`,
   `UI_`), data assets or tables (`DA_`, `DT_`), other assets. The validator counts them by path and name prefix. A long thread confined to one function is a
   short task in disguise.
3. **Several outcomes.** At least 3 required outcome probes, one per issue the thread settled, so partial work earns
   partial credit (a compound ticket). A thread that settled only one observable thing is rarely long enough.
4. **The first attempt didn't hold, or the cause is far from the symptom.** The thread had a fix that was undone,
   complained about again ("still too low") or broke something else; or the symptom shows in one system and the cause
   sits in another (a HUD symptom from a data asset, a camera symptom from collision channels, a crash only in the
   packaged build, an intermittent or timing bug, a regression from an earlier change).
5. **Checkable by the grader.** Every required outcome is measurable in the grader's own plays: a scenario
   (`play_map` options at the seed) that triggers the moment, or a task play whose scripted keys reach it (key names,
   mouse buttons included, but no mouse movement). A thread no probe can measure is not a task.

**Never make a task easier (owner, 2026-11-04; permanent).** After a task is first written, these are banned if they
lower the bar: widening a threshold or window, making a required probe optional, removing a probe, removing a
requirement from the brief or narrowing what it asks. A plainly broken probe may be fixed only so that it asks at least
as much as the brief. Otherwise drop the whole task and say so; fewer tasks is an acceptable result.

The four kinds say where the thread comes from; each is a long thread, never one commit:

| kind | the thread | `seed.commit` | `seed.reference` |
|---|---|---|---|
| `bug_fix` | a bug the game's sessions fixed over several attempts or commits | the parent of the first attempt | the final fix that held |
| `correction` | a person's direction (`user.direction` rows) that took several rounds or follow-ups to satisfy | the last commit before the first direction | the commit that answered the last round |
| `feature` | a mechanic the game itself built over a span of commits (code, assets, input, HUD) | the parent of the span's first commit | the span's last commit, once it played |
| `change` | a look or content pass built over a span (lighting plus post plus materials, a camera rework, a HUD restyle) | the parent of the span's first commit | the span's last commit |

`seed.reference` is always set: a task without the game's own accepted end of the thread is not a task. Merge, don't
split: a chain whose first fix didn't hold is one task, not two; a direction with several issues fixed in several
commits is one compound task with a probe per issue; neighbouring fixes of the same system in the same stretch belong
together. A separate thread in the same stretch (another system, other issues) is its own task, even over the same
commits (section 2).

Not a task: a single fix or a single commit, a one-setting change, a bug with one cause in one file, status chatter,
process rules, questions, praise, a fix that is only a re-import of assets the start does not have, a sweeping pass
resting on a pack imported later, anything whose outcome neither play nor code can show. If a game's history has fewer
than 10 qualifying threads, ship fewer tasks.

**Where strong agents fail (measured on our tries, 2026-11).** Most tasks a strong agent missed had the code
written and the outcome never checked in the running game. Prefer threads that settled these, and give each one its
own probe in a play that reaches the moment:

- **Feedback that must show in play**: a HUD readout, a marker, a sound or an effect when the event happens (a play
  that triggers the event, then `ui`, `drawn`, `audio`, `lit`);
- **A look change**: colours, materials, dressing, HUD art (`drawn` base colour, `lit`, `screen`, `pieces`, relative to
  the start);
- **Menu, pause and back flows**: Escape or Back closes what it opened and returns where it came from (a task play
  with the keys, then `ui`);
- **A tuned outcome judged in play**: seen or not seen at a distance, holds or breaks under load, passable, winnable
  (a teleport to the spot, then the outcome);
- **Many small requirements in one span**: one probe each, so a single dropped item shows.

Threads that strong agents solve in minutes: one system's logic, a feature whose outcome the code alone shows, a brief
that points at the system. Hiding the list of problems (a brief that reports the symptoms a player meets, not a
checklist) lengthens a run without changing what it misses.

**Finding threads.** Walk the history for clusters: `git log --stat` around a feature, runs of commits on the same
files (`git log --format=%h -- <path>` piled up in a short window), several `user.direction` rows on one topic
(the workflow rows' `"direction"` links), fixes followed by "still", "again", "regressed" or a revert, ports that broke
a system and the commits that mended it. Read the whole span before picking its ends.

## 2. Picking the commits

### Starts on the engine (owner's rule, 2026-10-19)

The checker builds a start exactly as committed, on UE 5.7: it never ports, patches or rewrites a game, and
it refuses a start that isn't a 5.7 project. So `seed.commit` and `seed.reference` must both be commits whose
`.uproject` says `"EngineAssociation": "5.7"` and that build as they are (the validator checks the engine). A real fix
made before the game's 5.7 port can't be used as it was; give it a start on 5.7 instead:

- **B** = main's head (5.7). **S** (`seed.commit`) = B with the change taken back out of the game itself (`Source/`,
  `Content/`, `Config/`, `Plugins/`, the `.uproject`), re-created by hand where later work moved the code: the issue
  must really be back, and S must still compile. Every other path of S (`workflow.jsonl`, `Scripts/`, `Docs/`,
  `README.md`, manifests, tools) is exactly as at the old pre-fix commit, so nothing in the start records or
  regenerates the fix. **R** (`seed.reference`) = a child of S whose tree is B's (`git commit-tree <B^{tree}> -p S`).
- Both live on the branch `starts/<task name>` (pointing at R), pushed with the game; the dataset ships main's
  history and every `starts/` branch, and no other branch, so the delivered history holds them. A seed on any other
  branch is not delivered.
- A binary asset (.uasset/.umap) goes back to its pre-fix version only if no later commit changed it; otherwise
  re-create the issue in code or config, or pick another task.
- For a thread, "the change" is the whole thread: S takes every commit of it back out, not only the last one, and the
  thread's commits on main (its count and files) are what qualify it; note them in the task's `tasks-workflow.jsonl`
  row (`"thread"`: first and last commit of main).
- A thread made after the port needs none of this: the parent of its first attempt and its final fix are both 5.7
  commits of main.

- **Read the code at `seed.commit`** and confirm the issue is there (the reference diff's removed lines, or a search).
- **The thread's real ends are often not the commits that say so**: a descriptive commit may touch only
  `workflow.jsonl` while the code is in the WIP commit before it; the last attempt may land a commit or two after a
  port. Use `git show --stat` around that time and the workflow rows that link the direction (`"direction"`). Start
  before the first attempt, so the agent faces every issue the thread settled, and end at the commit after which no
  more work on it followed.
- **The reference must build and run**: the grader plays it beside the agent's result. If the last fix crashed until a
  later commit, extend the thread to the later one.
- **Chains and splits merge**: a person complained again after a fix ("still too low"): one task from before the first
  fix to the last. A direction with several issues fixed in separate commits: one compound task, one required probe
  per issue.
- **Spans may overlap; issues may not** (owner, 2026-11-05). Two tasks may share commits, overlap or nest: one task's
  start or reference may be another's, and a long feature span may contain a shorter thread that settled different
  issues. Different threads that ran at the same time (a camera rework during a HUD pass) are separate tasks over the
  same commits. What never repeats is an issue: two tasks never test the same outcome, so dedupe against the game's existing tasks by issue (their briefs and
  required probes), not by commits. Merging still wins over splitting one thread into short tasks (section 1).
- **Measure the thread on its own commits** (owner, 2026-11-05). The validator measures everything from `seed.commit`
  to `seed.reference`, so a short thread inside another thread's stretch can pass the floors on the other thread's
  work. Which commits are the thread's own is your call (the commits that answer its directions or work on its
  issues); list them and count them:
  `python <GF_ROOT>/game-factory/tools/thread-stats.py <GF_ROOT>/games/<slug> <commit> <commit> ... --span <seed.commit>..<seed.reference>`
  (git only, seconds). A thread whose own commits are below the floors (section 6) is too short, whatever the span
  says: extend it, merge it with its neighbouring issues, or drop it. When you tell the person a task is ready, give
  its own line from the tool (commits, files, code lines, systems).
- Binary-only fixes are fine (the agent can make the same change through editor scripts or C++); drop one only when
  its outcome cannot be seen.

## 3. The instruction (the brief)

Write it from the context, never by quoting a person: no quotes, typos, capitals, profanity, "the owner said" or chat
wording. The reader is a capable developer who has never seen the game.

**Every brief is only an observation**: what a player or QA sees, in plain words, for every issue the thread settled.
It names no cause, no place to look, no file, system, class or asset, and no mechanism ("the camera feels jammed
against the ship", not "the obstruction sweep counts the sea"). It never says how many changes are needed or that the
issues are related. Leave out the play_map line, which the harness adds.

- **bug_fix**: a QA bug report listing each symptom: what happens, how to reproduce it, what is expected. Code
  identifiers only inside a quoted compiler or crash-log line, which is what a player or a log shows.
- **correction**: what is wrong and how a player sees it, item by item, then the wanted outcome.
- **feature / change**: a producer's ticket: what and why, how the player uses it (which key), the behaviours and
  looks wanted, what must still work. Close with the art bar: the project's own assets and engine features, no
  primitive placeholder shapes, no debug text.
- Describe the controls the player needs; the harness tells the agent which map QA plays (`play_map`).
- Never name the studio, its pipeline or its tools. Never describe the fix or any step of the thread.

## 4. `play_map`

The game's default map is usually a title menu that simulated keys cannot leave, so a task almost always needs
`play_map`: the map path and URL options that start straight in the gameplay where the issue shows (e.g.
`/Game/Maps/L_Level?Scenario=2`). Read the GameMode's option parsing at `seed.commit` and check the map exists there.
Every grader play opens it (boots, idle and drive, the route, the before and reference plays).

## 5. Milestones and checks: deterministic probes decide

**Pass/fail is decided by checks the grader computes itself** (the owner, 2026-10-19): `build`, `boot`, `log_absent`
and **`probe`** checks, and nothing is graded from pixel statistics of the game's frames except the frame's mean
luminance (`screen`, the owner, 2026-11-06), whose threshold is always calibrated or relative to the start. Two judges
are required (the owner, 2026-11-11): `looks_as_asked`, whose rubric items are the brief's own look-and-feel asks, and
one in `still_works` of what must still look as it did (below). Every other judge (`judge`, `code_judge`,
`actions_judge`: taste, readability, code review, how the agent worked) stays a `"required": false` quality check. A
task still needs required probes the grader decides without a judge (section 6). The probe language, every play,
measure and threshold with the rules that gate a task, is the task author's contract
[docs/task-probes.md](../../docs/task-probes.md), checked by the schema
[docs/schemas/game-task.schema.json](../../docs/schemas/game-task.schema.json) and `tools/validate-game.py`.

Each milestone is a reward group; a run that gets part of the way earns part of the reward. **A no-op scores zero
(owner, 2026-11-04; permanent):** the score is the weighted share of checks passed, so every check the start already
passes takes `"weight": 0`: `builds`, `boots`, all of `still_works`, and any `log_absent` or `file_exists` true of the
start. They still gate: a run must pass the required ones to be solved. `validate-game.py` and the task check refuse a
task a no-op would earn anything on. The usual order:

1. `builds`: `build` (`editor_builds`).
2. `boots`: `boot` 60 s (`boots_clean`), `needs` the build.
3. `fixed` (bug_fix, correction) / `done` (feature, change): `probe` checks of the reported outcomes, `required`,
   `needs` `boots_clean`: at least 3, one per issue the thread settled (split them over several milestones, e.g.
   `fixed_hud`, `fixed_camera`, when the issues are separable). Each one fails at the start for the reported reason
   and passes on the reference. The required `looks_as_asked` judge goes here when the brief asks for a look.
4. `still_works`: probes that what must keep working still does (the player still moves, the HUD still shows, the
   level still loads its scenario), and a required judge with `"before": true` for what must still look as it did.
5. `quality` (optional, never required): a `judge` for taste items no probe can capture ("reads as a castle",
   readability of text over the scene), a `code_judge` for code quality, and the standard `actions_judge`
   `worked_well` (or `trace` probes, `"required": false`).

**Every look-and-feel ask in the brief gets a required `looks_as_asked` rubric item** (a review of delivered tasks
found the checks thinner than the briefs, look-and-feel asks most of all; the owner, 2026-11-11: such an ask gates the
task). Go through the brief ask by ask: what a probe can measure gets a probe; what only an eye can tell (reads
clearly, fits the style, looks like the thing it is meant to be) gets its own rubric item, `"required": true`, in one
required `judge` named `looks_as_asked`, with `"before": true` and `"reference": true` when the seed has a reference.
A judge can misread screenshots, so word each item concretely, decidable from the screenshots alone, so the unchanged
game scores 0 on it and any solution that meets the brief scores 1. What must still look as it did goes in a required
judge in `still_works` the same way. A judge is shown screenshots of the idle `look` and the `drive` on `play_map` and
nothing else, unless the check names its own plays. When what must be seen appears only after a task-specific key, in
another scenario or level, or past a title screen, give the check `plays`: up to 4 task plays that reach that state
(when a probe's play already does, reuse it under its name, written identically):

```json
{"name": "looks_as_asked", "kind": "judge", "required": true, "needs": ["boots_clean"], "before": true,
 "reference": true,
 "question": "With the upgrade menu open, does it read the way the request asks?",
 "rubric": [{"key": "costs_legible", "criterion": "Each upgrade's cost is legible against the panel behind it.",
             "required": true}],
 "plays": [{"name": "open_upgrades", "seconds": 10,
            "inputs": [{"t": 0.5, "key": "U", "press": true}, {"t": 0.7, "key": "U", "press": false}]}]}
```

The judge is shown 5 screenshots of each play, at 10, 30, 50, 70 and 90% of its `seconds`: time the inputs so the
state is on screen at those moments. A play also runs on the task's start (`"before": true`) and on the reference
(`"reference": true`), so it must run there too; a key that does nothing at the start is fine
([docs/task-probes.md](../../docs/task-probes.md), section 3.2).

**Motion is asked two ways.** Motion that is a number (eases instead of snapping, gentle, no sudden moves) is a probe:
a task play with `"every": 0.1` and a field over the window of the move, with `"agg": "step"` for the largest jump
between two samples (section 2.1 of the same doc). Motion that can only be seen (feet that slide, a trail) is a
`looks_as_asked` item with a short play and many `shots` (2-20 of each play, plays times shots 20 at most): a 5 s play
with `"shots": 20` is a frame every 0.25 s, screenshot i of N at `seconds` x (i + 0.5) / N.

A probe names one measurement and its threshold:

```json
{"name": "hero_on_ground", "kind": "probe", "required": true, "weight": 3, "needs": ["boots_clean"],
 "describe": "After the scenario starts, the hero stays on ground near the west kiln tower instead of falling under the town.",
 "play": "look",
 "measure": {"probe": "pawn", "field": "z", "window": [3, 18], "agg": "min"},
 "expect": {"op": ">=", "calibrate": 0.5}}
```

- `play`: `look` (20 s idle), `drive` (22 s: W 1-6 s, D 6-8 s, W 8-13 s with a jump at 9 s, A 13-15 s, W 15-21 s),
  a task play `{"name": ..., "seconds": ..., "inputs": [{"t", "key", "press"}]}` when the outcome needs other keys
  (F2, a fire button, a menu key), or `editor` for asset facts.
- `measure.probe`: `pawn` (track: x/y/z/speed/moved/dist), `camera` (distance/height/pitch/fov/occluded/
  pawn_on_screen), `actors` (select by class, tag, name, near; count, transform, extent, hidden, collision, speed,
  `prop:<Component>.<Property>` by reflection), `widgets` (visible, text, percent, has_brush), `ui` (what the HUD
  shows, whatever draws it: text, count, place of UMG, Slate and canvas elements alike;
  signature with agg changes for a readout that updates; number and clock for which way a readout or a timer
  moved, with agg rises/falls), `drawn` (what is drawn near a point or along a line, rendered: drawn, motion, base
  colour, a beam's reach), `light` (illuminance,
  exposure, brightness at a point), `grading` (the colour pipeline: cast, warmth, tint, saturation, contrast, grey),
  `spawns`, `log`, `asset` (editor: material_default, material:<prop>, mesh_collision, asset properties).
- `expect`: a literal (`{"op": ">=", "value": 1}`) for facts (counts, booleans, "not the default material"), or
  `{"op": ">=", "calibrate": 0.5}` for continuous quantities: the grader measures the start and the reference in the
  grading environment and puts the threshold that fraction of the way from start to fix; `op` points to the fix's side.

Write probes from the game's own code at `seed.commit`: the real class names, actor tags, map paths, widget names and
components. **Never a name only the reference has** (a class, tag, widget, map or asset the thread itself created):
another fair build names it otherwise and reads as absent. Select what the thread creates by what it does or where it
is (`has`, `near`, `ui` with a `rect` or text, `drawn`, `lit`, `changed`); `validate-game.py` refuses a required probe
that names something the start lacks and the reference has. **Test the outcome a player sees, never the implementation**: another valid fix
must pass ("the hero stands on ground", "the stone breaks the wall piece it hits", "the light reaching the tunnel
floor times the camera's exposure is brighter", not "SpawnZ is 92" or "the function was changed"). Lighting and
colour are measured from the engine (`light`, `grading`), never from screenshots. `describe` says the assertion in
plain words; it is shown in the grade, never to the agent. Check names are unique and `needs` only names earlier
checks; calibrated probes, `code_judge` and `"reference": true` judges need `seed.reference`.

A task is valid only when it passes the task check: its start fails the task and its reference fix passes every
required check, and every required `still_works`
probe already passes at the start. Write the probes per [docs/task-probes.md](../../docs/task-probes.md), then
check the game's tasks **together, in one background run** (owner, 2026-11-05: one run builds a commit several tasks
share once, and the person can leave it running and come back). Write and commit every task first, then start the
check as its own process so it outlives your turn and no tool timeout cuts it short (PowerShell, under either agent):

```powershell
Start-Process python -WindowStyle Hidden -WorkingDirectory <GF_ROOT>\game-factory `
  -ArgumentList 'tools\task-check.py', '<GF_ROOT>\games\<slug>', '--all' `
  -RedirectStandardOutput <GF_ROOT>\games\<slug>\.task-checks\run.out `
  -RedirectStandardError <GF_ROOT>\games\<slug>\.task-checks\run.log
```

Create `.task-checks` first if it doesn't exist. Tell the person it is running, roughly how long (about 20-60 minutes
a task, less where tasks share commits), and that they can leave it. Read
`<GF_ROOT>\games\<slug>\.task-checks\progress.txt` to see where it stands (rewritten after every task; it says
`finished` at the end); never start a second run of the same game while one is going. A recheck of the tasks you
fixed takes `--task <name>` once per task instead of `--all`. `--task <path>/Tasks/<name>.json` checks a file not
committed yet ([docs/task-check.md](../../docs/task-check.md)). The check builds each start and reference with the
probe plugin, plays them and writes VALID or INVALID per task with the reasons and the measured values. **A task ships only when the task check says VALID**; for INVALID, fix the task (the
docs' "Common reasons and fixes"), never the threshold toward what the start happens to measure.

**The check asks no model, so you answer the judges.** For every `judge` check it plays the check's plays on the start
and on the reference and saves the screenshots the cloud's judge would be shown under
`.task-checks\<task>\judge-shots\<check>\` (`start\`, `reference\`, and a blind copy in `blind\A\` and `blind\B\`
whose sides are in `blind\key.json`), with `ask.md` holding the brief, the question and the rubric; `progress.txt` says
`judge <check>: shots saved for start/reference, answer needed`. Before you call a task with a required judge VALID,
look at the pictures yourself, blind: score every rubric item for A and for B from 0 to 1 first, then open the key.
The start must fail every required rubric item (below 0.5) and the reference must pass every one; if either doesn't,
reword the item or fix the plays so the pictures show the state, never by asking less of the solution. Write both
sides' scores in the task's notes (its `tasks-workflow.jsonl` row).

### Every ask has a check

Before the game is packaged, read each task you wrote, its instruction against its checks, yourself; no tool or
reviewer does this for you. Lab reviews every task the same way at submission and sends the game back when an ask has
no check at all, naming the task and the sentence. Fix what you find in the task before it is packed:

- **Go through the instruction sentence by sentence.** The game's description, the controls line and the art line are
  context, and so are a bug report's symptom, cause and steps to reproduce; they ask nothing. What should now be
  different is an ask (in a bug report, the expected behaviour); what must stay as it is is a keep.
- **Every ask has a check that would fail if that ask alone were not done**: a required probe for each key, direction,
  scenario or case it lists; a number it states held on both sides; a look-and-feel ask as a required
  `looks_as_asked` rubric item in the ask's own words, with the judge's own `plays` when the state must be reached
  first; motion as a probe sampled every 0.1 s with `agg` `step`, or a required judge with a run of `shots`.
- **A keep that names a thing** ("the boss bar still starts full") has a required `still_works` check reading that
  thing; a bare "everything else keeps working" is covered by any required `still_works` check.
- **Never cover an ask with an optional probe, a `build` or `boot` check, or the `worked_well` actions judge alone.**
- **An ask that shows only after a contact** (a blow landing, getting hit, a stun, the last foe of a group falling) is
  staged, never left out because "no fixed play guarantees the contact": `pin` the foe or target ahead of the player
  (a target the build invents: the nearest movable drawn thing near the player) and press the task's own attack key;
  `set` a start-named health only to set the fight up; `damage` for a hit taken at a known moment where the game
  takes damage through the engine; `where` to pick the live ones (docs/task-probes.md, section 1.3). Read the result
  deterministically: a state change in a probe one sentence explains; a hit stop by `world` `time_dilation` or
  `frozen`, never a judge (no screenshot shows it); a stagger, knock-back or interrupted action by `montage`, the
  actor unable to move, or its distance from the attacker, never a judge. What it looks like (sparks, colours, glow)
  goes to the required visual judge on named frames across the contact. Names come from the start commit; `set` and
  `where` only on members the task does not ask to change. Where the nearest movable thing is not surely the target,
  the ask is listed as not testable.
- **Hints, never answers (owner, 2026-11-11).** An instruction may hint, in the ticket's own words, at what a player
  must see, hear or meet, or what must exist in the world, and may say that damage goes through the engine's damage
  interface. It never says how the build names or stores it: no class, property, function, tag, asset or file name,
  nothing that is really the check's read target dictated to the solver.
  - Good: "Every blow that lands throws sparks and a short pause." "A training post stands in the yard to practise
    on." "Hits reach her through the engine's damage events."
  - Refused: "Add an actor of class AsTrainingPost to the yard." "Keep the enemy's health in a property called
    Health." "Tag each generator Generator so QA can find it."
  _(failure: tasks were reworked by writing the check's read target into the ticket, which hands the solver the
  answer)_
- **A sound ask** is checked by a sound starting when the event happens: `audio` `started_audible` near the source,
  in a window right after the event; `sounds` or `repeats` (by asset name) when the ticket asks for distinct sounds,
  "each gun has its own sound". What the sound is, how it sounds, is never checked. New games import every sound
  (game-session skill), so every sound has an asset name.
- **An ask that cannot be checked fairly** comes out: rewrite the instruction so it no longer asks for it, rather than
  ship an ask nothing checks. The instruction stays plain prose, never fields.

## 6. Difficulty, limits and what the validator enforces

- `difficulty` is `hard` (at most one of the game's tasks may be `medium`, never `easy`), and `tags` hold `long-thread`.
- `limits`: 400 turns, 480 min, 150 USD, 1800 s tool timeout unless the task needs more; a long thread needs room.
- `tools/validate-game.py` fails a task that is `easy`, has no `seed.reference`, has fewer than 3 required probes
  outside `still_works`, or whose reference changes fewer than 5 game files, fewer than 100 code lines or fewer than 2
  systems against its start; for a seed on main it
  also fails fewer than 4 game-changing commits from `seed.commit` to `seed.reference`, and any required probe that
  names a class, tag, map or asset the reference has and the start doesn't (section 5). These are floors, not targets:
  pick the longest threads the history has.
- **Judge difficulty in the session; never run the task with another agent** (owner, 2026-11-05: the try took up to
  25 minutes a task and slowed contractors down). Don't run `tools/task-try.py` or start a fresh Claude Code or Codex
  session on a task. Before committing, review each task against section 1 here, with the person: would a strong
  agent given only the brief and the start solve it easily (25 minutes is a guide, not a cut-off)? It would when the brief points at one
  place, the issues share one obvious cause, or the reference diff is mostly one file or one system. If so, extend the
  thread back to an earlier attempt, merge it with its neighbouring issues, or drop it. Tell the person which tasks you
  judged long enough and why, in a line each. We try every submitted task with a strong agent and measure its time;
  that grade decides.

Probes may measure the cause's effect directly, since the agent never sees them.

Wording: neutral and technical, for the game's people and creatures as for the rest. Describe meshes, bones, poses,
hits and reactions. Never use gore, injury or body-horror words ("crumpled body", "cut neck"); a cloud content
filter rejects such briefs and rubrics.

## 7. What must never reach the agent

The agent sees only the brief and the game at `seed.commit` (a commit of main, so without the tasks branch) as a fresh
repository without history, `Tasks/`, `History/` or `Dataset/` (the harness rule: those hold every task's checks and the reference fixes). The grader's
half (`milestones`: probes, rubrics, questions, `log_absent` patterns; and `seed.reference`) never reaches it. So:

- the instruction holds nothing of the grader's half and does not describe the fix;
- nothing else at `seed.commit` should spell out the answer (a design-doc "known issues" line naming the cause, a
  comment saying how to fix it): if it does, pick another seed or another task;
- never point the game's code, docs or README at `Tasks/` or the tasks branch.

## 8. Pitfalls already hit

| pitfall | rule |
|---|---|
| checks or log patterns shown in the brief | the agent gets the brief only |
| an ask in the brief that no check reads, so Lab sends the game back | read each task against its checks before packing (section 5, "Every ask has a check") |
| a model judge misread screenshots and failed a correct fix (or passed a wrong one) | required probes for what can be measured; only the brief's own looks in a required judge (`looks_as_asked`, still-looks in `still_works`), each item concrete and decidable from the screenshots; every other judge `"required": false` |
| a judge was shown only the title screen, or never the state a task's own key opens | the `judge` check names its own `plays` that reach it (section 5) |
| five stills couldn't show whether a move eased or feet slid | a number: a probe sampled every 0.1 s with `agg` `step`; only seen: a `looks_as_asked` item with a short play and `shots` (section 5) |
| a fix made only in binary assets failed the code review | the cause is checked by its measured effect (a probe), never by reading the diff |
| a pixel threshold moved between GPUs | light and colour from the engine (`light`, `grading`); the frame's luminance (`screen`) only calibrated or relative to the start, never a literal |
| a level dressed with instanced meshes counted as one actor | count placed pieces (`pieces`), not actors or components |
| a dense forest merged into 3 procedural sections read 108 pieces against a threshold of 423 | count the drawn geometry (`pieces` `visible_triangles`), calibrated or relative to the start, never a literal |
| a count stopped at 200 rows and a threshold was set on it | counts and `of` read every match (since 2026-11-06); recalibrate a threshold set before |
| a light's turn read relative to its own actor | `world_yaw:`/`world_pitch:`/`forward:` read the component in the world |
| a lamp hidden in game (or at intensity 0) read as lit | the `light` probe counts only lights the renderer draws; a lamp's `on` and `intensity` are `components` fields |
| a collapsed warning still counted as shown | `"visible": true` in a widget select counts only what is on screen |
| every audio component read inactive (plays ran with `-nosound`) | `audio` reads what the player hears; a play with it runs with sound, muted; volumes calibrated or relative to the start |
| relief judged by the height of one spot | `ground` over a box: `range`, calibrated or relative to the start |
| a teleport to fixed coordinates missed what each build placed itself | `teleport_to` an actor select (nearest match), facing it or a point |
| a select by class or tag also matched the scene's own actors, or named the class the reference happened to use | select by what the actor carries: `has` (a component that is `lit`, `visible`, of a `class`, `near` a point) |
| cars that are components of one actor had no position or speed | `components` fields `x`, `y`, `z`, `speed` |
| a broken crate kept its pieces drawn and tagged, so counts couldn't see it break | actor `simulating` and `spread`, component `extent_*` and `simulating` |
| an object that breaks by hiding a part or by animating its pieces read whole to `spread`, `extent_*` and `simulating` | actor or component `changed` (since the start; `bounds_change` and `pose_change` calibrated or relative to the start) |
| a lamp drawn by an emissive material rather than a light component read dark to `on`, `intensity` and `light` | actor or component `lit` (any light component or glowing mesh; `glow` calibrated or relative to the start) |
| a HUD drawn on the canvas rather than with widgets read as absent to `widgets` | `ui`: what the UI shows on screen, whatever draws it (text with `match`, counts by `kind` and `rect`) |
| a lamp lit by a custom node or a texture in a shared material read lit from the start, so it could not turn on | `lit` and `glow` as they are: a mesh whose material graph can't be evaluated whole is read as rendered |
| a readout drawn with canvas lines read as absent to `ui` | `ui` `line` elements (count or place in a `rect`, relative to the start), or `text` where the digits are drawn seven-segment style |
| a readout drawn with slanted lines or stroked letters read no text | `ui` `text` with `match` on a `select` of `"kind": "text"` with a `rect` around the readout (read from the frame as drawn); else its `line` elements in the `rect` |
| a task needs a readout to keep updating, and it may be drawn as text or as lines | `ui` `signature` with `"agg": "changes"` on a `select` with a `rect` around the readout (calibrated or relative to the start) |
| a HUD widget that paints its own text or shapes read as absent to `ui` | `ui` as it is: what a widget paints itself is read from the window's draw elements |
| an effect (particles, a panned material, a spinning mesh) had no reading that it shows and moves | `drawn` `near` a point: `drawn`, and `motion` calibrated or relative to the start |
| a spinning part had no speed, or needed its component's name | `spin` of `components` near a point or by `owner`, or an actor's `spin`; calibrated or relative to the start |
| duplicate effects after a restart went unseen | `components` with `"effect": true` and `near`: `count` of live effects, read after the restart |
| a score or a timer had to be read as a number, not a string | `ui` `number` or `clock` on a `select` of `"kind": "text"` with a `rect`; `rises`, `falls`, `range` over the window |
| a lamp lit only by particles read dark | `lit` and `glow` as they are: particle systems are sources |
| a beam's length had no reading | `drawn` along a `line` from its source: `reach` or `length`, calibrated or relative to the start |
| a surface's tint change (not emissive) had no reading | `drawn` `near` it: `base_r`/`base_g`/`base_b` or `base_change`, calibrated or relative to the start |
| the nearest object a player can push had to be named by class | `has` with `"simulating": true` (and `"movable": true`), in a select or `teleport_to` |
| the game reset the player's ground position every tick, undoing a teleport | `teleport` or `teleport_to` with `hold` (seconds) |
| a lamp above matched together with one below it | `near` with `z_min`/`z_max` (world, or `z_relative` to the point) |
| a menu that pages on real time never reached its later pages in a play | a task-play input `{"t": ..., "wait": seconds}`: the play's clock holds while the game runs on in real time |
| a probe that tests the reference's implementation ("SpawnZ = 92") | measure the outcome; another valid fix must pass |
| the brief said "scenario 1" but not `?Scenario=1` | `play_map` always set and checked at the seed |
| a HUD widget or class name guessed | read the names from the code and assets at `seed.commit` |
| a probe named a class, tag or map only the reference had, so a fair build that named it otherwise read as absent | select what the thread creates by what it does or where it is; the validator refuses a reference-only name |
| a run wrote the feature but never ran the game to see it, and the task had no probe of the moment | a play that triggers each piece of feedback, and a probe of what the player sees then |
| a judge's pictures came from views the game itself lists, so a build could dress only those spots | the task's own tour: `map`, `teleport_to` what the build made, `view`, named `shot` inputs (docs/task-probes.md, section 1.1); never a view list from the game's files |
| quoting the person | write from context |
| a reference that crashed | the reference must build and run |
| tasks solved in minutes: one cause, one place, the brief named the system | only long threads of multiple edits, compound probes, observation-only briefs (section 1) |
| a chain split into two short tasks | one task from before the first attempt to the fix that held |
| a bug that never shows in the grader's plays | a scenario or a task play that triggers the moment |
| a brief rejected by a content filter (injury wording) | neutral technical words: mesh, bones, pose, hit, reaction |

## 9. Examples

Older tasks on the game repos' tasks branches (`duo-kart-fix-wheels-turned-sideways.json`,
`rally-racer-corr-steering-and-chase-camera.json`, `battle-boats-feat-coal-burst.json`) show the file format and probe
style only; most are single fixes that no longer meet the bar (section 1). Rework such a task into its whole thread or
remove it.

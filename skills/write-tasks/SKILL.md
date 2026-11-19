---
name: write-tasks
description: How to write the tasks a game ships with (Tasks/ on the repo's orphan tasks branch, never on main, one GameTask JSON per task, at least 5 and up to about 10 per game, at least 4 of them hard and the others medium) so an agent can be given them in the game-creation environment: the tasks branch and its worktree, the one bar every task meets (a long thread of multiple edits from the game's real history: many commits, many files, several systems, every task medium or hard, never easy or a single fix), the four kinds as where a thread comes from, picking seed.commit (the parent of the thread's first attempt) and seed.reference (its final accepted fix), observation-only briefs, play_map, milestones and deterministic probe checks (pass/fail never by pixels; judges only for asked looks; one required probe per issue), limits, and what keeps a task gradable and unleaked. Use when a game session writes, moves or reviews tasks, and before calling a game complete.
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
"easy" one. A task is `"difficulty": "hard"`, with the tag `long-thread`. A game needs at least 4 hard tasks; the others may be
`"medium"` (a task that names no difficulty counts as medium), none easier; with fewer than 4 hard ones the game is
rejected. Four is the floor, not a target: pick threads that make every task hard, and call a task medium only when
its thread is.

A thread qualifies only when all of these hold (the validator measures the numbers, section 6):

1. **Many edits.** From `seed.commit` to `seed.reference`, at least 4 commits change the game itself (`Source/`,
   `Content/`, `Config/`, `Plugins/`, the `.uproject`), and the reference changes at least 5 game files against the
   start, with at least 100 code lines added plus removed. Status, docs and `workflow.jsonl` commits don't count.
   Assets and binary files don't count as code lines.
2. **Several systems.** The change spans at least two of: C++ (`Source/`), config (`Config/`, the `.uproject`), plugins,
   levels (`.umap`), materials and textures (`M_`, `MI_`, `MF_`, `T_`), Blueprint or UMG assets (`BP_`, `WBP_`, `ABP_`,
   `UI_`), data assets or tables (`DA_`, `DT_`), other assets. The validator counts them by path and name prefix. A long thread confined to one function is a
   short task in disguise.
3. **Several outcomes.** At least 3 required outcome probes, one per issue the thread settled, so partial work earns
   partial credit (a compound ticket). A thread that settled only one observable thing is rarely long enough. Every
   outcome probe carries `"weight"` 1 or more (a probe of weight 0 earns nothing, so it is no outcome and doesn't count
   toward the 3). Neither does a `seen` probe: a model reads it, as a judge's pictures.
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
Playtest rows (`"target": "playtest"`) and the commits that answer them are the first place to look: what a
person felt while playing is what strong agents miss.

**Taste threads (owner, 2026-11-19).** A thread that settled how the game looks or feels (playtest issues, a choice
between two versions, a look or feel direction) is a taste thread. The person who directed the game picks which
candidate threads are taste threads and writes or approves each one's brief in a playtester's words (section 3 still
holds: observations only, nothing quoted from chat). The brief opens with the game's feel intent from the design doc,
so "better" has a direction. Its reference is a commit the person's verdict called better: a fix they judged same or
worse is no reference, so extend the thread to the round they called better, or drop it.
What the design doc's keep list holds is what the task's `still_works` look judge checks, so a solution that spoils
it fails. A feel probe's threshold is calibrated between the start and the reference the person approved (or taken
from a number the brief states), never from the starting numbers in the game-session skill: each game is judged by
its own feel, so the games don't all drift toward one.

**Fixed framings for look judges (owner, 2026-11-19).** A judge compares sides like for like, so its plays show each
asked look from fixed framings, the same on the start, the reference and the agent's build: for a 3D game, from above
the area (layout, overlap), at eye level (looks), and from the player's own view during the action (feel); for a 2D or
2.5D game, the whole play area, a close-up of the subject, and the player's view during the action. Reach each
framing through something the start already has (an actor, a tag, a control the instruction names), never through
raw coordinates of the reference's level.

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
- **The reference does everything the instruction asks**, in a place a play can reach. An ask the reference doesn't
  meet, or meets only where no play gets to (behind a menu no scripted key opens, in a level no option starts), fails
  its own check on the reference: move the reference to a commit that does it, or take the ask out.
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
- **Say what the grader does to the game, where it matters**, in a QA note on the test conditions, never the fix: QA
  steps the game at a fixed frame rate, as fast as the machine renders it (faster than real time), and may move the
  player straight to a spot. Game logic driven by the wall clock (a timer on the platform's clock, a menu that pages
  on real time), or state that doesn't follow a moved player (something carried, a tether, a signal range), behaves
  otherwise under it. The checks allow for it too: windows with room for a clock that runs ahead of real time, a
  `wait` input where the game must see real seconds (docs/task-probes.md, section 1.1).
- Never name the studio, its pipeline or its tools. Never describe the fix or any step of the thread.

## 4. `play_map`

The game's default map is usually a title menu that simulated keys cannot leave, so a task almost always needs
`play_map`: the map path and URL options that start straight in the gameplay where the issue shows (e.g.
`/Game/Maps/L_Level?Scenario=2`). Read the GameMode's option parsing at `seed.commit` and check the map exists there.
Every grader play opens it (boots, idle and drive, the route, the before and reference plays).

**A play does what a player must do to reach the state it probes.** When the instruction makes the game start on a
title screen or a menu and `play_map` opens it there, every play that checks something in the level first clicks the
start control the instruction names, by its on-screen text, and waits for the level; or the instruction states the
direct way in for QA (the map and options QA plays), and the plays open that. Never a shortcut only the reference has:
a URL option, a dev flag or a map its own code added (section 5).

## 5. Milestones and checks: deterministic probes decide

**Pass/fail is decided by checks the grader computes itself** (the owner, 2026-10-19): `build`, `boot`, `log_absent` and
**`probe`** checks, and nothing is graded from pixel statistics of the game's frames except the frame's mean luminance
(`screen`, the owner, 2026-11-06), whose threshold is always calibrated or relative to the start, and whose `rect` is
`[x0, y0, x1, y1]` with x0 < x1 and y0 < y1, since a reversed area holds no pixels to measure. Two judges are
required (the owner, 2026-11-11): `looks_as_asked`, whose rubric items are the brief's own look-and-feel asks, and one
in `still_works` of what must still look as it did (below). Every other judge (`judge`, `code_judge`: taste,
readability, code review) stays a `"required": false` quality check. Nothing in a task reads the agent's tool calls: a
task is graded on the game's outcome alone. Retired (the owner, 2026-11-13): `actions_judge` checks and `trace` probes;
never add one, take them out of a task you edit. A task still needs required probes the grader decides without a judge
(section 6). The probe language, every play, measure and threshold with the rules that gate a task, is the task author's
contract [docs/task-probes.md](../../docs/task-probes.md), checked by the schema
[docs/schemas/game-task.schema.json](../../docs/schemas/game-task.schema.json) and `tools/validate-game.py`.

Each milestone is a reward group; a run that gets part of the way earns part of the reward. **A no-op scores zero
(owner, 2026-11-04; permanent):** the score is the weighted share of checks passed, so every check the start already
passes takes `"weight": 0`: `builds`, `boots`, all of `still_works`, and any `log_absent` or `file_exists` true of the
start. They still gate: a run must pass the required ones to be solved. `validate-game.py` and the task check refuse a
task a no-op would earn anything on. **Weight 0 belongs only in `builds`, `boots` and `still_works`**, the milestones a
no-op passes; every probe in any other milestone (`fixed`, `done`, `fixed_hud`, ...) carries weight 1 or more, since an
outcome that pays nothing rewards no work. A check that must hold but that the start already passes is a keep: it goes
in `still_works` with weight 0, never as a weight-0 probe beside the outcomes. The usual order:

1. `builds`: `build` (`editor_builds`).
2. `boots`: `boot` 60 s (`boots_clean`), `needs` the build.
3. `fixed` (bug_fix, correction) / `done` (feature, change): `probe` checks of the reported outcomes, `required`,
   `needs` `boots_clean`: at least 3, one per issue the thread settled (split them over several milestones, e.g.
   `fixed_hud`, `fixed_camera`, when the issues are separable). Each one fails at the start for the reported reason
   and passes on the reference. The required `looks_as_asked` judge goes here when the brief asks for a look.
4. `still_works`: probes that what must keep working still does (the player still moves, the HUD still shows, the
   level still loads its scenario), and a required judge with `"before": true` for what must still look as it did.
5. `quality` (optional, never required): a `judge` for taste items no probe can capture ("reads as a castle",
   readability of text over the scene), and a `code_judge` for code quality.

**Every look-and-feel ask in the brief gets a required `looks_as_asked` rubric item** (such an ask gates the task, like
any other). Go through the brief ask by ask: what a probe can measure gets a probe; what only an eye can tell (reads
clearly, fits the style, looks like the thing it is meant to be) gets its own rubric item, `"required": true`, in one
required `judge` named `looks_as_asked`, with `"before": true` and `"reference": true` when the seed has a reference.
A judge can misread screenshots, so word each item concretely, decidable from the screenshots alone, so the unchanged
game scores 0 on it and any solution that meets the brief scores 1: never an empty criterion ("shows what the ticket
asks"), and no item about "every screen" unless a play opens every screen. **A rubric item quotes the instruction**:
it takes the words of the sentence it covers and asks no more and nothing other than that sentence (no added detail,
no stricter bar, no other look), since a judge holds a solution to the item, not to the brief. What must still look as it did goes in a
required judge in `still_works` the same way. One subject per judge: the brief's looks in `looks_as_asked`, what must
still look as it did in the `still_works` judge, each taste question in a judge of its own. **Every judge has plays of
its own that show each rubric item at the moment it can be seen**: a judge without them is shown screenshots of the
idle `look` and the `drive` on `play_map` and nothing else, never a task-specific key, another scenario or level, or
what lies past a title screen. Give the check `plays`: up to 4 task plays that reach that state (when a probe's play
already does, reuse it under its name, written identically):

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
- **A play may last up to 1200 seconds.** A moment a player reaches only after many minutes of one uninterrupted play
  (a dawn, a night's last wave, the morning after) is played to in one play of that length, because skipping time
  with flags or teleports tests something other than what the player sees.
- **A play that reads what another play writes names it in `after`. Never rely on the grader's order.** A task play
  that reads a save (a level reached, a profile filled in) lists the plays that write it:
  `"after": ["<writer's name>"]`. On each side they run, and end, first; the plays of a side share the game's
  `Saved/` folder, so the save is there. A writer that failed still counts as run, so the failure shows in the
  reader's checks. Without `after`, plays run in the order checks first ask for them (docs/task-probes.md, 1.1).
- **A play that must find what an earlier session saved, after the game was quit and started again, `continues` that
  play**: `"continues": "<first session's name>"`. On each side the game's save state is cleared, the named play is
  played as a first session and quits, and this play starts as a new process on the same save data; its probes read
  the second session. It names one task play of the task, never itself, never together with `after`, and the play it
  names runs after no play. That play may itself continue another: up to 4 sessions are played earliest first, the
  first on a cleared save, each later one on what the one before left. A save the game makes only on a menu action needs that action in the first session's inputs
  (what it saves on quit is saved when the play ends). A first session clears `SaveGames` and `Config` for the whole
  side, so what earlier plays saved is gone for later ones (docs/task-probes.md, 1.1). A click's `widget` may be a
  control's text in any script, with no control character and no space at either end.
- **A play keeps its own preconditions true.** No input on the frame of a state reset: press a few seconds into the
  phase, never at its start. No teleport that breaks the game's state (something carried, a tether, a signal range,
  anything the instruction gives a limit to): teleport what the game moves together, or walk there.
- **A play never repeats an action that already happened.** No second click on Continue or Retry after the first
  worked: the button is gone, and the click is a miss.
- **A play needs no state a new game doesn't have, unless the instruction gives it.** An existing save, a profile, an
  unlocked level, a timer already run out: the instruction states it as a step a player takes, or the play makes it
  with the player's own steps (or names, in `after`, the play that does). Write each play so it holds whether or not
  an earlier play of the same side left a save behind: the plays of a side share `Saved/`, so a dialog that only a
  save brings up may or may not be there, depending on what ran before.
- **A play that must start as a new game is `"fresh": true`.** The game's save state (`Saved/SaveGames`,
  `Saved/Config`) is cleared before it, so a first-run menu is there and a dialog only a save brings up is not,
  whatever ran before it. Use it when the play's first steps depend on there being no save; a fresh play never takes
  `after` or `continues`, which read what another play left (docs/task-probes.md, 1.1).
- **Launch a play `"attended": true` only when the game hides menus or skips saves in automated runs.** Every other
  play is launched with `-unattended`, which a game may read as an automated run; an attended play is launched as a
  player launches the game. Mark it only when the play needs what the game hides or skips for that flag, because the
  plain launch is the one every grader run makes.
- **A click names its button as the player sees it.** `widget` takes the button's name, its class, or its on-screen
  text exactly as shown, spaces and punctuation included (`"widget": "New expedition"`): the text a player reads is in
  every build that meets the brief, so the play needs no widget name the instruction would have to give away.
- **A click names a control by the words shown on it, even when the control is not a button** (a menu row the game
  builds itself, a menu drawn on the HUD). A click no button takes is made on its text as shown, as a player clicks
  the words they see: the pointer goes there and the left button goes down and up. Exactly one place on screen may
  read those words, because a click on words shown twice can't tell which one the player meant: the click is then a
  miss that names both places, so name the control by words only it shows (a row's words read joined left to right
  count, "1 BUY RANK 300 PT").
- **A click is `"optional": true` only when a correct game may or may not show its control** (a confirmation that
  appears only when a save exists): unmarked, a click no button takes is a miss that fails the play. Never mark a
  click on a control the task asks for optional: a game without that control would pass. Prefer a `fresh` play, or one
  that reaches a state where the control always shows, and mark the click optional only when neither will do.
- **A click on a button the game disables by design (a locked choice) is `"disabled": true`.** It lands when that
  button is shown but disabled and does nothing, as a player's click on it; unmarked, a click on a disabled button is
  a miss, since a click the task relies on must reach a control that works (docs/task-probes.md, 1.4).
- **A click needs no scroll step, and nothing may cover its button.** A click scrolls its button's own scroll box to
  it before pressing, as a player does, so write no cursor and wheel steps for it. A button something else is drawn
  over is not pressed: the click is a miss, "covered by another control", that no option excuses, because a player's
  press there would not reach it either. Close what covers it in the play first, the way a player would.
- **A shot of a moment whose time varies between builds says `when`** (an event as `since` takes one; within the
  play's 1200 s): the picture is taken in the first frame the event holds, so a judge sees the moment on every build.
  Its event reads widgets `count` or `visible`, or actors `count`, `x`, `y`, `z`, `hidden` or a `prop:` member, which
  the probe can read every frame; a shot whose event never comes is a missed input (docs/task-probes.md, 1.1).
- `measure.probe`: `pawn` (track: x/y/z/speed/moved/dist), `camera` (distance/height/pitch/fov/occluded/
  pawn_on_screen), `actors` (select by class, tag, name, near; count, transform, extent, hidden, collision, speed,
  `prop:<Component>.<Property>` by reflection), `widgets` (the drawn widgets of a name or class: visible, text, percent, has_brush, covered), `ui` (what the HUD
  shows, whatever draws it: text, count, place of UMG, Slate and canvas elements alike;
  signature with agg changes for a readout that updates; number and clock for which way a readout or a timer
  moved, with agg rises/falls), `drawn` (what is drawn near a point or along a line, rendered: drawn, motion, base
  colour, a beam's reach), `light` (illuminance,
  exposure, brightness at a point), `grading` (the colour pipeline: cast, warmth, tint, saturation, contrast, grey),
  `spawns`, `log`, `asset` (editor: material_default, material:<prop>, mesh_collision, asset properties).
- **Read text from the game's UI first** (`ui`, `widgets`). `seen` (the visual model reads a named shot of the check's
  own task play; docs/task-probes.md 2.22) only for text nothing else gives: drawn by a shader, a material or a
  texture. Give it a loose `rect` or none, and take the shot at a still moment (a clock ticks). It is a visual check:
  the task still needs a required probe besides it, and the task check saves its crops for you to read blind.
- `expect`: a literal (`{"op": ">=", "value": 1}`) for facts (counts, booleans, "not the default material"), or
  `{"op": ">=", "calibrate": 0.5}` for continuous quantities: the grader measures the start and the reference in the
  grading environment and puts the threshold that fraction of the way from start to fix; `op` points to the fix's side.

Write probes from the game's own code at `seed.commit`: the real class names, actor tags, map paths, widget names and
components. **Everything a required probe or its play relies on is stated in the instruction or exists at the start
commit.** Never something only the reference has: a name (a class, tag, widget, property, map or asset the thread
itself created), a URL option the reference's GameMode added, an exact string or regex of text the reference happens
to show or log, a coordinate where the reference happens to put a thing, a count of key presses that walks the
reference's own menu or level layout. Another fair build names it, words it, places it or lays it out otherwise, and
the probe reads nothing or the play ends up somewhere else. Select what the thread creates by what it does or where it
is (`has`, `near`, `ui` with a `rect` or text, `drawn`, `lit`, `changed`; a part's direction by `components`
`world_yaw`/`world_pitch` with `near`, not `world_yaw:<Component>`). Select a thing the task asks to move by what it
is, never by where the old one was: no `near` sphere around its place at the start, which a correct build moves it
out of. `validate-game.py` refuses a required probe that names something the start lacks and the reference has, a
component in a field such as `world_yaw:<Component>` included, and you check the rest yourself:

- **Prefer what the player sees.** On-screen text is read with a loose `match` (the number, the word the ticket uses),
  never the reference's whole string; an exact string only when the instruction quotes it. A thing is found by what it
  carries or by a tag or class the start already has. A place is reached by `teleport_to` or `pin` on an actor select,
  never by raw coordinates of the reference's level. A menu is driven by the key the instruction gives, or by clicking
  the button whose text the instruction quotes, never by "Down three times, then Enter".
- **"Shown" means on screen.** A `widgets` check reads the widgets drawn: a hidden or collapsed one, one at zero
  opacity or under such a parent is matched by nothing, so "the warning is not shown" passes for a build that hides
  it as for one that removes it, and "the bar is shown" fails for one that only keeps it in the tree. Write
  `"visible": false` in a select only when the check really means "exists while hidden".
- **What the solver has to create and a play cannot do without** (the words on a new screen, a new level QA must open)
  is said in the instruction the way a ticket says it: the wording quoted, the level as where QA will play it. Never a
  class, property, function or tag name ("Hints, never answers", below): if only such a name would make the probe
  work, the probe moves to what the player sees.
- **Ask the second-solution question of every check**: would a correct build that names things differently, lays the
  level or the menu out differently, or hides a thing where the reference removes it (or removes where it hides) still
  pass? If not, the check tests the reference, not the task: rewrite it.

**Test the outcome a player sees, never the implementation**: another valid fix
must pass ("the hero stands on ground", "the stone breaks the wall piece it hits", "the light reaching the tunnel
floor times the camera's exposure is brighter", not "SpawnZ is 92" or "the function was changed"). Measure the
effect, never one way of building it: not a global variable (time dilation for "runs at double speed"), not a
component's offset relative to its parent (it changes when a correct fix re-parents it), not the root actor's
rotation when a child mesh does the moving, not a count of samples standing in for a count of events. Lighting and
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

**No check is written blind: read what each one measured, on both sides, before the task is submitted.** VALID says
the start failed and the reference passed; it doesn't say the check measured what you meant. For every probe open the
result's line (`measured ..., threshold ... (start ..., fix ...)`) and the two plays' `probe.json`
([docs/task-check.md](../../docs/task-check.md)) and see that:

- the play's inputs landed on both sides (`inputs_missed` is empty: a click found its button, a stage its actor, a
  key its moment), and the play reached the state the check is about;
- the probe matched something on both sides (rows in the sample, not "nothing it selects was measured" excused as the
  start's bug), and the event falls inside the `window` on both, with room to spare;
- the value at the start is wrong for the reported reason, not because the play never got there;
- a judge's frames show the moment on the reference (look at them: section "The check asks no model").

A threshold comes from the instruction (a number it states) or from the start (calibrated, or relative to it), never
from "what makes the reference pass". A check added or changed after the run is run again before it ships.

**The check asks no model, so you answer the judges.** For every `judge` check it plays the check's plays on the start
and on the reference and saves the screenshots the cloud's judge would be shown under
`.task-checks\<task>\judge-shots\<check>\` (`start\`, `reference\`, and a blind copy in `blind\A\` and `blind\B\`
whose sides are in `blind\key.json`), with `ask.md` holding the brief, the question and the rubric; `progress.txt` says
`judge <check>: shots saved for start/reference, answer needed`. Before you call a task with a required judge VALID,
look at the pictures yourself, blind: score every rubric item for A and for B from 0 to 1 first, then open the key.
The start must fail every required rubric item (below 0.5) and the reference must pass every one. **When a picture
does not show what an item asks, rewrite the play, never the check** (owner, 2026-11-18): change its inputs and the
moments its screenshots are taken (a named `shot` tied to the event with `when` where the moment moves between builds)
until it shows that state on every run, or edit the game itself so the asked thing really appears on screen. Never
drop the item, point it at something else, or loosen it or its wording to get a pass (no "wording may vary" against an
instruction that names the wording): a check eased until the reference passes no longer asks what the instruction
asks, and passes builds that don't do it. The same holds for a `seen` probe. An item the
pictures can't show scores 0 on that side, never a pass for lack of evidence. Write both
sides' scores in the task's notes (its `tasks-workflow.jsonl` row).

### The no-op and the oracle, checked on your own PC

Every task is checked in the cloud by two scripted runs before any agent gets it, and the task check runs both on your
PC with the same rules:

- **The no-op** is the start (`seed.commit`) left untouched, graded as if an agent had handed it in. It must **fail**:
  it must not pass every required outcome probe, it earns nothing (every check it passes has `"weight": 0`), and it
  passes every required `still_works` probe (what still works must already work there).
- **The oracle** is the reference (`seed.reference`) graded as if an agent had handed it in. It must **pass**: it
  builds, boots and passes every required check, and no check holds a task error (below).

A task is not finished until both are right: the no-op fails and the oracle passes, on your PC, after the last edit
of the task. Step by step:

1. **Validate the format** after committing on the tasks branch:
   `python <GF_ROOT>\game-factory\tools\validate-game.py <GF_ROOT>\games\<slug>`. Fix every task error it names
   first; the task check refuses a task that doesn't validate.
2. **Run the check** of every task in one background run (the `Start-Process` command above), or one task:
   `python <GF_ROOT>\game-factory\tools\task-check.py <GF_ROOT>\games\<slug> --task <name>` (repeat `--task` for
   several; a path to a `.json` file checks a task not committed yet). It builds the start and the reference once
   each, plays them with the probe plugin and grades both sides: the start as the no-op, the reference as the oracle.
3. **Follow it** in `<GF_ROOT>\games\<slug>\.task-checks\progress.txt` until it says `finished`. The console prints one
   line a task: `VALID <name>`, or `INVALID <name>: <first reason>`; the exit code is 0 only when every task is VALID.
4. **Read each task's result**, `.task-checks\<name>.json`: `verdict`; `reasons` (why INVALID, one line each); `notes`
   (the oracle's failures that decide nothing: optional probes, `log_absent`, `file_exists`); `probes` (each probe's
   `start` and `reference` measures, its `threshold`, and `start_passed` / `reference_passed`); `start_checks` and
   `reference_checks` (every check's row on each side, with its `detail`). Each play's `probe.json`, screenshots and
   log are under `.task-checks\<name>\start\<play>\` and `reference\<play>\`.
5. **Answer what the check can't, then ask the person for each task's scores**: every required `judge`
   (`judge-shots\`, above) and every `seen` probe (`seen-shots\`,
   [docs/task-check.md](../../docs/task-check.md)), blind first. A required judge passes on the oracle only when the
   reference scores every required item; a required `seen` probe decides nothing until both sides are answered.
   Keep each judge's blind 0-1 rubric scores in the task's notes (`tasks-workflow.jsonl`), then copy them by judge
   name, side (`start`, `reference`) and rubric key into `judges` in
   `<GF_ROOT>\games\<slug>\.task-checks\writer-scores.json`. Before packaging, **ask the person** for every task's
   `difficulty_estimate` (`hard` or `medium`, matching its `difficulty`; omitted difficulty means medium), `quality`
   (integer 1-5: a long thread, every ask checked, fair to an agent), `minutes_to_solve_estimate` (positive number,
   their estimate for a strong agent; section 6's 25-minute guide), and `notes` (one line of plain text, at most 300
   characters, data only). Record their answers; never guess the person's scores or missing blind judge answers.
   The file is `{"schema":"writer-task-scores/1","tasks":{"<name>":{"difficulty_estimate":"hard","quality":4,
   "minutes_to_solve_estimate":45,"judges":{},"notes":"Several interacting changes; every ask checked."}}}` with
   exactly one row per shipped task; `{}` is for a task with no judges. The schema and full judge example are in
   [docs/task-check.md](../../docs/task-check.md), "Writer scores and delivery".
6. **Fix and run again** each task that isn't VALID (`--task <name>`), and run again every task you changed after its
   last VALID check, however small the change. Commit task edits before the check: the newest
   `.task-checks\<name>.json` must be VALID and bound to the exact task by `task_digest` (`task-check/2` requires it).
   A rebase or amend of unchanged content needs no new check; only a legacy `task-check/1` without a digest falls
   back to requiring a check at least as new as the task file's last commit. Packaging refuses anything else, and
   refuses missing scores or required answers. It ships `Checks/<name>.json`, `Checks/writer-scores.json` and only the small blind
   answer JSON files; `probe.json`, screenshots and logs stay out.
   Until Lab reads `Checks/`, the temporary `package-dataset.ps1 -NoWriterChecks` switch omits that folder and its
   refusal with one warning; remove it once Lab supports the folder (see the delivery rules in `docs/task-check.md`).

What each verdict means:

| verdict | meaning |
|---|---|
| `VALID` | the no-op fails, the oracle passes, a no-op earns nothing, the still-works probes pass at the start, no task error; judges and `seen` probes still need your answers before the task ships |
| `INVALID` | one of those doesn't hold: `reasons` says which; the task doesn't ship as it is |
| `ERROR` | the checker couldn't check it (a commit not fetched, LFS objects missing, the engine refused the project); fix that and run again, it says nothing about the task |

What each failure means and what to do (never by asking less of the solution, section 1):

| the check says | it means | do this |
|---|---|---|
| `start already passes every required probe`, or `start already passes required probe X` | the no-op passes: the check doesn't test the change (the play never reaches the moment, or the measure doesn't see the issue) | compare the two sides' `probe.json` for that measure; give the probe a play that reaches the moment and a measure the change moves |
| `a no-op scores N, not 0` | the start earns reward for doing nothing | give the named checks `"weight": 0` (builds, boots, still-works, anything true at the start) |
| `start fails still-works X` | the probe is broken: what still works fails at the start | fix the probe (its selector, its play, its window), never the threshold |
| `reference fails X` | the oracle fails: the check, or the reference, is wrong | read the reference's row and `probe.json`: a threshold on the wrong side (`op`), a play that doesn't reach the state on the reference, or a reference that doesn't do the ask (move the reference, or take the ask out of the instruction) |
| `task error in X: ... an input did not land ...` | the play can't be driven on the reference (a click found no button, a tap no widget, a stage no actor) | drive the play by what the reference shows at that moment: the on-screen text the instruction gives, a wait, a stage on something both sides have |
| `task error in X: ... matched nothing ...: the check reads nothing even on the task's own fix` | the selector finds nothing on the reference, so no build can pass it | select by what the thing does or carries, or by names the start has; read the rows in the reference's `probe.json` |
| `task error in X: ... carries nothing over to the next session` | a play that `continues` another found no save on the reference | give the first session the inputs that make the game save, and the time to do it |
| `uncalibrated: ... both measure X` | start and reference read the same: nothing to put a threshold between | measure something the change moves, or a literal for a count or a boolean |
| a value that differs between two runs of the same commit, or a reference just past its threshold | a flaky reading: a window at the edge of the event, a sample at a moment that moves, a threshold with no room | widen the window around the event so it holds on both sides, read a quantity with a clear gap between start and reference, calibrate between them; never ease what the instruction asks |
| `judge X: shots saved ..., answer needed` / `seen X: crops saved ..., answer needed` | the check can't decide it without you | answer it (step 5), then check again |
| the reference fails a required judge item or `seen` probe because its pictures don't show what is asked | the play never put that state on screen when its shots were taken | rewrite the play: its inputs and the moments of its shots (`when` on a shot whose moment moves between builds), or edit the game so the asked thing appears on screen; never drop, repurpose or loosen the check or its rubric |

The full list of reasons and their fixes is in [docs/task-check.md](../../docs/task-check.md), "Common reasons and
fixes".

### Every ask has a check

Before the game is packaged, read each task you wrote, its instruction against its checks, yourself; no tool does
this for you. Every submitted task is read the same way, and a task is not accepted as it is when an ask has no
required check, when a check is tied to the reference (it relies on something the instruction doesn't give and the
start doesn't have), or when the reference doesn't do an ask. Fix what you find before it is packed.

### Fixing a task that came back

A task sent back for fixing is fixed from its files as they came back: that is the current version, and an older copy
of your own may lack changes made since, which editing it would undo. A game restored from a delivery has no
git identity of its own: when a commit is refused for a missing name or email, set them in that repo only
(`git config user.name` and `user.email`, never `--global`), from the machine's own git identity or the person's
answer. Change only the tasks the return lists; every
other task stays exactly as it is, since each change needs its own check run and review. Hand each fixed task back
with a note of what changed and why (also in its `tasks-workflow.jsonl` row), so the reviewer can check the change
against what was asked. Every rule of this skill holds as for a new task: a visual check that failed is fixed in its
play or in the game, never by easing the check (above, "The check asks no model"), and nothing is made easier
(section 1).

**Brief the person, then go straight on (owner, 2026-11-18).** The person steering the fix may never have seen this
game. As your first message on a task, write this in the chat, in plain words and without task jargon. It is context
for them to read while you work, not a question: do not wait for an answer, ask whether to proceed or offer a choice
of approaches. They have no basis yet to choose one. Start the investigation in the same turn:

1. **The game.** What it is and its genre, in a sentence or two; whether it has one level or several; how a player
   wins and loses.
2. **The part of the game this task touches.** The rooms or areas involved and how they connect, and who and what is
   in them (the player, creatures, objects). Keep to the areas the task concerns, not the whole game. Name a thing as
   a player sees it the first time you mention it: "the wireless, a radio on the workshop bench", not "the wireless".
3. **The controls.** What a player can press and what each input does, and what can be interacted with in those
   areas.
4. **The task.** Its instruction in full, what the game does at the start, and what the reference is meant to change.
5. **The checks.** Each check of the task in one line: what its play does, what it measures or shows, and its
   threshold.
6. **What may be wrong.** The reason the return gives and, where the return has one, its detail (the `Detail` column
   of the list of returned tasks), in the return's own words and then in plain words: which check it names and what
   it says happened. Present it as what was flagged, a hypothesis to test, not as the cause: say plainly that it may
   be wrong, may be out of date, or may be one of several things wrong with the task.

7. **The words.** Two short lists, so the person can tell them apart. *Words from the game*: every object, place,
   creature or mechanic you will mention, with what it is and where ("the wireless: a radio on the workshop bench;
   pressing it makes a noise", "the cot: a folding bed by the boiler room door"). *Words from the task*: the terms of
   this work you will use, each in a few words (start, reference, check, play, the task check, no-op).

**Write every message so someone who has never seen the game can follow it (owner, 2026-11-18).** The person reads
your messages as you work, and a word they can't place stops them following: "use the wireless" could be an object
in the game or a term of ours. In everything you write to them, the brief and every update after it:

- Say what a thing is whenever it has not been named for a while: "the wireless (the radio on the bench)". Don't
  rely on a list given many messages ago.
- Make it plain whether a word is from the game or from the task: "the creature's state stays 'roaming'" says a
  value in the game; "the check `comes_to_noise`" says one of the task's checks, and say once what that check tests
  ("`comes_to_noise`: after the radio is played, the creature must reach the workshop bench within 25 s").
- Never give a bare name from the code, a file or a check as if the person knew it (a class, a property, a commit,
  a probe field): say what it is or does in the game, and give the name after it only if they will need it.
- Say what happened in the game, then what it means for the check: "the creature walked to the boiler room door and
  stopped, because a bed blocks the doorway; so the check that it reaches the bench fails on both sides", not
  "comes_to_noise fails, nav path partial".
- Short plain sentences. No shorthand of your own invention, no abbreviations they were not given.

After every task check run, give a short table of every check, pass or fail on the start and on the reference, and
one line on what you will try next, and carry on. Use the names from the brief, so the person can follow and step
in. Stop for the person only where this skill says to: a judge's or a `seen` probe's pictures to score, a play you
have offered to show them ("Showing a play to the person", below), or a task you cannot fix.

**The return's detail is a lead, not a finding.** It is what our own check of the task flagged, often one check's
name and a reading, written before anyone looked at the game. Start there, and test it:

- Read the check it names and that check's play, then run the task check and look at that check on the start and on
  the reference (its row and `probe.json`). Say whether the detail holds: confirmed, not reproduced, or true but not
  the cause.
- Then look at every other check of the task the same way. A returned task often has more wrong than the return
  lists (a play that never reaches the moment, a start that already passes, a no-op that scores), and a later failure
  can hide behind the first. The task is fixed when the whole task check says VALID, not when the named check passes.
- A detail that no longer matches what the task check shows (the check passes, or fails for another reason) is not
  an error of yours: say so, and follow what the task check shows.
- A return with no detail is investigated the same way from its reason alone.

In your note of what changed, say what the detail claimed, what you found, and anything else you found wrong.

**You may change the game to fix a returned task, and the new commits are its reference (owner, 2026-11-18).** A
check that fails on the reference is fixed in its play first: its staged state, its inputs and their timing, the
moments of its shots, until the play gets the game into the state the check needs on the start and on the reference.
That is the cheapest fix, so try it first (and see "Showing a play to the person", below, when a play keeps going
wrong). When the play is not the cause, the game is: the thing the instruction asks
for was never finished, or something in the game stops it (a prop in a doorway, a widget over a button, a level with
no path between two rooms). Then fix the game. You have authority to write that fix now, as new work, and to commit
it: a reference does not have to be something the game's history already did. Commit the fix on main (many small
commits, as for any work on the game), then give the task a start and a reference that hold it ("Starts on the
engine", section 2: S and R on `starts/<task name>`, R with the fix and S without it), and run the task check again.
"No commit in the game's history changes this" is never a reason to stop, to narrow a check or to drop the task: make
the commit. Keep the fix to what the instruction asks, and add nothing it doesn't ask for. A fix that also changes
what another task of the game measures is that task's business too: say so in your note, and leave that task's files
alone unless the return lists it.

**Showing a play to the person (owner, 2026-11-18).** Not a step of every fix: something you may offer when you
are stuck on a play. You read a play through its numbers and a few screenshots; a person watching it sees at once
that the character walked into a wall, turned the wrong way or never reached the radio. Offer it when you have
rewritten a play twice and it still doesn't get the game into the state the check needs, or when you can't tell from
the readings whether the play or the game is at fault. It costs a build and a few minutes of the person's attention,
so don't use it for what the readings already show.

- Show the side you suspect: the reference when the play doesn't reach the state there, the start when it behaves
  oddly at the start. One side, one play:
  `python <GF_ROOT>\game-factory\tools\task-check.py <game repo> --task <name> --watch <play> --side reference`
  (`--side start` for the start; `<play>` is a task play's name, or `look` or `drive`).
- Before you run it, say in the chat what you are doing and why, in plain words: which version of the game they will
  see (before the fix or after it), what the play is meant to do step by step ("walk from the stairs to the workshop
  bench, press the radio, wait for the creature"), what you suspect goes wrong and where, and that a game window will
  open by itself once the build is done (a sound plays), run for about as long as the play, and close. They don't
  press anything.
- Then ask what they saw, in their own words: where the character went, where it stopped, what it did or didn't
  press, anything that looked wrong. Rewrite the play, or fix the game, from what they say.
- A watched play is never a reading of the check: it runs in a window at the game's own speed, nothing in it is
  graded and no result is written. Its screenshots and `probe.json` are kept under
  `.task-checks\<task>\watch\<side>\`, to look at with the person afterwards. Run the task check again for the
  verdict.

**A start or a reference that is broken for a reason outside the task.** A returned task's commits are often older
than a fix the whole game needed later, made under another task (the player spawns outside the level and falls, the
game doesn't boot on this engine, a menu blocks every play). Then every play fails before it reaches the task, on
both sides, and the checks read the breakage, not the task. Don't patch the checks around it and don't count it
against the task: rebuild the task's start and reference on main's head ("Starts on the engine", section 2: the start
is main's game with only this task's change taken out, the reference is main's game), and say in your note which
later fix the old commits lacked.

**Never offer the person an eased check as a choice.** "Commit the narrower check, or drop the task" is not a
question to put to them: they are paid for a fixed task and have no way to judge what a check should ask, and section
1 already answers it. When the original check can't pass, the next step is the game ("You may change the game",
above), not a weaker check. Tell them about a check you could not fix only after the play and the game have both been
tried, with what you tried and why it failed, and leave the check as it was.

**A returned game with fewer than 5 tasks is still fixed.** The validator says a game ships at least 5 tasks; some
returned games have fewer, and that count is not yours to repair. Fix the tasks the return lists, don't write new
tasks to make up the number unless the person asks for one, and say the count in your note. Every other validator
error on a task the return lists is yours to fix.

**When a game's listed tasks are all VALID, say what is ready to hand back.** One message, plain words: each task
fixed and what changed in it; whether the game itself changed (the new commits on main and each `starts/<task name>`
branch) or only its tasks; where everything is on disk (the game's folder, its tasks worktree, the results under
`.task-checks`); and anything you could not fix, with what you tried. The person hands the work back the way they
were told to; delete nothing, and push nothing unless they ask.

**A returned task is never "not fixable" for its size.** Its start and reference, rebuilt around a fix, are often
smaller than the thread the task was written from, and the validator only warns about the size of a span (section 6).
Give the task's own numbers in your note (`tools/thread-stats.py`) and go on with the fix.

Each of these is a mistake in a check, to avoid when writing it: a play staged otherwise than with the steps the
instruction gives a player; a window or a judge's frames away from the moment the event happens; a selector aimed at
something other than what the instruction names; a click by a name the player never sees where on-screen text or a
wait would do; a property read that is empty in play while the screen shows the value; a click repeated after its
action already happened; text read in a way that reads nothing on the reference (read it from the widget or element
that shows it); a readout drawn in a way no reading sees (read the value the game keeps for it, by a name the start
already has, moving the way the ask says); `speed` combined by `count` (a count of rows, not a speed: `"of": "max"`);
a staged foe or target out of reach of the attack the play makes; a literal threshold the reference misses when the
instruction states no number (calibrate between the start and the reference instead); a click at a point of the
screen where a click by the control's name or on-screen text would do (another layout puts the control elsewhere); a
press at a point on a control below the visible part of a scrolling list or panel (a tap or a cursor click: scroll
first, with a `cursor` over the list, then `wheel` notches, then the press; a click by the button's name or text
scrolls to it by itself and needs no scroll); a
click
on a control that shows only in some states, such as a confirmation that appears only when a save exists, left
unmarked (start the play `fresh` or reach a state where the control always shows; mark the click `optional` only when
a correct game may or may not show it); a
window set by round seconds rather than around the moment the event happens on both sides (read when it happens in
each side's play first, then place the window over it with room either way; when the moment moves between builds, tie
the window to the event with `since`); a count of the parts a build is made of
(components, widgets, meshes) where the instruction states no such count.

Read each task this way:

- **Go through the instruction sentence by sentence.** The game's description, the controls line and the art line are
  context, and so are a bug report's cause and steps to reproduce; they ask nothing. A sentence that would be equally
  true in every task of the game is context (a line shared word for word with the game's other tasks usually is, but
  a shared line this task's request depends on can still be a keep). What should now be different is an ask; what must
  stay as it is is a keep. The title counts as given to the solver, like the instruction, and follows the same rules.
- **In a bug report, the expected behaviour is the ask only when it is as broad as the symptom.** With no "expected"
  sentence, or a narrower one, the symptom is the ask too: its no longer happening, under the reported conditions,
  needs a check.
- **A check covers an ask by what it reads**: its select, field, window, threshold and play. Its `describe` is a
  label; a `describe` that claims more than the measure reads covers nothing more. Make each ask's check plainly its
  own: its `describe` or rubric item in the ask's own words, its play reaching the moment the ask is about, so any
  reader sees the coverage without arguing for it.
- **An ask about time or about many cases needs checks that match it.** "Stays until", "never", "for as long as",
  "whatever the player does" need a window over that span (a check at one instant covers it only in part); in a bug
  report such words mean under the reported conditions, so the play runs past the moment the symptom was reported.
  "Every" or "each" means each case it lists gets a check of its own.
- **Every ask has a check that would fail if that ask alone were not done**: a required probe for each key, direction,
  scenario or case it lists; a number it states held on both sides; a look-and-feel ask as a required
  `looks_as_asked` rubric item in the ask's own words, with the judge's own `plays` when the state must be reached
  first; motion as a probe sampled every 0.1 s with `agg` `step`, or a required judge with a run of `shots`.
- **A keep that names a thing** ("the boss bar still starts full") has a required `still_works` check reading that
  thing; a bare "everything else keeps working" is covered by any required `still_works` check.
- **Never cover an ask with an optional probe, a `build` or `boot` check, or a `"required": false` quality check alone.**
- **An ask that shows only after a contact** (a blow landing, getting hit, a stun, the last foe of a group falling) is
  staged, never left out because "no fixed play guarantees the contact": `pin` the foe or target ahead of the player
  (a target the build invents: the nearest movable drawn thing near the player) and press the task's own attack key;
  `set` a start-named health only to set the fight up; `damage` for a hit taken at a known moment where the game
  takes damage through the engine; `where` to pick the live ones (docs/task-probes.md, section 1.3). Read the result
  deterministically: a state change in a probe one sentence explains; a hit stop by what the ask says stops, never
  a judge (no screenshot shows it): the one struck freezing by actors `frozen`, the game's time slowing or stopping,
  where the ticket itself says so, by `world` `time_dilation`, and never by `time_dilation` where a fair build could
  freeze the actors instead (freezing them leaves time dilation untouched); a stagger, knock-back or interrupted
  action by `montage`, the actor unable to move, or its distance from the attacker, never a judge. What it looks like (sparks, colours, glow)
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
  Writing the check's read target into the ticket hands the solver the answer; when only such a name would make a
  check work, the check moves to what the player sees.
- **The instruction stays a producer's or a playtester's text.** No coordinates of things that exist at the start; a
  new thing's place as a designer gives it ("about 6 m in front of each base"), in coordinates only where the task
  already speaks in them. Never how QA stages a play (teleports, holds, timings) and nothing of the checks' workings:
  the instruction would become the check's script. A statement of an interface the solver must keep (the engine's
  damage events, the words on a new screen) is one short sentence.
- **A sound ask** is checked by a sound starting when the event happens: `audio` `started_audible` near the source,
  in a window right after the event; `sounds` or `repeats` (by asset name) when the ticket asks for distinct sounds,
  "each gun has its own sound"; audio `waves` counts the different recordings a repeating sound played, for an ask
  that a sound varies each time it plays (a cue that picks one of several recordings). What the sound is, how it sounds, is never checked. New games import every sound
  (game-session skill), so every sound has an asset name. A sound the game's own characters hear and react to (guards
  hearing footsteps, a door that alerts) is a gameplay ask: its check reads the reaction or the state it changes, not
  only a sound starting.
- **A look described by a list of items** gets those items named in the `looks_as_asked` rubric, an item each where
  the instruction asks for each on its own (its own sentence or numbered point): a judge asked only about the whole
  look can pass a build that leaves one out.
- **An ask about how the work is built or documented needs no check** ("fix it at its cause", "keep it in a data
  table", "in C++", "add it to the README"): no check of the game's outcome can decide it. Anything about what the
  player sees, hears or can do is never such an ask, however it is worded.
- **Exactly five kinds of sentence need no check**, because no play can show them: a packaged or Shipping build's own
  behaviour; given screen sizes or resolutions (the size itself: what must be visible on screen still needs a check);
  a frame rate or performance on given hardware; how a sound sounds (its quality, mix or tone); a statement of what the
  task does not add or change. Everything else stays an ask, however hard to check: a value the running game holds, a
  timing, a random or rare event, something a play must set up first, something kept across sessions (a best score,
  settings, a checkpoint after the game is closed and opened again: a play that `continues` the play that earned it).
  When in doubt, it is an ask.
- **A sentence no check can decide as written** ("every exit stays reachable", "the game's own tests still pass") is
  reworded into what the reference demonstrably does and a check can decide, so the task asks as much as before; a
  sentence that can be checked is never dropped. The instruction stays plain prose, never fields.
- **A `still_works` probe never calibrates.** What still works reads the same on the start and the reference, so a
  calibrated threshold has nothing to sit between: use a literal, or a threshold relative to the start.
- **A check's name says what it decides** (`hud_shows_ammo`, not `check3`): the grade, the result files and every
  reader of the task go by it.

## 6. Difficulty, limits and what the validator enforces

- `difficulty` is `hard` (a game needs at least 4 `hard` tasks; the others may be `medium`, never `easy`; four is the
  floor, so aim every task at hard), and `tags` hold `long-thread`.
- `limits`: 400 turns, 480 min, 150 USD, 1800 s tool timeout unless the task needs more; a long thread needs room.
- `tools/validate-game.py` fails a task that is `easy`, has no `seed.reference`, has fewer than 3 required probes
  outside `still_works`, or has a required probe that names a class, tag, map or asset the reference has and the start
  doesn't (section 5). **The size of the span is a soft bar (owner, 2026-11-18): it warns and never rejects.** The
  validator warns when the reference changes fewer than 5 game files, fewer than 100 code lines or fewer than 2 systems
  against its start, and for a seed on main when fewer than 4 game-changing commits lie from `seed.commit` to
  `seed.reference`. For a new task these are still floors, not targets: pick the longest threads the history has, and
  don't write a task you know is under them. A warning on a task that came back is no reason to stop, to call the task
  unfixable or to drop it ("Fixing a task that came back", section 5): say the numbers in your note and carry on.
  It also refuses every shape the cloud grader refuses: a select that names
  nothing to pick by, a window outside 0-1200 s, `to_angle` on a field that isn't an angle, `match` on a field that
  holds no text, a regular expression that doesn't compile, a wheel or mouse move that moves nothing, and the like;
  its message says which.
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
repository without history, `Tasks/`, `Checks/`, `History/` or `Dataset/` (the harness rule: those hold every task's checks and the reference fixes). The grader's
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
| a part's direction read by a component name only the reference had | `components` `world_yaw`/`world_pitch` of the part picked by `near`, `class` or `owner`, with `to_angle` |
| a lamp hidden in game (or at intensity 0) read as lit | the `light` probe counts only lights the renderer draws; a lamp's `on` and `intensity` are `components` fields |
| a collapsed warning still counted as shown, or a "not shown" check failed a build that hid the widget where the reference removed it | a `widgets` select matches only what is drawn; `"visible": false` only for "exists while hidden" |
| an ask to keep a best score or a setting after the game is closed and opened again had no check, or was read in the same run that set it | a play that `continues` the play that sets it: a first session on a cleared save, a quit, a new process (section 5) |
| a continuing play found nothing saved because the game saves only from its pause menu | the first session's inputs open the menu and save before its time is up |
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
| text drawn by a shader or baked into a texture read nothing to `ui`, even from the frame | `seen` on a `shot` of the check's own task play, taken while the text holds still; a loose `rect` or none (a tight one fails a build that draws it elsewhere) |
| a lamp lit only by particles read dark | `lit` and `glow` as they are: particle systems are sources |
| a beam's length had no reading | `drawn` along a `line` from its source: `reach` or `length`, calibrated or relative to the start |
| a surface's tint change (not emissive) had no reading | `drawn` `near` it: `base_r`/`base_g`/`base_b` or `base_change`, calibrated or relative to the start |
| the nearest object a player can push had to be named by class | `has` with `"simulating": true` (and `"movable": true`), in a select or `teleport_to` |
| the game reset the player's ground position every tick, undoing a teleport | `teleport` or `teleport_to` with `hold` (seconds) |
| a key pressed on the frame the game reset its state was lost, or a teleport left behind what the player carried (or broke a tether or a signal range) | press a few seconds into the phase; teleport what the game moves together, or walk there (section 5) |
| a lamp above matched together with one below it | `near` with `z_min`/`z_max` (world, or `z_relative` to the point) |
| a menu that pages on real time never reached its later pages in a play | a task-play input `{"t": ..., "wait": seconds}`: the play's clock holds while the game runs on in real time |
| a probe that tests the reference's implementation ("SpawnZ = 92") | measure the outcome; another valid fix must pass |
| a check read a global variable (time dilation for "double speed"), a component's offset from its parent or the root's rotation while a child mesh turned, or counted samples for events, and failed a correct build made another way | measure the effect the player sees, never one way of building it (section 5) |
| the brief said "scenario 1" but not `?Scenario=1` | `play_map` always set and checked at the seed |
| a HUD widget or class name guessed | read the names from the code and assets at `seed.commit` |
| a probe matched the reference's exact on-screen string, so a build that worded it otherwise read no text | a loose `match` on what the ticket asks to see; an exact string only when the instruction quotes it |
| a play teleported to coordinates, or pressed Down three times, that only fit the reference's level or menu | `teleport_to` or `pin` on an actor select; the key the instruction gives, or a click on the button whose text it quotes |
| a play opened a map or passed a URL option only the reference has, and ended at 0 s on every other build | the play's map and options exist at the start, or the instruction says where QA plays the new level |
| every play probed the level while the game stood on the title screen the instruction asked for | each play clicks the start control the instruction names, by its text, and waits; or the instruction states QA's direct way in (section 4) |
| a check passed the task check but had measured nothing it meant to (the click found no button, the window missed the event, the property was null) | read each check's measured values and the plays' `probe.json` on both sides before submitting (section 5) |
| a second click on Continue or Retry, after the first had worked, missed: the button was gone | a play never repeats an action that already happened |
| a threshold was picked to make the reference pass | from the instruction's own number, or calibrated or relative to the start |
| the instruction asked for something the reference itself doesn't do, or does where no play reaches | the reference does every ask in a place a play can reach (section 2) |
| a probe named a class, tag or map only the reference had, so a fair build that named it otherwise read as absent | select what the thread creates by what it does or where it is; the validator refuses a reference-only name |
| a thing the task asks to move was selected `near` its place at the start, and a correct build moved it out of the sphere | select it by what it is, never by where the old one was |
| a run wrote the feature but never ran the game to see it, and the task had no probe of the moment | a play that triggers each piece of feedback, and a probe of what the player sees then |
| a judge's pictures came from views the game itself lists, so a build could dress only those spots | the task's own tour: `map`, `teleport_to` what the build made, `view`, named `shot` inputs (docs/task-probes.md, section 1.1); never a view list from the game's files |
| quoting the person | write from context |
| a reference that crashed | the reference must build and run |
| tasks solved in minutes: one cause, one place, the brief named the system | only long threads of multiple edits, compound probes, observation-only briefs (section 1) |
| a chain split into two short tasks | one task from before the first attempt to the fix that held |
| a bug that never shows in the grader's plays | a scenario or a task play that triggers the moment |
| a play that reads a save ran before the play that writes it and read nothing (a later level not yet unlocked, an empty profile) | the reading play names its writers in `after`; never rely on the grader's order (docs/task-probes.md, 1.1) |
| a brief rejected by a content filter (injury wording) | neutral technical words: mesh, bones, pose, hit, reaction |

## 9. Examples

Older tasks on a game's tasks branch show the file format and probe style only; most are single fixes that no longer
meet the bar (section 1). Rework such a task into its whole thread or remove it.

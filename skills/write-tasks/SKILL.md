---
name: write-tasks
description: How to write the tasks a game ships with (Tasks/ on the repo's orphan tasks branch, never on main, one GameTask JSON per task, about 10 per game) so an agent can be given them in the game-creation environment: the tasks branch and its worktree, the four kinds (bug_fix from real fixes in the history, correction from user.direction rows, feature, change), picking seed.commit and seed.reference, writing the instruction from context, play_map, milestones and deterministic probe checks (pass/fail never by a model judge or pixels), difficulty and limits, the hard tier (about 2-3 per game: long threads, far causes, compound tickets, observation-only briefs), and what keeps a task gradable and unleaked. Use when a game session writes, moves or reviews tasks, and before calling a game complete.
---

# Writing a game's tasks

A game is complete when its repo's orphan `tasks` branch has `Tasks/`: tasks an LLM agent can be given on this game,
fair, checkable and not leaked. One file per task, `Tasks/<game>-<kind>-<slug>.json` (`kind`: `fix`, `corr`, `feat`,
`change`), in the task format `GameTask`
([docs/schemas/game-task.schema.json](../../../docs/schemas/game-task.schema.json), game-task/1), with `"name"` equal
to the file stem (run and grade ids depend on it; never rename a shipped task). About 10 per game is the
recommendation; a mix of kinds. The tasks branch is the single source: tasks are loaded as `Tasks/*.json` from the
repos' tasks branches, and the packager ships them in the dataset split into the agent's and the grader's halves
(docs/game-format.md).

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
main or the task's `starts/<name>` branch and on UE 5.7, the branch an orphan, nothing under `Tasks/` on main). Before
committing a task, run the task check on it (section 5, `tools/task-check.py`): only a VALID task is committed and
shipped. Commit tasks as you go, like any work (commit-always skill), but on the tasks branch only.

## 1. The four kinds

| kind | where it comes from | `seed.commit` | `seed.reference` | good when |
|---|---|---|---|---|
| `bug_fix` | a real fix in this game's history | the fix's parent | the fix | the bug shows in play or a log at the start; the fix is mostly code; one cause |
| `correction` | a person's direction (`user.direction` row) the game then answered | the last commit before the direction | the commit that answered it (the last of its span) | the direction is about the game itself and its outcome shows in play or code |
| `feature` | a new mechanic a producer would plausibly ask for | a stable 5.7 commit (main's head is usual) | none, or the game's own later feature | small enough for one session, uses keys a grader can press, judgeable in play |
| `change` | a look or content change (lighting, weather, camera, HUD style) | a stable commit | none, or the game's own later change | clearly visible in screenshots, before vs after |

Not a task: status chatter, process rules, questions, praise, a fix that is only a re-import of assets the start does
not have, a sweeping pass resting on a pack imported later, anything whose outcome neither play nor code can show.

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
- Both live on the branch `starts/<task name>` (pointing at R), pushed with the game; the dataset ships every branch
  but `tasks`, so the delivered history holds them.
- A binary asset (.uasset/.umap) goes back to its pre-fix version only if no later commit changed it; otherwise
  re-create the issue in code or config, or pick another task.
- A feature or change with no reference starts at B itself (no branch), once you've checked B doesn't already have it.
- A real fix made after the port needs none of this: its parent and the fix are both 5.7 commits of main.

- **Read the code at `seed.commit`** and confirm the issue is there (the reference diff's removed lines, or a search).
- **The real fix is often not the commit that says so**: a descriptive commit may touch only `workflow.jsonl` while the
  code is in the WIP commit before it; a fix may span commits (use the last); a fix may land a commit or two after a
  port. Use `git show --stat` around that time and the workflow rows that link the direction (`"direction"`).
- **The reference must build and run**: the grader plays it beside the agent's result. If the fix crashed until a
  later commit, use the later one.
- **Chains**: a person complained again after a fix ("still too low") gives two tasks; the second starts from the
  first fix. **Splits**: a direction with several issues fixed in separate commits is one task per issue; issues fixed
  together stay together.
- **Dedupe** against the game's existing tasks by fix commit and by issue. One fix commit may serve two tasks only when
  each code-judge question says which part of the reference belongs to the other.
- Binary-only fixes are fine (the agent can make the same change through editor scripts or C++); drop one only when
  its outcome cannot be seen.

## 3. The instruction (the brief)

Write it from the context, never by quoting a person: no quotes, typos, capitals, profanity, "the owner said" or chat
wording. The reader is a capable developer who has never seen the game.

- **bug_fix**: a QA bug report: what happens, how to reproduce it, what is expected. Name no file, function or cause;
  code identifiers only inside a quoted compiler or crash-log line, which is what a player or a log shows.
- **correction**: what is wrong and how a player sees it, then the wanted outcome.
- **feature / change**: a producer's ticket: what and why, how the player uses it (which key), details, what must still
  work. Close with the art bar: the project's own assets and engine features, no primitive placeholder shapes, no
  debug text.
- Describe the controls the player needs; the harness tells the agent which map QA plays (`play_map`).
- Never name the studio, its pipeline or its tools. Never describe the fix.

## 4. `play_map`

The game's default map is usually a title menu that simulated keys cannot leave, so a task almost always needs
`play_map`: the map path and URL options that start straight in the gameplay where the issue shows (e.g.
`/Game/Maps/L_Level?Scenario=2`). Read the GameMode's option parsing at `seed.commit` and check the map exists there.
Every grader play opens it (boots, idle and drive, the route, the before and reference plays).

## 5. Milestones and checks: deterministic probes decide

**Pass/fail is decided only by checks the grader computes itself** (the owner, 2026-10-19): `build`, `boot`,
`log_absent` and **`probe`** checks. A model judge (`judge`, `code_judge`, `actions_judge`) never decides pass/fail
and nothing is graded from pixel statistics of the game's frames. Judges may stay as `"required": false` quality
checks (taste, readability, how the agent worked). The probe language, every play, measure and threshold with the
rules that gate a task, is the task author's contract [docs/task-probes.md](../../docs/task-probes.md), checked by the
schema [docs/schemas/game-task.schema.json](../../docs/schemas/game-task.schema.json) and `tools/validate-game.py`.

Each milestone is a reward group; a run that gets part of the way earns part of the reward. The usual order:

1. `builds`: `build` (`editor_builds`).
2. `boots`: `boot` 60 s (`boots_clean`), `needs` the build.
3. `fixed` (bug_fix, correction) / `done` (feature, change): `probe` checks of the reported outcome, `required`,
   `needs` `boots_clean`. Every bug_fix and correction has at least one required probe that the start fails for the
   reported reason and the reference passes.
4. `still_works`: probes that what must keep working still does (the player still moves, the HUD still shows, the
   level still loads its scenario).
5. `quality` (optional, never required): a `judge` for taste items no probe can capture ("reads as a castle",
   readability of text over the scene), a `code_judge` for code quality, and the standard `actions_judge`
   `worked_well` (or `trace` probes, `"required": false`).

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
  `prop:<Component>.<Property>` by reflection), `widgets` (visible, text, percent, has_brush), `light` (illuminance,
  exposure, brightness at a point), `grading` (the colour pipeline: cast, warmth, tint, saturation, contrast, grey),
  `spawns`, `log`, `asset` (editor: material_default, material:<prop>, mesh_collision, asset properties).
- `expect`: a literal (`{"op": ">=", "value": 1}`) for facts (counts, booleans, "not the default material"), or
  `{"op": ">=", "calibrate": 0.5}` for continuous quantities: the grader measures the start and the reference in the
  grading environment and puts the threshold that fraction of the way from start to fix; `op` points to the fix's side.

Write probes from the game's own code at `seed.commit` and `seed.reference`: the real class names, actor tags, map
paths, widget names and components. **Test the outcome a player sees, never the implementation**: another valid fix
must pass ("the hero stands on ground", "the stone breaks the wall piece it hits", "the light reaching the tunnel
floor times the camera's exposure is brighter", not "SpawnZ is 92" or "the function was changed"). Lighting and
colour are measured from the engine (`light`, `grading`), never from screenshots. `describe` says the assertion in
plain words; it is shown in the grade, never to the agent. Check names are unique and `needs` only names earlier
checks; calibrated probes, `code_judge` and `"reference": true` judges need `seed.reference`.

A task is valid only when it passes the task check: its start fails the task and its reference fix passes every
required check (with no reference, the start fails at least one required probe), and every required `still_works`
probe already passes at the start. Write the probes per [docs/task-probes.md](../../docs/task-probes.md), then run
the task check on every task before committing it:
`python <GF_ROOT>/game-factory/tools/task-check.py <GF_ROOT>/games/<slug> --task <path>/Tasks/<name>.json` (a task
file not committed yet; `--task <name>` checks one on the tasks branch; [docs/task-check.md](../../docs/task-check.md)).
It builds the start and the reference with the probe plugin, plays them and prints VALID or INVALID with the reasons
and the measured values. **A task ships only when the task check says VALID**; for INVALID, fix the task (the
docs' "Common reasons and fixes"), never the threshold toward what the start happens to measure.

## 6. Difficulty and limits

- `easy`: one obvious cause or setting, visible at once. `medium`: investigation across a few files or an asset (the
  usual case). `hard`: a cause far from the symptom, editor work (rebuilding assets through scripts), or a broad change.
- `limits`: 120 turns, 180 min, 40 USD, 1800 s tool timeout unless the task needs otherwise.

### The hard tier

Each game also ships about 2-3 hard-tier tasks: `"difficulty": "hard"` and the tag `hard-tier`. A task with one cause
in one place and a brief that names the system is not hard, however long the fix took; strong agents finish those in
minutes. A hard-tier task has at least one of these traits, and its brief gives nothing away:

1. **A long thread in the real history.** Pick stretches where the game's own sessions needed many commits or
   several rounds of directions before the fix held. `seed.commit` is the parent of the first attempt;
   `seed.reference` is the final accepted fix. A chain whose first fix didn't hold is one task, not two. Prefer
   causes spread over several files, systems and assets (C++ plus Blueprint or data plus assets built by editor
   scripts).
2. **The cause is far from the symptom:** a HUD symptom caused by a data asset, a camera symptom caused by collision
   channels, a crash only in the packaged build, an intermittent or timing bug, a regression from an earlier change.
3. **A compound ticket:** several real issues in one task, each its own `required` probe, so partial work earns
   partial credit.
4. **A brief that is only an observation:** a player or QA report of what is seen, in plain words. It names no
   cause, no place to look, no file, system or asset, and no mechanism ("the camera feels jammed against the ship",
   not "the obstruction sweep counts the sea"). It says only what a player knows. Leave out the play_map line,
   which the harness adds. Probes may measure the cause's effect directly, since the agent never sees them.
5. **Checkable by the grader:** every required outcome must be measurable in the grader's own plays. Use a scenario
   (`play_map` options at the seed) that triggers the moment, or a task play whose scripted keys reach it (key
   names, mouse buttons included, but no mouse movement). A bug no probe can measure in the grader's plays or the
   editor pass is not a hard-tier task.

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
| a model judge misread screenshots and failed a correct fix (or passed a wrong one) | pass/fail by probes only; judges are `"required": false` |
| a fix made only in binary assets failed the code review | the cause is checked by its measured effect (a probe), never by reading the diff |
| a pixel threshold moved between GPUs | light and colour from the engine (`light`, `grading`), never screenshot statistics |
| a probe that tests the reference's implementation ("SpawnZ = 92") | measure the outcome; another valid fix must pass |
| the brief said "scenario 1" but not `?Scenario=1` | `play_map` always set and checked at the seed |
| a HUD widget or class name guessed | read the names from the code and assets at `seed.commit` and `seed.reference` |
| quoting the person | write from context |
| a reference that crashed | the reference must build and run |
| "hard" tasks solved in minutes: one cause, one place, the brief named the system | hard tier: long threads, far causes, compound tickets, observation-only briefs |
| a bug that never shows in the grader's plays | a scenario or a task play that triggers the moment |
| a brief rejected by a content filter (injury wording) | neutral technical words: mesh, bones, pose, hit, reaction |

## 9. Examples

One of each kind, in `Tasks/` on the game repos' tasks branches once moved there: `duo-kart-fix-wheels-turned-sideways.json` (bug_fix),
`rally-racer-corr-steering-and-chase-camera.json` (correction), `battle-boats-feat-coal-burst.json` (feature).

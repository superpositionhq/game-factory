---
name: write-tasks
description: How to write the tasks a game ships with (the repo's Tasks/, one GameTask JSON per task, about 10 per game) so an agent can be given them in the game-creation environment: the four kinds (bug_fix from real fixes in the history, correction from user.direction rows, feature, change), picking seed.commit and seed.reference, writing the instruction from context, play_map, milestones, checks and judge rubrics, difficulty and limits, and what keeps a task gradable and unleaked. Use when a game session writes, moves or reviews tasks, and before calling a game complete.
---

# Writing a game's tasks

A game is complete when its repo has `Tasks/`: tasks an LLM agent can be given on this game, fair, checkable and not
leaked. One file per task, `Tasks/<game>-<kind>-<slug>.json` (`kind`: `fix`, `corr`, `feat`, `change`), in the game
environment's format `GameTask` ([docs/schemas/game-task.schema.json](../../../docs/schemas/game-task.schema.json),
game-task/1), with `"name"` equal to the file stem (run and grade ids depend on it; never rename a shipped task).
About 10 per game is the recommendation; a mix of kinds. The repo's `Tasks/` is the single source: the environment
loads `Tasks/*.json` from the repos, and the packager ships them in the dataset split into the agent's and the
grader's halves (docs/game-format.md).

Check every task before committing: `python <GF_ROOT>/game-factory/tools/validate-game.py <GF_ROOT>/games/<slug>`
(schema, the environment's extra rules, name = file name, seed commits exist). Commit tasks like any work (commit-always
skill), with one `workflow.jsonl` row per task written (`op:"task.write"`, `target:"Tasks/<name>.json"`).

## 1. The four kinds

| kind | where it comes from | `seed.commit` | `seed.reference` | good when |
|---|---|---|---|---|
| `bug_fix` | a real fix in this game's history | the fix's parent | the fix | the bug shows in play or a log at the start; the fix is mostly code; one cause |
| `correction` | a person's direction (`user.direction` row) the game then answered | the last commit before the direction | the commit that answered it (the last of its span) | the direction is about the game itself and its outcome shows in play or code |
| `feature` | a new mechanic a producer would plausibly ask for | a stable commit (after the 5.7 port when it matters) | none, or the game's own later feature | small enough for one session, uses keys a grader can press, judgeable in play |
| `change` | a look or content change (lighting, weather, camera, HUD style) | a stable commit | none, or the game's own later change | clearly visible in screenshots, before vs after |

Not a task: status chatter, process rules, questions, praise, a fix that is only a re-import of assets the start does
not have, a sweeping pass resting on a pack imported later, anything whose outcome neither play nor code can show.

## 2. Picking the commits

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

## 5. Milestones and checks

Each milestone is a reward group; a run that gets part of the way earns part of the reward. The usual order:

1. `builds`: `build` (`editor_builds`).
2. `boots`: `boot` 60 s (`boots_clean`), `needs` the build.
3. `fixed` (bug_fix, correction): `code_judge` against the reference: does the change address the request at its
   cause, as the reference does, without unrelated changes. 3-4 rubric items, phrased as outcomes; it may describe the
   cause plainly for the reviewer (the agent never sees it) and should note unrelated changes in the reference the
   agent is not expected to make.
4. `looks_right` / `plays`: a `judge` over the grader's own plays, only when play can show the outcome. Seeded tasks
   use `"before": true`; corrections also `"reference": true`. Rubric items must be judgeable from a 20 s idle play,
   the 22 s scripted drive (W, D, W with a Space jump, A, W), screenshots including the HUD, the player's position
   track, and the camera's measures (height, distance, pitch, FOV). A feature that needs other keys asks the agent for
   a route file (`route`), which the grader plays.
5. `worked`: the standard `actions_judge` `worked_well` (copy it from an existing task): looked before editing, kept
   the game building, checked the result in the running game after its last change (required), stayed on task.

Rubrics: outcomes, never the reference's implementation ("the chase camera shows the road ahead", not "SpringArm
length is 700"); mark the actual complaint `"required": true`; ask only what the evidence can show (no `looks_right`
for a mouse-only outcome; HUD items need the HUD in screenshots; motion needs the drive or a route). Check names are
unique and `needs` only names earlier checks; a `code_judge` or a `"reference": true` judge needs `seed.reference`.

## 6. Difficulty and limits

- `easy`: one obvious cause or setting, visible at once. `medium`: investigation across a few files or an asset (the
  usual case). `hard`: a cause far from the symptom, editor work (rebuilding assets through scripts), or a broad change.
- `limits`: 120 turns, 180 min, 40 USD, 1800 s tool timeout unless the task needs otherwise.

## 7. What must never reach the agent

The agent sees only the brief and the game at `seed.commit` as a fresh repository without history, `Tasks/`,
`History/` or `Dataset/` (the harness rule: those hold every task's rubrics and the reference fixes). The grader's
half (`milestones`: rubrics, questions, `log_absent` patterns; and `seed.reference`) never reaches it. So:

- the instruction holds nothing of the grader's half and does not describe the fix;
- nothing else at `seed.commit` should spell out the answer (a design-doc "known issues" line naming the cause, a
  comment saying how to fix it): if it does, pick another seed or another task;
- never point the game's code, docs or README at `Tasks/`.

## 8. Pitfalls already hit

| pitfall | rule |
|---|---|
| rubric or log patterns shown in the brief | the agent gets the brief only |
| a win the grader never saw | `required` items; the agent's route, played by the grader |
| the brief said "scenario 1" but not `?Scenario=1` | `play_map` always set and checked at the seed |
| HUD items guessed | screenshots include the HUD; ask only what the evidence shows |
| camera/HUD changes read as "nothing changed" | judge from camera measures and side-by-side screenshots, track only for motion |
| quoting the person | write from context |
| two directions answered by one commit | each code-judge question names the other's part |
| a reference that crashed | the reference must build and run |

## 9. Examples

One of each kind, in the game repos' `Tasks/` once moved there: `duo-kart-fix-wheels-turned-sideways.json` (bug_fix),
`rally-racer-corr-steering-and-chase-camera.json` (correction), `battle-boats-feat-coal-burst.json` (feature).

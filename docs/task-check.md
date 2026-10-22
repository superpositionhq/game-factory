# Task check: check your own tasks

A task (a GameTask JSON in `Tasks/` on the game repo's orphan `tasks` branch, schema
[schemas/game-task.schema.json](schemas/game-task.schema.json)) is only useful when its checks tell a broken game from a
fixed one. The task checker proves that on your machine before you hand the task in: it builds the game at the task's
start (`seed.commit`) and at its reference (`seed.reference`, the change that solves it), plays both with the TaskProbe
plugin, measures every probe, and says **VALID** or **INVALID** with the reasons.

```powershell
python tools\task-check.py C:\Users\<you>\Work\games\<slug> --task <task-name>
python tools\task-check.py C:\Users\<you>\Work\games\<slug> --task <one> --task <two>
python tools\task-check.py C:\Users\<you>\Work\games\<slug> --all
python tools\task-check.py C:\Users\<you>\Work\games\<slug> --task C:\Users\<you>\Work\tasks\<slug>\Tasks\<task-name>.json
```

A task is read from the repo's `tasks` branch by name; give the path of a `.json` file instead to check a task you
haven't committed yet.

Run it from PowerShell (the machine's `ue-heavy.ps1` is a PowerShell script; see "Requirements"). Without `--task` or
`--all` it lists the tasks on the branch. Each task prints one line, and the exit code is 0 only when every task is
VALID:

```
VALID   metro-runner-corr-cell-and-dead-meter
INVALID island-survival-fix-hut-door: start already passes every required probe
```

Options: `--keep` keeps the built copies (to look at a build or rerun a play by hand), `--out DIR` puts the results
elsewhere, `--scratch DIR` puts the copies elsewhere, `--direct` runs Unreal without the machine's job slots,
`--timeout S` (a play or the editor pass, default 1800) and `--build-timeout S` (default 3600).

## Requirements

- Windows with Unreal Engine 5.7 where the machine config says (`engine` in `%USERPROFILE%\.game-factory\config.json`,
  [machine/README.md](../machine/README.md); a project's `EngineAssociation` picks the install). Every start and reference
  must be a UE 5.7 project as committed: the checker never ports or patches a game.
- Python 3.12 (standard library only), git and Git LFS. The checker reads the game's files straight from its git objects
  and its local LFS store, so the LFS objects of both commits must be there: `git -C <repo> lfs fetch origin <commit>`
  when it says one is missing.
- Disk: each task makes up to two copies of the game plus their build outputs, deleted when the task is done. The
  copies go on the repo's own drive (its resolved path, junctions followed), so LFS files are hardlinks of the repo's
  own objects and cost no disk; `--scratch` elsewhere makes them copies. It refuses to start below the machine's
  free-space floor (`min_free_gb`).
- Time: two cold builds and a few plays, typically 20-60 minutes per task. Every build, play and editor run goes
  through `<root>\tools\ue-heavy.ps1` when the machine has it, so checks share the machine's job slots with everything
  else; its timeouts count from when a job starts, not the wait for a slot. If PowerShell refuses to load
  `ue-heavy.ps1` (an `AllSigned` execution policy), run the checker from a PowerShell session that may run the
  machine's scripts, or pass `--direct`.

## What it does

1. Reads the task from the `tasks` branch (else `origin/tasks`) and validates it like
   [tools/validate-game.py](../tools/validate-game.py) does; a task that doesn't validate is INVALID.
2. Materializes the start and the reference into a scratch folder outside the repo, on its drive (default
   `<root>\.task-check\` when the machine root is on the repo's drive, else a `.task-check` folder beside the folder
   that holds the repo):
   every file of that commit exactly as committed, LFS files hardlinked from the repo's store (copied across drives),
   without `Tasks/`, `History/`, `Dataset/` or `Dataset.zip`. The TaskProbe plugin is added as `Plugins/TaskProbe`;
   nothing else is added or changed, the `.uproject` included, and nothing comes from another commit (no port, no
   patch). Your checkout is never touched. When a map the task plays names `/Game` packages the commit doesn't hold (a
   store pack committed only later, say), the result says so in a note: that is the task's commit to fix.
3. Builds the start (`Build.bat <Name>Editor Win64 Development -DisableAdaptiveUnity`). A start that doesn't build makes
   the task INVALID, unless its build check says so (`"fails_at_start": true`: making it build is the task); then the
   start failing to build is the start failing the task, and it is never played.
4. Checks the reference as if it were a solution: the task's checks in order (a check whose `needs` failed doesn't run
   and fails): build, boot (a play of `seconds` that must end without a crash or fatal error), `log_absent`,
   `file_exists`, and every probe against its threshold.
5. Checks the start on its probes.
6. Writes the result and deletes the scratch copies (unless `--keep`).

### The plays

Each play is the game started with `-game`, offscreen at 960x540 and a fixed 30 fps, on the task's `play_map` (or the
task play's own `map`), with the TaskProbe plugin sampling every 0.5 s (a task play's `every`). Each play is played once
per side, with the measures of every probe that names it.

| `play` | What |
|---|---|
| `"look"` | 20 s, no input |
| `"drive"` | 22 s: W 1-6 s, D 6-8 s, W 8-13 s with a jump (SpaceBar) at 9 s, A 13-15 s, W 15-21 s |
| `{"name": ..., "seconds": ..., "inputs": [...]}` | a task play: keys, axes, widget clicks, cursor moves and teleports at their times, its own `map`, `args` and `every` |
| `"editor"` | one headless editor pass per side over every `asset` measure (the project as saved) |
| a boot check | `seconds` of play, no input; `log_absent` reads a 60 s boot's log |

### Thresholds

- `{"op": ">=", "value": 1}`: a literal.
- `{"op": ">=", "calibrate": 0.5}`: `s + 0.5 * (r - s)` between the start's measure `s` and the reference's `r`.
  If the start measured nothing (its play crashed: often the bug itself), the threshold is `r` moved a quarter of
  `|r|` toward the start's side. If the reference measured nothing, or both sides measure the same, the probe fails as
  **uncalibrated**.
- `{"op": ">=", "start_times": 1.3}` / `{"op": ">=", "start_plus": 500}`: `s * 1.3` / `s + 500` from the start (for a
  task with no reference). A start that measured nothing leaves no threshold (uncalibrated).

## VALID and INVALID

A task is **VALID** when all of this holds:

- the start builds, or doesn't build exactly when a build check says `fails_at_start`;
- with a reference: the reference builds, boots (every `boot` check) and passes every **required** probe;
- the start fails at least one required probe outside `still_works` (or doesn't build by design);
- every required probe in the `still_works` milestone already passes at the start. What must keep working has to work
  before the change, or the probe is broken and would fail every correct solution. A still-works probe the start
  measured nothing for (its play crashed, which is often the task's own bug) doesn't count against it.

Never part of the check: judges (`judge`, `code_judge`, `actions_judge`: quality scores, never pass/fail), trace probes
(they read an agent's own tool calls), and `package` checks. The reference's other failures (`log_absent`,
`file_exists`, probes with `"required": false`) are reported as notes and never make a task INVALID.

A task with no reference (most features and changes) is checked on its start alone: it must build, fail a required
probe (thresholds relative to the start, or literals), and pass its still-works probes.

## Results

- One line per task on the console; progress goes to stderr.
- `<repo>\.task-checks\<task>.json` (format `task-check/1`): `verdict`, `reasons` (why INVALID), `notes`, the `start` and
  `reference` commits and whether they built, `probes` (per probe: its milestone, `required`, `op`, `expect`, the
  `start` and `reference` measures, the `threshold`, and whether each side passed), every check's row on each side
  (`start_checks`, `reference_checks`: `passed` and a `detail` such as
  `... | measured 118, threshold >= 119.274 (start 118, fix 120.547)`), and the task file's `task_sha256`.
- `<repo>\.task-checks\<task>\<side>\<play>\`: each play's `probe.json` (the track, the camera rows, every measure's
  samples), its screenshots and its log; `build\build.log` when a build failed. Read these when a value surprises you.
- `.task-checks\` is git-ignored: new games have it in `.gitignore` (templates/ue-game); for an older game the checker
  adds it to the repo's own `.git\info\exclude`. Never commit results.

## Common reasons and fixes

**`start already passes every required probe`.** The bug doesn't show in what the probes measure.
- The play never reaches the situation: the idle `look` stands at the spawn, the `drive` walks a fixed pattern. Write a
  task play that gets there: a `teleport` input (`{"t": 0.2, "teleport": [x, y, z], "yaw": 90}` places the player pawn;
  take the coordinates from the editor, or from the `track` in a play's `probe.json`), its own `map` with options
  (`/Game/Maps/L_Arena?Scenario=2`) and `args` (`-Scenario=2`), and the inputs that trigger the bug.
- The measure is the wrong one: compare the start's and the reference's `probe.json` samples for the field you read
  and pick one that differs.

**`uncalibrated: ... the start and the reference both measure X`.** The measures are equal on both sides, so there is
nothing to put a threshold between: the probe doesn't see the change. Measure something the fix changes (a
different field, window or play), or use a literal value when the fact is a count or a boolean.

**`no samples in the window (the play ended at X s)`.** The play ended before the window: the window or `at` lies past
the play's `seconds`, or the game crashed or quit (see the play's log). **`the play wrote no probe file`**: the game
never got to play (a crash at load, a map that doesn't exist).

**`no value in the window (nothing it selects was measured)`.** The selection matched nothing, or nothing it matched
has that field. `class` is the class name without its prefix letter (`SCCastlePiece` for `ASCCastlePiece`; a Blueprint
by its asset name with `_C`, `BP_Wall_C`); a component property is `prop:<Component>.<Property>`; `; the plugin said:
...` quotes what the plugin couldn't read. The `rows` in the play's `probe.json` show what was found.

**`of` defaults to `count`.** For `actors`, `widgets`, `components` and map `asset` measures, `of` combines the
selected rows of one sample, and without it a field like `z` counts the rows whose value isn't 0 instead of reading
the value. Set `"of": "first"`, `"max"`, `"min"` or `"mean"` when you mean the value.

**Angles.** `yaw`, `pitch`, `roll` and `rel_yaw:` are normalised to (-180, 180], so a raw yaw jumps from 180 to -180
and `mean` or `delta` across the wrap mean nothing. Use `"to_angle": 90` (the shortest distance to 90 degrees, 0-180)
or `"to_axis": 90` (the distance to that axis, 0-90: a direction and its opposite are one axis), with the threshold on
that distance. A `prop:` that holds an angle takes `to_angle`/`to_axis` too.

**Mouse look moves too little or too much.** An axis input (`{"t": 1, "key": "MouseX", "axis": 4.0}`) is a raw mouse
delta: the turn it gives is the axis value times the game's own mouse scale (its input mapping's modifiers and the
engine's mouse sensitivity in the input settings), so the same 4.0 turns one game a few degrees and another a whole
turn. Check the camera's `yaw` in the start play's `probe.json` and scale the axis values to the turn you need.

**`start fails still-works X`.** The game works at the start, so a still-works probe that fails there is broken: it
doesn't find the HUD, the actor or the value it looks for. Fix the probe (see the play's `probe.json`), never the
threshold.

**`reference fails X`.** The reference doesn't do what the probe asks (a threshold on the wrong side: check `op`), or
the reference's play doesn't reach the situation either. `reference fails boots_clean: crashed` means the reference
crashes in a plain boot.

**`start: /Game/Maps/L_X names N of its M /Game packages that the commit doesn't have`** (a note). The map refers to
assets the commit lacks, typically a store pack committed only later; in the plays they load as missing (a bare,
checkered level), which can make probes measure the wrong thing. Pick a commit that has the packs, or commit them so the
task's commits hold them; the checker never adds files from other commits.

**`start doesn't build`.** The start doesn't compile on UE 5.7 as committed. Pick a start that builds, or, when making
it build is the task, set `"fails_at_start": true` on the build check (then no threshold may be relative to the start).

**`... LFS object(s) ... aren't in ...'s local store`** (an ERROR line, not a verdict): fetch them,
`git -C <repo> lfs fetch origin <commit>`, and run again.

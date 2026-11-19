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

**Check a game's tasks in one run** (`--all`, or several `--task`). The run makes one scratch copy per commit and
builds it once, so a commit that is one task's start and another's reference, or two tasks' start, costs one build;
each copy is deleted after the last task that needs it (or when the disk runs below the floor, then rebuilt if a later
task needs it). A shared copy is the commit exactly as committed, so sharing changes no result. A run of 10 tasks
takes hours, so start it where it can run on its own and come back; a game session starts it as its own process
(write-tasks skill, section 5). `<out>\progress.txt` (and `progress.json`) is rewritten after every task: how many
are done, each one's verdict and minutes, and which is running; it says `finished` at the end. Progress lines carry
the time of day, and each build and play logs how long it took.

Run it from PowerShell (the machine's `ue-heavy.ps1` is a PowerShell script; see "Requirements"). Without `--task` or
`--all` it lists the tasks on the branch. Each task prints one line, and the exit code is 0 only when every task is
VALID:

```
VALID   <game>-corr-<slug>
INVALID <game>-fix-<slug>: start already passes every required probe
```

Options: `--keep` keeps the built copies (to look at a build or rerun a play by hand), `--out DIR` puts the results
elsewhere, `--scratch DIR` puts the copies elsewhere, `--direct` runs Unreal without the machine's job slots,
`--timeout S` (a play or the editor pass, default 1800) and `--build-timeout S` (default 3600).

`--watch PLAY` (with one `--task`, and `--side start` or `--side reference`, the default) doesn't check anything: it
builds that one side and shows that one play in a game window at the game's own speed, for a person to watch and say
what they see when a play keeps going wrong (write-tasks, "Showing a play to the person"). The plays it comes `after`,
and a first session it `continues`, are played as always, offscreen, before it. A sound plays when the window is about
to open. The play saves 12 screenshots, its `probe.json` and its log under `<out>\<task>\watch\<side>\`, and the
run prints one line, `WATCHED <task>: <side> play <PLAY>: shown for N s ...`. Nothing is graded and no result is
written: a watched play runs without the fixed step and frame rate a check's play has, so its readings are not the
check's. `PLAY` is a task play's name, or `look` or `drive`; a name the task doesn't have is refused with the names it
has.

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
- Time: two cold builds and a few plays, typically 20-60 minutes per task; a commit shared by several tasks of one
  run is built once. Every build, play and editor run goes
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
5. Checks the start on its probes, and on its weighted `log_absent`, `file_exists` and `package` checks for the
   no-op's score (below).
6. Writes the result and deletes the scratch copies (unless `--keep`).

### The plays

Each play is the game started with `-game`, offscreen at 960x540 and a fixed 30 fps, on the task's `play_map` (or the
task play's own `map`), with the TaskProbe plugin sampling every 0.5 s (a task play's `every`). Each play is played once
per side, with the measures of every probe that names it, and the measure of each one's `since` event; a named shot's
`when` event goes to the plugin with the play's inputs, as one query it reads every frame from the shot's time. A play runs without sound (`-nosound -benchmark`), unless
one of its measures is `audio`: then it runs with sound, muted (`-muteaudio`, with `-benchmark`'s fixed step and seed
kept; docs/task-probes.md, section 2.16).

A mobile game (a `Platform.json` at the root of the copy, as the game had it at that commit) is played as a phone
plays it: the engine's mobile renderer (`-FeatureLevelES31`) at the phone's size, 1920x1080 for a landscape game and
1080x1920 for a portrait one, in place of 960x540; the checker's own `drive` is by touch (a thumb on the lower left
pushing as a stick, a tap on the lower right), and the task's plays send the touches they name (docs/task-probes.md,
sections 1.1 and 1.5). A task play never chooses the renderer or the size itself: `validate-game.py` refuses it.

| `play` | What |
|---|---|
| `"look"` | 20 s, no input |
| `"drive"` | 22 s: W 1-6 s, D 6-8 s, W 8-13 s with a jump (SpaceBar) at 9 s, A 13-15 s, W 15-21 s |
| `{"name": ..., "seconds": ..., "inputs": [...]}` | a task play: keys, axes, widget clicks, cursor moves, teleports and teleports next to an actor at their times, its own `map`, `args` and `every`; `fresh`: on a cleared save; `attended`: launched without `-unattended` |
| `"editor"` | one headless editor pass per side over every `asset` measure (the project as saved) |
| a boot check | `seconds` of play, no input; `log_absent` reads a 60 s boot's log |

Plays run in the order the task's checks first ask for them, except that a task play with `after` runs once every play
it names has run on the same side, a failed one too (docs/task-probes.md, section 1.1), as on the Lab. Every play of a
side runs on the same scratch copy, and between launches only the probe's folder (`Saved/TaskProbe/play`) and its log
are cleared, so what a play saves in the project's `Saved/` folder is there for every later play. A run of several tasks
shares a commit's copy, so that includes plays of earlier tasks on the same commit. A task play that `continues`
another is played after the sessions it continues (up to 4, earliest first, each launched on what the one before
left; the earlier ones are kept as `play_<name>-first-<n>`) of its own: the copy's `Saved/SaveGames` and `Saved/Config` are deleted, the
play it names is played (kept as `play_<name>-first`) and quits, then the play itself starts as a new process on the
same copy (docs/task-probes.md, section 1.1). Before a `fresh` task play the copy's `Saved/SaveGames` and
`Saved/Config` are deleted too, so it starts as a new game does, as on the Lab. An `attended` task play is launched
without `-unattended`, as a player launches the game. A task play may last up to 1200 s; a play gets at least its own
seconds and 600 s more to run, however low `--timeout` is.

A boot is the same idle game as `"look"`, only longer, so on the side that boots (the reference; a start is never
booted) one 60 s idle play with look's queries serves both: the boot check reads all of it and `"look"` reads only its
first 20 s, exactly what a 20 s play would have measured. That saves a game launch per task, and each launch costs
minutes beyond its scripted seconds. A look probe that reads the log (`"probe": "log"`) keeps its own 20 s play,
because a log covers the whole play. The kept files are then under `boot_60s\`, not `look\`. Each play's progress
line says how long it took, and how much of that it waited for a machine slot (`ue-heavy.ps1`).

### Thresholds

- `{"op": ">=", "value": 1}`: a literal.
- `{"op": ">=", "calibrate": 0.5}`: `s + 0.5 * (r - s)` between the start's measure `s` and the reference's `r`.
  If the start measured nothing (its play crashed: often the bug itself), the threshold is `r` moved a quarter of
  `|r|` toward the start's side. If the reference measured nothing, both sides measure the same, or the start
  measured nothing and the reference measured 0 (a quarter of nothing is no margin), the probe is **uncalibrated**,
  and the task is INVALID whether the probe is required or not: the cloud's grade can't make its threshold and grades
  no run of the task.
- `{"op": ">=", "start_times": 1.3}` / `{"op": ">=", "start_plus": 500}`: `s * 1.3` / `s + 500` from the start (for a
  task with no reference). A start that measured nothing leaves no threshold (uncalibrated: INVALID, as above).

## VALID and INVALID

A task is **VALID** when all of this holds:

- the start builds, or doesn't build exactly when a build check says `fails_at_start`;
- with a reference: the reference builds, boots (every `boot` check) and passes every **required** check the
  checker runs: probes, `log_absent` and `file_exists` (the cloud's oracle must pass every required check);
- no probe is uncalibrated, on either side, `required` or not (Thresholds, above);
- the start fails every required probe outside `still_works` (or doesn't build by design): each is one issue of the
  thread, and one the start already passes rewards no work. A required check of `"weight": 0` rewards nothing, so the
  check doesn't refuse a start that passes one; but weight 0 belongs only in `builds`, `boots` and `still_works`
  (write-tasks section 5): a probe in any other milestone carries weight 1 or more, and a check the start already
  passes is a keep that goes in `still_works`;
- every required probe in the `still_works` milestone already passes at the start. What must keep working has to work
  before the change, or the probe is broken and would fail every correct solution. A still-works probe the start
  measured nothing for (its play crashed, which is often the task's own bug) doesn't count against it;
- a no-op scores zero: no check the start passes carries weight, so build, boot and `still_works` checks take
  `"weight": 0`. As the cloud's no-op is graded on every check, a weighted `log_absent` or `file_exists` is measured
  on the start too (a 60 s boot of the start for the log), and a weighted `package` check counts as passed on a start
  that builds (local only: the checker never packages). Judges aren't measured here, so a judge's weight isn't
  covered by this rule;
- no check holds a **task error**, on either side, `required` or not: a check no version of the game can pass. One is
  a probe whose selector reads nothing in the reference's play (no row matched, or none had the field; a `count`, or a
  `widgets` reading combined by count, any, all or sum, reads 0 of nothing, which is an answer unless 0 fails the
  threshold on the reference), and a task play, a probe's or a judge check's own, whose inputs don't land on the
  reference (`inputs_missed`: a click no
  button took or on a button something else covers, a tap no widget, a stage nothing took, a shot whose `when` event
  never came) or whose first session there doesn't end cleanly or saves nothing
  (`continues`). An `optional` click no button took, and a `disabled` click whose button the plugin found shown but
  disabled, are no misses, as on the Lab; a click on a covered button ("covered by another control") is a miss whatever
  its options. The cloud's grade of every run fails while a task holds one. An input the start's play missed while
  the reference's landed fails that check on the start: the start's play didn't do what the task says. A judge
  check's own play is read the same way before its pictures are saved: a missed input on the reference fails the
  judge there (a task error when the input missed for good), as the cloud fails it before asking its judge.

This is the cloud's own check of every task, by two scripted runs: the **no-op** (the start, untouched) must fail and
earn nothing, and the **oracle** (the reference) must pass. VALID here is both of them as they must be; the write-tasks
skill (section 5, "The no-op and the oracle") walks through it step by step.

Never decided by the check: judges (`judge`, `code_judge`: no model is asked; you answer them, below), `package`
checks on the reference (the cloud packages the reference for a required one, which must then pass: the game's own
packaging is checked when the game is released), and the retired `actions_judge` checks and `trace` probes an older
task still carries. The reference's failures of checks that aren't required (`"required": false`) are reported as
notes and never make a task INVALID, as the cloud's oracle needs only its required checks.

A `judge` check is looked at by you instead. The check plays its plays on the start and on the reference (its own
`plays`, else `look` and `drive`; a play a probe names is the same play, played once) and saves the screenshots the
cloud's judge would be shown ([task-probes.md](task-probes.md) section 3.2) under
`<task>\judge-shots\<check>\`: `start\` and `reference\` (`<play>_<nn>.png`, in the order taken), `ask.md` (the
brief, the question, the rubric and what each picture is) and a blind copy, `blind\A\` and `blind\B\`, whose sides
are in `blind\key.json`. The task's line in the result and in `progress.txt` says
`judge <check>: shots saved for start/reference, answer needed`. Before you call a task with a required judge VALID:

1. Open `ask.md`, then look at `blind\A\` and `blind\B\` and score every rubric item of each from 0 to 1, as if
   each were the developer's game, before opening `blind\key.json` and `sides.md`. The blind folders hold only the
   pictures both sides have and the same names in each; each side's own count and notes (a play cut short) are in
   `sides.md`, read with the key.
2. The start must fail every required rubric item (below 0.5) and the reference must pass every one. When a picture
   doesn't show what an item asks, rewrite the play: its inputs and the moments its shots are taken (a named shot's
   `when`, tied to the event, where the moment moves between builds), or edit the game so the asked thing really
   appears on screen. Never drop the item, point it at something else, or loosen it or its wording to get a pass (no
   "wording may vary" against an instruction that names the wording): an eased check no longer asks what the
   instruction asks. Then check again.
3. Write both sides' scores in the task's notes (its `tasks-workflow.jsonl` row on the tasks branch), by judge name
   and rubric key. Copy those same scores into `.task-checks\writer-scores.json` before packaging ("Writer scores
   and delivery", below); never invent or infer missing blind scores.

`--no-judge-shots` skips the judge plays.

A `seen` probe ([task-probes.md](task-probes.md) section 2.22) is read by you too, since the check asks no model. Its
task play is played on the start and on the reference (once, with the other probes of that play), and each named shot
it reads is saved under `<task>\seen-shots\<check>\` as the Lab's model would get it: `start\` and `reference\`
(`<shot>.png`, cropped to the probe's `rect`, or the whole frame without one), `ask.md` (the Lab's prompt, what the
probe reads, what each picture is), `crops.json` (each crop's sha256) and a blind copy, `blind\A\` and `blind\B\`,
whose sides are in `blind\key.json`. The crops are at the shot's own pixels, a mobile play's shot first kept within
960x540 (540x960 held upright) as the Lab keeps every play's shots: the Lab also scales them up (`ask.md` says how
much), which the checker can't do without an image library. Until it is answered, the probe measures nothing
on either side, the task's line says `seen <check>: crops saved for start/reference, answer needed`, and the task is
not VALID, the probe `required` or not (the Lab's reading of an optional one can still be a task error). To answer:

1. Before opening `blind\key.json`, copy every line of text you can read in each crop of `blind\A\` and `blind\B\`,
   top to bottom, exactly as shown (`?` for a character you can't read for sure, `[]` when there is no text), into
   `blind\answers.json`:

   ```json
   {"A": ["COMBO x3"], "B": ["COMBO"]}
   ```

   For a probe that reads a list of shots, give each shot's lines by its name:
   `{"A": {"before": ["12"], "after": ["15"]}, "B": {"before": ["12"], "after": ["12"]}}`.
2. Check the task again. The checker reads the answer with the Lab's own reduction (the `match`, the first number, the
   first time; the `agg` over a list of shots) and uses the values as the start's and the reference's measures, so
   the probe decides VALID or INVALID like any other. A reference whose answer gives nothing the probe reads is a
   task error, as in the Lab, so the task is INVALID whether the probe is required or not. The line then says
   `seen <check>: read from blind/answers.json`.
   When the reference's crop doesn't show the text asked, rewrite the play as for a judge (above), never the probe's
   `match`.

The folder is kept from one check to the next, and an answer stands while its crop is the same (`crops.json`); a
crop that changed (another commit, a play that changed) drops that side's answer, with a note. A start that doesn't
build by design is never played: only the reference is saved, as `blind\A\`. In the Lab the model must read the start
and the reference the same 3 times out of 3, or the probe is a task error. This check asks no model, so it holds your
answer to that bar instead (local only): a `?` in the reference's answer, or in the start's when the threshold is
relative to the start, is a task error. Make the text one you can read for sure (larger, at a stiller moment, a looser
rect); a crop you can read only at full zoom may not read the same 3 times either.

A task with no reference is checked on its start alone: it must build, fail every required probe outside
`still_works` (thresholds relative to the start, or literals), and pass its still-works probes. Every shipped task has
a reference (write-tasks section 1; `tools/validate-game.py` rejects one without), so this is for drafts only.

## Results

- One line per task on the console; progress goes to stderr.
- `<repo>\.task-checks\<task>.json` (format `task-check/2`): `verdict`, `reasons` (why INVALID), `notes`, the `start` and
  `reference` commits and whether they built, `probes` (per probe: its milestone, `required`, `op`, `expect`, the
  `start` and `reference` measures, the `threshold`, and whether each side passed), every check's row on each side
  (`start_checks`, `reference_checks`: `passed` and a `detail` such as
  `... | measured 118, threshold >= 119.274 (start 118, fix 120.547)`), and the task file's `task_sha256`. Every result
  also has `task_digest`, which binds it to the whole task, and `at` (the check's ISO 8601 timestamp). The strict schema is [schemas/task-check.schema.json](schemas/task-check.schema.json).
- `<repo>\.task-checks\<task>\<side>\<play>\`: each play's `probe.json` (the track, the camera rows, every measure's
  samples), its screenshots and its log; `build\build.log` when a build failed. Read these when a value surprises you.
- `<repo>\.task-checks\<task>\judge-shots\<check>\`: each judge check's pictures to answer (VALID and INVALID
  above); the result's `judges` lists them, each `answer needed`.
- `<repo>\.task-checks\<task>\seen-shots\<check>\`: each `seen` probe's crops to answer (above); the result's `seen`
  lists them, each `answer needed` or `read from blind/answers.json`.
- `.task-checks\` is git-ignored: new games have it in `.gitignore` (templates/ue-game); for an older game the checker
  adds it to the repo's own `.git\info\exclude`. Never commit results.

## Writer scores and delivery

Commit the task's final edits on the tasks branch, then check it. Packaging reads the newest result at
`<repo>\.task-checks\<task>.json`; an older VALID result cannot replace the latest INVALID or ERROR. It refuses a
missing or malformed result, a verdict other than VALID, or a `task_digest` that differs from that task. A matching
digest establishes freshness regardless of commit dates: rebasing or amending an unchanged task needs no new check.
Only a legacy `task-check/1` result without a digest falls back to comparing its `at` with the last commit changing
`Tasks/<task>.json` on the tasks branch; it refuses a missing commit timestamp or a check older than that commit.
`task-check/2` always requires a digest. Even a small content edit needs another check. The digest binds the task
alone, not the checker or its TaskProbe plugin: after you pull a change to either, check your tasks again before
packaging, because a result from the earlier checker still matches an unchanged task's digest while the cloud grades
with the new one. Required judge and `seen`
answers must be complete before the task ships.

`task_digest` is the lowercase SHA-256 of the whole task encoded as canonical JSON: sorted object keys, no spaces
between tokens, Unicode kept as Unicode (`json.dumps(task, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`),
then UTF-8. This is the same digest Lab computes after merging the delivered halves: copy `task.json`, overlay
`grader.json`'s `milestones`, and merge the grader's `seed` into the task's `seed`. `task_sha256` remains the hash of
the original task file's bytes. The packager first checks the result against the original task on the tasks branch,
then verifies that the delivered task differs only by the package's full commit-ID substitutions. Any other scrub
change refuses packaging: fix that text on the tasks branch and check it again. For a matching task it binds the
shipped `task_digest` to the delivered merged task, without changing the verdict or measures. The manifest records
`tasks.last_commit_at` as a map from each task name to its original tasks-branch last commit time (ISO 8601 with
Git's timezone offset), so a consumer can apply the legacy time fallback without receiving the private tasks branch.

Before packaging, the writer's agent **asks the person to score every task**: confirm hard or medium (matching the
task), give a quality rating from 1 to 5, estimate how many minutes a strong agent would take to solve it, and supply
a short note. Quality means a long thread, every ask checked, fair to an agent. The 25-minute guide in write-tasks
section 6 helps that discussion; it is not a cut-off. Record their answers in
`<repo>\.task-checks\writer-scores.json` (schema
[schemas/writer-task-scores.schema.json](schemas/writer-task-scores.schema.json)):

```json
{
  "schema": "writer-task-scores/1",
  "tasks": {
    "game-fix-long-thread": {
      "difficulty_estimate": "hard",
      "quality": 4,
      "minutes_to_solve_estimate": 45,
      "judges": {
        "looks_as_asked": {
          "start": {"clear_feedback": 0},
          "reference": {"clear_feedback": 1}
        }
      },
      "notes": "Several interacting changes; each requested outcome has a check."
    }
  }
}
```

There is exactly one row for every shipped task. `difficulty_estimate` is `hard` or `medium` and agrees with the
task's `difficulty` (`medium` when omitted); `quality` is an integer 1-5; `minutes_to_solve_estimate` is a positive
number; `notes` is one line of plain text, at most 300 characters. Notes are data for staff, never instructions to
another contractor. `judges` maps each answered judge's name to `start` and `reference` rubric-key scores from 0 to
1, transcribed from the task's notes after blind scoring. A task with no judges uses `{}`. All required judges must
have their scores; the agent never fills missing answers with guesses.

`tools/package-dataset.ps1` ships the result as `Checks/<task>.json` and these scores as
`Checks/writer-scores.json`. It copies only the small blind answer JSON files into
`Checks/<task>/judge-shots/<check>/blind/answers.json` and
`Checks/<task>/seen-shots/<check>/blind/answers.json` when present. Each answer file must be a nonempty object whose
only keys are `A` and/or `B`; each side's JSON is limited to 8 KiB, and the whole file to 16 KiB.
Screenshots, `probe.json`, logs, blind keys and
all other run artifacts stay on the writer's PC. The per-probe measures and check rows remain in the result JSON.
`Checks/` is staff/grader material, kept out of the agent's snapshot with `Tasks/`, `History/` and `Dataset/`.

A dataset check uses the same shape, binding, verdict, freshness and score requirements. During rollout,
`python tools/validate-game.py --dataset <Dataset.zip> --checks-mode warn` reports their failures as warnings
(the default). Use `--checks-mode reject` when the Lab project switches to reject mode; those failures then make
the dataset INVALID. Packaging refuses them by default, whichever validation mode a consumer uses.

**Temporary Lab compatibility switch.** Lab does not yet accept a top-level `Checks/` folder: its layout validator
rejects it as `layout.unexpected`. Until Lab's format change is deployed and the project reads `Checks/`, use
`tools/package-dataset.ps1 <game> -Package <package> -NoWriterChecks`. The matching Python helper option is
`python tools/package-checks.py <repo> <split Tasks dir> <Checks out> --no-writer-checks`. Each skips the writer-check
refusal and omits `Checks/`, printing one warning; task packaging and the other package validations still run.
The default remains to validate and ship `Checks/`. Remove this temporary switch once Lab's project reads `Checks/`.

## Common reasons and fixes

**`start already passes every required probe`.** The bug doesn't show in what the probes measure.
- The play never reaches the situation: the idle `look` stands at the spawn, the `drive` walks a fixed pattern. Write a
  task play that gets there: a `teleport` input (`{"t": 0.2, "teleport": [x, y, z], "yaw": 90}` places the player pawn;
  take the coordinates from the editor, or from the `track` in a play's `probe.json`), its own `map` with options
  (`/Game/Maps/L_Arena?Scenario=2`) and `args` (`-Scenario=2`), and the inputs that trigger the bug.
- The measure is the wrong one: compare the start's and the reference's `probe.json` samples for the field you read
  and pick one that differs.

**`calibration impossible in X: ... the start and the reference both measure X`** (the check's row says
`uncalibrated: ...`). The measures are equal on both sides, so there is nothing to put a threshold between: the probe
doesn't see the change. This holds for an optional probe too: the cloud's grade can't make the threshold, so it grades
no run of the task. Measure something the fix changes (a
different field, window or play), or use a literal value when the fact is a count or a boolean.

**`no samples in the window (the play ended at X s)`.** The play ended before the window: the window or `at` lies past
the play's `seconds`, or the game crashed or quit (see the play's log). **`the play wrote no probe file`**: the game
never got to play (a crash at load, a map that doesn't exist). **`map X could not be loaded (the game ran Y | the game
opened no map; ...)`**: the play asked for a map (its own `map`, else `play_map`) and ended in another or in none: the
map isn't in that commit (a map only the reference has), or it is broken.

**`the play's first session (play X) did not end cleanly`**, or, on the reference, **`the task's own fix carries
nothing over to the next session`**. A play that `continues` another: its first session crashed, timed out or was cut
off, or the reference's wrote no file under `Saved/`. Give the first session the inputs that make the game save (a
save made on a menu action needs that action), and time for it; the game's save on quit runs when the play ends.

**`its event never happened (its <probe> <field> never read <op> <value>)`.** The measure's `since` event never came in
the play (or not within its `within` seconds), so the measure has no value; on the reference a calibrated threshold is
then uncalibrated. Check in the play's `probe.json` that the event's measure reads what its `expect` asks on the side
that failed: the play may stop before the event, or the event's measure may select the wrong thing.

**`no value in the window (nothing it selects was measured)`.** The selection matched nothing, or nothing it matched
has that field. `class` is the class name without its prefix letter (`SCCastlePiece` for `ASCCastlePiece`; a Blueprint
by its asset name with `_C`, `BP_Wall_C`); a component property is `prop:<Component>.<Property>`; `; the plugin said:
...` quotes what the plugin couldn't read. The `rows` in the play's `probe.json` show what was found.

**`of` defaults to `count`.** For `actors`, `widgets`, `components` and map `asset` measures, `of` combines the
selected rows of one sample, and without it a field like `z` counts the rows whose value isn't 0 instead of reading
the value. Set `"of": "first"`, `"max"`, `"min"` or `"mean"` when you mean the value.

**More than 200 matches.** The plugin keeps at most 200 rows a sample in `probe.json`, but reads every match: the
sample's `total` is how many matched and `full` sums up every match's numeric value of each field (`n`, `nonzero`,
`sum`, `min`, `max`). `count` reads `total`, and `of` (`count`, `any`, `all`, `sum`, `min`, `max`, `mean`) reads
`full`, so neither stops at 200. Only `"of": "first"` and values read through `match`, `to_angle` or `to_axis` read the
200 rows alone. Before 2026-11-06 the checker counted the rows, so a selection of 389 read 200.

**Angles.** `yaw`, `pitch`, `roll`, `rel_yaw:`, `world_yaw:`/`world_pitch:`/`world_roll:` and `components`'
`world_yaw`/`world_pitch` are normalised to
(-180, 180], so a raw yaw jumps from 180 to -180
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

**`task error in X: in the reference's play P, an input did not land (...): the task's own fix can't be driven by its
play`.** The play's click, tap, wheel or stage found nothing on the reference (the play's `probe.json` lists it in
`inputs_missed`). Drive the play by what the reference shows at that moment: the on-screen text the instruction gives,
a wait until the screen is there, a stage on something both sides have. A click "covered by another control" met
something drawn over its button: close it in the play first, as a player would. A `shot_when` miss ("its event never
happened") is a shot whose event didn't come within its `within` or by the play's end: lengthen the play, or read the
event from what the reference really shows. **`the play's input did not land: ...`** on
the start alone is the start failing the check (often the task's own bug: the button isn't there yet).

**`task error in X: in the reference's play P, its selector {...} matched nothing in N samples: the check reads nothing
even on the task's own fix`** (or `nothing its selector matched had a value for F`; or, for a count, `the task's own
fix fails it`). No build can pass the check as written: the selector names something the reference doesn't have in
that play, or a field its rows don't carry. Read the rows in the reference's `probe.json` and select by what the thing
does or carries, or by a name the start already has.

**`task error in X: in the reference's play P, its first session ... : the task's own fix carries nothing over to the
next session`.** See the session reason above: on the reference this can be passed by no build.

**`its probe file was malformed`**: the play's `probe.json` isn't of the plugin's shape (a game that wrote over it, a
cut-off file); it reads as nothing, as in the cloud.

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

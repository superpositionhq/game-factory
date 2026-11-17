# Game format v1

The final format of a game: its **repo** at the release commit and its **dataset** (`Dataset.zip`, layout v1.3). It is
the same for every game, whether a game session here made it or a contractor delivered it. What the RL environment
needs from a game (tasks that start from any commit, the person's directions, the brief) is in it.

| Machine-readable | What |
|---|---|
| [game-format-v1.json](game-format-v1.json) | the rules for the repo and the dataset (this page in JSON) |
| [dataset-layout-v1.3.json](dataset-layout-v1.3.json) | the dataset's entries, names, video format, manifest keys, README sections (earlier: [v1.2](dataset-layout-v1.2.json), [v1.1](dataset-layout-v1.json)) |
| [schemas/dataset-manifest.schema.json](schemas/dataset-manifest.schema.json) | `manifest.json` |
| [schemas/workflow-row.schema.json](schemas/workflow-row.schema.json) | one row of `workflow.jsonl` |
| [schemas/replay-report.schema.json](schemas/replay-report.schema.json) | `ReplayScripts/Verification/report.json` |
| [schemas/assets-manifest.schema.json](schemas/assets-manifest.schema.json) | the repo's `assets.manifest.json` (one format for every game) |
| [schemas/task-check.schema.json](schemas/task-check.schema.json) | `Checks/<task>.json` (`task-check/2`) |
| [schemas/writer-task-scores.schema.json](schemas/writer-task-scores.schema.json) | `Checks/writer-scores.json` (`writer-task-scores/1`) |

## Validate

```bash
python tools/validate-game.py <games>/<slug>
```
```bash
python tools/validate-game.py --dataset <path to Dataset.zip>
```

The first checks the repo, then its `Dataset/` and `Dataset.zip`; the second checks a dataset alone, the way a
consumer receives it. Both run `tools/validate-dataset.ps1` (layout, sizes, sha256, videos) on Windows. Verdict
**VALID** or **INVALID** (exit 0 / 2); warnings never change it. Options: `--quick` (do not unpack the history),
`--no-hash`, `--no-layout`, `--json <file>`. `--checks-mode warn` is the default while writers update their skill
packs: problems with `Checks/` warn. `--checks-mode reject` makes those problems errors when the Lab project switches
to reject mode. Packaging requires valid checks and scores by default; the temporary `-NoWriterChecks` compatibility
switch omits them until Lab reads `Checks/` (see [task-check.md](task-check.md)). Standard library Python 3.10+.

## The repo

Everything needed to rebuild the game from the repo alone, tracked in git (binaries in Git LFS):

| Path | Rule |
|---|---|
| `<Project>.uproject` | one, `EngineAssociation` 5.7 (5.3 for the first games) |
| `Source/<Project>/AutoPlay/AutoPlaySubsystem.h/.cpp` | the AutoPlay drop-in ([autoplay-contract.md](autoplay-contract.md)) |
| `Config/`, `Content/` | project config; all game content, store packs included |
| `Scripts/` | every editor script that was run, kept unchanged |
| `workflow.jsonl` | the creation record, one row per operation, written when it happened (row schema) |
| `README.md` | hero image + captioned gallery of 5-7 real gameplay stills, every image committed |
| `assets.manifest.json` | every external asset in `assets-manifest/v1` (below) |
| `Docs/ThirdPartyNotices.md` | credits and licences |
| `ReplayConfig.json` | creation replay config ([ue-replay.md](ue-replay.md)) |
| `Platform.json` | a mobile game only ("Platform", below): `{"platform": "mobile", "orientation": "landscape" or "portrait"}`; a desktop game has no such file |
| `.gitattributes`, `.gitignore` | LFS for every binary type; `/Dataset.zip`, `/Dataset.pending.zip`, `/.dataset/` ignored; `Content/` never ignored |
| `Dataset/` | the dataset minus `UEProject/`, `Build/`, `History/`, `Tasks/` and `Checks/` (written by the packager) |

**Tasks live on the orphan `tasks` branch, never on main.** The same repo has a branch `tasks` that shares no history
with main: `Tasks/<game>-<kind>-<slug>.json` (one task each in the task format `GameTask`,
[schemas/game-task.schema.json](schemas/game-task.schema.json); at least 5, up to about 10, at least 4 of them hard (the others may be medium, none easier), every one a long thread of
multiple edits; written with the `write-tasks` skill), a short `README.md`, optionally `tasks-workflow.jsonl`. It is checked out as a git worktree
outside the game folder (e.g. `<root>/tasks/<slug>`), committed and pushed there. Task work never enters the game's
history: main never tracks `Tasks/` and never references the tasks branch, the recording and live-replay hooks ignore
commits on it, and the delivered history leaves it out. Seeds (`seed.commit`, `seed.reference`) point at commits of
main's history.

**Combat contract (every game not yet submitted, from 2026-11-11).** In a game where anything can be hurt, damage is received in
`AActor::TakeDamage` (or an `OnTake*Damage` handler) and dealt through `UGameplayStatics::Apply*Damage` or a target's
`TakeDamage`; every key gameplay state member (a number, bool or enum named with a word of health, hp, hitpoints,
hull, poise, armor, shield, stamina, mana, lives, dead, alive, dying, stun, stagger, invulnerable, invincible, guard,
blocking, parry, alert, aggro, awake, asleep, dormant, roused or cooldown; a whole number or enum named with phase or
state) is a `UPROPERTY` of a `UCLASS` or `USTRUCT`, UI classes aside; and a situation that takes more than a minute
of play to reach has a scenario start option. Every sound the game plays is an imported asset (a file, or a WAV a
committed script made), never made at run time (no procedural sound wave, synth component or sound generator). The
validator checks the first two (rule `contract`) and the last (rule `sound`) as errors, and `package-game.ps1` and
`package-dataset.ps1` refuse a game that fails them (`validate-game.py <repo> --rules-only`). A game in progress is
brought up to them before it is packaged; games already approved in the Lab are not re-validated.

No tool, vendor or owner names anywhere in the repo's text (the validator scans tracked text files; the packager
scans binaries too). The build machine's account name (machine paths carry it) counts too: the validator reads it at
run time, and enforces it everywhere except in scripts (`Scripts/`, and `.ps1`/`.psm1`/`.py`/`.sh`/`.bat`/`.cmd` files
anywhere), because scripts that already ran stay unchanged; the packager scrubs them in every delivery. In
`ReplayConfig.json` write machine paths with `{root}` / `{home}` (match strings) or `{pipeline}` (tool scripts). That includes `workflow.jsonl`: it is append-only except that a row naming a banned term (or the
old schema id `superposition.ue-workflow/v0`) is edited in place to a neutral word or placeholder, nothing else
changed, with one `log.correct` row appended (`params {rows, what}`) and the edited rows named in the commit message:
`python tools/scrub-workflow-rows.py <repo>` (dry run), then `--apply`.

**Store content.** Store packs may sit in any folder under `Content/` (or `RawAssets/` for import sources): what
matters is that every file the game uses is committed, so a clone builds the game. The repo stays private.
`assets.manifest.json` lists each external asset once:

```json
{ "schema": "assets-manifest/v1", "project": "MyGame", "assets": [
  { "name": "Modular Warehouse", "source": "Fab", "url": "https://www.fab.com/listings/...", "licence": "Fab Standard License",
    "licence_url": "https://www.fab.com/eula", "version": "5.2", "store": true,
    "files": ["Content/Warehouse/"], "used_for": "level kit", "changes": "materials re-tinted" } ] }
```

Every asset needs an https `url` (its listing or source page), except one made in-house by the studio (e.g. the
studio's own earlier project): that one has `"origin": "studio"` and a short `description` (what it is, where it comes
from inside the studio) instead of a url.

`files` are repo paths; one ending in `/` stands for every file under it. Each must be committed (repo check) and be
inside `UEProject/` of `Dataset.zip` (dataset check). Content shipped with the engine and content made by the game's
own scripts are not listed. `tools/migrate-assets-manifest.py <repo>` converts the earlier shapes (dry run first; it
lists what needs a person).

## Platform

A game is a desktop (Windows) game unless its root has `Platform.json`, written by `templates/new-game.ps1 -Platform
mobile -Orientation landscape|portrait` when the project is created and never edited after. That file makes it a mobile
game: an Android phone game held one way, played by touch (the mobile-game skill). Every tool reads the platform from
it through one reader (`tools/validate-game.py` `read_platform`; the PowerShell tools ask it with `validate-game.py
--platform <folder>`): the validator's rule `mobile` holds the project's Android settings in
`Config/DefaultEngine.ini` to it (the orientation, arm64 alone, the SDK levels 26 and 34, Vulkan, the package name
`com.<project lowercase>.game`, the data inside the APK, the Linux and Windows mobile shader formats, nothing of the
desktop renderer alone turned on), a mobile game's task plays never choose a renderer, and the task check, the
recording pipeline and the stills all play a mobile game with the mobile renderer at the phone's size (1920x1080
landscape, 1080x1920 portrait). A file that says anything else is an error, never read as a desktop game.

A mobile game's dataset says so in its manifest: `platform` is `{"kind": "mobile", "orientation": ...}` (a desktop
game's manifest has no `platform`), its gameplay videos have the phone's size, and `Build/` holds the Windows build
the videos were recorded from and the Android Shipping APK (arm64) as `Build/Android/<name>.apk`, named by
`build.apk`. The APK is required: a mobile game's dataset without it is refused, so a mobile game is released from a
machine with the Android toolchain ([new-machine.md](new-machine.md), "Android"). The dataset check compares
`platform` with `UEProject/Platform.json`, the videos with the size, and `build.apk` with `Build/`.

Budgets a mobile game keeps in any view the player can reach: at most 500,000 triangles drawn, 700 draw calls and
1 GB of textures in memory (a task can measure them: docs/task-probes.md, section 2.21). Nothing here changes for a
desktop game.

## The dataset (layout v1.3)

`<repo>\Dataset.zip`, one top folder `<game>/`, made by `tools/package-game.ps1 -Dataset` (which runs
`tools/package-dataset.ps1`):

| Entry | In the repo's `Dataset/` | What |
|---|---|---|
| `README.md` | yes | the game, how to play, open, replay and restore it; sections in the order of the layout file |
| `git.log` | yes | every commit up to the release, oldest first: message, `dev_NN` authors, dates, full text diff; binaries as path + sha256 |
| `workflow.jsonl` | yes | the creation record; **the person's directions are `user.direction` rows** (the prompts and replies themselves are in `History/sessions/`) |
| `Brief/` | yes | `brief.md`, the original brief; `design.md`, the design doc with story bible and status |
| `History/` | no | `<game>.bundle` (the release commit's history as `refs/heads/main` and each task's start branch as `refs/heads/starts/<task>`, nothing else: no side branch, tag off main or stash, and never the tasks branch) and `lfs/objects/<aa>/<bb>/<sha256>` (every Git LFS object of every commit of the bundle); `sessions/messages.jsonl` (every prompt the person typed and every reply the model wrote) and `sessions/actions.jsonl` (every tool call), when the game's sessions were recorded |
| `Tasks/` | no | the game's tasks, each split: `Tasks/<name>/task.json` (the agent's part) and `Tasks/<name>/grader.json` (milestones, `seed.reference`), plus a generated `README.md` |
| `Checks/` | no | every shipped task's latest VALID `task-check/2` result (`<task>.json`), `writer-scores.json` (`writer-task-scores/1`), and small blind judge/`seen` answer JSON files; no screenshots, probes or logs |
| `UEProject/` | no | the project at the release commit, store content included |
| `ReplayScripts/` | yes | the creation replayed headless, with `Verification/report.json` (required for complete; its verdict PASS or FAIL is metadata) |
| `Gameplay/<game>_S<n>.mp4` | yes | at least one scenario video (user rule 2026-10-19: one recorded scenario is enough, the first valid one by scenario order; videos of other scenarios already recorded may be included), 1920x1080 h264 + aac |
| `Screenshots/` | yes | the README's images |
| `Build/` | no | the packaged Windows Shipping build, no `.pdb` |
| `manifest.json` | yes | metadata, `history`, `brief`, and path / bytes / sha256 of every file except the content-addressed `History/lfs/objects/` |

**The sessions' record (`History/sessions/`, owner 2026-11-10).** What the recording hooks wrote while the game was
made (machine/README.md, Recording), one JSON row per line: `messages.jsonl`, every prompt the person typed (`role`
`user`), every reply the model wrote (`role` `assistant`) and every reasoning summary the agent saved (`role` `thinking`;
a `thinking` row is a reasoning summary the agent saved for a turn (`redacted` true and no text when the agent saved it without readable text)), and `actions.jsonl`, every tool call with its input and
its whole result (up to 1,000,000 characters, `response_chars` and `response_truncated` on a longer one; a picture or other binary payload as a short marker). A game recorded before 2026-11-12 has no `thinking` rows and only the start of each result. Rows up to the release commit's time, without the sessions that packaged; scrubbed like every
other text file; full commit ids are the delivered history's. `session_id` is `session_NN`, the same session in both
files, and `time` orders the rows. `manifest.json` `history.sessions` names the files and counts their rows. Both files
are optional: a game whose sessions were recorded before prompts and replies were has no `messages.jsonl` (the
validators note it, never an error).

**The history is rewritten for delivery** (user decision 2026-10-15; the game repos are not changed): authors and
committers become `dev_NN`, agent trailer lines go, the scrub rules apply to every message and text blob, and LFS
objects that name the build machine's account are patched (same length). The scrub replaces a name in text only as a
whole word, never inside an identifier (`_` counts as part of a word), and only a name of 4+ characters that is not a
generic word (dev, user, admin, test, ...): a short or generic author name is anonymised in the commit metadata only
(author, committer, tagger, `Co-authored-by:` / `Signed-off-by:` trailers), a short or generic account name in user
paths only, so the game's code (`WITH_DEV_AUTOMATION_TESTS`) is delivered as it was written. Commit ids therefore differ from the private
repo; the dataset uses the delivered ids everywhere (`manifest.json` `commit`, `git.log`, `ReplayScripts/`), and the
packager keeps the old -> new map next to the package. Restore a commit:

```bash
git clone History/<game>.bundle <game>
```

then copy `History/lfs` into `<game>/.git/lfs`, `git lfs install --local`, `git checkout <commit>`, `git lfs checkout`.

**Tasks.** A game is complete when its repo's orphan `tasks` branch has `Tasks/`: tasks an agent can be given on
this game (a bug fix from its history, a correction from a person's direction, a feature, a look or content change),
in the task format (`GameTask`, game-task/1), one file per task named
`<game>-<kind>-<slug>.json` with `name` equal to the file name. About 10 are recommended. A game with fewer than 5 fails, and so does one with
fewer than 4 `hard` tasks: the others may be `medium` (what a task that names no difficulty is), none easier. The tasks branch is the single source: tasks are loaded as `Tasks/*.json` from
the repos' tasks branches. How to write them: the `write-tasks` skill. The validator reads the tasks from `tasks`
(else `origin/tasks`) and checks each against [schemas/game-task.schema.json](schemas/game-task.schema.json)
(the task format; probe checks: [task-probes.md](task-probes.md)), that its seed is on this game and its seed commits are ancestors of main's head,
that the branch shares no history with main, and that main tracks nothing under `Tasks/`.

In a dataset (layout v1.3) the packager copies the tasks from the tip of the tasks branch, maps each seed's commits
through the history rewrite, scrubs them, and splits each into `Tasks/<name>/task.json` (what the agent may see) and
`Tasks/<name>/grader.json` (the grader's half: `milestones` with their probes, rubrics, judge and code-judge questions and
log patterns, and `seed.reference`); merging the two gives the task. `Tasks/README.md` explains it.

**Writer checks and scores.** By default every newly packaged task ships `Checks/<name>.json` from
`<repo>/.task-checks/<name>.json`, a `task-check/2` result. Packaging refuses a missing, INVALID or ERROR result, or a
`task_digest` different from the task. A matching digest establishes freshness despite rebases or amends; only a
legacy `task-check/1` without a digest uses the task file's last commit time as its freshness fallback. The
digest is the SHA-256 of the whole task as sorted, compact, Unicode JSON encoded as UTF-8, the same canonicalisation
Lab uses for the merged halves. The packager validates the original binding and verifies that the delivered task
differs only by full commit-ID substitutions through the delivery's commit map. Other scrub changes refuse
packaging and must be fixed and checked in the source. It then binds the shipped result to the delivered merged
task. `task_sha256` keeps its original meaning. `manifest.tasks.last_commit_at` maps each task name to its tasks-branch
last commit time (ISO 8601 with Git's timezone offset), for the legacy fallback without the private tasks branch.

`Checks/writer-scores.json` has schema `writer-task-scores/1`, with a `tasks` object keyed by every shipped task's
name. Each row holds `difficulty_estimate` (`hard` or `medium`, matching the task), integer `quality` (1-5), positive
`minutes_to_solve_estimate`, `judges` (blind 0-1 rubric scores by judge, then `start` and `reference`, transcribed
from the task's notes), and `notes` (one line of plain text, at most 300 characters, staff data). The writer's agent
asks the person for these ratings and estimates before packaging and saves them in
`<repo>/.task-checks/writer-scores.json`; missing answers are not guessed. Required judges and `seen` probes must
be answered. Only the small `blind/answers.json` files accompany the results, under
`Checks/<name>/{judge-shots|seen-shots}/<check>/blind/answers.json`; screenshots, `probe.json`, logs and blind keys
stay out. [task-check.md](task-check.md), "Writer scores and delivery", gives the complete file example and rules.

**The harness rule.** An agent given a task starts from a history-less snapshot of the game at `seed.commit`, with
`Tasks/`, `Checks/`, `History/` and `Dataset/` removed (every task's answers are in them, and the reference fixes are in the
history); it sees only the brief and that snapshot. The grader's half never reaches the agent.

**Complete vs pending.** `status` is `complete` when every entry is there, `ReplayScripts/` with its
`Verification/report.json` included; `pending` while `ReplayScripts/` or `Gameplay/` is missing (the zip is then
`Dataset.pending.zip`). A delivery whose `Gameplay/` is pending fails the validator and is rejected at upload: a game
needs at least one gameplay video. The replay is required but need not pass (user rule): a FAIL verdict is metadata, like a
gameplay run's result: manifest `replay_verification.pass` false (equal to the report's `verdict.pass`) and the README
says FAIL.

## For a contractor

Deliver the repo (private, with Git LFS) and run the packager, or deliver the same content yourself:

1. The repo rules above; `assets.manifest.json` in `assets-manifest/v1`.
2. `workflow.jsonl` from the first operation, with every direction you were given as a `user.direction` row
   (neutral wording, what and why) before the work it caused, and `"direction": "<id>"` on the rows that act on it.
3. `Brief/brief.md` (the brief you were given) and `Brief/design.md` (your design doc).
4. Your game's tasks in `Tasks/` on an orphan `tasks` branch of the repo, never on main (at least 5, about 10, at least 4 of them hard, the others may be medium; the
   `write-tasks` skill, or the format and examples it points to), each seeded on commits of main's history.
5. Run the no-op and oracle after each task's last edit; answer required judges and `seen` probes blind. Ask the
   person for each task's scores, then save `.task-checks/writer-scores.json`. The packager ships `Checks/` and refuses
   missing, stale, unbound or non-VALID results and incomplete scores.
6. `python tools/validate-game.py <repo>` VALID, and the same for the `Dataset.zip` (`--checks-mode reject` checks
   the writer files as errors).

Your agent sessions use only the game-factory skills (`commit-always`, `game-session`, `write-tasks`, installed by
`machine/setup.ps1`): never install, enable or invoke any other skill, whether your own personal or project skills,
a plugin's or marketplace's, or one bundled with the agent (AGENTS.md, "Only these skills"). The recorded sessions are
the dataset, so the game is made under these rules alone.

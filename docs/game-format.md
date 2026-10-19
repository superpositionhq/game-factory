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
`--no-hash`, `--no-layout`, `--json <file>`. Standard library Python 3.10+.

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
| `.gitattributes`, `.gitignore` | LFS for every binary type; `/Dataset.zip`, `/Dataset.pending.zip`, `/.dataset/` ignored; `Content/` never ignored |
| `Dataset/` | the dataset minus `UEProject/`, `Build/`, `History/` and `Tasks/` (written by the packager) |

**Tasks live on the orphan `tasks` branch, never on main.** The same repo has a branch `tasks` that shares no history
with main: `Tasks/<game>-<kind>-<slug>.json` (one task each in the game environment's format,
[schemas/game-task.schema.json](schemas/game-task.schema.json); at least one, about 10 recommended; written with the
`write-tasks` skill), a short `README.md`, optionally `tasks-workflow.jsonl`. It is checked out as a git worktree
outside the game folder (e.g. `<root>/tasks/<slug>`), committed and pushed there. Task work never enters the game's
history: main never tracks `Tasks/` and never references the tasks branch, the recording and live-replay hooks ignore
commits on it, and the delivered history leaves it out. Seeds (`seed.commit`, `seed.reference`) point at commits of
main's history.

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

## The dataset (layout v1.3)

`<repo>\Dataset.zip`, one top folder `<game>/`, made by `tools/package-game.ps1 -Dataset` (which runs
`tools/package-dataset.ps1`):

| Entry | In the repo's `Dataset/` | What |
|---|---|---|
| `README.md` | yes | the game, how to play, open, replay and restore it; sections in the order of the layout file |
| `git.log` | yes | every commit up to the release, oldest first: message, `dev_NN` authors, dates, full text diff; binaries as path + sha256 |
| `workflow.jsonl` | yes | the creation record; **the person's directions are `user.direction` rows** (they replace conversation transcripts) |
| `Brief/` | yes | `brief.md`, the original brief; `design.md`, the design doc with story bible and status |
| `History/` | no | `<game>.bundle` (every commit of every ref except the tasks branch) and `lfs/objects/<aa>/<bb>/<sha256>` (every Git LFS object of every commit) |
| `Tasks/` | no | the game's tasks, each split: `Tasks/<name>/task.json` (the agent's part) and `Tasks/<name>/grader.json` (milestones, `seed.reference`), plus a generated `README.md` |
| `UEProject/` | no | the project at the release commit, store content included |
| `ReplayScripts/` | yes | the creation replayed headless, with `Verification/report.json` (required for complete; its verdict PASS or FAIL is metadata) |
| `Gameplay/<game>_S<n>.mp4` | yes | at least one scenario video (user rule 2026-10-19: one recorded scenario is enough, the first valid one by scenario order; videos of other scenarios already recorded may be included), 1920x1080 h264 + aac |
| `Screenshots/` | yes | the README's images |
| `Build/` | no | the packaged Windows Shipping build, no `.pdb` |
| `manifest.json` | yes | metadata, `history`, `brief`, and path / bytes / sha256 of every file except the content-addressed `History/lfs/objects/` |

**The history is rewritten for delivery** (user decision 2026-10-15; the game repos are not changed): authors and
committers become `dev_NN`, agent trailer lines go, the scrub rules apply to every message and text blob, and LFS
objects that name the build machine's account are patched (same length). Commit ids therefore differ from the private
repo; the dataset uses the delivered ids everywhere (`manifest.json` `commit`, `git.log`, `ReplayScripts/`), and the
packager keeps the old -> new map next to the package. Restore a commit:

```bash
git clone History/<game>.bundle <game>
```

then copy `History/lfs` into `<game>/.git/lfs`, `git lfs install --local`, `git checkout <commit>`, `git lfs checkout`.

**Tasks.** A game is complete when its repo's orphan `tasks` branch has `Tasks/`: tasks an agent can be given on
this game (a bug fix from its history, a correction from a person's direction, a feature, a look or content change),
in the game environment's task format (`GameTask`, game-task/1), one file per task named
`<game>-<kind>-<slug>.json` with `name` equal to the file name. About 10 are recommended; the count is reported,
and only a game with none fails. The tasks branch is the single source: the environment loads `Tasks/*.json` from
the repos' tasks branches. How to write them: the `write-tasks` skill. The validator reads the tasks from `tasks`
(else `origin/tasks`) and checks each against [schemas/game-task.schema.json](schemas/game-task.schema.json)
(vendored from the environment), that its seed is on this game and its seed commits are ancestors of main's head,
that the branch shares no history with main, and that main tracks nothing under `Tasks/`.

In a dataset (layout v1.3) the packager copies the tasks from the tip of the tasks branch, maps each seed's commits
through the history rewrite, scrubs them, and splits each into `Tasks/<name>/task.json` (what the agent may see) and
`Tasks/<name>/grader.json` (the grader's half: `milestones` with their probes, rubrics, judge and code-judge questions and
log patterns, and `seed.reference`); merging the two gives the task. `Tasks/README.md` explains it.

**The harness rule.** An agent given a task starts from a history-less snapshot of the game at `seed.commit`, with
`Tasks/`, `History/` and `Dataset/` removed (every task's answers are in them, and the reference fixes are in the
history); it sees only the brief and that snapshot. The grader's half never reaches the agent.

**Complete vs pending.** `status` is `complete` when every entry is there, `ReplayScripts/` with its
`Verification/report.json` included; `pending` while `ReplayScripts/` or `Gameplay/` is missing (the zip is then
`Dataset.pending.zip`). The replay is required but need not pass (user rule): a FAIL verdict is metadata, like a
gameplay run's result: manifest `replay_verification.pass` false (equal to the report's `verdict.pass`) and the README
says FAIL.

## For a contractor

Deliver the repo (private, with Git LFS) and run the packager, or deliver the same content yourself:

1. The repo rules above; `assets.manifest.json` in `assets-manifest/v1`.
2. `workflow.jsonl` from the first operation, with every direction you were given as a `user.direction` row
   (neutral wording, what and why) before the work it caused, and `"direction": "<id>"` on the rows that act on it.
3. `Brief/brief.md` (the brief you were given) and `Brief/design.md` (your design doc).
4. Your game's tasks in `Tasks/` on an orphan `tasks` branch of the repo, never on main (about 10; the
   `write-tasks` skill, or the format and examples it points to), each seeded on commits of main's history.
5. `python tools/validate-game.py <repo>` VALID, and the same for the `Dataset.zip`.

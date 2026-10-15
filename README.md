# game-factory

Game-**creation** data: how a game gets made, step by step, with the finished project as ground truth.

We build new 3D games in Unreal Engine 5 and record the creation as it happens: real editor operations with
timestamps, screen video, inputs, code commits and a playtest with inputs.

**Priorities (user decision).** What ships is what matters, in this order: the game plays; the game builds (editor and packaged Shipping); the dataset holds the replay scripts and the git log. The AutoPlay bot should still play like a human (human-like input, aim and camera), but bot work never blocks a release: one recording per scenario that shows the game running is enough, whatever the result (win/lose/timeout is metadata). No tuning for win rates, seed sweeps or "clean" runs, and no re-runs or re-recordings to improve how the bot plays. No retest loops: every GPU or editor run costs about 30 minutes of the shared machine and holds up delivery, so run the minimum once and report; re-run only when the user asks. Game-session work never blocks dataset packaging or sharing.

## Getting started

On a fresh Windows 11 PC (8+ threads, 16 GB RAM or more, 300 GB free; an NVIDIA GPU only for recording), with a
GitHub account in `<org>` (the organisation that owns this repo and the private `game-<slug>` repos), an Epic Games
account and a Claude account:

1. Get `machine/setup.ps1` (Download ZIP on github.com, or `gh api`; [docs/new-machine.md](docs/new-machine.md)) and
   run the one command: `powershell -ExecutionPolicy Bypass -File setup.ps1 -Org <org>`. It installs the toolchain
   through winget, asks before changing Windows settings, signs in to GitHub, clones this repo into the root, runs
   `machine/bootstrap.ps1` (which asks before installing the recording hooks) and `machine/check.ps1`, and ends with a
   PASS / TODO list.
2. Do the TODOs only you can do (Epic sign-in + Unreal Engine 5.7 in the Launcher, the NVIDIA driver, Fab and Claude
   sign-in) and run setup again until nothing is left.
3. Start the first session: with the desktop app, the coordinator ([docs/briefs/coordinator.md](docs/briefs/coordinator.md));
   or solo in a terminal, one game with [docs/briefs/solo-game.md](docs/briefs/solo-game.md).

## How a game goes from idea to dataset

1. **Story bible and design doc**: `docs/games/<slug>.md` (pitch, systems, maps, scenarios, art and story), after a
   duplicate check against the games already made.
2. **New project**: `templates/new-game.ps1` creates `%GF_ROOT%\games\<slug>` from the UE 5.7 template: hooks that
   record every action and commit, `ReplayConfig.json` (`"live": true`), `Scripts/ue.ps1`, a private GitHub repo.
3. **Build**: the session follows the `commit-always` and `game-session` skills; every action is recorded
   (`workflow.jsonl`, the action hooks, git history).
4. **Creation replay in the background**: after every commit, the post-commit hook starts the live replay
   (`tools/ue-replay`, `ue_replay.py live`). It replays the new commits into an isolated copy of the project at low
   priority and checks them against the commit. Anything that keeps the history from replaying comes back to the
   session at its next commit ([docs/ue-replay.md](docs/ue-replay.md), section 3).
5. **Framing check, then the recording queue**: AutoPlay contract v1.4, one gameplay mp4 per scenario
   ([docs/ue-pipeline.md](docs/ue-pipeline.md)).
6. **Scrub and privacy**: no user names, machine paths or tool names in anything that ships (`tools/package-game.ps1`
   scrub rules, leak scan).
7. **Dataset v1.1**: `ue_replay.py release` (the replay is already verified, so only the last windows, a full final
   verify and the package remain: minutes), then `tools/package-dataset.ps1` writes `games\<slug>\Dataset.zip`.

## Dataset format (layout v1.3, all games)

Every game is delivered in **dataset layout v1.3** ([docs/game-format.md](docs/game-format.md)): the creation record
(`git.log`, `workflow.jsonl` with the person's directions, `ReplayScripts/`, the full git history in `History/`), the
brief and design doc, the project, per-scenario gameplay videos, README screenshots and the packaged build:

```
<game>/                          games\<game>\Dataset.zip (always with store content; git-ignored)
  README.md
  git.log
  workflow.jsonl                 editor operations + user.direction rows (the person's directions)
  Brief/                         brief.md (the original brief), design.md (design doc, story bible, status)
  History/                       <game>.bundle (every commit but the tasks branch) + lfs/objects/ (every LFS object); not in the repo Dataset/
  Tasks/                         the game's tasks, each <name>/task.json (agent) + grader.json; from the tasks branch
  UEProject/                     not in the repo Dataset/
  ReplayScripts/
  Gameplay/<game>_S<n>.mp4       one video per scenario of the release version, game audio muxed
  Screenshots/                   the README's hero and gallery
  Build/                         Windows Shipping, no .pdb; not in the repo Dataset/
  manifest.json
```

Each game repo keeps the same delivery in `Dataset/`, minus `UEProject/`, `Build/`, `History/` and `Tasks/` (its tasks
live in `Tasks/` on the repo's orphan `tasks` branch, never on main). The game repo itself
follows the same format's repo rules (one `assets.manifest.json` format, every asset committed). Machine-readable:
[docs/game-format-v1.json](docs/game-format-v1.json), [docs/dataset-layout-v1.3.json](docs/dataset-layout-v1.3.json),
[docs/schemas/](docs/schemas/). Build with `tools/package-game.ps1 ... -Dataset`; check a repo and its datasets with
`python tools/validate-game.py <repo>` (or `--dataset <zip>`). Earlier deliveries stay valid as layout v1.2 or v1.1
([docs/game-deliverable.md](docs/game-deliverable.md#dataset-layout-v11-the-delivery)).

## Read first

- [docs/plan.md](docs/plan.md): the plan, phases, open decisions.
- [docs/autoplay-contract.md](docs/autoplay-contract.md): what each game implements so a bot can play and record it.
- [docs/ue-pipeline.md](docs/ue-pipeline.md): build, package, smoke-test and gameplay recording pipeline (`tools/ue-pipeline/`).
- [docs/game-format.md](docs/game-format.md): the final game format (repo + Dataset.zip layout v1.3), its schemas and `tools/validate-game.py`.
- [docs/game-deliverable.md](docs/game-deliverable.md): the per-game deliverable (`tools/package-game.ps1`): layout, store-content variants, scrub.
- [AGENTS.md](AGENTS.md): rules for agents working here (each with the failure behind it).
- [CLAUDE.md](CLAUDE.md): what every Claude session reads first; points at the skills in `.claude/skills/`
  (commit-always, game-session).
- [docs/new-machine.md](docs/new-machine.md): setting up another Windows machine (`machine/setup.ps1`, which runs `machine/bootstrap.ps1` and `machine/check.ps1`).
- [docs/briefs/](docs/briefs/README.md): the prompts that start the coordinator, game and helper sessions (templates + originals).

## Layout

```
tools/ue-pipeline/                  UE build, package and gameplay recording pipeline; AutoPlay drop-in
tools/package-game.ps1, package-dataset.ps1   per-game deliverables and dataset layout v1.1
tools/ue-replay/                    creation replay: per-commit (live) and at release; ReplayScripts/ of the dataset
machine/                            machine setup: setup (entry point), bootstrap/check, ue-heavy limiter, recording hooks, ffmpeg, asset-scout
templates/                          UE 5.7 game skeleton + new-game.ps1
.claude/skills/                     commit-always, game-session
docs/                               everything learned so far; docs/briefs/ = session prompts
```

Machine paths in docs are written `%GF_ROOT%` (the Work root: env `GF_ROOT`, else `%USERPROFILE%\.game-factory\config.json`,
else `%USERPROFILE%\Work`); see [machine/README.md](machine/README.md).

Full packages (tens of GB with the project snapshot) do not go in this repository.

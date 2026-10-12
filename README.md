# game-factory

Game-**creation** data: how a game gets made, step by step, with the finished project as ground truth.

We build new 3D games in Unreal Engine 5 and record the creation as it happens: real editor operations with
timestamps, screen video, inputs, code commits and a playtest with inputs.

**Recordings and results.** Gameplay recordings capture real play. The result (win/lose/timeout) is metadata, never a
quality gate. Never re-record or exclude a run because the bot lost. Package the first valid run per scenario. Bots
should play like a competent human, which doesn't mean they must win.

## Dataset format (layout v1.1, all games)

Every game is delivered in **dataset layout v1.1**, our standard delivery: the creation record (`git.log`,
`workflow.jsonl`, `ReplayScripts/`), the project, per-scenario gameplay videos, README screenshots and
the packaged build:

```
<game>/                          games\<game>\Dataset.zip (always with store content; git-ignored)
  README.md
  git.log
  workflow.jsonl
  UEProject/                     not in the repo Dataset/
  ReplayScripts/
  Gameplay/<game>_S<n>.mp4       one video per scenario of the release version, game audio muxed
  Screenshots/                   the README's hero and gallery
  Build/                         Windows Shipping, no .pdb; not in the repo Dataset/
  manifest.json
```

Each game repo keeps the same delivery in `Dataset/`, minus `UEProject/` and `Build/`. Spec:
[docs/game-deliverable.md](docs/game-deliverable.md#dataset-layout-v1-the-delivery-approved-2026-10-12), machine-readable:
[docs/dataset-layout-v1.json](docs/dataset-layout-v1.json). Build with `tools/package-game.ps1 ... -Dataset`, check with
`tools/validate-dataset.ps1 <zip | folder>`.

## Read first

- [docs/plan.md](docs/plan.md): the plan, phases, open decisions.
- [docs/autoplay-contract.md](docs/autoplay-contract.md): what each game implements so a bot can play and record it.
- [docs/ue-pipeline.md](docs/ue-pipeline.md): build, package, smoke-test and gameplay recording pipeline (`tools/ue-pipeline/`).
- [docs/game-deliverable.md](docs/game-deliverable.md): the per-game deliverable (`tools/package-game.ps1`): layout, store-content variants, scrub.
- [AGENTS.md](AGENTS.md): rules for agents working here (each with the failure behind it).
- [CLAUDE.md](CLAUDE.md): what every Claude session reads first; points at the skills in `.claude/skills/`
  (commit-always, game-session).
- [docs/new-machine.md](docs/new-machine.md): setting up another Windows machine (`machine/bootstrap.ps1`, `machine/check.ps1`).
- [docs/briefs/](docs/briefs/README.md): the prompts that start the coordinator, game and helper sessions (templates + originals).

## Layout

```
tools/ue-pipeline/                  UE build, package and gameplay recording pipeline; AutoPlay drop-in
tools/package-game.ps1, package-dataset.ps1   per-game deliverables and dataset layout v1.1
machine/                            machine setup: bootstrap/check, ue-heavy limiter, recording hooks, ffmpeg, asset-scout
templates/                          UE 5.3 game skeleton + new-game.ps1
.claude/skills/                     commit-always, game-session
docs/                               everything learned so far; docs/briefs/ = session prompts
```

Machine paths in docs are written `%GF_ROOT%` (the Work root: env `GF_ROOT`, else `%USERPROFILE%\.game-factory\config.json`,
else `%USERPROFILE%\Work`); see [machine/README.md](machine/README.md).

Full packages (tens of GB with the project snapshot) do not go in this repository.

# game-factory

Game-**creation** data: how a game gets made, step by step, with the finished project as ground truth.
It is the counterpart to Superposition Lab's game-**play** data (people playing games, recorded with inputs and voice).

Two tracks:

1. **LiaoZhai replication.** Turn the real 4-year history of a shipped Unity game,
   [MapleLeafGitHub/LiaoZhaiRL](https://github.com/MapleLeafGitHub/LiaoZhaiRL) (private), into feature-sized
   creation packages: editor-level steps derived from real commits, the code history, and the project snapshot.
2. **New 3D games in Unreal.** Build new games in Unreal Engine 5 and record the creation as it happens:
   real editor operations with timestamps, screen video, inputs, code commits and a playtest with inputs.

Both tracks start from a format a data vendor sent us (three Unreal packages, `parkour`, `island_explore` and `robofootball`):
see [docs/vendor-packages.md](docs/vendor-packages.md) for what they contain and where they fall short.

## Dataset format (layout v1, all games)

Every Track B game is delivered in **dataset layout v1**, the vendor samples' top level plus per-scenario gameplay
videos, README screenshots and the packaged build:

```
<game>/                          <game>.zip, and <game>_nostore.zip without the store packs
  README.md
  git.log
  workflow.jsonl
  replay.mp4
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

## Status (2026-10-11)

| Item | State |
|---|---|
| Vendor packages analysed (`parkour`, `island_explore`, `robofootball`) | done, [docs/vendor-packages.md](docs/vendor-packages.md) |
| LiaoZhaiRL repo surveyed | done, [docs/liaozhai.md](docs/liaozhai.md) |
| Converter (`tools/build_package.py`) | working; pilot feature 葛巾_旗袍 → 27 commits, 811 steps |
| Pilot package (with the 42 GB project snapshot) | done 2026-10-11 at `~/Downloads/liaozhai_gejin_qipao/`; all 418 end-state files hash-verified |
| Pilot sample | [samples/liaozhai-gejin-qipao/](samples/liaozhai-gejin-qipao/) (final, GUIDs resolved to paths) |
| Unreal track | planned, [docs/plan.md](docs/plan.md) |

## Read first

- [docs/plan.md](docs/plan.md): the plan for both tracks, phases, open decisions.
- [docs/vendor-packages.md](docs/vendor-packages.md): the vendor's format, file by file, and its weaknesses.
- [docs/liaozhai.md](docs/liaozhai.md): the LiaoZhaiRL repository, its features, and the pilot.
- [docs/workflow-format.md](docs/workflow-format.md): our package layout and `liaozhai.unity-workflow/v1` step schema.
- [docs/creation-vs-gameplay.md](docs/creation-vs-gameplay.md): how this differs from Lab gameplay data.
- [docs/autoplay-contract.md](docs/autoplay-contract.md): what each Track B game implements so a bot can play and record it.
- [docs/ue-pipeline.md](docs/ue-pipeline.md): build, package, smoke-test and gameplay recording pipeline (`tools/ue-pipeline/`).
- [docs/game-deliverable.md](docs/game-deliverable.md): the per-game deliverable (`tools/package-game.ps1`): layout, store-content variants, scrub.
- [AGENTS.md](AGENTS.md): rules for agents working here (each with the failure behind it).
- [CLAUDE.md](CLAUDE.md): what every Claude session reads first; points at the skills in `.claude/skills/`
  (commit-always, game-session, coordinator).
- [docs/new-machine.md](docs/new-machine.md): setting up another Windows machine (`machine/bootstrap.ps1`, `machine/check.ps1`).
- [docs/briefs/](docs/briefs/README.md): the prompts that start the coordinator, game and helper sessions (templates + originals).

## Layout

```
tools/build_package.py              converter: one Unity feature → workflow.jsonl + git.log + manifests
tools/ue-pipeline/                  UE build, package and gameplay recording pipeline; AutoPlay drop-in
tools/package-game.ps1, package-dataset.ps1   per-game deliverables and dataset layout v1
machine/                            machine setup: bootstrap/check, ue-heavy limiter, recording hooks, ffmpeg, asset-scout
templates/                          UE 5.3 game skeleton + new-game.ps1
.claude/skills/                     commit-always, game-session, coordinator
samples/liaozhai-gejin-qipao/       pilot output: workflow.jsonl, commits.json, summary.json
docs/                               everything learned so far; docs/briefs/ = session prompts
```

Machine paths in docs are written `%GF_ROOT%` (the Work root: env `GF_ROOT`, else `%USERPROFILE%\.game-factory\config.json`,
else `%USERPROFILE%\Work`); see [machine/README.md](machine/README.md).

Full packages (tens of GB with the project snapshot) do not go in this repository.
The pilot package lives at `~/Downloads/liaozhai_gejin_qipao/` on the owner's Mac.

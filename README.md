# game-factory

Game-**creation** data: how a game gets made, step by step, with the finished project as ground truth.
It is the counterpart to Superposition Lab's game-**play** data (people playing games, recorded with inputs and voice).

Two tracks:

1. **LiaoZhai replication.** Turn the real 4-year history of a shipped Unity game,
   [MapleLeafGitHub/LiaoZhaiRL](https://github.com/MapleLeafGitHub/LiaoZhaiRL) (private), into feature-sized
   creation packages: editor-level steps derived from real commits, the code history, and the project snapshot.
2. **New 3D games in Unreal.** Build new games in Unreal Engine 5 and record the creation as it happens:
   real editor operations with timestamps, screen video, inputs, code commits and a playtest with inputs.

Both tracks start from a format a data vendor sent us (two Unreal packages, `parkour` and `island_explore`):
see [docs/vendor-packages.md](docs/vendor-packages.md) for what they contain and where they fall short.

## Status (2026-10-11)

| Item | State |
|---|---|
| Vendor packages analysed (`parkour`, `island_explore`) | done, [docs/vendor-packages.md](docs/vendor-packages.md) |
| LiaoZhaiRL repo surveyed | done, [docs/liaozhai.md](docs/liaozhai.md) |
| Converter (`tools/build_package.py`) | working; pilot feature 葛巾_旗袍 → 27 commits, 783 steps |
| Pilot sample | [samples/liaozhai-gejin-qipao/](samples/liaozhai-gejin-qipao/) (before GUID→path resolution) |
| Pilot project snapshot (Unity project at the end commit) | downloading on the owner's Mac, ~44 GB of files |
| Unreal track | planned, [docs/plan.md](docs/plan.md) |

## Read first

- [docs/plan.md](docs/plan.md): the plan for both tracks, phases, open decisions.
- [docs/vendor-packages.md](docs/vendor-packages.md): the vendor's format, file by file, and its weaknesses.
- [docs/liaozhai.md](docs/liaozhai.md): the LiaoZhaiRL repository, its features, and the pilot.
- [docs/workflow-format.md](docs/workflow-format.md): our package layout and `liaozhai.unity-workflow/v1` step schema.
- [docs/creation-vs-gameplay.md](docs/creation-vs-gameplay.md): how this differs from Lab gameplay data.
- [AGENTS.md](AGENTS.md): rules for agents working here (each with the failure behind it).

## Layout

```
tools/build_package.py              converter: one Unity feature → workflow.jsonl + git.log + manifests
samples/liaozhai-gejin-qipao/       pilot output: workflow.jsonl, commits.json, summary.json
docs/                               everything learned so far
```

Full packages (tens of GB with the project snapshot) do not go in this repository.
The pilot package lives at `~/Downloads/liaozhai_gejin_qipao/` on the owner's Mac.

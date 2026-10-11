# LiaoZhaiRL — 葛巾_旗袍 (qipao skin for the 葛巾 form)

How one feature of a shipped Unity game was made, step by step, taken from the game's real Git history.
Source: [MapleLeafGitHub/LiaoZhaiRL](https://github.com/MapleLeafGitHub/LiaoZhaiRL) (private), branch `Development`.

## Package contents

- `UnityProject/` — the whole Unity project at the feature's last commit `d8adc87262` (2026-09-21),
  137,756 files, 42 GB. A plain folder (no Git).
- `workflow.jsonl` — 811 editor-level steps, schema `liaozhai.unity-workflow/v1`.
- `git.log` — the 27 real commits, in commit-date order, with diffs of this feature's files.
- `History/commits.json` — the same commits as data (files, blob ids, the steps each commit produced).
- `History/summary.json` — scope rule, start and end commit, counts.
- `UnityProject.manifest.jsonl`, `manifest.json` — path, bytes and SHA-256 of every file.
- `Tools/build_package.py` — the script that produced this package from the repository.

## Open the project

Unity **2022.3.10f1c1** (China build). Open `UnityProject/` from Unity Hub; the first import builds
`Library/` and takes a long time. Windows is recommended: Wwise, Steam and Stove SDK plugins are Windows-only.

## What the steps are

The feature ran from 2026-07-30 to 2026-09-21: 27 commits by 5 people (anonymized `dev_01`–`dev_05`).
Each commit's changes to this feature's files become steps:

| op | count | from |
|---|---:|---|
| `object.set` | 417 | a changed object in a prefab, animation, timeline or asset: property path → before / after |
| `object.add` / `object.remove` | 143 / 32 | an object (GameObject, component) added to or removed from an existing asset |
| `asset.create` | 95 | a new prefab, animation, timeline…: its objects, hierarchy and references |
| `asset.move` | 50 | a file renamed or moved |
| `prefab.override` | 34 | overrides on a prefab instance |
| `asset.import` / `asset.replace` | 23 / 15 | models and textures, with SHA-256 and importer settings |
| `importer.set` | 1 | import settings changed alone |
| `table.edit` | 1 | cells changed in an Excel config table, with column header and row key |

By chapter: 特效 323, 预制体 238, 技能 Timeline 93, 动画 74, 贴图 30, 场景 21, 配置资产 12, 材质 10, 模型 8,
配置表 1, 其他 1.

Every step carries the commit's time, author and message (`reason`, verbatim). `depends_on` names the previous
step on the same asset and the steps that created any asset it references. References name the asset path
when the GUID is in the project (393 resolved; 14 GUIDs point outside the repository, most likely Unity package
scripts). Field reference: `docs/workflow-format.md` in `superpositionhq/game-factory`.

## What is observed and what is derived

- Observed: which files changed in which commit, when, by whom, and the commit message.
- Derived: the split of a file's change into steps (object by object, cell by cell) and the order of steps
  inside one commit. Which editor panel or clicks produced a change was not recorded.
- Nothing is invented: no reasons beyond the commit message, no reconstructed order.

Scope: commits touching `Player_女侠_形态10_葛巾_旗袍/`, plus commits mentioning 葛巾 since 2026-07-30. From each,
only files whose path contains 葛巾 or 形态10, or that lie outside `Combat_战斗相关/Characters_角色/`, are kept;
`git.log` says how many files of a commit belong to other features.

## Checks

- All 418 files whose last change belongs to this feature have the same SHA-256 in `UnityProject/` as in the
  commit.
- No real author name, e-mail or user-profile path appears in `workflow.jsonl`, `git.log` or `History/`.

## Before sharing outside Superposition

The project is fully authorised for this work, including sharing packages.

- 28 of the 51 Excel tables in `UnityProject/Assets/LiaoZhaiRL/墨境导表文件夹/` carry a person's name in their
  document properties (`creator`, `lastModifiedBy`), including `形态皮肤_PlayerSkins.xlsx`. They are left as
  committed so hashes match; clear those fields in a copy before it leaves.

No replay script or videos yet.

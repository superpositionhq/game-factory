# LiaoZhaiRL

Repository: https://github.com/MapleLeafGitHub/LiaoZhaiRL (private, owner `MapleLeafGitHub`, default branch
`Development`). Local blobless clone: `~/Repo/LiaoZhaiRL` (`git clone --filter=blob:none`).

## Facts (surveyed 2026-10-10)

| | |
|---|---|
| Engine | Unity **2022.3.10f1c1** (China build, revision 81bc2caa39c8) |
| Serialization | `m_SerializationMode: 2` (Force Text): prefabs, scenes, materials, animations are YAML, so diffs are readable |
| History | 61,225 commits on `Development` (63,659 reachable), 2022-03-13 → 2026-09-24, ~30 authors; messages in Chinese |
| Size | GitHub reports 68.5 GB for the whole history; the tree at one recent commit is ~44 GB of files |
| Files at HEAD | 137,769: 72k `.meta`, 22.7k `.png`, 10k `.prefab`, 8.5k `.mat`, 6.2k `.anim`, 4.5k `.cs`, 4.1k `.asset`, 1.8k `.controller`, 1.5k `.playable`, 1k `.unity`, 1.1k `.fbx` |
| LFS | none (`.gitattributes`: `* text=auto`) |
| Notable folders | `Assets/LiaoZhaiRL/` (game), `Assets/Plugins`, `Assets/Wwise` + `LiaoZhaiRL_WwiseProject/` (audio), `Assets/stove_sdk_kit_2.6.6`, `steam_appid.txt`, BGDatabase backups, Addressables |
| Config tables | Excel sheets under `Assets/LiaoZhaiRL/墨境导表文件夹/` (e.g. `形态皮肤_PlayerSkins.xlsx`); “导表” commits export them |
| Platforms | PC (Steam, Stove); Windows-only plugins (Wwise, Steam, Stove SDK) may not load in the macOS editor |

The local clone shows every file as staged-deleted with an empty working tree; that is the owner's clone
state and was left alone. Objects are fetched on demand.

## Playable forms (`Combat_战斗相关/Characters_角色/Player_总集/`)

Each form (形态) is a folder; skins are sibling folders with a suffix. Commits touching the folder only:

| Folder | Commits | Files | Period |
|---|---:|---:|---|
| Player_女侠_形态1_剑客 | 1088 | 7722 | 2024-05 → 2026-08 |
| Player_女侠_形态11_如意 | 617 | 52 | 2025-12 → 2026-09 |
| Player_女侠_形态12_奥莉朵 | 599 | 701 | 2026-01 → 2026-09 |
| Player_女侠_形态6_白猿 | 526 | 549 | 2024-05 → 2026-08 |
| Player_女侠_形态7_金和尚 | 433 | 465 | 2024-05 → 2026-08 |
| Player_女侠_形态4_阿宽 | 417 | 419 | 2024-05 → 2026-08 |
| Player_女侠_形态10_葛巾 | 281 | 681 | 2024-11 → 2026-08 |
| Player_女侠_形态3_弈秋 | 176 | 992 | 2024-05 → 2026-08 |
| Player_女侠_形态8_清砚 | 175 | 434 | 2024-05 → 2026-08 |
| Player_女侠_形态9_子楚 | 174 | 521 | 2024-05 → 2026-08 |
| Player_女侠_形态2_刺客 | 154 | 615 | 2024-05 → 2026-08 |
| Player_女侠_形态5_老六 | 114 | 550 | 2024-05 → 2026-08 |
| Player_女侠_形态13_寄幻 | 1 | 46 | 2026-08 |
| Skins: 剑客_重生皮肤 31, 刺客_圣诞形态 27, 清砚_中秋形态 28, 白猿_夏日潜水 21, 弈秋_夏日 23, 金和尚_旗袍 19, **葛巾_旗袍 19**, 老六_夏日 15, 阿宽_新春 12, 子楚_旗袍 10 | | | 2024-12 → 2026-09 |

A feature also touches files outside its folder: Excel tables, Addressables groups
(`Configs/AddressableAssetsData/AssetGroups/Nvxia_form10.asset`), `Editor/ResourceConfig/*.asset`, UI, level
prefabs. 葛巾 as a whole has 402 commits mentioning it (boss fight 葛巾1/2阶段, the playable form, skins, summons
花妖), too broad for one package.

## Pilot: 葛巾_旗袍 (qipao skin for the 葛巾 form)

Scope rule (`tools/build_package.py`):

- commits = touching `Player_女侠_形态10_葛巾_旗袍/` ∪ message contains 葛巾 since 2026-07-30; no merges;
- a file is in scope if its path contains `葛巾` or `形态10`, or it is outside `Combat_战斗相关/Characters_角色/`;
- commits with no file in scope drop out (e.g. `9984469eb2 金和尚旗袍皮肤特效上传`, `1a2d0e9ef2 …形态7…`);
- mixed commits keep only in-scope files and record how many were left out (e.g. `72ca8d7ba8` 白猿，金和尚，青砚，
  子楚，葛巾，奥利朵形态特效分级: 88 of 519 files kept).

Result (test run 2026-10-10, before GUID→path resolution):

- **27 commits → 783 steps**, 2026-07-30 → 2026-09-21, 5 authors (anonymized dev_01–dev_05),
  start commit `2bca8019de` (parent of the first), end commit `d8adc87262`.
- Ops: `object.set` 389, `object.add` 143, `asset.create` 95, `asset.move` 50, `prefab.override` 34,
  `object.remove` 32, `asset.import` 23, `asset.replace` 15, `importer.set` 1, `table.edit` 1.
- Chapters (by asset type): 特效 303, 预制体 230, 技能 Timeline 93, 动画 74, 贴图 30, 场景 21, 配置资产 12, 材质 10, 模型 8.
- Sizes: `workflow.jsonl` 1.35 MB, `git.log` 13 MB (diffs capped at 3,000 lines per file), `commits.json` 238 KB.
- Anonymization check: none of the real names or emails (10 identities) appear in `git.log`, `workflow.jsonl`
  or `commits.json`; no e-mail addresses; no `C:\Users\…`, `/Users/…` or `/home/…` paths.
- Example `table.edit`: `形态皮肤_PlayerSkins.xlsx`, sheet `形态皮肤_SkillGroupsSkins`, row 25, column
  `形态皮肤的模型预制体|Skin_Model`: `MODEL_女侠_形态10_旗袍` → `MODEL_女侠_形态10_旗袍_无鞋` (commit c026
  “新模型基础配置+修改表格”).
- Example `object.set`: `MODEL_爆炸花妖.prefab`, `SortingGroup` on the model: `m_SortingLayerID 0 → 1405785603`,
  `m_SortingLayer 0 → 5`, `m_SortingOrder 0 → -99` (commit “修改模型层级”).
- Converter run time: ~3 minutes (blobs fetched lazily through one `git cat-file --batch`).

Project snapshot: `git worktree add --detach ~/Downloads/liaozhai_gejin_qipao/UnityProject d8adc87262`,
2026-10-10 23:39 → 2026-10-11 ~00:33 EDT (download ~25 GB at ~2–9 MB/s, then writing 137,756 files, 42 GB).
Then `UnityProject/.git` removed and `git worktree prune`d, so it is a plain folder.

Final package (2026-10-11), converter run 3 minutes with the snapshot present:

- 783 steps (same as the test run; 811 after the rebuild below); 72,045 GUIDs indexed from `.meta` files; 393 references resolved to asset
  paths; 14 distinct GUIDs point outside the repository (most likely Unity package scripts in
  `Library/PackageCache`; unverified).
- `depends_on`: 516 steps with one dependency, 229 with none, 36 with 2–8, 2 with 72.
- Verification: all 418 files whose last change belongs to the feature hash identically (SHA-256) in the
  snapshot; 27 more were changed again later by commits outside the feature.
- `UnityProject.manifest.jsonl` (30 MB, 137,756 entries) and `manifest.json` written; package README added.
- 28 of the 51 Excel tables in `墨境导表文件夹/` carry a person's name in `creator` / `lastModifiedBy`
  (including `形态皮肤_PlayerSkins.xlsx`); left as committed, to be cleared in any copy that leaves.

Rebuild (2026-10-11, Windows, after the Unity replay traced mismatches to the converter; `docs/unity-replay.md`):

- Unity-faithful YAML typing (`UnityLoader`): 811 steps instead of 783. The 28 new steps are `object.set` in c022
  (`m_LocalPosition.x/y: -0 → 0`); YAML 1.1 read both sides as the int 0, so these byte changes were invisible.
  `10019_1` (a skin id in `skinNames`, `SkinType`, `HongHuang_10_Material_SkinName`) is no longer the int 100191.
- `list_inserts` on 131 `object.set` steps (`m_Component` 102, `HongHuang_10_Material_Skin` 16, `m_Materials` 7,
  Addressables `m_SerializeEntries` 6).
- Runs on Windows without a wrapper: LF output, forward-slash GUID paths. 12 min with the snapshot.

## Rights

Fully authorised for this work, including sharing packages (confirmed 2026-10-11). Anonymizing commit authors
does not cover the project snapshot's Excel document properties, which may name their authors; scrub those too.

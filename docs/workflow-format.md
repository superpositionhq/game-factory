# Package format (LiaoZhai track)

Modelled on the vendor packages, with every step taken from a real commit.

```
<feature-package>/
  README.md
  workflow.jsonl                 one editor-level step per line, schema liaozhai.unity-workflow/v1
  git.log                        real commits in commit-date order, anonymized, in-scope files only, with diffs
  History/commits.json           machine-readable commit records (files, blob ids, step ids)
  History/summary.json           feature, scope rule, start/end commit, counts
  UnityProject/                  the whole Unity project at the end commit (plain folder, no .git)
  UnityProject.manifest.jsonl    path, bytes, sha256 of every snapshot file
  manifest.json                  path, bytes, sha256 of every other package file
  Tools/build_package.py         the converter that produced it
```

No replay script and no videos yet (see plan, phase A3).

## Step schema `liaozhai.unity-workflow/v1`

```json
{
  "schema": "liaozhai.unity-workflow/v1",
  "id": "W00771", "seq": 771,
  "chapter": "配置表",
  "commit": "c026", "time": "2026-09-21T13:39:32+08:00", "author": "dev_02",
  "op": "table.edit",
  "target": "Assets/LiaoZhaiRL/墨境导表文件夹/形态皮肤_PlayerSkins.xlsx",
  "params": {"cells": [{"sheet": "形态皮肤_SkillGroupsSkins", "row": 25, "col": 19,
                        "column_header": "形态皮肤的模型预制体|Skin_Model", "row_key": 1,
                        "before": "MODEL_女侠_形态10_旗袍", "after": "MODEL_女侠_形态10_旗袍_无鞋"}],
             "cells_changed_total": 1, "sha256": "…", "bytes": 66716},
  "reason": "新模型基础配置+修改表格", "reason_source": "commit_message",
  "depends_on": [], "derivation": "table_cell_diff", "status": "observed_in_commit",
  "source": {"commit_sha": "ed1323eebc…", "diff": "git.log#c026"}
}
```

| Field | Meaning |
|---|---|
| `time`, `author` | the commit's author date and anonymized author (`dev_NN` by first appearance) |
| `chapter` | asset category: 模型, 贴图, 音频, 配置表, 代码, 着色器, 材质, 动画, 技能 Timeline, 场景, 配置资产, 特效 (prefab under `/Effects/` or named `vfx*`), 预制体, 其他 |
| `reason` | the commit message verbatim; nothing model-written |
| `depends_on` | the previous step on the same asset, plus the steps that created or imported any asset this step references (by GUID) |
| `derivation` | how the step was derived (below) |
| `status` | always `observed_in_commit`: the change happened in that commit; the order inside a commit and the UI used are not observed |

Within a commit, steps are ordered: binaries and code first (by path), then YAML assets (by path).

### Ops

| op | derivation | params |
|---|---|---|
| `asset.import` / `asset.replace` | `binary_change` | `kind` (model, texture, audio, font, binary), `bytes`, `sha256`, `before_sha256`, `importer` (the `.meta` importer settings) |
| `asset.create` | `unity_yaml_new_file` | `asset_type`, `objects`, `classes{}`, `game_objects[{path, components[]}]` (≤300), `references[]` (≤200), `sha256`, `bytes` |
| `object.add` / `object.remove` | `unity_yaml_object_diff` | `object{class, class_id, file_id, game_object, script}`, `values` (add) |
| `object.set` | `unity_yaml_object_diff` | `object`, `values{path: after}`, `before{path: before}`; >400 paths → `truncated`, `changed_paths_total` |
| `prefab.override` | `unity_prefab_instance_diff` | `source_prefab`, `overrides_set[]`, `overrides_removed[]`, `other`; >20 element overrides of one array collapse to `{property: ….Array.data[*], changed_elements, sample}` |
| `importer.set` | `unity_meta_diff` | importer settings changed without the asset changing |
| `table.create` / `table.edit` | `table_cell_diff` | `cells[{sheet,row,col,column_header,row_key,before,after}]` (≤400), `cells_changed_total` |
| `code.change` / `file.edit` | `text_diff` | `added_lines`, `deleted_lines`, `sha256`; the diff is in `git.log` |
| `asset.move` / `asset.delete` | `file_renamed` / `file_deleted` | `from` / `before_sha256` |

Property paths flatten nested YAML (`m_LocalPosition.x`). List items are keyed by identity when every item has
one (`m_SerializeEntries[m_GUID=…]`, `m_Component[component=<fileID>]`), else by index, so an insertion does
not shift every later item. References `{fileID, guid, type}` stay whole and gain `path` when the GUID resolves;
`guid_paths` maps GUIDs that appear as plain text. `object.game_object` is the GameObject's hierarchy path
(`Root/Child/…`), built from Transform parents.

## `git.log`

```
LIAOZHAI-FEATURE-LOG 1
Feature: 葛巾_旗袍
…
commit c018 26db2385046ca4834305c77d4019ea4aa43f4635
Author: dev_02
Date:   2026-08-11T…

    修改模型层级

 M    Assets/…/MODEL_爆炸花妖.prefab +3 -3
Replay-Record: {"id": "c018", "sha": "…", "parent": "…", "time": "…", "author": "dev_02", "steps": ["W00…"]}
diff --git a/… b/…
```

Binary files show `Binary <path> sha256=<hash>`. Diffs longer than 3,000 lines are cut with a note naming the blob.

# Vendor packages: `parkour` and `island_explore`

Received 2026-10-10 as two folders (`~/Downloads/parkour`, `~/Downloads/island_explore`). Same vendor, same
README template, same build machine (paths under `D:\hk\`). Both are **game-creation** packages: a finished
Unreal Engine 5.8 game plus a record of how it was built. Neither is gameplay data.

In one sentence (中文): 就是一个做好的游戏，加上“这个游戏是怎么一步步做出来的”记录和视频，不是玩游戏的数据。

## Shared layout

```
README.md          how to open the game and run the replay
UEProject/         finished Unreal 5.8 project (Source, Config, Content, Win64 editor binaries)
ReplayScripts/     replay.py + UE Python adapters, initial assets, code at each stage, verification JSON
workflow.jsonl     ordered editor operations (the "sequence data")
git.log            code history: stage-by-stage diffs with a reason each
replay.mp4         screen recording of the editor replaying workflow.jsonl (4K, 15 fps, no audio)
play.mov|mp4       a short playtest video, no input log
```

Requirements stated by both: Windows 64-bit, Python 3.11+, UE 5.8 build `55116800`, DX12 / SM6 GPU with
hardware ray tracing. `python .\ReplayScripts\replay.py --engine ..\UE_5.8` copies initial assets into a new
project, opens Unreal, executes every workflow step through UE's Python API (plus a C++ bridge module),
reads back each change, saves and quits. `--fast` and `--prepare-only` exist. The replay does not play the
game and does not record video.

## `parkour` (ISLE RUN / AetherIsles island obstacle racer)

- 2.3 GB, 1,440 files. Third-person parkour race on an island: 7 checkpoints, pendulum hazards, HUD,
  settings menu. HUD shows `WASD MOVE / SPACE JUMP / SHIFT SPRINT / R CHECKPOINT`, elapsed time, best time.
- `workflow.jsonl`: 612 rows, schema `isle-run.editor-action/v1`, tracks `prepare` (32) and `editor` (580).
  Ops: `actor.properties` 266, `widget.add` 189, `edge.connect` 38, `node.add` 33, `code.apply` 30,
  `actor.add` 12, `asset.inspect` 8, `blueprint.patch` 7, `component.configure` 6, others 1–3 each.
  Chapters (Chinese): 海岛材质与光照 258, HUD 制作 123, 运动蓝图 73, 设置页制作 70, 源码阶段 30, 检查点和终点 24, …
- Row fields: `schema, id, chapter, track, op, target, params, reason, depends_on, source[{path, sha256}],
  expected{readback}, presentation{before{panel, select}, after{refresh, separate_slate_tick}}`.
  `actor.properties` rows carry `values` and `before`.
- `git.log` (3.8 MB): `ISLE-RUN-REPLAY-LOG 1`, 30 stages `code-001…030`, each with `Replay-Record` JSON
  (`provenance.type: original_git_source_projection`, `source_commit`, `source_repository: D:/hk/run`,
  `intermediate_compilation: not_claimed`) and the full diff.
- `replay.mp4`: 625 s, 3840×2160, 15 fps, no audio, 580 actions. `ReplayScripts/Docs/video-verification.json`
  aligns every action id to video time (max clock error 0.156 s). `VideoChapters.md` lists chapter times.
- `play.mov`: 60.7 s, 2560×1392, 60 fps, stereo AAC; a play-in-editor session (outliner visible).
- Assets include third-party packs `ChallengeGame` and `ST_Characters_JC` (licence unverified).
- Tell-tale of reconstruction: many reasons read “在真实 Details 中应用 untitled104 的保存属性” (apply the saved
  properties of untitled104), i.e. the steps were derived from the final saved state, not observed.
  The replay result lists `not_tested: ['PIE/gameplay', 'physical movement equivalence', 'recording']`.

## `island_explore` (AetherIsles jungle exploration)

- 12 GB, ~17,000 files (includes 2.9 GB `Intermediate` and 816 MB `Saved` that need not ship).
  Third-person exploration with a pet fox (云团), four regions (river valley, highland, waterfall, canopy),
  building (B), backpack (Tab), regions (J), pet (P), save/load. HUD in Chinese. Resource counters read
  10003 / 9999 / 9999 in the playtest (debug values).
- `workflow.jsonl`: 707 rows, schema `aether.semantic-workflow/v1`; tracks `prepared_baseline` 602 and
  `source_import_alternative` 105 (optional branch, not in the default replay).
  ~80 op kinds: `ue.property.set` 90, `ue.designer.add_group` 79, `ue.movement.link` 57,
  `ue.mesh.retain_authored_lods` 50, `ue.mesh.bind_material_slots` 33, `ue.import.static_mesh` 32,
  `ue.postprocess.set` 28, `ue.authoring.import_ui_texture` 27, `ue.authoring.catalog.add_recipe` 24,
  `code.commit` 21, …
- Extra row fields over parkour: `ui{panel, field_or_action, mapping_status}`, `execution`, `status`.
  **Every row** is `status: planned_not_replayed`; 439 rows are `mapping_status: semantic_mapping_not_observed_clicks`;
  695 sources are `prior_project_evidence_not_replay_result` (old build scripts such as `jungle_build.py`).
  `depends_on` is a straight chain (705 of 707 rows depend only on the previous row). No timestamps.
  `presentation.wait_seconds` are staging pauses for the video, not real time.
- `git.log`: 37 entries. Its own header: “游戏阶段 01–21 是按依赖顺序重建的制作记录，并非恢复出的原始 Git 历史；
  中间阶段不保证可编译。” (stages 01–21 were rebuilt in dependency order, are not the original Git history, and
  intermediate stages may not compile). 22–28 and tooling-001–009 are replay adaptations.
- `replay_game.py` docstring: “This controller never sends mouse or keyboard input.” Gameplay is verified by
  automated checks (`map_and_regions, spawn_on_ground, companion_present, travel_region_0..3,
  save_load_position, foundation_place, foundation_remove`).
- `replay.mp4`: 1028 s, 4K, 15 fps. `Verification/Release/selection.json` marks the video
  `deferred_by_user` with a `previous_path`: the video probably comes from an earlier run and was not
  verified against this exact workflow (unverified).
- `play.mp4`: 128.7 s, 2560×1440, 30 fps, stereo AAC, standalone (no editor chrome). No input log.
- The level is the marketplace `PureNature_Jungle` demo map (1.2 GB) with fixes on top, not built in the
  package. Character: Epic Paragon **Shinbi** (959 MB); fox: VanillaFox with Khronos Fox animations (CC BY 4.0,
  attribution required); also Epic Manny/Quinn. `ReplayScripts/Docs/asset_audit.md` (Chinese) documents all
  of this frankly.

## What the format is good for, and its weaknesses

Strengths: a finished, openable project as ground truth; per-step `expected` readback; a script that
rebuilds the project from initial assets; a reason per step; code diffs per stage.

Weaknesses we should not copy:

- The step order is reconstructed after the fact; nothing was observed (they say so).
- No timestamps, no real durations, no human inputs; videos are scripted replays at 15 fps.
- Gameplay is a 1–2 minute clip with no inputs.
- Third-party assets with unclear redistribution rights.
- Windows + UE 5.8 + ray-tracing GPU required to replay.

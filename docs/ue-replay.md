# Unreal creation replay (Track B)

Rebuilds a Track B Unreal game from its first commit by re-running, in order, what its builder actually ran. That
includes the editor-Python scripts that created its maps and placed every actor. The replay then checks the result
against the game's final commit and records an editor video in which the 3D world gets built. It is the counterpart
of the vendor packages' `ReplayScripts/` + `replay.mp4` ([vendor-packages.md](vendor-packages.md)) and of the
LiaoZhai Unity replay ([unity-replay.md](unity-replay.md)).

Tool: `tools/ue-replay/` (host driver `ue_replay.py`, Python 3.12, standard library only; editor-side scripts in
`tools/ue-replay/editor/`; per-game settings in `tools/ue-replay/games/<game>.json`). Pilot: liaozhai-night
`release/1.1.2` = `2cf1aa2`.

Status, results and the run log are at the end ([Pilot results](#pilot-results-liaozhai-night-2cf1aa2)).

## 1. What the vendor replays cover for world building

All three vendor packages were read in full (op counts from `workflow.jsonl`, adapters in `ReplayScripts/`, the
initial-asset manifests and the verification files). **None of them builds a 3D world from an empty level.** Each
starts from a store or demo map that arrives pre-made in `InitialAssets/`, saves it under a new name, places a few
actors and re-tunes what is already there.

| | `island_explore` | `parkour` | `robofootball` |
|---|---|---|---|
| Final map | `AetherJungle` = save-as of the `PureNature_Jungle` demo map `Jungle_Demo` (20.8 MB, in InitialAssets) | `IslandRun` = save-as of `ChallengeGame/Level_Scene_01` (19 MB, in InitialAssets) | new blank `SportsStadium_Day` that streams a copy of the store `Stadium_Day_map` (~70 MB) and `Outside_Day_Map` |
| Actors in the final map | 396 | 657 | not recorded (38,534 seats, 148,928 turf instances pre-made) |
| Actors the replay places | 9 (4 region actors, 4 nav bounds, 1 PlayerStart) + RecastNavMesh from the nav build | 12 (8 course triggers, 4 ocean planes) | 6 (4 cameras, 1 crowd actor fed from a pre-made 22,925-person manifest, 1 QA runner) |
| Actors removed | 0 (177 of 10,269 foliage instances removed near landing spots) | 0 | demo props (ball, sky, night-tagged actors) |
| Level ops | `level.open`, `level.save_as`, `level.save` (1 each) | `world.create` (= open + save as), `world.bind`, `world.save` | open, derive (save as), create blank map, 2 × add streamed level, save |
| Actor edits | 90 `property.set` (30 lighting/atmosphere, 20 on the region actors), 15 class-default restores | 266 `actor.properties` on 251 existing actors: 234 material swaps to 3 pre-made instances, 7 light/sky/fog/PPV | 4 `apply_actor_settings` (sun, sky, fog, PPV), foliage mesh swap on existing instances |
| Meshes / materials | 50 `mesh.retain_authored_lods` (a no-op hash check), 15 material-node edits, 8 MI scalars; imports only on an optional track that the default replay does not run | none as ops (material instances pre-made) | 2 read-only material checks |
| Landscape | none (1 tag) | none (pre-made landscape with paint layers) | none |
| Foliage | remove 177 instances, count check | none | mesh + cull distances on existing instancers |
| Lighting / post-process | 28 `postprocess.set`, 1 reset, 1 `light.set_color`, plus the 30 property sets | 7 rows | 4 rows |
| Navigation | 4 `NavMeshBoundsVolume` spawns + `RebuildNavigation` | none | none |
| How it runs | visible `UnrealEditor.exe … -ExecutePythonScript=ue_replay.py`, one row per Slate post-tick | same, plus a C++ bridge (`ImportText_Direct`) for properties | same (`start_editor.py`), waits for shader/asset compiles before each row |
| What is verified | per-step read-back raising on mismatch; a final export (`reference-state.json`: actors with class/label/tags/transform, lights, PPV, materials, textures, meshes) that is **not diffed** against the reference; no content hashes | 580/580 actions, a fresh-process reload checking widget trees, graph and checkpoint actors, "2,342 properties on 266 objects" (script not shipped) | in-run counts and bindings only; `provenance.json` says validation is pending |
| Video | 4K/15 fps; the camera jumps between 4 cine cameras of the demo map; recorded against an older workflow (`video_matches_current_workflow: false`) | 4K/15 fps, Windows Graphics Capture of the editor, max clock error 0.156 s; camera jumps to each edited actor; recorded against an older workflow hash | 1080p, owned UE windows composited, ready/finished/stop handshake, alignment check; video older than the final workflow |

What arrives pre-made in all three: the terrain, almost every mesh placement, foliage, sky and atmosphere actors,
the materials the steps point at, and (in `robofootball`) the crowd seat data. What the replays add is a thin layer
of tuning and gameplay actors on top. Their step orders are reconstructed after the fact (island_explore's rows are
all `status: planned_not_replayed`; its `git.log` header says the history was rebuilt in dependency order).

## 2. How our Unreal games were actually built

The Track B games were made by agent sessions, almost entirely through committed code:

- **C++** in `Source/` (gameplay, plus editor helper libraries), compiled with UBT.
- **Editor-Python scripts** in `Scripts/`, run headless (`UnrealEditor-Cmd <project> -run=pythonscript -script=…`
  through `tools/ue-heavy.ps1`, usually wrapped by the game's own `Scripts/ue.ps1`). They import art and audio,
  create materials, Niagara systems, Blueprints and data assets, **create the maps and place every actor**. Each
  script logs one `workflow.jsonl` row per operation or per placed group, with its own `params` and reason.
- **Shell steps**: generators that write source PNG/WAV files (engine Python outside the editor), config edits,
  copies of store packs from the asset library, git.

Three records cover this, and the replay uses all three:

| Record | What it gives the replay |
|---|---|
| git history (`games/<game>`) | the exact inputs (code, scripts, config, source art) at every commit, and the committed content to compare against |
| `workflow.jsonl` | what each script run did (rows with `source.script`, time, `status`, params such as piece counts) |
| `.recording/<game>/actions.jsonl` | the agent's tool calls in order: every script run (with the command line and its output), every `Write`/`Edit` of a file, every shell copy |

In liaozhai-night (`2cf1aa2`), for example, the four chapter maps are created from empty levels by
`build_level_L1…L3*.py` and `build_level_MainMenu*.py`. They call `LevelEditorSubsystem.new_level`, then
`EditorActorSubsystem.spawn_actor_from_class` for every wall piece, temple hall, rock, card and lantern. They also
create moonlight, sky light, height fog with volumetric fog, an ink-wash post-process volume, nav bounds, point
lights and Niagara actors, plus gameplay actors (encounters, barriers, shrines, prompts, exits, bot waypoints).
The store packs supply meshes, never maps. So the world is built here, not inherited. That is what makes world
building first-class in this replay.

## 3. Replay design

### 3.1 The replay unit

The unit is the **window**: the work between two consecutive commits on the first-parent chain, closed by the
commit. A window's steps come from the ledger (`ue_replay.py ledger`), in the order they happened:

| Step | Source | What the replay does |
|---|---|---|
| `inputs.apply` | commit tree | writes every tracked file outside `Content/` that the commit adds or changes (code, scripts, config, source art, docs); deletes what it deletes |
| `script.version` | `actions.jsonl` `Write`/`Edit` calls | the exact text of a script at the moment it ran, rebuilt by re-applying the agent's writes and edits from the previous commit's blob (falls back to the commit's version when a shell command also touched the file, logged) |
| `assets.drop` | game settings + `actions.jsonl` | copies an initial asset (a store pack from the asset library) into `Content/` at the point where the builder copied it |
| `build.editor` | `Source/` changed | UBT editor build of the replay project (lazily, before the next editor run) |
| `editor.script` | `actions.jsonl` command lines | re-runs the editor script headless, with the same command shape (`-run=pythonscript -script=<path> [args]`, same environment variables), in the replay project |
| `shell.replay` | game settings (allow list) | shell commands that changed `Content/` outside the editor (for example moving a pack's loose `.fbx` files) |
| `boundary` | commit | checks the window (below), then makes the replay project's inputs equal to the commit |

Read-only runs (probes, analyses, checks: settings `readonly_patterns`) are listed but skipped. Game launches,
packaging and AutoPlay tests do not change the project and are not replayed. The replay never commits.

**Content is never copied from a commit when the replay produced it.** At a boundary, a `.uasset`/`.umap` that the
commit added or changed but no replayed step wrote is copied from the commit (`fallback`, with the reason). An
example is a file that a shell command produced. A file the replay wrote keeps the replay's version, so errors
accumulate visibly instead of being reset. Files the commit deletes are deleted.

### 3.2 Preparing the isolated project

`ue_replay.py prepare` creates `%GF_ROOT%\ue-replay\<game>\` with:

- `project/`: `git clone --shared --no-checkout` of the game repo, Git LFS reading the game's own object store
  (`lfs.storage`; nothing downloaded), checked out at the **first commit** (for liaozhai-night: the UE 5.3 Third
  Person C++ template). The game repo itself is only read.
- `work/`: ledger, plan, blobs (reconstructed script texts), logs, dumps, results.
- `truth/`: the same clone at the final commit, built, used to dump the reference state.

`initial-assets.manifest.json` lists what the replay gets from outside the game's history, with sha256 per file:
the store packs (from `asset-library\fab-ue\<pack>\Content\<Folder>`) and external source trees the scripts read
(for liaozhai-night the read-only LiaoZhaiRL snapshot `liaozhai-replay\end`, only the files the import scripts
name). The engine is `UE_5.3` as installed; the C++ toolchain is the one the game compiled with.

### 3.3 Running

`ue_replay.py run` executes the plan, resumable (`work/state.json`). Every engine process goes through
`tools/ue-heavy.ps1`; headless runs take a general slot, never the GPU slot. Each editor run's new `workflow.jsonl`
rows are cut out and saved (`work/rows/<run>.jsonl`), and the project's `workflow.jsonl` is then restored, so the
file stays an input.

### 3.4 What is checked

Per window (`work/windows.jsonl`):

1. **Reconstruction**: every script whose text was rebuilt from `Write`/`Edit` calls matches the commit's blob at
   the boundary (sha256).
2. **Behaviour**: each replayed script run emits the same workflow rows as the original run (same `op`, `target`,
   `status`, and the same `params` once times, ids and absolute paths are masked). This catches a run that failed
   differently or placed a different number of pieces.
3. **Content set**: the `.uasset`/`.umap` paths under `Content/` equal the commit's (missing, extra, fallback).

At the end (`ue_replay.py verify`, against the final commit):

1. **Files**: every tracked file outside `Content/` is byte-identical to the final commit (sha256).
2. **Content**: the same set of packages; per package, byte-identical or not. Unreal writes a random
   `PersistentGuid` into every new package, and random GUIDs into actors and material expressions, so a re-created
   asset is not expected to be byte-identical, but an untouched or only moved one is.
3. **Structure**: `editor/ue_dump.py` runs headless on the replayed project and on `truth/`, and the dumps are diffed.
   - Each map: every actor's class, label, outliner folder, transform (tolerance 0.01 cm / 0.01°), static mesh,
     materials, mobility, collision profile, light, sky, fog and post-process settings, Niagara asset, and the
     editor properties of the game's own actor classes.
   - Each asset: class, plus a per-class digest (mesh vertex and triangle counts, bounds and material slots;
     texture size, format and source hash; material expressions and parameters; material instance parent and
     values; sound duration and channels; animation length, frames and skeleton; Blueprint parent and
     components; data-asset and data-table contents as exported text).
4. **Cooked content** (optional, `verify --cook`): both projects cooked for Windows with the same command; the
   cooked file sets are compared and cooked files hashed. Cooking drops editor-only data such as `PersistentGuid`,
   so cooked bytes say more than editor bytes.

### 3.5 World-building ops and the video

The headless replay is the reference. A headless script places hundreds of actors inside one call, so nothing
appears on screen piece by piece. For the video, every map is therefore also replayed as **world ops**:

- After every replayed run that changed a map, `ue_dump.py` exports the map: a JSON dump, and every actor as T3D
  (the editor's own copy/paste text, every non-default property included).
- `ue_replay.py derive` turns consecutive exports into ops, one per actor, each tied to the script run (and its
  workflow rows) that produced it:
  - `ue.level.create`, `ue.actor.spawn` (the actor's T3D), `ue.actor.update`, `ue.actor.remove`, `ue.level.save`.
  - The ops are written in the vendor field set (`id`, `chapter`, `op`, `target`, `params`, `reason`,
    `depends_on`, `source`, `expected`, `presentation`) with `status: derived_from_replayed_script_run`.
- `editor/ue_world_replay.py` runs in a visible editor and plays the ops one Slate tick at a time:
  - a map is created empty;
  - its actors are pasted in the order the script spawned them, group by group (the script's logged groups and
    outliner folders), with the viewport camera framing each group;
  - the map is saved, then dumped and compared with the headless result (`expected`).
- The capture uses the Unity replay's method: Windows Graphics Capture of the editor window only, a
  ready/go/done/stopped handshake, fragmented MP4. A caption track (commit, script, the builder's own row reason)
  is burned in from the aligned step log.
- `video-verification.json` aligns every op id with video time.
- Code, import and material steps appear in the caption track. They take no screen time, because the headless
  replay already ran them.

The video is a GPU job. It runs through `ue-heavy.ps1` in a slot the coordinator schedules.

### 3.6 Deliverable layout

`ue_replay.py package --game games/<game>.json` assembles it in
`%GF_ROOT%\deliverables\_replay\<game>\<final sha8>\` (unscrubbed; `tools/package-dataset.ps1 -ReplayScripts
<dir>\ReplayScripts -ReplayVideo <dir>\replay.mp4` copies it into the dataset and scrubs the copy):

```
ReplayScripts/
  README.md                       how to replay, what is observed vs derived, results
  ue_replay.py, runner.py, ledger.py, derive.py, verify.py, record.py, shellfx.py, package.py
                                  the tooling as it ran (it works outside the game-factory checkout: GF_ROOT or ~/Work)
  editor/ue_dump.py, ue_world_replay.py
  game.json                       the game's replay settings ({root} placeholders, no machine paths)
  ledger.json                     windows, script runs, versions (from history + actions)
  workflow.replay.jsonl           the derived world ops (vendor field set) that drive replay.mp4
  initial-assets.manifest.json    store packs and external sources, sha256 per file
  Blobs/                          reconstructed script texts by sha256
  Verification/
    report.md, report.json        files, content, structure, (cook) results
    windows.jsonl                 per-window checks
    dump-replay/, dump-truth/     structure dumps
    video-verification.json
replay.mp4
verification.json                 summary for the packager: parts present, windows, verify report, video verification
READY                             written last, only when every part is present; the packager waits for it
```

`--force` assembles an incomplete copy without `READY` (for checks only).

## Packager integration

See the end of this file (filled in with the pilot).

## Pilot results (liaozhai-night `2cf1aa2`)

Filled in as the pilot runs.

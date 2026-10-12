# Unreal creation replay

Rebuilds one of our Unreal games from its first commit by re-running, in order, what its builder actually ran. That
includes the editor-Python scripts that created its maps and placed every actor. The replay then checks the result
against the game's final commit. It produces the dataset's `ReplayScripts/` ([game-deliverable.md](game-deliverable.md));
the dataset has no replay video (layout v1.1).

Tool: `tools/ue-replay/` (host driver `ue_replay.py`, Python 3.12, standard library only; editor-side scripts in
`tools/ue-replay/editor/`). Per-game settings live in the game's own repo as `<root>/games/<slug>/ReplayConfig.json`;
`ue_replay.py --game <game>` loads them, and `--game <path>` takes a settings file instead (for example a delivered
`ReplayScripts/game.json`). Per-game results belong in the game's own docs, not here.

## 1. How our Unreal games were actually built

Our games were made by agent sessions, almost entirely through committed code:

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

## 2. Replay design

### 2.1 The replay unit

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

### 2.2 Preparing the isolated project

`ue_replay.py prepare` creates `%GF_ROOT%\ue-replay\<game>\` with:

- `project/`: `git clone --shared --no-checkout` of the game repo, Git LFS reading the game's own object store
  (`lfs.storage`; nothing downloaded), checked out at the **first commit** (for liaozhai-night: the UE 5.3 Third
  Person C++ template). The game repo itself is only read.
- `work/`: ledger, plan, blobs (reconstructed script texts), logs, dumps, results.
- `truth/`: the same clone at the final commit, built, used to dump the reference state.

`initial-assets.manifest.json` lists what the replay gets from outside the game's history, with sha256 per file:
the store packs (from `asset-library\fab-ue\<pack>\Content\<Folder>`) and external source trees the scripts read
(read-only, listed in the game's settings; only the files the import scripts name). The engine is `UE_5.3` as
installed; the C++ toolchain is the one the game compiled with.

### 2.3 Running

`ue_replay.py run` executes the plan, resumable (`work/state.json`). Every engine process goes through
`tools/ue-heavy.ps1`; headless runs take a general slot, never the GPU slot. Each editor run's new `workflow.jsonl`
rows are cut out and saved (`work/rows/<run>.jsonl`), and the project's `workflow.jsonl` is then restored, so the
file stays an input.

### 2.4 What is checked

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
4. **Verdict** (`report.json` `verdict`, top of `report.md`): PASS only when (a) every tracked file outside `Content/`
   is byte-identical, none missing, and no extra files except git-ignored ones; (b) every asset has the same class and
   structure digest; (c) every game map (`map_roots`) has the same actors with the same transform, components,
   properties and world settings. Known non-content differences are normalised first and counted in
   `verdict.exclusions`: random GUIDs (`ExpressionGUID=`/`Guid=`), memory addresses in printed values (delegates),
   the AnimSequence compressed-size tag (derived data), Content/ bytes (random `PersistentGuid`), maps outside
   `map_roots` (store-pack demo levels). Workflow-row comparison is informational. `package` writes `READY` only on
   PASS, and a dataset is COMPLETE only with it.
5. **Cooked content** (optional, `verify --cook`): both projects cooked for Windows with the same command; the
   cooked file sets are compared and cooked files hashed. Cooking drops editor-only data such as `PersistentGuid`,
   so cooked bytes say more than editor bytes.

### 2.5 World-building ops (and an optional video, not in the dataset)

The headless replay is the reference. A headless script places hundreds of actors inside one call; to show world
building per actor, every map is also described as **world ops** (included in `ReplayScripts/` when derived):

- After every replayed run that changed a map, `ue_dump.py` exports the map: a JSON dump, and every actor as T3D
  (the editor's own copy/paste text, every non-default property included).
- `ue_replay.py derive` turns consecutive exports into ops, one per actor, each tied to the script run (and its
  workflow rows) that produced it:
  - `ue.level.create`, `ue.actor.spawn` (the actor's T3D), `ue.actor.update`, `ue.actor.remove`, `ue.level.save`.
  - The ops are written in the workflow field set (`id`, `chapter`, `op`, `target`, `params`, `reason`,
    `depends_on`, `source`, `expected`, `presentation`) with `status: derived_from_replayed_script_run`.
- Optional, not part of the dataset (layout v1.1 has no video): `ue_replay.py record` plays the ops in a visible
  editor and records it (`editor/ue_world_replay.py`, one op per Slate tick, GPU slot with recording priority):
  - a map is created empty;
  - its actors are pasted in the order the script spawned them, group by group (the script's logged groups and
    outliner folders), with the viewport camera framing each group;
  - the map is saved, then dumped and compared with the headless result (`expected`).
- The capture: Windows Graphics Capture of the editor window only, a
  ready/go/done/stopped handshake, fragmented MP4. A caption track (commit, script, the builder's own row reason)
  is burned in from the aligned step log.
- `video-verification.json` aligns every op id with video time.
- Code, import and material steps appear in the caption track. They take no screen time, because the headless
  replay already ran them.

The optional video is a GPU job with recording priority; it is not run for datasets.

### 2.6 Deliverable layout

`ue_replay.py package --game <game>` assembles it in
`%GF_ROOT%\deliverables\_replay\<game>\<final sha8>\` (unscrubbed; `tools/package-dataset.ps1 -ReplayScripts
<dir>\ReplayScripts` copies it into the dataset and scrubs the copy):

```
ReplayScripts/
  README.md                       how to replay, what is observed vs derived, results
  ue_replay.py, runner.py, ledger.py, derive.py, verify.py, shellfx.py, package.py
                                  the tooling as it ran (it works outside the game-factory checkout: GF_ROOT or ~/Work)
  editor/ue_dump.py
  game.json                       the game's replay settings ({root} placeholders, no machine paths)
  ledger.json                     windows, script runs, versions (from history + actions)
  workflow.replay.jsonl           the derived world ops (workflow field set), when derived
  initial-assets.manifest.json    store packs and external sources, sha256 per file
  Blobs/                          reconstructed script texts by sha256
  Verification/
    report.md, report.json        files, content, structure, (cook) results
    windows.jsonl                 per-window checks
    dump-replay/, dump-truth/     structure dumps
verification.json                 summary for the packager: parts present, windows, verify report
READY                             written last, only when every window was replayed and verified; the packager waits for it
```

`--force` assembles an incomplete copy without `READY` (for checks only).

## Packager integration

The packager waits for `READY`, then passes the folder of section 2.6 to `tools/package-dataset.ps1 -ReplayScripts
<dir>\ReplayScripts`. Without it, the dataset zips stay `<game>.pending.zip`.

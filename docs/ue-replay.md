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
| `shell.replay` | game settings (allow list) | shell commands that changed `Content/` outside the editor, matched to the recorded command (`match`) and replayed as `argv`: `delete <paths>`, `move-merge <src> <dst>`, `host-python <script> <args>` (engine Python, outside the editor), `keep-committed <dirs>` (a prune the replay cannot recompute, e.g. one driven by Shipping cook output: deletes the files under the dirs that the commit `ref` does not have) |
| `boundary` | commit | checks the window (below), then makes the replay project's inputs equal to the commit |

Read-only runs (probes, analyses, checks: settings `readonly_patterns`) are listed but skipped, except a script in
`not_readonly` (every run of it) or a single run in `not_readonly_runs` (`{tool_use_id, script, reason}`) whose output a
later run reads: horror's probe_clip_speeds.py writes Saved/clip_speeds.json; stealth's first inspect_pack_meshes.py
creates Saved/PackMeshes, where prune_packs.py writes (its slow later runs stay skipped). A run the recorded actions
miss is rebuilt from the workflow row its wrapper wrote when it ended (`runs_from_rows`: `[{"row": "<id>"}]`; script,
time, duration and mode from the row; listed as a deviation). The usual cause is a tool call interrupted while its
editor kept running: an interrupted call records no PostToolUse event (rts-command: three runs at 03:55-04:12). Rows a
wrapper writes around each run go in `wrapper_row_ops`, so they are not counted as the script's own. Game launches,
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
- `truth/`: the same clone at the final commit, built, used to dump the reference state (`ue_replay.py truth`).

`initial-assets.manifest.json` lists what the replay gets from outside the game's history, with sha256 per file:
the store packs (from `asset-library\fab-ue\<pack>\Content\<Folder>`) and external source trees the scripts read
(read-only, listed in the game's settings; only the files the import scripts name). The engine is the one the game's
`.uproject` names (`UE_5.3` for the first games), as installed; the C++ toolchain is the one the game compiled with.

An external source the builder unpacked into a scratch folder that no longer exists takes a `rebuild` recipe in
`external_sources`: `{"unzip": [{"zip": "{root}/asset-library/...*.zip", "to": "<subdir>", "exclude": ["*Cavity*"]}]}`,
the builder's own unpack command in data. `prepare` rebuilds it under `work/external/<id>/` (listed with sha256 in the
manifest), and a run whose recorded env names the old folder gets the rebuilt one. Without it the import script finds
nothing and the replay silently diverges (horror: three scanned surfaces, 11 material instances).

Settings never hold a machine's user name or tool folders. What the recording says (commands in `match`, the old
location of an external source in `recorded`) is written as a template and matched on any machine: `{home}` = any user
profile, `{root}` = any path prefix, `*` = one path component (in `recorded`), `/` = any slash. `path` is where the
source is on this machine (`{root}`, `{home}` expanded); copies of files that lived outside the project on the build
machine go under `{root}/ue-replay/_sources/<game>/`. `"remap_scripts": true` points absolute paths inside the
builder's scripts at that copy for each run and puts the scripts back afterwards (listed under the report's deviations).

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
   `verdict.exclusions`: random GUIDs (`ExpressionGUID=`/`Guid=`), random localization keys, memory addresses in
   printed values (delegates), absolute paths into the folder the editor ran in (`project_path`: import sources such
   as FontFace `source_filename` name the game repo in truth and the replay project in the replay, under any
   user-profile name), the AnimSequence compressed-size tag (derived data), Content/ bytes (random `PersistentGuid`),
   maps outside `map_roots` (store-pack demo levels), folders in `dump_exclusions` (assets that crash the editor on
   load, in the final commit too). Workflow-row comparison is informational. `package` writes `READY` only on
   PASS, and a dataset is COMPLETE only with it.
5. **Cooked content** (optional, `verify --cook`): both projects cooked for Windows with the same command; the
   cooked file sets are compared and cooked files hashed. Cooking drops editor-only data such as `PersistentGuid`,
   so cooked bytes say more than editor bytes.

### 2.5 World-building ops (and an optional video, not in the dataset)

The headless replay is the reference. A headless script places hundreds of actors inside one call; to show world
building per actor, every map can also be described as **world ops** (optional, for the editor video only; not in `ReplayScripts/`):

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
`<out>\_replay\<game>\<final sha8>\` (`<out>`: env `GF_OUT`, config `out`, else `%GF_ROOT%\deliverables`) (unscrubbed; `tools/package-dataset.ps1 -ReplayScripts
<dir>\ReplayScripts` copies it into the dataset and scrubs the copy):

```
ReplayScripts/
  README.md                       how to replay, what is observed vs derived, results
  ue_replay.py, runner.py, ledger.py, derive.py, verify.py, shellfx.py, package.py, live.py
                                  the tooling as it ran (it works outside the game-factory checkout: GF_ROOT or ~/Work)
  editor/ue_dump.py
  game.json                       the game's replay settings ({root} placeholders, no machine paths)
  ledger.json                     windows, script runs, versions (from history + actions)
  initial-assets.manifest.json    store packs and external sources, sha256 per file
  Blobs/                          reconstructed script texts by sha256
  Verification/
    report.md, report.json        files, content, structure, (cook) results
    windows.jsonl                 per-window checks
    dump-replay/, dump-truth/     JSON structure dumps (no T3D)
verification.json                 summary for the packager: parts present, windows, verify report
READY                             written last, only when every window was replayed and verified; the packager waits for it
```

`--force` assembles an incomplete copy without `READY` (for checks only).

Disk: `prepare`, `run` and `dump` refuse to start when the work drive has less than `GF_MIN_FREE_GB` (default 50 GB)
free, `package` likewise for `<out>` (a disk that filled mid-run once corrupted a replay). Once `READY` exists,
`ue_replay.py clean --game <game>` lists the replay project, truth project and bulky work files (dumps, blobs, rows,
logs; ~20 GB a game) and removes them with `--yes`; the ledger, state and report stay.

### 2.7 Code as it stood when each script ran

The window's inputs are the commit's, but a run that happened before a mid-window code change ran with the earlier
C++ (stealth L02: built with the window's later code, the level got duplicate actors). The ledger records, per run,
every code file (`Source/`, `Plugins/` C++ and C#, `.uproject`, `.uplugin`) whose text at the run's start differs
from the commit (`code`). The runner writes those texts and rebuilds the editor before the run, and puts the commit's
code back at the boundary. If the earlier code does not compile here, the run gets the commit's code (listed). A run
whose code text the recording cannot rebuild (a shell edit the ledger does not follow) also gets the commit's code
(`code_unknown`). Deviations: `code_at_run_time`, `code_at_run_time_not_buildable`, `code_at_run_time_unknown`.
Settings `"code_at_run_time": false` turns it off.

## 3. Live replay (per commit, during development)

A game whose `ReplayConfig.json` has `"live": true` (the template's default) is replayed while it is being built, so
its `ReplayScripts/` is verified commit by commit and release only adds the last windows.

**Trigger.** The game repo's post-commit hook (`machine/install-git-hook.ps1`, installed by `templates/new-game.ps1`)
runs `tools/ue-replay/live-hook.ps1`. It returns at once: it prints the last job's findings once, then starts
`ue_replay.py live --game <settings>` detached at below-normal priority unless a job for the game runs (one per game,
`work/live/lock`; the running job picks up new commits before it exits).

**The job** (`live.py`):

1. Builds the ledger up to `HEAD` and compares it window by window with the ledger already replayed (commit, runs,
   script and code texts, drops, shell steps). If history was rewritten (an amend, a rebase) or the settings changed
   what a replayed window does, the replay project goes back to the last unchanged commit's tree and replays from
   there (`work/live/events.jsonl`, `replay_restarted_from_commit`).
2. Replays the new windows into the persistent replay project (section 2.3). Every engine process goes through
   `ue-heavy.ps1 -Low`: one low-priority job machine-wide, which takes a general slot only while no other job waits
   for one and another slot stays free, below-normal process priority. `work/STOP` pauses it as usual.
3. Checks the new windows: each run against its original (exit code, workflow rows), each window's Content against
   its commit (fallbacks, extras), and the assets and maps the new commits touched against the truth project at
   `HEAD` (`truth/`, built when code changed; `ue_dump.py --packages` dumps only the touched packages).
4. Reads the recording for work the replay cannot redo: an editor started without a run the ledger recognises (a
   wrapper missing from `run_patterns`, a script given by an absolute or variable path), custom commandlets
   (`-run=<Name>`), scripts outside the repo, script texts naming the live project folder or an `os.chdir`, runs
   that logged no workflow row, script texts the recording cannot rebuild.
5. Writes `work/live/reports/<sha8>.md/.json`, `work/live/status.json` and, when something needs the builder,
   `work/live/feedback.md`; the hook prints it at the session's next commit.

`ue_replay.py live-status` lists every live game (HEAD, replayed window, last result, findings, job running).

**Rules for game sessions** (game-session skill, "Replay-friendly work"): every editor script committed and run by its
project-relative path through `Scripts/ue.ps1 script -Script Scripts/<name>.py` or a wrapper in `run_patterns`;
relative paths only, never an absolute path to or `os.chdir` into `games\<slug>`; probes named by `readonly_patterns`
(`not_readonly` for one that writes something later work reads); one workflow row per run at least; scripts edited
with Write/Edit or written as `name_v2.py`; no custom commandlets; `ReplayConfig.json` from day one, with an
`asset_drops` entry for every store pack copied in; no amend or rebase.

**Release** (`ue_replay.py release --game <slug>`, normal priority): catches the replay up to the settings' `final`
(`HEAD` by default), checks out and builds `truth/` there, dumps both projects in full, runs `verify` and `package`.
With the live replay current, that is the last windows plus a full final verify: minutes. Then
`tools/package-dataset.ps1` as before. `ue_replay.py truth --game <slug>` alone prepares the truth project.

The games built before the live replay existed (liaozhai-night, siege-catapult, tower-defense, rally-racer,
horror-escape, island-survival, stealth) keep the end-of-game replay of sections 2.2-2.6.

## Packager integration

The packager waits for `READY`, then passes the folder of section 2.6 to `tools/package-dataset.ps1 -ReplayScripts
<dir>\ReplayScripts`. Without it, the dataset zip stays `Dataset.pending.zip`.

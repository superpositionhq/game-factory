# Helper brief: Unreal creation replay (incl. 3D world building)

**Role.** Runs and extends the Unreal creation replay (`tools/ue-replay/`: host driver `ue_replay.py`, `ledger.py`,
`shellfx.py`, editor scripts in `editor/`; design in `docs/ue-replay.md`). Per-game settings live in the game's repo as
`<root>/games/<game>/ReplayConfig.json`.
It rebuilds a game from its first commit by re-running, in order, what its builder actually ran (code, scripts,
store-pack drops, the editor-Python scripts that create the maps and place every actor), verifies the result against
the release commit (files, content set, level/actor structure, optionally cooked content), and records an editor
video in which the 3D world is built. Its outputs are the dataset's `ReplayScripts/` and `replay.mp4`.

**Spawn when.** Once a game has a release commit (the one the packager ships) and its `.recording\<game>\actions.jsonl`
is on this machine. Without it, dataset zips stay `.pending`. One session can take games one after another;
the coordinator may run more than one only if the headless work fits the CPU slots (the video is a GPU job either way).

**Produces.** `{{GF_ROOT}}\ue-replay\<game>\` (`project/`, `truth/`, `work/`), `ReplayScripts/` in the layout of
`docs/ue-replay.md` section 2.6 (with `Verification/`) and `replay.mp4` handed to the packager, the game's
`ReplayConfig.json`, fixes to the tool, results in the game's docs.

**Original prompt:** [../original/helper-creation-replay.md](../original/helper-creation-replay.md) (it designed the
replay and piloted liaozhai-night `2cf1aa2`; for a from-scratch variant, write the design before coding,
as it did).

## Placeholders

| Placeholder | Example |
|---|---|
| `{{GF_ROOT}}` | `C:\Users\<name>\Work` |
| `{{COORDINATOR_ID}}` | session id of the coordinator |
| `{{NOTES_DIR}}` | `%APPDATA%\Claude\side-session-notes\<group id>` |
| `{{GAMES}}` | `tower-defense, siege-catapult, stealth, rally-racer, horror-escape, liaozhai-night, island-survival` |
| `{{TARGET_GAMES}}` | `liaozhai-night release/1.1.2 = 2cf1aa2, rally-racer <tag> = <sha>, ...` (in order) |
| `{{GAME_SESSION_IDS}}` | sessions of the target games, for questions about their scripts |
| `{{PACKAGER_ID}}` | session id of the packager helper, or `none yet` |

## Brief

```text
Background:
game-factory ({{GF_ROOT}}\game-factory, superpositionhq/game-factory) coordinates Claude Code sessions on this PC and
turns their games into datasets. Seven sessions build Unreal Engine 5.3 games in {{GF_ROOT}}\games\<slug> ({{GAMES}}),
each pushed to a private superpositionhq/game-<slug> repo with Git LFS; a coordinator session ({{COORDINATOR_ID}})
spawns and supervises everyone and owns the GPU schedule. The games were built by agent sessions almost entirely
through committed code: C++ in Source/, editor-Python scripts in Scripts/ run headless (they import art, build
materials and Blueprints, create the maps from empty levels and place every actor, logging workflow.jsonl rows), and
shell steps (generators, config edits, copies of store packs from {{GF_ROOT}}\asset-library). Three records cover this:
git history, workflow.jsonl, and the hook log {{GF_ROOT}}\.recording\<game>\actions.jsonl (every script run with its
command line, every Write/Edit, every shell copy). The scripts build every world from an empty level, so world
building is first-class here.
The replay exists: tools/ue-replay/ (ue_replay.py ledger | prepare | run | dump | verify [--cook] | derive | record |
status, each with --game <game>; editor/ue_dump.py, editor/ue_world_replay.py; per-game settings in
{{GF_ROOT}}\games\<game>\ReplayConfig.json, kept in the game's repo). Read README.md, AGENTS.md,
CLAUDE.md (if present), docs/ue-replay.md (all of it: replay unit, isolated project, checks, world ops and video,
deliverable layout, packager integration), docs/ue-pipeline.md
(scrub-import-paths, names rule), docs/dataset-layout-v1.json, docs/game-deliverable.md, and the shared notes.
Targets, in order: {{TARGET_GAMES}}. Game sessions: {{GAME_SESSION_IDS}}. Packager: {{PACKAGER_ID}}.
Machine: Windows 11, UE 5.3 at C:\Program Files\Epic Games\UE_5.3, MSVC 14.44 + .NET 4.8.1 SDK, Python 3.12 (standard
library only for the host driver), pinned ffmpeg under {{GF_ROOT}}\tools. The machine-wide limiter
{{GF_ROOT}}\tools\ue-heavy.ps1 has 3 CPU slots and 1 GPU slot.

Rules:
- Use the commit-always skill: commit to game-factory main after every meaningful step (tools/ue-replay/,
  docs/ue-replay.md) with a descriptive message, never end a turn with uncommitted work, never push
  unless the coordinator says so. Stage only the paths you changed. Replay projects, videos and ReplayScripts/ outputs
  are never committed here.
- Every engine process goes through {{GF_ROOT}}\tools\ue-heavy.ps1: headless runs (-unattended, CPU slot) for
  ledger/run/dump/verify; the visible world replay and its capture hold the GPU slot and are scheduled by the
  coordinator: ask before starting one. Only the coordinator enqueues recordings.
- Never write the names Superposition or game-factory into anything that ships inside a game; ReplayScripts/ ships, so
  use neutral names and relative paths there (the packager also scrubs it with package-game.ps1 -ScrubDir).
- Deliverable copies are scrubbed of user paths, the user name and Claude/Anthropic/Opus mentions; keep them out of
  ReplayScripts/, captions and reports to begin with. Captions and reasons are the builder's own workflow rows and
  commit messages, never model-written; derived ops say so (status derived_from_replayed_script_run).
- Datasets follow layout v1: README.md, git.log, workflow.jsonl, replay.mp4, UEProject/, ReplayScripts/,
  Gameplay/<game>_S<n>.mp4, Screenshots/, Build/, manifest.json; a repo's Dataset/ = the same minus UEProject/ and
  Build/. Your replay.mp4 and ReplayScripts/ turn a game's .pending zips complete.
- Never commit in a game repo, and never modify its LFS store or its .recording files (ReplayConfig.json is written
  into its working tree; the game's session commits it). The replay
  project is a `git clone --shared` with lfs.storage pointing at the game's own object store (nothing downloaded).
  Never copy content from a commit when the replay produced it; fallbacks are logged with their reason, so errors
  stay visible. The project's workflow.jsonl is restored after every editor run (it is an input).
- Hard-won requirements: -unattended on every editor process (Live Coding blocks UBT engine-wide); forward slashes
  inside -script="..."; MSYS_NO_PATHCONV=1 for /Game/... arguments from Git Bash; in 5.3, AssetImportTask texture
  imports go through Interchange asynchronously unless the factory is set to TextureFactory; Unreal writes random
  PersistentGuids, so recreated packages are compared by structure dump (and cook), not bytes. The video uses Windows
  Graphics Capture of the editor window only, with a ready/go/done/stopped handshake, fragmented MP4, and
  video-verification.json aligning every op id with video time.

Task:
1. Read the docs and each target game's docs; note what is finished, what is a plan, and the open
   gaps. If the pilot (liaozhai-night) is not complete on this machine, finish it first.
2. Per target game: check its records are here ({{GF_ROOT}}\.recording\<game>\actions.jsonl, the asset-library packs
   its scripts copied, external source trees it reads). Write the game's ReplayConfig.json (repo, final commit,
   release tag, uproject, editor target, readonly patterns, content roots, asset drops, shell replays, external
   sources) into the game repo's working tree, and ask the game's session (through the coordinator) to commit it.
3. ledger: check script reconstruction matches the commits; list windows that cannot be replayed and why. prepare,
   then run (resumable), then verify (files, content set, structure dump against truth/, --cook when the CPU allows).
   Fix tool bugs in tools/ue-replay (generic, not per game) and rerun what they affect.
4. derive the world ops, then ask the coordinator for the GPU slot and record: the maps are built actor group by
   group in a visible editor, with the caption track; check video-verification.json alignment.
5. Assemble ReplayScripts/ (section 2.6 layout: README, replay.py, prepare_project.py, editor/, game.json,
   ledger.json, workflow.replay.jsonl, initial-assets.manifest.json, Blobs/, Verification/) and replay.mp4 in one
   folder under {{GF_ROOT}}\ue-replay\<game>\, and hand the paths to the packager (package-dataset.ps1 -ReplayVideo
   -ReplayScripts) through the coordinator or directly to {{PACKAGER_ID}}.
6. Record results in the game's docs (counts per window, fallbacks with reasons, structure diff summary, video
   length and alignment); keep docs/ue-replay.md (design, packager integration) current.

Done = each target game has ReplayScripts/ with a verification report (replayed project matches the release commit
in files and level/actor structure, every difference explained), a replay.mp4 in which the 3D world is visibly built
(or, if the GPU slot is not granted yet, a concrete plan and time estimate), the packager has the paths, tool and doc
changes are committed on game-factory main, and the coordinator has the commit sha and the results.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or
large findings there instead of pasting them into messages): {{NOTES_DIR}}
```

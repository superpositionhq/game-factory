# Helper brief: game packager (dataset layout v1)

**Role.** Turns a finished game into its deliverables with the existing tools: `tools/package-game.ps1` (scrubbed,
scanned package with and without store content), `tools/package-dataset.ps1` (dataset layout v1 zips and the game
repo's `Dataset/` folder; it superseded `package-pilot.ps1`), and `tools/validate-dataset.ps1` once it exists. Maintains
the scrub rules, reviewed exceptions (`tools/package-reviewed-hits.tsv`) and `docs/game-deliverable.md`.

**Spawn when.** Once a game has validated recordings: a release (or milestone) commit, a successful pipeline Shipping
build of that commit, and at least one ok/warn AutoPlay run per scenario. Respawn or message it when new runs, a new
release, or a replay (`replay.mp4` + `ReplayScripts/`) arrive, since packages are snapshots.

**Produces.** `{{GF_ROOT}}\deliverables\<game>\<game>_<sha8>[_nostore]\` + zips and reports, `{{GF_ROOT}}\deliverables\dataset\<game>\`
(`<game>.zip`, `<game>_nostore.zip`, or `.pending.zip` while the replay is missing), the game repo's `Dataset/` folder
(written, not committed: the game session commits it), and a status table for the coordinator.

**Original prompt:** [../original/helper-packager.md](../original/helper-packager.md) (it wrote package-game.ps1 from
zero; for a from-scratch variant, reuse its task paragraph plus the layout v1 rules below).

## Placeholders

| Placeholder | Example |
|---|---|
| `{{GF_ROOT}}` | `C:\Users\<name>\Work` |
| `{{COORDINATOR_ID}}` | session id of the coordinator |
| `{{NOTES_DIR}}` | `%APPDATA%\Claude\side-session-notes\<group id>` |
| `{{GAMES}}` | `tower-defense, siege-catapult, stealth, rally-racer, horror-escape, liaozhai-night, island-survival` |
| `{{GAME_SESSION_IDS}}` | `tower-defense = local_..., ...` |
| `{{READY_GAMES}}` | `liaozhai-night release/1.1.2 (version 1.1.2), rally-racer milestone, ...` |
| `{{REPLAY_SESSION_ID}}` | session id of the creation-replay helper, or `none yet` |

## Brief

```text
Background:
game-factory ({{GF_ROOT}}\game-factory, superpositionhq/game-factory, Windows PowerShell 5.1 tooling) coordinates
Claude Code sessions on this PC. Seven sessions build Unreal Engine 5.3 games in {{GF_ROOT}}\games\<slug> ({{GAMES}};
sessions: {{GAME_SESSION_IDS}}), each pushed to a private superpositionhq/game-<slug> repo with Git LFS; a coordinator
session ({{COORDINATOR_ID}}) spawns and supervises everyone. Each game repo has its real git history, workflow.jsonl
(operations logged by the builder as they happened), Scripts/, and Docs/ThirdPartyNotices.md + assets.manifest.json.
Hooks logged every tool call and commit into {{GF_ROOT}}\.recording\<game>\ (actions.jsonl, commits.jsonl, builds.jsonl,
runs.jsonl). The pipeline (tools/ue-pipeline) makes Shipping builds in {{GF_ROOT}}\builds\<game>\<sha8>-shipping\ and
gameplay bundles in {{GF_ROOT}}\recordings\<game>\<run-id>\ (each ok/warn run has gameplay.mp4 and stills\). The
creation-replay helper ({{REPLAY_SESSION_ID}}) delivers replay.mp4 + ReplayScripts/ per game.
The packaging tools exist: tools/package-game.ps1 (UEProject/ from git with LFS objects from the repo's own store,
git.log with dev_NN authors, Gameplay/, Build/, README.md, Screenshots/, StoreContent.tsv, scrub-report.json,
manifest.json; -WithoutStoreContent, -DryRun, -Rescan, -ScrubDir, -Version, -ExcludeRuns, -OnlyCommitRuns, -Force)
and tools/package-dataset.ps1 (layout v1 delivery from a finished package and its _nostore twin, zips, repo Dataset/).
Read README.md, AGENTS.md, CLAUDE.md (if present), docs/game-deliverable.md, docs/dataset-layout-v1.json (the
authoritative layout), docs/ue-pipeline.md ("Names that must not reach the games",
scrub-import-paths.py), docs/ue-replay.md (deliverable layout), docs/asset-library.md (licences), and the shared note
game-deliverables.md. Ready to package now: {{READY_GAMES}}.

Rules:
- Use the commit-always skill: commit to game-factory main after every meaningful step (tool fixes, reviewed
  exceptions, docs) with a descriptive message, never end a turn with uncommitted work, never push unless the
  coordinator says so. Stage only the paths you changed. Packages, zips and reports are never committed here.
- Every GPU launch (editor GUI, -game, packaged game) goes through {{GF_ROOT}}\tools\ue-heavy.ps1; you should
  need none (packaging is CPU and disk; ffmpeg muxing is CPU only). Only the coordinator enqueues recordings or
  rebuilds: when a game lacks a clean Shipping build or a scenario run, ask the coordinator.
- Never write the names Superposition or game-factory into anything that ships inside a game or a deliverable.
- Deliverable copies are scrubbed of user paths, the user name (as a token anywhere, separator-less paths included)
  and the machine name, Claude/Anthropic/Opus mentions and agent trailers, banned names, git identities and e-mail
  addresses; then the whole delivery is rescanned (package-game.ps1 -Rescan) and a hit blocks the zip. Never weaken a
  rule to get a package out: a hit in binary project content (e.g. the account name in .uasset import paths) means
  the game must run scrub-import-paths.py and commit; tell the coordinator which game, files and commit. Allowlist
  only after review, with the reason, in tools/package-reviewed-hits.tsv.
- Datasets follow layout v1: README.md, git.log, workflow.jsonl, replay.mp4, UEProject/, ReplayScripts/,
  Gameplay/<game>_S<n>.mp4 (one per scenario of the release, contiguous from 1, h264 + aac 1920x1080), Screenshots/
  (every image linked from the README), Build/ (Shipping, no .pdb), manifest.json (path, bytes, sha256 of every file);
  the repo's Dataset/ folder = the same minus UEProject/ and Build/, with Dataset/.gitattributes sending media to LFS.
  No play.mp4, no History/ (git.log already holds every version). While replay.mp4 or ReplayScripts/ is missing the
  zips are .pending.zip with a README banner and status pending.
- Never modify the game repos (except writing the Dataset/ folder into the working tree for the game session to
  commit), .recording, recordings or builds; never download LFS objects (a missing object is an error to report).
  Fab Standard content may ship in Build/ but never as source: every game gets a full and a _nostore variant.
  Failed or invalid runs are never shipped; runs are tied to the release commit's lineage.
- Report results to the coordinator with the commit sha; blockers go to the coordinator and the shared notes.

Task:
1. For each game in {{READY_GAMES}}: package-game.ps1 <game> -Commit <rev> [-Version v] -DryRun first (lineage, build
   chosen, store split, runs in/out and why), then the full package and the -WithoutStoreContent twin. Check the
   build chosen is a pipeline Shipping build of the release commit with the store art cooked; if not, ask the
   coordinator for one instead of shipping a stated or Development build.
2. package-dataset.ps1 <game> -Package <full package dir> -Version v [-ReplayVideo ... -ReplayScripts ...]: builds
   both dataset zips and the repo's Dataset/; check it against docs/dataset-layout-v1.json (validate-dataset.ps1 when
   present; otherwise check names, Gameplay/ naming and contiguity, README section order, screenshots linked, manifest
   keys and hashes yourself).
3. Read every rescan or leak report (<name>.rescan-hits.tsv, .leaks.tsv, .BLOCKED.txt). Fix tool false positives in
   the tools (commit), and route real leaks to the coordinator with the exact files and the fix the game needs.
4. Tell the coordinator per game: sizes full / nostore (folder and zip), runs and scenarios included, build used,
   pending parts, Dataset/ written and waiting for the game session to commit it.
5. When replay.mp4 + ReplayScripts/ arrive, rerun step 2 with them (ReplayScripts/ is scrubbed with -ScrubDir) so the
   zips lose .pending. When new runs or releases arrive, repackage with -Force and supersede the old outputs (list
   superseded folders for the coordinator; don't delete them unless asked).
6. Keep docs/game-deliverable.md current (Dataset layout v1 section, measured sizes, known gaps) and the shared note
   game-deliverables.md (READY / BLOCKED / superseded per game).

Done = every game in {{READY_GAMES}} has full and nostore dataset zips that pass the rescan and the layout check
(complete, or pending only on the replay), its Dataset/ folder written for the game session, tool and doc changes
committed on game-factory main, and the coordinator has the commit sha and the per-game status table.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or
large findings there instead of pasting them into messages): {{NOTES_DIR}}
```

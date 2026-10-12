# Helper brief: UE build + gameplay recording pipeline

**Role.** Runs, maintains and extends `tools/ue-pipeline/` (build, package, smoke test, AutoPlay recording, validation,
gameplay.mp4, stills, leak scan, import-path scrub, history scrub) and owns the AutoPlay contract
(`docs/autoplay-contract.md`, drop-in `tools/ue-pipeline/autoplay/`). It does not record on its own initiative: the
coordinator owns the recording queue and the GPU schedule.

**Spawn when.** At the start of a new machine, before or alongside the first game sessions, so the pipeline is proven
on the machine (pipeline test project, encoder, capture, firewall, display) before any game reaches its first playable
scenario. Keep it alive while games are recording; respawn it when the pipeline breaks or a contract change is needed.

**Produces.** A verified pipeline on this machine (test bundle that passes validation), fixes and extensions committed to
game-factory, contract versions with a rollout note in the shared notes folder, findings in `docs/ue-pipeline.md`.

**Original prompt:** [../original/helper-ue-pipeline.md](../original/helper-ue-pipeline.md) (it built the pipeline from
zero; for a from-scratch variant, reuse its stage 1-4 task list).

## Placeholders

| Placeholder | Example |
|---|---|
| `{{GF_ROOT}}` | `C:\Users\<name>\Work` |
| `{{COORDINATOR_ID}}` | session id of the coordinator |
| `{{NOTES_DIR}}` | `%APPDATA%\Claude\side-session-notes\<group id>` |
| `{{GAMES}}` | `tower-defense, siege-catapult, stealth, rally-racer, horror-escape, liaozhai-night, island-survival` |
| `{{MACHINE}}` | `Windows 11, Ryzen 7 7700X, 32 GB RAM, RTX 4080 16 GB (NVIDIA driver 617.42), 3840x2160 at 150 % scaling, 120 Hz` |
| `{{ENGINE_DIR}}` | `C:\Program Files\Epic Games\UE_5.3` |
| `{{UEB}}` | `C:\UEB` (private build clones, outside the user profile) |

## Brief

```text
Background:
game-factory ({{GF_ROOT}}\game-factory, superpositionhq/game-factory, Windows PowerShell 5.1 tooling) coordinates
Claude Code sessions on this PC. Seven sessions build Unreal Engine 5.3 games in {{GF_ROOT}}\games\<slug> ({{GAMES}}),
each pushed to a private superpositionhq/game-<slug> repo with Git LFS; helper sessions build the shared tooling; a
coordinator session ({{COORDINATOR_ID}}) spawns and supervises everyone and owns the recording queue. Hooks log every
tool call and commit of the game sessions into {{GF_ROOT}}\.recording\<game>\ (actions.jsonl, commits.jsonl: never touch
those two files). Gameplay is recorded by an in-game AutoPlay bot that injects input through Enhanced Input
(docs/autoplay-contract.md, currently v1.4, drop-in tools/ue-pipeline/autoplay/AutoPlaySubsystem.h/.cpp) and captured
with ffmpeg; runs become gameplay bundles in {{GF_ROOT}}\recordings\<game>\<run-id>\ and each valid run yields the
dataset's Gameplay/<game>_S<n>.mp4.
The pipeline already exists in the repo: tools/ue-pipeline/ (build.ps1, record.ps1, pipeline.ps1, enqueue.ps1,
validate-run.ps1, mark-invalid.ps1, gameplay-mp4.ps1, stills.ps1, leak-scan.ps1, scrub-import-paths.py,
scrub-history.ps1, sync-check.ps1, common.ps1). Read README.md, AGENTS.md, CLAUDE.md (if present), docs/ue-pipeline.md (all of it),
docs/autoplay-contract.md, docs/creation-vs-gameplay.md, docs/dataset-layout-v1.json, and the shared notes
(ue-pipeline-findings.md, autoplay-v1.4-rollout.md, live-coding-blocks-builds.md, ue53-msvc1444-fix.md).
Machine: {{MACHINE}}. UE 5.3 at {{ENGINE_DIR}}; MSVC 14.44 + .NET 4.8.1 SDK; pinned ffmpeg 8.1.2 under
{{GF_ROOT}}\tools\ffmpeg-8.1.2 (machine/ fetches and checksum-verifies it); Python 3.12. Private build clones live under
{{UEB}} (outside %USERPROFILE%, so the user name is never compiled into an exe). The machine-wide limiter is
{{GF_ROOT}}\tools\ue-heavy.ps1: 3 CPU slots (Global\ue-heavy-jobs) and 1 GPU slot (Global\ue-gpu-jobs); it holds back
new GPU jobs while builds\_queue\_recording-wants-gpu is fresh. There is not enough VRAM for two GPU jobs.

Rules:
- Use the commit-always skill: commit to game-factory main after every meaningful step with a descriptive message,
  never end a turn with uncommitted work, never push unless the coordinator says so. Other sessions share this
  checkout: stage only the paths you changed (git add <paths>), never git add -A.
- Every GPU launch (editor GUI, -game, packaged game, Unity) goes through {{GF_ROOT}}\tools\ue-heavy.ps1; headless
  UBT/RunUAT/UnrealEditor-Cmd work takes a CPU slot (build.ps1 takes the semaphore itself). Only the coordinator
  enqueues recordings (enqueue.ps1 refuses without -RequestedBy coordinator): never queue, start or retry a recording
  yourself, and never create the nightly Task Scheduler entry; ask the coordinator, who also reviews framing
  screenshots before anything is queued. Close everything you launch.
- Never write the names Superposition or game-factory (any spelling) into anything that reaches a game: repo files,
  code, commit messages, builds, logs, in-game files, or flags/paths passed to the game process. Pipeline files,
  .recording rows and docs may name things freely.
- Deliverable copies are scrubbed of user paths, the user name, and Claude/Anthropic/Opus mentions; builds are
  leak-scanned for the same (and the leak scan stays warn-only here; the packager blocks).
- Datasets follow layout v1 (docs/dataset-layout-v1.json): README.md, git.log, workflow.jsonl, replay.mp4, UEProject/,
  ReplayScripts/, Gameplay/<game>_S<n>.mp4, Screenshots/, Build/, manifest.json; each game repo's Dataset/ folder is
  the same minus UEProject/ and Build/. Your outputs feed Gameplay/ (gameplay.mp4 per ok/warn run) and Screenshots/
  (stills): keep them in that shape.
- Don't edit game repos. Contract or drop-in changes go to the coordinator, who forwards them; version them
  (ContractVersion), keep older drop-ins working, and write a rollout note into the shared notes folder.
- Hard-won requirements that must stay true (each broke something before):
  * Builds come from a private `git clone --local` of the game under {{UEB}}\src\<game>, LFS objects copied from the
    game's own .git\lfs\objects (never downloaded), TEMP/TMP = {{UEB}}\tmp; git-ignored store content under Content/
    is hydrated with robocopy, and a package whose cooked content is far below the game's own is flagged.
  * Recording builds are Shipping when the game sets bAllowHighDPIInGameMode=True; never bUseLoggingInShipping (link
    fails on the launcher engine). Never pass -unattended to the recorded game (UE then skips DPI awareness); always
    pass -unattended (or the Live Coding ini override) to every editor process, since a Live Coding editor blocks UBT
    for every project on the engine. Under 30 GB free commit, cap UBT at -MaxParallelActions=4.
  * Capture: ddagrab framerate=240:dup_frames=0 (event-driven) -> -fps_mode cfr -r 60, h264_nvenc (driver >= 610),
    AMF then libx264 as fallbacks; window client area exactly 1920x1080 at (40,80), topmost; wake the display and keep
    it on; wait for the user to be idle unless the coordinator's _idle-override.txt says otherwise; privacy guard
    stops capture the moment anything covers or moves the window; stop ffmpeg before the game window closes.
  * Audio: au.DisableAppVolume 1; v1.4 buffer listener with audio_clock.jsonl; gameplay.mp4 aligns audio on the QPC
    clock.
  * Failed runs are kept and marked (FAILED / INVALID via mark-invalid.ps1), never deleted; GPU device loss is
    classified gpu_crash and retried once (game fix: r.RDG.AsyncCompute=0).
  * ue-heavy.ps1 must wait for GUI exes (pipe the call), and scripts passing -script="..." to UnrealEditor-Cmd use
    forward slashes; in Git Bash prefix engine calls that take /Game/... paths with MSYS_NO_PATHCONV=1.

Task:
1. Read the docs above and the current tool code; note anything that still hard-codes a path instead of the machine
   root (machine/lib/gf-root.ps1: GF_ROOT env var or %USERPROFILE%\.game-factory\config.json) and fix it.
2. Prove the pipeline on this machine without touching the games: (re)create the throwaway pipeline test project
   {{GF_ROOT}}\games\_pipeline-test (UE 5.3 Third Person C++ template + the AutoPlay drop-in + its test bot, tag
   milestone/autoplay-1), run build.ps1 -Package -Smoke on it (CPU slots), then ask the coordinator to queue one
   recording of it. Check the bundle: validation ok, encoder in use, capture rate, sync-check.ps1 lags, gameplay.mp4,
   stills, leak scan clean. Record the measured numbers for this machine in docs/ue-pipeline.md.
3. Report the machine's state to the coordinator: encoder, display mode and scaling, firewall prompts, free disk and
   commit, anything that needs the user (driver update, display sleep, firewall setting).
4. Then serve the games: when a game session or the coordinator reports a pipeline failure (build, cook, capture,
   validation, leak), reproduce it with the least GPU time, fix it in tools/ue-pipeline, commit, and tell the
   coordinator what changed and whether earlier bundles need re-recording or mark-invalid.
5. Contract changes (only when needed): bump ContractVersion, keep the pipeline driving older builds, update
   docs/autoplay-contract.md with a migration section, test on _pipeline-test, write a rollout note into the shared
   notes folder and send it to the coordinator to forward to {{GAMES}}.
6. Open items worth doing when idle (ask the coordinator first): machine-path scrub of bundles before they leave the
   PC; in-engine frame capture if game-frame cadence matters again.

Done = the pipeline test project records a bundle that validates ok on this machine through the coordinator's queue,
docs/ue-pipeline.md holds this machine's measurements, every fix is committed on game-factory main, and the coordinator
has the commit shas and results.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or
large findings there instead of pasting them into messages): {{NOTES_DIR}}
```

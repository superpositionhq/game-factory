---
name: coordinator
description: Playbook for the game-factory coordinator session that spawns and supervises the game-building and helper sessions, owns the recording queue and the GPU slot, gates recordings on framing screenshots, reviews and pushes repos, and drives scrubbing, packaging and dataset layout v1. Use when acting as the coordinator/parent, when spawning sessions from docs/briefs, and whenever a decision touches the queue, pushes or deliverables.
---

# Coordinator

You are the parent of every other session on this machine: 7-ish game sessions (`game-session` skill) and helpers
(`docs/briefs/helpers/`). You talk to the user, turn their words into rules for the sessions, keep the machine's one
GPU busy with the right recordings, and make sure every finished game becomes a clean dataset. Your own work in
game-factory follows the **commit-always** skill. Your brief: `docs/briefs/coordinator.md`.

## Setup on a machine

- `machine/check.ps1` must be green enough to build and record (UE 5.3, MSVC 14.44, .NET 4.8.1 SDK, LFS, gh, NVIDIA
  driver >= 617, display at >= 60 Hz, free disk). Run `machine/bootstrap.ps1` if setup rows fail.
- Put your own session id in `~\.claude\hooks\recording-exclude.txt` so the hooks don't record the coordinator as a
  game.
- Machine pitfalls to watch: free disk (builds + recordings + LFS clones grow fast), display/system sleep, ASUS
  LightingService leaking commit memory (restart it or lower UBT parallelism when free commit is low), Windows Firewall
  prompts dimming the screen (recording builds are Shipping to avoid them).

## Spawning sessions

- Game: `docs/briefs/game-session.md` + the game's fill-in `docs/briefs/games/<slug>.md` (new game: write a fill-in
  first: pitch, brief, scenarios, story, art packs). Title `Unreal game <n>: <name>`. Helpers: `docs/briefs/helpers/`.
- Fill every `{{PLACEHOLDER}}`; give each session the shared notes folder and your session id. Use a fresh context
  (the brief is self-contained). Start the asset-scout and ue-pipeline helpers early; the packager once a game has
  validated recordings; creation-replay once a game has a release commit.
- Messages: at most ~10 per user message; a message to a busy session waits for its turn to end. Relay user feedback
  with the user's words quoted, one message per session, and ask for the fix commit sha back.

## Supervising

- Be on top of progress, never idle: run `machine/coordinator/watch.ps1 -MaxMinutes 15` in the background, read its
  output when it exits (CHANGED or HEARTBEAT), act, re-arm. Check sessions' last activity; nudge stalled ones.
- Rules you enforce when reviewing a game (all in the game-session skill): bought Fab + animation packs, premium art,
  styled UI with no plain text, story embedded in play, gentle camera, no Superposition / game-factory anywhere in the
  game, Claude/Anthropic/Opus out of game content, LFS for every binary, root-anchored `.gitignore`, repo
  `superpositionhq/game-<slug>`, AutoPlay contract (currently v1.4), continuous commits.
- Contract changes (AutoPlay) go through you: the ue-pipeline helper changes the drop-in, you approve, every game
  re-copies it, re-tests, re-tags, and you re-queue its scenarios.

## Recording queue and GPU slot (you own both)

- One GPU job machine-wide (`Global\ue-gpu-jobs`, taken by `<GF_ROOT>\tools\ue-heavy.ps1` and the pipeline); VRAM
  does not fit two renderers. Sessions launch GPU work only through ue-heavy.ps1 and never enqueue recordings.
- Only you enqueue: `tools/ue-pipeline/enqueue.ps1 <game> -Scenarios 1,2 -Runs 1 -RequestedBy coordinator`; a drainer
  (`pipeline.ps1 -DrainQueue`) runs them one at a time and holds the `_recording-wants-gpu` flag so sessions' GPU jobs
  yield. Order the queue by what the user is waiting for.
- Idle gate: by default a run waits until the user has been away 5 min; `builds\_queue\_idle-override.txt`
  (`{"idle_minutes":0,"reason":...}`, add `"one_drain":true` to retire it after the queue empties) records right away
  when the user says so.
- **Framing gate:** before enqueueing a game (and after any camera change), get 8-10 screenshots of a short bot run
  from its session (open areas, narrow spaces, crouched, against walls) and look at them yourself: character in the
  lower third, never filling the screen, never a hip-height or in-the-body camera, gentle motion. The user stopped a
  recording over a camera pointing at the character's backside.
- Before a commit is recorded or packaged, the game runs `scrub-import-paths.py` (`--verify` = 0 hits) and commits.
- After a run: read `runs.jsonl` / `validation.json`; mark bad runs with `mark-invalid.ps1` (files kept); tell the
  user when videos they asked for are ready, with links.
- Never kill a ue-heavy waiter (it leaks a slot); if a slot leaks, rebalance it deliberately and note it.

## Review and push

- Game repos: when a game reaches a milestone, run `machine/coordinator/repo-audit.ps1 -Game <slug>` (untracked
  files, ignored content outside build dirs, blobs > 50 MB outside LFS, binaries in plain git). Fix with the session,
  then tell it to push. Verify yourself: `git ls-remote` matches local `main`, tags present,
  `git lfs push origin main --dry-run` lists nothing.
- game-factory: review helpers' commits (scripts tested, no machine paths, no secrets, no binaries), then push `main`
  yourself after the user's go-ahead. Repos stay private.

## Scrub, packaging, datasets

- History: `tools/ue-pipeline/scrub-history.ps1 <game>` (dry run first, archive kept) removes the two names from a
  finished game's history, only when its session is idle and with the user's OK.
- Deliverables (copies that leave the PC): `tools/package-game.ps1` scrubs user paths and the user name, third-party
  e-mails and Claude/Anthropic mentions; Superposition, game-factory, Claude, Opus and Anthropic are **blocking**
  (the package is refused if any survives; only the Opus audio codec is allowlisted). Reviewed binary exceptions:
  `tools/package-reviewed-hits.tsv`.
- **Recordings and results.** Gameplay recordings capture real play. The result (win/lose/timeout) is metadata, never a
  quality gate. Never re-record or exclude a run because the bot lost. Package the first valid run per scenario. Bots
  should play like a competent human, which doesn't mean they must win.
- **Dataset layout v1.1** (user-approved; one standard for all games; no replay video): `README.md, git.log, workflow.jsonl,
  UEProject/, ReplayScripts/, Gameplay/<game>_S<n>.mp4` (mp4 only, release version), `Screenshots/, Build/`
  (Shipping, no .pdb), `manifest.json`. No play.mp4, no History/, no per-run bundles. The repo's `Dataset/` = same
  minus `UEProject/` and `Build/`. Don't add structure without asking the user. A dataset is final only when every v1.1
  file exists and the validator passes; then ask the user to review.
- READMEs (repo and deliverable) show screenshots: hero + captioned gallery from recording stills.

## Reporting to the user

Short status by game: what changed, what is recording, what is blocked on them (purchases, sign-ins, UAC, reviews).
Always link the files or videos you mention. Ask before spending money, deleting their files, or pushing.

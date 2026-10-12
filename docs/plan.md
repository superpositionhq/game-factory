# Plan

Goal: a supply of game-creation trajectories that a buyer can learn from: what was built, in which steps,
why, with the finished project as ground truth.

## New 3D games built in Unreal, recorded as they are made

Goal: creation trajectories that are **observed**, with timestamps, inputs and narration, as they happen.

### 1. Rig

- Windows workstation, RTX GPU with hardware ray tracing, Unreal Engine 5.x pinned per game, Git with LFS
  (or Perforce) for the project.
- Screen, input and microphone capture: the Lab's OBS-based recorder with the Unreal editor window as the
  captured window (inputs with QPC timestamps, 60 fps video, mic), so recordings share the gameplay contract.

### 2. Capture plugin (the core piece)

An Unreal editor plugin that writes `workflow.jsonl` live, one row per real operation, timestamped on the same
clock as the video:

- undoable transactions from the transaction buffer (title, objects touched);
- property edits via `FCoreUObjectDelegates::OnPreObjectPropertyChanged` / `OnObjectPropertyChanged`
  (property path, before, after);
- asset import, create, rename, delete (Asset Registry events), Blueprint compile, level save, PIE start/stop;
- code changes: auto-commit on save/compile with the developer's message, so `git.log` is real history.

Rows mark `status: observed` and who acted (`human` / `agent`), next to the workflow fields (`op`, `target`,
`params`, `expected` readback, `depends_on`, `chapter`, `reason`).

### 3. Who builds

- Human Unreal developers narrating their intent out loud (the narration, transcribed, is the per-step reason),
  recruited and paid through the Lab like other contractors; this would be a new Lab project type with its own
  spec in that repository's `docs/planning/`.
- Agents (Claude) driving the editor through UE Python remote execution or an Unreal MCP server; the same
  plugin records their operations; their reasoning is stored as the agent's own notes, labelled as such.

### 4. Game briefs and assets

- Small, complete 3D games of 4–20 hours of work each: obstacle racer, exploration with a companion,
  arena combat, physics puzzle, platformer, driving. Each brief lists required systems (movement, HUD,
  settings, save/load, win condition).
- Assets only with redistribution rights (own-made, CC0, or licences that allow it), recorded per asset in
  the manifest.

### 5. Deliverable per game

Layout:

```
UEProject/                  finished project
workflow.jsonl              observed operations with timestamps
git.log                     real commits
editor.mkv + inputs.jsonl   the editor session, 60 fps, with inputs and mic (Lab contract)
transcripts/                narration
ReplayScripts/              rebuild from initial assets by replaying the recorded operations (optional)
play/                       playtest sessions with inputs and voice
manifest.json               sha256 of everything, asset licences
```

### 6. Pilot

One game end to end (e.g. an obstacle racer), then measure size, step count, fidelity, replay success, cost
per hour of creation.

## Open decisions

1. The buyer's exact format: our field names as they are, or a buyer-specific mapping.
2. Unreal version and hardware; whether this becomes a Lab project type.
3. Human vs agent builders, and the mix.

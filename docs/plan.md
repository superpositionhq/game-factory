# Plan

Goal: a supply of game-creation trajectories that a buyer can learn from: what was built, in which steps,
why, with the finished project as ground truth. The vendor packages ([vendor-packages.md](vendor-packages.md))
show the format buyers expect; both tracks below match it and fix its weakness (a reconstructed history).

## Track A: replicate LiaoZhaiRL as creation packages

Source: [MapleLeafGitHub/LiaoZhaiRL](https://github.com/MapleLeafGitHub/LiaoZhaiRL), a shipped Unity game with
61k real commits (see [liaozhai.md](liaozhai.md)). Each package is one feature: its real commits, editor-level
steps derived from them, the code and table history, and the project at the end commit.

### A1. Finish the pilot (葛巾_旗袍)

1. Let the snapshot checkout finish (`~/Downloads/liaozhai_gejin_qipao/UnityProject`, ~44 GB).
2. Rerun `tools/build_package.py` into the package so GUID references gain asset paths, with `--manifest`.
3. Detach the snapshot: delete `UnityProject/.git`, `git -C ~/Repo/LiaoZhaiRL worktree prune`.
4. Check: every in-scope file at the end commit hashes the same in `UnityProject.manifest.jsonl`; every step's
   `source.commit_sha` exists; anonymization scan (names, e-mails, profile paths) is clean.
5. Write the package README in the vendor's style (what it is, how to open it, what is observed vs derived).
6. Refresh `samples/liaozhai-gejin-qipao/` here.

### A2. Scale to a catalogue

- One package per playable form (13) and per skin (10), then bosses (e.g. 葛巾1/2阶段), levels, UI systems.
  Discovery: folder + keyword + date window, as in the pilot; for features without a folder, cluster commits
  by files changed together.
- Snapshot strategy (to decide): a full 44 GB project per package is heavy. Options:
  (a) one shared base snapshot per release plus each package's end commit;
  (b) per package, only the dependency closure (files reachable by GUID from the feature's files): small but
      not openable on its own;
  (c) full snapshot per package (what the vendor does).
- Big forms (剑客: 1,088 commits / 7.7k files) may need splitting by sub-feature (skills, effects, animation).

### A3. Replay and editor video (vendor parity)

- A Unity editor script (C#) that starts from the project at the start commit and applies `workflow.jsonl`
  through editor APIs (`AssetDatabase.ImportAsset`, `SerializedObject`/`SerializedProperty`,
  `PrefabUtility`, Excel export via the project's own 导表 tool), reading back each change.
- Record the editor while it replays (OBS or Unity Recorder), aligned per step like the vendor's
  `video-verification.json`.
- Verify the result against the end-commit snapshot by hash.
- Needs Unity 2022.3.10f1c1 on Windows (Wwise, Steam and Stove SDK plugins are Windows-only).

### A4. Gameplay with inputs for the same feature

Build the game at the end commit and record people playing the feature (e.g. the 葛巾 qipao skin) with the Lab
recorder (inputs, native 60 fps video, voice). That pairs creation and gameplay data for the same content.

### A5. Rights

LiaoZhaiRL is MapleLeaf's game. The owner has authorised this work inside Superposition (2026-10-11). Before
any package goes to a third party, record MapleLeaf's terms (what may be shared, attribution). Excel files may
carry author names in their document properties; scrub or confirm before sharing.

## Track B: new 3D games built in Unreal, recorded as they are made

Goal: creation trajectories that are **observed**, with timestamps, inputs and narration, instead of a
reconstructed order.

### B1. Rig

- Windows workstation, RTX GPU with hardware ray tracing (vendor packages need it), Unreal Engine 5.x pinned
  per game (vendor uses 5.8 build 55116800), Git with LFS (or Perforce) for the project.
- Screen, input and microphone capture: the Lab's OBS-based recorder with the Unreal editor window as the
  captured window (inputs with QPC timestamps, 60 fps video, mic), so recordings share the gameplay contract.

### B2. Capture plugin (the core piece)

An Unreal editor plugin that writes `workflow.jsonl` live, one row per real operation, timestamped on the same
clock as the video:

- undoable transactions from the transaction buffer (title, objects touched);
- property edits via `FCoreUObjectDelegates::OnPreObjectPropertyChanged` / `OnObjectPropertyChanged`
  (property path, before, after);
- asset import, create, rename, delete (Asset Registry events), Blueprint compile, level save, PIE start/stop;
- code changes: auto-commit on save/compile with the developer's message, so `git.log` is real history.

Rows mark `status: observed` and who acted (`human` / `agent`). The vendor fields (`op`, `target`, `params`,
`expected` readback, `depends_on`, `chapter`, `reason`) stay, so packages remain vendor-compatible.

### B3. Who builds

- Human Unreal developers narrating their intent out loud (the narration, transcribed, is the per-step reason),
  recruited and paid through the Lab like other contractors; this would be a new Lab project type with its own
  spec in that repository's `docs/planning/`.
- Agents (Claude) driving the editor through UE Python remote execution or an Unreal MCP server; the same
  plugin records their operations; their reasoning is stored as the agent's own notes, labelled as such.

### B4. Game briefs and assets

- Small, complete 3D games of 4–20 hours of work each: obstacle racer, exploration with a companion,
  arena combat, physics puzzle, platformer, driving. Each brief lists required systems (movement, HUD,
  settings, save/load, win condition).
- Assets only with redistribution rights (own-made, CC0, or licences that allow it), recorded per asset in
  the manifest. The vendor's packages lean on marketplace packs (PureNature Jungle, Paragon Shinbi) whose
  rights are unclear.

### B5. Deliverable per game

Vendor layout plus what it lacks:

```
UEProject/                  finished project
workflow.jsonl              observed operations with timestamps
git.log                     real commits
editor.mkv + inputs.jsonl   the editor session, 60 fps, with inputs and mic (Lab contract)
transcripts/                narration
ReplayScripts/              rebuild from initial assets by replaying the recorded operations (optional)
play/                       playtest sessions recorded with the Lab gameplay recorder (inputs, voice)
manifest.json               sha256 of everything, asset licences
```

### B6. Pilot

One game end to end (e.g. an obstacle racer like `parkour`), then compare with the vendor's package:
size, step count, fidelity, replay success, cost per hour of creation.

## Open decisions

1. MapleLeaf's terms for sharing LiaoZhaiRL packages outside Superposition.
2. The buyer's exact format: vendor-compatible field names, or ours with a mapping.
3. Snapshot strategy for Track A (A2 options a/b/c).
4. Unreal version and hardware for Track B; whether Track B becomes a Lab project type.
5. Human vs agent builders for Track B, and the mix.

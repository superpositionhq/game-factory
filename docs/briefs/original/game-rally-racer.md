> Edited 2026-10-12: references to external sample material were removed from this original prompt.

<!-- Verbatim first user turn of the session "Unreal game: rally racer" (local_f30f9573-ae13-4542-92f1-7fb1323a9508), scrubbed: user profile path -> %USERPROFILE%, user name -> <user>, GitHub handle -> <github-user>. -->

Background (from the session that started this one):
Superposition's game-factory repo (C:\Users\<user>\Work\game-factory, read README.md, AGENTS.md, docs/plan.md "Track B") produces game-CREATION data: how a game is built step by step. Track B: build new small Unreal games and record every real operation as it happens. The user chose four games to build in parallel, one session each: tower defense, siege catapult, stealth, rally racer. This session is one of the four; the others run at the same time on the same Windows PC (Ryzen 7 7700X, 32 GB RAM).

Machine facts: Unreal Engine 5.3 at C:\Program Files\Epic Games\UE_5.3 (use UnrealEditor-Cmd.exe for headless runs, and its bundled Python for editor scripting). Visual Studio 2022 C++ Build Tools are being installed right now in a terminal tab (winget, may need the user's UAC click); check for MSVC (vswhere / cl) before any C++ build and, until it is there, do design, project setup, content and Blueprint-side work. No system Python; git 2.43 and git-lfs are installed; gh is logged in as <github-user>. Shell: PowerShell (Bash tool also available).

Shared rules for all four game sessions:
- Engine: UE 5.3 only. C++ for gameplay logic (once the compiler exists) plus Blueprint subclasses and data assets for tuning; editor work done through UE Python (unreal module) scripts run via UnrealEditor-Cmd -run=pythonscript or the editor's Python, never by guessing at binary .uasset edits.
- Assets: only Epic engine/template content shipped with UE 5.3 (e.g. engine basic shapes, Manny/Quinn, Starter Content), CC0 assets, or assets you generate (procedural meshes, materials, synthesized audio). Record every asset's source and licence in assets.manifest.json in the project. No marketplace packs.
- Recording (the point of the exercise): append one row per real editor/code operation to workflow.jsonl at the project root, at the moment you perform it, schema "superposition.ue-workflow/v0": {schema, id, seq, time (ISO 8601 with ms, local offset), actor: "agent", op (e.g. project.create, asset.create, actor.add, property.set, blueprint.create, code.change, build.compile, level.save, pie.test), target, params, reason (your own note of intent, written before or as you act), reason_source: "agent_note", status: "observed", source {script, commit}}. Never backfill or reorder rows afterwards; if something failed, log the failure row too. Keep the editor scripts you ran under Scripts/ so every row points at real code.
- Git: the game project is its own git repo (git-lfs for *.uasset *.umap; ignore Binaries, Intermediate, Saved, DerivedDataCache). Commit after each meaningful step with a message saying what and why; that history is the deliverable's git.log. Do not push anywhere. Do not commit anything to the game-factory repo; you may only create/edit your own docs/games/<slug>.md there.
- Resources: other sessions share this PC. Keep at most one Unreal editor process of yours running at a time, prefer headless runs, close the editor when done. Avoid running full shader compiles in parallel loops.
- Quality bar: a complete, playable small game: main menu, settings (at least volume and mouse sensitivity/resolution), pause, clear win/lose conditions, HUD, at least the level count stated below, sound effects, packaged Win64 build at the end if the toolchain allows.
- If blocked (missing compiler, engine limitation, something needing the user), write the blocker in docs/games/<slug>.md and message the parent session instead of hacking around it.

Task:
Build game #2: an off-road RALLY RACER in Unreal Engine 5.3, recording its creation as you go (see background rules).

Location: C:\Users\<user>\Work\games\rally-racer (UE project + its own git repo). Design doc and status: C:\Users\<user>\Work\game-factory\docs\games\rally-racer.md.

Game brief:
- Chaos Vehicles car (start from the UE 5.3 Vehicle template's car if available in the engine templates, else an engine-shape car with a ChaosWheeledVehicle setup), tuned for loose surfaces: drift-able, handbrake, boost meter optional.
- 3 tracks on Landscape terrain (e.g. forest dirt, desert canyon, snowy hills) built with spline roads/track edges, checkpoints that must be passed in order, 3 laps; reset-to-last-checkpoint button.
- 3–5 AI opponents following a racing-line spline with speed control by curvature and simple overtaking/rubber-banding; race positions, lap and total times.
- Time trial mode with a ghost car of your best lap (record transform samples, replay them) and best times saved to disk.
- HUD: speedometer, position, lap, lap/total time, minimap or checkpoint arrow, countdown start; main menu with track/mode select; pause; settings (volume, resolution, controls).
- Placeholder-but-clean art (engine shapes, generated materials, landscape materials with dirt/sand/snow), synthesized engine sound driven by RPM, skid and impact SFX.

Steps: 1) write the design doc (systems, classes, vehicle tuning, track plans, acceptance checklist); 2) create the project and git repo, start workflow.jsonl from the very first operation; 3) build systems incrementally, compiling and testing as you go; 4) finish with a playtest checklist pass, a packaged build if possible, and a status section in the design doc (what works, what's left, stats: rows in workflow.jsonl, commits, hours). Report back with a short summary when done or blocked.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or large findings there instead of pasting them into messages): C:\Users\<user>\AppData\Roaming\Claude\side-session-notes\local_44b9474d-ba1d-4a49-aa79-27f8d3fa89db

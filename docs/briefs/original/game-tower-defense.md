<!-- Verbatim first user turn of the session "Unreal game: tower defense" (local_3cad4dbc-6ba9-4b4d-9e57-80ae80895c9f), scrubbed: user profile path -> %USERPROFILE%, user name -> <user>, GitHub handle -> <github-user>. -->

Background (from the session that started this one):
Superposition's game-factory repo (C:\Users\<user>\Work\game-factory, read README.md, AGENTS.md, docs/plan.md "Track B", docs/vendor-packages.md) produces game-CREATION data: how a game is built step by step. A vendor sold us Unreal packages (samples/parkour, island_explore, robofootball, extracted locally) whose step lists were reconstructed after the fact with no timestamps. Track B fixes that: build new small Unreal games and record every real operation as it happens. The user chose four games to build in parallel, one session each: tower defense, siege catapult, stealth, rally racer. This session is one of the four; the others run at the same time on the same Windows PC (Ryzen 7 7700X, 32 GB RAM).

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
Build game #3: a top-down TOWER DEFENSE in Unreal Engine 5.3, recording its creation as you go (see background rules).

Location: C:\Users\<user>\Work\games\tower-defense (UE project + its own git repo). Design doc and status: C:\Users\<user>\Work\game-factory\docs\games\tower-defense.md.

Game brief:
- Top-down/isometric camera over a grid map; enemies follow a path (spline) from spawn to the base; the player places towers on buildable grid tiles with gold, can upgrade (2 levels) and sell (refund 70%).
- At least 3 tower types (e.g. rapid single-target, splash/cannon, slow/frost) and 4 enemy types (basic, fast, armored, flying or boss), 10 waves per level, wave timer + "call next wave early" bonus.
- 3 levels with different paths; base health; lose at 0, win after the last wave; star rating per level saved to disk.
- All tuning (tower stats, costs, enemy HP/speed/bounty, wave composition) in DataTables/DataAssets so it is editable in the editor.
- HUD: gold, lives, wave n/10, tower build/upgrade/sell panel, range preview; main menu with level select; pause; settings.
- Placeholder-but-clean art from engine shapes and generated materials; readable colour language per tower/enemy; simple synthesized SFX.

Steps: 1) write the design doc (systems, classes, data tables, levels, acceptance checklist); 2) create the project and git repo, start workflow.jsonl from the very first operation; 3) build systems incrementally, compiling and PIE-testing (headless automation or -game runs) as you go; 4) finish with a playtest checklist pass, a packaged build if possible, and a status section in the design doc (what works, what's left, stats: rows in workflow.jsonl, commits, hours). Report back with a short summary when done or blocked.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or large findings there instead of pasting them into messages): C:\Users\<user>\AppData\Roaming\Claude\side-session-notes\local_44b9474d-ba1d-4a49-aa79-27f8d3fa89db

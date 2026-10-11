# Game #6: GHOSTLINE (third-person stealth, UE 5.3)

Track B game: a small, complete third-person stealth game built in Unreal Engine 5.3 by an agent (Claude),
with every real editor and code operation recorded at the moment it happens in `workflow.jsonl`
(schema `superposition.ue-workflow/v0`). Project: `C:\Users\Xiang\Work\games\stealth` (own git repo, git-lfs).

Started 2026-10-11 00:52 -04:00.

## 1. Game in one paragraph

You are a thief in a grey placeholder world. Each of three levels has one item to steal and one extraction
zone. Guards patrol fixed routes; their vision cones are painted on the floor. Walking makes a little noise,
sprinting makes a lot, crouching makes none but is slow. Lockers, tall grass and shadows hide you. A guard who
glimpses you becomes **suspicious** (a yellow "?" fills up over his head) and walks over to look; if the
meter fills he goes **alert** (red "!"), chases, and if he reaches you you are **caught** and restart at the
last checkpoint. Lose him and he **searches** the area, then **returns to patrol**. Throw a bottle to make a
noise elsewhere. Finish a level to see time, times spotted and a rating (GHOST / SHADOW / AGENT); best results
are saved to disk.

## 2. Controls

| Action | Keyboard / mouse | Gamepad |
|---|---|---|
| Move / look | WASD / mouse | left / right stick |
| Sprint (loud) | Left Shift (hold) | left thumb |
| Crouch (quiet, slow) | C or Left Ctrl (toggle) | right face (B) |
| Interact (grab item, enter/leave locker) | E | left face (X) |
| Throw distraction | Left mouse / G | right trigger |
| Pause | Esc / P | Start |

## 3. Systems and classes (C++ module `Stealth`, Blueprint subclasses for tuning)

| Class | Role |
|---|---|
| `AStealthCharacter` (from template `TP_ThirdPersonCharacter`) | walk / sprint / crouch speeds, footstep noise events (`UAISense_Hearing::ReportNoiseEvent`) + footstep SFX, visibility value 0..1, interaction, throwing, lockers, `IAISightTargetInterface` (multi-point line-of-sight, hidden in locker) |
| `AStealthPlayerController` | Enhanced Input contexts, look sensitivity, pause, creates HUD / menus |
| `AStealthGameMode` | level flow: objective state, checkpoints, caught → fade → respawn + guard reset, level timer, times-spotted counter, results + save |
| `AStealthMenuGameMode` | main-menu map: shows main menu with level select and settings |
| `UStealthGameInstance` | settings (master volume, mouse sensitivity, resolution, fullscreen), save/load, level table |
| `UStealthSaveGame` | settings + per-level best time / fewest spotted / best rating / completed |
| `AStealthGuard` | guard character (Manny, tinted), vision-cone component, patrol route ref, tuning (sight radius/angle, speeds) |
| `AStealthGuardAIController` | `UAIPerceptionComponent` (sight + hearing), suspicion meter, alert state machine, Blackboard + Behavior Tree |
| `UStealthVisionConeComponent` (`UProceduralMeshComponent`) | floor fan mesh, line-traced against walls, colour by alert state |
| `AStealthPatrolRoute` | waypoint list (edit widgets) + per-point wait, spline preview |
| `AStealthHidingSpot` | `Locker` (enter/leave with E, unseen unless watched entering), `Grass` (crouched: visibility ×0.2), `Shadow` (×0.45) |
| `AStealthObjectiveItem`, `AStealthExtractionZone`, `AStealthCheckpoint` | objective chain |
| `AStealthThrowable` | thrown bottle, loud noise on first impact |
| `AStealthHUD` + UMG widgets (built in C++) | HUD (visibility meter, noise meter, objective, timer, spotted, throwables, messages), detection indicators over guards, main menu, level select, settings, pause, results, caught overlay |

Tuning lives in Blueprint subclasses created by editor scripts (`BP_StealthCharacter`, `BP_Guard`, …)
so level scripts place Blueprint assets, not raw native classes.

### Visibility and noise

- Visibility `V` = 1.0 standing, ×0.6 crouched, ×1.15 sprinting, ×0.45 in a shadow zone, ×0.2 crouched in
  grass, 0 inside a locker. Shown on the HUD as the eye meter.
- Noise: footstep events every 0.55 s (walk, loudness 0.35, range 600 cm) / 0.33 s (sprint, 1.0, 1400 cm);
  crouch emits none. Throwable impact: loudness 1.0, range 1800 cm. Shown on the HUD as the noise meter.

### Guard AI

Perception: `UAISenseConfig_Sight` (radius 1600, lose 1900, peripheral half-angle 50°, all affiliations) +
`UAISenseConfig_Hearing` (range 1800). The controller converts raw perception into a **suspicion meter** 0..1:

`dS/dt = +rate × V × distanceFactor` while the player is in sight (rate ×3 inside 400 cm), `−0.25/s` when not.

State machine (`EStealthAlertState`, written to the Blackboard key `AlertState`):

```
Patrol --sees player (S>0) or hears noise--> Suspicious (investigate InvestigateLocation, "?" fills with S)
Suspicious --S reaches 1--> Alert (chase TargetActor, "!"; catch inside 110 cm → player caught)
Suspicious --S decays to 0 and investigation done--> Patrol
Alert --loses sight for 3 s--> Search (go to LastKnownLocation, visit 3 random nav points around it)
Search --sees player--> Alert ; --search done--> Patrol (return to nearest waypoint)
```

Behavior Tree (built in C++ at runtime by `StealthGuardBehavior.cpp`, Blackboard keys `AlertState`(enum),
`TargetActor`, `InvestigateLocation`, `LastKnownLocation`, `PatrolLocation`, `SearchLocation`, `PatrolWait`):

```
Selector
├─ [AlertState == Alert,   abort both]  Sequence: MoveTo(TargetActor, 60)
├─ [AlertState == Search,  abort both]  Sequence: FindSearchPoint → MoveTo(SearchLocation) → Wait(1.5)
├─ [AlertState == Suspicious, abort both] Sequence: Wait(0.6) → MoveTo(InvestigateLocation) → Wait(2.5)
└─ Sequence: NextPatrolPoint → MoveTo(PatrolLocation) → WaitBlackboardTime(PatrolWait)
```

Why runtime-built: Behavior Tree and StateTree graphs cannot be authored from UE Python (their editor graphs
are not scriptable), and hand-editing binary `.uasset` graphs is off-limits. Building the
`UBehaviorTree`/`UBlackboardData` objects in code keeps them real engine BT/BB objects (gameplay debugger
shows them) and makes every change a recorded code change.

Speeds: patrol 180, investigate 230, search 300, chase 480 (player: crouch 200, walk 330, sprint 600).

### Vision cones

Each guard has a procedural fan mesh (24 segments) at floor height; each ray is line-traced against the world
so cones stop at walls. Unlit translucent material `M_VisionCone` with colour parameter; white-ish on patrol,
yellow when suspicious, red when alert, orange when searching.

## 4. Levels

| # | Map | Setting | Guards | Hiding | Item → extraction |
|---|---|---|---|---|---|
| 0 | `MainMenu` | backdrop, camera | – | – | – |
| 1 | `L01_Warehouse` | indoor warehouse, shelving aisles, office | 3 (2 patrols, 1 loop) | 2 lockers, 3 shadow corners | ledger in the back office → loading dock |
| 2 | `L02_Courtyard` | courtyard at night, lamp posts, fountain, hedges | 4 (3 patrols, 1 sentry) | grass patches, shadow zones, 1 locker | relic in the gazebo → side gate |
| 3 | `L03_Office` | office floor, cubicles (low walls hide crouched player), server room | 5 | lockers, cubicle cover, dark corridor | keycard in server room → elevator |

Each level has a start checkpoint plus 1–2 mid checkpoints. Levels are built by editor scripts
(`Scripts/build_level_*.py`) from engine shapes and template `LevelPrototyping` meshes.

### AutoPlay scenarios (contract v1.3)

`-Scenario=<n>` opens heist n from its start checkpoint. `StealthGameInstance` supplies `StartScenario`, and `StealthGameMode` reports `ScenarioStarted(<display name>)`.

| n | Name | Start state | Win | Lose |
|---|---|---|---|---|
| 1 | Warehouse | `L01_Warehouse`, start vestibule SW, 3 bottles, no item | take the ledger (back office), reach the loading-dock extraction | `-MaxSeconds` runs out (a catch only sends you back to the last checkpoint and costs score) |
| 2 | Courtyard at Night | `L02_Courtyard`, gatehouse S, 3 bottles | take the relic (gazebo), reach the west side gate | as 1 |
| 3 | Office Floor | `L03_Office`, stairwell SE, 3 bottles | take the keycard (server room), reach the elevator | as 1 |

Bot status (2026-10-11): skill 1 wins scenario 1 on seeds 1–3 (103–132 s, 1–4 catches). Scenarios 2 and 3 are not yet tuned for the bot.

## 5. Assets and audio

Built here first: materials, synthesized WAVs and music, level layouts, the locomotion anim instance. Supplements:
UE 5.3 engine/template content (Manny/Quinn, LevelPrototyping), CC0 Poly Haven models/textures, and Fab packs
copied unchanged under `Content/<Pack>/` (first: **Stealth Locomotion Animation Set**, purchased, retargeted
to Manny into `Content/Stealth/Animations/Locomotion`). Every asset's source, licence, version and changes goes in
`assets.manifest.json` (`packs` + per-file sha256). SFX synthesized by `Scripts/synth_sfx.py` (footstep soft / hard, alert sting,
suspicious blip, pickup, extraction, caught, bottle impact, UI click, ambience hum).

## 6. Recording

- `workflow.jsonl` rows: `{schema, id, seq, time, actor:"agent", op, target, params, reason,
  reason_source:"agent_note", status:"observed", result, source{script, commit}}`, appended by
  `Scripts/wf.py` (CLI for shell operations; imported by editor scripts for editor operations).
  `result` is `ok` or `failed` (failed rows carry `params.error`). `source.commit` is the project HEAD at the time.
- Ops used: `project.create`, `repo.init`, `config.set`, `code.change`, `build.compile`, `asset.create`,
  `asset.import`, `property.set`, `blueprint.create`, `level.create`, `actor.add`, `level.save`, `pie.test`,
  `package.build`, `vcs.commit`.
- Git history of the game repo is the deliverable `git.log`.

## 7. Acceptance checklist

- [x] Main menu with level select (locked/unlocked + best stats), settings, quit
- [x] Settings: master volume, mouse sensitivity, resolution + fullscreen, persisted
- [x] Pause menu: resume, restart from checkpoint, settings, quit to menu
- [x] Walk / sprint / crouch with different speed and noise
- [x] Hiding: lockers, tall grass, shadow zones lower visibility
- [x] Guards: patrol routes, sight cone + hearing, suspicious → alert → search → patrol
- [x] "?" / "!" indicators over guards, vision cones on the floor
- [x] Objective chain: item → extraction; HUD objective text
- [x] Caught → restart at last checkpoint
- [x] Throwable distraction draws guards
- [x] 3 levels with different layouts
- [x] Per-level stats (time, times spotted) and rating saved to disk
- [x] HUD: visibility + noise meters, objective, timer
- [x] SFX: footsteps, alert sting, pickup, caught, UI
- [x] Packaged Win64 build

## 8. Status (2026-10-11 02:53)

Playable end to end: main menu → 3 levels → results, with saves. **Not called complete**: the user judged the first
(primitive-shape) art "really low taste"; a CC0 art pass followed (below), and art quality is the open item. Verified by an in-game test director
(`AStealthTestDirector`, `-StealthTest`), 11/11 checks passing on every level, and by rendered screenshots.

### Fab / animation / UI pass (2026-10-11, user direction: use the downloaded packs, UI in the game's style)

Commits: ad13940 (L1), 1d01aab (L3), 67c3972 (UI, L2, audio), ee08731 (guards, menu).

- **Player:** the thief is the Rogue Character Model. Its Manny-compatible skeleton (plus a cape chain) runs the native locomotion through skeleton remapping.
- **Levels:** dressing goes on top of unchanged gameplay volumes. Blockers keep their collision; the visuals are Fab meshes.
  - **L1:** the Modular Warehouse Interior shell has a roller door with an exit sign, steel pilasters, roof sheets with skylights, beams, pipes, lamps and fire gear. Industry Props Pack 6 supplies blue racks, crates, cartons, barrels, pallets and litter. DownTown Office furnishes the back office. The pack's one-sided checker wall panels were tried and dropped; the walls are CC0 concrete block.
  - **L2:** City Park supplies:
    - bush hedge rows and maples;
    - iron lamp posts, benches and bins;
    - a fountain with a statue;
    - a pergola over the relic;
    - tall and short grass, path leaves and ivy.
  - **L3:** DownTown Office supplies cubicle desks with monitors, keyboards, towers and clutter, a copier, a conference table, shelving, paintings and a clock.
  - **Menu diorama:** dressed with City Park and Industry Props.
- **New actors:**
  - `AStealthTileStrip`: instanced runs of one modular mesh.
  - `AStealthScatter`: jittered scatter of several meshes.
  - **Bug found via an unlit top-down shot and fixed:** a static child under a movable root never attached, so every instance rendered around the world origin.
- **Guards:** `UStealthGuardAnimInstance` uses MoCap Online clips retargeted to Manny:
  - relaxed idle;
  - power walk on patrol (180 cm/s);
  - jog when searching (300);
  - run when chasing (470);
  - a look-around walk while suspicious or searching.

  The anim instance now takes gait lists (speed, cycles, left-plant phase, blend-from). The player's numbers are unchanged.
- **UI:**
  - **Fonts and style:** OFL fonts (Barlow Condensed for display, Barlow for body, Share Tech Mono for numbers) with an ink and amber palette (`StealthUIStyle`).
  - **HUD:**
    - a dossier objective card;
    - segmented SEEN/NOISE meters with icons;
    - bottle icons, keycap controls and prompt;
    - an alert banner with an icon.
  - **Screens:** the menu is a dark slab with an amber edge and flat list buttons. The jobs list shows lock, check and target icons. Pause is restyled, and the results screen has a tilted rating stamp.
  - **Guard indicators:** these use icon masks.
  - **Icons:** drawn in code (`Scripts/make_ui_icons.py`, SDF), not sampled.
- **Audio:** Essential Footsteps (concrete walk and run), a Free UI click, and the SFX Essentials light-rain loop as night ambience. Stings and story audio stay synthesized.
- **Packs:** every pack is pruned to the packages it references (the library keeps the full pack) and recorded in `assets.manifest.json` with listing URL, licence, version, changes and per-file sha256.
- **Verified:** `-StealthTest` passes 12/12 on L1–L3 after each unit. The move test is unchanged. Rendered shots were taken of every level, the UI and the guards.
- **Still open:**
  - City Sample Crowds bodies for the guards (they are still the template mannequin);
  - the Free Sample anims for pickup and locker;
  - per-surface footsteps;
  - the L2 wall dressing (ivy unverified);
  - re-packaging.

### Movement rework (2026-10-11, after the user: "character movement sucks")

- **Animation:** `UStealthAnimInstance` (native, no Anim Blueprint graph). The proxy blends:
  - standing idle/walk/run (template);
  - sneak idle/slow/fast (Stealth Locomotion mocap, retargeted);
  - the fall loop.

  All gait cycles share one counter aligned on the left-foot plant, so cross-fades keep the feet in step. Play rate follows ground speed, using measured cycle speeds (`Scripts/measure_gait_v2.py`). Idle↔move, stand↔sneak and ground↔air fade over time. The root is locked, because the template walk and run carry root motion. This replaces the single-node crouch clips that popped on every switch.
- **Feel:**
  - Acceleration 2400, braking 2600, friction 8, turn rate 720°/s.
  - All applied in BeginPlay, so the Blueprint can't mask them.
  - Camera lag is capped at 60 cm.
  - The crouch capsule drop (36 cm) is eased instead of snapping the camera.
- **Verified:** `-StealthMoveTest` runs a scripted walk/sprint/stop/crouch/sneak/turn/stand sequence at a fixed 60 fps, with metrics and side-on shots (move4).

  | | Before | After |
  |---|---|---|
  | Largest per-frame bone jump | 50–170 cm | ≤21 cm |
  | Planted-foot skate, walk | | 109 cm/s at 322 cm/s |
  | Planted-foot skate, sneak | | 48 cm/s at 198 cm/s |

  `-StealthTest` passes 12/12 on L1–L3.
- **Next:**
  - start/stop/turn clips from the pack;
  - stride warping for the walk;
  - lean into turns;
  - wall-hug moves (the pack has them).

### What works

| Area | State |
|---|---|
| Player | walk 330 / sprint 600 (loud) / crouch 200 (silent); generated crouch idle + walk animations; jump; interact; bottle throw (3 per level) |
| Visibility | 0..1 from stance, shadow zones (×0.45), tall grass (×0.2 crouched), lockers (0); multi-bone line of sight (head/chest/hips) so 130 cm cover hides a crouched player only |
| Guards | AI Perception sight (1600 cm, 50° half-angle) + hearing (18 m); suspicion meter; Patrol → Suspicious → Alert → Search → Patrol; radio to nearby guards; catch at 1.15 m; guard who watched you enter a locker opens it |
| Behavior Tree | `UBehaviorTree` + `UBlackboardData` built in code (`StealthGuardBehavior.cpp`), engine MoveTo/Wait + custom alert-state decorator, guard-step and look tasks |
| Readability | floor vision cones traced against walls and coloured by state; "?" with fill bar / "!" over guards, clamped to screen edges; red guard uniforms |
| Objective | item → extraction; checkpoints; caught → 2.2 s → respawn at last checkpoint with guards reset (item put back if taken after it) |
| Stats | time, times spotted (one per alert episode), times caught; GHOST / SHADOW / AGENT rating; bests saved to `Saved/SaveGames/Ghostline.sav` |
| UI (UMG built in C++) | HUD (objective, timer, spotted/caught, visibility + noise meters, status, prompts, messages); main menu with live diorama, level select with locks and bests, settings (volume, mouse sensitivity, invert Y, resolution, window mode), how to play; pause (resume, restart checkpoint/level, settings, quit); results |
| Levels | `L01_Warehouse` (3 guards), `L02_Courtyard` night (4 guards with torches incl. sentry), `L03_Office` (5 guards, cubicles), `MainMenu` |
| Audio | 13 synthesized SFX (footsteps soft/hard, alert sting, suspicious blip, pickup, extract, caught, bottle, throw, checkpoint, UI click, locker, looping ambience) |
| Art (pass 2) | CC0 Poly Haven, user-approved download (33 models, 8 PBR texture sets, night HDRI, ~187 MB in `ArtSource/polyhaven`): world-aligned PBR surfaces (concrete, sheet metal, brick, cobblestone, grass, carpet, plaster), crate storage via `AStealthPropFill` (keeps cover volumes as sight blockers), caged lamps, street lamps, trees, benches, real desks/chairs/laptops/plants/fluorescent panels, ledger/relic/keycard as real objects |
| Assets | `assets.manifest.json`: 717 files, each Epic template/engine content, CC0 (with source URL) or generated here, with sha256 |
| Package | Win64 Shipping, 764 MB (`games/stealth/Packaged/Windows`), verified headless on all 3 levels (`-StealthLevel=N -StealthTest`) and by a rendered screenshot |

### Automated test (per level, `Scripts/run_game.sh ... -StealthTest`)

`setup` (guards, BT running, navmesh) · `patrol_moves` · `sight_alert` (suspicious at once, alert ≈1.07 s at 6.5 m) ·
`catch` (≈1.2 s) · `respawn_reset` · `hearing_investigate` (noise behind a guard → investigate → back to patrol) ·
`crouch_visibility` · `locker_hidden` · `low_cover` (130 cm wall hides crouched, standing is seen) · `item` ·
`extract_results_save`, plus `low_cover` and `throwable`: 12/12 PASS on L01, L02, L03 after the art pass.

### Problems hit and how they were solved (all recorded as failed rows in `workflow.jsonl`)

- **UE 5.3.2 + MSVC 14.44**: `ConcurrentLinearAllocator.h` fails on `__has_feature` because MSVC now ships
  `sanitizer/asan_interface.h`. Fix in both Target.cs files: `bOverrideBuildEnvironment = true;
  GlobalDefinitions.Add("PLATFORM_HAS_ASAN_INCLUDE=0");` (shared with the other sessions in the notes folder).
- **Empty saved navmesh**: re-saving a map in the headless editor stores a `RecastNavMesh-Default` actor with an
  empty navmesh, and guards stopped moving (caught by the test). The tune script now removes it; levels rely on
  runtime navmesh generation.
- `MaterialEditingLibrary.delete_all_material_expressions` asserts (`!IsRooted`) on loaded materials → patch
  materials by inserting nodes instead (`patch_materials_exposure.py`).
- Fixed exposure per level (EV 7.5 indoors, 2.5 at night) made unlit cones/glows vanish or blow out → emissive
  goes through `EyeAdaptationInverse`.
- Recorder fixes: Git Bash rewrote `/Game/...` arguments into Windows paths (one row has a mangled target; a
  `log.correction` row follows it) and `unreal.Name` was not JSON-serialisable (two rows written by hand right
  after the operation, marked with `performed_at`).
- Shared machine: UBT and UAT are machine-wide single-instance; packaging waits with `-WaitForUATMutex`.

### Known limits / what's left

- **Art is still the weak point.** Characters are the template mannequins (player = Quinn, guards = Manny tinted red);
  gazebo, fountain, server racks and cubicle partitions are textured boxes/cylinders; no decals, no foliage
  density, no props with animation. Next sources to consider (all need a download OK): CC0 rigged characters
  (Quaternius), ambientCG textures for fabric/metal, Poly Haven structures; Epic Starter Content (installed) for doors/windows.
- Vision cones are deliberately visible but still bright against the night level.

- Crouch animations are generated from the template idle / in-place walk by IK, so they are serviceable rather
  than authored; there is no crouch-to-stand transition (switch is instant).
- Behavior Tree is built in code, so it is not visible as a BT asset in the editor (it is visible in the
  gameplay debugger at runtime).
- Shadow zones are authored volumes, not computed from actual light levels.
- Recording covers editor/code/build operations made through scripts; there is no screen video or input log
  (Track B rig not used here).

### Stats

- `workflow.jsonl`: 1171 rows, 2026-10-11 00:57:24 → 02:53:04 (20 rows `result: failed`, each followed by its fix).
  Top ops: actor.add 659, property.set 156, asset.import 59, asset.create 52, code.change 48, asset.download 42.
- Git: 12 commits in `games/stealth` (agent identity, no personal data; leak scan of tracked text clean).
- Time: ~2 h of agent work (00:52 → 02:53), single Unreal process at a time, headless where possible.

## 9. Story bible (told through play, not text)

### Premise (one paragraph, never shown as one)

Two years ago the Lantern Street depot of **Morrow Freight** burned down. The night watchman, **Tomas Reyes**, died
inside. Morrow's cargo was declared lost and **Halden Mutual** paid the claim without a question. You play **Wren
Reyes**, Tomas's daughter, now a thief for hire. A fixer called **Mara** sends you jobs on a pager: steal one object a
night, deliver it, get paid. Each object looks like an ordinary heist target. Each one is a piece of the fire.
In the last level you break into Halden Mutual's own office and find your three jobs pinned to a whiteboard under
"ASSET RECOVERY: REYES": Mara works for Halden. You have been collecting the evidence so the people who covered up
your father's death can destroy it. You leave with the keycard to the archive, and this time you keep everything.

### How it reframes the mechanics

- **Why stealth**: Wren must not be seen because she is not supposed to exist on their cameras a second time.
- **Why guards**: Morrow and Halden pay private security to sit on exactly the places where the evidence is.
- **Why one item and an exit**: Mara's rule ("one object, no witnesses, out by the marked exit"). It is the rule
  of someone who wants the objects, not the truth, out of those rooms.
- **The ghost rating**: Wren's father was the man nobody saw; being a ghost is the family trade.

### Characters

| Who | Role | How the player meets them |
|---|---|---|
| Wren Reyes | player | never speaks; her pager line opens each level |
| Tomas Reyes | the watchman who died | memorial plaque at the dock (L1), his name in the ledger (L1), his photo on the whiteboard (L3) |
| Mara | the fixer, Halden's cleaner | only as a pager sender name; guards mention "Mara's courier" (L3) |
| Victor Halden | insurer, owner of the manor | the manor (L2), "Halden Mutual" crest on the urn and in the office (L3) |
| Morrow Freight | the shipper that staged the fire | warehouse signage, crates stencilled "MORROW", the ledger (L1) |
| The guards | hired security who half-know | barks |

### Beat per level (the only text the game shows per level is the pager line and one extraction line)

| Level | Pager line (start, < 15 words) | What the player steals and why it matters | Environmental story (optional, for players who look) | Extraction line (one line) |
|---|---|---|---|---|
| 1 Warehouse | `MARA: Morrow's back office. The ledger. Nothing else.` | Morrow's shipping ledger: it records the "burned" cargo leaving Lantern Street two days before the fire | memorial plaque "T. REYES, NIGHT WATCH, LANTERN ST." by the dock; scorched crates stencilled LANTERN ST.; a corkboard of manifests with one date circled | `The cargo that burned left two days early.` |
| 2 Courtyard | `MARA: Halden's garden. The brass urn in the gazebo.` | an engraved urn Halden keeps as a trophy: "FOR A QUIET CLAIM, MORROW FREIGHT" | party leftovers on benches, a banner "HALDEN MUTUAL, 50 YEARS OF TRUST", a gardener's shed with Morrow crates | `A gift, for a quiet claim.` |
| 3 Office | `MARA: Halden Mutual, server room. Bring me the archive key.` | the archive keycard | meeting room whiteboard: photos of the ledger and the urn, Wren's photo, "ASSET RECOVERY: REYES", "SHRED AFTER RECEIPT"; Mara's courier box on reception; shredder bags | `Mara never worked for me. I keep this one.` |

Level 3 recolours the first two: the ledger and the urn were not jobs, they were evidence being recovered.

### Guard barks (subtitled over the guard, short, two or three per guard per level, by state)

- L1 patrol: "Morrow wants that office locked till dawn." · "Smells like smoke in here. Always does." · "Old lot burned with a man inside, they say."
- L1 suspicious/search: "Who's back there?" · "Probably rats. Probably."
- L2 patrol: "Mister Halden's guests leave at midnight." · "Don't touch the urn. He talks to it." · "Insurance pays for all of this, you know."
- L2 alert: "Someone's in the garden!"
- L3 patrol: "Mara's courier came by again." · "Shred bins go out at six." · "They're watching the Reyes kid. Easy money."
- L3 alert / lost you: "Stop right there!" · "Lost them. Check the server room."
- any: caught → "Got you." · search ends → "Nothing. Back to rounds."

Barks are the plot in fragments; they never repeat within 20 s and only play near the player.

### Visual and audio motifs

- **The lantern**: warm amber light (Lantern Street) marks story objects (memorial, urn, keycard glow); the rest of
  each level is cool blue night.
- **Halden crest** (a shield with a key) on the urn, banner and office walls.
- **Music**: a three-note descending motif (D, B-flat, A) on a muted piano/synth pad; menu plays it slowly; each
  level's ambient bed hides it; the L3 extraction plays it in full, in a major key, once.
- **Pager**: a short two-tone beep and a one-line message at level start (the only "UI story").

### What the player learns where and how

| Fact | Where | How |
|---|---|---|
| a man died in a fire at Lantern Street | L1 dock | plaque, guard bark |
| Morrow staged the loss | L1 office | the ledger (extraction line), corkboard |
| Halden profited and knew | L2 | urn engraving, banner, bark |
| Wren is Tomas's daughter | L3 | whiteboard photo + name, guard bark "the Reyes kid" |
| Mara works for Halden | L3 | whiteboard, courier box, bark, extraction line |

### Implementation plan

Level dressing built by script (plaque, signage, whiteboard, crest as generated textures + meshes), barks as
subtitled lines with a synthesized radio-chatter sound (spoken voice pending a licensed TTS choice), pager line at
level start, one extraction line on the results screen, music motif synthesized; every asset and edit logged.

## 10. Fab requests (for the user to add in the Epic Games Launcher; 2026-10-11)

Researched by a subagent from Fab listing pages (prices = Personal tier, USD, 11 Oct 2026; Fab shows no download
sizes). All are Fab **Standard** licence unless noted: fine to ship in the game, **not** redistributable as source
to data buyers, so they will live under `Content/Fab/<Pack>/` and be listed in `assets.manifest.json`.
"Owned" = already in the user's Fab library. Everything listed supports UE 5.3 (packs made for older versions open in 5.3).

| # | Category | Listing | URL | Price | UE | Replaces / adds |
|---|---|---|---|---|---|---|
| 1 | Warehouse (L1) | Factory Environment Collection | https://www.fab.com/listings/2ee66462-8c2b-4303-892c-83f7fc0d9b3e | Free (owned) | 4.20–5.6 | storage, office and changing-room modules: walls, racking, doors for L1 |
| 2 | Warehouse props | Industry Props Pack 6 | https://www.fab.com/listings/b5603e44-e1b0-4346-9c3d-04887aa9f87d | Free (owned) | 4.18–5.7 | crates, pallets, industrial clutter (replaces CC0 crate stacks) |
| 3 | Courtyard (L2) | City Park Environment Collection | https://www.fab.com/listings/11cc2abb-126c-4452-9fe4-6f2381d96544 | Free (owned) | 4.24–5.7 | 524 park meshes: paths, benches, lamps, trees, plants |
| 4 | Courtyard walls | Modular Courtyard 1.0 | https://www.fab.com/listings/ecd3dc8a-5888-4421-91b5-a18390ed4828 | Free (owned) | 4.27–5.4 | modular walled-yard pieces for the manor perimeter and gatehouse |
| 5 | Courtyard trees | European Black Alder (Megascans) | https://www.fab.com/listings/9de7ce19-5813-42d2-a5f0-5e6447006f72 | Free (owned) | 4.25–5.6 | hero trees (replaces the CC0 island tree) |
| 6 | Tall grass | temperate Vegetation: optimized Grass Library | https://www.fab.com/listings/8b68642e-35f4-438e-82b4-799fc2228303 | Free (owned) | 4.19–5.4 | tall grass for the hiding patches |
| 7 | Office (L3) | Big Office | https://www.fab.com/listings/b2dee859-c670-4d95-871b-4bfd54d57fd9 | $34.99 (sale) | 4.19–5.7 | 18 office spaces incl. workstations, manager rooms, security room |
| 8 | Server room (L3) | Server Room Kit | https://www.fab.com/listings/34f4694a-555d-42f3-92d3-17171b2d90bb | $19.99 | 4.20–5.4 | server racks and room (replaces textured boxes) |
| 9 | Player character | Stranger Man | https://www.fab.com/listings/0e6a78a9-90d1-4b6d-ac8a-89f388fd790f | $29.99 | 5.0–5.8 | hooded thief on the UE5 skeleton (replaces Quinn) |
| 10 | Guard character | Police Character / NPC | https://www.fab.com/listings/879f876d-0c63-4a23-8e86-7f12cbce874c | $19.99 | 4.22–5.8 | uniformed guard, recolourable (replaces tinted Manny) |
| 11 | Crouch / patrol anims | MoCap Online Free Animation Pack | https://www.fab.com/listings/64c53af0-dcb7-4483-9d65-5cbc84bd9a93 | Free (owned) | 4.10–5.6 | crouch idle/walk, patrol look-around (UE4 skeleton, retarget) |
| 12 | Sneak anims | Free Animation Library | https://www.fab.com/listings/481ef75b-892b-424f-a213-f1cc058c9c19 | Free (Personal) | 5.1–5.8 | 9 crouch anims, cover, doors |
| 13 | Guard flashlight anims | Flashlight Set | https://www.fab.com/listings/efdc3a60-796c-4305-9205-8fc7bcfe489a | $9.99 | 5.0–5.7 | 88 flashlight anims on the UE5 skeleton (guards in L2) |
| 14 | Player sneak locomotion | Stealth Locomotion Animation Set | https://www.fab.com/listings/5de627fd-5c59-431d-b8e9-3009f8fc8605 | $29.99 | 4.19–5.8 | 62 hand-keyed sneak/wall/peek anims (replaces generated crouch) |
| 15 | VFX dust | Niagara Dust | https://www.fab.com/listings/79010b57-8646-4ed9-88b8-930d993bd316 | $1.99 | 5.3–5.8 | dust motes in lamp and torch beams |
| 16 | VFX flashlight | Flashlights Pack | https://www.fab.com/listings/49d57ea0-97cf-4e25-9646-28b8e0364375 | $12.99 | 4.25–5.8 | torch models, beam patterns, lens flare |
| 17 | VFX fountain | Water Fountain | https://www.fab.com/listings/ca1ca322-d262-4473-ada4-cc7f18dd4a74 | $14.99 | 4.16–5.8 | fountain with Niagara jets (replaces cylinder fountain) |
| 18 | Water material | Water Materials | https://www.fab.com/listings/063155ea-d9d2-4f29-b09f-33270b0bc861 | Free (CC BY 4.0, credit) | 4.13–5.8 | fountain basin water |
| 19 | UI | UI Material Lab (Epic) | https://www.fab.com/listings/69680f34-e5d2-44e6-b023-f054bbf629eb | Free | 5.1–5.5 | animated UI materials for detection meters and HUD |
| 20 | Footsteps | Essential Footsteps SFX | https://www.fab.com/listings/d8833d76-3270-41d5-8fd0-efeae4057750 | Free (Personal) | 4.27–5.8 | 272 footsteps: concrete, gravel, metal, wood |
| 21 | Foley | Small Sound Kit | https://www.fab.com/listings/7191b22b-b183-4d21-8beb-cb29f641f333 | Free | 4.20–5.8 | doors, lockers, cloth, wind/rain |
| 22 | Ambience | Essential Ambience SFX | https://www.fab.com/listings/c4e9f60e-f1c1-433c-8b1b-fb5867da0d64 | Free (Personal) | 4.27–5.8 | night garden and interior room tones |
| 23 | Music | Ultimate Stealth Music Pack | https://www.fab.com/listings/91c2359a-b293-48f8-95bc-5af7f9616c9c | $4.99 | 5.3 | 10 tense stealth tracks (alongside our synthesized story motif) |

Paid total if all are taken: about $180 (Personal tier). Highest impact first: 9, 10 (characters), 7, 8 (office),
1–6 (free environments), 14, 13 (animations). Not 5.3-compatible and skipped: Game Animation Sample (5.4+),
Quixel "Warehouse" level, Megaplants, Hebe Fountain, Modular Security Guard (5.6+), the 5.8-only stealth stings.
Unverified: which skeleton #10 uses; whether #3 has a fountain/gazebo; #4 description is Russian only.
Open question: spoken guard barks need a voice source we are licensed to ship (e.g. a recorded voice pack or a TTS
voice with a commercial licence); until then barks are subtitles with synthesized radio chatter.

# Siege Catapult (Track B game #1)

A small physics game built in Unreal Engine 5.3 by an agent (Claude), recorded as it is made
(`workflow.jsonl`, schema `superposition.ue-workflow/v0`). Part of the four-game Track B batch
(tower defense, siege catapult, stealth, rally racer); see [../plan.md](../plan.md) "Track B".

- Project: `%GF_ROOT%\games\siege-catapult` (`SiegeCatapult.uproject`, its own git repo with LFS)
- Engine: UE 5.3 (`C:\Program Files\Epic Games\UE_5.3`), Win64
- Builder: agent; every row is `actor: agent`, `reason_source: agent_note`, `status: observed`

## Game

The player aims a catapult on a hill (yaw, pitch, power charge, with a trajectory preview arc that includes
wind) and throws projectiles at a castle. Each level has one or more **kings** (target pieces) standing on
platforms inside the castle. A level is won when every king is destroyed; it is lost when ammo runs out and the
last shot has settled with kings still standing. Fewer shots → more stars (1–3), saved to disk.

### Controls

| Input | Action |
|---|---|
| Mouse X / A, D | yaw |
| Mouse Y / W, S | pitch |
| Hold LMB / Space | charge power (release to fire) |
| RMB / Space while in flight | split the split-shot |
| 1 / 2 / 3, mouse wheel | ammo type |
| R | retry level |
| C | skip follow camera back to the catapult |
| Esc / P | pause |

### Ammo

| Type | Behaviour | Tuning (data asset `DA_Ammo_*`) |
|---|---|---|
| Stone | heavy ball, large impact impulse, breaks GC clusters by collision | mass 400 kg, radius 30 cm |
| Explosive | lighter keg, explodes on first impact: radial impulse on bodies, strain + radial velocity field on Geometry Collections | radius 600 cm, strain 500k |
| Split shot | splits into 3 stones at the player's click (or automatically 1.2 s after apex) | 3 × 120 kg, 8° spread |

Each level sets its own ammo counts and its par values (shots for 3 and 2 stars).

### Levels

| # | Name | Castle | Kings | Ammo (stone/explosive/split) | Wind |
|---|---|---|---|---|---|
| 1 | Training Yard | one wooden tower + one wall | 1 | 5/0/0 | none |
| 2 | Twin Towers | two stone towers on a ledge | 2 | 4/2/0 | none |
| 3 | The Gatehouse | wall + gatehouse, king behind wall | 2 | 4/2/2 | none |
| 4 | Windy Ridge | towers on raised platforms | 3 | 3/2/2 | light, cross |
| 5 | Keep | thick double wall, king inside keep | 3 | 3/3/2 | medium, head |
| 6 | The Citadel | three-tier citadel, kings on each tier | 4 | 3/3/3 | strong, gusting |

## Story bible

**Rule: show, don't tell.** No cutscenes, no text walls. At most one short line per level (a carved inscription,
under 15 words), one optional discovery line on the results screen, and one payoff line after the last level.
Everything else is in the castles, the banners, the light and the music.

### Premise (never stated outright)

You are an old siege engineer. Thirty years ago, at the end of the long war, the old king had you build six castles
along the valley. They were never meant for soldiers: each hides a sealed room where the valley's families could
wait out a raid. The king is long dead. A Regent rules now, and his order is simple: *every crowned figure in the
valley comes down.* The villagers have been setting crowned straw figures on the walls of "your" castles, so the
Regent sends the one man who knows exactly where those walls are weakest: you, with the catapult you also built.

The player is told none of this. They learn it from:
- **Your mark.** A mason's mark (a compass over an arch) is carved on the catapult's plaque, on a keystone in every
  castle, on the old blue banners, and on the chest of every crowned figure. Early on it reads as decoration.
- **The two banners.** Blue banners with your mark fly on the castles; red banners with a black tower (the Regent)
  stand beside your catapult. You are on the red side, demolishing the blue.
- **The sealed rooms.** Each castle hides a room that only opens when you break the right wall. What's inside
  grows more personal level by level. Discovering a room rings a low chime; the results screen then adds one line.
- **The inscriptions.** Each level opens with the line carved over that castle's gate, in your voice from 30 years ago.
- **The valley.** Spring morning → summer noon → late-summer haze → autumn gale → winter dusk → first snow at dawn.
  The banners on the castles get older and more torn; the red ones by the catapult multiply.

### Beat per level

| # | Castle | Inscription (level intro) | Sealed room (revealed when its wall breaks) | Discovery line (results) | Light / weather | Banners |
|---|---|---|---|---|---|---|
| 1 | Training Yard | "My first tower. Built in the spring the war ended." | none: just your keystone with the mark (teaches the mark) | — | spring morning, clear | blue, new |
| 2 | Twin Towers | "Two towers, so each village could see the other's fire." | between the towers: two lanterns, still oiled | "Someone kept the lanterns filled." | summer noon | blue |
| 3 | The Gatehouse | "No gate here was ever closed against a stranger." | behind the long wall: cots, a cold hearth, a child's wooden horse | "Twelve cots. The hearth is still warm." | late summer haze | blue, faded |
| 4 | Windy Ridge | "Raised above the floods, as the old king asked." | on the ridge: stores, ropes, a ladder down the back | "Supplies for a winter. Fresh." | autumn gale, gusting | blue, torn; first red by you |
| 5 | The Keep | "Walls thick enough to sleep behind." | inside the keep: a long table set for many | "Bread on the table. They left in a hurry." | winter dusk, low orange sun | blue, burnt; more red |
| 6 | The Citadel | "For the builder, who kept us safe." | top tier: your old drafting table, your plans of all six castles, a carved likeness of you, crowned | "They crowned the one who built their walls." | first snow, cold dawn | one blue banner left |

**Payoff.** The level 6 inscription is addressed to *the builder*; the sealed room holds your own drawings and a
crowned likeness of you. The crowned figures were never kings. They were you: the villagers crowned the man who
built their shelters, and the Regent sent that same man to pull them down. After level 6 the main menu's line changes
to "They crowned the one who built their walls," and the diorama shows the menu castle in snow with its figure fallen.

### Motifs

- **Visual:** the mason's mark; blue (refuge, old crown) vs red (Regent); lanterns as signs of life; seasons.
- **Audio:** a plucked-string theme in D minor (synthesized). Every level plays a variation that gets sparser and
  colder; level 6's win plays the theme for the first time in D major. Opening a sealed room rings a low bell.
- **Mechanic reframed:** stars reward fewer shots, so the "best" play is the cleanest demolition, exactly what the
  Regent wants. The discoveries reward the opposite: breaking the walls that hide the rooms.

### What the player learns where

| Where | What |
|---|---|
| Catapult plaque, level 1 keystone | the mark exists; it's on your machine *and* their castle |
| Banners | you serve red; the castles belong to blue |
| Inscriptions | you built these, for people not soldiers |
| Sealed rooms (optional) | people still live here, right now |
| Kings' chests (look closely) | the crowned figures wear your mark |
| Level 6 inscription + room, menu line | the figures are you |

### Story: implemented (2026-10-11 ~04:00–05:00)

| Element | Where in the game |
|---|---|
| Inscriptions | `ASCLevelSettings.IntroText` → level banner, in quotes |
| Mason's mark | `T_SC_MasonMark`; catapult plaque (`SM_SC_MarkPlaque`), keystone in every castle (`SM_SC_Keystone`), blue banners, gold mark on every crowned figure's chest (`SM_SC_King` slot 5), results screen, level select |
| Banners | `SM_SC_Banner` + `MI_SC_BannerBlue/Torn/Red`; blue on the castle side aging per level, red beside the catapult: 1,1,1,2,3,4 |
| Sealed rooms | `GC_Chamber` (brick hut Geometry Collection) + `ASCHiddenRoom` (shadowed warm light that spills out once the walls break; opened by nearby breaks/impacts; bell; saved per level; `room_found` telemetry). Contents: lanterns (L2), cots + warm hearth + rocking horse (L3), winter stores + ladder (L4), feast table in the keep (L5), drafting table with the plans + stone effigy of the builder, crowned (L6) |
| Discovery lines | `DA_GameConfig.RoomLines` → results screen under the mark, only if the room was opened; the ending line is shown on the last win either way |
| Seasons | per-level sun angle/colour/fog + ground/foliage palettes (`make_levels_v2.py` SEASONS): spring morning → summer noon → haze → autumn gale → winter dusk → first snow at dawn |
| Older sieges | boards propped over old breaches in levels 4–6 |
| Music | `Scripts/gen_music.py`: D-minor plucked theme, one variation per level (sparser/colder), menu theme, D-major finale on the last win (`mus_final_win`), room bell; Music volume slider |
| Payoff | after the last castle: menu line "They crowned the one who built their walls." and the diorama's crowned figure lies fallen |

### Built vs sampled (what the player sees), after the Fab pass (2026-10-11 ~05:30–07:35)

User direction (relayed): Fab store assets required for a premium look; use the animation packs; medieval UI with no plain
text. What the player sees now:

| Element | Source | How it got in |
|---|---|---|
| Castle walls, towers, keep, piers, palisade | Medieval Castle Modular Vol 1 (Fab, bought) | kit modules fitted into the old piece boxes and Voronoi-fractured (`make_castle_pieces_v4.py`, C++ `BuildFracturedGeometryCollection` via PlanarCut); same asset paths, sizes and tuning, so levels/kings unchanged |
| Blocks, platforms, cap slabs, fracture faces | kit textures (Stone_Wall/Floor/Wood_01) | `M_SC_KitSurface` (RMA), our instances re-parented (`make_kit_surfaces.py`) |
| Trees, ferns, rocks, grass, plants, mountains | kit Real_Landscape set | `make_dressing_v2.py`: generated firs/bushes/boulders/sphere hills swapped, grass + plant HISM scatter |
| Catapult | Animated Siege Weapons (Fab, bought) | skeletal mesh + shot (x1.8) / reload / loaded anims; ball on the bucket bone; release point moved to the bucket at the top of the swing |
| Crowned figures | "Medieval King - Game Ready", Adam Richard, CC BY 4.0 | FBX + PBR textures (2K cap, OpenGL normals flipped); IK rigs + retargeter; MC Sample mocap (idle look-around, grab-head / stomp / point reactions near breaks, knockdown); ragdoll on fall; crown on the head bone |
| Effects | Realistic Starter VFX Pack Vol 2 | brick-hit, wood-splinter, building-dust (breaks), big explosion (keg), dust puff (king down) |
| UI | 4K Full Fantasy GUI (Honeti, bought) + Cinzel / IM Fell English (OFL) | every text in kit fonts with ink outline; stone dialog frames, leather strips, gilded buttons, icon ammo slots, star/crown/wind/shot icons, textured power bar/sliders/checkbox, arrow steppers, credits screen |
| Ground | Poly Haven CC0 scans (earlier pass) | unchanged |
| Music, SFX, story textures, banners, keystones, sealed rooms | built by this project's scripts | unchanged |

Credits screen + `Docs/ThirdPartyNotices.md` carry the CC BY attribution. Not used: Mangonel, free catapult, Megascans
castle wall FBX, item-destruction Niagara systems (copied, not wired), grass library pack (kit grass used instead).

### AutoPlay scenarios (contract v1.3, migrated 2026-10-11 15:44)

Scenario N = level N, started directly through `StartScenario` (no menu). Every scenario starts with the catapult at
its pad, full ammo for that level and all crowned figures standing; it is **won** when every figure is down and
**lost** when the ammunition is spent with figures still standing (after the last shot settles).

| # | Name | Start state (ammo stone/keg/split, kings, wind) |
|---|---|---|
| 1 | Training Yard | 5/0/0, 1 king on a small tower behind a palisade, calm |
| 2 | Twin Towers | 4/2/0, 2 kings on two stone towers on a ledge, calm |
| 3 | The Gatehouse | 4/2/2, 2 kings behind a wall + gatehouse, calm |
| 4 | Windy Ridge | 3/2/2, 3 kings on towers on raised platforms, light cross wind (gusting) |
| 5 | The Keep | 3/3/2, 3 kings, one inside the keep, medium head wind |
| 6 | The Citadel | 3/3/3, 4 kings on three tiers, strong gusting wind |

Migration: drop-in re-copied (ContractVersion 3), `StartScenario` / `ScenarioStarted` (display name), DefaultEngine.ini
`bAllowHighDPIInGameMode=True` (no `bUseLoggingInShipping`) and `r.RDG.AsyncCompute=0` against the first-frame GPU hang
(Lumen screen-probe gather on async compute vs VSM init, diagnosed by tower-defense; we saw it at level 3/5 boots).
Hand test scenario 1 off-screen: validate-run PASS, drop-in version 3.

#### Earlier (v1.1)

- Drop-in `AutoPlaySubsystem.h/.cpp` unchanged in `Source/SiegeCatapult/AutoPlay/`; `StartLevel` opens level N
  (1-based) directly; `LevelStarted` + bot on level start; `FinishRun(win|lose, score, {stars, shots, kings_left,
  kings_total, ammo_left})`.
- Bot (`USCBotComponent`): plans with the aiming simulation, then acts only through `Inject`: injected mouse deltas
  to aim (`MouseX`/`MouseY`), `One/Two/Three` for ammo, holds `LeftMouseButton` until the power bar reaches the plan
  and releases to fire, `RightMouseButton` to split near the target.
- **Skill:** reaction/thinking time 3.0 s (0) → 0.6 s (1); aim noise σ 4° → 0.3° on yaw and pitch; power noise
  σ 0.08 → 0.01; search grid coarse below 0.5 (no refinement); below 0.4 it picks a random standing king; below 0.3
  it never switches to explosives after a miss; mouse speed 4 → 12° per frame.
- Score: 1000 per king; on a win + 500 per star + 100 per unused ammo.
- Telemetry: `shot_fired`, `split`, `impact`, `shot_settled`, `king_destroyed`, `ammo_changed`, `score`,
  `room_found`, `state` at 10 Hz (location, rotation, yaw, pitch, power, ammo counts, selected ammo, kings left,
  round state, wind).
- Hand tests (`Scripts/autoplay_test.sh`, validate-run PASS): L1 skill 1 (1 shot, 3★), L1 skill 0 (5 shots, 1★),
  L2–L6 at skill 0.5–1. Two level-3 runs died at engine boot with a D3D12 GPU page fault (machine shared by 8+ UE
  sessions); the retry passed.

## Systems and classes (C++ module `SiegeCatapult`, editor module `SiegeCatapultEditor`)

| Class | Role |
|---|---|
| `ASCCatapultPawn` | catapult built from engine shapes (base, wheels, arm, cup); yaw/pitch/power input (Enhanced Input), arm swing animation, spawns projectiles, trajectory preview (instanced dots from `USCTrajectory`, which integrates gravity + wind with the same step the projectile uses) |
| `ASCProjectile` (+ `Stone`, `Explosive`, `Split`) | physics sphere, wind force each tick, impact handling, follow-camera hook, SFX |
| `USCAmmoData` (PrimaryDataAsset) | per-ammo tuning: class, mass, radius, material, explosion values, icon colour |
| `ASCKing` | target piece: physics body on a platform; destroyed when it falls 150 cm below its start, leaves its platform, or takes an impulse over threshold ("broken") |
| `ASCBlock` | simple physics block (wood/stone) for loose castle parts |
| `ASCLevelSettings` | placed once per map: ammo counts, par shots, wind (base, gust amplitude/period), level index |
| `ASCGameMode` | rules: counts kings, shots, ammo; win/lose; star rating; retry; slow-motion on impact |
| `ASCPlayerController` | input mapping context, pause, UI ownership, follow-camera blending |
| `ASCFollowCamera` | spring-arm camera that follows the live projectile, then returns to the catapult |
| `USCGameInstance` | level list, save game access, settings apply (volume via sound mix, sensitivity) |
| `USCSaveGame` | stars and best shots per level, settings (volume, sensitivity) |
| UI (`USCHudWidget`, `USCMainMenuWidget`, `USCPauseWidget`, `USCSettingsWidget`, `USCResultWidget`) | UMG widgets whose trees are built in C++ (no binary widget layout to hand-edit) |
| `USCEditorBuildLibrary` (editor) | Python-callable: builds Geometry Collection assets from engine shapes (brick stacks + Voronoi fracture) |

Design choices:
- Widget trees in C++ rather than Widget Blueprints: Widget Blueprint graphs cannot be authored reliably from
  Python in 5.3; code is reviewable in git.
- Editor work runs as Python scripts in `Scripts/` (headless where possible). Each script appends its own
  `workflow.jsonl` rows at the moment it performs each operation, via `Scripts/wflog.py`.
- Code edits by the agent are logged with `Scripts/wf.py` (same module) right when the file is written.

### Chaos setup

- Castle walls and towers are Geometry Collection assets built from `/Engine/BasicShapes/Cube` and `Cylinder`
  (brick courses, staggered), clustered one level, each brick optionally Voronoi-fractured into a few pieces.
- Damage thresholds tuned so a stone at full power breaks a cluster, a half-power stone only dents it.
- Performance: ≤ ~400 rigid bodies per level, sleep thresholds raised, broken debris removed after it sleeps
  (`Remove on Sleep` / max lifetime), collision type implicit boxes for bricks, no per-poly collision.
- Physics substepping on for stable stacks; `p.Chaos` defaults otherwise.

### Audio and art

- SFX synthesized by `Scripts/gen_sfx.py` (launch whoosh, stone impact, explosion, crumble, UI click, win, lose),
  16-bit WAV, imported as SoundWaves under a `SC_Master` sound class (volume slider drives a sound mix).
- Art: Fab packs + CC BY king + Poly Haven scans + project-generated story assets (see "Built vs sampled"). Every
  asset or pack is listed in `assets.manifest.json` with source and licence.

## Recording

`workflow.jsonl` rows: `{schema, id, seq, time, actor, op, target, params, reason, reason_source, status,
source{script, commit}}`. `time` is local ISO 8601 with ms; `source.commit` is the git HEAD at the moment of the
operation (the commit the operation was applied on top of). Failed operations get their own row with
`params.error`. Rows are never edited or reordered after being written.

## Acceptance checklist (playtest pass 2026-10-11 ~03:00)

How each item was checked: **auto** = autopilot run (`-sctest`, logged as a `pie.test` row), **shot** = rendered
screenshot inspected, **input** = `-scinput` run injecting real key/mouse events through Enhanced Input,
**code** = by reading the code only (not exercised).

- [x] Main menu with level select (stars + best shots shown, locked until previous level cleared), settings, quit
  — shot (`-sctour`); quit button: code
- [x] Settings: master/effects/ambience volume, mouse sensitivity, invert Y, resolution, window mode; saved to
  `SiegeCatapult.sav` / `GameUserSettings.ini` — shot; applying a resolution change: code only
- [x] Pause menu (resume, retry, settings, main menu) — shot + input (P pauses)
- [x] Catapult aiming (yaw, pitch, hold-to-charge power) with trajectory preview incl. wind; preview shortens from
  100 % (level 1) to 40 % (level 6) of the arc — input (mouse 100 px → 7° yaw; Space hold → 54 % after 0.9 s) + shot
- [x] 3 ammo types (stone, explosive keg, split shot), limited per level, switchable (1/2/3, wheel) — input + auto
- [x] Geometry Collection castle pieces break (a stone breaks ~160 pieces off level 2's front); loose blocks topple;
  nothing breaks at load (all 6 levels, idle runs) — auto + shot
- [x] Kings destroyed when knocked off / toppled / broken / blasted; win when all down; lose when out of ammo — auto
  (both outcomes seen)
- [x] 1–3 star rating by shots vs par, saved to disk, shown in level select — auto + shot
- [x] Follow camera + slow motion on impact; retry (R) — shot + input
- [x] HUD: ammo per type, shots + par, kings standing, wind arrow + strength, power bar, angle — shot
- [x] 6 levels, increasing difficulty, wind (gusting) in 4–6 — auto (all won by the solver: 1/2/2/1–4/3/6 shots)
- [~] SFX: launch, impacts (stone/wood), explosion, crumble, king down, split, charge, UI click, win/lose, wind loop —
  wired in code and the assets exist; **not listened to** (all automated runs use `-nosound`)
- [x] Packaged Win64 build — `Scripts/package.sh` → `Packaged/Windows/SiegeCatapult.exe` (Shipping, 488 MB,
  git-ignored). Smoke test: packaged exe, menu → level 6 through the level-select path (`-sclevel=6`), autopilot won
  with 3 stars; screenshots inspected. (Shipping ignores a map on the command line, hence `-sclevel`.)

## Status

**Fab pass (2026-10-11 07:35).** All visible art is now Fab / CC BY / CC0 content (castle kit fractured, animated
catapult, mocap-animated kings with ragdoll falls, kit dressing, particle effects, kit UI with period fonts). AutoPlay L3
PASS after the swap; all six levels still won by the autopilot in screenshot runs (L1 1 shot, L3 2, L5 3, L6 5).
Commits b8276d9, 0c82a66, a8d444d. Packaged Win64 Shipping 912 MB (was 559), smoke test menu -> L3 won. Names scrubbed from the repo (new rows use schema `ue-workflow/v0`; the AutoPlay
drop-in keeps its strings until the neutral v1.2 arrives).

**Done (2026-10-11, 03:07).** Playable end to end, in the editor build and as a packaged Win64 Shipping build.

Stats: `workflow.jsonl` 4,626 observed rows (38 op kinds, 00:56 → 03:07, 2.2 h wall clock): 3,086 `actor.add`
(levels were rebuilt ~6 times while tuning), 297 `property.set`, 65 `pie.test` playtests, 41 headless editor runs
(5 failed, each failure logged), 23 compiles (6 failed, logged), 53 `code.change`. 11 commits in the game repo.
140 assets in `assets.manifest.json` (135 generated, 5 engine basic shapes). Content 26 MB.

Before this becomes a vendor-style package: `workflow.jsonl` has 2 rows with absolute user paths (build error
text) and git authorship is the machine's git user; run the anonymization/leak scan from AGENTS.md first.

What works: everything in the checklist above. Art (after the user's "this art is ass" feedback): all meshes and
textures are generated by scripts (Geometry Scripting meshes: irregular brick variants, planks, crates, cap slabs,
modelled king and crown, detailed catapult frame/arm, rock/keg/split-shot projectiles, fir trees, bushes,
boulders, banners; procedural tiling textures with normal maps). Only `/Engine/BasicShapes` remain as engine content
(physics proxies, preview dots).

Known gaps / left to do:
- Nobody has listened to the audio, and a human hasn't played it yet (all play was by the autopilot plus injected
  input). The par values match perfect aim; a human may find levels 4–6 harder than the stars suggest.
- Frame-time spikes of 60–160 ms (headless CPU) when a big structure breaks; average 1.3–2.2 ms headless, ~8 ms
  rendered at 1280×720 on this PC (shared with three other sessions).
- Two break events fire at load in some towers with engine-cube bricks; with the generated bricks + light density
  there are none, but the root cause (`t≈0.2 s`, bottom-front bricks) was never fully explained.
- Art is still procedural/low-poly: no animation on the king, flat cloth banners, no particle FX (the explosion is
  an emissive sphere + light, no dust). CC0 packs (Kenney, Quaternius) would raise it further; downloading them
  needs the user's OK.
- The dev-only `Gallery` map is in the project but not in the cook list.

### Log

- 2026-10-11 00:56: design written; project + recorder created. MSVC still installing, so first came project
  setup, generated materials, synthesized SFX (12) and Enhanced Input assets, all via headless Python.
- 01:20: MSVC 14.44 + NetFx SDK present → C++ modules added (needed `PLATFORM_HAS_ASAN_INCLUDE=0`, found by the
  rally-racer session). First compile had 4 errors, second passed.
- 01:23–01:28: data assets, Blueprint subclasses, 7 Geometry Collection pieces (built by a C++ editor library
  from engine cubes), level builder.
- 01:31: autopilot harness (`-sctest -scshots -sctour -scseq -scquit`) + `Scripts/playtest.sh` logging `pie.test`
  rows. Level 1 won by the autopilot in one shot.
- Bugs found by looking at screenshots: every material fell back to the default material
  (`PreSkinnedPosition` is vertex-shader-only → SM6 compile failure, invisible in -nullrhi runs); towers collapsed on
  their own at start (overlapping tower bricks + ground discs 1.5 cm above z=0); GC break events never fired
  (`bNotifyBreaks` must be set before the physics proxy exists, plus solver `bGenerateBreakData`).
- 01:43: blocked ~10 min on "Live Coding is active" from another session's `-game` run without `-unattended`
  (engine-wide UBT check); note left in the shared notes folder. Later bypassed with `-NoHotReloadFromIDE`.
- 02:00: per-level preview length, autotest save slot; all six levels won by the autopilot.
- 02:05: `-scinput` test drove the real bindings; found mouse aim 12× too slow (engine's 0.07 axis sensitivity
  already applied) and fixed it. Anchoring stone ground courses (A/B) made towers nearly indestructible → reverted.
- 02:16: user: "we need more detailed models btw, this art is ass" → art pass: generated textures, masters, 18
  Geometry Scripting meshes, C++ visuals over physics proxies.
- 02:36–02:46: the art pass exposed castle instability (towers/keep cracking at load). A/B with engine cubes showed it
  wasn't the meshes: at 2000 kg/m³ the structures' self-weight impulse exceeded the damage threshold whenever they
  woke. Fixed with 150 kg/m³ stone + higher thresholds + kings/blocks starting asleep; destruction from hits kept.
- 05:30–07:35 Fab pass (user: Fab assets required, animation packs, medieval UI with no plain text): packs copied
  unchanged; C++ for skeletal catapult/kings, FX, kit UI; king imported + retargeted; castle rebuilt from the kit.
  Bugs found in screenshots and fixed: king materials fell back to default twice (sampler defaults, then Linear
  Grayscale for masks); crown 100x too big (the Blender rig's bones carry a x100 scale: crown now seated in component
  space); king faced away (yaw); banner overflowed then wrapped per word; piers rendered as lines (L-trim module);
  fractured pieces lost every module but the first (collapsing the module level dropped module transforms: now
  root > module > chunk); menu diorama hidden behind the panel by the bigger catapult. Validator copy lacked
  `common.ps1` → one false FAIL, invalidated and re-validated (PASS).


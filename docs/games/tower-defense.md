# Game #3: Tower Defense (agent-built, UE 5.3)

Project: `%GF_ROOT%\games\tower-defense` (own git repo, git-lfs for `*.uasset *.umap`).
Recording: `workflow.jsonl` at the project root, schema `ue-workflow/v0` (rows before td-02090: `superposition.ue-workflow/v0`), one row per real
operation written at the moment it happens. Builder: Claude (agent), reasons are the agent's own notes.

## Brief

Top-down tower defense on a grid. Enemies walk a spline path from the spawn to the base. The player
builds towers on free grid tiles with gold, upgrades them twice and sells them for 70 % of what was spent.
3 tower types, 4+ enemy types, 10 waves per level, 3 levels, wave timer with an early-call bonus, lives,
win/lose, star rating saved to disk, main menu with level select, pause, settings, HUD, synthesized SFX.

## Design

### Core loop

1. Level starts with `StartGold` and `Lives` from the level row; a countdown runs to wave 1.
2. During the countdown and during waves the player clicks a free tile → build panel (3 towers, cost,
   hotkeys 1/2/3); clicks a tower → upgrade/sell panel; range disc previews the range (hover and selection).
3. A wave spawns its groups; once the wave has finished spawning, the countdown to the next wave starts
   (`WaveCountdown` seconds). **Call next wave** (button or `N`) starts it at once and pays
   `EarlyCallGoldPerSecond × seconds left`.
4. An enemy that reaches the base costs `LivesCost` lives. Lives 0 → defeat screen.
   All 10 waves spawned and no enemy alive → victory screen with stars.
5. Stars: 3 if lives left ≥ 90 % of start, 2 if ≥ 50 %, else 1. Best result per level saved
   (`USaveGame`, slot `TDSave`). Level N+1 unlocks when level N has ≥ 1 star.

### Towers (rows in `DT_Towers`, 3 levels each: build + 2 upgrades)

| Id | Role | Colour | Hits air | Notes |
|---|---|---|---|---|
| `Rapid` | fast single target, low damage | yellow | yes | armour hurts it |
| `Cannon` | slow, splash damage | red/orange | no | ground only, good vs armour and groups |
| `Frost` | low damage, slows (% and duration), small splash | cyan | yes | support |

Per level: `Cost, Damage, Range, FireInterval, SplashRadius, SlowPct, SlowDuration, ProjectileSpeed`.
Sell refund = `SellRefundRatio (0.7) × total spent`.

### Enemies (rows in `DT_Enemies`)

| Id | Look | Colour | Notes |
|---|---|---|---|
| `Basic` | sphere | green | baseline |
| `Fast` | cone (pointing forward) | yellow-green | fast, low HP |
| `Armored` | cube | grey/steel | flat armour subtracted from each hit (min 15 % of the hit gets through) |
| `Flyer` | flattened sphere, hovers 250 cm up | purple | ignores nothing but only `Rapid`/`Frost` can hit it |
| `Boss` | large cube+sphere | dark red | wave 10, huge HP, costs 5 lives |

Fields: `MaxHP, Speed, Armor, Bounty, LivesCost, bFlying, Scale, Color, Mesh`.

### Waves (`DT_Waves_L1..L3`, one row per wave)

Row: `Groups[]` of `{Enemy, Count, Interval, StartDelay}`; groups of a wave run in parallel from
their `StartDelay`. HP scales by the level row's `HPMultiplier`.

### Levels (`DT_Levels`)

`Id, DisplayName, Map (soft world ref), StartGold, Lives, HPMultiplier, Waves (DataTable)`.

| Level | Map | Path idea |
|---|---|---|
| 1 Meadow | `L_Meadow` | long S-curve, gentle |
| 2 Canyon | `L_Canyon` | zig-zag with two long straights, fewer tiles near the path |
| 3 Fortress | `L_Fortress` | spiral into the centre, short last leg |

### Global tuning (`DA_TDConfig`, `UTDConfig : UPrimaryDataAsset`)

`TowerTable, EnemyTable, LevelTable, WaveCountdown, FirstWaveCountdown, EarlyCallGoldPerSecond,
SellRefundRatio, StarThresholds, Sounds (per event), Materials, Meshes`.

## Fab requests (2026-10-11)

Goal: premium stylized look that serves "The Last Lantern" (warm storybook valley that drains to grey). One
coherent style family (Polyart-compatible hand-painted stylized). All listings checked on fab.com for UE 5.3
support (engine versions from the listing's Unreal Engine format data). Fab does not expose download size; the
launcher shows it when adding to the project. Store content goes to `Content/Fab/<Pack>/`.

| # | Listing | URL | Price (Personal) | Licence | UE 5.3 | Replaces / adds | Why |
|---|---|---|---|---|---|---|---|
| 1 | Stylized Fantasy Castle Environment (Polyart Studio) | https://www.fab.com/listings/62e26424-f7c0-4bb3-962d-ca2fe5f9ff84 | $189.99 | Fab Standard | 5.1-5.8 | Kenney tower pieces + base keep: the **Lantern** (castle tower with crown), tower bodies, walls, banners, carts, keepers' props | the Lantern and the towers must read as one architecture; banners/ruins carry the environmental story |
| 2 | Dreamscape: Stylized Nature (Polyart Studio) | https://www.fab.com/listings/c4e83f22-369a-4f5c-8f86-d53ccd716ae6 | $79.99 | Fab Standard | 5.0-5.3 file | Kenney grass/tree/rock tiles: terrain materials, stylized trees, foliage, rocks, river bed | lush act-1 valley that can be desaturated per act; matches the castle pack's style |
| 3 | RPG Monster Wave Bundle Polyart (Dungeon Mason) | https://www.fab.com/listings/5e2581d3-eb37-48de-ade0-0921811b29a3 | $59.99 | Fab Standard | 4.18-5.8 | Kenney UFOs: animated creatures (walk/hit/die) for Glimmer, Darter, Shellback, Drifter (flying), Elder (boss) | living, colourful creatures that can be read first as monsters and later as the land's colour walking home |
| 4 | Animated Siege Weapons (mr.Necturus) | https://www.fab.com/listings/7b404175-8036-4cdc-bb7f-fd3629b94557 | $34.99 | UE Marketplace licence | 4.12-5.4 | Kenney ballista/cannon tops: animated ballista and catapult/cannon with firing animations | towers that visibly fire instead of static props |
| 5 | Stylized Crystals, Rocks and Gems (Snowchimp Interactive) | https://www.fab.com/listings/6afb3015-446c-4d4d-80a6-7ccbb1eeaf7c | $14.99 | Fab Standard | 4.24-5.8 | Lantern crown and Frost Spire crystals | the crystal is the story's central motif (it holds the stolen colour) |
| 6 | Anime Stylized VFX (Vefects) | https://www.fab.com/listings/d85dee78-9584-4b4b-a3b7-4b96de33c2b8 | $52.99 | Fab Standard | 4.27-5.8 | my sphere bursts: Niagara impacts, colour release on Glimmer deaths, frost slow, Lantern flare, spawn portal | premium hit feedback; the colour-release burst is a story beat |
| 7 | Classic RPG UI (PONETI) | https://www.fab.com/listings/477a40f3-5058-4a56-8649-6d588ea1ae43 | $14.99 | Fab Standard | 4.27-5.7 | Kenney UI pack: framed panels, buttons, icons for HUD, menus, win/lose screens | storybook frames instead of flat game UI |
| 8 | Ambient Fantasy (Donat Baracsi) | https://www.fab.com/listings/6f652883-3ed8-4059-9a67-8cb8c0ec4f78 | $19.99 | Fab Standard | 4.27-5.6 | synthesized music: per-act ambient tracks (warm / hollow / sparse) and Lantern ambience | music carries the story's mood shift |
| 9 | Magic Spell Sound Effects Pack Vol 1 (PlaceHolder Inc) | https://www.fab.com/listings/8e59e01f-7ad3-4bd7-8ff0-26a980ef90c4 | $19.99 | Fab Standard | 4.20-5.8 | synthesized SFX for frost, Glimmer death chimes, Lantern hum/flare | soft chimes instead of explosions are part of the reframe |
| F1 | Free Fantasy Music Pack (Donat Baracsi) | https://www.fab.com/listings/2423c639-983b-4378-903c-d4b1428924e8 | free | listed as CC BY / CC0 (check on add) | 4.15-5.5 (5.3 ok) | menu theme, win/lose stingers | same composer as #8 |
| F2 | FREE Stylized Foliage (StyleHex Studio) | https://www.fab.com/listings/b494d1c5-8d02-48c4-9038-54bb8970a26f | free | Fab Standard | 4.27-5.8 | flowers left where Glimmers fall; grass detail | story detail: colour returns where they fall |
| F3 | FREE Stylized Forest Sample (StyleHex Studio) | https://www.fab.com/listings/3c1a31b6-e523-4a0f-97d0-26b0db69b6bc | free | Fab Standard | 4.27-5.8 | extra trees for the forest band | filler variety |

Paid total about $488 (Personal tier). Cheaper alternatives if needed: #1 -> Modular Medieval Castle - Stylized
Fantasy (Sugar Works, $29.99, https://www.fab.com/listings/73ee89c8-08eb-4692-8ac4-4bcb16ce5f09); #6 -> Stylized Vfx
Mix (Fateloom, $20.99, https://www.fab.com/listings/52ffdc11-ad0f-4170-ac4d-77267db17246). Rejected: Polyart
"Stylized Ruins" (UE 5.4+ only), WOW "Generic Fantasy UI SFX" (UE 5.6+ only), FicusProsound orchestral pack
(UE 4.22 file only).

## Story bible: "The Last Lantern"

Told the high-taste way: in play, in the land and in sound. At most one short line of text per level.

### Premise

The valley's keepers built the **Lantern**, a tower crowned with crystal, to hold back the long night. It
works. It burns by drinking the colour of the land around it: green from the fields, blue from the rivers,
warmth from the stone. The things that walk the roads toward it are not invaders. They are the **Glimmers**,
the colour of the drained places given shape, walking home to the light that took them. The player is the
Lantern's last keeper and believes, until the end, that they are defending a beacon from monsters.

### History (never stated; inferred from the map)

- The Lantern was lit generations ago; the oldest ruins sit farthest from it, the newest closest.
- Each age the keepers raised the Lantern taller (its stacked storeys are the "upgrades" of the past) and
  built smaller lanterns along the roads: **the towers you build are those**: same stone, same crystal.
- The roads were the river beds and cart tracks of the villages that emptied as the colour left; the
  Glimmers follow them because they remember them.

### What the mechanics mean (reframed by the ending)

| Mechanic | First reading | After the reveal |
|---|---|---|
| Enemies walk the road to the base | monsters raid the beacon | the drained land walking home |
| Killing an enemy pays gold | bounty | the Lantern feeds on what you scatter |
| Frost tower slows | ice magic | the Lantern's crystal pulling warmth out of them |
| Lives lost when they reach the base | damage | colour returning to the Lantern's heart, dimming it |
| Boss (Elder) in wave 10 | big monster | the largest memory: a whole village |
| Upgrading towers adds storeys | power | the same act that built the Lantern |

### Three acts, one per level

| Level | Land | What the player sees | One line (title card) | Optional details |
|---|---|---|---|---|
| 1 Meadow (setup) | full colour, spring | a lush valley; the Lantern glows warm and proud at the road's end; Glimmers are small, bright, almost playful | "Keep the Lantern lit." | a grey ring of drained grass right around the Lantern; flowers bloom where Glimmers fall |
| 2 Canyon (doubt) | autumn palette, rivers dry | dry riverbed road, rock pillars, empty villages; the drained ring around the Lantern is wider; Glimmers come in families (small ones trailing big ones) | "Here the river ran, before the light drank it." | an abandoned cart and a fallen banner of the keepers; the road follows the old river bend |
| 3 Fortress (payoff) | winter/ash, almost colourless | the road spirals into the Lantern itself; the land is grey snow; the only colour on the map is the Glimmers and the Lantern's crystal | "Every light you stop is a field that never wakes." | the spiral is the drained ring at its widest; two Elders: the last two villages |

**Payoff.** Winning Fortress: the Lantern flares, the last colour streams into it, the screen holds on a
grey valley around a brilliant tower: *"The Lantern burns on."* Losing Fortress: the Glimmers reach the
heart, the crystal cracks and colour washes back over the valley: *"The lights come home."* Losing is the
kinder ending; the player learns it only by playing it.

### Motifs

- **Visual:** saturation falls level by level and toward the Lantern on every map (drain ring); the
  Lantern's crystal and the Glimmers are the only things that keep full colour in act 3; flowers/colour
  left where Glimmers fall.
- **Audio:** a low Lantern hum near the base; music moves from a warm major loop (Meadow) to a hollow minor
  loop (Canyon) to sparse bells (Fortress); Glimmer deaths are soft chimes, not explosions; the win
  stinger in act 3 is the warm theme played wrong (slowed, detuned).
- **UI:** the Lantern is the game's emblem (menu backdrop at dusk, the base icon in the HUD lives counter).

### Where the player learns what

1. Menu and level 1: a beacon worth defending (warm Lantern, cheerful music, grey ring hinted).
2. Level 2 title line + dry river + empty villages: something was taken from this land.
3. Level 3 line + grey world + spiral into the Lantern: the Lantern is the taker.
4. End of level 3 (win or lose line): the reframe of everything above.

### Names

Towers: Ballista (Rapid), Cannon, Frost Spire (crystal). Enemies: Glimmer (basic), Darter (fast),
Shellback (armoured), Drifter (flying), Elder (boss). Base: the Lantern.

## Scenarios (AutoPlay `-Scenario=<n>`)

| # | Name | Start state | Win | Lose |
|---|---|---|---|---|
| 1 | Meadow | `L_Meadow`, 220 gold, 20 Lantern lives, no towers, wave 1 countdown | survive all 10 waves with at least 1 life | Lantern lives reach 0 |
| 2 | Canyon | `L_Canyon`, 260 gold, 20 lives, no towers | survive all 10 waves | Lantern lives reach 0 |
| 3 | Fortress | `L_Fortress`, 300 gold, 15 lives, no towers | survive all 10 waves (two Elders in wave 10) | Lantern lives reach 0 |

The numbering is the level-select order (`DT_Levels.Order`); `UTDGameInstance` maps `StartScenario(n)` to that level.
Score: 1 per kill plus wave and life bonuses (telemetry `score`).

## Code (module `TowerDefense`, prefix `TD`)

| Class | Job |
|---|---|
| `TDTypes.h` | row structs `FTDTowerRow`, `FTDTowerLevel`, `FTDEnemyRow`, `FTDWaveRow`, `FTDWaveGroup`, `FTDLevelRow`, enums |
| `UTDConfig` | data asset with tables and global tuning |
| `UTDGameInstance` | save game, settings apply, level travel |
| `UTDSaveGame` | stars per level, settings (volumes, sensitivity, resolution, window mode) |
| `ATDGameMode` | gold, lives, wave state machine, spawning, win/lose, stars |
| `ATDPath` | `USplineComponent` placed in each map; spline start = spawn, end = base |
| `ATDGrid` | builds the tile grid (instanced meshes), marks tiles the spline crosses as path, occupancy |
| `ATDBase` | the base at the path end (visual + hit flash) |
| `ATDEnemy` | moves along the spline by distance, HP, armour, slow, flying height, health bar |
| `ATDTower` | targets the enemy furthest along the path in range, fires projectiles, levels |
| `ATDProjectile` | homing shot, splash and slow on impact |
| `ATDCameraPawn` | top-down camera: WASD / edge pan, wheel zoom, clamped |
| `ATDPlayerController` | hover/select tiles and towers, build/upgrade/sell, hotkeys, pause, HUD |
| `ATDMenuGameMode`, `ATDMenuPlayerController` | main menu map |
| `STDHud`, `STDMainMenu`, `STDSettingsPanel` | Slate UI built in C++ (no binary widget assets) |
| `UTDAudio` | plays SFX from the config with the saved volumes |

Blueprint subclasses (created by script, defaults set by script): `BP_TDGameInstance`, `BP_TDGameMode`,
`BP_TDMenuGameMode`, `BP_TDTower`, `BP_TDEnemy`, `BP_TDProjectile`.

## Assets

History: engine shapes, then Geometry Script meshes (rejected by the user as low quality, 2026-10-11 ~02:13), then
the Kenney kit (CC0) as a stopgap. **Current art (2026-10-11 05:40): Unreal-format Fab packs** delivered by the
asset scout (`asset-library/fab-ue/<pack>`, SHA-1 checked) and copied unchanged into `Content/<PackFolder>` by
`Scripts/fetch_fab_ue.sh` (the packs' internal `/Game/<PackFolder>/` references need the original folder name, so
they are not under `Content/Fab/`). Raw Fab files are git-ignored (not redistributable) and restored by rerunning the
script; they ship inside the packaged game. `assets.manifest.json` lists every pack and file with listing and licence.

| Pack (licence) | Used for | Adaptation |
|---|---|---|
| Stylized Fantasy Provencal (Fab Std) | rocks, cliffs, bushes, trees, houses, windmill, shrine, water mill, cart, paving | scattered per level by `ATDGrid` (blocked tiles, forest band, road edges) and hand-placed story props; Virtual Texturing turned on |
| StyleHex Forest Sample + Foliage (Fab Std) | birch/broadleaf trees, grass, flowers, stones, terrain textures | forest band, meadow grass; flower clumps are the blooms where Glimmers fall; terrain textures in `M_TD_Ground` |
| Stylized castle (Fab Std, bought) | the Lantern keep (dais, drums, roof, lamp crown), tower plinths, Fortress ruins, fallen banner | stacked by `ATDBase`/`ATDTower`; the lamp is the Lantern's crown and the Frost Spire's light |
| Stylized Human Siege Weapons (Fab Std, bought) | Ballista and Catapult tower tops with idle/attack animations; bolt and stone ammo | skeletal heads turn to target, attack animation sped to the fire rate, shot released mid-swing |
| Paragon Minions / Sevarog (Fab Std, Epic) | Glimmer (melee minion), Shellback (super minion), Elder boss (Sevarog) | run/walk + death animations, play rate matched to ground speed, rim-glow overlay in the Glimmer's colour |
| Quadruped Fantasy Creatures (Fab Std) | Darter (Barghest), Drifter (Griffon) | run / fly + death animations, flyers fall when killed |
| Realistic Starter VFX Vol 2, M5 VFX Vol2 (Fab Std) | impacts (wood, ice, vegetation), explosions, burning stone trail | spawned through `TDFX` (Cascade or Niagara) |
| HONETi 4K Full Fantasy GUI (Fab Std, bought) | bronze buttons, wood panel frame, gold icons, stars, slider, checkbox | Slate brushes at a nominal size (4K art, thin frames); the pack's font drew digits as boxes, so it is not used |
| Fantasy Music Starter Pack v2 (CC BY 4.0, "Music by Cinematsic") | menu + one track per act | looped in code; credit on the main menu |
| Good SKY (Fab Std) | copied, not placed yet | — |
| Cinzel, Alegreya Sans (SIL OFL 1.1) | display and body fonts | inline FontFaces |
| Built here | ground material with runtime path mask, Glimmer rim glow, stencil-masked drain post-process, Lantern glow, story systems, all SFX | `Scripts/s25*`..`s29*` |

Story hooks moved to the new art: the drain is now a post-process (`M_TD_DrainPP`) reading `MPC_TD`, so store
materials grey out with the land; Glimmers, shots, lamps, crown and blooms write custom stencil 1 and keep colour.

## Recording

- `Scripts/wf.py`: the logger (importable from UE Python, and a CLI for shell-side ops). Rows are appended,
  never rewritten. `seq` = line number, `id` = `td-NNNNN`. Failed rows have `status: failed`; each row carries
  `source.script`, `source.commit` (HEAD when it ran) and `source.script_sha256`.
- Editor work: one script per step under `Scripts/`, run headless (`run_ue.sh`, commandlet) or in the full
  editor when an importer needs Slate (`run_ue_gui.sh`). A script that failed is fixed in a new version
  (`s12` -> `s12b`, `s16` -> `s16b`, `s19` -> `s19b..e`) so failed rows point at the code that ran.
- Shell side: `build.sh` (build.compile), `wf_code.sh` (code.change), `commit.sh` (vcs.commit),
  `playtest.sh` (pie.test), `package*.sh` (build.package), `fetch_*.sh` (asset.download).
- Gaps before 01:48 (authoring of early scripts, the design doc, notes/messages, first nine commits) are
  recorded as `log.gap` rows (td-00311..00324), not backfilled.
- Heavy jobs go through the machine-wide limiter `tools/ue-heavy.ps1`; every run passes `-NoLiveCoding`,
  builds pass `-NoHotReloadFromIDE` (another session's Live Coding console otherwise blocks all builds).

## Input and test bot

All player decisions are Enhanced Input actions (14 actions, `IMC_TD`): pan, zoom, select, cancel, drag-pan,
build 1/2/3, upgrade, sell, next wave, speed, pause, back. The cursor is read through
`ATDPlayerController::GetPointerPosition` (real mouse, or a virtual cursor drawn by the HUD). The test bot
(`UTDAutoPlay`, flags `-tdauto -tdspeed=N -tdshots -tdquit`) acts only by injecting those actions and moving
the virtual cursor, so it is ready to be switched onto the AutoPlay contract drop-in.

## Acceptance checklist

- [x] Main menu: Play (level select with stars and locks), Settings, Quit
- [x] Settings: master/effects/music volume, mouse/camera sensitivity, edge scroll, resolution, window mode; saved
- [x] 3 levels with different paths (S-curve, zig-zag canyon, spiral fortress); 10 waves each; boss in wave 10 (two on Fortress)
- [x] 3 tower types (ballista, cannon, frost), 2 upgrades each, sell for 70 %
- [x] 5 enemy types incl. flying (cannon cannot hit it) and boss
- [x] Wave timer + call-early bonus
- [x] HUD: gold, lives, wave n/10, countdown, build bar, upgrade/sell panel with upgrade preview, range preview
- [x] Pause (Esc / P) with resume, restart, settings, main menu
- [x] Win / lose screens, star rating saved to disk and shown in level select
- [x] All tuning in DataTables / DataAsset (Data/*.json is the text copy)
- [x] SFX: build, upgrade, sell, shoot (per tower), hit, explosion, enemy death, leak, wave start, win, lose, click, error, coin; music loop
- [ ] Packaged Win64 build (in progress)
- [ ] AutoPlay contract v1 (waiting for the coordinator's go on the drop-in)

## Status (2026-10-12 01:35): complete

**Done.** Every brief item is in; store art (Fab packs), animated enemies and towers, HONETi UI with no plain text,
story "The Last Lantern" told through the drain. Latest game commit `ff5f1ee` (import paths scrubbed; game code as
recorded on `937ec12`).

- Recordings: AutoPlay v1.4, scenarios 1-3 recorded, validated and won (0 audio gaps, ~60 fps); tag
  `milestone/autoplay-3`.
- Package: `deliverables/tower-defense/tower-defense_ff5f1eea` (+ `_nostore`), complete.
- Dataset (layout v1.1): `deliverables/dataset/tower-defense/tower-defense.pending.zip` (10.26 GB) and
  `tower-defense_nostore.pending.zip` (1.41 GB), scan PASS; repo `Dataset/` committed (3db154b). **Pending only the
  creation replay** (`ReplayScripts/`); then rerun `tools/package-dataset.ps1
  tower-defense -Package <package> -ReplayScripts <d>`.
- Repo: `superpositionhq/game-tower-defense`, everything tracked (store packs in LFS), README with screenshots.
- Known: intermittent first-frame GPU hang in editor `-game` launches (mitigated with `r.RDG.AsyncCompute=0`, never seen
  in packaged runs); Good SKY copied but not placed.

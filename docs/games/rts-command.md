# Banners in the Mist — design doc and story bible

Real-time strategy, three-quarter view, Unreal Engine 5.3. One faction (the Ninth Survey) against one AI faction (the
Ash Banners) in a misty frontier valley. Small scope, polished: one valley, three scenarios, five unit types, six
buildings, two resources, fog of war that is the valley's own mist.

Project `RtsCommand` (module `RtsCommand`, class prefix `RC`), slug `rts-command`, workflow ids `rc-NNNNN`.

## Pillars

1. **Readable, calm RTS.** A small number of units you can tell apart at a glance (weapon silhouettes), one clear
   counter cycle, a camera that glides and never jerks.
2. **The mist is the map.** Fog of war is literal valley mist; lifting it is how the story is found.
3. **Premium heritage look.** Photogrammetry scans of Korean heritage architecture and props, scanned soldiers in
   traditional armour with hand-keyed weapon animation; an original kingdom, no real history depicted.
4. **Story in play, never in walls of text.** Objectives, short barks as subtitles, things you find in the mist,
   one late payoff that recolours every raid you fought.

## Story bible

### Premise

The Court at Hanseol sends **surveys** into the unmapped valleys beyond its border: a commander, porters, a few
companies of soldiers and a commission seal. They chart the land, raise a Survey Hall, and send the map home. You
command the **Ninth Survey** into the **Haeun valley**, a basin of terraced hills, pine ridges and a braided river
where the mist never fully lifts.

The valley is held by the **Ash Banners**: soldiers in persimmon-dyed coats who raid your fields, burn your
outposts and fight with the same weapons and drills you do. You read them as banner-lords, a rival warband.

They are the **Third Survey**, sent thirty winters ago. The Court never recalled them and never sent supplies. They
stayed, cut the terraces, married into the hill villages, re-dyed their faded indigo banners with persimmon because
indigo does not grow here, and kept the crane of the commission under the new colour. Every "abandoned" terrace you
harvest is theirs. Their raids are farmers taking back their rice.

### World

- **The Court at Hanseol** (never seen): sends surveys, receives maps, forgets the people who drew them.
- **Haeun valley**: late autumn. Gold rice terraces, red maples, black pines on the ridges, persimmon trees by the
  houses, a shallow braided river with one ford, thatched farmhouses and a tiled hall in the north-east. Morning
  mist pools in the low ground (the fog of war).
- **Time**: an invented kingdom in a pre-gunpowder age; architecture, armour and weapons are drawn from Korean
  heritage scans, but no real dynasty, place, battle or person is named or depicted.

### Factions

| Faction | Who | Colour | Banner | Units |
|---|---|---|---|---|
| **The Ninth Survey** (player) | the Court's newest expedition: Surveyor-Commander Yun (the player, never shown), porters, soldiers | indigo (*jjok* dye), white trim | white crane holding a measuring cord, on indigo | Porter, Spearman, Shieldbearer, Glaive, Archer |
| **The Ash Banners** (AI) | the Third Survey and the valley families that joined it | persimmon brown-orange (*gam* dye) | the same crane, sun-faded, under persimmon dye (a ghost of indigo shows at the hem) | the same five unit types, older kit |

The mirror is the clue: same buildings in an older, patched, thatched state; same drills; same crane. Players who
look closely can work it out before the payoff.

### Tone

Melancholic and restrained. Beautiful mornings, honest skirmishes (no gore: units fall and fade), quiet music.
Nobody is a villain. The only antagonist is a Court that is never on screen.

### How the story is told in play

1. **Mission objectives** (one framed scroll card at a time, under 15 words each; ticked off in play).
2. **Barks as subtitles** (no voices): short lines when you select or order a unit, when a building finishes, and
   from enemy units the first time they are seen in a scenario. A soft synthesized cue (drum tap, bamboo click,
   horn) plays with each; the line sits above the unit card for 2.5 s. Never more than one bark on screen.
3. **Environmental storytelling in the mist**: things the player uncovers just by lifting the mist:
   - rice terraces cut in the royal measure (the same plot width your porters use);
   - **survey stones** (boundary markers) carved with a crane and the numeral **III**; uncovering one pins a small
     crane glyph on the minimap and shows one line (`A boundary stone. Third commission.`);
   - enemy farmhouses with drying persimmons, children's tops on the porches, a loom with indigo thread;
   - a grave row behind the Ash Banner hall, thirty winters of stones (scenario 3).
4. **The enemy's barks** drift from hostile to familiar: S1 `Off our terraces!`, S2 `They came up the ford again.`,
   S3 (when their hall is low) `We were the Third. Who sent you?`
5. **The payoff** (scenario 3, the Ash Banner hall falls): the camera glides into the courtyard (slow, eased), the
   map board inside the hall is revealed: the valley charted thirty years ago, your camp drawn in red ink as
   "raiders from the ford". Two lines, one after the other:
   `Their map marks your camp in red.` / `Nine surveys went into the mist. None were recalled.`
   Then your porters plant the indigo banner beside the persimmon one. Losing scenario 3 ends on the Ash Banners
   re-planting their crane over your hall: `The valley keeps its own.`

### What the mechanics mean (reframed by the payoff)

| Mechanic | First reading | After the payoff |
|---|---|---|
| Harvesting rice from "abandoned" terraces | free resources | taking someone's harvest |
| Enemy raids on your porters | aggression | farmers defending their fields |
| Fog of war / mist | tactical unknown | thirty years of a life you were never told about |
| Enemy uses your unit types | lazy mirror | they were trained by the same Court |
| Destroying the enemy hall | victory | you did what the Court would have done to you |

### Names

Units: **Porter** (worker, A-frame carrier), **Spearman** (long spear), **Shieldbearer** (rattan shield and short
sword), **Glaive** (moon-glaive), **Archer** (horn bow). Buildings: **Survey Hall** (HQ), **Granary**, **Drill Yard**,
**Bowyer & Smithy**, **Watchtower**, **Waystation** (forward hall). Resources: **Rice**, **Timber**. Places: Haeun
valley, the Ford, Crane Ridge, the Old Terraces, the Ash Hall.

## Core loop

Gather (porters bring rice and timber to a hall or granary) → build (granary for supply, Drill Yard and Smithy for
soldiers, watchtowers for vision) → train an army with the right counters → scout the mist → defend raids → expand to
a second resource site → attack and destroy the objective.

### Camera (gentle by rule)

- Three-quarter view, fixed yaw (no rotation at all), pitch -55°, FOV 50. Zoom 2,400–5,200 cm arm length in three
  eased steps per wheel notch; pitch eases to -50° when zoomed in so units are never seen from hip height.
- Pan: WASD / arrow keys / edge scroll (edge scroll off by default, option in settings) / middle-drag. Velocity is
  eased (accel 0.35 s to full, decel 0.25 s), max 2,600 cm/s at full zoom-out, scaled down when zoomed in. Clamped
  to the scenario's playable bounds with a soft spring, never a hard stop.
- No camera snaps: jumping to an alert, the minimap or a control group is a 0.8 s eased glide (ease-in-out cubic),
  never a cut. The AutoPlay bot uses the same glides and pans.

### Selection and orders

- Left click selects a unit or building; left drag draws a box (styled frame, brush stroke corners) and selects all
  own units in it (units over buildings). Shift adds. Double-click selects all on-screen units of that type.
- Right click: context order. Ground → move (formation keeps relative offsets, spread to a loose grid for groups);
  enemy → attack; resource → gather (porters); unfinished building → help build; own hall/granary → drop off.
- `A` + left click: attack-move. `S`: stop. `H`: hold position. Ctrl+1..5 set control groups, 1..5 select them,
  double-tap glides the camera. `.` selects an idle porter. `Space` glides to the last alert.
- Build menu: select a porter, `B` opens the build bar, hotkeys `1..6` pick a building, a ghost follows the cursor
  (green/red footprint on a grid of 200 cm), left click places, right click cancels.
- Train: select a building, hotkeys `Q W E` queue its units (up to 5 in a queue), rally point by right click.

### Economy

| Resource | Source | Gather | Notes |
|---|---|---|---|
| Rice | rice terraces (`ARCResourceNode`, 1,200–2,000 each) | 8 per trip, 4.5 s harvest | the Old Terraces near each start; a rich field at the Ford |
| Timber | pine groves (clusters of tree nodes, 400 each) | 10 per trip, 6 s chop | trees fall and leave stumps when spent |

Supply: Survey Hall +10, Waystation +6, Granary +8, cap 60. Porters cost 1 supply, soldiers 2.
Start stock per scenario (see Scenarios).

### Buildings (`DT_Buildings`)

| Id | Name | Cost (rice / timber) | Build s | HP | Does | Art |
|---|---|---|---|---|---|---|
| `Hall` | Survey Hall (HQ) | — / 400 | 90 | 2,400 | trains Porter, drop-off, +10 supply, reveal 2,200 | tiled hall (Dongrae Hyanggyo / House of Changwon scans), drum, flagpole supports, indigo banners |
| `Granary` | Granary | — / 100 | 25 | 700 | drop-off, +8 supply | thatched barn (Naganeupseong `Barn`), rice straw stacks |
| `DrillYard` | Drill Yard | 50 / 150 | 40 | 1,100 | trains Spearman, Shieldbearer | Naganeupseong farmhouse + weapon racks, flagpole, fenced yard |
| `Smithy` | Bowyer & Smithy | 100 / 150 | 45 | 1,000 | trains Glaive, Archer (needs Drill Yard) | Naganeupseong `Smithy` with forge glow, quivers, bow racks |
| `Tower` | Watchtower | 25 / 100 | 30 | 650 | archer post (12 dmg, 1,500 range), reveal 2,800 | timber tower kitbashed from walled-town gate/wall pieces |
| `Waystation` | Waystation | 100 / 250 | 60 | 1,400 | forward hall: drop-off, trains Porter, +6 supply | smaller tiled house (`Anche`) + banner |

Construction: porters walk to the site and hammer; several porters build faster (diminishing). Unfinished buildings
rise through scaffolding (scale/clip reveal + timber scaffold props).

### Units (`DT_Units`) and counters

| Id | Name | Cost (rice / timber) | Train s | HP | Armour | Damage / cooldown / range | Speed | Strong vs | Weak vs |
|---|---|---|---|---|---|---|---|---|---|
| `Porter` | Porter | 50 / — | 12 | 60 | 0 | 4 / 1.5 s / melee | 320 | — | everything |
| `Spear` | Spearman | 50 / 20 | 18 | 110 | 1 | 11 / 1.3 s / 230 cm reach | 300 | Glaive (x1.75) | Archer, Shieldbearer |
| `Shield` | Shieldbearer | 60 / 25 | 20 | 150 | 3, pierce -60 % | 9 / 1.1 s / melee | 280 | Archer (shield up), Spearman (x1.5) | Glaive |
| `Glaive` | Glaive | 70 / 45 | 24 | 135 | 2 | 17 / 2.0 s / 200 cm, cleave 160 cm arc | 290 | Shieldbearer (x1.75, ignores shield) | Spearman, Archer |
| `Archer` | Archer | 45 / 45 | 20 | 80 | 0 | 10 pierce / 1.6 s / 1,400 cm | 310 | Spearman (x1.5), Glaive (x1.25) | Shieldbearer |

Counter cycle in one sentence for the player: **spears stop glaives, glaives break shields, shields stop arrows and
spears, arrows thin spears.** The damage multipliers live in `DT_Counters` (attacker × target), so tuning is
data-only. Units auto-acquire targets in their sight radius (1,600 cm), prefer the target they counter, keep
formation spacing (simple separation steering on top of navmesh paths), and fall with a death animation and fade.

### Fog of war (the mist)

- CPU grid 256×256 cells over the valley (≈ 200 cm per cell), three states: **unexplored** (thick white mist),
  **explored** (thin haze, desaturated, last-seen buildings shown as ghosts), **visible**. Updated at 8 Hz from every
  own unit and building's reveal radius (line of sight ignores height for simplicity, ridges block nothing).
- Uploaded to a `UTexture2D` (R8) and smoothed on the GPU; a post-process material reads it by world position: the
  unexplored mist is animated volumetric-looking noise (two panning noise layers + height fade), explored is a soft
  grey veil, visible is clear. The minimap uses the same texture.
- Enemy units are hidden outside visible cells; enemy buildings stay as "last seen" ghosts.

### Enemy AI (`URCEnemyAI`, Ash Banners)

Plays by the same rules (same costs, same supply, sees through its own vision only, no map hacks except a scripted
"knows where the Survey Hall is" in scenario 2 waves). Layers:

1. **Economy**: keep porters at target (8/12/16 by phase), balance rice/timber gatherers by the next purchase.
2. **Build order** per scenario and seed variant (e.g. S3 seed even = shield/archer opening, odd = spear/glaive),
   from `DT_AIBuildOrders`; timings jittered ±12 % by the seed.
3. **Army**: trains toward a composition that counters what it has *seen* of the player's army (count by type in
   the last 60 s of sightings).
4. **Attack**: gathers at a rally point, attacks when army value ≥ threshold (rising per wave) or on a scripted wave
   time; targets nearest player porters/granary first in raids, the hall in pushes; retreats wounded groups below 35 %
   of starting value.
5. **Defence**: pulls the army home when its buildings are attacked; towers at chokepoints.

## Scenarios (AutoPlay `-Scenario=<n>`)

All three play on one map, `L_Haeun`, with per-scenario playable bounds, start actors and AI script (data in
`DT_Scenarios`). `-Seed` seeds the AI build-order variant, timing jitter, resource node amounts (±10 %) and the
bot's RNG. Target length for a recording: S1 5–7 min, S2 8–10 min, S3 10–14 min (MaxSeconds 900 for S3).

| # | Name | Start state | Win | Lose |
|---|---|---|---|---|
| 1 | **First Light** (tutorial skirmish) | south-west quarter of the valley; Survey Hall, 4 Porters, 2 Spearmen; 150 rice, 200 timber; mist everywhere but the camp; Ash Banner watch-post across the stream (Watchtower + small Drill Yard, 4 soldiers), it sends two small raids (3 and 5 units) at ~2:30 and ~4:30 | destroy the watch-post's Drill Yard and Watchtower | Survey Hall destroyed, or no units and no resources to train |
| 2 | **Hold the Ford** (defend and expand) | west half; Survey Hall, Granary, Drill Yard, 6 Porters, 3 Spearmen, 2 Shieldbearers; 200 rice, 250 timber; the rich Ford terraces lie across the river | raise a Waystation at the Ford and keep it and the Hall standing through three Ash Banner attack waves (at ~3:00, ~5:30, ~8:00, growing, mixed counters) | Survey Hall or the finished Waystation destroyed (an unfinished Waystation can be rebuilt) |
| 3 | **The Ash Hall** (destroy the enemy HQ) | whole valley; both sides start with a Survey Hall, 5 Porters, 1 Spearman, 250 rice, 300 timber; Ash Banners build a full base and attack from ~6:00 | destroy the Ash Hall (enemy Survey Hall) → payoff | your Survey Hall destroyed |

Score: rice + timber gathered / 10 + 5 per enemy unit + 25 per enemy building + objective bonuses; telemetry `score`.

### What the AutoPlay bot does (plays like a competent human)

- **Opening**: selects the hall and queues porters (`Q`), box-selects idle porters and right-clicks the nearest
  terraces / pines, keeps a 60/40 rice/timber split, builds a Granary near the pines at ~130 timber, a Drill Yard at
  ~200 timber; scouts with one Spearman along a planned arc (lifting the mist; the camera follows only in glides).
- **Mid game**: trains counters to what it has seen (reads visible enemy composition from game state, as a human
  reads the screen); builds a Smithy, then archers + shields; Watchtower at the approach; re-assigns idle porters
  (`.`); defends raids by box-selecting the army (control group 1) and attack-moving to the alert.
- **Expansion** (S2, S3): sends 3–4 porters with an escort to the Ford, builds the Waystation, splits gatherers.
- **Attack**: at army value ≥ target and supply ≥ 30, attack-moves the army along the road with the camera gliding
  behind it; focuses buildings once enemy soldiers are down; reinforces from the rally point.
- **Skill** (0..1) interpolates: reaction time 1.2 s → 0.25 s; cursor travel time (Fitts) and jitter; APM cap
  25 → 70; build-order accuracy (skips/delays steps at low skill); counter choice (random at 0, informed at 1);
  retreat discipline. Skill 1 should win all three scenarios; 0.5 usually wins S1.
- **Input only through Enhanced Input** (`AP->Inject`) and the virtual cursor (`SetVirtualCursor`), which the HUD
  draws as a brush-stroke pointer. The cursor moves along eased curves, never teleports; the camera pans with eased
  `IA_Pan` values (no jumps) and zooms in single notches.

### Input actions (`IMC_RC`)

`IA_Pan` (Axis2D, WASD/arrows), `IA_Zoom` (Axis1D, wheel), `IA_DragPan` (Bool, MMB), `IA_Select` (Bool, LMB; press,
drag = box, release), `IA_SelectAdd` (Bool, Shift), `IA_Command` (Bool, RMB), `IA_AttackMove` (Bool, A),
`IA_Stop` (S), `IA_Hold` (H), `IA_BuildMenu` (B), `IA_Slot1..6` (1..6, build slot / control group), `IA_SetGroup`
(Ctrl modifier), `IA_TrainQ/W/E` (Q/W/E), `IA_IdlePorter` (.), `IA_LastAlert` (Space), `IA_Cancel` (Esc),
`IA_Pause` (P / F10), `IA_Speed` (F, 1x/2x in single play only).

### Telemetry (contract + game events)

`state` at 10 Hz (camera location as player location, rice, timber, supply, supply_cap, own/enemy unit counts,
selected count, visible_pct), `score`, `unit_trained` {type, building}, `building_placed` / `building_done` /
`building_lost` {type, id, location}, `gather_trip` {resource, amount}, `unit_killed` {type, side, by}, `attack_wave`
{wave, units}, `objective` {id, state}, `mist_revealed` {pct}, `survey_stone` {id}, `alert` {kind, location},
`ai_phase` {phase}.

## Map: `L_Haeun`

Landscape about 50,000 × 50,000 cm (500 m), heightmap generated in Python (`Scripts/gen_valley.py`): terraced
hillsides (stepped contours in the south-west and north-east), pine ridges on the west and east rims, a braided
river from north to south with one shallow Ford in the middle, a road that links both halls through the Ford.
Created through a small editor library `URCEditorLibrary::CreateLandscapeFromRaw` (UE 5.3 Python cannot create
landscapes; rally-racer's solved approach). Landscape material from the KCISA smart-material Land set and Megascans
surfaces (soil, grass, gravel, terrace mud), with a terrace-straw layer.

Zones: Survey camp (SW), Old Terraces (W), Ford (centre), Crane Ridge (pine ridge, E of the Ford), Ash Hall (NE) with
farmhouses, persimmon trees and the grave row. Navmesh over the whole map; buildings carve it at runtime
(dynamic modifiers only).

Lighting: low autumn sun, warm key, cool sky; exponential height fog low in the river bed (separate from the fog of
war); `r.RDG.AsyncCompute=0`.

## Art direction

Realistic heritage: photogrammetry architecture and props, scanned armour, autumn palette (gold terraces, red maples,
black pines, white mist), faction colour only on cloth and banners. Units are 1.3× scale so they read from the
three-quarter camera, with a faction-coloured rim outline (custom depth stencil) and a selection ring decal styled as
a brush circle.

Packs (all on disk under `asset-library\fab-ue\`, `"result":"ok"`, UE 5.3 OK):

| Pack | Used for |
|---|---|
| `kcisa-korean-traditional-martial-arts` | **all soldiers**: 4 scanned soldier meshes on one skeleton; weapon meshes + hand-keyed Idle/Walk/Run/Attack/Damage/Die sets for Jangchang (Spearman), Deungpae (Shieldbearer), Woldo (Glaive), Fist/Gonbang (Porter idle/walk) |
| `kcisa-korean-traditional-props` | Horn Bow + Quiver (Archer), war drums (Hall), flagpole supports (banners), stone pagoda / pedestals (story props) |
| `khs-naganeupseong-walled-town` | thatched farmhouses, barns (Granary), Smithy, ox mill, watermill, walls and gates (Watchtower kitbash), farm tools, food props (persimmons, jars) for both camps and the Ash Banner village |
| `dongrae-hyanggyo`, `kcisa-house-of-changwon` | tiled halls: Survey Hall, Ash Hall (weathered variant), Waystation |
| `kcisa-korean-traditional-smart-materials-vol-1` / `-vol-4` | land, wood, brick surfaces; painted (*dancheong*) wood patterns for the UI frames |
| `khs-korean-stone-pagoda`, `khs-king-tomb-of-silla` | survey stones / grave row dressing (credit Korea Heritage Service) |
| `temperate-vegetation-foliage-collection`, `-conifer-bushes-saplings-i`, `-optimized-grass-library`, `-meadow-flowers` | pines (timber nodes), shrubs, grass, autumn ground cover |
| `city-park-environment-collection` | maples for autumn colour |
| `realistic-starter-vfx-pack-vol-2`, `niagara-dust`, `free-realistic-niagara-explosions-pack` | hit sparks, dust when buildings fall, burning thatch |
| `craft-resources-icons` | rice sack and log icons (re-tinted) |

Animation work: the archer's draw/release and the porter's harvest/chop/hammer are retargeted onto the soldier
skeleton with IK Retargeter (Paragon bow clips from `fab\paragon-animations-retargeted-to-manny\`, harvest/chop/hammer
from `fab-ue\ramsterz-survival-animations\`), with an IK Rig per skeleton built by script.

Built here: valley heightmap and landscape material, mist post-process and minimap, faction cloth tint, rim outline,
selection decals, scaffolding reveal, all UI art composition, synthesized music and SFX.

### Requests (no purchase needed)

- Fonts (OFL, Google Fonts): **Gowun Batang** (body, Latin + Hangul), **Song Myung** (display), for the asset scout.
- Nothing to buy: every pack above is already owned and on disk.

## UI style: lacquer and dancheong

- Panels are black lacquered wood (smart-material wood, darkened, with a soft clear-coat sheen baked into the
  texture) framed by a thin band of *dancheong* pattern (green, red, ochre, white) cropped from the KCISA painted-wood
  textures, with mother-of-pearl corner inlays. No flat colour blocks, no engine font.
- Bottom-left: minimap in a round-cornered lacquer frame, mist drawn as white wash, own units indigo dots, enemies
  persimmon. Bottom-centre: selection card (portrait rendered from the unit mesh, HP as a brush stroke bar, armour and
  counter icons). Bottom-right: command grid (build/train buttons with hotkey seals). Top: resource strip (rice sack,
  log, supply crane), objective scroll on the right, bark subtitle above the selection card.
- Seals (*dojang*): hotkeys and the Ninth Survey emblem are drawn as red seal stamps.
- Fonts: Song Myung (titles, unit names), Gowun Batang (numbers and body). Numbers have a soft ink outline.
- Main menu: the valley at dawn behind a slow parallax of mist, the crane seal, buttons as lacquer plaques. Settings
  (master/music/effects volume, camera pan speed, edge scroll, resolution, window mode), pause, scenario select with
  three hanging-scroll cards. Save/load: scenario progress and settings (`URCSaveGame`).

## Audio

- Music synthesized in `Scripts/gen_music.py`: pentatonic plucked-zither phrases over slow hourglass-drum patterns,
  a breathy bamboo-flute pad; three loops (camp, battle, the payoff stinger played on one string).
- SFX: synthesized UI clicks, seal stamps, drum taps for barks; `free-realistic-sword-sound-effects-pack` (WAV) for
  blade hits, `essential-footsteps-sfx`, `essential-ambience-sfx` (wind, birds, river), `sfx-essentials` for wood
  chops and building collapse.
- No voices; barks are subtitles with a cue sound.

## Code (module `RtsCommand`, prefix `RC`)

| Class | Job |
|---|---|
| `RCTypes.h` | `FRCUnitRow`, `FRCBuildingRow`, `FRCCounterRow`, `FRCScenarioRow`, `FRCAIBuildStep`, enums (`ERCSide`, `ERCResource`) |
| `URCConfig` (data asset) | tables, global tuning, sound and material refs |
| `URCGameInstance` | save, settings, `StartScenario` wiring (one map, scenario id) |
| `ARCGameMode` | scenario setup, resources and supply per side, objectives, win/lose, score, telemetry |
| `ARCUnit` (`ACharacter`) | HP, armour, attack, gather, build, carry, order queue, separation, anim state |
| `URCUnitAnimInstance` | locomotion blend, attack/harvest/hit/death montages per weapon set |
| `ARCBuilding` | footprint, construction, HP, training queue, rally point, drop-off, supply, tower attack |
| `ARCResourceNode` | rice terrace / pine, amount, gatherer slots, depletion visuals |
| `URCFogOfWar` (world subsystem) | grid, reveal, texture upload, visibility queries |
| `ARCCameraPawn` | eased pan/zoom/glide, bounds |
| `ARCPlayerController` | selection, box select, orders, build placement, hotkeys, control groups, pointer via `GetCursorPosition` |
| `URCEnemyAI` | Ash Banner economy, build order, army, attack/defend |
| `URCBotComponent` | AutoPlay bot (planner + human-like cursor/camera + injected input) |
| `SRCHud`, `SRCMainMenu`, `SRCSettings` | Slate UI in C++ |
| `URCAudio` | music and SFX with saved volumes |
| `URCStory` | objectives, barks, survey stones, payoff sequence |

Tables: `DT_Units`, `DT_Buildings`, `DT_Counters`, `DT_Scenarios`, `DT_AIBuildOrders`, `DT_Barks`; `Data/*.json` is
the text copy, imported by script.

## Acceptance checklist

- [ ] Three-quarter camera: eased pan/zoom/glide, no rotation, no snaps; framing screenshots approved.
- [ ] Box select, click select, right-click orders, attack-move, control groups, idle porter key.
- [ ] Porters gather rice and timber, build all six buildings; supply cap works.
- [ ] Five unit types with the counter cycle visible in fights (data-driven).
- [ ] Mist fog of war with three states, minimap, hidden enemies, last-seen buildings.
- [ ] Ash Banner AI builds, gathers, trains counters and attacks in waves.
- [ ] Scenarios 1–3 winnable by the bot at Skill 1; lose states reachable.
- [ ] Story: objectives, barks, survey stones, enemy bark drift, payoff on S3 win and lose.
- [ ] Styled UI everywhere (no engine font), menu, settings, pause, scenario select, save of progress/settings.
- [ ] Music and SFX; no voices.
- [ ] AutoPlay v1.4 drop-in unchanged; validate-run PASS for S1..S3; tags `milestone/autoplay-<n>`.
- [ ] Packaged Win64 Shipping build; `scrub-import-paths.py --verify` = 0.

## Risks

- Scanned heritage meshes are heavy: use Nanite where the pack ships it, merged instances for repeated houses,
  HLOD off (small map).
- Retargeting bow/harvest clips onto the KCISA soldier skeleton: if a clip fails, the Archer uses the Deungpae
  set's attack as a fallback pose with a bow attached until fixed.
- Many skeletal meshes on screen (up to ~120): animation budget via URO (update-rate optimisation) and LOD.

## Status

- 2026-10-12: story bible and design doc written; waiting for the coordinator's OK before building.

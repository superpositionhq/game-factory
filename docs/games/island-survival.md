# Game #3 (Unreal): LANTERN KEY — third-person island survival (UE 5.3)

Track B game: a complete third-person island-survival game with gathering, crafting and a building flow, built in
Unreal Engine 5.3 by an agent (Claude), with every real editor, code and build operation recorded at the moment it
happens in `workflow.jsonl` (schema `superposition.ue-workflow/v0`, ids `is-NNNNN`).
Project: `C:\Users\Xiang\Work\games\island-survival` (own git repo, git-lfs). Module `IslandSurvival`.
Started 2026-10-11 02:41 -04:00.

The vendor's `island_explore` is the bar to beat: a marketplace demo map with fixes on top, a Paragon character,
a "building" that places one foundation, debug resource counters and no record of how it was made. Lantern Key is
built here (landscape, layout, systems, building set, UI, story) with every step observed, and its survival loop is
real: needs, weather, night, threats, tool tiers, crafting, a socketed building set, and an escape arc.

## 1. Game in one paragraph

You wake on the south beach of Lantern Key, a small volcanic island, with nothing but your hands. Survive: keep
health, hunger, thirst, stamina and warmth up; nights are cold and the island's night hunters come out; rain and
storms soak you and close the view. Gather (branches, stones, fibre, fronds, coconuts and fruit by hand; logs,
flint and fish with stone tools; ore and ironwood with metal), craft at hand, at a workbench and at a campfire,
and build shelter from a socketed timber set (foundation, floor, wall, doorway, roof, stairs) plus campfire,
storage chest, bed and rain collector. The island opens in three rings, each gated by a tool tier: the **beach**
(hands), the **jungle** (stone axe clears the overgrowth), the **highland** with the dead lighthouse (stone pick
breaks the rockfall; ore there leads to metal), and the **sea cave** under the headland (metal pick). To escape,
light a signal fire on the lighthouse headland and finish the raft in the west cove. Along the way the island
tells, without a word of exposition, who lived here, why it is empty, and who the night hunters really are.

## 2. Story bible

**Premise (never stated as text in game).** Lantern Key had a lighthouse and one keeper, **Wren Halloway**, who
kept it from 1964 with her dogs. In 1981 the light was automated and the post closed. The relief boat came to take
her off; dogs were not allowed aboard. Wren hid in the sea cave with her four dogs (Bosun, Pip, Juno, Tack) until
the boat gave up and left. She stayed for the rest of her life. The automated lamp failed a few years later and
nobody came back. Wren grew old; she built a raft she never launched and marked the island for whoever the sea would
bring next: ochre hands at fresh water, cairns on safe paths, notches on trees that bear fruit. Her dogs outlived
her and their descendants became the pack that hunts the island at night. They are not monsters. They are waiting
for someone to come down the hill with food, the way she did every evening.

**What the player believes, then learns.** Early on the stone pads on the beach read as a ruined village, the claw
marks on the lighthouse door as an attack, the night pack as the island's threat, the half-built raft as wreckage.
The cave reveals that the pads were the dogs' run, the scratches were dogs waiting at her door, the raft was left
on purpose, and the pack is hers. From then on, offering cooked food to a dog at night calms it; a fed pack stops
hunting you and lies down by your fire. The ending (raft at dawn) is quieter for it: one dog swims after the raft,
or the pack watches from the beach if you never fed them.

**One line per area** (shown once, small, lower third, when the area is first entered; under 15 words):

| Area | Line |
|---|---|
| Beach (start) | "Someone squared these stones. They meant to stay." |
| Jungle | "Ochre hands at every spring. Someone wanted to be followed." |
| Highland / lighthouse | "The lamp went dark. The scratches on the door did not stop." |
| Sea cave (payoff) | "She stayed for them. They are still waiting for her." |
| Ending | "Keep the light." |

**Discoverable details** (optional, inspect shows only a 2–4 word name, never a page of text):
enamel dog bowls by the beach pads; a stencilled relief crate `LANTERN KEY — LAST RELIEF — 1981`; a rusted
collar tag on a branch over the jungle spring (BOSUN), three more in the island (PIP, JUNA→JUNO, TACK; finding all
four is tracked); tally notches on a fig tree that stop abruptly; the lighthouse logbook open on a desk, last entry
date only; a child-height ochre hand next to an adult one at the highland spring (Wren's hand and a dog's paw);
the cave wall: a painted frieze read left to right — the boat leaving, a woman and four dogs in the cave, the
lamp dark, a raft, a woman feeding dogs at a fire, the raft on the water with a figure that is not her.
Story progress is saved (areas entered, tags found, frieze seen, pack fed).

## 3. Controls

| Action | Keyboard / mouse | Gamepad | Input action |
|---|---|---|---|
| Move / look | WASD / mouse | left / right stick | `IA_Move`, `IA_Look` |
| Jump / swim up | Space | A | `IA_Jump` |
| Sprint (stamina) | Left Shift (hold) | left thumb | `IA_Sprint` |
| Use tool / attack / gather / place | Left mouse | right trigger | `IA_Primary` |
| Interact (pick up, open, drink, sleep, light) | E | X | `IA_Interact` |
| Eat / drink held item, feed | F | Y | `IA_Use` |
| Hotbar slot 1–8 / next / prev | 1–8 / wheel | d-pad | `IA_Hotbar1..8`, `IA_HotbarNext/Prev` |
| Build mode on/off | B | d-pad up (hold) | `IA_BuildMode` |
| Build: next / previous piece | wheel / Q-E in build mode | shoulders | `IA_BuildCycle` |
| Build: rotate | R | B | `IA_Rotate` |
| Build: demolish (aim at piece, hold) | X (hold) | B (hold) | `IA_Demolish` |
| Inventory + crafting | Tab / I | Back | `IA_Inventory` |
| Craft selected recipe (in panel) | Enter / click | A | `IA_Craft` |
| Pause | Esc / P | Start | `IA_Pause` |

Everything the player does is an Enhanced Input action, so the AutoPlay bot can do it (crafting has hotkeys:
`IA_Craft` crafts the recipe selected with `IA_RecipeNext/Prev`).

## 4. Systems and classes (C++ module `IslandSurvival`, Blueprint subclasses + DataTables for tuning)

Base: Epic's **Third Person C++ template** (UE 5.3): project setup, Manny/Quinn, locomotion ABP, Enhanced Input.
Gameplay is C++. Tuning lives in Blueprint subclasses and DataTables created by editor Python scripts from CSVs in
`Data/` (so table changes are diffs). UI is UMG built in C++ (no hand-authored widget graphs).

| Class | Role |
|---|---|
| `AIslandCharacter` | template character + sprint (stamina), swim (water physics volume; stamina drain, drowning when 0), interaction trace (300 cm, sphere), equipped-item mesh on the hand socket, primary action (swing timing, hit trace), build mode, footstep surface, wetness |
| `UIslandNeedsComponent` | health, hunger, thirst, stamina, warmth (0..100); rates by activity, weather, time of day, shelter, fire; damage when starving/dehydrated/freezing; events for HUD |
| `UIslandInventoryComponent` | 24 slots + 8-slot hotbar (first 8 slots), stacks per item, add/remove/count, drop, split; selected hotbar index |
| `UIslandItemDB` (game-instance subsystem) | loads `DT_Items`, `DT_Recipes`, `DT_Buildables`; lookups |
| `AIslandResourceNode` | tree / palm / rock / ore / ironwood / bush / fibre plant / overgrowth; HP, required tool kind + tier, drops per hit and on break, hit feedback (shake, particle, sound, wobble), fall (trees), respawn timer, saved state |
| `AIslandPickup` | loose items (branches, stones, shells, coconuts) and dropped stacks; interact to take |
| `AIslandPackMarker` | death drop: holds the whole inventory, beacon light + compass marker, taken by interact |
| `UIslandCraftingComponent` | recipe availability (items + station in range), craft (consume, add, sound), station detection |
| `UIslandBuildComponent` | placement mode: ghost mesh, surface trace, socket snapping, grid fallback, rotation, valid/invalid material, cost check, place, demolish with refund |
| `AIslandBuildPiece` | placed structure piece: type, sockets (generated from type), HP, owner save id; doorway piece owns a hinged door |
| `AIslandPlaceable` (+ `AIslandCampfire`, `AIslandChest`, `AIslandBed`, `AIslandRainCollector`, `AIslandWorkbench`, `AIslandSignalFire`, `AIslandRaft`) | interactive placeables: fire (light/fuel, warmth radius, cooking/smelting station, scares the pack), chest (24 slots), bed (sleep to dawn if safe, sets respawn), rain collector (fills while raining → drink), workbench (station), signal fire + raft (endgame) |
| `AIslandTimeOfDay` | sun/moon rotation, sky atmosphere, sky light recapture, fog, star dome, exposure; day length; day counter; dusk/dawn events |
| `AIslandWeather` | Clear → Overcast → Rain → Storm state machine; rain/storm Niagara around the camera, wetness, fog, wind, lightning + thunder, cloud coverage |
| `AIslandShelterProbe` (on character) | sheltered = roof overhead trace + enclosure ratio from 8 horizontal traces; blocks rain wetness and warms |
| `AIslandAnimal` + `AIslandAnimalAI` | boar (day: wander/graze, flee, charge when hurt or close) and pack dog (night: hunt, circle, attack, fear of fire, blocked by walls/doors, calmed when fed after the payoff); state machine in C++, nav mesh movement |
| `AIslandSpawner` | spawns boars by day, dogs at dusk at dens, despawns at dawn |
| `AIslandAreaVolume` | area id (beach/jungle/highland/cave), first-entry story line, ambient sound, compass label |
| `AIslandStoryItem` | discoverable detail (collar tag, bowl, crate, logbook, frieze): inspect name, story flag |
| `AIslandGameMode` | world start/load, respawn, win (escape), death flow, AutoPlay level start |
| `AIslandMenuGameMode` | main menu map |
| `UIslandGameInstance` | settings (volumes, resolution, window mode, sensitivity, invert Y), save/load slots, AutoPlay hook |
| `UIslandSaveGame` | player (location, needs, inventory, spawn), world (structures, placeables, chests, nodes depleted + respawn times, pickups taken, pack marker), time of day, weather, story flags, play time |
| `UIslandHUDWidget` & panels | needs bars, hotbar, interaction prompt, compass, toasts, area line; inventory/crafting panel; build bar; chest panel; main menu; pause; settings; save/load; death; ending |
| `UIslandBotComponent` | AutoPlay bot (section 11) |

### Data tables (CSV in `Data/`, imported to DataTables)

**Items** (`DT_Items`: id, name, kind, max stack, tool kind, tool tier, damage, food, water, warmth, mesh, icon)

| Id | Name | Kind | Stack | Notes |
|---|---|---|---|---|
| Branch | Branch | resource | 30 | trees by hand, ground |
| Stone | Stone | resource | 30 | ground, boulders |
| Fibre | Plant Fibre | resource | 50 | fibre plants by hand |
| Frond | Palm Frond | resource | 30 | palms by hand |
| Log | Log | resource | 20 | trees, needs axe T1 |
| Flint | Flint | resource | 20 | jungle boulders, pick T1 |
| Ore | Iron Ore | resource | 20 | highland veins, pick T1 |
| Ingot | Iron Ingot | resource | 20 | smelted at campfire |
| Ironwood | Ironwood | resource | 20 | highland ironwood, axe T2 |
| Resin | Resin | resource | 20 | jungle trees (chance), ironwood |
| Rope | Rope | resource | 20 | crafted |
| Sailcloth | Sailcloth | resource | 5 | relief crate canvas in the cave |
| LampOil | Lamp Oil | resource | 5 | lighthouse store (highland) |
| Coconut | Coconut | food | 10 | food 10, water 20 |
| Banana | Banana | food | 10 | food 15, water 5 |
| RawFish / CookedFish | Fish | food | 10 | raw: food 8, chance of sickness; cooked: food 30 |
| RawMeat / CookedMeat | Meat | food | 10 | boar; raw food 10, cooked 40; feeding a dog |
| Canteen | Bamboo Canteen | tool | 1 | holds 3 drinks, fill at fresh water or collector |
| StoneAxe / StonePick | Stone Axe / Stone Pick | tool T1 | 1 | durability 120 |
| Spear | Spear | tool T1 | 1 | weapon (25 dmg), fishing in shallows |
| MetalAxe / MetalPick | Iron Axe / Iron Pick | tool T2 | 1 | durability 300, ×2 yield |
| Torch | Torch | tool | 1 | light, warmth +, 240 s burn, scares the pack |

**Recipes** (`DT_Recipes`: output, count, inputs, station)

| Output | Inputs | Station |
|---|---|---|
| Rope | 3 Fibre | hand |
| Stone Axe | 2 Branch, 2 Stone, 1 Rope | hand |
| Stone Pick | 2 Branch, 3 Stone, 1 Rope | hand |
| Spear | 3 Branch, 1 Stone, 1 Fibre | hand |
| Torch | 1 Branch, 2 Fibre | hand |
| Canteen | 1 Log, 1 Rope | workbench |
| Iron Axe | 2 Ingot, 1 Log, 1 Rope | workbench |
| Iron Pick | 3 Ingot, 1 Log, 1 Rope | workbench |
| Iron Ingot | 2 Ore, 2 Branch (fuel) | campfire |
| Cooked Fish / Cooked Meat | 1 raw | campfire |

**Buildables** (`DT_Buildables`: id, kind, cost, refund, HP, snap type, size)

| Id | Kind | Cost | Snap |
|---|---|---|---|
| Foundation | structure | 4 Log, 4 Stone | grid 300 cm / foundation edge sockets, terrain conform (stilts) |
| Floor | structure | 3 Log | floor sockets (wall tops, foundation edges) |
| Wall | structure | 3 Log, 1 Rope | edge sockets |
| Doorway | structure (door opens) | 3 Log, 2 Rope | edge sockets |
| Roof | structure (slope) | 2 Log, 6 Frond | wall-top sockets |
| Stairs | structure | 4 Log | foundation/floor sockets |
| Campfire | placeable/station | 5 Stone, 3 Branch | ground or floor |
| Workbench | placeable/station | 6 Log, 2 Rope, 4 Stone | ground or floor |
| Storage Chest | placeable | 6 Log, 2 Rope | ground or floor |
| Bed | placeable (spawn) | 4 Log, 8 Frond, 4 Fibre | floor/foundation |
| Rain Collector | placeable | 3 Log, 6 Frond, 2 Rope | ground or floor |
| Signal Fire | endgame | 8 Ironwood, 10 Frond, 2 Lamp Oil | only on the headland beacon pad |
| Raft | endgame | 16 Log, 8 Rope, 4 Ingot, 1 Sailcloth | only at Wren's slip in the west cove (adds to her frame) |

Demolish refunds 100 % within 60 s of placing, 50 % after.

### Survival numbers (tunable in `BP_IslandCharacter` / `DA_SurvivalTuning`)

- Hunger 100 → 0 in 30 min (×1.5 sprinting/swimming); thirst 100 → 0 in 20 min (×0.6 in rain, ×1.5 in sun at noon).
- Stamina: sprint −14/s, swim −4/s (sprint-swim −12/s), swing −8; regen +18/s after 1 s; ≤0 → no sprint, swimming
  at 0 drains health (drowning) −8/s.
- Warmth: target from environment (day 80, night 35, rain −20, storm −35, wet −15, sheltered +20, fire within 6 m
  +45, torch +15); moves toward target at 2/s; below 25 → health −0.5/s and slower stamina regen.
- Starving / dehydrated: health −0.8/s each. Health regen +0.4/s when hunger and thirst > 60 and warmth > 40.
- Day cycle 24 in-game hours = 20 real minutes (day 06:00–19:30, night 19:30–06:00). Sleeping in a bed when sheltered
  and no hunters within 20 m skips to 06:00 (needs drop as if 2 h passed).

## 5. Building flow (the core)

- **B** toggles build mode; the hotbar is replaced by the build bar (structures, then placeables) with costs shown
  and unaffordable pieces dimmed; wheel / Q-E cycles, R rotates 90° (structures) or 15° (placeables).
- Ghost = the piece mesh with a translucent fresnel material, **green** valid / **red** invalid (reason shown:
  "Needs 2 more Log", "Blocked", "Too steep", "Must snap to a foundation").
- Placement: line trace from the camera (8 m). Foundations snap to a world grid (300 cm, 22.5° rotation steps) or,
  near another foundation, to its edge sockets; on slopes they extend stilts down to the ground (max 2.5 m).
  Walls/doorways snap to foundation and floor edges, floors to wall tops, roofs to wall tops (sloped, fronds),
  stairs to foundation/floor sides. Socket choice = closest socket to the aim point whose type accepts the piece.
- Validity: overlap test against world/other pieces with a small inset, slope limit for free placement, support
  (non-foundation pieces need a supporting socket), cost.
- Place → resources removed, piece spawns with a settle animation, dust puff and sound. Demolish (hold X while aiming)
  → refund, pieces that lose support collapse (simple support graph: foundation → walls → floors/roofs).
- Shelter: under a roof with ≥ 5/8 horizontal traces blocked → sheltered (no rain wetness, warmth +20, HUD icon).
  Pack dogs cannot enter: pieces block navigation (dynamic nav mesh), doors close; inside a closed shelter you are safe.

## 6. Threats and AI

- **Boar** (day, beach edge and jungle): wander/graze between nav points, flee when hit below 40 % HP, charges when
  the player comes within 5 m while it is "irritated" (hit or rutting 25 %), 15 damage per gore, 60 HP; drops 2 Raw
  Meat. Spear 25, axes 15, fists 5.
- **Pack dogs** (night, 2 at night 1, 3–4 later): spawn at dusk at dens (jungle den, highland den), hunt the player by
  sight/smell radius (35 m, or anywhere after 60 s of night), circle at 4–6 m before lunging (10 damage), keep out of a
  lit campfire's 6 m radius and away from a held torch (3 m), cannot pass walls/closed doors; when blocked by a shelter
  they circle and howl. At dawn they retreat to the den and despawn. After the cave frieze is seen, `IA_Use` with cooked
  meat/fish in hand within 3 m of a dog feeds it: the dog sits, the pack's hostility drops; when 3 dogs are fed the pack
  is calm for the rest of the game (they lie by your fire at night).
- **Death** → the whole inventory drops as a pack at the death location (marker on compass + light beam), respawn at
  the last bed slept in (or the beach) with full health and 50 hunger/thirst. Interact the pack to take everything back.

## 7. Map plan (one persistent map `L_Island`, plus `L_MainMenu`)

Landscape 1261×1261 vertices at 100 cm (1.26 km square), island ~1.0 × 0.8 km, ocean (UE Water plugin ocean body) around
it. Heightmap generated by Python (shaped noise, beach shelf, jungle basin with a stream, highland plateau at 60–90 m,
headland cliff, cave mouth). Landscape material blends by height/slope/noise (sand, damp sand, jungle floor, grass,
rock, volcanic rock) with no paint layers.

| Area | Where | Gate | Resources | Landmarks |
|---|---|---|---|---|
| Beach | south and west shores | none (start) | branches, stones, fibre, fronds, coconuts, shells, fish in shallows (spear) | wreck debris, kennel pads + bowls, west cove with Wren's raft frame |
| Jungle | island centre basin | overgrowth walls on the 3 trails need a **stone axe** | logs, resin, bananas, flint boulders, boars, fresh-water spring + stream | ochre hands at springs, cairns, fig tree with notches, collar BOSUN, jungle den |
| Highland | north-east plateau and headland | rockfall on the switchback needs a **stone pick** | ore veins, ironwood trees, stone, lamp oil (lighthouse store) | dead lighthouse with clawed door + logbook, beacon pad (signal fire), highland den |
| Sea cave | under the headland cliff, entered from the north shore | collapsed iron grille + rubble needs an **iron pick** | sailcloth (relief crate), ore | Wren's last camp, the frieze, collar TACK |

## 8. Art and audio direction

**Look:** premium stylised-realistic tropical: scanned surfaces with a slightly heightened palette. Turquoise shallows
grading to deep blue ocean, pale coral sand, black volcanic rock on the highland, a dense layered jungle (canopy trees,
palms, understorey broadleaf, ferns, ground cover), warm sun and long shadows, wet glossy surfaces in rain.
Lighting: SkyAtmosphere + VolumetricCloud + real-time sky light, Lumen GI and reflections, exponential height fog with
volumetric fog (morning haze over the jungle), sun/moon directional light driven by `AIslandTimeOfDay`; nights are
moonlit blue, never black; fires and torches are the warm counterpoint. Post: filmic tonemapper, mild bloom, slight
vignette, auto exposure clamped. Water: UE Water plugin ocean (waves, shoreline foam, depth colour) and a stream river.
Foliage: wind via material WPO.
**Sources:** Poly Haven CC0 scans (island trees, coast rocks and cliffs, boulders, ferns, shrubs, tropical understorey
plants, sand/rock/bark/thatch/plank textures, props such as the hatchet, oil lamp, radio, crates), assets from the
asset-scout library, Fab/Megascans where requested (section 13), Epic's Manny/Quinn re-dressed. The timber building
set, tools, placeables and story props are built here (Geometry Script + scanned textures) to match the scans.
**Audio:** CC0 recordings where available (surf, jungle birds/insects, rain, thunder, fire, wood/stone hits, footsteps
on sand/grass/rock/wood, boar, dogs), synthesized where not; Sound classes Master/Music/SFX/Ambience with a mix for the
settings; ambience per area and time of day; a sparse music cue at dusk, at the frieze and at the ending.

## 9. UI

HUD: needs as five compact radial/linear bars bottom-left (health, hunger, thirst, stamina, warmth) with icons, wet and
sheltered status icons; hotbar bottom-centre (8 slots, count, durability); interaction prompt centre (`[E] Take Branch`,
`Needs Stone Axe`); compass top-centre (N/E/S/W, markers: pack, bed, discovered landmarks); day + clock top-right;
toasts for pickups; area line lower third. Panels: inventory + crafting (Tab), chest, build bar, pause (resume, save,
load, settings, main menu), settings (master/music/SFX/ambience volume, mouse sensitivity, invert Y, resolution,
window mode, quality), main menu (Continue, New Game, Load, Settings, Quit) over a live island backdrop, death screen,
ending.

## 10. Save / load

Three slots + autosave (every in-game dawn and on sleep). Everything in section 4's `UIslandSaveGame` row.

## 11. AutoPlay (contract v1.3)

Drop-in `UAutoPlaySubsystem` v1.3 (`ContractVersion` 3, unchanged). The game is one open-world island (`L_Island`);
a **scenario** is a defined start state on it plus a win/lose condition, applied by `StartScenario(N)`
(`AIslandGameMode::StartAutoPlayScenario`: time of day, day number, starting inventory, bot plan). Players never see
scenarios; New Game is the open island with the signal-fire + raft goal.

| `-Scenario` | Name | Start | Win | Lose |
|---|---|---|---|---|
| 1 | First Night | fresh start on the beach at 10:00 of day 1 with one coconut; daylight at normal speed (~8 min), the night ×6 faster | alive at 06:00 of day 2 | death |
| 2 | Toolmaker | day 2, 08:00, with a stone axe, 2 rope, 2 branches (what survived the night) | a stone pick and a canteen (crafted at a workbench the bot builds) in the pack | death |

Planned next: 3 "Ironworks" (smelt ore, iron pick), 4 "Raft and Signal" (the escape), added as the bot can win them.

(Changed while building the bot: scenario 1 starts earlier so a full shelter fits before dusk inside the pipeline's
600 s; scenario 2 originally asked for an iron pick, which needs the highland ore behind the rockfall gate — too long
for one run, so it now covers the workbench tier.)

Bot (`UIslandBotComponent`, `TG_PrePhysics`): a goal planner over the real game state (needs, inventory, recipes,
nodes, time of day) choosing the next goal (gather X, craft Y, build shelter, light fire, eat/drink, retreat inside at
dusk, fight/flee). Movement is nav-mesh path following through `IA_Move` + `IA_Look` deltas; gathering is aim at node +
`IA_Primary`; crafting via `IA_Inventory` + `IA_RecipeNext/Prev` + `IA_Craft`; building via `IA_BuildMode`,
`IA_BuildCycle`, `IA_Rotate`, aim, `IA_Primary`. Skill: reaction delay 0.1–0.9 s, look noise 0–8°, swing timing
error, planning quality (efficient vs wasteful gathering, shelter size), late retreat at dusk at low skill.
Telemetry: `state` 10 Hz (location, rotation, velocity, health, hunger, thirst, stamina, warmth, time of day, weather,
sheltered), `gather` {node, item, count}, `craft` {item}, `build_place` {piece, location}, `build_demolish`,
`eat`/`drink`, `damage` {source, amount}, `death`, `dusk`/`dawn`, `weather` {state}, `area_enter`, `score` (score =
items gathered + 10 × pieces placed + 100 × nights survived).

## 12. Recording

- `workflow.jsonl` rows `{schema, id ("is-NNNNN"), seq, time, actor:"agent", op, target, params, reason,
  reason_source:"agent_note", status, source{script, sha256, commit}}`, appended by `Scripts/wf.py` (shell: `Scripts/wf.sh`,
  editor scripts import it). `status`: observed / failed / reverted / unrecorded (`log.gap`).
- Every editor script that ran stays in `Scripts/` unchanged (a new version is a new file).
- Heavy jobs go through `C:\Users\Xiang\Work\tools\ue-heavy.ps1`.

## 13. Fab requests

Already in use (fetched by the asset scout, recorded in `assets.manifest.json`): Poly Haven CC0 scans (97: coast
rocks/cliffs, island tree, understorey plants, props, 28 surface sets), Megascans Alexandra Palm, Tree Branch, Nordic
Beach Rock Formation, Campfire (Fab Standard, $0), CC BY palms (Realistic Palm, Game-Ready Palm, Fan Palm), Monstera
B02/B03, Ribbon Grass, FOREST SOUNDS. These need **the user's Launcher step** (they are Unreal-format packs: Launcher →
Fab Library → *Add to project* → `asset-library\fab-ue\FabVault53`); all are UE 5.3-compatible:

| # | Listing | Price | Licence | Replaces / adds | Priority |
|---|---|---|---|---|---|
| 1 | [ANIMAL VARIETY PACK](https://www.fab.com/listings/2dd7964c-a601-4264-a53d-465dcae1644c) (Protofactor) | free (claimed) | Fab Standard | **Wolf → the night pack dogs, Pig → wild boar** (rigged, 20–26 anims each). Without it there are no animals in the game | **blocking** |
| 2 | [Soul: Cave](https://www.fab.com/listings/75f42402-40bb-4a1b-b557-18e2c9604273) (Epic) | free | Fab Standard | Sea-cave interior kit (walls, stalactites, wet rock) instead of rock scans arranged as a cave | high |
| 3 | [Survival Character](https://www.fab.com/listings/11d20d01-b764-4936-8163-cb20d05c369e) (Arberry, UE5 mannequin skeleton) | free (claimed) | Fab Standard | Castaway look for the player instead of the grey mannequin | high |
| 4 | [tropical Vegetation: Banana Plants](https://www.fab.com/listings/9dfde0b8-807c-4390-96ae-afa6a95aa573), [Pandanus Plants](https://www.fab.com/listings/55f17946-a4cf-4dac-955a-e97160600fe7), [Ground Plants](https://www.fab.com/listings/ef6db212-dfcf-4a50-8ade-fbca49963240) (Project Nature) | free | Fab Standard | Real banana plants for the fruit node, pandanus on the beach, jungle ground cover | high |
| 5 | [Procedural Sea Waves](https://www.fab.com/listings/2b11f781-970a-4c37-9ab2-90d16137555f) (MetaSound) | $0 Personal | Fab Standard | Surf, replacing the synthesized surf loop | medium |
| 6 | [Animal Sound Effect Pack](https://www.fab.com/listings/55dac71f-7a34-46fb-8076-513c7d821683) | $0 Personal | Fab Standard | Boar grunts, dog growls/barks/howls (now: fox/deer clips from Forest Sounds) | medium |
| 7 | [Acoustic Guitar Music Pack](https://www.fab.com/listings/4fcb44c5-7797-41ed-a1f0-6cc5f0ab1aae) | $0 Personal | Fab Standard | Menu, dusk and ending music cues (now synthesized stings) | medium |
| 8 | Tropical Jungle Pack (in the scout's cart) | $49.99 | Fab Standard | Coconut palms + jungle canopy trees (the island tree scan is heavy; palms are a mix of free models) | optional, paid |
| 9 | Realistic Boar (in the cart) | $69.99 | Fab Standard | A real boar instead of the re-textured pig | optional, paid |
| 10 | Survival Tools / Survival construction pack (in the cart) | $19.99 / $13.99 | Fab Standard | Tool meshes / building pieces (the game builds its own; these would only add polish) | optional, paid |

Nothing paid is required; items 1–4 are the ones that change what the player sees.

**Update 2026-10-11 07:20:** the asset scout now pulls Unreal-format packs directly (no Launcher step). Arrived and
UE 5.3-checked: ANIMAL VARIETY PACK, Realistic Boar (purchased), Tropical Jungle Pack (purchased), Soul: Cave,
Survival Character, Survival Tools, Banana/Pandanus/Ground Plants, Acoustic Guitar, Critters vol 2 (gulls), Atlantic
Ghost Crab. In the game so far: **Realistic Boar → BP_Boar, AnimalVarietyPack wolf → BP_Dog (the pack)** (rows
is-00317, is-00322..325), **Tropical Jungle Pack → node palms/trees + canopy and understory** (is-00318, jungle_redress_v1).
Procedural Sea Waves and Animal Sound Effect Pack were saved by a newer engine (`ue53_ok: false`) and are not usable.

## 14. Acceptance checklist

- [ ] Main menu (Continue, New Game, Load, Settings, Quit) over a live backdrop
- [ ] Settings: volumes, mouse sensitivity, invert Y, resolution, window mode, quality; persisted
- [ ] Pause: resume, save, load, settings, quit to menu; three save slots + autosave
- [ ] Third-person move, sprint (stamina), jump, swim (stamina, drowning) (surface swim with pack clips verified in shots; drowning not exercised)
- [ ] Needs: health, hunger, thirst, stamina, warmth with the rates above; HUD bars
- [ ] Day/night cycle; colder night; sleep in bed to dawn (cycle + night verified by AutoPlay; bed not yet)
- [ ] Weather: rain and storm affect wetness, warmth, thirst and visibility; lightning
- [x] Gathering: trees, palms, rocks, ore, bushes, fibre plants with hit feedback, drops, respawn timers (palms, trees, fibre, pickups verified by AutoPlay; rock/ore/bush implemented)
- [ ] Tool tiers hand → stone → iron gate nodes and areas (overgrowth, rockfall, cave grille)
- [ ] Inventory with stacks + hotbar; crafting at hand, workbench, campfire (cooking, smelting) (hand + workbench verified by AutoPlay; campfire recipes not yet)
- [x] Building: ghost, grid + socket snap, rotate, valid/invalid colour, cost, demolish/refund, support collapse (placement, snap, costs, validity verified; demolish/collapse implemented)
- [ ] Placeables: campfire, storage chest, bed (spawn), rain collector, workbench
- [ ] Shelter protects from rain/cold and from the night pack (shelter + fire detection verified; the pack vs shelter not observed)
- [ ] Boars by day, pack at night, simple AI; death drops pack at a marker; respawn at bed
- [ ] Four areas (beach, jungle, highland, cave) with gates; story lines, details, frieze payoff, feeding the pack
- [ ] Signal fire + raft → escape ending
- [x] HUD: needs, hotbar, prompt, compass, clock, toasts (styled survival UI: burlap/plank skin, painted craft icons, key-cap prompts; review shots)
- [ ] Look: Water plugin ocean, scanned materials, foliage, sky/clouds, Lumen, weather VFX — clearly beyond `island_explore`
- [ ] Audio: ambience per area/time, weather, gathering, footsteps, creatures, UI, music cues (all slots wired 2026-10-11 11:00 after finding the first Forest Sounds import was never saved; mix peaks at -1 dBFS in AutoPlay recordings; not yet listened to by a human)
- [x] AutoPlay scenario 1 (First Night) passes `validate-run.ps1`; tag `milestone/autoplay-1`; recording queued (scenario 2 too: `milestone/autoplay-2`; v1.3 migration re-tagged)
- [x] Packaged Win64 build (`Packaged/Windows/IslandSurvival.exe`, 3.0 GB; AutoPlay scenario 2 wins in it, validate-run PASS)
- [x] `assets.manifest.json` lists every external asset

## 15. Status

_Updated 2026-10-11 11:30 (session started 02:41). Second pass after the user asked for the bought/free packs, pack
animations and a fully styled UI._

**Verified working** (AutoPlay runs through Enhanced Input injection, telemetry, review shots):
- Core loop end to end: pick up branches/stones, strip fibre, craft rope + stone axe at hand, fell palms, build
  foundation → 3 walls → doorway → roof → campfire inside, open the door, light the fire, shelter detection, eat,
  survive the night. Scenario 1 won on seeds 1, 3, 5, 6, 7 (skill 1) and 4 (skill 0.5); after the second pass scenario 1
  seed 7 still wins (7 pieces, health 100) and scenario 2 wins in 75 s; validate-run PASS on all.
- Workbench tier: scenario 2 crafts a stone pick, places a workbench, crafts a canteen at it.
- Day/night, dusk/dawn; boars by day, the dog pack at the dens by night, running their AI states.
- Styled UI (review shots `Saved/Shots/ui3`, `menu1`): Barlow Condensed / IM Fell English / Caveat Brush family,
  burlap panels, plank buttons, wood slots painted from CC0 scans; Craft Resources icons on all 30 items and 13
  buildables; recipe rows with ingredient icon chips; build mode shows an icon strip and have/need cost chips;
  prompts show a key cap; serif title on the main menu, pause and ending.
- Pack animations on the castaway: RamsterZ Survival Animations (bought, retargeted UE4 -> UE5 Manny) for the
  horizontal tree chop, pick strike, hammering when placing pieces, craft hammering, flint at the campfire, canteen
  sips, kneeling to drink at water and filling the canteen; Motifect eat clip (retargeted) for eating; free packs for
  ground pickup, reach, spear thrusts and surface swim (buoyancy fixed so the swimmer floats head-and-shoulders out).
- Wildlife: 26 ghost crabs on the beaches (scuttle sideways, bolt and dig in), seagull flocks over the coast and
  crows over the jungle (VAT Niagara flocks, visible over the menu).
- Building: foundation, floor, wall and door frame from the bought Survival Construction kit (weathered planks),
  fitted to the 3 m cell; thatch hip roof and hinged plank door kept.
- Audio: footsteps per surface, swing, node hit/break sounds by kind (bark chops, pickaxe strikes, grass slices),
  rain/wind/thunder, day/night beds per area, springs, animal calls, UI clicks, doors, nailing.

**Implemented, compiled, not yet exercised end to end:** main menu actions / pause / settings / three save slots +
autosave; drowning; rain/storm effects; metal tier and gates; cave frieze payoff and feeding the pack; signal
fire + raft escape and both endings; death → pack marker → respawn at bed; chest, bed, rain collector.

**Left / known weak spots:**
- Eating is the Motifect clip (standing); the RamsterZ eating clips are seated, unused so far.
- Beach berm and escarpment read as plain green slopes; jungle floor litter too orange; sea cave still Poly Haven
  rocks (Soul: Cave downloaded, unused). Banana/pandanus/ground-plant packs unused.
- Dog pack is the wolf mesh as-is; the hat sits a little high.
- The construction kit's tier A only; stairs/roof still from the built kit. The craft-pack has no axe or torch icon:
  stone/iron axe use hammer-like tools, the torch a stick.
- AutoPlay covers scenarios 1–2 only.

**Where the content came from:**
- Built here: terrain + landscape material, roof/door/stairs of the building kit, fire/rain/ocean/ghost materials,
  synthesized surf/fire/stings, all UI code (C++ UMG) and the UI skin textures (painted from Poly Haven scans).
- Store (Fab, Unreal format, via the scout): bought — Realistic Boar, Tropical Jungle Pack, Survival Construction
  Pack, Survival Tools, Atlantic Ghost Crab, Critters Vol. 2 (crows & seagulls); free — Animal Variety Pack (wolf),
  Survival Character, Craft Resources Icons, Free Animation Library, Free Sample Animation Set, Acoustic Guitar
  Music Pack, Free Game SFX Starter, 50 Free Game Sounds; Fab FBX: Paragon animations retargeted to Manny,
  Megascans palm/branch/rock/campfire/grass.
- Scout (free/CC): 98 Poly Haven CC0 assets, CC BY palms/monstera, Forest Sounds (CC BY), OFL fonts.
  `assets.manifest.json`: 129 entries (URL, licence, version, files, changes).

**Packaged build:** `games/island-survival/Packaged/Windows/IslandSurvival.exe` (Win64 Development, 3.2 GB), rebuilt after
the second pass; AutoPlay scenario 2 wins in it in 66 s at 60 fps, audio peaks at -1.1 dBFS, validate-run PASS.

**Tags / recording:** AutoPlay contract v1.3 (scenarios, drop-in version 3). `milestone/autoplay-2` on bf92f9d
(scenarios 1-2 win, validate-run PASS, RamsterZ clips in). Recording queued:
`20261011-161128-458-island-survival-bf92f9d3.json` (scenarios 1-2, 2 runs); it replaced the not-yet-run fcab398
request. Earlier requests: 21ea558 failed (UnrealBuildTool collision), 31d2c19 ran "level 12" (enqueue array passed
through `powershell -File`); both superseded.

**Stats (at 16:30):** 489 workflow rows, 25 commits, 89 scripts under `Scripts/`, about 13.8 hours since the session
started at 02:41.

# Lantern Key (`island-survival`)

Fill-in for [../game-session.md](../game-session.md). Original prompt: [../original/game-island-survival.md](../original/game-island-survival.md).

| Placeholder | Value |
|---|---|
| `{{GAME_TITLE}}` | Unreal game 3: island survival |
| `{{SLUG}}` | island-survival |
| `{{PROJECT}}` | IslandSurvival (`IslandSurvival.uproject`, C++ module `IslandSurvival`, from the Third Person C++ template) |
| `{{GENRE_LINE}}` | a third-person ISLAND SURVIVAL game with resource gathering, crafting and a building flow |
| `{{VENDOR_BEAT}}` | samples/island_explore (a marketplace demo map, one placeable foundation, debug counters, no record of how it was made) |

## {{PITCH}}

You wake on the south beach of Lantern Key, a small volcanic island, with nothing but your hands. Gather, craft
tools that open the jungle, the highland and the sea cave, build a shelter before the cold night when the island's
dog pack hunts, and escape by lighting the signal fire and finishing the raft. The island tells, without a word of
exposition, who lived here and who the night hunters really are.

## {{BRIEF}}

- One open-world map `L_Island` (+ `L_MainMenu`): ~1.26 km generated landscape, island ~1.0 x 0.8 km, UE Water
  plugin ocean around it, landscape material by height/slope/noise (no paint layers). Areas gated by tool tier:
  beach (hands) -> jungle (stone axe clears overgrowth) -> highland with the dead lighthouse (stone pick breaks the
  rockfall; ore leads to iron) -> sea cave (iron pick).
- Character: Survival Character on the Manny base; sprint (stamina), jump, swim at the surface (stamina, drowning).
- Needs 0-100: health, hunger (empty in 30 min), thirst (20 min), stamina, warmth (day 80, night 35, rain -20, storm
  -35, wet -15, shelter +20, fire within 6 m +45, torch +15). Day = 20 real minutes; sleeping in a sheltered bed with
  no hunters near skips to 06:00. Weather: Clear -> Overcast -> Rain -> Storm (wetness, warmth, thirst, visibility,
  lightning).
- Gathering: pick up branches/stones by hand, pluck fibre plants and fruit (forage clips, not strikes), chop trees and
  palms with an axe, mine rocks with a pick; hit feedback, drops, respawn timers. Tool tiers hand -> stone (120
  durability) -> iron (300, x2 yield).
- Crafting: 24-slot inventory with stacks, first 8 slots = hotbar; recipes at hand (rope, stone axe/pick, spear,
  torch), at a workbench (canteen, iron axe/pick) and at a campfire (smelt ore, cook fish/meat). Data in
  `DT_Items`, `DT_Recipes`, `DT_Buildables`, imported from CSVs in `Data/`.
- Building (the core): `B` build mode, build bar with costs, ghost preview green/red with a reason, 300 cm grid +
  socket snapping, stilts on slopes, rotate (90 / 15 deg), place with a settle animation, demolish (hold X) refund
  100 % within 60 s then 50 %, unsupported pieces collapse. Pieces: foundation, floor, wall, doorway (hinged door),
  roof, stairs; placeables: campfire, workbench, storage chest, bed (spawn), rain collector. A roof + >= 5/8 blocked
  traces = sheltered; pack dogs cannot pass walls or closed doors.
- Threats: boars by day (charge when irritated, drop meat), the dog pack at night from dens (circle, lunge, fear fire
  and torches). Death drops the whole pack at a compass marker; respawn at the last bed.
- Endgame: signal fire on the headland beacon pad (ironwood, fronds, lamp oil) and the raft at the west-cove slip (logs,
  rope, ingots, sailcloth from the cave).
- HUD: five need bars with icons, wet / sheltered icons, hotbar, key-cap interaction prompt, compass, day + clock,
  toasts, area line. Panels: inventory + crafting, chest, pause (save, load, settings), settings (volumes, mouse
  sensitivity, invert Y, resolution, window mode, quality), main menu (Continue, New Game, Load, Settings, Quit) over a
  live island, death, ending. Three save slots + autosave at dawn and on sleep.
- Look: premium stylized-realistic tropical (turquoise shallows, coral sand, black volcanic rock, layered jungle),
  SkyAtmosphere + volumetric clouds, Lumen, moonlit blue nights, warm fires. Styled survival UI (burlap panels, plank
  buttons, painted icons; Barlow Condensed / IM Fell English / Caveat Brush), no plain text.

## {{SCENARIOS}}

Scenarios are AutoPlay test starts on the same open island; players never see them (the user asked for "scenarios",
not "levels").

1. First Night — fresh start on the beach at 10:00 of day 1 with one coconut; day at normal speed, night x6 faster —
   win: alive at 06:00 of day 2 / lose: death
2. Toolmaker — day 2, 08:00, with a stone axe, 2 rope, 2 branches — win: a stone pick and a canteen (crafted at a
   workbench the bot builds) in the pack / lose: death

Planned: 3 Ironworks (smelt ore, iron pick), 4 Raft and Signal (the escape). Score = items gathered + 10 x pieces
placed + 100 x nights survived.

## {{STORY}}

Lighthouse keeper Wren Halloway refused to leave without her four dogs when the light was automated in 1981, hid in
the sea cave until the relief boat gave up, and stayed for life; the night pack are her dogs' descendants, still
waiting for someone to come down the hill with food. Told by squared stone pads, enamel bowls, ochre hands at springs,
cairns, a clawed lighthouse door, four collar tags (BOSUN, PIP, JUNO, TACK), and one line per area ("Someone squared
these stones. They meant to stay."). Payoff: the cave frieze ("She stayed for them. They are still waiting for her.");
after it, feeding cooked food to dogs calms the pack, and at the raft ending ("Keep the light.") one dog swims after you.

## {{ART_PACKS}}

- `fab-ue\tropical-jungle-pack\` (bought): palms, canopy trees, understory for nodes and dressing.
- `fab-ue\realistic-boar\` (bought): `BP_Boar`. `fab-ue\animal-variety-pack\`: the wolf as `BP_Dog` (the pack).
- `fab-ue\survival-character\`: the castaway. `fab-ue\survival-construction-pack\` (bought): foundation, floor, wall,
  door frame (tier A); thatch roof, plank door and stairs are ours. `fab-ue\survival-tools\` (bought): tool meshes.
- `fab-ue\atlantic-ghost-crab\` (bought, beach crabs), `fab-ue\critters-vol-2-crows-seagulls\` (bought, Niagara flocks).
- `fab-ue\craft-resources-icons\`: icons for all items and buildables.
- Animation: `fab-ue\ramsterz-survival-animations\` (bought; chop, pick strike, hammer, craft, flint, drink, forage,
  retargeted UE4 -> Manny), `fab\motifect-daily-life-motion-pack\` (eat), `fab\paragon-animations-retargeted-to-manny\`,
  `fab-ue\free-animation-library\`, `fab-ue\free-sample-animation-set\` (pickup, reach, spear, swim).
- Megascans and CC BY plants (`fab\...`): `alexandra-palm-ukgkcilia`, `free-livistona-chinensis-fan-palm`,
  `realistic-palm-model`, `free-game-ready-palm`, `monstera-b02/b03`, `ribbon-grass-tbdpec3r`, `tree-branch-pcsvq`,
  `campfire-uenpfeifa`, `nordic-beach-rock-formation-vflrejtfa` (credits in `catalog.jsonl`).
- CC0: `polyhaven\island-models\`, `island-textures\`, `island-hdri\`, `island-request\`; ambientCG sand, thatch, lava.
- Audio: `fab\forest-sounds\` (CC BY, credit "FOREST SOUNDS by take"), `fab-ue\free-game-sfx-starter-pack-65\`,
  `fab-ue\50-free-game-sounds-pack\`, `fab-ue\acoustic-guitar-music-pack\`. Fonts: `fonts\BarlowCondensed\`,
  `fonts\Barlow\`, `fonts\IMFellEnglish\`, `fonts\CaveatBrush\`.
- On disk, not used yet: `fab-ue\soul-cave\` (sea-cave kit), `fab-ue\tropical-vegetation-banana-plants\`,
  `-pandanus-plants\`, `-ground-plants\`. Unusable in 5.3: `procedural-sea-waves`, `animal-sound-effect-pack`.

## {{GAME_NOTES}}

- User playtest: ground pickups slid away, plants were struck instead of picked, the character walked while the craft
  clip played. Fix: action clips plant the character (no moving, jumping or new interactions; a deliberate move after
  0.3 s cancels), the character turns to the target first, plants use forage clips, trees take axe hits and rocks
  pick hits to yield, a ground pickup lands when the hand reaches the ground (1.05 s into the clip).
- The user got motion sick while building: the camera rotated and jumped too much. Fix: spring-arm rotation lag, our
  own damped collision (pull in fast, ease out slowly, never closer than 1.5 m), no camera shakes or FOV kicks on
  actions; the bot turns the camera at most 90 deg/s with eased acceleration and jumps only over low obstacles.
- Build-piece cycling must never be blocked by the hammering clip (the bot's doorway depends on it).
- Swim buoyancy 1.38 keeps head and shoulders out of the water.
- The first Forest Sounds import was never saved; check that imported assets are saved before wiring sounds.
- Bot (`UIslandBotComponent`): a goal planner over real state (needs, inventory, recipes, nodes, time) acting only via
  `IA_Move`, `IA_Look`, `IA_Primary`, `IA_Inventory`, `IA_RecipeNext/Prev`, `IA_Craft`, `IA_BuildMode`, `IA_BuildCycle`,
  `IA_Rotate`. Scenario 1 builds foundation, 3 walls, doorway, roof and a campfire inside before dusk.
- Built but not exercised end to end: menus / pause / save slots, drowning, rain and storm effects, iron tier and
  gates, cave frieze + feeding the pack, signal fire + raft endings, death -> pack marker -> bed respawn, chest, bed,
  rain collector.
- Weak spots: beach berm and escarpment read as plain green slopes, jungle floor litter too orange, the cave is still
  Poly Haven rocks, the dog pack is the wolf mesh as-is, no axe/torch icon in the craft-icon pack.
- `-FramingShots` gives UI-on review captures (every 45 s, every 8 s while building): check them before a recording.
  Workflow row ids are `is-NNNNN`; rows carry the script's sha256.

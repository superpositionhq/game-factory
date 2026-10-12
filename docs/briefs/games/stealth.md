# GHOSTLINE (`stealth`)

Fill-in for [../game-session.md](../game-session.md). Original prompt: [../original/game-stealth.md](../original/game-stealth.md).

| Placeholder | Value |
|---|---|
| `{{GAME_TITLE}}` | Unreal game: stealth |
| `{{SLUG}}` | stealth |
| `{{PROJECT}}` | Stealth (`Stealth.uproject`, C++ module `Stealth`, from the UE 5.3 Third Person template) |
| `{{GENRE_LINE}}` | a third-person STEALTH game: steal one item per level past perception-driven guards and reach the exit |

## {{PITCH}}

GHOSTLINE: Wren, a thief for hire, takes three night jobs from a fixer: a warehouse ledger, a brass urn from a
manor garden, an archive keycard from an insurer's office. Guards patrol with vision cones painted on the floor; you
sneak, hide and distract, and the objects you steal turn out to be evidence about your own father's death.

## {{BRIEF}}

- Third-person thief (Rogue Character Model on the Manny skeleton): walk 330 (some noise), sprint 600 (loud),
  crouch 200 (silent); eased crouch camera. Interact `E` (grab item, enter/leave locker), throw a bottle (LMB / G,
  3 per level) that makes a loud noise where it lands.
- Visibility V: 1.0 standing, x0.6 crouched, x1.15 sprinting, x0.45 in shadow, x0.2 crouched in tall grass, 0 in a
  locker. A guard can make you out to `300 + (SightRadius - 300) x V` cm. Footstep noise events every 0.55 s walking
  (600 cm) / 0.33 s sprinting (1400 cm); throwable 1800 cm.
- Guards (Police Character body, red uniform tint) with AI Perception sight (1600 cm, 50 deg half-angle) + hearing
  (1800 cm) feeding a suspicion meter. States: Patrol -> Suspicious ("?" fills, investigate) -> Alert ("!", chase,
  catch at ~1.15 m) -> Search (last known spot + 3 nav points) -> Patrol. Nearby guards are radioed. A guard who saw
  you enter a locker opens it. Speeds: patrol 180, investigate 230, search 300, chase 480.
- Behavior Tree + Blackboard (built in C++ at runtime). Vision cones: floor fan meshes traced against walls, coloured
  by state (white / yellow / red / orange). "?" and "!" indicators clamped to screen edges.
- Objective per level: grab the item, reach the extraction zone; checkpoints; caught -> 2.2 s -> respawn at the last
  checkpoint with guards reset (item put back if taken after it).
- 3 levels: **Warehouse** (3 guards, shelving aisles, back office), **Courtyard at night** (4 guards with torches incl.
  a sentry, hedges, fountain, gazebo), **Office floor** (5 guards, cubicles whose low walls hide a crouched player,
  server room). Per-level time, times spotted, times caught and a GHOST / SHADOW / AGENT rating, bests saved.
- HUD: dossier objective card, segmented SEEN / NOISE meters with icons, bottle icons, key-cap prompts, alert banner,
  objective marker with distance, first-time tip cards. Main menu over a live diorama, level select with locks and
  bests, settings (master volume, mouse sensitivity, invert Y, resolution, window mode), how to play, pause (resume,
  restart checkpoint/level, settings, quit), results with a tilted rating stamp.
- Look: realistic night; cool blue moonlight with warm amber marking story objects; Fab environment packs over
  unchanged gameplay volumes. UI in an ink-and-amber palette, Barlow Condensed / Barlow / Share Tech Mono, icons drawn
  in code: no plain text.
- Sound: recorded footsteps and UI clicks, rain loop as night ambience; synthesized alert sting, suspicious blip,
  pickup, caught, checkpoint, locker, bottle, radio chatter and the story motif.

## {{SCENARIOS}}

1. Warehouse — `L01_Warehouse`, start vestibule SW, 3 bottles, no item — win: take the ledger in the back office and
   reach the loading-dock extraction / lose: `-MaxSeconds` runs out (a catch only sends you back to the last checkpoint)
2. Courtyard at Night — `L02_Courtyard`, gatehouse S, 3 bottles — win: take the relic (urn) in the gazebo and reach
   the west side gate / lose: timeout
3. Office Floor — `L03_Office`, stairwell SE, 3 bottles — win: take the keycard in the server room and reach the
   elevator / lose: timeout

## {{STORY}}

Two years ago the Lantern Street depot of Morrow Freight burned with the night watchman, Tomas Reyes, inside, and
Halden Mutual paid the claim. You play his daughter Wren; her fixer Mara sends one job per night by pager. The only
text per level is the pager line (`MARA: Morrow's back office. The ledger. Nothing else.`) and one extraction line;
the rest is a memorial plaque, stencilled crates, an engraved urn, a whiteboard, and short guard barks. Payoff in L3:
the whiteboard reads "ASSET RECOVERY: REYES": Mara works for Halden, and the ledger and urn were evidence being
recovered; Wren keeps the keycard ("Mara never worked for me. I keep this one.").

## {{ART_PACKS}}

- `fab-ue\modular-warehouse-interior\` (bought): L1 shell, roller door, pilasters, roof, beams, pipes, lamps.
- `fab-ue\industry-props-pack-6\`: racks, crates, cartons, barrels, pallets, litter (L1, menu diorama).
- `fab-ue\downtown-office\` (bought): L3 cubicles, monitors, copier, conference table, shelving; L1 back office.
- `fab-ue\city-park-environment-collection\`: L2 hedges, maples, lamp posts, benches, fountain, pergola, grass, ivy.
- `fab-ue\rogue-character-model\` (player), `fab-ue\police-character-npc\` (bought; guards, skeleton marked compatible
  with Manny).
- Animation: `fab-ue\stealth-locomotion-animation-set\` (bought; sneak cycles retargeted to Manny),
  `fab-ue\mocap-online-free-animation-pack\` (guard idle, power walk, jog, run, look-around walk),
  `fab-ue\free-sample-animation-set\` (pickup / locker moves, not wired yet).
- Audio: `fab-ue\essential-footsteps-sfx\`, `fab-ue\free-ui-soundpack\`, `fab-ue\sfx-essentials\` (rain loop).
- CC0: `polyhaven\stealth-models\`, `polyhaven\stealth-textures\`, `polyhaven\stealth-hdri\`, `ambientcg\Asphalt033\`.
- Fonts (OFL): `fonts\BarlowCondensed\`, `fonts\Barlow\`, `fonts\ShareTechMono\`.

## {{GAME_NOTES}}

- Camera: the user stopped the recordings because the camera kept pointing at the player's backside. Current rig
  (`UStealthSpringArm`): pivot at upper chest (+62 standing / +42 crouched), shoulder offset 40, arm 380, pitch -20
  clamped to [-65, -4], positional lag only, up-and-over swing before pulling in, thief dithers out within 55-130 cm.
  Check framing shots (`-CamShots`) before any recording.
- Movement: the user said "character movement sucks". Fix: native `UStealthAnimInstance` (no AnimBP graph) with all
  gait cycles on one left-foot-plant phase, play rate from measured cycle speeds, root locked; acceleration 2400,
  braking 2600, friction 8, turn 720 deg/s, applied in BeginPlay so the Blueprint can't mask them. `-StealthMoveTest`
  measures bone jumps and foot skate.
- Behavior Tree / Blackboard graphs cannot be authored from UE Python, so they are built in C++ at startup
  (`StealthGuardBehavior.cpp`); they show in the gameplay debugger, not as BT assets.
- Re-saving a map headless stores a `RecastNavMesh-Default` with an empty navmesh and guards stop moving: remove it and
  rely on runtime navmesh generation.
- Fixed exposure per level made unlit cones and glows vanish or blow out: route emissive through `EyeAdaptationInverse`.
- `MaterialEditingLibrary.delete_all_material_expressions` asserts on loaded materials: patch by inserting nodes.
- Instanced dressing actors (`AStealthTileStrip`, `AStealthScatter`): a static child under a movable root never
  attached and rendered everything at the world origin; dressing sits on top of unchanged gameplay blockers.
- Before the visibility-scaled sight radius, any line of sight made a guard suspicious and hiding only slowed the
  climb to alert. Guards freeze while a catch plays out and turn before walking (no backwards running).
- Tests: `-StealthTest` (12 checks per level), `-StealthLevel=N`. The bot wins scenario 1 at skill 1 (seeds 1-5)
  with patrol forecasts and timed crossings; scenarios 2-3 are not tuned for the bot yet.
- Open: spoken guard barks need a voice source licensed to ship (subtitles + synthesized radio chatter for now);
  per-surface footsteps; pack pickup/locker clips. Workflow row ids are `op-NNNNN`.

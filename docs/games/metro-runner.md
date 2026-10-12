# Ember Line: story bible and game design

Slug `metro-runner`, project/module `MetroRunner`, Unreal Engine 5.3, Windows.
Genre: three-lane endless rail runner, third person behind the runner.

## 1. The game in one paragraph

At the evening peak the old Underline, the rail tunnels that carry a city's trains and its power cables side by side,
trips its breakers one after another. Linemen call a cascade like that **the Hush**: lamp by lamp, signal by signal, the
dark rolls down the line toward Coldwell Generating Station, and when it reaches Coldwell the turbines trip and the city
stays dark for weeks. Coldwell can only restart from a charged starter cell. Wren Ashby, a nineteen-year-old cable
courier at Cinder Yard depot, has the only live one, the **Ember**, a brass cell glowing amber on a harness. The only
straight way to Coldwell is down the tracks, through the freight trains still running on automatic. Wren runs; the
player switches lanes, jumps, slides, grabs sparks and power-ups, and stays ahead of the dark. Dispatcher Tam talks
Wren through it on the radio (subtitles only), and Tam seems to know every sagging gantry on the line.

## 2. Story bible

### World

- **The city** is never named on screen. Its Underline has three districts on the route:
  - **Cinder Yard**: the underground maintenance depot. Concrete tunnels, sunk rails, sodium lamps, green guide lights,
    parked works trains and buffer stops.
  - **Ironside Cut**: an open-air freight cutting through the factory district at sunset. Cranes, container stacks,
    rusted wagons, signal gantries, loading ramps.
  - **Coldwell**: the generating station's approach at night. Brick boiler halls, steam pipes over the tracks, white
    floodlights, chimneys ahead.
- **The Hush** is not a monster. It is a cascade of tripping relays with a sound (a heavy *chunk* per relay, the mains
  hum dropping out) and a look (lamps behind Wren going dark one by one, a cold edge of darkness creeping in at the
  sides of the view). It moves a little slower than a clean runner and gains every time Wren scrapes something.
- **The last Long Dark** was twenty years ago ("'06"): the city was dark for forty days. Everyone over thirty
  remembers it. Nobody talks about who carried the cell that night.

### Characters

| Who | Role | How the player meets them |
|---|---|---|
| **Wren Ashby** | The runner. Cable courier, quick, a little reckless, trusted with the Ember because nobody else was at the depot. | The player character, seen from behind, Ember glowing on the back harness. |
| **Tam** (Tamsin Arlow) | Night dispatcher at Cinder Yard, in her fifties. Calm, dry, oddly specific about the route. | Radio subtitles only (a radio icon and "TAM"), never seen. |
| **The Hush** | The chaser: the cascade itself. | Lamps switching off behind, relay sounds, the edge-darkness gauge. |
| **The freights** | Driverless trains on automatic schedules; they don't stop for anyone. | Parked wagons, oncoming trains with headlights and horns. |

### How the story is told in play (never a wall of text)

1. **Tam's radio**: one short subtitle (under 15 words) at a few points per run, triggered by distance or by the first
   time something happens (first train, first gantry, first stumble). They double as the tutorial.
2. **Tally plates** (the collectible story fragments): stamped brass plates nailed to tunnel ribs and signal posts,
   three per district, placed off the easy line (on a wagon roof, in the lane next to a train). Picking one up shows its
   stamped line for a few seconds. They are signed "T.A. '06".
3. **The districts themselves**: lights going out behind you, the sun setting over Ironside, Coldwell's chimneys
   growing on the horizon, the station's floodlights.
4. **The late payoff**: the last plate in Coldwell reads *"Here's where it caught me. Cell went cold in my hands."*
   Tam, on the radio right after: *"That's where I dropped mine. In '06."* Then: *"Past my mark now, Wren. All yours."*
   Tam ran this exact route in the last Long Dark and didn't make it. Every hint she gave was her own route from twenty
   years ago, and the plates the player has been collecting were her markers. On a win, the result shows the lamps
   coming back on down the whole line, from Coldwell back toward the Yard.

### Tally plates (stamped text, one line each)

| # | District | Text |
|---|---|---|
| 1 | Cinder Yard | "T.A. '06. Cell's warm in my coat. Hush behind me. Going." |
| 2 | Cinder Yard | "Gantry by Shed 4 sags. Duck it every time." |
| 3 | Cinder Yard | "Yard Gate. Lights still on ahead. Good sign." |
| 4 | Ironside Cut | "Freights run blind when the Hush comes. Watch the near rail." |
| 5 | Ironside Cut | "Ramps up onto the wagons. Roofs are faster. Don't look down." |
| 6 | Ironside Cut | "Sun's going. Coldwell by dark, if the legs hold." |
| 7 | Coldwell | "Coldwell's chimneys. Never been this close at night." |
| 8 | Coldwell | "Relays dropping right behind me now. Loud as doors." |
| 9 | Coldwell | "Here's where it caught me. Cell went cold in my hands." |

The Route Log (main menu) shows the plates found so far as stamped brass on a board; finding all nine stamps "'06"
onto the Ember on the menu screen.

### Tam's radio lines (subtitles)

| When | Line |
|---|---|
| S1 start | "Cell's live, Wren. Yard's tripped. Run, and stay ahead of it." |
| first parked train | "Train on your rail. Slip to a clear one." |
| first low barrier | "Buffer block. Jump it." |
| first sagging gantry | "Sagging gantry. Get low and slide." |
| first spark line | "Grab the sparks. They keep the cell warm." |
| first stumble (any scenario) | "Easy! It gains every time you scrape." |
| S1 end (Yard Gate) | "Yard Gate's open. Ironside next." |
| S2 start | "Ironside Cut. The freights are on automatic. They won't stop." |
| first oncoming train | "Headlights! One's coming at you. Move." |
| first loading ramp | "Loading ramp. Take the roofs." |
| first power-up | "Grab that canister. Spare charge from the line crews." |
| S2 mid | "Sun's nearly down. Keep the pace." |
| S2 end (Coldwell Viaduct) | "Coldwell Viaduct. I can see the chimneys from here." |
| S3 start | "If it reaches the turbines, we're dark for weeks. Last stretch." |
| S3 surge | "It's surging. Don't you dare stumble." |
| after plate 9 | "That's where I dropped mine. In '06." |
| shortly after | "Past my mark now, Wren. All yours." |
| S3 win | "Slot it in!" then on the result: "Lights coming back. All the way down the line." |
| lose, crash | "Wren? ... Wren, answer me." |
| lose, caught | "It's got the cell. Line's dark." |

### Motifs

- Warm amber (the Ember, sodium lamps, sparks) against cold blue-black (the Hush).
- Relays: one *chunk* per lamp that dies behind you; their rhythm speeds up when the Hush gains.
- Light returning is the reward: every win ends with lamps re-lighting toward the camera.

### Tone

Tense but warm, small-scale, human. No villains, no violence, no gore. The danger is the dark and the trains.

## 3. Core loop and controls

Run forward automatically; read the three lanes ahead; dodge, jump and slide; collect sparks and power-ups; keep the
Hush gauge out of the red; reach the district's end (scenario) or go as far as possible (Endless).

| Action | Keyboard | Gamepad | Enhanced Input action |
|---|---|---|---|
| Lane left / right (one lane per press, swipe-style) | A / D, Left / Right | D-pad, left stick flick | `IA_Lane` (Axis1D, -1 / +1, Pressed trigger) |
| Jump | W, Up, Space | A (bottom face) | `IA_Jump` (Pressed) |
| Slide / roll (in the air: drop fast, then roll) | S, Down, Left Ctrl | B (right face) | `IA_Slide` (Pressed) |
| Pause | Esc, P | Start | `IA_Pause` |
| Menus | mouse, arrows + Enter | stick + A/B | UI actions |

## 4. Mechanics

### Runner (custom kinematics, no physics, deterministic per frame)

| Parameter | Value |
|---|---|
| Lanes | 3, centres at -420, 0, +420 cm (lateral Y; the wagons are 3.7 m wide) |
| Lane change | 0.22 s at constant lateral speed; a press during a change retargets |
| Forward speed | per scenario curve (below); ramps with distance |
| Jump | apex 135 cm, airtime 0.67 s at any speed (gravity 24 m/s^2) |
| Spring Coils jump | apex 540 cm, airtime 1.34 s (clears a wagon roof at 505 cm) |
| Slide / roll | 0.75 s, collision height 90 cm instead of 180 cm; Slide in the air = dive (fast fall) then roll |
| Ground | analytic: rail bed 0 cm, wagon roofs 505 cm, ramps in between (no physics traces) |

### Obstacles (per district the same function, different meshes)

| Type | Size | Answer | Hit from the front | Hit from the side |
|---|---|---|---|---|
| Low barrier (buffer block, crash barrier, valve manifold) | 100 cm high | jump (or change lane) | crash | stumble |
| Sagging gantry (cable tray, signal beam, steam pipe) | clear below 110 cm, blocks 110-260 cm | slide (or change lane) | crash | stumble |
| Parked wagon (works train, freight wagon, ore car) | 320 cm high, 12-24 m long | change lane, or ramp onto the roof | crash | stumble, bounced back |
| Loading ramp + wagon | ramp 6 m long rising to 320 cm | run up it and along the roof | none | none |
| Oncoming train (S2, S3, Endless) | 320 cm high, moves toward you at 6-14 m/s | change lane early | crash | stumble |
| Light clutter (cones, crates, sandbags) | 60 cm | jump or ignore | stumble | stumble |

- **Stumble**: short stagger animation, small speed loss, and the Hush gains 18 m.
- **Crash**: fall animation; the Hush washes over; run lost. **Arc Shield** turns one crash into a stumble.

### Pickups

- **Sparks** (the coins): small amber motes with a short trail, in lines and arcs (over jumps, along roofs). +1 each.
- **Power-up canisters** (glowing brass canisters with a coloured band):

| Power-up | Effect | Duration |
|---|---|---|
| Lodestone | sparks within 7 m (all lanes) drift to Wren | 10 s |
| Spring Coils | high jumps (onto wagon roofs without a ramp) | 10 s |
| Arc Shield | the next crash becomes a stumble; blue arc around Wren | until used or 20 s |
| Overcharge | sparks and distance score x2 | 12 s |

- **Tally plates**: story fragments (section 2).

### The Hush gauge

- Distance `D` between Wren and the Hush, starting at 40 m (S1), 32 m (S2), 26 m (S3), 40 m (Endless).
- The Hush moves at 97 % of Wren's speed, so clean running slowly widens the gap, capped at the start value.
- Stumble: `D -= 18 m`. S3 surges: at fixed distances `D` shrinks by 8 m over 2 s. `D <= 0` = caught (lose).
- Shown as an analog ammeter on the HUD (needle into the red), the edge darkness, and the relay rhythm.

### Score

`score = metres + 10 x sparks`, both x2 under Overcharge. Results: distance, sparks, plates found, time, best.

## 5. Track generation (procedural chunks from modular pieces)

- The track is a sequence of 32 m **chunks** (four 8 m rail pieces). Each chunk = district dressing (floor, three rail beds, side walls or
  verges, ceiling or sky-side props, lights) + an **obstacle pattern** (what stands in each lane over the 30 m) + pickups.
- `DT_Patterns` (DataTable rows): per row the obstacles per lane with start/end offsets, a difficulty tier 1-5, allowed
  districts, spark lines, power-up slot. Hand-written in a CSV in `Data/` so table changes are diffs.
- `DT_Dressing` per district: the modular meshes and their transforms for one chunk, plus variants (pillar spacing,
  lamp types, background set pieces every N chunks: cranes, chimneys, platforms).
- **Generator** (`AMRTrackManager`): a seeded `FRandomStream` picks the next pattern from the tier allowed at the current
  distance, rejects repeats, and runs a **fairness check**: a lane/time reachability search (the same one the bot uses)
  must find at least one path through the new chunk from every lane reachable at the end of the previous chunk, given
  the lane-change time at the current speed. Unfair picks are rejected (max 8 tries, then a safe rest chunk).
- Chunks are spawned 8 ahead and recycled 2 behind (actor pools; no spawning per frame during a run).
- **District transitions** happen inside a tunnel portal chunk: sky, sun, fog, post-process and music cross-fade over
  ~3 s while the view is enclosed.
- One map, `L_Underline`; the scenario picks the start district, its seed, the speed curve and the end distance.

## 6. Scenarios (AutoPlay contract v1.4)

| # | Name | Start state | Win | Lose |
|---|---|---|---|---|
| 1 | Cinder Yard | Cinder Yard tunnels, seed 1101, speed 10 -> 13 m/s, Hush 40 m behind, tiers 1-2 (parked trains, barriers, gantries, no moving trains), one Arc Shield, plates 1-3 placed | reach Yard Gate at 1,100 m | crash, or caught by the Hush |
| 2 | Ironside Cut | Ironside Cut at sunset, seed 2202, speed 13 -> 18 m/s, Hush 32 m, tiers 2-4, oncoming trains, ramps and roofs, all four power-ups, plates 4-6 | reach Coldwell Viaduct at 1,800 m | crash, or caught |
| 3 | Coldwell Run | Coldwell at night, seed 3303, speed 18 -> 24 m/s, Hush 26 m with 3 surges, tiers 3-5, plates 7-9 | reach the black-start switch at 2,400 m | crash, or caught |

- Seeds are fixed per scenario so the track is the same every run; `-Seed` seeds the bot's own randomness (reaction
  noise, spark greed) and is added to nothing else, so recordings of one scenario show the same district layout.
- Expected run lengths: S1 ~95 s, S2 ~115 s, S3 ~115 s (well under `-MaxSeconds` 600).
- Not an AutoPlay scenario: **Endless** ("Night Shift", from the menu): Cinder Yard -> Ironside Cut -> Coldwell -> back
  round, speed 10 -> 24 m/s over 4 km, random seed, best distance saved.
- Telemetry (besides the contract's `score`, `state` at 10 Hz, `restart`): `lane_change` {from, to}, `jump`, `slide`,
  `stumble` {obstacle, hush_m}, `crash` {obstacle, shielded}, `pickup` {kind}, `powerup` {kind, on}, `plate` {index},
  `hush_surge`, `district` {name}, `radio` {line_id}; `state` adds distance_m, speed_ms, lane, hush_m, sparks, powerups.
- `FinishRun` extra: distance_m, sparks, plates, stumbles, hush_min_m.

## 7. Camera (user rule: gentle, no motion sickness)

- Behind and above: 1250 cm back, 560 cm above the feet, looking at a point 1000 cm ahead of Wren at 120 cm height
  (about -11 degrees pitch); Wren is about 1/12 of the frame height. Settings: near (1050/500), far (1450/640). FOV 70, **constant** (no speed FOV kick), **no shake**, no roll, no camera cuts in play.
- Lateral: follows 70 % of Wren's lane offset with 0.35 s critically damped smoothing, so all three lanes stay in view
  and a lane change is a small slide of the view, not a jerk.
- Vertical: follows 40 % of a jump, 100 % of standing on a roof, smoothed over 0.4 s.
- Wren stays small in the lower third (about 1/8 of the frame height); the lanes 40-60 m ahead fill the middle.
- Tunnels are built tall enough (ceiling >= 650 cm) that the camera never needs collision; no spring-arm pops.
- Crash/caught: the camera eases to a stop over 1 s; no impact shake.
- Settings: camera distance (near / standard / far).

## 8. AutoPlay bot (plays like a skilled human, reads the lanes ahead)

- `UMRBotComponent` on the player controller, ticks in `TG_PrePhysics` before input, acts **only** through
  `UAutoPlaySubsystem::Inject` (`IA_Lane` with key "A"/"D", `IA_Jump` "W", `IA_Slide` "S").
- **Perception**: queries `AMRTrackManager` for obstacles, pickups and trains in each lane up to a lookahead time
  (moving trains projected forward by their speed).
- **Planning**: a small search over (lane, time) with actions {stay, left, right, jump, slide} at decision points;
  scores paths by survival first, then Hush margin, then sparks, power-ups and plates, then staying near the centre.
  Same reachability model as the generator's fairness check.
- **Human-likeness**: a reaction delay before acting on anything newly seen; one press per lane (no spam), a minimum
  0.15 s between presses; jumps only when needed or for a spark arc; small timing jitter; it sometimes takes a riskier
  spark line at high skill and misses one at low skill.

| Skill | Reaction | Lookahead | Timing jitter | Wrong-choice chance | Spark greed |
|---|---|---|---|---|---|
| 0 | 0.42 s | 0.9 s | ±0.12 s | 25 % | low |
| 1 | 0.16 s | 1.9 s | ±0.03 s | 0 % | high |

  (linear in between). Skill 1 should win all three scenarios; skill 0 usually stumbles and often crashes in S2/S3.

## 9. Systems, classes, data, maps

| Class | Role |
|---|---|
| `AMRRunner` (APawn) | capsule-sized kinematic runner, lanes, jump/slide/stumble/crash, power-up state, Ember light |
| `UMRRunnerAnimInstance` | native anim instance (no AnimGraph): run cycle by speed, jump start/loop/land, slide/roll, stumble, crash, all cross-faded |
| `AMRPlayerController` | Enhanced Input contexts (game / menu), pause, HUD ownership |
| `AMRGameMode` | scenario setup, win/lose, score, AutoPlay hooks (`ScenarioStarted`, `FinishRun`, telemetry) |
| `UMRScenarioData` (data asset) | per scenario: district, seed, speed curve, end distance, Hush start/surges, tiers, plates, radio cues |
| `AMRTrackManager` | chunk pooling, pattern selection, fairness check, obstacle queries for runner/bot |
| `AMRChunk`, `AMRObstacle`, `AMRTrain`, `AMRPickup` | track pieces, hazards (type + extents), moving trains, sparks/power-ups/plates |
| `AMRHush` | Hush distance, lamp-off sequence behind Wren, edge-darkness post-process, relay audio |
| `AMRDistrictDirector` | per-district lighting/sky/fog/post/music presets and cross-fades |
| `UMRRadioDirector` | Tam's lines by distance/event, subtitle queue |
| `UMRBotComponent` | AutoPlay bot (section 8) |
| `UMRSaveGame` | best per scenario and Endless, plates found, total sparks, settings |
| UI (UMG built in C++) | HUD, main menu, scenario select, Route Log, settings, pause, results |

Data in `Data/*.csv` imported into DataTables by script. Maps: `L_MainMenu` (Cinder Yard platform diorama, Wren idle
with the Ember, slow push-in), `L_Underline` (the runtime track). Editor work through UE Python in `Scripts/`.

## 10. Art direction and packs

Look: **sodium and ember**. Realistic PBR industrial sets, warm amber light sources against cold blue-black shadow,
volumetric fog in tunnels, Lumen GI. Each district has one strong palette: Cinder Yard (concrete grey, sodium amber,
green guide lights), Ironside Cut (sunset orange-violet sky, rust and teal containers), Coldwell (night blue, white
floodlights, steam). No primitives or flat colours in the final game.

| Need | From (library) | Notes |
|---|---|---|
| Cinder Yard tunnels, platforms, sunk rails, fences, guide lights, tunnel lamps | Metro Maintenance Station Pack (`fab-ue\metro-maintenance-station-pack`) | modular kit, ideal for 30 m chunks |
| Wagons, engines, cargo carts, containers, cranes, barrels, crash blocks, background towers and hangars | Factory Environment Collection (`fab-ue\factory-environment-collection`) | `SM_Train01`, `SM_TrainCar01/02`, `SM_TrainEngine01`, `SM_CargoCart01`; scale and look to verify in editor |
| Coldwell boiler halls, pipes, steam stacks | Modular Old Power Plant (`fab-ue\modular-old-power-plant-65-assets`) | |
| Extra industrial props | Industry Props Pack 6, Metro Maintenance fuse boxes | |
| Ballast, gravel, rusted metal, concrete | Poly Haven / ambientCG CC0 (rally/stealth sets on disk, Gravel023) | rail bed material |
| Sky (sunset, night) | Good SKY (`fab-ue\good-sky`) | |
| Wren | City Sample Crowds modular outfit (hoodie + work jacket) on the UE5 skeleton; fallback Survival Character | pick after a look in the editor |
| Run, sprint, jumps, slide, roll, stumble, fall | Game Animation Sample anims retargeted to Manny (`fab\game-animation-sample-anims-retargeted-to-manny`: Run, Sprint, Jump F start/loop/land, Land_Roll, Land_Stumble, Slide, Ragdoll) + Paragon-to-Manny hit reacts | FBX on the Manny skeleton |
| Sparks, arcs, steam, dust | Realistic Starter VFX Pack Vol 2, Niagara Dust, Item Destruction FX | |
| Icons | game-icons.net (lightning, magnet, spring, shield, plate) | CC BY 3.0 credit |
| Fonts | Barlow Condensed + Share Tech Mono (on disk); want Big Shoulders Display / Stencil (OFL, to ask the scout) | |

Fab requests: none yet. If the factory wagons don't read as rail freight at runner scale, or no crowd outfit reads as a
courier, a request (listing, price, licence, UE 5.3 support, what it replaces) goes to the coordinator before anything
is bought.

## 11. Audio

- Music: Racing Music Vol.1 (`fab-ue\racing-music-vol-1`), one track per district, cross-faded at portals; a calm cue
  for menus.
- Ambience and trains: Essential Ambience SFX (subway interior, trains passing, doors), City/industrial beds.
- Footsteps on concrete / metal / gravel: Essential Footsteps SFX; pickups and UI: Interface & Item Sounds.
- Synthesized: relay *chunk*, mains hum and its drop-out, the Hush rush, the Ember's charge chime, shield arc.
- No recorded or TTS voices: Tam is subtitles plus a short radio-squelch blip.

## 12. UI style: "signal-box enamel"

- Enamel plates (cream on deep teal) in brass bezels, stamped stencil numerals, analog gauges; frames rendered from
  CC0 painted-metal and brass textures through a UMG material (bevel, rivets, wear), no default font anywhere.
- HUD: distance plate top-left, spark counter in a brass token top-right, Hush ammeter bottom-centre, power-up badges
  with draining rings bottom-left, radio subtitle strip (radio icon + "TAM" in amber) above the gauge, plate pickup
  card centre-top for 3 s.
- Menus: a lit signal-box lever panel over the live diorama: Run (scenario select: three district cards with best
  distance and plates), Night Shift (Endless), Route Log, Settings, Quit. Pause and results in the same style.
- Settings: master/music/effects volume, resolution, window mode, graphics quality, subtitle size, camera distance.

## 13. Acceptance checklist

- [ ] Three scenarios playable start to finish; win and both lose cases (crash, caught) reachable.
- [ ] Endless mode loops all three districts with the speed ramp; best distance saved.
- [ ] Fairness check: 2,000 generated chunks per tier, every one passable (automated test).
- [ ] AutoPlay: skill 1 wins S1-S3 by hand-test, `validate-run.ps1` PASS, framing screenshots checked.
- [ ] Camera: no shake, no FOV change, runner in the lower third, lanes ahead readable in all districts.
- [ ] Art: Fab/CC0 sets in every district, animated runner, no primitives; lighting per district.
- [ ] UI: styled HUD, menus, settings, pause, results, Route Log; no default font.
- [ ] Story: Tam's lines, 9 plates, payoff in S3, lamps re-lighting on the win.
- [ ] Audio: music per district, ambience, footsteps, pickups, synthesized Hush.
- [ ] Packaged Win64 Shipping build runs; no forbidden names; scrub `--verify` 0 hits.

## 14. Status

- 2026-10-12: project created (`mr-00001`), story bible and design written. Next: coordinator OK, then build.
- 2026-10-12: design approved by the coordinator, with these review notes (now requirements):
  - Comfort: the Hush darkness and lamp switch-offs fade and creep, never flicker or strobe; the edge darkening stays
    soft and never covers the lanes the player has to read.
  - Readability at 24 m/s (S3): obstacles and lanes read at once; oncoming trains are telegraphed early with headlights
    and a horn; the runner stays small in the lower third.
  - Footage variety: S1 depot, S2 sunset cutting and S3 night power station must look clearly different; power-up
    effects visible.
  - Train scale and the runner's outfit: if the library assets don't fit, a Fab request with prices goes to the
    coordinator before anything is bought.
  - Licences: City Sample Crowds and the Game Animation Sample anims are recorded in `assets.manifest.json`.
- 2026-10-12 (build, first pass):
  - Built: shared runner simulation + beam-search planner (`MRCore`), chunk generator with a fairness check from
    every lane (40 ms timing slack), three district kits from the store packs, moving trains with headlights,
    pickups and power-ups, the Hush (gap, surges, lamps fading behind, edge darkness, relay sounds), Tam's radio and
    the nine tally plates, painted HUD and C++ menus (main, run select, Route Log, settings, pause, results), save
    game, native animation blending of 22 clips, synthesized SFX, AutoPlay bot.
  - Tests: `MetroRunner.Smoke.Fairness` passes (S1-S3 and three Endless seeds, 0 hits for a perfect runner);
    `MetroRunner.Smoke.Bot` passes (skill 1 wins S1-S3 on 4 seeds each; lower skills lose some runs).
  - Rendered hand tests (off-screen): S1 win, S2 win (validate-run PASS); S3 was stopped at 1,660 m by the slot hold.
  - Found and fixed on the way: depot kit paths, ScenarioMaps duplicates collapsing, ramp landing, planner step size
    and the bot's timing model (side hits), motion blur (off for comfort), washed-out depot, dark Ironside, glaring
    Coldwell floodlights.
  - Next: rebuild with the lighting and UI changes, run content_v2 (container colours, lamp glass, window glow, UI
    icons), screenshots of all three districts and the menu, framing set, recording request.

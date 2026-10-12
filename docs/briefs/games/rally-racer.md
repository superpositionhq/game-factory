# Last Run at Harrow (`rally-racer`)

Fill-in for [../game-session.md](../game-session.md). Original prompt: [../original/game-rally-racer.md](../original/game-rally-racer.md).

| Placeholder | Value |
|---|---|
| `{{GAME_TITLE}}` | Unreal game: rally racer |
| `{{SLUG}}` | rally-racer |
| `{{PROJECT}}` | RallyRacer (`RallyRacer.uproject`, modules `RallyRacer` + editor `RallyRacerEditor`) |
| `{{GENRE_LINE}}` | an off-road RALLY RACER with Chaos Vehicles, AI rivals and a time-trial ghost |
| `{{VENDOR_BEAT}}` | none |

## {{PITCH}}

The Harrow Valley Rally runs for the last time before a new dam floods the valley. You drive car #7, a restored
three-time winner, in three-lap races on loose gravel, desert sand and snow against four rivals with their own
liveries and driving styles. Nobody tells you the story: the roads, the car and the crowds do.

## {{BRIEF}}

- Car: `ARallyCarPawn` (from the Vehicle template's `AWheeledVehiclePawn`) with Rally Cars Pack bodies. Loose-surface
  tuning: AWD with rear bias (FrontRearSplit 0.65), rear wheels with less cornering stiffness and friction, high
  rear-only handbrake, front max steer 40 deg reduced with speed, lowered centre of mass, mild downforce.
- Off track (by distance to the spline) friction x0.7 plus drag; snow road ~0.82. Boost (Shift) meter, refills
  faster while drifting. Reset (R) to the last checkpoint at a free spot, 3 s ghosting through cars.
- 3 stages on ~1 km landscapes with a 12 m road corridor carved along a closed spline: **SS1 Pinewood** (forest dirt,
  2.3 km, 13 checkpoints, morning mist), **SS2 Red Rock** (desert canyon, 1.9 km, 11, noon), **SS3 Frostbite Pass**
  (snowy hills with crest jumps, 2.1 km, 12, dusk). Checkpoints in order (a skipped gate shows MISSED CHECKPOINT),
  3 laps, start grid for up to 6 cars.
- AI (3-5 rivals, 4 by default): racing-line look-ahead steering, target speed from track curvature with a braking
  pass, lane change to pass, rubber band x0.9-1.08 vs the player, reset when stuck 3 s or upside down; per-rival
  skill, noise, aggression and boost eagerness. Live positions, lap and total times, results table.
- Time trial: best-lap ghost (transform samples at 20 Hz, interpolated, translucent car) and best times saved.
- HUD: painted analogue gauge with speed and gear, standings ladder with team colours, position, lap, lap / total /
  best time, minimap, checkpoint arrow, boost bar, countdown READY / 3-2-1 / GO, pace-note arrows with tones (no voice).
- Menus: Race / Time Trial, track, opponents count, settings (master volume, resolution, window mode, steering speed,
  mouse look sensitivity, minimap, controls list), credits, pause (resume, restart, settings, quit), podium.
- Audio: synthesized engine from RPM and throttle (`USynthComponent`), skid and impact SFX, pace-note tones, racing
  music in menus and at the finish, ambience per stage, a horn at the SS3 finish.
- Look: photoreal scans over our terrain, a separate HDRI, sun, fog and grade per stage, wheel spray per surface;
  styled rally UI (timing boards, number ladder) in Saira Condensed / Rajdhani with no plain text.

## {{SCENARIOS}}

1. SS1 Pinewood — Forest stage, morning; 3-lap race; player #7 last on a 5-car grid behind #1, #4, #11, #23 —
   win: finish P1 / lose: finish P2-P5, or not finished within `-MaxSeconds`
2. SS2 Red Rock — Canyon stage, noon; same race setup — same win / lose
3. SS3 Frostbite Pass — Snow stage, dusk; same race setup (veteran #4 may salute on the last lap) — same win / lose

Score: 10 per checkpoint plus (racers + 1 - position) x 100 at the finish.

## {{STORY}}

A dam will flood the valley in spring; this is the last running, and #7 is Mara Kell's car, restored after she died.
Told only by stage cards (one line each: "By spring this road lies under forty metres of water." / "The dam wall closes
this canyon in March." / "Above the waterline. The only road that stays."), orange FSL 412 survey paint that drops from
above the road (SS1) to below it (SS3), empty homesteads, dam works, rival liveries and the veteran's salute.
Payoff at the SS3 finish: the whole valley lines the last straight with red flares, and a cairn holds a #7 door,
"M. KELL", with flowers.

## {{ART_PACKS}}

- `fab-ue\rally-cars-pack\` (bought): every car (2 bodies x 3 skins, wheel anim BP, bolt-on parts); liveries
  recombined and partly recoloured by our `M_RallyLivery`.
- `fab-ue\vehicle-wheel-vfx\` (bought): dirt / sand / snow wheel spray.
- `fab-ue\temperate-vegetation-spruce-forest\`, `-conifer-bushes-saplings-i\`, `-foliage-collection\`,
  `-meadow-flowers\` (Project Nature): SS1/SS3 forests, verges, memorial flowers.
- `fab-ue\rural-australia\`: SS2 eucalypts, grass trees, cliffs, rocks, logs; delineators and fences on all stages.
- Megascans (`fab\...`): surfaces `dirt-ground-xdhhefr`, `mud-tire-tracks-vbuqbg3ew`, `bright-desert-sand-sjzkfega`,
  `canyon-sandy-mud-wdunfjf`, `fresh-windswept-snow-ugspafgdy`, `trampled-snow-vcqnfdk`, `uncut-grass-oilpt20`;
  cliffs/rocks (desert-western-cliff, sandstone, nordic-forest-cliff, tundra rock); hay bale, concrete barrier, cone,
  fence post, wild/dry grass.
- `fab-ue\free-character-emote-pack\` (crowd, workers, farm family), `fab-ue\free-animations-pack\` (in-car loop, unused).
- `fab-ue\racing-music-vol-1\` (menu and finish), `fab-ue\free-city-nature-sounds\` (CC BY 4.0, credit Gregor Quendel:
  SS3 crowd, SS1 wind and leaves).
- `polyhaven\rally-hdri\`, `polyhaven\rally-textures\`, `polyhaven\rally-models\` (CC0); `fonts\SairaCondensed\`,
  `fonts\Rajdhani\` (OFL).
- Built here: terrain, roads, story props and printed signs (our TrueType rasteriser), lighting, all SFX, the UI.

## {{GAME_NOTES}}

- UE 5.3 Python cannot create landscapes: the editor module wraps `ALandscape::Import`
  (`URallyEditorLibrary::CreateLandscapeFromRaw`). Heightmaps come from Python and carve the road with the same
  Catmull-Rom as UE's spline, so corridor and spline agree to the centimetre.
- Chaos: `bReverseAsBrake` off (it turned any brake into full brake plus reverse; reverse is handled in the pawn),
  aggressive vehicle sleep off, CCD on all car bodies, gears at 4600 / 2200 rpm.
- The bot found a latched brake (S stayed on after the first press). Playtest fixes: keyboard steering is
  `IA_SteerLeft/Right`, most recent key wins (A+D used to cancel); chase camera arm 700, height 280, pitch -13, FOV 95.
- The user saw the left side of the HUD flashing: the standings ladder was rebuilt every 0.25 s and close cars swapped
  every frame. Ladder rows are built once and updated in place, a new order must hold 0.6 s, the off-road plate needs
  0.35 s to show and 0.8 s to clear. Keep it at <= 3 ladder updates per 10 s.
- Stacked cars produced absurd contact impulses (cars launched at thousands of km/h): depenetration cap, a clamp above
  300 km/h that restores the last sane velocity, blow-ups reset to the last checkpoint; #11 aggression lowered to 0.75.
- No driver figures: the only in-car loop in the packs is a standing pose (the mannequin stood through the roof);
  seated clips exist only on the ActorCore skeleton.
- The bot (`URallyAutoPlayBot`) computes with the same `FRallyDriver` as the AI and injects `IA_Throttle`, `IA_Brake`,
  `IA_Steering` (scaled up to beat the player's high-speed steering cap), `IA_Handbrake`, `IA_Boost`, `IA_Reset`.
- Run `--framing N` (`-FramingShots=N`) before a recording: car about 1/6 of the frame, road ahead visible.
- Known: AI still bumps and resets on SS2 (#23 can fail to finish); the veteran's salute has never been seen in a
  test; spectators are tinted mannequins. Workflow row ids are `rr-NNNNN`.

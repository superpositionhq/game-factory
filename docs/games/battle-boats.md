# IRON GANNET: story bible and game design

Third-person naval action, Unreal Engine 5.3, C++ module `BattleBoats` (project `BattleBoats`, slug `battle-boats`).
Status: **approved 2026-10-12; offline build during the slot hold** (see section 15).

## 1. The game in one paragraph

You command the *Gannet*, an old coal-fired fishery gunboat refitted for war, the only warship of the Holm League, a
league of twelve fishing towns spread across the cold basalt islands of the Skerrow Reach. The Sarne Crown has
declared the Reach a "protected sea" and blockades it with ironclads and licensed raiders. You steer with an engine
telegraph and a rudder, feel the ship's weight and momentum, lob arcing shells from a forward turret and broadside
quick-firers, lead your shots onto moving ships, launch torpedoes and drop mines, and keep the ship alive by fighting
fires, pumping floods and sending repair parties. Between missions the towns send iron, and the ship is rebuilt from
their gates, cranes, rails and bells. Three missions: gunnery trials in Skerry Sound, a convoy run down the Grey
Mile, and a storm battle against the Crown's armoured cruiser at Hallow Rock.

**Not a duplicate of the other games:** you sail and fight a moving ship (no static artillery puzzle as in
siege-catapult, no racing as in rally-racer); the sea is open water between islands, not a seawall interior
(fps-breach); you never leave the ship (island-survival).

## 2. Story bible

**Rule: show, don't tell.** No cutscenes, no text walls. Story lines are signal-flag hoists that the ship's
signaller reads aloud as one subtitle (under 15 words), plus short crew calls. At most one story line per area;
everything else is in the islands, the ships, the flags, the cargo, the light and the weather.

### World

- **The Skerrow Reach**: a cold northern archipelago of black basalt islands, sea stacks, kelp beds and grey-green
  water. Era of coal and steel, invented (no real dates, places or navies): steam engines with tall funnels,
  turreted breech-loading guns, self-propelled "fish" torpedoes, contact mines, signal flags and heliographs.
- **The Holm League** (the player): twelve fishing towns (Skarre, Lysholm, Ronnet, Kettleby, Ostby, Hallow,
  Fenmouth, Tarn, Ulla, Saltness, Dunmere, Brisk) that share pilots, harbours and a council. Colours slate blue and
  bone white; emblem the **League knot** (a ring of rope tied in a twelve-turn knot, one turn per town).
- **The Sarne Crown**: the mainland kingdom to the south. It wants the Reach's harbours and its pilots, who know the
  only safe channels north. Its ships are long, dark and well armed. Colours oxblood and black; emblem a black
  seven-pointed star. Ship names are legal words: *Edict*, *Warrant*, *Decree*, *Statute*.
- **The Gullwake**: raiders who sail under Crown licence: fast steam launches and torpedo boats patched with scrap
  plate. Colours soot grey; emblem a grey gull's wing on black.

All flags, emblems, hull schemes and ship designs are invented. No real navy insignia, ensigns or ship names.

### The ship and crew

- **The *Gannet***: built thirty years ago to chase poachers off the cod banks. One forward gun turret, two
  quick-firers on each beam, a stern torpedo tube pair and a mine rail. Slow to turn, hard to sink. Her bell hangs
  in front of the bridge and rings every watch.
- **You, the Captain**: never seen, never named, never voiced. You are the telegraph, the rudder and the orders.
- **Wren Ostby**, signaller: the youngest aboard; reads every hoist through a long glass and is the voice of the
  story lines. Portrait: oilskin hood, a knot of signal halyard around the wrist.
- **Aud Kettle**, bosun: an old Kettleby fisherman; runs the pumps and the hoses. Calls flooding and fire.
- **Pell Morrow**, chief engineer: speaks for the boilers and the rudder gear. Calls speed and engine damage.
- **Sabine Orr**, gunner: commands the turret. Calls splashes, hits and reloads.

Crew are shown as painted portraits on the HUD crew board and as small animated figures on deck (if a fitting
sailor pack is available, section 12). Their lines are subtitles with a synthesized murmur, never recorded or TTS
voices.

### Premise (never stated outright)

The League has **one** warship. Everything else is a bluff. The League's signal stations hoist orders "to the
fleet" in plain code so the Crown will read them; in quiet coves there are "squadrons" of timber and canvas with
painted gunports. To keep the one real ship fighting, the twelve towns strip themselves: harbour gates become armour,
crane arms become the turret's gun-house, the rails of the fish quay become torpedo tubes, and the church bells are
melted for shell bronze. The player is never told this; they work it out.

### How it surfaces in play

- **Signal hoists.** A row of flags appears at the top of the HUD; Wren decodes it in one line. Early signals talk
  about "the fleet", "Squadron Two" and "the line". The player assumes the League has ships offscreen.
- **The refit.** Between missions the upgrade cards say what each upgrade is made of and which town gave it:
  "Belt plate: Skarre harbour gate", "Gun-house: Ronnet crane arm", "Shell bronze: Lysholm bell". It reads as
  flavour text.
- **The hull blueprint.** The HUD damage diagram labels each hull zone with the town whose iron covers it once
  that upgrade is fitted. Damage control is literally saving a town's gate.
- **The islands.** S1: towns with smoke from every chimney and a bell in every tower. S2: the bell towers stand
  empty and the harbour gates are gone. S3: the towns are dark in the storm.
- **The cargo.** In S2 the colliers carry something lashed under tarpaulins. Sail close and the wind lifts a
  corner: church bells, bound for the foundry.
- **The cove squadron (optional).** In S1 and S2 a "League squadron" lies at anchor in a far cove. Sail within
  300 m and Wren says: "Those guns are painted on canvas, Captain."

### Beats per mission

| # | Mission (scenario) | Light / weather | Story line (one hoist, Wren reads it) | Optional discovery (results screen) |
|---|---|---|---|---|
| 1 | Skerry Sound (gunnery trials) | clear spring morning, light swell | "Shore to Gannet: the fleet is watching your trials." | cove squadron: "Canvas guns. Somebody painted a fleet." |
| 2 | The Grey Mile (convoy escort) | overcast afternoon, moderate swell, fog banks | "Kettle Line to Gannet: Squadron Two holds the north channel." (the raiders come from the north) | bells under the tarpaulins: "The colliers carry church bells. For our shells." |
| 3 | Hallow Rock (storm battle) | storm at dusk, heavy swell, rain, distant lightning | start: "All League ships, form on Gannet." / mid: "Captain... there's no one forming on us." / end (Edict): "Where is your fleet?" Gannet's reply hoist: "HERE." | — |

**Payoff.** In S3 the hoist "All League ships, form on Gannet" is answered by nobody. The Crown flagship sees it
too, and it is why she came: she is hunting a fleet. When the *Edict* strikes her colours she hoists "Where is your
fleet?" and the *Gannet* answers with one word: "HERE." The results screen (ship's log page) ends: "There never was
a fleet. Twelve towns built one hull." The main menu changes after S3: the hull blueprint shows every plate labelled
with its town, all twelve knot turns filled in, and the bells are back in the towers of the menu harbour.

Recolouring: the "fleet" in every earlier signal was a bluff aimed at the enemy; the upgrades were the towns
taking themselves apart; every fire you put out was in somebody's harbour gate.

### Tone

Stoic, salt-weathered, quietly hopeful. No gore: hits are fire, smoke, steam and splinters; beaten ships list,
burn and settle, or strike their colours, and their crews take to the boats. No villain speeches: the Crown is
cold and procedural (its signals read like legal notices).

### Motifs

- **Visual:** the League knot (twelve turns); flags as speech; empty bell frames; canvas guns; the one funnel of
  the *Gannet* against long lines of Crown smoke.
- **Audio:** the ship's bell (synthesized, a soft bronze strike) rings watches, marks a completed repair and,
  at the payoff, rings twelve times. A modal theme on low strings and a concertina-like reed (synthesized) that
  thins out from S1 to S3 and returns full at the win.
- **Mechanic reframed:** repairs and damage control are protecting what the towns gave; the refit is the story.

### What the player learns, where

| Where | What |
|---|---|
| S1 signals, cove squadron | the League talks about a fleet; the fleet in the cove is canvas (optional) |
| Refit cards | the upgrades are made of the towns' gates, cranes, rails and bells |
| S2 islands and cargo | the towns are emptying themselves; the bells are going into the shells |
| S2 signal + raiders from the north | "Squadron Two" never existed |
| S3 hoists | no one forms on the Gannet; the Gannet is the fleet |

### Crew calls (gameplay barks, subtitles under 15 words)

| Event | Speaker | Example line |
|---|---|---|
| fire started | Aud | "Fire in the forward hold! Hoses!" |
| flooding | Aud | "Water coming in aft. Pumps, Captain?" |
| fire out / flood stopped | Aud | "Fire's out." / "She's holding." |
| engine hit | Pell | "Boilers hit. I can give you half, no more." |
| rudder jammed | Pell | "Rudder's jammed. Repair party to the stern!" |
| splash short / over | Sabine | "Short." / "Over." / "Straddle!" |
| hit | Sabine | "Hit! She's burning." |
| torpedo in water | Wren | "Torpedo wake, starboard bow!" |
| enemy sinking / strikes | Wren | "She's striking her colours." |
| convoy ship hit | Wren | "The Marta's hit. She's slowing." |

Each line plays once per cooldown (8-20 s per type) so the screen never fills.

## 3. Controls

Keyboard and mouse, gamepad in parallel. Every action is an Enhanced Input action (`IA_*`), so the AutoPlay bot
can drive everything.

| Action | KBM | Gamepad | Notes |
|---|---|---|---|
| `IA_Telegraph` (step up/down) | W / S | D-pad up/down or right trigger/left trigger tap | Full Astern, Half Astern, Stop, Slow, Half, Full, Flank; the ship accelerates toward the ordered speed |
| `IA_Rudder` (axis -1..1) | A / D | left stick X | rudder angle follows input at the steering-gear rate; centres on release |
| `IA_Look` (2D) | mouse | right stick | orbits the camera; the guns train toward the aim point |
| `IA_Aim` (hold) | RMB | left trigger | calm zoomed aim view |
| `IA_FireMain` | LMB | right trigger | turret salvo when loaded and the target bearing is inside the arc |
| `IA_FireSecondary` | Q / E | LB / RB | port / starboard quick-firers at the aim point (beam arcs) |
| `IA_ShellType` | R | Y | AP / HE for the main gun (reload applies) |
| `IA_Torpedo` | T | B | launch a two-torpedo spread along the aim bearing (stern tubes, rear arc + quarter) |
| `IA_Mine` | F | D-pad down (hold) | drop a contact mine from the stern rail |
| `IA_Pumps` | 1 | D-pad left | stop leaks, drain flooding (cooldown) |
| `IA_Hoses` | 2 | D-pad right | fight fires (cooldown) |
| `IA_Repair` | 3 | X | repair party: restores the worst module, some hull (cooldown) |
| `IA_Smoke` | Shift | left stick press | funnel smoke screen (upgrade, limited) |
| `IA_Pause` | Esc / P | Start | pause menu |

## 4. Core loop and campaign

**Mission loop:** read the hoist → sail to the action (telegraph + rudder; momentum, turning circle) → pick a
target → angle the ship (armour and gun arcs both depend on it) → range and lead shots, watch the fall of shot,
correct → torpedo or mine when they close → fight fires and floods, repair → win or sink → results (ship's log).

**Campaign:** Mission 1 → refit → Mission 2 → refit → Mission 3. Missions replay from the chart (main menu) once
unlocked. **Iron** is earned per mission (targets sunk, convoy ships saved, damage avoided) and spent at the refit.

### Upgrades (refit, data table `DT_Upgrades`)

Two tiers each. Every card names its town and what was taken apart.

| Line | Tier 1 / Tier 2 effect | Made of |
|---|---|---|
| Belt plate | +30 % / +60 % armour on bow and midships | Skarre harbour gate |
| Gun-house | +25 % turret traverse, -10 % / -20 % reload | Ronnet crane arm |
| Boilers | +8 % / +15 % top speed, faster acceleration | Lysholm distillery copper |
| Torpedo tubes | +1 torpedo per spread / faster reload | Kettleby quay rails |
| Pumps and hoses | -20 % / -40 % damage-control cooldowns | Fenmouth fire engine |
| Plotting table | shows a lead marker for the main gun / for torpedoes too | Ostby schoolhouse clock |
| Shell bronze | HE fire chance +, AP penetration + | Lysholm and Tarn bells |
| Smoke | funnel smoke screen x1 / x2 | Dunmere smokehouse |

## 5. Ships and movement

### Feel

Heavy and readable: a ship takes seconds to answer the telegraph and the rudder, carries way when stopped, turns in
a wide circle that tightens at lower speed, heels slightly outward in hard turns and pitches into the swell. The
hull rides the Water plugin waves; the **camera does not** (section 7).

### Model (`UBBShipMotion`)

Kinematic, deterministic integration in C++ (not rigid-body physics), so AI, bot and player ships behave the same
and never tunnel or explode:

- Speed: ordered speed from the telegraph step × class top speed; `accel` / `decel` per class; water drag;
  flooding and boiler damage scale the cap.
- Turning: rudder angle (steering gear rate per class) × speed factor → yaw rate, with a minimum steerage speed;
  slight drift (sideslip) in turns.
- Buoyancy: four (bow, stern, port, starboard) samples of the water surface from the Water plugin
  (`UWaterBodyComponent::GetWaterSurfaceInfoAtLocation`) give heave, pitch and roll of the hull mesh, low-pass
  filtered per class (big ships move slowly). Flooding per zone adds trim and list; sinking lowers the hull until
  it settles under.
- Collisions: swept hull capsule against islands (rocks) and other ships; ramming does damage by closing speed.
- Wake: Niagara wake ribbon and bow spray scaled by speed; Water plugin's water-body waves for distant motion.
  Floating debris, targets and mines use the Water plugin's `UBuoyancyComponent`.

### Ship classes (`DT_ShipClasses`)

| Class | Side | Length | Top speed | Armament | Role |
|---|---|---|---|---|---|
| *Gannet* (fishery gunboat) | League (player) | 68 m | 13 m/s | 1 turret (2 guns), 4 quick-firers, 2 stern tubes, mine rail | everything |
| Collier (Kettle Line) | League (convoy) | 80 m | 7 m/s | none | escorted |
| Timber target / towed target | League (S1) | 30-50 m | 0 / 5 m/s | none | gunnery targets |
| Gullwake launch | raiders | 24 m | 17 m/s | 1 light gun | flanker |
| Gullwake torpedo boat | raiders | 40 m | 16 m/s | 2 torpedo tubes, 1 light gun | torpedo runs |
| Crown sloop *Warrant* class | Crown | 60 m | 11 m/s | 3 broadside guns per side | kiter |
| Crown armoured cruiser *Edict* | Crown (boss) | 120 m | 10 m/s | 2 turrets, 6 broadside guns, bow tubes, stern mine rail | flagship |

Game ranges are compressed for readability: gun engagement 250-2200 m, torpedo run 1200 m.

## 6. Weapons and damage

### Gunnery

- **Ballistic shells** (`ABBShell`): integrated per tick with gravity and light drag; flight time 2-7 s. The aim
  point is where the camera ray meets the sea (or a ship); the turret solves the elevation to hit it (lower arc)
  within its limits. Turret traverse rate is real: the reticle shows where the guns point now and where they will
  settle.
- **Lead:** the player leads by hand: place the aim point ahead of a moving ship. Splashes give fall-of-shot
  feedback (short / over / straddle). The *Plotting table* upgrade adds a faint lead marker.
- **Dispersion:** salvo spread grows with range, own speed and turning; shrinks while steady.
- **Shell types:** AP (penetration vs armour, few fires), HE (fire chance, splinter damage, poor penetration).
- **Quick-firers:** fast, light, beam arcs only; good against launches.
- **Torpedoes** (`ABBTorpedo`): straight runners at set depth, visible bubbling wake; spread of 2 (3 with the upgrade);
  a hit floods a zone heavily. Can be dodged by turning into or away from the track.
- **Mines** (`ABBMine`): floating contact mines (buoyancy component), armed after 5 s, last the mission.

### Damage model (`UBBDamageModel`)

- **Hull zones:** Bow, Forward, Midships (boilers), Aft, Stern. Each has plate HP, armour thickness and a leak
  rate. Hits resolve to a zone by box components on the hull.
- **Penetration:** effective armour = thickness / cos(impact angle); AP penetrates if its pen (falling with range)
  exceeds it, else ricochet or shatter. Angling the bow to the enemy matters.
- **Modules:** main turret, quick-firer groups, torpedo tubes, boilers (speed cap), steering gear (rudder can jam).
  Damaged modules work worse; destroyed ones stop until repaired.
- **Flooding:** hits low on the hull and every torpedo open leaks; water per zone rises over time → trim, list,
  speed loss; too much → founders.
- **Fire:** HE and boiler hits can start fires; fire burns HP per second, makes smoke, may spread to the next zone.
- **Damage control:** Pumps (stop leaks, drain), Hoses (put out all fires), Repair party (worst module back to
  working, some HP). Each has a cooldown; using them well is the skill. Repairs end with the ship's bell.
- **Defeat:** hull HP of the ship reaches 0 or flooding exceeds the reserve buoyancy. AI ships may strike their
  colours below 10 % instead (flag lowered, engines stop, crew to the boats); that counts as sunk.

## 7. Camera (user rule: gentle, the user gets motion sick)

- **Stabilised rig**: a camera root follows the ship's *filtered* position (heave removed, 1-2 s lag) and its yaw is
  only the player's orbit. The horizon never rolls; wave pitch and roll never reach the camera.
- **Default:** behind and above the ship, ~55 m arm, 14° down, ship in the lower third, never filling the screen.
  Spring arm with collision against islands; probe never into the water.
- **Aim view:** hold RMB: the rig eases (0.8 s ease-in-out) to a higher, longer view along the aim bearing; FOV eases
  70 → 45 (no snap, no kick); mouse sensitivity drops 50 %. Release eases back.
- **No shake** on firing, hits or explosions; no FOV kicks; no camera motion from waves. Lightning in S3 is a slow,
  dim sky flash (no strobe).
- Optional "follow shell" is off by default (and never used in recordings).

## 8. Enemies and AI (`UBBShipAI`)

- **Formations:** line-ahead (Crown), wedge (Gullwake). The leader steers; followers hold slots in the leader's frame
  by adjusting speed and rudder. Formations break when the leader dies or when a role takes over.
- **Roles:**
  - *Kiter* (sloop, cruiser): holds a range band, turns to bring the broadside to bear (target 60-110° off the bow),
    reverses course rather than closing.
  - *Flanker* (launch): runs for the player's quarter (120-160° off the player's bow, outside the turret arc), then
    makes gun runs and breaks away.
  - *Torpedo runner* (torpedo boat): zig-zag approach at full speed, launches a spread at 600-900 m on a predicted
    intercept, turns away 120°, re-arms out of range.
  - *Raider vs convoy*: picks the weakest collier unless the player is within 800 m and hurting it (threat score).
  - *Boss* (*Edict*): line-ahead duel at long range; below 60 % HP drops mines astern and turns to fire bow
    torpedoes; below 35 % calls torpedo boats; strikes colours at 10 %.
- **Enemy gunnery:** predicts the player's position by velocity × time of flight, adds seeded dispersion by skill,
  and corrects after each splash (bracketing) like a gun crew.
- **Enemy damage control:** same three actions with a reaction delay.
- All randomness from the scenario seed (`FRandomStream`), so a scenario replays the same way for the same inputs.

## 9. Scenarios (AutoPlay contract v1.4)

| # | Name | Map | Seed | Start state | Win | Lose | MaxSeconds |
|---|---|---|---|---|---|---|---|
| 1 | Skerry Sound | `L_SkerrySound` | 1101 | *Gannet* at Slow ahead at the Sound's mouth, base refit, clear morning, low swell. 3 moored timber targets at 600/900/1400 m, then 2 targets towed by a tug at 5 m/s, then one Gullwake launch enters from the north passage. | all 5 targets and the launch sunk | *Gannet* sinks | 480 |
| 2 | The Grey Mile | `L_GreyMile` | 2207 | *Gannet* at Half ahead beside three colliers in column on a 4 km channel between islands to Lysholm harbour. Refit: Belt plate 1, Plotting table 1. Overcast, moderate swell, fog banks. Waves: 2 launches (flank from the islands), 2 torpedo boats (out of the north fog), a Crown sloop + a launch. | convoy arrives with 2+ colliers | 2 colliers lost, or *Gannet* sinks | 600 |
| 3 | Hallow Rock | `L_HallowRock` | 3313 | *Gannet* at Full ahead, refit: Belt 2, Gun-house 1, Pumps 1, Plotting 1, Shell bronze 1. Storm at dusk, heavy swell, rain. Crown line-ahead: the cruiser *Edict* + 2 sloops at 2.5 km; 2 torpedo boats join at the *Edict*'s 35 %. | *Edict* sunk or strikes her colours | *Gannet* sinks | 720 |

The campaign uses the same scenario setups with the player's own refit. AutoPlay skips menus and applies the fixed
refit above. Win/lose/timeout is metadata only.

Telemetry rows (game side): `shot_fired`, `shell_hit` (zone, pen/ricochet), `torpedo_launched`, `torpedo_hit`,
`fire_started`, `flood_started`, `dc_used`, `ship_sunk`, `colours_struck`, `convoy_ship_lost`, `signal_shown`,
`discovery`, `objective` and `SetScore` (iron earned).

## 10. AutoPlay bot (`UBBBotComponent`, injection only)

Reads game state directly, acts only through `AP->Inject`, scaled by `Skill`.

- **Navigation:** desired heading from the tactic; rudder via `IA_Rudder` with a PD controller (no oscillation);
  telegraph steps via `IA_Telegraph` (one step per decision, a human cadence). Island avoidance: forward probe fan +
  per-map lane waypoints.
- **Tactics:** pick target (convoy threats first in S2, the *Edict* in S3 once escorts are down or when it is closest);
  keep a range band where its guns outrange launches; turn to open the turret arc and to angle the bow to heavy
  guns.
- **Aim:** moves the camera with `IA_Look` deltas, rate-limited and eased like a hand on a mouse; aims at the lead
  point (own solution: target velocity × shell time of flight, iterated twice) plus skill error; corrects from its
  own fall of shot; fires `IA_FireMain` when loaded and the reticle settles; holds `IA_Aim` while ranging long
  shots; uses quick-firers on launches inside 700 m.
- **Torpedoes and mines:** torpedo when a target is within 900 m in the stern/quarter arc with a good intercept;
  mine when a launch or torpedo boat chases astern.
- **Damage control:** reacts after 0.5-1.5 s (skill): Hoses on fire, Pumps on leaks, Repair on a jammed rudder or a
  dead turret; never wastes a cooldown on nothing.
- **Evasion:** turns into torpedo tracks it sees within 500 m.

## 11. Maps and world

Three scenario maps plus `L_MainMenu`, built by committed editor scripts (`Scripts/build_*.py`):

- **Water:** UE 5.3 Water plugin (Water Body Ocean + Water Zone; Gerstner wave asset per map: S1 calm, S2
  moderate, S3 heavy), shoreline foam on the islands, underwater post process; `UBuoyancyComponent` for floating
  objects. Splash columns, bow spray, wakes and foam trails as Niagara systems tuned per shell size.
- **Islands:** black basalt and grass-topped cliffs (Poly Haven coastal cliffs, Nordic beach rock, Icelandic biome
  sampler, basalt columns), sea stacks, kelp beds near shore, small harbour towns with smoke, bell towers, piers.
- **Sky and light:** Good Sky + Poly Haven HDRIs; volumetric clouds and fog; S3 rain (Niagara), dim distant
  lightning, darkened towns.
- `L_MainMenu`: the *Gannet* at anchor in Skerre harbour at dawn, slow orbit-free establishing view.

## 12. Art direction and assets

**Look:** realistic, cold and weathered: soot-stained funnels, rust bleeding from rivets, grey-green sea, black
rock, white spray, warm brass on the bridge. League ships in slate blue and bone white; Crown ships oxblood and
black; Gullwake soot grey with scrap patches. Never primitives or flat colours; every ship from a quality pack,
re-textured to the faction scheme with original insignia decals.

**On disk now (library):** UE Water plugin (engine), Good Sky (UE5), Poly Haven HDRIs (day, island, night),
Poly Haven coastal cliffs / coast rocks / modular wooden pier, `fab\nordic-beach-rock-formation`,
`fab\updraft-art-icelandic-biome-pack-sampler`, `fab\small-basalt-column-sample`, Free Realistic Niagara
Explosions, Realistic Starter VFX Vol 2 (smoke, fire), M5 VFX Vol2 Fire and Flames, Water Materials (CC BY),
Critters Vol 2 (seagulls), Modular Rural Cabins (town houses), Essential Ambience SFX, Free Game SFX packs,
game-icons (CC BY 3.0), fonts (Big Shoulders Stencil Display, IM Fell English, Barlow Condensed).

**Fab requests (ships are missing from the library).** The asset scout found no game-ready 1890s gunboat or
pre-dreadnought pack on Fab, so the fleet is kitbashed from WWI-era and fictional hulls, restyled to the invented
faction schemes with our own ensigns (any real insignia painted out). Personal tier, before tax; needs the user's OK.

| # | Listing | Price | Format / UE | Role in the game |
|---|---|---|---|---|
| 1 | V25-class torpedo boat (warship) | $14.99 | OBJ | the *Gannet* (player), slate blue and bone |
| 2 | Anti-Air Light Cruiser "Ignis" (Red Kaiser) | $14.99 | FBX | the *Edict*, Crown flagship (fictional design) |
| 3 | Old Ship Collection (MiradorStudio) | $14.99 | UE 4.10-5.7 | separate turrets, rudders, propellers, funnel smoke; spare hull for the Crown sloops |
| 4 | Military Gunboat 01 (TF3D) | $4.99 | FBX, 2K PBR | Gullwake launches |
| 5 | Medium-sized steamship (SmallMeatMeat) | $6.99 | FBX | Kettle Line colliers (convoy) |
| 6 | Universal naval gun mount 57 mm (IgYerm) | $9.99 | FBX, 4K | Gannet turret and quick-firers, raider guns |
| 7 | PIR - Sea Mine (Dekogon) | $5.99 | FBX, 4K | contact mines |
| 8 | Modular Norway Lofoten Houses (Lucapy) | $24.99 | UE 4.24-5.8 | League fishing towns |
| 9 | Realistic Water Explosions Pack (MassiveFx) | $34.99 | UE 4.26-5.4 | shell splash columns, torpedo and mine blasts |
| 10 | Niagara Smoke (SoerGame) | $2.99 | UE 5.3-5.8 | funnel smoke, fire smoke, smoke screen |
| 11 | Easy Rain (William Faucher) | $24.99 | UE 5.3-5.8 | S3 storm rain |
| 12 | Cannon Sound FX (cplomedia) | $4.99 | UE 5.0-5.8 + WAV | gun reports |
| 13 | Storm in the Sea SFX (SoundVibeStudio) | $7.99 | WAV | S3 storm, waves, thunder |
| 14 | Lighthouse & Foghorn Coast SFX (MoodFrog) | $4.99 | WAV | horns, harbour, coast |
| | **Total** | **$178.86** | | |

Optional: WARSHIPS - Cruiser Class II ($34.99) as a distinct Crown sloop hull; Niagara WaterFoam Splash Pack
($34.99) for bow foam. Free, already downloaded: two trawlers (CC BY: Romain Ferre, Charlie Catling) as Gullwake
torpedo boats (raiders are converted fishing boats), Lighthouse (CC BY, DylanHayes), Dock Pier (CC BY, Pixol3d),
Harbor Props vol.1 (Fab Standard). Until the ships land, every class uses a stand-in hull flagged
`bPlaceholderMesh` (generated by `Scripts/make_placeholder_hulls.py`), never shipped in a recording.

## 13. UI (styled, no plain text)

Style "chart room": brass and enamel instruments on dark oilcloth, ink-on-blueprint diagrams, signal flags in
colour. Fonts: Big Shoulders Stencil Display (headings, numbers on brass), IM Fell English (crew lines and
signals), Barlow Condensed (small labels). Icons from game-icons, recoloured to brass.

- **Engine telegraph** (bottom left): a brass dial with the seven orders, needle eases to the order; speed in knots.
- **Compass ring + rudder arc** (bottom centre): heading, rudder angle, ordered vs actual.
- **Hull blueprint** (bottom right): the ship's outline in ink; five zones tinted by state; fire and water icons;
  town labels on fitted plates; module pips (turret, quick-firers, tubes, boilers, steering).
- **Weapons rail**: reload rings for turret / port / starboard / tubes / mines; AP/HE token; damage-control buttons
  with cooldown sweeps and key glyphs.
- **Reticle**: a thin brass ring with a range readout in cables, the guns' current bearing ghost and splash ticks;
  no circular range-ladder or ribbon awards (avoid other naval games' UI).
- **Signal strip** (top centre): the hoist as flag icons, then Wren's decoded line beneath, fading after 5 s.
- **Crew board**: four small portraits light up with their subtitle line.
- **Menus:** main menu (chart table: mission chart, refit, settings, quit), settings (master/music/effects volume,
  resolution, window mode, mouse sensitivity, invert Y), pause, refit screen (upgrade cards with the town knot and
  what it was made from), results (a ship's log page: ships sunk, hits, fires fought, iron earned, discovery line).

## 14. Audio

Synthesized and library SFX only, no voices: gun reports with distance low-pass, shell whistle, splashes by size,
hull hits (metal clang + splinter), fire crackle, pump clatter, steam vents, boiler rumble scaled by telegraph,
telegraph bell rings, ship's bell, seagulls (S1), wind and rain (S3), distant thunder (synthesized rumble). Crew
lines carry a soft synthesized murmur under the subtitle. Music: modal theme, sparser per mission.

## 15. Status and open items

**2026-10-12 20:40.** Playable in the editor and as a packaged Win64 Shipping build (842 MB cooked, no leak hits).

- All three scenarios run under AutoPlay v1.4 with validate-run PASS (one run each; results are metadata):
  S1 win 282 s, S2 lose 425 s, S3 lose 388 s. Tags `milestone/autoplay-1`, `milestone/autoplay-3`.
- Water plugin ocean with three Gerstner sea states; hulls ride four wave samples; the camera rig never takes heave,
  pitch or roll; aim view only narrows the lens; framing checked by the coordinator (HUD clear of the ship, labels
  stacked).
- Islands from Megascans and Poly Haven rock scans; lighthouses and piers from free CC BY packs; raiders on the free
  trawler hulls; fire, explosions and sea ambience from the copied packs; synthesized SFX and score.
- Story in play: signal hoists S1-S3 including the payoff exchange, crew calls, the canvas-squadron and bells
  discoveries, refit cards naming the towns, ship's-log results with the payoff line, changed menu line after S3.

Open:
- [ ] Fab purchase (section 12) with the user: real League/Crown hulls (stand-ins are flagged), splash columns,
      wakes, rain, town houses (bell towers, dark towns). No recording until the hulls land.
- [x] UE-format packs moved under `Content/Fab/` (reference fix-up; two unloadable UE4 destructible meshes removed).
- [ ] Sea colour toward the cold grey-green of the Reach.

## 16. Acceptance checklist

- [ ] Premium water (Water plugin ocean, buoyant ships, wakes, spray, splash columns), ships from quality packs.
- [ ] Ship handling with telegraph, rudder, momentum; arcing shells with lead; torpedoes; mines.
- [ ] Hull zones, armour angle, flooding, fire, damage control, repair.
- [ ] Enemy formations; flanking, kiting and torpedo-run AI; boss flagship.
- [ ] Refit upgrades between missions; save/load of campaign and settings.
- [ ] Story: hoists, refit cards, island changes, cargo, cove squadron, the S3 payoff, the changed main menu.
- [ ] Gentle stabilised camera, calm aim view, no shake, horizon never rolls.
- [ ] Styled UI everywhere, no default font.
- [ ] Main menu, settings, pause, results; packaged Win64 Shipping build.
- [ ] AutoPlay v1.4: S1-S3, validate-run PASS, framing screenshots reviewed.
- [ ] No studio, tool or vendor names anywhere in the game content (naming rule).

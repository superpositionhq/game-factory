# TIDEBREAK: story bible and game design

First-person shooter, Unreal Engine 5.3, C++ module `FpsBreach`. Slug `fps-breach`.
Status: **approved 2026-10-12; in production** (see section 11).

## 1. The game in one paragraph

Tonight is the Ninth Tide, the highest of the year. The Halvard Barrier, three kilometres of sluice gates, pump
halls and turbine galleries, is all that keeps the sea out of Varo Low, the harbour district built below the
waterline. Every screen in the city says the barrier is failing and Varo Low must be evacuated. You are a Keeper,
one of the engineers who ran the barrier until the Ostrand company bought the contract and replaced them with
armed automatons. You don't believe the screens. You go in through the old service tunnels with a carbine, a
shotgun and an EMP launcher to find out what the barrier is really doing, and to stop whoever plans to open the
gates at high water.

## 2. Story bible

### World

- **Varo**, a cold northern port city some decades from now. **Varo Low** is the old harbour district: narrow
  streets, tenements and fish markets, all of it three metres below the high-tide line.
- **The Halvard Barrier** is a seawall the city's lock-keepers' guild (**the Keepers**) built two generations ago.
  It is a working industrial machine of sluice towers, pump halls, turbine galleries and a crest road, run
  by hand and by old analogue gauges. The Keepers read every gauge in chalk on the pipe beside it, every night,
  initialled. That habit is the thread that runs through the whole game.
- **Ostrand Civic Solutions** bought the barrier's maintenance contract eighteen months ago. It laid off the
  Keepers, installed its own digital monitoring screens ("BARRIER INTEGRITY nn %") and guards the site with
  **Ostrand Sentinels**: tall, graphite-plated security automatons with an amber visor strip. They are machines
  following a security directive, not people. When they are beaten they power down, kneel and go dark. No blood
  and no gore, anywhere.
- **The lie.** Ostrand's own posters, seen everywhere, promise "VARO LOW: A NEW WATERFRONT". To get the land it
  needs the district condemned. So its screens show the barrier failing (61 %, then 44 %, then 23 %), the city
  orders an evacuation, and at 21:40 on the Ninth Tide Ostrand will open the sluices "for emergency relief".
  The flood will do the condemning. The barrier itself is fine. It always was.

### People

- **You: Ren Aldane**, a third-generation Keeper and a former harbour-militia marksman. Your family's street is in
  Varo Low. Never seen or heard; you are your gloved hands, your Keeper's field kit and your choices. You fight
  because the water will come into houses you know by name.
- **Mags (Magda Fenn)**, retired chief Keeper, on the radio from the city side over the Keepers' old intercom
  network. Dry, practical, fond of you. She taught you to read the gauges. Her lines are subtitles only (no
  recorded or synthesized voice), a radio click and a short burst of static, each line under 15 words.
- **Ostrand**: never a face. Present through its screens, posters, schedule boards, its automatons and the
  flat announcement chimes over the PA (shown as styled text, "OSTRAND SECURITY: ZONE 4 LOCKDOWN").

### How the story is told in play (never a wall of text)

| Where | What the player sees or hears | What it means (fully clear only at the end) |
|---|---|---|
| S1 yard | A big Ostrand screen on the seawall: "BARRIER INTEGRITY 61 % / EVACUATE VARO LOW". Next to it on a pipe gauge, faded chalk: "98 M.F." | Mags's last reading before she was laid off, against Ostrand's number. |
| S1 yard | The Keepers' drill yard is half dismantled; their lockers are stencilled with names, one is yours. | Who the Keepers were; you belong here. |
| S1 end | Mags: "Good. You still shoot like your mother. Tide's at nine-forty." | The clock starts. |
| S2 tunnel | Ostrand posters: "VARO LOW: A NEW WATERFRONT", an architect's render of glass towers where the fish market is. | The motive, before you know it is one. |
| S2 turbine gallery | Every screen says 44 %. Every analogue gauge reads in the green, with fresh chalk: "98 M.F." and today's date. | Someone has been coming in at night to read the real gauges. |
| S2 panel B | A schedule board: "SLUICE RELEASE 21:40 / AUTHORISED: OSTRAND". | The flood is planned. |
| S2 lift | Mags: "That chalk's mine. I never stopped checking. Neither should you." | Mags has been inside, alone, every night. |
| S3 crest | Screens now say 23 %, red and flashing; the sea is high but the wall is dry and solid under the floodlights. | The player can see for themselves the wall is holding. |
| S3 control room | The Keepers' analogue gauge desk, unplugged and pushed into a corner under a dust sheet. | The real data was there all along, cut off. |
| S3 payoff | You patch the Keepers' gauge line into the uplink and hold it. Every screen on the barrier, and the skyline of Varo beyond, flips from red "23 %" to "INTEGRITY 98 % / HOLDING". The sluice order cancels. Dawn starts at the horizon. Mags: "Ninety-eight. Told you." | Every warning seen in all three scenarios was the weapon. The barrier never failed. |

Scenario title cards, one line each:
- 1. *Calibration Yard*: "The Keepers trained here. Ostrand calls it scrap."
- 2. *Pump Hall*: "Every gauge in here has a name chalked next to it."
- 3. *Ninth Tide*: "High water at 21:40. Hold the wall."

Motifs: the chalk reading "98 M.F." (every scenario); the integrity screens counting down (61, 44, 23, then 98);
the amber visor of the Sentinels against the sodium-amber work lights of the Keepers (same colour, two owners);
the tide clock on the HUD (S2 and S3, a styled 21:40 countdown, in-fiction).

Tone: grounded, stormy, determined, with warmth from Mags. Concrete, rain, salt, sodium lights, steel, in a
clean low-poly style.

## 3. Core loop

Move through a combat space toward an objective → Sentinels detect you → fight from cover: pick shots, manage
the magazine, switch weapons for range, flush cover with the EMP launcher → Sentinels reposition and flank, you
keep moving → clear or bypass, pick up ammo and health → complete the objective (breaker, uplink, lever), get a
radio line and a checkpoint → next space. Pace: combat beats of 30–90 s separated by quieter traversal with
environmental story.

### Controls (all Enhanced Input actions, so the bot can do everything a player does)

| Action | Keyboard / mouse | Gamepad |
|---|---|---|
| Move / look | WASD / mouse | left / right stick |
| Sprint | Left Shift (hold) | left thumb |
| Crouch | C / Left Ctrl (toggle) | right face (B) |
| Jump | Space | bottom face (A) |
| Fire | Left mouse | right trigger |
| Aim (slight zoom, FOV 90 → 75, slower sway) | Right mouse (hold) | left trigger |
| Reload | R | left face (X) |
| Weapon 1 / 2 / 3, next / previous | 1 / 2 / 3, mouse wheel | top face (Y) cycles |
| Interact (hold) | E | left face (X) hold |
| Pause | Esc | Start |

### Movement and camera (comfort first; the user gets motion sick)

- Walk 320 cm/s, sprint 560 (no firing while sprinting; 0.2 s sprint-to-fire), crouch 170, jump 420 cm/s up,
  air control 0.3. Crouch lowers the camera 88 → 50 cm over 0.2 s (eased, never a snap).
- **FOV 90** by default (settings 80–100). Aim-down-sights narrows to 75 over 0.18 s (eased).
- **Head bob: off by default**; a setting "subtle" gives 0.4 cm vertical only, no roll. No landing dip beyond
  2 cm. No camera roll anywhere.
- **No screen shake.** Recoil is a small pitch kick that recovers by itself (carbine 0.3°, shotgun 1.0°, launcher
  0.8°), plus weapon-model kick in the hands. Taking damage shows a soft edge vignette and a directional arc on the
  HUD, never a camera jolt.
- Motion blur off (post-process `MotionBlurAmount 0`), no chromatic aberration, no lens distortion; mild film grain
  off. Exposure eased slowly (2 s adaptation) so walking from dark tunnels into floodlights is not a flash.
- Weapon sway: gentle, lagged 0.08 s behind the view; idle breathing 0.2 cm.

## 4. Weapons (distinct feel)

| Weapon | Mesh (low-poly kit, section 7) | Type | Numbers | Feel |
|---|---|---|---|---|
| **KR-7 "Tern" carbine** | Infima AG14W | Hitscan, full auto | 600 rpm, 30-round mag, 150 reserve, 16 damage, visor ×2, spread 0.6° → 2.5° bloom, aim 0.25°, reload 2.1 s (1.6 s with a round chambered) | Precise mid-range workhorse, tracer every 3rd round |
| **"Mallet" combat shotgun** | Infima MAK12 (magazine-fed, semi-auto) | Hitscan pellets | 9 pellets × 10 damage, 6.5° cone, falloff 8 → 20 m, 8-round magazine + 40 reserve, 110 rpm, reload 2.6 s (3.2 s empty) | Close quarters, staggers a Sentinel at short range |
| **"Lantern" EMP launcher** | Infima LRAF9 frame, canister round | Projectile (lobbed canister) | 1,400 cm/s, full gravity (about 20 m range); aimed at a surface it flies the low arc that lands there, at open sky it flies along the view; bursts on impact or after 2.5 s; radius 420 cm: 55 damage + **stun 2.5 s** (Sentinels freeze, visor flickers, cannot shoot), 1 loaded + 5 reserve, reload 1.2 s | The special: flush or freeze a group behind cover, opens the Bulwark's back core |

Ammo pickups: carbine box (+60), shells (+12), EMP canisters (+2). Health: Keeper med kit (+40; low-poly
med kit in Keeper orange). No health regeneration except back to 25 if below it, slowly (forgiveness).

Hit feedback: crosshair hit marker (white tick on hit, amber on visor hit, a short amber ring on a kill),
a soft "tick" hit sound layered by surface (metal plate for Sentinels), sparks and plate chips on Sentinels
(Niagara), directional hit-react animations (front/back/left/right), stagger on heavy hits, and a power-down
death (kneel, visor fades out with a falling hum, the body stays as cover-height debris).

## 5. Enemies: Ostrand Sentinels

Low-poly automatons (a low-poly robot set, section 7, retargeted to the UE5 mannequin skeleton): graphite
plating, hazard-orange Ostrand markings and an emissive amber visor strip. Animated with the Lyra
rifle/pistol/shotgun locomotion, hit-react and death sets (UE5 Manny). Their sounds are synthesized servo whirs and chirps, never voices.

| Type | Weapon | HP | Behaviour |
|---|---|---|---|
| **Warden** | carbine (bursts of 3–5) | 100 | Takes cover, peeks to fire, suppresses, flanks when given the flank token |
| **Breacher** | shotgun | 140 | Closes in along flank routes, rushes when you reload, retreats behind cover below 30 % |
| **Bulwark** (S3) | heavy carbine, long bursts | 320 | Slow, front-armoured (half damage from the front); an EMP stun or a flank exposes the glowing back core (×2.5) |
| Training sentry (S1) | paint rounds (3 damage) | 60 | Warden behaviour, slower reactions |

### AI (C++ AIController + world squad coordinator, no Behavior Tree assets)

States: `Idle/Patrol` → `Alert` (sees you, or hears gunfire within 25 m) → `TakeCover` → `PeekFire` →
`Reposition` / `Flank` / `Rush` (Breacher) → `Retreat` (low HP) → `Stunned` / `Stagger` → `Down`.

- **Cover:** placed `AFBCoverPoint` actors (stand/crouch, facing, peek side) plus a sampled check: a point is cover
  if a trace from the player's eye to the Sentinel's head at that point is blocked. Score = distance band
  (6–22 m), blocks line of sight, not taken, angle from squadmates, path length.
- **Squad coordinator** (`UFBSquadSubsystem`): at most 2 Sentinels fire at once (attack tokens, rotated every
  2–4 s), at most one flanker at a time. A flanker is sent when you have stayed behind the same cover more than
  5 s: it picks cover more than 60° around you from the squad's current line.
- **Shooting:** hitscan with visible tracers. Accuracy grows while you stay exposed (0.6 s warm-up), drops when you
  move, sprint or crouch behind cover; the first burst after spotting you always misses (warning shots). Damage
  per round: Warden 7, Breacher pellets 5 × 8, Bulwark 9.
- **Fairness:** a red-orange glint and chirp on the visor 0.4 s before a burst; never more than two shooters;
  no shots from outside your view cone in the first 2 s of an engagement.

## 6. Scenarios (AutoPlay contract v1.4)

All randomness comes from `FRandomStream(Seed)`: pop-up order, patrol starts, cover choices, flank timing,
spread. One map per scenario.

| # | Name | Map | Start state | Win | Lose |
|---|---|---|---|---|---|
| 1 | **Calibration Yard** (training range) | `L_CalibrationYard` | Morning, overcast. The Keepers' drill yard behind the seawall. Carbine in hand (30 + 90), 100 HP. Shotgun and launcher on racks along the course | Finish the course: 3 lanes of pop-up plates (carbine 8 plates at 10–30 m, shotgun house 6 plates, launcher 3 plates behind a bunker), a movement section (jump a wall, crouch through a culvert, sprint a timed stretch), then the live drill: 3 training sentries that take cover and flank. All down = win | HP 0 (paint rounds), or 6 min |
| 2 | **Pump Hall** (mission) | `L_PumpHall` | Night, storm outside. The service tunnel door. Carbine (30 + 90) and shotgun (6 + 12), 100 HP, 3 lives. Tide clock 21:40 | Restore the 3 breaker panels (hold Interact 1.5 s each; each is a checkpoint) in the turbine gallery, the control mezzanine and the sump walkway, then reach the freight lift. ~13 Sentinels (Wardens + Breachers); the launcher is found after panel A | All 3 lives lost (a down restarts at the last checkpoint, telemetry `restart`), or 12 min |
| 3 | **Ninth Tide** (final assault) | `L_NinthTide` | Night, rain, high sea. The barrier crest road, all three weapons (carbine 30 + 120, shotgun 6 + 18, launcher 1 + 3), 100 HP, 3 lives | Fight along the crest (two pushes, the second with a Bulwark), enter Gate Control, patch the gauge line into the uplink (hold Interact 3 s), **hold 60 s** while Sentinels flank from two stairwells and the gantry, then pull the master lever. The screens flip to 98 % | All 3 lives lost, or 15 min |

Score: 100 per Sentinel (+50 visor finish), 500 per objective, accuracy bonus (hits / shots × 1000 at the end),
time bonus in S1. `ExtraJson`: kills, shots, hits, accuracy, deaths, objectives, time.

Telemetry (beyond `score`, `state`, `restart`): `shot_fired` {weapon, mag, reserve}, `hit` {enemy, damage,
part, weapon}, `enemy_state` {enemy, from, to}, `enemy_down` {enemy, type, weapon}, `player_damaged` {amount, hp,
from}, `pickup` {kind, amount}, `reload` {weapon}, `weapon_switch` {from, to}, `objective` {id, state},
`checkpoint` {id}, `plate_down` {lane, plate} (S1). `state` at 10 Hz adds hp, weapon, mag, reserve, stance,
enemies_alive, objective, tide_clock.

### AutoPlay bot (watchable, comfortable, human-like)

The bot lives on the PlayerController (TG_PrePhysics) and acts only through `AP->Inject`.

- **Navigation:** navmesh path to the next objective waypoint; `IA_Move` from the path direction relative to the
  view; it walks in combat, sprints only on long clear stretches, crouches only where the level needs it and
  behind cover. Jumps only at marked jump gates (S1 wall). No strafe-jitter.
- **Looking:** `IA_Look` deltas from a critically damped turn toward the target with a **turn-rate cap**
  (skill 1: 140°/s yaw, 70°/s pitch; skill 0: 80°/s / 40°/s) and an acceleration cap, so every turn is a smooth
  arc; while walking without a target it looks along the path, leading corners. Pitch stays within ±25° except
  when aiming at targets above or below. Never a snap.
- **Combat:** reaction delay (skill 1: 0.25 s, skill 0: 0.7 s) before engaging; aims at the torso with
  skill-scaled noise that settles over 0.4 s; fires bursts (carbine 4–7 rounds, then 0.3 s settle); uses cover:
  picks the nearest cover point on its side that blocks most visible Sentinels, crouches behind it, rises/strafes
  to peek, ducks back to reload or when below 40 HP; switches to the shotgun under 7 m, fires the launcher at 2+
  Sentinels within 4 m of each other or at a Bulwark; picks up health under 50 HP and ammo under 25 % when a
  pickup is within 12 m.
- **Skill** (0..1) interpolates reaction time, turn caps, aim noise, cover discipline (how often it peeks from
  the same spot) and weapon choice quality. Skill 1 should usually win S1 and S2.

## 7. Art direction: low poly (user direction, 2026-10-12)

**Chosen and bought (2026-10-12):** Synty **POLYGON - Sci-Fi Space** for every level (modular walls, floors,
doorframes, consoles, tanks, rails, lift, signs, steam/explosion FX) and Infima **Low Poly Animated - Modern Guns**
for the first-person arms and the three weapons (with their attachments, clips, HUD icons and sounds). The Sentinels
are Quaternius's CC0 **Animated Mech Pack** (Mike = Warden, Stan = Breacher, George = Bulwark, Leela = training
sentry), tinted with an amber visor. The sea is our own faceted low-poly mesh and material. The original asset plan
below is kept for the record.

**Low-poly stylized**, one coherent kit family, never primitives or untextured blocks: faceted shapes with
bevelled silhouettes, flat-shaded or palette-atlas materials (Synty-style gradient atlas), clean readable
forms, strong colour blocking. Lit with Lumen, volumetric fog and coloured practical lights, so the low-poly world
still has depth and mood. Palette: storm navy and slate concrete, galvanised blue-grey steel, Keeper safety orange
and the two light colours in conflict: the Keepers' sodium-amber lamps and Ostrand's cold teal floodlights and
screens. Water is a stylized faceted sea (Water plugin with a flat-shaded, banded material and foam lines); rain
is stylized streaks and splash rings, not photoreal. Characters and weapons in the same low-poly language as the
world. Readability first: Sentinels' amber visors and orange stripes pop against the cool environment.

| Element | Wanted source (low poly) | Fallback already on disk |
|---|---|---|
| Barrier, pump hall, tunnels, crest, control room | one modular low-poly industrial / sci-fi kit (walls, floors, catwalks, pipes, machinery, doors, screens, containers, barriers, crates) | none suitable (on-disk sets are photoreal scans) |
| Weapons (carbine, pump shotgun, launcher) | low-poly gun pack in the same style (with or without FP arms) | Lyra meshes are realistic-stylized, would clash |
| First-person arms | low-poly gloved arms matching the kit, or the weapon held by simple low-poly gloves | UE template arms re-materialed flat (weak) |
| Sentinels | low-poly humanoid robots / mech soldiers on a humanoid rig (retarget to Manny for Lyra animations) | Manny bodies with flat-shaded material (weak) |
| Animations | **Lyra** Manny rifle/pistol/shotgun locomotion, hit reacts, deaths (retargeted onto the robot rig); Paragon-retargeted Manny set for extras | on disk |
| Weapon and impact FX, weapon sounds | **Lyra** muzzle flash, tracers, shell eject, impacts, weapon sounds; **Realistic Starter VFX Vol 2** and **Niagara Explosions** re-tinted and simplified to match the stylized look | on disk |
| Ambience and foley | **Essential Ambience SFX**, **Essential Footsteps SFX**, **Free Game SFX Starter (65)**, **Small Sound Kit**, Kenney impact and UI audio | on disk |
| Fonts and icons | Rajdhani, Barlow Condensed, Share Tech Mono (OFL); game-icons.net (CC BY 3.0) | on disk |

Not used, to stay clear of other games and third-party looks: no Paragon heroes, no Lyra team colours, no
signature designs of known shooters.

### Asset requests (for the coordinator and the asset scout; purchases need the user's OK)

Free CC0 candidates the scout can fetch directly (licence to confirm per pack):
1. **Kenney** (CC0): Blaster Kit (low-poly guns), Space Station Kit / Modular Space Kit, City Kit Industrial,
   Conveyor Kit, Survival Kit (crates, barrels, props), Animated Characters, UI Pack Sci-Fi (frames).
2. **Quaternius** older CC0 packs: Ultimate Guns / Guns Pack (rifle, shotgun, launcher), Animated Robot / Mech
   packs, Ultimate Modular Sci-Fi. (The library notes say the *newer* Quaternius packs have a custom licence: CC0
   ones only.)

Premium low-poly (Fab, Personal tier, prices for the scout to confirm), the coherent route:
3. **Synty POLYGON Military** (soldiers, weapons with FP-ready meshes, bases, barriers, towers): would cover the
   weapons, the crest and the yard.
4. **Synty POLYGON Sci-Fi Industrial / Sci-Fi Worlds / Mech** (or similar): industrial interiors, robots for the
   Sentinels.
5. A low-poly **first-person arms + weapon animation** pack (rifle, shotgun, pistol: idle, fire, reload, equip),
   UE5 skeleton, 5.3.

Recommendation: one Synty family (3 + 4) for a consistent premium look, CC0 Kenney/Quaternius as fill. If no
purchase, a Kenney + Quaternius CC0 build is feasible but needs more kitbashing and material work to look premium.

## 8. UI style: "Keeper field kit"

Industrial signage, not sci-fi chrome: stencil-cut corners, hazard ticks, sodium amber (#FFB347) on deep
storm-navy translucent panels (#0E1A24 at 80 %), warning red-orange (#FF5A36), Ostrand's screens in a cold
teal (#5FE3D6) that the HUD never uses. Rajdhani for titles, Share Tech Mono for every number (ammo, HP, tide
clock), Barlow Condensed for labels and subtitles. Frames are 9-slice textures with chamfered corners and hazard
ticks; icons from game-icons. No default font or plain text anywhere.

- **HUD:** bottom-left HP bar (segmented, amber, red below 30) with a med-kit count; bottom-right weapon card
  (icon, mag / reserve in large mono digits, small icons for the other two weapons); top-centre the objective line
  and the tide clock; a small diamond waypoint on the current objective; the crosshair (4 ticks that open with
  spread) and hit markers; directional damage arcs; radio subtitles bottom-centre in a framed strip with "MAGS"
  and a waveform icon. The HUD fades its frames during quiet traversal.
- **Screens:** main menu (title "TIDEBREAK" over a slow, stable shot of the barrier at dusk: no camera motion),
  mission select with the three title cards, settings (master / music / sfx volume, mouse sensitivity, invert Y,
  FOV, head bob off/subtle, resolution, fullscreen), pause, mission complete (kills, accuracy, time, score,
  ★ rating), downed / retry, credits.
- **Save:** missions unlocked, best score per mission, settings.

## 9. Tech plan

- C++ module `FpsBreach` on the factory template; gameplay in C++, tuning in Blueprint subclasses / data assets
  made by editor Python scripts in `Scripts/`; levels built by editor scripts (`-run=pythonscript`), never
  hand-edited `.uasset`.
- Classes: `AFBCharacter` (movement, camera, stance, weapons inventory, health), `UFBWeaponComponent` +
  `UFBWeaponData` (data asset per weapon), `AFBProjectile_EMP`, `AFBSentinel` + `AFBSentinelAI` +
  `UFBSquadSubsystem` + `AFBCoverPoint`, `AFBPickup`, `AFBObjective` (breaker, uplink, lever, exit),
  `AFBTargetPlate` + `AFBRangeDirector` (S1), `AFBGameMode` (scenario flow, checkpoints, lives, tide clock),
  `UFBGameInstance` (settings, save, AutoPlay hook), `UFBSaveGame`, `AFBPlayerController` + UMG widgets in C++,
  `UFBBotComponent` (AutoPlay bot).
- Config: `r.RDG.AsyncCompute=0`, `bAllowHighDPIInGameMode=True`, nav agent settings from horror-escape's
  lessons, motion blur off in `DefaultEngine.ini`.

## 10. Acceptance checklist

- [ ] Three scenarios playable start to finish by hand and by the bot; win and lose both reachable
- [ ] Three weapons with distinct feel, ammo, reload, pickups, health
- [ ] Sentinels take cover, peek, flank (one at a time) and shoot back fairly; readable hit reacts and power-downs
- [ ] Hit markers, damage arcs, no screen shake, FOV 90, head bob off by default, motion blur off
- [ ] Story told through screens, chalk, posters, the schedule board, Mags's subtitled radio and the S3 payoff
- [ ] Styled UI everywhere, no default font; main menu, settings, pause, save, mission complete, credits
- [ ] AutoPlay v1.4: validate-run PASS for S1..S3; bot turns smoothly within its caps, uses cover
- [ ] Framing screenshots checked (open areas, tunnels, crouched, against walls, ADS)
- [ ] Packaged Win64 Shipping build; scrub-import-paths `--verify` = 0; assets.manifest.json and ThirdPartyNotices

## 11. Levels as built (scripts in `Scripts/build_level_S*.py`)

- **S1 Calibration Yard** (`L_CalibrationYard`): a 175 m straight course on the barrier top, sea below the north rail:
  lockers with the Keepers' name plates and the 61 % screen beside a chalked gauge; Lane A (8 carbine plates, two on
  rails); a 66 cm jump wall; a crouch culvert (124 cm); a sprint stretch; Lane B shotgun house (6 plates); Lane C
  launcher bunker (3 EMP-only plates behind 151 cm cover); the live drill against three training sentries. One life.
- **S2 Pump Hall** (`L_PumpHall`): service tunnel with the waterfront posters; a two-storey turbine gallery (44 %
  screens, chalked gauges, 4 Wardens, breaker A, the launcher); corridor; control mezzanine (the sluice schedule board,
  2 Wardens + 2 Breachers, breaker B); sump walkway (steam, side doors, breaker C with 3 ambushers); freight lift with
  a rear ambush. Checkpoint at each breaker, 3 lives.
- **S3 Ninth Tide** (`L_NinthTide`): crest road between the storm sea and the harbour, Varo Low's skyline with its own
  23 % screens; push 1 (3 Wardens + Breacher), push 2 (Bulwark + 2 Wardens); Gate Control with the gauge desk under a
  dust sheet; uplink (hold 3 s), 60 s hold against three waves through the north, south and east doors, master lever.
  On the win every screen flips to 98 % in a wave from the room outward and a dawn light comes up.
- **L_MainMenu**: a still dusk view of the crest and skyline from a fixed camera.

## 12. Status

- 2026-10-12: design draft v1 written; art direction switched to **low poly** on the user's instruction; repo
  created; approved by the coordinator.
- 2026-10-12: systems in C++ (player, weapons, Sentinel AI + squad tokens, scenario game mode, HUD/menus, AutoPlay
  bot); packs imported; data assets; look-dev renders checked (mech scale/facing fixed; first-person sight alignment
  and weapon attachments added). Level scripts for S1-S3 and the menu written; waiting for the shared heavy-job slots
  to build and test them.

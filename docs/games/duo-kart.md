# Whirlvale Karts: story bible and game design

Slug `duo-kart`, project/module `DuoKart`, Unreal Engine 5.3, Windows. Genre: local 2-player split-screen arcade
kart racer with CPU racers, items, a 4-track cup, single versus races and (if time allows) a battle arena.

Status: **design draft, waiting for the coordinator's OK** (2026-10-12). Nothing built yet.

## 1. The game in one paragraph

Whirlvale is a storybook valley where the weather is made by hand. Guilds of craftsfolk blow the spring blossom out of
bellows, polish the summer sun, paint the autumn leaves one by one and sift the winter snow. At the end of every
season the guilds race their workshop karts on the valley's lanes in **the Turning Cup**, and everybody knows the rule:
the winning guild's weather comes next. Two players sit on the starting bench side by side, pick a driver each, and race
each other and six CPU guild racers through four seasonal tracks: drifting to wind up a tailwind, hopping over
puddles, catching **storm jars** for weather items. Over the cup the valley changes season under their wheels, and on
the last track, at the Great Vane on top of the valley, they find out what the race was always for.

## 2. How this differs from the factory's other games

- **rally-racer** is realistic off-road rally (Chaos vehicles, loose surfaces, landscape scans, one player, pace notes,
  an elegiac story). Whirlvale is cartoon arcade: custom kinematic kart movement (no simulation), drifting with
  charge-up boosts, hops, items, tracks built as roads with walls, two humans in split-screen, a cheerful story.
- **metro-runner** is an endless runner; nothing else in the factory is local multiplayer.

## 3. Story bible

### 3.1 World

- **Whirlvale**: a long green valley of villages, orchards, a canal town, an old wood and a snowy castle at its head.
  Never a map screen; the player sees it track by track and from the main-menu terrace.
- **The guilds** make the weather by hand, each in its workshop:

| Guild | Workshop | Weather | Colour |
|---|---|---|---|
| Petal Works | bellows barns in the orchards | spring blossom and soft rain | coral and leaf green |
| Brightwork | mirror sheds by the canal | summer sun | marigold and brass |
| Rustle Mill | paint mill in the wood | autumn leaves | russet and ochre |
| Sieve House | sifting tower under the castle | winter snow | ice blue and white |
| Bottlery | corking cellar (serves all seasons) | bottled winds | teal |
| Loomhouse | rain looms | rain | slate violet and silver |
| Mistcellar | fog cellar | fog | grey lilac |

- **The Turning Cup** is run at the end of each season. Everyone believes the winning guild picks the next season.
- **The Great Vane**: a huge copper weathervane on the castle hill at the head of the valley, a swift with a long
  kite tail. It has been stuck pointing at winter for a long time this year; that is why this Turning matters.
- **The truth (late payoff)**: the guilds make the weather, but the **race turns the year**. Every windmill, pinwheel
  and mill wheel along the tracks is belted, roped and kite-lined up the valley to the Great Vane. Every kart that
  passes winds it a notch: the leader and the last kart alike. The winner never chose anything; the seasons always
  came in order. Only the vane's keeper, Ada Tock, remembers.

### 3.2 Drivers (8; two human picks, the rest CPU)

Every driver is an apprentice or master of a guild, races a workshop kart dressed with their trade, and has a reason
to race. Meshes come from the character pack we get (section 11): the identity lives in colours, a hat or prop, the
kart's dressing and the banter, so it survives a pack swap.

| Driver | Guild | Look and kart | Personality | Why they race | CPU style |
|---|---|---|---|---|---|
| **Posy Thimblewick** | Petal Works | coral and green, petal cap; bellows on the back that puff petals | bubbly, impatient | her guild hasn't won in twelve Turnings and the orchard fair is waiting for spring | great starts, average lines |
| **Sol Brassmoor** | Brightwork | marigold and brass, goggles; mirror fins | show-off | wants a long summer "so everyone sees how shiny it is" | aggressive items |
| **Marta Rook** | Rustle Mill | russet coat; basket of paint pots | calm, the oldest racer | thirty Turnings raced; she races for the racing | smooth lines, few items |
| **Juno Hale** | Sieve House | ice blue, white scarf; sieve drum | dry humour, precise | promised her little brother a deep snow for the sledge run | best drifter |
| **Fennick Gale** | Bottlery | teal waistcoat; crates of corked bottles | trickster | the Bottlery sells wind to every season; he just likes to win | loves Crosswind |
| **Nell Drizzlewood** | Loomhouse | slate violet, silver brolly; a little loom | shy, apologetic | wants a gentle rain for the new looms | defensive, holds Brolly |
| **Odo Murk** | Mistcellar | grey lilac hood; chimney puffing mist | says almost nothing | nobody knows | drops Puddles |
| **Ada Tock** | Keeper of the Great Vane | copper green and cream; a big wind-up key turning on the kart's back | grandmotherly, cryptic | "keeps it turning" | always mid-pack, drives near the last kart |

Ada is the story's hinge and, in plain sight, the game's only rubber band: her AI hangs back near whoever is last and
keeps the field together. Players read it as kindness; the finale explains it.

### 3.3 How the story surfaces in play (never a wall of text)

1. **Track intro postcard** (one line, under 15 words): a painted postcard frame over a slow, level dolly along the
   start grid (4 s, at most 8 deg/s of rotation, skippable). Lines in section 3.5.
2. **Rival banter as subtitles**: a speech ribbon with the speaker's portrait in the guild colour, at the top of the
   half-screen of the player involved (overtakes, item hits, last lap, finish). At most one line every 8 s per half,
   under 15 words, no voices (a short synthesized "chirp" per driver instead). Section 3.6.
3. **The season turns during each race**: lap 1 starts in the look of the season before; by the last lap the track has
   turned. Blossom Lanes thaws from frost to full blossom; Sunmill Quay from wet spring to glare; Emberleaf Wood from
   green to red-gold with leaves falling; the Great Vane from grey to snowing. (One material parameter collection
   `MPC_Season`, foliage tint lerps, particle rates.) Players feel the race doing it before they know why.
4. **Things that spin when you pass**: windmills, pinwheels on fences, mill wheels and kite strings along every track
   turn faster as the pack goes by (driven by kart proximity). Nobody comments; it is just charming, until track 4.
5. **"Past Turnings" boards** (discoverable detail): a chalk board beside each start straight lists recent winners and
   the season that followed: "Turning 212: Brightwork won. Autumn followed." Every board shows the seasons coming in
   order, whoever won. Observant players notice; the finale confirms it.
6. **The finale (track 4, the Great Vane)**: the road climbs past the belts and kite lines that come up from every
   mill in the valley into the vane's gearhouse. The lap gate sits under the vane; a ring of notches on the gate
   lights up each time any kart passes through, all eight, not just the leader. On the last lap the vane creaks off
   winter. Ada's banter here: "There. Hear it click?" / "Every lap counts. Even the last one."
7. **Cup endings** (a short podium scene, then one line):
   - A human wins: their driver rings the vane bell; the vane's banner takes their guild colour; spring blossoms down
     the whole valley in the menu backdrop. Line: "Every kart turned it. Always has." (Ada)
   - Both humans on the podium: they pull the bell rope together.
   - A CPU wins: the same season turn, the CPU rings the bell, and the humans' karts are on the gearhouse plaque with
     everyone else's. The plaque around the vane's rim carries all eight names every time.
   - The main-menu terrace afterwards shows the vane pointing at spring, in the winner's colours.

### 3.4 What the player learns, where and how

| Fact | Where | How |
|---|---|---|
| The guilds make weather by hand | driver karts, workshops along the tracks | kart dressing, set dressing |
| The winner is said to choose the season | main-menu cup card, postcard of track 1 | one line each |
| The vane is stuck at winter | menu terrace, track 4 postcard | the vane itself, frost on the menu scene |
| Racing turns the season | every race (lap 1 to lap 3) | the world changes under the wheels |
| Every kart counts, not only the winner | spinning mills; gate notches on track 4; Ada | behaviour and props, two banter lines |
| The seasons always came in order | Past Turnings boards | discoverable chalk lists |

### 3.5 Track postcard lines

| Track | Line |
|---|---|
| Blossom Lanes | "Petal Works lanes. The orchards are waiting to wake." |
| Sunmill Quay | "Where the Brightwork polishes the noon." |
| Emberleaf Wood | "The Rustle Mill paints every leaf by hand." |
| The Great Vane | "Top of the valley. The old vane is stuck on winter." |
| Weathercock Square (battle) | "Market day. Mind the pinwheels." |

### 3.6 Banter (subtitles; examples, the full set lives in `DT_Banter`)

Triggers: `start`, `overtake` (speaker passes someone), `overtaken`, `hit_given`, `hit_taken`, `final_lap`,
`finish_first`, `finish_last`, `near_ada`. Each driver has 1-2 lines per trigger; a line is never repeated in a race.

| Driver | Example lines |
|---|---|
| Posy | "Spring's coming early this year!" · "Hey! I was blooming there!" · "Blow, bellows, blow!" |
| Sol | "Shades on, everyone. I shine first." · "See that glint? That was me." · "Smudged! Do you know how long polishing takes?" |
| Marta | "Easy on the bends, young ones." · "Thirty Turnings. Still got it." · "Ha. Good shot, that." |
| Juno | "Snow doesn't hurry. Neither do I. Until now." · "Slippery, aren't I?" |
| Fennick | "Mind the draught!" · "Bottled that breeze myself." |
| Nell | "Sorry! Sorry. Brolly's up." · "Rain's coming. Gently." |
| Odo | "..." · "Mist." · "You didn't see me." |
| Ada | "Keep it turning, dears." · "Every lap counts. Even the last one." · "There. Hear it click?" |

Human-vs-human: when one human overtakes or hits the other, the line comes from the drivers they picked, shown in the
other player's half, so the couch rivalry gets a voice.

## 4. Core loop and modes

- **Race**: 8 karts (2 humans + 6 CPU by default; CPU count 0-6), 3 laps, countdown with a well-timed throttle
  "tailwind start", items on/off. Laps are about 55-65 s (1.1-1.3 km at ~22 m/s average), a race about 3 to 3.5 min.
- **Turning Cup (Grand Prix)**: the 4 tracks in order; points 10-8-6-5-4-3-2-1; cup standings between races; ties
  broken by the last race. Cup endings section 3.3.7.
- **Versus**: one race, any track, CPU count, items on/off, laps 1-5.
- **Battle, optional ("Pinwheel Scramble")**: Weathercock Square arena (the village square of Blossom Lanes,
  closed off). Every kart carries 3 pinwheels on a rod; an item hit blows one away (it lands on the ground and can be
  picked up). 2 minutes; most pinwheels wins; a kart with none keeps racing with a "puff" icon and can win some back.
- **CPU difficulty**: Breezy / Blustery / Stormy (skill 0.6 / 0.8 / 0.95 for the CPU brain).
- **Single player** works too: the second seat stays empty (full-screen view).

## 5. Split-screen and input

### 5.1 Split: horizontal (P1 top, P2 bottom), with a vertical option in Settings

Why horizontal: a kart racer needs width more than height (the road, the corner ahead and karts alongside are spread
horizontally), and the horizon stays one straight line across both halves. Each half is 1920x540 at 1080p. To avoid
a squashed view, `AspectRatioAxisConstraint = MaintainYFOV` with a 42 deg vertical FOV: each half shows about 106 deg
horizontally, the kart stays a readable size, nothing is stretched. The vertical (side by side, 960x1080) layout is a
setting for players who prefer it (`UGameMapsSettings::TwoPlayerSplitscreenLayout`), not the default. A 6 px seam in
the guild-wood frame colour separates the halves; one shared mini-map sits on the right edge across the seam so both
players see the whole field.

### 5.2 Devices and the join screen

- Join screen ("the starting bench"): two empty seats. Any device's confirm sits in the next free seat: gamepad (A),
  left keyboard half (Space), right keyboard half (Enter). The seat then shows the device glyph and the player picks a
  driver in their half (both pick at the same time). Back (B / Esc / Backspace) stands up again.
- Device routing: a custom `UDuoGameViewportClient` overrides `InputKey`/`InputAxis` and sends each event to the local
  player whose seat owns the device (keyboard events are split by key into the left and right halves). UE would
  otherwise give the whole keyboard and gamepad 0 to player 1.
- Each local player has its **own Enhanced Input action set** (`IA_P1_*`, `IA_P2_*`) and mapping context. This also
  makes the AutoPlay log name the player in every row (section 9).

| Action | Left keyboard (P1 default) | Right keyboard (P2 default) | Gamepad |
|---|---|---|---|
| Throttle | W | Up | RT (A also works) |
| Brake / reverse | S | Down | LT |
| Steer | A / D | Left / Right | left stick X, d-pad |
| Hop / drift (hold) | Space | Right Ctrl | RB |
| Use item | E | Right Shift | LB / X |
| Look back (hold) | Q | `/` | Y |
| Pause | Esc | Backspace | Start |

Keys were chosen so the two halves never share a key and the modifiers (Ctrl/Shift) avoid membrane-keyboard ghosting;
gamepads are recommended and shown first on the join screen. Rebinding is in Settings (per seat).

### 5.3 Camera (per player, gentle)

- Chase camera behind and above the kart: arm 560 cm, height 180 cm, pitch -10 deg; the kart sits in the lower third,
  about 1/8 of the half's width.
- Yaw follows a smoothed blend of the kart's heading and its velocity (critically damped, 0.25 s), so drifts and item
  hits do not swing the view; roll always 0 (stable horizon); pitch follows slopes slowly and is clamped to +-8 deg;
  height follows jumps and landings on a damped spring (no jolt).
- **No shake, no FOV change** ever. Boost shows as speed lines at the edges of that half (a faint particle sheet on the
  camera), wind ribbons behind the kart, and engine pitch.
- Look back is a hard cut to a rear camera while held (a cut instead of a swing).
- Item hits: the kart body does a short wobble-spin on its own mesh; the camera and the kart's travel direction stay
  steady.
- Respawn after falling off: a swirl of wind sets the kart back on the road at the last checkpoint (1.5 s), the camera
  fades through the swirl rather than flying.

## 6. Kart handling (arcade, custom)

`UKartMovementComponent` (C++), kinematic with fixed 120 Hz sub-steps, no Chaos vehicle:

- Ground: a sphere sweep down plus 4 corner probes give the ground normal; the kart aligns to it smoothly and never
  flips. Gravity 1.6x for a snappy feel; walls deflect with a small bounce and keep 70% of the speed along the wall.
- Speed: top 27 m/s (~97 km/h), acceleration to top in ~3 s; off-road surfaces (grass, sand, snow banks, leaf
  drifts) cap speed at 55-70%; slipstream behind a kart within 12 m for 1 s gives +8%.
- **Hop**: tapping hop makes a 0.25 s hop (clears puddles and small hazards, breaks a Kite Line).
- **Drift**: hold hop while steering at speed: the kart enters a drift in that direction; steering tightens or widens
  it. Drift charge fills in three tiers shown as wind ribbons from the rear wheels:
  1. **Breeze** (0.6 s): pale mint ribbons -> 0.5 s tailwind,
  2. **Gust** (1.3 s): teal ribbons with leaves -> 1.0 s tailwind,
  3. **Gale** (2.2 s): gold ribbons and swirling leaves -> 1.5 s tailwind.
  Release hop to fire the tailwind (+30% speed). Colours and names are our own (no blue/orange/pink spark ladder).
- **Tailwind start**: throttle pressed in the last 0.4 s of the countdown -> 1 s tailwind; too early -> a brief sputter.
- **Gust vents** (boost pads): round grates in the road with petals or leaves blowing up; 1 s tailwind.
- **Jump ramps and bouncy awnings**: launch with a short airborne arc; a hop at take-off adds a tiny "trick" tailwind
  on landing.
- Kart-to-kart bumps: overlap resolution pushes both karts apart and trades a little speed (no spin-outs from bumps).

## 7. Items (storm jars)

**Pickups**: glass storm jars in wicker cages, floating in rows across the road under strung bunting, each jar holding a
small swirling weather (petal, cloud, leaf, snow). Drive through one: it pops into motes and the item badge in your HUD
flips through weather labels for 1 s. One item at a time, no stacking. Jars reappear after 4 s.

| Item | What it does | Counterplay | Odds (by race position) |
|---|---|---|---|
| **Tailwind Bottle** | 1.2 s self boost (corked bottle pops) | none needed | all, more at the back; **Tailwind Trio** (3 uses) only in the back half |
| **Puff Cloud** | thrown forward; a small rain cloud floats straight along the road at 30 m/s for 3 s; the first kart under it gets **soggy** for 1.5 s (top speed 80%, softer steering, no spin) | visible and slow: steer around it; a Brolly blocks it | middle and back |
| **Puddle** | dropped behind: a 2.5 m rain puddle stays 20 s; driving through makes the kart skid (no steering 0.5 s, half wobble-spin) | visible; drive round or **hop over** it; Brolly blocks it | front and middle |
| **Crosswind** | a sideways gust from your kart (6 m radius) shoves every kart alongside 3 m sideways | keep distance; drifting karts are shoved half as far | front and middle |
| **Kite Line** | thrown at the kart ahead within 25 m: a kite string tows you behind them for 2 s (slipstream +15% for you, -5% for them) | the leader can **hop** to snap the line after 0.4 s | middle and back |
| **Brolly** | an umbrella over the kart for 6 s that blocks one Puff Cloud or Puddle | **Crosswind shoves a Brolly kart twice as far** (it catches the wind) | front and middle |

Rules for fairness: no item targets the leader from far back, nothing removes a kart from the race, every effect is
over within 1.5 s, every effect is visible before it lands. Item odds move only by position bucket (front 1-2, middle
3-5, back 6-8). **Rubber banding stays subtle**: CPU karts get a 0.97-1.03 speed factor by distance to the nearest
human; humans are never sped up or slowed down by the game; catch-up comes from slipstream, items and Ada's driving.

## 8. Tracks

Built from track data (`Data/Tracks/<id>.json`: control points, road width per point, banking, surfaces, checkpoint
spacing, jar rows, vents, ramps, shortcuts, hazards, set-dressing anchors) by a committed Python script; the road
ribbon, curbs and walls are generated by `ADuoTrack` in C++ from the spline (procedural mesh, deterministic), the
surrounding ground is a generated landscape as in rally-racer, dressing comes from the packs. Each track has a main
spline, alternative shortcut splines, a racing line for the AI and respawn points.

| # | Track | Season / look | Layout | Shortcut | Hazards | Packs |
|---|---|---|---|---|---|---|
| 1 | **Blossom Lanes** | spring: Provencal village lanes, lavender fields, orchards; frost thaws into blossom over the race | wide, forgiving figure of flowing bends through the village square and orchards, 1.1 km | hop the hay ramp through the Petal Works barn (cuts a hairpin) | sprinkler arcs from the bellows barns (wet patches that make karts skid), duck-pond splash off-road | Stylized Fantasy Provencal, Stylized Foliage, FANTASTIC Village |
| 2 | **Sunmill Quay** | summer: canal town, market square, a big watermill; wet spring to bright noon | canal-side loop with two bridges and a market chicane, 1.2 km | ramp off the quay crates over the canal (needs speed) | the watermill sluice: a timed spray that pushes karts sideways; bouncy market awnings (jump) | FANTASTIC Village, Provencal, Good SKY |
| 3 | **Emberleaf Wood** | autumn: the Rustle Mill in an old wood; green to red-gold, leaves falling | twisting forest road with a long drift valley and a climb to the mill, 1.25 km | the hollow-log tunnel (narrow, fast) | leaf drifts (slow, hide the road edge), swinging paint buckets at the mill (timed) | Stylized Forest Sample, Stylized Nature Pack (tinted), FANTASTIC Village (mill) |
| 4 | **The Great Vane** | winter: the castle hill and the vane's gearhouse; grey to snowing | climbing loop through castle gates, a gear bridge and the gate under the vane, 1.3 km | through the castle hall (its gate opens from lap 2) | ice patches (low grip), the turning gear bridge (timed gap), snow banks off-road | Stylized castle, Medieval Castle Modular (tinted), Stylized Forest + snow material |
| B | **Weathercock Square** (optional battle) | market day in the Blossom Lanes village square | closed arena with a fountain, stalls and ramps | - | sprinklers | as track 1 |

## 9. AutoPlay (contract v1.4) and the three scenarios

- Drop-in `Source/DuoKart/AutoPlay/AutoPlaySubsystem.h/.cpp` unchanged. `StartScenario(n)` creates the second local
  player, seats both on gamepads (devices `Bot0`/`Bot1`), sets mode, track, drivers, CPU count, items, seed and cup
  state, and opens the track map; the game skips the join screen, menus and postcard in AutoPlay and calls
  `ScenarioStarted(name)` when the countdown begins. The recording is the full 1920x1080 split-screen window.
- **Both human seats are played by a bot** (`UKartBotComponent` on each PlayerController, tick group pre-physics),
  acting only through `AP->Inject(PC, IA_Pn_*, Value, Key)`. **Player index in inputs.jsonl**: the drop-in keys its
  edge tracking by action, so each player has its own actions; every inject row names the player through the action
  (`IA_P1_Steer`, `IA_P2_Item`), and `action_info` rows list the mapped keys per player. (Asked the coordinator
  whether a contract bump should add an explicit `player` field; until then this needs no drop-in change.)
- Key names logged: gamepad keys (`Gamepad_LeftX`, `Gamepad_RightTriggerAxis`, `Gamepad_LeftTriggerAxis`,
  `Gamepad_RightShoulder`, `Gamepad_LeftShoulder`).
- CPU racers are not human seats: they use the same driving brain but write their kart input directly (as any AI).
- **Bot behaviour (human-like)**: follows the track's racing line with look-ahead steering and analog stick values,
  drifts into corners below a radius threshold and releases at Gust or Gale, uses gust vents and (with enough skill)
  shortcuts, hops over puddles it sees in time, and uses items by rules: Tailwind on a straight or to carry a
  shortcut, Puff Cloud when a kart is ahead in line, Puddle when a kart is close behind, Crosswind when a kart is
  alongside, Kite Line when a kart is 8-25 m ahead, Brolly when leading and threatened. It never snaps the stick and
  makes occasional wide lines.
- **Skill** (`-Skill`, 0..1): reaction time 0.40 -> 0.12 s, stick noise 0.25 -> 0.03, racing-line error 2.0 -> 0.3 m,
  drift release tier (Breeze at low skill, Gale at high), item rule quality (random use at 0, rules at 1), shortcut
  attempts only above 0.6, a mistake (wide line or missed hop) every ~40 s at 0, every ~4 min at 1. P1's bot plays at
  `Skill`, P2's at `Skill - 0.1` (clamped) with a scrappier style (more items and shortcuts), from separate seeded
  streams (`Seed`, `Seed + 101`).
- Seeds: item roulette, CPU noise and jar timing use `FRandomStream`s from `-Seed`.

| # | Name | Start state | Result (metadata only) |
|---|---|---|---|
| 1 | **Blossom Lanes Duel** | Versus, track 1, 3 laps, the two seats only (P1 Posy, P2 Juno), items on, seed 11 | `win` with `extra.winner = "p1"/"p2"`, both finish times, positions, items used, drift counts |
| 2 | **Emberleaf Wood, Cup race 3** | Turning Cup race 3 of 4, track 3, 3 laps, P1 Sol, P2 Nell + 6 CPU (Blustery), items on, cup standings after races 1-2 preset (deterministic table), seed 23 | `win` if a human finishes 1st, else `lose`; extra: finish order, cup points after the race |
| 3 | **The Great Vane, Cup final** | Turning Cup race 4 of 4, track 4, 3 laps, P1 Fennick, P2 Marta + 6 CPU, standings after races 1-3 preset, seed 37; after the finish the cup ending plays (podium + season turn, about 10 s) before `FinishRun` | `win` if a human wins the cup, else `lose`; extra: race order, final cup table |

`-MaxSeconds` 600 for all three (a race takes about 3.5 min). Telemetry (beyond the contract's required rows): `state`
at 10 Hz per seat (`player`, location, rotation, velocity, speed_kmh, lap, position, item, drift_tier), and
`countdown_end`, `checkpoint`, `lap_complete`, `position_changed`, `item_pickup`, `item_used`, `item_hit`,
`drift_release` {tier}, `boost` {source}, `shortcut`, `respawn`, `banter` {speaker, line_id}, `race_finish` {kart,
position, time_s}, `cup_standings`.

## 10. Systems and classes (C++ module `DuoKart`)

| Class | Role |
|---|---|
| `UDuoGameInstance` | seats and devices, settings, mode/track/cup state, save/load, AutoPlay `StartScenario` |
| `UDuoGameViewportClient` | routes keyboard halves and gamepads to the seat that owns them; split layout |
| `ADuoKartPawn` | kart body + wheels (static meshes), driver (skeletal, seated anim), camera rig, ribbons, speed lines, engine synth, item holder |
| `UKartMovementComponent` | arcade movement (section 6) |
| `UKartCameraComponent` | the gentle chase camera (section 5.3) |
| `ADuoTrack` | spline, road/curb/wall procedural mesh, surfaces, checkpoints, racing line, respawns, shortcut splines |
| `AStormJarRow`, `AGustVent`, `AJumpRamp`, hazard actors (`ASprinkler`, `ASluiceSpray`, `ASwingBucket`, `AGearBridge`, `AIcePatch`) | track furniture |
| `UItemComponent` + item actors (`APuffCloud`, `APuddle`, `AKiteLine`, `ABrolly`) | item use, effects, odds from `DT_ItemOdds` |
| `ADuoRaceGameMode` | grid, countdown, laps, positions, finish, results, cup points, season blend, banter triggers |
| `UKartDriverBrain` | racing line, drift, items, shortcuts; drives CPU karts directly and feeds the AutoPlay bot |
| `AKartAIController` | CPU racers (brain -> kart input, rubber band factor, Ada's "keep together") |
| `UKartBotComponent` | AutoPlay seat bot: brain -> `AP->Inject` per seat |
| `UBanterSubsystem` | `DT_Banter`, triggers, cooldowns, routing to the right half |
| `USpinnerComponent` | windmills/pinwheels/mill wheels spinning with kart proximity; vane notches on track 4 |
| UI (C++ widget trees) | join bench, main menu, driver select (per half), track/cup select, HUD per half, shared mini-map, banter ribbon, postcard, results, cup standings, podium, pause, settings |
| `UKartEngineSynth : USynthComponent` | small buzzy kart engine per kart, pitch from speed, our own synthesis |

Data: `DT_Drivers`, `DT_Items`, `DT_ItemOdds`, `DT_Banter`, `DT_Tracks`, `DT_CupPoints`, `DT_Scenarios`.
Maps: `L_Frontend` (menu terrace over the valley, the vane in the distance), `L_Track_Blossom`, `L_Track_Sunmill`,
`L_Track_Emberleaf`, `L_Track_Vane`, optional `L_Arena_Square`. Editor work through Python scripts in `Scripts/`
(imports, materials, maps, landscape, dressing), each logging `workflow.jsonl` rows; nothing hand-edited.

Performance (two views): Lumen off (sky light with real-time capture + distance field AO), cascaded shadow maps
instead of virtual shadow maps, Nanite on pack meshes where they allow it, foliage cull distances per track,
`r.RDG.AsyncCompute=0`. Target 60 fps at 1920x1080 split in Shipping on this machine.

## 11. Art, audio and UI direction

**Look: a storybook valley.** Stylized hand-painted PBR, warm saturated light, soft shadows, gentle fog; karts and
drivers a little chunky and readable at small size; one coherent family per track from the stylized packs we own.

| Need | From the library (owned) | Request (section 12) |
|---|---|---|
| Village, lanes, canal town, mills | Stylized Fantasy Provencal, FANTASTIC Village Pack | - |
| Forest, foliage, rocks | FREE Stylized Forest Sample, FREE Stylized Foliage, Stylized Nature Pack | stylized winter add-on |
| Castle, gearhouse | Stylized castle (bought), Medieval Castle Modular Vol 1 (bought, tinted) | - |
| Sky | Good SKY | - |
| Karts | none | stylized kart pack |
| Drivers | none (Paragon / realistic packs don't fit) | cartoon character pack; the in-car loop from Free Animations Pack (SoerGame) and Free Character Emote Pack for podium/celebrations |
| VFX | Realistic Starter VFX Vol 2 (puffs only, restyled) | stylized Niagara pack (wind trails, puffs, petals, splashes) |
| UI | HONETi 4K Full Fantasy GUI (bought; frames recoloured to painted wood and paper), Kenney fantasy-ui-borders, ambientCG Paper, game-icons.net (item glyphs inside our badges) | - |
| Fonts | - | Lilita One (titles, positions, numbers) and Fredoka (body), OFL, asked of the scout |
| Music / SFX | Fantasy Music Starter Pack v2 (CC BY) as a fallback, Kenney impact/ui audio | upbeat cartoon racing music + cartoon SFX |

Kart engine and per-driver chirps are synthesized by us (no recorded or TTS voices). **UI style**: painted wood frames,
paper cards, guild ribbons; positions as big "1st"-style numerals in the driver's guild colour with a cream outline;
the item badge a round wicker frame; the drift gauge three little vanes that spin up; no plain or default-font text.
**IP**: everything original. No look-alikes of any existing kart series' characters, items (no mystery boxes, shells,
banana-like peels, leader-hunting item), tracks (no rainbow road), logos, HUD or sounds.

## 12. Fab requests (prices pending from the asset scout; nothing is bought without the user's OK)

Asked the asset-scout session (2026-10-12) for listings with Personal prices, UE 5.3 support and ratings:

1. Stylized/cartoon karts (separate wheels, recolourable, 4+ variants). Without one, the fallback is a wooden
   "workshop kart" kitbashed from FANTASTIC Village wheels, crates and planks (on-theme, but weaker).
2. 8 cartoon drivers or a modular stylized character kit, retargetable to UE5 Manny.
3. Stylized Niagara VFX (wind ribbons, puffs, sparkles, splashes, petals/leaves, speed lines).
4. Stylized winter add-on for track 4 (snowy pines, snow ground).
5. Upbeat cartoon racing music and cartoon SFX.
6. Free OFL fonts Lilita One and Fredoka.

The list with prices goes to the coordinator when the scout replies.

## 13. Build order

1. Design OK (this doc).
2. Offline while the build/GPU hold lasts: C++ for movement, camera, track spline/road mesh, race flow, items, brain,
   bot, viewport routing, UI trees; data tables as CSV/JSON; Python editor scripts; track JSON for Blossom Lanes.
3. After the hold: compile (ue-heavy), import packs, build Blossom Lanes, S1 end to end, AutoPlay hand test,
   `validate-run` PASS, framing screenshots, tag `milestone/autoplay-1`.
4. Tracks 2-4, CPU racers, cup flow, S2 and S3, `milestone/autoplay-3`.
5. Menus, settings, banter, postcards, cup endings, audio, polish; battle arena if time allows; Shipping package.

## 14. Acceptance checklist

- [ ] Join bench: two seats, gamepads and both keyboard halves, each routed to its own player
- [ ] Horizontal split (vertical in Settings), gentle camera per half, no shake or FOV change
- [ ] Drift with three tailwind tiers, hop, tailwind start, gust vents, ramps, slipstream
- [ ] 6 items with their counterplay; storm jar rows; position-based odds; subtle CPU rubber band
- [ ] 4 tracks with shortcut and hazards each; season turns during each race
- [ ] Turning Cup with standings, podium and endings; Versus; (Battle optional)
- [ ] Banter subtitles, postcards, Past Turnings boards, the vane payoff
- [ ] Main menu, settings (volume, resolution, split layout, rebinding per seat), pause, results, save of cup unlocks/best times
- [ ] Styled UI only; premium pack art; synthesized engine and chirps
- [ ] AutoPlay S1-S3 validate PASS; framing screenshots reviewed; Shipping build

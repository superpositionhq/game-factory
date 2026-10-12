# Game #2: Rally Racer (Track B)

Off-road rally racer built in Unreal Engine 5.3 by an agent (Claude), with every editor and code operation
recorded as it happened in `workflow.jsonl` (schema `superposition.ue-workflow/v0`).

- Project: `%GF_ROOT%\games\rally-racer` (own git repo, git-lfs for `*.uasset` / `*.umap`)
- Builder: agent session `ue-rally-racer` (one of four parallel Track B games)
- Started: 2026-10-11 00:55 -04:00

## 1. Game in one paragraph

Three-lap rally races on loose surfaces against four AI drivers, on three landscape tracks (Forest dirt,
Desert canyon, Snowy hills). Checkpoints must be passed in order; a reset key puts you back at the last
checkpoint. A time-trial mode races your best-lap ghost and saves best times and the ghost to disk.
HUD with speedometer, gear, position, lap, lap/total times, minimap, next-checkpoint arrow, boost meter and
start countdown. Main menu with mode and track select, settings (volume, resolution, window mode, steering
and camera sensitivity, controls list), pause menu, results screen.

## 1b. Story bible: "Last Run at Harrow"

Told only through what the player sees and hears while racing. At most one short line per stage (the stage
card), no cutscenes, no spoken lines (no voice or TTS; pace notes are icons plus tones).

**Premise.** The Harrow Valley Rally has run every autumn since 1961 on the farm and forestry roads of a long
valley. In spring the new Calder Hydro dam closes the canyon and the valley floods. This is the last running.
You drive car **#7**: the car Mara Kell won Harrow with three times, restored after she died last winter, in
her pale blue, red and cream colours (Rally Cars Pack skin 01, weathered). Nobody says any of this. The player reads it from the roads, the car and the
crowds.

**What the race means.** Win the last running in her car, on the only stretch of road that will still exist
next year.

### Rivals (characters shown through cars and driving)

| Car | Livery (Rally Cars Pack skin) | Driving style (AI parameters) | Who they are, as the player sees it |
|---|---|---|---|
| #1 Calder Hydro works car (car 02) | clean black (skin 02 clear) | skill 1.0, no steering noise, aggression 0.3, boost 0.7; rubber band | the dam builder's team: fast, spotless, sponsor boards everywhere on SS2 |
| #4 the veteran, Haig & Sons (car 02) | skin 01 recoloured in `M_RallyLivery`: faded orange and teal | skill 0.93, aggression 0.1, rarely boosts; **salutes** (moves to the verge and lifts when #7 closes in on the last lap of SS3) | Mara's old rival; always in the grid (slot 2 of 3-5) |
| #11 Dunmore Garage (car 02) | cream and black, dirty (skin 03) | skill 0.97, noise 0.15, aggression 0.95 (leans on cars) | the hard-charging local garage |
| #23 Harrow Feed & Seed (car 01) | skin 03 clear recoloured green | skill 0.99, noise 0.45 (erratic), boost 0.9 | the last valley family's kid |
| #9 Calder Hydro (car 01) | clean black (skin 02 clear) | skill 0.96, middle of the field | makes the works team look like an army |

### Beats per stage (one day: morning, noon, dusk)

| Stage | Time / weather | Stage card (the only line) | What the player sees |
|---|---|---|---|
| SS1 Pinewood (Forest) | early morning, low sun, mist | "By spring this road lies under forty metres of water." | Emptied homesteads: fences, hay bales, a for-sale board. Orange survey paint **FSL 412** on trees and posts high above the road: everything you drive will be under water. Few spectators: one family at a farm gate. The tight corner has a faded board, "KELL'S" (her corner). Faded 1961-2025 start banner. |
| SS2 Red Rock (Canyon) | noon heat, hard light | "The dam wall closes this canyon in March." | The dam site: concrete barriers, cones, delineators, construction fencing, Calder Hydro boards, the dry diverted riverbed. Dam workers in hi-vis watch with arms folded. Survey marks are now at road height. |
| SS3 Frostbite (Snow) | dusk, cold blue light, flares | "Above the waterline. The only road that stays." | The high pass. The survey marks are now **below** the road, down the slope. The biggest crowd of the day lines the last straight with red flares: the valley people who were missing from SS1 all came up here. At the finish: a stone cairn with a car door, **#7 M. KELL**, and flowers. The finish banner reads "HARROW 1961-2026". |

**Payoff (SS3 recolours SS1-2).**
- The empty roadsides on SS1-2 were not indifference: everyone was waiting at the top.
- The survey marks, seen falling from above the road to below it, show this is the only road that survives.
- The memorial door matches the player's own car.

The podium screen line: "Last winner of the Harrow Valley Rally" (if first) / "Harrow Valley Rally, 1961-2026".

### Motifs

- **Visual.**
  - Orange survey paint (FSL 412) whose height above or below the road tells the story.
  - #7 in pale blue, red and cream (the player's car, the memorial door, the HUD colour of the player).
  - Faded old race banners against clean new corporate boards.
  - Light across the day: mist, then heat, then dusk with flares.
- **Audio.**
  - Pace-note chimes, one pitch per corner severity.
  - Racing music in the menus and at the finish.
  - Ambience per stage: birds and wind in the forest, machinery hum and wind in the canyon, wind and the crowd at the snow finish.
  - A horn blast at the finish of SS3.
- **Menu.** The main-menu scene is #7 parked by the cairn at dusk.

### What the player learns, where and how

| Fact | Where | How |
|---|---|---|
| This valley will flood | SS1 stage card; survey marks | one line, then paint on trees |
| A company is building the dam | SS2 boards, works cars' livery | sponsor boards, clean car |
| Your car belonged to someone who mattered | #7 livery; "KELL'S" corner board; memorial door | discoverable details |
| She is dead, and this is for her | SS3 memorial at the finish | cairn, door, flowers |
| The rivals respected her | SS3 veteran's salute | AI behaviour only |
| The valley people care | SS3 crowd with flares | where the crowd stands |

## 2. Content sources and licences

Premium pass (after the user's direction to use the Fab packs, animation packs and a styled UI). Store content
lives in its own top-level folders, copied unchanged from the read-only asset library (same folder names keep
the packs' internal references valid, so they are not under `Content/Fab/`).

| Content | Source | Licence | Used for |
|---|---|---|---|
| Rally Cars Pack (2 cars x 3 skins + clean variants, wheel anim BP, physics asset, bolt-on parts) | Fab, bought (`Content/RallyCarsPack`) | Fab Standard (Personal) | every car; liveries recombined and partly recoloured by us |
| Vehicle Wheel VFX (Niagara dirt/sand/snow) | Fab, bought (`Content/VehicleWheelVFX`) | Fab Standard (Personal) | wheel spray per stage |
| Project Nature: Spruce Forest (summer + winter), Conifer Bushes, Foliage Collection, Meadow Flowers | Fab, free | Fab Standard | SS1/SS3 forests, saplings, verge grass, memorial flowers; needle colours adapted |
| Rural Australia | Fab, free | Fab Standard | SS2 eucalypts, grass trees, cliffs, rocks, logs; road delineators, fences (all stages) |
| Megascans: 7 surfaces (forest floor, tyre-track mud, desert sand, canyon mud, fresh/trampled snow, uncut grass), 6 cliffs/rocks, hay bale, concrete barrier, cone, fence post, wild/dry grass | Fab (Megascans) via the asset library | Fab Standard | landscape surfaces, cliffs, dam works, homestead |
| Free Character Emote Pack (UE5 Manny/Quinn + 12 emotes), Free Animations Pack (in-car driving loop) | Fab, free | Fab Standard / Personal | the SS3 crowd, dam workers, the farm family, drivers in the cockpits |
| Racing Music Vol.1 (2 of 30 tracks) | Fab, free | Fab Standard (Personal) | menu and finish music |
| Poly Haven scans, textures, HDRIs (kiara_3_morning, qwantani_noon_puresky, kloppenheim_06_puresky) | Poly Haven | CC0 | rocks, logs, ferns, rock faces, skies |
| Saira Condensed, Rajdhani | Google Fonts via the asset library | SIL OFL 1.1 | all UI text |
| UE 5.3 Vehicle template pawn/input, engine BasicShapes | Epic | UE EULA | pawn base class, input actions |

**Built by us** (scripts in `Scripts/`, all recorded): stage layouts, heightmaps, road masks and scatter
(`gen_track.py`); landscape, livery, banner, sky, emissive and scan master materials; the hue-shift livery
instances; the TrueType rasteriser (`ttf_raster.py`) and every printed texture (survey tags, signs, KELL'S
board, #7 door, banners); story props (survey stakes/poles, sign boards, memorial door, flares); tyre-stack
barriers; all story dressing and placement (`dress_story.py`); lighting, fog and colour grading per stage;
engine sound synth, all SFX and the pace-note tones; the whole UI (painted gauge, pace-note arrows, minimap,
boards); AI driving styles, salute, AutoPlay bot.

**Built vs sampled (what the player sees):** the cars, trees, cliffs and people are sampled store content; the
roads, terrain shapes, story props, signs, layout, lighting, UI, sounds and all behaviour are ours. By screen
area on a typical stage roughly half the pixels are store meshes (trees, cars) and half our own (landscape
material over our terrain, roads, sky setup, UI, props).

Every file is listed with source, licence and sha256 in `assets.manifest.json`.

## 3. Systems and classes

All gameplay logic in C++ (module `RallyRacer`); Blueprint subclasses and data assets hold tuning and asset
references. UI widgets build their trees in C++ (no hand-authored Widget Blueprint graphs), so every UI
element is code that is in git. Editor-side work (assets, maps, landscapes, placement) is done by UE Python
scripts under `Scripts/`, each run headless, each appending its own `workflow.jsonl` rows.

| Class | Role |
|---|---|
| `ARallyCarPawn : AWheeledVehiclePawn` | from the template pawn: chase/bumper cameras, Enhanced Input (throttle, brake, steer, handbrake, boost, look, camera, reset, pause), boost meter, reset to last checkpoint, surface grip (off-track penalty via wheel friction multipliers), engine synth, skid and impact SFX. Used by both player and AI. |
| `URallyWheelFront/Rear : UChaosVehicleWheel` | loose-surface tyre tuning |
| `URallyEngineSynth : USynthComponent` | procedural engine sound: firing frequency from RPM, harmonics + noise, load from throttle |
| `ARallyTrack : AActor` | closed spline from `ControlPoints`; marker posts, tyre-stack walls on the outside of tight corners, gates (poles + printed banner), start grid, runtime checkpoint triggers; queries: distance/lateral on spline, curvature, advised AI speed table. The road surface is painted into the landscape through a generated road mask. |
| `ARallyScenery : AActor` | 12 instanced layers (scanned rocks/plants, generated firs, hidden trunk colliders) filled by Python scatter |
| `ARallyGameMode` | race flow: spawn grid, countdown, checkpoints in order, laps, positions (lap, checkpoint, spline distance), finish, results; time-trial flow with ghost |
| `ARallyAIController` + `FRallyDriver` | racing line: look-ahead steering, target speed from a curvature table with a braking pass, lane change to pass, speed cap behind moving cars (steer round stopped ones), rubber band vs player, reverse/reset recovery. The same driver is the player's autopilot after the finish and in automated tests. |
| `ARallyGhostCar : AActor` | replays recorded transform samples (20 Hz, interpolated) as a translucent car |
| `URallyGameInstance` | selected mode/track, settings, save/load |
| `URallySaveGame : USaveGame` | best lap and best race time per track, best-lap ghost samples per track, settings |
| `ARallyPlayerController` | HUD, pause, results, menu input mode |
| `ARallyMenuGameMode` + `URallyMainMenuWidget` | main menu: mode (Race / Time Trial), track, opponents count, Settings, Quit |
| `URallyHUDWidget` | speedometer, gear, position, lap, lap/total time, best lap, countdown, checkpoint arrow, minimap (track polyline + car dots drawn in `NativePaint`), boost bar, messages |
| `URallyPauseWidget`, `URallySettingsWidget`, `URallyResultsWidget` | pause (resume/restart/settings/quit), settings, end-of-race table |
| `URallyEditorLibrary` (editor module `RallyRacerEditor`) | `CreateLandscapeFromRaw` (wraps `ALandscape::Import`) and `RerunConstruction`, because UE 5.3 Python cannot create landscapes |

## 4. Vehicle tuning (loose surface)

Start from the template's offroad car and change, in `ARallyCarPawn` / wheel classes / `BP_RallyCar`:

- AWD with rear bias (FrontRearSplit 0.65, i.e. more torque to the rear) so throttle can hold a slide.
- Rear wheels: lower cornering stiffness and friction than the front so the rear steps out on lift-off and
  handbrake; handbrake torque rear-only, high (lets the car rotate for hairpins).
- Front wheels: higher cornering stiffness, max steer 40 deg; steering reduced with speed (steering curve).
- Centre of mass lowered, mild downforce, mild drag; angular damping only in the air (template).
- Surface grip: on the road ribbon friction multiplier 1.0; off track 0.7 plus extra drag (tracked by
  distance to the spline, so it needs no painted physical-material layers). Snow track road 0.85.
- Boost: Shift adds forward force while the meter lasts; refills slowly, faster while drifting.
- Reset (R): last passed checkpoint, at a free spot near it, velocity zeroed, 3 s ghosting through other cars.
- Chaos `bReverseAsBrake` off (it turned any brake input into full brake plus reverse gear); reverse is handled in the pawn.
- Chaos aggressive vehicle sleep off; CCD on all car bodies; automatic gears shift at 4600 / 2200 rpm.

## 5. Tracks

Landscapes 1009 x 1009 vertices at 1 m (about 1 km square), heightmaps generated in Python: noise terrain
shaped per theme, a flat 12 m road corridor carved along the spline (same Catmull-Rom interpolation as UE's
spline, so corridor and spline agree to the centimetre), smooth shoulders. One textured landscape material:
CC0 ground/rock/road PBR sets blended by slope and a generated road mask (road, verge, ruts).

| Track | Length (approx.) | Shape | Look |
|---|---|---|---|
| Forest (`Track_Forest`) | 2.30 km, 13 checkpoints | flowing loop, tightest corner R 21 m | forest floor, gravel road, generated firs, mossy rocks, logs, ferns, partly cloudy HDRI |
| Canyon (`Track_Canyon`) | 1.87 km, 11 checkpoints | fast loop between sandstone walls | sand, sandy gravel road, red sandstone, scanned boulders and cliffs, quiver trees, shrubs, clear-sky HDRI |
| Snow (`Track_Snow`) | 2.09 km, 12 checkpoints | rolling hills, three crest jumps, R 22 m bends | snow, packed-snow road (grip 0.82), snow-laden firs, boulders, overcast HDRI |

Shapes are polar harmonic loops auto-fitted into the 400 m playable area and checked for minimum radius and
self-separation; 3 laps; start grid for up to 6 cars behind the start/finish gate.

## 6. AI

Racing line = track spline with per-AI lateral offset. Per tick: project car onto spline, aim at a point
look-ahead (8 m + 0.5 s of speed) ahead, steer by angle to that point; target speed from minimum radius over
the next (speed x 2 s) of track with a per-driver skill factor; throttle/brake to close the speed gap; when a
car is close ahead, shift lateral offset to the side with more room; rubber band: target speed x 0.9 to
1.08 based on distance to the player; reset to last checkpoint if stuck for 3 s or upside down.

## 6b. AutoPlay (QA self-play, contract v1.4)

- Drop-in `Source/RallyRacer/AutoPlay/AutoPlaySubsystem.h/.cpp`, copied unchanged (v1.4, ContractVersion 4: audio clock, render stalls filled with silence). Shipping
  recording builds are enabled: `bAllowHighDPIInGameMode=True` in `DefaultEngine.ini`, `bUseLoggingInShipping`.
- **Scenarios** (`-Scenario=<n>`; `milestone/autoplay-<n>` = scenarios 1..n work):

| # | Name (display) | Start state | Win / lose |
|---|---|---|---|
| 1 | SS1 Pinewood | Forest stage, morning; 3-lap race; player #7 last on a 5-car grid behind #1, #4, #11, #23 | win = finish P1; lose = finish P2-P5; timeout if not finished in MaxSeconds |
| 2 | SS2 Red Rock | Canyon stage, noon; same race setup | same |
| 3 | SS3 Frostbite Pass | Snow stage, dusk; same race setup (veteran #4 may salute on the last lap) | same |

  - The game boots into the main menu.
  - `StartScenario(n)` selects stage n (race mode, 4 rivals) and opens it.
  - `ScenarioStarted("SS1 Pinewood")` etc. is called when the grid is set up.
- **Bot.** `URallyAutoPlayBot` is a component on the player controller that ticks in PrePhysics.
  - It computes the racing line with the same `FRallyDriver` the AI uses (`Compute`, nothing applied directly).
  - It acts only through `AP->Inject` on `IA_Throttle` (W), `IA_Brake` (S), `IA_Steering` (A/D, analog value), `IA_Handbrake` (SpaceBar), `IA_Boost` (LeftShift) and `IA_Reset` (R, one frame when the driver's recovery asks for a reset).
  - Its steering is scaled up to make up for the harder high-speed steering cap on player input.
- **Skill.**
  - Corner speed factor: 0.84 at skill 0 to 1.09 at skill 1 (rivals rubber-band up to x1.10 against a leading player).
  - Steering wobble: (1 - skill) x 0.7.
  - Control reaction: 4/s to 14/s.
  - Boost eagerness: 0.2 to 0.95. Any driver boosts only when the advised speed 1.2 s and 2.5 s ahead is well above its speed.
  - At skill 0 the bot is a cautious, wobbly novice that still finishes.
- **Telemetry.**
  - `countdown_end`, `checkpoint` {index, lap}, `lap_complete` {lap, lap_time_s}, `position_changed` {position}.
  - `reset` {checkpoint, reason} plus `restart`, `collision` {impulse, other} (player only, impulse > 2.5e5), `race_finish` {position, total_time_s}.
  - `score`: 10 per checkpoint, plus (racers + 1 - position) x 100 at the finish.
  - `state` at 10 Hz with location, rotation, velocity, speed_kmh, gear, lap, position, boost and boosting.
- **Outcome.** `FinishRun` reports `win` (P1) or `lose`. Extra fields: position, racers, total_time_s, best_lap_s, lap_times_s, resets and stage. After finishing, the car coasts (no autopilot) during the 2 s hold.
- **Hand test.** `Scripts/autoplay_test.py` runs the editor `-game` off-screen with Live Coding off, through the job limiter, then `validate-run.ps1`.
- **Framing check before recordings.** `--framing N` passes `-FramingShots=N`: N screenshots spread over the race distance plus the first overtake and first handbrake turn, moved to `<run>/framing/`, and one `RR_TEST: framing` line with camera rotation speed (p50/p95/p99/max deg/s) and the car's screen share (mean/max).
- **Import paths.** `Scripts/scrub_paths.py` runs the pipeline's `scrub-import-paths.py`; the 4 FontFace source paths are project-relative now (verify: 0 hits).

## 7. Acceptance checklist

- [x] Main menu: Race / Time Trial, track select (3), opponents (3 to 5), Settings, Quit (main page checked by screenshot; sub-pages only in code)
- [~] Settings: master volume, resolution, window mode, steering speed, mouse look sensitivity, minimap, controls list; persisted (implemented, not used by a human yet)
- [x] Race: countdown READY / 3-2-1 / GO, 3 laps, checkpoints in order (a skipped gate shows MISSED CHECKPOINT), reset to last checkpoint
- [x] 4 AI opponents complete laps on all three tracks without getting stuck permanently (autotests; 5-10 resets per race)
- [x] Positions update live; finish shows results table with total and best lap times
- [~] Time trial: best-lap ghost recorded and replayed from the next lap; best times saved (SaveGame) and shown in the track menu (ghost not yet seen in a screenshot)
- [x] HUD: speed, gear, position, lap, lap/total time, minimap, checkpoint arrow, boost, countdown
- [~] Pause menu: resume, restart, settings, quit to menu (implemented, works while paused; not used by a human yet)
- [~] Car drifts on handbrake, holds slides on throttle, off-track is slower (tuned by numbers and AI telemetry; needs a human drive)
- [~] Engine sound follows RPM; skid sound when sliding; impact sound on collisions; UI/checkpoint sounds (all wired; nobody has listened yet; impact hits only fire since a late fix)
- [x] Three tracks with distinct look (forest, canyon, snow)
- [x] Packaged Win64 build launches into the main menu (Shipping, checked off-screen)
- [x] `workflow.jsonl` rows for every operation; git history per step; `assets.manifest.json`

## 8. Recording

`workflow.jsonl` rows are written by the scripts that perform the operation (`Scripts/wflog.py` helper,
imported by editor scripts and called from the shell for code changes and builds), at the moment of the
operation, with `reason` written before acting. Failures get their own rows. `source.commit` is the project
HEAD when the operation ran.

## 9. Status (2026-10-11, premium pass)

**Playable, story-dressed, packaged; AutoPlay levels 1-3 pass (tag `milestone/autoplay-3`).**
- Win64 Shipping build: `Packaged/Windows/RallyRacer.exe`.
- AutoPlay levels 1-3 pass the contract hand test; tags `milestone/autoplay-1` and `milestone/autoplay-3`.
- The second pass followed the user's directions:
  - Fab cars, environments and animation packs.
  - Story told through play.
  - Styled UI with no plain text.
  - Build-it-ourselves where possible.

### What changed in the premium pass

- **Cars.**
  - The Rally Cars Pack bodies replace the template buggy.
  - Six entrants with story liveries, two of them recoloured by our own `M_RallyLivery`.
  - Bolt-on parts, wheel spray (Vehicle Wheel VFX).
  - Per-rival driving styles, including the veteran's salute on the last lap of SS3.
- **Stages (build_track_v3).**
  - Megascans surfaces on our terrain.
  - Project Nature spruce forest (summer and winter, 3x density).
  - Rural Australia eucalypts, cliffs and rocks; Megascans cliffs; delineator posts.
  - Time of day: SS1 morning, SS2 noon, SS3 dusk, each with its own HDRI, sun, fog and grade.
- **Story (dress_story).**
  - SS1: FSL 412 survey marks above the road, homestead with family and PROPERTY ACQUIRED notice, KELL'S corner board, old HARROW VALLEY RALLY banner.
  - SS2: dam works and workers.
  - SS3: survey stakes below the road, the crowd with flares, memorial cairn with the #7 door, HARROW 1961-2026 finish banner.
  - Stage cards with one line each.
  - The SS3 podium line.
  - Main menu: #7 parked by the memorial at dusk.
- **Audio.** Crowd cheering along the SS3 last straight and wind/leaves on SS1 ("Free City & Nature Sounds" by Gregor Quendel, CC BY 4.0, credited in `Docs/ThirdPartyNotices.md` and on the in-game CREDITS page).
- **UI.**
  - Saira Condensed and Rajdhani throughout.
  - Timing boards, position board, team-colour number ladder, painted analogue gauge, pace-note arrows with synthesized tones, styled menus and podium.
- **AutoPlay** (section 6b).
  - The bot found and fixed a real bug: the brake latched after the first press of S, which a human player would have hit in every race.

### Checked (automated runs and screenshots)

- **Races** (player car on autopilot), all three stages finish:
  - SS1: 1 reset in the race.
  - SS2: 4 finishers within 3.3 s, 6 resets.
  - SS3: all 5 finish, 3 resets.
- **AutoPlay hand tests**, all validate-run PASS:
  - L1 skill 1: P3, laps 94 / 83 / 94 s, 1 reset.
  - L2 skill 1: P5, laps 84 / 75 / 91 s, 2 resets.
  - L3 skill 0.5: P2, 1 reset.
- **Pipeline recording** of L1 (queued by the coordinator) failed for an environment reason: the game window was covered by `Shell_SystemDim` (the Windows dim/UAC layer) for 240 s. Siege-catapult and island-survival runs failed the same way at the time.
- **SS2 physics:** after the fix below, no car leaves the ground in a full SS2 race (the clamp caught 3 blow-ups).
- **Packaged build:** boots to the menu, track select and credits (screenshots); car close-up checked.
- **Photo tours** of SS1, SS2 and SS3 story beats.
- **HUD and podium** screenshots on SS3.

### Not verified by a person yet

- Driving feel with keyboard or gamepad (the brake fix above came from the bot, not from a person).
- Audio mix: pace-note tones against engine and music.
- Pause menu and settings.
- The veteran's salute: the logic exists, but no screenshot of it yet.
- One editor menu-screenshot run hung under machine load (killed, recorded); later runs and the packaged build were fine.

### Known issues / next

- The AI still bumps and needs resets on SS2 (6 in one race), and the kid #23 can fail to finish there.
- Spectators are Epic mannequins with tinted materials, not dressed people.
- Stacked cars (one landing on another) can produce absurd contact impulses. Seen on SS2: cars launched at 2,000-125,000 km/h.
  - Now: a depenetration cap on the car bodies, plus a clamp above 300 km/h that restores the last sane velocity (logged `RR_TEST: clamp`).
  - Nobody flies off any more, but a car can still end up stuck off-road afterwards.
  - #11's aggression is lowered from 0.95 to 0.75.
- No driver figures in the cars.
  - The only in-car loop in the packs is a standing pose: the mannequin stood through the roof.
  - Seated animations exist only on the ActorCore skeleton, which would need retargeting.
- The veteran's salute is logged (`RR_TEST: salute`) but hasn't triggered in a test yet. It needs the player right behind #4 on the last lap of SS3.
- AutoPlay levels 2 and 3 are implemented (same flow) but only level 1 was hand-tested.

### Stats

| Item | Value |
|---|---|
| workflow.jsonl rows | 1527 (40 failed operations; 6 `log.correction` rows; premium pass: 665 rows) |
| Commits | 26 (tags `milestone/autoplay-1`, `milestone/autoplay-3`) |
| Assets | 4753 files in `assets.manifest.json` (store packs, Megascans, Poly Haven, fonts, own work) |
| Built vs sampled | see section 2 |

### Before this becomes a package

- Run the history/name scrub and the leak scan. Old rows carry the old schema name and 3 early compiler-error paths; new rows use `ue-workflow/v0` and hide paths.
- Store content is Fab Standard: it ships inside the built game, never as raw files in a data package.

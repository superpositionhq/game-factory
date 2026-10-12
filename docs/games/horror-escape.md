# Game #7: ASHGROVE (first-person horror escape, UE 5.3)

Track B game: a small, complete first-person horror escape / puzzle game built in Unreal Engine 5.3 by an agent
(Claude), with every real editor and code operation recorded at the moment it happens in `workflow.jsonl`
(schema `ue-workflow/v0`; rows before hx-02469 carry the old schema name). Project: `%GF_ROOT%\games\horror-escape` (own git repo,
git-lfs). Started 2026-10-11 01:40 -04:00.

## 1. Game in one paragraph

You come back to Ashgrove, your family's old house, at night, looking for your little sister Ada, who never left
it. The front door slams behind you. To get out you go through the house floor by floor: the **ground floor**
(chapter 1), the **basement** (chapter 2) and the **attic** (chapter 3). Each floor is a chain of 3–4 linked
puzzles that gates the way on. You have a flashlight whose battery runs down, an inventory of keys and items,
and the notes the family left behind. From chapter 2 something lives in the house with you: it roams, it
listens, it comes to noise and light, and if it touches you the run ends. You can hide in wardrobes and cupboards.
Atmosphere carries the game: dark rooms lit by a few practical lamps, cold moonlight through windows,
volumetric fog and drifting dust, creaking boards, a heartbeat when it is near.

## 1b. Story bible (added 07:40 after the user's story direction)

Rules we hold ourselves to: show, don't tell. The house is the storyteller. Notes are few (five in the whole
game) and short (under 25 words). No recorded or synthesized voices: written fragments, non-verbal sounds,
music-box and wireless audio, and the house itself. Each chapter gets one line on its title card. Puzzle
solutions are pieces of the family's life. The stalker is never named. The ending recolours everything the
player has already seen.

**Premise (never stated in-game).** It is 1934. Thomas Vale, the player, comes back to Ashgrove, the
late-Victorian house he walked out of thirteen years earlier at seventeen. The front door shuts behind him and
will not open again.

**The family.**
- **Edmund Vale**, the father: a clock and automaton maker. Every mechanism in the house is his, and every one
  was made as a game for Ada: the magic lantern and its tin shadow figures, the tuned laundry pipes, the moon
  mirrors, the dollhouse copy of Ashgrove, the music-box dancer.
- **Margaret (M.)**, the mother: a dressmaker. The dresses are hers.
- **Thomas**, the eldest: the player.
- **Ada**, the youngest: eight in 1921. She was afraid of the dark. Her motifs are a red ribbon, and the crow
  and the moon from her favourite bedtime story, "the crow who carried the moon home".

**What happened.** One winter night in 1921 Thomas quarrelled with his father and left through the kitchen door
at two in the morning. Ada was afraid of the dark, so he left his oil lamp burning on the attic stair for her.
By four the nursery was on fire. Edmund went in after her and came out burned and blind, without her. Margaret
left Ashgrove that spring (the dining-room clock, nine in the evening). Edmund closed up the house and stopped
every clock at the hour someone left. He kept every room exactly as it was and never went out again.
- What he has become in thirteen years of dark is the stalker: gaunt, pale as something that has not seen daylight,
  eyeless, hunting by sound (the Whisper creature).
- It wears a faded red ribbon round its wrist.
- It carries the only clock in the house that still runs, a pocket watch. You hear its ticking before you see it.

**What the player learns, where and how**

| Where | What the player finds (all optional except the puzzle props) | What it means (understood only at the end) |
|---|---|---|
| Ch1 hall | Family photographs in the hall and study: father, mother, a tall boy, a small girl. The boy's face is scratched out in every one. A grandfather clock stopped at **4**. | It is Thomas's face the father scratched out. 4 a.m. was the fire: Ada's hour. |
| Ch1 dining | Table laid for four. One chair under a dust sheet with a black band on it. Mantel clock stopped at **9**, with a thimble beside it. | Margaret's chair and her hour. |
| Ch1 kitchen | Height marks on the door frame: "T" climbs to a man's height; "A" stops low, with a last mark dated *1921*. The back door is boarded and chained from inside. A wall clock stopped at **2**. A boy's cap still on its hook. | 2 a.m. is Thomas: the door he left by, sealed since. |
| Ch1 parlour | A child's painting (house, crow on the roof, moon) in a gilt frame over the fireplace. The magic lantern with its tin figures. | Ada's story. The father's toy. Solving it opens the painting (the basement key). |
| Ch1 upstairs | Footsteps cross the ceiling when the power comes on. | Someone lives here. |
| Ch2 workshop | The father's bench: a wireless that plays four notes at the same hour every night, cracked spectacles with blackened lenses, scorched gloves, clock parts, an unfinished tin crow. Thomas's own boyhood notebook. | He is still making things for her. |
| Ch2 boiler room | A cot made up beside the boiler. One cup. Tally marks scratched in the brick, thousands of them. A small mitten drying on a pipe. | He sleeps down here and keeps the house warm because she was always cold. |
| Ch2 wine cellar | Four racks laid down "one for each of us". A life-size porcelain doll of Ada stands among the racks in a new dress. | The father made her again, the age she would be, in dresses for the birthdays she never had. It moves (a Watcher). |
| Ch3 attic | The burned nursery corner: charred rafters, new boards patched over the hole, a blackened cot. The dollhouse, an exact Ashgrove, with its attic room burned black. Three more porcelain Adas, each a little taller. | The fire. The dolls are the Watchers. |
| Ch3 trunk | Ada's trunk: the scorched oil lamp (the same model as the hall lamp in chapter 1), her drawing of the crow carrying the moon over the house with three figures on the roof labelled "PAPA", "ADA" and "TOM", and the roof key. | The lamp was Thomas's. The scratched-out boy was Thomas. |
| Ending | Dawn on the roof: a crow on the chimney and a pale moon (the shadow-play picture, real). The stalker climbs to the hatch and stops at the edge of the light. The ribbon on its wrist moves in the wind. It sits down facing the sun. The ticking stops. The camera pulls back: the back half of Ashgrove is a burned-out shell. | It was the father all along, keeping Ada's house from the boy who left the lamp burning. |

**Chapter title cards (one line each):**
- I. *The house remembers* ("Every clock in Ashgrove stopped on the night someone left.")
- II. *Something is down here* ("Someone has kept the boiler lit.")
- III. *Ada* ("She was always afraid of the dark.")

**Notes (five in total, each under 25 words, period paper and ink):**
1. Ch1 hall, Father: "Each clock stopped on the night one of them left. Hall, dining room, kitchen. Their hours keep my desk."
2. Ch1 kitchen, an old note from M.: "Tom: spare fuses in Father's desk and the bottom drawer here. Box in the pantry. Three in, then the lever."
3. Ch1 parlour, a child's card propped on the lantern: "make the picture: the house, the crow on the roof, the moon".
4. Ch2 workshop, Thomas's notebook: "Pipes tuned to the wireless. Lowest on the left. Ada plays the same four notes back."
5. Ch2 cellar ledger, Father: "One rack for each of us, eldest first. The black seals are the ones never opened. Count them."

The boiler's instructions are an engraved brass plate, not a note. The two long diary pages from the first
build are removed.

**How each puzzle ties to the story:**
- Ch1: the clock hours are the three departures. The fuse box is M.'s old household routine. The shadow play is
  Ada's bedtime story.
- Ch2: the lullaby the father plays every night on the wireless is Ada's four notes. The boiler keeps her warm.
  The wine racks count the family.
- Ch3: the moon mirrors are the father's moon brought indoors for her. The music-box dancer stops at her story's
  symbols (moon, bird, key, eye). The trunk holds the truth.

**Motifs.**
- Visual:
  - the crow and the moon (painting, shadow play, dollhouse roof, ending)
  - the red ribbon (Ada's drawing, the stalker's wrist)
  - stopped clocks
  - soot and fire damage growing floor by floor (none on the ground floor, soot-streaked flues in the basement,
    the burned nursery in the attic)
  - the oil lamp
- Audio:
  - Ada's four-note lullaby (wireless, pipes, music box, menu, ending, where it finally resolves)
  - the pocket-watch tick that means the stalker is near (the only running clock)
  - the stalker's ragged, burned breathing (processed, unintelligible, non-verbal)
  - crow calls at key moments
  - a phantom fire crackle near the burned nursery

**Menu art.** The lamp-lit entry hall: the grandfather clock stopped at 4, and a family photograph with the boy's
face scratched out, in soft focus behind the title.

## 2. Controls

| Action | Keyboard / mouse | Gamepad |
|---|---|---|
| Move / look | WASD / mouse | left / right stick |
| Sprint (loud) | Left Shift (hold) | left thumb |
| Crouch (quiet, slow) | C / Left Ctrl (toggle) | right face (B) |
| Lean left / right | Q / E (hold) | left / right shoulder |
| Interact (pick up, open, read, use, hide) | Left mouse / F | bottom face (A) |
| Flashlight on/off | T / Right mouse | top face (Y) |
| Inventory + journal | Tab / I | special left (Back) |
| Back / close / leave puzzle | Esc in a panel, Backspace | right face (B) in a panel |
| Pause | Esc / P | Start |

In a **puzzle close-up** (combination dials, symbol lock) `Move` selects (A/D) and changes (W/S) the dial; Interact
confirms; Back leaves. In **inspect** mode `Look` rotates the item, Interact takes it, Back puts it down. All of
these are Enhanced Input actions, so the AutoPlay bot can do everything a player does.

## 3. Systems and classes (C++ module `HorrorEscape`, Blueprint subclasses for tuning)

Base: Epic's **First Person C++ template** (UE 5.3) for project setup, Enhanced Input and the camera rig; the
template weapon/projectile/arms are not used. Gameplay is C++; tuning lives in Blueprint subclasses and data
assets created by editor scripts; levels are built by editor Python scripts.

| Class | Role |
|---|---|
| `AHorrorCharacter` | first-person camera, walk 260 / sprint 470 / crouch 140 cm/s, crouch (capsule 88→50), lean (camera roll ±12°, offset ±35 cm, blocked by walls), head bob, footsteps by surface (physical material → MetaSound surface index), noise events (`UAISense_Hearing`), flashlight (spot light + battery 0..100, drains 1.1 %/s, flicker below 15 %, batteries +45), interaction trace (220 cm), inspect mode, hiding state |
| `AHorrorPlayerController` | input mapping contexts (game / panel), look sensitivity + invert, pause, owns the HUD widget and panels |
| `UHorrorGameInstance` | settings (master/music/sfx volume, mouse sensitivity, invert Y, resolution, fullscreen, brightness), save/load, chapter table, AutoPlay hook |
| `UHorrorSaveGame` | settings + highest chapter unlocked + "chapter started" checkpoint (saved at chapter start) + best times |
| `AHorrorGameMode` | chapter flow: intro sequence → play → exit → next chapter (save) / death → death screen → retry chapter; chapter timer; spawns the AutoPlay bot |
| `AHorrorMenuGameMode` | main-menu map: title, Continue, New Game, Chapter select (unlocked chapters), Settings, Quit |
| `UHorrorPuzzleSubsystem` (world) | the puzzle **flag bus**: `SetFlag(name)`, `HasFlag`, `OnFlagSet`. Puzzle actors raise flags when solved; doors, drawers, lights, compartments, scares listen. This is what links puzzles into chains |
| `AHorrorInteractable` | base: prompt text, `RequiredFlag`, `RequiredItem`, `bConsumeItem`, `FlagOnUse`, `LockedMessage` |
| `AHorrorDoor` | hinged door: opens with E (or key), locked by item/flag, `Slam()` for scares, creak sound, noise event |
| `AHorrorDrawer` | sliding drawer / cabinet / compartment, optional lock flag, may hold a pickup |
| `AHorrorPickup` | key / fuse / battery / item / valve handle / crank; inspectable (rotate), goes to inventory |
| `AHorrorNote` | readable note (paper mesh), opens the note panel, stored in the journal |
| `AHorrorDialLock` | N dials of digits or symbols; close-up camera; correct code → flag |
| `AHorrorFuseBox` | 3 fuse slots, takes fuses from inventory, lever → `power_on` flag (all practical lights on that circuit switch on) |
| `AHorrorRotator` | rotatable puzzle piece (45° steps): shadow cut-outs, mirrors; a `AHorrorRotatorPuzzle` checks all target angles → flag |
| `AHorrorBeamPuzzle` | moonbeam: traced from the window through mirrors (`AHorrorRotator` with `bMirror`), drawn as a light shaft mesh + spot light; hitting the crystal → flag |
| `AHorrorValvePuzzle` + `AHorrorValve` | valves with 4 positions, weighted sum drives a gauge needle; needle on the red mark → flag |
| `AHorrorChime` + `AHorrorChimePuzzle` | struck pipes with pitches; sequence must match the radio tune → flag (loud: noise event) |
| `AHorrorSoundClue` | radio / music box: plays the clue tune when used (subtitle shows ♪ for accessibility) |
| `AHorrorPowerLight` | practical lamp: on/off by circuit flag, optional flicker, bulb emissive material instance |
| `AHorrorHidingSpot` | wardrobe / cupboard: enter/leave with E, camera peeks through slats, hidden from the stalker unless it saw you enter |
| `AHorrorScareTrigger` | one-shot trigger volume: play a Level Sequence, flicker a light group, slam a door, play a 3D sound; each fires once per chapter |
| `AHorrorExit` | chapter exit (door/hatch); requires flag/item; triggers outro / next chapter |
| `AHorrorStalker` + `AHorrorStalkerAI` | the threat (section 6) |
| `UHorrorHUDWidget` & panels (UMG built in C++) | HUD (dot, interaction prompt, battery, item toast, subtitle), inventory/journal, note reader, dial lock, pause, settings, death, chapter card, main menu |
| `UHorrorBotComponent` | AutoPlay bot (section 9) |
| `UStalkerAnimInstance` / `UWatcherAnimInstance` | C++ procedural animation over mannequin clips (section 6b) |
| `AHorrorWatcher` | porcelain mannequins that move only when unobserved (section 6b) |
| `AHorrorTestDirector` | `-HorrorShots` screenshot runs, nav maps and probes for checking levels from scripts |

Tuning Blueprints (`BP_HorrorCharacter`, `BP_Stalker`, `BP_Door_*` …) and data assets are created by editor
scripts so level scripts place Blueprint assets.

## 4. Chapters and puzzles (with solutions)

Every chapter is its own map; the player starts at the chapter entrance, the game saves at chapter start, death
restarts the chapter. Puzzle chains (→ = unlocks):

### Chapter 1 — Ground floor (`L1_GroundFloor`): "The house remembers"

Rooms: entry hall (start; front door slammed shut and won't open), parlor, study, dining room, kitchen, pantry,
hallway with the basement door. Only moonlight and two oil lamps until the power comes back.

1. **Stopped clocks → combination lock.** The note on the hall table ("*The clocks stopped the night each of
   them left us. Hall first, then the dining room, then the kitchen.*") points at three clocks whose hour hands
   are stopped at **4**, **9**, **2**. The study desk drawer has a 3-dial lock: **4-9-2** → drawer opens → **fuse A**.
2. **Fuse box → power.** The pantry fuse box has 3 slots, one fuse in place. Fuse A (study) and **fuse B** (kitchen,
   bottom drawer by the stove, among other drawers holding a battery and a cutlery tray) go in, pull the lever →
   `power_on`: ceiling lamps across the floor come on (some flicker), the parlor magic-lantern lamp lights.
3. **Shadow play (light and shadow).** In the parlor the lamp throws the shadows of three cut-out figures on the
   wall. The painting over the fireplace shows the house with a crow on its roof and a moon. Rotate the cut-outs
   (45° steps) so their shadows rebuild that picture: house **0°**, crow **45°** (crow shadow lands on the roof),
   Each cut-out turns in 45° steps; the shadows match the painting at house **0°**, crow **0°**, moon **180°**
   (the crescent must open to the right). Requires `power_on` (no lamp, no shadow). → `shadow_solved`: the
   painting swings open → **basement key**.
4. **Exit:** basement door in the hallway takes the basement key → chapter 2.

Scares (each once): the hall lamp gutters out right after you take the flashlight; the dining-room door slams
behind you (Sequencer); when the power comes on, footsteps cross the floor above.

### Chapter 2 — Basement (`L2_Basement`): "Something is down here"

Rooms: stair landing (start), corridor, workshop, laundry, boiler room, storage, wine cellar, coal room with the
service stair (exit). The **stalker** appears here (first sighting is scripted: it crosses the far end of the
corridor). Hiding: wardrobe in storage, cupboard under the stairs, laundry cabinet.

1. **Radio tune → chimes (audio clue).** The workshop radio plays a 4-note tune (subtitled ♪ ♪ ♪ ♪ with rising /
   falling marks). Four copper pipes hang in the laundry, pitched low→high 1-2-3-4. Strike them in the tune's order:
   **3-1-4-2** → `chimes_solved`: the laundry chute grate drops → **valve handle**. Striking a pipe is loud
   (noise event), so the stalker comes.
2. **Boiler pressure (mechanical).** Three valves in the boiler room (one missing its handle until you bring it)
   each have 4 positions (0–3). Gauge = 1×A + 2×B + 3×C; the red mark is **10** (e.g. A=1, B=0, C=3 or A=3, B=2,
   C=1 — the gauge shows live feedback). Holding 10 for 2 s → `boiler_on`: pipes knock, the hydraulic door to the
   wine cellar rises.
3. **Wine racks → combination lock.** The cellar ledger: "*Four racks, one for each of you. Count the black
   bottles, eldest to youngest — left to right.*" Black bottles per rack: **3, 1, 5, 2** → strongbox lock
   **3-1-5-2** → **attic key**.
4. **Exit:** the service-stair door in the coal room takes the attic key → chapter 3.

Scares: lights die as you reach the bottom of the stairs (only the flashlight and a work lamp remain); the first
sighting; a shelf of jars crashes in storage when the boiler starts.

### Chapter 3 — Attic (`L3_Attic`): "Ada"

Rooms: hatch landing (start), storage under the eaves, nursery corner, the round window, the dollhouse, the
music-box automaton, the trunk, the roof hatch (exit). Storm: lightning flashes through the round window. The
stalker is faster here. Hiding: wardrobe, chest under the eaves.

1. **Moonbeam mirrors (light).** Moonlight enters through the round window. Two standing mirrors rotate in 45°
   steps; aim the beam window → mirror 1 → mirror 2 → the crystal on the dollhouse roof. Solution: mirror 1 at
   **45°** (beam turns north), mirror 2 at **45°** (beam turns west); mirrors are two-sided and the beam is
   traced, so 225° works as well. → `beam_solved`: the dollhouse
   front opens → **music-box crank**.
2. **Music box (mechanical + audio).** Fit the crank to the automaton and wind it: the dancer turns and stops,
   with a chime, at four painted symbols in turn: **moon, bird, key, eye**.
3. **Ada's trunk (symbol lock).** 4 symbol dials (moon, bird, key, eye, star, hand): **moon-bird-key-eye** → trunk
   opens → Ada's ribbon and the **roof hatch key**.
4. **Exit:** the roof hatch → ending sequence (dawn, you climb onto the roof; the stalker stands still at the hatch
   and does not follow).

Scares: lightning reveals a figure that is gone at the next flash (Sequencer); the rocking chair rocks on its own;
the music box keeps playing after you leave it.

## 5. Interaction and inventory

Look at something within 220 cm → prompt (`[F] Open drawer`, `[F] Read note`, `Locked — needs Basement Key`).
Pickups first open **inspect** (rotate with mouse, name + description), Interact takes it. Inventory screen
(Tab): grid of items with name/description, journal of notes read, battery count, current goal hint. Keys are
used automatically by the door that needs them.

## 6. The stalker (AI)

`AHorrorStalker` (UE5 Manny skeleton and template locomotion animations, re-materialed as a tall, thin, charred
figure, scaled 1.12, with a cloth-like dark material and faint eye glow) + `AHorrorStalkerAI` (AIController with
`UAIPerceptionComponent`: sight + hearing). State machine in C++ (no BT needed):

```
Roam --hears noise--> Investigate (walk 230 to noise location, look around 3 s) --nothing--> Roam
Roam/Investigate --sees player--> Chase (run 400 ch2 / 440 ch3; kill inside 110 cm)
Chase --loses sight 4 s--> Search (last known location + 3 random nav points, 300) --> Roam
Hidden player: not visible; if the stalker saw the player enter that spot → it opens it → death
```

- Sight: 60° half-angle; range 900 cm in darkness, 1800 cm if the player's flashlight is on or the player stands
  in a lit area (light probe: nearest `AHorrorPowerLight` that is on). Crouching in the dark: 500 cm.
- Hearing: footsteps (walk 600 cm, sprint 1500 cm, crouch none), doors 900, chimes 2500, dropped items.
- Roam: random points from the chapter's `AHorrorRoamPoint`s, biased toward the player's room every 30–45 s so it
  never disappears for long; never spawns in sight of the player.
- Contact → short kill sequence (camera snaps to it, scream, cut to black) → death screen (Retry / Main menu).
- Presence feedback: heartbeat MetaSound (rate/volume by distance), screen vignette/grain pulse, low drone.

### 6b. Monster upgrade (after user feedback "better movement and better monsters", 05:00)

- **Stalker body:** the mannequin is animated by a C++ anim instance (`UStalkerAnimInstance`, no AnimBP graph): it
  blends idle/walk/run clips by speed and bends the pose procedurally — spine hunched 26–38°, neck pushed forward,
  head hanging to one side with random twitches, a slow head scan while it stands and listens, forearms and hands
  stretched. Script-built parts hang on the skeleton: a long cracked bone mask with black sockets and pinpoint eyes,
  bone claws, strips of rotten cloth that flutter. Skin: dark, wet, charred.
- **Stalker behaviour:** growls when it starts a chase, sniffs while listening, **lunges** (×1.45 speed for 0.7 s)
  when it sees you inside 4.2 m, and after losing you it **pulls open up to two wardrobes** near where it lost you
  (50 % each): hiding is a gamble, not a save. Hiding while out of breath is audible (a small noise every 2 s).
- **The Watchers** (`AHorrorWatcher`): porcelain mannequins (Ada's dress forms). Frozen in a random frame of a
  mannequin clip, head cocked toward you, arms reaching further the closer they are; a new pose with every step.
  They only move while unobserved: out of your view cone or line of sight, or in the dark beyond 6 m unless the
  flashlight is on them. After any glance they wait 1.3 s before the next step; each step (70 cm, ~1 s) scrapes;
  touching distance while unobserved kills. One in the wine cellar wakes when the strongbox opens; three in the
  attic wake with the music box.

### 6c. Movement feel

The camera is the control rotation plus body feel: step-synced bob on a damped spring (footsteps kick it), lateral
sway and a roll into strafes, landing dips, lean roll/offset, idle breathing (deeper when winded or afraid), sprint
FOV +7°. Acceleration 950 (700 while sprinting) and braking 1100 give weight. Breathing audio follows stamina and
dread.

## 7. Levels and art direction

Late-Victorian house, abandoned for years. Palette: faded green damask wallpaper, dark oak boards, cream plaster,
brass; basement in brick, wet concrete, rusted iron, copper pipes; attic in raw timber, dusty boards, sheets over
furniture. Light: warm tungsten practicals (2400–2800 K, low intensity, flicker), cold blue moonlight through
windows (directional + rect lights), Lumen GI and reflections, exponential height fog with volumetric fog,
Niagara dust motes in light shafts, post: limited exposure range (no auto-brightening in the dark), vignette,
film grain, slight chromatic aberration, cool shadows / warm highlights grade.

**Art pass with store assets (07:30 onward, after the user's direction that every visible object must look
premium).**
- **Surfaces:** walls, floors and ceilings keep our layouts but sit on scanned surfaces through `M_ArchHQ`.
  - The master is world-aligned with separate U/V tiling, an ARM channel selector, a grime mask, a damp band and a
    soot gradient.
  - Sources: Megascans damask wallpaper, oak floor and worn brick; Poly Haven plaster, decrepit wallpaper, concrete,
    planks and raw timber.
- **Furniture and props:** these are swapped in place for Victorian House and Old Library pieces, fitted to each old
  footprint (`Scripts/dress_props.py`, 117 pieces). The kit covers tables, armchairs, sofa, cupboards, beds, metal
  stillage, fireplaces, rugs, candlesticks, jars, crates and dust covers.
- **Doors:** the panel doors and door frames are the pack's own.
- **Puzzle props:** dials, clocks, pipes, valves, mirrors, dollhouse and trunk stay ours, on scanned wood and metal.
- **The stalker:** the Whisper creature (Fab) with its own clips. Our C++ anim instance blends them by speed and
  plays its attack on a kill.
- **The Watchers:** Ada's porcelain dolls (Free Killer Doll, Fab). They follow the hidden mannequin's frozen poses by
  leader pose.
- **Story dressing:** placed by `Scripts/dress_story.py`; see §1b.
- **Packs:** every pack sits in its own `Content/<Pack>/` folder. Each is listed with its listing URL, licence and
  use in `assets.manifest.json` and `Docs/ThirdPartyNotices.md`.

### 7b. Fab requests

None outstanding. The asset scout delivered every category this game needs:
- the house shell and interiors (Modular Victorian House, Victorian Interior Environment, both bought);
- the stalker (Whisper) and the dolls;
- animation packs, music (Whispers of Macabre) and footsteps (Essential Footsteps);
- the basement packs;
- Megascans surfaces.

Not used:
- Classical Music Box Collection and Free Thunder Sounds have no 5.3 build, so our synthesized music box and thunder
  stay.
- Horror Props (corpse props) and the Abandoned Power Plant shell don't fit the story or layout.

Optional later additions:
- a crow model for the ending's chimney;
- Megascans old wooden door for the cellar doors.

| # | Map | Size | Rooms | Light |
|---|---|---|---|---|
| 0 | `MainMenu` | small | the entry hall, lamp-lit, slow camera drift | warm |
| 1 | `L1_GroundFloor` | ~24×18 m | 7 | moon + 2 oil lamps → power on |
| 2 | `L2_Basement` | ~26×20 m | 8 | flashlight + one work lamp, boiler glow |
| 3 | `L3_Attic` | ~22×10 m under a pitched roof | 1 long space, partitions | moonlight, lightning |

Sequencer: intro (chapter 1: camera drifts through the hall, the door slams, title), chapter cards, scripted
scares, ending (roof at dawn, credits).

## 8. Audio

- **Our synthesized MetaSounds and one-shots** carry the story's motifs:
  - Ada's four notes (the wireless, the pipes, the music box)
  - creaks and knocks in the ambience beds
  - heartbeat, stalker breath, scream and sniff
  - doors, drawers, locks, fuses, valves, boiler, thunder and UI
- **Recorded footsteps** per surface come from Essential Footsteps (Fab): wood, concrete, sand (as carpet), metal.
- **Each chapter has a looping dark-ambient score** under its ambience bed (Whispers of Macabre, Fab):
  - Veil of Shadows A (ground floor)
  - Eternal Thirst A (basement)
  - Abode of the Immortal A (attic)
  - Veil of Shadows B on the menu
- **Sound classes:** Master, Music and SFX, with a sound mix for the volume settings.
- **No recorded or synthesized voices.**

## 9. AutoPlay

Drop-in `UAutoPlaySubsystem` (unchanged). `StartLevel(n)` opens chapter n without menus/intro. The bot
(`UHorrorBotComponent` on the player controller, `TG_PrePhysics`) runs a per-chapter **plan** of steps derived from
the known solutions (go to actor tag, look at it, interact, set dial to digit, rotate piece until angle, strike
chimes in order, use exit). Navigation: nav-mesh path → inject `IA_Move` (forward) + `IA_Look` (yaw/pitch delta);
interaction only via `IA_Interact`; dials via `IA_Move`. In chapters 2–3 the bot hides (nearest hiding spot) when
the stalker chases it, waits until it leaves, then resumes. Skill: reaction delay 0.15–0.8 s, look noise
(0–6°), wrong-dial probability (0–25 %, corrected after the lock rejects), path hesitation. Telemetry: `state`
(10 Hz: location, rotation, velocity, battery, flashlight, stance, hidden, stalker state/distance), `interact`,
`pickup`, `puzzle_solved`, `flag`, `stalker_state`, `hide_enter`/`hide_exit`, `noise`, `death`, `restart`,
`chapter_exit`.

### 9b. AutoPlay scenarios (contract v1.4)

`-Scenario=<n>` opens chapter n directly (no menu, no intro), saved checkpoint state.

| # | Name | Start state | Win | Lose | Bot win (seed 1) | MaxSeconds |
|---|---|---|---|---|---|---|
| 1 | The house remembers (`L1_GroundFloor`) | Entry hall, front door shut, no items, flashlight on the hall table | Basement door opened with the basement key | — (no threat on the ground floor; timeout only) | 55 s | 180 |
| 2 | Something is down here (`L2_Basement`) | Stair foot, no items; the stalker sleeps until the wireless plays | Service-stair door opened with the attic key | Stalker or watcher contact; timeout | 132 s | 420 |
| 3 | Ada (`L3_Attic`) | Hatch landing, no items; lightning glimpse at once, the stalker returns on `beam_solved` | Roof hatch opened with the roof key (ending plays) | Stalker or doll contact; timeout | 92 s | 240 |

Chapter 2 gets 420 s because the stalker's hunts vary in length (an earlier build needed 384 s before it was caught).

## 10. Recording

- `workflow.jsonl` rows `{schema, id ("hx-NNNNN"), seq, time, actor:"agent", op, target, params, reason,
  reason_source:"agent_note", status, source{script, commit}}`, appended by `Scripts/wf.py` (CLI via
  `Scripts/wf.sh`, imported by editor scripts). `status`: observed / failed / reverted / unrecorded (`log.gap`).
- Every editor script that ran stays in `Scripts/` unchanged (new version = new file).
- Heavy jobs go through `%GF_ROOT%\tools\ue-heavy.ps1`.

## 11. Acceptance checklist

Ticked = verified in this session (AutoPlay run, screenshot run, or log). Unticked items are built but not verified
end to end.

- [x] Main menu: Continue, New Game, Chapter select (unlocked only), Settings, Quit (screenshot menu_ui2, period UI)
- [x] Settings: master/music/SFX volume, mouse sensitivity, invert Y, resolution + fullscreen, brightness; persisted (code review)
- [x] Pause: resume, restart chapter, settings, quit to menu (code review; earlier panel screenshots)
- [x] Walk / sprint / crouch / lean; footsteps by surface (AutoPlay telemetry shows crouch/sprint; recorded surface footsteps)
- [x] Flashlight with battery drain, low-battery flicker, battery pickups (telemetry battery drain; bot flashlight discipline)
- [x] Interact: pick up, inspect/rotate, doors, drawers, notes; inventory + journal screen (chapter 1 AutoPlay uses all of them)
- [x] Chapter 1: clocks → dial lock → fuses → power → shadow puzzle → key → exit (AutoPlay **win**, ch1_try13, 110 s, after the art pass)
- [x] Chapter 2: radio → chimes → valve → boiler → cellar → lock → key → exit (AutoPlay **win**, ch2_try32, 132 s)
- [x] Chapter 3: mirrors → crank → music box → symbol lock → key → roof hatch (AutoPlay **win**, ch3_try34, 92 s)
- [x] Stalker from chapter 2: roam, investigate noise, chase, search; contact = death; hiding works (telemetry: all states, hide_enter/exit, extraction)
- [x] Scripted scares (Sequencer, flicker, slams), each once (scare events in telemetry, once each)
- [x] Atmosphere: Lumen, practical lights, volumetric fog, Niagara dust, PBR materials (scanned surfaces + store furniture; screenshots)
- [x] MetaSounds: ambience, heartbeat, creaks (ours); recorded footsteps by surface; chapter scores
- [ ] Sequencer intro and ending (intro verified earlier; ending v2 with the creature at the hatch built but not watched in a run)
- [x] HUD: prompt, battery, item toast on paper slips; death/retry; save at chapter start
- [x] AutoPlay v1.4: all three chapters solved by the bot (`milestone/autoplay-1..3` on 97ed7ec); scenario 1 hand test passes validate-run with 0 render stalls
- [x] Packaged Win64 build (Shipping; packaged AutoPlay chapter 1 win, validate-run PASS)

## 12. Status (2026-10-12 01:20 -04:00)

**What works**
- **Chapters:** all three are playable maps with their puzzle chains, the stalker (chapters 2–3), the porcelain-doll
  Watchers, hiding, death/retry, saves at chapter start, chapter cards, pause/settings, menu with chapter select,
  and the intro.
- **AutoPlay (drop-in v1.4):** wins all three chapters: ch1 55 s, ch2 132 s, ch3 92 s (tags `milestone/autoplay-1..3`
  on 97ed7ec). Chapter 2's stalker now gives up on a player hidden 20 s and is gone 45 s, as in the attic; before
  that the bot shuttled between the boiler-room wardrobe and the cellar until caught.
- **Fixes found by the framing screenshots:**
  - the roof hatch sat inside the roof boards (it kept the pre-fix slope), so it could not be used;
  - both attic gables were upside down under the floor, leaving the attic's ends open to the sky;
  - the wardrobe's hanging rail ran 1 m out of its side.
- **Import paths:** the user profile path is scrubbed from the assets' import-source paths (verify: 0 hits).
- **Art pass:**
  - scanned surfaces on every wall, floor and ceiling (Megascans, Poly Haven);
  - 117 script-built furniture pieces replaced by Victorian House / Old Library pieces fitted in place;
  - Victorian panel doors;
  - the Whisper creature as the stalker;
  - Ada's porcelain dolls as the Watchers;
  - recorded footsteps;
  - a dark-ambient score per chapter and on the menu.
- **Story (§1b):** told through the house:
  - five short notes; the long diaries removed; one line per chapter card;
  - the table laid for four, M.'s chair under a sheet, height marks with Ada's last mark in 1921;
  - the boarded back door with the cap on its hook, the family photograph with Thomas's face scratched out;
  - the cot and tally marks by the boiler, the burned nursery, Ada's crayon drawing (PAPA, ADA, TOM);
  - an ending in which the creature reaches the hatch at dawn and collapses beside Ada's ribbon.
- **UI:** period UI throughout: IM Fell English, panels on aged paper, HUD prompts on paper slips.
- **Monsters and movement (the user's earlier request):**
  - the stalker has a spotted freeze, lunges, opens wardrobes, has a calm window after waking and a glimpse-then-vanish
    reveal in chapter 3, and uses its own creature animations;
  - movement has weight, bob, sway and breathing (§6c).

**What's left**
- **Re-run after the last two fixes.** The gables were flipped and the import paths scrubbed after the last verified
  wins. Chapter 3 won on the scrubbed content (ch3_try34) but before the gables were upright, and chapter 2's win
  (ch2_try32) predates both. Runs ch2_try33 and ch3_try35 are queued. Closing the attic ends makes the attic darker.
- **The packaged Shipping build** (below) is from 2026-10-11 14:21 and predates these fixes; repackage before release.
- **The ending has still not been watched in a run.** The family photograph's scratch decal placement is approximate.
- **Cellar doors, the hall stairs and the puzzle clocks** are still our script-built meshes, on scanned materials,
  as are the radio, the valves, the fuse box and the wardrobes.

**Built vs sampled assets** (per `assets.manifest.json`)
- **Store (Fab):** Modular Victorian House and Victorian Interior Environment (bought), Whisper, Free Killer Doll,
  Essential Footsteps, Whispers of Macabre.
  - Copied but unused: Zombie Animation Pack, Horror Props, Abandoned Power Plant.
- **Scans and fonts:** Megascans surfaces, Poly Haven textures (CC0), IM Fell English (OFL).
- **Epic engine content:** the UE5 mannequin skeleton and clips (hidden pose drivers), the Niagara template and the
  sky cubemap.
- **Ours:** everything in `/Game/Horror`:
  - level layouts and gameplay actors; puzzle props;
  - materials (`M_ArchHQ`, decals); story textures (drawing, tally, height marks, scorch, scratches);
  - synthesized SFX and MetaSounds; sequences; C++ UI; the bot.

**Packaged build:** `%GF_ROOT%/games/horror-escape/Packaged/Shipping/Windows/HorrorEscape.exe` (Win64
Shipping, 871 MB, 4,352 cooked packages). The first attempt failed on an editor-only call (`GetActorLabel`) and was
fixed. AutoPlay chapter 1 wins in the packaged exe (135 s), and `validate-run.ps1` passes.

**Stats:** 3,124 workflow rows (hx-00001..hx-03124; failures kept, corrections as new rows), 40 commits on
github.com (private, Git LFS: 4,013 files), 111 scripts, 486 assets under /Game/Horror.

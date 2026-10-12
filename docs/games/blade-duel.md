# WHETSTONE: story bible and game design

One-on-one 3D blade-duel fighting game, Unreal Engine 5.3, C++ module `BladeDuel`. Slug `blade-duel`.
Status: **design draft 2026-10-12, waiting for the coordinator's OK** (section 14).

## 1. The game in one paragraph

Ninety winters of war ended when the four Seats of Coriant swore the **Whetstone Concord**: no army marches again.
Every quarrel between Seats is settled by two champions in a duel, and the loser does not die: they **yield**, their
blade is struck from their hands and planted in the Field of Hilts under the Whetstone, a sea-cave at the heart of
the land, and the ruling is law. Once a generation the Concord calls the **Open Rite**, when every grievance is
fought at once and the last champion standing must face the keeper of the Concord, the masked **Whetwarden**. This
is that year. Four champions with four different blades fight a best-of-three ladder across their home grounds
(dawn saltpans, a castle dam, a lantern-lit cliff stair, a melting ice shelf) and then descend into the Whetstone,
where the Warden waits with a poleaxe called *the Last Word*, and where the blades they won are already planted.
Modes: **Rite** (story ladder vs CPU), **Versus** (two players on one PC, shared camera; or player vs CPU),
**Practice**.

Not liaozhai-night: no exploration, no 2.5D, no monster hordes. A versus duel fighter: two fighters, one ring,
rounds, frame data, guard, parry, posture.

## 2. Story bible

### World: Coriant and the Concord

- **Coriant**, a windy coastal land of terraces, sea cliffs and ice to the north. Late-medieval technology,
  no magic beyond the hints that skilled people read as magic (a sword drawn so fast it seems to ring twice).
- **The Ninety Winters**: the war between the Seats, three generations ago. It ended at the Whetstone when the last
  champion of the war, alone on a field of the dead, swore never to let another army form. The blades of the war
  were melted and forged into one poleaxe, *the Last Word*, and the oath became the Concord.
- **The Whetstone Concord**: a quarrel between Seats is settled by a **Rite**: one champion each, best of three
  *edges* (rounds). An edge ends when a champion's vigour is spent or when they are broken and made to **yield**.
  The losing champion's blade is planted in the **Field of Hilts**. The ruling cannot be appealed. No one dies:
  the Concord's whole point is that the quarrel costs a blade, not a life.
- **The Open Rite**: called once a generation. Any champion may challenge; the last undefeated champion wins their
  Seat's claim **and must face the Whetwarden**. Nobody outside the cave knows what happens to the champion who beats
  the Warden. The last Open Rite was forty-one years ago. Its champion never came home.

### The four Seats and their quarrel (why everyone duels this year)

| Seat | Place | Grievance |
|---|---|---|
| **Merrow** | southern saltpans and rice terraces | Highcourt's new dam starves Merrow's terraces of fresh water; the pans go to brine |
| **Highcourt** | the castle-city on the river, built the dam | defends the dam ("the water is Highcourt's") and its right to rule the river |
| **Rimeshelf** | the northern ice shelf | the ice is thawing, its villages are sinking; it claims land in Merrow |
| **Calder** | *drowned* in the Ninety Winters; its people live on **the Stair**, a city cut into the sea cliff | has had no Seat for sixty years; the Concord calls it "dormant"; the Stair wants it back |

### The fighters (original; no likeness to any existing fighting-game character)

| Fighter | Seat | Blade | Who they are | Why they duel |
|---|---|---|---|---|
| **Ishen Mor**, "the Terrace Blade" | Merrow | **moonedge**: a single-edged curved sword, drawn from a lacquered scabbard (the katana role) | a salt farmer's son, self-taught on the ferry posts; quiet, exact, polite to everyone he beats | the farmers chose him because he has never lost a wager on the posts; if he loses, Merrow's terraces die |
| **Ser Odric Hale**, "the Lamp of Highcourt" | Highcourt | **greatsword** *Vow*, two-handed (the longsword role) | the oldest knight of the Lamp-Guard, scarred, courteous, privately thinks the dam is wrong | duty: his oath binds him to defend Highcourt's claim even when he disagrees with it |
| **Kesh Sarrow**, "Debt and Due" | Calder (the Stair) | **twin sabres** she calls Debt and Due | a Stair duellist who learned in alleys and pays her rent in wagers; fast, funny, furious | to wake Calder's Seat: if a Stair champion wins the Open Rite, the Concord must hear Calder again |
| **Hessa Rime**, "Thawmoon" | Rimeshelf | **crescent glaive** *Thawmoon*, with a blue cord on the shaft | a young ice-shelf ferrier, tall, patient, keeps distance like weather | publicly: land for her sinking village. Privately: her grandmother **Aud Rime** won the last Open Rite and never came home. Hessa wants to know why |
| **The Whetwarden** (boss) | the Concord | **poleaxe** *the Last Word* | huge, masked, armour grown over with salt; never speaks above a few words; a faded blue cord is knotted on the poleaxe | the Concord's keeper; every Open Rite ends against them |

**The truth (late payoff):** the Whetwarden is not a guardian appointed by the Seats. The Warden is always **the
last Open Rite's champion**: whoever beats the Warden must take up *the Last Word* and stay, so that every Rite
ends against someone everyone fears to lose to, and the Concord holds. The current Warden is **Aud Rime**,
Hessa's grandmother, forty-one years in the cave. The blue cord on the poleaxe is the cord missing from Hessa's
glaive. Every finisher the player performed on the way down was not only a victory: it was a blade delivered to the
Warden's field.

### How the story surfaces in play (never a wall of text)

All lines are subtitles in the styled subtitle band (section 10), under 15 words, with the speaker's portrait; no
recorded or synthesized voices. Synthesized foley only (breath is a soft filtered noise, not a voice).

| Where | What the player sees | What it means |
|---|---|---|
| Rite title card (one per duel) | Arena name + one line, e.g. *Merrow Saltpans*: "The pans are white. They should be green." | Each Seat's quarrel, in one breath |
| Pre-fight (intro, ~4 s) | Two lines: challenger, then defender, over their intro emotes | Why these two fight, personal stakes |
| Yield (finisher) | The loser's blade spins out and plants in the ground; one short line from the loser | The Concord's rule, shown, not told |
| Arena dressing | Saltpans: Highcourt's dam on the horizon, cracked channels. Dam-Crown: closed sluices carved "THE WATER IS HIGHCOURT'S". The Stair: drowned Calder towers visible below the tide line, Calder's sigil chalked on doors. Rimeshelf: houses half-sunk in meltwater, a marker post with a blue cord stub | The grievances are real places |
| The Whetstone | The Field of Hilts: thousands of planted blades; at the front, **the actual blades of the three rivals the player beat this ladder** (spawned from the ladder record); one glaive with no cord | The player's victories, collected |
| Warden duel | The Warden's poleaxe carries a faded blue cord. To Hessa only, the Warden's last line is personal | The reveal, for Hessa; a hint for the others |
| Ladder ending | Three in-engine stills with one subtitle each | Each fighter's answer to the Warden's burden |

**Pre-fight lines (challenger first).** Every ladder pair has its own exchange; the full table lives in the
`DT_Dialogue` DataTable (`Content/Data/Dialogue.csv`). The ones the scenarios show:

| Duel | Lines |
|---|---|
| S1 Ishen vs Odric (Saltpans) | Ishen: "Open the dam, Ser Odric. I'll bow and go home." / Odric: "I'd like that. My oath wouldn't." |
| S2 Kesh vs Hessa (the Stair) | Kesh: "Lost, ice-girl? The Stair charges for directions." / Hessa: "Then I'll pay. Seen a blue cord, forty years old?" |
| S3 Hessa vs Warden (Whetstone) | Hessa: "Champions come here. None go home. Why?" / Warden: "...Someone must stay." |
| Ishen vs Kesh | Kesh: "Farm boy with a pretty sword." / Ishen: "Farm boys sharpen everything." |
| Ishen vs Hessa | Hessa: "Your pans or my village. One of us drowns." / Ishen: "Then let's be quick and fair." |
| Odric vs Kesh | Kesh: "Highcourt sank Calder too. Remember that?" / Odric: "I remember. I was there. I'm sorry." |
| Odric vs Hessa | Odric: "Your grandmother beat me once. I was fifteen." / Hessa: "Then you know how this ends." |
| Kesh vs Odric | Odric: "Go home, child." / Kesh: "Show me where it is, old man." |
| Hessa vs Odric | Hessa: "You knew her. Where did she go?" / Odric: "Down. Like all of them." |
| any vs Warden | Warden: "Every blade you took, you brought to me." |

**Yield lines** (one per fighter, said by the loser when planted): Ishen "Well struck. I yield."; Odric "The Lamp
yields. Gladly, almost."; Kesh "Fine. Keep Debt. I'll want Due back."; Hessa "The ice yields. For now."; Warden
(on the final yield) "...Then it's yours."

**Ladder endings (three stills each):**
- **Ishen**: the dam opens and water runs green through the terraces / he plants his moonedge beside the poleaxe /
  "Farmers don't keep blades. Someone else can stay." (He walks out; the Warden stays.)
- **Odric**: Odric rules against his own Seat and opens the dam / he lifts *the Last Word* / "An old oath for a
  new one. Go home, Aud."
- **Kesh**: Calder's banner over the Stair / she plants the poleaxe in the Field and leaves it / "Five Seats. No
  Warden. Let them argue."
- **Hessa**: the Warden unmasks: a grey-haired woman with Hessa's eyes / Hessa takes the poleaxe and ties the blue
  cord on her own wrist / "Go see the thaw, grandmother. I'll keep the stone."

Motifs: the struck bell that opens every edge; planted blades (every arena gets one more per finished ladder
duel); the blue cord; water (dam, brine, tide, meltwater) as the thing every Seat is actually fighting over.

Tone: grave, warm, physical. Weathered steel, salt, wind, lantern light. Fights are fierce but nobody bleeds:
hits read through sparks, hit-stop and stagger; no gore, no deaths (round losers kneel or fall exhausted).

## 3. Modes and flow

- **Main menu** (Rite / Versus / Practice / Settings / Quit) over a slow camera drift across the Field of Hilts.
- **Rite (story ladder)**: pick a fighter → 3 rivals in a fixed order per fighter, each on the rival's or the
  quarrel's ground, CPU tier rising 1→3 → the Whetwarden (tier 4) in the Whetstone → ending stills. Losing a duel:
  "Rise" (retry) or "Leave the Rite" (menu). Progress (fighter, duel index, beaten rivals' blades) saved in a
  `USaveGame`; finishing any ladder unlocks the Warden in Versus.
- **Versus**: P1 vs P2 (two gamepads, or split keyboard, or one of each; shared camera) or P1 vs CPU (tier
  choice). Fighter select (both cursors on one screen), arena select (or random), best of 3.
- **Practice**: pick fighter and opponent; opponent behaviour Stand / Guard / Parry sometimes / CPU tier; move list
  overlay with frame data; infinite vigour toggle.
- **Pause**: resume, move list, settings, leave. **Settings**: master/music/SFX volume, resolution, window mode,
  CPU difficulty default, control display (keyboard split / gamepad), subtitles size.

## 4. Combat systems

### Simulation and frame data approach

- Combat runs in a **fixed-step 60 Hz duel simulation** (`UBDDuelSim`, a world subsystem with an accumulator),
  independent of render frame rate, seeded from `-Seed` / a match seed. All timing is in **sim frames (1/60 s)**.
- Every move is a row in a per-fighter **DataTable** (`DT_Moves_<Fighter>`, from `Content/Data/Moves_<Fighter>.csv`,
  imported by script): input, height (Mid / Low / Overhead / Unblockable), startup, active, recovery, damage,
  poise damage, hit stun, block stun, on-block advantage, range, tracking (linear / tracking), lunge distance,
  cancel windows (chain-into list, cancel frame), armour frames, the montage and its section, trail on/off.
- **Animation follows the data, never the reverse**: an offline analysis script (`Scripts/analyze_clips.py`, run in
  the editor) measures each source clip's length, the frame where the blade tip's speed peaks and the root-motion
  curve; the move's startup/active/recovery are chosen from that and the montage play rate is set so the clip's
  strike frame lands exactly on the first active frame. Root motion is extracted into a per-move displacement
  curve that the sim applies (no anim-driven movement, so it is deterministic and feet don't slide).
- **Hit detection** (changed while writing the sim, 2026-10-12): during active frames a move hits if the target is
  within the move's **reach** (cm from the attacker's centre, plus body radius) and inside its **arc** (degrees
  around the attacker's facing). Analytic reach + arc on the floor plane keeps the fight deterministic and
  independent of animation playback (a blade sweep against hurt capsules would depend on the pose and frame rate);
  the blades (base/tip points per weapon) are used for sparks and trails. One hit per move per target.
  Weapon-vs-weapon **clashes**: both fighters land active frames on each other in the same step → both recoil,
  sparks, no damage.

### Universal rules

| Rule | Value |
|---|---|
| Vigour (health) | 1000 (Warden 1400) |
| Poise (posture) | 100 (Odric 130, Kesh 85, Warden 170); regenerates 15/s after 75 frames without poise damage, 5/s while guarding |
| Edges (rounds) | best of 3, 75 s each; timeout = higher vigour % wins the edge |
| Arena | circular ring 11-14 m across with a soft boundary (no ring-outs, no wall combos) |
| Input buffer | 8 frames; Light+Heavy within 3 frames = Shove |
| Hit-stop | light 5 f, heavy 8 f, counter +2 f, parry 10 f, break 12 f; both fighters freeze, no camera shake |

- **Two guards (directional guard).** Hold **Guard** = **Crest guard** (blade high): stops Mid and Overhead
  attacks. Hold Guard + **down** = **Root guard** (crouched, blade low): stops Mid and Low attacks. Overheads beat
  Root, Lows beat Crest, Mids are stopped by both. Blocking costs poise (the move's poise damage), no vigour.
  Blocked heavies push back. Guarding slows walking to 50 %.
- **Parry ("Turn").** Pressing Guard so the guard *starts* within the defender's parry window (6 frames; Ishen 7,
  Odric/Warden 5) before the attack's first active frame, with the matching guard (Crest for Mid/Overhead, Root
  for Mid/Low), **turns** the blade: attacker loses 30 poise and recoils 26 frames, defender gets a free
  **Riposte** (the next attack within 20 frames does 1.5x damage and cannot be guarded). A Guard press only opens
  a parry window if Guard was released for at least 12 frames (no mashing). Heavies can be turned; Shoves cannot.
- **Dodge.** Dodge + up/down = **sidestep** (22 frames, evades *linear* attacks on frames 4-14; *tracking*
  attacks still hit); Dodge + back = **backstep** (18 frames, evades frames 3-10); Dodge + forward = **dash in**
  (12 frames, no evasion). A second dodge within 40 frames has half the evasion frames.
- **Counter hit.** Hitting a fighter during their startup frames: +25 % damage, +50 % poise damage, +8 frames hit
  stun, a styled COUNTER stamp.
- **Shove** (Light + Heavy): short unblockable push (14 f startup), 25 poise damage, no vigour, leaves the target
  at -12; beats turtling, loses to any attack or dodge.
- **Break.** Poise at 0 → **Broken** for 70 frames (stagger loop, the guard is open). A heavy on a broken fighter
  is a **Break Strike** (2x damage).
- **Finisher: the Yield.** A Break Strike on a broken fighter whose vigour is at or under 30 % becomes the
  fighter's **Yield** (finisher): a 1.6 s sequence at 0.6x speed (no camera change beyond the normal framing, no
  FOV change), the victim's blade is struck out and plants upright in the ground, and the edge ends **YIELDED**.
  A vigour-0 knockout ends the edge **SPENT** (the loser drops to one knee).

### Controls (all Enhanced Input; per-player action assets so both players can be injected and logged apart)

| Action | P1 keyboard | P2 keyboard | Gamepad (each player) |
|---|---|---|---|
| Move (2D): left/right = toward/away along the duel line, up/down = circle step | W A S D | arrow keys | left stick / d-pad |
| Light | F | Numpad 1 | X / Square |
| Heavy (hold 0.4 s = charged, fighters that have one) | G | Numpad 2 | Y / Triangle |
| Guard (hold; + down = Root guard) | H | Numpad 3 | RB / R1 (or RT) |
| Dodge (+ direction) | Space | Numpad 0 | A / Cross |
| Pause | Esc | Numpad Enter | Start |

Directions are relative to the fighter's facing, so "forward" is always toward the opponent whichever side of the
screen they are on. Input actions are `IA_P1_Move`, `IA_P1_Light`, ... and `IA_P2_*`: the AutoPlay drop-in tracks
held inputs per action asset, so two injected players need separate assets, and the action name then records which
player acted (`inputs.jsonl`: `"action":"IA_P2_Guard"`). Local player 0 owns both keyboard contexts and gamepad 0;
local player 1 is created for gamepad 1; the P2 fighter merges both sources.

## 5. Roster and movesets

Each fighter is a licensed Paragon hero body (free Epic content on Fab, renamed, re-skinned with an alternate skin or
material tints, original names and story; the name "Paragon" never appears in the game) driven by its **own** matched
animation set (attacks, guard, hit reacts in four directions, knockback, stun loop, death/fall, victory pose,
select-screen loop and intro emote), plus extra clips where a style needs them. Frame numbers below are the design
targets; the analysis script adjusts them to the clips within ±3 frames.

### Ishen Mor (moonedge): balanced, best parry, the draw

Body: Paragon **Feng Mao**, *Royal Guard* skin (on disk). Walk 360 cm/s, range 210 cm.

| Move | Input | Height | Frames (start/active/rec) | Dmg / Poise | Notes |
|---|---|---|---|---|---|
| Ferry Cut 1-2-3 | L, L, L | Mid, Mid, Overhead | 10/3/14, 12/3/16, 16/4/22 | 60/8, 70/8, 95/16 | 3rd hit overhead |
| Rising Moon | H | Mid | 20/4/24 | 130/26 | |
| The Draw | hold H | Mid, tracking | 28/4/30 | 210/40 | sheathe-and-draw, armour none |
| Brine Sweep | down + H | Low | 19/4/26 | 110/22 | |
| Post Step | forward + L | Mid | 13/3/18 | 70/10 | lunges 120 cm |
| Turning Cut | sidestep + L | Mid, tracking | 14/4/20 | 75/12 | |
| Riposte | after a Turn | Mid | 8/3/16 | x1.5 | |
| Yield | Break Strike ≤30 % | | | | Feng Mao *Ultimate* clip |

Clips: Feng Mao Melee_A/B/C (Fast/Med), Primary_A-D, Dash_Attack, Attack_Stack chain, Ultimate, Shield (guard),
HitReact_Fwd/Bwd/Left/Right, Knock/KnockBack, Stunned_Start/Loop/End, Death_Fwd, VictoryPose_1,
SelectScreen_Loop, Emote_Taunt (intro), Walk_*, Dash_Pose.

### Ser Odric Hale (greatsword): slow, heavy, steadfast

Body: Paragon **Greystone** (to fetch, free). Walk 300 cm/s, range 260 cm. **Steadfast**: from frame 8 of every
heavy, absorbs one light hit (takes the damage, does not flinch). Poise 130, parry window 5.

Moves: Lamp Strokes (L, L: Mid, Mid; 13/4/18, 15/4/20), Vow (H, Overhead, 24/5/30, 170/34, Steadfast), Oathbreaker
(hold H, Overhead, 34/5/34, 260/50), Low Ward (down+H, Low, 22/5/28), Shoulder (forward+L, Mid, knocks back),
Wheel (sidestep+H, Mid tracking, 26/6/30), Riposte, Yield. Clips: Greystone attack/ability set plus
`GreystoneManny`/`KwangManny` greatsword clips from the Paragon-to-Manny pack, retargeted onto Greystone if more are
needed.

### Kesh Sarrow (twin sabres): rushdown, low poise

Body: Paragon **Kallari** (to fetch, free). Walk 400 cm/s, range 180 cm. Poise 85. Long evasion (sidestep 3-15).

Moves: Debt-and-Due string (L x5: Mid, Mid, Low, Mid, Overhead; 8/2/12 → 14/3/20, 40-60 dmg each), Cross Cut (H,
Mid, 17/3/22), Rent Day (hold H, Mid tracking spin), Gutter Slide (down+H, Low slide), Alley Hop (forward+H,
Overhead jump cut), Stair Step (sidestep+L, tracking), Riposte (double), Yield. Clips: Kallari's own set; Paragon
`CountessManny` blade clips retargeted if the string needs more variety.

### Hessa Rime (crescent glaive): reach and spacing

Body: Paragon **Aurora** (on disk), her ice weapon hidden (weapon bone scaled to zero) and the **KCISA Woldo**
crescent glaive attached to the hand socket. Locomotion, attacks and guard from the KCISA **Woldo** set
(Idle, Walk 4-way, Run, Attack1-4, Defense, Damage, Die), extended with KCISA **Hyeobdo** and **Jangchang**
polearm attacks, all retargeted from the KCISA soldier skeleton onto Aurora with an IK Retargeter (script);
Aurora's own hit reacts, knockback, stun and victory pose. Walk 330 cm/s, range 320 cm.

Moves: Thaw Arc (L, L: Mid, Mid wide; 12/4/18), Crescent (H, Overhead, 22/4/28), Floe Sweep (down+H, Low, long
reach, 18/5/26), Ferrier's Push (back+L, Mid, pushes away), Pole Vault (forward+H, Overhead, closes distance),
Moonturn (sidestep+H, Mid tracking spin), Riposte, Yield.

### The Whetwarden (poleaxe): boss

Body: Paragon **Sevarog** (on disk) in its **Chronos** skin, not the default body that tower-defense and giant-fall
use, re-tinted salt-white and verdigris by material instances, with a faded blue cord knotted on the haft (coordinator
note 2026-10-12: make the Warden visibly distinct). Vigour 1400, poise 170, walk
280 cm/s, range 300 cm. Delayed overheads (startup 30, with a visible wind-up), a three-hit **Wheel** spin
(Mid, Mid, Low), a tracking haft thrust, a ground slam (Low, wide), and a **Recall** move per rival style
(a short move that mirrors each challenger's signature, reusing the timing, not their clips). Playable in Versus
after any ladder is finished.

### CPU behaviour (one brain for the CPU and for the AutoPlay bot)

`FBDDuelBrain` (plain C++, deterministic with an `FRandomStream`) reads the opponent's sim state **through a
reaction delay** (a ring buffer of past sim frames) and outputs a virtual pad (move vector + button edges):

- **Spacing**: holds its fighter's ideal range ± jitter, circles a little, steps back out of the opponent's range
  after its own string, dashes in against long-range fighters.
- **Defence**: on a perceived attack startup (after the reaction delay) guards with the correct height with
  probability *read*; tries a **Turn** with probability *parry*, timed with noise σ; dodges telegraphed heavies;
  shoves a turtling opponent.
- **Offence**: punishes whiffs and blocked heavies when in range, uses strings and mix-ups (low / overhead) with
  per-fighter habits (Kesh pressures, Odric waits and armours through, Hessa keeps range, Ishen counters).
- **Tiers** (CPU) and **Skill** (AutoPlay `-Skill`, 0..1, interpolated): reaction 30 → 11 frames, read 0.40 →
  0.85, parry attempt 0.05 → 0.35, timing noise σ 7 → 2 frames, punish rate 0.3 → 0.9, input slip (wrong
  direction, late button) 12 % → 2 %. Tier 1 = Skill 0.15, tier 2 = 0.4, tier 3 = 0.65, tier 4 (Warden) = 0.85.

## 6. Arenas

Each arena: a circular stone or earth ring (the duel ground), a dressed near ring (props, banners, planted blades),
a far set and sky; built by committed `Scripts/build_arena_<name>.py` from pack content. Lighting is Lumen with
Exponential Height Fog; each arena has a fixed time of day. Ambience is a looping bed plus sparse one-shots.

| Arena | Light | Built from (section 9) | Story dressing |
|---|---|---|---|
| **Merrow Saltpans** | dawn, low gold sun, mirror brine | Icelandic biome sampler, basalt columns, nordic beach rocks, Poly Haven coast rocks, wooden racks and salt cones | the Highcourt dam on the horizon, cracked dry channels |
| **Dam-Crown of Highcourt** | late afternoon, warm, long shadows | Medieval Castle Modular Vol 1, castle wall/structure scans | closed sluice gates, carved "THE WATER IS HIGHCOURT'S", Lamp-Guard banners, spillway mist |
| **The Stair** | dusk into night, lanterns | castle modular stairs and arches, KHS walled-town walls, candles/lanterns, ropes, laundry | drowned Calder towers below the tide, Calder's sigil chalked on doors |
| **Rimeshelf** | overcast snow-light | Megascans snow and tundra rocks, snow hill, frozen boats from the siege/pirate props | houses sinking into meltwater, the marker post with a cut blue cord |
| **The Whetstone** (boss) | shafts of daylight through a blowhole, candles | Soul: Cave, ancient temple stones, KCISA weapon meshes as planted blades, candles | the Field of Hilts; the three blades the player won, at the front; a glaive with no cord |

S1/S2/S3 use three different arenas (section 8).

## 7. Camera (gentle; the user gets motion sick)

- Classic versus side view: the camera looks at the midpoint of the two fighters (chest height), from the side,
  perpendicular to the line between them; the side is kept (the perpendicular closest to the previous camera yaw),
  so sidesteps turn the view slowly instead of flipping it.
- Distance grows with separation: `clamp(0.85 * separation + 380, 480, 920)` cm; pitch -7°, height 165 cm; **fixed
  FOV 50°**, never animated.
- Smoothing: position critically damped (0.35 s), yaw rate limited to 30°/s, zoom limited to 250 cm/s. No shake,
  no FOV kicks, no hit zooms; impact is sold by hit-stop, sparks, trails, sound and hit reacts.
- Round intro: a slow 4 s dolly from a wide establishing shot into the duel framing (constant speed, ease in/out),
  the only camera move outside the duel framing. The Yield plays inside the normal framing at 0.6x speed.
- Both fighters always in frame; the arena boundary keeps them inside the ring so the camera never meets walls.

## 8. AutoPlay scenarios (contract v1.4)

In every scenario P1 is the bot (the brain above, acting only through `AP->Inject` on `IA_P1_*`, with
`-Skill` and `-Seed`); P2 is the game's CPU at a fixed tier. Best of 3; the run ends when the match ends
(`FinishRun("win"|"lose")`) or at `-MaxSeconds` (default 600; a match runs about 2.5-4.5 min). Win/lose is metadata only.
Menus, ladder screens and ending stills are skipped; the pre-fight lines play (they are part of the round intro).

| # | Name | Start state | P1 (bot) | P2 (CPU) | Arena |
|---|---|---|---|---|---|
| 1 | **First Rite** | ladder duel 1, edge 1 | Ishen Mor | Ser Odric Hale, tier 1 (tutorial level) | Merrow Saltpans, dawn |
| 2 | **The Stair** | ladder duel 3 (mid-ladder) | Kesh Sarrow | Hessa Rime, tier 3 | The Stair, dusk |
| 3 | **The Whetstone** | ladder duel 4, final | Hessa Rime | The Whetwarden, tier 4 | The Whetstone (Field of Hilts dressed with Kesh's, Ishen's and Odric's blades) |
| 4 (optional, later) | **Versus** | versus match | Ishen (bot, `IA_P1_*`) | Kesh (second injected bot, `IA_P2_*`) | Dam-Crown |

Telemetry (beyond `scenario_start/end`, `score`, `state` at 10 Hz with both fighters' positions, rotations,
vigour, poise, state): `edge_start` {edge}, `edge_end` {edge, winner, how: yielded/spent/time}, `attack`
{player, move, height}, `hit` {attacker, move, damage, poise, counter, riposte}, `blocked` {defender, guard},
`turn` {defender, move} (parry), `dodge` {player, kind, evaded}, `clash`, `shove`, `break` {player}, `yield`
{winner}, `match_end` {winner, edges}. Every telemetry row names the player index (`"player":1|2`). Score = P1
damage dealt + 500 per edge won. `ExtraJson`: edges won/lost, turns, counters, yields, P2 fighter and tier.

Bot comfort rules for watchable video: no dodge spam (cooldown 40 frames), no jitter walking (move intents held
at least 10 frames), guards held for realistic durations, a short "breath" after each exchange.

## 9. Art direction and packs

**Look:** grounded heroic fantasy, painterly-realistic: weathered steel and lacquer, salt, stone and ice under
strong single-direction light, warm/cool contrast per arena. Coherent because every fighter comes from one
art family (Paragon heroes: same detail level and shading) and every arena is scanned PBR under Lumen.

| Need | Pack (asset library) | Status |
|---|---|---|
| Ishen body + anims | Paragon: Feng Mao (Royal Guard skin) | on disk |
| Hessa body | Paragon: Aurora | on disk |
| Warden body + anims | Paragon: Sevarog | on disk |
| Odric body + anims | **Paragon: Greystone** (Fab, free, Pro $0) | **to fetch (asset scout)** |
| Kesh body + anims | **Paragon: Kallari** (Fab, free, Pro $0, UE 4.19-5.3) | **to fetch (asset scout)** |
| Glaive, polearm anims, planted blades | KCISA Korean Traditional Martial Arts (CC BY: Woldo, Hyeobdo, Jangchang sets + 11 weapon meshes) | on disk |
| Extra blade clips | Paragon animations retargeted to Manny (Greystone, Kwang, Countess, Feng Mao sets) | on disk (FBX) |
| Sparks, dust | Realistic Starter VFX Pack Vol 2 (P_Sparks_A-G), Niagara Dust, Paragon hero FX | on disk |
| Weapon trails | own ribbon (C++ procedural mesh from blade sockets) + a trail material built by script | built here |
| Arenas | Icelandic biome sampler, basalt columns, nordic beach rocks, Poly Haven coast; Medieval Castle Modular Vol 1, castle wall/structure scans; KHS Naganeupseong walls; Megascans snow/tundra; Soul: Cave, ancient temple stones; Good Sky; Poly Haven HDRIs (sunrise, overcast, snow) | on disk |
| Sword SFX | Free Realistic Sword SFX (swings, clashes, hits), Kenney impact sounds | on disk |
| Music | Fantasy Music Starter Pack v2 (CC BY, "Music by Cinematsic"), Fantasy Music and Ambience freebie | on disk |
| Ambience | Free City & Nature Sounds (surf, wind), Forest Sounds (CC BY), Essential Ambience SFX | on disk |
| UI | HONETi 4K Full Fantasy GUI (owned), game-icons.net, fonts Cinzel (titles), Alegreya Sans (body) | on disk |

**Fab requests (for the coordinator / asset scout):** Paragon: Greystone and Paragon: Kallari (both free, Pro $0,
Epic, UE 5.3 OK): add to the library and download. No purchase needed for the base roster. Optional, only if the
Greystone/Kallari sets prove too thin after the clip analysis: a dedicated greatsword and dual-sword mocap animset
from Fab (the scout to quote price, licence and UE 5.3 support; purchase only with the user's OK). Fallback without
any fetch: Odric and Kesh on KCISA soldier bodies with the Ssangsudo (two-handed) and Ssanggeom (twin swords) sets.

IP note: the Paragon bodies are Epic's free licensed content (Fab Standard), as tower-defense uses Sevarog. Names,
story, movesets, UI, round calls and arenas are original; the trademark "Paragon" is never used in the game.

## 10. UI style: "whetted steel and oiled paper"

HONETi fantasy frames re-tinted to blued steel and parchment; Cinzel for titles and numbers, Alegreya Sans for
small text; no default font anywhere.

- **Vigour bars**: two long blade shapes meeting at a centre medallion (the timer, Cinzel numerals in a stone
  disc); vigour drains from the tip toward the hilt, recent damage shows as a dull grey section that catches up.
- **Poise**: a thin whetstone-grey band under each blade that fills toward break; at 80 % it shows hairline
  cracks; at break it shatters (UI shards, no screen effect).
- **Edges won**: small hilt icons under the medallion.
- **Round calls** (original wording, struck bell + styled card, no announcer voice): "FIRST EDGE" / "SECOND EDGE" /
  "FINAL EDGE", then "DRAW" (blades drawn); end of edge "YIELDED", "SPENT" or "TIME"; match end "THE RULING
  STANDS" with the winner's name.
- **Stamps** near the fighter: COUNTER, TURNED, BROKEN, RIPOSTE, small and quick (0.6 s).
- **Subtitle band**: dark oiled-paper strip low on screen, speaker portrait (rendered from the fighter mesh into a
  texture by script), name in small caps.
- **Fighter select**: four (five) portrait cards, blade silhouette, Seat sigil, three stat ticks (reach, speed,
  poise); two cursors in P1/P2 colours (salt white / ember amber).

## 11. Audio

Sword SFX pack for swings (per weapon weight), blocks and clashes; layered with synthesized transients (steel ring
per weapon pitch, low thump on heavies, a glassy "turn" chime on parry, crack on break). Bell strike for edges
(synthesized). Music: one calm menu track, a duel loop per arena family, a boss track for the Whetstone (CC BY
credit). Ambience beds per arena. No voices of any kind.

## 12. Tech plan (module `BladeDuel`)

| Class | Role |
|---|---|
| `UBDGameInstance` | modes, ladder state, save, AutoPlay `StartScenario` (opens the scenario's arena map with the match setup) |
| `ABDDuelGameMode` | match flow: intro, edges, timer, results, ladder advance; calls `ScenarioStarted`/`FinishRun` |
| `UBDDuelSim` (world subsystem) | fixed 60 Hz step: input sampling, move state machines, hit sweeps, guard/parry/dodge, poise, hit-stop, events |
| `ABDFighter` (character) | visuals only: skeletal mesh, weapon meshes, sockets, hurt capsules, trail, plays montages for sim states |
| `UBDFighterAnimInstance` | native anim instance (no AnimGraph, as stealth and metro-runner do): locomotion blend by sim velocity, guard poses, montage slot for moves and reacts |
| `UBDFighterData` (data asset) | per fighter: mesh, skin, weapon, clips, `DT_Moves_*`, stats, portrait, dialogue keys |
| `FBDDuelBrain` | CPU and bot brain (section 5) |
| `UBDBotComponent` | AutoPlay P1: runs the brain, injects `IA_P1_*` through `AP->Inject` (TG_PrePhysics) |
| `ABDDuelCamera` | the camera rules of section 7 |
| `UBDBladeTrailComponent` | procedural-mesh ribbon from blade sockets |
| `UBDHud` widgets | built in C++ (Slate/UMG from code) with kit textures |

**Replay-friendly work:** every editor change through committed scripts in `Scripts/` (imports, retargeting,
montage creation, DataTable import, materials, arena builds, portraits), run headless through ue-heavy.ps1; each
script run gets a workflow row with the script's sha256. Pack content copied unchanged under `Content/<Pack>/`.

## 13. Acceptance checklist

- [ ] 4 fighters + Warden with distinct movesets, guard, parry, dodge, poise, counter, Yield finisher
- [ ] best of 3 with timer; Rite ladder with dialogue and endings; Versus 2P on one PC (keyboard split and two pads); Practice
- [ ] 5 arenas from pack content, no primitives or flat colours
- [ ] hit-stop, sparks on clash and hits, weapon trails, directional hit reacts; no camera shake, fixed FOV
- [ ] styled HUD/menus (no default font), subtitles for every line, settings (volume, resolution), pause
- [ ] AutoPlay v1.4: S1-S3 pass validate-run, bot plays like a competent human; framing screenshots reviewed
- [ ] packaged Win64 Shipping, ThirdPartyNotices + assets.manifest.json complete, scrub verify = 0

## 14. Status

- 2026-10-12: story bible and design drafted; repo created with new-game.ps1. **Approved by the coordinator**
  (942d5fe). Build/GPU slots on hold until the dataset replays finish: offline work only until released.
- Offline C++ written (not compiled yet): duel sim (`FBDDuelSim`), brain (`FBDDuelBrain`), fighter actor + native
  anim instance, blade trails, camera, game instance (Rite ladders, scenario table), duel and menu game modes,
  controller with per-player actions, AutoPlay bot, canvas HUD and menus, settings.
- Data: frame-data CSVs for Ishen, Hessa, the Warden (Data/Moves_*.csv), all subtitle lines (Data/Lines.csv),
  arena cards, fighter spec (Data/Fighters.json). Odric and Kesh wait for their packs.
- Editor scripts ready to run once released: make_input.py, make_data.py, p01_probe_fighters.py,
  p02_probe_maps.py, make_presentation.py, make_fighters.py, retarget_hessa.py (full editor), make_portraits.py
  (full editor, GPU); run tooling (Scripts/run_ue.sh, run_ue_gui.sh through ue-heavy.ps1, stage_packs.sh).
- Done offline: 12 synthesized sounds (Scripts/gen_audio.py), 23 HUD/menu kit textures from the HONETi GUI sources
  (Scripts/gen_ui.py, gen_ui_v2.py; mock HUD reviewed), Root guard as a procedural crouch in the anim proxy,
  headless brain-vs-brain automation test, startup map / cook config.
- Release plan (in order): compile; stage Feng Mao, Aurora, Sevarog, KCISA, sword SFX, music, sparks, Soul Cave,
  castle packs; make_input, make_data, probes; retarget Hessa; make_presentation, make_fighters, portraits; arena
  maps from the Soul Cave and castle demo maps (+ Saltpans, Stair built from scans); headless sim test; S1 by hand,
  validate-run, framing screenshots, then ask for a recording.
- Asset requests: Paragon Greystone + Paragon Kallari (free) asked of the asset scout 2026-10-12.
- Disk: C: has about 74 GB free (97 % used); packs are staged only when needed and pruned to the used assets
  before commit.

# EMBERWAKE: story bible and game design

Third-person grapple action, Unreal Engine 5.3, C++ module `GiantFall`. Slug `giant-fall`.
Status: **draft v1, 2026-10-12, waiting for the coordinator's OK** (see section 13).

## 1. The game in one paragraph

Every autumn, when the river mist climbs out of the gorge, the stone giants walk down from the high passes toward
Lanthorn, a walled town of timber halls and lantern terraces built across the throat of the Ember Vale. The town
calls them **Cairns**, because at rest they look like heaps of mossed rock, and it answers them with the **Kite
Ward**: runners who fly between the masts, halls and pines on two forearm reels of ember-wire, a bellows of warm
"breath" on their backs and a single long cleaver. A Cairn falls only one way: reach the ember seam glowing at the
back of its neck and cut it at speed. You are Kite Nine, the newest runner, and this is the autumn the oldest
Cairn of all comes down the pass.

## 2. Story bible

### World

- **The Ember Vale.** A steep river valley closed at its upper end by snow passes and at its lower end by the
  gorge. Spruce forests taller than any building, mossed cliffs, terraced fields. Autumn: red maples, mist,
  long low sun.
- **Lanthorn.** The town fills the narrow middle of the vale in tiers: the **Lower Ward** of thatched houses,
  mills and drying racks; the **Ringwall**, a nine-metre stone rampart with gate pavilions; the **Kiln Terraces**
  where the furnaces and resupply towers stand; and at the top, above the town, the **Hearth Temple** with the
  great **Hearth Bell**, whose amber glow can be seen from the whole vale. Tall **kite masts** (timber lattice
  towers with iron anchor rings) stand all over the town: they exist so the runners have something to hook. Every
  street has lanterns, and every lantern burns with the same amber light.
- **Ember.** The amber light is *ember*, a warm, slow-burning stone the Kiln Guild "mines". It heats the town,
  lights the lanterns, and, crushed and bellowed, gives the Kite Ward the breath that drives their reels. Nobody
  in the town asks where the Guild finds it. (Truth, section "Payoff": every piece of ember is a Cairn's heart.)
- **The Cairns.** Giants of stone hide over something warm, many times a person's height. They walk slowly, with
  great patience, always uphill, always toward the town's centre. They break whatever stands in their way, and
  they strike at anything that flies at them. In the back of each neck a seam of amber light pulses: the only
  place a blade can stop one. When a Cairn falls, it turns fully to stone where it lies and the ember in its neck
  keeps glowing; the Guild carts it away by morning.
- **The Mistwalk.** The yearly descent, nine to twelve days each autumn. The town shutters, hangs extra lanterns
  ("so the runners can see"), and rings the Hearth Bell at each sighting.

### People and factions

| Who | What they want | How the player meets them |
|---|---|---|
| **Kite Nine** (the player) | to earn a name; the Ward gives runners numbers until their first autumn is over | the hero; rust-red hooded mantle, forearm reels, brass bellows pack, long cleaver, spare edges in a back quiver |
| **The Kite Ward** | keep the Cairns off the Bell; proud, small, losing runners every year | Captain **Odile Marr** (signals and short subtitled calls from the masts), other runners swinging between masts in the background, the training yard |
| **The Kiln Guild** | keep the furnaces lit; secretive about where ember comes from | the resupply towers, ember carts, sealed crates with the Guild's furnace mark, kiln-hands who wave the runners in |
| **The Bell-keepers** | warn the town; old, devout, they keep the temple and the founders' records | the bell towers, the temple murals in S3, the bell rings at each sighting |
| **The townsfolk** | survive the Mistwalk | stranded on roofs and towers in S2 (rescue), lantern strings, shuttered houses |
| **The Last Pilgrim** | to reach the Hearth Bell | the S3 boss: the oldest and tallest Cairn, hooded in a mantle of fused stone |

Emblem of the Kite Ward: a red diamond kite with two trailing tails tied in a knot. Never wings.

### Gear (the player's)

- **Kite reels:** one on each forearm. Each fires a barbed hook on an ember-wire line (about 45 m), which bites
  into wood, stone and Cairn hide. The lines leave the wrists with a faint amber glow.
- **Bellows pack:** a brass canister of pressurised warm air, driven by crushed ember. It reels the lines in hard
  and gives short bursts of thrust; it vents in warm orange shimmer and sparks (never white puffs).
- **Hookcleaver:** one long single-edged cleaver. Its cutting edge is a replaceable tempered strip; strips dull
  with every cut and snap on stone, and four spares ride in a quiver on the back.
- Resupply at the Guild's **kiln towers**: refill breath, new edges, a knot of bandage cord (health).

### Tone

Melancholy, heroic, autumnal. Big quiet skies, the creak of rope and the thunder of footsteps far away. The
giants are frightening by size and patience, never by gore: there is no blood anywhere; struck Cairns spill
sparks and dust, fallen ones become stone. Courage, small people against huge things, and a slow, uneasy
question about what keeps the lanterns lit.

### How the story is told in play (never a wall of text)

- **One short line per area**, as a brush-stroke banner at the bottom of the screen (under 15 words), e.g.
  S1: "Old Nine-Autumns has walked this ring longer than you've been alive." S2: "Every lantern lit. Let them see
  us coming." S3: "It doesn't look at us. It looks at the Bell."
- **Captain Marr's calls** as subtitles with a synthesized signal-whistle (no voices): "Seam's on the left
  shoulder. Go high." "Kiln Two is open." Two to five words each, only for gameplay.
- **Environmental storytelling:** every resupply tower keeps its ember in glass jars that pulse slowly like a
  heartbeat. Ember carts and Guild crates stand near the training yard's chained giant. In S2 a Lantern Warden
  stops in a lantern street, kneels, and reaches very gently for a lantern instead of attacking (a scripted beat
  that the player can interrupt). Fallen Cairns keep a glowing seam; kiln-hands arrive with a cart.
- **Optional details:** *kite cords*, knotted message cords tied to masts (3 per scenario), each a single line
  on pickup: "Grandfather says they used to walk past us. Not toward us." Collected cords show in the pause
  ledger. The S3 temple murals (founders hauling a glowing stone down from the pass, a giant kneeling without one)
  are visible from the air while fighting the boss.
- **Late payoff (S3):** when the Last Pilgrim's stone mantle finally cracks open, its neck seam is **empty and
  dark**: its heart was taken long ago. It ignores the player and reaches for the Hearth Bell, which pulses with
  the same rhythm as every jar on every resupply tower the player has used. The final strike fells it with its
  hand on the temple steps; the Bell's light gutters, and every lantern in the town below dims for a moment.
  Closing banner: "It only came for its heart." Ending card: "Next autumn, we carry them home." Everything
  earlier recolours: the breath in your pack, the lanterns you were told to light, the giants that always walked
  uphill toward the Bell.

## 3. Core loop

Spot a Cairn (bell, compass ribbon, footstep dust) → fly in by grapple through masts, roofs and pines → circle to
its back, staying out of its telegraphed reach → soft-lock the seam → build speed on a swing or a boost → cut at
the seam (speed = damage) → peel away before it turns → watch breath and edges, resupply at a kiln tower → next
Cairn, rescue stranded people on the way (S2).

### Controls (all Enhanced Input actions, so the bot can do everything a player does)

| Action | Keys (KB/M) | Gamepad | What it does |
|---|---|---|---|
| `IA_Move` | WASD | left stick | run on the ground; air steering while flying |
| `IA_Look` | mouse | right stick | orbit the camera (aim = screen centre with a soft assist cone) |
| `IA_HookLeft` / `IA_HookRight` | LMB / RMB (hold) | LT / RT (hold) | fire the left/right line at the aimed anchor; hold to stay attached, release to let go |
| `IA_Boost` | Space (hold) | A (hold) | on the ground: jump; attached: hard reel-in; free: thrust along the view; drains breath |
| `IA_Reel` | Left Shift (hold) | LB (hold) | gentle reel-in of attached lines (little breath) |
| `IA_Strike` | E | X | cleaver cut; damage from speed when inside the seam's reach |
| `IA_Lock` | Q (toggle) | R3 | soft-lock the nearest seam in view (or a tether seam in S3) |
| `IA_Interact` | F (hold) | Y (hold) | resupply at a kiln tower; rescue a stranded person; pick up a kite cord |
| `IA_SwapEdge` | R | B | snap in a fresh edge |
| `IA_Pause` | Esc | Start | pause menu |

### Traversal (C++, `UGFKiteRigComponent`)

- Movement runs in `MOVE_Falling` on the standard Character Movement Component with forces added each tick, so
  collisions and landing stay engine-standard.
- **Aim:** a camera-centre trace plus an assist cone (8°) picks the best anchor within 45 m: any surface on the
  `Anchor` collision channel (masts, walls, roofs, trees, cliffs, Cairn bodies) scored by angle and distance;
  the HUD shows the aimed point as a small kite-knot marker that turns red when out of range.
- **Lines:** the hook flies at 140 m/s (a `UCableComponent` line plus hook mesh). On bite the line length is the
  current distance. While attached, a rope constraint removes the outward radial velocity beyond the length
  (pendulum swing) and adds a small tangential assist toward the move input. Two lines = the constraint is
  applied to both (a swing between two anchors, or a strong pull toward their midpoint while reeling).
- **Reel / Boost:** reel shortens the lines at 6 m/s (2 breath/s); boost reels at 20 m/s while attached or thrusts
  1,800 cm/s² along the view when free (22 breath/s). Each hook fired costs 1 breath. Breath 100; regenerates
  3/s only while standing on the ground, so resupply matters.
- **Speed cap 32 m/s** (115 km/h) with soft drag above 24 m/s: fast but readable. Speed tier shown on the HUD.
- **Hooks into Cairns:** a line bitten into a Cairn moves with the bone it hit (socket attachment), so the
  player can swing round a walking giant to reach its back. Cairns shrug off lines after 4 s (telegraphed by a
  shiver and dust).

### Combat (C++, `UGFBladeComponent`, `UGFWeakPointComponent`)

- **Seam strike:** a strike counts when the cleaver's sweep (a 3.5 m capsule in front of the hero) overlaps the
  seam sphere. Damage from speed at the moment of contact: under 10 m/s = **glance** 10; 10–18 = **cut** 35;
  18–26 = **deep** 70; over 26 = **sever** 110. Stoneback HP 100, Lantern Warden 140, Last Pilgrim's nape 3 strikes
  (see S3). A sever on a full-health Stoneback fells it.
- **Edges:** each edge has 3 cuts; a dull edge (last cut) does half damage; a strike on armour or stone hide (outside
  the seam) breaks the edge outright. The HUD shows 5 edge strips. Swap with `IA_SwapEdge` (0.6 s, can be done in
  the air). Resupply restores all 5.
- **Stagger:** a cut that does not fell a Cairn makes it stagger and reach for its neck (2.5 s), which also slows
  its next attack: a second pass is the human answer.
- **Health = knots:** 3 knots. Swat or toss hit: −1 knot and a knockback (camera follows smoothly, no shake).
  Grab: the hand closes over the hero (2.5 s); strike the fingers or boost twice to slip free, else thrown for
  −2. Stomp shockwave: −1 if grounded within its ring. 0 knots = **down**. Resupply restores 1 knot.
- **Downs:** S1: the instructor's net catches you, restart at the yard gate (telemetry `restart`). S2/S3: 3 flares;
  a down respawns you at the last kiln tower and spends a flare; no flares left = lose.

## 4. The Cairns (giants)

Premium Paragon skeletal meshes from the library, scaled up, re-materialed toward mossed stone with an ember
underglow, and slowed so they read as enormous. No primitive shapes anywhere.

| Cairn | Mesh (pack) | Height | Speed | HP | Attacks | Notes |
|---|---|---|---|---|---|---|
| **Stoneback** | Paragon Rampage (base skin), ×5.5 | ~14 m | 1.6 m/s | 100 | Swat, Grab, Stomp (Ability_GroundSmash), Rock Toss (RipNToss) | the common Cairn; seam between the shoulder rocks |
| **Cinderback** | Paragon Rampage *Elemental* skin, ×6 | ~16 m | 1.4 m/s | 120 | Swat, Stomp, ember breath cloud (area denial, telegraphed) | glowing cracks, the S2 elite |
| **Lantern Warden** | Paragon Sevarog (base skin), ×7 | ~21 m | 1.2 m/s | 140 | Hammer sweep (Swing1/2), Grab, Stomp | tall and hooded; kneels at lanterns (story beat) |
| **The Last Pilgrim** | Paragon Sevarog *Chronos* skin, re-materialed as fused stone, ×11 | ~33 m | 0.8 m/s | 3 nape strikes | Staff sweep, Grab, Stomp, Inhale (pulls fliers in) | S3 boss, stone mantle over the nape |

- **Reading as huge:** animation play rate 0.5–0.6 with root motion scaled to the stride; every footfall spawns a
  dust ring (Niagara Dust) and loose debris on nearby roofs; birds flush from roofs ahead of them; low synthesized
  thuds with long distance falloff; aerial perspective (height fog) on distant giants; the hero is ~1.8 m.
  Never camera shake.
- **Telegraphs (fair, readable):** every attack has a wind-up of 1.0–1.6 s (×1.5 in S1): the attacking limb's
  ember veins brighten, a low horn note sounds, stomps paint a dust ring decal on the ground where the shockwave
  will land, grabs open the hand toward the hero. Recovery after each attack is 1.5–2.5 s (the opening).
- **AI** (C++ `AGFCairnAI`, a state machine, no Behavior Tree assets): `Walk` (follow its path spline toward the
  scenario goal: the ring in S1, the Bell Gate in S2, the Hearth Bell in S3) → `Notice` (head turns to a hero
  within 40 m) → `Telegraph` → `Attack` → `Recover`; `Stagger` on a non-lethal cut; `Shrug` when lines are hooked
  into it; `Fall` on death (Death anim at 0.5 rate, a petrify material ramp over 2 s, dust plume, sparks rise from
  the seam, the stone body stays). Attack choice from the hero's position relative to the giant (front + hand
  height: swat/grab; low and close: stomp; far front: toss/inhale; on its back: shrug). One attack at a time per
  giant; a world `UGFThreatSubsystem` allows at most two giants to wind up against the hero at once.
- **Animation:** Paragon anim sets on their own skeletons (no retarget needed for the Cairns); creature roars
  only from non-speech effort sounds, otherwise synthesized; the packs' dialogue waves are never used.

## 5. Scenarios (AutoPlay contract v1.4)

All randomness from `FRandomStream(Seed)`: giant spawn order and path variants, which person is stranded where,
attack choice ties, bot decisions. One map per scenario.

| # | Name | Map | Start state | Win | Lose |
|---|---|---|---|---|---|
| 1 | **First Thaw** (training yard) | `L_TrainingYard` | Misty morning in the Kite Ward's gorge yard below the Ringwall: kite masts, rope bridges, a kiln tower, Guild carts. Full breath, 5 edges, 3 knots. **Old Nine-Autumns**, a chained Stoneback, walks a slow ring (60 % speed, swat only, long telegraphs) | Three beats: hook through the 3 lit practice rings on the masts, resupply at the kiln tower once, then fell Old Nine-Autumns | none but time: downs restart at the yard gate; 8 min timeout |
| 2 | **Lantern Night** (town defence) | `L_LanternWard` | Dusk turning to night in the Lower Ward, lanterns lit for the festival. The Ringwall's north sluice is broken; **4 Cairns** (2 Stonebacks, 1 Cinderback, 1 Lantern Warden) arrive in two pairs, walking toward the Bell Gate. **4 people stranded** (a roof, a broken bell tower, a mill wheel, a runner hanging from a snapped line). 2 kiln towers, 3 flares | All 4 Cairns felled (rescues add score and the result tier) | the Bell Gate breached (gate integrity 0; Cairns at the gate hammer it), or 3 flares spent; 12 min timeout |
| 3 | **The Last Pilgrim** (boss) | `L_PilgrimPass` | Dawn, first snow on the switchback road from the pass down to the Hearth Temple; spruce forest, cliffs, temple terraces, bell towers. The Last Pilgrim (33 m) climbs the road; 1 escort Stoneback in the first minute. 2 kiln towers, 3 flares | Fell the Last Pilgrim: cut its 3 **tether seams** (back of each knee, small of the back) to make it kneel and crack its mantle, then strike the open nape within 20 s; three nape strikes (the mantle re-forms after each, the tethers re-light) | it reaches the Hearth Bell (road progress 100 %), or 3 flares spent; 15 min timeout |

Score: Stoneback 500, Cinderback 650, Warden 800, Pilgrim nape strike 1,000 each; strike quality bonus (deep +100,
sever +250); rescue 400; kite cord 100; S1 time bonus; S2 gate integrity bonus. `ExtraJson`: giants_felled,
strikes {glance,cut,deep,sever}, edges_broken, resupplies, rescues, flares_used, downs, max_speed_ms,
cords_found, gate_integrity (S2), road_progress (S3).

Telemetry (beyond `score`, `state`, `restart`): `hook_fired` {side, target_kind, distance}, `hook_bite` {side,
target, kind}, `hook_release` {side, held_s}, `boost` {on, breath}, `strike` {giant, part, speed_ms, tier,
damage, edge}, `edge_broken` {edges_left}, `edge_swap`, `giant_state` {giant, from, to}, `giant_attack` {giant,
attack, phase: telegraph/strike/recover}, `hero_hit` {giant, attack, knots}, `grabbed` / `grab_escape`,
`giant_felled` {giant, type, by_tier}, `resupply` {station}, `rescue` {person}, `person_lost` {person}, `gate_damage`
{integrity} (S2), `tether_cut` {index}, `mantle_open` / `mantle_closed`, `road_progress` {pct} (S3), `cord_found`
{id}, `ring_passed` {index} (S1). `state` at 10 Hz adds speed_ms, breath, edges, edge_wear, knots, flares, lock
target, lines attached, giants_alive, gate_integrity / road_progress.

### AutoPlay bot (watchable, comfortable, human-like)

`UGFBotComponent` on the PlayerController (TG_PrePhysics), acting only through `AP->Inject`.

- **Plan:** pick a target Cairn (S2: the one closest to the gate, unless a stranded person is in danger and no
  giant is within 25 s of the gate; then rescue first). Compute an **approach point** behind and above its nape
  (8 m back, 3 m up, updated as it walks). If breath < 30 or edges ≤ 1 or knots = 1, go to the nearest kiln tower
  first.
- **Grapple navigation:** the level scripts place `AGFAnchorHint` points (mast rings, roof ridges, tree crowns,
  cliff lips) that form a graph; the bot picks the next anchor ahead of and above its route (within 40 m, < 55°
  off the desired direction), turns the camera onto it with smooth `IA_Look` deltas, fires the line on the side
  of the turn, holds through the swing, gives a short boost in the low part of the arc, releases just past the
  bottom-forward point, and chains the next anchor with the other hand. On the ground it runs to the nearest
  launch point and jumps first.
- **Attack run:** when within 35 m of the approach point it toggles `IA_Lock`, swings or boosts down along the
  back toward the seam, presses `IA_Strike` when the seam is inside reach and its speed is in its chosen tier
  (skill 1 waits for deep or better), then hooks away to an anchor on the far side of the giant's facing.
- **Evasion:** when a Cairn telegraphs an attack whose zone holds the bot, it releases and boosts sideways/up
  after a reaction delay; when grabbed it strikes the fingers. It never hangs in front of a giant's face.
- **Camera:** `IA_Look` from a critically damped turn with caps (skill 1: 120°/s yaw, 60°/s pitch; skill 0: 70°/s,
  35°/s), pitch kept within −35°..+25° except when aiming at high anchors. No snaps, no spinning.
- **Skill (0..1)** interpolates reaction delay (0.25 → 0.8 s), aim noise on anchors (1° → 6°), strike tier patience
  (sever/deep → any cut), approach discipline (from behind vs. whatever is nearest), resupply thresholds and how
  often it misses a release. Skill 1 should usually win S1 and S2 and sometimes S3.

## 6. Camera (comfort first; the user gets motion sick)

- Spring arm 520 cm at rest, easing to 700 cm above 15 m/s (lerp over ~1.5 s), socket offset up 90 cm and right
  45 cm: the hero sits in the lower third and small in frame, never at hip height, never filling the screen.
- Position lag 7, rotation lag 10, **fixed FOV 75** (no FOV change ever), **no roll** (camera roll locked at 0
  even during swings), no camera shake anywhere (impacts shown with dust, sound and HUD ripples only), motion
  blur off.
- Spring-arm collision probe 14 cm with a short "pull-in" lag, so wall contacts don't snap; near a wall the arm
  shortens but never below 260 cm (the hero fades to 40 % opacity if the camera gets closer).
- **Soft lock:** `IA_Lock` frames the line between hero and seam: the camera's yaw/pitch ease toward a framing
  that keeps both on screen, at most 50°/s, with a 6° dead zone; input still orbits freely inside a ±30° leash.
  The seam marker is a soft amber diamond. Lock releases if the seam leaves view for 2 s.
- **Speed feel without kicks:** wind streak particles (Niagara, camera-attached, alpha and count scale with speed
  above 10 m/s), the mantle and line flutter, a rising wind tone; a faint vignette of streaks at the screen edges
  above 24 m/s. Nothing moves the camera's angle or FOV.
- Settings: camera distance, sensitivity, invert Y, wind streak intensity (0–100 %), lock assist strength.

## 7. Art direction: "Autumn Vale"

Realistic-stylised, warm. Scanned stone and timber, East-Asian-flavoured timber halls on stone bases, thatched
houses, red maples and huge spruces, mist, a long golden sun; the amber ember glow as the one saturated accent.
The Cairns are mossed grey stone with ember underglow. The hero's mantle is rust red, the Ward's kites red,
Guild crates black iron.

| Element | Pack (library path under `asset-library\`) | Licence |
|---|---|---|
| Hero (Kite Nine) | `fab-ue\rogue-character-model` (hooded rogue, UE5 Manny skeleton), mantle recoloured rust red, kite-knot emblem decal | Fab Standard |
| Hero animation | `fab\paragon-animations-retargeted-to-manny` (air poses, falls, landings, spin slashes), `fab-ue\lyra-starter-game` locomotion, `fab-ue\free-animation-library` | Fab Standard |
| Cairns | `fab-ue\paragon-rampage` (base, Elemental), `fab-ue\paragon-sevarog` (base, Chronos) with their own anim sets | Fab Standard |
| Town (Lower Ward, Ringwall) | `fab-ue\khs-naganeupseong-walled-town` (walled town: walls, gates, thatched houses, mills, props), `fab-ue\khs-korean-gwanghwamun-gate` (the Bell Gate pavilion) | Fab Standard (KHS) |
| Tall halls, towers, temple | `fab-ue\china-modular-temple`, `fab-ue\khs-korean-temples`, `fab-ue\khs-korean-stone-pagoda`, `fab-ue\dongrae-hyanggyo` | Fab Standard / CC BY (KHS) |
| Kite masts, kiln towers | kitbashed from the town and temple timber pieces + `fab-ue\medieval-castle-modular-vol-1` ironwork and `fab-ue\survival-construction-pack` scaffolding | Fab Standard |
| Forest, cliffs | `fab-ue\temperate-vegetation-spruce-forest`, `...-foliage-collection`, `...-optimized-grass-library`, `fab\nordic-forest-cliff-large-xibsff1`, `fab\massive-tundra-rock-formation-wcrmbiar`, `fab\mossy-rocks-tjmudcfda` | Fab Standard |
| Ground, stone | `fab\rocky-forest-path-vbhsfesga`, `fab\mossy-forest-floor-vfylbge`, `fab\fort-stone-wall-tfuebj3n`, Poly Haven `siege-textures` / `liaozhai-textures` | Fab Standard / CC0 |
| Sky, light | `fab-ue\good-sky`, Poly Haven `day-hdri` (belfast_sunset_puresky for dusk) | Fab Standard / CC0 |
| VFX | `fab-ue\niagara-dust` (footfalls), `fab-ue\realistic-starter-vfx-pack-vol-2` (sparks, debris), `fab-ue\item-destruction-fx`, Paragon Rampage FX (debris, shockwave), own Niagara wind streaks | Fab Standard |
| UI | `fab-ue\honeti-4k-full-fantasy-gui` frames recoloured to lacquer red / ink / brass, `gameicons\` | Fab Standard / CC BY 3.0 |
| Fonts | `fonts\SongMyung` (titles), `fonts\GowunBatang` (body), `fonts\BarlowCondensed` (numbers) | OFL |
| Music, SFX | `fab-ue\fantasy-music-starter-pack-v2` (CC BY, "Music by Cinematsic"), `fab\wafu-vol35-mountain-temple` (calm), `fab\free-realistic-sword-sound-effects-pack` (cleaver), `kenney\impact-sounds`, `fab-ue\essential-footsteps-sfx`; synthesized wind, reel whirr, bellows, bell, giant thuds | Fab Standard / CC BY / CC0 |

**IP guard:** no exposed-muscle giants, no human-faced giants, no "titan" anywhere, no wings emblem, no green
cloaks, no hip-mounted gas tanks or twin box-sheathed swords (our gear is forearm reels + back bellows + one
cleaver), no wall names from any existing work, no look-alike characters. Also avoid white skull masks and holes
through chests on the Cairns (another franchise's look); the Pilgrim's head stays hooded stone.

### Asset requests (for the coordinator and the asset scout; purchases need the user's OK)

1. **Townsfolk** in period clothing on the UE4/UE5 skeleton (4–6 people for the S2 rescues and the kiln-hands),
   matching the East-Asian timber town; today only modern or pirate/adventurer characters exist in the library.
2. **Rope/cable material** and a barbed hook mesh (CC0 is fine), or I build them from Poly Haven rope textures.
3. Optional: a timber watchtower/scaffold kit if the kitbashed kite masts don't read well at 25–30 m.
Prices will be listed by the scout; nothing is bought without the user's OK.

## 8. UI style: "Ward ledger"

Lacquer-red and ink panels with brass corners (HONETi frames recoloured), brush-stroke dividers, kite-knot motif.

- **HUD:** breath as a curved brass bellows gauge at lower left; 5 edge strips beside it (dull edges greyed,
  broken ones cracked); 3 knot icons; a compass ribbon at the top (Cairns red, kiln towers brass, stranded people
  as lanterns, the Bell Gate / Hearth Bell); aim marker (kite knot, red out of range); when locked, the seam
  diamond and a **strike-tier pip** (glance/cut/deep/sever) that lights from the current speed; S2 gate integrity
  bar, S3 road progress as a winding path icon. Story lines as brush banners, Marr's calls as small subtitles with
  a whistle glyph.
- **Screens:** main menu over a still view of Lanthorn at dusk (Play, Scenarios, Settings, Credits, Quit),
  scenario select as three painted panels, settings (volume x3, resolution, window mode, sensitivity, invert Y,
  camera distance, wind streaks, lock assist), pause (resume, restart, settings, ledger of cords, quit), result
  screen (giants felled, strikes by tier, rescues, time, rank seal). Save: unlocked scenarios, best ranks, cords,
  settings. No default font anywhere.

## 9. Audio

Synthesized and pack sounds, no recorded or TTS voices. Giant footfalls: synthesized sub-bass thump + debris
rattle, distance-attenuated to 300 m; roar: Paragon creature efforts (non-speech) or synthesized growl; reel:
synthesized whirr pitched by line speed; hook bite: Kenney impacts on wood/stone; bellows: filtered noise burst;
wind: noise bed whose volume and cutoff follow speed; cleaver: sword WAVs, with a bright ring on sever; Hearth
Bell: synthesized bell (additive partials). Music: calm temple music in S1, a building theme in S2, a slow heavy
march for the Pilgrim.

## 10. Tech plan

- C++ module `GiantFall` on the factory template; gameplay in C++, tuning in data assets / DataTables made by
  editor Python scripts in `Scripts/`; levels built by `Scripts/build_level_*.py` (`-run=pythonscript`), never
  hand-edited `.uasset`; packs copied into `Content/Fab/<Pack>/`.
- Classes: `AGFHero` (character, camera rig), `UGFKiteRigComponent` (lines, rope constraint, reel, boost, breath),
  `AGFKiteLine` (cable + hook visual), `UGFBladeComponent` (edges, strike, tiers), `UGFCameraDirector` (arm
  length, soft lock, collision fade), `UGFWindStreaks` (Niagara by speed), `AGFCairn` + `UGFCairnData`
  (data asset: mesh, anim set, scale, speed, HP, attacks) + `AGFCairnAI` + `UGFWeakPointComponent` (seams, tethers,
  mantle) + `UGFThreatSubsystem`, `AGFAnchorHint` + `UGFAnchorGraph`, `AGFKilnTower`, `AGFStrandedPerson`,
  `AGFBellGate`, `AGFPilgrimRoad` (spline + progress), `AGFPracticeRing`, `AGFKiteCord`, `AGFAmbientRunner`
  (background runners on splines), `AGFGameMode` (scenario flow, flares, win/lose, score, telemetry),
  `UGFGameInstance` (settings, save, AutoPlay hook), `UGFSaveGame`, `AGFPlayerController`, UMG widgets in C++
  (`UGFHudWidget`, menus), `UGFBotComponent`.
- DataTables: `DT_Cairns`, `DT_Attacks` (wind-up, active, recovery, damage, zone), `DT_Scenarios`, `DT_StoryLines`.
- Engine: `CableComponent` plugin, Niagara, Enhanced Input. Config: `r.RDG.AsyncCompute=0`,
  `bAllowHighDPIInGameMode=True`, motion blur off, a custom `Anchor` trace channel.
- Performance: Nanite on scanned set pieces, HLOD off (small maps), giants at most 4 at once with animation
  budget (URO) for distant ones, Lumen on with conservative settings for the 60 fps recording target.

## 11. Acceptance checklist

- [ ] Grapple traversal feels good: swing, chain, reel, boost; landing and take-off on the ground
- [ ] Seam strike with speed tiers, edges dull and break, resupply works; knots, downs, flares
- [ ] Cairns read as huge (scale, slow heavy animation, dust, sound) and look premium; all 4 types animated
- [ ] Every Cairn attack is telegraphed and dodgeable; grab escape works
- [ ] S1–S3 playable start to finish by hand and by the bot; win and lose both reachable; S2 rescues; S3 tethers
      + mantle + payoff
- [ ] Camera: fixed FOV, no roll, no shake, hero small in the lower third; soft lock gentle; wind streaks show speed
- [ ] Story in play: area banners, Marr's calls, ember jars, the kneeling Warden, kite cords, S3 payoff
- [ ] Styled UI everywhere, no default font; main menu, scenario select, settings, pause, result, credits, save
- [ ] AutoPlay v1.4: validate-run PASS for S1–S3; bot grapples smoothly within its turn caps
- [ ] Framing screenshots checked (open sky, between houses, close to a giant, against walls, grounded)
- [ ] Packaged Win64 Shipping build; scrub-import-paths `--verify` = 0; assets.manifest.json + ThirdPartyNotices
- [ ] No banned names, no IP look-alikes (section 7 guard)

## 12. Build order

1. (Hold) Story + design (this doc), repo, C++ systems written offline: rig, blade, camera, Cairn AI, scenario
   flow, HUD, bot; editor scripts for imports, data assets and the three level layouts.
2. (Slots released) Compile, import packs (hero, Cairns, town, forest), grey-free look-dev map with one Stoneback;
   tune traversal and camera; framing check.
3. S1 end to end → AutoPlay → validate-run → `milestone/autoplay-1` → framing screenshots → recording request.
4. S2 (town, 4 Cairns, rescues, gate) → `milestone/autoplay-2`; S3 (boss, tethers, mantle, payoff) →
   `milestone/autoplay-3`.
5. Polish: menus, settings, save, audio, ambient runners, cords, Shipping package, status.

## 13. Status

- 2026-10-12: story bible and design draft v1 written during the shared-slot hold; title EMBERWAKE chosen; repo
  created; sent to the coordinator for approval.

# Siege Catapult (`siege-catapult`)

Fill-in for [../game-session.md](../game-session.md). Original prompt: [../original/game-siege-catapult.md](../original/game-siege-catapult.md).

| Placeholder | Value |
|---|---|
| `{{GAME_TITLE}}` | Unreal game: siege catapult |
| `{{SLUG}}` | siege-catapult |
| `{{PROJECT}}` | SiegeCatapult (`SiegeCatapult.uproject`, modules `SiegeCatapult` + editor `SiegeCatapultEditor`, prefix `SC`) |
| `{{GENRE_LINE}}` | a SIEGE CATAPULT physics game: aim a catapult and bring down Chaos-destructible castles |

## {{PITCH}}

An old siege engineer aims the catapult he built at the six castles he also built, thirty years ago, and knocks down
every crowned figure on their walls with as few shots as possible. Chaos destruction breaks real kit walls into
pieces; wind, three ammo types and a shrinking trajectory preview make each castle harder than the last.

## {{BRIEF}}

- Catapult on a hill: yaw (mouse X / A,D), pitch (mouse Y / W,S), hold LMB or Space to charge power, release to throw.
  Trajectory preview arc includes wind; it shortens from 100 % of the arc (level 1) to 40 % (level 6).
- 3 ammo types (1/2/3 or wheel), limited per level: **Stone** (400 kg, r 30 cm, big impulse, breaks clusters),
  **Explosive keg** (explodes on first impact: radial impulse 600 cm + strain field on Geometry Collections),
  **Split shot** (3 x 120 kg, 8 deg spread, split on RMB/E or 1.2 s after apex). Tuning in `DA_Ammo_*`.
- Castles are Chaos Geometry Collections (kit walls/towers Voronoi-fractured) plus physics blocks. **Kings** (crowned
  figures) are destroyed when they fall 150 cm, leave their platform or take an impulse over threshold.
- Win: every king down. Lose: ammo spent and the last shot settled with kings standing. 1-3 stars by shots vs par,
  saved with best shots (`SiegeCatapult.sav`).
- 6 levels: Training Yard, Twin Towers, The Gatehouse, Windy Ridge, The Keep, The Citadel (1/2/2/3/3/4 kings); wind
  (gusting) from level 4.
- Follow camera on the projectile, slow motion on impact, `C` returns to the catapult, `R` retries.
- HUD: ammo per type, shots + par, kings standing, wind arrow + strength, power bar, angle. Main menu with level select
  (stars, best shots, locks), pause (resume, retry, settings, main menu), settings (master / effects / ambience volume,
  mouse sensitivity, invert Y, resolution, window mode), credits screen.
- Look: realistic scanned medieval. Castles from a bought modular kit, animated catapult, mocap-animated kings with
  ragdoll falls, debris/dust FX, seasonal light per level. Medieval UI with no plain text: kit fonts with ink outline,
  stone frames, gilded buttons, icon ammo slots, key-cap control hints.
- Sound: launch, impacts (stone/wood), explosion, crumble, king down, split, charge, UI, win/lose, wind loop;
  synthesized music (a D-minor plucked theme per level).

## {{SCENARIOS}}

Scenario n = level n via `StartScenario` (no menu). Each starts with the catapult at its pad, full ammo, all kings standing.

1. Training Yard — ammo 5/0/0 (stone/keg/split), 1 king on a small tower behind a palisade, calm — win: all kings down / lose: ammo spent with kings standing
2. Twin Towers — 4/2/0, 2 kings on two stone towers on a ledge, calm — same win / lose
3. The Gatehouse — 4/2/2, 2 kings behind a wall + gatehouse, calm — same
4. Windy Ridge — 3/2/2, 3 kings on towers on raised platforms, light gusting cross wind — same
5. The Keep — 3/3/2, 3 kings, one inside the keep, medium head wind — same
6. The Citadel — 3/3/3, 4 kings on three tiers, strong gusting wind — same

Score: 1000 per king; on a win +500 per star and +100 per unused ammo.

## {{STORY}}

The old king had you build six castles as shelters for the valley's families; now the Regent sends you, with your own
catapult, to pull down every crowned figure the villagers set on the walls. Told by your mason's mark (catapult plaque,
keystones, blue banners, the kings' chests), blue vs red banners, the seasons (spring to first snow), one carved gate
inscription per level ("My first tower. Built in the spring the war ended.") and sealed rooms that open only if you
break the right wall, each adding one results line. Payoff after level 6: the last sealed room holds your own plans and
a crowned likeness of you; the menu line becomes "They crowned the one who built their walls."

## {{ART_PACKS}}

- `fab-ue\medieval-castle-modular-vol-1\` (bought): walls, towers, keep, piers, palisade (fractured into Geometry
  Collections); kit textures for blocks/platforms; its Real_Landscape set for trees, ferns, rocks, grass, mountains.
- `fab-ue\animated-siege-weapons\` (bought): the catapult skeletal mesh with shot / reload / loaded clips.
- `fab\king\` ("Medieval King - Game Ready" by Adam Richard, CC BY 4.0): the crowned figures; credit required.
- `fab-ue\mc-sample-animation-pack\` (MoCap Central): king idle look-around, reactions near breaks, knockdown.
- `fab-ue\realistic-starter-vfx-pack-vol-2\`: brick hit, wood splinter, building dust, keg explosion, dust puff.
- `fab-ue\honeti-4k-full-fantasy-gui\` (bought) + `fonts\Cinzel\`, `fonts\IMFellEnglish\` (OFL): all UI.
- `polyhaven\siege-textures\`, `polyhaven\td-textures\` (CC0): ground scans.
- Built here: music (`Scripts/gen_music.py`), SFX (`gen_sfx.py`), banners, keystones, mason's mark, sealed rooms.
- Not used: `fab\010-medieval-mangonel\`, `fab\free-catapult\`, Megascans castle wall FBX, `fab-ue\item-destruction-fx\`.

## {{GAME_NOTES}}

- Castle stability: at 2000 kg/m3 the structures' own weight exceeded the damage threshold whenever they woke and
  towers cracked at load. Use 150 kg/m3 stone, higher thresholds, kings and blocks starting asleep.
- Geometry Collection break events only fire if `bNotifyBreaks` is set before the physics proxy exists and the solver
  has `bGenerateBreakData`.
- Fractured kit pieces must keep the hierarchy root > module > chunk; collapsing the module level dropped every module
  but the first. Round kit wall/battlement pieces are quarter arcs: close towers and caps from four quarters.
- `PreSkinnedPosition` is vertex-shader-only: using it fails the SM6 compile and the material silently falls back to
  the default. That is invisible in `-nullrhi` runs, so always check rendered screenshots.
- King import: OpenGL normals flipped, masks need Linear Grayscale samplers, the Blender rig's bones carry a x100 scale
  (seat the crown in component space), check facing yaw. Ragdoll on fall, crown on the head bone.
- Mouse aim was 12x too slow: the engine's 0.07 axis sensitivity is already applied to mouse input.
- Bot (`USCBotComponent`) plans with the same trajectory simulation as the preview (`USCTrajectory`, gravity + wind) and
  acts only by injected mouse deltas, 1/2/3, holding LMB to the planned power and RMB to split.
- Test flags: `-sctest -scshots -sctour -scinput -scseq=N -scquit` (own save slot `SiegeCatapult_AutoTest`); Shipping
  ignores a map on the command line, use `-sclevel=N`.
- Par values match perfect aim; a human may find levels 4-6 harder. Big breaks spike 60-160 ms: keep <= ~400 rigid
  bodies per level and remove debris on sleep.
- Keep `r.RDG.AsyncCompute=0` (first-frame GPU hang at some level boots). Workflow row ids are `sc-NNNNN`.

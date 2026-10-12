# The Last Lantern (`tower-defense`)

Fill-in for [../game-session.md](../game-session.md). Original prompt: [../original/game-tower-defense.md](../original/game-tower-defense.md).

| Placeholder | Value |
|---|---|
| `{{GAME_TITLE}}` | Unreal game: tower defense |
| `{{SLUG}}` | tower-defense |
| `{{PROJECT}}` | TowerDefense (`TowerDefense.uproject`, C++ module `TowerDefense`, class prefix `TD`) |
| `{{GENRE_LINE}}` | a top-down TOWER DEFENSE game on a grid, with enemies walking a spline road to the base and upgradable towers |
| `{{VENDOR_BEAT}}` | none |

## {{PITCH}}

The Last Lantern: you are the last keeper of a crystal-crowned tower that holds back the long night, and you build
siege weapons along the valley roads to stop the creatures walking toward it. Three levels move from a lush spring
valley to a grey, drained winter, and the ending reveals what the Lantern really burns.

## {{BRIEF}}

- Top-down camera over a tile grid (WASD / edge / middle-drag pan, wheel zoom, clamped). Enemies follow a spline
  (`ATDPath`) from spawn to the base; tiles the spline crosses are path, the rest are buildable.
- Click a free tile to build (hotkeys 1/2/3), click a tower to upgrade (`U`, 2 upgrades) or sell (`X`, refund 70 % of
  everything spent). Range disc on hover and selection; upgrade panel previews the next level's stats.
- 3 towers: **Ballista** (rapid single target, hits air, armour hurts it), **Catapult** (slow splash, ground only),
  **Frost Spire** (low damage, slow % + duration, small splash, hits air).
- 5 enemies: **Glimmer** (basic), **Darter** (fast, low HP), **Shellback** (flat armour, at least 15 % of a hit gets
  through), **Drifter** (flies 250 cm up, only Ballista/Frost hit it), **Elder** (boss, wave 10, costs 5 lives).
- 3 levels with different roads: **Meadow** (long S-curve), **Canyon** (zig-zag along a dry riverbed),
  **Fortress** (spiral into the Lantern). 10 waves each; waves are groups `{Enemy, Count, Interval, StartDelay}` run in
  parallel; HP scaled by the level's `HPMultiplier`.
- Wave countdown after each wave finishes spawning; **call next wave** (`N` / Space) starts it at once and pays
  `EarlyCallGoldPerSecond x seconds left`. 1x/2x speed (`F`).
- Lives: lose at 0; win when all 10 waves have spawned and nothing is alive. Stars: 3 if lives left >= 90 % of start,
  2 if >= 50 %, else 1. Best per level saved (`USaveGame`, slot `TDSave`); level N+1 unlocks at 1 star.
- All tuning in DataTables / DataAsset: `DT_Towers` (3 levels each: cost, damage, range, fire interval, splash, slow,
  projectile speed), `DT_Enemies`, `DT_Waves_L1..L3`, `DT_Levels`, `DA_TDConfig`; `Data/*.json` is the text copy.
- HUD: gold, lives (Lantern icon), wave n/10, countdown, build bar with tower icons, upgrade/sell panel, range preview.
  Main menu with level select (stars, locks), pause (resume, restart, settings, main menu), settings (master / effects /
  music volume, camera sensitivity, edge scroll, resolution, window mode; saved).
- Look: premium stylized fantasy (hand-painted, Kingdom-Rush-like) from the Fab packs, animated siege-weapon towers on
  castle-stone plinths, animated enemies, Niagara/Cascade impacts. Styled fantasy UI on the HONETi kit with Cinzel /
  Alegreya: no engine font, no bare text (banners, framed cards, icons, outlined labels).
- Sound: SFX for build, upgrade, sell, shoot per tower, hit, explosion, death (soft chimes), leak, wave start, win,
  lose, click, error, coin; menu music and one track per act.

## {{SCENARIOS}}

1. Meadow — `L_Meadow`, 220 gold, 20 Lantern lives, no towers, wave 1 countdown running — win: survive all 10 waves
   with at least 1 life / lose: lives reach 0
2. Canyon — `L_Canyon`, 260 gold, 20 lives, no towers — win: survive all 10 waves / lose: lives reach 0
3. Fortress — `L_Fortress`, 300 gold, 15 lives, no towers — win: survive all 10 waves (two Elders in wave 10) /
   lose: lives reach 0

Scenario n = level-select order (`DT_Levels.Order`). Score: 1 per kill plus wave and life bonuses.

## {{STORY}}

The Lantern burns by drinking the colour of the land; the "enemies" (Glimmers) are the drained fields and rivers given
shape, walking home to the light that took them, and the towers you build are the keepers' old road lanterns.
Told by saturation (the land greys level by level and toward the Lantern), a grey drain ring, flowers blooming where
Glimmers fall, and music from warm major to sparse bells. One title line per level: "Keep the Lantern lit." /
"Here the river ran, before the light drank it." / "Every light you stop is a field that never wakes."
Payoff at the end of Fortress: winning shows "The Lantern burns on." over a grey valley; losing cracks the crystal
and colour washes back: "The lights come home." Losing is the kinder ending.

## {{ART_PACKS}}

- `fab-ue\stylized-fantasy-provencal\`: rocks, cliffs, bushes, trees, houses, windmill, shrine, cart, paving (scatter
  and story props); needs Virtual Texturing on.
- `fab-ue\free-stylized-forest-sample\`, `fab-ue\free-stylized-foliage\` (StyleHex): forest band, meadow grass,
  flower clumps (the blooms where Glimmers fall), terrain textures.
- `fab-ue\stylized-castle\` (bought): the Lantern keep (dais, roof, lamp crown), tower plinths, Fortress ruins, banner.
- `fab-ue\stylized-human-siege-weapons\` (bought; FBX also in `fab\stylized-human-siege-weapons\`): Ballista and
  Catapult tops with idle/attack animations, bolt and stone ammo.
- `fab-ue\paragon-minions\` (Glimmer, Shellback), `fab-ue\paragon-sevarog\` (Elder),
  `fab-ue\quadruped-fantasy-creatures\` (Darter = Barghest, Drifter = Griffon): enemies with run/fly/death clips.
- `fab-ue\realistic-starter-vfx-pack-vol-2\`, `fab-ue\m5-vfx-vol2-fire-and-flames\`: impacts, explosions, burning stone.
- `fab-ue\honeti-4k-full-fantasy-gui\` (bought): buttons, wood panel frames, gold icons, stars, slider, checkbox.
- `fonts\Cinzel\`, `fonts\AlegreyaSans\` (OFL): display and body text.
- `fab-ue\fantasy-music-starter-pack-v2\` (CC BY 4.0, credit "Music by Cinematsic"): menu + one track per act.
- `fab-ue\good-sky\`: copied, not placed (the top-down camera barely sees the sky).
- Built here: ground material with runtime path mask, Glimmer rim glow, drain post-process, Lantern glow, all SFX.

## {{GAME_NOTES}}

- Store packs go into `Content/<PackFolder>/` unchanged (not `Content/Fab/`): their internal `/Game/<PackFolder>/`
  references need the original name. `Scripts/fetch_fab_ue.sh` re-copies; then run `Scripts/s36c_fix_broken_refs.py`
  once (four Paragon minion physics assets saved by UE 5.7 and one unused Sevarog skin are cleared).
- The drain is a stencil-masked post-process (`M_TD_DrainPP` reading `MPC_TD`). Anything that must keep colour
  (Glimmers, shots, lamps, crown, blooms, towers) writes custom stencil 1.
- The siege-weapon pack material reads black from the top-down camera: towers use our own material with a colour lift
  and lower metallic (ballista blue trim, catapult red).
- Paragon and quadruped enemies read small from above: scale them 1.5-2x and match animation play rate to ground speed.
- UI is Slate built in C++ (`STDHud`, `STDMainMenu`, `STDSettingsPanel`). The HONETi pack's own font draws digits as
  boxes; use Cinzel / Alegreya. Hold references to UI icon brushes (dangling brushes crashed only in packaged builds).
- Another packaged-only crash: the ground plane was garbage-collected on level travel. Debug packaged crashes with a
  PDB build. Shipping ignores a map on the command line; use `-tdlevel=<Id>`.
- Every player decision is an Enhanced Input action (14 in `IMC_TD`); the cursor goes through
  `ATDPlayerController::GetPointerPosition` (real mouse or a HUD-drawn virtual cursor), so the bot can play it.
- Test bot flags: `-tdauto -tdspeed=N -tdshots -tdquit`. Bot at 4x: Meadow 20/20 lives, Canyon 12/20 (HP x1.28 after
  the art swap), Fortress 10/15. Tune tables field by field from bot results (`tune.py`).
- An intermittent first-frame GPU hang in editor `-game` launches came from Lumen screen-probe gather on async compute
  racing VSM init: keep `r.RDG.AsyncCompute=0`.
- Workflow row ids are `td-NNNNN`.

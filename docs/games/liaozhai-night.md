# Unreal game 2: Liaozhai Night (聊斋·兰若夜)

Track B game (batch 2): a small, complete third-person Chinese-folklore **action** game in Unreal Engine 5.3, built by
an agent (Claude) with every real editor and code operation recorded when it happens in `workflow.jsonl`
(schema `superposition.ue-workflow/v0`). Project: `%GF_ROOT%\games\liaozhai-night`
(`LiaozhaiNight.uproject`, C++ module `LiaozhaiNight`, own git repo with LFS).

It shares the theme of LiaoZhaiRL (the shipped Unity game in Track A) on purpose, so the dataset has the same kind of
content built in Unity and in Unreal. **Reuse pivot (user, 2026-10-11 ~03:00):** "reuse as much resource from liaozhai
as possible, that's the whole purpose". From then on LiaoZhaiRL's art is brought across from a read-only snapshot
(`liaozhai-replay/end`, git d8adc87262): characters and their clips (Unity `.anim` converted to Unreal), painted
textures, temple/bamboo/grave sprites as cut-out cards, ground tiles, VFX sprites, the UI font. Code, levels, kit
meshes, materials, audio and gameplay are built here. Every reused file is listed in `assets.manifest.json`; the
mapping is in `docs/liaozhai-reuse.md` in the game repo. Locomotion clips LiaoZhaiRL (a 2.5D game) never had (walk,
jump, land, light flinch) come from the CC0 Quaternius Universal Animation Library, retargeted onto the hero (user's
choice, chat 2026-10-11).

Started 2026-10-11 01:40 -04:00.

## 1. The game in one paragraph

A wandering scholar (书生) seeks shelter for the night in the ruined Lanruo Temple (兰若寺). The moon is up, the
mist is thick, and the temple belongs to spirits: ghost lanterns drift through the courtyard, tree-spirit thralls
lurch out of the bamboo, a fox spirit throws foxfire from the graves, and in the inner hall waits 姥姥 (Lao Lao),
the ancient tree demon whose roots hold the whole temple. Armed with a peach-wood sword (桃木剑, the traditional
exorcist's weapon) and three kinds of paper talismans (符咒), the scholar fights through three levels until dawn.
Tone: moonlit, misty, eerie and beautiful, ink-wash inspired; spirits dissolve into ink and petals, never gore.

**Presentation pivot (user, 2026-10-11 ~08:20): 2.5D / HD-2D.** LiaoZhaiRL's own `MainCamera.prefab` is
orthographic, tilted 30° down at a fixed yaw, with 3D heroes moving freely on the ground, so the game now uses that
framing: a fixed tilted camera (perspective, 36° FOV from ~23 m, so Lumen, fog, depth of field and parallax between
depth layers still work), free ground movement (no side-scroller plane: LiaoZhaiRL has none and the fights need
depth), camera zones (`ALNCameraZone`) that reframe areas, and a cut-away that hides scenery between camera and hero.
Characters stay 3D (LiaoZhaiRL's are 3D models). Stages are restaged as left-to-right strips with a far-side
backdrop (halls, walls, bamboo) facing the camera and low foreground pieces, built from store kits (China Modular
Temple, Photorealistic Bamboo Forest, Japanese Forest Grave, Korea Heritage Service scans) plus LiaoZhai's sprite cards.

## 1b. Story bible

**Show, don't tell.** No dialogue, no lore screens. The story lives in the temple (belongings, couplets, steles,
talismans on doors, a faded mural), in who the enemies turn out to be, in the boss's two phases and in the music.
On screen: at most one short line per chapter (a title-card verse under 15 characters) and the ending line.

**Premise.** Lanruo Temple (兰若寺, from 聊斋志异's 聂小倩) stands empty on a mountain road. Scholars travelling to
the examinations shelter there for one night and are never seen again; by morning only their book chests remain.
The temple belongs to 姥姥, an ancient tree whose roots run under every hall. Long ago she caught 葛巾, the white
peony spirit of 聊斋's story of that name, and grafted her on as a lure and a face: travellers see a lovely woman
at the edge of the lantern light and follow. Each scholar she takes becomes a light in her branches (the ghost
lanterns) or wood in her roots (the tree thralls); the foxes are her house servants.

**Characters.**
- **青砚 (Qingyan)**, the player: a wandering ink-talisman exorcist (LiaoZhaiRL's ink-brush fighter). She is not a
  scholar; she came because of the missing ones. Never speaks.
- **The white figure / 葛巾 (Gejin)**, the spirit ally: glimpsed, never met. A pale woman in white at the far edge
  of a scene, gone in white peony petals when 青砚 comes close. White peonies and drifting petals mark the right way.
  (Model: LiaoZhaiRL's 葛巾 body in a pale spirit material; portrait: LiaoZhaiRL's 温柔版葛巾 dialogue art.)
- **姥姥 (Lao Lao)**, the boss: the tree. Phase 1 she fights through 葛巾's body (LiaoZhaiRL's crazed 疯狂版葛巾
  look: the face the player has been following, now wrong); phase 2 the tree itself tears through (roots, crimson).
- **The missing scholars**: never seen alive. Their book chests, umbrellas, letters, a brush case, names on graves.

**Motifs.** White peony = 葛巾, guidance, the ending. Lanterns = captured souls (warm orange, a face inside). Roots =
姥姥's reach: thin cracks through paving in chapter 1, roots through walls in chapter 2, filling the hall in chapter
3. Ink = 青砚 (her slashes, talismans and the enemies' death dissolve). Moon → crimson → dawn. Books and brushes left
behind.

**Beats per chapter (and what the player learns where).**

| Chapter | One line (中 / EN) | Beat | Learned from |
|---|---|---|---|
| 1 前院 | 夜宿兰若，莫应人声 / "Sleep at Lanruo; answer no voice." | 青砚 enters the abandoned temple. Lanterns drift where no one lit them. After the first fight, the white figure stands on the far side of the courtyard, then dissolves into petals; the petals drift toward the inner gate. | Book chests and an open umbrella by the side halls (people came and did not leave); yellow sealing talismans on the hall doors, torn (someone fought here); couplet on the main hall; stele 「兰若寺记」 (optional); thin roots cracking the paving. |
| 2 竹林·乱葬岗 | 竹深无路，花自引人 / "No path in the bamboo; the petals lead." | Through bamboo and a stream to the burial ground. Petals settle on the safe stepping stones (the figure helps). In the graveyard the figure kneels at one grave, then is gone. | Graves of scholars (inscriptions: 赴试书生 "scholar on the way to the examinations"); offerings no one has tended; roots wrapped around tombstones; stele on the grave she knelt at (optional). |
| 3 内殿 | 一树千灯，皆是故人 / "A thousand lamps on one tree: all who came before." | The inner hall, roots everywhere, the tree through the roof hung with lanterns. The figure stands at the tree with her back turned; as 青砚 approaches she turns, and 姥姥 rises in her body. Doubt: was the ally the lure? | A faded mural of a woman among peonies (LiaoZhaiRL's 葛巾 background art) on the hall wall; a pile of book chests at the roots. |
| Boss phase 2 | (none) | At half health the tree's real face breaks through: crimson light, root walls; the lanterns she summons now drift into her and are swallowed (they are the scholars). White petals flicker through the crimson storm and she falters once (葛巾 holding her back: a stagger window). | The recolouring: the lanterns were people; the white figure was a prisoner, not the lure. |
| Ending | 花落天明 / "Petals fall; the dawn." | The tree withers into ink. Dawn. Every lantern light rises out of the branches into the sky. The white figure stands close for the first time, bows, and becomes white peony petals. Completion card. | Resolution without words. |

**Music.** Menu: LiaoZhaiRL's title theme. Chapters 1-2: sparse guqin/xiao exploration, a combat layer in fights.
A three-note music-box/guqin motif plays only when the white figure appears (and once more at the ending). Boss:
drums; phase 2 adds the dissonant drone. Ending: the calm temple piece.

**Discoverable texts** (stele/plaque, read with Interact; short classical Chinese with an English line):
- 兰若寺记 (ch. 1): 「寺有古木，夜则灯行。宿者晨失，惟书箱在。」 "An old tree in the temple; at night its lanterns
  walk. Lodgers vanish by morning; only their book chests remain."
- 无名冢 (ch. 2): 「葬赴试书生十七人，皆不知其名。」 "Seventeen scholars bound for the examinations lie here,
  names unknown."
- 牡丹碑 (ch. 2, the grave she knelt at): 「白牡丹一株，夜开不谢。」 "A white peony grows here; it blooms at night
  and never fades."
- Main-hall couplet (ch. 1): 「风扫空庭无客到 / 月悬古殿有灯明」, plaque 「兰若寺」.

## 2. Controls

| Action | Keyboard / mouse | Gamepad |
|---|---|---|
| Move (camera is fixed, HD-2D) | WASD | left stick |
| Light attack (3-hit combo) | Left mouse | X (left face) |
| Heavy attack (stagger, combo finisher) | Right mouse | Y (top face) |
| Dodge (i-frames) | Left Shift / Left Alt | B (right face) |
| Jump | Space | A (bottom face) |
| Lock-on toggle / switch target | Q or middle mouse / mouse wheel | right thumb / right stick flick |
| Fire talisman 火符 | 1 | left shoulder |
| Binding talisman 缚符 | 2 | right shoulder |
| Wind talisman 风符 | 3 | left trigger |
| Interact (pray at shrine) | E | X (hold) |
| Pause | Esc / P | Start |

All actions are Enhanced Input actions (`IA_*`), which the AutoPlay bot also injects.

## 3. Combat systems

### Ability system choice: custom components, not GAS

A clean custom ability layer (`ULNCombatComponent` for melee, dodge, poise and hit reactions;
`ULNTalismanComponent` for talismans, cooldowns and spirit energy; `ULNHealthComponent` shared by player and
enemies; `ULNTalismanData` data assets for tuning), not the Gameplay Ability System. Why:

- Scope: one player, three talismans, one resource. GAS's value (replication, prediction, stacking effect rules,
  tag queries across many abilities) is unused in a single-player game of this size, while its setup cost is high
  (attribute sets, gameplay effect assets, tag tables, ability tasks).
- Recording: GAS tuning lives in GameplayEffect/Ability Blueprint graphs that UE Python cannot author; a custom
  component keeps every rule in readable C++ diffs (`code.change` rows) and every tuning number in data assets
  that editor scripts create and set (`asset.create` / `property.set` rows).
- AutoPlay: the bot reads cooldowns, spirit and enemy states directly from these components.

### Melee

- **Light attack** (LMB): 3-hit combo (slash, back-slash, thrust); 0.35-0.5 s per swing; an input buffered in the
  last 40 % of a swing chains the next hit; the combo resets 0.6 s after the last swing.
- **Heavy attack** (RMB): slow overhead strike (0.8 s), 2.2x damage, big poise damage. After light hit 2 or 3 it
  becomes the **finisher** (spinning sweep, hits all around).
- Hit detection: sword sweep sphere traces between swing start and end frames (per-swing hit list, no double hits).
- **Hit-stop**: attacker and victim `CustomTimeDilation` = 0.05 for 60 ms (light) / 110 ms (heavy, finisher).
- **Camera shake**: small on light hits, medium on heavy hits and when the player is hit, large on boss slams.
- **Hit reactions**: victims flash (material parameter `HitFlash`), are knocked back along the hit direction and
  play a flinch; enemies have **poise**: when it breaks they are **staggered** for 1.5 s (dizzy ink swirl, take
  +50 % damage). The player flinches on every hit (0.35 s, cancels attacks) and is knocked down by heavy blows.
- **Feel pass** (user: "movement is very unnatural, we need better movement and 打击感"): hit windows come from the
  frame where each LiaoZhai clip's hand actually peaks (`Scripts/analyze_qy_clips.py`), clips play at fixed rates
  instead of being stretched; the lunge lands on the strike frame; hit-stop 70 ms light / 90 ms third hit / 120 ms
  finisher / 140 ms heavy; an ink slash arc (`ALNSlashFX`, painted crescent) draws across every swing with its own
  tilt and sweep direction; heavy connects punch the FOV in; enemies recoil along the hit; the last kill of a fight
  plays at 0.25x for 0.45 s. Locomotion: idle → walk → run share one stride phase advanced by distance travelled
  (run speed measured from the clip's planted foot, so feet do not slide), take-off / air / landing and a brake skid,
  per-bone layer blending (clips without a bone's track keep the pose under them), the body always turns toward
  where it runs (no strafe clips exist).
- **Dodge** (Shift): 0.45 s dash in the input direction (backstep with no input), **i-frames 0.08-0.38 s**,
  0.25 s recovery; cancels the recovery part of an attack.
- **Lock-on** (Q): picks the enemy nearest to screen centre within 18 m in view; attacks and casts snap to it (the camera stays fixed);
  wheel / Q while locked switches to the next target; breaks beyond 25 m or on death. HUD marker on the target.

### Talismans and spirit energy (灵力)

Spirit energy 0-100: +6 per light hit, +10 per heavy hit, +15 per kill, +1.5/s regeneration, refilled at shrines.

| Talisman | Cost | Cooldown | Effect |
|---|---|---|---|
| 火符 Fire | 25 | 4 s | Thrown paper talisman (homes on the lock target), bursts into cyan-white spirit fire: 35 damage in 3 m + burn 6/s for 3 s |
| 缚符 Binding | 40 | 10 s | Golden seal chains on the lock target (or nearest in front, 12 m): bound 3 s (no move, no attack); interrupts boss attacks; boss: 1.5 s |
| 风符 Wind | 30 | 7 s | Gust ring around the scholar: knocks enemies back 6 m, 15 damage, destroys enemy projectiles, clears ghost-lantern flames for 2 s |

### Health, death, checkpoints

Player 100 HP. Health shrines (土地龛, small roadside shrines) are checkpoints: praying (E) restores health and
spirit and sets the respawn point; one use per visit. Death: ink fades the screen, "你已殒命 / You have fallen",
retry from last checkpoint (enemies of uncleared encounters reset) or quit to menu.

## 4. Enemies (Behavior Trees built in C++)

Behavior Tree / Blackboard assets cannot be authored from UE Python (their graphs are not scriptable) and binary
`.uasset` hand-editing is not allowed, so, like the stealth session, each enemy's `UBehaviorTree` and
`UBlackboardData` are built in C++ at startup (`LNEnemyBehavior.cpp`, real BT objects: the gameplay debugger shows
them) with custom tasks (`UBTTask_LNAttack`, `UBTTask_LNStrafe`, `UBTTask_LNBlink`, ...). Common base `ALNEnemy`
(health, poise, hit reactions, death dissolve, bound state, spirit drop).

| Enemy | Look | Behaviour | HP / poise |
|---|---|---|---|
| 灯笼鬼 Ghost lantern | floating paper lantern with a ghost-fire face and paper tail, bobbing | drifts toward the player at head height, circles, then telegraphs (flame flares 0.6 s) and lunges (bite 10 dmg); flees briefly after; flames scorch if touched while flared | 40 / 20 |
| 树妖仆 Tree thrall | mannequin with bark material, branch antlers, moss | walks in, telegraphs (0.7 s raise) and slams (18 dmg, short AoE) or two-swipe combo; high poise, slow | 130 / 80 |
| 狐妖 Fox spirit | slim figure in red-white robe, fox mask and three tails | keeps 8-14 m away, strafes, casts 3 homing foxfire orbs (8 dmg each, slow, can be cut by sword or blown by wind); blinks away in petals when the player closes in (cooldown 5 s) | 80 / 40 |

**Boss 姥姥 Lao Lao, the tree demon** (inner hall): a huge twisted trunk with a pale mask-like face rooted in the
middle of the hall, branches through the broken roof; her heart lantern glows in the trunk. 900 HP.

- Phase 1 (100-50 %): root spikes erupt under the player (telegraph: glowing crack ring 0.9 s), root sweep across
  half the arena (jump or dodge), spits petal bolts, summons 2 ghost lanterns every 25 s. Weak point: the trunk
  (all damage) — heavy hits and fire talismans stagger her (opens the heart for +50 %).
- Phase change (50 %): she screams, the arena **transforms**: the floor tiles break, a ring of roots walls off the
  outer arena, the moonlight turns crimson-violet, petals storm, branch canopy closes overhead.
- Phase 2 (50-0 %): faster spikes in lines of three, a root wave ring (jump over), vine grabs (binding talisman or
  dodge breaks), summons a fox spirit + thralls once. Defeat: the tree withers into ink, dawn light floods the hall.

## 5. Levels

| # | Map | Setting | Content |
|---|---|---|---|
| 0 | `MainMenu` | temple gate under the moon, slow camera | title 聊斋·兰若夜, level select, settings, quit |
| 1 | `L1_Courtyard` 兰若寺·前院 | broken mountain gate, courtyard with stone lanterns, incense burner, side halls, main hall facade | tutorial prompts (move, attack, dodge, lock-on, each talisman); fights: 2 lanterns → 3 lanterns + 1 thrall → 1 fox; shrine mid-way; rear gate opens when the courtyard is cleared |
| 2 | `L2_BambooGraves` 竹林·乱葬岗 | misty bamboo path, stream with stepping stones and a broken bridge (light platforming), graveyard with tombstones and a pagoda | 2 encounters on the path, 3-wave graveyard arena (lanterns + foxes + thralls); 2 shrines; falling into the stream = small damage + reset to last safe stone |
| 3 | `L3_InnerHall` 内殿 | ruined inner hall around a giant tree, broken roof, moon shaft | shrine at the entrance, boss fight, ending (dawn) |

Level complete screen: time, deaths, damage taken, talismans used, a grade (甲 / 乙 / 丙); best values are saved.

## 6. Art direction (built here unless noted)

- **Palette**: ink black, rice-paper beige, cold moon silver-blue, vermilion (lanterns, talismans, pillars),
  jade-cyan spirit fire, pale gold seals. Night with strong value contrast.
- **Lighting**: low moonlight (directional, cool), skylight, exponential height fog with volumetric fog, warm
  lantern point lights; light shafts through broken roofs.
- **Ink-wash post-process** (`M_PP_InkWash`, HLSL in a Custom node): depth/normal edge lines in ink, desaturation
  toward paper tones, paper grain, soft vignette, slight edge bleed. Character materials have a fresnel **rim light**.
- **Mist**: height fog plus translucent drifting mist cards with a panning noise material.
- **Store kits (from 2026-10-11 ~08:30, user direction "premium quality, use the Fab packs")** replace the built-here
  kit as the visible architecture: China Modular Temple (halls, walls, doors, roofs, plaques), Photorealistic Bamboo
  Forest (bamboo grove), Japanese Forest Grave (graves, roots, dead trees, stone steps; its Japanese-only pieces such as
  torii and gohei are not used), Korea Heritage Service scans where a Chinese piece is missing. Store content lives
  under `Content/Fab/<Pack>/`, out of git, listed in `assets.manifest.json`.
- **Temple architecture kit (first build, superseded)** (Geometry Script from editor Python, saved as static meshes): timber columns with
  stone bases, beams and brackets, curved tiled roofs with ridge and upturned eave ends, walls, paper lattice
  windows, doors, steps, platform, stone lanterns, paper lanterns, incense burner, broken roof pieces, mountain
  gate, bamboo stalks, tombstones, pagoda, rocks, bridge planks, the boss tree.
- **Materials**: lacquered red timber, grey roof tiles, aged plaster, stone, bamboo, bark, paper (emissive for
  lanterns), ink, gold seal; textures generated by Python (noise, tiles, paper grain, lattice masks).
- **Niagara**: spirit fire (cyan), talisman burst, binding seal chains, wind gust ring, falling petals,
  fireflies, mist motes, hit sparks (ink splashes), enemy death (ink + petals). Built from Niagara's template
  emitters by a small editor module (`LiaozhaiNightEditor`) that Python calls, with our own materials and
  parameters.
- **Characters (after the reuse pivot)**: the hero is LiaoZhaiRL's ink-brush fighter **青砚** with her own clips
  (light/heavy combo, 飞墨惊云 finisher, dash, casts, hits, death; 102 Unity clips converted by `Scripts/lzanim.py`,
  error ~1e-6 against FBX ground truth) plus the LiaoZhai 女侠 dodge and CC0 walk/jump/land/flinch retargets. Enemies:
  树妖 (tree thrall, FBX clips), 狐妖 (fox spirit), 鬼火 wisp inside a kit paper lantern (ghost lantern). Boss 姥姥's
  avatar is 葛巾's phase-1 peony-demon body with its v19a clips (rise, attacks synced to their strike frames,
  ground-spike cast, death), standing before a 1400 cm kit tree. All on a toon material (`M_LN_Toon`) because
  LiaoZhai textures carry painted lighting. (The first plan, a kitbashed Manny scholar, was replaced.)
- **UI art (2026-10-11 ~09:00)**: LiaoZhaiRL's own battle UI: brush plate, red health bar in a gold frame, jade spirit
  stroke, skill rings around the talisman papers with a round cooldown shade, the ornate boss bar with cloud ornaments,
  monster bar over the lock target, the chapter scroll plaque, 魂飞墨散 death strip and seal, victory strip and seal,
  prompt bars, pause / settings panels, slider art, gold-edged buttons, the hero portrait 青砚 on the title screen
  (`Art/LZ/ui.json`, 39 files, sha256 per file).
- **UI**: Chinese by default with an English toggle; all text in LiaoZhaiRL's LXGW WenKai 楷体 (SIL OFL; the
  project's other fonts are commercial and not used); health/spirit bars as ink brush strokes; talisman icons drawn by code
  (flame, chain seal, wind swirl on yellow talisman paper).

## 7. Audio (offline synthesis, `Scripts/synth_audio.py`)

Pentatonic (宫商角徵羽) music: guqin plucks (Karplus-Strong with body resonance and slides), xiao flute (breathy sine
with vibrato and noise), low drones and wind; tracks: menu, exploration (L1/L2), combat layer, boss (with drums),
victory. SFX: sword swishes, hits (wood/paper/flesh-less thumps), heavy impact, dodge whoosh, talisman throw,
fire burst, binding bell chime, wind gust, lantern wail, fox giggle chirps, tree creak and root rumble, boss scream
(formant-filtered noise), shrine bell, UI wood-block click, death drum, victory gong. Imported as SoundWaves with
sound classes (Music / SFX) for the volume settings.

## 8. Code layout (module `LiaozhaiNight`)

| Class | Role |
|---|---|
| `ALNCharacter` | scholar: movement, Enhanced Input, combat + talisman + health components, outfit attachments |
| `ULNCombatComponent` | light/heavy combos, input buffer, sword traces, dodge + i-frames, hit-stop, lock-on |
| `ULNTalismanComponent`, `ULNTalismanData` | spirit energy, cooldowns, casting the three talismans |
| `ULNHealthComponent` | HP, poise, damage events, death |
| `ALNProjectile` | fire talisman, foxfire orb, boss petal bolt |
| `ALNEnemy` (+ `ALNGhostLantern`, `ALNTreeThrall`, `ALNFoxSpirit`) | enemy base and types |
| `ALNEnemyAIController`, `LNEnemyBehavior` | perception, Blackboard, runtime-built Behavior Trees and tasks |
| `ALNBossLaoLao`, `ALNRootSpike`, `ALNArenaTransform` | boss, its attacks, the phase-2 arena change |
| `ALNEncounter` | trigger volume + waves of enemy spawns, gates that close/open |
| `ALNShrine`, `ALNLevelExit`, `ALNTutorialPrompt`, `ALNKillZone` | level flow pieces |
| `ALNGameMode`, `ALNMenuGameMode`, `ALNPlayerController` | level flow, checkpoints, death/retry, pause, menus |
| `ULNGameInstance`, `ULNSaveGame` | settings, language, progress, AutoPlay wiring |
| `ALNHUD`, `LNWidgets` | HUD and menus (UMG built in C++) |
| `ULNBotComponent` | AutoPlay bot (input injection only) |
| `UAutoPlaySubsystem` | shared drop-in, unchanged |

Editor module `LiaozhaiNightEditor`: BlueprintCallable helpers Python cannot do itself (Niagara system assembly).

## 9. AutoPlay (docs/autoplay-contract.md)

Bot = `ULNBotComponent` on the player controller, acting only through `UAutoPlaySubsystem::Inject`. It walks a
per-level route (waypoint list, read from level actors), locks on to the nearest enemy, keeps fighting distance,
attacks in combos, dodges when an enemy telegraph starts (reaction time), uses talismans when the cooldown is ready
and the situation fits, prays at shrines, jumps the platforming gaps. **Skill** (0..1): reaction time
0.65 s → 0.12 s, dodge success chance 25 % → 95 %, aim/turn noise 25° → 2°, combo discipline (stops attacking
when an enemy telegraphs) 10 % → 90 %, talisman use quality (random → situational), camera look noise.
Telemetry adds `enemy_killed`, `player_hit`, `player_death`, `talisman_cast`, `lock_on`, `dodge`, `checkpoint`,
`boss_phase`, `encounter_start/end`; `state` adds hp, spirit, lock target, enemies alive.
Story telemetry: `story_glimpse` (id), `story_read`, `story_falter`.

**Scenarios (contract v1.3; `-Scenario=<n>`, `milestone/autoplay-<n>`).** `StartScenario(n)` opens chapter n from
the main menu; `ScenarioStarted` reports the chapter's Chinese name.

| # | Name (ScenarioStarted) | Start state | Win | Lose |
|---|---|---|---|---|
| 1 | 第一章 · 兰若寺前院 | chapter 1 player start outside the broken gate, full health and spirit | main hall door reached with E1 + E2 cleared (`level_complete`) | `-MaxSeconds` timeout (deaths respawn at the last shrine) |
| 2 | 第二章 · 竹林与乱葬岗 | chapter 2 start in the bamboo, full health and spirit | broken stupa gate reached with E3 + E4 cleared | timeout |
| 3 | 第三章 · 内殿 · 姥姥 | chapter 3 start on the veranda, full health and spirit | 姥姥 defeated (`boss_defeated`, then `level_complete` after the dawn ending) | timeout |

## 10. Recording

- `workflow.jsonl` rows `{schema, id, seq, time, actor:"agent", op, target, params, reason, reason_source:"agent_note",
  status, source{script, commit}}` appended by `Scripts/wf.py` (imported by editor scripts, `Scripts/wf.sh` from the
  shell). `status`: observed / failed / reverted; `log.gap` + `unrecorded` for anything done without a row.
- Every editor script that ran stays in `Scripts/` unchanged (new file for a new version).
- External assets in `assets.manifest.json` (URL, licence, version/date, what changed).

## 11. Acceptance checklist

- [x] Main menu (calligraphy title, level select with locks + best grade, settings, quit), 中文/English toggle
- [ ] Settings (built, not re-verified after the reuse pivot): master / music / SFX volume, resolution + fullscreen, mouse sensitivity, invert Y; saved
- [ ] Pause (built, not re-verified after the reuse pivot): resume, retry from checkpoint, settings, quit to menu
- [x] Light 3-hit combo, heavy + finisher, dodge with i-frames, lock-on with marker and target switching
- [x] Hit-stop, camera shake, hit flash, knockback, stagger (poise) on enemies, player flinch
- [x] Three talismans with cost, cooldown, spirit meter, distinct VFX + SFX
- [x] Ghost lantern, tree thrall, fox spirit with Behavior Tree AI and telegraphed attacks
- [x] Boss 姥姥: 2 phases, root attacks, summons, arena transformation, boss bar
- [x] 3 levels: courtyard tutorial, bamboo/graveyard with platforming and waves, boss hall
- [x] Shrines (checkpoint + heal), death → retry, level complete screen, progress saved
- [x] HUD: health, spirit, talisman cooldowns, lock-on marker, boss bar, prompts
- [x] Ink-wash post-process, mist, rim light, moonlight; temple kit built here
- [x] Niagara: spirit fire, talismans, petals, fireflies, hits, deaths
- [x] Synthesized guqin/xiao music and SFX, volume classes
- [x] AutoPlay contract (level 1 at least), `milestone/autoplay-1`
- [x] Packaged Win64 build

## 12. Status

_2026-10-11 10:20 -04:00: second pass done (HD-2D camera, store kits, LiaoZhaiRL UI, story). All three chapters
pass AutoPlay; packaged Win64 build rebuilt. (First pass, 08:15: third-person version, all chapters passing.)_

**Works**
- LiaoZhaiRL's framing: fixed camera tilted 30°, free ground movement, camera zones, cut-away of scenery between
  camera and hero, a camera lead so the backdrop fills the frame.
- Chapters restaged as left-to-right stages with the store kits: ch. 1 China Modular Temple halls, paving, grave-pack
  stone walls, lanterns, fire bowls, creeping roots; ch. 2 Photorealistic Bamboo grove, a dark reflective stream with
  stepping stones, a burial ground of grave-pack tombstones wrapped in roots; ch. 3 the inner hall's veranda and the
  grave pack's great dead tree as 姥姥's body with nine soul lanterns in it. LiaoZhaiRL's painted cards between.
  Title screen: the main hall under the moon with LiaoZhaiRL's 青砚 portrait.
- UI entirely on LiaoZhaiRL's art (40 files): brush HP plate and bars, skill rings, boss bar, chapter plaque, brush
  line bars for every message, 魂飞墨散 death strip, victory strip, panels, sliders, dark gold buttons.
- Story (§1b) in play: one verse per chapter, readable steles / couplet / mural (LiaoZhaiRL 葛巾 art, faded), the white
  figure in each chapter (telemetry `story_glimpse`), petals on the safe stones, souls rising from destroyed
  lanterns, the boss faltering at 30 % (`story_falter`), the dawn ending (souls rise, the figure, 花落天明).
- AutoPlay Skill 1 (editor, latest maps): ch1 win 53.2 s, ch2 win 124.7 s (1 death, 1 fall), ch3 win 81.3 s;
  packaged exe ch3 win 98.3 s. Every story event fires in the bot runs.
- Packaged build: `%GF_ROOT%\builds\liaozhai-night\Windows\LiaozhaiNight.exe` (Development, 2.4 GB).

**Left / known issues**
- Not hand-played by a person yet (`docs/playtest-checklist.md` has the new camera / story items).
- Under warm lantern light the ink-wash post turns some enemies (ghost lanterns, thralls) almost paper-white.
- Spirit barriers are smaller but still read as glassy slabs.
- The grave pack's tombstones are Japanese in form; the Korea Heritage Service tomb pack (on disk) could replace
  them. No book-chest / belongings meshes yet (the story bible mentions them; none in the packs or LiaoZhaiRL sprites).
- Exploration / combat / boss music still synthesized (LiaoZhaiRL's Wwise banks need vgmstream); the title loop, two
  boss cues and the new ally motif are in.
- LiaoZhaiRL reused content lives under `Content/LN/...` (each file named in the manifest), not a separate
  `Content/LiaoZhai/` folder.
- The AutoPlay drop-in still carries the old schema strings; waiting for the neutral v1.2 drop-in.

**Built here vs. reused**
- Built: C++ gameplay and UI (~11.5k lines), 130+ editor/tool scripts, materials (ink-wash post, spirit, soul glow,
  stream water), 31 Niagara systems, synthesized audio, 4 maps, the mural composite.
- Reused (`assets.manifest.json`): 170 LiaoZhaiRL assets (snapshot git d8adc87262, sha256 per file for the new ones),
  6 CC0 Quaternius clips, 3 Fab packs (China Modular Temple, Photorealistic Bamboo Forest Foliage, Japanese Forest
  Grave; Fab Standard, kept out of git under `Content/Fab/`).

**Stats**: 1086 workflow rows (46 failed, 3 log.gap), 22 commits, 01:42 → 10:20 (about 8.6 h).

# 聊斋·兰若夜 Liaozhai Night (`liaozhai-night`)

Fill-in for [../game-session.md](../game-session.md). Original prompt: [../original/game-liaozhai-night.md](../original/game-liaozhai-night.md).

| Placeholder | Value |
|---|---|
| `{{GAME_TITLE}}` | Unreal game 2: Liaozhai night |
| `{{SLUG}}` | liaozhai-night |
| `{{PROJECT}}` | LiaozhaiNight (`LiaozhaiNight.uproject`, modules `LiaozhaiNight` + editor `LiaozhaiNightEditor`, prefix `LN`) |
| `{{GENRE_LINE}}` | a Chinese-folklore ACTION game with melee and talisman combat, seen through a fixed tilted HD-2D camera |
| `{{VENDOR_BEAT}}` | none (it pairs with the LiaoZhaiRL Unity game: same theme and content, built in Unreal) |

## {{PITCH}}

青砚, a wandering ink-talisman exorcist, spends one night at the ruined Lanruo Temple (兰若寺), where travelling
scholars vanish. With a peach-wood sword and three paper talismans she fights ghost lanterns, tree thralls and a fox
spirit through the courtyard, a bamboo grove and a burial ground, to the old tree 姥姥 in the inner hall. Moonlit,
misty, ink-wash beautiful, never gore.

## {{BRIEF}}

- Reuse rule (user, replaces the original "copy nothing"): reuse as much of LiaoZhaiRL as possible (characters and
  clips, painted textures, sprite cards, VFX sprites, UI art, font, title music) from the read-only snapshot
  `liaozhai-replay/end` (git d8adc87262). Code, levels, kit layout, materials, most audio and gameplay are built here.
- Camera (user pivot to HD-2D): LiaoZhaiRL's framing, fixed yaw, tilted ~30 deg down, perspective 36 deg FOV from
  ~23 m (so Lumen, fog, DOF and parallax still work); free ground movement, no side-scroller plane; camera zones
  (`ALNCameraZone`) reframe areas; scenery between camera and hero is cut away. Stages are left-to-right strips with a
  far backdrop facing the camera and low foreground pieces.
- Combat (custom components, not GAS): light 3-hit combo (buffer in the last 40 % of a swing), heavy 2.2x with big
  poise damage, finisher after light 2 or 3; dodge 0.45 s with i-frames 0.08-0.38 s; jump; lock-on within 18 m
  (breaks at 25 m). Hit-stop 70 / 90 / 120 / 140 ms, camera shake, hit flash, knockback, poise break = 1.5 s stagger
  (+50 % damage), ink slash arcs, last kill of a fight at 0.25x.
- Talismans on spirit energy 0-100 (+6 light hit, +10 heavy, +15 kill, +1.5/s): Fire 火符 (25, 4 s, homing burst
  35 + burn), Binding 缚符 (40, 10 s, bound 3 s, boss 1.5 s), Wind 风符 (30, 7 s, knockback ring 6 m, clears projectiles).
- Enemies (Behavior Trees): 灯笼鬼 ghost lantern (40 HP, flare telegraph, lunge bite), 树妖仆 tree thrall (130 HP,
  slam / two-swipe, high poise), 狐妖 fox spirit (80 HP, keeps 8-14 m, 3 homing foxfire orbs, blinks away).
  Boss 姥姥 (900 HP): phase 1 root spikes, root sweep, petal bolts, lantern summons; at 50 % the arena transforms
  (floor breaks, root ring, crimson light); phase 2 faster spike lines, root wave, vine grabs, summons.
- 3 levels: 兰若寺·前院 courtyard (tutorial + first fights), 竹林·乱葬岗 bamboo and burial ground (stream stepping
  stones, waves), 内殿 inner hall (boss, dawn ending). Shrines (土地龛) heal and set the respawn; death = retry from
  the last shrine. Level complete: time, deaths, damage, talismans, grade 甲 / 乙 / 丙, bests saved.
- HUD and menus entirely on LiaoZhaiRL's battle UI art: brush HP plate, jade spirit stroke, talisman skill rings with
  cooldown shade, ornate boss bar, lock-on marker, chapter scroll plaque, death and victory strips. Chinese by default
  with an English toggle; all text in LXGW WenKai. Main menu (calligraphy title, level select with locks + best grade),
  settings (master / music / SFX volume, resolution, fullscreen, mouse sensitivity, invert Y), pause.
- Look: palette of ink black, rice paper, moon silver-blue, vermilion, jade spirit fire; ink-wash post-process
  (`M_PP_InkWash`), rim light, height fog + drifting mist cards, light shafts, 31 Niagara systems (spirit fire,
  talismans, petals, fireflies, ink hit splashes, death dissolve). Music: LiaoZhaiRL title theme and boss cues plus
  synthesized pentatonic guqin / xiao; synthesized SFX.

## {{SCENARIOS}}

1. 第一章 · 兰若寺前院 — chapter 1 start outside the broken gate, full health and spirit — win: main hall door
   reached with encounters E1 + E2 cleared (`level_complete`) / lose: `-MaxSeconds` timeout (deaths respawn at shrines)
2. 第二章 · 竹林与乱葬岗 — chapter 2 start in the bamboo, full health and spirit — win: broken stupa gate reached
   with E3 + E4 cleared / lose: timeout
3. 第三章 · 内殿 · 姥姥 — chapter 3 start on the veranda, full health and spirit — win: 姥姥 defeated
   (`boss_defeated`, then `level_complete` after the dawn ending) / lose: timeout

## {{STORY}}

姥姥, an ancient tree under the temple, grafted the white peony spirit 葛巾 on as a lure; the scholars she takes become
her ghost lanterns and root thralls. A white figure glimpsed at the edge of each scene (gone in peony petals) leads
the way. One verse per chapter (夜宿兰若，莫应人声 / 竹深无路，花自引人 / 一树千灯，皆是故人), readable steles, a
couplet and a faded mural; book chests and umbrellas left behind. Payoff: 姥姥 rises in 葛巾's body (was the ally the
lure?), then in phase 2 the lanterns are swallowed (they were the scholars) and petals make her falter; at dawn the
souls rise and the figure bows and becomes petals: 花落天明.

## {{ART_PACKS}}

- `fab-ue\china-modular-temple\` (bought): halls, walls, doors, roofs, plaques (ch1, ch3 veranda, title screen).
- `fab-ue\photorealistic-bamboo-forest-foliage-pack\` (bought): the ch2 bamboo grove.
- `fab-ue\japanese-forest-grave\` (bought): tombstones, roots, dead trees, stone steps; the great dead tree is
  姥姥's body. Its Japanese-only pieces (torii, gohei) are not used.
- Store packs live under `Content/Fab/<Pack>/` and are listed in `assets.manifest.json`.
- LiaoZhaiRL snapshot: hero 青砚 with 102 converted clips, 女侠 dodge, 树妖, 狐妖, 鬼火 wisp, 葛巾 phase-1 body as the
  boss avatar, painted cards and ground tiles, VFX sprites, 40 UI art files, LXGW WenKai font (OFL), title theme.
- Quaternius Universal Animation Library (CC0): walk, jump, land, light flinch retargeted onto the hero.
- On disk if needed: `fab-ue\khs-king-tomb-of-silla\` and other KHS / KCISA scans (Chinese-looking tombs to replace
  the Japanese ones; CC BY, credit "Korea Heritage Service"), `fab\chinese-game-music-v10\`, `fab\wafu-vol35-mountain-temple\`.
- Ignore the asset-library notes about Spine / PaperZD 2D sprites: the characters are LiaoZhaiRL's 3D models.

## {{GAME_NOTES}}

- Why custom components instead of GAS: one player, three talismans, one resource; GAS tuning lives in graphs UE
  Python cannot author, while components keep rules in C++ diffs and numbers in data assets the bot can read.
- Enemy Behavior Trees / Blackboards are built in C++ at startup (`LNEnemyBehavior.cpp`); Niagara systems are
  assembled through a `LiaozhaiNightEditor` helper that Python calls.
- Unity `.anim` clips are converted by `Scripts/lzanim.py` (error ~1e-6 vs FBX); the reuse mapping is in the game
  repo's `docs/liaozhai-reuse.md`. LiaoZhaiRL textures carry painted lighting: use the toon material `M_LN_Toon`.
- Feel: hit windows come from the frame where each clip's hand peaks (`Scripts/analyze_qy_clips.py`); clips play at
  fixed rates; locomotion shares one stride phase advanced by distance; the body turns toward where it runs.
- Animation polish (1.1): no momentum sliding into attacks/casts, action clips stop when a character moves, the fox no
  longer moonwalks while strafing, enemy strides synced to measured clip speeds, thrall walks at 180 cm/s. An earlier
  bug had the hero facing 90 deg off her movement.
- Tutorial hints sit in a top band: the tilted camera keeps the hero in the lower half of the frame.
- Fixed bugs to keep fixed: a boss retry locked the player out of the arena; ch2 needed a landing stone at the far bank.
- Known: under warm lantern light the ink-wash post turns ghost lanterns and thralls almost paper-white; spirit
  barriers read as glassy slabs; no book-chest meshes yet; exploration/combat music still synthesized (LiaoZhaiRL's
  Wwise banks need vgmstream). `SK_LaoLao` is an unused legacy import; the boss uses `SK_LaoLaoBody`.
- State: version 1.1.2, all three chapters win under AutoPlay at skill 1, the user called it ready to ship. Keep
  `r.RDG.AsyncCompute=0`. Workflow row ids are `op-NNNNN`.

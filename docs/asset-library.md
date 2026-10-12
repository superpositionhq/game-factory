# Asset library (Track B games)

Curated 3D, texture, audio, UI and font resources for the seven UE 5.3 Track B games, gathered by the
asset-scout session (2026-10-11). Machine-readable catalogue and logs live outside this repo:

| File | What |
|---|---|
| `%GF_ROOT%\asset-library\catalog.jsonl` | one row per downloaded pack: games, source, URL, licence + link, version, engine, bytes, sha256, local path, purpose, quality note |
| `%GF_ROOT%\asset-library\scout-log.jsonl` | every search, decision, Fab library add, cart add and download (time, action, url, result, reason) |
| `%GF_ROOT%\asset-library\fab-library.psv` | every Fab listing added to the account library: `uid|name|licence|game(s)` |
| `%GF_ROOT%\asset-library\fab-ue\LAUNCHER-CHECKLIST.md` | Unreal-format Fab packs to pull through the Epic Launcher into the FabVault53 staging project |
| `%GF_ROOT%\tools\asset-scout\` | scout tools: `scout.py` (log, fetch, Poly Haven), `fabdl.py` (Fab signed downloads), `build_catalog.py` + `packs_meta.tsv` (catalogue) |

Library layout: `asset-library\<source>\<pack>\` (one folder per pack, downloads are untouched archives or
loose files; never run anything inside them). Sources: `fab` (browser downloads: Megascans, FBX/glTF packs,
WAV packs), `fab-ue\FabVault53` (Launcher-only Unreal packs), `polyhaven`, `ambientcg`, `kenney`,
`gameicons`, `fonts`, `opengameart`.

## How things were obtained

- **Fab**: the user signed in to fab.com in the Claude browser pane. Free listings were added to the
  library through Fab's own "Add to My Library" call, always choosing the **Professional** licence when it
  is $0, so the rights hold regardless of revenue. Browser-downloadable formats (Megascans FBX "high"
  tier = 4K maps, texture sets at 4K, FBX/glTF/WAV zips) were downloaded from Fab's signed download links
  (`fabdl.py`; tokens are never logged). **Unreal-format packs only download through the Epic Launcher**:
  the user adds them to `FabVault53` (checklist above).
- **Licence tier for purchases**: the user chose the Fab **Personal** tier (under $100k revenue in the last
  12 months). Items whose Personal tier is $0 were therefore also added (marked "Personal $0" below).
- **CC0 sites** (Poly Haven API, ambientCG, Kenney, OpenGameArt CC0), **OFL fonts** (google/fonts repo,
  OFL.txt kept next to each font) and **game-icons.net** (CC BY 3.0) were downloaded directly.
- Not used: Sketchfab and freesound (both need a login; freesound CC0 picks are listed for the user to
  fetch), Mixamo (Adobe login), Megaplants (UE 5.7+ only), UEFN "reference only" licences, Infinity Blade
  (not on Fab), Quaternius newer packs (custom licence, not CC0).

## Storage

Everything lives in `%GF_ROOT%\asset-library\` (the user asked for all packs there, overriding a
brief plan to put new downloads on D:; the few packs that went to D: were moved back). Catalogue, scout log,
status files and `fab-library.psv` are there too; `local_path` / `path` give exact folders. Tools:
`scout.DL` (default = the C: library; env `ASSET_DL_ROOT` to redirect).

Game credits: per the user's rule, third-party credits inside a game go in its `Docs/ThirdPartyNotices.md`,
written as a normal developer would, with no mention of Superposition, game-factory or recording. The credit
strings in this doc are written for that file.

## Unreal-format Fab packs (no Launcher)

The user asked not to click every pack in the Launcher, so the scout downloads Unreal-format Fab packs itself:
Fab's `download-info` for an owned item returns the Epic build manifest (the same data the Launcher uses);
`tools/asset-scout/fabue.py` fetches the CDN chunks, rebuilds every file and checks its SHA-1 against the
manifest; `fabue_batch.py` runs the batch and scans every `.uasset`/`.umap` header for the engine that saved it.

- **Where:** `asset-library\fab-ue\<pack>\` (as the Launcher would install it: `Content\<PackFolder>\...`,
  sample projects with `Config\` + `.uproject`, plugins under `Engine\Plugins\`). 125 packs, 157 GB, all OK.
- **Status per pack:** `asset-library\fab-ue\_status\<pack>.json` (`result`, `bytes`, `saved_by`, `ue53_ok`,
  `ue53_notes`, `manifest_sha256`) plus the manifest itself. Usage note for game sessions:
  `side-session-notes\...\fab-ue-packs.md`.
- **Pack list in the repo:** [asset-library-fab-ue.tsv](asset-library-fab-ue.tsv) (one row per `_status` file: slug,
  listing, bytes, files, ue53_ok, saved_by, result, manifest_sha256). `machine/check.ps1` compares it and the Path
  column of the per-game tables below with `%GF_ROOT%\asset-library\` on a new machine.
- **Deferred to save disk (20, fetch on request):** Electric Dreams (59.8 GB), Medieval Village Megascans
  sample (22.6 GB), European Hornbeam / Black Alder / Beech, City Sample Vehicles, Downtown West, Megascans
  Warehouse, Saloon Interior, City Street Props, Office Pack, Common Hazel, Landscapes Pack, Vehicle Variety
  Pack, Free Furniture Pack, Lyra, Paragon Feng Mao, KCISA Martial Arts, Dungeon Mason monster + dragon.
- **Not loadable in UE 5.3 (saved by a newer engine; no older build offered):** Animal Sound Effect Pack
  (5.6), Classical Music Box Collection (5.5), Free Thunder Sounds (5.5), Procedural Sea Waves (5.6) and
  Procedural Wind (5.5) MetaSounds. Replaced by raw audio where Fab offers it:
  `fab\horror-ambient-sound-effects-pack-01-wav\` (WAV), `fab\free-city-nature-sounds-unitypackage-audio\`
  and `fab\free-game-sfx-sampler-33-unitypackage-audio\` (audio extracted from the Unity builds),
  `fab\free-realistic-sword-sound-effects-pack\` (WAV).
- **Partly newer:** Paragon Minions (4 physics assets saved by 5.7: regenerate), M5 VFX Vol2 (demo maps
  only, 5.5), Stylized Nature Pack (example map, 5.4), Whisper (demo map, 5.5), Auto Footsteps Utility
  (editor utility, MetaSound presets and the Wood_V1 set are 5.6).

## Licences in use

| Licence | Link | Obligation |
|---|---|---|
| Fab Standard License (Personal / Professional) | https://www.fab.com/eula | Use in games; no redistribution of the raw assets; Personal only under $100k revenue |
| UE Marketplace License (legacy Fab items) | https://www.unrealengine.com/eula/content | Unreal-only use |
| CC BY 4.0 (Fab "CC-BY" items) | https://creativecommons.org/licenses/by/4.0/ | Credit in the game credits (strings below) |
| CC BY 3.0 (game-icons.net) | https://creativecommons.org/licenses/by/3.0/ | "Icons made by {author}. Available on https://game-icons.net" |
| CC0 1.0 (Poly Haven, ambientCG, Kenney, OGA tracks) | https://creativecommons.org/publicdomain/zero/1.0/ | None |
| SIL OFL 1.1 (fonts) | https://openfontlicense.org | Ship OFL.txt with the font; don't sell the font alone |

Note for packaging: Fab Standard assets may ship inside a built game but not as raw files; this matters
for any package that redistributes `Content/` (see plan.md B4). CC0/CC-BY/OFL items have no such limit.

## Common import notes (UE 5.3)

- **Megascans FBX zips** (`fab/<name>-<id>/`): one FBX + 4K JPG maps (BaseColor, Normal, Roughness, AO,
  Displacement, plus Cavity/Gloss/Specular/Bump you can ignore). Real-world scale (the zip's `<id>.json`
  has `physicalSize`). The raw download's normal-map convention isn't stated in the metadata: check one
  asset under a moving light and flip green if the relief looks inverted. Import BaseColor sRGB, the rest
  linear; use one master material with separate slots. Enable Nanite on the scans (25k-130k tris).
- **Megascans texture sets**: tileable 4K surfaces; same map set; displacement suits virtual heightfield
  or tessellation-free parallax.
- **Poly Haven textures**: `diff` (sRGB), `nor_dx` (DirectX normal, use as-is), `arm` (R=AO, G=Rough,
  B=Metal, linear), `disp` PNG. **Poly Haven model FBX ship OpenGL normals (`nor_gl`): flip green on import.**
- **Variable fonts** (Noto Serif SC, Cinzel): UE 5.3 font import uses the default (Regular) instance.
- **Launcher packs** land in `FabVault53\Content\<Pack>\`. Copy the whole pack folder into the game's
  `Content\` (same folder name) to keep internal references; don't move files inside it.

---

## tower-defense

Art direction chosen: **stylized fantasy** (hand-painted / stylized PBR, Kingdom-Rush-like) replacing the
Kenney low-poly look. One family for the world (Provencal + FANTASTIC Village + StyleHex foliage), one for
enemies (Paragon Minions + Sevarog, Griffon flyer), Niagara VFX from M5/FX Cat.

### On disk now

| Pack | Path | Licence | Replaces / serves |
|---|---|---|---|
| FANTASTIC - Village Pack (Tidal Flask) | `fab\fbx-and-textures-fantastic-village-pack\` (337 MB zip: 452 FBX, 80 textures, UE collision meshes) | Fab Standard (Pro $0) | Tower bases (stone/wood), the base keep, Fortress walls and gate, Meadow village dressing, fences, spikes |
| Free Low-Poly Siege Engines (PolyClem) | `fab\polyclem-siege-engines-fbx\` | Fab Standard | Rapid = ballista, Cannon = onager tower tops with Fire/Reload clips; bolt + stone projectiles |
| [FREE] Catapult (ArchViz) | `fab\free-catapult\` (glTF) | CC BY 4.0 | Alternative cannon top |
| Poly Haven td-textures | `polyhaven\td-textures\` (rocky_trail, grass_path_2, red_sandstone_wall, sandstone_cracks, cliff_side, castle_brick_07, medieval_blocks_03) | CC0 | Path dirt, Canyon rock, Fortress stone ground/walls |
| Kenney fantasy-ui-borders | `kenney\fantasy-ui-borders\` | CC0 | 9-slice frames for the build/upgrade panel and menus (until the HONETi GUI is bought) |
| Kenney impact-sounds, rpg-audio, ui-audio, music-jingles | `kenney\...` | CC0 | Hits, coins, UI clicks, win/lose/wave stingers (replace synthesized SFX where better) |
| game-icons.net PNG + SVG | `gameicons\` | CC BY 3.0 | Tower, upgrade, sell, wave, speed icons |
| Cinzel + Alegreya Sans | `fonts\Cinzel\`, `fonts\AlegreyaSans\` | OFL | Titles / HUD text |
| OGA Medieval Market Day (loop), Battle Theme A | `opengameart\...` | CC0 | Meadow music, boss wave |

### In the Fab library (Launcher → FabVault53)

Stylized Fantasy Provencal (claimed while free until 24 Oct), FREE Stylized Forest Sample, FREE Stylized
Foliage, Stylized Tree (Nest), Stylized Nature Pack (Personal $0), Paragon: Minions, Paragon: Sevarog,
Paragon: Rampage, Quadruped Fantasy Creatures, Monster for Survival Game PBR Polyart + Dragon for Boss
Monster (alternative cute set, 512 px textures, not recommended), M5 VFX Vol2 Fire and Flames, Realistic
Starter VFX Pack Vol 2 (Personal $0), FREE! Realistic Niagara Explosions, Paragon: Aurora, Good SKY, Fantasy
Music Starter Pack v2.0 (CC BY, credit "Music by Cinematsic"), Interface & Item Sounds (Personal $0).

### What each piece should replace

| Game element | Now | Replace with |
|---|---|---|
| Ground / Meadow | flat green + Kenney tiles | Provencal landscape material + StyleHex grass/flowers, Poly Haven grass_path_2 for buildable tiles |
| Path | orange Kenney road | rocky_trail (Meadow), red_sandstone_wall/sandstone_cracks (Canyon), medieval_blocks_03 (Fortress) as spline-mesh or decal material |
| Trees, bushes | Kenney cones | StyleHex Forest + Stylized Tree + Tiny Talisman bushes/rocks |
| Rapid / Cannon / Frost towers | Kenney stacked towers | FANTASTIC stone/wood tower bases (3 tiers = 3 levels) + PolyClem ballista / onager tops; Frost = mage/crystal top kitbashed from Provencal/FANTASTIC with Aurora ice FX |
| Enemies | primitive spheres/cubes/cones | Basic/Fast/Armored = Paragon Minions (melee / ranged / super); Flyer = Griffon (Quadruped Fantasy Creatures); Boss = Sevarog |
| Base | purple Kenney tower | FANTASTIC keep/gate (or the paid Stylized castle) |
| Projectiles, hits | spheres | PolyClem bolt/stone, M5 fire muzzle/burn, Realistic Starter explosions, Aurora frost |
| Sky | Poly Haven HDRI | Good SKY (stylized dynamic) |
| UI | flat Slate boxes | Kenney fantasy borders now, HONETi 4K Fantasy GUI after purchase; game-icons for buttons; Cinzel titles |
| Music/SFX | synthesized | Fantasy Music Starter Pack + OGA loops; Kenney SFX layers |

Import notes: Paragon characters use the UE4 mannequin skeleton (retarget not needed for their own anims;
scale ~1 for a top-down camera means they read small: scale 1.5-2x). Paragon FX are Cascade, still render in
5.3. Provencal needs Virtual Texturing on (FabVault53 has it on). PolyClem FBX are in metres with Blender
+Y forward: check axis on import.

### Paid shortlist (purchased, Personal tier)

| Item | Price | Why / replaces |
|---|---|---|
| Stylized castle (AleksandrIvanov) | $14.99 | The base and Fortress castle pieces, rated 5.0 (24) |
| Stylized Human Siege Weapons (N-Hance) | $24.99 | Proper stylized ballista/catapult/cannon tower tops, matching the stylized world (replaces PolyClem) |
| 4k Full Fantasy GUI (HONETi) | $49.99 | 524 PNG + 186 UMG widgets; replaces the flat HUD and Kenney borders |
| Not carted (optional): Stylized Fantasy Creatures Bundle (N-Hance) | $169.99 | One cohesive stylized enemy roster incl. flyers and bosses, if Paragon reads too sci-fi |

---

## liaozhai-night

**Pivot (2026-10-11): 2.5D side-view (HD-2D style).** Characters, enemies, boss and most VFX come from
LiaoZhaiRL's own 2D sprites and Spine animations, so no 3D characters/animations are sourced any more
(Paragon Feng Mao and KCISA Martial Arts stay in the library but are no longer recommended). The 3D sets below
now serve as **lit side-view backdrops and midgrounds**: build the temple, bamboo and graveyard as layered
3D sets viewed from the side, with height fog, volumetric god rays and the ink-wash post-process.

### 2D animation runtime (Spine, PaperZD)

| Item | Licence | UE 5.3 | Notes |
|---|---|---|---|
| **Spine runtime for Unreal** (`spine-ue`, [docs](https://esotericsoftware.com/spine-ue4), [repo](https://github.com/EsotericSoftware/spine-runtimes)) | [Spine Runtimes License](https://esotericsoftware.com/spine-runtimes-license): free to integrate, but distributing software containing the runtime needs a Spine Editor licence at integration time, and each user of the runtime needs their own Spine licence (Essential $69, Professional $379, Enterprise required at $500k+ revenue; per named person) | Branch **4.2**: UE 4.27-5.4, reads data exported from **Spine 4.2.xx** only. C++ project required; plugin copied into `Plugins/` with spine-cpp sources | **Blocker: LiaoZhaiRL's Spine data is version 3.8.75** (154 `.skel.bytes`, checked `Dialog_对话/Spine`, `"spine":"3.8.75"`). The 3.8 runtime (`spine-ue4` branch 3.8) targets UE 4.21-4.25+ and would need porting to 5.3. Options: (a) re-export the source `.spine` projects with Spine Editor 4.2 (needs the source projects + a licence; meshes need Professional), (b) port spine-ue4 3.8 to UE 5.3, (c) bake Spine animations to PNG sequences (in LiaoZhaiRL's Unity project, which has the 3.8 runtime) and play them as Paper2D flipbooks via PaperZD. Also from 5.3 on, `.skel`/`.json` and `.atlas` must not share a name prefix. Default materials are unlit: lit sprites need custom materials (`SpriteTexture` parameter) |
| **PaperZD** (Critical Failure Studio), [Fab](https://www.fab.com/listings/6664e3b5-e376-47aa-a0dd-f7bbbd5b93c0) | Fab Standard (Pro $0), in the library | Yes (4.26-5.8), rated 4.9 (581) | 2D animation blueprints, state machines, notifies on Paper2D flipbooks. Needs a C++-capable build environment to package. Use with option (c) above |
| UI Effect Function Library, [Fab](https://www.fab.com/listings/00621b21-3d59-422e-8bf0-cac99bb01f2b) | Fab Standard (Pro $0), in the library | Yes | UMG/Sequencer helpers for animated ink-brush UI |

Lighting/post references (no download needed): UE 5.3 Exponential Height Fog with Volumetric Fog +
directional light "light shaft bloom/occlusion" for god rays through the broken roof; Local Fog Volumes are
5.3+. Paid ink/painterly post-process options (not carted): Post Process Hand Draw Outline ($19.99, 5.0-5.7,
rated 5.0), Dynamic Sketch Post-Process ($24.99), Anisotropic Kuwahara Oil Paint ($14.99), Chameleon Post
Process ($44.99, rated 4.8 from 257); Ink Painting Gallery Hall Eastern Fantasy ($9.99, Chinese ink-painting
props). Chinese UI: no free Chinese-style UI kit on Fab; build frames from ambientCG Paper + brush strokes
with the OFL brush fonts.

Added audio for the pivot (on disk): `fab\wafu-vol35-mountain-temple\` (temple music, OGG), `fab\wafu-vol31-long-rain\`
(rain music), `fab\forest-sounds\` (CC BY, credit "FOREST SOUNDS by take (fab.com), CC BY 4.0": leaves,
wind, wood, water one-shots). Guqin/xiao: the freesound CC0 picks need a login (Bell at Daitokuji 131348,
Mokugyo 607215, guqin 415167, dizi 108242 / 339357, bamboo creaking 335891); keep the synthesized guqin/xiao.

The earlier 3D environment set follows (unchanged).
Architecture comes from Korea Heritage Service / KCISA scans (Joseon timber halls share the Chinese
structure: columns on stone bases, dougong brackets, curved grey tile roofs, paper lattice). Recolour the
green-red Korean dancheong to vermilion + ink in the material instances; after the ink-wash pass they read
as East Asian temple architecture. Bamboo was the one free gap (paid pack in cart).

### On disk now

| Pack | Path | Licence | Serves |
|---|---|---|---|
| Japanese Stone Lantern (Megascans) | `fab\japanese-stone-lantern-ufnscjdga\` | Fab Standard | Courtyard stone lanterns |
| Japanese Shrine Stairs (Megascans) | `fab\japanese-shrine-stairs-ud4mbgtfa\` | Fab Standard | Hall steps, gate stairs |
| Japanese Shrine Stone Floor (Megascans) | `fab\japanese-shrine-stone-floor-ugrxbjkfa\` | Fab Standard | Courtyard paving |
| Japanese Mossy Stone Wall (Megascans) | `fab\japanese-mossy-stone-wall-ulldfby\` | Fab Standard | Platform and boundary walls |
| Japanese Komainu Statue (Megascans) | `fab\japanese-komainu-statue-ubrpbjcfa\` | Fab Standard | Gate guardian pair (stand-in for stone lions) |
| Dead Tree (Megascans) | `fab\dead-tree-qletl\` | Fab Standard | Graveyard trees, boss kitbash |
| Mossy Rocks (Megascans) | `fab\mossy-rocks-tjmudcfda\` | Fab Standard | Stepping stones, stream banks |
| Rocky Forest Path (Megascans) | `fab\rocky-forest-path-vbhsfesga\` | Fab Standard | Bamboo path ground |
| Ancient Temple Stones (Megascans) | `fab\ancient-temple-stones-tixjegefa\` | Fab Standard | Rubble, broken plinths |
| Old Gravestone x2 (Megascans) | `fab\old-gravestone-wjuvdfeqx\`, `...-wjuvde2qx\` | Fab Standard | Broken grave slabs (mix with KHS tombs) |
| Surfaces 4K: Mossy Forest Floor, Forest Floor, Tree Bark, Damaged Wall Plaster | `fab\mossy-forest-floor-vfylbge\` etc. | Fab Standard | Ground layers, thrall/boss bark, aged plaster |
| Spider Lily (Lycoris Radiata) | `fab\spider-lily-lycoris-radiata\` | CC BY 4.0 | 彼岸花 in the graveyard and on the boss approach |
| Chinese Game Music (BiteMe) | `fab\chinese-game-music-v10\` | Fab Standard | Guzheng/flute/drums: combat + calm, loop versions |
| Free Realistic Sword SFX | `fab\free-realistic-sword-sound-effects-pack\` | Fab Standard | Sword swings/hits |
| Poly Haven liaozhai-textures (12) | `polyhaven\liaozhai-textures\` | CC0 | red_plaster_weathered, worn_mossy_plasterwall, japanese_stone_wall, monastery_stone_floor, chinese_cedar_bark, forest_leaves_02, mossy_rock, weathered_planks, lacquered_cherry_wood (tint vermilion: columns), grey_roof_tiles, roof_tiles_14, bamboo_wall |
| Poly Haven liaozhai-models (11) | `polyhaven\liaozhai-models\` | CC0 | Chinese armchair, cabinet, chandelier, console table, screen panels, stool, tea table (inner/side halls); dead_tree_trunk, root_cluster_01/02 (boss roots), rock_moss_set_01 |
| Poly Haven night HDRIs | `polyhaven\night-hdri\` | CC0 | qwantani_moon_noon_puresky (moon), rogland_moonlit_night, kloppenheim_02_puresky |
| ambientCG Paper001/003, RoofingTiles015A/B, Bamboo001A/002A | `ambientcg\...` | CC0 | Lattice paper, lanterns, talismans; roof tiles; bamboo culm material |
| Fonts | `fonts\MaShanZheng\`, `ZhiMangXing\`, `NotoSerifSC\`, `ZCOOLXiaoWei\` | OFL | Title calligraphy, boss/death screen cursive, body text, menu serif |

### In the Fab library (Launcher → FabVault53)

KHS - Korean temples (CC BY), Dongrae Hyanggyo (UE 5.3 build), KHS - Korean Stone Pagoda, KHS - Korean
Jongmyo Shrine (CC BY), Korean Traditional Heritage Props (CC BY, credit "National Museum of Korea"), KHS -
King Tomb of Silla (CC BY), KHS - Soswaewon Garden (CC BY), KCISA House of Changwon (CC BY), KCISA Spline
Builder (CC BY), KCISA Smart Materials Vol.1 + Vol.4 (CC BY), KCISA Korean Traditional Props (CC BY),
Korean Traditional Interactive Props Vol.2 (CC BY), KCISA Seyeonjeong Pavilion (CC BY), KHS Gwanghwamun
Gate, KHS Naganeupseong Walled Town, Paragon: Feng Mao (sword anims + SFX), KCISA Korean Traditional
Martial Arts (CC BY, 314 anims).

### What each piece should replace

| Game element | Now (design doc) | Replace with |
|---|---|---|
| Main hall, side halls (L1) | Geometry Script kit | Dongrae Hyanggyo compound + KHS temple halls; China Modular Temple (paid) for an authentic Chinese silhouette |
| Mountain gate | built kit | KHS temples Iljumun (single-pillar gate) or Gwanghwamun scaled down; Komainu pair |
| Courtyard | built kit | Megascans shrine stone floor, stairs, stone lanterns, mossy wall; Heritage Props incense burner |
| Bamboo path (L2) | built bamboo | Photorealistic Bamboo Forest (paid) + Rocky Forest Path + Mossy/Forest Floor surfaces |
| Stream, stepping stones, bridge | built | Mossy Rocks, KHS temples stone bridge, weathered_planks for the broken bridge |
| Graveyard + pagoda | built | KHS King Tomb mounds + statues, Old Gravestones (broken), KHS Stone Pagoda, Dead Tree, Spider Lily; Japanese Forest Grave (paid) |
| Inner hall + boss tree | built | Jongmyo/temple hall interior, Poly Haven Chinese furniture, root_cluster + dead_tree_trunk + Tree Bark surface for 姥姥 |
| Materials | Python-generated | Poly Haven + Megascans surfaces + KCISA Smart Materials (tile/timber/plaster) |
| Sky | built | qwantani_moon_noon_puresky HDRI for reflections / backdrop under the moon directional light |
| Music / SFX | synthesized | keep synthesized guqin/xiao as the base; BiteMe tracks as combat/calm layers; sword SFX + Feng Mao cues |
| UI fonts | OFL brush font | Ma Shan Zheng (title), Zhi Mang Xing (boss), Noto Serif SC (body), ZCOOL XiaoWei (menus) |

Import notes: KHS/KCISA packs have no LODs and 4K-8K textures: enable Nanite on the meshes and set texture
LOD bias for distant pieces; they support Lumen. Their dancheong colours live in material instances:
override base colour tint toward vermilion/ink. Spider Lily and Megascans foliage need two-sided foliage
shading. Poly Haven model FBX: flip normal green.

### Credits (CC BY)

"Korea Heritage Service" (KHS packs); "National Museum of Korea" (Korean Traditional Heritage Props);
"Korea Culture Information Service (KCISA)" (KCISA packs); "Spider Lily (Lycoris Radiata)" by Osian3D
(fab.com), CC BY 4.0.

### Paid shortlist (purchased, Personal tier)

| Item | Price | Why / replaces |
|---|---|---|
| Photorealistic Bamboo Forest Foliage Pack | $9.99 | Closes the bamboo gap: 32 stalks, shoots, undergrowth (listing says generated with AI) |
| China Modular Temple (LansenHan) | $24.99 | Authentically Chinese temple kit (blue-grey tiles, eaves, brackets, doors), UE 4.24-5.3 |
| Japanese Forest Grave | $24.99 | Bamboo trees + graves showcase (Nanite and non-Nanite) for L2 |
| Not carted (optional): Traditional_Chinese_Style_Park | $99.99 | Southern-Chinese village set (205 meshes), rated 4.7 (63) |

---

## siege-catapult

Style: **realistic scanned PBR**. Tileable photo materials look right on both outer and Chaos fracture
faces; keep Geometry Collection source meshes simple (beveled 2-4 m blocks) and put the detail in materials.

### On disk now

| Pack | Path | Licence | Replaces / serves |
|---|---|---|---|
| Medieval Mangonel (3DreaMax) | `fab\010-medieval-mangonel\` (FBX + 4K PBR, 171 MB) | CC BY 4.0 | The player catapult (basic shapes); separate the arm for the throw anim |
| Medieval King - Game Ready (Adam Richard) | `fab\king\` (king.fbx rigged + textures.zip 412 MB) | CC BY 4.0 | King targets |
| Castle Wall, Castle Structure (Megascans) | `fab\castle-wall-sctv3\`, `fab\castle-structure-sczvi\` | Fab Standard | Battlements, wall caps, tower dressing |
| Fort Stone Wall 4K (Megascans surface) | `fab\fort-stone-wall-tfuebj3n\` | Fab Standard | Main wall material for the Geometry Collections |
| Poly Haven siege-textures | `polyhaven\siege-textures\` | CC0 | castle_wall_slates, medieval_wall_01 (walls), weathered_brown_planks + wood_planks (catapult, platforms), aerial_grass_rock + forest_ground_04 (hill) |
| Poly Haven td-textures | `polyhaven\td-textures\` | CC0 | castle_brick_07, medieval_blocks_03 (more wall options), rocky_trail |
| Poly Haven siege-models | `polyhaven\siege-models\` | CC0 | large_castle_door, wooden_barrels_01, wooden_crate_01, treasure_chest, cannon_01 (debris, props) |
| Poly Haven day-hdri | `polyhaven\day-hdri\` | CC0 | kloofendal_48d_partly_cloudy_puresky, belfast_sunset_puresky |
| Kenney impact/rpg/ui audio, music-jingles | `kenney\...` | CC0 | Stone/wood impacts, UI, win/lose stingers |
| [FREE] Catapult (ArchViz) | `fab\free-catapult\` | CC BY 4.0 | Alternative catapult |
| Cinzel + Alegreya Sans, game-icons | `fonts\`, `gameicons\` | OFL / CC BY 3.0 | UI text, ammo icons |

### Launcher (FabVault53)

Medieval Village Megascans Sample (UE 5.3 build: wall/tower kitbash source), European Beech, temperate
Vegetation optimized Grass Library, Item Destruction FX (debris puffs), Realistic Starter VFX Vol 2
(Personal $0: dust, explosions, fire ammo).

### Paid (purchased)

Medieval Castle Modular Vol 1 ($39.99: modular PBR walls ideal for fracturing), Animated Siege Weapons
($34.99: rigged/animated catapult and trebuchet, would replace the Mangonel).

Credits: "Medieval Mangonel" by 3DreaMax Studio; "Medieval King - Game Ready" by Adam Richard (both fab.com,
CC BY 4.0).

## rally-racer

Style: photoreal scans on landscape auto-material; Megascans surfaces per track, Project Nature foliage.

### On disk now

| Pack | Path | Licence | Replaces / serves |
|---|---|---|---|
| 11 Megascans 4K surfaces | `fab\dirt-ground-xdhhefr`, `rocky-forest-floor-wjvpaff`, `uncut-grass-oilpt20`, `mud-tire-tracks-vbuqbg3ew`, `soil-mud-pkbch0` (Forest); `bright-desert-sand-sjzkfega`, `rippled-sand-vd3lecfs`, `canyon-sandy-mud-wdunfjf` (Canyon); `fresh-windswept-snow-ugspafgdy`, `trampled-snow-vcqnfdk` (Snow); `tire-tracks-on-mud-seymxkg` (decal) | Fab Standard | Generated landscape layers and the road ribbon |
| Megascans cliffs/rocks | `fab\desert-western-cliff-layered-xl-01-veoneio`, `-xl-14-vjrmfb1ab`, `gigantic-sandstone-terrain-wldhdhxva`, `sandstone-cliff-vmiecie` (Canyon); `nordic-forest-cliff-large-xibsff1` (Forest); `massive-tundra-rock-formation-wcrmbiar`, `snow-hill-vdbmabvva`, `snowy-ground-vefkajufa` (Snow) | Fab Standard | Engine-shape scenery and canyon walls |
| Megascans plants + props | `fab\wild-grass-vlkhcbxia`, `dry-grass-tbbqejqr`, `round-hay-bale-rlcay`, `traffic-cone-uhrhabqfa`, `concrete-barrier-ubitfhtfa`, `modular-fence-post-xh0rah1iy` | Fab Standard | Verges, roadside dressing, barriers |
| Desert Plants (docjana) | `fab\desert-plants\` (FBX, 144 MB) | CC BY 4.0 | Cacti |
| Poly Haven rally-hdri | `polyhaven\rally-hdri\` (4K) | CC0 | kiara_3_morning + spruit_sunrise (Forest), qwantani_noon_puresky + goegap_road (Canyon), snowy_hillside_02 + snow_field + kloofendal_overcast_puresky (Snow) |
| Poly Haven rally-textures / rally-models | `polyhaven\rally-textures\`, `polyhaven\rally-models\` | CC0 | gravel_road, cracked_red_ground, red_laterite_soil_stones, red_sand, rock_face_03, snow_02; quiver_tree_02, shrub_01, namaqualand cliff/boulder, boulder_01, concrete_road_barrier |
| ambientCG Ice002, Ice004, Gravel023 | `ambientcg\...` | CC0 | Ice patches, gravel |
| Fonts Saira Condensed, Rajdhani | `fonts\...` | OFL | HUD |

### Launcher (FabVault53)

Vehicle Variety Pack (drivable AI bodies), City Sample Vehicles (Chaos reference), MW Landscape Auto
Material (5.3+), Project Nature Spruce Forest + conifer Bushes + Foliage Collection + Meadow Flowers,
Megascans European Hornbeam + Black Alder, Niagara Footstep VFX (dirt/mud/gravel/snow puffs for wheels),
Rural Australia, Landscapes Pack (CC BY, credit DigitalTris Studio), Racing Music Vol.1 (Personal $0),
Electric Dreams (large; PCG graphs only).

### Paid (purchased)

Rally Cars Pack ($29.99: 2 drivable rally cars, clean/dirty skins, replaces the template car), Vehicle
Wheel VFX ($13.99). Optional (not carted): Rally Cars Pack 2, Winter Environment.

Credits: "Desert Plants" by docjana (fab.com), CC BY 4.0.

## horror-escape

Style: late-Victorian scanned interiors; Old West VOL.1 furniture is 1880s and matches.

### On disk now

| Pack | Path | Licence | Replaces / serves |
|---|---|---|---|
| Megascans 4K surfaces | `fab\old-decorative-wallpaper-umridamn` (tint green for the damask), `old-wallpaper-ufimeaady`, `framed-wallpaper-ufsnadydy`, `wooden-floor-ucklejqdy`, `brick-wall-worn-sexkaitb` | Fab Standard | Generated wallpaper, oak, basement brick |
| Megascans props | `fab\interior-wall-panel-wboweczdw` (wainscot), `old-wooden-door-uflvddofa`, `wooden-cabinet-vmhlfbi` (hideable), `wooden-bookshelf-vmhndfu`, `wrinkled-tarp-vh2mee1` (attic sheets), `small-metal-valve-wdlnah1aw`, `rusty-metal-workbench-ukkiejiaw`, `old-candle-udlufhnqx` | Fab Standard | Geometry Script furniture and props |
| Poly Haven horror-models (25) | `polyhaven\horror-models\` | CC0 | GothicBed_01, GothicCabinet_01 (wardrobe), GothicCommode_01, gothic_coffee_table, vintage cabinet/drawers, nightstand, console, armchair, rocking chair, old_bed_frame, grandfather + mantel clocks (rigged), ornate_mirror_01, vintage_oil_lamp, Chandelier_01, brass candleholders, picture frame, radio, vintage_flashlight, suitcase, worn bookshelf, power_box_01 (fuse box, rigged), industrial pipes, caged light |
| Poly Haven horror-textures | `polyhaven\horror-textures\` | CC0 | decrepit_wallpaper, dark_wooden_planks, old_wood_floor, worn_plaster_wall, red_brick, damaged_concrete_floor, rusty_metal_02, raw_plank_wall (attic) |
| HDRIs | `polyhaven\horror-hdri\` (moonless_golf, creepy_bathroom), `polyhaven\night-hdri\` | CC0 | Window views, reflections |
| ambientCG WoodFloor064, Bricks023, Rust009, Metal047B | `ambientcg\...` | CC0 | Parquet, basement brick, rust, copper pipes |
| IM Fell English | `fonts\IMFellEnglish\` | OFL | Titles, notes, letters |

### Launcher (FabVault53)

Old West VOL.1 Interior Furniture + VOL.2/4/5/6, Free Furniture Pack, Cigar Room Environment (CC BY,
credit Hane Studios), Horror Props (CC BY, Bugrimov), **Whisper** (stalker creature, 16 anims),
Zombie Animation Pack, Killer Doll, Zombie Nurse, Monster with Book Head (CC BY), MoCap Online Free Pack,
Into Insanity Vol.1 + Grimytheus Vol.2 + Gothic Horror Music, Classical Music Box Collection + Free Thunder
Sounds (CC BY, Gregor Quendel), Modular Old Power Plant + Metro Maintenance (Personal $0: boiler, pipes,
fuse panels), Horror Ambient SFX + Essential Footsteps (Personal $0). Saloon Interior (Megascans, FBX
857 MB high tier) is in the library: download on request.

### Paid (purchased)

Modular Victorian House ($99.99: whole house shell), Victorian Interior Environment ($49.99). Optional:
Ghost Creature Anims.

## stealth

Style: realistic; warehouse / night courtyard / office.

### On disk now

| Pack | Path | Licence | Replaces / serves |
|---|---|---|---|
| Megascans props | `fab\wooden-pallet-vh1jeck`, `cardboard-boxes-pack-uewlfg2va`, `rusty-metal-shelf-vhtmaifaw`; `fab\wild-grass-vlkhcbxia` (L2 tall grass) | Fab Standard | Engine-shape crates/shelves, grass patches |
| SFX Essentials (InspectorJ) | `fab\sfx-essentials-free-sample\` | Fab Standard | Doors, foley, impacts |
| Poly Haven stealth-models (23) | `polyhaven\stealth-models\` | CC0 | steel_frame_shelves_01-03, rollershutter_door (dock), security_camera_01/02 (rigged), security_light, hand_truck, fluorescent lights, metal_office_desk, fire_alarm, wet-floor sign, air duct, utility box, cardboard box (L1/L3); street_lamp_01/02, large_iron_gate (side gate), chain-link fence, fire_hydrant, shrubs (L2) |
| Poly Haven stealth-textures | `polyhaven\stealth-textures\` | CC0 | hangar_concrete_floor, garage_floor, concrete_floor_painted, cobblestone_floor_01, patterned_paving |
| HDRIs | `polyhaven\stealth-hdri\` (courtyard_night, unfinished_office_night), `polyhaven\night-hdri\` | CC0 | L2/L3 lighting |
| ambientCG Asphalt033 | `ambientcg\Asphalt033\` | CC0 | Dock/courtyard asphalt |
| Fonts Rajdhani, Barlow Condensed, Share Tech Mono | `fonts\...` | OFL | HUD, keypad screens |

### Launcher (FabVault53)

Industry Props Pack 6, Factory Environment Collection (L1 shell, dock), City Park Environment Collection
(L2), Common Hazel (hedges), Modular Courtyard, Downtown West facades, Apartment Tech Props (L3 electronics),
City Street Props, Office Pack Vol.1 (CC BY, MeikWModels), City Sample Crowds (guards), Rogue Character
Model (thief, UE5 mannequin), Survival Character, Quantum Modular sample, Lyra, VanillaLoop Free Sample
Animation Set, MoCap Online pack, Free UI Soundpack, Free City & Nature Sounds (CC BY, Gregor Quendel),
Essential Footsteps + Metro Maintenance (Personal $0). Megascans Warehouse (UE 5.4+, FBX high 4.7 GB) is
in the library: download on request.

### Paid (purchased)

Modular Warehouse Interior ($39.99), DownTown Office ($79.99), Stealth Locomotion Animation Set ($29.99).

## island-survival

Style: photoreal tropical (Poly Haven Smuggler's Cove scans + Project Nature tropical + Tropical Jungle Pack).

### On disk now

| Pack | Path | Licence | Replaces / serves |
|---|---|---|---|
| Plant Series - Palm Tree (UPWARD) | `fab\free-game-ready-palm\` | CC BY 4.0 | Palm until the paid jungle pack lands |
| Poly Haven island-models (24) | `polyhaven\island-models\` | CC0 | Understory: fern_02, calathea, anthurium, pachira, bermuda grass, sorrel; shore: coast_rocks_01/02/03/05, coast_line_01, coastal_cliff_01/02, coast_land_rocks_02, sand_rocks_small_01; tree_stump_01; tools: wooden_axe, hatchet, machete; stone_fire_pit, wicker_basket_01, wooden_lantern_01, lambis_shell, modular_wooden_pier |
| Poly Haven island-textures | `polyhaven\island-textures\` | CC0 | coast_sand_01, coast_sand_rocks_02, damp_beach_sand_02, dark_rock_02 (volcanic), palm_tree_bark, bamboo_wall_02, rough_wood |
| Poly Haven island-hdri | `polyhaven\island-hdri\` (4K) | CC0 | kloofendal_43d_clear_puresky, spiaggia_di_mondello, umhlanga_sunrise, qwantani_night_puresky |
| ambientCG Ground093C, Ground095A, ThatchedRoof001A, Lava001 | `ambientcg\...` | CC0 | Dry/wet sand, thatch roofs, lava |
| game-icons, Barlow, Barlow Condensed, Caveat Brush | `gameicons\`, `fonts\...` | CC BY 3.0 / OFL | Inventory icons, HUD, journal |

Ocean: the engine's Water plugin (Edit > Plugins > Water; shoreline-spline Water Body Ocean, buoyancy
component for the raft) is the recommended base; nothing to download.

### Launcher (FabVault53)

Project Nature tropical Banana / Pandanus / Ground Plants, Light Foliage (Personal $0), ANIMAL VARIETY PACK
(crow, fox, deer, ...), Craft Resources Icons (REXARD), Survival Craft: Inventory, Modular Rural Cabins,
Automotive Beach Scene, Survival Character, Electric Dreams (cliffs/rocks/PCG).

### Added for the island-survival request (2026-10-11)

| Need | On disk | Launcher (FabVault53) | Licence |
|---|---|---|---|
| Wolf / dog (night pack) | | **ANIMAL VARIETY PACK**: Wolf (10k tris, 4K, 26 anims), also Fox, Deer stag/doe, Pig (20 anims), Crow | Fab Standard |
| Wild boar | | ANIMAL VARIETY PACK **Pig** as a boar base (re-texture, add tusks); paid Realistic Boar in the cart | Fab Standard |
| Palms, ground cover, beach grass | `fab\alexandra-palm-ukgkcilia` (Megascans), `fab\free-livistona-chinensis-fan-palm`, `fab\realistic-palm-model`, `fab\free-game-ready-palm`, `fab\monstera-b02`, `fab\monstera-b03`, `fab\ribbon-grass-tbdpec3r` | Project Nature tropical Banana / Pandanus / Ground Plants, Light Foliage | Megascans Fab Standard; others CC BY 4.0 (credits in catalog.jsonl) |
| Driftwood, shells, campfire | `fab\tree-branch-pcsvq`, `fab\real-time-ready-seashells-scan`, `fab\turret-shell-free-model`, `fab\campfire-uenpfeifa`; Poly Haven lambis_shell, stone_fire_pit | | Fab Standard / CC BY / CC0 |
| Castaway character | | Survival Character (Arberry, UE5 mannequin), Adventure Character + Pirate (Bugrimov, 4.7-4.9 rated) | Fab Standard |
| Volcanic / basalt rock, sea cave | `fab\small-basalt-column-sample` (CC BY), `fab\updraft-art-icelandic-biome-pack-sampler`, `fab\nordic-beach-rock-formation-vflrejtfa`; Poly Haven coastal_cliff_01/02, coast_rocks, dark_rock_02 | **Soul: Cave** (Epic sample, UE 5.3: cave interior kit) | |
| Audio | `fab\forest-sounds` (CC BY: wood split/creak, leaves, wind, water) | Procedural Sea Waves + Procedural Wind (MetaSound, Personal $0), Essential Ambience SFX, 50 Free Game Sounds, Free Game SFX Starter (65) + Sampler (33), Animal Sound Effect Pack, Auto Footsteps Utility, Footsteps Mini (CC BY), Acoustic Guitar Music Pack, Fantasy Music and Ambience freebie | Fab Standard / CC BY |

Not free: Megascans Icelandic porous rocks, coconuts, eroded logs ($2.99 Personal each). freesound CC0
surf/jungle/boar/dog clips need a login; Sonniss GDC bundles block scripted downloads (403).

### Paid (purchased)

Tropical Jungle Pack ($49.99: palms + jungle, rated 4.9 from 126), Survival construction pack ($13.99:
building pieces), Survival Tools ($19.99), Atlantic Ghost Crab ($12.99), Critters Vol.2 Crows & Seagulls
($14.99), Realistic Boar ($69.99).

---

## Paid shortlist: total in the cart

21 items, **$750.79** (Personal tier, before tax), all UE 5.3-compatible. **Purchased by the user on 2026-10-11** (all 21 now owned; only Stylized Human Siege Weapons has a browser FBX, on disk at fab\stylized-human-siege-weapons\; the rest come through the Launcher, see LAUNCHER-CHECKLIST.md "Purchased"):
liaozhai-night $59.97, tower-defense $89.97, siege-catapult $74.98, rally-racer $43.98,
horror-escape $149.98, stealth $149.97, island-survival $181.94. Optional extras not carted: about
+$380 (Traditional Chinese Style Park, Stylized Fantasy Creatures Bundle, Rally Cars Pack 2, Winter
Environment, Ghost Creature Anims).

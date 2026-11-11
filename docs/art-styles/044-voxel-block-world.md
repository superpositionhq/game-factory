# Voxel block world

Reference works: Minecraft.

## References

- *Minecraft* (2011), Mojang Studios, video game. https://en.wikipedia.org/wiki/Minecraft
- *Dragon Quest Builders* (2016), Square Enix, video game. https://en.wikipedia.org/wiki/Dragon_Quest_Builders
- *Terraria* (2011), Re-Logic, video game. https://en.wikipedia.org/wiki/Terraria
- *Minecraft Dungeons* (2020), Mojang Studios and Double Eleven, video game. https://en.wikipedia.org/wiki/Minecraft_Dungeons

## Visual definition

- **Shape language and proportions:** Everything is made of 1 m cubes on a grid. Characters are a few rectangular boxes. No curves anywhere; circles are stepped.
- **Line and outline:** No outline.
- **Shading model:** Each cube face gets a fixed brightness by direction (top brightest, two side levels, bottom darkest) plus simple corner ambient occlusion.
- **Palette:** `#7cb342` `#8d6e4a` `#7f7f7f` `#4fa3e0` `#c2b280` `#3b6e2a` `#d9d9d9` `#5a3d28`. Natural block colours: grass green, dirt brown, stone grey, sand, water blue.
- **Lighting:** Uniform sky light; block light levels fall off in steps.
- **Texture and surface:** 16x16 px textures per block face, unfiltered, with noisy pixel variation.
- **Atmosphere and post-processing:** None. Distance fog to sky colour.
- **Camera and framing:** First-person, 70 degree field of view.
- **UI and typography:** Square pixel-art panels in stone grey `#7f7f7f` with a one-pixel light edge and a one-pixel dark edge; a hotbar of square slots holds 16x16 px item icons, above rows of pixel hearts and food icons. Text is a blocky pixel sans in white with a dark drop shadow, and item counts are small digits in the slot corners.
- **VFX and motion:** Particles are tiny flat squares cut from the block textures: break fragments, smoke puffs, hit stars. A struck creature flashes red and is knocked back. Animation is stiff, with box limbs that swing on simple pivots and never bend or squash.

## Fits

- **Genres:** `survival-craft`, `exploration`, `simulation`, `action-adventure`, `rpg`, `tower-defense`
- **Moods:** calm, playful, adventurous
- **Settings:** blocky wilderness, underground mines, village and farmland, cube-built castle

## Unreal recipe

### Assets

Build the world from unit cubes on a 100 cm grid. Generate terrain chunks by script (Geometry Script or Blender): merged cube faces only where exposed, one static mesh per chunk, UVs pointing into a block atlas of 16x16 px tiles. Bake corner ambient occlusion into vertex colour at build time, darkening each vertex by the number of solid neighbours (0 to 3). Characters and creatures are a few boxes each, with rigid limbs on a simple skeleton. Store packs do not fit; only their colours can be sampled when painting the 16x16 tiles by script, with per-pixel noise of a few percent.

### Materials

`M_Voxel`: Unlit. Base is the atlas sample (Filter Nearest, NoMipmaps, Texture Group 2D Pixels (Unfiltered)). Multiply by a face-direction factor from VertexNormalWS: top 1.0, north-south sides 0.8, east-west sides 0.6, bottom 0.5. Multiply again by vertex-colour AO and by a stepped block-light term, `floor(Light * 15) / 15`, supplied per vertex or per instance through Custom Primitive Data. A Masked variant handles leaves and glass edges; water is a Translucent Unlit instance in `#4fa3e0`. Nothing is bevelled, glossy or studded, which keeps it apart from plastic brick styles.

### Lighting and atmosphere

Lumen off, no Directional Light shadows needed; face shades are fixed. An optional Directional Light with Virtual Shadow Maps may affect characters only through Lighting Channels. Exponential Height Fog with Fog Inscattering Color set to the sky colour `#4fa3e0`, start distance near the chunk draw limit, Volumetric Fog off. A sky dome with an Unlit flat gradient. Manual exposure for steady daylight.

### Post-processing

Full resolution, `r.AntiAliasingMethod=1` (FXAA) or 0; TSR softens texels. Tone Curve Amount 0. Bloom, grain, vignette, fringe, depth of field, Ambient Occlusion Intensity and Motion Blur Amount 0. No post materials. Camera field of view 70 degrees, first person.

### UI and effects

Panels are Box brushes built from a small pixel texture: `#7f7f7f` fill, one-pixel light edge top-left, one-pixel dark edge bottom-right, scaled by whole multiples. A hotbar of square slots with 16x16 item icons, hearts and food in rows above. Text in Pixelify Sans or Silkscreen, white with a dark Slate shadow offset of one scaled pixel; stack counts sit bottom-right of each slot. Niagara: sprite particles that are 4x4 px sub-rectangles of the broken block's atlas tile (random SubUV offset), 8 to 16 per break, gravity on, lifetime 0.5 s, no fade or rotation. A struck creature gets a red multiply for 0.2 s through a material parameter.

## Do / Do not

Do:

- Build everything from unit cubes on a grid.
- Use 16x16 unfiltered textures.
- Shade faces by direction with fixed levels.
- Add per-vertex corner ambient occlusion.

Do not:

- Do not use smooth plastic bricks with studs; that reads as `052`.
- Do not use 2D sprite tiles with three colours each; that reads as `042`.
- Do not add vertex wobble and affine warping; that reads as `036`.
- Do not use rounded or bevelled geometry.

## Nearest styles

- `052` Brick toy: `052` is smooth, clean, glossy plastic with studs; this style has noisy pixel textures on every cube face and no studs or gloss.
- `042` NES 8-bit tile: `042` is flat, unlit 2D tiles and sprites in a few saturated colours; this style is a 3D perspective world with three face shades and many natural colours.
- `036` PS1 low-poly wobble: `036` is dark, with wobbling low-poly models, warped textures and soft light blended across each polygon; this style is in bright daylight, with steady cubes and one fixed shade per face direction.

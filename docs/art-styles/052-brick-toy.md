# Brick toy

Reference works: The Lego Movie.

## References

- *The Lego Movie* (2014), Animal Logic (Phil Lord and Christopher Miller), animated film. https://en.wikipedia.org/wiki/The_Lego_Movie
- *Lego Star Wars: The Skywalker Saga* (2022), Traveller's Tales, video game. https://en.wikipedia.org/wiki/Lego_Star_Wars:_The_Skywalker_Saga
- *Lego Builder's Journey* (2019), Light Brick Studio, video game. https://en.wikipedia.org/wiki/Lego_Builder's_Journey
- *The Lego Batman Movie* (2017), Animal Logic (Chris McKay), animated film. https://en.wikipedia.org/wiki/The_Lego_Batman_Movie

## Visual definition

- **Shape language and proportions:** Everything is assembled from a small set of modular bricks on a stud grid (8 mm pitch, 9.6 mm brick height, plates at one third). Curves are stepped. Figures have cylindrical heads and C-shaped hands.
- **Line and outline:** No drawn outline. Thin dark seams appear between bricks.
- **Shading model:** Smooth glossy plastic with sharp highlights and soft reflections.
- **Palette:** `#d01012` `#0055bf` `#f2cd37` `#237841` `#ffffff` `#1b2a34` `#a0a5a9`. A fixed set of solid plastic colours: red, blue, yellow, green, white, black and greys.
- **Lighting:** Bright studio or macro-photography lighting with soft shadows.
- **Texture and surface:** Clean plastic. At macro scale: fine scratches, slight dents, mould marks and a logo bump on each stud.
- **Atmosphere and post-processing:** Macro depth of field; animation stepped like stop motion.
- **Camera and framing:** Macro, low among the bricks, 50 to 100 mm equivalent with a thin focus plane.
- **UI and typography:** Panels are flat plastic plates with studded rims, buttons are round studs or smooth tiles, and icons look like decals printed on a tile. Type is a bold rounded sans like toy-box lettering. Counters are chunky white or yellow numerals beside a stud icon, on red, blue and black panels.
- **VFX and motion:** Everything breaks into loose parts: destroyed objects burst into bouncing bricks and studs, and smoke, fire and water are built from small bricks and transparent pieces. Animation is stepped like stop motion, with stiff-jointed figure poses and objects that assemble brick by brick.

## Fits

- **Genres:** `action-adventure`, `platformer`, `puzzle`, `racing`, `vehicle-combat`
- **Moods:** playful, comic, energetic
- **Settings:** toy city, pirate island, space base, medieval castle

## Unreal recipe

### Assets

Build a brick kit by script in Blender background mode: about 20 part types (1x1 to 2x8 bricks, plates at one third height, slopes, tiles, round studs, minifigure parts) at true ratios, 8 mm pitch to 9.6 mm height, scaled uniformly for gameplay. Bevel every edge slightly and add studs with a raised logo bump on all exposed tops. Assemble scenery from kit parts with Instanced Static Meshes snapped to the stud grid; curves are stepped. A store pack can serve only as a voxelisation source: sample its volume and emit bricks. Figures have cylinder heads, C-shaped hands and rigid joints.

### Materials

`M_Plastic`: Default Lit, one `BrickColour` parameter restricted to `#d01012`, `#0055bf`, `#f2cd37`, `#237841`, `#ffffff`, `#1b2a34`, `#a0a5a9`, supplied through Custom Primitive Data so instances share one material. Roughness 0.15 to 0.25 with a fine scratch map adding plus or minus 0.05; a faint scratch and mould-mark normal. Specular 0.5. Clear Coat is unnecessary. Transparent parts use a Thin Translucent instance. No painted or weathered textures; decals printed on tiles are small DBuffer decals or a second UV texture. Seams between bricks come from geometry bevels plus ambient occlusion, not drawn lines.

### Lighting and atmosphere

Lumen GI and Lumen reflections on; glossy plastic needs clean reflections, so add a studio cubemap to the Sky Light and one or two large Rect Lights whose shapes show as sharp highlights. Virtual Shadow Maps with soft sources, Contact Shadows on for the stud gaps. No fog. Manual exposure, bright.

### Post-processing

Macro depth of field: 50 to 100 mm, f/2 to f/2.8, thin focus plane placed on the hero figure. TSR on. Bloom 0.3, Vignette 0.2, Film Grain 0.05, Ambient Occlusion Intensity 0.7 with small radius to darken seams. Motion Blur Amount 0. No post materials. Tick figure animation at 12 to 15 fps from C++ for stop-motion stepping.

### UI and effects

Panels are flat plates with a studded rim (9-slice Box brush rendered from the kit) in red, blue or black; buttons are round studs or smooth tiles with a glossy highlight image. Text in Baloo 2 Bold or Fredoka Bold, white or `#f2cd37`. Counters are chunky numerals beside a stud icon. Niagara uses mesh renderers with kit parts only: a destroyed object bursts into 20 to 60 of its own bricks with collision and bounce, lifetime 2 s; fire is stacked transparent orange and yellow 1x1 pieces flickering by swap; smoke is grey round bricks rising in steps; water is transparent blue studs.

## Do / Do not

Do:

- Snap every part to the stud grid.
- Put studs on all exposed tops.
- Use a fixed small set of solid colours.
- Use glossy plastic with macro depth of field.

Do not:

- Do not use plain cubes with pixel textures; that reads as `044`.
- Do not use freeform smooth toy shapes; that reads as `057`.
- Do not add painted or weathered textures.
- Do not use matte primaries without studs or gloss; that reads as `098`.

## Nearest styles

- `044` Voxel block world: bricks here are smooth, glossy, single-colour plastic with studs on top; `044` is plain cubes with pixel-art textures and matte faces, each side a flat step lighter or darker.
- `057` Toy-diorama tilt-shift: forms here are assembled from studded bricks in a small set of strong solid plastic colours; `057` has freeform rounded moulded shapes in a wider, softer range of colours.
- `006` Glossy ink-splat pop: plastic here is clean and plain, in a few solid toy colours; `006` covers surfaces in wet, glittering ink splats and neon paint.

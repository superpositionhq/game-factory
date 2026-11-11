# Expressionist painted set

Reference works: The Cabinet of Dr. Caligari.

## References

- *The Cabinet of Dr. Caligari* (1920), Robert Wiene (sets by Hermann Warm, Walter Reimann and Walter Rohrig), silent film. https://en.wikipedia.org/wiki/The_Cabinet_of_Dr._Caligari
- *Metropolis* (1927), Fritz Lang, silent film. https://en.wikipedia.org/wiki/Metropolis_(1927_film)
- *The Golem: How He Came into the World* (1920), Paul Wegener and Carl Boese, silent film. https://en.wikipedia.org/wiki/The_Golem:_How_He_Came_into_the_World
- *Vincent* (1982), Tim Burton, stop-motion short film. https://en.wikipedia.org/wiki/Vincent_(1982_film)

## Visual definition

- **Shape language and proportions:** Stage sets with no right angles: walls lean, doors are trapezoids, windows are jagged shards, chimneys and lamp posts bend, paths zig-zag. Flat scenery panels with forced perspective.
- **Line and outline:** Bold painted black lines on set surfaces: outlines of windows, spiky grass, radiating floor stripes.
- **Shading model:** Light and shadow are painted on the sets as hard-edged black and white shapes; real lighting is flat and frontal. Faces are white with dark eye make-up.
- **Palette:** `#0c0c0c` `#f1ead6` `#6b6b63` `#2f3a35` `#b5a878` `#3a2f2a`. Black, white and grey, optionally tinted per scene in one colour (sepia, green or blue) like tinted film stock.
- **Lighting:** Flat front light; the drama comes from painted shadow wedges and painted light pools.
- **Texture and surface:** Painted cloth flats and plaster with visible rough brush strokes; film scratches and flicker.
- **Atmosphere and post-processing:** Monochrome with a single tint, iris vignette, grain, flicker, low frame rate.
- **Camera and framing:** Static, frontal, theatrical framing; often an iris mask.
- **UI and typography:** Silent-film intertitle cards: black panels with a jagged hand-painted white border, text in a crooked, angular hand-lettered display face whose letters lean and vary in size. Counters use the same uneven painted numerals in bone white `#f1ead6`, icons are spiky painted silhouettes, and the whole UI takes the scene's single tint.
- **VFX and motion:** Effects are painted or theatrical: jagged white starburst shapes on impact, flat cut-out smoke, iris-in and iris-out transitions, film scratches and flicker. Characters move like stage actors at a low frame rate, creeping along walls with long held poses and sudden jerky gestures.

## Fits

- **Genres:** `survival-horror`, `detective-mystery`, `stealth`, `puzzle`, `exploration`
- **Moods:** uneasy, feverish, theatrical
- **Settings:** crooked hill town, asylum, travelling fairground, rooftops at night

## Unreal recipe

### Assets

Build the sets; no store architecture is crooked enough. A Blender script makes thin scenery flats and simple volumes, then shears and tapers each one with a lattice so no wall is vertical and no opening is rectangular: trapezoid doors, shard windows, bent chimneys, zig-zag paths. Force perspective by shrinking far flats. Characters can come from a library: realistic humans in dark period costume, faces re-textured chalk white with black eye sockets.

### Materials

Sets use an Unlit master, `M_PaintedFlat`, so real light cannot model them. Its texture is painted per flat by a Pillow script: bone `#f1ead6` and grey `#6b6b63` grounds, hard-edged black `#0c0c0c` shadow wedges, white light pools, thick outlines round windows, spiky grass strokes and radiating floor stripes. Multiply by a coarse brush-stroke greyscale so the paint looks rough on cloth. Characters stay Default Lit, receiving only the flat front light, with roughness 1 and no specular.

### Lighting and atmosphere

Lumen off. One Directional Light aimed along the camera axis with Cast Shadows disabled, plus a white Sky Light, gives actors even frontal light with no modelling. No fog, no sky, no volumetrics. Shadows on the walls exist only as paint. Manual exposure. Camera locked off and frontal for each set.

### Post-processing

Chain at Scene Color After Tonemapping, in order:

1. Desaturation, then a two-point gradient map to the scene tint: black to sepia `#b5a878`, green `#2f3a35` or brown `#3a2f2a` range, one tint per scene.
2. Film damage: vertical scratch texture panned at random offsets, dust specks, and brightness flicker of 5 percent stepped at 16 Hz.
3. Iris: a circular mask with a soft 40 px edge, black outside, radius driven from C++ for iris-in and iris-out.

PPV: Film Grain Intensity 0.7, Contrast 1.2, Bloom 0, fringe 0, depth of field off, Motion Blur Amount 0. Simulate a low frame rate by ticking character animation at 12 to 16 Hz (Update Rate Optimizations or a fixed pose-snapshot interval); do not cap the game's frame rate. No Sobel pass: the black lines are painted on the sets, not detected.

### UI and effects

Intertitle cards: full-screen black Image with a jagged white painted border texture (Box brush with wide margins), text centred in Pirata One with per-letter Render Transform shear and size variation of 10 percent, colour `#f1ead6`. Counters reuse the face. The whole UI sits in a Retainer Box using the same tint and flicker material.

Niagara: impact starburst as one flat jagged white sprite held for 3 frames; smoke as two flat grey cut-out cards rising with stepped motion; no soft particles. Scene changes use the iris mask, closing in 0.8 s.

## Do / Do not

Do:

- Lean and skew every wall and opening.
- Paint shadows and light shapes onto the sets.
- Keep real lighting flat and frontal.
- Tint the monochrome image with one colour.

Do not:

- Do not use real hard-light photography on normal architecture; that reads as `068`.
- Do not use 3D puppets with smooth shading and colour accents; that reads as `049`.
- Do not threshold to two values with a colour spot; that reads as `069`.
- Do not fragment objects into overlapping transparent planes; that reads as `078`.

## Nearest styles

- `068` Film noir hard light: this style paints its shadows and bold black lines onto crooked flat sets under flat front light; `068` photographs normal, upright architecture with real hard light, real cast shadows and no drawn lines.
- `049` Gothic stop-motion puppet: this style is tinted black and white with flat painted scenery and live actors in white make-up; `049` shows solid miniature puppets and sets in blue-violet with orange or green accents, lit by real stage light with smooth shading.
- `078` Analytic cubist facets: here objects stay whole, only leaning and skewed, with painted light and shadow shapes on them; `078` breaks each object into overlapping ochre-grey facets seen from several viewpoints.

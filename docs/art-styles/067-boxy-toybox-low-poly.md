# Boxy toybox low-poly

Reference works: Katamari Damacy.

## References

- *Katamari Damacy* (2004), Namco, video game. https://en.wikipedia.org/wiki/Katamari_Damacy
- *We Love Katamari* (2005), Namco, video game. https://en.wikipedia.org/wiki/We_Love_Katamari
- *Noby Noby Boy* (2009), Namco Bandai Games (Keita Takahashi), video game. https://en.wikipedia.org/wiki/Noby_Noby_Boy
- *Wattam* (2019), Funomena (Keita Takahashi), video game. https://en.wikipedia.org/wiki/Wattam

## Visual definition

- **Shape language and proportions:** Everyday objects reduced to naive boxy models: a cow is a box with four box legs, a person is a rectangular block with a cylinder head, trees are a cone on a stick. Hundreds of small objects scattered densely.
- **Line and outline:** No outline.
- **Shading model:** Simple two- or three-step shading with little contrast. Objects look evenly lit.
- **Palette:** `#ff6fae` `#ffd400` `#3ec1ff` `#7be04a` `#ff8a1f` `#ffffff` `#8a4fff` `#5a3a2a`. Many bright candy colours at once: pink, yellow, sky blue, lime, orange, with white and brown.
- **Lighting:** Flat, bright, shadowless; small blob shadows only.
- **Texture and surface:** Simple flat decals: stripes, dots, checks, faces made of two dots and a line, product labels as plain rectangles.
- **Atmosphere and post-processing:** None. Rainbow or flat pastel backgrounds.
- **Camera and framing:** Low third-person behind a rolling ball, wide angle; scale changes from tabletop to city.
- **UI and typography:** Round bubbles, rainbow arcs and thick circular gauges in candy fills, with icons that are tiny boxy objects or faces made of two dots and a line. Text is a chunky rounded sans mixed with wobbly hand-drawn lettering, in white `#ffffff` or brown `#5a3a2a` on pink, yellow and sky blue; counters are big numerals that bounce when they change.
- **VFX and motion:** Flat stars, hearts, sparkles and plain puffs pop out on pickups and bumps, with no smoke or realistic debris. Animation is stiff and toy-like: objects wobble, hop and spin as whole pieces, characters waddle through a few rigid poses, and everything pops in with squash and stretch.

## Fits

- **Genres:** `puzzle`, `platformer`, `simulation`, `sports`, `racing`, `exploration`
- **Moods:** playful, silly, cheerful
- **Settings:** cluttered living room, suburban town, toy city, playground

## Unreal recipe

### Assets

Hundreds of small everyday objects, each made of 2 to 10 boxes, cylinders and cones. Generate the whole catalogue from a Python table (object name, list of primitives with size, offset and colour) through Geometry Script or Blender, baked to static meshes with box collision. Keep edges square with a 2 mm bevel; do not round or subdivide. Store props carry too much form; use them only as a size reference. Characters are a block body and cylinder head on a five-bone rig with rigid weights, one bone per piece, so limbs never bend. Scatter with instanced static meshes from a placement script.

### Materials

`M_Toy` is Default Lit, roughness 1, specular 0, metallic 0, with a colour parameter chosen from `#ff6fae`, `#ffd400`, `#3ec1ff`, `#7be04a`, `#ff8a1f`, `#ffffff`, `#8a4fff`, `#5a3a2a`. PerInstanceRandom picks among three palette entries per mesh type. Add 0.35 of the base colour to Emissive, which compresses light-to-shade contrast to two or three gentle steps. Decals come from one 1024 px atlas drawn by Pillow: stripes, dots, checks, two-dot-and-line faces, blank label rectangles; sample it through a second UV channel with flat alpha, no normal.

### Lighting and atmosphere

Lumen off; `r.DynamicGlobalIlluminationMethod=0`. A Sky Light with a white cubemap provides nearly all light, plus one Directional Light at intensity 2 with Cast Shadows disabled. Objects get blob shadows instead: a dark translucent disc decal or flat quad under each mover, 40 percent opacity. No Sky Atmosphere and no fog; the backdrop is a dome with an Unlit rainbow band or a flat pastel. Manual exposure.

### Post-processing

Tone Curve Amount about 0.3 and Saturation 1.15 so candy colours stay loud. Bloom 0, grain 0, vignette 0, fringe 0, Ambient Occlusion Intensity 0, Motion Blur Amount 0. Depth of field must stay off: the whole frame is sharp from near to far. No outline or banding material. TSR at 100 percent.

### UI and effects

Circular and pill-shaped Rounded Box brushes in pink, yellow and sky blue; a thick ring progress gauge made from a UI material using a radial mask; a rainbow arc image across the top. Text in Baloo 2 ExtraBold, with headings in Patrick Hand for the wobbly voice, white with a 3 px brown `#5a3a2a` font outline. Counters bounce: scale 1 to 1.4 to 1 over 0.2 s on every change.

Niagara: flat star, heart and sparkle sprites with opaque masked materials, 6 to 12 per pickup, popping to full size in 0.05 s, spinning, gone by 0.5 s. Bump puffs are three white circles. No smoke, debris or additive glow.

## Do / Do not

Do:

- Reduce every object to a few boxes and cylinders.
- Scatter objects densely.
- Use many bright colours with flat lighting.
- Use stripe, dot and simple-face decals.

Do not:

- Do not round and gloss the forms with tilt-shift blur; that reads as `057`.
- Do not use sharp light-and-shadow toon shading on smooth caricatured characters; that reads as `003`.
- Do not use irregular triangulated terrain; that reads as `066`.
- Do not limit colours to three primaries with geometric purity; that reads as `098`.

## Nearest styles

- `003` Flat-shape ocean toon: `003` has smooth curved caricature characters with crisp toon shadows in a sea-and-sky colour scheme; this style has crude boxy objects, almost no shadow and candy colours everywhere.
- `098` Bauhaus primary geometry: `098` uses pure circles, squares and triangles in red, yellow and blue with black and white, in sparse ordered layouts; this style crowds the frame with naive boxy objects in every candy colour.
- `057` Toy-diorama tilt-shift: `057` has rounded glossy toy forms with soft shading and a blurred top and bottom of frame, like a miniature photograph; this style is matte, boxy and sharp across the whole frame.

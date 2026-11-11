# Flat-shape ocean toon

Reference works: The Legend of Zelda: The Wind Waker.

## References

- *The Legend of Zelda: The Wind Waker* (2002), Nintendo EAD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_The_Wind_Waker
- *The Legend of Zelda: Phantom Hourglass* (2007), Nintendo EAD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Phantom_Hourglass
- *The Legend of Zelda: Spirit Tracks* (2009), Nintendo EAD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Spirit_Tracks
- *Oceanhorn: Monster of Uncharted Seas* (2013), Cornfox & Bros., video game. https://en.wikipedia.org/wiki/Oceanhorn:_Monster_of_Uncharted_Seas

## Visual definition

- **Shape language and proportions:** Strong caricature: large heads, large eyes, short limbs. Objects are reduced to a few bold shapes with sharp tapered points (wave crests, flames, smoke curls).
- **Line and outline:** No outlines. Shapes separate by colour contrast alone.
- **Shading model:** Two bands with a razor-sharp boundary. No specular, no gradient inside a band.
- **Palette:** `#1f8fd6` `#6fd0f0` `#ffffff` `#5cc04a` `#f2d15c` `#e8553d` `#2a5e2e`. Saturated sea blue, white, grass green and a few warm accents. Shadows are a darker, more saturated version of the base colour.
- **Lighting:** One sun; the terminator is the only shading feature. Cast shadows are simple dark blobs.
- **Texture and surface:** Almost none. Surfaces are flat colour, with at most a few large painted shapes (a stripe, a swirl).
- **Atmosphere and post-processing:** None apart from clear sky gradient. Effects (smoke, explosions, water foam) are solid white or coloured stylised shapes.
- **Camera and framing:** Medium-wide, slightly above the character, bright horizon line visible.
- **UI and typography:** Chunky rounded panels and buttons in flat sea blue and white, with no border line or bevel. Icons are bold two-colour shapes and text is a friendly rounded bold sans. Counters are large white numerals on a flat dark-blue backing shape.
- **VFX and motion:** Smoke is solid curling swirls, explosions are flat star and ring shapes in white, yellow and red, and defeated enemies burst into a puff of coloured cloud. Animation is bouncy, with strong squash and stretch and big readable expressions.

## Fits

- **Genres:** `action-adventure`, `exploration`, `platformer`, `puzzle`, `tower-defense`
- **Moods:** cheerful, breezy, playful
- **Settings:** island archipelago, open sea, seaside village

## Unreal recipe

### Assets

Most models are better built from scratch here. In Blender background mode, model islands, boats, barrels and huts from 3 to 6 bold primitives each, with tapered points on wave crests, flames and smoke curls, and smooth normals throughout. If a pack is used, delete every texture map, assign one palette colour per material slot and decimate fine detail. For rigged characters, scale head and hand bones up and shorten limb bones to reach caricature proportions.

### Materials

`M_FlatToon`, Unlit. The shadow colour is derived from the base colour parameter by lowering value 35 percent and raising saturation, so shade is never grey. Sun direction comes from a Material Parameter Collection updated in C++. Shading is `Step(0, dot(VertexNormalWS, SunDir))` with no smoothing, which gives the one-pixel terminator. No specular term, no Fresnel, no gradient. An optional mask texture parameter places one large painted shape (a stripe or swirl) in a second flat colour. Water is the same master with a Panner-driven white foam mask cut by Step. Character cast shadows are blob decals: a dark ellipse DBuffer decal under each actor.

### Lighting and atmosphere

Scene lights do not affect Unlit surfaces, so keep the level cheap: Lumen off for both GI and reflections, no Sky Light, no fog of any kind. The sky is a dome mesh with an Unlit two-colour vertical gradient from `#1f8fd6` to `#6fd0f0` and solid white cloud meshes.

### Post-processing

Set Tone Curve Amount 0 and Expand Gamut 0, Manual exposure, Bloom Intensity 0, grain 0, vignette 0, Scene Fringe Intensity 0, Ambient Occlusion Intensity 0, no depth of field, Motion Blur Amount 0. There is no outline pass; adjacent surfaces must differ in hue or value. Anti-aliasing is FXAA (`r.AntiAliasingMethod=1`), which keeps the terminator crisp where temporal methods would smear it.

### UI and effects

Buttons and panels are Rounded Box brushes with large corner radius, flat `#1f8fd6` or white, no outline and no bevel. Text is Fredoka Bold or Baloo 2; counters are large white numerals on a dark-blue rounded backing shape. Niagara uses mesh renderers more than sprites: smoke is a solid white curl mesh that scales up and shrinks over 0.6 s, explosions are flat star and ring meshes in white, `#f2d15c` and `#e8553d` popping over 0.3 s, and a defeated enemy bursts into 6 to 8 round cloud meshes. All particle materials are Unlit and opaque or Masked.

## Do / Do not

Do:

- Keep the band boundary one pixel sharp.
- Use colour contrast to separate shapes.
- Make effects from solid stylised shapes.
- Keep shadows saturated, not grey.

Do not:

- Do not add outlines; that reads as `015` or `004`.
- Do not add painted gradients or haze; that reads as `002`.
- Do not use smooth Lambert shading; that reads as `037`.
- Do not add blocky patterned stickers on boxy shapes; that reads as `067`.

## Nearest styles

- `002` Painterly open-air cel: this style keeps each surface one flat vivid colour under clear air; `002` paints soft gradients and brush patches and fades distance into pale blue haze.
- `067` Boxy toybox low-poly: this style has smooth rounded caricature forms with two sharp tone steps and almost no surface pattern; `067` builds everything from boxes and covers them with stripes, dots and labels in many more colours.
- `015` Two-tone fighting-anime cel: this style has no line at all and separates shapes by colour; `015` inks every silhouette in black and adds hard highlight shapes on hair and metal.

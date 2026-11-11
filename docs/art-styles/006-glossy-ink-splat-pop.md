# Glossy ink-splat pop

Reference works: Splatoon.

## References

- *Splatoon* (2015), Nintendo EAD, video game. https://en.wikipedia.org/wiki/Splatoon_(video_game)
- *Splatoon 2* (2017), Nintendo EPD, video game. https://en.wikipedia.org/wiki/Splatoon_2
- *Splatoon 3* (2022), Nintendo EPD, video game. https://en.wikipedia.org/wiki/Splatoon_3
- *De Blob* (2008), Blue Tongue Entertainment, video game. https://en.wikipedia.org/wiki/De_Blob

## Visual definition

- **Shape language and proportions:** Stylised teen characters with large heads; urban props with rounded, toy-like simplification. Ink splats are thick, blobby pools with raised edges.
- **Line and outline:** No outlines.
- **Shading model:** Smooth PBR-like shading. Ink is glossy with sharp bright specular highlights; base surfaces are matte.
- **Palette:** `#f02d7d` `#19d719` `#603bff` `#ff8a00` `#1ad6c5` `#2b2b33` `#f5f5f0`. Two opposing neon ink colours (for example pink against green) covering neutral grey concrete and white.
- **Lighting:** Bright overcast-sun mix with a clear environment reflection in the ink.
- **Texture and surface:** Base surfaces have simple material detail (concrete speckle, painted metal). Ink has glitter flecks and a visible thickness.
- **Atmosphere and post-processing:** Light bloom on ink highlights; colours stay clean.
- **Camera and framing:** Third-person, slightly above, 35 mm equivalent.
- **UI and typography:** Sticker-like panels tilted off axis with rounded, wobbly edges, in the two ink colours on dark grey (`#2b2b33`) or white. Type is a chunky rounded display face with a hand-cut look, and icons are flat splat-shaped badges. Counters are big bold numerals that bounce when they change.
- **VFX and motion:** Ink flies as thick glossy blobs and droplets that land as splats with a raised rim; hits burst in the attacker's ink colour with glitter flecks. Animation is quick and bouncy, with squash and stretch on characters and wobble on ink.

## Fits

- **Genres:** `third-person-shooter`, `sports`, `platformer`, `top-down-shooter`, `puzzle`
- **Moods:** playful, energetic, upbeat
- **Settings:** city plaza, skate park, shopping district, rooftop arena

## Unreal recipe

### Assets

Urban packs with rounded, toy-like props fit. Keep realistic base surfaces but simplify them: halve normal map strength, replace albedo detail with plain concrete speckle or painted metal in `#2b2b33` to `#f5f5f0`, and push Roughness to 0.8 or above. Ink is built from scratch: a script generates 8 to 12 splat masks (round blobs with satellite drops) and a matching height map with a raised rounded rim.

### Materials

Two Default Lit masters with opposite finishes. `M_Base` is matte, as above. `M_Ink` is Clear Coat: base colour is one of the two team hues (for example `#f02d7d` against `#19d719`), Roughness 0.08, Clear Coat 1, Clear Coat Roughness 0.03, with the splat height map converted to a normal so the rim catches a sharp highlight. Glitter comes from a high-frequency noise texture thresholded with Step and added to Emissive at low strength, offset by CameraVectorWS so flecks sparkle as the view moves. Ground coverage is painted at run time into a render target by C++; `M_Base` samples that target (world-aligned UVs) and lerps to the ink layer's colour, roughness and normal, with the mask edge sharpened by SmoothStep to give a thick pool outline. Static dressing uses DBuffer decals from the splat set.

### Lighting and atmosphere

Lumen GI and Lumen reflections on; the mirror-like ink needs a real environment. Directional Light at moderate intensity with Source Angle 2, and a strong Sky Light (Real Time Capture) with Sky Atmosphere and Volumetric Cloud for an overcast-sun mix. No fog. Virtual Shadow Maps with contact shadows.

### Post-processing

Bloom Intensity 0.3 with Threshold 1.5 so only ink highlights and glitter bloom. Keep the filmic tone curve; Global Saturation 1.05, no colour tint, no LUT. Grain 0, vignette 0, Scene Fringe Intensity 0, Motion Blur Amount 0, no depth of field. No post-process materials: there is no line and no banding. TSR anti-aliasing.

### UI and effects

Panels are sticker shapes: Image widgets with a hand-cut wobbly-edged texture, rotated 3 to 8 degrees, filled with one ink hue on `#2b2b33` or white. Text is Fredoka Bold or Baloo 2 Extra Bold; icons sit on splat-shaped badges; counters play a 0.2 s bounce on change. Niagara: ink shots are mesh-renderer blobs (deformed spheres using `M_Ink`) with 6 to 10 trailing droplets, 0.5 s lifetime, a wobble through World Position Offset, and a collision event that stamps a splat. Hits burst 20 droplets in the attacker's hue plus small additive glitter sprites for 0.3 s.

## Do / Do not

Do:

- Limit ink to two opposing hues per scene.
- Make ink clearly glossier than the base surface.
- Give ink pools a raised rounded rim.
- Cover large parts of the floor with ink and leave bare ground visible between the pools.

Do not:

- Do not add black outlines or flat bands; that reads as `004`.
- Do not use many unrelated hues; that reads as `013`.
- Do not make every surface hard glossy plastic with studs; that reads as `052`.
- Do not leave ink flat without specular.

## Nearest styles

- `013` Stylised hero PBR: this style lets two neon ink hues dominate neutral grey and white ground, with glossy ink on matte surfaces; `013` spreads many softer hues across the scene with an even material finish.
- `052` Brick toy: this style shows concrete speckle and painted metal on base surfaces and keeps gloss for the ink; `052` makes everything clean glossy plastic with studs and seams.
- `004` Graffiti street cel: this style has no outline and smooth shading with glossy highlights; `004` puts a black outline on every silhouette and shades in two flat tone steps.

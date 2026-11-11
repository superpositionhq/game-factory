# One-bit dither

Reference works: Return of the Obra Dinn.

## References

- *Return of the Obra Dinn* (2018), Lucas Pope, video game. https://en.wikipedia.org/wiki/Return_of_the_Obra_Dinn
- *Dark Castle* (1986), Silicon Beach Software, video game. https://en.wikipedia.org/wiki/Dark_Castle
- *Shadowgate* (1987), ICOM Simulations, video game. https://en.wikipedia.org/wiki/Shadowgate
- *World of Horror* (2023), Panstasz, video game. https://en.wikipedia.org/wiki/World_of_Horror

## Visual definition

- **Shape language and proportions:** Realistic 3D forms at modest polygon counts; ships, rooms, figures. The form is described entirely by dither density and edge lines.
- **Line and outline:** One-pixel lines on silhouettes and creases, drawn in the dark value on light areas and in the light value on dark areas.
- **Shading model:** Continuous light is converted to two values by dithering. Three or four dither densities are visible as distinct tone steps.
- **Palette:** `#333319` `#e5ffff` `#000000` `#ffffff` `#2b2b26`. Exactly two values: a dark and a light. Either pure black and white or a tinted pair such as dark olive and pale cyan-white.
- **Lighting:** Strong single light so forms split clearly into light, dithered midtone and dark.
- **Texture and surface:** Dither is the texture: ordered Bayer pattern on smooth surfaces, blue-noise pattern on organic ones.
- **Atmosphere and post-processing:** Low output resolution (about 640x360 to 800x450), nearest upscale, dither pattern stabilised against camera motion.
- **Camera and framing:** First-person, 60 to 70 degree field of view.
- **UI and typography:** Plain boxes with one-pixel ruled borders, like early desktop windows and the pages of a ship's ledger; icons are small two-value pictograms. Text is a serif book face or a hand-written ledger script drawn as crisp bitmap, with plain tabular figures for counts and times. The UI uses only the same two values and inverts them to mark a selection.
- **VFX and motion:** Particles are single pixels or small dithered clusters: dust, sparks, sea spray, gun smoke. An impact shows as a white flash or a brief inversion of the whole frame. Motion is sparse, with frozen tableaux, a slow camera and held poses of a few frames.

## Fits

- **Genres:** `detective-mystery`, `exploration`, `puzzle`, `survival-horror`
- **Moods:** eerie, austere, mysterious
- **Settings:** 19th-century sailing ship, haunted castle, cursed coastal town

## Unreal recipe

### Assets

Realistic packs at modest polygon counts work well: ship timbers, stone rooms, clothed figures. Strip every texture; only form and light survive the two-value conversion. Keep normal maps on large shapes (planks, folds) and drop fine grain, which turns into dither noise. Tag each mesh by script as `smooth` or `organic` through a stencil value so the post chain can choose its pattern. Build from scratch only what needs a clean silhouette: rigging lines, window bars, ledger props.

### Materials

One Default Lit master, `M_OneBit_Base`: mid-grey Base Color (a scalar `Albedo` of 0.3 to 0.8 per instance), Roughness 1, Specular 0, optional normal map. Material instances differ only in albedo, so tone comes from light. Set Render CustomDepth Pass on every mesh, with CustomDepth Stencil Value 1 for smooth surfaces and 2 for organic ones (`r.CustomDepth=3`).

### Lighting and atmosphere

Lumen off (`r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`). One strong Directional Light or one Point Light per room with Virtual Shadow Maps, plus a dim Sky Light from a grey cubemap so shadow sides sit at about 15 percent. No fog, no Sky Atmosphere; the sky is the dark value. Manual exposure.

### Post-processing

Scene renders at about 640x360: `r.ScreenPercentage` near 33 at 1080p, `r.AntiAliasingMethod=0`, `r.Upscale.Quality=0`. Bloom, grain, vignette, fringe, Motion Blur Amount and depth of field all 0. One post material, `PP_OneBit`, at Scene Color After Tonemapping:

1. Luminance of PostProcessInput0, pushed through a contrast curve so three or four densities read as separate steps.
2. Threshold against an 8x8 Bayer texture (stencil 1) or a 64x64 blue-noise texture (stencil 2), both Filter Nearest. Sample the pattern with UVs taken from the view direction mapped onto a sphere, not from ScreenPosition, so the pattern turns with the camera and does not swim.
3. One-pixel edges from a Roberts cross on SceneDepth and WorldNormal; write the edge as the opposite of the local dithered value.
4. Lerp between `DarkColour` `#333319` and `LightColour` `#e5ffff` (vector parameters).

### UI and effects

UMG uses the same pair only. Panels are Border widgets with a one-pixel light rule on the dark value; a selected row swaps the two colours. Text in IBM Plex Mono or EB Garamond rendered to a low-resolution Retainer Box whose effect material thresholds to two values. Counts use tabular figures. Niagara: single-pixel sprite particles in the light value (sea spray 40 to 80, lifetime 0.6 s; gun smoke as 6 to 10 dithered quads, 1.5 s). An impact inverts the whole frame for two frames by swapping the two colour parameters.

## Do / Do not

Do:

- Output exactly two colours.
- Dither with a stable ordered or blue-noise pattern.
- Draw one-pixel edges that invert against the local tone.
- Render at low resolution with nearest upscale.

Do not:

- Do not use round print dots and pen-weight outlines on white; that reads as `020`.
- Do not use four shades; that reads as `038`.
- Do not build tone from parallel engraved lines; that reads as `072`.
- Do not let the dither pattern swim with camera rotation.

## Nearest styles

- `020` Manga screentone monochrome: `020` is mostly white paper with round print dots and pen-weight outlines; this style is mostly dark, with pixel-scale dither patterns and one-pixel lines.
- `072` Engraved crosshatch print: `072` builds tone from parallel engraved lines on bright paper and outlines almost every form; this style is darker, builds tone from pixel dither and leaves some edges without a line.
- `038` Game Boy four-shade green: `038` shows four shades of green; this style shows only two values, one dark and one light.

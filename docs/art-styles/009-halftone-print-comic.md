# Halftone print comic

Reference works: Spider-Man: Into the Spider-Verse.

## References

- *Spider-Man: Into the Spider-Verse* (2018), Sony Pictures Animation, animated film. https://en.wikipedia.org/wiki/Spider-Man:_Into_the_Spider-Verse
- *Spider-Man: Across the Spider-Verse* (2023), Sony Pictures Animation, animated film. https://en.wikipedia.org/wiki/Spider-Man:_Across_the_Spider-Verse
- *The Mitchells vs. the Machines* (2021), Sony Pictures Animation, animated film. https://en.wikipedia.org/wiki/The_Mitchells_vs._the_Machines
- *Marvel's Spider-Man: Miles Morales* (2020), Insomniac Games, video game. https://en.wikipedia.org/wiki/Marvel's_Spider-Man:_Miles_Morales

## Visual definition

- **Shape language and proportions:** Semi-realistic 3D forms with slightly stylised proportions. City geometry is dense and angular.
- **Line and outline:** Selective ink: drawn lines on key contours and on faces, not on every edge. Line weight varies.
- **Shading model:** Two or three bands where the midtone is rendered with halftone dots and the shadow with parallel hatch lines.
- **Palette:** `#e23636` `#1b1b3a` `#25c4f2` `#ff4fa3` `#f7d038` `#7b3fe4` `#f2f2f2`. Saturated magenta, cyan, yellow and red over deep blue-violet night tones.
- **Lighting:** Strong coloured key and opposite coloured rim (for example pink and cyan).
- **Texture and surface:** Print artefacts everywhere: Ben-Day dots, line screens, and colour layers printed slightly out of register.
- **Atmosphere and post-processing:** Chromatic offset that grows away from the focus point in place of lens blur; bloom rendered as dot patterns; occasional graphic bursts.
- **Camera and framing:** Dynamic, tilted, wide angle; strong foreshortening.
- **UI and typography:** Panels are comic caption boxes and speech balloons: yellow (`#f7d038`) or white boxes with a thin black border and a slightly offset colour layer behind. Type is comic hand-lettering in bold italic capitals. Hit words and numbers are large outlined display letters filled with dots, in magenta, cyan and yellow.
- **VFX and motion:** Impacts show drawn burst shapes, action lines, lettered sound effects and a brief split of the colour layers. Characters animate on twos with crisp held poses against smooth camera motion; glows and sparks break up into dot patterns.

## Fits

- **Genres:** `action-adventure`, `fighting`, `hack-and-slash`, `platformer`, `third-person-shooter`
- **Moods:** energetic, vibrant, youthful
- **Settings:** New York City at night, neon rooftops, subway, glitching multiverse

## Unreal recipe

### Assets

Dense angular city packs and semi-realistic rigged characters work with little change to geometry. Reduce textures to flat colour regions: quantise base colour to palette hues, remove roughness detail, keep normal maps only on characters at half strength so the light term stays readable. Draw selected ink into the base colour of faces and key props by script; leave most environment edges without ink.

### Materials

`M_PrintBase`, Default Lit, Roughness 1, Specular 0. Print artefacts are done in post, so one master with colour instances is enough. Emissive signage uses saturated `#ff4fa3` and `#25c4f2`.

### Lighting and atmosphere

Lumen GI off or at low quality; the look needs clear light and shadow regions, not bounce. A coloured key (Directional or Spot Light in pink `#ff4fa3`) and an opposite rim light in cyan `#25c4f2`, with a dim blue-violet Sky Light (`#1b1b3a`) as fill. Hard shadows: Source Angle 0, Virtual Shadow Maps. No volumetric fog. Manual exposure.

### Post-processing

Chain at Scene Color After Tonemapping, in Blendable Priority order:

1. `PP_Screens`: recover the light term (PostProcessInput0 divided by BaseColor), split into lit, midtone and shadow. Midtone is drawn as round dots on a 45 degree screen-space grid, about 6 px pitch, dot radius from the light value. Shadow is drawn as parallel lines at a different angle. Lit areas stay flat.
2. `PP_Ink`: edge detect on CustomStencil only, so lines appear on tagged key contours and faces; width varies with a noise lookup.
3. `PP_Misregister`: sample red, green and blue at UV offsets that grow with the difference between SceneDepth and a focus distance parameter, 0 px in focus up to 6 px far away.

Bright pixels above a threshold are spread into a dot pattern in the first pass, so native Bloom Intensity is 0. Depth of field off, Motion Blur Amount 0, grain 0. Keep a mild tone curve (Tone Curve Amount 0.5). Use FXAA; temporal anti-aliasing makes screen-space dots shimmer.

### UI and effects

Caption boxes are Border widgets in `#f7d038` or white with a 2 px black outline, and a duplicate panel in magenta or cyan offset 3 px behind. Text is Bangers or Comic Neue Bold Italic in capitals. Hit words are large letters with a black font outline and a dot-pattern UI material fill. Niagara: burst-shape sprites, action-line ribbons and sound-effect letter meshes held for 0.3 s; sparks are small flat discs. On impact, pulse the misregistration offset to 10 px for 0.1 s.

## Do / Do not

Do:

- Render midtones with dots and shadows with lines.
- Offset colour channels more with distance from the focus plane.
- Use complementary key and rim colours.
- Keep some contours unlined.

Do not:

- Do not use large uniform dots with thick outlines and primaries only; that reads as `081`.
- Do not replace screens with hand hatching and full outlines; that reads as `001`.
- Do not use Gaussian depth of field.
- Do not drop colour for black and white screens; that reads as `020`.

## Nearest styles

- `081` Ben-Day pop art: this style draws lines only on key contours and puts small dots in the midtones of shaded 3D forms, in many colours; `081` puts a thick outline around every form and fills flat areas with large uniform dots in a few primaries.
- `001` Ink-outline comic cel: this style leaves some contours unlined and uses vivid magenta, cyan and yellow with dot and line screens; `001` inks every silhouette, hatches by hand and uses dusty earth colours.
- `017` Neon megacity 1980s anime: this style is brighter and covers the frame with print dots, line screens and colour offset; `017` is darker, with a clean thin line and detail painted by hand.

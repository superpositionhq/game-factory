# Brush-block martial painterly

Reference works: Sifu.

## References

- *Sifu* (2022), Sloclap, video game. https://en.wikipedia.org/wiki/Sifu_(video_game)
- *Absolver* (2017), Sloclap, video game. https://en.wikipedia.org/wiki/Absolver
- *Hero* (2002), Zhang Yimou, live-action film. https://en.wikipedia.org/wiki/Hero_(2002_film)

## Visual definition

- **Shape language and proportions:** Realistic proportions with simplified planes. Faces, cloth and furniture are reduced to broad, slightly angular surfaces as if blocked in with a wide brush.
- **Line and outline:** No outline.
- **Shading model:** Three to five broad tone steps with soft but visible boundaries, like a gouache study. No fine gradient, no sharp specular.
- **Palette:** `#c94f3d` `#e8c9a0` `#2f4858` `#6b8f71` `#f2a65a` `#3b2f2f` `#d8d2c4`. Each location has one dominant hue (red club, teal museum, warm wood dojo) with skin and cloth in muted complementary tones.
- **Lighting:** Strong coloured key light per room, large soft shadows, practical lamps as flat glowing shapes.
- **Texture and surface:** Low detail. Surfaces show large brush patches and soft tonal blocks; no pores, no grain, no small scratches.
- **Atmosphere and post-processing:** Mild bloom on lamps, light atmospheric haze tinted with the room colour, soft vignette.
- **Camera and framing:** Third-person at shoulder height, 35 mm equivalent, corridors and rooms framed in one-point perspective.
- **UI and typography:** Almost frameless UI: bars drawn as single thin brush strokes and round ink-seal icons, with no bevelled panels. Labels use a clean condensed sans; chapter cards and counters use brush-lettered numerals. Bone `#d8d2c4` text sits on dark brown `#3b2f2f`, with red `#c94f3d` for damage and alerts.
- **VFX and motion:** Snappy martial-arts animation: fast strikes with a short held pose on each impact and slow motion on finishing blows. Hits show a brief flat brush-smear flash and a small dust puff; no spark showers or flying debris.

## Fits

- **Genres:** `fighting`, `hack-and-slash`, `action-adventure`, `stealth`, `roguelike`, `soulslike`
- **Moods:** focused, vengeful, stylish
- **Settings:** kung fu dojo, neon nightclub, art museum, Chinese city back streets

## Unreal recipe

### Assets

Realistic-proportion characters and interior packs (dojo, club, gallery furniture) are the right base. Run a script pass that decimates props to their main planes and recomputes normals with a 40 to 60 degree hard-edge angle, so faces, cloth and tables break into broad angular facets. Strip every normal map and detail texture. Reduce albedo to large tonal patches: downscale each texture to 128 px, apply a median filter, then upscale to 1024 px with bilinear filtering. Build lamps and signs from scratch as emissive cards and boxes.

### Materials

One master, `M_BrushBlock`, Default Lit: BaseColor from the blurred albedo multiplied by a tint parameter, Roughness fixed at 0.9, Specular 0.1, no normal input. A very low-frequency `Noise` node through `WorldAlignedTexture` shifts value by about 5 percent to suggest wide brush patches, never small marks. Lamp shapes use an Unlit instance with a flat colour at 3 to 5 times scene white. The tone steps come from post-processing, not from the surface.

### Lighting and atmosphere

Lumen GI on, so the room's key colour floods walls and skin. One strong Rect or Spot Light per room in the dominant hue (`#c94f3d` club, `#2f4858` museum, `#f2a65a` dojo) with a large source size for wide soft shadows, plus two or three weak practicals. Virtual Shadow Maps on. Exponential Height Fog with Volumetric Fog on, Fog Inscattering Color set to the room hue at low density. Manual exposure.

### Post-processing

`PP_ToneSteps` at Scene Color Before Bloom: divide PostProcessInput0 by DiffuseColor to recover the light term, quantise luminance to four steps, and blend each boundary with a `SmoothStep` about 8 percent of a step wide, so edges stay soft but visible; multiply back by DiffuseColor. A second material with a 5 px plain Kuwahara filter runs after it to melt remaining small detail into blocks. Bloom Intensity 0.4 with Threshold 1.5 so only lamps glow, Vignette Intensity 0.35, Film Grain 0, Motion Blur Amount 0, Scene Fringe 0. TSR anti-aliasing.

### UI and effects

UMG has no panels: health and focus bars are single brush-stroke textures used as Progress Bar fill images, icons sit in round ink-seal brushes. Labels in Barlow Condensed, chapter cards and counters in a brush face such as Permanent Marker, bone `#d8d2c4` on `#3b2f2f`, damage in `#c94f3d`. Niagara: each hit spawns one flat brush-smear sprite (4-frame SubUV, Unlit, 0.12 s) aligned to the strike direction and a 6 to 10 sprite dust puff lasting 0.4 s. No sparks or debris; finishing blows use time dilation, not extra particles.

## Do / Do not

Do:

- Give each room one dominant light colour.
- Keep tone steps broad and few.
- Simplify surfaces into large planes.
- Remove small-scale surface detail.

Do not:

- Do not add outlines or hard two-band cel edges; that reads as `015`.
- Do not add dense brush-stroke texture and painted highlights; that reads as `024`.
- Do not use full photoreal materials; that reads as `029`.
- Do not use flat unlit colour layers; that reads as `060`.

## Nearest styles

- `024` Brush-textured 3D drama: this style keeps surfaces as large soft tone blocks with no small marks; `024` shows individual brush strokes and painted highlight marks on every surface.
- `026` Oily concept-art realism: here light falls in three to five visible steps and each room is bright and strongly coloured; `026` has smooth gradients and darker, grey rooms with little colour.
- `060` Layered flat-colour wilderness: forms here are shaded as rounded volumes in muted colours; `060` is stacked flat colour layers with no volume, in vivid sunset colours.

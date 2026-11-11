# Watercolour wash minimal

Reference works: Gris.

## References

- *Gris* (2018), Nomada Studio, video game. https://en.wikipedia.org/wiki/Gris
- *Neva* (2024), Nomada Studio, video game. https://en.wikipedia.org/wiki/Neva_(video_game)
- *Child of Light* (2014), Ubisoft Montreal, video game. https://en.wikipedia.org/wiki/Child_of_Light
- *The Red Turtle* (2016), Michael Dudok de Wit (Studio Ghibli and Wild Bunch), animated film. https://en.wikipedia.org/wiki/The_Red_Turtle

## Visual definition

- **Shape language and proportions:** Elegant, geometric simplification: circles, thin columns, long triangles. Architecture is tall and delicate; figures are small with flowing cloth.
- **Line and outline:** Sparse, thin pencil-like line on some structures. Most shapes have no line.
- **Shading model:** None. Shapes are flat washes with internal watercolour variation.
- **Palette:** `#f4efe9` `#e4b7b2` `#8fb8c9` `#b7a3c9` `#5d6d7e` `#f2d6a2` `#2f3a45`. Mostly pale: off-white, blush, dusty blue, lilac, with a dark slate for the figure. Colour is introduced one hue at a time.
- **Lighting:** No directional light. Depth is shown by layers that get paler with distance.
- **Texture and surface:** Watercolour: granulation, soft blooms, darker pigment at shape edges, visible paper.
- **Atmosphere and post-processing:** Paper overlay and soft edge bleed.
- **Camera and framing:** Side view with strong parallax layers; very wide framing, subject small.
- **UI and typography:** Almost no UI: thin pencil-line icons and small circular markers, with no panels or frames. Text is a light, widely spaced thin geometric sans in dark slate `#2f3a45` or off-white `#f4efe9`; counters are rows of small shapes instead of numerals.
- **VFX and motion:** Soft watercolour blooms, drifting dust motes and pigment that spreads through the paper when a new hue arrives; no hard impact flashes. Animation is fluid and hand-drawn, with long flowing cloth and hair and slow eases.

## Fits

- **Genres:** `platformer`, `puzzle`, `exploration`, `action-adventure`
- **Moods:** melancholic, serene, hopeful
- **Settings:** ruined temples, pale deserts, underwater caverns, sky palaces

## Unreal recipe

### Assets

Almost everything is built from scratch: circles, thin columns, long triangles, arches and stairs as flat or barely extruded meshes made in Blender background mode or Geometry Script, arranged in parallax layers along the depth axis. Store packs rarely fit; if one is used, keep only the silhouette and discard all its textures. Generate watercolour textures by script: a granulation noise, three soft bloom masks, and a paper texture. Each mesh also needs a signed-distance-to-silhouette map baked into a UV channel or texture for edge pigment. The figure is a small rigged character with cloth and hair simulated for long flowing motion.

### Materials

`M_Wash`, Unlit. BaseColor is a per-instance hue from the palette multiplied by granulation (world-aligned, 10 percent strength) and a slow large-scale bloom mask. The distance-to-edge map darkens the outer 3 to 5 percent of each shape by about 15 percent for pooled pigment, then the opacity fades out in the last pixels for a soft bleeding edge (Translucent or `DitherTemporalAA` Masked). A `LayerDepth` scalar parameter lerps the colour toward paper `#f4efe9`, so far layers pale out. A Material Parameter Collection holds a "hue arrival" amount per colour; materials desaturate to grey wash until gameplay raises it. Sparse pencil lines are thin mesh strips with an Unlit `#5d6d7e` material on a few structures only. The figure is flat `#2f3a45`.

### Lighting and atmosphere

No lights and no shadows. Lumen off, `r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`, `r.DefaultFeature.AmbientOcclusion=0`. No Sky Atmosphere; the background is a large Unlit plane in paper colour with a faint wash gradient. Fog is not used: the per-layer paling in the material controls depth exactly. Fixed manual exposure.

### Post-processing

At Scene Color After Tonemapping, in order: `PP_EdgeBleed`, a 4 px blur weighted by a noise so shape edges wander, without drawing any line; then `PP_Paper`, which multiplies the paper texture and adds fine grain locked to the screen. Tone Curve Amount 0, Expand Gamut 0 so pale hexes come through unchanged. Bloom, vignette, fringe, depth of field and Motion Blur Amount all 0. TSR.

### UI and effects

UMG shows almost nothing: thin pencil-line icons and small circle markers, no panels. Text in Jost Light or Josefin Sans Thin with wide letter spacing, `#2f3a45` or `#f4efe9`. Counters are rows of small filled shapes instead of numerals. Niagara: 20 to 40 dust motes drifting for 6 to 10 s; when a hue arrives, a spreading bloom sprite expands over 2 s with an eroding noise edge while the MPC value rises. Soft, slow eases only; no flashes.

## Do / Do not

Do:

- Use pale washes with darker pigment edges.
- Stack depth layers that fade to paper.
- Keep the figure small and dark against pale shapes.
- Limit each scene to one to three hues.

Do not:

- Do not add brush outlines on every contour; that reads as `022`.
- Do not use clean flat vector fills with strong saturation; that reads as `060`.
- Do not use thin lines on perfectly flat pastel colour; that reads as `012`.
- Do not add directional light and shadows.

## Nearest styles

- `022` Sumi-e ink wash: this style is mostly lineless, built from pale wash shapes; `022` draws almost every form with a heavy black brush line.
- `012` Thin-line pastel desert: washes here show granulation, blooms and paper grain, with few lines; `012` puts a fine dark line on perfectly flat, untextured colour.
- `060` Layered flat-colour wilderness: this style is pale and washed out, with soft bleeding edges; `060` uses vivid, deep sunset colours in crisp-edged flat layers.

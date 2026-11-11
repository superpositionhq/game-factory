# Synthwave sunset grid

Reference works: Far Cry 3: Blood Dragon; Out Run.

## References

- *Far Cry 3: Blood Dragon* (2013), Ubisoft Montreal, video game. https://en.wikipedia.org/wiki/Far_Cry_3:_Blood_Dragon
- *Out Run* (1986), Sega AM2 (Yu Suzuki), arcade video game. https://en.wikipedia.org/wiki/Out_Run
- *Hotline Miami* (2012), Dennaton Games, video game. https://en.wikipedia.org/wiki/Hotline_Miami
- *Kung Fury* (2015), David Sandberg, live-action short film. https://en.wikipedia.org/wiki/Kung_Fury
- *Drive* (2011), Nicolas Winding Refn, live-action film. https://en.wikipedia.org/wiki/Drive_(2011_film)

## Visual definition

- **Shape language and proportions:** A flat plain covered by a perspective grid running to the horizon, a huge striped sun, jagged wireframe or flat mountains, palm tree silhouettes, a low wedge sports car, chrome lettering.
- **Line and outline:** No dark outline. Bright neon lines form the grid and edge the mountains.
- **Shading model:** Mostly unlit gradients. Chrome objects use a stylised horizon reflection (dark below, bright sky above with a sharp line).
- **Palette:** `#12002b` `#ff2fd1` `#19f0ff` `#ff9a1f` `#6a1bff` `#ffe14d` `#2a0a4a`. Deep purple-black ground and sky, hot magenta, cyan, orange-to-yellow sun gradient, violet.
- **Lighting:** Self-lit. The sun is a graphic disc, not a light source.
- **Texture and surface:** Grid lines, sun stripes (horizontal gaps that widen toward the bottom), star dots, scanlines.
- **Atmosphere and post-processing:** Bloom, scanlines, chromatic aberration, slight VHS noise and vignette.
- **Camera and framing:** Low, centred, looking down the grid at the sun; wide field of view with forward motion.
- **UI and typography:** Titles are chrome-gradient lettering with a sharp horizon line; panels are thin neon outlines in magenta and cyan on purple-black, and icons are simple neon line shapes. Body text is a wide italic sans or a neon-tube script. Counters are slanted arcade numerals, yellow for score and magenta for damage, under the scanlines.
- **VFX and motion:** Neon sparks, laser bolts with long glowing streaks, and explosions as flat rings in magenta and orange; a hit flashes one colour-split glitch frame. Motion is constant forward speed with grid lines rushing past, and characters move in snappy arcade poses.

## Fits

- **Genres:** `racing`, `fps`, `top-down-shooter`, `vehicle-combat`, `fighting`, `third-person-shooter`
- **Moods:** nostalgic, energetic, campy
- **Settings:** 1980s Miami, neon highway, retro-future wasteland

## Unreal recipe

### Assets

Few objects, mostly scripted: an endless ground plane, jagged low-poly mountain strips with marked edges, palm trunks and fronds as flat silhouette cards, a huge sun disc mesh at the horizon, extruded chrome lettering. A low wedge sports car from a store pack fits once its textures are removed and its body set to chrome or flat magenta.

### Materials

Mostly Unlit. `M_Grid`: world-space lines from Frac and Step on WorldPosition, magenta `#ff2fd1` on `#12002b`, emissive at 8, scrolled toward the camera with Time to show speed. `M_Sun`: vertical Lerp from `#ffe14d` to `#ff9a1f` to `#ff2fd1`, with horizontal gaps cut by Step on a Frac of V whose duty cycle widens toward the bottom. `M_Sky`: gradient dome from `#12002b` through `#6a1bff` to magenta at the horizon, with star dots from a thresholded Noise. Mountains are `#2a0a4a` fills with cyan `#19f0ff` emissive edges from a baked edge mask. `M_Chrome` is Unlit too: sample a small gradient texture by the reflection vector's Z (dark purple below, sharp horizon line, bright sky above), so no real reflections are needed.

### Lighting and atmosphere

Self-lit: no directional light, no Sky Light, Lumen off for both global illumination and reflections, shadows disabled. The sun is graphics, not a light. A light Exponential Height Fog tinted `#6a1bff` blends the far grid into the horizon glow. Manual exposure.

### Post-processing

Bloom Intensity 1.5, Threshold 0.8. Scene Fringe Intensity 2 for chromatic aberration. Vignette Intensity 0.5. Tone Curve Amount 0.5 so neon stays saturated; Global Saturation 1.2. Motion Blur Amount 0, no depth of field. One post-process material at Scene Color After Tonemapping, authored with a Custom node, applies in order: scanlines (a sine on ScreenPosition Y darkening alternate rows by 15%), VHS noise (horizontal row jitter of 1 to 2 px driven by Noise and Time, plus fine luminance noise at 4%). A scalar parameter triggers a one-frame red/cyan channel split on hits. Anti-aliasing TSR.

### UI and effects

Titles are images or text with a User Interface material that paints the chrome gradient and horizon line inside the glyphs; use Monoton or an italic Audiowide. Panels are 2 px neon outlines in magenta and cyan on `#12002b`, drawn as Border brushes with no fill. Body text is italic Rajdhani. Counters are Press Start 2P or a slanted Orbitron: `#ffe14d` for score, `#ff2fd1` for damage. Put the HUD in a Retainer Box so the scanline material covers it too.

Niagara: laser bolts are stretched emissive sprites with a 0.2 s ribbon streak; sparks are 20 to 30 additive magenta and cyan points, 0.4 s; explosions are flat expanding ring meshes in magenta then orange, 0.35 s.

## Do / Do not

Do:

- Run a neon grid to the horizon.
- Place a large striped gradient sun at the centre.
- Use magenta, cyan and purple with bloom.
- Add scanlines and chromatic aberration.

Do not:

- Do not use only one or two line colours on pure black; that reads as `040` or `088`.
- Do not add rain, grime and realistic city detail; that reads as `089`.
- Do not use a naturalistic orange desert with teal sky; that reads as `033`.
- Do not use flat layered mountains without neon; that reads as `060`.

## Nearest styles

- `088` Neon grid cyberspace: this style has a bright gradient sky, a striped sun and several neon colours together; `088` is near-black with one or two line colours on solid glossy objects.
- `060` Layered flat-colour wilderness: this style has neon lines, bloom and hot magenta and cyan on a dark ground; `060` is a lighter picture of flat layered landscape shapes with no neon or glow.
- `040` Vector display glow: this style has filled gradients in the sky and sun; `040` is only glowing lines on black.

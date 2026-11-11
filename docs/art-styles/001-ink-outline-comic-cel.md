# Ink-outline comic cel

Reference works: Borderlands.

## References

- *Borderlands* (2009), Gearbox Software, video game. https://en.wikipedia.org/wiki/Borderlands_(video_game)
- *Borderlands 2* (2012), Gearbox Software, video game. https://en.wikipedia.org/wiki/Borderlands_2
- *Borderlands 3* (2019), Gearbox Software, video game. https://en.wikipedia.org/wiki/Borderlands_3
- *Tales from the Borderlands* (2014), Telltale Games, video game. https://en.wikipedia.org/wiki/Tales_from_the_Borderlands

## Visual definition

- **Shape language and proportions:** Realistic proportions with exaggerated mechanical detail. Hard-surface props are boxy, welded, dented and asymmetric; panels overlap and bolts are oversized.
- **Line and outline:** Black ink on every silhouette and on most creases. Line width changes along the stroke (2 to 6 px at 1080p), heavier on silhouettes than on inner edges, with visible wobble.
- **Shading model:** Three flat bands (lit, half tone, shadow). Shadow areas carry hand hatching; full shadow gets cross-hatching.
- **Palette:** `#17110f` `#c9772e` `#e8c27a` `#8a3b24` `#5f7f86` `#6b4f8a` `#f2e2c0`. Dusty oranges, rust and sand against cool steel blue; shadows lean violet; ink is a warm near-black.
- **Lighting:** One hard warm sun at a low angle plus flat ambient. Cast shadows have hard edges.
- **Texture and surface:** Textures look inked by hand: panel lines, scratches, chipped paint, rivets and hatch strokes drawn over flat base colours.
- **Atmosphere and post-processing:** Warm distance haze, light paper grain, soft vignette. No bloom, no depth of field.
- **Camera and framing:** 35 to 50 mm equivalent, eye level or slightly low, wide establishing shots with strong foreground props.
- **UI and typography:** Panels look like inked comic captions: sand and rust fills (`#e8c27a`, `#c9772e`) inside a wobbly warm-black border. Type is bold condensed grotesque capitals set at a slight slant; icons are flat inked pictograms. Damage numbers are heavy outlined digits in cream, with orange for critical hits.
- **VFX and motion:** Explosions, muzzle flashes and smoke are flat inked shapes with black outlines and hatched shadows, not soft sprites. Hits throw short ink speed lines and outlined spark stars; motion is weighty, with snappy recoil and brief held poses on impact.

## Fits

- **Genres:** `fps`, `rpg`, `vehicle-combat`, `third-person-shooter`, `top-down-shooter`
- **Moods:** irreverent, rowdy, gritty
- **Settings:** desert wasteland, scrapyard outpost, frontier mining planet

## Unreal recipe

### Assets

Scrap vehicles, sheet-metal shacks and bolted weapons from realistic packs suit this style. Keep the meshes; replace the textures. In a texture script, flatten each base colour map to 4 to 6 palette colours (median filter, then quantise), then draw ink over it: run an edge detector on the pack's normal and ambient occlusion maps and stamp the result as `#17110f` panel lines, scratches and rivet rings. Delete roughness and metallic maps. Build from scratch the oversized bolts, weld beads and dented plates that give the asymmetric silhouette, in Blender background mode.

### Materials

One master, `M_InkCel`, Default Lit, Roughness 1, Specular 0, Metallic 0, no normal map. The three bands are made in a post-process material, not in the surface: `PP_InkBands` divides PostProcessInput0 by the BaseColor scene texture to recover the light term, splits it at two thresholds into lit, half tone and shadow, and offsets the thresholds with a small noise texture so the band edge is rough. In the half-tone band it multiplies in the hatch texture, in full shadow the cross-hatch, both sampled in screen space at a fixed pixel scale and tinted violet (`#6b4f8a` over the base).

### Lighting and atmosphere

Lumen GI off (`r.DynamicGlobalIlluminationMethod=0`), reflections off. One Directional Light, warm (`#e8c27a`), pitch 20 to 30 degrees, Source Angle 0 for hard shadow edges, Virtual Shadow Maps on. A Sky Light with a flat cubemap gives even ambient. Exponential Height Fog in dusty orange (`#c9772e`, low density) supplies the distance haze. Exposure is Manual.

### Post-processing

At Scene Color Before Bloom, `PP_InkBands` runs first, then `PP_InkLine`. The line pass runs a Sobel on SceneDepth and WorldNormal; width comes from a screen-space noise lookup scaled between 2 and 6 px, with depth edges weighted higher than normal edges so silhouettes are heavier, and low-frequency noise displaces the sample UV for wobble. Line colour is `#17110f`. A last pass after tonemapping multiplies a faint paper grain. Bloom Intensity 0, no depth of field, Motion Blur Amount 0, Vignette Intensity 0.3, Tone Curve Amount about 0.3. Use FXAA (`r.AntiAliasingMethod=1`).

### UI and effects

Panels are Border widgets with a 9-slice brush drawn by script: sand or rust fill inside an uneven warm-black frame. Text uses Barlow Condensed Bold or Anton with a Slate skew transform; damage numbers are cream with a 3 px black font outline, orange for criticals. Niagara effects use sprite flipbooks of drawn shapes with ink edges (4 to 8 SubUV frames, stepped at 12 fps): explosion clouds with hatched undersides, six-point spark stars, short black speed lines on hits lasting 0.15 s. Particle materials are Unlit and Masked.

## Do / Do not

Do:

- Vary line weight along each stroke and between silhouette and crease.
- Keep band boundaries hard and slightly noisy.
- Put hatching only in shadow and half tone.
- Paint wear marks as ink shapes, not as noise.

Do not:

- Do not use constant-width clean lines with flat fills; that reads as `011`.
- Do not add halftone dots or misregistered colour; that reads as `009`.
- Do not use smooth PBR shading under the outlines.
- Do not fill large areas with solid black; that reads as `010`.

## Nearest styles

- `009` Halftone print comic: this style shades with hand-drawn hatch strokes and inks every silhouette; `009` shades with printed dot screens, leaves some contours unlined and prints its colour layers out of register.
- `004` Graffiti street cel: this style has three tone steps, a wobbly line of changing width and hatching over worn surfaces; `004` has two tone steps, an even line and clean flat surfaces apart from its graffiti.
- `010` Heavy-black gothic comic: this style stays bright, with shadows drawn as hatching over colour; `010` drops about half of every form into solid black.

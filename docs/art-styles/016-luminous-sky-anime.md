# Luminous sky anime

Reference works: Your Name.

## References

- *Your Name* (2016), CoMix Wave Films (Makoto Shinkai), animated film. https://en.wikipedia.org/wiki/Your_Name
- *Weathering with You* (2019), CoMix Wave Films (Makoto Shinkai), animated film. https://en.wikipedia.org/wiki/Weathering_with_You
- *5 Centimeters per Second* (2007), CoMix Wave Inc. (Makoto Shinkai), animated film. https://en.wikipedia.org/wiki/5_Centimeters_per_Second
- *The Garden of Words* (2013), CoMix Wave Films (Makoto Shinkai), animated film. https://en.wikipedia.org/wiki/The_Garden_of_Words
- *Suzume* (2022), CoMix Wave Films (Makoto Shinkai), animated film. https://en.wikipedia.org/wiki/Suzume

## Visual definition

- **Shape language and proportions:** Realistic, precisely observed modern settings: power lines, railway crossings, rooftops, wet streets. Characters are simple anime figures, small in the frame.
- **Line and outline:** Thin dark line on characters only. Scenery edges are defined by light.
- **Shading model:** Characters: two bands with a coloured rim. Scenery: painted realism with strong light gradients and bounce colour.
- **Palette:** `#1e3a8a` `#60a5fa` `#fbcfe8` `#fde68a` `#f97316` `#0f172a` `#a7f3d0` `#ffffff`. Deep blue to pink and gold twilight skies, bright lens highlights, saturated reflected colour in shadows.
- **Lighting:** Low sun or twilight with long shadows, backlight, glowing cloud edges and visible light shafts.
- **Texture and surface:** High detail in sky and reflective surfaces: layered clouds, stars, wet ground reflections, glints on glass and metal.
- **Atmosphere and post-processing:** Bloom, lens flare streaks, light shafts, slight chromatic fringe, floating dust particles.
- **Camera and framing:** Low angles that give the sky 50 to 70% of the frame; wide lens.
- **UI and typography:** Very light UI: thin white lines and frosted translucent panels that let the sky show through, with small white outline icons. Text is a thin, clean modern sans in white, like film subtitles and phone-screen messages; counters are slim white numerals with a faint glow. Accents are twilight pink or gold.
- **VFX and motion:** Drifting dust motes, rain streaks, falling petals, lens flare streaks and slow meteor trails with glowing tails. Impacts are soft bursts of light and ripples on wet ground, not hard flashes. Characters animate on twos with restrained natural movement while clouds, light shafts and reflections move smoothly.

## Fits

- **Genres:** `exploration`, `detective-mystery`, `puzzle`, `simulation`, `racing`
- **Moods:** wistful, romantic, hopeful
- **Settings:** modern Tokyo rooftops, rural railway crossing, rain-soaked city park, lakeside mountain town

## Unreal recipe

### Assets

Use photoreal modern-city and suburb packs and keep their detail: power lines, railway crossings, rooftops with tanks and aerials, vending machines, road markings. Scenery textures stay close to realistic; only grade base colour toward clean saturated hues and remove heavy grime. Add wetness by script: lower Roughness to 0.1 to 0.2 on roads and roofs through a puddle mask. Build thin cable and overhead-wire meshes from splines by script. Characters are simple rigged anime figures, small in frame.

### Materials

Scenery: `M_RealWet`, Default Lit, full PBR with the puddle mask blending roughness and flattening normals. Characters: `M_SkyCel`, Unlit, two bands by SmoothStep on N·L with a tight range, light direction and colours from a Material Parameter Collection that C++ fills from the sun and the sky's current tint, so shadows pick up saturated sky colour (`#1e3a8a` toward `#60a5fa`). A Fresnel rim in sun colour (`#fde68a` or `#f97316`) is added on the side facing the sun. A thin dark inverted-hull Overlay Material gives the character line; scenery has none.

### Lighting and atmosphere

Lumen GI and Lumen reflections on at high quality; wet ground must mirror the sky. Directional Light at 5 to 12 degrees elevation for long shadows, usually backlighting the view. Sky Atmosphere with Volumetric Cloud in two layers, tuned so cloud edges glow toward the sun; a star dome for late twilight. Exponential Height Fog with Volumetric Fog on and the sun's Volumetric Scattering Intensity raised to 2 to 4 for visible shafts. Virtual Shadow Maps. Auto exposure with a narrow range biased bright.

### Post-processing

Bloom Method Convolution (or Standard at Intensity 1) with a low Threshold so sky and reflections glow. Lens Flare Intensity 0.5 to 1 with a streak-shaped bokeh. Scene Fringe Intensity 0.3. Grade: Shadows tinted blue-violet, Highlights toward pink and gold (`#fbcfe8`, `#fde68a`), Global Saturation 1.15. Local Exposure to hold sky detail against dark ground. No grain, Vignette 0.2, Motion Blur Amount 0, light depth of field only on close-ups. TSR.

### UI and effects

Panels use a UI material with Background Blur widgets behind them and 15 percent white tint, edged by 1 px white lines, so the sky shows through. Text is a thin sans (Jost Light, Noto Sans JP Light) in white; counters are slim numerals with a faint outer glow from a soft shadow. Accents are `#fbcfe8` or `#fde68a`. Niagara: 50 to 100 dust motes drifting 6 to 10 s in the light shafts, GPU rain streak sprites, petals, meteor ribbons with glowing tails lasting 2 s, and ripple decals on wet ground. Impacts are soft additive light bursts of 0.4 s, never hard flashes.

## Do / Do not

Do:

- Give the sky at least half of the frame.
- Rim clouds and objects with sun-coloured light.
- Add reflections on wet or glossy ground.
- Use bloom and light shafts from the sun position.

Do not:

- Do not paint matte gouache backgrounds without glow; that reads as `014`.
- Do not flatten scenery into bands and gradients; that reads as `018`.
- Do not turn the scene into a black night filled with neon signs; that reads as `017`.
- Do not line the scenery.

## Nearest styles

- `014` Hand-painted pastoral anime: `014` has matte poster-colour scenery in plain daylight with no glow; this style has glowing skies, lens flares, light shafts and shining wet reflections.
- `017` Neon megacity 1980s anime: `017` is a near-black night city lit only by signs, windows and lamps; this style is lit by a bright open sky at low sun or twilight.
- `018` Soft open-world anime cel: `018` has clean, simplified scenery with smooth gradients and outlined props; this style has closely observed real places with detailed clouds, cables and reflections and no line on scenery.

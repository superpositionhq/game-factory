# Stylised hero PBR

Reference works: Overwatch.

## References

- *Overwatch* (2016), Blizzard Entertainment, video game. https://en.wikipedia.org/wiki/Overwatch_(2016_video_game)
- *Overwatch 2* (2022), Blizzard Entertainment, video game. https://en.wikipedia.org/wiki/Overwatch_(2023_video_game)
- *Valorant* (2020), Riot Games, video game. https://en.wikipedia.org/wiki/Valorant
- *Fortnite* (2017), Epic Games, video game. https://en.wikipedia.org/wiki/Fortnite
- *Big Hero 6* (2014), Walt Disney Animation Studios, animated film. https://en.wikipedia.org/wiki/Big_Hero_6_(film)

## Visual definition

- **Shape language and proportions:** Heroic, slightly exaggerated proportions with clean large forms, chamfered hard-surface armour and readable silhouettes. Small detail is grouped into a few areas.
- **Line and outline:** No outline.
- **Shading model:** Full PBR with smooth gradients, simplified: broad clean roughness regions, soft ambient occlusion and bright rim light.
- **Palette:** `#f79e1b` `#2d9cdb` `#f2f2f2` `#3c4654` `#e74c3c` `#7ed6a5` `#ffd66b`. Bright, optimistic: clean white and grey armour with orange, blue and teal accents; emissive strips.
- **Lighting:** Sunny key, strong coloured fill and bounce; environments are evenly lit and airy.
- **Texture and surface:** Clean material definition with hand-painted gradients inside PBR maps; little noise or grime.
- **Atmosphere and post-processing:** Bloom on emissives, mild colour grade toward warm highlights and cool shadows, anti-aliased.
- **Camera and framing:** Third or first person, 40 to 50 mm equivalent, heroic low angles.
- **UI and typography:** Slanted, semi-transparent dark panels with chamfered corners and thin white edges; icons are flat white glyphs in circles or hexagons. Text is a bold italic condensed sans in white, with orange for the player and blue or red for teams. Damage numbers and ability counters are large slanted white numerals that pop and fade, with yellow for critical hits.
- **VFX and motion:** Effects are clean, bright shapes colour-coded per character: thick tracer streaks, soft-edged energy shields, chunky sparks and a short shaped flash on hit. Animation is snappy with strong anticipation, slight squash and stretch and a clear held pose at the end of each move.

## Fits

- **Genres:** `fps`, `third-person-shooter`, `top-down-shooter`, `tower-defense`, `vehicle-combat`, `sports`
- **Moods:** optimistic, energetic, heroic
- **Settings:** near-future city, sunny Mediterranean town, high-tech laboratory, moon base

## Unreal recipe

### Assets

Sci-fi and hero packs with clean large forms are the right base. Bevel every hard edge (Blender bevel pass by script where the pack is sharp) and bake the result to normals. Clean the textures: remove grime, scratches and noise overlays from albedo and roughness, flatten roughness into three or four broad regions (matte paint 0.6, plastic 0.35, metal 0.25, rubber 0.8), and add a soft painted gradient, darker toward the bottom of each part, into base colour. Keep normal maps for form and panel seams only. Add emissive strip geometry where an asset has none.

### Materials

`M_HeroPBR`, Default Lit, standard metal and roughness workflow, driven by a colour-ID mask so instances recolour regions: white `#f2f2f2` and grey `#3c4654` armour, with accents in `#f79e1b`, `#2d9cdb`, `#7ed6a5`. Parameters: region colours, region roughness, emissive colour and intensity (8 to 20 for bloom), ambient occlusion from the baked map. A Fresnel term feeds a small amount into Emissive for a clean rim on characters. Use Clear Coat for visors and lacquered armour, Subsurface Profile for skin. No stylised shading tricks: real light on clean maps is the look.

### Lighting and atmosphere

Lumen GI and Lumen reflections on, Final Gather Quality raised for clean bounce. Sunny Directional Light, Source Angle 1, with Sky Atmosphere, Sky Light (Real Time Capture) and light Volumetric Cloud. Add coloured Rect Lights as fill in interiors so no area is dark. A back Directional Light on the character Lighting Channel gives the rim. Light Exponential Height Fog only. Virtual Shadow Maps with contact shadows. Auto exposure with a narrow EV100 range.

### Post-processing

Bloom Method Standard, Intensity 0.6, Threshold 1 so emissives glow and white armour does not. Default filmic tone curve. Grade through the volume: Highlights Gain slightly warm, Shadows Gain slightly cool, Global Saturation 1.1. Ambient Occlusion soft and wide. No grain, Vignette Intensity 0.2, Scene Fringe Intensity 0, Motion Blur Amount 0, depth of field only in menus and cut scenes. No post-process materials. TSR with `r.Tonemapper.Sharpen` about 0.5.

### UI and effects

Panels are dark translucent shapes (60 percent `#3c4654`) with chamfered corners cut into the 9-slice texture, a 1 px white edge and a slight shear. Icons are white glyphs in circles or hexagons. Text is Barlow Condensed Bold Italic or Rajdhani Bold in white; player elements are orange, teams blue or `#e74c3c`. Damage numbers pop to 130 percent then settle and fade in 0.6 s, `#ffd66b` for criticals. Niagara: thick ribbon tracers, soft-edged translucent shield meshes with Fresnel, chunky mesh sparks, and a shaped additive flash of 0.1 s on hit, each character keeping one signature colour.

## Do / Do not

Do:

- Bevel every hard edge.
- Group detail into a few clusters and leave large clean areas.
- Add emissive accents with bloom.
- Keep roughness regions broad and distinct.

Do not:

- Do not add photographic grime and noise; that reads as `032` or `030`.
- Do not paint heavy detail into albedo with little PBR response; that reads as `023`.
- Do not mute the palette and tint the terminator; that reads as `005`.
- Do not add outlines or bands.

## Nearest styles

- `005` Rim-lit illustrative caricature: `005` uses muted, earthy colours with a warm tint where light turns to shadow; this style is bright and clean with white armour and vivid accent colours.
- `023` Chunky hand-painted fantasy: `023` paints highlights, shadows and wear directly into its textures; this style keeps surfaces clean and lets real light show metal, plastic and cloth.
- `006` Glossy ink-splat pop: `006` covers the scene in wet, glossy splats of two opposing ink colours; this style spreads many accent colours over clean white and grey surfaces.

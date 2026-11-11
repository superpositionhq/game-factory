# Neon megacity 1980s anime

Reference works: Akira.

## References

- *Akira* (1988), Tokyo Movie Shinsha (Katsuhiro Otomo), animated film. https://en.wikipedia.org/wiki/Akira_(1988_film)
- *Ghost in the Shell* (1995), Production I.G (Mamoru Oshii), animated film. https://en.wikipedia.org/wiki/Ghost_in_the_Shell_(1995_film)
- *Bubblegum Crisis* (1987), AIC and Artmic, original video animation. https://en.wikipedia.org/wiki/Bubblegum_Crisis
- *Cyberpunk: Edgerunners* (2022), Studio Trigger, animated TV series. https://en.wikipedia.org/wiki/Cyberpunk:_Edgerunners

## Visual definition

- **Shape language and proportions:** Dense megacity: stacked towers, highways, pipes and cables, drawn with accurate perspective and mechanical detail. Vehicles are low, wide and angular.
- **Line and outline:** Thin, precise black line on all foreground objects, with drawn panel and mechanical detail.
- **Shading model:** Two or three flat cel bands on foreground objects; backgrounds are painted night scenes with thousands of lit windows.
- **Palette:** `#0a0a14` `#d7263d` `#f46036` `#2e294e` `#1b998b` `#f5d547` `#3a86ff`. Near-black blue night with red, orange and teal light; one key red object.
- **Lighting:** Night. Light comes from signs, windows, headlights and street lamps; strong coloured rim light.
- **Texture and surface:** Painted background detail: window grids, stains, signage. Light trails from moving lamps.
- **Atmosphere and post-processing:** Glow around lights, light-trail streaks, mild film grain. No modern lens effects.
- **Camera and framing:** Deep one- and three-point perspective, low angles along streets, 28 mm equivalent.
- **UI and typography:** Thin-line rectangular frames on near-black with small technical callouts, like 1980s vehicle dashboards and video monitors. Text is a bold condensed sans in capitals, with blocky segmented digits for speed, time and ammunition counters. UI colours are red and orange on black with teal for secondary readouts; warnings blink in yellow.
- **VFX and motion:** Long red and white light trails behind lamps, hand-drawn explosions built from layered flat orange and yellow shapes, drawn smoke plumes, debris chunks and spark showers. Animation is detailed and weighty with fast cuts; vehicles lean and skid with drawn motion streaks.

## Fits

- **Genres:** `racing`, `vehicle-combat`, `third-person-shooter`, `action-adventure`, `detective-mystery`, `stealth`
- **Moods:** tense, rebellious, frenetic
- **Settings:** neon megacity at night, elevated highway, back-alley market, military research complex

## Unreal recipe

### Assets

Stack dense city blocks from sci-fi or modern city packs: towers, elevated highways, pipes, cable bundles. Foreground props and vehicles (low, wide, angular) keep their mechanical detail as geometry so the line pass can trace it; flatten their textures to plain colour. Distant towers are best built from scratch as boxes with a script-painted night texture: near-black walls (`#0a0a14`, `#2e294e`) with thousands of small lit windows in orange, yellow and teal, plus stains and signage. Mark one hero object in red `#d7263d`.

### Materials

`M_NightCel`, Default Lit, Roughness 1, Specular 0, Metallic 0, no normal map: foreground objects receive the real sign and lamp lights, and the bands are cut in post. `M_PaintedTower`, Unlit, shows the painted window texture as emissive at moderate intensity; a PerInstanceRandom offset varies which windows are lit. Sign and lamp materials are Unlit emissive at high intensity. No wet or glossy response anywhere; matte paint under ink line is what keeps this from a filmed rain-city look.

### Lighting and atmosphere

Night, no sun and no moonlight. Lumen GI off; a very dim blue Sky Light keeps blacks from being empty. Light with many Point, Spot and Rect Lights at signs, windows, headlights and street lamps in red, orange and teal (`#f46036`, `#1b998b`), few of them casting shadows. Place strong coloured rim lights behind foreground subjects. Volumetric Fog off; only a faint dark Exponential Height Fog for depth. Manual exposure.

### Post-processing

At Scene Color Before Bloom, on stencil-tagged foreground objects only:

1. `PP_NightBands`: light term from PostProcessInput0 over BaseColor, quantised to three flat steps with hard edges.
2. `PP_MechLine`: Sobel on SceneDepth and WorldNormal, 1 to 1.5 px, pure black, no width variation, so panel seams and mechanical detail are drawn precisely.

Painted towers pass through untouched. Bloom Method Standard, Intensity 0.7, small size, giving a tight glow around lights. Film Grain Intensity 0.3. Lens Flare 0, Scene Fringe 0, no depth of field, Motion Blur Amount 0: no modern lens effects. Light trails are geometry, not blur. TSR or FXAA.

### UI and effects

Frames are 1 px red or orange outlines on `#0a0a14` with small technical callout labels, like a dashboard monitor. Text is Barlow Condensed Bold or Oswald in capitals; speed, time and ammunition use a segmented-digit face (DSEG7, open licence) in orange, secondary readouts in teal, warnings blinking `#f5d547` at 2 Hz. Niagara: ribbon light trails in red and white following lamp sockets, 0.5 to 1 s long; explosions as layered flat orange and yellow flipbook shapes stepped at 12 fps; drawn smoke plumes; mesh debris chunks; spark showers of 30 to 60 short streak sprites.

## Do / Do not

Do:

- Fill the background with lit window grids.
- Light the scene from signs and lamps, not a sun.
- Keep line thin and mechanical.
- Include one strongly red hero object.

Do not:

- Do not use smooth PBR with wet reflections and volumetric haze; that reads as `089`.
- Do not reduce the scene to emissive lines on black; that reads as `088`.
- Do not use print dots and channel offsets; that reads as `009`.
- Do not light with a sunset sky; that reads as `016`.

## Nearest styles

- `089` Rain-soaked tech-noir: `089` has no drawn line and looks filmed, with smooth shading, wet reflections and thick haze; this style has black ink lines and flat cel tones on every foreground object.
- `009` Halftone print comic: `009` looks printed on paper, with visible dot screens and lighter page tones; this style is a dark night scene of clean flat cel colour and painted lit windows.
- `016` Luminous sky anime: `016` is filled by a bright sky at low sun or twilight; this style is a black night where all light comes from signs, windows and lamps.

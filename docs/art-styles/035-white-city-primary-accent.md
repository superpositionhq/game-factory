# White city with primary accents

Reference works: Mirror's Edge.

## References

- *Mirror's Edge* (2008), DICE, video game. https://en.wikipedia.org/wiki/Mirror's_Edge
- *Mirror's Edge Catalyst* (2016), DICE, video game. https://en.wikipedia.org/wiki/Mirror's_Edge_Catalyst
- *Portal* (2007), Valve, video game. https://en.wikipedia.org/wiki/Portal_(video_game)
- *Playtime* (1967), Jacques Tati, live-action film. https://en.wikipedia.org/wiki/Playtime

## Visual definition

- **Shape language and proportions:** Clean modern architecture: flat roofs, glass towers, ducts, railings, scaffolds and cranes. Simple orthogonal volumes with a few diagonal pipes.
- **Line and outline:** No outline.
- **Shading model:** Smooth, with soft global-illumination-like colour bleeding: coloured objects tint nearby white surfaces.
- **Palette:** `#ffffff` `#e9edf0` `#e2231a` `#f7a800` `#1f7ae0` `#2bb673` `#9aa4ad`. Overexposed white on almost every surface, with single-hue accents: one saturated red, orange, blue or green per area.
- **Lighting:** Very bright clear daylight, slightly overexposed; soft blue sky fill in shadows.
- **Texture and surface:** Nearly none. Clean painted concrete and metal with faint panel joints.
- **Atmosphere and post-processing:** High exposure, bloom on sky and white surfaces, light blue tint in shadows.
- **Camera and framing:** First-person, 90 degree field of view, rooftop vistas with deep perspective.
- **UI and typography:** Almost invisible: thin hairlines, wide white space and small flat pictograms like wayfinding signs. Type is a clean geometric sans in light weights, with large thin numerals for timers and speed. Text is cool grey `#9aa4ad` on white, and the key red `#e2231a` marks objectives and the route ahead.
- **VFX and motion:** Few particles: soft white bloom flashes, small dust puffs on landing and glass shards that catch the light, with no smoke or grime. Motion is fluid and driven by momentum, with realistic body weight, camera bob and roll on landings; objective objects pulse red.

## Fits

- **Genres:** `platformer`, `fps`, `action-adventure`, `puzzle`, `racing`, `exploration`
- **Moods:** clean, airy, kinetic
- **Settings:** rooftop cityscape, glass corporate towers, sterile test facility, modernist plaza

## Unreal recipe

### Assets

Modern rooftop architecture: flat roofs, glass towers, ducts, railings, scaffolds, cranes, air-conditioning units. Store city packs fit after cleaning: delete grime decals and replace all albedo, roughness and detail textures with flat values, keeping only a faint panel-joint normal. Simple orthogonal volumes, pipes and scaffold runs are faster to build from scratch with Geometry Script. Each area gets a set of accent props (doors, pipes, containers, awnings) in one hue.

### Materials

`M_WhiteCity`, Default Lit. BaseColor `#e9edf0` at high albedo (about 0.85 linear), Roughness 0.6, Specular 0.3, normal input limited to thin joint lines. `M_Accent` instances use pure saturated BaseColor in `#e2231a`, `#f7a800`, `#1f7ae0` or `#2bb673`, one hue per area, with a small Emissive boost (0.3) so their bounce onto white is clearly visible. Glass uses Thin Translucent with a pale blue tint and Lumen reflections. Objective objects pulse red through a `Time`-driven emissive parameter. Shading stays smooth; no facets and no outline.

### Lighting and atmosphere

Lumen GI is essential and set high: Lumen Scene Lighting Quality 2, Final Gather Quality 2, with the Directional Light's Indirect Lighting Intensity raised to 1.5 so accent colours bleed onto nearby white. Directional Light around 10 lux, clear daylight, 45 to 60 degrees elevation, Source Angle 1. Sky Atmosphere with a clear sky and a strong Sky Light (Real Time Capture, intensity 1.5) so shadows fill pale blue. Virtual Shadow Maps on. Distance haze from light Exponential Height Fog in white. Manual exposure set about one stop over neutral, so sunlit white clips slightly.

### Post-processing

Bloom Intensity 0.8, Threshold 1, blooming sky and sunlit white. Shadows Gain tinted light blue; Global Saturation 1.1 keeps accents pure. Film Shoulder lowered for an early roll into white. Ambient Occlusion Intensity 0.3. Vignette 0, Film Grain 0, Scene Fringe 0, depth of field off, Motion Blur Amount 0 with gentle first-person bob. No post-process materials. TSR with field of view 90.

### UI and effects

Near-invisible UMG: 1 px hairlines, wide empty space, small flat wayfinding pictograms. Type in Jost Light or Montserrat Light; timers and speed in large thin numerals. Text `#9aa4ad` on white; `#e2231a` only for objectives and route markers. Niagara is minimal: a soft white additive flash sprite for 0.15 s, 4 to 6 pale dust puffs on landing lasting 0.4 s, and glass shards as small mesh particles with a low-roughness material that catch the sun for 1.5 s. No smoke, no dark particles.

## Do / Do not

Do:

- Keep almost every surface white.
- Use one pure accent hue per area.
- Tint shadows pale blue and overexpose slightly.
- Let accent colours bleed onto nearby white.

Do not:

- Do not use faceted flat shading with only red; that reads as `063`.
- Do not move indoors with curved moulded panels and no accent colour; that reads as `091`.
- Do not add grime or weathering.
- Do not use raw grey concrete with heavy texture; that reads as `097`.

## Nearest styles

- `063` White-and-red faceted minimal: this style has smooth shaded surfaces with red, orange, blue and green accents that tint the white around them; `063` has faceted crystalline figures and uses only red and black against white.
- `091` Clinical white space-age: this style is outdoor rooftops blown out by daylight, with blue-tinted shadows and bold accent blocks; `091` is indoor curved, padded panels lit evenly by built-in strips, with visible seams and almost no colour.
- `097` Brutalist concrete: this style has clean white painted surfaces with almost no surface marks; `097` is mid-grey raw concrete with plank imprints and rain streaks.

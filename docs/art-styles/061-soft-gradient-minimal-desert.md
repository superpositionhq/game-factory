# Soft-gradient minimal desert

Reference works: Journey.

## References

- *Journey* (2012), Thatgamecompany, video game. https://en.wikipedia.org/wiki/Journey_(2012_video_game)
- *Abzu* (2016), Giant Squid, video game. https://en.wikipedia.org/wiki/Abzû
- *The Pathless* (2020), Giant Squid, video game. https://en.wikipedia.org/wiki/The_Pathless
- *Sky: Children of the Light* (2019), Thatgamecompany, video game. https://en.wikipedia.org/wiki/Sky:_Children_of_the_Light

## Visual definition

- **Shape language and proportions:** Wide empty dunes with a few monumental simple ruins: slabs, arches, towers, a distant mountain with a split peak. The figure is a small cone-shaped robed form with thin legs and a long scarf.
- **Line and outline:** No outline.
- **Shading model:** Smooth and soft, with sand that glows: strong warm backscatter, a sharp glitter sparkle layer and soft ridge shadows.
- **Palette:** `#e9a35a` `#f6d08a` `#c9683c` `#7a2e2a` `#fbe9c6` `#5b3a4a`. Almost one hue family: gold, orange, rust and cream, with a dark maroon figure. Other scenes switch the whole frame to one other hue.
- **Lighting:** Low sun with long soft shadows; sky and ground are close in colour so the horizon dissolves.
- **Texture and surface:** Fine sand sparkle and ripple lines; ruins are smooth stone with simple inlaid bands.
- **Atmosphere and post-processing:** Warm haze that removes the horizon, bloom on the sun and sparkle, slight vignette.
- **Camera and framing:** Very wide, subject small, low horizon; slow lateral moves.
- **UI and typography:** Almost no HUD and no panels or frames; state shows in the world, such as glowing white glyphs along the scarf. Any text is a thin, widely spaced geometric sans in cream `#fbe9c6`, icons are simple single-stroke glyph symbols, and counters are small cream glyph marks instead of numerals.
- **VFX and motion:** Sand spray and dust plumes trail behind movement, cloth scraps flutter, and soft cream glow pulses replace hard hit flashes. Motion is slow and gliding, with long eased arcs, floaty jumps and constant follow-through on scarf and robe.

## Fits

- **Genres:** `exploration`, `platformer`, `puzzle`, `action-adventure`
- **Moods:** serene, lonely, awed
- **Settings:** dune desert, buried ruins, mountain pilgrimage, sunken temple

## Unreal recipe

### Assets

Build the dunes by script: a Blender or Geometry Script heightfield from layered ridged noise, smoothed until crests are long clean curves, exported as dense static meshes with Nanite on. Ruins are slabs, arches and towers with large bevels and one inlaid band; build them rather than restyle. From a store ruin pack keep only large forms, with normal maps and albedo detail deleted. The figure is a rigged character hidden under a cone robe mesh, with scarf and hem on cloth simulation.

### Materials

`M_Sand` uses the Subsurface shading model. Base Colour lerps `#c9683c` to `#f6d08a` by `VertexNormalWS.Z`, and Subsurface Colour `#e9a35a` supplies the backscatter when the sun is behind a crest. Add three layers:

- Ripples: a fine world-aligned sine normal, strength 0.2, faded by PixelDepth.
- Glitter: a Custom node hashes a high-frequency world-space cell normal, takes its Dot with the half vector from CameraVectorWS and SkyAtmosphereLightDirection, raises it to a power near 400 and sends it to Emissive in `#fbe9c6`.
- Fresnel lift of 0.15 toward `#f6d08a` at grazing angles.

`M_Stone` is Default Lit, one colour per instance, roughness 0.7, with a mask band for the inlay. `M_Robe` is Cloth in `#7a2e2a` and `#5b3a4a`; scarf glyphs are an emissive mask driven by a scalar parameter from C++.

### Lighting and atmosphere

Lumen GI on; reflections can stay screen-space. One Directional Light at 8 to 15 degrees elevation, Source Angle 3 for soft ridge shadows, colour near `#f6d08a`. Sky Atmosphere with Rayleigh and Mie tinted warm so the sky sits near `#f6d08a`, and a real-time-capture Sky Light. Exponential Height Fog does the horizon: Fog Inscattering Color sampled from the sky at the horizon, low Height Falloff, density raised until the dune line disappears at 300 to 500 m, strong Directional Inscattering toward the sun. Virtual Shadow Maps on; manual exposure, set bright.

### Post-processing

Filmic tonemapper with Shoulder lowered so highlights roll off softly. Bloom Intensity 0.8, Threshold 1, so only sun and glitter bloom. White Balance warm, Shadows gain tinted `#5b3a4a`, global Saturation 1.05. Vignette 0.3. No grain, fringe or outline material; Motion Blur Amount 0. TSR, with glitter emissive clamped below 20 to stop fireflies. To switch a level's hue family, swap the fog, sky and sand instance colours together, never the grade alone.

### UI and effects

No panels. Josefin Sans Thin, letter spacing 300, `#fbe9c6`, fading in over 1.5 s. Niagara: sand spray as GPU sprites emitted from foot sockets, velocity inherited, 1.5 s life, colour sampled from the sand; cloth scraps as mesh particles with a flutter WPO. Pickups emit a soft cream radial glow that swells and fades over 0.8 s.

## Do / Do not

Do:

- Keep the frame in one hue family.
- Add sharp glitter sparkle to smooth sand.
- Dissolve the horizon with haze of the sky colour.
- Keep the figure small and dark.

Do not:

- Do not add thin ink lines and flat fills; that reads as `012`.
- Do not use hard flat colour layers; that reads as `060`.
- Do not grade to teal and orange with gritty machines; that reads as `033`.
- Do not add realistic rock and plant detail; that reads as `032`.

## Nearest styles

- `012` Thin-line pastel desert: `012` draws thin ink contour lines around flat pastel fills; this style has no lines and models the sand with soft glowing gradients.
- `060` Layered flat-colour wilderness: `060` stacks hard-edged flat colour layers that step through several hues into the distance; this style blends one hue family smoothly with no layer edges.
- `033` Teal-orange desert blockbuster: `033` sets teal sky and shadows against orange sand, with gritty rusted machines; this style stays in gold, orange and rust, with smooth clean surfaces.

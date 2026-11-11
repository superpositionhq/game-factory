# Atomic-age Googie

Reference works: Fallout; The Jetsons.

## References

- *Fallout 4* (2015), Bethesda Game Studios, video game. https://en.wikipedia.org/wiki/Fallout_4
- *The Jetsons* (1962), Hanna-Barbera Productions, animated TV series. https://en.wikipedia.org/wiki/The_Jetsons
- *The Incredibles* (2004), Pixar Animation Studios (Brad Bird), animated film. https://en.wikipedia.org/wiki/The_Incredibles
- *Theme Building, Los Angeles International Airport* (1961), Pereira and Luckman with Paul Williams and Welton Becket, architecture. https://en.wikipedia.org/wiki/Theme_Building
- *TWA Flight Center* (1962), Eero Saarinen, architecture. https://en.wikipedia.org/wiki/TWA_Flight_Center

## Visual definition

- **Shape language and proportions:** Optimistic space-age forms: upswept cantilevered roofs, parabolic arches, boomerangs, kidney shapes, starbursts, atoms with orbit rings, flying-saucer discs, tail fins, bubble domes, tapered legs, bullet-shaped robots and rockets.
- **Line and outline:** No outline.
- **Shading model:** Smooth and glossy: enamel paint, chrome trim and coloured plastics with clean highlights.
- **Palette:** `#4fc1c9` `#f26b4f` `#f6d55c` `#f4efe1` `#e8a0b4` `#3b3b3b` `#c9d1d3`. Turquoise, coral, mustard yellow, pink and cream with chrome and charcoal.
- **Lighting:** Bright sunny daylight or a cheerful showroom; neon sign glow at dusk.
- **Texture and surface:** Clean surfaces with printed mid-century patterns: boomerang laminate, starburst wallpaper, terrazzo speckle, wood veneer. Minimal wear.
- **Atmosphere and post-processing:** Slight warm grade and mild bloom on chrome and neon.
- **Camera and framing:** Low three-quarter views emphasising roof sweep; wide lens.
- **UI and typography:** Rounded kidney and boomerang panels with chrome trim and starburst accents; icons are cheerful flat pictograms like 1950s appliance badges. Type mixes a bouncy casual brush script for titles with a bold rounded sans for labels. Counters are chunky cream numerals on turquoise `#4fc1c9` or coral `#f26b4f`, or needle dials like a car dashboard.
- **VFX and motion:** Four-point star twinkles on chrome, atom orbit rings, puffy stylised smoke clouds and ray-gun rings; hits pop as starbursts in coral and mustard. Motion is bouncy and upbeat, with light squash and stretch, quick anticipation and smoothly hovering vehicles.

## Fits

- **Genres:** `action-adventure`, `racing`, `survival-craft`, `simulation`, `vehicle-combat`, `rpg`
- **Moods:** optimistic, playful, cheerful, retro
- **Settings:** 1950s space-age suburb, roadside diner, sky city, world's fair

## Unreal recipe

### Assets

Mid-century and retro-future packs suit this: diners, motels, finned cars, bubble-dome vehicles, bullet robots, tapered-leg furniture. Strip rust, dirt, peeling paint and post-apocalyptic damage from their materials so everything looks new. Build signature shapes by Blender script: upswept cantilever roofs, parabolic arches, boomerang and kidney tabletops, starburst signs on poles, atom models with orbit rings, saucer discs. Generate pattern textures by script too: boomerang laminate, starburst wallpaper, terrazzo speckle.

### Materials

Default Lit throughout, glossy and clean. `M_Enamel`: Clear Coat shading model, base in turquoise `#4fc1c9`, coral `#f26b4f`, mustard `#f6d55c`, pink `#e8a0b4` or cream `#f4efe1`, Clear Coat 1, Clear Coat Roughness 0.05. `M_Plastic`: Default Lit, Roughness 0.25. `M_Chrome`: Metallic 1, Base Colour `#c9d1d3`, Roughness 0.05. `M_Pattern`: the printed textures at Roughness 0.4 on counters, walls and floors, giving surfaces their decoration without wear. Wood veneer uses a fine grain with a satin finish. Neon tubes are Emissive Color at 10 to 20. Charcoal `#3b3b3b` is limited to tyres, trim and asphalt.

### Lighting and atmosphere

Bright sun: Directional Light at 45 to 60 degrees, slightly warm, Source Angle about 1, with Sky Atmosphere, Sky Light on Real Time Capture and a few Volumetric Clouds so chrome has a sky to reflect. Lumen global illumination and reflections on. Virtual Shadow Maps on; shadows are clear but not black. No fog beyond default aerial perspective. For dusk scenes lower the sun and let neon signs and Rect Lights at shop fronts carry the light. Auto exposure with a narrow range.

### Post-processing

White Balance Temp slightly warm; Global Saturation 1.1; Contrast 1.05. Filmic tone curve at defaults. Bloom Intensity 0.4 with Threshold 1.2 so only chrome glints and neon glow. Vignette Intensity 0.15. Film Grain Intensity 0, Scene Fringe Intensity 0, Motion Blur Amount 0. Depth of field off: the whole frame stays sharp, with no tilt-shift blur bands. TSR anti-aliasing.

### UI and effects

UMG panels are kidney and boomerang shaped images with a chrome trim ring and small starburst accents. Titles use a casual brush script such as Pacifico or Lobster; labels use Fredoka or Baloo 2. Counters are chunky cream numerals on turquoise or coral plates; speed and health can be needle dials styled like a car dashboard.

Niagara: four-point star twinkles on chrome, 0.3 s, rotating a quarter turn; atom orbit rings as ribbon loops; puffy smoke as 4 to 6 lit sphere-cluster meshes that scale up with squash and stretch; ray-gun shots as expanding ring meshes. Hits pop a coral and mustard starburst mesh for 0.2 s.

## Do / Do not

Do:

- Use upswept roofs, boomerangs, starbursts and atom motifs.
- Combine turquoise, coral and mustard with chrome.
- Keep surfaces glossy and clean.
- Add tail fins and bubble domes to vehicles.

Do not:

- Do not use dark stepped symmetry with gold and black; that reads as `096`.
- Do not flatten the light and frame symmetrically in muted pastels; that reads as `034`.
- Do not round everything into tiny blurred toys; that reads as `057`.
- Do not add brass gears and rivets; that reads as `095`.

## Nearest styles

- `034` Symmetric pastel dollhouse film: this style has glossy curved forms in vivid turquoise and coral, seen from low three-quarter angles; `034` is flat-lit, muted pastel and strictly symmetric.
- `096` Art Deco streamline: this style is bright and sunny with playful swept curves; `096` is dark and formal, polished in black, gold and teal.
- `057` Toy-diorama tilt-shift: this style shows full-size buildings and vehicles in sharp focus with printed patterns on their surfaces; `057` is plain miniature toys with the top and bottom of the frame blurred.

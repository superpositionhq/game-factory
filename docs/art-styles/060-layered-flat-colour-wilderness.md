# Layered flat-colour wilderness

Reference works: Firewatch.

## References

- *Firewatch* (2016), Campo Santo, video game. https://en.wikipedia.org/wiki/Firewatch
- *Alto's Adventure* (2015), Snowman and Harry Nesbitt, video game. https://en.wikipedia.org/wiki/Alto's_Adventure
- *A Short Hike* (2019), Adam Robinson-Yu, video game. https://en.wikipedia.org/wiki/A_Short_Hike
- *Federal Art Project posters* (1935-1943), Works Progress Administration, screen-printed posters. https://en.wikipedia.org/wiki/Federal_Art_Project

## Visual definition

- **Shape language and proportions:** Landscapes simplified into overlapping silhouette layers: ridge lines, tree lines, rock towers. Trees are simple cone and trunk shapes; rocks are angular blocks.
- **Line and outline:** No outline.
- **Shading model:** Each depth layer is one flat colour. Near objects have two to four flat tones with hard edges.
- **Palette:** `#f25c2a` `#f7a531` `#7a2f5a` `#2b1e3f` `#f9d9a0` `#3f7a6a` `#1c4a5a`. A sunset-style ramp from deep purple foreground through magenta and orange to pale yellow sky, or a green-teal variant for daytime.
- **Lighting:** Low sun behind the layers; strong colour-graded atmospheric perspective.
- **Texture and surface:** Almost none. Flat fills with a few simple shapes for rock faces and tree shadows.
- **Atmosphere and post-processing:** Heavy coloured distance fog that shifts hue with depth; soft sun glow.
- **Camera and framing:** Wide vista from a height, 28 to 35 mm equivalent, horizon in the middle third.
- **UI and typography:** Panels are flat, borderless colour blocks taken from the sunset ramp, and icons are simple one-colour silhouettes. Type is a bold condensed sans or wide display capitals in the manner of 1930s national park posters, in pale yellow on deep purple. Numbers are plain flat numerals in orange or pale yellow.
- **VFX and motion:** Effects stay flat: smoke is stacked hard-edged puffs, fire is two or three orange shapes, and ash, dust and tiny bird silhouettes drift across the layers. Motion is smooth and unhurried, with slow tree sway and distant layers that slide in parallax.

## Fits

- **Genres:** `exploration`, `detective-mystery`, `survival-craft`, `action-adventure`, `sports`
- **Moods:** wistful, calm, lonely
- **Settings:** national park forest, mountain range, canyon country, alpine slopes

## Unreal recipe

### Assets

Compose vistas from silhouette layers: ridge lines, tree lines and rock towers placed at stepped distances. Landscape or simple displaced meshes work for ridges; trees are cone-and-trunk meshes built by script, rocks are angular blocks. A realistic forest pack can be restyled by removing normal maps, roughness and albedo textures entirely and replacing dense foliage cards with solid cone canopies; photographic bark and leaf detail must go. Distant layers can be plain cards with a cut ridge profile. Keep foreground props to large simple shapes.

### Materials

`M_FlatLayer`: Unlit. Near objects (within about 30 m) take a `BaseTone` parameter and step it through two to four hard tones: N·L against a Material Parameter Collection sun vector, quantised with Floor, plus an optional hard-edged shape mask for rock faces and tree shadows. Beyond that, colour is driven only by depth: PixelDepth normalised between `NearDist` and `FarDist` indexes a CurveAtlasRowParameter ramp running `#2b1e3f`, `#7a2f5a`, `#f25c2a`, `#f7a531`, `#f9d9a0` (a second curve row holds the teal day variant `#1c4a5a`, `#3f7a6a`). Quantise the depth lookup into 6 to 8 steps so each ridge resolves to one flat colour. No smooth gradients across a surface and no texture.

### Lighting and atmosphere

Lumen off; surfaces are Unlit. No Directional Light is needed, but a sun disc mesh with an emissive Unlit material sits low behind the layers. The sky is a dome with a flat banded gradient ending in `#f9d9a0`. Exponential Height Fog may add a thin tinted haze between layers, with Fog Inscattering Color matched to the ramp and Volumetric Fog off; the material ramp remains the main depth cue. Manual exposure.

### Post-processing

Bloom Intensity 0.5 with Threshold 1 for a soft sun glow only. Tone Curve Amount 0 so ramp colours are exact. TSR on. Vignette 0.2. Grain, fringe, depth of field, Ambient Occlusion and Motion Blur Amount 0. No outline, paper or watercolour materials. Camera 28 to 35 mm equivalent from a height, horizon in the middle third.

### UI and effects

Panels are flat borderless Border widgets in ramp colours, pale yellow text on deep purple `#2b1e3f`. Headings in Bebas Neue or League Spartan capitals with wide tracking, like park posters; numbers plain in `#f25c2a` or `#f9d9a0`. Icons are one-colour silhouettes. Niagara stays flat: smoke as stacked hard-edged Unlit puff sprites with no alpha fade (scale down to vanish, lifetime 3 s), fire as two or three orange shapes swapping at 8 fps, drifting ash and tiny bird silhouettes (5 to 10) crossing far layers slowly. Trees sway through World Position Offset at low amplitude.

## Do / Do not

Do:

- Reduce the landscape to flat-colour depth layers.
- Drive colour by depth through a fixed ramp.
- Keep the foreground darkest and the sky lightest.
- Use simple cone trees and angular rocks.

Do not:

- Do not use watercolour texture and pale washes; that reads as `025`.
- Do not use only a handful of flat colours with cut-paper figures; that reads as `064`.
- Do not add smooth sand shading and sparkle; that reads as `061`.
- Do not go dark with theatrical spotlights; that reads as `065`.

## Nearest styles

- `064` Mid-century cut-paper poster: this style stacks many depth layers with coloured haze between them, along a full sunset ramp; `064` is a single flat sheet of a few paper colours with no depth haze.
- `061` Soft-gradient minimal desert: near objects here have hard-edged flat tones in strong sunset colour; `061` has smooth soft gradients across its dunes.
- `066` Faceted low-poly gradient: fog here flattens each distant layer to one colour; `066` shows a separately shaded facet on every triangle.

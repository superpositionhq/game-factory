# Metaphysical long-shadow plaza

Reference works: Giorgio de Chirico; Ico.

## References

- *The Song of Love* (1914), Giorgio de Chirico, oil painting. https://en.wikipedia.org/wiki/The_Song_of_Love
- *Mystery and Melancholy of a Street* (1914), Giorgio de Chirico, oil painting. https://en.wikipedia.org/wiki/Mystery_and_Melancholy_of_a_Street
- *Ico* (2001), Team Ico (Fumito Ueda), video game. https://en.wikipedia.org/wiki/Ico
- *The Persistence of Memory* (1931), Salvador Dali, oil painting. https://en.wikipedia.org/wiki/The_Persistence_of_Memory
- *The Disquieting Muses* (1916-1918), Giorgio de Chirico, oil painting. https://en.wikipedia.org/wiki/The_Disquieting_Muses

## Visual definition

- **Shape language and proportions:** Empty town squares with long arcades of round arches, a tower or chimney, a statue or mannequin, a few isolated objects (a ball, a glove, a train on the horizon). Simple, smooth, solid volumes; steep, inconsistent perspective.
- **Line and outline:** No outline.
- **Shading model:** Simple firm modelling in three to five tone steps; cast shadows are large, flat, very dark shapes with hard edges.
- **Palette:** `#d9a441` `#c8553d` `#2f5d50` `#1f3a4d` `#e9d9a6` `#6b4a32` `#f2efe2`. Ochre and terracotta buildings, dark green-teal sky that lightens to yellow at the horizon, deep brown-black shadows.
- **Lighting:** Very low late-afternoon sun producing shadows two to five times longer than the objects; shadow directions need not agree.
- **Texture and surface:** Smooth, matte painted surfaces with slight dry-brush unevenness.
- **Atmosphere and post-processing:** None; clear air with no haze.
- **Camera and framing:** Wide angle from slightly above, with exaggerated converging lines; deep empty foreground.
- **UI and typography:** Panels are plain flat rectangles in ochre or pale cream with a hard dark drop shadow, offset like a cast shadow, and no ornament; icons are simple solid silhouettes (arch, tower, ball, clock). Text is a classical Roman serif in widely spaced capitals, in deep brown or cream. Counters use old-style serif numerals, with terracotta for warnings.
- **VFX and motion:** Particles are few: a train's smoke plume as a firm white shape, a flag that moves in a wind nothing else feels. A hit shows as a brief flat flash and a jump of the long shadow. Motion is slow and deliberate with long stillness, and moving objects are read by their sliding hard shadows.

## Fits

- **Genres:** `puzzle`, `exploration`, `action-adventure`, `detective-mystery`, `stealth`, `platformer`
- **Moods:** eerie, melancholic, lonely, dreamlike
- **Settings:** empty Italian piazza, deserted seaside town, ruined castle

## Unreal recipe

### Assets

The world is built mostly from scratch by Geometry Script or Blender: long arcades of identical round arches, plain towers and chimneys, a plinth with a statue or tailor's mannequin, a distant train, a ball, a glove. Keep volumes smooth and solid with bevelled edges and no trim. If a Mediterranean town pack is used, delete weathering decals, shutters, signage and clutter, remove normal maps and repaint albedo to plain ochre `#d9a441`, terracotta `#c8553d` and cream `#e9d9a6`.

### Materials

Master `M_PlazaMatte`, Default Lit, Roughness 1, Specular 0, no normal map. Base Colour is a flat parameter multiplied by a faint WorldAlignedTexture dry-brush mask (variation under 6%). Firm modelling comes from the post-process chain, not the material.

### Lighting and atmosphere

One Directional Light at 10 to 20 degrees elevation, warm white, Source Angle 0 for razor-hard shadow edges; shadows then run two to five times object height. Virtual Shadow Maps on. Lumen global illumination off (`r.DynamicGlobalIlluminationMethod=0`); a Sky Light with a fixed dark cubemap gives low flat fill so shadows stay deep brown-black `#6b4a32` darkened further. To make shadow directions disagree, give chosen props a second Directional Light on its own Lighting Channel with a different yaw. No Exponential Height Fog and no Sky Atmosphere: the sky is an Unlit dome with a vertical gradient from `#1f3a4d` through `#2f5d50` to yellow `#d9a441` at the horizon. Manual exposure.

### Post-processing

A post-process material at Scene Color Before Bloom divides PostProcessInput0 by DiffuseColor, quantises the light term into four steps with Floor, and multiplies back; the shadow step is pushed to near-black so cast shadows become flat hard shapes. Volume settings: Tone Curve Amount 0.3, Saturation 0.95, Bloom Intensity 0, Vignette Intensity 0, grain 0, Ambient Occlusion Intensity 0, Motion Blur Amount 0, deep focus. TSR anti-aliasing. Camera field of view 95 to 105 degrees from slightly above.

### UI and effects

UMG panels are flat ochre or cream Box brushes, square corners, each with a duplicate dark image offset 14 px right and 10 px down as a cast shadow. Font is Cinzel in capitals with wide letter spacing, deep brown `#6b4a32` or cream; counters use EB Garamond old-style figures, terracotta for warnings.

Niagara is sparse: the train's plume is 6 to 8 opaque white mesh puffs with Lit shading that hold shape for 6 s; one flag animates with World Position Offset while nothing else moves. A hit is a single-frame flat cream flash on the target, and C++ nudges the sun yaw by 2 degrees for 0.1 s so the long shadow jumps.

## Do / Do not

Do:

- Cast very long, hard, dark shadows.
- Leave the plaza almost empty.
- Repeat round arches in long receding rows.
- Use a dark green sky that turns yellow at the horizon.

Do not:

- Do not use an isometric camera with pastel three-tone faces and no shadows; that reads as `059`.
- Do not use hazy single-hue sand and soft light; that reads as `061`.
- Do not go to deep black backgrounds with a spotlight on figures; that reads as `085`.
- Do not add weathering detail.

## Nearest styles

- `059` Isometric pastel impossible architecture: this style has a perspective camera with steep converging lines, earthy ochre and terracotta, and very long hard cast shadows; `059` has an isometric view, pastel faces in three flat tones and no cast shadows.
- `061` Soft-gradient minimal desert: this style has firm tone steps, hard dark shadows, clear air and ochre walls against a green sky; `061` has smooth gradients, haze, soft light and one hue family across the scene.
- `097` Brutalist concrete: this style has warm ochre and terracotta arcades under a green and yellow sky; `097` is raw grey concrete with almost no colour.

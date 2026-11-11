# Glowing forest painterly

Reference works: Ori and the Blind Forest.

## References

- *Ori and the Blind Forest* (2015), Moon Studios, video game. https://en.wikipedia.org/wiki/Ori_and_the_Blind_Forest
- *Ori and the Will of the Wisps* (2020), Moon Studios, video game. https://en.wikipedia.org/wiki/Ori_and_the_Will_of_the_Wisps
- *Trine 2* (2011), Frozenbyte, video game. https://en.wikipedia.org/wiki/Trine_2
- *Rayman Legends* (2013), Ubisoft Montpellier, video game. https://en.wikipedia.org/wiki/Rayman_Legends

## Visual definition

- **Shape language and proportions:** Organic, twisting forest forms: gnarled roots, hanging vines, mushrooms, mossy rocks. The hero is a small, simple, glowing white figure.
- **Line and outline:** No outline. Foreground elements are dark silhouettes.
- **Shading model:** Soft painted gradients with strong glow light sources. Smooth.
- **Palette:** `#0d1b2a` `#1b4965` `#5fa8d3` `#bee9e8` `#ffd166` `#7b2cbf` `#2d6a4f` `#ffffff`. Deep blue and teal night forest with cyan, gold and violet light sources and a white-glowing hero.
- **Lighting:** Many small emissive sources (spirit lights, glowing plants) and shafts of light; strong backlight.
- **Texture and surface:** Painterly foliage and bark with soft detail; layered depth with blurred near and far planes.
- **Atmosphere and post-processing:** Heavy bloom, light shafts, floating particles, depth of field on foreground and background layers, vignette.
- **Camera and framing:** Side-on, layered parallax; medium-wide.
- **UI and typography:** Frameless UI: glowing icons and thin luminous lines laid directly over the scene, with round orbs for health and energy. Text is a light, elegant serif with a soft glow, and counters are small glowing numerals. UI colours are pale cyan `#bee9e8` and white `#ffffff`, with gold `#ffd166` for pickups.
- **VFX and motion:** Dense particles: glowing motes, drifting leaves, light trails behind the hero and soft sparkle bursts on hits. Animation is quick and fluid, with strong squash and stretch and bright arcs on jumps and dashes.

## Fits

- **Genres:** `platformer`, `exploration`, `action-adventure`, `puzzle`
- **Moods:** wondrous, bittersweet, magical
- **Settings:** enchanted night forest, glowing caverns, ancient spirit trees, misty swamps

## Unreal recipe

### Assets

Organic forest assets: gnarled roots, vines, mushrooms, mossy rocks, large trunks. Store foliage packs work when stripped of fine detail: blur albedo and normal maps by script and repaint leaves toward `#2d6a4f` and `#1b4965`. Arrange the level as depth layers for a side-on camera: a near silhouette layer, the play layer, and three or four background layers. Build glowing plants, spirit orbs and lantern fruit from scratch as simple meshes with emissive caps. The hero is a small, simple white character.

### Materials

`M_ForestPaint`, Default Lit, Roughness 0.85, soft normals, with a top-down painted gradient and a `Fresnel` rim tinted `#5fa8d3` to fake backlight. Foliage uses Two Sided Foliage so backlight passes through leaves. `M_Glow`, Unlit, drives plants and orbs at 8 to 20 times scene white in `#bee9e8`, `#ffd166` or `#7b2cbf`, pulsing slowly with `Time`. The near silhouette layer gets an instance with BaseColor `#0d1b2a` and no emissive, on a separate Lighting Channel so glows do not light it. The hero material is Unlit white at 25 times scene white: the brightest object on screen.

### Lighting and atmosphere

Lumen GI on, with emissive meshes contributing; back them with 10 to 20 small Point Lights (radius 300 to 600, no shadows) where pools of colour are needed. One strong Directional or Spot backlight in pale cyan aimed toward the camera, Volumetric Scattering Intensity 3 to 4. Exponential Height Fog with Volumetric Fog on, Fog Inscattering Color `#1b4965`, so shafts form between trunks and the far forest stays deep blue, never grey or black. Virtual Shadow Maps on. Manual exposure.

### Post-processing

Bloom Method Standard, Intensity 1.2 to 1.5, Threshold 0.8: heavy, the main signature. Depth of Field with Focal Distance on the play layer and Aperture F-stop about 1.4 so foreground and background layers blur. Vignette Intensity 0.5. Shadows graded toward blue, highlights left clean. An optional light 4 px Kuwahara pass at Scene Color Before DOF softens leaf detail into paint. No outline material. Film Grain 0, Scene Fringe 0, Motion Blur Amount 0. TSR.

### UI and effects

Frameless UMG: health and energy are rows of round orb images with an additive glow sprite behind; thin luminous lines replace panels. Text in Cormorant Light with a soft outer glow from a blurred duplicate layer, `#bee9e8` and white, pickups in `#ffd166`. Niagara is dense: 200 to 400 GPU sprite motes drifting for 5 to 8 s across each screen, mesh leaves falling, a ribbon trail of 0.4 s behind the hero, and 12 to 20 sparkle sprites bursting for 0.3 s on hits, all additive.

## Do / Do not

Do:

- Put a dark silhouette layer in front and blurred layers behind.
- Use many small glowing sources with strong bloom.
- Make the hero the brightest object.
- Add drifting particles and light shafts.

Do not:

- Do not use pure black silhouettes on grey fog without colour; that reads as `070`.
- Do not cover plants in neon patterns with photoreal detail; that reads as `093`.
- Do not light evenly with painted albedo detail; that reads as `023`.
- Do not add outlines.

## Nearest styles

- `093` Bioluminescent alien jungle: this style has soft painted forms, gentle glow and a visible deep-blue forest behind; `093` is almost black, with sharp realistic leaf detail and vivid neon patterns.
- `070` Silhouette fog monochrome: behind the dark foreground this style is full of colour, in deep blue, cyan, gold and violet; `070` uses only black and greys.
- `023` Chunky hand-painted fantasy: this style is dark, with glowing light sources and heavy bloom; `023` is bright and evenly lit, with detail painted onto the surfaces.

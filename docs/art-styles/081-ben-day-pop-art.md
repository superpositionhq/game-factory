# Ben-Day pop art

Reference works: Roy Lichtenstein.

## References

- *Whaam!* (1963), Roy Lichtenstein, acrylic and oil painting. https://en.wikipedia.org/wiki/Whaam!
- *Drowning Girl* (1963), Roy Lichtenstein, oil and acrylic painting. https://en.wikipedia.org/wiki/Drowning_Girl
- *Look Mickey* (1961), Roy Lichtenstein, oil painting. https://en.wikipedia.org/wiki/Look_Mickey
- *Oh, Jeff...I Love You, Too...But...* (1964), Roy Lichtenstein, oil and acrylic painting. https://en.wikipedia.org/wiki/Oh,_Jeff...I_Love_You,_Too...But...
- *Marilyn Diptych* (1962), Andy Warhol, silkscreen painting. https://en.wikipedia.org/wiki/Marilyn_Diptych

## Visual definition

- **Shape language and proportions:** Enlarged comic-panel imagery: simplified glamorous faces, machines, explosions as spiky bursts, smoke as scalloped clouds. Shapes are clean and mechanical.
- **Line and outline:** Thick black outlines of even or smoothly swelling weight around every form; black shapes for hair and shadow.
- **Shading model:** None beyond black shadow shapes. Tone is given by a regular grid of large dots (red dots on white for skin, blue dots for sky) or by parallel stripes.
- **Palette:** `#000000` `#ffffff` `#e3202a` `#ffd500` `#1747b5` `#f7c8b0`. Primary red, yellow and blue with black and white. Nothing else.
- **Lighting:** None.
- **Texture and surface:** Mechanical Ben-Day dots: uniform size, perfectly regular grid, large enough to see individually (dot pitch about 1.2 to 2% of frame height).
- **Atmosphere and post-processing:** None; hard clean edges.
- **Camera and framing:** Tight crop like a single comic panel; flat.
- **UI and typography:** Panels are yellow caption boxes with black borders and white speech balloons with pointed tails; icons are thick-outlined black shapes with one flat primary fill. Text is hand-lettered comic capitals in black, bold italic for emphasis. Damage numbers and counters are heavy slanted block numerals in red or yellow with a black outline, set inside spiky burst shapes.
- **VFX and motion:** Hits are spiky red-and-yellow starbursts with a lettered sound word; smoke is scalloped outlined clouds and speed is drawn as straight black lines. Motion uses snappy held poses that change on twos or threes, like one panel replacing another, with no blur.

## Fits

- **Genres:** `fighting`, `vehicle-combat`, `top-down-shooter`, `platformer`, `puzzle`
- **Moods:** bold, ironic, melodramatic
- **Settings:** 1960s America, aerial dogfight, comic-book city

## Unreal recipe

### Assets

Pick models with clean, mechanical silhouettes: stylised faces, aircraft, cars, simple city blocks. On a realistic store pack, delete normal, roughness and ambient-occlusion maps and replace every albedo with one flat palette colour per material slot. Build from scratch in Blender background mode the things packs never have: spiky burst meshes, scalloped smoke clouds, speech-balloon planes with pointed tails, and black hair and shadow shapes as separate flat-coloured shells.

### Materials

One Unlit master, `M_BenDay`, authored with `unreal.MaterialEditingLibrary`. Parameters: `FillColour`, `DotColour`, `DotMode` (0 solid, 1 dots, 2 stripes), `DotPitch`. A Custom HLSL node takes ScreenPosition, corrects for aspect ratio, rotates the grid 45 degrees and returns `step(length(frac(uv * N) - 0.5), Radius)`; N gives a pitch of 1.5% of frame height (about 66 rows), and Radius stays constant so every dot is the same size. Instances: skin is `#e3202a` dots on `#ffffff` (not the peach flat), sky is `#1747b5` dots on white, machines are solid `#ffd500` or `#e3202a`, hair and shadow shells are solid `#000000`.

### Lighting and atmosphere

No lighting. Turn Lumen off (`r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`), disable Virtual Shadow Maps, and place no fog, sky atmosphere or sky light. The background is an Unlit dome in white or dotted blue. Exposure is Manual with Exposure Compensation set so Unlit colours reach the screen unchanged.

### Post-processing

Post Process Volume, unbound: Bloom Intensity 0, Film Grain Intensity 0, Vignette Intensity 0, Scene Fringe Intensity 0, Motion Blur Amount 0, no depth of field, Tone Curve Amount 0 and Expand Gamut 0 so the primaries stay pure. One post-process material at Scene Color After Tonemapping draws the outline: a Sobel on CustomStencil (one stencil value per form, `r.CustomDepth=3`) plus SceneDepth, dilated to 5 to 7 px at 1080p and output as `#000000`. The line is even and thick around every form. Use FXAA (`r.AntiAliasingMethod=1`).

### UI and effects

UMG: caption boxes are `#ffd500` Box brushes with a 4 px black border; dialogue sits in white balloon images with tails. Font is Bangers in black capitals; emphasis uses the italic slant. Damage numbers use Anton with a 3 px black Slate outline in `#e3202a` or `#ffd500`, placed on a spiky burst image rotated 8 degrees.

Niagara: hits spawn one mesh-renderer starburst (red outer, yellow inner, black rim) that scales from 0.6 to 1.2 in 0.08 s, holds 0.2 s, then disappears with no fade, plus a lettered sound-word sprite. Smoke is 3 to 5 scalloped cloud meshes stepping through sizes at 8 frames per second. Speed lines are straight black ribbon segments lasting 0.15 s.

## Do / Do not

Do:

- Use only red, yellow, blue, black and white.
- Fill skin and sky with large regular dots.
- Outline everything in thick black.
- Crop like a single comic panel.

Do not:

- Do not use small varied screens, colour offsets and many hues; that reads as `009`.
- Do not use free round paint dots without outlines; that reads as `077`.
- Do not use flat fills with thin even lines and no dots; that reads as `011`.
- Do not add gradients or grain; that reads as `007`.

## Nearest styles

- `009` Halftone print comic: this style puts a thick black outline around every form and uses only red, yellow, blue, black and white with large uniform dots; `009` outlines selectively, uses small dot screens of varied size with colour offsets, and prints many more hues.
- `011` Clear-line adventure comic: this style fills skin and sky with large visible dots inside thick outlines; `011` has plain flat fills with thin even lines and no dots.
- `079` Primary grid neoplasticism: this style shows curved outlined faces, machines and explosions filled with dots; `079` is only plain rectangles of primary colour divided by straight black bars.

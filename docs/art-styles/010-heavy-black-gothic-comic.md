# Heavy-black gothic comic

Reference works: Hellboy (Mike Mignola).

## References

- *Hellboy: Seed of Destruction* (1994), Mike Mignola (Dark Horse Comics), comic book. https://en.wikipedia.org/wiki/Hellboy:_Seed_of_Destruction
- *Hellboy* (1993), Mike Mignola (Dark Horse Comics), comic book series. https://en.wikipedia.org/wiki/Hellboy
- *Batman: The Animated Series* (1992), Warner Bros. Animation, animated TV series. https://en.wikipedia.org/wiki/Batman:_The_Animated_Series
- *Darkest Dungeon* (2016), Red Hook Studios, video game. https://en.wikipedia.org/wiki/Darkest_Dungeon
- *The Amazing Screw-On Head* (2002), Mike Mignola (Dark Horse Comics), comic book. https://en.wikipedia.org/wiki/The_Amazing_Screw-On_Head

## Visual definition

- **Shape language and proportions:** Blocky, angular simplification. Figures have heavy torsos, small legs and squared hands. Architecture is slabs, arches and broken statues.
- **Line and outline:** Medium-weight angular outline; many edges vanish into black shadow shapes instead of being drawn.
- **Shading model:** Two bands: flat colour and solid black. Black shadow covers 40 to 60% of each form with a jagged, designed edge.
- **Palette:** `#0b0b0c` `#b3261e` `#4a5a63` `#c8a45a` `#2f3b2f` `#d9d2c0`. Muted slate, olive and ochre flats with one strong red accent. Black dominates.
- **Lighting:** Single hard light from above or the side; no fill, no bounce.
- **Texture and surface:** None. Colour areas are perfectly flat. Detail is suggested with a few small black notches.
- **Atmosphere and post-processing:** None. Optional very light paper tint.
- **Camera and framing:** Static, formal compositions; figures small against large black architecture.
- **UI and typography:** Plain black panels with a thin bone-coloured (`#d9d2c0`) rule and squared corners, like comic gutters and caption boxes. Type is angular hand-lettered capitals with uneven, chiselled strokes; icons are flat black-and-ochre silhouettes. Numbers are blocky bone digits, with red (`#b3261e`) kept for damage and warnings.
- **VFX and motion:** Effects are flat designed shapes: jagged black smoke, angular flame in ochre and red, and hard-edged white flash cuts on impact. Motion is sparse and heavy: strong poses held long, few in-between frames and no soft trails.

## Fits

- **Genres:** `survival-horror`, `roguelike`, `detective-mystery`, `action-adventure`, `soulslike`, `hack-and-slash`
- **Moods:** ominous, brooding, pulpy
- **Settings:** ruined abbey, gothic crypt, haunted castle, art deco night city

## Unreal recipe

### Assets

Pick blocky architecture: slabs, arches, stairs, broken statues, heavy doors. From a realistic gothic pack, delete every texture, decimate ornament, and set normals to flat (hard edges on all faces) by script so the light and shadow boundary breaks along polygon edges and reads angular. Characters need heavy torsos, small legs and squared hands; adjust bone scales, and split vertex normals on the character mesh too. Small black notch meshes or decals suggest cracks and bricks.

### Materials

`M_BlackCut` is Unlit. Inputs: one flat colour parameter from the muted set (`#4a5a63`, `#2f3b2f`, `#c8a45a`, `#d9d2c0`) and a light direction from a Material Parameter Collection. Output is `Step(threshold, N·L)` choosing between the flat colour and `#0b0b0c`, with the threshold raised to about 0.2 so black covers 40 to 60 percent of each form. A low-frequency world-space noise added before the Step gives the edge a designed jag on large curved surfaces. No texture, gradient or hatch. Red `#b3261e` is a separate instance used on one accent per scene. Cast shadows are needed for architecture: give floors and walls a Default Lit variant with black base colour response handled in post (below).

### Lighting and atmosphere

One Directional Light from above or the side, Source Angle 0, Virtual Shadow Maps on. No Sky Light, no Lumen GI, no reflections, no fog. With no fill, any shadowed Default Lit surface is already black.

### Post-processing

Two passes at Scene Color After Tonemapping, Tone Curve Amount 0:

1. `PP_Crush`: for Default Lit pixels, threshold the recovered light term (PostProcessInput0 over BaseColor) and output either BaseColor or `#0b0b0c`, so cast shadows become solid black shapes with hard edges.
2. `PP_AngularLine`: edge detect on WorldNormal and SceneDepth, 2 to 3 px, drawn only where both neighbouring pixels are non-black, so edges vanish inside shadow shapes.

An optional multiply by a very light paper tint follows. Bloom, grain, vignette, fringe, ambient occlusion and depth of field off; Motion Blur Amount 0. FXAA.

### UI and effects

Panels are black Box brushes with a 1 px `#d9d2c0` rule and square corners, laid out like caption boxes with gutters. Text is an angular chiselled capital face (Metal Mania, New Rocker) in bone; icons are flat black and ochre silhouettes. Digits are blocky bone numerals, red only for damage and warnings. Niagara: jagged black smoke as Masked flipbook sprites stepped at 8 fps, angular flame cards in ochre and red, and a one-frame white full-screen flash on impact. No soft sprites, no trails, long holds between poses.

## Do / Do not

Do:

- Let black shadow shapes cover about half of each form.
- Use flat normals so shadow edges are angular.
- Keep one saturated accent colour.
- Leave colour areas completely flat.

Do not:

- Do not add hatching or wear textures; that reads as `001`.
- Do not go greyscale with a single colour spot; that reads as `069`.
- Do not fill the frame with saturated red; that reads as `008`.
- Do not add gradients or soft shadows.

## Nearest styles

- `069` Selective-colour ink noir: this style puts flat muted colour fills beside its black; `069` is only black and white with one small spot of colour.
- `008` Red-black pop-punk graphic cel: this style uses muted slate, olive and ochre with one small red accent in static compositions; `008` is brighter, flooded with pure red, tilted and jagged.
- `001` Ink-outline comic cel: this style has perfectly flat colour and solid black shadow shapes; `001` hatches its shadows, draws wear marks and shades in three tone steps.

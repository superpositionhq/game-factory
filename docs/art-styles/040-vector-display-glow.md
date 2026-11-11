# Vector display glow

Reference works: Asteroids; Battlezone.

## References

- *Asteroids* (1979), Atari, Inc., arcade video game. https://en.wikipedia.org/wiki/Asteroids_(video_game)
- *Battlezone* (1980), Atari, Inc., arcade video game. https://en.wikipedia.org/wiki/Battlezone_(1980_video_game)
- *Tempest* (1981), Atari, Inc., arcade video game. https://en.wikipedia.org/wiki/Tempest_(video_game)
- *Star Wars* (1983), Atari, Inc., arcade video game. https://en.wikipedia.org/wiki/Star_Wars_(1983_video_game)
- *Vectrex* (1982), Smith Engineering, vector display game console. https://en.wikipedia.org/wiki/Vectrex

## Visual definition

- **Shape language and proportions:** Wireframe only. Objects are minimal edge sets: a tank is about 30 lines, a mountain range one polyline. No filled surfaces.
- **Line and outline:** Bright glowing lines of constant width on black. Line ends and corners are brighter dots where the beam dwells.
- **Shading model:** None. Brightness varies only per line (beam intensity).
- **Palette:** `#000000` `#39ff14` `#ffffff` `#00e5ff` `#ff2a2a` `#ffe600`. One phosphor colour (green or white) on black, or a few pure colours for colour vector monitors.
- **Lighting:** None.
- **Texture and surface:** None.
- **Atmosphere and post-processing:** Phosphor glow around lines, short persistence trails on motion, slight flicker.
- **Camera and framing:** First-person or top-down; perspective lines converge to a flat horizon.
- **UI and typography:** The UI is drawn with the same glowing strokes as the world: no panels or fills, only thin line brackets, a line crosshair and wireframe icons such as small ship outlines for lives. Type is a monospaced stroke face in capitals, built from straight segments. Scores are large segment numerals at the top in phosphor green `#39ff14` or white, with red `#ff2a2a` for warnings on colour displays.
- **VFX and motion:** A destroyed object breaks into its separate line segments, which fly apart, spin and fade; shots are bright dots and short dashes, and a big hit flashes the whole screen for a moment. Motion is smooth and rigid: objects drift and rotate with inertia and never deform.

## Fits

- **Genres:** `top-down-shooter`, `vehicle-combat`, `fps`, `racing`, `simulation`
- **Moods:** stark, tense, hypnotic
- **Settings:** deep space, wireframe battlefield, geometric tunnel, trench run

## Unreal recipe

### Assets

Only edges are drawn, so every model is built from scratch as a minimal edge set: a tank of about 30 lines, a mountain range as one polyline. A Blender script converts each low-polygon mesh's chosen edges into thin camera-facing strips (two triangles per edge, with the edge direction and a side sign stored in UV channels) and exports a matching black occluder mesh, shrunk slightly, to hide back edges. Store packs serve only as shapes to trace. No textures at all.

### Materials

`M_VectorLine`, Unlit, Additive. World Position Offset expands each strip in screen space using the stored edge direction and CameraVectorWS, scaled by PixelDepth so width is constant on screen (about 2 px at 1080p). Emissive is the phosphor colour (`#39ff14` or white, or one of `#00e5ff`, `#ff2a2a`, `#ffe600` on colour displays) times a per-line beam intensity from Custom Primitive Data. A UV-based term brightens the last few percent at each end, giving the dwell dots at corners. `M_Occluder` is Unlit opaque black.

### Lighting and atmosphere

No lights. Lumen off (`r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`), shadows and ambient occlusion off, no fog, no sky: the world is `#000000`. The horizon is a single line strip. Manual exposure fixed so line emissive of about 4 sits just above bloom threshold.

### Post-processing

Bloom is the phosphor glow: Method Standard, Intensity 1.5, Threshold 0.5, with a tight inner size and a wide faint outer size. Persistence: a post material at Scene Color After Tonemapping blends the current frame with a render target holding the previous output multiplied by 0.75, updated each frame from C++, so moving lines leave trails of 3 to 5 frames. A `Time`-driven 2 to 3 percent brightness flicker is added in the same material. Render at full resolution with TSR or FXAA so lines stay smooth; never lower `r.ScreenPercentage`. Grain 0, Vignette 0.2 for tube falloff, Scene Fringe 0, depth of field off, Motion Blur Amount 0.

### UI and effects

UMG uses the same strokes: line brackets, a line crosshair, small wireframe ship outlines for lives, all as 2 px line textures or a User Interface material, with no panels or fills. Wrap the HUD in a Retainer Box with a blur-and-add glow material. Type must be a stroke face: generate a segment font texture by script for capitals and numerals; scores are large at the top in `#39ff14`, warnings `#ff2a2a`. Destruction: swap the object for its separate line strips as mesh particles that fly apart, spin and fade over 1.2 s. Shots are bright dots and short dashes; a big hit flashes the screen for 0.1 s.

## Do / Do not

Do:

- Draw edges only, on pure black.
- Add glow and short persistence trails.
- Brighten vertices where lines meet.
- Hide back edges with a black occluder mesh.

Do not:

- Do not fill surfaces with dark colour and emissive trim; that reads as `088`.
- Do not add a gradient sunset and filled mountains; that reads as `090`.
- Do not draw white lines on blue with dimension marks; that reads as `062`.
- Do not use pixel-stepped raster lines at low resolution.

## Nearest styles

- `088` Neon grid cyberspace: only lines exist here, so objects are see-through wireframes; `088` has solid dark glossy surfaces that carry light strips and reflect their glow.
- `062` Blueprint technical drawing: this style is glowing lines on pure black; `062` is crisp white lines without glow on a blue paper ground, with dimension marks.
- `090` Synthwave sunset grid: this style uses one phosphor colour or a few pure line colours and fills nothing; `090` has a gradient sky, a large striped sun and magenta and cyan fills.

# Flat-vector stage light

Reference works: Kentucky Route Zero.

## References

- *Kentucky Route Zero* (2013), Cardboard Computer, video game. https://en.wikipedia.org/wiki/Kentucky_Route_Zero
- *Nighthawks* (1942), Edward Hopper, oil painting. https://en.wikipedia.org/wiki/Nighthawks_(Hopper)
- *Night in the Woods* (2017), Infinite Fall, video game. https://en.wikipedia.org/wiki/Night_in_the_Woods
- *Oxenfree* (2016), Night School Studio, video game. https://en.wikipedia.org/wiki/Oxenfree

## Visual definition

- **Shape language and proportions:** Simple flat-faced geometry seen side-on like a stage set: buildings with one wall removed, long horizontal roads, thin poles and wires, small faceless figures built from a few polygons.
- **Line and outline:** No outline.
- **Shading model:** Flat colour per face. Light appears as hard-edged geometric shapes: cones from lamps, rectangles from doorways.
- **Palette:** `#0d1117` `#1f2a36` `#e8d9a8` `#3a6f7a` `#c2543c` `#56616e`. Near-black and deep blue-grey with a pale yellow light colour and one muted accent.
- **Lighting:** Night. Isolated practical lights cut clear shapes out of darkness; most of the frame is dark.
- **Texture and surface:** None. Pure flat vector fills.
- **Atmosphere and post-processing:** None, or a very faint glow on light shapes.
- **Camera and framing:** Side-on, distant, slow horizontal moves; long lens or orthographic. Subjects small with much negative space.
- **UI and typography:** Dialogue and menus are plain text on the dark ground with no frame, or inside a thin 1 px ruled box; icons are simple flat geometric shapes. Text is a small monospaced or plain grotesque sans in pale yellow `#e8d9a8`, with unselected choices in grey `#56616e` and highlights in teal `#3a6f7a` or rust `#c2543c`; numerals are plain and the same size as the text.
- **VFX and motion:** Few particles. Effects are flat shapes: a light cone that switches on, a rectangle of light that slides across a floor, flat dots for fireflies and dust. Motion is slow and theatrical, with gentle eases, sets that slide or rotate like stage flats, and figures that walk with simple unexaggerated steps.

## Fits

- **Genres:** `detective-mystery`, `exploration`, `puzzle`, `stealth`
- **Moods:** melancholic, quiet, eerie
- **Settings:** rural highway at night, small-town America, abandoned mine, roadside gas station

## Unreal recipe

### Assets

Stage sets viewed from the side: buildings modelled as open boxes with the near wall missing, a long road strip, poles, wires as thin strips, a pickup truck from a dozen polygons. Build by Blender script or Geometry Script. Figures are 100 to 200 triangles, no faces, on a standard skeleton with plain walk clips. Light shapes are geometry too: cone meshes under each lamp, floor quads in front of doorways, window parallelograms on the ground.

### Materials

All surfaces use an Unlit master, `M_Flat`, one colour per face group through material instances: `#0d1117` for most of the world, `#1f2a36` for planes one step forward, `#56616e` for the few readable edges, and `#3a6f7a` or `#c2543c` for a single accent object per scene. Light is not computed. `M_LightShape` is Unlit translucent in `#e8d9a8` at fixed opacity 0.85 with hard mesh edges and no falloff gradient. Surfaces inside a light shape switch colour instead of being lit: a second instance colour, selected in the material by a signed-distance test against cone or box parameters passed through Custom Primitive Data, with a Step and no smoothing.

### Lighting and atmosphere

No dynamic lights and no Lumen; set GI and reflection methods to 0. No Sky Atmosphere, no height fog, no volumetrics; the sky is the clear colour `#0d1117`. Roughly three quarters of every frame must remain the two darkest colours. Manual exposure, compensation 0.

### Post-processing

Tone Curve Amount 0 so the six hex colours are exact. Bloom Intensity at most 0.15 with Threshold set so only `#e8d9a8` contributes; that is the faint glow and the only effect. Grain 0, vignette 0, fringe 0, depth of field off, Motion Blur Amount 0, no outline or edge pass. Anti-aliasing with TSR at native resolution; edges must be clean vector edges, never pixelated. Camera: orthographic or a 10 to 15 degree field of view, moving only horizontally.

### UI and effects

Dialogue is bare text on the dark ground or inside a Border with a 1 px `#56616e` outline and no fill. Use IBM Plex Mono at 14 to 16 px: body `#e8d9a8`, unselected choices `#56616e`, hover `#3a6f7a`, rare warnings `#c2543c`. Numerals share the text size.

Effects are mostly C++ transforms: a light cone toggles visibility in one frame, a door rectangle slides its floor quad over 2 s, set walls rotate away like stage flats. Niagara is limited to flat Unlit dots: fireflies as 10 to 20 sprites of 2 px in `#e8d9a8` drifting for 6 s, dust as square specks visible only inside light shapes.

## Do / Do not

Do:

- Draw light as hard-edged geometric shapes.
- Keep most of the frame dark and empty.
- Stage sets side-on with a wall removed.
- Keep figures small and featureless.

Do not:

- Do not use soft gradients and fog; that reads as `070`.
- Do not use bright graded sunset layers; that reads as `060`.
- Do not fill the frame with red and jagged shapes; that reads as `008`.
- Do not add outlines or texture.

## Nearest styles

- `070` Silhouette fog monochrome: `070` is pure greyscale with soft fog, blur and film grain; this style has blue-grey darkness, a yellow light colour and clean hard-edged shapes.
- `060` Layered flat-colour wilderness: `060` is a bright landscape of graded colour layers; this style is night, mostly near-black, with a few small lit shapes.
- `058` Shadow-puppet cut-out: `058` puts black cut-out figures in front of a glowing coloured screen that fills the frame; this style has no glowing backdrop, only isolated lamps and doorways that cut shapes out of the dark.

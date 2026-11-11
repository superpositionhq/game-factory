# Silhouette fog monochrome

Reference works: Limbo.

## References

- *Limbo* (2010), Playdead, video game. https://en.wikipedia.org/wiki/Limbo_(video_game)
- *Inside* (2016), Playdead, video game. https://en.wikipedia.org/wiki/Inside_(video_game)
- *Nosferatu* (1922), F. W. Murnau, silent film. https://en.wikipedia.org/wiki/Nosferatu

## Visual definition

- **Shape language and proportions:** A small child figure and simple hazards (spider legs, saws, crates, ropes) as solid black silhouettes. Forest, industrial and rooftop scenery in layered silhouette planes.
- **Line and outline:** No line. Foreground objects are solid black shapes.
- **Shading model:** None on the foreground. Background layers are flat greys that get lighter and blurrier with distance.
- **Palette:** `#000000` `#1c1c1c` `#5a5a5a` `#9a9a9a` `#d8d8d8` `#ffffff`. Greyscale only. The only pure white is the figure's eyes and a few light sources.
- **Lighting:** Back-lit fog: a soft bright area behind the scene; light shafts between trees.
- **Texture and surface:** Film grain and soft dust. No surface texture on silhouettes.
- **Atmosphere and post-processing:** Heavy vignette, grain, flicker, depth blur on near and far layers, soft glow in the light area.
- **Camera and framing:** Side-on, orthographic or long lens, with parallax layers.
- **UI and typography:** No HUD panels. Prompts are small soft-edged white text or a single white glyph in the fog. Type is a thin plain sans or a slightly worn light serif in white `#ffffff` or light grey `#d8d8d8`, with the same blur and flicker as the frame; counters, if any, are small white tally marks or numerals.
- **VFX and motion:** Dust motes, falling ash, water splashes and sparks appear as black or soft white specks; deaths are abrupt breaks of the silhouette with no colour. Motion is weighty and physical, with realistic ragdoll and rope swing, and long stillness broken by sudden lethal snaps.

## Fits

- **Genres:** `platformer`, `puzzle`, `survival-horror`, `stealth`, `exploration`, `soulslike`
- **Moods:** bleak, eerie, lonely
- **Settings:** dark forest, abandoned factory, rain-swept rooftops, flooded ruins

## Unreal recipe

### Assets

Shapes are judged by outline alone. Take trees, machinery, crates, gears, pylons and rooftops from any pack and ignore their textures; reject assets with a blob outline. Build spider legs, saws, ropes (cable components) and traps by script with exaggerated thin parts. The child is a small rigged character with a large head; add two tiny emissive eye quads on the head bone. Arrange the level as a side-on strip: one play plane, two or three near-foreground planes and four to six background layers spaced 5 to 30 m apart in depth.

### Materials

`M_Sil` is Unlit, pure `#000000`, applied to everything on the play plane and in front of it, with no shading inside the shape. Background layers use Unlit instances of flat grey chosen by layer: `#1c1c1c`, `#5a5a5a`, `#9a9a9a`, `#d8d8d8` from near to far. Eyes and lamp bulbs are Unlit emissive `#ffffff` at intensity 5.

### Lighting and atmosphere

No lighting on surfaces, so Lumen GI and reflections are off. The glow is fog: Exponential Height Fog with Volumetric Fog enabled, grey albedo, and one or two Spot Lights behind the scene pointed toward camera with high Volumetric Scattering Intensity, shadowed so trunks cut shafts into the fog. A large Unlit gradient card at the back, `#d8d8d8` centre falling to `#5a5a5a`, forms the bright area. Manual exposure.

### Post-processing

- Depth of field: focus on the play plane with a low f-stop and long focal length, so both near foreground and far layers blur while the play layer stays sharp.
- Colour Grading Saturation 0 as a safeguard against stray colour.
- Bloom Intensity 0.7, Threshold 0.8, for soft glow in the light area and round the eyes.
- Film Grain Intensity 0.6; Vignette Intensity 0.8 to 1.
- Flicker: a post material at Scene Color After Tonemapping multiplies the frame by 1 plus or minus 0.03 using a stepped noise of Time at about 12 Hz, and adds soft dust blotches from a panning texture.

Fringe 0, Motion Blur Amount 0, no edge detection of any kind. TSR. Camera orthographic or 15 degree field of view.

### UI and effects

No panels. Prompts are a single Text Block in Josefin Sans Light or Cormorant Light, `#ffffff` or `#d8d8d8`, inside a Retainer Box whose material blurs slightly and applies the same flicker.

Niagara: dust motes and ash as 1 to 3 px sprites, black in front of the glow and soft white inside shafts, 8 to 12 s life, slow drift. Water splashes are black droplet sprites with gravity; sparks are short white streaks lasting 0.3 s. Deaths use physics: ragdoll or detached silhouette pieces.

## Do / Do not

Do:

- Render the play layer as solid black.
- Lighten and blur layers with distance.
- Add grain, flicker and a heavy vignette.
- Keep eyes and lamps as the only pure white.

Do not:

- Do not add a coloured glowing backdrop; that reads as `058`.
- Do not light surfaces with modelled grey gradients; that reads as `068`.
- Do not use hard two-value threshold with a colour accent; that reads as `069`.
- Do not add coloured glows and painted detail; that reads as `027`.

## Nearest styles

- `058` Shadow-puppet cut-out: `058` sets black cut-outs against a glowing coloured backdrop; this style has only grey fog behind them, with grain and blur and no colour.
- `068` Film noir hard light: `068` lights real surfaces, so brick, faces and wet streets show in greys; this style keeps every foreground object a solid black shape with no interior detail.
- `065` Flat-vector stage light: `065` has clean hard-edged flat shapes in blue-grey darkness with yellow light; this style is colourless, soft and grainy, with blurred fog layers and a paler background.

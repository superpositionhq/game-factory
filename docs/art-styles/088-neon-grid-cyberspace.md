# Neon grid cyberspace

Reference works: Tron.

## References

- *Tron* (1982), Steven Lisberger (Walt Disney Productions), live-action and computer-animated film. https://en.wikipedia.org/wiki/Tron
- *Tron: Legacy* (2010), Joseph Kosinski (Walt Disney Pictures), live-action film. https://en.wikipedia.org/wiki/Tron:_Legacy
- *Tron 2.0* (2003), Monolith Productions, video game. https://en.wikipedia.org/wiki/Tron_2.0
- *Rez* (2001), United Game Artists, video game. https://en.wikipedia.org/wiki/Rez_(video_game)

## Visual definition

- **Shape language and proportions:** A digital world of smooth dark geometric solids: slabs, towers, ramps, discs and vehicles with clean chamfered forms. Bodies and vehicles carry thin circuit-like light lines. The ground is an infinite grid.
- **Line and outline:** No dark outline. Bright emissive lines trace edges and circuit paths on dark surfaces.
- **Shading model:** Surfaces are near-black with faint glossy reflection; almost all visible form comes from emissive lines and their glow.
- **Palette:** `#020308` `#0a1220` `#18e0ff` `#ff7a1a` `#e8fbff` `#123a5a`. Black and deep blue-black, with cyan-white light for one faction and orange for the other.
- **Lighting:** Self-illumination only. Emissive strips cast soft coloured glow onto nearby dark surfaces and reflect in the glossy floor.
- **Texture and surface:** None apart from circuit line patterns and the floor grid.
- **Atmosphere and post-processing:** Strong bloom on emissive lines, light trails behind moving vehicles, slight reflection blur.
- **Camera and framing:** Low wide shots along the grid; fast lateral tracking.
- **UI and typography:** Frames are thin glowing cyan lines with chamfered corners on black, with no filled panels; icons are single-weight line glyphs. Text is a wide geometric sans in capitals with squared letterforms. Counters use a monospaced digital face, cyan-white for the player and orange for enemies and warnings.
- **VFX and motion:** A hit breaks the target into glowing square fragments that scatter and fade; vehicles leave solid light trails or light walls, and thrown discs leave thin arcs. Motion is fast and precise, with sharp 90-degree turns, constant speed and little easing.

## Fits

- **Genres:** `racing`, `vehicle-combat`, `fps`, `third-person-shooter`, `fighting`, `top-down-shooter`
- **Moods:** cold, sleek, tense
- **Settings:** inside a computer, digital arena, light-cycle grid

## Unreal recipe

### Assets

Build nearly everything by script: chamfered slabs, towers, ramps, discs and wedge vehicles from Geometry Script or Blender, each with a second UV channel or vertex colour marking where light lines run (along chamfers and in circuit paths with 90-degree turns). Store characters and vehicles work if smooth and armour-like: discard all their textures, keep the mesh, and generate a circuit-line mask by script from UV seams and hard edges.

### Materials

`M_GridSolid`, Default Lit. Base Colour `#020308` to `#0a1220`, Metallic 0, Specular 0.5, Roughness 0.15 to 0.25, no normal map. Emissive Color = line mask × faction colour × intensity, with cyan `#18e0ff` (core lifted toward `#e8fbff`) for one side and orange `#ff7a1a` for the other, passed per component through Custom Primitive Data so one master serves both. Intensity 15 to 40 so lines drive bloom and Lumen. The floor uses a world-space grid from Frac and Step on WorldPosition with a `#123a5a` line, 1 m pitch, Roughness 0.1. Light walls and trails use an Unlit translucent material with a DepthFade soft base.

### Lighting and atmosphere

Zero placed lights. Lumen global illumination and Lumen reflections on (`r.DynamicGlobalIlluminationMethod=1`, `r.ReflectionMethod=1`), so emissive strips cast soft coloured glow on nearby solids and mirror in the floor; raise Lumen Final Gather Quality to 2 to keep emissive bounce stable. No Sky Light, no Sky Atmosphere, no directional light: the sky is black. Optional Exponential Height Fog at very low density tinted `#0a1220` to separate distant towers; no volumetric fog. Exposure Manual, set so unlit surfaces sit just above black.

### Post-processing

Bloom Method Standard, Intensity 1.2, Threshold 1 so only lines bloom. Tone Curve Amount 1 (filmic) to roll line cores toward white. Global Saturation 1.1; Shadows tint slightly blue. Vignette Intensity 0.3. Scene Fringe Intensity 0, Film Grain Intensity 0, Lens Flare Intensity 0, depth of field off. Motion Blur Amount 0; speed is shown by trails instead. TSR (`r.AntiAliasingMethod=4`), which keeps thin lines stable.

### UI and effects

UMG frames are 1 px cyan line borders with chamfered corners (9-slice Border brush, transparent centre), never filled panels. Titles use Orbitron in wide capitals; counters use Share Tech Mono, `#e8fbff` for the player and `#ff7a1a` for enemies and warnings. A soft outer glow is a blurred copy of each line image at 40% opacity.

Niagara: on a hit, a mesh renderer spawns 30 to 60 small emissive square plates in the target's faction colour that fly outward at constant speed and fade over 0.6 s. Vehicles emit a ribbon renderer trail, constant width, lifetime 2 to 4 s, hard-cornered because movement turns in 90-degree steps.

## Do / Do not

Do:

- Keep surfaces near-black and glossy.
- Trace edges and circuits with emissive lines.
- Use at most two emissive colours.
- Add strong bloom and a grid floor.

Do not:

- Do not draw wireframe only without solid surfaces; that reads as `040`.
- Do not add a magenta sunset and purple gradients; that reads as `090`.
- Do not add rain, haze and many sign colours; that reads as `089`.
- Do not light surfaces with white diffuse light.

## Nearest styles

- `040` Vector display glow: this style has solid near-black surfaces with glossy reflections under the light lines; `040` is glowing lines only on empty black, with nothing solid.
- `090` Synthwave sunset grid: this style is almost wholly black with one or two line colours; `090` has a bright gradient sky, a striped sun, and magenta, purple and orange together.
- `089` Rain-soaked tech-noir: this style has clean black solids lit only by their own lines; `089` is a fully shaded realistic wet city with haze, grime and many sign colours.

# Blueprint technical drawing

Reference works: Cyanotype blueprints.

## References

- *Cyanotype process* (1842), John Herschel, photographic printing process. https://en.wikipedia.org/wiki/Cyanotype
- *Blueprint* (19th century), after John Herschel's cyanotype process, reprographic drawing process. https://en.wikipedia.org/wiki/Blueprint
- *Photographs of British Algae: Cyanotype Impressions* (1843), Anna Atkins, cyanotype book. https://en.wikipedia.org/wiki/Anna_Atkins
- *Vitruvian Man* (c. 1490), Leonardo da Vinci, pen and ink drawing. https://en.wikipedia.org/wiki/Vitruvian_Man

## Visual definition

- **Shape language and proportions:** Objects shown as technical drawings: precise edges, visible hidden lines, centre lines, construction circles. Mechanical and architectural subjects.
- **Line and outline:** White or pale blue lines of two weights (visible edges 2 px, hidden and construction lines 1 px dashed) on blue. No dark lines.
- **Shading model:** None. Surfaces are transparent or the flat blue ground; section cuts are hatched with thin diagonal white lines.
- **Palette:** `#0b3d91` `#1f5fbf` `#ffffff` `#bcd4f6` `#082a66`. Prussian blue ground with white line work; pale blue for secondary lines.
- **Lighting:** None.
- **Texture and surface:** Faint paper grain and uneven blue wash; a light grid; fold creases. Dimension lines with arrowheads and tick marks.
- **Atmosphere and post-processing:** Slight blur and bleed on lines, edge darkening of the sheet.
- **Camera and framing:** Orthographic: front, side, top or isometric projection.
- **UI and typography:** Panels are thin white ruled boxes like a drawing title block, with corner ticks and leader lines that point to objects; icons are single-weight white line symbols. Text is an all-caps single-stroke drafting hand or a monospaced technical sans in white `#ffffff`, with secondary labels in pale blue `#bcd4f6`; numbers appear as dimension call-outs with arrowheads and units.
- **VFX and motion:** Effects are line work: impacts are expanding construction circles with radiating tick marks, trails are dashed paths, and destroyed objects separate into an exploded view. Motion is precise and mechanical, with linear moves, rotations that snap in fixed steps and lines that draw themselves on.

## Fits

- **Genres:** `puzzle`, `strategy`, `tower-defense`, `simulation`, `stealth`
- **Moods:** precise, calm, cerebral
- **Settings:** engineering workshop, factory floor plan, machine interior, heist floor plan

## Unreal recipe

### Assets

Machines, buildings and floor plans with clean hard edges: CAD-like kit pieces, gears, pipes, walls with openings. From store packs keep geometry only, and remove bevels under 1 cm in Blender so each edge yields one line. Generate annotation geometry by script: dimension lines with arrowheads, centre lines, construction circles and tick marks as thin quads or spline meshes placed from object bounds.

### Materials

One Unlit opaque master, `M_Sheet`, outputs flat `#0b3d91` for every surface. Set Render CustomDepth Pass on all drawn meshes, with stencil 1 for solids and 2 for section-cut faces. Section faces (caps generated where a clip plane cuts a mesh) get screen-space diagonal hatch: Frac of ScreenPosition x plus y times a density parameter, Step at 0.15, white on blue.

Hidden lines need the back edges. Give each mesh an Overlay Material that is translucent with Disable Depth Test on, drawing a wireframe mask baked into a UV channel (feature edges only, written by the Blender script), multiplied by a dash pattern from Frac of the UV along the edge, in `#bcd4f6` at one pixel.

### Lighting and atmosphere

No lights. `r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`, no sky, no fog, shadows off on every component. The camera is orthographic (Projection Mode Orthographic on the Camera Component) in front, side, top or isometric view. Manual exposure.

### Post-processing

Tone Curve Amount 0 and Expand Gamut 0 so the blue stays exact. Chain, all at Scene Color After Tonemapping:

1. Visible edges: Roberts cross on SceneDepth and WorldNormal plus CustomStencil changes, two pixels wide, drawn `#ffffff`.
2. Sheet: multiply by a tiling paper-grain texture and a low-frequency wash noise shifting the blue between `#082a66` and `#1f5fbf`; overlay a faint 64 px grid and two fold creases.
3. Bleed: a 3-tap blur blended at 30 percent, then darkening toward the sheet edges.

Bloom Intensity 0, grain 0, fringe 0, Motion Blur Amount 0. Use FXAA (`r.AntiAliasingMethod=1`), because TSR softens and ghosts one-pixel dashed lines.

### UI and effects

Widgets are title-block boxes: Border brushes with a 1 px white outline and transparent fill, corner ticks as small images, leader lines drawn in `NativePaint` from label to the projected object position. Type is Share Tech Mono in capitals, `#ffffff`, secondary labels `#bcd4f6`. Values read as dimension call-outs with units.

Niagara uses ribbon and mesh renderers only, Unlit white. Impact: a ring mesh scaling 0 to 2 m in 0.4 s with twelve radial tick sprites. Trails: ribbons with the dash material. Destruction: C++ translates each part along its axis from the assembly centre over 0.6 s with linear interpolation, leaving an exploded view joined by centre lines.

## Do / Do not

Do:

- Draw white lines on a blue ground.
- Show hidden edges as dashed lines.
- Use orthographic projection with dimension lines.
- Hatch section cuts.

Do not:

- Do not use glowing lines on black; that reads as `040`.
- Do not fill surfaces with shaded colour.
- Do not add neon glow and a floor grid in perspective; that reads as `088`.
- Do not use dark lines on white paper; that reads as `073`.

## Nearest styles

- `040` Vector display glow: `040` draws glowing lines on a black screen; this style draws crisp white lines with no glow on a Prussian blue paper ground.
- `088` Neon grid cyberspace: `088` is a dark space in perspective with neon trim, a receding floor grid and bloom; this style is a flat blue sheet in orthographic view with plain white lines.
- `073` Graphite pencil sketch: `073` is grey pencil strokes on white paper; this style is the reverse, white lines on deep blue with no dark lines.

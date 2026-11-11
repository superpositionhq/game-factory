# Primary grid neoplasticism

Reference works: Piet Mondrian; Rietveld Schroder House.

## References

- *Composition with Red, Blue and Yellow* (1930), Piet Mondrian, oil painting. https://en.wikipedia.org/wiki/Composition_with_Red,_Blue_and_Yellow
- *Broadway Boogie Woogie* (1943), Piet Mondrian, oil painting. https://en.wikipedia.org/wiki/Broadway_Boogie_Woogie
- *Rietveld Schroder House* (1924), Gerrit Rietveld, architecture. https://en.wikipedia.org/wiki/Rietveld_Schröder_House
- *Red and Blue Chair* (1918), Gerrit Rietveld, furniture. https://en.wikipedia.org/wiki/Red_and_Blue_Chair

## Visual definition

- **Shape language and proportions:** Only horizontals and verticals: rectangular planes and straight bars meeting at right angles. Planes slide past one another and overhang rather than joining at closed corners. No curves, no diagonals.
- **Line and outline:** Thick black bars of constant width separate colour fields; in 3D, black linear members (rails, mullions, frame bars).
- **Shading model:** None. Every plane is one flat colour.
- **Palette:** `#f7f5ee` `#111111` `#d21f1f` `#1f3fa8` `#f2cc1f` `#bdbdbd`. White dominates, with small areas of pure red, blue and yellow, black bars, and occasionally grey.
- **Lighting:** Even, shadowless.
- **Texture and surface:** None. Smooth opaque paint.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** Frontal or axonometric (orthographic), aligned to the grid.
- **UI and typography:** UI is the grid itself: white rectangular panels `#f7f5ee` divided by thick black bars, with one small red, blue or yellow block to mark the active item, health or score. Text is an all-capitals geometric sans built from straight strokes, close to De Stijl block lettering; numbers are square block numerals, and icons are made only of rectangles.
- **VFX and motion:** No particles, glow or blur. Effects are flat rectangles that flash a primary colour, slide along the grid, extend or pop in and out, in the stepping rhythm of Broadway Boogie Woogie; motion is straight-line and snappy, with instant starts and stops.

## Fits

- **Genres:** `puzzle`, `strategy`, `tower-defense`, `platformer`, `simulation`, `racing`
- **Moods:** orderly, crisp, upbeat
- **Settings:** modernist house, city street grid, abstract board, gallery

## Unreal recipe

### Assets

Everything is generated: no store pack is orthogonal enough. A Geometry Script or Blender generator emits only axis-aligned boxes: thin rectangular planes (walls, floors, panels) and square-section bars (rails, mullions, posts, frame members), all snapped to a 10 cm grid. Planes are placed to overlap and run 20 to 60 cm past each junction instead of meeting at a corner. No bevels, cylinders, spheres or rotated parts. Characters and vehicles are assemblies of boxes moving on straight tracks.

### Materials

One Unlit master, `M_Plane`, with a colour enum parameter limited to `#f7f5ee`, `#d21f1f`, `#1f3fa8`, `#f2cc1f`, `#bdbdbd`, and `M_Bar` in `#111111`. The generator assigns colours with a budget: at least 70 percent of visible plane area white, each primary under 10 percent, grey rare. Black bars are real geometry 8 to 12 cm thick, and in flat views they are also drawn in the plane material: a UV-edge mask with constant world-space width frames each field. No texture, no roughness variation, no gradient.

### Lighting and atmosphere

Unlit means no lighting set-up: disable Lumen, reflections, shadows, ambient occlusion and fog. If overlapping planes need separation in an axonometric view, do not add shade; offset them so a black bar or a colour change falls between them. Background is a white dome. Camera orthographic, either frontal or axonometric at fixed 45 degree yaw, always aligned to the grid.

### Post-processing

Tone Curve Amount 0, Expand Gamut 0, manual exposure: the primaries must be exact. Bloom 0, grain 0, vignette 0, fringe 0, depth of field off, Motion Blur Amount 0. No post-process materials and no paper overlay; the paint is smooth. Anti-aliasing FXAA or TSR at 100 percent. With an orthographic camera and axis-aligned geometry most edges are pixel-aligned, so keep widget and world bars on whole-pixel positions.

### UI and effects

Menus and HUD are a grid: white Border cells separated by 8 px black bars built from Image widgets in a Grid Panel, with unequal row and column sizes. The active item, health and score are each one small solid block in red, blue or yellow. Text in League Spartan Bold or Jost capitals with tight spacing; numerals from a square block font such as Silkscreen at large size, black.

No Niagara sprites, glow or trails. Effects are box meshes or widgets driven from C++ with constant-velocity moves and no easing: a rectangle flashes a primary for 0.1 s, a bar extends along its axis in 0.15 s, small squares step along grid lines at a steady beat of 4 to 8 moves per second. Things appear and vanish in one frame.

## Do / Do not

Do:

- Use only horizontal and vertical elements.
- Separate fields with thick black bars.
- Keep white dominant with a few primary rectangles.
- Let planes overlap and extend past junctions.

Do not:

- Do not add circles, triangles or diagonals; that reads as `098` or `080`.
- Do not back-light coloured panes; that reads as `054`.
- Do not add any shading, gradient or texture.
- Do not use thin lines; bars are thick.

## Nearest styles

- `098` Bauhaus primary geometry: this style is flat rectangles divided by thick black bars, with no shading; `098` has no bars and builds its scenes from softly shaded spheres, cones and cylinders.
- `054` Stained glass: this style is a bright, mostly white surface under even light with a few plain primary rectangles; `054` is dark, with glowing back-lit panes of deep red and blue between curved lead lines.
- `080` Constructivist agit poster: this style is strictly horizontal and vertical, with thick black bars and clean smooth paint; `080` thrusts along diagonals, has no bars around its shapes, and shows paper grain and uneven ink.

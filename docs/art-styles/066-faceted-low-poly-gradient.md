# Faceted low-poly gradient

Reference works: Astroneer; Islanders.

## References

- *Astroneer* (2019), System Era Softworks, video game. https://en.wikipedia.org/wiki/Astroneer
- *Islanders* (2019), Grizzly Games, video game. https://en.wikipedia.org/wiki/Islanders_(video_game)
- *Lara Croft Go* (2015), Square Enix Montreal, video game. https://en.wikipedia.org/wiki/Lara_Croft_Go

## Visual definition

- **Shape language and proportions:** Landscapes and objects made of visible triangles: irregular faceted terrain, crystal rocks, trees as a few stacked low-poly cones or blobs. Medium-low polygon counts, deliberately uneven triangulation.
- **Line and outline:** No outline.
- **Shading model:** Flat shading: one tone per triangle, so curved forms show many small flat steps. Soft overall light.
- **Palette:** `#f2a65a` `#ef6f6c` `#7fd1b9` `#4a7fb5` `#f7e3af` `#8e6bbf` `#2f4858`. Bright, soft gradient schemes: coral, sand, mint, sky blue and violet. Colour varies smoothly across the terrain by height.
- **Lighting:** Soft sun with coloured sky fill; gentle shadows.
- **Texture and surface:** None. Colour comes from vertex colours and facets.
- **Atmosphere and post-processing:** Soft gradient sky, light distance fog, mild bloom; clean anti-aliased edges.
- **Camera and framing:** Elevated three-quarter view or third-person; 35 to 50 mm equivalent.
- **UI and typography:** Rounded flat panels in soft pastel fills with no borders, and chunky simple icons, some built from a few facets. Text is a friendly rounded geometric sans in cream `#f7e3af` or dark slate `#2f4858`; counters are large clean numerals, with coral `#ef6f6c` and mint `#7fd1b9` as resource colours.
- **VFX and motion:** Particles are small flat-shaded triangles, cubes and low-poly puffs, not soft sprites; impacts throw a short burst of shards and a small pop of scale. Motion is smooth and bouncy with light squash and stretch, and placed objects settle with a small overshoot.

## Fits

- **Genres:** `survival-craft`, `strategy`, `simulation`, `exploration`, `tower-defense`, `puzzle`
- **Moods:** calm, cheerful, curious
- **Settings:** alien planet, tropical islands, floating islands, crystal canyon

## Unreal recipe

### Assets

Terrain, rocks and trees are built by script. In Blender, displace a jittered point grid with two octaves of noise, triangulate with Delaunay so triangles are irregular, then decimate rocks to 40 to 200 faces. Trees are two or three stacked squashed cones on a tapered trunk. A store low-poly pack fits once its texture atlas is replaced by vertex colour; a realistic pack needs decimation to about 5 percent and all maps dropped. Mark every edge sharp before export so each triangle has its own normal.

### Materials

One Default Lit master, `M_Facet`, with no texture samplers. Base Colour is a lerp across a Curve Atlas row indexed by world height (WorldPosition Z remapped by per-level min and max parameters): `#2f4858` in the deepest ground, through `#4a7fb5`, `#7fd1b9`, `#f7e3af`, `#f2a65a`, to `#ef6f6c` and `#8e6bbf` on peaks. Multiply by VertexColor for per-object tint. Roughness 0.85, specular 0.2. Because the height colour is evaluated per pixel, quantise it per triangle: feed the ramp from a height value baked into vertex colour alpha with the three corners of each face set equal.

### Lighting and atmosphere

Lumen GI on with software ray tracing. One Directional Light at 45 degrees, warm white, Source Angle 4 for soft shadow edges. Sky Light with real-time capture at intensity 1.5, so shadowed facets take sky colour and never go dark. The sky is a dome mesh with an Unlit vertical gradient from `#4a7fb5` to `#f7e3af`. Exponential Height Fog at low density with inscattering matched to the dome's horizon colour. Contact shadows off, since they speckle facets. Auto exposure with a narrow range, about 9 to 11 EV100.

### Post-processing

Filmic tonemapper at defaults, global Saturation 1.1, shadows Gain lifted slightly toward violet. Bloom Intensity 0.4, Threshold 1. No grain, no fringe, vignette at most 0.15, depth of field off, Motion Blur Amount 0. No posterise or pixel pass: the image is full resolution with TSR (`r.AntiAliasingMethod=4`, `r.ScreenPercentage=100`), and facet edges must be clean.

### UI and effects

Rounded Box brushes with a 16 px radius, borderless, filled `#2f4858` at 85 percent or `#f7e3af`. Text in Nunito Bold or Quicksand Bold, cream on slate or slate on cream. Resource counters are large numerals beside faceted icons rendered from the game's own meshes, coral `#ef6f6c` and mint `#7fd1b9`.

Niagara uses mesh renderers only: tetrahedra and cubes with `M_Facet`, 8 to 20 per burst, 0.5 s life, tumbling, shrinking to zero. Dust puffs are low-poly icospheres that scale up to 1.3 and back to 0 over 0.4 s. Placed objects settle with a scale curve of 0, 1.15, 1.

## Do / Do not

Do:

- Make triangles irregular and visibly faceted.
- Colour by vertex colours with a height gradient.
- Use flat shading at full resolution with anti-aliasing.
- Keep lighting soft and bright.

Do not:

- Do not use a strict cube grid with the same top, left and right face tones on every block; that reads as `059`.
- Do not render at low resolution with very few polygons; that reads as `043`.
- Do not flatten layers into single fog colours; that reads as `060`.
- Do not add textures.

## Nearest styles

- `059` Isometric pastel impossible architecture: `059` builds on a strict block grid in isometric view, with the same tones on every top, left and right face; this style has irregular triangles that each catch a different tone, and colour that shifts with height.
- `043` Flat-shaded early polygon: `043` looks like an early 3D game, with low resolution, jagged pixel edges and very coarse models; this style is crisp, anti-aliased and bright, with enough triangles to shape hills and rocks.
- `067` Boxy toybox low-poly: `067` builds objects from boxes and cylinders with stripe, dot and face decals; this style has triangulated organic forms and no decals.

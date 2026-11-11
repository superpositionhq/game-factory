# Flat-shaded early polygon

Reference works: Star Fox; Virtua Fighter.

## References

- *Star Fox* (1993), Nintendo EAD and Argonaut Software, video game. https://en.wikipedia.org/wiki/Star_Fox_(1993_video_game)
- *Virtua Fighter* (1993), Sega AM2, arcade video game. https://en.wikipedia.org/wiki/Virtua_Fighter_(video_game)
- *Another World* (1991), Eric Chahi (Delphine Software), video game. https://en.wikipedia.org/wiki/Another_World_(video_game)
- *Virtua Racing* (1992), Sega AM2, arcade video game. https://en.wikipedia.org/wiki/Virtua_Racing
- *Alone in the Dark* (1992), Infogrames, video game. https://en.wikipedia.org/wiki/Alone_in_the_Dark_(1992_video_game)

## Visual definition

- **Shape language and proportions:** Very low polygon counts (20 to 300 polygons per object) with large flat facets. Shapes are angular abstractions: wedge ships, box buildings, prism figures.
- **Line and outline:** No outline. Facet edges are visible only as colour changes.
- **Shading model:** Flat shading: one colour per polygon, brightness from the facet's angle to the light. No interpolation, no textures.
- **Palette:** `#1c2a6b` `#3e6fd1` `#c8322b` `#e8b83a` `#8f9aa8` `#2e8b57` `#f0f0f0`. Solid saturated colours per object part (blue, red, yellow, grey) on a simple two-colour sky and ground.
- **Lighting:** One directional light; no shadows.
- **Texture and surface:** None.
- **Atmosphere and post-processing:** Low resolution (about 256x224 or 320x200) with hard pixel edges; no filtering.
- **Camera and framing:** Behind-the-ship or side-on views with a 60 degree field of view.
- **UI and typography:** A sparse arcade overlay: thin single-colour bars for shield, boost and health, flat-polygon or wireframe icons, no panel textures. Text is blocky bitmap capitals or a slanted arcade sans, with large digits for lap time, speed and score in white, yellow `#e8b83a` and red `#c8322b`.
- **VFX and motion:** Explosions are bursts of flat-coloured triangles and spinning polygon shards; lasers are solid coloured bars, and a hit flashes the whole object white for a frame. Figures move stiffly on rigid limb segments at 15 to 20 frames per second, while the ground and scenery rush past the camera.

## Fits

- **Genres:** `vehicle-combat`, `racing`, `fighting`, `action-adventure`, `platformer`
- **Moods:** retro, brisk, abstract
- **Settings:** space battle corridor, race circuit, alien planet, fighting arena

## Unreal recipe

### Assets

Build nearly everything in Blender background mode: 20 to 300 polygons per object, wedge ships, box towers, prism limbs. A store pack can be reduced with a decimate pass to under 300 triangles, but only if the result still has large planar facets; otherwise rebuild. Export with split normals (flat shading, every face its own vertices) and assign colour per polygon as vertex colour. No UV maps are needed. Figures are rigid segments parented to bones, never smooth-skinned.

### Materials

One master, `M_FlatPoly`, shading model Unlit. Base tint is VertexColor times a `Tint` vector parameter. The facet normal comes from a Custom node, `normalize(cross(ddx(WorldPos), ddy(WorldPos)))`, so shading stays flat even on imported meshes with smooth normals. Dot it with a light vector from a Material Parameter Collection (set once from C++), remap to 0.45 to 1.0 and multiply. A `HitFlash` scalar lerps the whole object to `#f0f0f0` for one frame. No textures of any kind; that single rule separates this look from its textured retro neighbour.

### Lighting and atmosphere

No light actors are required, since facets take brightness from the collection vector. Lumen off, shadows off, no fog. The sky and ground are two colours: a sky dome with an Unlit material in `#3e6fd1` and a ground plane in `#2e8b57` or `#1c2a6b`, meeting at a hard horizon. Manual exposure.

### Post-processing

Target about 320x200: `r.ScreenPercentage` near 20 at 1080p, `r.AntiAliasingMethod=0`, `r.Upscale.Quality=0`, giving hard stair-stepped edges. Tone Curve Amount 0 and Expand Gamut 0 keep the solid colours saturated. Bloom, Film Grain, Vignette, Scene Fringe, Depth of Field, Ambient Occlusion and Motion Blur Amount all 0. Optional post material at Scene Color After Tonemapping that quantises each channel to 5 bits. Camera field of view 60 degrees.

### UI and effects

Sparse overlay with no panel art: thin Progress Bars for shield and boost with flat single-colour fills, white for normal, `#e8b83a` for boost, `#c8322b` when low. Large digits in Silkscreen or slanted Barlow Condensed Bold Italic for speed, lap time and score. Icons are wireframe or flat-polygon glyphs. Niagara uses a mesh renderer only: explosions emit 12 to 30 single triangles and small tetrahedra in the object's own colours, spinning, lifetime 0.5 to 0.8 s, no fade, just a scale to zero. Lasers are stretched box meshes in `#c8322b`. Tick character animation at 15 to 20 fps from C++ so limbs move in steps while scenery scrolls at full rate.

## Do / Do not

Do:

- Use one flat colour per polygon.
- Keep polygon counts very low.
- Render at low resolution without filtering.
- Use a simple two-colour sky and ground.

Do not:

- Do not add textures, even tiny ones; that reads as `036`.
- Do not raise polygon counts and use soft pastel gradients; that reads as `066`.
- Do not draw only edges; that reads as `040`.
- Do not smooth-shade.

## Nearest styles

- `066` Faceted low-poly gradient: `066` is bright and soft, with many small facets, pastel gradients and smooth edges; this style is darker, with a few large facets, solid colours and hard jagged pixels.
- `036` PS1 low-poly wobble: `036` covers its polygons with small pixelated textures that warp and wobble; this style has no textures, only one flat colour per polygon.
- `063` White-and-red faceted minimal: `063` is almost all white with a few red accents; this style puts strong blue, red and yellow on every object.

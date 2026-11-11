# White void ink-splat

Reference works: The Unfinished Swan.

## References

- *The Unfinished Swan* (2012), Giant Sparrow, video game. https://en.wikipedia.org/wiki/The_Unfinished_Swan
- *Elegy to the Spanish Republic* (1948-1967), Robert Motherwell, painting series. https://en.wikipedia.org/wiki/Robert_Motherwell
- *White on White* (1918), Kazimir Malevich, oil painting. https://en.wikipedia.org/wiki/White_on_White

## Visual definition

- **Shape language and proportions:** A normal 3D world (garden, walls, statues, furniture) that is entirely white and unshaded, so it is invisible until black paint is thrown onto it. Shapes are revealed only where splats land.
- **Line and outline:** No outline. Edges appear where a black splat wraps over a corner.
- **Shading model:** None. Surfaces are pure white; paint is pure black.
- **Palette:** `#ffffff` `#0a0a0a` `#f2f2f2` `#e6c84b` `#d9d9d9`. White and black, with a single rare gold-yellow accent object.
- **Lighting:** None visible. No shadows in the pure variant.
- **Texture and surface:** Paint splats: round blobs with radiating spikes, satellite drops and drips running down vertical surfaces.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** First-person, 70 to 80 degree field of view.
- **UI and typography:** Almost no UI: a small black dot reticle and, where text is needed, a few words in a thin storybook serif set in black directly on the white, with no panels or frames. Counters are plain black numerals, and the gold-yellow `#e6c84b` is used only to mark a goal or collectible.
- **VFX and motion:** Paint balls fly in a visible arc and burst into a splat with spikes, satellite drops and drips that run down walls for a moment before they stop. No glow, smoke or sparks; motion is calm and physical, and splats stay where they land.

## Fits

- **Genres:** `exploration`, `puzzle`, `platformer`, `stealth`
- **Moods:** quiet, curious, eerie
- **Settings:** storybook garden, empty castle, hedge maze, unfinished kingdom

## Unreal recipe

### Assets

An ordinary, detailed 3D world: garden walls, hedges, statues, benches, stairs, furniture, trees. Realistic store packs work well because splats need real corners and surface variety to describe; textures and normal maps are all discarded. Prefer assets with clear medium-scale form over fine filigree. Every paintable mesh needs a non-overlapping lightmap-style UV channel with even texel density, generated on import by script, because paint is stored in UV space.

### Materials

`M_Void` is Unlit. Its emissive is a lerp from `#ffffff` to `#0a0a0a` by a paint mask, with nothing else contributing, so an unpainted wall is indistinguishable from empty space. The mask comes from a per-actor Render Target (512 or 1024 px, single channel) sampled with the unique UV channel. C++ paints into it on each hit: find the hit UV with Find Collision UV (enable Support UV From Hit Results in project settings), then draw a splat brush material into the target with Draw Material to Render Target. Brush textures are made by Pillow: a round blob, 8 to 14 radiating spikes, satellite drops. For large shared surfaces a world-space Runtime Virtual Texture can replace per-actor targets. The gold goal object uses a separate Unlit instance, `#e6c84b`, always visible.

### Lighting and atmosphere

Nothing: no lights, no Sky Light, no sky, no fog, Lumen and reflections off, shadow casting disabled on all meshes. Ambient Occlusion Intensity 0 and Distance Field Ambient Occlusion off, since any corner darkening breaks the void. The world background is a white Unlit dome. Optional late-game variant: one Directional Light whose shadows show as `#d9d9d9`, through a second master.

### Post-processing

Tone Curve Amount 0, Expand Gamut 0, manual exposure, so `#ffffff` is exactly white. Bloom 0, grain 0, vignette 0, fringe 0, depth of field off, Motion Blur Amount 0. No post-process materials: no edge detection, no threshold. Anti-aliasing with TSR or FXAA only softens splat edges. Field of view 75 degrees on the camera.

### UI and effects

A 6 px black dot Image as reticle. Text, when unavoidable, in Cormorant Light or EB Garamond, `#0a0a0a`, set straight on the screen with no backing. Counters are plain numerals in the same serif. Gold marks only the goal or a collectible count.

The paint ball is a small black Unlit sphere on a visible ballistic arc. On hit, Niagara throws 6 to 10 black droplet mesh particles with gravity; each calls back to paint a small satellite splat where it lands. Drips: C++ extends a narrow streak downward in the Render Target for 1 to 2 s on vertical surfaces, then stops. Splats are permanent; nothing glows, smokes or sparks.

## Do / Do not

Do:

- Keep all unpainted surfaces pure white with no shading.
- Reveal form only with black paint splats.
- Give splats spikes, droplets and drips.
- Keep paint sparse: most of the frame stays blank white, with splats only where the player has thrown paint.

Do not:

- Do not add ambient occlusion or shading on the white; that reads as `063` or `035`.
- Do not draw pencil lines and hatching; that reads as `073`.
- Do not threshold a lit scene to black and white; that reads as `069`.
- Do not use red faceted figures; that reads as `063`.

## Nearest styles

- `063` White-and-red faceted minimal: here the white world has no shading at all and is seen only through black paint splats; `063` shows its white rooms through soft corner shading and fills them with glossy red faceted figures.
- `073` Graphite pencil sketch: this style has no drawn lines and no greys, only black splats on blank white; `073` outlines and shades every object in grey pencil.
- `069` Selective-colour ink noir: this frame is almost all white with scattered black splats; `069` is almost all black, with white shapes cut out by light and one spot of colour.

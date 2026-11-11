# White-and-red faceted minimal

Reference works: Superhot.

## References

- *Superhot* (2016), Superhot Team, video game. https://en.wikipedia.org/wiki/Superhot
- *Superhot: Mind Control Delete* (2020), Superhot Team, video game. https://en.wikipedia.org/wiki/Superhot:_Mind_Control_Delete
- *THX 1138* (1971), George Lucas, live-action film. https://en.wikipedia.org/wiki/THX_1138
- *Antichamber* (2013), Alexander Bruce, video game. https://en.wikipedia.org/wiki/Antichamber

## Visual definition

- **Shape language and proportions:** Environments are clean white architectural models with simple blocky furniture. Enemies are faceted, crystalline human figures that shatter into shards. Weapons and interactive objects are simple solid shapes.
- **Line and outline:** No outline.
- **Shading model:** Flat-shaded facets on figures; environments have soft ambient occlusion on white. No textures.
- **Palette:** `#f4f4f4` `#dcdcdc` `#ff2a1a` `#141414` `#b8b8b8`. White and pale grey environment, glossy red enemies, solid black interactive objects. Nothing else.
- **Lighting:** Bright, diffuse, shadowless-looking light; faint ambient occlusion defines corners.
- **Texture and surface:** None.
- **Atmosphere and post-processing:** High exposure; red motion trails on bullets; slight bloom.
- **Camera and framing:** First-person, 80 to 90 degree field of view.
- **UI and typography:** No frames or panels. Messages are huge all-caps words in a heavy condensed sans that fill the screen one word at a time, in black `#141414` or red `#ff2a1a` on white. Icons are solid black flat shapes, and counters are plain bold numerals.
- **VFX and motion:** Enemies break into hard red glass shards with no blood or smoke; bullets leave straight red trails and muzzle flashes are simple faceted bursts. Motion is abrupt and linear and stays readable in slow motion, with shards that hang and drift in the air.

## Fits

- **Genres:** `fps`, `puzzle`, `top-down-shooter`, `roguelike`, `stealth`
- **Moods:** tense, clinical, stark
- **Settings:** office block, laboratory, virtual simulation, parking garage

## Unreal recipe

### Assets

Rooms are plain architectural blocks: walls, stairs, desks, shelves and columns as boxes with a 5 mm bevel, built by Geometry Script or taken from an office pack with fittings (handles, cables, signs, vents) deleted. Figures start as a rigged mannequin; decimate the skin in Blender to about 800 triangles with planar bias, split every normal, and keep the skin weights. Also pre-fracture the figure into 40 to 60 shard meshes per body region (Blender cell fracture, exported as separate static meshes) for the shatter.

### Materials

Three Default Lit masters and no textures at all:

- `M_White`: Base Colour `#f4f4f4`, roughness 0.9, specular 0. An instance at `#dcdcdc` for floors and secondary blocks, `#b8b8b8` only for far background.
- `M_RedGlass`: Base Colour `#ff2a1a`, roughness 0.15, with emissive at 0.4 of the same red so figures never fall dark. Normal comes from a flat normal derived by DDX/DDY of WorldPosition, which keeps facets hard even on skinned deformation.
- `M_Black`: `#141414`, roughness 0.5, for everything the player can pick up or use.

### Lighting and atmosphere

Lumen GI on, because bounce between white surfaces is what makes the rooms read. A Sky Light with a plain white cubemap at high intensity is the main source; add one weak Directional Light with Source Angle 10 and shadow strength reduced, or none. Corners are defined by Lumen's short-range occlusion plus Ambient Occlusion Intensity 0.5, Radius 60. No fog, no sky visible; windows show flat white. Manual exposure pushed about one stop over, so `#f4f4f4` sits just below clip.

### Post-processing

Keep the filmic tonemapper but lower Toe and raise White Clip slightly for a clean high-key roll-off; Saturation 1.1 so the red stays pure. Bloom Intensity 0.3, Threshold 1.5. No grain, vignette, fringe or outline pass. Depth of field off. Motion Blur Amount 0: bullet streaks are geometry, not blur. TSR at full resolution for clean facet edges.

### UI and effects

One full-screen Text Block per message in Anton or Bebas Neue, capitals, sized to fill 80 percent of the width, shown one word at a time for 0.25 s each in `#141414` or `#ff2a1a`. No frames. Counters are plain Anton numerals.

Niagara: bullets leave a straight ribbon in emissive red, width 2 cm, life 1.2 s, no fade in width. On death, hide the skeletal mesh and spawn the shard meshes as physics-driven mesh particles with low drag so they hang in slow motion; add 30 small triangle shards. Muzzle flash is a six-point faceted mesh burst visible for 0.05 s. No smoke, no blood, no sparks.

## Do / Do not

Do:

- Use only white, red and black.
- Facet the figures like crystal.
- Leave the environment untextured white.
- Shatter figures into shards.

Do not:

- Do not add more accent hues and smooth city architecture; that reads as `035`.
- Do not add moulded panels and equipment detail; that reads as `091`.
- Do not scatter black ink splats on white; that reads as `074`.
- Do not colour the environment.

## Nearest styles

- `035` White city with primary accents: `035` has smooth-shaded white city buildings with several bright accent colours; this style allows only red and black against white and facets its figures like crystal.
- `074` White void ink-splat: `074` is an unlit blank white void where the world shows only where black ink splats land; this style shows all of its white rooms, with soft corner shadows and faceted red figures.
- `091` Clinical white space-age: `091` has moulded panels, seams and equipment on smooth glossy white surfaces; this style has bare untextured white blocks with no fittings.

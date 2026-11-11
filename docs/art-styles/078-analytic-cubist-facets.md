# Analytic cubist facets

Reference works: Picasso; Braque.

## References

- *Les Demoiselles d'Avignon* (1907), Pablo Picasso, oil painting. https://en.wikipedia.org/wiki/Les_Demoiselles_d'Avignon
- *Violin and Candlestick* (1910), Georges Braque, oil painting. https://en.wikipedia.org/wiki/Georges_Braque
- *Portrait of Daniel-Henry Kahnweiler* (1910), Pablo Picasso, oil painting. https://en.wikipedia.org/wiki/Daniel-Henry_Kahnweiler_(Picasso)
- *Houses at l'Estaque* (1908), Georges Braque, oil painting. https://en.wikipedia.org/wiki/Houses_at_l'Estaque
- *Nude Descending a Staircase, No. 2* (1912), Marcel Duchamp, oil painting. https://en.wikipedia.org/wiki/Nude_Descending_a_Staircase,_No._2

## Visual definition

- **Shape language and proportions:** Objects (guitars, bottles, faces, houses) are broken into angular facets and shown from several viewpoints at once. Facets overlap, slide apart and interpenetrate; object and background merge.
- **Line and outline:** Dark straight or arc line segments along some facet edges, broken and discontinuous.
- **Shading model:** Each facet has its own gradient from light on one edge to dark on the opposite edge, inconsistent with any single light source.
- **Palette:** `#8a7a5c` `#5f5a50` `#c9b88f` `#3a3a36` `#a89a7a` `#6f7a7a` `#e3d9c0`. Near-monochrome ochre, grey, brown and dull green.
- **Lighting:** No single light; each facet is lit as if separately.
- **Texture and surface:** Short, parallel, dabbed brush strokes (hatched dabs) inside facets; occasional stencil letters or wood-grain patches.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** Frontal, shallow space; the picture plane is flat and crowded.
- **UI and typography:** Panels are overlapping angular planes in ochre `#c9b88f` and grey `#5f5a50` with broken dark line segments along some edges, like collage pieces. Text and numbers are stencil capitals in dark grey-brown `#3a3a36`, in the manner of the stencilled letters in the paintings, and icons are objects reduced to a few shifted facets.
- **VFX and motion:** Hits shatter an object into flat angular shards that slide apart and overlap before they settle; dust and smoke are stacks of small ochre and grey facets. Movement can leave a short trail of overlapping repeated poses, as in Nude Descending a Staircase, and facets shift as the camera turns.

## Fits

- **Genres:** `puzzle`, `detective-mystery`, `exploration`, `stealth`, `strategy`
- **Moods:** cerebral, disorienting, sombre
- **Settings:** Paris studio, café table still life, hillside village, music hall

## Unreal recipe

### Assets

Still-life and village subjects: guitars, bottles, glasses, tables, heads, small houses. Start from ordinary models and process each in Blender by script: cut the mesh with 8 to 20 random planes into angular chunks, separate the chunks, then offset each by 1 to 6 cm and rotate it 5 to 25 degrees about a random axis so parts slide apart, overlap and interpenetrate. Keep each chunk as its own mesh element with a random value in vertex colour. Add flat background shards of the same kind behind and through the object so figure and ground merge.

### Materials

`M_Facet` is Unlit, because one consistent light source would undo the style. Per chunk (vertex colour id): pick a hue from `#8a7a5c`, `#5f5a50`, `#c9b88f`, `#a89a7a`, `#6f7a7a`, and compute a gradient across the chunk along a random direction derived from the id, running from `#e3d9c0` at one edge to `#3a3a36` at the opposite. Use object-space position relative to the chunk centre, stored in a UV channel, as the gradient coordinate. Multiply by a hatched-dab texture of short parallel strokes rotated per chunk. A few chunks swap to a wood-grain or stencil-letter texture by id. Dark edge lines are a second baked UV-space mask covering only some chunk borders, with gaps.

To show several viewpoints, give chunks a World Position Offset that rotates each around the object centre by an id-dependent angle scaled by camera yaw, so facets shift against each other as the view turns.

### Lighting and atmosphere

No lights, Lumen off, no fog, no shadows, no ambient occlusion. Camera frontal with a long lens or orthographic; keep sets shallow, under 3 m deep, and crowd the frame.

### Post-processing

Tone Curve Amount 0 and manual exposure to hold the ochre-grey values. Bloom 0, vignette 0, fringe 0, depth of field off, Motion Blur Amount 0. One optional post material multiplies a canvas weave at 5 percent. No edge detection: lines come from the baked masks so they stay broken and partial. TSR.

### UI and effects

Panels are two or three overlapping angular Image planes in `#c9b88f` and `#5f5a50`, each slightly rotated, with short dark line segments on some edges. Text and numbers in Stardos Stencil or Special Elite capitals, `#3a3a36`.

Niagara uses mesh renderers with flat triangular and quadrilateral shards in `M_Facet`: on a hit 15 to 30 shards slide outward 20 to 40 cm along their planes over 0.6 s, overlap and stop. Movement trails: C++ leaves three or four frozen pose copies (Poseable Mesh snapshots) fading over 0.4 s.

## Do / Do not

Do:

- Fragment objects into shifted angular facets.
- Show several viewpoints of one object together.
- Give each facet its own light-to-dark gradient.
- Hold the palette to ochre, grey and brown.

Do not:

- Do not keep objects whole with clean low-poly facets under one light; that reads as `043` or `066`.
- Do not use primary colours with black bars on white; that reads as `079`.
- Do not use diagonal red-black poster geometry; that reads as `080`.
- Do not paint coherent leaning sets with hard shadows; that reads as `071`.

## Nearest styles

- `071` Expressionist painted set: this style breaks objects into overlapping ochre-grey facets seen from several viewpoints; `071` keeps its sets whole but skewed, in tinted black and white with painted shadow shapes.
- `066` Faceted low-poly gradient: this style is dull ochre and grey with broken dark lines on facet edges and objects that fall apart into shifted planes; `066` keeps objects whole, with clean triangles in bright coral, mint and sky blue and no lines.
- `079` Primary grid neoplasticism: this style has brushy, shaded facets at all angles in ochre and grey; `079` is perfectly flat white, red, blue and yellow rectangles between straight black bars.

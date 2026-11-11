# Embroidered tapestry

Reference works: Bayeux Tapestry.

## References

- *Bayeux Tapestry* (1070s), Anglo-Norman embroiderers, wool embroidery on linen. https://en.wikipedia.org/wiki/Bayeux_Tapestry
- *The Lady and the Unicorn* (c. 1500), Flemish workshops, wool and silk tapestry. https://en.wikipedia.org/wiki/The_Lady_and_the_Unicorn
- *The Hunt of the Unicorn* (1495-1505), South Netherlandish workshops, wool and silk tapestry. https://en.wikipedia.org/wiki/The_Unicorn_Tapestries
- *Apocalypse Tapestry* (1377-1382), Nicolas Bataille workshop (after Jean Bondol), wool tapestry. https://en.wikipedia.org/wiki/Apocalypse_Tapestry

## Visual definition

- **Shape language and proportions:** Flat, frieze-like figures in profile or three-quarter view, with long limbs and simple gestures. Buildings, ships and trees are schematic symbols. No perspective; size shows importance.
- **Line and outline:** Every shape is outlined in dark stem stitch. Folds and features are single stitched lines.
- **Shading model:** None. Areas are filled with one thread colour laid in parallel stitches.
- **Palette:** `#d8c9a3` `#8a3b2a` `#2f4a5a` `#b58a2f` `#4f6b3a` `#3a2a22` `#c9a57a`. Natural linen ground with a few plant-dyed wools: terracotta, blue-green, old gold, olive, dark blue-black.
- **Lighting:** None in the image. Real light may rake across the raised thread.
- **Texture and surface:** Visible thread everywhere: parallel laid stitches in filled areas, couching lines across them, plain-weave linen showing between shapes.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** Flat, frontal, wide strip format with decorative borders above and below.
- **UI and typography:** Panels are strips of bare linen with stitched borders of running animals, leaves and chevrons, like the tapestry margins, and icons are small embroidered emblems. Type is a hand-stitched Latin capital with uneven uncial letters in dark wool, like the captions above the Bayeux scenes. Numbers are stitched Roman numerals in terracotta or blue-black.
- **VFX and motion:** Effects are stitched symbols: arrows, flames, waves and stars appear as thread shapes sewn in stitch by stitch, and a hit pulls threads loose or leaves a frayed gap. Figures move through a few held poses with jerky limb swings and slide along the baseline.

## Fits

- **Genres:** `strategy`, `tower-defense`, `rpg`, `action-adventure`, `puzzle`
- **Moods:** solemn, archaic, wry
- **Settings:** Norman conquest, medieval court, castle siege, hunting forest

## Unreal recipe

### Assets

Everything is a flat stitched picture, so 3D packs are of little use except as pose reference. Generate art by script: draw each figure, ship, tree and building as flat vector shapes in profile, then a Pillow pass fills every shape with parallel laid stitches in one wool colour, adds couching lines across them, and traces a dark stem-stitch outline. Export albedo, a thread normal map and an opacity mask. In the level these are flat cards standing a few millimetres above one long linen plane, all on a single baseline, with decorative border strips above and below. Characters are jointed card puppets (limbs as separate cards on a simple rig).

### Materials

`M_Thread`: Default Lit, Masked. Base Color from the stitched texture, limited to terracotta `#8a3b2a`, blue-green `#2f4a5a`, old gold `#b58a2f`, olive `#4f6b3a` and outline `#3a2a22`. Roughness 0.85, Specular 0.3, the thread normal map at full strength so raking light picks out each strand. `M_Linen`: Default Lit, `#d8c9a3` with a plain-weave normal and albedo pattern. No Cloth fuzz, no gradients, no shading painted into fills; the only tonal change is real light on raised thread. Flat cards on bare linen, not plump stuffed forms, mark the difference from soft-toy fabric styles.

### Lighting and atmosphere

Lumen off. One Directional Light raking across the cloth at about 20 degrees, with shadows disabled or Contact Shadows only, so thread relief shows but figures cast no shadow. A neutral Sky Light fills. No fog, no sky. Manual exposure.

### Post-processing

Orthographic camera, frontal, in a wide strip format with letterbox bars filled by the stitched borders. TSR on, `r.Tonemapper.Sharpen` about 0.5. Tone Curve Amount reduced to about 0.5 and Saturation 0.9 to keep plant-dyed colours muted. Bloom, grain, vignette, fringe, depth of field, Ambient Occlusion and Motion Blur Amount 0. No post materials.

### UI and effects

Panels are strips of linen with stitched borders of running animals, leaves and chevrons as tiling Border brushes. Captions in an uncial-style face such as Cinzel Decorative or Pirata One, pre-rendered through the stitch script in dark wool `#3a2a22`. Numbers are Roman numerals in terracotta or blue-black. Effects are cards, not sprites: arrows, flames, waves and stars are stitched textures revealed stitch by stitch with a mask that advances along the thread direction over 0.4 s. A hit shows a frayed-gap decal and two or three ribbon-renderer loose threads in Niagara. Figures step through held poses at 6 to 8 per second and slide along the baseline.

## Do / Do not

Do:

- Outline every shape with dark stitches.
- Fill areas with parallel laid stitches.
- Keep figures flat on one baseline without perspective.
- Leave linen ground visible.

Do not:

- Do not build soft 3D stuffed forms in bright pastels; that reads as `051`.
- Do not use smooth flat ink colour without thread texture; that reads as `082`.
- Do not use dense interlaced ornament and gold; that reads as `086`.
- Do not add shading or perspective.

## Nearest styles

- `051` Felt and yarn: this style is a flat stitched picture on bare linen in muted wool colours; `051` builds plump, softly shaded stuffed forms in bright pastels.
- `086` Insular illuminated manuscript: here a few muted wools sit on plain linen that stays open between sparse figures; `086` fills the page with rich colour, gold and dense knotwork.
- `082` Ukiyo-e woodblock: every filled area here shows parallel thread and the linen weave; `082` has smooth flat printed colour on paper with only a faint wood grain, and fine flowing black line.

# Gothic stop-motion puppet

Reference works: The Nightmare Before Christmas; Coraline.

## References

- *The Nightmare Before Christmas* (1993), Henry Selick (Touchstone Pictures and Skellington Productions), stop-motion film. https://en.wikipedia.org/wiki/The_Nightmare_Before_Christmas
- *Coraline* (2009), Laika (Henry Selick), stop-motion film. https://en.wikipedia.org/wiki/Coraline_(film)
- *Corpse Bride* (2005), Tim Burton and Mike Johnson, stop-motion film. https://en.wikipedia.org/wiki/Corpse_Bride
- *ParaNorman* (2012), Laika, stop-motion film. https://en.wikipedia.org/wiki/ParaNorman
- *Frankenweenie* (2012), Tim Burton, stop-motion film. https://en.wikipedia.org/wiki/Frankenweenie_(2012_film)

## Visual definition

- **Shape language and proportions:** Thin, elongated puppets: stick limbs, tiny waists, very large heads with huge round eye sockets. Sets are crooked: leaning houses, spiral hills, twisted fences and bare trees.
- **Line and outline:** No outline. Painted stripes and stitches act as graphic line.
- **Shading model:** Smooth, photographed-miniature shading with hard theatrical shadows.
- **Palette:** `#14141c` `#3b3350` `#6b6f7a` `#c9c2b0` `#d9772b` `#5a7a4a` `#8a2f3a`. Dark blue-violet and grey with bone white, and pumpkin orange or sickly green accents.
- **Lighting:** Low-key stage lighting: strong back and side light, long distorted shadows, a large moon disc.
- **Texture and surface:** Hand-made miniature materials: painted resin, wire, fabric, scratched wood, with visible paint strokes and stitched seams.
- **Atmosphere and post-processing:** Vignette, slight depth of field, light fog; animation stepped on twos.
- **Camera and framing:** Low and wide for sets, tilted compositions; macro-like for faces.
- **UI and typography:** Frames are twisted wrought iron with curled spiral ends, or stitched fabric patches; icons are small props such as buttons, keys, bones and pumpkins. Lettering is a tall, spindly hand-drawn serif with uneven letter heights and curled tails. Counters are thin scratchy numerals in bone white `#c9c2b0` on dark violet `#3b3350`, with pumpkin orange `#d9772b` for highlights.
- **VFX and motion:** Effects look hand-made: cotton fog, paper bats and leaves, flickering candle glow, sickly green wisps, a puff of dust on impact. Animation runs on twos with slightly jerky stop-motion timing, long gliding strides, spidery limb gestures and sharp held poses.

## Fits

- **Genres:** `action-adventure`, `platformer`, `stealth`, `puzzle`, `exploration`, `survival-horror`
- **Moods:** macabre, whimsical, eerie
- **Settings:** haunted town, graveyard hill, crooked old house, twisted forest

## Unreal recipe

### Assets

Shapes do the work: stretch store characters by script (scale limb bones long and thin, enlarge the head bone 1.5 to 2 times) or build puppets in Blender from wire-thin limbs and ball heads with deep round eye sockets. Bend architecture with a lattice or shear deformer so houses lean, fences twist and hills curl; a straight pack wall must not ship as it came. Reduce textures to simple painted colour areas and repaint stripes and stitched seams onto them. Bare trees, curled iron gates and the moon disc are better built from scratch.

### Materials

`M_Puppet`: Default Lit, Base Color from a small painted texture limited to `#14141c`, `#3b3350`, `#6b6f7a` and bone `#c9c2b0`, with accent masks for pumpkin `#d9772b` or green `#5a7a4a`. Roughness 0.6 to 0.8 with a brush-stroke normal map at low strength so paint strokes catch the side light. A stripe function (Frac on a UV axis through Step) and a stitch function (dashed line along a seam mask) are material functions reused across instances. Cloth parts use the Cloth shading model with a dark fuzz colour. No subsurface clay softness and no bright colour: thinness, darkness and painted graphics set it apart from chunky clay.

### Lighting and atmosphere

Lumen GI on at low intensity. A cool Directional Light as moonlight from behind and to the side, small Source Angle for hard edges, Virtual Shadow Maps so long distorted shadows cross the set. One or two Spot Lights as theatrical side light; warm Point Lights in windows and lanterns. The moon is an oversized Unlit disc mesh. Exponential Height Fog with low Volumetric Fog density, tinted `#3b3350`. Manual exposure, held low-key.

### Post-processing

Vignette 0.6, Depth of Field at f/4 (stronger for face close-ups), Bloom 0.3 for candle and moon, Film Grain 0.2. Colour grading: Saturation 0.8 globally, shadows pushed to blue-violet, highlights neutral so bone white stays clean. TSR on, Motion Blur Amount 0. No outline or posterise materials; real smooth light on 3D miniatures is the point. Animate on twos by ticking poses at 12 fps from C++.

### UI and effects

Frames are wrought-iron 9-slice borders with spiral ends, or stitched fabric patches with a dashed thread border. Lettering in a tall spindly face such as Pirata One or Cormorant Italic with per-letter baseline offsets, bone white on `#3b3350`, pumpkin orange for highlights. Counters are thin scratchy numerals; icons are buttons, keys, bones. Niagara: cotton fog as slow lumpy mesh puffs, paper bats and leaves as two-sided card meshes that flutter (10 to 20, lifetime 3 s), green wisps as thin ribbons in `#5a7a4a`, candle flicker through a light renderer. Step particle updates on twos.

## Do / Do not

Do:

- Elongate limbs and enlarge heads.
- Twist and lean every building.
- Backlight with a moon and cast long shadows.
- Paint stripes and stitches on surfaces.

Do not:

- Do not use chunky rounded clay in bright colours; that reads as `048`.
- Do not go fully greyscale with painted-on shadows on flat sets; that reads as `071`.
- Do not use photoreal stone architecture and fog; that reads as `031`.
- Do not use flat black silhouettes; that reads as `070`.

## Nearest styles

- `048` Claymation: `048` is bright and warm, with chunky rounded clay figures; this style is dark and muted, with thin elongated puppets.
- `071` Expressionist painted set: `071` is nearly monochrome, with light and shadow painted onto flat sets; this style has real smooth light on 3D miniatures and orange or green colour accents.
- `031` Gothic dark-fantasy realism: `031` is photoreal, with dense stone and material detail; this style looks like hand-made miniatures, with a limited palette and simple painted surfaces.

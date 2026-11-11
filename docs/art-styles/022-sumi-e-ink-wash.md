# Sumi-e ink wash

Reference works: Okami.

## References

- *Okami* (2006), Clover Studio, video game. https://en.wikipedia.org/wiki/Ōkami
- *Okamiden* (2010), Capcom, video game. https://en.wikipedia.org/wiki/Ōkamiden
- *Pine Trees* (1595), Hasegawa Tohaku, ink on paper folding screens. https://en.wikipedia.org/wiki/Shōrin-zu_byōbu
- *The Tale of the Princess Kaguya* (2013), Studio Ghibli (Isao Takahata), animated film. https://en.wikipedia.org/wiki/The_Tale_of_the_Princess_Kaguya_(film)

## Visual definition

- **Shape language and proportions:** Simplified, flowing forms. Trees, hills and clouds are stylised into curls and sweeping curves; characters are compact with expressive silhouettes.
- **Line and outline:** Black brush line with strong calligraphic variation: thick in the middle of a stroke, thin and dry at the ends, with breaks. Lines overshoot corners.
- **Shading model:** Two tones: base wash and a slightly darker wash. No smooth light gradient.
- **Palette:** `#1c1a17` `#f3ead7` `#b23a2e` `#6f8f5e` `#d9a441` `#5b6f8c` `#e9c9b1`. Warm paper ground, ink black, and thin washes of vermilion, moss green, ochre and indigo.
- **Lighting:** None in the physical sense. A soft directional wash only.
- **Texture and surface:** Paper fibre over everything. Colour sits as uneven wash with darker pooled edges. Dry-brush streaks in strokes.
- **Atmosphere and post-processing:** Full-frame paper texture multiply, slight edge darkening, ink-bleed blur on lines.
- **Camera and framing:** Wide landscape views with large empty paper areas; 35 mm equivalent.
- **UI and typography:** Panels are paper scrolls with torn or brushed edges; icons are round ink-seal stamps and small brush drawings, and counters are rows of ink pots. Headings and numerals are hand-lettered brush script. Text is ink black `#1c1a17` on paper `#f3ead7`, with vermilion `#b23a2e` for seals and health.
- **VFX and motion:** Effects are brush strokes: a slash is one sweeping black stroke that fades dry, hits burst into ink splashes, and flowers and petals bloom along the hero's path. Animation is flowing, with trailing ink lines behind fast motion.

## Fits

- **Genres:** `action-adventure`, `exploration`, `rpg`, `puzzle`, `hack-and-slash`, `soulslike`
- **Moods:** serene, mythic, playful
- **Settings:** mythic Japan, mountain villages, misty pine forests, spirit shrines

## Unreal recipe

### Assets

Choose low-polygon characters, trees and hills with flowing silhouettes; stylised packs work better than scanned ones. Delete all normal, roughness and metallic maps. Replace albedo with a flat wash colour from the palette plus a baked ambient-occlusion pass re-imported as a "pooling" mask. Build trees, clouds and hills from scratch in Blender as curled, swept profiles; clouds and distant mountains can be camera-facing cards carrying hand-shaped brush textures. Generate dry-brush stroke textures and a paper fibre texture by script.

### Materials

`M_InkWash`, Unlit. A Material Parameter Collection holds a wash direction set from C++. `Dot` of VertexNormalWS with that vector goes through a `Step` at 0.35 to choose between the base wash and a wash 20 percent darker: two tones, no gradient. Multiply by the pooling mask so colour darkens toward edges and creases, and by a world-aligned blotch noise for uneven pigment. The brush line is an inverted hull: a Masked two-sided Unlit material showing back faces only via `TwoSidedSign`, pushed along the vertex normal by World Position Offset, set as each component's Overlay Material. Hull width is driven by a noise sampled along world position, from zero to about 8 px, and the opacity mask is eroded by the dry-brush texture so strokes thin out and break.

### Lighting and atmosphere

Lumen off (`r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`). Every material is Unlit, so no lights or shadows are needed. The sky is a sphere with an Unlit paper-colour material. Depth is handled by Exponential Height Fog with Fog Inscattering Color `#f3ead7`, so distant hills fade into bare paper.

### Post-processing

Chain, all at Scene Color After Tonemapping:

1. `PP_InkLine`: Sobel on SceneDepth and WorldNormal adds inner crease lines in `#1c1a17`, its thickness modulated by screen-space noise.
2. `PP_Bleed`: a small 3 px blur applied only where the line mask is set, for ink bleed.
3. `PP_Paper`: multiply the paper fibre texture over the full frame and darken the frame edge slightly.

Tone Curve Amount 0 and Expand Gamut 0 so wash colours match the palette. Bloom, grain, fringe and motion blur off. FXAA (`r.AntiAliasingMethod=1`) avoids temporal smearing of the line texture.

### UI and effects

Panels are scroll textures with torn edges drawn as Box brushes; icons are round vermilion `#b23a2e` seal stamps; counters are rows of ink-pot images. Headings and numerals in a brush face such as Zen Antique, ink `#1c1a17` on paper. Niagara: a slash is one ribbon with a dry-brush texture whose opacity erodes over 0.5 s; hits throw 8 to 12 ink-splash sprites from a 4-frame SubUV; petal mesh particles spawn along the hero's footsteps and settle for 2 s.

## Do / Do not

Do:

- Vary stroke width from zero to very thick.
- Leave large areas of bare paper.
- Multiply a paper texture over the full frame.
- Let lines break and overshoot.

Do not:

- Do not use even-width outlines with flat clean fills; that reads as `082` or `011`.
- Do not drop line work and rely on soft watercolour shapes; that reads as `025`.
- Do not add three bands with pen hatching; that reads as `001`.
- Do not use saturated opaque colour.

## Nearest styles

- `082` Ukiyo-e woodblock: lines here swell, dry out and break like brush strokes, and colour pools unevenly in two wash tones; `082` has an even, fine carved keyline around clean flat printed colour.
- `025` Watercolour wash minimal: here almost every form is drawn with a black brush line; `025` is mostly lineless, built from soft pale wash shapes.
- `007` Rubber-hose 1930s cartoon: the line here runs from hair-thin to very thick over uneven washes on bare paper; `007` uses a thick outline of even weight around flat fills, with aged film grain.

# Art Nouveau ornamental poster

Reference works: Alphonse Mucha.

## References

- *Gismonda* (1894), Alphonse Mucha, lithographic poster. https://en.wikipedia.org/wiki/Gismonda
- *The Seasons* (1896), Alphonse Mucha, colour lithograph series. https://en.wikipedia.org/wiki/The_Seasons_(Mucha)
- *Hotel Tassel* (1893), Victor Horta, architecture. https://en.wikipedia.org/wiki/Hôtel_Tassel
- *The Kiss* (1908), Gustav Klimt, oil and gold leaf painting. https://en.wikipedia.org/wiki/The_Kiss_(Klimt)
- *Paris Metro entrances* (1900), Hector Guimard, cast-iron architecture. https://en.wikipedia.org/wiki/Paris_Metro_entrances_by_Hector_Guimard

## Visual definition

- **Shape language and proportions:** Long flowing curves everywhere: whiplash tendrils, hair in ribbon-like strands, lily and iris stems, peacock feathers. Figures are tall and framed by circles, arches and ornamental panels. Architecture and furniture curve like plants.
- **Line and outline:** Bold, smooth contour of varying weight around figures (heavier outside, finer inside), in dark brown rather than black.
- **Shading model:** Flat colour with at most one soft tone step; faces may have light gradient modelling.
- **Palette:** `#3b2f2f` `#e8d5a9` `#c9a24b` `#8fa98b` `#d9897a` `#6f8fa8` `#f3ead2` `#a8566a`. Muted warm pastels: cream, peach, sage green, dusty blue and rose, with gold and a dark brown line.
- **Lighting:** None, or a soft even light.
- **Texture and surface:** Dense ornament inside frames: mosaic halos, repeating floral and geometric borders, stylised stars, gold patterns on robes. Lithographic paper grain.
- **Atmosphere and post-processing:** Paper tint; no other effects.
- **Camera and framing:** Frontal, tall vertical format, centred figure inside a decorative frame.
- **UI and typography:** Panels sit in ornamental frames with arched or circular tops, whiplash-curve corners and floral borders in gold on cream; icons are stylised flowers, stars and feathers in a dark brown contour. Text is hand-drawn Art Nouveau display lettering with swelling curved strokes, in dark brown or gold. Numbers use the same lettering, rose for damage and sage green or gold for gains.
- **VFX and motion:** Particles are drifting petals, leaves, stars and gold flecks that follow long curling paths; hits show as a ring of radiating halo lines or a burst of petals. Motion is slow and flowing with long ease-in and ease-out, and hair, ribbons and cloth trail in S-curves.

## Fits

- **Genres:** `puzzle`, `rpg`, `exploration`, `detective-mystery`, `strategy`
- **Moods:** elegant, dreamy, romantic
- **Settings:** Belle Époque Paris, flower garden, theatre, fairy-tale court

## Unreal recipe

### Assets

Choose tall, graceful characters with long hair and cloth, and architecture or furniture with plant-like curves. For store packs, remove normal and roughness detail and bake albedo down to flat regions. Build by Blender script: ribbon hair strands and trailing sashes as curve-swept meshes, lily and iris stems, peacock feathers, and the decorative frames (circular halo discs, arched panels, floral borders) that stand behind characters as real scene geometry.

### Materials

Master `M_NouveauFlat`, Unlit. Colour comes from a `Flat` parameter in the muted pastel set (`#e8d5a9`, `#8fa98b`, `#d9897a`, `#6f8fa8`, `#a8566a`, `#f3ead2`). One optional tone step: N·L from a Material Parameter Collection light vector through SmoothStep with a narrow range, darkening by 12% only; faces instead get a soft vertical gradient. An `Ornament` texture parameter (tiling floral, star or mosaic pattern in `#c9a24b`) is blended in by a mask, used on robes, halos and borders but left off skin and plain backgrounds so ornament has rest areas around it.

The contour is an inverted hull: a Masked two-sided Unlit overlay material in `#3b2f2f` showing back faces only, with World Position Offset along the vertex normal. Its width is multiplied by a painted VertexColor channel so the line swells and tapers; a thinner post-process pass adds interior lines.

### Lighting and atmosphere

No dynamic lighting is needed: Lumen off, no shadows, no fog, no sky atmosphere. The backdrop is a cream `#f3ead2` Unlit dome or a decorative panel. Exposure is Manual.

### Post-processing

Post-process material one (Scene Color After Tonemapping, lower priority): fine interior lines from a Sobel on WorldNormal and CustomStencil, 1.5 px, dark brown. The outer hull runs 4 to 6 px, so silhouettes read heavier than inner edges. Material two: multiply by a lithographic paper-grain texture with a warm tint of `#e8d5a9` at 15%.

Volume settings: Tone Curve Amount 0, Bloom Intensity 0, Film Grain Intensity 0, Vignette Intensity 0, Scene Fringe Intensity 0, Motion Blur Amount 0, depth of field disabled. TSR anti-aliasing.

### UI and effects

Every UMG panel sits in a 9-slice gold-on-cream frame with whiplash corners; headers get an arched or circular top image. Titles use Limelight or Poiret One in `#3b2f2f` or `#c9a24b`; body text uses Cormorant. Numbers share the display face: rose `#a8566a` for damage, sage `#8fa98b` or gold for gains.

Niagara: petals, leaves, stars and gold flecks as unlit sprites, 10 to 30 at once, lifetime 3 to 5 s, moved by a curl-noise force so paths are long S-curves. A hit spawns a ring of 16 thin radiating halo lines that expand over 0.5 s with ease-out, plus a petal burst.

## Do / Do not

Do:

- Build forms from long whiplash curves.
- Frame the figure with a circle or arch and ornament borders.
- Use muted pastels with gold and a brown line.
- Vary contour weight smoothly.

Do not:

- Do not use straight streamlined geometry with chrome and stepped forms; that reads as `096`.
- Do not use an even thin keyline with blue-dominated flats; that reads as `082`.
- Do not fill the frame with interlaced knotwork in strong colours; that reads as `086`.
- Do not back-light glass panes with black leading; that reads as `054`.

## Nearest styles

- `082` Ukiyo-e woodblock: this style has a contour of changing weight, dense ornament borders, gold and many muted pastels; `082` has an even fine keyline, plain flat colour areas and a small palette built on blue.
- `086` Insular illuminated manuscript: this style has tall flowing figures in muted pastels with plain areas between the ornament; `086` has stiff geometric figures in strong red, blue and green, with knotwork that fills every border and shape.
- `096` Art Deco streamline: this style is outlined in brown, with plant-like curves and flat colour; `096` has no outline and shows straight, stepped, streamlined forms in smooth-shaded metal and stone.

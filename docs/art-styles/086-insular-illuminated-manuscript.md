# Insular illuminated manuscript

Reference works: Book of Kells; The Secret of Kells.

## References

- *Book of Kells* (c. 800), Columban monks (Iona and Kells), illuminated manuscript. https://en.wikipedia.org/wiki/Book_of_Kells
- *Lindisfarne Gospels* (c. 715-720), Eadfrith of Lindisfarne, illuminated manuscript. https://en.wikipedia.org/wiki/Lindisfarne_Gospels
- *The Secret of Kells* (2009), Cartoon Saloon (Tomm Moore and Nora Twomey), animated film. https://en.wikipedia.org/wiki/The_Secret_of_Kells
- *Song of the Sea* (2014), Cartoon Saloon (Tomm Moore), animated film. https://en.wikipedia.org/wiki/Song_of_the_Sea_(2014_film)

## Visual definition

- **Shape language and proportions:** Flat, geometric stylisation: figures built from circles and rounded rectangles with almond eyes; trees as spirals and concentric rings; everything fitted into circles, squares and bordered panels.
- **Line and outline:** Dark brown-black outline of even weight around every shape and every strand of ornament.
- **Shading model:** None. Flat colour.
- **Palette:** `#2b1d14` `#e9d8a6` `#c8962e` `#b3261e` `#1f6f6b` `#3b4fa0` `#6a3d7c` `#3f7d3a`. Vellum cream ground with gold-yellow, red, teal-green, blue and purple.
- **Lighting:** None.
- **Texture and surface:** Extremely dense ornament filling borders and shapes: interlaced knotwork bands, triple spirals, key patterns, rows of red dots, tiny interlocked animals. Vellum grain.
- **Atmosphere and post-processing:** Vellum overlay with slight mottling.
- **Camera and framing:** Flat, frontal, orthographic; compositions framed by ornamental borders.
- **UI and typography:** Panels are vellum blocks inside knotwork borders with spiral corner bosses; icons are tiny interlaced animals and geometric emblems outlined in dark brown. Text is a rounded insular half-uncial script in brown-black, with large decorated initials in red and gold. Numbers use the same pen-written script, red for damage and gold for rewards, often ringed by red dots.
- **VFX and motion:** Particles are flat outlined shapes: spirals, triple spirals, rows of red dots and gold flecks that unwind along curling paths. Hits burst as concentric rings or a rosette of flat petals. Animation is flat and graphic on twos, and knotwork lines draw themselves along their path.

## Fits

- **Genres:** `puzzle`, `platformer`, `exploration`, `action-adventure`, `rpg`, `tower-defense`
- **Moods:** mystical, reverent, whimsical
- **Settings:** early medieval Ireland, island monastery, enchanted forest, Viking raid coast

## Unreal recipe

### Assets

Almost nothing in a realistic pack suits this look, so build by Blender script: figures from circles and rounded rectangles with almond eyes, trees as spiral and concentric-ring discs, round towers, boats and beasts as flat-fronted low-relief shapes. Generate the ornament textures by script as well (Pillow or Blender curves): tiling knotwork bands, triple spirals, key patterns and red dot rows, each drawn with its own dark outline.

### Materials

Unlit master `M_Illuminated`. Inputs: `Flat` colour from the strong set (`#c8962e`, `#b3261e`, `#1f6f6b`, `#3b4fa0`, `#6a3d7c`, `#3f7d3a`) and an `Ornament` texture sampled with object-aligned UVs so every shape is filled with interlace, never left plain. The ornament texture carries its own `#2b1d14` lines, which keeps line weight even at any distance when the texture scale is tied to camera ortho width through a Material Parameter Collection scalar. Ground and sky planes use vellum `#e9d8a6`. No lighting input at all: no ramp, no rim.

### Lighting and atmosphere

No lights, no Lumen, no shadows, no fog. Use an orthographic camera, frontal, so nothing foreshortens. Exposure is Manual.

### Post-processing

Post-process material one at Scene Color After Tonemapping: outline from a Sobel on CustomStencil (stencil value per shape) and SceneDepth, constant 2.5 px at 1080p, colour `#2b1d14`. It surrounds every shape and matches the ornament's line weight. Material two: multiply by a vellum texture with slight mottling (low-frequency Noise at 5% plus a scanned grain). A screen-space border material or UMG overlay frames the play view with knotwork.

Volume settings: Tone Curve Amount 0, Expand Gamut 0, Bloom Intensity 0, grain 0, Vignette Intensity 0, Motion Blur Amount 0, no depth of field. FXAA (`r.AntiAliasingMethod=1`).

### UI and effects

UMG panels are vellum Box brushes inside a 9-slice knotwork border with spiral bosses at the corners. Body text uses Uncial Antiqua or a similar open-licence uncial face in `#2b1d14`; the first letter of each heading is a separate large image initial in `#b3261e` and `#c8962e`. Numbers use the same script, red for damage and gold for rewards, with a ring of red dots drawn by a small material in the User Interface domain.

Niagara: flat outlined sprite shapes only (spirals, triskeles, gold flecks, red dots), 8 to 20 per burst, lifetime 1 to 1.5 s, following curling paths from a vortex force, with flipbooks stepping at 12 frames per second. A hit spawns three concentric outlined rings or an 8-petal rosette that expands for 0.3 s and cuts out. Knotwork lines that "draw themselves" are meshes whose material reveals along UV with a Step on a time parameter.

## Do / Do not

Do:

- Fill borders and shapes with knotwork and spirals.
- Outline every element in dark brown.
- Fit compositions into circles and framed panels.
- Use a vellum ground.

Do not:

- Do not leave large plain areas with thread texture; that reads as `056`.
- Do not use flowing whiplash figures in muted pastels; that reads as `083`.
- Do not use glazed star-and-polygon tiling without figures or outlines; that reads as `100`.
- Do not add shading.

## Nearest styles

- `056` Embroidered tapestry: this style has strong red, blue, purple and gold on vellum, with ornament packed into every border and shape; `056` has muted colours, large plain areas and visible thread texture.
- `083` Art Nouveau ornamental poster: this style has stiff geometric figures, an even outline and strong colours with knotwork everywhere; `083` has tall flowing figures, a contour of changing weight and muted pastels with plain areas between the ornament.
- `100` Islamic geometric tile: this style has a dark outline around every element, flat matte colour and figures and animals; `100` has star-and-polygon tiles with pale grout lines, a glossy glazed surface and no figures.

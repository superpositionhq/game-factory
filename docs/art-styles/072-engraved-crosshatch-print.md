# Engraved crosshatch print

Reference works: Gustave Dore engravings.

## References

- *Illustrations for The Divine Comedy* (1861), Gustave Dore, wood engraving. https://en.wikipedia.org/wiki/Gustave_Doré
- *Melencolia I* (1514), Albrecht Durer, copper engraving. https://en.wikipedia.org/wiki/Melencolia_I
- *Knight, Death and the Devil* (1513), Albrecht Durer, copper engraving. https://en.wikipedia.org/wiki/Knight,_Death_and_the_Devil
- *The Rime of the Ancient Mariner (illustrated edition)* (1876), Gustave Dore, wood engraving. https://en.wikipedia.org/wiki/The_Rime_of_the_Ancient_Mariner

## Visual definition

- **Shape language and proportions:** Realistic, dramatic subjects: figures, drapery, rocks, clouds, architecture, rendered with careful volume.
- **Line and outline:** Black contour on forms, plus tone built entirely from fine parallel lines that follow the surface curvature.
- **Shading model:** Four to six tone levels from line density: bare paper, single hatch, closer hatch, cross-hatch, double cross-hatch, solid black. Lines swell and taper.
- **Palette:** `#14110f` `#f2ead8` `#3a332c` `#8a8072` `#d6ccb6`. Black ink on cream paper. The intermediate values listed are apparent tones of hatching.
- **Lighting:** Strong directional light with deep shadows and bright rim-lit edges; light rays drawn as parallel lines.
- **Texture and surface:** Hatching everywhere except highlights. Line direction changes by surface: horizontal for sky and water, curved around limbs, vertical for walls.
- **Atmosphere and post-processing:** Paper tone and slight ink spread; no colour.
- **Camera and framing:** Grand, composed views; any lens.
- **UI and typography:** Panels look like book plates: a thin double ruled border on cream paper `#f2ead8`, with engraved corner ornaments and a caption strip below. Text is a high-contrast old-style book serif with small-capital headings, numbers are old-style engraved numerals in black ink, and icons are small hatched vignettes; bars fill with hatching that gets denser, never with colour.
- **VFX and motion:** Smoke, dust, light rays and water spray are drawn as bundles of parallel or curling engraved lines, and impacts are radiating line bursts with bare-paper flashes. Motion is weighty and stately, with hatch lines that stay attached to surfaces instead of shimmering.

## Fits

- **Genres:** `soulslike`, `rpg`, `action-adventure`, `exploration`, `strategy`, `hack-and-slash`
- **Moods:** solemn, epic, ominous
- **Settings:** underworld, medieval kingdom, storm-tossed sea, gothic cathedral

## Unreal recipe

### Assets

Realistic, high-detail assets with strong volume: figures with drapery, rock faces, gothic architecture, gnarled trees, clouds as meshes or dense cards. Keep normal maps, because hatch direction and density read from the lit form; drop albedo colour. Every mesh needs clean, continuous UVs that run along the form (around limbs, up walls, across water), since hatching is anchored in UV space. Re-unwrap by script in Blender where a pack's UVs are chaotic, storing the hatch UV in a second channel.

### Materials

Hatching is applied per object in UV space, not in screen space, so lines stay attached to surfaces. Unlit materials cannot read lights, so `M_Engrave` is Unlit and computes its own tone: N dot L from a Material Parameter Collection sun vector (PixelNormalWS, so normal-map detail counts), multiplied by a baked ambient occlusion texture and a baked shadow mask, with a Fresnel term adding a bright rim. `MF_Engrave` then selects and blends six tileable stroke textures by that tone, sampled with the hatch UV: bare paper, single hatch, closer hatch, cross-hatch, double cross-hatch, solid. Darker layers are drawn with thicker strokes, so lines swell as tone deepens. Output is `#14110f` ink on `#f2ead8` paper and nothing between.

### Lighting and atmosphere

No Lumen and no real lights. The scene holds one logical sun, its direction set in the collection from C++, steep and from the side for deep shadow. Static cast shadows are baked per level into mask textures by a Blender script; movers get an elongated blob shadow drawn as hatch. The sky is a dome hatched with horizontal lines, clouds with curved ones. No fog: distance is shown by sparser, thinner hatching driven by PixelDepth.

### Post-processing

1. Contour pass at Scene Color After Tonemapping: Sobel on SceneDepth and WorldNormal, 2 px, `#14110f`.
2. Ink spread: a slight 1 px blur then re-threshold, softening line ends.
3. Paper: multiply by a cream fibre texture.

Tone Curve Amount 0, Saturation 0, Bloom 0, grain 0, vignette 0, Motion Blur Amount 0. Full resolution with FXAA; no pixelation, no dots.

### UI and effects

Book-plate panels: cream Border with a double 1 px ruled outline, corner ornament images and a caption strip. Headings in Cormorant small capitals, body in EB Garamond with old-style figures, all `#14110f`. Bars fill by swapping hatch textures of rising density.

Niagara: smoke and spray as sprites textured with curling parallel lines, alpha-masked, 2 to 4 s life; light rays as static cards of ruled lines; impacts as a 16-line radial burst with a one-frame bare-paper flash.

## Do / Do not

Do:

- Build all tone from line density.
- Make hatch lines follow surface curvature.
- Swell line width as tone darkens.
- Leave highlights as bare paper.

Do not:

- Do not use dot screens; that reads as `020`.
- Do not use pixel dither at low resolution; that reads as `041`.
- Do not use soft graphite smudges and grey tone; that reads as `073`.
- Do not add colour bands with hatching only in shadow; that reads as `001`.

## Nearest styles

- `020` Manga screentone monochrome: this style builds every grey from fine curved hatch lines that wrap around the forms, covering almost the whole picture; `020` fills flat areas with dot screens and leaves large clean black and white shapes.
- `073` Graphite pencil sketch: this style is pure black ink on cream paper with firm contours and precise, dense hatching; `073` is soft grey pencil with loose doubled lines, smudges and scribbled shading.
- `041` One-bit dither: this style is a mostly light page of smooth curved hatch lines at full resolution; `041` is a darker low-resolution image whose tone comes from square pixel dither patterns.

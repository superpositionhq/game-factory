# Manga screentone monochrome

Reference works: Berserk; Akira (manga).

## References

- *Berserk* (1989), Kentaro Miura, manga. https://en.wikipedia.org/wiki/Berserk_(manga)
- *Akira (manga)* (1982), Katsuhiro Otomo, manga. https://en.wikipedia.org/wiki/Akira_(manga)
- *Lone Wolf and Cub* (1970), Kazuo Koike and Goseki Kojima, manga. https://en.wikipedia.org/wiki/Lone_Wolf_and_Cub
- *Vagabond* (1998), Takehiko Inoue, manga. https://en.wikipedia.org/wiki/Vagabond_(manga)

## Visual definition

- **Shape language and proportions:** Realistic to semi-realistic drawing with dramatic foreshortening. Any subject; forms are described by line density.
- **Line and outline:** Black pen line with clear weight variation on every contour. Speed lines and focus lines radiate from the subject.
- **Shading model:** Tone comes from screentone: regular dot patterns at 2 or 3 fixed densities, plus solid black. No grey pixels; grey is always dots.
- **Palette:** `#000000` `#ffffff` `#8c8c8c` `#4d4d4d` `#d9d9d9`. Pure black and white. The grey values listed are the apparent tones of screentone at viewing distance.
- **Lighting:** Strong directional light so forms split into white, toned and black areas.
- **Texture and surface:** Dot screens at 45 degrees, fine pen hatching on rough materials, white highlights scratched out of tone.
- **Atmosphere and post-processing:** Threshold to two values. Optional panel border in black.
- **Camera and framing:** Dramatic angles, close-ups and wide establishing shots; any lens.
- **UI and typography:** White panels with black borders laid out like manga page frames, plus speech balloons and jagged shout balloons. Text is hand-lettered comic capitals in black, with heavy brush-drawn sound-effect lettering for emphasis. Damage numbers and counters are thick black brush numerals with a white edge; bars are solid black or filled with dot tone, never grey.
- **VFX and motion:** Effects are ink marks: radial speed lines, black ink splashes, white slash arcs scratched across tone, dust clouds drawn as outlined shapes with dot tone, and large sound-effect lettering on impact. Animation holds strong poses on twos or threes, with a one-frame black and white inversion on heavy hits.

## Fits

- **Genres:** `hack-and-slash`, `soulslike`, `fighting`, `action-adventure`, `survival-horror`, `detective-mystery`
- **Moods:** grim, intense, dramatic
- **Settings:** feudal Japan, dark medieval battlefield, post-apocalyptic city, demon-haunted castle

## Unreal recipe

### Assets

Any realistic or semi-realistic pack works, because form is redrawn in post. Keep geometry and normal maps (they feed line and tone), but replace base colour with plain greys that set each surface's tone class: white, light tone, dark tone or black. Mark rough materials such as stone, bark and cloth with a stencil value so they receive pen hatching. Build speed-line and focus-line cards from scratch as radial meshes with a streak alpha.

### Materials

`M_MangaBase`, Default Lit, Roughness 1, Specular 0, grey base colour parameter. The surface does no stylising. Effect materials are Unlit, pure black or pure white, Masked. Translucency is avoided; anything semi-transparent would create grey.

### Lighting and atmosphere

One strong Directional Light with Source Angle 0 and Virtual Shadow Maps, plus a weak Sky Light so forms divide into white, toned and black regions. Lumen GI off. No fog, no atmosphere; the background is white paper. Manual exposure.

### Post-processing

Disable anything that makes soft greys: bloom, grain, vignette, fringe, depth of field, Motion Blur Amount 0, and set `r.AntiAliasingMethod=0`, since anti-aliasing blends black and white. Raise `r.ScreenPercentage` to 150 to 200 for smoother edges by supersampling before the threshold. Chain at Scene Color After Tonemapping:

1. `PP_Tone`: luminance of PostProcessInput0 is sorted into four classes. White and solid black output directly. The two middle classes output a 45 degree screen-space dot grid at two fixed dot sizes (apparent `#d9d9d9` and `#8c8c8c`), each dot compared with Step so pixels are only `#000000` or `#ffffff`. Stencil-tagged rough surfaces use short hatch strokes. Specular peaks cut white through tone.
2. `PP_Pen`: Sobel on SceneDepth and WorldNormal, black, width 1.5 to 4 px varied by depth discontinuity size and a noise lookup, so silhouettes are heavy and inner lines fine.
3. An optional black panel border.

Dot pitch stays fixed in screen pixels (about 5 px at 1080p), clean and regular in chosen areas on a mostly white page; this is what keeps it from a pixel-dither look.

### UI and effects

Menus are laid out as manga page frames: white Box panels with 3 px black outlines and gutters, speech-balloon and jagged shout-balloon 9-slice brushes. Text is comic capitals (Comic Neue Bold, Bangers); sound words use a heavy brush face (Rock Salt, Yuji Boku). Numbers are thick black brush digits with a white font outline. Bars fill with solid black or a dot-pattern UI material. Niagara: radial speed-line cards, black ink splash sprites, white slash arcs, outlined dust clouds, all stepped on twos or threes. Heavy hits invert the frame for one frame through a parameter in `PP_Tone`.

## Do / Do not

Do:

- Output only pure black and pure white pixels.
- Use dot screens at fixed densities for tone.
- Vary pen line weight.
- Add radial speed or focus lines for action.

Do not:

- Do not use ordered or noise dithering over the full frame at low resolution; that reads as `041`.
- Do not build tone from long parallel engraved lines; that reads as `072`.
- Do not allow grey or coloured fills.
- Do not add a single colour accent; that reads as `069`.

## Nearest styles

- `041` One-bit dither: `041` is a dark, low-resolution image where pixel-sized dither patterns cover the whole frame and there is no pen line; this style is a mostly white page with drawn pen outlines and clean dot tone in chosen areas.
- `072` Engraved crosshatch print: `072` builds all its tone from long parallel and crossed engraved lines; this style builds tone from regular dot screens and solid black.
- `073` Graphite pencil sketch: `073` has soft grey pencil tones and smudged edges on paper; this style has only pure black and pure white with sharp pen edges.

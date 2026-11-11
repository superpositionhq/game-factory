# Ukiyo-e woodblock

Reference works: Hokusai.

## References

- *The Great Wave off Kanagawa* (1831), Katsushika Hokusai, woodblock print. https://en.wikipedia.org/wiki/The_Great_Wave_off_Kanagawa
- *Fine Wind, Clear Morning* (1831), Katsushika Hokusai, woodblock print. https://en.wikipedia.org/wiki/Fine_Wind,_Clear_Morning
- *The Fifty-three Stations of the Tokaido* (1834), Utagawa Hiroshige, woodblock print series. https://en.wikipedia.org/wiki/The_Fifty-three_Stations_of_the_Tōkaidō
- *Sudden Shower over Shin-Ohashi Bridge and Atake* (1857), Utagawa Hiroshige, woodblock print. https://en.wikipedia.org/wiki/Sudden_Shower_over_Shin-Ōhashi_Bridge_and_Atake

## Visual definition

- **Shape language and proportions:** Stylised nature and travel scenes: waves with claw-like foam fingers, a conical mountain, pines with layered flat canopies, bridges, small figures in straw hats. Flattened space with high horizon or diagonal layout.
- **Line and outline:** Even, fine, dark keyline around every shape (carved line), slightly irregular, dark blue-black rather than pure black.
- **Shading model:** None on objects. Flat colour areas; skies and water have one smooth printed gradient (bokashi) from a dark band at the top edge to paper.
- **Palette:** `#1d3557` `#3d6a9e` `#f1e3c4` `#c9d6c2` `#c8553d` `#2b2b2b` `#e8c98a`. Prussian blue in several strengths, pale buff paper, soft green, with small accents of brick red and ochre.
- **Lighting:** None. Rain is drawn as thin dark parallel lines; mist as blank paper bands.
- **Texture and surface:** Paper fibre and faint wood-grain in large colour areas; slight colour misregistration against the keyline.
- **Atmosphere and post-processing:** Paper overlay; optional title cartouche block.
- **Camera and framing:** Flat, elevated views; large foreground element framing a small distant subject.
- **UI and typography:** Panels are buff paper rectangles with a fine blue-black keyline, shaped like title cartouches; icons are flat woodblock motifs, and red seal stamps mark alerts and confirmations. Text is brush-written calligraphic lettering in blue-black, set in vertical or cartouche blocks. Counters and damage numbers are brush-written numerals in blue-black, with brick red for critical values.
- **VFX and motion:** Splashes, smoke and dust are flat keylined shapes: claw-fingered foam, curled cloud bands, thin parallel rain lines. Hits show as short radiating line bursts or a spray of paper-coloured droplets. Motion uses held poses animated on twos or threes, with scenery layers that slide like printed sheets.

## Fits

- **Genres:** `action-adventure`, `exploration`, `hack-and-slash`, `stealth`, `strategy`, `soulslike`
- **Moods:** serene, contemplative, dramatic
- **Settings:** Edo-period Japan, coastal fishing village, mountain road, stormy sea

## Unreal recipe

### Assets

Suitable packs are stylised Japanese villages, pines, boats and bridges with simple readable silhouettes. Strip normal and roughness maps; repaint each albedo by script (Pillow) to one flat palette colour per region. Build by script what the prints are known for: wave meshes with claw-fingered foam edges, a conical mountain, pine canopies as stacked flat discs, curled cloud bands and small straw-hat figures. Arrange scenery as a few depth layers so it can slide like printed sheets.

### Materials

Unlit master `M_Woodblock` with a `Flat` colour parameter chosen from `#1d3557`, `#3d6a9e`, `#c9d6c2`, `#c8553d`, `#e8c98a` and paper `#f1e3c4`. A WorldAlignedTexture sample of a tiling wood-grain mask multiplies the colour by 0.94 to 1.0 so large areas show faint grain. Sky and water use a second instance type, `M_Bokashi`: a Lerp from `#1d3557` to paper driven by screen-space V (sky) or by PixelDepth (water), giving one smooth printed gradient with the dark band at the top edge. No object receives light, so no tone steps appear anywhere.

### Lighting and atmosphere

Lumen off, no directional light, no shadows, no height fog. Mist is made of Unlit paper-coloured bands placed between scenery layers. Rain is a mesh of thin `#2b2b2b` parallel lines at a fixed slant in front of the camera. Manual exposure, compensation fixed.

### Post-processing

Three post-process materials, ordered by Blendable Priority at Scene Color After Tonemapping:

1. Keyline: Roberts cross on SceneDepth, WorldNormal and CustomStencil (per-region stencil values), 1.5 to 2 px at 1080p, colour `#1d3557` darkened toward `#2b2b2b`, with the sample offset perturbed by a low-frequency Noise so the carved line is slightly irregular but even in weight.
2. Misregistration: the colour layer is sampled 1.5 px off from the keyline pass.
3. Paper: multiply by a fibre texture tinted `#f1e3c4`.

Set Tone Curve Amount 0, Bloom Intensity 0, Vignette Intensity 0, grain off, Motion Blur Amount 0, no depth of field. Use FXAA (`r.AntiAliasingMethod=1`).

### UI and effects

UMG panels are `#f1e3c4` Box brushes with a 2 px blue-black border, tall and narrow like title cartouches; alerts and confirmations stamp a brick red `#c8553d` seal image with a 0.1 s scale-in. Text uses Zen Antique in `#1d3557`; vertical captions stack one character per line in a Vertical Box. Numbers are the same face, red for critical values.

Niagara uses flipbook sprites drawn as keylined flat shapes at 8 frames per second: claw-foam splashes, curled smoke bands, dust curls. A hit emits 8 to 10 short radiating line sprites for 0.2 s or a spray of 12 paper-coloured droplets on ballistic arcs. Nothing is additive and nothing fades softly; sprites end by cutting out.

## Do / Do not

Do:

- Outline every shape with an even fine keyline.
- Use flat colour with one edge gradient in sky or water.
- Build the palette around Prussian blue and buff paper.
- Stylise foam, clouds and trees into repeated motifs.

Do not:

- Do not use variable brush strokes with wash and two tones; that reads as `022`.
- Do not use clean white ground and brighter colours without paper texture; that reads as `011`.
- Do not add whiplash ornament, gold halos and floral borders; that reads as `083`.
- Do not add smooth shading.

## Nearest styles

- `022` Sumi-e ink wash: this style puts an even fine keyline around every shape and fills it with flat colour; `022` has calligraphic brush strokes of changing width, ink washes in two tones and visible brush texture.
- `011` Clear-line adventure comic: this style prints on buff paper with visible fibre and wood grain, builds its colours around Prussian blue and has a gradient band in the sky; `011` has a clean white ground, brighter varied colours and no paper texture.
- `083` Art Nouveau ornamental poster: this style keeps colour areas plain and the palette small and blue-led; `083` surrounds tall figures with dense ornament, gold halos and floral borders in many muted pastels.

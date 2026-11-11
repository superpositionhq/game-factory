# Pointillist dot field

Reference works: Georges Seurat.

## References

- *A Sunday Afternoon on the Island of La Grande Jatte* (1886), Georges Seurat, oil painting. https://en.wikipedia.org/wiki/A_Sunday_Afternoon_on_the_Island_of_La_Grande_Jatte
- *Bathers at Asnieres* (1884), Georges Seurat, oil painting. https://en.wikipedia.org/wiki/Bathers_at_Asnières
- *The Circus* (1891), Georges Seurat, oil painting. https://en.wikipedia.org/wiki/The_Circus_(Seurat)
- *The Port of Saint-Tropez* (1901), Paul Signac, oil painting. https://en.wikipedia.org/wiki/Paul_Signac

## Visual definition

- **Shape language and proportions:** Calm, formal, static compositions. Figures and trees are simplified into smooth columns, cones and ovals with stiff poses, mostly in profile or frontal.
- **Line and outline:** None. Edges are where dot colours change; a slight halo of contrast appears along edges.
- **Shading model:** Smooth modelling achieved by changing the proportions of dot colours: more yellow and orange dots in light, more blue and violet dots in shadow.
- **Palette:** `#2f6fb0` `#f2c94c` `#e2574c` `#4caf6a` `#f08a3c` `#8a5fb5` `#f5efdc`. A small set of pure pigments (blue, yellow, red, green, orange, violet) plus white; apparent colours form by optical mixing.
- **Lighting:** Clear afternoon sun with long, soft, blue-violet shadows.
- **Texture and surface:** Uniform small round dots of pure colour, evenly spaced, covering the whole image including the sky; often a painted dotted border.
- **Atmosphere and post-processing:** Full-frame dot pass; no blur.
- **Camera and framing:** Frontal, level, wide park or riverside view; long lens flattening.
- **UI and typography:** Every panel has a painted dotted border in contrasting colours, like Seurat's painted frames, around a pale cream `#f5efdc` field of fine dots. Text is a tall, formal poster-style sans with even strokes in deep blue `#2f6fb0`, numbers are upright and evenly spaced in the same face, and icons are simple stiff silhouettes filled with dots.
- **VFX and motion:** Particles are loose dots that scatter out of a surface and settle back into the dot field; impacts are rings of dots in the opposite colour (orange against blue, yellow against violet). Motion is slow and poised, with held formal poses and smooth glides instead of quick snaps.

## Fits

- **Genres:** `puzzle`, `strategy`, `simulation`, `sports`, `tower-defense`, `exploration`
- **Moods:** calm, formal, sunny
- **Settings:** riverside park, seaside harbour, circus ring, Sunday promenade

## Unreal recipe

### Assets

Smooth, simplified, formal shapes: trees as ovals on columns, figures as stiff cone-and-cylinder forms with parasols and hats, boats, a riverbank, a circus ring. Build most by Blender script with subdivision so surfaces are perfectly smooth; a stylised character pack can be used with textures removed and poses limited to profile and frontal. Remove folds and small detail from any store mesh.

### Materials

Default Lit, roughness 1, specular 0, one flat Base Colour per material instance. No normal maps. Smooth vertex normals everywhere; a faceted edge would show as a line of contrasting dots.

### Lighting and atmosphere

Lumen GI on for soft bounce. One Directional Light at about 30 degrees, warm, Source Angle 2, casting long shadows. Sky Light tinted blue-violet (`#8a5fb5` mixed with `#2f6fb0`) at intensity 1.5 so shadows are coloured and clearly lighter than black. Plain gradient sky dome; no fog and no depth blur, because the dot field must be equally crisp everywhere. Manual exposure.

### Post-processing

PPV: Tone Curve Amount 0.5, Saturation 1.1, Bloom 0, grain 0, vignette 0, fringe 0, depth of field off, Motion Blur Amount 0.

One post material at Scene Color After Tonemapping, a Custom node:

1. Lay a jittered hexagonal lattice of round dots, 5 to 6 px diameter at 1080p, spacing equal to the diameter, each centre offset by a hash of up to 25 percent so the field looks hand-placed, never a mechanical screen.
2. For each dot, read the scene colour at its centre and choose one pigment from `#2f6fb0`, `#f2c94c`, `#e2574c`, `#4caf6a`, `#f08a3c`, `#8a5fb5` and white. Selection is stochastic: express the target colour as weights over its two or three nearest pigments and pick by a per-dot random number, so proportions give the optical mix.
3. Bias weights by luminance: more yellow and orange in light, more blue and violet in shade.
4. Along depth edges, push the two sides apart in value by 10 percent for the contrast halo.
5. Between dots show `#f5efdc`.

Anchor the lattice to the screen and keep camera motion slow and gliding.

### UI and effects

Each panel is a Border whose 9-slice frame texture is a band of contrasting dots (orange on blue, yellow on violet) round a cream field of fine pale dots. Text in Josefin Sans SemiBold or Poiret One, upright capitals, `#2f6fb0`.

Niagara: particles are round opaque sprites the size of the screen dots in pure pigments, leaving a surface, hanging 0.6 s and easing back. Impacts are a ring of 24 dots in the complementary pigment expanding over 0.5 s.

## Do / Do not

Do:

- Cover the entire frame with small round dots.
- Use only a small set of pure pigments.
- Model light by changing dot proportions.
- Keep forms smooth, simplified and static.

Do not:

- Do not use a regular rotated halftone grid with black outlines; that reads as `081` or `009`.
- Do not use elongated, varied brush dabs; that reads as `075`.
- Do not use square tiles with grout; that reads as `055`.
- Do not mix colours inside a dot.

## Nearest styles

- `075` Impressionist broken colour: this style covers smooth, stiff forms with even round dots of a few pure pigments; `075` dissolves its forms into irregular, elongated dabs of many blended pastel colours.
- `081` Ben-Day pop art: this style has no outlines and covers the whole picture with hand-placed dots; `081` has thick black outlines and uses a mechanical dot grid only in some areas, next to flat colour.
- `055` Mosaic tessera: this style has no gaps or lines between its marks and models forms smoothly with round dots; `055` is built from square tiles with dark grout lines and stepped tile tones.

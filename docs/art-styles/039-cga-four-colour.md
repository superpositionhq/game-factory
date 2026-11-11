# CGA four-colour

Reference works: Alley Cat.

## References

- *Alley Cat* (1983), Synapse Software (Bill Williams), video game. https://en.wikipedia.org/wiki/Alley_Cat_(video_game)
- *Digger* (1983), Windmill Software, video game. https://en.wikipedia.org/wiki/Digger_(video_game)
- *Lode Runner* (1983), Broderbund (Doug Smith), video game. https://en.wikipedia.org/wiki/Lode_Runner
- *Paratrooper* (1982), Orion Software (Greg Kuperberg), video game. https://en.wikipedia.org/wiki/Paratrooper_(video_game)

## Visual definition

- **Shape language and proportions:** Chunky pixel shapes at 320x200. Objects are simple icons: a few rectangles and diagonal steps.
- **Line and outline:** Black gaps and black outlines separate cyan, magenta and white areas where needed.
- **Shading model:** None. Intermediate tones are made by checkerboard dithering two of the four colours.
- **Palette:** `#000000` `#55ffff` `#ff55ff` `#ffffff` `#00aaaa` `#aa00aa`. Exactly four colours on screen: black, bright cyan, bright magenta and white. The two darker hex values listed are the low-intensity variant of the same palette; use one intensity per frame.
- **Lighting:** None.
- **Texture and surface:** Checker and stripe dither patterns; flat fills.
- **Atmosphere and post-processing:** 320x200 output with non-square pixels (stretch to 4:3), optional scanlines and composite colour bleed.
- **Camera and framing:** Fixed side or front view; in 3D, a fixed perspective with simple forms.
- **UI and typography:** Flat black panels with a one-pixel cyan `#55ffff` or magenta `#ff55ff` border, and blocky icons of a few rectangles. Type is a chunky 8x8 px bitmap face in capitals, as in early PC text modes. Score and lives counters sit in a single row at the top in white or cyan, with magenta for highlights.
- **VFX and motion:** Effects are bursts of a few white and magenta pixels, and a hit makes a sprite flicker by swapping its colours; nothing is transparent. Animation has two or three frames per cycle and sprites move in jerky steps of several pixels.

## Fits

- **Genres:** `platformer`, `puzzle`, `top-down-shooter`, `tower-defense`, `roguelike`
- **Moods:** quirky, garish, nostalgic
- **Settings:** back alley, underground mine, brick maze, night-sky gun emplacement

## Unreal recipe

### Assets

Chunky iconic shapes: a few rectangles and stepped diagonals per object. Draw sprites and backgrounds by script at 320x200 using only four index values, or build simple box-based 3D props from scratch with Geometry Script for a fixed perspective camera. Store packs are unsuitable beyond rough silhouettes. Checker and stripe dither patterns are baked into the textures at one-texel scale. Import with Filter Nearest, NoMipmaps, Texture Group 2D Pixels (Unfiltered).

### Materials

`M_CGA`, Unlit, opaque or Masked only; nothing is translucent. Each instance picks one of three flat fills (cyan, magenta, white) or a checker of two palette colours generated in screen space: `Floor` of the 320x200 pixel coordinate, x plus y modulo 2, selecting between two colour parameters. Screen-space dither keeps the checker stable at one pixel regardless of distance. Black gaps between adjacent colour areas come from 1 px black outlines in the sprite art, or from thin black hull geometry on 3D props. Hit flicker swaps the cyan and magenta parameters for 0.1 s.

### Lighting and atmosphere

No lighting. Lumen off (`r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`), ambient occlusion off, no lights, fog or sky; the background is pure `#000000`. Fixed exposure.

### Post-processing

Render to a 320x200 render target and present it stretched to a 4:3 area (pixels 1.2 times taller than wide) with nearest sampling, pillarboxed on wide screens. `r.AntiAliasingMethod=0`. Post materials at Scene Color After Tonemapping:

1. `PP_CGAPalette`: snaps every pixel to the nearest of `#000000`, `#55ffff`, `#ff55ff`, `#ffffff`. A switch parameter selects the low-intensity set (`#00aaaa`, `#aa00aa`, light grey) for a whole frame; never mix the two sets.
2. `PP_Composite` (optional): on the upscaled image, darken alternate output rows by 15 percent for scanlines and blur chroma horizontally by one source pixel for composite colour bleed.

Tone Curve Amount 0 and Expand Gamut 0, or the palette values shift. Bloom, grain, vignette, fringe, depth of field, Motion Blur Amount 0.

### UI and effects

Panels are flat black with a 1 px `#55ffff` or `#ff55ff` border. Font: an 8x8 PC text-mode style face such as Press Start 2P or VT323 in capitals, unfiltered. Score and lives sit in one row at the top in white or cyan, highlights in magenta; icons are two or three rectangles. Effects: bursts of 4 to 8 single white and magenta pixels flying outward for 0.3 s, as sprite particles snapped to the 320x200 grid with opaque Unlit material. Sprites animate with two or three frames and move in steps of 2 to 4 pixels.

## Do / Do not

Do:

- Use only black, cyan, magenta and white.
- Dither with a checkerboard for extra tones.
- Render at 320x200 and stretch to 4:3.
- Keep shapes iconic and blocky.

Do not:

- Do not use green shades; that reads as `038`.
- Do not use a wider tile palette; that reads as `042`.
- Do not draw glowing lines on black without fills; that reads as `040`.
- Do not anti-alias.

## Nearest styles

- `038` Game Boy four-shade green: this style is harsh bright cyan, magenta and white on black; `038` is four soft olive greens.
- `042` NES 8-bit tile: this style shows only black, cyan, magenta and white, with checkerboard dither for in-between tones; `042` mixes many colours on one screen, such as red, blue, green and orange.
- `040` Vector display glow: this style fills areas with solid and checker-dithered pixels; `040` draws only thin glowing lines on black and fills nothing.

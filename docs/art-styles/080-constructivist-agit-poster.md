# Constructivist agit poster

Reference works: El Lissitzky; Rodchenko.

## References

- *Beat the Whites with the Red Wedge* (1919), El Lissitzky, lithographic poster. https://en.wikipedia.org/wiki/Beat_the_Whites_with_the_Red_Wedge
- *Books (Please)! In All Branches of Knowledge* (1924), Alexander Rodchenko, poster. https://en.wikipedia.org/wiki/Alexander_Rodchenko
- *Monument to the Third International* (1920), Vladimir Tatlin, architectural model. https://en.wikipedia.org/wiki/Tatlin's_Tower
- *Black Square* (1915), Kazimir Malevich, oil painting. https://en.wikipedia.org/wiki/Black_Square
- *Battleship Potemkin* (1925), Sergei Eisenstein, silent film. https://en.wikipedia.org/wiki/Battleship_Potemkin

## Visual definition

- **Shape language and proportions:** Pure geometric elements in dynamic diagonal arrangements: wedges, circles, bars, arcs, megaphone cones, spiral towers and scaffolds. Compositions thrust along one strong diagonal.
- **Line and outline:** Thin ruled black lines and arcs as construction elements. No outline around colour shapes.
- **Shading model:** None. Flat ink. Photographic elements appear as grey halftone cut-outs.
- **Palette:** `#d7261e` `#111111` `#efe6d0` `#8a8a8a` `#f4f0e4`. Red, black and unbleached paper, with grey. No other colours.
- **Lighting:** None.
- **Texture and surface:** Print texture: slightly uneven ink coverage, paper fibres and yellowing, coarse halftone dots inside photomontage pieces, slight misregistration.
- **Atmosphere and post-processing:** Paper overlay; optional 1 px offset of the red plate.
- **Camera and framing:** Flat poster view, or steep diagonal low angle on 3D structures.
- **UI and typography:** UI is poster layout: solid red `#d7261e` and black `#111111` bars, wedges and circles on unbleached paper `#efe6d0`, often set on a diagonal, with thin ruled lines. Text is a heavy condensed all-capitals grotesque sans, set large and sometimes rotated to follow the diagonal; numbers are big block numerals in red or black, and icons are flat geometric pictograms.
- **VFX and motion:** Effects are flat graphic shapes: red wedges that stab in on impact, expanding black rings, radiating ruled lines and megaphone-style cones. Motion is fast and mechanical along diagonals, with hard cuts, snap zooms and stamped-on shapes in the manner of Eisenstein's montage; photomontage pieces move as stiff cut-outs.

## Fits

- **Genres:** `strategy`, `tower-defense`, `top-down-shooter`, `vehicle-combat`, `fighting`, `platformer`
- **Moods:** urgent, militant, bold
- **Settings:** revolutionary city, factory floor, battleship harbour, rally square

## Unreal recipe

### Assets

Ruled geometric solids built by script: wedges, discs, rings, long bars, arcs, megaphone cones, lattice scaffolds and spiral towers, with exact edges and no bevels. Lay scenes out so the dominant elements align to one diagonal, 25 to 40 degrees. Photomontage pieces are the one use for realistic assets: render a character, crowd, ship or machine from a store pack to a greyscale image by script, cut it to its alpha silhouette and place it as a stiff card.

### Materials

`M_Ink` is Unlit with colour limited to `#d7261e` and `#111111`; paper `#efe6d0` and `#f4f0e4` is the backdrop. Uneven coverage: multiply ink by a low-contrast blotch noise (0.9 to 1.0) in object space. `M_Photo` is Unlit: N dot L from a Material Parameter Collection vector, or the baked render, converted to a coarse dot screen in screen space at 45 degrees, about 8 px pitch, printing `#111111` and `#8a8a8a` on paper. Only photomontage pieces use it. Thin construction lines are 1 to 2 cm bar meshes and arc strips in black. Mark red objects with CustomDepth stencil 1.

### Lighting and atmosphere

No lights, no Lumen, no fog, no shadows. Flat poster views use an orthographic camera; 3D structures are shot from a steep low angle with the camera rolled so verticals follow the composition's diagonal. Paper fills everything that is not ink.

### Post-processing

Tone Curve Amount 0, manual exposure. Post materials at Scene Color After Tonemapping:

1. Misregistration: where CustomStencil equals 1 at a UV offset of one pixel right and down, print red there, so the red plate sits 1 px off the black.
2. Paper: multiply by a fibre texture with yellowing toward the edges.

Bloom 0, PPV grain 0 (grain is in the paper), vignette 0, fringe 0, depth of field off, Motion Blur Amount 0. FXAA. No outline pass; colour shapes are never lined. Snap zooms are cuts between two fixed fields of view.

### UI and effects

Layouts are poster compositions: red and black bars, wedges and circles as Image widgets with Render Transform Angle matching the scene diagonal, thin 1 px rules, paper ground. Text in Bebas Neue or Anton capitals, very large, some rotated to the diagonal. Scores are oversized block numerals in red or black.

Niagara uses mesh renderers and opaque Unlit shapes: a red wedge stabbing in over 0.08 s and holding 0.2 s; a black ring expanding over 0.3 s; 12 ruled lines radiating from a point; megaphone cones for shouts and alarms. Shapes stamp on at full size and cut off without fading.

## Do / Do not

Do:

- Compose along one strong diagonal.
- Use red, black and paper only.
- Use ruled geometric wedges, circles and bars.
- Include a halftone photomontage element.

Do not:

- Do not use hand-cut crooked shapes with orange or blue fields; that reads as `064`.
- Do not restrict to horizontals and verticals with yellow and blue; that reads as `079`.
- Do not darken the frame with jagged anime shapes; that reads as `008`.
- Do not use balanced primary solids; that reads as `098`.

## Nearest styles

- `064` Mid-century cut-paper poster: this style places ruled, exact wedges, circles and bars in red and black on bare paper; `064` fills the frame with a strong orange, red or blue field and crooked scissor-cut shapes.
- `008` Red-black pop-punk graphic cel: this style is a light paper-coloured frame with unlined geometric shapes; `008` is mostly red and black, with outlined anime characters and jagged torn shapes.
- `098` Bauhaus primary geometry: this style is flat red and black ink on paper, composed on a diagonal; `098` uses red, blue and yellow solids with soft shading in a balanced arrangement.

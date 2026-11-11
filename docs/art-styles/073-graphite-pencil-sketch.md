# Graphite pencil sketch

Reference works: Take On Me (a-ha music video).

## References

- *Take On Me (music video)* (1985), Steve Barron (animation by Michael Patterson and Candace Reckinger), rotoscoped pencil animation. https://en.wikipedia.org/wiki/Take_On_Me
- *Hotel Dusk: Room 215* (2007), Cing, video game. https://en.wikipedia.org/wiki/Hotel_Dusk:_Room_215
- *Drawing Hands* (1948), M. C. Escher, lithograph. https://en.wikipedia.org/wiki/Drawing_Hands

## Visual definition

- **Shape language and proportions:** Observed, natural proportions drawn loosely. Forms are found with several overlapping searching lines rather than one clean contour.
- **Line and outline:** Grey graphite lines, 1 to 2 px, doubled or tripled along contours, with gaps and overshoot. Lines redraw slightly differently every few frames (boiling).
- **Shading model:** Three to five tone levels of diagonal pencil shading: light scribble, denser scribble, cross layer. Shading strokes are short and at a consistent hand angle.
- **Palette:** `#f7f5ef` `#4a4a4a` `#8c8c8c` `#c8c6c0` `#2e2e2e`. White paper and graphite greys. No black darker than soft pencil.
- **Lighting:** Simple single light so shading falls on one side.
- **Texture and surface:** Paper tooth showing through pencil; smudges; construction lines left in place.
- **Atmosphere and post-processing:** Line boil at 8 to 12 changes per second; paper texture.
- **Camera and framing:** Any; hand-held feel suits the look.
- **UI and typography:** UI looks drawn in a sketchbook: panels are loose hand-ruled pencil boxes with overshooting corners on white paper `#f7f5ef`, and icons are quick pencil doodles. Text is casual pencil handwriting, numbers are scribbled and circled or underlined for emphasis, and everything stays in graphite greys with selected items shaded darker.
- **VFX and motion:** Effects are drawn marks: scribbled dust clouds, speed lines, short radiating pencil dashes on impact and eraser smears for fades. Animation is rotoscoped, lifelike motion held on twos or threes, with every line boiling between drawings.

## Fits

- **Genres:** `detective-mystery`, `puzzle`, `exploration`, `racing`, `platformer`
- **Moods:** intimate, wistful, playful
- **Settings:** old roadside hotel, sketchbook pages, 1980s diner, city backstreets

## Unreal recipe

### Assets

Natural, observed subjects from realistic packs: rooms, streets, cars, people with motion-captured animation, which gives the rotoscoped feel. Geometry detail matters more than textures; strip albedo to flat mid grey and keep normal maps only where they describe real form such as folds. Add a few construction-line props by script: thin centre-line and box-guide meshes left around key objects.

### Materials

Scene materials are Default Lit, Base Colour 0.7 grey, roughness 1, so the lit buffer holds a clean tone for shading. No per-object hatching; pencil work is done in post, in screen space, which suits the boiling line.

### Lighting and atmosphere

One Directional Light from upper left with a small Sky Light fill at 0.3, Lumen off, so shade falls on one side with a simple terminator. Virtual Shadow Maps on with a soft Source Angle of 2; cast shadows become scribble areas. No fog; the background is paper. Manual exposure.

### Post-processing

One post material at Replacing the Tonemapper, built around a Custom node, with a seed parameter `Boil` that C++ changes 8 to 12 times a second:

1. Paper: start from `#f7f5ef` times a paper-tooth texture.
2. Shading: take luminance of PostProcessInput0, split into four bands; each darker band adds one layer of a short-stroke diagonal scribble texture at a fixed 40 degree hand angle, the darkest adding a crossed layer. Offset the texture UV by the seed. Clamp the darkest result to `#2e2e2e`.
3. Contours: sample a depth and normal edge detector three times, each with UVs displaced by a different low-frequency noise (amplitude 2 to 3 px, offset by the seed), and draw them at 1 to 2 px in `#4a4a4a`, `#8c8c8c` and `#8c8c8c`. The offsets give doubled, overshooting, gapped lines; multiply by tooth so strokes break up.
4. Smudge: add a faint blurred copy of the shading in `#c8c6c0`.

PPV: Bloom 0, grain 0, vignette 0, fringe 0, depth of field off, Motion Blur Amount 0. TSR off in favour of FXAA, because temporal accumulation smears the reseeded lines. Hold character animation on twos or threes at 8 to 12 Hz in step with the seed.

### UI and effects

Panels are Box brushes drawn from a hand-ruled pencil rectangle texture with overshooting corners, no fill. Text in Caveat or Patrick Hand, `#4a4a4a`; selected items `#2e2e2e` with a scribble underline image; important numbers circled.

Niagara: scribbled dust clouds as a 4-frame SubUV flipbook of pencil loops at 10 Hz, speed lines as short grey streak sprites, impact as eight radiating dashes for 0.2 s. Fades use a wiping eraser-smear mask instead of alpha.

## Do / Do not

Do:

- Draw contours with two or three overlapping loose lines.
- Shade with short diagonal strokes at one hand angle.
- Keep the darkest value a soft grey.
- Re-seed line wobble several times per second.

Do not:

- Do not use pure black ink and precise hatching; that reads as `072`.
- Do not use dot screentone; that reads as `020`.
- Do not leave the frame nearly empty white with black splats; that reads as `074`.
- Do not use one clean constant-width contour; that reads as `011`.

## Nearest styles

- `072` Engraved crosshatch print: this style is soft grey pencil on white paper with loose, doubled contours and scribbled shading; `072` is pure black ink with firm contours and dense, precise hatching.
- `074` White void ink-splat: here every object is outlined and shaded in pencil; `074` leaves the world blank white with no lines and shows form only where black paint splats land.
- `020` Manga screentone monochrome: this style uses soft graphite greys and scribbled shading; `020` is strict black and white with clean inked lines and dot screens.

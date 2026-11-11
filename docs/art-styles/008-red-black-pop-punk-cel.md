# Red-black pop-punk graphic cel

Reference works: Persona 5.

## References

- *Persona 5* (2016), Atlus (P-Studio), video game. https://en.wikipedia.org/wiki/Persona_5
- *Persona 5 Royal* (2019), Atlus (P-Studio), video game. https://en.wikipedia.org/wiki/Persona_5
- *Persona 5 Strikers* (2020), Omega Force and P-Studio, video game. https://en.wikipedia.org/wiki/Persona_5_Strikers
- *Persona 3 Reload* (2024), Atlus (P-Studio), video game. https://en.wikipedia.org/wiki/Persona_3_Reload

## Visual definition

- **Shape language and proportions:** Slim anime proportions. The environment is cut into jagged, slanted shapes: torn-paper edges, star bursts, diagonal bars and skewed type blocks.
- **Line and outline:** Black outline of medium weight (2 to 4 px) on characters and props; white keylines around black shapes.
- **Shading model:** Two bands. Shadow is solid black or deep red, covering large areas.
- **Palette:** `#e60012` `#0d0d0d` `#ffffff` `#f5d400` `#3a3a3a` `#8c000a`. Pure red, black and white with one small yellow accent. Most of the frame is red or black.
- **Lighting:** Graphic, not physical: a hard key from one side so half of each form drops to black.
- **Texture and surface:** Flat fills with halftone dot gradients in red areas and rough torn-paper edges.
- **Atmosphere and post-processing:** Hard contrast. Optional posterise. No haze.
- **Camera and framing:** Dutch angles of 10 to 20 degrees, low wide shots, tight crops.
- **UI and typography:** UI is a main part of the image: skewed black and red panels with torn or jagged edges, white keylines and star bursts, layered at clashing angles. Type mixes heavy condensed sans capitals with ransom-note cut-out letters of mixed size and tilt. Numbers are large slanted white digits on black with a red offset shadow.
- **VFX and motion:** Hits trigger full-screen graphic cuts: red and black splash panels, star bursts, radiating speed lines and halftone wipes. Motion is snappy, with strongly held key poses, fast smears between them and freeze frames on finishing blows.

## Fits

- **Genres:** `rpg`, `stealth`, `hack-and-slash`, `fighting`, `detective-mystery`
- **Moods:** stylish, rebellious, tense
- **Settings:** modern Tokyo, night city, surreal palace

## Unreal recipe

### Assets

Use slim anime-proportioned rigged characters and urban or interior packs with strong straight edges. Strip all textures from the environment and assign flat red, black or white per material slot; pick which by script from each surface's facing so neighbouring planes alternate. Build from scratch the graphic dressing: star-burst cut-outs, diagonal bars, skewed type blocks and wall panels with torn-paper edges (a jagged alpha generated from thresholded noise). Shear some architecture a few degrees by script.

### Materials

`M_PunkCel` is Unlit. A Material Parameter Collection supplies a key direction chosen by art direction, side-on. `Step` on N·L selects between the flat fill (`#e60012`, `#ffffff` or `#3a3a3a`) and the shadow colour, which is `#0d0d0d` or deep red `#8c000a`; bias the threshold to 0.15 so about half of each form drops out. Inside red fills, a halftone gradient: a screen-space dot grid (Frac of ScreenPosition times a dot count, distance to cell centre) compared against a vertical gradient, switching between `#e60012` and `#8c000a`. Dots appear in red areas only, never across the frame. Yellow `#f5d400` is a parameter used on one small item per scene.

### Lighting and atmosphere

No scene lighting. Lumen, shadows and fog off; no haze of any kind. The backdrop is a flat red or black dome with white star-burst meshes.

### Post-processing

Two materials at Scene Color After Tonemapping, with Tone Curve Amount 0 before them:

1. `PP_Line`: Sobel on CustomStencil and SceneDepth for a 2 to 4 px black line on characters and props (stencil-tagged components only).
2. `PP_Keyline`: where a stencil edge lies between two black pixels, draw a 2 px white line instead, so black forms stay readable on black.

Optional posterise to 4 levels per channel in the second pass. Bloom, grain, vignette, fringe, depth of field off; Motion Blur Amount 0. FXAA. Hold the camera at a fixed 10 to 15 degree roll; never animate it.

### UI and effects

UI carries much of the look. Panels are black and red Images with jagged alpha edges and a white keyline, sheared and rotated at clashing angles, layered three deep. Headings use Anton or Bebas Neue in capitals; ransom-note words are built from single-letter Text widgets with mixed fonts, sizes and tilts. Numbers are slanted white digits on black with a red shadow offset 4 px. Hits trigger a full-screen widget cut for 0.2 to 0.4 s: a red and black splash panel with a star burst, then a halftone wipe driven by a UI material. Niagara: radiating speed lines as flat white ribbons, star sprites, all Unlit and Masked, with a freeze frame on finishing blows.

## Do / Do not

Do:

- Keep nearly the whole frame in red, black or white.
- Tilt the camera and shear the geometry.
- Let shadows drop to solid black.
- Use white keylines to separate black from black.

Do not:

- Do not add more hues; that reads as `004`.
- Do not remove red and keep only black with one small colour spot; that reads as `069`.
- Do not use muted colours under heavy black; that reads as `010`.
- Do not apply halftone over the full frame with colour offsets; that reads as `009`.

## Nearest styles

- `069` Selective-colour ink noir: this style floods the frame with pure red next to black and white; `069` is black and white with only one small spot of colour.
- `010` Heavy-black gothic comic: this style is dominated by pure bright red, with halftone gradients and torn-paper edges; `010` uses muted slate, olive and ochre under heavier black, with perfectly flat colour.
- `080` Constructivist agit poster: this style is a dark frame of red and black with outlined characters; `080` sits on light yellowed paper with unoutlined flat shapes and thin ruled lines.

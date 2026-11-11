# Graffiti street cel

Reference works: Jet Set Radio.

## References

- *Jet Set Radio* (2000), Smilebit, video game. https://en.wikipedia.org/wiki/Jet_Set_Radio
- *Jet Set Radio Future* (2002), Smilebit, video game. https://en.wikipedia.org/wiki/Jet_Set_Radio_Future
- *Bomb Rush Cyberfunk* (2023), Team Reptile, video game. https://en.wikipedia.org/wiki/Bomb_Rush_Cyberfunk
- *Hi-Fi Rush* (2023), Tango Gameworks, video game. https://en.wikipedia.org/wiki/Hi-Fi_Rush

## Visual definition

- **Shape language and proportions:** Lanky characters with big shoes and hands; city blocks are simple boxes tilted into exaggerated perspective. Low polygon counts are visible.
- **Line and outline:** Uniform black outline, 3 to 4 px, on every silhouette. Few inner lines.
- **Shading model:** Two bands with a hard edge. The shadow band is a darker flat colour, not black.
- **Palette:** `#101014` `#ffd21f` `#ff3f8e` `#19c3ff` `#7dff3a` `#ff7a1a` `#f4f4f4`. Acid yellow, hot pink, cyan and lime against asphalt grey and white. Colours clash on purpose.
- **Lighting:** Flat daylight; shading mostly fixed to the model. Ground shadows are solid dark ovals.
- **Texture and surface:** Walls and vehicles carry large graffiti pieces: fat bubble letters, arrows, drips and stars with their own black outline and white highlight.
- **Atmosphere and post-processing:** None, or a slight colour boost. Hard aliased or lightly anti-aliased edges are acceptable.
- **Camera and framing:** Low, wide angle (24 to 28 mm equivalent) with tilted horizon for speed.
- **UI and typography:** UI looks like stickers and spray tags: slanted panels with a thick black outline and white keyline, filled with acid yellow, hot pink or cyan. Titles use fat bubble lettering and labels use a bold italic condensed sans. Score and combo numbers are large, tilted, outlined digits that jump in size when they change.
- **VFX and motion:** Spray puffs, drips, stars, arrows and speed streaks are flat outlined shapes in clashing palette colours. Hits flash a comic burst with a short freeze; animation is snappy and rhythmic, with exaggerated poses held on the beat.

## Fits

- **Genres:** `sports`, `platformer`, `racing`, `hack-and-slash`, `fighting`
- **Moods:** energetic, rebellious, playful
- **Settings:** city streets, skate park, rooftops, train yard

## Unreal recipe

### Assets

Low-poly city kits fit: box buildings, simple cars, rails and ramps, faceting left visible. For a realistic urban pack, reduce meshes to the lowest LOD and make that LOD 0, remove normal, roughness and metallic maps, and repaint base colour as flat fills in asphalt grey and white with palette accents. Shear or taper tall buildings by script for the tilted perspective. Graffiti is built from scratch: a script renders fat bubble letters, arrows, drips and stars with a black outline and white highlight into 1024 px atlases with alpha.

### Materials

`M_StreetCel` is Unlit with the shadow fixed to the model: a two-step value from `Step` on N·L against a constant light vector stored in a Material Parameter Collection. The shadow band multiplies the base by a flat 0.6 tint, never black. Graffiti pieces are DBuffer decals, or a second UV-channel layer in the master, placed so every view has one large piece. The outline uses the inverted hull: a Masked, two-sided Unlit material in `#101014` that shows back faces only through TwoSidedSign, with World Position Offset along the vertex normal scaled by distance to camera so the width stays 3 to 4 px on screen. Assign it as each mesh component's Overlay Material. Ground shadows are dark oval decals.

### Lighting and atmosphere

Disable Lumen GI and reflections, shadows and fog. Sky is a flat cyan (`#19c3ff`) dome or a two-colour gradient. Exposure is Manual.

### Post-processing

Tone Curve Amount 0 so the acid hues are not desaturated by the filmic curve; Global Saturation 1.1. Bloom, grain, vignette, fringe, ambient occlusion and depth of field all off, Motion Blur Amount 0. There is no post-process line pass: the hull outline already gives an even silhouette line with few inner lines. Anti-aliasing is FXAA or none (`r.AntiAliasingMethod=1` or `0`). A small fixed camera roll gives the tilt without shake.

### UI and effects

Panels are slanted (Render Transform shear) Border widgets: fill in `#ffd21f`, `#ff3f8e` or `#19c3ff`, a thick black outline and a white keyline. Titles use Bangers or Permanent Marker; labels use Barlow Condensed Bold Italic. Score digits are tilted with a black font outline and play a 0.15 s scale punch on change. Niagara: Masked sprite shapes with a black edge baked into the texture, such as spray puffs, drips, stars and arrows, in two clashing hues per burst; hits spawn a comic burst sprite held for 0.1 s with a short hit-stop.

## Do / Do not

Do:

- Keep outline width constant in screen space.
- Cover at least one large surface with a graffiti piece.
- Use clashing saturated hues side by side.
- Tilt the camera and use a wide lens.

Do not:

- Do not add hatching or line-weight variation; that reads as `001`.
- Do not restrict the palette to red, black and white; that reads as `008`.
- Do not add rim highlights and gradient shadow tints; that reads as `015`.
- Do not use glossy PBR paint; that reads as `006`.

## Nearest styles

- `001` Ink-outline comic cel: this style has an even line, two tone steps and clean surfaces apart from graffiti; `001` has a wobbly line of changing width, three tone steps, hatching and inked wear marks.
- `015` Two-tone fighting-anime cel: this style clashes loud hues, covers walls with graffiti and shows its low polygon count; `015` keeps surfaces clean, tapers its line and adds tinted shadows and hard highlight shapes.
- `008` Red-black pop-punk graphic cel: this style uses many clashing bright hues in flat daylight; `008` keeps nearly the whole frame red, black and white and drops shadows to solid black.

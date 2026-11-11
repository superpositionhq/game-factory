# Stained glass

Reference works: Chartres Cathedral; Sainte-Chapelle.

## References

- *Stained glass windows of Chartres Cathedral* (c. 1205-1240), Chartres workshops, stained glass. https://en.wikipedia.org/wiki/Chartres_Cathedral
- *Sainte-Chapelle windows* (1248), Parisian workshops, stained glass. https://en.wikipedia.org/wiki/Sainte-Chapelle
- *Tiffany lamp* (1895), Tiffany Studios (Louis Comfort Tiffany and Clara Driscoll), leaded glass lamps. https://en.wikipedia.org/wiki/Tiffany_lamp
- *Beauty and the Beast (prologue windows)* (1991), Walt Disney Feature Animation, animated film. https://en.wikipedia.org/wiki/Beauty_and_the_Beast_(1991_film)

## Visual definition

- **Shape language and proportions:** Images are divided into cells of coloured glass, each a simple convex or gently curved piece. Figures are stiff and frontal, with forms simplified to fit the cell layout. In 3D, objects are faceted shells of glass panes.
- **Line and outline:** Thick black lead lines (came) between all pieces, of even width, plus thicker iron bars across large windows.
- **Shading model:** None from scene lighting. Each pane is a single glowing colour with internal variation; fine detail is painted in dark enamel.
- **Palette:** `#0d0d10` `#1e3fae` `#c21f2b` `#e8b21a` `#1f8a4c` `#7a2fa0` `#f2e6c2`. Deep ruby red and cobalt blue dominate, with gold, green and violet; all seen against black.
- **Lighting:** Back-lit: the glass is the light source. The surroundings are dark, with coloured light patches cast on nearby surfaces.
- **Texture and surface:** Glass streaks, bubbles and ripples inside each pane; dark painted trace lines for faces and folds.
- **Atmosphere and post-processing:** Glow around bright panes; dark vignette.
- **Camera and framing:** Frontal for windows; for 3D objects, any angle with a dark background.
- **UI and typography:** Panels are leaded window frames: black lead borders around panes of ruby, cobalt and gold glass, with icons set in small roundels. Type is a heavy gothic blackletter or uncial capital, painted in dark enamel on a pale pane or cut as glowing gold glass. Numbers glow gold against black.
- **VFX and motion:** Hits shatter panes into coloured shards with a flash of white light. Effects are shafts of coloured light, glowing dust motes and light patches that sweep across dark floors. Figures move stiffly from pose to pose, like panes sliding inside their lead lines, and the glow pulses slowly.

## Fits

- **Genres:** `puzzle`, `action-adventure`, `platformer`, `rpg`, `exploration`, `soulslike`
- **Moods:** solemn, mystical, radiant
- **Settings:** gothic cathedral, medieval kingdom, enchanted castle

## Unreal recipe

### Assets

Model objects as faceted shells of panes. A Blender background script takes a simple store mesh, decimates it to large convex facets, insets each face to leave a gap, and fills the gaps with a raised strip of lead of even width; large windows also get straight iron bars. Flat windows are built from a 2D cell layout (Voronoi or hand-defined regions) the same way. Each pane gets a vertex colour for its glass colour. Surrounding architecture is plain dark stone from any gothic pack with albedo darkened to near `#0d0d10`.

### Materials

`M_Glass`: Unlit. Pane colour from VertexColor or a parameter (ruby `#c21f2b` and cobalt `#1e3fae` dominant, then gold `#e8b21a`, green `#1f8a4c`, violet `#7a2fa0`) multiplied by a streak-and-bubble texture and slow Noise for internal variation, then by a `Glow` scalar of 2 to 6 so panes exceed the bloom threshold. A dark enamel trace-line texture multiplies over it for faces and folds. `M_Lead`: Unlit black `#0d0d10`. Because both are Unlit, scene lights never shade the glass; it is the light source. A light-function material derived from the same window texture projects colour onto floors.

### Lighting and atmosphere

Lumen GI on so emissive panes tint nearby stone. Behind each window, a Spot or Rect Light with the window Light Function throws coloured patches on the floor; Volumetric Fog on with low density so shafts of coloured light show. No Sky Light, or one at very low intensity. No Directional Light on the glass side. Manual exposure, set for the panes, leaving the surround nearly black.

### Post-processing

Bloom Method Standard, Intensity 0.8 to 1.0, Threshold about 1 so only panes glow. Vignette 0.7. Tone curve default; Expand Gamut left on to keep ruby and cobalt deep. TSR on. Grain, fringe, depth of field and Motion Blur Amount 0. No outline post material: the lead is real geometry of fixed width, not a screen-space line.

### UI and effects

Panels are leaded frames: black 9-slice borders around translucent ruby, cobalt and gold pane fills, icons set in small roundels. Text in UnifrakturCook or Pirata One, dark enamel on a pale pane `#f2e6c2` or glowing gold on black. Numbers glow `#e8b21a`. Niagara: a hit shatters panes into flat triangular shards (mesh renderer, Unlit emissive in the pane's colour, 15 to 30, lifetime 1 s) with a one-frame white flash; ambient dust motes drift in the shafts (additive sprites, 40 to 80, lifetime 5 s). Pane glow pulses slowly through a shared parameter. Characters animate pose to pose with holds.

## Do / Do not

Do:

- Separate every colour area with a black lead line.
- Make panes self-lit against a dark surround.
- Use deep red and blue as the main colours.
- Add streak and bubble variation inside panes.

Do not:

- Do not use small square pieces with light grout and surface shading; that reads as `055`.
- Do not use opaque flat fills with black bars on white; that reads as `079`.
- Do not use thin curving outlines with pastel fills; that reads as `083`.
- Do not light the glass from the front.

## Nearest styles

- `079` Primary grid neoplasticism: this style glows in deep ruby and cobalt against a black surround; `079` is mostly white, with a few flat opaque blocks of red, blue and yellow between straight black bars.
- `055` Mosaic tessera: here large panes of one glowing colour are each fully enclosed by thick black lead and lit from behind; `055` is thousands of tiny tiles with thin grout, lit from the front, with tones stepped across each form.
- `086` Insular illuminated manuscript: this style uses large plain panes of glowing colour; `086` packs a painted vellum page with fine knotwork and interlace, with no backlight.

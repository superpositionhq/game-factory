# Blue-and-white glazed porcelain

Reference works: Jingdezhen porcelain; Delftware.

## References

- *The David Vases* (1351), Jingdezhen kilns, Yuan dynasty, blue-and-white porcelain. https://en.wikipedia.org/wiki/David_Vases
- *Delftware* (17th century), Delft potteries, tin-glazed earthenware tradition. https://en.wikipedia.org/wiki/Delftware
- *Willow pattern* (c. 1790), English potteries (attributed to Thomas Minton), transfer-printed ceramic design. https://en.wikipedia.org/wiki/Willow_pattern

## Visual definition

- **Shape language and proportions:** Wheel-thrown forms: vases, jars, bowls, plates, tiles and figurines with smooth continuous curves and thickened rims and feet. Whole scenes are made of the same glazed ceramic.
- **Line and outline:** No outline on the forms. The decoration contains painted cobalt contour lines.
- **Shading model:** Smooth, glossy glaze with sharp specular highlights and soft reflections.
- **Palette:** `#fbfcfa` `#1a3a8a` `#2f5fc4` `#8fa9dc` `#dfe6ee` `#0f2460`. White glaze and cobalt blue only, the blue ranging from pale wash to nearly black-blue.
- **Lighting:** Soft museum or daylight setting with clear window-like reflections.
- **Texture and surface:** Hand-painted cobalt decoration: scrolling vines, lotus and peony, wave and lappet borders, cloud bands, landscapes in panels. Brush washes with uneven density; faint glaze pooling and pinholes.
- **Atmosphere and post-processing:** None, or slight depth of field.
- **Camera and framing:** Product-style three-quarter view, 50 to 85 mm equivalent.
- **UI and typography:** Panels are white glazed plaques or tiles framed with cobalt wave, lappet or scroll borders, and icons are small brush-painted motifs in round medallions. Type is brush-painted lettering with thick and thin strokes, in dark cobalt on white. Numbers are brush-drawn numerals, with pale blue wash for inactive states.
- **VFX and motion:** Hits craze the glaze with fine dark cracks and break objects into curved white shards, each with a piece of blue painting on it. Particles are cobalt ink blooms, brush-stroke swirls and painted clouds that spread like wash on glaze. Bodies are rigid ceramic that glides, spins and rocks, never bends.

## Fits

- **Genres:** `puzzle`, `exploration`, `strategy`, `platformer`
- **Moods:** serene, delicate, contemplative
- **Settings:** imperial China, Dutch canal town, tea house, willow garden

## Unreal recipe

### Assets

Build the forms: vases, jars, bowls, plates and figurines are lathe profiles spun in Blender background mode, with thick rounded rims and feet, and UVs unwrapped as bands around the axis so borders run horizontally. Buildings, trees and characters are treated as figurines of the same ceramic: take simple store meshes, smooth and round every edge as if dipped in glaze, and discard their textures entirely. Paint decoration by script into band-layout textures: a lappet border at the foot, a wave border at the rim, scrolling vine or a landscape panel between.

### Materials

`M_Porcelain`: Clear Coat shading model. Base Color is white `#fbfcfa` lerped to cobalt by a single-channel decoration mask; the mask value picks a blue along a CurveAtlasRowParameter ramp from pale wash `#8fa9dc` through `#2f5fc4` and `#1a3a8a` to `#0f2460`, so brush density becomes tone. Multiply the mask by a low-frequency Noise for uneven wash. Base Roughness 0.3, Clear Coat 1.0, Clear Coat Roughness 0.05. A faint normal map adds glaze pooling and pinholes. A `Craze` parameter reveals a fine dark crack texture after hits. No third hue exists anywhere in the material.

### Lighting and atmosphere

Lumen GI and reflections on, hardware ray tracing if available for clean reflections. Soft daylight: a Sky Light with a neutral studio cubemap, plus two or three Rect Lights placed to appear as window-shaped highlights on the glaze. Soft Virtual Shadow Maps. No fog. The backdrop is pale `#dfe6ee`. Manual exposure set so white glaze sits just below clipping.

### Post-processing

Nearly none. TSR on. Depth of Field optional at f/5.6 on a 50 to 85 mm camera. Bloom 0.15 for highlight glints only. Grain, vignette, fringe and Motion Blur Amount 0. Colour grading: Saturation 1.0, White Balance neutral to slightly cool; check that no warm cast tints the white. No post materials.

### UI and effects

Panels are white glazed plaques: Rounded Box brushes with a cobalt wave, lappet or scroll 9-slice border. Icons are brush-painted motifs in round medallions. Lettering in a brush face such as Zen Antique or Amiri, dark cobalt `#0f2460` on white; inactive states use pale wash `#8fa9dc`. Numerals are brush-drawn. Niagara: cobalt ink blooms as sprites that expand and fade like wash over 1.5 s on a translucent material; painted cloud and swirl flipbooks. Breakage uses pre-fractured shards (Geometry Collection or swapped mesh pieces), each curved, white, keeping its part of the blue painting; they slide and ring to rest. Bodies move rigidly: glide, spin, rock.

## Do / Do not

Do:

- Use only white and cobalt blue.
- Organise decoration in horizontal bands with borders.
- Make the glaze glossy with clear reflections.
- Round every edge as if glazed.

Do not:

- Do not add other colours or gold; that reads as `100` or `055`.
- Do not use matte, unglazed surfaces.
- Do not use geometric star tiling; that reads as `100`.
- Do not leave the white undecorated; that reads as `091`.

## Nearest styles

- `100` Islamic geometric tile: this style has only cobalt on white, with freely brushed vines, flowers and landscapes on curved vessels; `100` uses several glaze colours in strict repeating star-and-polygon tiling that covers flat walls.
- `091` Clinical white space-age: white surfaces here are covered in painted cobalt decoration; `091` leaves its white surfaces plain and undecorated.
- `055` Mosaic tessera: this style is one continuous glossy glaze in blue and white; `055` is thousands of small tiles in many colours with dark grout between them.

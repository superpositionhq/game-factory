# Mosaic tessera

Reference works: Basilica of San Vitale, Ravenna.

## References

- *Mosaics of the Basilica of San Vitale* (547), Byzantine workshops, Ravenna, glass and stone mosaic. https://en.wikipedia.org/wiki/Basilica_of_San_Vitale
- *Alexander Mosaic* (c. 100 BC), Roman workshop, House of the Faun, Pompeii, floor mosaic. https://en.wikipedia.org/wiki/Alexander_Mosaic
- *Mosaics of the Mausoleum of Galla Placidia* (c. 425-450), Late Roman workshops, Ravenna, glass mosaic. https://en.wikipedia.org/wiki/Mausoleum_of_Galla_Placidia
- *Park Guell trencadis* (1914), Antoni Gaudi and Josep Maria Jujol, broken-tile mosaic. https://en.wikipedia.org/wiki/Park_Güell

## Visual definition

- **Shape language and proportions:** Images and surfaces are built from thousands of small tiles (tesserae), roughly square, 5 to 15 mm, laid in rows that follow the contours of each shape. Figures are frontal and stylised with large eyes.
- **Line and outline:** Dark grout fills the gaps between tiles; darker tile rows trace the contours of figures.
- **Shading model:** Tone is stepped: each form uses three to five tile colours from light to dark, placed in rows. Individual tiles catch light at slightly different angles.
- **Palette:** `#c9a227` `#1f3f7a` `#2f7a5a` `#9a2f2a` `#e8dcc0` `#3a3a3a` `#d98a5a` `#f5f1e6`. Gold backgrounds with deep blue, green, red, flesh tones and white.
- **Lighting:** Raking light so tile tilt and gold sparkle are visible.
- **Texture and surface:** The tile grid itself: irregular small pieces, uneven gaps, varied tilt and gloss.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** Frontal for wall panels; any angle for mosaic-covered 3D objects.
- **UI and typography:** Panels are mosaic bands: gold tile fields edged with rows of dark and white tesserae, with icons as small tile pictures in round or square medallions. Type is a square Roman or Byzantine capital laid in dark tiles on gold. Numbers are tile-built numerals in white or deep blue.
- **VFX and motion:** Effects are made of tiles: hits knock tesserae loose and scatter them, colour changes ripple across a surface tile by tile, and gold tiles glint in sequence as the light moves. Figures hold stiff frontal poses and change position by re-laying rows of tiles, not by bending smoothly.

## Fits

- **Genres:** `puzzle`, `strategy`, `rpg`, `tower-defense`, `exploration`
- **Moods:** solemn, ancient, ornate
- **Settings:** Byzantine basilica, Roman villa, Mediterranean port, tiled garden park

## Unreal recipe

### Assets

The tile layout is the asset. For wall and floor pictures, a script (Pillow or Blender) takes a flat-colour drawing, lays rows of roughly square tesserae that follow each shape's contour, and writes three textures: a tile ID map, a flat colour-per-tile albedo snapped to three to five tones per form, and a normal map in which every tile has a slightly different tilt with recessed grout. For 3D objects, bake the same maps over simple, stylised store meshes at 5 to 15 mm tile scale. Figures are frontal with large eyes; strip all original textures.

### Materials

`M_Mosaic`: Default Lit. Base Color from the per-tile albedo, with grout pixels `#3a3a3a`. Roughness from a per-tile random value (hash of tile ID) between 0.2 and 0.5, grout 0.9. Gold tiles (`#c9a227`) are selected by a mask and set to Metallic 1 with Roughness 0.15 to 0.3, so they sparkle one by one as the light moves. The tilt normal map is essential; without it the surface reads as a flat print. A `Loose` parameter per region, driven from C++, hides tiles by ID for damage, and a wipe parameter changes colour tile by tile. Colour never varies inside one tile.

### Lighting and atmosphere

Lumen GI and reflections on. One Directional or Spot Light at a raking angle of 15 to 25 degrees to the wall so tilt and gold glint show; move it slowly for sequenced sparkle. A warm low Sky Light. Virtual Shadow Maps; Contact Shadows on for grout depth. No fog. Manual exposure.

### Post-processing

None beyond defaults. TSR on with `r.Tonemapper.Sharpen` near 0.5 to hold tile edges. Bloom 0.2 with a high threshold so only gold glints bloom. Grain, vignette, fringe, depth of field and Motion Blur Amount 0. No post materials; a screen-space tile filter would not follow contours and must not replace the baked layout.

### UI and effects

Panels are mosaic bands: gold tile fields with rows of dark and white tesserae as a 9-slice border; icons are small tile pictures in medallions. Text in Cinzel, pre-rendered through the tile script for headings so capitals appear laid in dark tiles on gold; body text plain Cinzel in `#3a3a3a`. Numerals are white `#f5f1e6` or deep blue `#1f3f7a` tile digits. Niagara: mesh-renderer tesserae (small bevelled squares, the struck surface's colours, 20 to 40, lifetime 1.2 s, bouncing) knocked loose on hits. Characters change pose by a tile-by-tile wipe between held frontal poses instead of smooth bending.

## Do / Do not

Do:

- Lay tiles in rows that follow contours.
- Give each tile one colour and a slightly different tilt.
- Use gold metallic tiles for backgrounds.
- Light at a raking angle.

Do not:

- Do not use a perfectly regular geometric star pattern in glazed tile; that reads as `100`.
- Do not use large panes with black lines and backlight; that reads as `054`.
- Do not use round paint dots without grout; that reads as `077`.
- Do not let colours vary inside one tile.

## Nearest styles

- `100` Islamic geometric tile: here small irregular tiles follow the contours of figures, with tone stepped from light to dark and many colours on gold; `100` is smooth glazed tile in a few colours, cut to a perfectly regular star pattern with no figures.
- `077` Pointillist dot field: dark grout separates every tile here and tone steps in rows; `077` is round paint dots that touch with no dark gaps and blend into soft colour at a distance.
- `054` Stained glass: the surface here is a dense field of tiny tiles lit from the front; `054` is large smooth panes held in thick black lead and lit from behind.

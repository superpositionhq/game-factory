# Islamic geometric tile

Reference works: Alhambra; Engare.

## References

- *Alhambra* (13th-14th century), Nasrid dynasty builders, palace architecture with zellij tilework. https://en.wikipedia.org/wiki/Alhambra
- *Shah Mosque, Isfahan* (1629), Safavid builders (Ali Akbar Isfahani), architecture with tile mosaic. https://en.wikipedia.org/wiki/Shah_Mosque_(Isfahan)
- *Engare* (2017), Mahdi Bahrami, video game. https://en.wikipedia.org/wiki/Engare
- *Bou Inania Madrasa, Fez* (1355), Marinid builders, architecture with zellij tilework. https://en.wikipedia.org/wiki/Bou_Inania_Madrasa

## Visual definition

- **Shape language and proportions:** Architecture organised around pattern: pointed and horseshoe arches, domes, courtyards, niches and honeycomb vaulting (muqarnas). All large surfaces carry geometric tiling based on stars and polygons generated from circle divisions (6-, 8-, 10- and 12-fold).
- **Line and outline:** Narrow pale grout lines between tile pieces and interlacing white strapwork bands that weave over and under through the pattern.
- **Shading model:** Smooth; glazed tiles are glossy with soft highlights, plaster is matte.
- **Palette:** `#1f5fa8` `#2f9e8f` `#f2efe6` `#d9a441` `#1a1a1a` `#b3472e` `#6fc3d0`. Cobalt blue, turquoise, white, ochre-gold and black, with terracotta accents.
- **Lighting:** Strong sun and deep shade in courtyards; light filtered through pierced screens casts patterned shadows.
- **Texture and surface:** Dense, exact, repeating star-and-polygon tessellation across walls, floors and domes; carved stucco arabesque bands; pierced lattice screens.
- **Atmosphere and post-processing:** None; crisp detail.
- **Camera and framing:** Symmetric frontal views of portals and courtyards; close views of tile panels.
- **UI and typography:** Panels framed by pointed-arch outlines and tile borders, with eight-point star medallions as buttons and interlaced strapwork as dividers; icons are geometric rosettes. Titles use angular, square-built calligraphic lettering and body text a clean humanist sans, in white `#f2efe6` or gold `#d9a441` on cobalt `#1f5fa8`. Counters are gold numerals inside star medallions.
- **VFX and motion:** Patterns draw themselves line by line, tiles flip, rotate and lock into place, and star-shaped glints cross the glaze; hits scatter small glazed shards and send out an expanding ring of pattern. Motion is exact and rhythmic: steady rotations, symmetric unfolding and smooth eased slides.

## Fits

- **Genres:** `puzzle`, `exploration`, `action-adventure`, `platformer`, `strategy`
- **Moods:** contemplative, serene, ornate
- **Settings:** Moorish palace, Persian mosque courtyard, desert madrasa, walled garden

## Unreal recipe

### Assets

Architecture comes from Moorish or Persian kits where available: pointed and horseshoe arches, domes, courtyards, niches. Replace their wall, floor and dome textures with generated tiling. Write a script that constructs star-and-polygon patterns from circle divisions (6-, 8-, 10- and 12-fold), then exports for each pattern a colour-ID map, a grout mask, a strapwork mask with over-under breaks, and a normal map with slightly raised tile faces. Build muqarnas vault cells and pierced lattice screens as real geometry in Blender so the screens cast patterned shadows.

### Materials

Default Lit master `M_Zellij`. The colour-ID map selects glaze colours from parameters: cobalt `#1f5fa8`, turquoise `#2f9e8f`, light blue `#6fc3d0`, ochre `#d9a441`, black `#1a1a1a`, terracotta `#b3472e`. Glazed tile: Roughness 0.12 to 0.2 with a small per-tile random offset in roughness and normal tilt, so highlights break across pieces. Grout and strapwork: `#f2efe6`, Roughness 0.85, slightly recessed (grout) or raised (strapwork) in the normal map. Lines stay narrow and pale; no dark outline exists anywhere. Carved stucco bands use a separate matte plaster instance with an arabesque height-derived normal.

### Lighting and atmosphere

Strong sun: Directional Light at high intensity, Source Angle 0.5, giving deep shade in courtyards and crisp lattice shadow patterns on floors. Virtual Shadow Maps on, with contact shadows for the fine screens. Lumen global illumination and reflections on so shaded arcades fill with warm bounce and glaze reflects the sky. Sky Atmosphere and Sky Light with Real Time Capture; clear sky. No height fog and no volumetrics. Auto exposure with a moderate range to handle courtyard-to-arcade changes; Local Exposure helps hold detail in both.

### Post-processing

Keep the image crisp and clean. Filmic tone curve at defaults; Global Saturation 1.05. Bloom Intensity 0.15. Film Grain Intensity 0, Vignette Intensity 0, Scene Fringe Intensity 0, Motion Blur Amount 0, depth of field off. `r.Tonemapper.Sharpen` at 0.5 helps fine grout lines. TSR anti-aliasing at full `r.ScreenPercentage`, since dense pattern shimmers when upscaled.

### UI and effects

UMG panels are cobalt `#1f5fa8` fills inside a pointed-arch frame image with a tiled border strip; buttons are eight-point star medallions; dividers are interlaced strapwork strips. Titles use a square Kufic-style display face such as Reem Kufi; body text uses Noto Sans, in `#f2efe6` or `#d9a441`. Counters are gold numerals centred in star medallions.

Niagara: glazed shards as small lit mesh particles (star and kite pieces) scattered on hits, 12 to 20, with gravity, 0.8 s; star-shaped glints crossing tiles, 0.25 s. The expanding pattern ring is a decal or mesh whose material reveals the tiling through a radial Step driven by time.

## Do / Do not

Do:

- Construct star-and-polygon patterns from circle divisions.
- Weave white strapwork over and under.
- Use cobalt, turquoise, white, ochre and black glazes.
- Cover large architectural surfaces completely.

Do not:

- Do not use irregular hand-set squares that follow figure contours; that reads as `055`.
- Do not paint free brush decoration in blue on white vessels; that reads as `053`.
- Do not use interlaced animals and figures on vellum with dark outlines; that reads as `086`.
- Do not leave tile surfaces matte and unlit.

## Nearest styles

- `055` Mosaic tessera: tiles here are exact star and polygon pieces in a few glaze colours with glossy highlights; `055` is small irregular hand-set squares in many colours that follow the contours of figures.
- `053` Blue-and-white glazed porcelain: this style covers architecture edge to edge in dense geometric pattern with several glaze colours; `053` is free blue brush painting on white vessels, with open white areas.
- `086` Insular illuminated manuscript: lines here are only narrow pale grout and white strapwork over glossy glaze; `086` puts a dark outline around every flat-coloured shape on vellum.

# Isometric pastel impossible architecture

Reference works: Monument Valley.

## References

- *Monument Valley* (2014), Ustwo Games, video game. https://en.wikipedia.org/wiki/Monument_Valley_(video_game)
- *Monument Valley 2* (2017), Ustwo Games, video game. https://en.wikipedia.org/wiki/Monument_Valley_2
- *Relativity* (1953), M. C. Escher, lithograph. https://en.wikipedia.org/wiki/Relativity_(M._C._Escher)
- *Waterfall* (1961), M. C. Escher, lithograph. https://en.wikipedia.org/wiki/Waterfall_(M._C._Escher)
- *Echochrome* (2008), Japan Studio, video game. https://en.wikipedia.org/wiki/Echochrome

## Visual definition

- **Shape language and proportions:** Small architectural monuments made of cubes, stairs, arches, domes and towers on a strict grid, floating in empty space. Structures form impossible loops that only connect from the fixed view.
- **Line and outline:** No outline.
- **Shading model:** Exactly three tones per colour: top faces lightest, left faces mid, right faces darkest. No gradients on faces, no cast shadows.
- **Palette:** `#f6c6b4` `#e58f8a` `#7fc7c2` `#3d7f8f` `#f7efd9` `#b89ad6` `#2f3e56`. Soft pastels with one deeper contrast colour; each level uses three or four hues.
- **Lighting:** Implied fixed light; tones are assigned by face direction, not computed with falloff.
- **Texture and surface:** None. Faces are flat colour; small details are simple geometric cut-outs (windows, doors, crenellations).
- **Atmosphere and post-processing:** Smooth gradient background; optional soft glow on a few elements.
- **Camera and framing:** Isometric orthographic view, fixed.
- **UI and typography:** UI is minimal: thin geometric line icons and small flat buttons in the level's pastel hues, with no frames or panels. Type is a light, widely spaced geometric sans in cream or the dark contrast colour. Numbers are small and thin, with Roman numerals for chapter titles.
- **VFX and motion:** Effects are few: slow drifting motes, a soft glow on switches and a thin ring that expands from a touched point. Motion is calm and mechanical: pieces of architecture rotate, slide and unfold with smooth eased moves, and the figure walks in small even steps.

## Fits

- **Genres:** `puzzle`, `exploration`, `platformer`, `tower-defense`
- **Moods:** serene, dreamlike, contemplative
- **Settings:** floating temples, impossible palace, sky ruins

## Unreal recipe

### Assets

Build every monument by script on a strict unit grid: cubes, stair runs, arches, domes, towers and crenellations assembled in Geometry Script or Blender background mode, with windows and doors as simple boolean cut-outs. Realistic packs are unsuitable. Each level is one small structure floating in empty space, designed so separate parts line up into impossible loops from the fixed isometric view; gameplay connectivity for those joins is defined in C++, not by geometry. The walking figure is a tiny simple character with a rigid cone body.

### Materials

`M_IsoFace`: Unlit. A Custom node reads VertexNormalWS and returns one of three colours: `TopColour` when the normal is up, `LeftColour` for one horizontal axis, `RightColour` for the other (curved domes quantise to the nearest of the three). The three are vector parameters per material instance, for example `#f7efd9`, `#f6c6b4`, `#e58f8a` for one hue and `#7fc7c2`, `#3d7f8f`, `#2f3e56` for another; each level uses three or four hue sets. No textures, no gradients on a face, no light term. Glow accents use an emissive instance above 1. Because tone is assigned by face direction, not computed, it never shows the per-facet variation of lit low-poly styles.

### Lighting and atmosphere

No lights, Lumen off, no shadows of any kind, no fog actor. The background is a large Unlit plane or sky dome with a smooth vertical two-colour gradient in the level's hues. Manual exposure.

### Post-processing

Orthographic camera at true isometric angles (yaw 45, pitch about -35.26 degrees), fixed. Tone Curve Amount 0 and Expand Gamut 0 so the pastels match their hex values. `r.AntiAliasingMethod=4` (TSR) or FXAA for clean diagonal edges. Bloom 0.2 with Threshold 1 so only emissive accents glow softly. Grain, vignette, fringe, depth of field, Ambient Occlusion and Motion Blur Amount 0. No post materials.

### UI and effects

UI has no frames or panels: thin geometric line icons (1.5 to 2 px strokes) and small flat buttons in the level's pastels. Type in Josefin Sans Light or Jost Light with wide letter spacing, cream `#f7efd9` or dark `#2f3e56`; chapter titles use Roman numerals; numbers are small and thin. Niagara stays sparse: 10 to 20 slow Unlit motes drifting (lifetime 6 to 8 s), a soft pulse on switches, and a thin ring mesh that expands from a touched point over 0.6 s and fades. Architecture rotates, slides and unfolds on eased curves of 0.8 to 1.5 s; the figure walks in small even steps.

## Do / Do not

Do:

- Use a true isometric orthographic camera.
- Assign exactly three tones by face direction.
- Build on a strict unit grid.
- Float the structure in an empty gradient background.

Do not:

- Do not use perspective or cast shadows.
- Do not use irregular triangulated facets and landscapes; that reads as `066`.
- Do not use pure primaries on white; that reads as `098`.
- Do not add long shadows on an empty plaza; that reads as `084`.

## Nearest styles

- `066` Faceted low-poly gradient: here each colour has just three flat tones set by face direction, on strict cubes and stairs; `066` has irregular triangle facets that each take a different shade, more colours and natural landscapes.
- `098` Bauhaus primary geometry: colours here are soft pastels on a gradient background; `098` uses pure red, yellow and blue on white.
- `084` Metaphysical long-shadow plaza: this style has no cast shadows and plain flat pastel faces; `084` throws long dark shadows across an empty plaza and uses deeper, painted colour.

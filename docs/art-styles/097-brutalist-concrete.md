# Brutalist concrete

Reference works: Control; Barbican Estate.

## References

- *Control* (2019), Remedy Entertainment, video game. https://en.wikipedia.org/wiki/Control_(video_game)
- *Barbican Estate* (1976), Chamberlin, Powell and Bon, architecture. https://en.wikipedia.org/wiki/Barbican_Estate
- *Unite d'Habitation* (1952), Le Corbusier, architecture. https://en.wikipedia.org/wiki/Unité_d'habitation
- *Boston City Hall* (1968), Kallmann McKinnell and Knowles, architecture. https://en.wikipedia.org/wiki/Boston_City_Hall
- *Habitat 67* (1967), Moshe Safdie, architecture. https://en.wikipedia.org/wiki/Habitat_67

## Visual definition

- **Shape language and proportions:** Massive raw-concrete volumes: deep cantilevers, heavy overhanging upper floors, thick columns (pilotis), repetitive deep-set window grids, bush-hammered ribbed walls, monumental stairs and voids. Simple geometry at very large scale.
- **Line and outline:** No outline.
- **Shading model:** Smooth, matte, soft-shadowed. Form reads through large planes of light and shade.
- **Palette:** `#8c8a84` `#6b6964` `#a9a69f` `#4a4946` `#c4c1b8` `#2e2d2b`. Concrete grey from pale to charcoal; almost no colour. Optional single muted accent (a rust door, a red carpet).
- **Lighting:** Overcast daylight or shafts from high slot windows and skylights; long gradients on big walls.
- **Texture and surface:** Board-marked concrete (imprint of timber formwork planks), tie-rod holes in a regular grid, pour lines, rain streaks, ribbed bush-hammered surfaces.
- **Atmosphere and post-processing:** Subtle ambient occlusion and slight haze in large interiors.
- **Camera and framing:** Wide, low, looking up at overhanging masses, or symmetric views of atria.
- **UI and typography:** Plain flat panels in concrete grey with square corners and no ornament, set on a strict grid; icons are bold wayfinding pictograms. Type is a heavy grotesque sans in large capitals, like lettering cast into a building wall, in pale `#c4c1b8` or charcoal `#2e2d2b`. Counters are big plain numerals, with one muted rust or red accent for alerts.
- **VFX and motion:** Concrete dust, falling chips and grey debris chunks; hits knock out puffs of powder and leave pale chipped marks. Motion is heavy, with dust drifting slowly through light shafts and large masses that move with inertia.

## Fits

- **Genres:** `third-person-shooter`, `stealth`, `puzzle`, `exploration`, `fps`
- **Moods:** austere, imposing, uncanny
- **Settings:** government bureau, housing estate, civic megastructure, underground bunker

## Unreal recipe

### Assets

Large simple masses are quick to build by Geometry Script: cantilevered slabs, overhanging upper floors on thick pilotis, deep-set window grids, monumental stairs, atrium voids. Work at very large scale, with the player small against 20 to 60 m walls. Brutalist or bunker store kits fit when undamaged; remove rubble piles, cracks, graffiti, rebar and broken edges, and replace their concrete with the master below so every wall matches.

### Materials

Default Lit master `M_BoardConcrete`, sampled through WorldAlignedTexture so plank marks keep a constant real-world size across huge surfaces. Layers: board-marked normal and albedo (planks about 15 cm wide, direction parameter for vertical or horizontal formwork); a tie-rod hole pattern on a regular 60 cm grid from a tiling mask; horizontal pour lines every 1.2 m as a faint value step; rain streaks under ledges from a vertical-streak mask gated by a baked occlusion map. Base Colour from `#8c8a84` (mid) with `#a9a69f` and `#6b6964` variants, Roughness 0.85 to 0.95, Metallic 0. A second instance uses a ribbed bush-hammered normal. The single accent, rust or red, is one flat matte instance used on one object type per level.

### Lighting and atmosphere

Lumen global illumination on with high Final Gather Quality; long soft gradients across big walls depend on bounce. Overcast setup: Sky Light with Real Time Capture, Sky Atmosphere plus Volumetric Cloud at full cover, and a weak Directional Light with a large Source Angle (5 to 8 degrees) for soft shadows. Interiors: light enters only through high slots and skylights; Exponential Height Fog with Volumetric Fog at low density shows shafts in big rooms. Virtual Shadow Maps on. Auto exposure with a moderate range, biased so concrete sits at mid-grey, not white.

### Post-processing

Ambient Occlusion Intensity 0.6 with a wide Radius to seat masses. Global Saturation 0.7; neutral White Balance. Filmic tone curve at defaults. Bloom Intensity 0.1, Film Grain Intensity 0.1, Vignette Intensity 0.2, Scene Fringe Intensity 0, Lens Flare Intensity 0, Motion Blur Amount 0, depth of field off. TSR anti-aliasing.

### UI and effects

UMG panels are flat `#6b6964` or `#4a4946` Box brushes with square corners, no border and no shadow, aligned to a strict column grid with generous margins. Type is Archivo Black or Anton in large capitals, pale `#c4c1b8` on dark or charcoal `#2e2d2b` on light; counters are big plain numerals. One muted rust accent marks alerts.

Niagara: concrete dust as lit grey sprites, 15 to 25 per puff, lifetime 2 to 3 s, slow drift; falling chips as small mesh particles with collision; ambient motes inside light shafts, lifetime 10 s. Hits leave a pale chipped decal.

## Do / Do not

Do:

- Build massive cantilevered concrete volumes.
- Show board marks and a tie-hole grid.
- Keep the image nearly monochrome grey.
- Light softly with large gradients.

Do not:

- Do not paint surfaces white with coloured accents; that reads as `035`.
- Do not smash the concrete into rubble with grit and scratches; that reads as `030`.
- Do not use smooth white moulded panels; that reads as `091`.
- Do not add gold, marble and ornament; that reads as `096`.

## Nearest styles

- `030` Gritty desaturated war realism: this style shows intact, clean-cut concrete masses in soft grey daylight; `030` is darker, with rubble, grit, scratches and battle damage on everything.
- `035` White city with primary accents: walls here are mid-grey with visible board marks and pour lines; `035` is clean painted white with bright primary accents.
- `091` Clinical white space-age: this style is grey, rough-cast and heavy; `091` is bright white with smooth moulded panels and glowing light strips.

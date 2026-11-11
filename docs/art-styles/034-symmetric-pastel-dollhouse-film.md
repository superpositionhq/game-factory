# Symmetric pastel dollhouse film

Reference works: The Grand Budapest Hotel.

## References

- *The Grand Budapest Hotel* (2014), Wes Anderson, live-action film. https://en.wikipedia.org/wiki/The_Grand_Budapest_Hotel
- *Moonrise Kingdom* (2012), Wes Anderson, live-action film. https://en.wikipedia.org/wiki/Moonrise_Kingdom
- *The Royal Tenenbaums* (2001), Wes Anderson, live-action film. https://en.wikipedia.org/wiki/The_Royal_Tenenbaums
- *Fantastic Mr. Fox* (2009), Wes Anderson, stop-motion film. https://en.wikipedia.org/wiki/Fantastic_Mr._Fox_(film)
- *Asteroid City* (2023), Wes Anderson, live-action film. https://en.wikipedia.org/wiki/Asteroid_City

## Visual definition

- **Shape language and proportions:** Real objects arranged like a dollhouse: boxy rooms seen straight-on, symmetric facades, tidy rows of props, model-like buildings and vehicles.
- **Line and outline:** No outline.
- **Shading model:** Photographic and smooth but flat: soft frontal light with weak shadows.
- **Palette:** `#f4b6c2` `#c75b7a` `#6b3fa0` `#f6e3b4` `#e8763a` `#7fb7be` `#8b2f2f`. Curated pastels: pink, lilac, cream and powder blue with red, purple and orange accents. Every object is colour-matched to the scheme.
- **Lighting:** Soft, even, frontal. Little contrast; no dramatic shadows.
- **Texture and surface:** Clean real materials: painted plaster, carpet, lacquer, uniforms. Tidy, not weathered.
- **Atmosphere and post-processing:** Slight warm grade, mild vignette, flat depth. Optional 4:3 framing.
- **Camera and framing:** Perfect one-point perspective, centred, level; planimetric framing with the camera perpendicular to the back wall; whip pans at 90 degrees.
- **UI and typography:** Centred, symmetric panels that look like title cards, hotel stationery and luggage labels, with thin double-rule borders; icons are flat badges and stamps. Titles use a hand-lettered sign-painter script, labels use widely spaced geometric sans capitals, and counters use tidy typewriter numerals. UI colours are pink `#f4b6c2` and cream `#f6e3b4` with dark red `#8b2f2f` text.
- **VFX and motion:** Effects look like stage props: small cotton-wool smoke puffs, paper confetti and neat dust puffs, with a tidy pop on impact and no sparks. Motion is brisk and deadpan: characters move in straight lines and right angles, hold poses, and start and stop suddenly, with a slight stop-motion feel.

## Fits

- **Genres:** `puzzle`, `detective-mystery`, `exploration`, `simulation`, `stealth`, `platformer`
- **Moods:** whimsical, deadpan, nostalgic
- **Settings:** grand alpine hotel, summer camp island, eccentric family townhouse, desert roadside town

## Unreal recipe

### Assets

Real-scale interior and facade props with clean surfaces: hotel furniture, luggage, uniforms, lifts, cable cars. Assemble rooms as boxes open toward the camera, with the back wall perpendicular to the view and props mirrored about the centre line in tidy rows; a layout script that mirrors placements across the room axis enforces this. Remove dirt, damage and wear masks from store packs. Recolour every albedo by script to the nearest scheme colour. Model-like exteriors, such as a hotel facade or funicular, are best built from scratch as simple symmetric meshes.

### Materials

`M_Dollhouse`, Default Lit, matte: Roughness 0.6 to 0.85 for plaster, carpet and cloth, 0.3 for lacquer; no chrome and no strong clear coat. BaseColor is a palette parameter multiplied by a faint fabric or plaster texture; normal maps at half strength. Each instance picks one scheme colour: walls `#f4b6c2`, trim `#f6e3b4`, uniforms `#6b3fa0`, accents `#8b2f2f`, `#e8763a`, `#7fb7be`. Carpets use the Cloth shading model.

### Lighting and atmosphere

Lumen GI on for soft bounce between pastel walls; reflections kept weak. Light from the camera side: one large Rect Light above and behind the camera plus a strong Sky Light, so shadows fall behind objects and stay faint. No hard key, no side light. Virtual Shadow Maps on with wide source sizes for blurred shadow edges. No volumetric fog; exteriors get a pale graded backdrop instead of haze. Manual exposure about a third of a stop bright.

### Post-processing

Slight warm White Balance, Global Saturation 0.95, Contrast 0.9, lifted shadows through Film Toe 0.4 for a flat photographic look. Vignette Intensity 0.3. Bloom 0.15, Film Grain 0.1. Depth of field off or at Aperture F-stop 11, so the whole room is sharp: no miniature blur at top and bottom. Scene Fringe 0, Motion Blur Amount 0. For optional 4:3 framing, constrain the camera aspect ratio to 1.33 with pillarbox bars in `#f6e3b4`. The camera uses a level, centred one-point view; 90 degree pans are done as short eased moves. No post-process materials. TSR.

### UI and effects

Panels are centred title cards and luggage labels with thin double-rule borders, built from Border brushes in `#f4b6c2` and `#f6e3b4` with `#8b2f2f` text. Titles in a sign-painter script such as Pacifico or Lobster, labels in Josefin Sans capitals with wide spacing, counters in Courier Prime numerals. Icons are flat badges and stamps. Niagara effects look like props: 5 to 8 cotton-wool puff meshes that scale up and vanish in 0.5 s, paper confetti as small unlit quads tumbling for 2 s, and one neat dust ring on impact. Animate at stepped intervals for a slight stop-motion feel; no sparks.

## Do / Do not

Do:

- Frame symmetric, centred and perpendicular to the back wall.
- Match every prop to a limited pastel scheme.
- Light softly from the front.
- Arrange props in ordered rows.

Do not:

- Do not use dramatic side light or deep shadow.
- Do not add atomic-age boomerang shapes and chrome; that reads as `099`.
- Do not miniaturise with blur and glossy plastic; that reads as `057`.
- Do not flatten to unlit isometric colour faces; that reads as `059`.

## Nearest styles

- `099` Atomic-age Googie: this style is boxy, matte and seen straight-on in soft muted pastels; `099` has glossy enamel and chrome, upswept curves and starbursts, and stronger turquoise and coral.
- `057` Toy-diorama tilt-shift: this style shows real-size plaster, carpet and cloth in sharp focus with muted pastels; `057` shows glossy moulded toys in brighter colours, with the top and bottom of the frame blurred like a photographed miniature.
- `059` Isometric pastel impossible architecture: this style is photographed rooms with soft continuous shading, seen straight-on; `059` is unlit geometric blocks seen from an isometric angle, each face one flat tone.

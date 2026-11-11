# Swirling impasto

Reference works: Vincent van Gogh; Loving Vincent.

## References

- *The Starry Night* (1889), Vincent van Gogh, oil painting. https://en.wikipedia.org/wiki/The_Starry_Night
- *Wheatfield with Crows* (1890), Vincent van Gogh, oil painting. https://en.wikipedia.org/wiki/Wheatfield_with_Crows
- *Cafe Terrace at Night* (1888), Vincent van Gogh, oil painting. https://en.wikipedia.org/wiki/Café_Terrace_at_Night
- *Loving Vincent* (2017), Dorota Kobiela and Hugh Welchman (BreakThru Films), oil-painted animated film. https://en.wikipedia.org/wiki/Loving_Vincent
- *Bedroom in Arles* (1888), Vincent van Gogh, oil painting. https://en.wikipedia.org/wiki/Bedroom_in_Arles

## Visual definition

- **Shape language and proportions:** Simplified, slightly warped forms: leaning buildings, flame-like cypress trees, rolling hills, a sky made of spirals and halos. Perspective is steep and a little wrong.
- **Line and outline:** Dark blue or black contour strokes around major objects (roofs, trees, furniture), drawn with the brush.
- **Shading model:** Little tonal modelling. Form is shown by stroke direction and by a few colour steps.
- **Palette:** `#1f3b7a` `#f2c12e` `#2e6f8e` `#e07b2a` `#3f7a3a` `#f5e6a8` `#16203a`. Strong complementary pairs: deep blue with chrome yellow, orange with blue, green with red-brown.
- **Lighting:** Night skies with haloed stars and lamps, or blazing daylight fields.
- **Texture and surface:** Thick impasto: long, directional, rhythmic strokes laid side by side, following contours of objects and swirling in the sky; ridges of paint catch the light.
- **Atmosphere and post-processing:** Full-frame stroke-flow pass and paint relief lighting.
- **Camera and framing:** Slightly high viewpoint over a village or field, or a tilted interior.
- **UI and typography:** Panels are slabs of thick paint in deep blue `#1f3b7a` or night navy `#16203a` with a brushed chrome-yellow `#f2c12e` border, and icons are simple objects drawn with dark brush contours. Text is a heavy hand-painted brush lettering with uneven strokes, and numbers are fat yellow brush numerals with a dark blue contour.
- **VFX and motion:** Effects are made of strokes: stars and lamps pulse with concentric ringed halos, wind and magic show as curling ribbons of parallel strokes, and impacts are bursts of short radiating yellow and orange strokes. The whole surface flows slowly along its stroke directions, and characters move on twos or threes like repainted frames.

## Fits

- **Genres:** `exploration`, `action-adventure`, `detective-mystery`, `rpg`, `puzzle`
- **Moods:** restless, dreamlike, intense
- **Settings:** Provençal village, wheat fields, starry night hillside, café terrace

## Unreal recipe

### Assets

Village houses, churches, cypress trees, wheat fields, cafe furniture, rolling hills. Take simple stylised or mid-poly packs and warp them in Blender: lean buildings 3 to 8 degrees, pull cypresses into flame shapes with a twist, exaggerate hill curves. Flatten textures to three or four colour steps per material by posterising albedo in Pillow; delete normal maps, since relief comes from the paint pass. Build the sky as a dome with star and moon discs.

### Materials

Default Lit with roughness 0.6, Base Colour from the posterised albedo pulled to the palette: `#1f3b7a`, `#2e6f8e`, `#3f7a3a`, `#e07b2a`, `#f2c12e`, `#f5e6a8`. The sky dome is Unlit, its emissive a two-channel flow texture painted by script with spirals round each star and mixed into blue by the post pass; it writes stencil 2. Stars and lamps are Unlit emissive yellow discs with ringed halo cards. Major objects (roofs, trees, furniture, figures) render CustomDepth with stencil 1.

### Lighting and atmosphere

Night: Lumen GI on, a dim blue Directional Light as moon, warm Point Lights at windows and lamps, Sky Light tinted `#1f3b7a`. Day: one strong yellow-white sun, sky fill kept blue so shade stays coloured, never grey. No volumetric fog; atmosphere is paint. Manual exposure per scene.

### Post-processing

PPV: Saturation 1.25, Contrast 1.1, Bloom 0, grain 0, fringe 0, Motion Blur Amount 0. Two post materials at Scene Color After Tonemapping:

1. Priority 0, contours: edges of stencil 1 regions, 4 to 6 px with width noise, in `#16203a`.
2. Priority 1, stroke flow in a Custom node: stroke direction is the WorldNormal projected to screen and turned 90 degrees, so strokes wrap forms, or the sky's flow texture where stencil is 2. Run a line integral convolution of PostProcessInput0 along it, 20 to 30 px long, so colour smears into long parallel strokes. Generate a height value from a stretched noise advected along the same direction, scrolled slowly with Time, and light it with a fixed screen-space light (DDX/DDY of height as a normal) to give ridged highlights and grooves.

The scroll makes the whole surface creep along its strokes. Animate characters on twos or threes.

### UI and effects

Panels: Box brushes cut from a thick-paint slab texture in `#1f3b7a` or `#16203a`, with a brushed `#f2c12e` border baked into the 9-slice edges. Text in Permanent Marker; numerals in `#f2c12e` with a 2 px `#16203a` font outline.

Niagara: halos as three or four concentric ring sprites pulsing outward over 2 s; wind and magic as ribbon bundles of five to eight parallel ribbons curling along curl noise; impacts as 14 short radial stroke sprites in `#f2c12e` and `#e07b2a`, 0.3 s.

## Do / Do not

Do:

- Make strokes long, parallel and rhythmic along a flow field.
- Swirl the sky around stars.
- Use blue and yellow complementary contrast.
- Add brushed dark contours to main objects.

Do not:

- Do not use short soft dabs in pastel daylight; that reads as `075`.
- Do not use uniform dots; that reads as `077`.
- Do not mute the palette and randomise stroke direction; that reads as `028`.
- Do not smooth the paint relief away.

## Nearest styles

- `075` Impressionist broken colour: this style has dark brushed contours, long swirling strokes and strong blue-and-yellow contrast; `075` has no contours and uses short soft dabs of pastel colour.
- `028` Expressionist oil isometric: this style uses strong blue, yellow and orange with dark contours and strokes that flow in one rhythm; `028` is muted green, grey and brown with no contours and strokes in many directions.
- `077` Pointillist dot field: this style draws dark contours and lays colour in long ridged strokes of a few distinct steps; `077` has no contours and covers smooth forms with small round dots that blend at a distance.

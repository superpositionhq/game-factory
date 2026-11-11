# Soft open-world anime cel

Reference works: Genshin Impact.

## References

- *Genshin Impact* (2020), miHoYo, video game. https://en.wikipedia.org/wiki/Genshin_Impact
- *Honkai: Star Rail* (2023), miHoYo, video game. https://en.wikipedia.org/wiki/Honkai:_Star_Rail
- *Tales of Arise* (2021), Bandai Namco Studios, video game. https://en.wikipedia.org/wiki/Tales_of_Arise
- *Zenless Zone Zero* (2024), miHoYo, video game. https://en.wikipedia.org/wiki/Zenless_Zone_Zero

## Visual definition

- **Shape language and proportions:** Slim anime characters with detailed layered costumes and ornaments. Scenery is clean and idealised: rounded hills, tidy stone towns, stylised trees.
- **Line and outline:** Thin dark outline (1 to 2 px), coloured slightly toward the local hue, on characters and props; light or none on terrain.
- **Shading model:** Two bands with a soft-edged ramp, plus a stylised metal highlight and a face shadow that keeps a clean shape.
- **Palette:** `#a8d8ea` `#fcefc7` `#aa96da` `#fcbad3` `#7fcd91` `#4d5b8c` `#ffffff`. Light pastels: sky blue, cream, lavender, mint, with gold trim. Shadows are lavender-blue.
- **Lighting:** Clear daylight with strong ambient; rim light on characters.
- **Texture and surface:** Smooth gradients inside flat regions; fine ornamental trim lines on costumes; terrain has simple painted variation.
- **Atmosphere and post-processing:** Soft bloom, light haze, gentle colour grade toward pastel.
- **Camera and framing:** Third-person, 35 to 50 mm equivalent, character centred against open scenery.
- **UI and typography:** Cream and dark slate-blue panels with rounded corners, thin gold borders and small ornamental flourishes at the corners. Icons are flat white or gold glyphs inside circles and diamonds. Text is an elegant rounded serif for titles and a clean sans for body text; damage numbers are small bold numerals coloured by element (lavender, mint, sky blue, gold) that float up and fade.
- **VFX and motion:** Soft glowing particles, petals, sparkles and translucent ribbon trails in pastel element colours, with a ring of light and a short bloom flash on hit. Animation is fluid and graceful, with flowing hair and cloth, flourished attack poses and a light floaty landing.

## Fits

- **Genres:** `rpg`, `action-adventure`, `exploration`, `hack-and-slash`, `roguelike`, `puzzle`
- **Moods:** serene, adventurous, bright
- **Settings:** fantasy meadows and cliffs, harbour city, mountain temple, floating islands

## Unreal recipe

### Assets

Stylised fantasy packs with rounded hills, tidy stone towns and simple trees are the right base. Smooth terrain textures to gentle gradients with light variation and drop their normal maps. Characters are slim anime rigs with layered costumes; add fine trim lines and gold edging into costume textures by script, and store a face shadow threshold map so the cheek and nose shadow keeps a clean shape as the head turns.

### Materials

`M_SoftCel`, Unlit, for characters and props. A Material Parameter Collection gives sun direction and colour. N·L goes through a CurveAtlasRowParameter ramp with two tones and a soft edge about 8 percent wide; the shadow side multiplies toward lavender-blue (`#aa96da` to `#4d5b8c` at low strength) and stays light. Faces replace N·L with the threshold map compared against the head's forward and right vectors. Metal regions (mask) add a stylised highlight: a matcap-like lookup from view-space normal into a small gold gradient texture. A soft Fresnel rim is added in white. Terrain and buildings use `M_SoftWorld`, Default Lit, Roughness 0.9, Specular 0.1, with smooth painted gradients.

Outline: inverted hull as Overlay Material, 1 to 2 px, and its colour is the base texture darkened and saturated, not black, so each line leans toward the local hue. Terrain has no hull.

### Lighting and atmosphere

Lumen GI on for the world, with a strong Sky Light so ambient is high. Clear-day Directional Light, Source Angle 2. Sky Atmosphere with light Volumetric Cloud. Exponential Height Fog in `#a8d8ea` at low density for gentle haze; Volumetric Fog off.

### Post-processing

Bloom Intensity 0.5, Threshold 0.9, for a soft overall glow. Grade toward pastel: Global Contrast 0.92, Shadows Gain lifted and tinted lavender, Highlights slightly cream (`#fcefc7`), Global Saturation 0.95. Tone Curve Amount 0.7. Props that need a line but have no hull are stencil-tagged and outlined by a thin post-process edge pass on CustomStencil at Scene Color Before Bloom, tinted from scene colour. No grain, no fringe, Vignette 0.15, Motion Blur Amount 0. TSR.

### UI and effects

Panels are Rounded Box brushes in cream or dark slate-blue (`#4d5b8c`) with a 1 px gold outline and small corner flourish images. Titles use Cormorant or Playfair Display, body text Nunito. Damage numbers are small bold numerals coloured by element (lavender, mint `#7fcd91`, sky blue, gold), rising and fading over 0.8 s. Niagara: soft additive glow sprites, petals, four-point sparkles, translucent ribbon trails in element colours, and on hit a ring of light expanding for 0.3 s with a short bloom flash.

## Do / Do not

Do:

- Use tinted, thin outlines.
- Keep shadows lavender and light.
- Add gold trim and a stylised metal highlight.
- Use soft-edged two-band ramps.

Do not:

- Do not use hard black lines and razor band edges with saturated shadows; that reads as `015`.
- Do not remove outlines and paint the terrain broadly; that reads as `002`.
- Do not add dense painted backgrounds; that reads as `014`.
- Do not use full PBR shading on characters; that reads as `013`.

## Nearest styles

- `002` Painterly open-air cel: `002` has almost no outline and paints its terrain in broad soft patches; this style outlines characters and props and keeps terrain clean and smooth.
- `015` Two-tone fighting-anime cel: `015` has black tapered outlines, razor-sharp shadow edges and strong, dark shadow colours; this style has thin tinted outlines, soft shadow edges and light lavender shadows.
- `014` Hand-painted pastoral anime: `014` paints its scenery with visible brush dabs and dense foliage detail; this style keeps scenery smooth, with simple gradients and tidy shapes.

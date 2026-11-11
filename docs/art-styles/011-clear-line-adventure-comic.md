# Clear-line adventure comic

Reference works: The Adventures of Tintin.

## References

- *The Adventures of Tintin* (1929), Herge, comic album series. https://en.wikipedia.org/wiki/The_Adventures_of_Tintin
- *Blake and Mortimer* (1946), Edgar P. Jacobs, comic album series. https://en.wikipedia.org/wiki/Blake_and_Mortimer
- *The Adventures of Tintin (film)* (2011), Amblin Entertainment and WingNut Films, animated film. https://en.wikipedia.org/wiki/The_Adventures_of_Tintin_(film)
- *XIII* (2003), Ubi Soft Paris, video game. https://en.wikipedia.org/wiki/XIII_(2003_video_game)

## Visual definition

- **Shape language and proportions:** Accurate, well-researched objects (vehicles, buildings, machines) drawn with simplified but correct proportions. Characters have simple round faces on realistic bodies.
- **Line and outline:** Black line of one constant weight (about 2 px) on every silhouette and every inner edge. No hatching, no line-weight variation.
- **Shading model:** None. One flat colour per surface, no cast shadows or only a flat ground shadow.
- **Palette:** `#1a1a1a` `#f4efe1` `#d93a2b` `#2f6fb5` `#f2c230` `#7fb069` `#c9a27a`. Clear, medium-saturation flats on off-white: red, blue, yellow, green and skin tan. No gradients.
- **Lighting:** Even, shadowless.
- **Texture and surface:** None. Detail is carried by line alone (bricks, planks and rivets drawn as outlines).
- **Atmosphere and post-processing:** None. Clean anti-aliased edges.
- **Camera and framing:** Eye-level, readable, full-figure compositions with deep focus.
- **UI and typography:** Off-white rectangular panels with a thin black border, like comic caption boxes and speech balloons. Text is hand-lettered upright comic capitals in black; icons are small flat-colour line drawings. Counters and damage numbers are bold black-outlined numerals filled with yellow or red.
- **VFX and motion:** Effects are drawn comic marks: white puff clouds with a black outline, star bursts on impact, speed lines, sweat drops and lettered sound words. Animation is crisp with clear held poses and quick moves between them; nothing glows or blurs.

## Fits

- **Genres:** `action-adventure`, `detective-mystery`, `exploration`, `puzzle`, `stealth`, `platformer`
- **Moods:** adventurous, light-hearted, curious
- **Settings:** 1930s port city, desert expedition, steamship and seaplane travel, mountain monastery

## Unreal recipe

### Assets

Accuracy matters: choose realistic vehicles, buildings and machines with correct proportions, then remove everything except shape. Delete all texture maps and assign one flat palette colour per material slot. Small detail must exist as geometry or as an ID mask so the line pass can find it: by script, bake a flat-colour ID texture where each brick, plank and rivet has a distinct grey value, or inset them as geometry in Blender. Characters keep realistic bodies; replace heads with simple round ones built from scratch (dot eyes, short nose).

### Materials

`M_ClearLine` shows one flat colour with no light response: Default Lit with BaseColor black, Specular 0, Roughness 1 and the flat colour in Emissive Color, so the GBuffer stays available to the line pass while lights have no effect. No bands, no shadow tint, no Fresnel. The baked detail ID is a greyscale texture wired to Metallic, a channel that has no visible result on a black base and can be read back in post. Whole objects that touch get different CustomDepth Stencil Values. A ground shadow, if wanted, is one flat grey ellipse decal.

### Lighting and atmosphere

Even and shadowless. Disable Lumen GI and reflections, cast shadows on all lights and fog. No Sky Atmosphere; the sky is a flat `#f4efe1` or pale blue dome. Exposure Manual.

### Post-processing

Tone Curve Amount 0 and Expand Gamut 0 so `#d93a2b`, `#2f6fb5` and `#f2c230` reach the screen as authored. One material, `PP_ClearLine`, at Scene Color After Tonemapping: a Roberts cross on SceneDepth, WorldNormal, CustomStencil and the Metallic ID, with thresholds tuned so every silhouette and every inner edge gets a line. Line width is fixed at 2 px with no noise, no depth scaling and no taper; colour is `#1a1a1a`. That single constant weight on all edges, with no shading of any kind, is the whole style. Bloom, grain, vignette, fringe, ambient occlusion off; no depth of field (deep focus); Motion Blur Amount 0. FXAA at 100 percent screen percentage smooths the line after it is drawn.

### UI and effects

Panels are off-white Box brushes with a 2 px black outline and square or slightly rounded corners; dialogue uses speech-balloon 9-slice brushes with a tail. Text is upright comic capitals (Comic Neue Bold, Patrick Hand SC) in black. Counters are bold numerals with a black font outline filled `#f2c230` or `#d93a2b`. Niagara: white puff clouds with a drawn black edge as Masked flipbook sprites (4 frames, 0.4 s), star bursts, straight speed-line sprites, sweat drops and lettered sound words as short-lived meshes. Nothing is additive and nothing glows.

## Do / Do not

Do:

- Keep one line weight everywhere.
- Use one flat colour per surface.
- Model or draw small details as outline only.
- Keep object proportions accurate.

Do not:

- Do not vary line weight or add hatching; that reads as `001`.
- Do not add shading bands; that reads as `015`.
- Do not shift to pale desaturated washes with sparse thin lines; that reads as `012`.
- Do not add print dots; that reads as `081`.

## Nearest styles

- `012` Thin-line pastel desert: `012` uses pale sand and pastel tints with thin lines that become sparse in open areas; this style uses clear red, blue and yellow flats with one firm black line on every edge.
- `081` Ben-Day pop art: `081` fills skin and skies with visible printed dots; this style keeps every fill a plain flat colour.
- `082` Ukiyo-e woodblock: `082` shows wood grain in its colour areas and fades its skies from dark to light; this style has clean fills with no grain and no fades.

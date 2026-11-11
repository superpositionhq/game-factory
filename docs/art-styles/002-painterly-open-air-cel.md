# Painterly open-air cel

Reference works: The Legend of Zelda: Breath of the Wild.

## References

- *The Legend of Zelda: Breath of the Wild* (2017), Nintendo EPD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Breath_of_the_Wild
- *The Legend of Zelda: Tears of the Kingdom* (2023), Nintendo EPD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Tears_of_the_Kingdom
- *The Legend of Zelda: Skyward Sword* (2011), Nintendo EAD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Skyward_Sword
- *Immortals Fenyx Rising* (2020), Ubisoft Quebec, video game. https://en.wikipedia.org/wiki/Immortals_Fenyx_Rising

## Visual definition

- **Shape language and proportions:** Natural proportions, simplified. Rocks, trees and ruins are soft, rounded masses with few small details; silhouettes read clearly at long distance.
- **Line and outline:** No drawn outline on scenery. Characters and small props get a thin, soft dark rim (1 to 2 px) and a bright fresnel rim on the lit side.
- **Shading model:** Two bands (lit and shadow) with a narrow soft transition, plus an optional specular highlight band on metal and hair.
- **Palette:** `#8fc46a` `#4f8a5b` `#bfe3f2` `#f3e7b8` `#c98d5a` `#6f7fa8` `#e06a4a`. Fresh greens, sky blues and warm stone; shadows are blue-tinted, never grey or black.
- **Lighting:** Bright outdoor sun with strong sky fill. Shadows are soft-edged and light in value.
- **Texture and surface:** Low-frequency painted gradients and broad brush patches. Grass and foliage are flat colour cards with a vertical gradient.
- **Atmosphere and post-processing:** Strong aerial perspective that fades distance to pale blue, mild bloom on sky and highlights, light volumetric haze.
- **Camera and framing:** Wide 28 to 35 mm equivalent, third-person height, horizon in the upper third to show terrain depth.
- **UI and typography:** Thin, quiet UI: small white icons and translucent dark panels with a fine pale border and soft corner ornaments. Text is a light humanist sans in white or pale cream (`#f3e7b8`). Counters are small plain numerals, with red-orange (`#e06a4a`) only for hearts and danger.
- **VFX and motion:** Effects are soft-edged stylised shapes: curled smoke puffs, pale blue glows, drifting spores and grass that bends in the wind. Hits give a brief white starburst and a short hit-pause; animation is fluid and natural with light anticipation.

## Fits

- **Genres:** `exploration`, `action-adventure`, `survival-craft`, `rpg`, `puzzle`
- **Moods:** serene, adventurous, wistful
- **Settings:** grassy highlands, overgrown ruins, mountain wilderness, sky islands

## Unreal recipe

### Assets

Choose packs with large, rounded forms: weathered boulders, broad-canopy trees, simple ruins. From a realistic pack, drop normal maps on scenery, blur each base colour map heavily and remap it toward the palette greens and warm stone, then cut textures to 512 px. Build grass and foliage from scratch as flat cards with soft vertex normals pointing up, so a clump shades as one mass.

### Materials

`M_SunlitCel` is Unlit and computes its own light. A Material Parameter Collection carries sun direction and colour, written from C++ each frame. N·L from VertexNormalWS passes through a SmoothStep with a narrow range (0.45 to 0.55). The result lerps between the base colour multiplied by a blue shadow tint (`#6f7fa8`, kept light) and the base colour itself. Metal and hair instances enable a second SmoothStep on the half-vector term for one highlight band. A character switch adds a Fresnel rim masked to the lit side. Foliage instances lerp from a dark root green (`#4f8a5b`) to `#8fc46a` along the card's V coordinate and sway through World Position Offset. Because Unlit receives no cast shadows, use a second master for terrain and large scenery: Default Lit, Roughness 1, Specular 0, so those surfaces take the soft sun shadow.

### Lighting and atmosphere

Lumen GI on for the Default Lit scenery, with a bright Sky Light (Real Time Capture) so shadow values stay high. One Directional Light with Source Angle 3 to 4 for soft shadow edges. Sky Atmosphere plus Exponential Height Fog with Fog Inscattering Color `#bfe3f2`, enough density that terrain at 300 m is half-way to sky colour; enable Volumetric Fog at low Extinction Scale for light haze.

### Post-processing

A single post-process material at Scene Color Before Bloom draws the character rim: components that need it render CustomDepth with a stencil value, and the pass darkens a 1 to 2 px band at the stencil edge with a soft falloff. Scenery has no stencil value, so no line. Bloom Intensity 0.4 with Threshold 1 so only sky and highlights glow. Keep the filmic tone curve but raise Shadows Gain and tint Shadows Offset blue. No grain or vignette, Motion Blur Amount 0, TSR anti-aliasing.

### UI and effects

Panels are Rounded Box brushes in dark blue-grey at 60 percent opacity with a 1 px `#f3e7b8` outline. Text is Nunito Light or Quicksand in white; counters are small plain numerals, and `#e06a4a` is reserved for hearts and warnings. Niagara: curled smoke puffs as soft-edged sprite flipbooks, 20 to 40 drifting spores living 4 to 6 s, pale blue additive glows, and a white starburst on hits lasting 0.2 s.

## Do / Do not

Do:

- Tint shadows blue and keep them light.
- Fade distant terrain strongly toward sky colour.
- Use a bright fresnel rim on characters.
- Keep textures as large soft patches.

Do not:

- Do not add heavy black outlines or hatching; that reads as `001`.
- Do not remove all texture and gradient; flat fills read as `003`.
- Do not use full PBR roughness and metal response; that reads as `013`.
- Do not use dense painted backgrounds with brown line art; that reads as `014`.

## Nearest styles

- `003` Flat-shape ocean toon: this style has soft painted gradients, distance haze and natural proportions; `003` uses single flat colours with a knife-sharp shadow edge, clear air and strong caricature.
- `018` Soft open-world anime cel: this style draws no outline on scenery and only a faint rim on characters; `018` draws a thin coloured outline around every character and prop and adds fine ornamental trim on costumes.
- `014` Hand-painted pastoral anime: this style keeps scenery as broad soft colour patches; `014` has densely painted backgrounds with visible brush dabs and a brown line on characters.

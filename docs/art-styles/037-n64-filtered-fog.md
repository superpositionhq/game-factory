# N64 filtered fog

Reference works: Super Mario 64; Ocarina of Time.

## References

- *Super Mario 64* (1996), Nintendo EAD, video game. https://en.wikipedia.org/wiki/Super_Mario_64
- *The Legend of Zelda: Ocarina of Time* (1998), Nintendo EAD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Ocarina_of_Time
- *Banjo-Kazooie* (1998), Rare, video game. https://en.wikipedia.org/wiki/Banjo-Kazooie_(video_game)
- *GoldenEye 007* (1997), Rare, video game. https://en.wikipedia.org/wiki/GoldenEye_007

## Visual definition

- **Shape language and proportions:** Low polygon counts with rounded, friendly forms: characters built from smooth-shaded segments, large simple hills, blocky castles.
- **Line and outline:** No outline.
- **Shading model:** Smooth per-vertex (Gouraud) shading with vertex-colour gradients baked into geometry.
- **Palette:** `#3a7fd5` `#4caf50` `#e53935` `#fdd835` `#8d6e63` `#b0bec5` `#f5f5f5`. Bright primary colours: blue sky, green grass, red and yellow accents.
- **Lighting:** Simple directional light plus ambient; fake shadows as dark round blobs.
- **Texture and surface:** Very small textures stretched over large surfaces and blurred by bilinear filtering; visible repetition.
- **Atmosphere and post-processing:** 320x240 output with soft blur from filtering and anti-aliasing; distance fog in a flat colour; no dither pattern.
- **Camera and framing:** Third-person follow camera, 45 to 60 degree field of view.
- **UI and typography:** Chunky rounded icons that look like small rendered 3D objects, with no panel frames around them. Titles use thick bubbly display lettering with a dark outline and drop shadow; text is a rounded bold sans. Counters are an icon, a cross and big outlined numerals in yellow `#fdd835` or white `#f5f5f5`.
- **VFX and motion:** A few large soft-edged sprites: star sparkles, round dust clouds, smoke balls and a simple coloured flash on a hit. Animation is bouncy and exaggerated, with squash and stretch on jumps and simple, readable run cycles.

## Fits

- **Genres:** `platformer`, `action-adventure`, `exploration`, `racing`, `fps`, `sports`
- **Moods:** cheerful, playful, nostalgic
- **Settings:** castle grounds, green fields and villages, tropical islands, snowy mountains

## Unreal recipe

### Assets

Low-polygon models with rounded, friendly forms: segmented smooth-shaded characters, big simple hills, blocky castles. Decimate store meshes to a few hundred triangles and keep smooth normals. Rebake albedo to 32 or 64 px and stretch it across large surfaces so repetition and blur show. Import textures with default bilinear filtering and mipmaps on; Maximum Texture Size 64. Remove normal, roughness and metallic maps. Paint gradients into vertex colours by script (grass darker at the base of a hill, sky-tinted tops). Most scenery is quickest built from scratch as simple primitives with bevels.

### Materials

`M_N64`, Unlit. BaseColor is the tiny blurred texture multiplied by vertex colour and by a smooth Gouraud term: `Dot` of VertexNormalWS with a light vector from a Material Parameter Collection, plus an ambient constant, computed in the vertex stage through Customized UVs so it interpolates across each triangle. No vertex snapping and no affine warp: geometry stays steady. Fog is a lerp to a flat colour (for example `#b0bec5`) by PixelDepth, starting at about 20 m. Blob shadows are a separate translucent Unlit decal or quad with a soft round dark texture placed under each character from C++.

### Lighting and atmosphere

Lumen off, `r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`, ambient occlusion off. No real shadows and no shadow-casting lights; the single directional term lives in the material. Sky is a dome with a vertical gradient from `#3a7fd5` to pale blue, or a low-resolution cloud texture. Distance fog is the material's flat colour, not volumetric. Fixed exposure.

### Post-processing

Render at 320x240 through `r.ScreenPercentage` but upscale softly: FXAA (`r.AntiAliasingMethod=1`) and a bilinear upscale (`r.Upscale.Quality=1`), giving the blurred edges of the hardware. No dither material and no colour-depth reduction. Tone Curve Amount 0 with Saturation 1.1 to keep primaries bright. Bloom 0, Film Grain 0, Vignette 0, Scene Fringe 0, depth of field off, Motion Blur Amount 0.

### UI and effects

UMG has no panel frames. Icons are small pre-rendered 3D objects (star, coin, heart) captured by a script and downscaled. Counters read as icon, cross, number in big outlined numerals: Baloo 2 ExtraBold or Fredoka with a 3 px dark font outline and a drop shadow, in `#fdd835` or `#f5f5f5`. Titles use the same bubbly face, larger. Niagara: a few large soft-edged sprites with bilinear-filtered 32 px textures: 4 or 5 star sparkles spinning for 0.6 s, 3 round dust clouds on landing, smoke balls that shrink over 0.8 s, and one coloured flash quad on a hit. Translucent, never additive.

## Do / Do not

Do:

- Blur small textures with bilinear filtering.
- Paint gradients with vertex colours.
- Use blob shadows and flat distance fog.
- Render at low resolution with linear upscale.

Do not:

- Do not use nearest filtering, dither or vertex wobble; that reads as `036`.
- Do not use hard two-band toon shading; that reads as `003`.
- Do not add glossy plastic with depth-of-field blur; that reads as `057`.
- Do not use crisp high-resolution textures.

## Nearest styles

- `036` PS1 low-poly wobble: textures here are smeared soft, geometry is steady and colours are bright; `036` has sharp square texels, jittering polygons and a dark, muddy, dithered image.
- `057` Toy-diorama tilt-shift: this style has angular low-polygon silhouettes with blurry stretched textures and a matte finish; `057` has smooth rounded glossy plastic forms and blurs the top and bottom of the frame like a photographed miniature.
- `003` Flat-shape ocean toon: surfaces here carry smooth gradients; `003` splits each surface into two flat tones with a razor-sharp boundary.

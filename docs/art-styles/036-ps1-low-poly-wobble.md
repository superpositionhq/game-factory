# PS1 low-poly wobble

Reference works: Silent Hill; Final Fantasy VII.

## References

- *Silent Hill* (1999), Konami (Team Silent), video game. https://en.wikipedia.org/wiki/Silent_Hill_(video_game)
- *Final Fantasy VII* (1997), Square, video game. https://en.wikipedia.org/wiki/Final_Fantasy_VII
- *Metal Gear Solid* (1998), Konami, video game. https://en.wikipedia.org/wiki/Metal_Gear_Solid_(video_game)
- *Tomb Raider* (1996), Core Design, video game. https://en.wikipedia.org/wiki/Tomb_Raider_(1996_video_game)
- *Crash Bandicoot* (1996), Naughty Dog, video game. https://en.wikipedia.org/wiki/Crash_Bandicoot_(video_game)

## Visual definition

- **Shape language and proportions:** Very low polygon counts: characters of 300 to 800 triangles with blocky hands and pointed joints; environments made of large flat quads.
- **Line and outline:** No outline.
- **Shading model:** Per-vertex lighting (Gouraud) at low colour depth, so gradients show stepped bands and dither.
- **Palette:** `#1a1a22` `#4a4438` `#7a6a55` `#5a6a7a` `#8a3a2a` `#b8a888` `#2e3a2e`. Muddy, dark and low-contrast; 15-bit colour with visible ordered dither.
- **Lighting:** Vertex lighting from one or two sources, short draw distance closed off by fog or darkness.
- **Texture and surface:** Tiny textures (32 to 128 px) with no filtering: large square texels, warped by affine mapping; polygons jitter because vertices snap to the pixel grid.
- **Atmosphere and post-processing:** 320x240 output upscaled with nearest-neighbour sampling, 4x4 ordered dither, no anti-aliasing.
- **Camera and framing:** Fixed or tank-control cameras; wide field of view (60 to 75 degrees).
- **UI and typography:** Plain rectangular windows in a dark flat or gradient fill with a thin pale border, and low-resolution pixel icons. Type is a chunky low-resolution bitmap face with fixed-width pixel numerals. Text is pale tan `#b8a888` on near-black `#1a1a22`, and damage numbers are small pale pixel digits that pop up over the target.
- **VFX and motion:** Effects are a few flat textured quads with large pixels: a flash sprite, a puff of smoke, blood as a few dull red squares; no soft particles. Animation is stiff and keyframed with few in-betweens: limbs move as rigid segments and the mesh jitters as it moves.

## Fits

- **Genres:** `survival-horror`, `rpg`, `action-adventure`, `stealth`, `platformer`, `exploration`
- **Moods:** eerie, uneasy, nostalgic
- **Settings:** foggy abandoned town, industrial megacity slums, military base, ancient tomb

## Unreal recipe

### Assets

Characters of 300 to 800 triangles with blocky hands and pointed joints; rooms from large flat quads. Decimate store meshes hard in Blender (Nanite off, `r.Nanite=0`), then rebake albedo to 64 or 128 px, quantised to 15-bit colour. Delete normal, roughness and metallic maps. Import textures with Filter Nearest, Mip Gen Settings NoMipmaps and Texture Group 2D Pixels (Unfiltered). Bake lighting into vertex colours with a Blender script. Rigid-segment characters are quick to build from scratch; skinned ones should use one bone per vertex so limbs move as stiff pieces.

### Materials

`M_PSX`, Unlit, since lighting is per vertex. Three parts:

- Vertex snap: a Custom node feeding World Position Offset transforms the vertex to clip space, rounds its xy to a 320x240 grid, transforms back and returns the offset. This produces the polygon jitter.
- Affine mapping: Customized UVs output UV multiplied by clip-space w from the vertex shader; the pixel shader divides by the interpolated w, removing perspective correction so textures warp across large quads.
- Gouraud light: baked vertex colour multiplied by one or two light terms evaluated in the vertex stage through Customized UVs, using light positions and colours from a Material Parameter Collection.

A fog parameter lerps to `#1a1a22` by vertex distance.

### Lighting and atmosphere

Lumen off: `r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`, `r.DefaultFeature.AmbientOcclusion=0`. No shadow-casting lights; the one or two "lights" are MPC vectors set from C++. Draw distance is short: the material's vertex fog and a far clip close the view in darkness within 15 to 25 m. No Sky Atmosphere; a black or flat-colour backdrop. Fixed exposure with `r.DefaultFeature.AutoExposure=0`.

### Post-processing

Render at 320x240: set `r.ScreenPercentage` so the internal height is 240, `r.AntiAliasingMethod=0`, `r.Upscale.Quality=0` for nearest upscale. One post material at Scene Color After Tonemapping, `PP_PSXDither`: adds a 4x4 Bayer threshold indexed by the 320x240 pixel coordinate, then floors each channel to 5 bits. Tone Curve Amount 0 so the muddy palette is not reshaped. Bloom, grain, vignette, fringe, depth of field and Motion Blur Amount all 0.

### UI and effects

UMG windows are flat or vertical-gradient rectangles in dark blue-grey with a 1 px `#b8a888` border, laid out on a 320x240 grid and scaled by an integer factor. Font: Silkscreen or Pixelify Sans, imported without anti-aliasing and with fixed-width numerals; text `#b8a888` on `#1a1a22`. Damage numbers pop 8 px upward and vanish after 0.5 s. Niagara: one to four unlit quads per effect with nearest-filtered 32 px textures, such as a 2-frame flash, a single smoke puff and three or four dull red squares for blood. No soft particles.

## Do / Do not

Do:

- Snap vertices to a 320x240 grid.
- Use affine texture mapping and nearest filtering.
- Render at 320x240 and upscale with nearest sampling.
- Add ordered dither at 5 bits per channel.

Do not:

- Do not filter textures or anti-alias edges; a blurred look reads as `037`.
- Do not remove textures and use flat colour polygons; that reads as `043`.
- Do not use billboard sprites in a ray-cast-style maze; that reads as `046`.
- Do not use perspective-correct mapping with stable vertices.

## Nearest styles

- `037` N64 filtered fog: textures here show hard square texels, polygons jitter, and the image is dark and dithered; `037` has smeared soft textures, steady geometry and bright primary colours.
- `046` Low-res sprite 2.5D shooter: characters and scenery here are textured polygon models; `046` uses flat sprites that always face the camera, in levels made of vertical walls and flat floors.
- `043` Flat-shaded early polygon: every polygon here carries a small pixelated texture; `043` has plain single-colour facets with no textures.

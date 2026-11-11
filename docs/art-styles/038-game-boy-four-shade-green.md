# Game Boy four-shade green

Reference works: Link's Awakening (1993); Tetris.

## References

- *The Legend of Zelda: Link's Awakening* (1993), Nintendo EAD, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Link's_Awakening
- *Tetris (Game Boy)* (1989), Nintendo, video game. https://en.wikipedia.org/wiki/Tetris_(Game_Boy_video_game)
- *Pokemon Red and Blue* (1996), Game Freak, video game. https://en.wikipedia.org/wiki/Pokémon_Red,_Blue,_and_Yellow
- *Super Mario Land* (1989), Nintendo R&D1, video game. https://en.wikipedia.org/wiki/Super_Mario_Land

## Visual definition

- **Shape language and proportions:** Tile-based: everything fits an 8 px or 16 px grid. Characters are 16x16 px with large heads. Shapes are built from single pixels.
- **Line and outline:** One-pixel outlines in the darkest shade around sprites and important tiles.
- **Shading model:** None beyond pixel clusters of the two middle shades; at most one light and one dark shade per object.
- **Palette:** `#0f380f` `#306230` `#8bac0f` `#9bbc0f` `#cadc9f`. Exactly four olive-green shades from near-black green to pale yellow-green.
- **Lighting:** None.
- **Texture and surface:** Pixel patterns: checker dither, brick and grass tiles, 2x2 dot clusters.
- **Atmosphere and post-processing:** 160x144 output scaled by an integer factor; optional LCD pixel grid with thin gaps and slight ghosting.
- **Camera and framing:** Orthographic top-down or side view; when used in 3D, a fixed three-quarter view.
- **UI and typography:** Text boxes in the lightest shade `#cadc9f` with a one-pixel border in the darkest shade `#0f380f`, and 8x8 px tile icons such as hearts and coins. Type is an 8x8 px bitmap face in capitals. Counters use the same pixel digits in a fixed status bar at the screen edge, and a selected item is shown with its shades inverted.
- **VFX and motion:** Effects are tiny sprites of two or three frames: a star burst, a dust puff, a sword arc. A hit makes the sprite blink or invert its shades, and big events flash the whole screen by shifting all four shades. Animation uses two to four frames per cycle and moves in whole-pixel steps, so it reads as snappy.

## Fits

- **Genres:** `rpg`, `puzzle`, `action-adventure`, `platformer`, `roguelike`, `exploration`
- **Moods:** cosy, nostalgic, simple
- **Settings:** island village, monster-filled routes and towns, tile dungeon, falling-block well

## Unreal recipe

### Assets

Everything is authored on an 8 px grid. The cleanest route is true 2D: tile maps and 16x16 px sprites drawn by a Pillow script and imported for Paper2D or instanced quads. For 3D seen from a fixed three-quarter orthographic camera, build blocky tile-sized meshes from scratch with Geometry Script and paint them with 16 px tile textures (brick, grass, checker dither). Store packs do not convert well; use at most their silhouettes. Import every texture with Filter Nearest, NoMipmaps, Texture Group 2D Pixels (Unfiltered), authored as four grey levels.

### Materials

`M_FourShade`, Unlit. The texture stores a shade index as grey (0, 85, 170, 255); the material passes it through unchanged, and the post chain maps index to colour, so palette shifts are global. Sprite and tile art already contains its one-pixel darkest-shade outline. Each object uses at most one light and one dark shade plus the outline. Hit blink is a scalar parameter that inverts the index (1 minus value) for two frames.

### Lighting and atmosphere

None. Lumen off, `r.DynamicGlobalIlluminationMethod=0`, `r.ReflectionMethod=0`, ambient occlusion off, no lights, no fog, no sky. Orthographic camera sized so one texel equals one output pixel at 160x144. Fixed exposure, auto exposure disabled.

### Post-processing

Render the scene to a 160x144 render target from C++ and present it in a UMG Image scaled by an integer factor, letterboxed with `#0f380f` or a dark bezel; this avoids fractional `r.ScreenPercentage` scaling. `r.AntiAliasingMethod=0`. Post materials at Scene Color After Tonemapping, in order:

1. `PP_FourGreens`: luminance quantised to four levels and mapped to `#0f380f`, `#306230`, `#8bac0f`, `#cadc9f` (with `#9bbc0f` as the screen-off background tint). An MPC offset shifts all four levels together for full-screen flashes.
2. `PP_LCDGrid` (optional, on the upscaled image as a User Interface material): thin dark gaps between pixels and a 10 percent blend with the previous frame for ghosting.

Tone Curve Amount 0. Bloom, grain, vignette, fringe, depth of field and Motion Blur Amount 0.

### UI and effects

Text boxes are `#cadc9f` with a 1 px `#0f380f` border, drawn at 160x144 and scaled with the game image. Font: Press Start 2P at 8 px, capitals, no anti-aliasing. Hearts and coins are 8x8 tile icons; counters sit in a fixed status bar at the bottom edge. A selected item swaps its shades. Effects are flipbook sprites of two or three frames at 8 to 10 frames per second: star burst, dust puff, sword arc, moved in whole-pixel steps from C++. Niagara is optional; if used, sprite renderer with SubUV and positions snapped to the pixel grid.

## Do / Do not

Do:

- Output exactly four green shades.
- Render at 160x144 with integer scaling.
- Align everything to an 8 px grid.
- Outline sprites in the darkest shade.

Do not:

- Do not use cyan, magenta and white; that reads as `039`.
- Do not use only two values with dense dither; that reads as `041`.
- Do not use more colours per tile; that reads as `042`.
- Do not smooth or filter the upscale.

## Nearest styles

- `039` CGA four-colour: this style is one soft olive-green hue from dark to pale; `039` is harsh bright cyan, magenta and white on black.
- `041` One-bit dither: this style has four shades and uses the two middle ones as flat fills; `041` has only a dark and a light value, so every midtone is a dense dither pattern.
- `042` NES 8-bit tile: every tile and sprite here shares the same four greens; `042` mixes many vivid colours on one screen, such as red, blue, green and orange on a sky-blue or black background.

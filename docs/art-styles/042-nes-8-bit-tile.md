# NES 8-bit tile

Reference works: Super Mario Bros.; 3D Dot Game Heroes.

## References

- *Super Mario Bros.* (1985), Nintendo R&D4, video game. https://en.wikipedia.org/wiki/Super_Mario_Bros.
- *The Legend of Zelda* (1986), Nintendo R&D4, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda_(video_game)
- *3D Dot Game Heroes* (2009), Silicon Studio, video game. https://en.wikipedia.org/wiki/3D_Dot_Game_Heroes
- *Mega Man 2* (1988), Capcom, video game. https://en.wikipedia.org/wiki/Mega_Man_2
- *Shovel Knight* (2014), Yacht Club Games, video game. https://en.wikipedia.org/wiki/Shovel_Knight

## Visual definition

- **Shape language and proportions:** 16x16 px tiles and sprites. Characters are squat with large heads; scenery repeats the same few tiles. In 3D, each sprite pixel becomes a cube.
- **Line and outline:** Dark outlines or dark background separation around sprites; not on every tile.
- **Shading model:** None. Each sprite uses three colours plus transparency; highlights are single lighter pixels.
- **Palette:** `#000000` `#fcfcfc` `#f83800` `#0058f8` `#00a800` `#fca044` `#5c94fc` `#ac7c00`. Saturated console colours on a flat sky blue or black background; at most 13 to 25 colours on screen.
- **Lighting:** None. In the 3D variant, a flat directional light may shade cube faces.
- **Texture and surface:** Repeating pixel tiles: bricks, blocks, bushes, clouds built from the same shapes.
- **Atmosphere and post-processing:** 256x240 output, integer scaling, optional scanlines.
- **Camera and framing:** Side-scrolling or top-down orthographic; for the 3D cube variant, a tilted view with shallow depth of field.
- **UI and typography:** A black status strip along the top or bottom with no panel art; dialogue boxes are black with a one-tile white or blue border. Text is a chunky 8x8 px bitmap face in white capitals, and counters are fixed-width digits with leading zeros for score, coins and time. Icons are 8 or 16 px sprites such as hearts and coins, in white, red-orange `#f83800` and blue `#0058f8`.
- **VFX and motion:** Effects are sprite animations of two to four frames: a star-burst puff, a sprite that flashes when hit, blinking while invulnerable, score numbers that pop up and rise. Motion is snappy, with two- or three-frame walk cycles, instant turns and fixed jump arcs.

## Fits

- **Genres:** `platformer`, `action-adventure`, `rpg`, `top-down-shooter`, `puzzle`, `sports`
- **Moods:** playful, nostalgic, bright
- **Settings:** cartoon kingdom, overworld fields and dungeons, robot fortress

## Unreal recipe

### Assets

Almost nothing from a realistic pack survives; build the art. For the flat variant, draw 16x16 tiles and sprites by script (Pillow) into atlases, three colours plus transparency each, and import them as Paper2D sprites, tile sets and flipbooks. For the cube variant, a Blender background script extrudes each opaque sprite pixel into a cube and bakes the pixel colour to vertex colour; export one static mesh per animation frame. Reuse the same few tiles for bricks, bushes and clouds, as the console did.

### Materials

`M_NES_Sprite`: Unlit, Masked, one TextureSampleParameter2D, opacity mask from alpha, a `Flash` scalar that lerps to `#fcfcfc` when hit. Textures: Filter Nearest, Mip Gen Settings NoMipmaps, Texture Group 2D Pixels (Unfiltered), compression UserInterface2D, sRGB on. `M_NES_Cube`: Unlit, VertexColor times a face factor from VertexNormalWS (top 1.0, sides 0.8, bottom 0.6), so cube faces step without any light. No normal maps, no roughness.

### Lighting and atmosphere

No lights at all in the flat variant; Lumen, shadows, fog and Sky Atmosphere off. The background is the camera clear colour, `#5c94fc` by day or `#000000` underground. The cube variant may add one Directional Light only to cast a soft shadow on the ground plane; surfaces stay Unlit. Manual exposure with Exposure Compensation 0.

### Post-processing

Orthographic camera. Render at 256x240 through a Scene Capture 2D to a render target shown in UMG with integer scaling and black bars, or use `r.ScreenPercentage` with `r.Upscale.Quality=0` and `r.AntiAliasingMethod=0`. Tone Curve Amount 0 so palette values pass unchanged. One post material at Scene Color After Tonemapping: a Custom node finds the nearest entry in a fixed console palette array (a 64x1 texture) and outputs it, then an optional scanline term darkens every second output row by 15 percent. Bloom, grain, vignette, fringe and Motion Blur Amount 0. The cube variant alone may use Depth of Field at f/2.8 on its tilted view.

### UI and effects

A black strip across the top: Press Start 2P at exact multiples of 8 px, white capitals, no outline. Score, coins and time are zero-padded fixed-width digits. Dialogue boxes are black Border widgets with a one-tile border in `#fcfcfc` or `#0058f8`; hearts and coins are 8 or 16 px sprites in `#f83800`. Effects are flipbooks, not simulated particles: a four-frame star puff, a rising score number, sprite visibility toggled every two frames during invulnerability. In Niagara use a sprite renderer with SubUV animation at 12 fps and no size or colour curves.

## Do / Do not

Do:

- Limit each sprite to three colours.
- Build everything on a 16 px tile grid.
- Reuse tiles and shapes.
- Snap output to a fixed console palette.

Do not:

- Do not restrict to four green or four cyan-magenta colours; that reads as `038` or `039`.
- Do not use 16-pixel textures on large cubes in a perspective world with face shading; that reads as `044`.
- Do not use detailed 16-bit sprites with bloom and depth blur; that reads as `047`.
- Do not use gradients.

## Nearest styles

- `044` Voxel block world: `044` is a perspective world of large cubes with noisy textures, three face shades and many natural greens and browns; this style is flat, unlit tiles and sprites in a few saturated console colours.
- `047` HD-2D pixel diorama: `047` puts detailed sprites in a lit 3D diorama with soft shadows, bloom, depth blur and rich colour; this style has no lighting, no glow and only a few colours.
- `039` CGA four-colour: `039` uses only black, white, cyan and magenta; this style has a wider console palette with reds, greens, blues and browns.

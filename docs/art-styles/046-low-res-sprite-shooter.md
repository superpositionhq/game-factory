# Low-res sprite 2.5D shooter

Reference works: Doom (1993).

## References

- *Doom* (1993), id Software, video game. https://en.wikipedia.org/wiki/Doom_(1993_video_game)
- *Wolfenstein 3D* (1992), id Software, video game. https://en.wikipedia.org/wiki/Wolfenstein_3D
- *Duke Nukem 3D* (1996), 3D Realms, video game. https://en.wikipedia.org/wiki/Duke_Nukem_3D
- *Heretic* (1994), Raven Software, video game. https://en.wikipedia.org/wiki/Heretic_(video_game)

## Visual definition

- **Shape language and proportions:** Levels are extruded 2D floor plans: vertical walls, flat floors and ceilings at different heights, no sloped surfaces. Enemies, items and decorations are flat sprites that always face the camera.
- **Line and outline:** No outline.
- **Shading model:** Sector-based light levels plus distance darkening in discrete steps through a colour map. No dynamic shading on surfaces.
- **Palette:** `#1b1b1b` `#6b4f2f` `#8f8f8f` `#a32020` `#3f5f2f` `#c8a060` `#2f3f6f` `#ff7b00`. A fixed 256-colour palette heavy in browns, greys, reds and greens.
- **Lighting:** Each room has one light level; some sectors flicker or pulse. Darkness increases with distance in visible bands.
- **Texture and surface:** 64x64 px wall and floor textures, unfiltered: tech panels, brick, metal, slime. Sprites are pixel art with 8 view angles.
- **Atmosphere and post-processing:** 320x200 output stretched to 4:3, nearest upscale, colours snapped to the palette.
- **Camera and framing:** First-person at fixed eye height, 90 degree horizontal field of view, no pitch.
- **UI and typography:** A wide status bar across the bottom built from bevelled grey-metal pixel panels, with a face portrait in the centre that reacts to damage, key-card icons, and the weapon sprite held at bottom centre. Health, armour and ammo are chunky pixel digits in red `#a32020` with a dark drop shadow; messages are small red pixel capitals.
- **VFX and motion:** Muzzle flashes are two-frame sprite overlays that brighten the room for an instant; projectiles are glowing sprite fireballs, and blood and bullet puffs are sprites of three or four frames. Damage tints the screen red and a pick-up tints it yellow. Enemies move in few-frame sprite cycles, and the player glides fast with a bobbing weapon.

## Fits

- **Genres:** `fps`, `survival-horror`, `roguelike`, `exploration`
- **Moods:** aggressive, grim, tense
- **Settings:** Mars research base, hell dimension, medieval crypt, seedy city streets

## Unreal recipe

### Assets

Levels are extruded floor plans: generate them by script from a 2D sector map (Geometry Script), vertical walls, flat floors and ceilings at varied heights, no slopes. Each sector becomes its own mesh section so it can carry a light level. Wall and floor textures are 64x64 px; make them by downsampling store-pack albedo maps with Pillow (box filter, then palette snap) and discard normal, roughness and metallic maps. Enemies and pickups are sprites: render a rigged store character from 8 yaw angles to small frames in an editor script, palette-snap them, and pack flipbook atlases.

### Materials

`M_Sector`: Unlit. Texture sample (Filter Nearest, NoMipmaps) multiplied by a stepped light term: `floor((SectorLight - PixelDepth * Falloff) * 32) / 32`, clamped, where `SectorLight` comes from Custom Primitive Data and can be pulsed from C++ for flicker. `M_Sprite`: Unlit, Masked, same light term, with a Custom node that rotates the quad to face the camera about the vertical axis only and selects one of 8 atlas columns from the angle between view and actor forward. Sprites carry no outline.

### Lighting and atmosphere

No light actors, no Lumen, no shadows, no fog actor; darkness with distance is the banded term in the materials. A muzzle flash raises every `SectorLight` in the room by a fixed step for two frames. Sky is a flat Unlit texture mapped to view yaw only. Manual exposure.

### Post-processing

Target 320x200 stretched to 4:3: render through a Scene Capture 2D into a 320x200 render target displayed at 4:3 in UMG with nearest sampling, or use low `r.ScreenPercentage` with `r.Upscale.Quality=0` and pillarbox bars. `r.AntiAliasingMethod=0`. Tone Curve Amount 0. A post material at Scene Color After Tonemapping maps each pixel through a 256-colour LUT texture built from the brown, grey, red and green palette. Damage and pickup tints are a `ScreenTint` vector in the same material (red `#a32020`, or yellow), fading over 0.3 s. Bloom, grain, vignette, fringe, depth of field and Motion Blur Amount 0. Camera: 90 degree horizontal field of view, pitch locked in C++.

### UI and effects

A full-width status bar at the bottom made from bevelled grey pixel panels (`#8f8f8f`, Box brushes scaled by integers), with a flipbook face portrait in the centre that changes with health, and key-card icons. Health, armour and ammo are chunky digits in Silkscreen Bold, `#a32020` with a one-pixel dark shadow. The weapon is a UMG sprite at bottom centre that bobs with movement. Niagara is limited to sprite flipbooks: fireballs in `#ff7b00`, blood and bullet puffs of three or four frames at 10 fps, no alpha fade and no soft particles.

## Do / Do not

Do:

- Keep walls vertical and floors flat.
- Use camera-facing sprites for all characters and items.
- Darken with distance in discrete steps.
- Snap output to a fixed 256-colour palette.

Do not:

- Do not use polygonal characters and vertex wobble; that reads as `036`.
- Do not use sprites in a tilt-shift diorama with bloom; that reads as `047`.
- Do not use cube voxels; that reads as `044`.
- Do not allow camera pitch or sloped floors.

## Nearest styles

- `036` PS1 low-poly wobble: `036` has polygonal characters, wobbling vertices, fewer colours and soft light blended across each polygon; this style has flat camera-facing sprites, steady walls and light that drops in visible steps.
- `047` HD-2D pixel diorama: `047` is brighter, with dark-outlined sprites, smooth lighting, bloom and depth blur; this style is dark, with sprites that have no outline, stepped light and no glow.
- `044` Voxel block world: `044` is an open world of cubes in bright daylight; this style is dark interiors made of vertical walls and flat floors.

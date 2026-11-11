# ASCII terminal glyph

Reference works: Rogue; Dwarf Fortress.

## References

- *Rogue* (1980), Michael Toy and Glenn Wichman, video game. https://en.wikipedia.org/wiki/Rogue_(video_game)
- *NetHack* (1987), The NetHack DevTeam, video game. https://en.wikipedia.org/wiki/NetHack
- *Dwarf Fortress* (2006), Bay 12 Games, video game. https://en.wikipedia.org/wiki/Dwarf_Fortress
- *Stone Story RPG* (2019), Martian Rex, video game. https://en.wikipedia.org/wiki/Stone_Story_RPG

## Visual definition

- **Shape language and proportions:** The image is a grid of text characters. Forms appear only through which glyph occupies each cell; resolution is about 80 to 160 columns.
- **Line and outline:** No outline as such. Edges can be suggested with directional glyphs: slash, backslash, bar, underscore.
- **Shading model:** Brightness maps to glyph density through a fixed ramp (space, dot, colon, dash, equals, plus, star, hash, percent, at-sign).
- **Palette:** `#000000` `#33ff33` `#00aa00` `#ffb000` `#c0c0c0` `#ffffff`. One phosphor colour (green or amber) on black, or the 16-colour terminal set used sparingly.
- **Lighting:** A simple strong light so the ramp has range.
- **Texture and surface:** The glyph grid itself. Every cell is high-frequency.
- **Atmosphere and post-processing:** Fixed monospace cell grid, optional CRT glow and scanlines.
- **Camera and framing:** Any; static or slow, since cells flicker when the image changes.
- **UI and typography:** Frames are built from box-drawing characters, menus are text lists with the selected row shown in inverted cells, and icons are single glyphs: an at-sign for the player, letters for monsters, punctuation for items. All text uses the same monospace terminal face as the scene, with stats on a status line as plain digits. The UI stays in the phosphor colour, with amber `#ffb000` or white for alerts.
- **VFX and motion:** Effects are glyph swaps: asterisks for an explosion, a run of dashes or slashes for a projectile, a cell that flashes inverted when hit. Movement goes cell by cell in discrete steps with no in-between frames.

## Fits

- **Genres:** `roguelike`, `rpg`, `simulation`, `strategy`, `puzzle`, `survival-craft`
- **Moods:** austere, cryptic, nostalgic
- **Settings:** dungeon depths, underground fortress, mainframe terminal

## Unreal recipe

### Assets

Any geometry works because the viewer never sees it directly; choose packs with strong, simple silhouettes (dungeon walls, pillars, large props) and ignore their textures. Fine detail smaller than one cell is lost, so remove clutter. What must be made by script is the glyph atlas: render the ten ramp glyphs (space . : - = + * # % @) plus slash, backslash, bar and underscore from IBM Plex Mono into one row of cells with Pillow, white on black, and import it Filter Nearest with NoMipmaps.

### Materials

Scene materials are one Default Lit master with grey Base Color, Roughness 1 and Specular 0, so brightness depends on light only. Gameplay entities that must read as fixed letters (player at-sign, monsters) write a CustomDepth Stencil Value equal to their glyph index.

### Lighting and atmosphere

Lumen off. One strong Directional or Spot Light with Virtual Shadow Maps and a low Sky Light, tuned so the scene spans the full ramp from empty cell to at-sign. No fog or atmosphere; empty space is `#000000`. Manual exposure, since auto exposure would make cells flicker.

### Post-processing

`r.AntiAliasingMethod=0`. One post material, `PP_Glyph`, at Scene Color After Tonemapping:

1. Cell UV: floor ScreenPosition to a grid of 120 columns, cell aspect 1:2.
2. Sample PostProcessInput0 luminance at the cell centre only, so nothing blends across cell borders.
3. Pick a ramp index, `floor(lum * 10)`, or the stencil glyph when CustomStencil is non-zero.
4. Where a Sobel on SceneDepth at the cell centre is strong, replace the ramp glyph with the slash, backslash, bar or underscore that matches the edge direction.
5. Sample the atlas with the in-cell fractional UV and multiply by the phosphor colour `#33ff33` (dim cells `#00aa00`).

A second material after it adds faint scanlines. Bloom Intensity about 0.4 with a low threshold gives the CRT glow; Vignette 0.3; grain, fringe, depth of field and Motion Blur Amount 0. Keep the camera slow or locked.

### UI and effects

UMG text is IBM Plex Mono or VT323 at the same cell size as the scene, phosphor green on black. Frames are box-drawing characters typed into Text Blocks, not image borders. The selected menu row is a green Border with black text. Alerts switch to `#ffb000` or `#ffffff`. Stats sit on one status line as plain digits. Effects are done in C++ and UMG, not sprites: an explosion writes asterisks into neighbouring cells for 0.2 s, a projectile is a run of dashes moving one cell per tick, and a hit inverts its cell for one tick. If Niagara is used, particles write a stencil glyph index and stay cell-sized.

## Do / Do not

Do:

- Map brightness to a density-sorted glyph ramp.
- Keep a fixed monospace cell grid.
- Use one phosphor colour on black.
- Use directional glyphs on strong edges.

Do not:

- Do not use dots or pixels in place of glyphs; that reads as `041`.
- Do not draw continuous vector lines; that reads as `040`.
- Do not use cells so small that glyphs cannot be read.
- Do not anti-alias the scene across cell borders.

## Nearest styles

- `040` Vector display glow: `040` draws clean continuous glowing lines on empty black; this style fills the screen with a busy grid of text characters.
- `041` One-bit dither: `041` is a neutral two-value pixel dither; this style builds tone from readable characters in phosphor green or amber, with several density steps.
- `088` Neon grid cyberspace: `088` has smooth dark surfaces crossed by neon grid lines; this style has no smooth surfaces, because every cell holds a glyph.

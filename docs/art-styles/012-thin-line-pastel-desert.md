# Thin-line pastel desert

Reference works: Sable; Moebius.

## References

- *Sable* (2021), Shedworks, video game. https://en.wikipedia.org/wiki/Sable_(video_game)
- *Arzach* (1975), Moebius (Jean Giraud), comic. https://en.wikipedia.org/wiki/Arzach
- *The Incal* (1980), Alejandro Jodorowsky and Moebius, comic series. https://en.wikipedia.org/wiki/The_Incal
- *Fantastic Planet* (1973), Rene Laloux, animated film. https://en.wikipedia.org/wiki/Fantastic_Planet
- *Rollerdrome* (2022), Roll7, video game. https://en.wikipedia.org/wiki/Rollerdrome

## Visual definition

- **Shape language and proportions:** Vast empty landscapes with eroded rock arches, bones and ruined machines. Vehicles and architecture are organic, with long curves and thin struts.
- **Line and outline:** Thin dark line (1 to 1.5 px) on silhouettes and creases; in open areas lines are sparse. Contour lines on dunes and rock strata are drawn as fine parallel strokes.
- **Shading model:** Flat colour with at most one flat shadow tone. Shadow is a hard-edged tint, not black.
- **Palette:** `#2b2623` `#f3d9b1` `#e8a87c` `#c38d9e` `#85cdca` `#f6f1e7` `#d96c4f`. Pale sand, peach, dusty rose and mint, with a small strong accent. Large areas of near-white.
- **Lighting:** High desert sun; time of day changes the whole palette at once.
- **Texture and surface:** None in colour. Fine line marks only.
- **Atmosphere and post-processing:** None. Colour areas are perfectly flat; distance is shown by lighter line and colour.
- **Camera and framing:** Very wide shots with a small subject; 24 to 35 mm equivalent.
- **UI and typography:** Minimal UI with no filled panels: thin dark line frames and simple line-drawn glyph icons placed straight on the scene. Text is a light, widely spaced geometric sans in the dark line colour; counters are small thin numerals. Selected items take the orange-red accent, other elements stay sand or near-white.
- **VFX and motion:** Dust trails, smoke and wind are flat pale shapes with a thin outline that break into a few dots and fade. Impacts are a short ring of radiating line strokes. Characters and vehicles animate on twos with calm, gliding movement and long holds.

## Fits

- **Genres:** `exploration`, `racing`, `action-adventure`, `puzzle`, `sports`, `platformer`
- **Moods:** calm, lonely, dreamlike
- **Settings:** desert wasteland, alien planet ruins, nomad camp, crashed starship

## Unreal recipe

### Assets

The world is mostly empty ground, so build it: Geometry Script or Blender dunes and mesas with long smooth curves, eroded arches, giant bones, and wrecked machines made of thin struts and organic hulls. Store rock packs can be used after decimating to smooth large forms and deleting all textures. Draw strata and dune contours as texture: a script writes fine parallel strokes (1 px dark lines on transparent) along height bands into a tiling mask.

### Materials

`M_PastelFlat`, Unlit. Colour parameters come from a Material Parameter Collection holding the whole palette (sand `#f3d9b1`, peach `#e8a87c`, rose `#c38d9e`, mint `#85cdca`, near-white `#f6f1e7`), so C++ can blend every colour at once for time of day. One optional shadow tone: `Step` on N·L with an MPC sun vector lerps to a hard-edged tint about 15 percent darker and cooler, never black. The contour mask is projected with WorldAlignedTexture along world Z and drawn in the line colour `#2b2623`. Distance fade is part of the material: lerp the fill toward near-white by PixelDepth, as flat steps (Floor on the depth factor), not a smooth gradient.

### Lighting and atmosphere

No lights are required. Lumen, shadows, Sky Atmosphere and fog off; a height fog gradient would break the flat fills. Sky is a single flat colour dome driven by the same MPC.

### Post-processing

Tone Curve Amount 0, Manual exposure. `PP_ThinLine` at Scene Color After Tonemapping detects edges on SceneDepth and WorldNormal with a high threshold so only silhouettes and firm creases draw. Width is 1 to 1.5 px (a one-pixel kernel with bilinear half-offset), and line opacity falls with SceneDepth so far lines are lighter; beyond a set distance only silhouettes remain. Everything else is off: bloom, grain, vignette, fringe, ambient occlusion, depth of field, Motion Blur Amount 0. TSR at 100 percent keeps the thin line stable; raise `r.ScreenPercentage` above 100 if lines flicker.

### UI and effects

No filled panels. Frames are 1 px `#2b2623` outlines (Border brush with transparent fill) and icons are line glyphs placed directly over the scene. Text is Josefin Sans Light or Jost Light with wide letter spacing; counters are small thin numerals. The selected item switches to `#d96c4f`. Niagara: dust trails are flat pale Masked shapes with a thin edge that split into 3 to 5 dots and fade over 1.5 s; an impact is a ring of 8 to 12 short radial line sprites lasting 0.25 s. Characters and vehicles update pose on twos and glide with long holds.

## Do / Do not

Do:

- Keep lines thin and lighter with distance.
- Use large empty areas of one flat colour.
- Draw strata and dune contours as fine parallel lines.
- Change the whole palette together for mood.

Do not:

- Do not thicken lines or switch to strong primary colours; that reads as `011`.
- Do not add smooth sand gradients and glitter; that reads as `061`.
- Do not add watercolour texture and soft edges; that reads as `025`.
- Do not shade with more than one shadow tone.

## Nearest styles

- `011` Clear-line adventure comic: `011` uses clear red, blue and yellow flats with a heavier line of one weight on every edge; this style uses pale sand and pastel tints with thin lines that thin out in open areas.
- `025` Watercolour wash minimal: `025` has soft bleeding edges, paper grain and almost no drawn line; this style has perfectly flat colour inside thin ink lines.
- `061` Soft-gradient minimal desert: `061` has no lines and shades its dunes with smooth gradients; this style draws every form in line and fills it with flat colour.

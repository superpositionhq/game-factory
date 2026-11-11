# Selective-colour ink noir

Reference works: Sin City.

## References

- *Sin City* (2005), Robert Rodriguez and Frank Miller, live-action film. https://en.wikipedia.org/wiki/Sin_City_(film)
- *Sin City (comics)* (1991), Frank Miller (Dark Horse Comics), comic series. https://en.wikipedia.org/wiki/Sin_City
- *MadWorld* (2009), PlatinumGames, video game. https://en.wikipedia.org/wiki/MadWorld
- *Schindler's List* (1993), Steven Spielberg, live-action film. https://en.wikipedia.org/wiki/Schindler's_List

## Visual definition

- **Shape language and proportions:** Realistic figures and city settings reduced to stark graphic shapes: silhouettes with white rim shapes, rain as white streaks, blinds and bricks as white lines on black.
- **Line and outline:** Where a black form meets a black ground, a white keyline or rim separates them; where a white form meets white, a black line does. Lines are bold.
- **Shading model:** Two values only: pure black and pure white, with no greys. Shadow shapes are large and designed.
- **Palette:** `#000000` `#ffffff` `#c40000` `#f2d21b` `#1a1a1a`. Black and white plus one small area of a single saturated colour (red lips or dress, yellow skin, blue eyes).
- **Lighting:** Extreme hard side or back light; negative-space lighting where figures are white outlines on black.
- **Texture and surface:** None in tone. Rain streaks, brick lines and spatter are solid white or black marks.
- **Atmosphere and post-processing:** Hard threshold; selective colour mask; optional slight glow on white.
- **Camera and framing:** Dramatic low and high angles, strong perspective, silhouettes against light.
- **UI and typography:** Solid black panels with bold white borders, or the reverse, like comic caption boxes; icons are stark two-value silhouettes. Text is heavy hand-inked comic block capitals in white `#ffffff` on black; the one key colour, red `#c40000` or yellow `#f2d21b`, marks health, damage numbers and the selected item.
- **VFX and motion:** Blood, spatter and muzzle flashes are flat ink shapes in solid white or the one key colour; rain is white streaks, and a hit flips the frame to its negative for an instant. Animation is punchy, with strong held poses and fast smears between them.

## Fits

- **Genres:** `hack-and-slash`, `detective-mystery`, `third-person-shooter`, `fighting`, `stealth`, `action-adventure`
- **Moods:** brutal, lurid, hardboiled
- **Settings:** corrupt city at night, rain-soaked alleys, docks, seedy bar

## Unreal recipe

### Assets

Realistic characters and city kits with strong silhouettes: fire escapes, brick walls, blinds, coats, cars. Textures are discarded except for a few converted to line art by script: threshold brick and plank albedos in Pillow to pure white mortar or seam lines on black, saved as single-channel masks. Build rain as long thin quads and add large planar shadow-caster cards off screen to design the black shapes.

### Materials

Two paths. Scene meshes keep Default Lit with Base Colour set to flat 0.5 grey, roughness 1, no normal map, so the lit result is pure light information for the threshold. Line masks from the converted textures go to Emissive with a parameter that the post pass reads as forced white. The selective-colour object (one per scene: lips, a dress, a sign) uses an Unlit material in `#c40000` or `#f2d21b`, with Render CustomDepth Pass on and stencil value 1. Characters write stencil 2 for rim keylines.

### Lighting and atmosphere

Lumen off, Sky Light off, no fog: bounce and haze create greys. One Directional or Spot Light per scene from the side or behind, Source Angle 0, Virtual Shadow Maps on for hard shadows. Add a rim Spot Light on Lighting Channel 1 for characters only, so a black figure on black ground gets a white edge shape. Manual exposure keeps the threshold stable.

### Post-processing

A single post material at Replacing the Tonemapper does the look in this order:

1. Luminance of PostProcessInput0, Step at a threshold parameter (about 0.18): output `#000000` or `#ffffff`, no SmoothStep wider than one pixel.
2. Keylines: Sobel on SceneDepth and WorldNormal, 3 px wide; the line takes the inverse of the thresholded value beneath it, giving white lines on black and black on white.
3. Where CustomStencil equals 1, pass the Unlit colour through untouched.

Then, in C++, a hit sets a scalar that inverts the frame for 0.05 s. Bloom Intensity 0.2 for a slight glow on white. Film Grain 0, vignette 0, fringe 0, depth of field off, Motion Blur Amount 0. Use FXAA; if edges shimmer, move the material to Scene Color After Tonemapping.

### UI and effects

Caption boxes: Border brushes, solid `#000000` with a 4 px white outline, or reversed for selection. Text in Bangers or Permanent Marker capitals, white. Health, damage numbers and the selected item use the scene's key colour and nothing else does.

Niagara sprites are opaque masked shapes: blood and spatter as flat blobs in white or the key colour (stencil 1), muzzle flash as a jagged white star for 2 frames, rain as white streak quads at stencil-forced white.

## Do / Do not

Do:

- Threshold to pure black and white.
- Keep exactly one small selective colour.
- Use white keylines on black forms.
- Design large shadow shapes.

Do not:

- Do not keep grey gradients and film grain; that reads as `068`.
- Do not fill colour areas with muted flats; that reads as `010`.
- Do not use dot screentone for greys; that reads as `020`.
- Do not flood the frame with red; that reads as `008`.

## Nearest styles

- `010` Heavy-black gothic comic: `010` also has heavy black shadows, but fills the lit areas with muted flat colours; this style leaves them pure white and allows one small spot of strong colour.
- `020` Manga screentone monochrome: `020` is mostly white paper with fine ink lines and dot screentone for greys; this style is mostly black, with solid shapes and no dot tones.
- `068` Film noir hard light: `068` is photographic black and white with smooth grey gradients and film grain; this style has no greys, only solid black and white shapes with keylines.

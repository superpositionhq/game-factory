# Rim-lit illustrative caricature

Reference works: Team Fortress 2.

## References

- *Team Fortress 2* (2007), Valve, video game. https://en.wikipedia.org/wiki/Team_Fortress_2
- *Freedom from Want* (1943), Norman Rockwell, oil painting. https://en.wikipedia.org/wiki/Freedom_from_Want
- *Evil Genius* (2004), Elixir Studios, video game. https://en.wikipedia.org/wiki/Evil_Genius_(video_game)

## Visual definition

- **Shape language and proportions:** Caricatured adult proportions: broad shoulders, small feet, distinct silhouette for each character class. Props are chunky with simplified, slightly swollen forms.
- **Line and outline:** No outline. Edges are defined by a strong rim light.
- **Shading model:** Smooth but compressed: a warm-to-cool ramp where the terminator is tinted red-brown and shadows stay mid-value. Wide, soft specular.
- **Palette:** `#b8383b` `#5885a2` `#e7b53b` `#7d4071` `#c5b9a0` `#3c352f` `#f0e0c0`. Muted team red and team blue on warm neutral backgrounds (tan, khaki, grey-brown). Saturation is concentrated on characters.
- **Lighting:** Warm key, cool ambient, and a bright rim light from behind on both sides of the form.
- **Texture and surface:** Hand-painted, low-contrast: broad brush marks, soft wear on edges, no photographic detail.
- **Atmosphere and post-processing:** Mild ambient occlusion and a soft vignette. No bloom.
- **Camera and framing:** Medium shots at chest height, 40 to 50 mm equivalent.
- **UI and typography:** Flat tan and khaki panels with a team-red or team-blue header bar, like mid-century print advertising and stencilled crate labels. Type is a bold grotesque sans in cream (`#f0e0c0`) with stencil capitals for headings. Health and ammo are large plain numerals; damage numbers are small bold digits that float up.
- **VFX and motion:** Explosions and smoke are soft painted puffs with warm cores, a few simple spark streaks and no glow. Animation is broad character acting: strong anticipation, exaggerated but weighty motion and a distinct pose silhouette for each character.

## Fits

- **Genres:** `fps`, `tower-defense`, `strategy`, `stealth`, `third-person-shooter`
- **Moods:** comedic, mischievous, nostalgic
- **Settings:** industrial desert outpost, 1960s spy base, farm and rail yard

## Unreal recipe

### Assets

Use chunky, slightly swollen props with generous bevels. Realistic packs need their bevels widened (a Blender bevel modifier pass by script) and their textures repainted: blur base colour to broad strokes, cut contrast by half, shift backgrounds toward tan and grey-brown (`#c5b9a0`, `#3c352f`), and keep saturated red or blue for characters and team objects only. Keep normal maps for large forms but blur them; remove micro-detail normals.

### Materials

`M_Illustrative` stays Default Lit, with Roughness fixed between 0.6 and 0.75 for a wide soft specular and Metallic 0 almost everywhere. Two additions go into Emissive Color. First, a terminator tint: a Material Parameter Collection supplies the key light direction, and a narrow bell curve around N·L = 0 adds red-brown (`#8a3a2a` at low strength). Second, a rim term: `pow(1 - dot(N, V), 4)` multiplied by a parameter colour in cream, masked so it appears on both side edges but fades on faces pointing at the camera or down. Character instances set rim strength 1, scenery 0.2. No outline and no banding anywhere.

### Lighting and atmosphere

Lumen GI and reflections on. Directional Light warm (about 4500 K), Source Angle 2. Sky Light tinted cool (`#5885a2`) at an intensity that keeps shadow sides at mid value. Two extra Directional Lights or wide Spot Lights from behind left and behind right, on a Lighting Channel shared only with characters, cast no shadows and reinforce the rim. Only a faint Exponential Height Fog. Virtual Shadow Maps with contact shadows on.

### Post-processing

Ambient Occlusion Intensity 0.5 with a wide Radius. Vignette Intensity 0.35. Bloom Intensity 0. Filmic tone curve kept at default, Global Saturation 0.9, Shadows Gain raised slightly so no shadow goes below mid-dark. No grain, no fringe, Motion Blur Amount 0, depth of field off in play. TSR anti-aliasing.

### UI and effects

Panels are flat Box brushes in tan or khaki with a team-red (`#b8383b`) or team-blue (`#5885a2`) header strip and square corners. Headings use a stencil face (Saira Stencil One or Stardos Stencil), body text Archivo Black or Oswald in `#f0e0c0`. Health and ammo are large plain numerals; damage numbers are small bold digits floating up for 0.8 s. Niagara: explosions are soft painted puff flipbooks with warm cores, translucent Lit sprites so they take scene light, with 5 to 10 simple spark streaks. Emissive stays low so nothing glows.

## Do / Do not

Do:

- Tint the terminator warm red-brown.
- Add a clear rim light on both edges of each form.
- Keep background saturation lower than character saturation.
- Bevel edges generously.

Do not:

- Do not add ink outlines or hard bands; that reads as `001` or `015`.
- Do not raise saturation and add emissive trim; that reads as `013`.
- Do not paint high-contrast chunky detail into textures; that reads as `023`.
- Do not use neutral grey shadows.

## Nearest styles

- `013` Stylised hero PBR: this style keeps colours muted, with warm neutral backgrounds, strong colour only on characters and no glowing trim; `013` has vivid colour across the whole scene, more hues and emissive accents.
- `023` Chunky hand-painted fantasy: this style keeps textures as quiet broad brush marks and lets the rim light define form; `023` paints bright edge highlights, dark seams and bold detail into the textures.
- `048` Claymation: this style has clean painted surfaces, a subdued palette and a strong rim light; `048` is brighter and shows fingerprints, dents and tool marks on every surface.

# Chunky hand-painted fantasy

Reference works: World of Warcraft.

## References

- *World of Warcraft* (2004), Blizzard Entertainment, video game. https://en.wikipedia.org/wiki/World_of_Warcraft
- *Warcraft III: Reign of Chaos* (2002), Blizzard Entertainment, video game. https://en.wikipedia.org/wiki/Warcraft_III:_Reign_of_Chaos
- *League of Legends* (2009), Riot Games, video game. https://en.wikipedia.org/wiki/League_of_Legends
- *Torchlight II* (2012), Runic Games, video game. https://en.wikipedia.org/wiki/Torchlight_II
- *Dota 2* (2013), Valve, video game. https://en.wikipedia.org/wiki/Dota_2

## Visual definition

- **Shape language and proportions:** Chunky and exaggerated: oversized shoulders, hands, weapons and roof beams; thick edges; bent and tapered silhouettes. Low to mid polygon counts.
- **Line and outline:** No outline. Dark painted crevices act as line.
- **Shading model:** Light and shadow are mostly painted into the albedo; real-time lighting adds a soft smooth gradient on top.
- **Palette:** `#7a4b2a` `#c8a15a` `#4f7a3a` `#3b5fa8` `#8b2f8f` `#e8d8a8` `#2a2333`. Warm wood and gold against saturated blue, purple and green. Each zone has a strong colour identity.
- **Lighting:** Soft, even daylight or a coloured zone ambient; no hard contrast from real-time lights.
- **Texture and surface:** Hand-painted with visible brush strokes: bright chiselled edge highlights, dark seams, gradients from top to bottom, painted metal shine.
- **Atmosphere and post-processing:** Light bloom, zone-coloured distance fog.
- **Camera and framing:** Third-person from above shoulder height or a top-down 55 degree view.
- **UI and typography:** Heavy ornate frames of gold metal, carved stone and wood, with painted square ability icons in bevelled borders. Titles use a chunky fantasy serif and values a bold sans; damage numbers are large floating yellow and white digits with a dark outline. UI colours are gold `#c8a15a` and parchment `#e8d8a8` on dark purple-black `#2a2333`.
- **VFX and motion:** Bold, readable spell effects in saturated blue, purple and green: big soft glows, painted swirls and large spark shapes. Animation is exaggerated, with wide anticipation, big weapon arcs and slight squash and stretch.

## Fits

- **Genres:** `rpg`, `strategy`, `hack-and-slash`, `tower-defense`, `action-adventure`, `roguelike`
- **Moods:** heroic, adventurous, warm
- **Settings:** high-fantasy kingdoms, orc war camps, enchanted forests, dungeon ruins

## Unreal recipe

### Assets

Use chunky stylised fantasy packs with thick edges and oversized hands, weapons and beams. A realistic pack can be converted: scale shoulders, hands and weapon bones up by 15 to 30 percent, add a bevel and inflate thin parts in Blender, then bake its normal map, ambient occlusion and a top-down gradient into a new albedo so the relief becomes paint. After baking, remove the normal, roughness and metallic maps. Keep albedo at 512 to 1024 px, filtered, never nearest. Crates, banners and roof beams are quick to build from scratch with bent, tapered profiles.

### Materials

`M_HandPainted`, Default Lit, diffuse-only: BaseColor from the painted albedo, Roughness constant 1, Specular 0, Metallic 0, no normal map. Shared material functions add the painted look by script-driven parameters:

- `MF_EdgeHighlight`: a curvature mask baked to vertex colour brightens chiselled edges by 20 to 30 percent.
- `MF_TopGradient`: local Z position lerps from a darker cool base to a lighter warm top.
- `MF_ZoneTint`: a Material Parameter Collection colour multiplies everything by the zone hue.

Metal shine is painted into the albedo as a fixed streak; it does not move with the camera. Each asset's instance sets gradient strength and tint.

### Lighting and atmosphere

Light must stay soft and even. One Directional Light at intensity 3 to 4 lux with Source Angle 5 for blurred shadow edges, and a strong Sky Light (intensity 1.5 to 2) with a zone-coloured Lower Hemisphere. Lumen GI on; `r.ReflectionMethod=0`. Virtual Shadow Maps on. Exponential Height Fog in the zone colour (`#3b5fa8` frost zone, `#8b2f8f` corrupted zone, `#4f7a3a` forest) with Start Distance beyond the play area. Manual exposure.

### Post-processing

No stylising post material: the paint lives in the textures. Bloom Intensity 0.3, Threshold 1. Saturation 1.15 and Contrast 1.05 globally. Ambient Occlusion Intensity 0.3 only, since crevices are already painted dark. Vignette 0.2, grain 0, fringe 0, Motion Blur Amount 0, no depth of field. TSR anti-aliasing.

### UI and effects

Frames are 9-slice Box brushes painted as gold metal and carved stone; ability icons are square paintings in bevelled borders. Titles in Cinzel bold, values in Archivo Black. Floating damage numbers are large `#e8d8a8` and yellow digits with a 2 px `#2a2333` font outline, popping up and fading over 0.8 s. Niagara spells are large and readable: soft additive glow sprites, a painted swirl flipbook on a rotating mesh ring, and 10 to 20 big star-shaped sparks in saturated blue, purple or green, each cast lasting about 1 s.

## Do / Do not

Do:

- Paint light, shadow and edge highlights into the albedo.
- Exaggerate thickness and silhouette.
- Use diffuse-only materials.
- Give each zone a strong colour identity.

Do not:

- Do not rely on normal maps and PBR response; that reads as `013`.
- Do not mute and compress the palette with rim light; that reads as `005`.
- Do not use nearest-filtered low-resolution pixel textures; that reads as `036` or `044`.
- Do not add ink outlines.

## Nearest styles

- `013` Stylised hero PBR: surfaces here are matte and carry painted brush strokes, edge highlights and dark seams; `013` has clean smooth surfaces with realistic material shine and little painted detail.
- `005` Rim-lit illustrative caricature: colours here are strong and every zone is saturated, with busy painted texture; `005` is muted on neutral backgrounds, with low-contrast brush marks and a bright rim light on every form.
- `024` Brush-textured 3D drama: this style is bright and evenly lit with soft smooth light; `024` is dark and dramatic, with light broken into stepped painted planes.

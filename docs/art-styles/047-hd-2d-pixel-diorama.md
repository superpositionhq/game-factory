# HD-2D pixel diorama

Reference works: Octopath Traveler.

## References

- *Octopath Traveler* (2018), Square Enix and Acquire, video game. https://en.wikipedia.org/wiki/Octopath_Traveler
- *Triangle Strategy* (2022), Square Enix and Artdink, video game. https://en.wikipedia.org/wiki/Triangle_Strategy
- *Dragon Quest III HD-2D Remake* (2024), Square Enix and Artdink, video game. https://en.wikipedia.org/wiki/Dragon_Quest_III
- *Live A Live* (2022), Square Enix and Historia, video game. https://en.wikipedia.org/wiki/Live_A_Live
- *Final Fantasy VI* (1994), Square, video game. https://en.wikipedia.org/wiki/Final_Fantasy_VI

## Visual definition

- **Shape language and proportions:** 16-bit style pixel-art characters (about 24x40 px) as flat sprites standing in a 3D diorama built from blocky geometry covered with pixel-art textures.
- **Line and outline:** Sprites have a dark one-pixel outline. Environment has none.
- **Shading model:** Environment is lit with modern smooth lighting, shadows and point lights; sprites are evenly lit and receive scene tint.
- **Palette:** `#2b2a33` `#6b5b45` `#a8895c` `#3f6b4f` `#4a6fa5` `#e8c170` `#c44d3a` `#f4e9c9`. Earthy mid-tones with warm lamp light and cool shadow; richer than true 16-bit palettes.
- **Lighting:** Dramatic point lights (torches, windows), light shafts, bright specular sparkle on water.
- **Texture and surface:** Pixel-art textures with visible square texels on walls and ground; sprites unfiltered.
- **Atmosphere and post-processing:** Strong tilt-shift depth of field, bloom, vignette, particles (dust, embers, snow).
- **Camera and framing:** Fixed side-on or slightly raised view with a long lens and a narrow focus band.
- **UI and typography:** Dark semi-transparent panels with thin gold filigree borders and parchment-toned `#f4e9c9` windows; item icons are small pixel-art pictures. Headings and dialogue use an elegant book serif drawn crisp at full resolution, not pixelated. Damage numbers are large bold serif digits in white, with warm gold `#e8c170` for critical hits and red `#c44d3a` for weakness hits.
- **VFX and motion:** Spells combine pixel-sprite flares with modern glow: fire that blooms and lights the set, sparkling particles, light shafts, drifting embers. Sprites animate in a few snappy frames with held poses and quick hit flashes, while the camera drifts and zooms slowly.

## Fits

- **Genres:** `rpg`, `strategy`, `tower-defense`, `exploration`, `roguelike`
- **Moods:** nostalgic, wistful, epic
- **Settings:** medieval kingdoms, torch-lit towns, snowy mountain villages, castle battlefields

## Unreal recipe

### Assets

Two asset classes. The set is blocky 3D: kitbash simple store-pack architecture or build walls, stairs and roofs by script, then repaint every texture as pixel art by downsampling albedo to roughly 16 texels per metre with Pillow and reducing colours toward the earthy palette. Keep low-strength normal maps derived from the pixel texture so torches catch block edges. Characters are sprites of about 24x40 px with a one-pixel outline in `#2b2a33`, drawn or rendered to flipbooks by script. Never use polygonal characters.

### Materials

`M_HD2D_Env`: Default Lit, pixel albedo with Filter Nearest and NoMipmaps, Roughness 0.7 to 0.9, the derived normal map. Water is Single Layer Water or a Default Lit instance with low roughness and a panning normal for bright specular sparkle. `M_HD2D_Sprite`: Default Lit, Masked, Two Sided, with the pixel normal forced to face the camera so sprites light evenly yet still take torch colour and cast shadows; add 20 percent of the texture to Emissive so faces never go black. Billboard about the vertical axis with World Position Offset.

### Lighting and atmosphere

Lumen GI and reflections on. A low-intensity Directional Light for moon or dusk, then 4 to 10 warm Point Lights (`#e8c170`) at torches and windows with Virtual Shadow Maps. Exponential Height Fog with Volumetric Fog on and raised Volumetric Scattering Intensity on window Spot Lights for shafts. Sky Light at low intensity with a cool tint. Auto Exposure limited to a narrow Min/Max EV100 range.

### Post-processing

Full resolution with TSR (`r.AntiAliasingMethod=4`); pixel art lives in the textures, not the frame. Depth of Field with a long lens (85 to 135 mm), low f-stop and focal distance on the party plane, so foreground and background fall into blur as a narrow focus band. Bloom Intensity 0.8 to 1.2, Vignette 0.5, slight Film Grain 0.1, warm Gain in highlights and blue Offset in shadows. Motion Blur Amount 0. No pixelation or palette post material; that would turn it into a true low-resolution look.

### UI and effects

Panels are dark translucent Borders (`#2b2a33` at 80 percent) with a thin gold filigree 9-slice frame; message windows use parchment `#f4e9c9`. Text is Cormorant or EB Garamond at full resolution, never pixelated. Damage numbers are large bold serif digits, white, `#e8c170` for criticals and `#c44d3a` for weakness hits, popping with a quick scale. Niagara mixes pixel flipbook flares (SubUV, 8 to 12 fps) with modern additive glow sprites and a light renderer so spells light the set; ambient emitters add 30 to 60 slow dust motes, embers or snow with lifetimes of 3 to 6 s.

## Do / Do not

Do:

- Combine flat pixel sprites with lit 3D blocks.
- Blur foreground and background with tilt-shift.
- Add bloom, light shafts and particles.
- Keep all textures unfiltered.

Do not:

- Do not render at low resolution without modern lighting; that reads as `042` or `046`.
- Do not replace pixel art with smooth glossy toys; that reads as `057`.
- Do not use polygonal characters; that reads as `036`.
- Do not filter textures.

## Nearest styles

- `057` Toy-diorama tilt-shift: `057` is smooth, glossy plastic toys; this style has square-texel pixel textures on every surface and dark-outlined sprite characters.
- `042` NES 8-bit tile: `042` is flat and unlit with only a few colours; this style adds smooth lighting, shadows, glow and a rich range of colours.
- `046` Low-res sprite 2.5D shooter: `046` is darker, with sprites that have no outline and light that drops in steps; this style is brighter, with dark-outlined sprites, smooth light and bloom.

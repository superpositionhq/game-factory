# Gothic dark-fantasy realism

Reference works: Bloodborne.

## References

- *Bloodborne* (2015), FromSoftware, video game. https://en.wikipedia.org/wiki/Bloodborne
- *Dark Souls* (2011), FromSoftware, video game. https://en.wikipedia.org/wiki/Dark_Souls_(video_game)
- *Elden Ring* (2022), FromSoftware, video game. https://en.wikipedia.org/wiki/Elden_Ring
- *Demon's Souls* (2020), Bluepoint Games, video game. https://en.wikipedia.org/wiki/Demon's_Souls_(2020_video_game)
- *Sleepy Hollow* (1999), Tim Burton, live-action film. https://en.wikipedia.org/wiki/Sleepy_Hollow_(film)

## Visual definition

- **Shape language and proportions:** Tall, narrow, vertical: spires, pointed arches, flying buttresses, iron fences, statues and gravestones packed tightly. Characters wear long coats and layered cloth.
- **Line and outline:** No outline.
- **Shading model:** Physically based and smooth, with low-key contrast and wet specular highlights on cobbles and metal.
- **Palette:** `#0e1116` `#2b3038` `#4d5560` `#7c7466` `#5c1a1a` `#a8a08c` `#1f2a33`. Blue-black night, cold grey stone, tarnished iron, with dark blood red and weak candle yellow.
- **Lighting:** Moonlight through fog as a cold rim, plus small warm lanterns. Sky is overcast or a pale moon disc.
- **Texture and surface:** Ornate carved stone, worn cobbles, wrought-iron filigree, heavy cloth weave; all weathered and damp.
- **Atmosphere and post-processing:** Thick layered fog, blue-teal grade, mild bloom on lanterns and moon, grain and vignette.
- **Camera and framing:** Third-person behind the character, 28 to 35 mm equivalent, streets framed by tall facades.
- **UI and typography:** Thin tarnished-iron frames with engraved gothic filigree around dark parchment panels; icons are etched line drawings in pale bone `#a8a08c` on blue-black `#0e1116`. Type is a high-contrast old-style serif with small capitals. Counters use the same serif, and damage numbers are small and pale, with dark blood red `#5c1a1a` for health and critical hits.
- **VFX and motion:** Dark blood sprays in arcs and stains cloth, sparks jump where steel hits stone, embers drift from lanterns and fog curls around moving figures. Motion is weighty and realistic: long wind-ups, committed swings and quick sidesteps.

## Fits

- **Genres:** `soulslike`, `hack-and-slash`, `action-adventure`, `rpg`, `survival-horror`, `exploration`
- **Moods:** oppressive, dreadful, melancholic
- **Settings:** plague-ridden Victorian city, gothic cathedral district, moonlit graveyard, ruined castle

## Unreal recipe

### Assets

Gothic architecture kits with spires, pointed arches, buttresses, iron fences, statues and gravestones, packed tightly along narrow streets. Realistic packs are kept at full detail with Nanite; ornament stays as carved normal relief or real geometry. Scale facades 20 to 30 percent taller on Z and narrow the streets so walls frame the view. Wrought-iron filigree panels and fence runs are good candidates for building from scratch in Blender with array and curve modifiers.

### Materials

`M_GothicPBR`, Default Lit, full metal-roughness maps. `MF_Damp` lowers Roughness to 0.15 to 0.3 on up-facing cobbles and along a height gradient near the ground, so moonlight draws wet highlights on streets and iron. Stone instances are tinted into a narrow cold range (`#2b3038` to `#4d5560`, with `#7c7466` for worn edges); iron is dark, metallic and tarnished. Cloth uses the Cloth shading model with a weave normal. Blood is a DBuffer decal in `#5c1a1a` with low roughness. Lantern glass is emissive candle yellow.

### Lighting and atmosphere

Lumen GI and reflections on. The moon is a Directional Light at 0.3 to 0.6 lux, cold blue, placed behind the scene toward the camera so figures and spires get a rim, with Volumetric Scattering Intensity 2. Sky Light from an overcast night cubemap at low intensity; a pale moon disc on the sky dome. Small warm Point Lights at lanterns (radius 400 to 600, shadows on for the nearest few). Virtual Shadow Maps and contact shadows on. Fog is the signature: Exponential Height Fog with a second fog layer enabled for low ground mist, Volumetric Fog on, inscattering `#1f2a33`, plus slow fog-card emitters. Manual exposure.

### Post-processing

Grade to blue-teal: White Balance Temp lowered, shadows Gain toward `#1f2a33`, Global Saturation 0.8, with lantern orange surviving in highlights. Film Toe 0.6. Bloom Intensity 0.5, Threshold 1, visible only on lanterns and moon. Film Grain Intensity 0.25, Vignette 0.5, Ambient Occlusion Intensity 0.7, Scene Fringe 0. Motion Blur Amount 0. No post-process materials. TSR.

### UI and effects

Panels are dark parchment inside thin tarnished-iron frames with engraved filigree corners, as 9-slice Box brushes. Icons are etched line drawings in `#a8a08c` on `#0e1116`. Type in Cormorant Garamond with small capitals for labels and counters; damage numbers small and pale, health and critical hits in `#5c1a1a`. Niagara: blood as 20 to 40 dark lit sprites thrown in an arc with decals on landing, 10 to 15 orange sparks with collision where steel meets stone (0.3 s), 3 to 5 embers rising from each lantern for 2 s, and fog sprites pushed aside by a velocity field around moving characters.

## Do / Do not

Do:

- Build tall pointed vertical forms.
- Backlight with cold moonlight through fog.
- Carve ornament into stone as normal relief.
- Add a few small warm lanterns.

Do not:

- Do not use modern interiors lit by a flashlight; that reads as `029`.
- Do not use daylight and bulky military forms; that reads as `030`.
- Do not reduce the scene to flat black silhouettes; that reads as `070`.
- Do not use organic ribbed machine forms; that reads as `094`.

## Nearest styles

- `029` Survival-horror dark photoreal: this style shows outdoor streets of ornate carved stone under cold moonlight and fog, in blue-black and grey; `029` shows plain, cluttered modern interiors in dirty browns, lit by a flashlight cone.
- `030` Gritty desaturated war realism: this style is a night scene with a moonlit rim, small warm lanterns and tall thin spires; `030` is overcast daylight on bulky armour and broken classical columns, almost without colour.
- `094` Biomechanical monochrome: this style is built from stone, iron and cloth with warm lantern and blood-red accents; `094` covers everything in bone-grey ribs and tubes that fuse anatomy with machinery, with no warm colour.

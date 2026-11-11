# Gritty desaturated war realism

Reference works: Gears of War.

## References

- *Gears of War* (2006), Epic Games, video game. https://en.wikipedia.org/wiki/Gears_of_War_(video_game)
- *Gears of War 2* (2008), Epic Games, video game. https://en.wikipedia.org/wiki/Gears_of_War_2
- *Killzone 2* (2009), Guerrilla Games, video game. https://en.wikipedia.org/wiki/Killzone_2
- *Children of Men* (2006), Alfonso Cuaron, live-action film. https://en.wikipedia.org/wiki/Children_of_Men

## Visual definition

- **Shape language and proportions:** Bulky, heavy forms: thick armour, oversized weapons, massive ruined classical architecture with broken columns and rubble piles.
- **Line and outline:** No outline.
- **Shading model:** Physically based with strong normal-map relief and crushed contrast.
- **Palette:** `#3b3a36` `#6e6a5e` `#8f8a7a` `#4a5560` `#7a3a2a` `#b8b2a0` `#1e1e1c`. Grey, brown and gunmetal with almost all colour removed; rare rust or blood accents.
- **Lighting:** Overcast or smoky daylight with a hard, low key that rakes across surface relief.
- **Texture and surface:** Very dense: chipped stone, pitted metal, grime in every crevice, scratches on every edge.
- **Atmosphere and post-processing:** Bleach-bypass look: desaturated, high contrast, slight sharpening, dust and smoke in the air, grain.
- **Camera and framing:** Over-the-shoulder, 35 mm equivalent, low and close to cover objects.
- **UI and typography:** Heavy angular frames like stamped steel plates, stencilled icons and a round gear-shaped weapon and ammo indicator. Text is a condensed stencil sans in capitals, with bold blocky numerals. UI colours are off-white `#b8b2a0` on gunmetal `#4a5560`, with rust red `#7a3a2a` for damage warnings.
- **VFX and motion:** Heavy muzzle flashes, tracer streaks, chunks of stone and dust bursting from cover, thick smoke and dark blood spray, with camera shake on explosions and sprints. Motion is weighty: heavy footfalls, slow turns and hard slams into cover.

## Fits

- **Genres:** `third-person-shooter`, `fps`, `vehicle-combat`, `top-down-shooter`, `tower-defense`, `strategy`
- **Moods:** grim, brutal, desperate
- **Settings:** ruined classical city, war-torn industrial zone, underground tunnels, refugee checkpoints

## Unreal recipe

### Assets

Bulky military and ruin packs: thick armour, oversized weapons, broken classical columns, rubble piles, sandbag cover. Realistic packs need more relief, not less. Keep 2K to 4K textures and Nanite geometry. A script pass adds edge wear and crevice dirt to every asset from baked curvature and ambient-occlusion maps. Scale armour plates and weapon bodies up 10 to 20 percent for heavier proportions. Rubble heaps and chipped column drums are quick to generate with Geometry Script boolean cuts and noise displacement.

### Materials

`M_WarPBR`, Default Lit. Normal map intensity is multiplied by 1.5 to 2 through a `FlattenNormal` function with negative flatness, and a tiling detail normal adds pitting at close range. `MF_EdgeScratch` uses the curvature map to brighten edges and lower their roughness; `MF_CreviceGrime` darkens cavities toward `#1e1e1c`. BaseColor passes through a `Desaturation` node at 0.6 inside the material, leaving only rust `#7a3a2a` and blood decals with colour. Roughness spans 0.3 to 0.9 so raked light picks out every chip.

### Lighting and atmosphere

Lumen GI and reflections on. One Directional Light at a low 15 to 25 degree elevation, hard (Source Angle 0.5), slightly warm, raking across surfaces. Sky Light with Real Time Capture under an overcast Volumetric Cloud layer, kept bright enough that shadows are grey, not black. Virtual Shadow Maps with contact shadows on. Exponential Height Fog `#6e6a5e` with Volumetric Fog for smoky air, plus local smoke emitters. Auto Exposure Histogram with a narrow range.

### Post-processing

Bleach bypass is done in grading: Global Saturation 0.35, Contrast 1.3, Film Slope 0.95, Toe 0.65, with a LUT that lifts highlights toward `#b8b2a0` and cools shadows toward `#4a5560`. `r.Tonemapper.Sharpen=1` for the slight sharpening. Film Grain Intensity 0.3, Vignette 0.35, Ambient Occlusion Intensity 0.8, Bloom 0.3, Scene Fringe 0.1. Motion Blur Amount 0 and explosion shake limited to a small, short camera offset. No post-process materials. TSR.

### UI and effects

Frames are angular stamped-steel plates drawn as Box brushes with bolt corners in `#4a5560`; icons are stencils. The weapon indicator is a gear-shaped radial meter built from a User Interface material with a radial mask. Text in a stencil face such as Stardos Stencil or Barlow Condensed capitals, bold blocky `#b8b2a0` numerals, `#7a3a2a` for damage warnings. Niagara: heavy 0.06 s muzzle flashes, ribbon tracers, 8 to 15 stone chunk mesh particles with collision plus a dust burst from cover hits, thick lit smoke lasting 6 to 10 s, and dark blood sprites.

## Do / Do not

Do:

- Desaturate with a bleach-bypass grade.
- Rake a low key light across strong normal relief.
- Fill crevices with dirt and edges with scratches.
- Use heavy, thick proportions.

Do not:

- Do not drop to flashlight darkness; that reads as `029`.
- Do not add ornate gothic detail and night fog; that reads as `031`.
- Do not restore natural colour and open landscapes; that reads as `032`.
- Do not leave concrete clean and geometric; that reads as `097`.

## Nearest styles

- `031` Gothic dark-fantasy realism: this style is set in grey, smoky daylight among bulky rubble; `031` is a night scene with moonlit fog, lanterns and ornate carved stone.
- `097` Brutalist concrete: here every surface is chipped, pitted and grimy under hard raking light; `097` has clean concrete in large smooth planes under soft, brighter light.
- `032` Frontier natural-light realism: this style is almost colourless grey and brown; `032` keeps natural earth, grass and sky colours in warm sunlight.

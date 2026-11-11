# Frontier natural-light realism

Reference works: Red Dead Redemption 2.

## References

- *Red Dead Redemption 2* (2018), Rockstar Games, video game. https://en.wikipedia.org/wiki/Red_Dead_Redemption_2
- *The Last of Us Part II* (2020), Naughty Dog, video game. https://en.wikipedia.org/wiki/The_Last_of_Us_Part_II
- *The Revenant* (2015), Alejandro G. Inarritu, live-action film. https://en.wikipedia.org/wiki/The_Revenant_(2015_film)
- *Among the Sierra Nevada, California* (1868), Albert Bierstadt, oil painting. https://en.wikipedia.org/wiki/Among_the_Sierra_Nevada,_California
- *Kingdom Come: Deliverance* (2018), Warhorse Studios, video game. https://en.wikipedia.org/wiki/Kingdom_Come:_Deliverance

## Visual definition

- **Shape language and proportions:** Accurate real-world proportions. Open landscapes, timber buildings, wagons, fences; natural irregularity in every object.
- **Line and outline:** No outline.
- **Shading model:** Full physically based shading with natural soft-to-hard shadow falloff and realistic sky lighting.
- **Palette:** `#8a7a5c` `#c9b48a` `#5f6f4a` `#9db4c8` `#6b4a32` `#e8dcc0` `#3a3a30` `#d99a5a`. Natural earth, dry grass, sage green and weathered wood under a soft blue sky; warm golden-hour highlights.
- **Lighting:** Natural sun and sky at golden hour or under broken cloud; long shadows, visible atmospheric scattering.
- **Texture and surface:** Photographic detail at every scale: wood grain, mud, grass, stone, cloth weave.
- **Atmosphere and post-processing:** Aerial haze, mild bloom, light film grain, gentle depth of field at long range.
- **Camera and framing:** Wide landscape framing, 28 to 40 mm equivalent, horizon low or on a third.
- **UI and typography:** Minimal and mostly hidden: worn paper panels like a hand-drawn map or journal, thin inked rules, and icons drawn as catalogue engravings. Body text is an old-style serif, with wood-type slab capitals for titles as on frontier posters. Counters are small plain numerals in cream `#e8dcc0`, with dusty orange `#d99a5a` for alerts; no floating damage numbers.
- **VFX and motion:** Dust rises from hooves and wheels, gunsmoke hangs and drifts on the wind, breath shows as vapour in cold air and campfires throw slow embers. Motion is weighty and realistic, with full anticipation and follow-through and no snap.

## Fits

- **Genres:** `action-adventure`, `exploration`, `third-person-shooter`, `survival-craft`, `rpg`, `simulation`
- **Moods:** contemplative, rugged, melancholic
- **Settings:** American frontier, mountain wilderness, medieval countryside, overgrown abandoned town

## Unreal recipe

### Assets

Photoscanned ground, rocks, trees and grass plus realistic timber buildings, wagons and fences. Use them at full quality: Nanite meshes, 4K texture sets, Nanite or masked foliage with wind. Scatter grass, shrubs and stones densely with PCG or foliage instancing from a script. Built objects need irregularity: a script applies a small random bend, sag and lean (1 to 3 degrees) to fence posts, roof lines and porch beams. Terrain is a Landscape with layered materials.

### Materials

Standard Default Lit PBR. `M_Landscape` blends dry earth, mud, grass and rock layers by slope and height, with a Runtime Virtual Texture so props and grass pick up ground colour at their base. Foliage uses Two Sided Foliage with subsurface colour and wind through World Position Offset. Wood, cloth and leather keep full albedo, normal and roughness detail; a shared `MF_Dust` adds pale dust on up-facing surfaces. Skin uses Subsurface Profile. Instance tints stay within natural earth and sage values (`#8a7a5c`, `#5f6f4a`, `#6b4a32`); no stylised simplification.

### Lighting and atmosphere

Lumen GI and reflections on, with hardware ray tracing where the machine allows. A physically based sky: Directional Light at 5 to 12 degrees elevation for golden hour with atmosphere transmittance colouring it, Sky Atmosphere, Volumetric Cloud with broken cover casting cloud shadows, Sky Light with Real Time Capture. Virtual Shadow Maps give long shadows with natural soft-to-hard falloff from a Source Angle near 0.5. Exponential Height Fog with low density and Volumetric Fog on for aerial haze; Sky Atmosphere aerial perspective left at default strength. Auto Exposure Histogram, with a moderate Min and Max EV100 range.

### Post-processing

Keep the default filmic tone curve and do not push a two-hue grade. Only small moves: White Balance slightly warm, Saturation 1.0 to 1.05, Contrast 1.0. Bloom Intensity 0.3. Film Grain Intensity 0.1. Depth of Field only at long range, with Aperture F-stop about 8 and focus on the subject. Vignette 0.15, Scene Fringe 0, Lens Flare Intensity 0.1 toward the sun. Motion Blur Amount 0. No post-process materials. TSR.

### UI and effects

HUD mostly hidden, fading in on demand. Panels are worn paper brushes like a journal or hand-drawn map with thin inked rules; icons are engraving-style drawings. Body in EB Garamond; titles in a wood-type slab such as Rye or Smokum capitals. Counters are small plain `#e8dcc0` numerals, alerts `#d99a5a`; no floating damage numbers. Niagara: lit dust sprites from hooves and wheels drifting downwind for 3 to 5 s, gunsmoke that hangs for 6 s, breath vapour puffs of 1 s in cold areas, and slow campfire embers rising for 3 s.

## Do / Do not

Do:

- Light with a physically based sky at low sun.
- Scatter dense instanced grass and rocks.
- Add irregularity and sag to built objects.
- Fade distance with aerial haze.

Do not:

- Do not push a two-hue colour grade; that reads as `033`.
- Do not desaturate and crush contrast; that reads as `030`.
- Do not simplify materials into clean stylised regions; that reads as `013`.
- Do not replace detail with visible dabs of paint; that reads as `075`.

## Nearest styles

- `033` Teal-orange desert blockbuster: this style keeps natural greens, soft haze and many quiet earth colours; `033` pushes the whole frame to vivid orange sand against teal sky and shadow.
- `030` Gritty desaturated war realism: this style has warm golden sun on an open landscape with clear natural colour; `030` is darker and almost colourless grey, with crushed shadows.
- `075` Impressionist broken colour: surfaces here show photographic detail with smooth tonal transitions; `075` builds the whole image from separate visible paint dabs in pale, bright pastels.

# Teal-orange desert blockbuster

Reference works: Mad Max: Fury Road.

## References

- *Mad Max: Fury Road* (2015), George Miller, live-action film. https://en.wikipedia.org/wiki/Mad_Max:_Fury_Road
- *Mad Max* (2015), Avalanche Studios, video game. https://en.wikipedia.org/wiki/Mad_Max_(2015_video_game)
- *Furiosa: A Mad Max Saga* (2024), George Miller, live-action film. https://en.wikipedia.org/wiki/Furiosa:_A_Mad_Max_Saga
- *Dune* (2021), Denis Villeneuve, live-action film. https://en.wikipedia.org/wiki/Dune_(2021_film)

## Visual definition

- **Shape language and proportions:** Real-world scale. Vehicles are welded hybrids with spikes, exhaust stacks and oversized engines; the landscape is flat desert with rock spires.
- **Line and outline:** No outline.
- **Shading model:** Physically based with hard sun shadows and bright specular glints on chrome.
- **Palette:** `#e07b1a` `#f2b04a` `#1f6f8b` `#0f3b4c` `#3a2a1c` `#f7e0b0` `#b5451b`. Two hues only: saturated orange sand and skin against teal sky and shadow. Almost no green or purple.
- **Lighting:** Hard midday sun, cloudless graded sky; night scenes are day-for-night blue.
- **Texture and surface:** Dust, rust, sand ripples and dirty chrome; detailed but subordinate to the colour grade.
- **Atmosphere and post-processing:** Aggressive teal-orange grade with high saturation and contrast, dust plumes, slight sharpening, centre-framed subjects.
- **Camera and framing:** Centre-framed action, wide 24 to 35 mm and long-lens compression shots, low to the ground.
- **UI and typography:** Panels look like welded scrap plate with rivets, hazard stripes and scratched paint; icons are spray-stencilled silhouettes. Type is a condensed stencil sans in capitals, and counters read like stamped gauge or odometer digits. UI colours are orange `#e07b1a` and cream `#f7e0b0` on dark teal `#0f3b4c`.
- **VFX and motion:** Tall dust plumes trail every vehicle, explosions are orange fireballs with black smoke, and metal-on-metal hits throw long sparks and sand spray. Motion is fast and violent: heavy vehicles bounce on their suspension, impacts shake the camera, and action can have a slightly sped-up, jerky feel.

## Fits

- **Genres:** `vehicle-combat`, `racing`, `third-person-shooter`, `action-adventure`, `survival-craft`, `fps`
- **Moods:** frantic, harsh, exhilarating
- **Settings:** desert wasteland, post-apocalyptic highway, salt flats, sand-planet outpost

## Unreal recipe

### Assets

Kitbash vehicles from realistic car, truck and scrap packs: weld on spikes, exhaust stacks, blowers and plate armour in Blender, keeping real-world scale. Terrain is a flat Landscape with sand ripples and a few rock spires. Keep full PBR texture sets. A script recolours albedo so nothing sits in green or purple: hues are remapped toward rust, sand and bare metal before the grade. Spike strips, exhaust pipes and welded plates are quick to build from scratch.

### Materials

`M_WastelandPBR`, Default Lit. `MF_SandDust` lays `#f2b04a` dust on up-facing surfaces with a world-aligned mask; `MF_Rust` blends `#b5451b` rust by curvature and ambient occlusion. Chrome parts are Metallic 1 with Roughness 0.1 to 0.2 under a dirt mask, giving bright sun glints. The sand material uses a ripple normal with a sparkle term from a high-frequency noise in Roughness. Skin and cloth instances are tinted warm so they fall on the orange side of the grade.

### Lighting and atmosphere

Lumen GI on, reflections on for chrome. One hard Directional Light near midday, 60 to 75 degrees elevation, Source Angle 0.5, intensity around 10 lux. Sky Atmosphere with no Volumetric Cloud: a cloudless sky. Sky Light with Real Time Capture. Virtual Shadow Maps with crisp edges. Exponential Height Fog thin, sand coloured; dust comes from particles, not haze. Night scenes are day-for-night: keep the sun position, drop exposure two stops and grade blue. Manual exposure.

### Post-processing

The grade is the style. Apply a Color Grading LUT built by script that maps shadows and sky to teal (`#0f3b4c` to `#1f6f8b`) and midtones and highlights to orange (`#e07b1a` to `#f7e0b0`), collapsing other hues onto those two. On top: Global Saturation 1.3, Contrast 1.2, shadows Gain teal, highlights Gain orange. `r.Tonemapper.Sharpen=0.8`. Bloom Intensity 0.3, Vignette 0.3, Film Grain 0.15, Scene Fringe 0. Motion Blur Amount 0; impact shake is a short, small camera offset only. No surface-flattening post material: full 3D shading and detail remain. TSR.

### UI and effects

Panels are welded scrap plate with rivets, hazard stripes and scratched paint, as Box brushes; icons are spray-stencil silhouettes with soft overspray. Type in Stardos Stencil or Bebas Neue capitals; counters are odometer-style digit wheels made from a scrolling User Interface material. Orange `#e07b1a` and cream `#f7e0b0` on `#0f3b4c`. Niagara: tall lit dust plumes behind every vehicle (sprites growing for 4 to 6 s, sand coloured), explosions as an orange fireball flipbook followed by black smoke for 5 s, long spark streaks with velocity-stretched sprites on metal hits, and sand spray fans from skidding wheels.

## Do / Do not

Do:

- Grade the frame to orange and teal only.
- Use hard sun and deep graded sky.
- Add dust plumes behind moving objects.
- Centre the subject in frame.

Do not:

- Do not keep natural greens and soft haze; that reads as `032`.
- Do not add a magenta sunset with a neon grid; that reads as `090`.
- Do not go dark and rainy with neon; that reads as `089`.
- Do not flatten shapes into colour layers; that reads as `060`.

## Nearest styles

- `032` Frontier natural-light realism: this style grades the whole frame to vivid orange against teal under hard midday sun; `032` keeps natural greens and browns in soft golden haze.
- `060` Layered flat-colour wilderness: this style is fully shaded 3D with dust, rust and sand ripples on every surface; `060` is a stack of flat single-colour silhouette layers with no surface detail.
- `061` Soft-gradient minimal desert: this style is gritty and rusty, with a teal sky set against orange sand; `061` shows smooth glowing dunes in one warm colour family, with soft shadows and no teal.

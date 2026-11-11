# Industrial used-future

Reference works: Alien (1979).

## References

- *Alien* (1979), Ridley Scott, live-action film. https://en.wikipedia.org/wiki/Alien_(film)
- *Alien: Isolation* (2014), Creative Assembly, video game. https://en.wikipedia.org/wiki/Alien:_Isolation
- *Aliens* (1986), James Cameron, live-action film. https://en.wikipedia.org/wiki/Aliens_(film)
- *Dead Space* (2008), EA Redwood Shores, video game. https://en.wikipedia.org/wiki/Dead_Space_(2008_video_game)
- *Outland* (1981), Peter Hyams, live-action film. https://en.wikipedia.org/wiki/Outland_(film)

## Visual definition

- **Shape language and proportions:** Functional industrial spacecraft interiors: low corridors with ribbed walls, exposed pipes and conduits, bulkhead doors, grated floors, chunky analogue control panels with small CRT screens and rows of square buttons.
- **Line and outline:** No outline.
- **Shading model:** Physically based and smooth, low-key, with soft specular on worn painted metal.
- **Palette:** `#0f1412` `#2b332f` `#59645c` `#8a8f80` `#c9b458` `#a8402a` `#3f6f6a`. Dark grey-green and off-white painted metal, with amber warning lights, dull red stencils and teal monitor glow.
- **Lighting:** Dim, practical: strip lights behind grilles, flashing amber beacons, monitor glow, steam-diffused back light. Many dark corners.
- **Texture and surface:** Worn paint, scuffs on edges, stencilled labels and hazard stripes, padded wall sections, condensation, grime in recesses.
- **Atmosphere and post-processing:** Steam and haze, film grain, slight anamorphic flare, CRT scanlines on screens.
- **Camera and framing:** Low, wide lens in tight corridors; slow tracking.
- **UI and typography:** Chunky CRT-style readouts in teal or amber phosphor on black, set in bevelled metal bezels with hazard-stripe edges; icons are blocky pictograms like stencilled ship labels. Type is a squared low-resolution monospace face, with condensed stencil capitals for labels. Counters are segmented digits in amber `#c9b458`, with dull red `#a8402a` for alarms.
- **VFX and motion:** Steam bursts from pipes, sparks from damaged panels, flickering strip lights and rotating amber beacons; hits throw sparks and a brief flash into the haze. Motion is weighty and realistic, with heavy slow doors and grounded, deliberate character animation.

## Fits

- **Genres:** `survival-horror`, `stealth`, `fps`, `third-person-shooter`, `exploration`, `survival-craft`
- **Moods:** tense, claustrophobic, oppressive, lonely
- **Settings:** commercial towing spaceship, mining station, deep-space refinery, colony outpost

## Unreal recipe

### Assets

Use realistic industrial sci-fi kits: ribbed corridor walls, bulkhead doors, grated floors, pipe and conduit sets, analogue consoles with square buttons and small CRT housings. Keep normal maps, roughness detail and full resolution. Repaint albedo by script toward grey-green `#2b332f`, `#59645c` and off-white `#8a8f80`; strip blue holograms, glossy touchscreens and clean white plastic. Build by script: stencil-label and hazard-stripe decal sheets, padded wall sections, extra pipe runs along splines.

### Materials

Default Lit master `M_WornPaint` using material layers: painted metal base, an edge-wear layer revealing bare steel (mask from a baked curvature texture), and a grime layer in recesses (ambient-occlusion mask) that raises Roughness to 0.8. Paint Roughness 0.45 to 0.6 for a soft specular. A condensation function adds small droplet normals on cold pipes. DBuffer decals place dull red `#a8402a` stencils and amber-black stripes. Monitors use an Unlit screen material: teal `#3f6f6a` phosphor text, scanlines from Frac on V, slight flicker; beacons use Emissive Color in amber `#c9b458`.

### Lighting and atmosphere

Lumen global illumination and reflections on. Lights are practical and few: Rect Lights behind grilles at low intensity, cool-white, some with a flicker driven from C++; rotating amber Spot Lights for beacons; weak teal Point Lights at monitors. Leave corners unlit and add no fill. Exponential Height Fog with Volumetric Fog on, density 0.03 to 0.06, so back-lit steam and beacon sweeps show as beams. Virtual Shadow Maps with contact shadows on. Exposure uses the Auto Exposure Histogram with Min and Max EV100 clamped close together so darkness is not lifted.

### Post-processing

Filmic tone curve with Film Toe 0.6. Colour grading: Global Saturation 0.8, Midtones tinted slightly green, Contrast 1.1. Film Grain Intensity 0.4. Bloom Intensity 0.5 with Lens Flare Intensity 0.2. Vignette Intensity 0.4. Scene Fringe Intensity 0.2. Depth of field off, Motion Blur Amount 0. TSR anti-aliasing.

### UI and effects

UMG readouts are black panels inside bevelled metal bezel images with a hazard-stripe edge. Text uses VT323 or Share Tech Mono in teal or amber phosphor; labels use a condensed stencil face such as Saira Stencil One in capitals. Counters are segmented digits in `#c9b458`, switching to `#a8402a` on alarm. A Retainer Box material adds scanlines and slight barrel curvature to the HUD only.

Niagara: steam bursts from pipe joints as lit sprites, 30 per burst, lifetime 2 s, pushed by an initial jet velocity then slowed by drag; panel sparks as orange streaks with gravity and one bounce, 0.5 s, with a Light renderer flashing the haze; continuous floor-vent haze at low opacity.

## Do / Do not

Do:

- Fill walls with ribs, pipes and analogue panels.
- Light with dim practical strips and amber beacons.
- Add stencil labels and hazard stripes.
- Add steam and haze.

Do not:

- Do not use clean bright white panels; that reads as `091`.
- Do not use bone-like organic ribbing in a single grey; that reads as `094`.
- Do not use domestic decay with a flashlight; that reads as `029`.
- Do not add neon signs and rain; that reads as `089`.

## Nearest styles

- `029` Survival-horror dark photoreal: everything here is manufactured (ribbed metal walls, control panels, stencil labels) and dimly lit by strips and beacons; `029` is darker still, lit mainly by a flashlight, and shows domestic rot, mould and peeling surfaces.
- `094` Biomechanical monochrome: this style is painted metal with flat labelled panels and amber, red and teal lights; `094` has no colour at all, and every surface is grown into bone-grey ribs and tubes.
- `089` Rain-soaked tech-noir: colour here is muted grey-green with only small warning lights; `089` is a wet city street lit by bright neon signs in vivid colours.

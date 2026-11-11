# Film noir hard light

Reference works: The Third Man.

## References

- *The Third Man* (1949), Carol Reed, live-action film. https://en.wikipedia.org/wiki/The_Third_Man
- *Double Indemnity* (1944), Billy Wilder, live-action film. https://en.wikipedia.org/wiki/Double_Indemnity
- *Touch of Evil* (1958), Orson Welles, live-action film. https://en.wikipedia.org/wiki/Touch_of_Evil
- *The Maltese Falcon* (1941), John Huston, live-action film. https://en.wikipedia.org/wiki/The_Maltese_Falcon_(1941_film)
- *L.A. Noire* (2011), Team Bondi, video game. https://en.wikipedia.org/wiki/L.A._Noire

## Visual definition

- **Shape language and proportions:** Real-world 1940s urban settings: wet cobbled streets, stairwells, offices with blinds, arches and tunnels. Realistic proportions.
- **Line and outline:** No outline.
- **Shading model:** Photographic and smooth, in black and white, with very high contrast: deep blacks, bright highlights, narrow midtone range.
- **Palette:** `#050505` `#2a2a2a` `#6e6e6e` `#b5b5b5` `#f0f0f0`. Greyscale only.
- **Lighting:** Hard, low-angle single sources: long shadows, light through window blinds in stripes, silhouettes in doorways, wet-street reflections, backlit haze.
- **Texture and surface:** Real materials in monochrome: wet cobbles, brick, plaster, wood grain, with film grain over all.
- **Atmosphere and post-processing:** Black-and-white conversion, strong contrast curve, film grain, vignette, slight halation around bright lights.
- **Camera and framing:** Tilted (Dutch) angles, low or high viewpoints, wide lens with deep focus.
- **UI and typography:** Thin white rule frames and plain black cards, like film title cards and case-file sheets; icons are simple white silhouettes. Titles are high-contrast serif capitals in the manner of 1940s film credits, with a typewriter face for notes, evidence and numerals, all in white `#f0f0f0` and grey `#b5b5b5` on black.
- **VFX and motion:** Muzzle flashes light the whole room white for one frame; cigarette smoke and steam drift through light shafts; rain splashes on wet streets. Motion is weighty and realistic, with slow deliberate movement and long shadows that swing across walls.

## Fits

- **Genres:** `detective-mystery`, `stealth`, `third-person-shooter`, `action-adventure`
- **Moods:** tense, cynical, brooding
- **Settings:** 1940s city at night, post-war Vienna, detective office, sewer tunnels

## Unreal recipe

### Assets

Realistic store packs are the right source: European street kits, cobbles, stairwells, period offices, Venetian blinds, iron railings, sewer tunnels. Keep all PBR maps, including normals and roughness detail; nothing is stripped. Restyling is about value, not form: by script, check each albedo's luminance and re-level textures so walls land in mid grey and trims go near-white or near-black, because hue contrast will be lost. Build by script only the shadow makers: blind slats, railing grids and window frames placed between light and wall.

### Materials

Default Lit throughout, on the packs' own masters. Insert a shared material function, `MF_Wet`, into ground and wall parents: lowers roughness to 0.08 in puddle masks from a world-aligned noise, darkens Base Colour by 40 percent and flattens the normal there. No colour work is needed in materials, since conversion happens in post, but keep emissive lamp values high (20 and above) so they clip to white with halation.

### Lighting and atmosphere

Lumen GI and Lumen reflections on for street reflections. Each scene has one key: a Spot or Directional Light with Source Radius or Source Angle near 0, placed low, 10 to 25 degrees. Blind stripes come from real slat geometry or a Light Function. Lower the key's Indirect Lighting Intensity to 0.3 and keep Sky Light under 0.1 so shadows fall to `#050505`. Exponential Height Fog with Volumetric Fog on gives backlit haze and shafts; raise the key's Volumetric Scattering Intensity to 2 to 4. Virtual Shadow Maps, contact shadows, manual exposure.

### Post-processing

Colour Grading: global Saturation 0 for the black-and-white conversion; Contrast 1.3; Film Toe raised and Slope near 0.95 so midtones stay narrow and blacks crush. Bloom Method Convolution, or Standard at Intensity 0.6 with large size scale, for halation round lamps. Film Grain Intensity 0.5. Vignette 0.5. Depth of field effectively off (high f-stop) for deep focus. Motion Blur Amount 0. No outline or threshold material: every grey from `#2a2a2a` to `#b5b5b5` must survive. TSR. Dutch tilt is a camera roll of 8 to 15 degrees.

### UI and effects

Black cards with a 1 px `#f0f0f0` inner rule (Border brush) for menus and case files. Titles in Playfair Display capitals with wide spacing, notes and all numerals in Special Elite, white with `#b5b5b5` for secondary text. Wrap the HUD in a Retainer Box whose material adds the same grain.

Niagara: muzzle flash pairs a sprite with a Point Light spiking to very high intensity for one frame; smoke and steam as lit translucent sprites with volumetric directional lighting, 4 to 8 s life, drifting through shafts; rain as GPU sprite streaks plus ripple flipbooks on puddles.

## Do / Do not

Do:

- Convert to pure black and white.
- Light with one hard low-angle source.
- Cast blind-slat or railing shadow patterns.
- Tilt the camera and add film grain.

Do not:

- Do not threshold to two values with a colour spot; that reads as `069`.
- Do not paint jagged shadows on distorted flat sets; that reads as `071`.
- Do not use flat black silhouettes in grey fog; that reads as `070`.
- Do not leave any colour in the frame.

## Nearest styles

- `069` Selective-colour ink noir: `069` reduces everything to pure black and pure white shapes with bold keylines and one spot of colour; this style keeps the full grey range of a photograph, with film grain and no lines or colour.
- `070` Silhouette fog monochrome: `070` shows flat black silhouettes against pale, blurred grey fog layers; this style shows lit, detailed surfaces under hard light with deep black shadow.
- `085` Baroque chiaroscuro: `085` has the same single hard light out of darkness, but in warm painted colour with flesh tones and brown shadows; this style is black-and-white film with no colour.

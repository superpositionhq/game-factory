# Oily concept-art realism

Reference works: Dishonored.

## References

- *Dishonored* (2012), Arkane Studios, video game. https://en.wikipedia.org/wiki/Dishonored
- *Dishonored 2* (2016), Arkane Studios, video game. https://en.wikipedia.org/wiki/Dishonored_2
- *Deathloop* (2021), Arkane Lyon, video game. https://en.wikipedia.org/wiki/Deathloop
- *BioShock Infinite* (2013), Irrational Games, video game. https://en.wikipedia.org/wiki/BioShock_Infinite

## Visual definition

- **Shape language and proportions:** Realistic scale with caricatured faces and hands (long angular features) and elongated, top-heavy architecture. Industrial Victorian shapes with heavy metal fixtures.
- **Line and outline:** No outline.
- **Shading model:** Smooth physically based shading, but with broad, simplified material response: wide soft highlights and little micro detail.
- **Palette:** `#2e3138` `#6b5a4a` `#8c8f8a` `#a23b2a` `#c9b68c` `#3f4f5c` `#d8d4c8`. Cold greys and slate blue with rusty brown, brass and a deep red accent. Overall low saturation.
- **Lighting:** Overcast daylight through tall windows, or lamps with soft pools; gentle contrast.
- **Texture and surface:** Textures look like oil studies: large soft brush areas, blurred wear, painted rather than photographed detail.
- **Atmosphere and post-processing:** Light fog, soft ambient occlusion, slight desaturation and a cool grade.
- **Camera and framing:** First-person, 28 to 35 mm equivalent, interiors with tall verticals.
- **UI and typography:** Painted icons in round engraved-brass or carved-bone frames, and parchment panels with ink sketches. Headings use a narrow Victorian serif and labels a plain small-caps serif; counters are plain off-white numerals. UI colours are off-white `#d8d4c8` and brass `#c9b68c` on slate `#2e3138`, with deep red `#a23b2a` for alerts.
- **VFX and motion:** Restrained effects: soft smoke, dark ash-like wisps for supernatural powers, brief dull sparks when steel meets steel. Motion is weighty and realistic, with slightly exaggerated, readable poses for first-person hands and enemies.

## Fits

- **Genres:** `stealth`, `fps`, `action-adventure`, `detective-mystery`, `exploration`
- **Moods:** oppressive, grim, conspiratorial
- **Settings:** plague-ridden port city, Victorian industrial districts, aristocratic mansions, whaling docks

## Unreal recipe

### Assets

Victorian and industrial store packs fit once their detail is softened. Script a texture pass over every albedo: bilateral blur at 12 to 16 px on a 2048 px map, then a slight posterise to 24 levels, so wear and stains become soft painted areas. Blur normal maps to remove pores, scratches and grain, keeping only large relief. Stretch buildings 15 to 25 percent on Z and widen cornices so architecture is top-heavy. Characters need caricature: lengthen faces, noses and fingers through bone scales or a Blender shape edit. Pipes, valves and lamp brackets are easy to build from scratch.

### Materials

`M_OilPBR`, Default Lit with full PBR inputs but simplified response. Roughness is clamped by parameters to 0.45 to 0.8 and read from a blurred roughness map, giving wide soft highlights and no pin-sharp glints. Metallic is binary. A `Desaturation` node at 0.3 runs on BaseColor before a tint. Two instances carry the accents: brass `#c9b68c` (metallic, roughness 0.5) and deep red `#a23b2a` for cloth and paint. Skin uses Subsurface Profile with a painted, pore-free albedo. No banding: gradients stay smooth.

### Lighting and atmosphere

Lumen GI and reflections on with Final Gather Quality 2 for clean interiors. Daylight scenes: a weak Directional Light (2 lux, Source Angle 8) plus Rect Lights placed in tall windows, cool white. Night scenes: Point Lights with a large Source Radius for soft pools, warm against `#3f4f5c` ambient. Sky Light with Real Time Capture over an overcast Sky Atmosphere and Volumetric Cloud layer. Exponential Height Fog, low density, slate tint, Volumetric Fog on for window shafts. Auto Exposure Histogram limited to a one-stop range.

### Post-processing

No stylising material is required; an optional 3 px Kuwahara pass at Scene Color Before DOF may be added at 40 percent blend to melt remaining photo detail, never strong enough to show steps. Global Saturation 0.75, Contrast 0.95, White Balance Temp shifted about 500 K cool, shadows Gain slightly blue. Ambient Occlusion Intensity 0.6 with a wide Radius. Bloom Intensity 0.25. Vignette 0.25, Film Grain 0.05, Scene Fringe 0, Motion Blur Amount 0, no depth of field in first person. TSR with `r.Tonemapper.Sharpen=0`.

### UI and effects

Icons sit in round engraved-brass or carved-bone ring brushes; panels are parchment Box brushes with ink sketches. Headings in Playfair Display, labels in EB Garamond small caps, counters in plain `#d8d4c8` numerals on `#2e3138`; alerts in `#a23b2a`. Niagara stays restrained: lit translucent smoke sprites drifting 3 to 5 s, dark ash wisps on ribbons for supernatural powers (near-black with a faint `#3f4f5c` edge, 0.8 s), and 4 to 8 dull orange sparks lasting 0.2 s on steel contact.

## Do / Do not

Do:

- Keep texture marks large and soft.
- Stretch architecture vertically.
- Hold saturation low with one red or brass accent.
- Use wide soft highlights.

Do not:

- Do not add sharp photographic micro detail; that reads as `029` or `032`.
- Do not quantise light into blocks; that reads as `021`.
- Do not add visible stroke-by-stroke brushwork; that reads as `024`.
- Do not cover everything in polished brass; that reads as `095`.

## Nearest styles

- `021` Brush-block martial painterly: this style has smooth gradients and grey rooms with little colour; `021` shows light in three to five visible steps and floods each room with one strong colour.
- `095` Brass steampunk: here cold grey and slate blue dominate and brass is a small accent; `095` fills the frame with warm brass, copper and furnace glow.
- `029` Survival-horror dark photoreal: scenes here are lit by soft daylight or lamp pools and textures look softly painted; `029` is mostly black, with sharp photographic detail.

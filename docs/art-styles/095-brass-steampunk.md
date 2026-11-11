# Brass steampunk

Reference works: Steamboy; Syberia.

## References

- *Steamboy* (2004), Sunrise (Katsuhiro Otomo), animated film. https://en.wikipedia.org/wiki/Steamboy
- *Syberia* (2002), Microids (Benoit Sokal), video game. https://en.wikipedia.org/wiki/Syberia
- *20,000 Leagues Under the Sea* (1954), Richard Fleischer (Walt Disney Productions), live-action film. https://en.wikipedia.org/wiki/20,000_Leagues_Under_the_Sea_(1954_film)
- *Machinarium* (2009), Amanita Design, video game. https://en.wikipedia.org/wiki/Machinarium
- *Castle in the Sky* (1986), Studio Ghibli (Hayao Miyazaki), animated film. https://en.wikipedia.org/wiki/Castle_in_the_Sky

## Visual definition

- **Shape language and proportions:** Victorian machinery: exposed gears, flywheels, pistons, boilers with domed ends, pressure gauges, valve wheels, riveted plates, copper pipe runs, leather straps and wood panelling. Ornate cast brackets on functional machines.
- **Line and outline:** No outline.
- **Shading model:** Physically based and smooth, dominated by warm metallic reflections.
- **Palette:** `#b5802e` `#7a4a1e` `#3a2a1c` `#c9a36a` `#5a6b5e` `#2f1f14` `#e6c88a` `#8a2f1f`. Brass, copper and bronze with dark wood, oxblood leather, iron black and verdigris green.
- **Lighting:** Warm gaslight and furnace glow, shafts of light through steam; dark surroundings.
- **Texture and surface:** Polished and tarnished metal, rivet rows, wood grain, stitched leather, soot, verdigris in crevices, engraved dials.
- **Atmosphere and post-processing:** Steam, warm haze, bloom on lamps and furnace, slight vignette.
- **Camera and framing:** Medium shots of machinery with shallow depth; low angles on large engines.
- **UI and typography:** Brass-framed panels with riveted corners, round pressure-gauge dials and engraved plates on dark wood or oxblood leather; icons look like etched or cast metal emblems. Type is an ornate Victorian serif with engraved slab capitals in cream `#e6c88a`. Counters are needle gauges or mechanical digit wheels like an odometer.
- **VFX and motion:** Steam jets, furnace sparks, soot puffs and spinning gears; hits throw orange sparks and bursts of white steam. Motion is mechanical and weighty: pistons pump in a steady rhythm, flywheels spin up slowly, and machines shudder when they start.

## Fits

- **Genres:** `puzzle`, `action-adventure`, `exploration`, `vehicle-combat`, `platformer`, `strategy`
- **Moods:** adventurous, inventive, warm, nostalgic
- **Settings:** Victorian factory, airship deck, clockwork workshop, steam submarine

## Unreal recipe

### Assets

Realistic Victorian and steampunk packs fit with little change: boilers, engines, gauges, valve wheels, pipe kits, riveted plates, wood-panelled rooms, leather furniture. Convert any steel-grey or chrome materials to brass, copper or iron black by script. Generate moving parts in Blender so they animate correctly: involute gears with matching tooth counts, flywheels, piston and crank assemblies, domed boiler ends, rivet rows instanced along plate edges, copper pipe runs swept on splines.

### Materials

Default Lit metals with Metallic 1. Brass `#b5802e` and copper `#7a4a1e` as Base Colour; Roughness is a two-level blend, polished (0.2) on exposed faces and tarnished (0.55) elsewhere, masked by baked curvature and a WorldAlignedTexture smudge map. A verdigris layer `#5a6b5e` (Metallic 0, Roughness 0.8) and a soot layer `#2f1f14` sit in crevices through an ambient-occlusion mask. Wood `#3a2a1c` uses grain normals at Roughness 0.5; leather `#8a2f1f` gets a stitched-seam normal. Gauge dials are engraved cream `#e6c88a` textures with a needle rotated by Custom Primitive Data.

### Lighting and atmosphere

Lumen global illumination and reflections are essential here: brass reads through what it reflects, so keep warm lit surfaces around every machine and raise reflection quality in the volume. Lights: Point Lights at gas lamps (2200 K, soft shadows), a flickering orange Rect Light in each furnace, and one or two Spot Lights through windows as shafts. Surroundings stay dark; Sky Light low and warm. Exponential Height Fog with Volumetric Fog on, Albedo warm grey, so steam and shafts are visible. Exposure auto with a narrow EV100 range.

### Post-processing

Filmic tone curve at defaults. White Balance Temp warm; Global Saturation 1.05; Shadows tinted brown, never blue. Bloom Intensity 0.6 with Threshold 1 on lamps and furnace. Vignette Intensity 0.35. Depth of field for medium shots, about f/2.8. Film Grain Intensity 0.1, Scene Fringe Intensity 0, Motion Blur Amount 0. TSR anti-aliasing.

### UI and effects

UMG panels use a 9-slice brass frame with riveted corners over a dark wood or oxblood leather fill; section headers sit on engraved plate images. Titles use Playfair Display SC or IM Fell English SC, labels a slab such as Rokkitt, in cream `#e6c88a`. Health and pressure are round gauge widgets with a rotating needle image; scores are odometer-style digit wheels made of vertically scrolling numeral strips in clipped boxes.

Niagara: steam jets as lit sprites with strong initial velocity, expanding and fading over 1.2 s; furnace sparks as orange streaks rising with turbulence, 0.8 s; soot puffs, dark and brief. Hits throw 20 to 30 orange sparks plus a white steam burst. Gears and pistons are driven in C++ at a steady rhythm.

## Do / Do not

Do:

- Make brass and copper the dominant materials.
- Show gears, pistons, gauges and rivets.
- Light with warm lamps and furnace glow.
- Provide a warm environment map for reflections.

Do not:

- Do not use cold grey industrial panels; that reads as `092`.
- Do not use sleek stepped geometric ornament in gold and black; that reads as `096`.
- Do not soften into low-saturation painted greys; that reads as `026`.
- Do not use chrome and pastel plastics; that reads as `099`.

## Nearest styles

- `096` Art Deco streamline: surfaces here are busy with rivets, gears, tarnish and soot in many warm metal and wood tones; `096` is smooth, polished and sparing, in black, gold and teal with clean geometric inlay.
- `026` Oily concept-art realism: this style has rich, warm brass and copper colour with crisp material detail; `026` is cold and greyed, with loose painted surfaces.
- `092` Industrial used-future: this style is warm metal glowing under gaslight; `092` is grey-green painted metal in dimmer, colder light.

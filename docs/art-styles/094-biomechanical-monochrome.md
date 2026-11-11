# Biomechanical monochrome

Reference works: H. R. Giger; Scorn.

## References

- *Necronom IV* (1976), H. R. Giger, airbrush painting. https://en.wikipedia.org/wiki/H._R._Giger
- *Alien* (1979), Ridley Scott (creature and derelict design by H. R. Giger), live-action film. https://en.wikipedia.org/wiki/Alien_(film)
- *Scorn* (2022), Ebb Software, video game. https://en.wikipedia.org/wiki/Scorn_(video_game)
- *Dark Seed* (1992), Cyberdreams, video game. https://en.wikipedia.org/wiki/Dark_Seed_(video_game)

## Visual definition

- **Shape language and proportions:** Fusion of anatomy and machinery: ribbed tubes, vertebra-like columns, pelvis-shaped arches, pistons that look like tendons, cable bundles like muscle fibre. Strong bilateral symmetry and repetition of segments.
- **Line and outline:** No outline.
- **Shading model:** Smooth, airbrushed gradients with a wet, semi-gloss sheen; deep occlusion in every recess.
- **Palette:** `#0c0c0d` `#2b2a28` `#5b5852` `#8c877c` `#b9b2a2` `#3f3a36`. Monochrome: black, cold grey, bone and gunmetal, with at most a faint sepia or blue-green cast.
- **Lighting:** Dim, soft, directionless light with a few rim highlights; forms emerge from darkness.
- **Texture and surface:** Very dense relief: closely spaced ribs, grooves, pores, rivet-like nodes and interwoven tubes covering all surfaces.
- **Atmosphere and post-processing:** Deep ambient occlusion, slight haze, fine grain, vignette.
- **Camera and framing:** Symmetric frontal views of corridors and portals, or close views of surface detail.
- **UI and typography:** Frames look grown, not built: ribbed bone-grey borders, vertebra dividers and socket-shaped slots, with icons as embossed relief glyphs. Type is a thin, tall, condensed engraved capital face in bone `#b9b2a2`. Counters are small and sparse in the same bone tone, with no colour; health can be an organ-like gauge.
- **VFX and motion:** Slow drips, viscous strands, pale mist and puffs of spore-like dust; hits land as dull wet impacts with dark grey spray, never bright flashes. Motion is slow and heavy: tubes pulse, pistons flex like tendons, and creatures unfold deliberately.

## Fits

- **Genres:** `survival-horror`, `exploration`, `puzzle`, `fps`, `soulslike`
- **Moods:** oppressive, grotesque, unsettling
- **Settings:** derelict alien ship, living machine temple, bone-walled labyrinth

## Unreal recipe

### Assets

Store packs rarely match, so most of the set is generated: in Blender background mode, array ribbed tubes, vertebra columns, pelvis-shaped arches and tendon-like pistons along curves, mirror them for strict bilateral symmetry, and bake dense relief (ribs, grooves, pores, nodes, woven tubes) to normal and height maps from a high-poly source. Alien-hive or organic horror kits can be mixed in after desaturating their textures. Remove anything manufactured: flat panels, labels, screens, lamps, bolts in rows.

### Materials

One Default Lit master, `M_Biomech`. Base Colour is a greyscale texture remapped by a Curve Atlas ramp through the cold range `#0c0c0d`, `#2b2a28`, `#5b5852`, `#8c877c`, `#b9b2a2`, with no hue variation. Roughness 0.3 to 0.45 for a wet semi-gloss sheen, lowered further by a slime mask on undersides. Baked cavity and ambient-occlusion maps multiply Base Colour strongly so every groove sinks to black. Fleshy parts use Subsurface with a grey subsurface colour. Pulsing tubes use World Position Offset along the normal on a slow sine with a phase offset along UV.

### Lighting and atmosphere

Lumen global illumination and reflections on. Lighting is dim and directionless: a Sky Light with a plain dark grey cubemap, plus two or three large, weak Rect Lights placed behind forms as rim sources. No visible fixtures, no coloured light, no sun. Exponential Height Fog with Volumetric Fog at low density, neutral grey Albedo, for slight haze that swallows corridor ends. Virtual Shadow Maps on with soft sources. Manual exposure, held low.

### Post-processing

Ambient Occlusion Intensity 1 with a large Radius, adding to the baked cavities. Global Saturation 0.1, then a faint sepia or blue-green cast through Gain. Film Toe 0.65 for deep blacks. Film Grain Intensity 0.25, Vignette Intensity 0.6. Bloom Intensity 0.1, Lens Flare Intensity 0, Scene Fringe Intensity 0, Motion Blur Amount 0. Depth of field only for close surface studies. TSR anti-aliasing.

### UI and effects

UMG frames are rendered ribbed-bone borders as 9-slice images in `#8c877c`, with vertebra strips as dividers and socket-shaped slot backgrounds. Type is a thin, tall condensed face such as Cormorant SC Light or Poiret One in spaced capitals, `#b9b2a2`, small. Counters stay sparse and colourless; health is an organ-shaped gauge whose fill is driven by a User Interface material mask.

Niagara: slow drips as single mesh droplets every 2 to 5 s with a viscous ribbon strand that stretches and snaps; pale mist sprites near the floor, lifetime 8 s; spore dust puffs of 20 grey particles. Hits spray dark grey droplets with gravity for 0.4 s and add a wet decal; no sparks, no flash, no emissive.

## Do / Do not

Do:

- Merge bone and machine shapes.
- Cover every surface with ribs and tube relief.
- Keep the image monochrome.
- Use bilateral symmetry and repeated segments.

Do not:

- Do not use flat manufactured panels, labels and signal lights; that reads as `092`.
- Do not use gothic masonry and lantern colour; that reads as `031`.
- Do not use rubble and military hardware in daylight; that reads as `030`.
- Do not add colour accents.

## Nearest styles

- `092` Industrial used-future: this style has no colour, and every surface is covered in ribs and interwoven tubes; `092` has flat painted panels, stencil labels and amber, red and teal lights.
- `031` Gothic dark-fantasy realism: this style stays in one cold grey range and is built from bone-and-machine forms; `031` is stone masonry warmed by lantern and candle light.
- `030` Gritty desaturated war realism: this style is dim and enclosed, with smooth, wet organic relief; `030` is daylight rubble with chipped, scratched hard surfaces and military hardware.

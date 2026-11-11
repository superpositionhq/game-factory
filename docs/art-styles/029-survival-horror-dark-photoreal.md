# Survival-horror dark photoreal

Reference works: Resident Evil.

## References

- *Resident Evil 2* (2019), Capcom, video game. https://en.wikipedia.org/wiki/Resident_Evil_2_(2019_video_game)
- *Resident Evil 7: Biohazard* (2017), Capcom, video game. https://en.wikipedia.org/wiki/Resident_Evil_7:_Biohazard
- *Resident Evil Village* (2021), Capcom, video game. https://en.wikipedia.org/wiki/Resident_Evil_Village
- *Resident Evil 4* (2023), Capcom, video game. https://en.wikipedia.org/wiki/Resident_Evil_4_(2023_video_game)
- *Silent Hill 2* (2024), Bloober Team, video game. https://en.wikipedia.org/wiki/Silent_Hill_2_(2024_video_game)

## Visual definition

- **Shape language and proportions:** True-to-life proportions and scale. Cluttered, decayed interiors: narrow corridors, heavy doors, stacked furniture, exposed pipes.
- **Line and outline:** No outline.
- **Shading model:** Physically based, smooth, with accurate specular on wet and glossy surfaces.
- **Palette:** `#0b0c0d` `#2a2622` `#5a4a3a` `#7d1f1a` `#8c8676` `#3c4a3e` `#c9b990`. Near-black shadow, dirty browns and greys, sickly green and deep blood red accents.
- **Lighting:** Very low key. A single flashlight cone or a few weak practical lamps; most of the frame is in darkness. Hard contact shadows.
- **Texture and surface:** High-frequency realism: stains, peeling paint, wood grain, mould, wet patches with sharp reflections.
- **Atmosphere and post-processing:** Film grain, strong ambient occlusion, volumetric dust in the light cone, slight chromatic fringe and vignette.
- **Camera and framing:** Over-the-shoulder or first-person, 35 to 50 mm equivalent, tight interior framing.
- **UI and typography:** Minimal, almost frameless UI: a small grid inventory with thin grey borders and photographic item icons, and health shown as a heartbeat trace that turns from green to red. Text is a plain narrow grotesque sans, with a typewriter face for found documents; the ammo counter is small white numerals. UI colours are pale khaki `#c9b990` and grey `#8c8676`, with blood red `#7d1f1a` for danger.
- **VFX and motion:** Realistic muzzle flashes that light the room for an instant, blood spray with wet decals, sparks, and dust drifting in the light beam. Motion is weighty and motion-captured: slow, deliberate player movement and lurching enemies.

## Fits

- **Genres:** `survival-horror`, `third-person-shooter`, `fps`, `stealth`, `puzzle`
- **Moods:** tense, oppressive, claustrophobic
- **Settings:** derelict police station, rotting farmhouse, fog-bound town, underground laboratory

## Unreal recipe

### Assets

Photoscanned and realistic interior packs are used almost as delivered: corridors, heavy doors, stacked furniture, pipes, clutter. Keep 2K to 4K textures with full normal, roughness and ambient-occlusion maps; Nanite on for dense props. Add decay by script rather than removing detail: place DBuffer decals for stains, mould, peeling paint and blood, and scatter small debris meshes. Characters need realistic skin and cloth. Little needs building from scratch beyond bespoke puzzle objects.

### Materials

`M_DecayPBR`, Default Lit, standard metal-roughness inputs. A material function `MF_Wetness` uses a world-aligned puddle mask (stronger on up-facing surfaces via VertexNormalWS Z) to drop Roughness to 0.05 to 0.15, darken BaseColor by 30 percent and flatten the normal, giving sharp reflections on floors and walls. `MF_Grime` multiplies a dirt layer by the ambient-occlusion map. Skin uses Subsurface Profile; blood decals use low roughness. Instances per asset push hue toward `#5a4a3a`, `#3c4a3e` and `#8c8676`.

### Lighting and atmosphere

Lumen GI and reflections on, hardware ray tracing if available, Lumen Scene Lighting Quality 2. No sun and almost no Sky Light (intensity 0.05). The player's flashlight is a Spot Light with an IES profile, outer cone 25 to 30 degrees, casting Virtual Shadow Map shadows with Contact Shadow Length 0.05 for hard contact edges. Two or three weak practical Point Lights per area, some flickering from C++. Exponential Height Fog with Volumetric Fog on and the flashlight's Volumetric Scattering Intensity at 2, so dust shows only inside the beam. Auto Exposure Histogram with Min and Max EV100 locked close together, so darkness is never lifted.

### Post-processing

Film Grain Intensity 0.4, Vignette Intensity 0.6, Scene Fringe Intensity 0.5. Ambient Occlusion Intensity 0.9. Bloom Intensity 0.3 with Lens Flare Intensity 0. Film Toe raised to 0.6 and Black Clip 0.02 for dense blacks; a slight green cast in shadows via Gain, Saturation 0.9. Depth of field is weak, used only when aiming. Motion Blur Amount 0. No post-process materials. TSR at `r.ScreenPercentage` 67 or higher.

### UI and effects

A small inventory grid with 1 px `#8c8676` borders and item icons rendered from the real meshes by a scene capture script. Health is a heartbeat trace drawn by a User Interface material that scrolls a pulse line and lerps green to `#7d1f1a`. Text in Barlow Condensed, found documents in Special Elite, ammo count in small white numerals. Niagara: a 0.05 s muzzle flash sprite paired with a Light Renderer that lights the room, blood spray of 30 to 50 lit sprites ending in decals, 6 to 10 sparks, and slow dust motes confined to the flashlight cone.

## Do / Do not

Do:

- Light with one narrow source and leave the rest dark.
- Add wet low-roughness patches.
- Layer stains, peeling and mould.
- Apply film grain and vignette.

Do not:

- Do not raise ambient light; an evenly lit grey scene reads as `030`.
- Do not use gothic spires and blue moonlit fog; that reads as `031`.
- Do not use industrial sci-fi panels and teal monitors; that reads as `092`.
- Do not add neon signs and rain; that reads as `089`.

## Nearest styles

- `031` Gothic dark-fantasy realism: this style shows cluttered modern interiors under a flashlight, in many dirty browns, greens and reds; `031` shows ornate carved stone under cold moonlight and fog, in a narrow blue-grey range.
- `092` Industrial used-future: here surfaces rot, with mould, stains and peeling paint in near-total darkness; `092` has worn but orderly painted metal panels lit by amber beacons and teal monitors, with a little more light.
- `085` Baroque chiaroscuro: colour here is cold and dirty and detail is sharp and grimy; `085` has warm golden light on smooth glazed surfaces.

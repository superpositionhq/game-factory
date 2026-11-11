# Bioluminescent alien jungle

Reference works: Avatar (2009).

## References

- *Avatar* (2009), James Cameron, live-action and computer-animated film. https://en.wikipedia.org/wiki/Avatar_(2009_film)
- *Avatar: The Way of Water* (2022), James Cameron, live-action and computer-animated film. https://en.wikipedia.org/wiki/Avatar:_The_Way_of_Water
- *Avatar: Frontiers of Pandora* (2023), Massive Entertainment, video game. https://en.wikipedia.org/wiki/Avatar:_Frontiers_of_Pandora
- *Subnautica* (2018), Unknown Worlds Entertainment, video game. https://en.wikipedia.org/wiki/Subnautica

## Visual definition

- **Shape language and proportions:** Dense alien jungle at night: giant trees with buttress roots, hanging vines, fan-shaped and spiral plants, mushroom caps, floating seeds like small jellyfish, moss carpets. Organic forms at many scales.
- **Line and outline:** No outline.
- **Shading model:** Realistic smooth shading in very low light, with self-illuminated patterns and soft subsurface glow in leaves.
- **Palette:** `#030812` `#0a2a3a` `#19e6c8` `#3a7bff` `#c44dff` `#7dff6a` `#ff6ad5`. Blue-black darkness with cyan, teal, violet, magenta and green bioluminescence.
- **Lighting:** No sun. Light comes from glowing dots, veins and fringes on plants and creatures; glow intensifies where things are touched. Faint blue moonlight from above.
- **Texture and surface:** Glowing vein networks and dot rows on leaves, speckled moss, wet bark; fine natural detail.
- **Atmosphere and post-processing:** Bloom, depth of field, drifting glowing particles, light mist.
- **Camera and framing:** Inside the forest at eye level looking through layered foliage; 35 mm equivalent, shallow focus.
- **UI and typography:** Thin glowing line frames and soft-edged translucent blue-black panels, with icons drawn as luminous organic glyphs (leaf, spiral, seed). Type is a light rounded sans with a faint glow. Counters are slim cyan `#19e6c8` numerals, with magenta `#ff6ad5` for damage and green `#7dff6a` for healing.
- **VFX and motion:** Drifting glowing spores, ripples of light that spread across plants where they are touched, and floating seeds that pulse; hits burst into luminous motes that fade slowly. Motion is fluid and organic: swaying fronds, gliding creatures, gentle ease in and out.

## Fits

- **Genres:** `exploration`, `survival-craft`, `action-adventure`, `stealth`, `rpg`
- **Moods:** wondrous, serene, mysterious
- **Settings:** alien jungle at night, glowing cave, deep ocean reef, forested alien moon

## Unreal recipe

### Assets

Start from realistic, dense foliage: tropical or fantasy jungle packs with giant buttress-root trees, vines, ferns, fan plants, mushrooms and moss, as Nanite meshes with full normal detail. Add by script an emissive mask for each plant texture: Pillow traces vein networks from the albedo's green channel and stamps dot rows along leaf edges. Build floating jellyfish-like seeds, spiral plants and glowing fringe strips in Blender.

### Materials

Foliage master: Two Sided Foliage shading model, Base Colour darkened to the `#030812` to `#0a2a3a` range, Subsurface Colour teal. Emissive Color = vein mask × hue parameter × pulse, with the hue chosen per instance from `#19e6c8`, `#3a7bff`, `#c44dff`, `#7dff6a` and `#ff6ad5` and varied by PerInstanceRandom. A touch response is added in the same master: a Material Parameter Collection holds the last few touch positions and times, and a sphere mask on WorldPosition expanding with time brightens the veins as a ripple. Bark is Default Lit, wet (Roughness 0.3), with a moss blend on upward faces. Wind sway uses World Position Offset.

### Lighting and atmosphere

No sun. One Directional Light as moonlight, blue `#3a7bff`, about 0.1 lux, with soft shadows. Lumen global illumination on so emissive veins light nearby leaves; add small Point Lights without shadows at the brightest plants and creatures because thin emissive detail alone gives noisy bounce. Sky Light very low, blue-black. Exponential Height Fog with Volumetric Fog on, low density, Albedo tinted `#0a2a3a`, for light mist that picks up glow. Virtual Shadow Maps on. Manual exposure fixed for night.

### Post-processing

Bloom Intensity 1, Threshold 0.6, so veins and dots glow softly. Depth of field active in play: 35 mm equivalent, about f/2, focused on the player, which blurs foreground leaves into coloured discs. Filmic tone curve; Shadows tinted blue; Global Saturation 1.15. Vignette Intensity 0.4. Film Grain Intensity 0.1, Scene Fringe Intensity 0, Motion Blur Amount 0. TSR anti-aliasing. No outline, banding or painterly filter: fine realistic leaf detail must survive.

### UI and effects

UMG panels are translucent blue-black `#030812` at 70% with soft feathered edges and a 1 px glowing line frame. Font is Quicksand Light or Nunito Light with a faint glow from a blurred duplicate text layer. Counters are slim `#19e6c8` numerals; damage is `#ff6ad5`, healing `#7dff6a`.

Niagara: 150 to 300 drifting spore sprites around the camera, additive, lifetime 6 to 10 s, moved by curl noise, cycling slowly in brightness. Floating seeds are mesh particles pulsing on a 2 s sine. Hits burst into 40 luminous motes that slow with drag and fade over 1.5 s.

## Do / Do not

Do:

- Light the scene only from glowing plants and a faint moon.
- Put vein and dot patterns on leaves.
- Use several glow hues: cyan, violet, magenta, green.
- Add drifting glowing particles and bloom.

Do not:

- Do not simplify into soft painted shapes with a glowing hero; that reads as `027`.
- Do not use straight emissive circuit lines on geometric solids; that reads as `088`.
- Do not add urban neon signs and rain; that reads as `089`.
- Do not add daylight.

## Nearest styles

- `027` Glowing forest painterly: this style shows realistic, finely detailed plants in deep darkness with many vivid glow colours; `027` is lighter and softer, with simplified painted shapes and one glowing hero.
- `088` Neon grid cyberspace: glow here follows veins and dot rows on dense organic foliage in many hues; `088` is straight glowing lines on bare geometric solids in only a few colours.
- `089` Rain-soaked tech-noir: light here comes from plants and creatures in vivid cyan, violet and magenta; `089` is a city where neon signs reflect in wet streets, with duller colour between the lights.

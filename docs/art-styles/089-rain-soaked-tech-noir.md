# Rain-soaked tech-noir

Reference works: Blade Runner.

## References

- *Blade Runner* (1982), Ridley Scott, live-action film. https://en.wikipedia.org/wiki/Blade_Runner
- *Blade Runner 2049* (2017), Denis Villeneuve, live-action film. https://en.wikipedia.org/wiki/Blade_Runner_2049
- *Cyberpunk 2077* (2020), CD Projekt Red, video game. https://en.wikipedia.org/wiki/Cyberpunk_2077
- *Deus Ex: Human Revolution* (2011), Eidos-Montreal, video game. https://en.wikipedia.org/wiki/Deus_Ex:_Human_Revolution
- *The Fifth Element* (1997), Luc Besson, live-action film. https://en.wikipedia.org/wiki/The_Fifth_Element

## Visual definition

- **Shape language and proportions:** Dense vertical city at street level: massive towers with added pipes and ducts, stacked signs, market stalls, overhead cables, flying vehicles. Layers of old and new construction.
- **Line and outline:** No outline.
- **Shading model:** Physically based and smooth; wet surfaces with strong reflections.
- **Palette:** `#0b0e14` `#1c2a3a` `#ff3b6b` `#18c8e8` `#f2a23a` `#6b4fd8` `#3a3a3a` `#d8e6f0`. Dark blue-black night with neon magenta, cyan, amber and violet light; smog glows in the colour of nearby signs.
- **Lighting:** Night and rain. Light comes from neon signs, video billboards, shop fronts and searchlights sweeping through haze.
- **Texture and surface:** Grimy concrete and metal, wet asphalt with puddles, steam, rain streaks, dense signage with glyphs.
- **Atmosphere and post-processing:** Volumetric haze, bloom, anamorphic horizontal flare streaks, rain, film grain, slight chromatic fringe.
- **Camera and framing:** Street-level or mid-air canyon views with 28 to 40 mm equivalent; shallow depth for close shots.
- **UI and typography:** Overlays are thin-line holographic displays in cyan and amber with slight flicker and scan noise; panels are dark translucent glass, and icons are simple line glyphs like street signage. Text is a condensed technical sans in capitals, with a monospaced terminal face for readouts. Numbers are monospaced, amber for normal values and magenta-red for damage.
- **VFX and motion:** Rain streaks, puddle splashes, steam from vents, sparks from broken signs and muzzle flashes that light the haze. Hits throw sparks, glass and wet spray. Motion is weighty and realistic, with slow camera drift.

## Fits

- **Genres:** `detective-mystery`, `third-person-shooter`, `fps`, `stealth`, `rpg`, `action-adventure`
- **Moods:** brooding, melancholic, tense
- **Settings:** rainy megacity street, neon night market, corporate tower, rooftop landing pad

## Unreal recipe

### Assets

Realistic city packs fit directly: modular towers, alleys, market stalls, signage, pipes, ducts, cables, vehicles. Keep full PBR texture sets and Nanite meshes. Kitbash for density: stack signs, add duct runs and overhead cable splines to every facade, and layer old brick beneath newer metal. Build sign faces (glyph textures on emissive planes) and billboard panels by script.

### Materials

Default Lit throughout. Add a `MF_Wetness` material function to every environment master: it lowers Roughness to 0.05 to 0.2, darkens Base Colour by 30%, and blends a puddle mask (WorldAlignedTexture noise gated by upward-facing VertexNormalWS) toward a flat normal so puddles mirror. A panning ripple normal and vertical rain-streak normals on walls use Panner and Time. Signs use Emissive Color at 20 to 60 in magenta `#ff3b6b`, cyan `#18c8e8`, amber `#f2a23a` and violet `#6b4fd8`, with a flicker parameter. Glass is Thin Translucent. DBuffer decals add leaks and stains.

### Lighting and atmosphere

Night. Lumen global illumination and reflections on, hardware ray tracing if available so wet streets reflect off-screen signs. No sun; a Sky Light at low intensity tinted `#1c2a3a`. Light with many Rect Lights at shop fronts and signs matching the emissive colours, plus two or three moving Spot Lights as searchlights. Exponential Height Fog with Volumetric Fog enabled, Fog Density about 0.05, Albedo grey, Scattering Distribution 0.6, and each sign light's Volumetric Scattering Intensity at 2 to 4 so smog glows in the nearest sign's colour. Auto exposure with a narrow range (Min/Max EV100 about 1 apart).

### Post-processing

Filmic tone curve at defaults. Bloom Method Convolution with a horizontally stretched kernel texture for anamorphic streaks, Intensity 0.8; or Standard bloom plus Lens Flare Intensity 0.3. Film Grain Intensity 0.3, Scene Fringe Intensity 0.5, Vignette Intensity 0.4. Colour grading: Shadows toward blue-teal, Global Saturation 0.9 so colour between the lights stays dull, Contrast 1.1. Depth of field only in close shots (f/2, 35 mm). Motion Blur Amount 0. TSR anti-aliasing.

### UI and effects

UMG overlays are thin-line holographic frames in cyan and amber on dark glass panels (Background Blur widget behind a `#0b0e14` fill at 60% alpha). Wrap the HUD in a Retainer Box whose effect material adds faint scanline noise and a 2% opacity flicker. Labels use Barlow Condensed capitals; readouts use IBM Plex Mono, amber for normal values and `#ff3b6b` for damage.

Niagara: GPU-sprite rain as stretched velocity-aligned streaks across the camera volume, with splash flipbooks on puddles; steam columns from vents as lit volumetric-looking sprites that catch sign colours; sign sparks as amber streaks with a Light renderer, 0.4 s. Hits throw sparks, glass shards as small meshes and a wet spray burst.

## Do / Do not

Do:

- Make it night, wet and hazy.
- Light the scene from signs and billboards.
- Reflect neon in wet ground.
- Stack signage and pipes on large tower masses.

Do not:

- Do not draw cel bands and ink lines; that reads as `017`.
- Do not reduce to emissive lines on black; that reads as `088`.
- Do not use a clean gradient sunset and grid; that reads as `090`.
- Do not use an empty dark interior with one flashlight; that reads as `029`.

## Nearest styles

- `017` Neon megacity 1980s anime: this style has no drawn line and smooth realistic shading with wet reflections; `017` has ink outlines and flat cel tone bands.
- `029` Survival-horror dark photoreal: this style is full of coloured neon light reflected in wet streets; `029` is nearly colourless, an empty dark interior lit by one flashlight.
- `093` Bioluminescent alien jungle: this style has hard urban surfaces of concrete, metal and signs, with neon dulled by smog; `093` has organic plants and creatures that glow in vivid colour.

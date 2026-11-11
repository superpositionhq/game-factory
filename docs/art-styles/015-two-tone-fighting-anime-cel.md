# Two-tone fighting-anime cel

Reference works: Guilty Gear Xrd.

## References

- *Guilty Gear Xrd* (2014), Arc System Works, video game. https://en.wikipedia.org/wiki/Guilty_Gear_Xrd
- *Dragon Ball FighterZ* (2018), Arc System Works, video game. https://en.wikipedia.org/wiki/Dragon_Ball_FighterZ
- *Guilty Gear Strive* (2021), Arc System Works, video game. https://en.wikipedia.org/wiki/Guilty_Gear_Strive
- *Naruto: Ultimate Ninja Storm* (2008), CyberConnect2, video game. https://en.wikipedia.org/wiki/Naruto:_Ultimate_Ninja_Storm

## Visual definition

- **Shape language and proportions:** Dynamic anime figures: long legs, sharp angular hair chunks, oversized weapons and belts. Forms are designed so shadow shapes look drawn.
- **Line and outline:** Clean black outline, 2 to 3 px, tapering to nothing at some points; a few drawn inner lines (muscle, folds).
- **Shading model:** Two bands with a crisp edge whose shape is art-directed (edited normals). Shadow colour is a hue-shifted, saturated tint. Hard-edged specular shapes on hair and metal.
- **Palette:** `#141414` `#e63946` `#f1faee` `#ffb703` `#219ebc` `#8338ec` `#ffd6a5`. Strong character colours (red, gold, blue, purple) with pure white highlights.
- **Lighting:** Light direction follows the character, not the scene, to keep shadow shapes attractive.
- **Texture and surface:** Flat colour. Inner lines are stored as straight, axis-aligned texture strokes so they stay sharp.
- **Atmosphere and post-processing:** Bright bloom on effects only; otherwise clean.
- **Camera and framing:** Side-on fighting view or dramatic close-ups with speed lines.
- **UI and typography:** Sharp angled health and tension bars with black frames, gold trim and red or blue fills; character portraits sit in slanted cut frames. Text is a heavy italic display face with pointed corners, joined by rough brush-script callouts for round starts and knockouts. Combo and damage counters are large slanted white numerals with a black outline that punch in at oversize and settle.
- **VFX and motion:** Effects look hand-drawn: flat-colour slash arcs, jagged impact stars, smoke drawn as solid shapes and bright beams with bloom. Animation uses snappy held poses with stepped timing, hit-stop freezes on contact, smear frames and brief full-screen flashes.

## Fits

- **Genres:** `fighting`, `hack-and-slash`, `action-adventure`, `rpg`, `roguelike`
- **Moods:** intense, flashy, heroic
- **Settings:** tournament arena, ninja village, ruined gothic city, floating sky fortress

## Unreal recipe

### Assets

Characters carry this style and need preparation beyond a store rig. In Blender background mode, transfer normals from simplified proxy shapes (spheres for heads, capsules for limbs) onto faces, hair chunks and cloth, so shadow edges come out as clean curves. Store per-vertex outline width in vertex colour alpha, 0 at hair tips and spikes. Inner lines (muscle, folds) are drawn into a texture as straight axis-aligned strokes on rectified UVs so they stay sharp at any distance. Stages can come from packs with textures flattened to plain colour.

### Materials

`M_FightCel`, Unlit. The light vector is a per-character parameter set from C++ through Custom Primitive Data, so it follows the character and is tuned per pose, not taken from the scene. Shading: `Step(Threshold, N·L + ShadowMask)` where a painted mask texture forces or forbids shadow by region. Lit and shadow colours are separate textures; shadow tints are chosen by hand, hue-shifted and saturated (skin `#ffd6a5` toward red-violet). A second Step on the half-vector, gated by a painted highlight mask, gives hard white shapes on hair and metal. Outline: inverted hull as Overlay Material (Masked, two-sided, back faces via TwoSidedSign) in `#141414`, with World Position Offset along the normal scaled by vertex alpha and camera distance for 2 to 3 px that tapers to nothing.

### Lighting and atmosphere

Characters ignore scene lights. Light the stage simply: Lumen off, one Directional Light for stage shadows, flat Sky Light, no fog or haze. Blob or projected shadows under fighters. Manual exposure.

### Post-processing

Clean frame: Tone Curve Amount 0.2, Global Saturation 1.1, no grain, vignette, fringe or depth of field, Motion Blur Amount 0 (smears are drawn, not blurred). Bloom Intensity 0.8 with Threshold above 2, and only effect materials emit above that level, so characters never glow. No post-process line pass, because screen-space edges cannot taper. FXAA or TSR at 100 percent; razor shadow edges matter more than softness.

### UI and effects

Health and tension bars are angled Progress Bars with black frames, gold `#ffb703` trim and red `#e63946` or blue `#219ebc` fills; portraits sit in slanted masked frames. Text is a heavy italic face (Anton or Russo One with shear); round calls use a brush script (Rock Salt, Permanent Marker). Combo digits are white with a black font outline, punching in at 160 percent and settling in 0.12 s. Niagara: flat-colour slash arc meshes with a panning erosion mask (0.2 s), jagged impact star sprites, solid drawn smoke flipbooks stepped at 12 fps, emissive beams. Add 3 to 6 frames of hit-stop and a one-frame white flash on heavy contact.

## Do / Do not

Do:

- Edit normals so shadow edges are simple drawn curves.
- Pick shadow colours by hand per region.
- Taper outline width to zero at spikes and tips.
- Use hard-edged specular shapes.

Do not:

- Do not use the mesh's raw normals on faces; noisy shadow shapes break the look.
- Do not add graffiti textures and uniform fat lines; that reads as `004`.
- Do not soften bands and add gradient ramps and haze; that reads as `018`.
- Do not add hatching; that reads as `001`.

## Nearest styles

- `018` Soft open-world anime cel: `018` has thin tinted outlines, soft shadow edges, pastel colour and light haze; this style has black tapered outlines, razor-sharp shadow edges and strong colour.
- `004` Graffiti street cel: `004` wraps everything in fat lines of one width and covers walls and clothes with graffiti art; this style tapers its lines to points and keeps surfaces as plain flat colour.
- `019` Mecha panel-line cel: `019` shows white armoured machines with a few primary colour blocks and straight panel lines; this style shows organic characters in many strong colours with curved, drawn shadow shapes.

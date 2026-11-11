# Papercraft

Reference works: Tearaway; Paper Mario.

## References

- *Tearaway* (2013), Media Molecule, video game. https://en.wikipedia.org/wiki/Tearaway_(video_game)
- *Paper Mario: The Origami King* (2020), Intelligent Systems, video game. https://en.wikipedia.org/wiki/Paper_Mario:_The_Origami_King
- *Paper Mario: The Thousand-Year Door* (2004), Intelligent Systems, video game. https://en.wikipedia.org/wiki/Paper_Mario:_The_Thousand-Year_Door
- *Lumino City* (2014), State of Play Games, video game. https://en.wikipedia.org/wiki/Lumino_City

## Visual definition

- **Shape language and proportions:** Everything is cut and folded from flat sheets: boxes with tabs, cones rolled from sectors, fringed grass strips, layered cut-outs, accordion folds. Thickness is that of card, and faces stay planar or singly curved.
- **Line and outline:** No drawn outline. Sheet edges show as a thin lighter or darker rim.
- **Shading model:** Each flat panel has one tone, so folded forms show two to four planar steps. Soft contact shadows between layers.
- **Palette:** `#f7f3e8` `#ef5350` `#ffca28` `#42a5f5` `#66bb6a` `#8d6e63` `#ab47bc`. Bright construction-paper colours on cream; each sheet is one solid colour.
- **Lighting:** Soft overhead light with clear, soft drop shadows that separate paper layers.
- **Texture and surface:** Fine paper fibre, faint fold creases, slightly rough cut edges, occasional glue tab or pencil mark.
- **Atmosphere and post-processing:** Slight depth of field. Animation may be stepped.
- **Camera and framing:** Slightly raised three-quarter view, 40 to 50 mm equivalent, like a tabletop model.
- **UI and typography:** Panels are cut paper cards and torn-edge scraps stacked with small drop shadows and held by tape or pins; icons are simple paper cut-outs, stickers and ink stamps. Lettering is chunky cut-out capitals or rounded marker handwriting, and counters are big cut-paper digits in cream `#f7f3e8` on a red, yellow or blue backing sheet.
- **VFX and motion:** Particles are confetti scraps, paper curls and folded stars; water and smoke are paper strips that unroll, and a hit crumples or tears the figure. Things appear by unfolding like a pop-up book or flipping like a turned card, with snappy stepped animation and flutter at loose edges.

## Fits

- **Genres:** `platformer`, `puzzle`, `action-adventure`, `rpg`, `exploration`, `tower-defense`
- **Moods:** playful, cheerful, handmade
- **Settings:** pop-up storybook world, paper town, folded forest, tabletop model city

## Unreal recipe

### Assets

Build nearly everything by script, because real paper forms are developable: boxes with glue tabs, cones rolled from sectors, accordion strips, fringed grass, stacked cut-outs. In Blender background mode, make each sheet as a flat or singly curved surface and add a Solidify thickness of about 0.3 to 0.5 mm scaled to the scene, so cut edges show. A store pack can only donate silhouettes: trace its props as layered flat cut-outs with small gaps between layers. Characters are folded-box bodies with flat card limbs on a simple rig.

### Materials

`M_Paper`: Default Lit, Two Sided. Base Color is one `SheetColour` parameter per sheet (`#ef5350`, `#ffca28`, `#42a5f5`, `#66bb6a`, `#ab47bc`, cream `#f7f3e8`) multiplied by a fine fibre texture at 5 percent contrast. Roughness 0.9, Specular 0.2, a faint fibre normal map and an optional crease normal along fold lines. Edge faces (identified by a second material slot or a vertex-colour flag) lerp 15 percent lighter to show the paper core. Flat-shaded normals on every panel give each fold one tone, so forms read in two to four planar steps. Fibre and real shadow separate it from flat unlit poster layers and from smooth untextured primitives.

### Lighting and atmosphere

Lumen GI on, which gives colour bleed between bright sheets. One large Rect Light or a Directional Light with a wide Source Angle from above for soft drop shadows; Contact Shadows on so layers a few millimetres apart still separate. Sky Light from a plain white cubemap. Distance Field Ambient Occlusion or Ambient Occlusion Intensity 0.6 with a small radius for the gaps. No fog or sky; a paper backdrop sheet. Manual exposure, bright.

### Post-processing

Depth of Field at f/4 to f/5.6 on a 40 to 50 mm camera, slight. TSR on. Bloom 0.1, Vignette 0.2, no grain, no fringe, Motion Blur Amount 0. Tone curve default with Saturation 1.05. No post materials. Optionally tick animation at 12 fps for a stepped feel.

### UI and effects

Panels are paper cards and torn-edge scraps (Box brushes with alpha-cut edges) stacked with small offset drop shadows and a tape or pin image at one corner. Headings in Bangers or Archivo Black look cut out; notes in Patrick Hand. Counters are big cream digits on a red, yellow or blue backing sheet that flips like a turned card when the value changes. Niagara with mesh renderers: confetti squares and paper curls using `M_Paper` (20 to 40, lifetime 1.5 s, tumbling, with drag), folded stars on impact. Water and smoke are rolled strip meshes that unroll by scale and rotation. Objects enter by unfolding along hinge bones.

## Do / Do not

Do:

- Use only flat or singly curved sheet forms.
- Stack layers with small gaps and soft shadows.
- Keep one solid colour per sheet.
- Show sheet thickness at cut edges.

Do not:

- Do not use doubly curved smooth surfaces; that reads as `048`.
- Do not flatten everything into unshaded poster layers; that reads as `064`.
- Do not use fabric fuzz and stitching; that reads as `051`.
- Do not use pure geometric primaries on white with no paper texture; that reads as `098`.

## Nearest styles

- `064` Mid-century cut-paper poster: `064` is flat, unlit poster layers in a handful of colours; this style has soft shadows between layers, light and dark sides on every fold, and more colours.
- `098` Bauhaus primary geometry: `098` uses solid, smooth primitives in a few primaries with no surface texture; this style uses thin folded sheets with visible paper fibre.
- `067` Boxy toybox low-poly: `067` is solid boxy forms in many strong colours; this style is thin sheets with faint paper fibre and slightly softer colour.

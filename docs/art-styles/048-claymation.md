# Claymation

Reference works: Wallace & Gromit.

## References

- *Wallace & Gromit: The Wrong Trousers* (1993), Aardman Animations (Nick Park), stop-motion film. https://en.wikipedia.org/wiki/The_Wrong_Trousers
- *Chicken Run* (2000), Aardman Animations, stop-motion film. https://en.wikipedia.org/wiki/Chicken_Run
- *Shaun the Sheep Movie* (2015), Aardman Animations, stop-motion film. https://en.wikipedia.org/wiki/Shaun_the_Sheep_Movie
- *The Neverhood* (1996), The Neverhood, Inc., video game. https://en.wikipedia.org/wiki/The_Neverhood
- *Pingu* (1990), Otmar Gutmann, stop-motion TV series. https://en.wikipedia.org/wiki/Pingu

## Visual definition

- **Shape language and proportions:** Rounded, hand-formed blobs: thick limbs, wide mouths, bulging eyes set close together, sausage fingers. No sharp edges; every corner is pressed round.
- **Line and outline:** No outline.
- **Shading model:** Smooth and soft, with a waxy sheen and slight subsurface softness.
- **Palette:** `#e9d2a6` `#c9793a` `#6e9b5b` `#4a78b0` `#b5483a` `#f3efe4` `#5b4636`. Warm, slightly muted plasticine colours: tan, orange-brown, green, blue, brick red, cream.
- **Lighting:** Small-studio lighting: one soft key, fill and a rim, with soft contact shadows on a miniature set.
- **Texture and surface:** Fingerprints, thumb dents, tool marks and tiny lumps on every clay surface. Sets mix in real miniature materials (wood, fabric, wallpaper).
- **Atmosphere and post-processing:** Shallow depth of field as in macro photography; animation stepped at 12 frames per second.
- **Camera and framing:** Close, macro-like, 50 to 85 mm equivalent, eye level with the puppets.
- **UI and typography:** Panels and buttons look pressed from clay slabs or cut from cardboard, with rounded edges and thumb dents; icons are small clay models of the objects. Lettering is a soft, chunky rounded sans that looks rolled from clay ropes, and counters are fat rounded digits in cream `#f3efe4`, brick red `#b5483a` and blue `#4a78b0`.
- **VFX and motion:** Effects are made from physical materials: cotton-wool smoke, clay pellets and blobs for splashes, clear gel for water, cut-card stars on impact. Animation runs on twos with strong squash and stretch, mouth shapes that pop from one pose to the next, and a slight shimmer on clay surfaces between frames.

## Fits

- **Genres:** `puzzle`, `platformer`, `action-adventure`, `detective-mystery`, `stealth`
- **Moods:** cosy, comic, warm
- **Settings:** English village, farmyard, inventor's workshop, wallpapered living room

## Unreal recipe

### Assets

Choose chunky cartoon packs with thick limbs and wide faces, or build props in Blender background mode from metaballs and bevelled primitives. Round every hard edge with a bevel and a subdivision pass, then break symmetry by a small displacement from a noise texture so nothing is machine-true. Strip the pack's albedo detail to one clay colour per part. Sets may keep real miniature materials (wood grain, wallpaper, cloth), scaled up so the grain looks oversized. Hands, mouths and replacement face shapes are best built from scratch.

### Materials

`M_Clay`: shading model Subsurface, Base Color and Subsurface Color both from one `ClayColour` parameter (`#c9793a`, `#6e9b5b`, `#4a78b0`, `#b5483a`), Opacity about 0.6 for waxy softness, Roughness 0.45 to 0.6. A tiling fingerprint normal map and a thumb-dent normal map are blended with WorldAlignedTexture so no UV work is needed; the same masks add roughness variation. A `Boil` parameter offsets the fingerprint UVs by a random step, changed 12 times a second from C++ through a Material Parameter Collection, giving the surface shimmer between frames. Fingerprints and the matte-waxy response are what keep it from reading as clean moulded plastic.

### Lighting and atmosphere

Lumen GI on for soft bounce inside the small set. Three Rect Lights as a studio rig: a warm soft key, a weaker fill, a rim from behind. Contact Shadows on with a short Contact Shadow Length, Virtual Shadow Maps, generous source size for soft penumbra. No Sky Atmosphere; a painted backdrop card. No fog. Manual exposure.

### Post-processing

Macro depth of field: Aperture f/2 to f/2.8, 50 to 85 mm, focus on the puppet. TSR on. Bloom Intensity 0.2, Vignette 0.3, Film Grain 0.15, a small warm White Balance shift. Motion Blur Amount 0, which also matches stop motion. No post materials. Stepped timing comes from animation, not from frame rate: tick skeletal animation at 12 fps from C++ (update the pose every second frame at 24, held between) while the camera stays smooth.

### UI and effects

Panels look pressed from slabs: Rounded Box brushes with a rendered clay texture, thumb dents in the corners and a soft drop shadow; some are cut cardboard. Text in Fredoka or Baloo 2, cream `#f3efe4` with brick red `#b5483a` and blue `#4a78b0` accents; counters are fat rounded digits that squash on change. Niagara uses mesh renderers with the clay material: cotton-wool smoke as lumpy white spheres (5 to 8, lifetime 1.2 s), splashes as clay pellets, impact stars as flat card meshes. Update particle positions on twos as well.

## Do / Do not

Do:

- Round every edge and break symmetry.
- Add fingerprints and thumb dents.
- Use macro depth of field.
- Step animation at 12 poses per second.

Do not:

- Do not make surfaces perfectly smooth and glossy; that reads as `057` or `052`.
- Do not use thin spindly forms in dark desaturated sets; that reads as `049`.
- Do not use fabric fuzz and stitches; that reads as `051`.
- Do not use hard-edged geometry.

## Nearest styles

- `049` Gothic stop-motion puppet: `049` is dark and muted, with thin spindly puppets on crooked sets; this style is bright and warm, with chunky rounded figures.
- `057` Toy-diorama tilt-shift: `057` is clean, glossy plastic with no marks; this style shows fingerprints and thumb dents on waxy clay.
- `051` Felt and yarn: `051` has fibre fuzz and visible stitches on every surface; this style is smooth clay with fingerprints and no stitch lines.

# Bauhaus primary geometry

Reference works: Triadic Ballet; Bauhaus Dessau.

## References

- *Triadic Ballet* (1922), Oskar Schlemmer, ballet costume and stage design. https://en.wikipedia.org/wiki/Triadisches_Ballett
- *Bauhaus Dessau building* (1926), Walter Gropius, architecture. https://en.wikipedia.org/wiki/Bauhaus_Dessau
- *Yellow-Red-Blue* (1925), Wassily Kandinsky, oil painting. https://en.wikipedia.org/wiki/Wassily_Kandinsky
- *Wassily Chair* (1926), Marcel Breuer, furniture. https://en.wikipedia.org/wiki/Wassily_chair
- *Bauhaus chess set* (1924), Josef Hartwig, product design. https://en.wikipedia.org/wiki/Josef_Hartwig

## Visual definition

- **Shape language and proportions:** Pure primitives: sphere, cube, cylinder, cone, disc and ring, combined without ornament. Figures are assembled from them (sphere head, cone skirt, cylinder limbs, disc collar). Furniture is bent tube and flat plane. Each basic shape is paired with a colour: triangle or cone yellow, square or cube red, circle or sphere blue.
- **Line and outline:** No outline. Thin black rods and tubes appear as real elements.
- **Shading model:** Soft, simple volume shading with two to four gentle steps, enough to read the solid; matte.
- **Palette:** `#f5f2ea` `#e63329` `#1c4fa1` `#f7c81e` `#141414` `#bfbfbf`. Red, blue and yellow on white, with black and neutral grey.
- **Lighting:** Even studio light with soft shadows on a white ground.
- **Texture and surface:** None. Smooth matte paint; chromed steel tube on furniture.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** Clear frontal or three-quarter object views on a white stage; orthographic or long lens.
- **UI and typography:** Flat rectangles, circles and triangles on a strict grid, with thin black rules and no bevels or borders; icons are built from the same three shapes. Type is a geometric sans, often all lowercase, in black `#141414`. Counters are bold geometric numerals, with red, blue or yellow blocks as status colours.
- **VFX and motion:** Flat geometric bursts: discs, rings, triangles and squares in primary colours that pop out and shrink away, with no smoke or glow. Motion is precise and mechanical, like a stage ballet: rotations, straight slides and puppet-like held poses with snappy changes.

## Fits

- **Genres:** `puzzle`, `strategy`, `platformer`, `tower-defense`, `sports`
- **Moods:** playful, orderly, cerebral
- **Settings:** white stage, design school studio, abstract board game, geometric theatre

## Unreal recipe

### Assets

Build everything from primitives by Geometry Script or Blender: spheres, cubes, cylinders, cones, discs and rings with enough segments to look perfectly round. Characters are assemblies of these (sphere head, cone skirt, cylinder limbs, disc collar) parented to a simple skeleton as rigid parts, so they animate like stage puppets. Furniture is swept steel tube plus flat planes; thin black rods are real cylinders. Store packs do not suit this style.

### Materials

One Default Lit master, `M_BauhausMatte`: a `Colour` parameter, Roughness 0.9, Specular 0.2, no textures, no normal map. Assign colour by shape and keep the rule everywhere: cones and triangles `#f7c81e`, cubes and squares `#e63329`, spheres and circles `#1c4fa1`; neutral parts use `#f5f2ea`, `#141414` or `#bfbfbf`. A second instance type, chrome tube, is Metallic 1 with Roughness 0.15 and is used only on furniture. The gentle tone steps come from a post-process material, described below. No studs, bevel highlights, decals or gloss on coloured solids.

### Lighting and atmosphere

Studio set-up on a white `#f5f2ea` floor that curves up into the backdrop. One large Rect Light as key from front-left, one weaker Rect Light as fill, and a Sky Light with a plain white cubemap. Shadows are soft: Virtual Shadow Maps with large source sizes. Lumen global illumination on at default quality for light colour bleed onto the white floor. No fog, no sky. Manual exposure with the floor just under white. Use an orthographic camera or a long lens (field of view 20 to 30 degrees).

### Post-processing

A post-process material at Scene Color Before Bloom recovers the light term (PostProcessInput0 divided by DiffuseColor), quantises it to three steps with a narrow SmoothStep at each boundary so the steps are gentle, and multiplies back. Chrome is excluded by masking on the Metallic scene texture. Volume: Tone Curve Amount 0.2, Expand Gamut 0, Bloom Intensity 0, Film Grain Intensity 0, Vignette Intensity 0, Ambient Occlusion Intensity 0.3, Motion Blur Amount 0, depth of field off. TSR anti-aliasing. No outline pass and no black bars drawn in screen space.

### UI and effects

UMG is flat rectangles, circles and triangles on a strict grid with 1 px black rules; no bevels, borders or shadows. Text uses Jost or League Spartan, lowercase, in `#141414`. Counters are bold geometric numerals; status is a red square, blue circle or yellow triangle block.

Niagara: flat unlit mesh particles (discs, rings, triangles, squares) in the three primaries, 6 to 12 per burst, that scale up in 0.1 s and shrink to nothing by 0.4 s, moving in straight lines at constant speed. No smoke, glow or blending.

## Do / Do not

Do:

- Build only from exact geometric primitives.
- Use red, blue and yellow with white, black and grey.
- Pair cone with yellow, cube with red, sphere with blue.
- Present on a plain white stage.

Do not:

- Do not restrict to rectangles with black bars and no shading; that reads as `079`.
- Do not add diagonal thrust, paper texture and red-black only; that reads as `080`.
- Do not add studs and gloss; that reads as `052`.
- Do not scatter many candy colours and decals; that reads as `067`.

## Nearest styles

- `079` Primary grid neoplasticism: this style uses spheres, cones and cylinders with soft shading and no black bars; `079` is flat rectangles only, divided by thick black bars, with no shading.
- `052` Brick toy: primitives here are matte and unstudded, shaded in a few gentle steps, in primaries with white, black and grey; `052` is glossy studded plastic bricks with smooth highlights.
- `067` Boxy toybox low-poly: colour here is only red, blue and yellow with white, black and grey; `067` uses many candy colours and decals.

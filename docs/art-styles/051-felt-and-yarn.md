# Felt and yarn

Reference works: Kirby's Epic Yarn.

## References

- *Kirby's Epic Yarn* (2010), Good-Feel, video game. https://en.wikipedia.org/wiki/Kirby's_Epic_Yarn
- *Yoshi's Woolly World* (2015), Good-Feel, video game. https://en.wikipedia.org/wiki/Yoshi's_Woolly_World
- *Unravel* (2016), Coldwood Interactive, video game. https://en.wikipedia.org/wiki/Unravel_(video_game)
- *LittleBigPlanet* (2008), Media Molecule, video game. https://en.wikipedia.org/wiki/LittleBigPlanet_(2008_video_game)

## Visual definition

- **Shape language and proportions:** Soft, stuffed, slightly lumpy forms. Characters are yarn outlines or plush shapes; scenery is fabric patches, buttons, zips and pompoms.
- **Line and outline:** Visible stitching: dashed thread lines along every seam and patch border, in a darker or contrasting thread.
- **Shading model:** Smooth and very soft; fabric fuzz brightens grazing angles.
- **Palette:** `#f48fb1` `#81d4fa` `#fff59d` `#a5d6a7` `#ce93d8` `#ffab91` `#f5f0e6`. Bright nursery pastels: pink, sky blue, lemon, mint, lilac, on a cream fabric ground.
- **Lighting:** Soft, even craft-table lighting with gentle contact shadows.
- **Texture and surface:** Dense fibre detail: knit loops, felt fuzz, woven cloth grain, twisted yarn strands.
- **Atmosphere and post-processing:** Mild depth of field; nothing else.
- **Camera and framing:** Side-on or slightly raised, close enough to read the fabric weave.
- **UI and typography:** Panels are felt patches with dashed stitch borders, buttons are sewn-on buttons and icons are appliqué shapes or embroidered badges. Type is a soft rounded sans that looks stitched in yarn or cut from felt. Counters are chunky rounded numerals in pink, sky blue and lemon on cream fabric.
- **VFX and motion:** Particles are yarn puffs, loose threads, pompoms and popping buttons, never sparks or smoke. A hit unravels a strand or bursts a seam with a puff of stuffing. Motion is bouncy with squash and stretch, and yarn outlines whip loose and re-form into new shapes.

## Fits

- **Genres:** `platformer`, `puzzle`, `exploration`, `action-adventure`
- **Moods:** cosy, playful, gentle
- **Settings:** craft-table world, patchwork countryside, toy bedroom, knitted seaside

## Unreal recipe

### Assets

Pick rounded cartoon packs and inflate them: a script pushes vertices along normals and smooths, so props look like stuffed cushions with slightly lumpy seams. Replace all albedo with fabric. Scenery is better built from scratch as patches, buttons, zips and pompoms; yarn outlines are tube meshes swept along curves in Blender background mode. Add a seam edge loop wherever two fabric pieces meet, with UVs running along it so a stitch texture can follow.

### Materials

`M_Felt`: Cloth shading model, Base Color from a pastel parameter (`#f48fb1`, `#81d4fa`, `#fff59d`, `#a5d6a7`, `#ce93d8`), Fuzz Color a lighter tint, Cloth 1.0, Roughness 0.9. A felt fibre normal map and albedo variation applied with WorldAlignedTexture. `M_Knit` adds a tiling knit-loop normal and height pattern in UV space; `M_Yarn` uses a twisted-strand normal along the tube. An extra Fresnel term (exponent 3) added to Emissive at 5 to 8 percent brightens grazing angles like fibre fuzz. A stitch material function draws dashed thread, `Step(0.5, Frac(U * Count))`, in a darker thread colour along seam UVs with a small raised normal. For close shots, 3 to 5 shell layers with a noise opacity mask add real fuzz depth. Every surface carries fibre; nothing stays smooth.

### Lighting and atmosphere

Lumen GI on. A large soft Rect Light overhead and a Sky Light from a white cubemap for even craft-table light, shadow contrast kept low. Contact Shadows on for gentle grounding. No fog, no sky; the ground is a cream `#f5f0e6` fabric sheet. Manual exposure, slightly high.

### Post-processing

Depth of Field at f/4, mild, with the camera close enough to read the weave. TSR on with `r.Tonemapper.Sharpen` about 0.5 so fibres stay crisp. Bloom 0.1, no grain, no vignette, no fringe, Motion Blur Amount 0. Saturation 1.0; lift Shadows Gain slightly so pastels never turn grey. No post materials.

### UI and effects

Panels are felt patches: Rounded Box brushes with a felt texture and a dashed stitch border baked into the 9-slice. Buttons are sewn-on button images that depress on click; icons are appliqué shapes or embroidered badges. Text in Fredoka or Baloo 2, with a thin dashed outline image behind headings; counters are chunky rounded numerals in pink, sky blue and lemon on cream. Niagara never emits sparks or smoke: mesh-renderer pompoms and stuffing puffs (6 to 12, lifetime 0.8 s, soft bounce), ribbon-renderer loose threads that curl and fall over 1 s, buttons that pop off and spin. A hit plays a seam-burst: one ribbon unravels while stuffing puffs out.

## Do / Do not

Do:

- Put a stitch line on every seam.
- Use sheen for fabric fuzz.
- Give every surface a knit, felt or weave pattern.
- Inflate forms like stuffed cushions.

Do not:

- Do not leave surfaces smooth; that reads as `048` or `057`.
- Do not flatten the scene into a long band of stitched figures on linen; that reads as `056`.
- Do not use flat paper sheets; that reads as `050`.
- Do not use hard plastic gloss.

## Nearest styles

- `056` Embroidered tapestry: this style builds plump, softly shaded stuffed forms in bright nursery pastels; `056` is a flat stitched picture on bare linen in muted plant-dyed wools, with no shading or depth.
- `048` Claymation: every surface here shows knit loops, felt fuzz and dashed stitch lines; `048` is smooth matte clay with thumb marks and no stitching.
- `050` Papercraft: forms here are inflated cushions covered in thick fuzzy fibre; `050` is built from flat folded paper sheets with crisp creases and only a faint paper grain.

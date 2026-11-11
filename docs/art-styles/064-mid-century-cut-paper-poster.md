# Mid-century cut-paper poster

Reference works: Saul Bass title sequences.

## References

- *Anatomy of a Murder (title sequence and poster)* (1959), Saul Bass, film title design. https://en.wikipedia.org/wiki/Anatomy_of_a_Murder
- *Vertigo (title sequence and poster)* (1958), Saul Bass, film title design. https://en.wikipedia.org/wiki/Vertigo_(film)
- *The Man with the Golden Arm (title sequence and poster)* (1955), Saul Bass, film title design. https://en.wikipedia.org/wiki/The_Man_with_the_Golden_Arm
- *Catch Me If You Can (title sequence)* (2002), Kuntzel + Deygas, film title design. https://en.wikipedia.org/wiki/Catch_Me_If_You_Can
- *Gerald McBoing-Boing* (1950), United Productions of America, animated short film. https://en.wikipedia.org/wiki/Gerald_McBoing-Boing

## Visual definition

- **Shape language and proportions:** Rough cut-paper shapes: figures and objects reduced to jagged, slightly crooked silhouettes with uneven straight cuts. Limbs are separate angular pieces. Strong diagonals and off-balance layouts.
- **Line and outline:** No outline. Shapes are solid.
- **Shading model:** None. Each shape is one flat colour.
- **Palette:** `#e8501e` `#111111` `#f4ead2` `#1f4e79` `#f2b632`. Three to five colours: one strong field colour (orange, red or blue), black, off-white and one accent.
- **Lighting:** None.
- **Texture and surface:** Flat ink with slight paper or print grain; edges are sharp but irregular as if cut with scissors.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** Flat, frontal, graphic composition; orthographic.
- **UI and typography:** Panels are crooked cut-paper blocks of flat colour laid at slight angles, with no borders; icons are jagged one-colour silhouettes. Text is uneven hand-cut block capitals with letters that jump off the baseline, in black `#111111` or off-white `#f4ead2` on the field colour; numbers use the same cut letterforms, with yellow `#f2b632` for scores.
- **VFX and motion:** Effects are flat paper shapes: impacts are jagged starbursts, smoke and dust are torn-edge blobs, and transitions are bars that slide across the frame. Animation is limited, on twos or threes, with shapes that slide, pivot and snap between held poses.

## Fits

- **Genres:** `detective-mystery`, `stealth`, `puzzle`, `platformer`
- **Moods:** suspenseful, jazzy, bold
- **Settings:** 1950s city, crime thriller, heist caper, courtroom

## Unreal recipe

### Assets

Nothing from a realistic pack survives here; build everything. A Python script with Pillow or Blender cuts each silhouette as a polygon of 6 to 14 straight segments with corners jittered by a few percent, so no edge is parallel to another and none is curved. Export shapes as flat planar meshes (real polygons, not alpha cards, so edges stay sharp). Figures are separate pieces for torso, head, each limb segment and props, pinned at pivots and posed by C++ or a simple rig. Sets are stacked planes separated by a few centimetres along the view axis only to fix draw order.

### Materials

One Unlit master, `M_Cut`, with a vector parameter restricted by script to the level's chosen set: field `#e8501e` or `#1f4e79`, black `#111111`, off-white `#f4ead2`, accent `#f2b632`. Multiply by a tiling print-grain texture at 4 percent contrast, mapped in screen space so the grain belongs to the sheet and not the object. No normal, no roughness, no vertex shading. The background is a single large plane in the field colour.

### Lighting and atmosphere

None: no lights, no sky, no fog, Lumen and reflections off through `r.DynamicGlobalIlluminationMethod=0` and `r.ReflectionMethod=0`. Orthographic camera, frontal. Compose with the planes rotated 5 to 20 degrees off axis and large diagonal shapes crossing the frame.

### Post-processing

Tone Curve Amount 0, Expand Gamut 0, manual exposure, so material colours reach the screen unchanged. Bloom, vignette, grain setting, fringe, depth of field and Motion Blur Amount all 0. No outline material. FXAA (`r.AntiAliasingMethod=1`) keeps the cut edges clean. A single optional post material at Scene Color After Tonemapping multiplies a paper fibre texture at 3 percent. Hold animation on twos or threes in C++ by updating piece transforms at 8 or 12 Hz while the camera stays at full rate.

### UI and effects

Panels are Image widgets using irregular quadrilateral textures in a flat palette colour, each given a Render Transform Angle between -4 and 4 degrees, no border. For type, set each letter as its own Text Block in Archivo Black capitals with a random baseline offset of up to 6 px and rotation of up to 3 degrees, black or `#f4ead2`; scores in `#f2b632`. Screen transitions are three coloured bars sliding across in 0.4 s.

Niagara uses mesh renderers with flat cut shapes and `M_Cut`: an impact starburst of one jagged 9-point mesh held for 3 frames; dust as two or three torn-edge blobs that step in scale at 12 Hz and vanish without fading. No sprites with soft alpha, no additive blending.

## Do / Do not

Do:

- Cut shapes with uneven straight edges.
- Use a few flat colours: one field colour, black, off-white and one accent.
- Break figures into separate angular pieces.
- Compose with strong diagonals.

Do not:

- Do not add paper thickness, folds and soft shadows; that reads as `050`.
- Do not use precise ruled geometry, photomontage and red-black type bars; that reads as `080`.
- Do not use depth layers with a graded colour ramp; that reads as `060`.
- Do not use clean circles, squares and triangles in primaries; that reads as `098`.

## Nearest styles

- `080` Constructivist agit poster: `080` uses ruler-straight bars, wedges and circles with photomontage and type bars on pale paper; this style uses crooked scissor-cut silhouettes on a strong colour field, with no photographs.
- `060` Layered flat-colour wilderness: `060` stacks many flat layers into the distance along a graded colour ramp; this style is one frontal plane with a few contrasting flat colours and no depth.
- `050` Papercraft: `050` shows real paper with thickness, folds and soft drop shadows; this style is a flat print with no shadows and no folds.

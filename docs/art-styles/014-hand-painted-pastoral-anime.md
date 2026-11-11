# Hand-painted pastoral anime

Reference works: Spirited Away; My Neighbor Totoro.

## References

- *My Neighbor Totoro* (1988), Studio Ghibli (Hayao Miyazaki), animated film. https://en.wikipedia.org/wiki/My_Neighbor_Totoro
- *Spirited Away* (2001), Studio Ghibli (Hayao Miyazaki), animated film. https://en.wikipedia.org/wiki/Spirited_Away
- *Kiki's Delivery Service* (1989), Studio Ghibli (Hayao Miyazaki), animated film. https://en.wikipedia.org/wiki/Kiki's_Delivery_Service
- *Ni no Kuni: Wrath of the White Witch* (2011), Level-5, video game. https://en.wikipedia.org/wiki/Ni_no_Kuni:_Wrath_of_the_White_Witch
- *Howl's Moving Castle* (2004), Studio Ghibli (Hayao Miyazaki), animated film. https://en.wikipedia.org/wiki/Howl's_Moving_Castle_(film)

## Visual definition

- **Shape language and proportions:** Gentle realism. Buildings are lived-in and slightly irregular; vegetation is lush and detailed. Characters have simple faces and soft rounded bodies.
- **Line and outline:** Thin dark-brown line on characters and moving props. Backgrounds have no line and are painted.
- **Shading model:** Characters: two flat bands. Backgrounds: fully painted light with soft gradients.
- **Palette:** `#6aa84f` `#2f6b3a` `#9fd3f0` `#fdfdf5` `#d9b382` `#b5533c` `#5a4636` `#f4d67a`. Rich greens, cumulus white, sky blue and warm wood and earth colours.
- **Lighting:** Summer daylight with tall white clouds, dappled leaf shadow, warm interiors.
- **Texture and surface:** Backgrounds look like poster-colour paintings: visible brush dabs in foliage, soft washed walls, crisp painted cloud edges.
- **Atmosphere and post-processing:** None beyond slight warmth. The split between flat characters and painted backgrounds is intended.
- **Camera and framing:** Calm, level, 35 to 50 mm equivalent; wide landscape views with large sky.
- **UI and typography:** Cream paper panels with a thin brown border, or small painted wooden signboards. Text is a soft rounded hand-lettered face in dark brown; icons are small poster-colour paintings with a brown line. Counters are plain rounded brown numerals with no glow; highlights use leaf green or warm yellow.
- **VFX and motion:** Effects are hand-drawn and flat: round dust puffs, soot specks, water drops with a single white highlight, leaves and petals on the wind. Character animation is on twos with gentle, weighty everyday movement; hair, grass and cloth sway slowly and clouds drift.

## Fits

- **Genres:** `exploration`, `simulation`, `action-adventure`, `rpg`, `puzzle`, `platformer`
- **Moods:** gentle, nostalgic, wondrous
- **Settings:** countryside village, forest shrine, seaside European town, spirit bathhouse

## Unreal recipe

### Assets

Village, farm and woodland packs with slightly irregular buildings and dense vegetation suit this style. The key step is repainting scenery textures as poster-colour paintings: a script applies a Kuwahara filter and palette remap to every base colour map, then stamps brush dabs, dark to light, over foliage atlases. Remove normal and roughness maps from scenery. Foliage cards get normals transferred from a sphere so each tree shades as one painted mass. Characters should be simple, rounded rigged models with small plain faces.

### Materials

Two masters, kept visibly different on purpose.

- `M_PaintedBG`, Default Lit, Roughness 1, Specular 0, painted base colour, Two Sided Foliage for leaves. It takes real sun, sky and dappled shadow.
- `M_CelChar`, Unlit, for characters and moving props: `Step` on N·L (sun vector from a Material Parameter Collection) between a flat fill and a flat shadow colour set per region by hand. Two bands, no highlight, no rim.

The character line is an inverted hull in dark brown `#5a4636`: Masked two-sided Unlit, back faces only via TwoSidedSign, World Position Offset along the normal for a thin 1.5 to 2 px width, set as Overlay Material. Scenery gets no line.

### Lighting and atmosphere

Lumen GI on for the backgrounds. Summer Directional Light with Source Angle 1.5 and a Light Function of leaf shapes for dapple under trees. Sky Light with Real Time Capture. The sky is a dome painted by script (blue `#9fd3f0` with tall cumulus, crisp lit edges, soft undersides) scrolling slowly, since Volumetric Cloud looks too photographic here. Very light Exponential Height Fog; no volumetrics. Warm Point Lights indoors.

### Post-processing

`PP_Kuwahara` at Scene Color Before Bloom: a Custom HLSL node with a 4-sector, 3 to 4 px radius Kuwahara filter over PostProcessInput0, masked by CustomStencil so characters (stencil-tagged) are skipped and stay flat. This merges lighting and texture into brush-like patches. Bloom Intensity 0, Lens Flare Intensity 0, no fringe, no grain, Vignette 0, Motion Blur Amount 0, deep focus. White Balance Temp nudged warm; Tone Curve Amount 0.6 for a matte result without glow. TSR.

### UI and effects

Panels are cream paper (`#fdfdf5`) Box brushes with a thin brown outline, or painted wooden signboard images. Text is a soft rounded hand face (Patrick Hand, Klee One) in `#5a4636`; counters are plain rounded brown numerals; highlights use `#6aa84f` or `#f4d67a`. Niagara: flat Unlit sprites drawn by hand, such as round dust puffs (3 frames, 0.5 s), soot specks, water drops with one white highlight, and 10 to 30 leaves or petals drifting 5 s on the wind. Grass and cloth sway through slow World Position Offset; characters animate on twos.

## Do / Do not

Do:

- Keep characters flat and backgrounds painted.
- Use brown, not black, for line.
- Paint clouds with crisp lit edges and soft undersides.
- Layer foliage dabs dark to light.

Do not:

- Do not add lens flare, glow gradients and photo-level sky detail; that reads as `016`.
- Do not line and flat-shade the scenery too; that reads as `018`.
- Do not use chunky high-contrast painted textures with smooth shading on characters; that reads as `023`.
- Do not use black outlines.

## Nearest styles

- `016` Luminous sky anime: `016` fills the frame with glowing twilight skies, lens flares and wet reflections; this style has matte daylight paintings with no glow.
- `018` Soft open-world anime cel: `018` has clean, smooth scenery with simple gradients and outlined props; this style has scenery painted with visible brush dabs and no line.
- `002` Painterly open-air cel: `002` has almost no line and paints the world in broad soft patches of colour; this style draws a brown line around characters and paints dense detail into foliage and buildings.

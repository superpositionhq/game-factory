# Expressionist oil isometric

Reference works: Disco Elysium.

## References

- *Disco Elysium* (2019), ZA/UM, video game. https://en.wikipedia.org/wiki/Disco_Elysium
- *Self-Portrait as a Soldier* (1915), Ernst Ludwig Kirchner, oil painting. https://en.wikipedia.org/wiki/Self-Portrait_as_a_Soldier
- *The Scream* (1893), Edvard Munch, painting. https://en.wikipedia.org/wiki/The_Scream

## Visual definition

- **Shape language and proportions:** Realistic, worn urban setting seen from an isometric angle. Forms are slightly loose and unsteady, as if painted quickly from life.
- **Line and outline:** No drawn outline. Some edges are reinforced by dark paint strokes.
- **Shading model:** Painted light with five to eight visible tone patches per form; transitions are made of separate strokes, not gradients.
- **Palette:** `#3a4a4f` `#8a6f4d` `#c4763a` `#5d7a6a` `#b9b3a0` `#7c3f3a` `#1d2326` `#d7c38a`. Muted greens, greys and browns with unexpected orange, teal and rust strokes inside shadows and highlights.
- **Lighting:** Flat overcast or weak dawn light; colour temperature shifts carry the form more than value contrast.
- **Texture and surface:** Thick oil paint: short, loaded strokes in many directions, palette-knife patches, visible linen weave, colours not fully mixed.
- **Atmosphere and post-processing:** Soft atmospheric haze; optional linen-weave overlay. No sharp digital effects.
- **Camera and framing:** Fixed isometric-like view, about 35 to 45 degrees down, long lens or orthographic.
- **UI and typography:** Painted portrait frames and dark text panels with rough brushed edges; dialogue runs in a tall text column. Body text is a bookish serif, headings are tall condensed sans capitals, and skill-check numbers are small plain numerals. Text is off-white `#b9b3a0` on near-black `#1d2326`, with orange `#c4763a` and grey-green `#5d7a6a` accents.
- **VFX and motion:** Sparse effects: drifting haze, rain and cigarette smoke painted as soft strokes, with no impact flashes. Character motion is slow, heavy and realistic, mostly walking and idle gestures.

## Fits

- **Genres:** `detective-mystery`, `rpg`, `exploration`, `puzzle`
- **Moods:** melancholic, bleak, introspective
- **Settings:** decaying harbour district, post-revolution city, run-down hostel, winter coastline

## Unreal recipe

### Assets

Worn urban props and buildings at realistic scale: harbour sheds, tenements, cars, fences. Store packs keep their geometry, with vertices jittered 1 to 2 cm by script so lines lean and wobble. Repaint every albedo offline: segment the texture into patches of 20 to 60 px, fill each patch with short strokes in one random direction, and inject a complementary accent (`#c4763a`, `#5d7a6a` or `#7c3f3a`) into about one patch in eight, leaving thin gaps where a `#8a6f4d` under-colour shows. Generate a matching impasto height map and a linen weave texture.

### Materials

`M_ImpastoPatch`, Default Lit. BaseColor is the patch-painted albedo. The impasto height map becomes a normal map at full strength with Roughness 0.55 to 0.7, so thick paint catches the weak light. Original asset normal maps are removed; form comes from the patches. A shadow-side accent is added in the material: where `Dot` of the normal and an MPC light vector is below zero, a patch-noise mask lerps toward teal or rust. No vertex-colour curvature lines and no contour material.

### Lighting and atmosphere

Flat overcast: Sky Light at intensity 2 as the main source with a grey-green cubemap, and a Directional Light at only 1 lux, warm `#d7c38a`, Source Angle 10, for a weak dawn hint. Lumen GI on, reflections off (`r.ReflectionMethod=0`). Virtual Shadow Maps on, with shadows staying pale under the sky fill. Exponential Height Fog `#b9b3a0` at low density for haze. Manual exposure.

### Post-processing

`PP_PaintPatches` at Scene Color Before DOF: plain Kuwahara, 5 px radius, with the sampling window rotated per screen cell by a stable world-position hash, so tone breaks into five to eight patches whose strokes run in many directions and never align into flowing curves. A second material multiplies the linen weave at 15 percent. Global Saturation 0.85, Contrast 0.9; push shadows Gain toward teal and highlights toward ochre so temperature carries form. Bloom 0.1, Vignette 0.2, Film Grain 0, Scene Fringe 0, Motion Blur Amount 0, depth of field off. The camera is orthographic or a long lens pitched 35 to 45 degrees down. TSR.

### UI and effects

Portrait frames and text panels are near-black `#1d2326` Box brushes with rough brushed alpha edges; dialogue runs in a tall right-hand column. Body in EB Garamond, headings in Bebas Neue capitals, skill-check numbers small and plain, text `#b9b3a0` with `#c4763a` and `#5d7a6a` accents. Niagara is sparse: rain as short stroke-shaped sprites, cigarette smoke as 3 or 4 soft painted sprites rising for 4 s, haze cards drifting slowly. No impact flashes.

## Do / Do not

Do:

- Place complementary accent strokes inside shadows.
- Vary stroke direction by patch.
- Let under-colour show between strokes.
- Use a fixed high three-quarter view.

Do not:

- Do not align all strokes into flowing swirls with dark contours; that reads as `076`.
- Do not use small soft dabs in bright daylight colours; that reads as `075`.
- Do not use ordered directional strokes on dramatic low-key 3D; that reads as `024`.
- Do not smooth the paint into gradients; that reads as `026`.

## Nearest styles

- `076` Swirling impasto: strokes here are short, run in many directions and have no contour line, in muted greens, greys and browns; `076` has long flowing swirls, dark brush contours and strong blue and yellow.
- `075` Impressionist broken colour: this style is dull and dark under overcast light; `075` is bright, sunny and pastel, with no dark shadows.
- `024` Brush-textured 3D drama: paint here is thick, strokes run in every direction and many unmixed hues sit side by side; `024` has thinner, ordered strokes that follow the form, in a teal and orange scheme.

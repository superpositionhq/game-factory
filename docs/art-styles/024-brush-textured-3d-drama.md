# Brush-textured 3D drama

Reference works: Arcane.

## References

- *Arcane* (2021), Fortiche and Riot Games, animated TV series. https://en.wikipedia.org/wiki/Arcane_(TV_series)
- *Puss in Boots: The Last Wish* (2022), DreamWorks Animation, animated film. https://en.wikipedia.org/wiki/Puss_in_Boots:_The_Last_Wish
- *Teenage Mutant Ninja Turtles: Mutant Mayhem* (2023), Nickelodeon Movies and Mikros Animation, animated film. https://en.wikipedia.org/wiki/Teenage_Mutant_Ninja_Turtles:_Mutant_Mayhem
- *Klaus* (2019), The SPA Studios, animated film. https://en.wikipedia.org/wiki/Klaus_(film)

## Visual definition

- **Shape language and proportions:** Realistic anatomy with slightly sharpened planes on faces and props. Architecture is dense and ornate with art-deco and industrial detail.
- **Line and outline:** Occasional dark painted accents at creases and under forms; no continuous outline.
- **Shading model:** Light is broken into four to six painted tone planes with visible stroke edges. Highlights are drawn as distinct brush marks.
- **Palette:** `#1f2a44` `#c2553f` `#e3a857` `#3e8e8c` `#7a3e65` `#d9cdb8` `#12141c`. Dark teal-blue shadow against warm orange and gold light; magenta and green accents.
- **Lighting:** Dramatic, low-key: strong warm practicals and cool fill, hard rim lights.
- **Texture and surface:** Every surface looks painted: directional brush strokes follow the form, with scumbled edges and painted speculars.
- **Atmosphere and post-processing:** Painted-looking smoke and glow drawn as 2D shapes; light bloom; subtle film grain.
- **Camera and framing:** Cinematic, shallow depth, 50 to 85 mm equivalent for characters, wide for cities.
- **UI and typography:** Art-deco frames with thin gold lines and angular corner ornaments, and painted icons with visible strokes. Titles use a tall condensed deco sans; damage numbers are rough hand-painted numerals. UI colours are gold `#e3a857` and cream `#d9cdb8` on near-black `#12141c`, with magenta or teal accents.
- **VFX and motion:** Smoke, sparks and explosions are hand-painted 2D shapes animated on twos over full-rate 3D motion; hits flash with magenta or teal painted bursts. Character motion is weighty and realistic, with sharp accents on impacts.

## Fits

- **Genres:** `action-adventure`, `third-person-shooter`, `fighting`, `stealth`, `detective-mystery`, `rpg`
- **Moods:** dramatic, gritty, tense
- **Settings:** steampunk undercity, art-deco upper city, industrial slums, back-alley laboratories

## Unreal recipe

### Assets

Realistic characters and dense industrial or art-deco architecture suit this style, so store packs keep their geometry. Sharpen facial and prop planes slightly with a weighted-normal pass. Every texture set is repainted by script: bake a tangent-direction map in Blender, then smear the albedo along it with a line-integral filter so strokes follow the form, and stamp distinct highlight marks where the original roughness was lowest. Keep normal maps but blur them and add a stroke-relief normal at half strength. Smoke cards and glow shapes are built from scratch as painted 2D flipbooks.

### Materials

`M_PaintedPlanes`, Default Lit. BaseColor is the stroked albedo. Roughness sits at 0.75 to 0.9, because real specular is replaced by painted marks: a highlight-mark texture is added to Emissive, gated by `Dot` of the reflection vector and an MPC key-light direction through a `Step`, so marks switch on and off as whole strokes. A shared stroke-relief normal map is blended by a parameter. A `MF_CreaseAccent` function darkens baked cavity areas to `#12141c`. Skin uses Subsurface Profile with the same stroke overlay.

### Lighting and atmosphere

Lumen GI and reflections on. Low-key setups: one warm practical per scene (Point or Rect, `#e3a857` to `#c2553f`), a dim cool fill in `#1f2a44`, and a hard Spot rim behind characters on its own Lighting Channel. Virtual Shadow Maps with contact shadows. Exponential Height Fog with Volumetric Fog on, tinted teal `#3e8e8c`, light density. Manual exposure set two thirds of a stop under neutral.

### Post-processing

`PP_PaintPlanes` at Scene Color Before DOF: an anisotropic Kuwahara filter in a Custom node, 6 px radius, oriented by a structure tensor taken from WorldNormal, breaks lighting into four to six tone planes whose borders run along stroke edges. A second pass multiplies a canvas-scale stroke overlay locked to object UVs via CustomStencil groups, not to the screen. Then depth of field with Aperture F-stop 2.0 to 2.8 on character shots, Bloom Intensity 0.5, Film Grain Intensity 0.15, Vignette 0.3. Grade: shadows Gain toward teal, highlights toward orange. Motion Blur Amount 0. TSR.

### UI and effects

Deco frames: thin 2 px gold `#e3a857` lines with angular corner ornaments on `#12141c`, drawn as Border brushes. Titles in Limelight or Poiret One capitals, body in Josefin Sans, damage numbers from a rough painted numeral texture font. Icons keep visible strokes. Niagara smoke, sparks and explosions are painted SubUV flipbooks played at 12 frames per second with no frame blending, over full-rate 3D motion; hit bursts are a 5-frame magenta `#7a3e65` or teal star shape lasting 0.25 s. Sprite materials are Unlit.

## Do / Do not

Do:

- Orient strokes along the form.
- Break tone boundaries along stroke edges.
- Paint highlights as discrete marks.
- Light with warm practicals against cool fill.

Do not:

- Do not blur strokes away into broad blocks; that reads as `021`.
- Do not light evenly with saturated zone colours; that reads as `023`.
- Do not cover the frame with thick swirling strokes and outlines; that reads as `076`.
- Do not add halftone dots; that reads as `009`.

## Nearest styles

- `021` Brush-block martial painterly: this style shows directional brush strokes and painted highlight marks on every surface; `021` smooths them into broad soft tone blocks with no small marks.
- `028` Expressionist oil isometric: strokes here follow the form in an ordered way under dramatic warm and cool light; `028` has thicker paint, short strokes running in many directions, unmixed colours and flat overcast light.
- `026` Oily concept-art realism: here light breaks into stepped planes with stroke edges and strong colour; `026` has smooth gradients and a greyer look.

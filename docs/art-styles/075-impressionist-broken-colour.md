# Impressionist broken colour

Reference works: Monet.

## References

- *Impression, Sunrise* (1872), Monet, oil painting. https://en.wikipedia.org/wiki/Impression,_Sunrise
- *Water Lilies* (1896-1926), Monet, oil painting series. https://en.wikipedia.org/wiki/Water_Lilies_(Monet_series)
- *Bal du moulin de la Galette* (1876), Pierre-Auguste Renoir, oil painting. https://en.wikipedia.org/wiki/Bal_du_moulin_de_la_Galette
- *Haystacks* (1890-1891), Monet, oil painting series. https://en.wikipedia.org/wiki/Haystacks_(Monet_series)
- *Woman with a Parasol - Madame Monet and Her Son* (1875), Monet, oil painting. https://en.wikipedia.org/wiki/Woman_with_a_Parasol_–_Madame_Monet_and_Her_Son

## Visual definition

- **Shape language and proportions:** Everyday outdoor subjects: water, gardens, bridges, haystacks, figures with parasols. Forms have soft, dissolved edges; nothing is sharply bounded.
- **Line and outline:** None. Edges are transitions between dabs of colour.
- **Shading model:** Light is shown by colour temperature, not by dark shadow: sunlit areas in warm yellow-pink, shadows in blue-violet of similar brightness.
- **Palette:** `#a9c7e8` `#f4d9a0` `#e8a6b8` `#7fae7a` `#c9b6e4` `#f6f0dc` `#5f7fb5` `#e9905a`. High-key pastel colours: sky blue, lilac, pink, pale gold, fresh green. No black, no brown-black shadows.
- **Lighting:** Bright outdoor daylight, hazy sun, strong reflections on water.
- **Texture and surface:** The whole image is short, separate brush dabs (comma strokes), each a slightly different colour, with bare linen showing between. Water is horizontal dabs, foliage is multi-directional.
- **Atmosphere and post-processing:** A full-frame brush pass that rebuilds the image from dabs; slight linen weave.
- **Camera and framing:** Eye-level landscape views with a high or absent horizon; 35 to 50 mm equivalent.
- **UI and typography:** Panels are soft-edged patches of pale cream paint `#f6f0dc` with dabbed borders and no hard frames, and icons are loose brush sketches made of a few strokes. Text is a light, rounded brush-lettered hand in deep sky blue `#5f7fb5`, and numbers are painted in the same hand with warm orange `#e9905a` for highlights.
- **VFX and motion:** Particles are loose dabs of paint: petals, light sparkles on water, drifting pollen and mist. Impacts are soft bursts of pale dabs with no hard flash, and motion is gentle and flowing, with dabs that shimmer slightly as light moves over water and leaves.

## Fits

- **Genres:** `exploration`, `simulation`, `puzzle`, `sports`
- **Moods:** serene, sunny, nostalgic
- **Settings:** water garden, riverside village, summer meadow, seaside harbour at dawn

## Unreal recipe

### Assets

Outdoor realistic packs: ponds, lilies, bridges, gardens, haystacks, poplars, village houses, figures in summer dress. Detail will dissolve, so medium-poly assets are enough. Restyle textures by script: raise albedo brightness into the upper half of the range, pull hue toward the palette, remove baked dark occlusion, and delete normal-map micro detail. No near-black anywhere; clamp albedo minimum to about 0.25.

### Materials

Default Lit on the packs' masters, with a shared function that lifts shadowed colour: nothing in a material may go below pastel. Foliage uses Two Sided Foliage with bright transmission in `#7fae7a` and `#f4d9a0`. Water is Single Layer Water with strong sky reflection, tinted `#a9c7e8` and `#5f7fb5`. All surfaces write a stroke-direction hint: stencil 1 for water (horizontal dabs), 2 for foliage (multi-directional), 0 for the rest.

### Lighting and atmosphere

Lumen GI and reflections on. Directional Light warm, `#f4d9a0`, Source Angle 3. Sky Atmosphere with a real-time-capture Sky Light at intensity 2 to 3, so shadows fill with blue-violet close in brightness to the lit side; tint the Sky Light toward `#c9b6e4`. Exponential Height Fog, pale `#f6f0dc`, moderate density for hazy sun. Shadow values should sit within one stop of lit values; reduce directional intensity instead of darkening shade. Auto exposure, biased bright.

### Post-processing

PPV first: Shadows gain tinted `#c9b6e4`, Highlights toward `#f4d9a0`, Film Toe lowered so nothing reaches black, Saturation 1.15, Bloom 0.5, no grain, vignette or fringe, Motion Blur Amount 0.

Then one post material at Scene Color After Tonemapping, a dab pass in a Custom node:

1. Divide the screen into jittered cells of about 10 by 5 px. For each pixel test the 9 nearest cells; each cell is an elliptical comma stroke with random rotation (near horizontal on stencil 1, free on stencil 2, loosely vertical elsewhere).
2. Each dab takes one colour from PostProcessInput0 at its centre, then shifts hue and brightness by a small random amount so neighbours differ.
3. Where no dab covers the pixel, show linen `#f6f0dc` with a weave texture.
4. Re-seed 10 percent of cells every 0.25 s for a slight shimmer.

No edge detection: edges must stay soft transitions. TSR runs before the pass.

### UI and effects

Panels are Image widgets using soft-edged cream paint-patch textures with dabbed rims, no rectangular frame. Text in Caveat Bold or Fredoka Light, `#5f7fb5`; highlighted numbers in `#e9905a`. Icons are four- or five-stroke brush sketches.

Niagara: petals and pollen as small opaque sprite dabs in `#e8a6b8` and `#f4d9a0`, 4 to 6 s life, drifting; water sparkle as short horizontal `#f6f0dc` dabs flickering at 4 Hz; impacts as 12 pale dabs expanding softly over 0.5 s, no flash.

## Do / Do not

Do:

- Build the image from short separate dabs.
- Colour shadows blue-violet at near the same brightness as lights.
- Keep edges soft and dissolved.
- Avoid black entirely.

Do not:

- Do not use round uniform dots of pure pigment; that reads as `077`.
- Do not use long swirling strokes with dark contours; that reads as `076`.
- Do not use muted overcast colours with accent strokes; that reads as `028`.
- Do not keep photographic detail under the dabs; that reads as `032`.

## Nearest styles

- `077` Pointillist dot field: this style uses irregular, elongated dabs of many blended pastel colours with soft dissolved forms; `077` uses even round dots of a few pure pigments on smooth, stiff, clearly shaped forms.
- `076` Swirling impasto: this style has no contours and keeps soft pastel daylight colour in short dabs; `076` draws dark brushed contours and uses long swirling strokes of strong blue and yellow.
- `028` Expressionist oil isometric: this style is bright, sunlit and pastel; `028` is dim and overcast, in muted greens, greys and browns with thick dark paint.

# Baroque chiaroscuro

Reference works: Caravaggio.

## References

- *The Calling of Saint Matthew* (1600), Caravaggio, oil painting. https://en.wikipedia.org/wiki/The_Calling_of_Saint_Matthew
- *Judith Beheading Holofernes* (c. 1599), Caravaggio, oil painting. https://en.wikipedia.org/wiki/Judith_Beheading_Holofernes_(Caravaggio)
- *The Night Watch* (1642), Rembrandt, oil painting. https://en.wikipedia.org/wiki/The_Night_Watch
- *Girl with a Pearl Earring* (c. 1665), Johannes Vermeer, oil painting. https://en.wikipedia.org/wiki/Girl_with_a_Pearl_Earring
- *Barry Lyndon* (1975), Stanley Kubrick, live-action film. https://en.wikipedia.org/wiki/Barry_Lyndon

## Visual definition

- **Shape language and proportions:** Realistic human figures and still-life objects (cloth, fruit, vessels, tables) in close, shallow interior space. Heavy drapery with deep folds.
- **Line and outline:** No outline. Edges on the shadow side dissolve into the background (lost edges).
- **Shading model:** Smooth, strongly directional modelling from bright lit flesh to deep shadow, with a soft terminator. Most of the picture is dark.
- **Palette:** `#0a0705` `#3a2416` `#8a4b2a` `#c9905a` `#e8cfa0` `#7a1f1a` `#2a3a2f`. Warm darks: black-brown background, umber and sienna midtones, golden flesh lights, deep red and dull green drapery.
- **Lighting:** A single shaft of light from high on one side, as from a small window; no fill. The background wall is almost black with a diagonal edge of light.
- **Texture and surface:** Smooth glazed oil surface; fine fabric and skin detail visible only in lit areas; subtle craquelure.
- **Atmosphere and post-processing:** Warm varnish tint, strong vignette into black.
- **Camera and framing:** Close, eye-level, half- or three-quarter-length figures; 50 to 85 mm equivalent.
- **UI and typography:** Minimal and dark: thin gilt frame lines on black-brown panels with a warm varnish tone; icons are small painted still-life objects (candle, key, skull, coin) lit from one side. Text is an old-style serif with italic for emphasis, in golden cream. Numbers are old-style numerals in gold, with deep red for damage.
- **VFX and motion:** Particles are dust motes in the light shaft, candle smoke and sparks from steel; blood is dark red and glossy, visible only where the light hits it. A hit throws the figure into or out of the light. Motion is weighty and realistic, with heavy cloth that follows through.

## Fits

- **Genres:** `soulslike`, `stealth`, `survival-horror`, `detective-mystery`, `action-adventure`, `rpg`
- **Moods:** dramatic, solemn, tense
- **Settings:** 17th-century tavern, candlelit chapel, palace interior, cellar

## Unreal recipe

### Assets

Use the best realistic assets available: scanned or high-detail human characters, heavy cloth with deep sculpted folds, fruit, pewter, glass, rough tables. Keep normal maps and full texture resolution, since detail must hold up in the lit areas. Re-tint albedo by script toward umber, sienna, deep red `#7a1f1a` and dull green `#2a3a2f`; remove any blue or saturated modern colour. Build rooms from scratch as plain plaster boxes with one small high window opening; walls need almost no detail because they stay black.

### Materials

Default Lit masters. Skin uses Subsurface Profile with a warm profile so lit flesh turns golden `#c9905a` to `#e8cfa0`. Cloth uses the Cloth shading model with low fuzz. All surfaces get a thin "varnish" response: Roughness biased to 0.35 to 0.5 and a faint craquelure normal overlay through a material function, visible only at grazing highlights. Walls are `#3a2416` at Roughness 0.9.

### Lighting and atmosphere

One Spot Light or Rect Light placed high on one side outside the window, 3200 K, narrow cone, with Virtual Shadow Maps and Contact Shadow Length 0.05. No fill light. Lumen global illumination on but restrained: set the key's Indirect Lighting Intensity to 0.3 and the Sky Light intensity to 0, so bounce lifts only surfaces next to lit cloth. A blocker card shapes a diagonal edge of light on the back wall. Exponential Height Fog with Volumetric Fog on at very low density, key Volumetric Scattering Intensity 0.5, shows the shaft and its dust. Exposure is Manual, set for the lit flesh; never auto, or the darkness lifts.

### Post-processing

Film Toe 0.7 and Black Clip 0.02 to crush shadow edges into the background; Shadows Gain lowered, Shadows Saturation 0.8. White Balance Temp warm (about 7500 on the slider) plus a LUT adding an amber varnish cast. Vignette Intensity 0.8. Bloom Intensity 0.15 on flames only. Film Grain Intensity 0.1. Depth of field at f/2.8, 50 to 85 mm equivalent. Scene Fringe Intensity 0, Motion Blur Amount 0. TSR. No outline or posterise materials.

### UI and effects

UMG panels are `#0a0705` to `#3a2416` fills with a 1 px gilt `#c9905a` line frame. Text is EB Garamond in golden cream `#e8cfa0`, italic for emphasis; numbers use old-style figures in gold, `#7a1f1a` for damage. Icons are small renders of a candle, key, skull and coin lit from one side.

Niagara: 40 to 60 lit dust-mote sprites drifting inside the shaft volume only, lifetime 8 s; candle smoke as a thin lit ribbon; steel sparks as short orange streaks, 0.3 s. Blood is a dark red mesh decal with Roughness 0.1, readable only inside the light.

## Do / Do not

Do:

- Light with one high side source and no fill.
- Let shadow-side edges disappear into a black background.
- Keep the palette to warm earth colours.
- Use deep drapery folds to catch the light.

Do not:

- Do not use cold grey-green decay and a flashlight; that reads as `029`.
- Do not remove colour; that reads as `068`.
- Do not add coloured neon or rain; that reads as `089`.
- Do not light the background.

## Nearest styles

- `029` Survival-horror dark photoreal: this style has warm earth colours, golden flesh and smooth glazed surfaces under one window shaft; `029` is cold grey-green with gritty decayed surfaces lit by a flashlight.
- `068` Film noir hard light: this style keeps warm colour in golden skin and red and green drapery; `068` is black and white.
- `049` Gothic stop-motion puppet: this style has realistic figures, most of them lost in black; `049` shows more of the scene and has thin stylised puppets.

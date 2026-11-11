# Clinical white space-age

Reference works: 2001: A Space Odyssey.

## References

- *2001: A Space Odyssey* (1968), Stanley Kubrick, live-action film. https://en.wikipedia.org/wiki/2001:_A_Space_Odyssey
- *THX 1138* (1971), George Lucas, live-action film. https://en.wikipedia.org/wiki/THX_1138
- *Moon* (2009), Duncan Jones, live-action film. https://en.wikipedia.org/wiki/Moon_(2009_film)
- *Portal 2* (2011), Valve, video game. https://en.wikipedia.org/wiki/Portal_2
- *Oblivion* (2013), Joseph Kosinski, live-action film. https://en.wikipedia.org/wiki/Oblivion_(2013_film)

## Visual definition

- **Shape language and proportions:** Clean engineered interiors: curved corridors, padded or moulded wall panels in a regular module, recessed light strips, round hatches, rotating ring sections. Spacecraft exteriors are white modular hulls with fine panel detail.
- **Line and outline:** No outline.
- **Shading model:** Smooth, soft, high-key. White surfaces are modelled by gentle gradients from large light panels.
- **Palette:** `#f4f4f1` `#dcdcd8` `#b9bcbf` `#1a1a1c` `#c4302b` `#8fa3b0`. White and pale grey almost everywhere, black for screens and space, with very small red or orange accents (a lamp, a seat, a suit).
- **Lighting:** Bright, even, built-in lighting: glowing floor or ceiling panels and wall strips. No visible hard shadows inside. Exteriors: one hard sun with black shadows.
- **Texture and surface:** Subtle panel seams, quilted padding, small labels and vents. Clean, not weathered.
- **Atmosphere and post-processing:** None, or very slight bloom from light panels. Crisp focus.
- **Camera and framing:** Symmetric one-point perspective down corridors, wide lens, level and centred.
- **UI and typography:** Thin-line panels in white and pale grey with rounded corners, like instrument readouts; icons are simple single-weight pictograms. Type is a clean geometric sans in widely spaced small capitals. Counters are plain tabular numerals in black or white, with red `#c4302b` only for warnings.
- **VFX and motion:** Sparse and clean: soft white light pulses, thin puffs of pale vapour, small red indicator flashes on hits. Motion is slow, smooth and deliberate, with gliding doors and steady weightless drift; no camera shake.

## Fits

- **Genres:** `puzzle`, `exploration`, `simulation`, `stealth`, `fps`
- **Moods:** sterile, calm, eerie, lonely
- **Settings:** space station, lunar base, test laboratory, orbital spacecraft

## Unreal recipe

### Assets

Clean modular sci-fi interior kits suit this: curved corridor segments, moulded wall panels on a regular module, round hatches, light troughs. Remove every grime, scratch, rust and edge-wear layer from store materials, and delete decals other than small labels. Build by script what is missing: quilted padded panels (subdivided grid with pinched points), ring-section corridors, recessed light strips and panel-seam normal maps drawn as thin uniform grooves.

### Materials

Default Lit master `M_WhitePanel`. Base Colour `#f4f4f1` or `#dcdcd8`, held at or below 0.85 linear so whites keep detail; Roughness 0.45 to 0.6, uniform, with no roughness texture; Metallic 0. A seam normal map and a faint ambient-occlusion multiply in the grooves are the only surface detail. Trim is grey `#b9bcbf`; screens are near-black `#1a1a1c` glass at Roughness 0.1. Light panels use Emissive Color in neutral white at 5 to 10. Red `#c4302b` appears on one or two small objects per room through a material instance, never on walls.

### Lighting and atmosphere

Interiors: Lumen global illumination and reflections on, with the emissive panels plus matching Rect Lights (large Source Width and Height, soft) behind every floor, ceiling and wall strip; no directional light indoors. The many large sources fill each other's shadows, so no hard shadow shows. Raise Lumen Final Gather Quality to 2 for clean white gradients. No fog, no volumetrics. Exposure Manual, set so walls land just below white. Exteriors: one Directional Light with Source Angle 0.5, no Sky Light and no Sky Atmosphere, giving black shadows against black space with an Unlit star dome.

### Post-processing

Keep the image neutral. Bloom Intensity 0.2 with Threshold 1.5 so only light panels glow. Film Shoulder 0.3 and Tone Curve Amount 0.8 to protect highlight detail. Ambient Occlusion Intensity 0.3. Film Grain Intensity 0, Vignette Intensity 0, Scene Fringe Intensity 0, Lens Flare Intensity 0, Motion Blur Amount 0, depth of field off for crisp focus. White Balance neutral; Global Saturation 0.95. TSR anti-aliasing. No post-process materials.

### UI and effects

UMG panels are 1 px line frames in `#dcdcd8` with Rounded Box corners, over white or 85% opaque pale grey. Font is Jost or Josefin Sans in small capitals with letter spacing 150 to 200; counters use tabular numerals in `#1a1a1c` or white. Red `#c4302b` is reserved for warnings.

Niagara stays sparse: soft white light pulses as an emissive ramp on the panel material over 0.5 s; pale vapour as 5 to 8 lit translucent sprites, 1.5 s, drifting without gravity; a small red indicator flash on hits, 0.1 s.

## Do / Do not

Do:

- Build from a regular module of white panels.
- Light with built-in glowing panels.
- Frame symmetrically in one-point perspective.
- Limit colour to one tiny red or orange accent.

Do not:

- Do not add outdoor sun, rooftops and several accent colours; that reads as `035`.
- Do not add grime, pipes and dim lighting; that reads as `092`.
- Do not facet red figures in an empty white room; that reads as `063`.
- Do not use raw concrete; that reads as `097`.

## Nearest styles

- `035` White city with primary accents: this style is a sealed interior of seamed white panels under soft built-in light, with whites that keep their detail; `035` is a sunlit outdoor city whose whites burn out, with several bright primary accents.
- `063` White-and-red faceted minimal: surfaces here are smoothly curved with soft gradients and pale grey panel detail; `063` breaks every form into flat facets and uses only white, red and a few neutrals.
- `092` Industrial used-future: this style is bright, white and clean everywhere; `092` is dark grey-green, grimy and dim, with exposed pipes and amber warning lights.

# Art Deco streamline

Reference works: Chrysler Building; BioShock.

## References

- *Chrysler Building* (1930), William Van Alen, architecture. https://en.wikipedia.org/wiki/Chrysler_Building
- *BioShock* (2007), 2K Boston and 2K Australia, video game. https://en.wikipedia.org/wiki/BioShock
- *Autoportrait (Tamara in a Green Bugatti)* (1929), Tamara de Lempicka, oil painting. https://en.wikipedia.org/wiki/Autoportrait_(Tamara_in_a_Green_Bugatti)
- *The Great Gatsby* (2013), Baz Luhrmann, live-action film. https://en.wikipedia.org/wiki/The_Great_Gatsby_(2013_film)
- *Metropolis* (1927), Fritz Lang, silent film. https://en.wikipedia.org/wiki/Metropolis_(1927_film)

## Visual definition

- **Shape language and proportions:** Symmetric, vertical, stepped: ziggurat setbacks, sunbursts, fan and fountain motifs, chevrons, fluted pilasters, stacked arcs, streamlined rounded corners with speed lines. Stylised heroic statues with smooth simplified anatomy.
- **Line and outline:** No outline. Thin inlaid metal lines form geometric patterns.
- **Shading model:** Smooth, polished: glossy stone, lacquer and metal with long clean highlights; figures have tubular, airbrushed modelling.
- **Palette:** `#0f1a24` `#c9a24b` `#1f4e4a` `#e8dcc0` `#7a1f2b` `#2b2b2b` `#8fa3a8`. Black, deep teal and oxblood with gold or brass, cream marble and chrome.
- **Lighting:** Dramatic uplighting and cove lighting, strong vertical light shafts, reflections on polished floors.
- **Texture and surface:** Flat polished materials with inlaid geometric patterns: sunburst floors, chevron bands, repeating fan grilles, marble veining.
- **Atmosphere and post-processing:** Soft bloom on light fixtures; otherwise clean.
- **Camera and framing:** Symmetric frontal views looking up at towering verticals; wide lens.
- **UI and typography:** Symmetric gold-line frames with stepped corners on black or deep teal panels, divided by sunburst and chevron bands; icons are geometric single-line emblems. Type is a tall geometric display sans in capitals with contrasting thin and thick strokes. Counters are tall gold `#c9a24b` numerals on black.
- **VFX and motion:** Clean and theatrical: radiating light rays, gold glints, sweeping spotlight beams and brief sunburst flashes on hits. Motion is smooth and elegant, with poised held poses and streamlined sweeps; doors and panels slide and fan open symmetrically.

## Fits

- **Genres:** `detective-mystery`, `fps`, `action-adventure`, `stealth`, `racing`, `strategy`
- **Moods:** glamorous, grand, decadent, ominous
- **Settings:** 1920s skyscraper, underwater city, luxury ocean liner, grand hotel lobby

## Unreal recipe

### Assets

Look for 1920s lobby, hotel, liner and skyscraper kits with stepped setbacks, fluted pilasters and fan grilles; keep them symmetric about a central axis when assembling. Remove wear, rust, rivets and clutter from store materials. Build the inlay patterns by script: sunburst floors, chevron bands and stacked-arc borders as mask textures, plus stepped ziggurat door frames and heroic statues simplified by smoothing and decimating a scanned figure until anatomy reads as tubes.

### Materials

Default Lit master `M_DecoPolish` with a pattern mask that switches between two polished materials inside one surface: for example black lacquer `#0f1a24` with gold `#c9a24b` metal lines, or cream marble `#e8dcc0` with teal `#1f4e4a` stone. Stone and lacquer use Roughness 0.08 to 0.15; lacquer may use Clear Coat. Gold is Metallic 1 at Roughness 0.2; chrome `#8fa3a8` at 0.1. Marble veining is a soft low-contrast texture; normal maps stay flat except fluting, so highlights run long and unbroken. Oxblood `#7a1f2b` is for upholstery and accent panels.

### Lighting and atmosphere

Lumen global illumination and reflections on, with hardware ray tracing preferred, because polished floors must mirror the room. Lights: Rect Lights hidden in coves, Spot Lights with narrow cones aimed upward from the floor at pilasters and statues (IES profiles help), and emissive fixtures of frosted glass. A light Volumetric Fog lets two or three strong vertical shafts show. Ambient level low so the palette stays dark and formal. Virtual Shadow Maps on. Manual exposure.

### Post-processing

Bloom Intensity 0.5 with Threshold 1 for a soft glow on fixtures only. Filmic tone curve; Contrast 1.1; Shadows tinted slightly teal, Highlights slightly warm. Vignette Intensity 0.3. Film Grain Intensity 0, Scene Fringe Intensity 0, Motion Blur Amount 0, depth of field off. Raise Lumen reflection quality in the volume. TSR anti-aliasing. No outline pass of any kind: lines exist only as inlaid metal in the materials.

### UI and effects

UMG frames are 2 px gold line borders with stepped corners (9-slice) on black `#0f1a24` or teal `#1f4e4a` fills, mirrored left to right; sunburst and chevron strip images divide sections. Titles use Limelight or Poiret One in capitals; body text uses Josefin Sans. Counters are tall `#c9a24b` numerals on black.

Niagara: radiating light rays as 12 to 16 thin additive gold sprites fanning from a point over 0.4 s; gold glints as four-point sparkle sprites, 0.2 s; sweeping spotlight beams as translucent cone meshes with DepthFade. Hits flash a brief sunburst, 0.15 s. Doors and panels open as mirrored pairs on smooth ease-in-out curves.

## Do / Do not

Do:

- Step and stack forms symmetrically.
- Use sunburst, chevron and fan motifs.
- Polish surfaces: brass, chrome, lacquer, marble.
- Uplight strong verticals.

Do not:

- Do not use organic whiplash curves and floral ornament; that reads as `083`.
- Do not cover machines in rivets, gears and tarnish; that reads as `095`.
- Do not use pastel boomerangs and starbursts with tail fins; that reads as `099`.
- Do not leave concrete raw; that reads as `097`.

## Nearest styles

- `095` Brass steampunk: surfaces here are smooth and polished, with a few flat inlaid patterns; `095` covers its machines in rivets, gears, tarnish and soot.
- `083` Art Nouveau ornamental poster: this style has no drawn outline, straight stepped geometry and polished rounded modelling; `083` has dark contour lines, flat colour fills and flowing floral curves.
- `099` Atomic-age Googie: this style is dark and formal in black, gold and teal; `099` is bright, sunny and playful in turquoise, coral and pink.

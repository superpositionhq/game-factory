# Mecha panel-line cel

Reference works: Mobile Suit Gundam.

## References

- *Mobile Suit Gundam* (1979), Nippon Sunrise (Yoshiyuki Tomino), animated TV series. https://en.wikipedia.org/wiki/Mobile_Suit_Gundam
- *Mobile Suit Gundam: Char's Counterattack* (1988), Sunrise, animated film. https://en.wikipedia.org/wiki/Mobile_Suit_Gundam:_Char's_Counterattack
- *Neon Genesis Evangelion* (1995), Gainax, animated TV series. https://en.wikipedia.org/wiki/Neon_Genesis_Evangelion
- *The Super Dimension Fortress Macross* (1982), Studio Nue and Tatsunoko Production, animated TV series. https://en.wikipedia.org/wiki/Super_Dimension_Fortress_Macross

## Visual definition

- **Shape language and proportions:** Humanoid machines built from large armour blocks with chamfered corners, vents, thrusters and antenna fins. Clear separation between armour plates and dark inner frame.
- **Line and outline:** Black outline on silhouettes plus thin panel lines dividing armour plates. Lines are straight and mechanical.
- **Shading model:** Two flat bands on armour, with a third hard white highlight streak on some edges.
- **Palette:** `#f2f2f2` `#1d3fa6` `#d62828` `#f6c90e` `#3a3f4b` `#9aa3ad` `#111111`. White armour with blue, red and yellow blocks; dark grey joints.
- **Lighting:** Single hard key in space or daylight; shadow shapes are large and simple.
- **Texture and surface:** None apart from panel lines, small warning marks and vent slots.
- **Atmosphere and post-processing:** Clean. Beam and thruster effects glow white-pink with bloom.
- **Camera and framing:** Low angle looking up for scale; long lens for poses.
- **UI and typography:** Cockpit-monitor UI: thin green or amber line frames, targeting brackets, range rings and angular gauges on dark grey. Text is a condensed stencil sans in capitals, like unit numbers and warning marks painted on armour; counters use blocky monospaced digits. Alerts are red blocks with yellow text; friendly markers are blue.
- **VFX and motion:** Pink-white beam shots, round layered explosion balls in flat pink, orange and white, thruster flares, drawn smoke trails and curving missile swarms. Machines move with weight: slow wind-up, hard stops and a held pose after each action, with a white streak sliding along armour edges.

## Fits

- **Genres:** `vehicle-combat`, `third-person-shooter`, `strategy`, `fighting`, `tower-defense`, `top-down-shooter`
- **Moods:** heroic, dramatic, militaristic
- **Settings:** space colony, orbital battlefield, desert military base, fortress city under attack

## Unreal recipe

### Assets

Hard-surface mecha are well suited to building from scratch in Blender background mode: large armour blocks with a single flat chamfer on each edge, vents, thrusters and antenna fins, mounted with real gaps over a separate dark inner frame. If a store mech is used, delete weathering, decals and normal maps, and re-cut panel lines. Panel lines are a texture drawn by script on rectified UVs: straight strokes at 45 and 90 degrees only, with small warning marks and vent slots.

### Materials

`M_ArmourCel`, Unlit. Colour comes from a region mask: white `#f2f2f2` dominant, with blocks of `#1d3fa6`, `#d62828` and `#f6c90e`; the frame uses `#3a3f4b`. Light vector from a Material Parameter Collection. `Step` on N·L with flat face normals gives two bands per plate, shadow being the region colour multiplied toward `#9aa3ad`. A third element, the white streak: a narrow band where the dot product of the normal and the half-vector crosses a threshold, masked to chamfer faces through vertex colour, with the threshold animated by a parameter so the streak slides along edges during poses. Panel lines multiply in as `#111111`. Silhouette line: inverted-hull Overlay Material of constant width. Thrusters and beams are Unlit emissive in white-pink.

### Lighting and atmosphere

For space scenes use no atmosphere, a star dome and one hard Directional Light for any Default Lit stage geometry; Lumen off. For daylight scenes add Sky Atmosphere and a flat Sky Light. Shadow shapes stay large and simple: Source Angle 0, no contact shadows, no ambient occlusion. Manual exposure.

### Post-processing

Keep it clean. Tone Curve Amount 0.2 so armour white stays white; Bloom Intensity 0.8 with Threshold 2 so only beams, thrusters and explosions glow. No grain, vignette, fringe or depth of field; Motion Blur Amount 0. No post-process line pass is needed since hull and texture lines cover silhouette and panels. FXAA or TSR at 100 percent.

### UI and effects

The HUD is a cockpit monitor: 1 px green or amber line frames, targeting brackets, range rings and angular gauges drawn with UI materials on dark grey. Text is a condensed stencil face (Saira Stencil One, Big Shoulders Stencil) in capitals; counters use monospaced blocky digits (Share Tech Mono). Alerts are red blocks with yellow text, friendly markers blue. Niagara: pink-white beam ribbons with a white core, explosion balls as layered Unlit spheres in flat pink, orange and white expanding over 0.5 s, thruster flare meshes, drawn smoke-trail ribbons and missile swarms on curved paths.

## Do / Do not

Do:

- Use single flat chamfers on armour edges.
- Separate plates with real gaps over a dark frame.
- Keep to white plus three primary blocks.
- Draw panel lines straight at 45 and 90 degrees.

Do not:

- Do not add weathering, scratches and hatching; that reads as `001`.
- Do not use organic costume shapes and many hues; that reads as `015`.
- Do not use smooth PBR metal; that reads as `013`.
- Do not round the forms into toy bricks with studs; that reads as `052`.

## Nearest styles

- `015` Two-tone fighting-anime cel: `015` shows organic characters in many strong colours with curved shadow shapes; this style shows mostly white machines with a few primary colour blocks and straight panel lines.
- `011` Clear-line adventure comic: `011` has no light or shadow, only one flat colour per surface; this style splits each armour plate into a lit tone and a shadow tone, with white highlight streaks on some edges.
- `098` Bauhaus primary geometry: `098` builds its forms from plain primary-coloured solids with no outline; this style draws a black outline and panel lines on every armour plate.

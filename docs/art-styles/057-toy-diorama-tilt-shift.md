# Toy-diorama tilt-shift

Reference works: Link's Awakening (2019).

## References

- *The Legend of Zelda: Link's Awakening* (2019), Grezzo, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Link's_Awakening_(2019_video_game)
- *Captain Toad: Treasure Tracker* (2014), Nintendo EAD Tokyo, video game. https://en.wikipedia.org/wiki/Captain_Toad:_Treasure_Tracker
- *Animal Crossing: New Horizons* (2020), Nintendo EPD, video game. https://en.wikipedia.org/wiki/Animal_Crossing:_New_Horizons
- *The Legend of Zelda: Echoes of Wisdom* (2024), Nintendo EPD and Grezzo, video game. https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Echoes_of_Wisdom

## Visual definition

- **Shape language and proportions:** Small, rounded, toy-like forms: stubby characters with bead eyes, trees as glossy lumps, houses like moulded play-set pieces. The world looks like a tabletop diorama.
- **Line and outline:** No outline.
- **Shading model:** Smooth, glossy plastic or glazed-toy shading with clear soft highlights.
- **Palette:** `#7ed957` `#4fc3f7` `#ffd54f` `#ff8a65` `#f5f5f5` `#8d6e63` `#ba68c8`. Bright, clean primaries and pastels: grass green, sky blue, yellow, coral.
- **Lighting:** Bright, soft overhead light with gentle shadows.
- **Texture and surface:** Almost none; smooth moulded surfaces with simple painted colour areas. Grass and water are simplified glossy shapes.
- **Atmosphere and post-processing:** Strong tilt-shift blur at the top and bottom of the frame to give a miniature scale; light bloom.
- **Camera and framing:** High three-quarter view (50 to 60 degrees down) with a long lens.
- **UI and typography:** Panels are rounded glossy plaques with soft drop shadows, and icons are small chunky toy models of the items they stand for. Type is a friendly rounded sans in white or cream. Counters are bold rounded numerals that pop in with a small bounce, with grass green, sky blue, yellow and coral accents.
- **VFX and motion:** Particles are simple chunky shapes: puffy white smoke balls, star bursts, glossy leaf and water blobs. A hit gives a quick squash, a white flash and a pop. Motion is bouncy with squash and stretch, short waddling steps and a toy-like wobble.

## Fits

- **Genres:** `action-adventure`, `puzzle`, `simulation`, `exploration`, `tower-defense`, `survival-craft`
- **Moods:** cheerful, cosy, whimsical
- **Settings:** island village, tabletop dungeon, toy town, seaside meadow

## Unreal recipe

### Assets

Rounded, stubby stylised packs fit well; realistic packs do not. To restyle, remove normal maps and roughness detail, flatten albedo to simple painted colour areas (posterise by script to three or four colours per prop), and bevel or subdivide hard edges until forms look moulded. Trees become glossy lumps, grass a few thick blades or a smooth sculpted surface, houses one-piece play-set shells. Characters get large heads and bead eyes. Build terrain as a tabletop tile set with rounded edges.

### Materials

`M_Toy`: Default Lit. Base Color from the flattened texture or a parameter (`#7ed957`, `#4fc3f7`, `#ffd54f`, `#ff8a65`, `#f5f5f5`, `#ba68c8`), Roughness 0.25 to 0.35 uniform, Specular 0.5, no normal map. Hero pieces and eyes use Clear Coat 1.0 with Clear Coat Roughness 0.1 for a glazed look. Water is Single Layer Water with a simple slow normal and strong colour. No fingerprints, scratches, studs or texel grids; clean, freeform gloss is what distinguishes it from clay, brick and pixel dioramas.

### Lighting and atmosphere

Lumen GI and reflections on. A Directional Light from high overhead with a wide Source Angle (3 to 5 degrees) for gentle shadows, a bright Sky Light with Real Time Capture, Sky Atmosphere optional but mostly out of frame. Contact Shadows on. Light Exponential Height Fog only to soften the far edge of the table. Auto Exposure in a narrow EV100 range or manual, bright.

### Post-processing

Tilt-shift is the signature. Camera 50 to 60 degrees down with a long lens (85 to 120 mm), Depth of Field at low f-stop focused on the player, which blurs the top and bottom of the frame. If the focus plane does not give enough, add a post material at Scene Color After DOF that blurs PostProcessInput0 with a 9 to 13 tap kernel whose radius grows with distance from screen centre in Y, leaving the middle 40 percent sharp. Bloom 0.4, Saturation 1.1, Vignette 0.2. TSR on. Grain, fringe and Motion Blur Amount 0.

### UI and effects

Panels are Rounded Box brushes with a glossy top highlight and soft drop shadow, white or cream text in Nunito ExtraBold or Quicksand Bold. Icons are small renders of the chunky item models. Counters are bold rounded numerals that pop in with a 0.15 s overshoot scale; accents in grass green, sky blue, yellow and coral. Niagara uses mesh renderers: puffy white smoke spheres (4 to 6, lifetime 0.6 s, scale up then down), star-burst meshes, glossy leaf and water blobs. A hit gives a squash, a one-frame white emissive flash and a pop of three stars.

## Do / Do not

Do:

- Round every form like a moulded toy.
- Blur the top and bottom of the frame.
- Use glossy clean materials.
- View from a high angle with a long lens.

Do not:

- Do not add fingerprints and matte clay; that reads as `048`.
- Do not build from studded bricks; that reads as `052`.
- Do not use low-poly blurry-textured forms without gloss; that reads as `037`.
- Do not use pixel sprites; that reads as `047`.

## Nearest styles

- `048` Claymation: surfaces here are smooth, glossy and clean, in many bright colours; `048` is matte clay with fingerprints and tool marks, in fewer colours.
- `037` N64 filtered fog: scenes here are bright, with smooth rounded glossy forms and blur only at the top and bottom of the frame; `037` has angular low-polygon models, blurry matte textures and distance fog.
- `052` Brick toy: this style has freeform rounded shapes in a wide range of soft bright colours; `052` assembles everything from studded bricks in a few strong solid plastic colours.

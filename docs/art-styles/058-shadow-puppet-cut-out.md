# Shadow-puppet cut-out

Reference works: The Adventures of Prince Achmed.

## References

- *The Adventures of Prince Achmed* (1926), Lotte Reiniger, silhouette animated film. https://en.wikipedia.org/wiki/The_Adventures_of_Prince_Achmed
- *Tales of the Night* (2011), Michel Ocelot, animated film. https://en.wikipedia.org/wiki/Tales_of_the_Night_(film)
- *Badland* (2013), Frogmind, video game. https://en.wikipedia.org/wiki/Badland_(video_game)

## Visual definition

- **Shape language and proportions:** All figures and scenery are flat black cut-outs with intricate lace-like perforations: filigree costumes, leaf-by-leaf trees, ornate arches. Figures are in strict profile with jointed limbs.
- **Line and outline:** No line. The silhouette edge is the drawing.
- **Shading model:** None. Foreground shapes are solid black; depth layers behind are progressively lighter translucent tones.
- **Palette:** `#000000` `#f2a23a` `#d9482b` `#2a6f97` `#f6e3b4` `#7a3b69`. Black over a luminous coloured background: amber, red-orange, or deep blue, with a soft bright centre.
- **Lighting:** Back-lit screen: a glowing light source behind translucent layers.
- **Texture and surface:** None in the black. The backlight has a soft gradient and faint paper or tissue mottling.
- **Atmosphere and post-processing:** Slight glow bleeding around silhouette edges; vignette.
- **Camera and framing:** Fixed, flat, orthographic side view.
- **UI and typography:** All UI is black cut-out: filigree frames, perforated borders and silhouette icons laid over the glowing backdrop. Type is an ornate cut-paper display face with thin serifs and curled flourishes, in solid black or cut through so the backlight shows as amber letters. Numbers are plain black silhouette numerals.
- **VFX and motion:** Effects are silhouettes too: black paper sparks and leaves, smoke as layered translucent tissue, and magic as bright holes of backlight that flare through the black. Figures move like jointed puppets, with limbs that pivot at pin joints, a slight frame-by-frame jitter and held profile poses.

## Fits

- **Genres:** `platformer`, `puzzle`, `action-adventure`, `stealth`, `exploration`
- **Moods:** enchanted, eerie, theatrical
- **Settings:** Arabian Nights palace, enchanted forest, fairy-tale kingdom

## Unreal recipe

### Assets

All art is flat cut-outs, authored by script. Draw each figure and scenery piece as a black shape with lace-like perforations (filigree costume, leaf-by-leaf trees, pierced arches) into a high-resolution alpha texture, 2048 px for hero figures so fine holes stay crisp. A store pack can donate silhouettes: render its props in profile to a mask in an editor script, then cut ornamental holes with Pillow. Figures are in strict profile, split into limb cards pinned at joints on a 2D rig. Arrange cards on parallel planes for depth layers.

### Materials

`M_Silhouette`: Unlit, Masked, Base colour `#000000`, opacity mask from the cut-out alpha; perforations are real holes in the mask so the backdrop shows through. Depth layers behind the play plane use a Translucent Unlit instance with a `LayerTone` parameter that lerps black toward the backdrop colour (about 25 percent lighter per layer), like tissue seen through the screen. `M_Backlight`: Unlit, a radial gradient from a bright centre `#f6e3b4` to amber `#f2a23a`, red-orange `#d9482b` or deep blue `#2a6f97`, multiplied by faint tissue mottling, emissive about 3 at the centre. Nothing is lit from the front and nothing is drawn inside a figure.

### Lighting and atmosphere

No lights, no Lumen, no shadows, no fog. The backdrop card is the only source of brightness. Manual exposure.

### Post-processing

Orthographic camera, fixed side view. Bloom Intensity 0.6 with Threshold about 1 so the backlight bleeds slightly round silhouette edges and through perforations. Vignette 0.6. TSR on; edges must be clean, not jagged. Tone curve default, Saturation 1.1. No grain, which would push it toward grey fog silhouettes; no fringe, no depth of field, Motion Blur Amount 0. No post materials.

### UI and effects

UI is black cut-out on the glow: filigree 9-slice frames and perforated borders as alpha textures tinted black, silhouette icons. Lettering in Cormorant Bold Italic or Limelight, either solid black or as a cut-through: black panel with letter-shaped holes so amber shows. Numbers are plain black silhouette numerals. Niagara: black paper sparks and leaves as Masked Unlit sprites (10 to 25, lifetime 1.5 s, tumbling), smoke as stacked translucent tissue sprites using the layer tone, magic as additive emissive sprites in the backdrop's bright centre colour that flare through the black for 0.3 s. Puppet animation: limbs pivot only at pin joints, poses update at 12 fps with a one or two pixel positional jitter per update, and profile poses hold.

## Do / Do not

Do:

- Keep all foreground shapes solid black.
- Cut fine perforations into silhouettes.
- Use a glowing coloured backdrop with a bright centre.
- Stage in flat profile with an orthographic camera.

Do not:

- Do not use grey fog and film grain without colour; that reads as `070`.
- Do not add incised line detail inside figures on an orange ground; that reads as `087`.
- Do not light the figures from the front.
- Do not use a few coloured flat shapes without black dominance; that reads as `064`.

## Nearest styles

- `070` Silhouette fog monochrome: backdrops here glow amber, red-orange or deep blue; `070` is entirely grey, with fog and film grain.
- `087` Greek black-figure pottery: figures here are pure black, with detail only as holes cut through to a glowing backlight; `087` scratches fine light lines inside its black figures and sets them on a flat, unlit terracotta ground.
- `064` Mid-century cut-paper poster: this style is dark, with black shapes filling most of the frame over a glowing backdrop; `064` is a bright poster of a few flat coloured paper shapes with little black.

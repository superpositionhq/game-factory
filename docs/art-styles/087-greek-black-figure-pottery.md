# Greek black-figure pottery

Reference works: Exekias; Apotheon.

## References

- *Achilles and Ajax playing a board game (Vatican amphora)* (c. 540-530 BC), Exekias, black-figure amphora. https://en.wikipedia.org/wiki/Exekias
- *Francois Vase* (c. 570 BC), Kleitias and Ergotimos, black-figure krater. https://en.wikipedia.org/wiki/François_Vase
- *Apotheon* (2015), Alientrap, video game. https://en.wikipedia.org/wiki/Apotheon
- *Hercules* (1997), Walt Disney Feature Animation, animated film. https://en.wikipedia.org/wiki/Hercules_(1997_film)

## Visual definition

- **Shape language and proportions:** Figures as black silhouettes in strict profile: profile head with frontal eye, frontal torso, profile legs; long limbs, pointed beards and feet. Shields, spears, horses, chariots. Bands of ornament divide the surface.
- **Line and outline:** Fine incised lines inside the black figures, showing the clay colour: muscles, hair, armour patterns, drapery folds.
- **Shading model:** None. Flat black on flat orange.
- **Palette:** `#c96a2b` `#1a1512` `#e08a45` `#7a2f1a` `#f2e2c4` `#5a2a1a`. Orange terracotta ground and glossy black, with small added dark red and white (cream) details.
- **Lighting:** None in the image. On a real vessel, a soft highlight on the curved glazed surface.
- **Texture and surface:** Ornament bands: meander (Greek key), palmettes and lotus chains, rays at the base, tongues at the shoulder. Slight clay speckle; brush streaks in the black gloss.
- **Atmosphere and post-processing:** None.
- **Camera and framing:** Side-on frieze view, orthographic; or a product view of a vessel.
- **UI and typography:** Panels are terracotta-orange fields or black bands edged with a meander strip; icons are black silhouettes with incised detail (helmet, shield, lyre, amphora). Text is in monoline capitals with the angular letterforms of Greek inscriptions, black on orange or cream on black. Numbers use the same face, with dark red for damage.
- **VFX and motion:** Particles are flat black or cream shapes: dust as scalloped silhouettes, blood as dark red drops, fire as stylised flame tongues. A hit flashes the figure cream or dark red for one frame, with short radiating lines. Animation is stiff profile poses on twos, with limbs that rotate like jointed cut-outs.

## Fits

- **Genres:** `hack-and-slash`, `platformer`, `action-adventure`, `fighting`, `sports`, `strategy`
- **Moods:** heroic, mythic, austere
- **Settings:** ancient Greece, Mount Olympus, the underworld, Trojan battlefield

## Unreal recipe

### Assets

Play on a side-on frieze. Characters can be rigged store humans (hoplites, horses, chariots) restyled, because only their silhouette survives; choose ones with spears, crested helmets, round shields and pointed beards, and pose animation in strict profile. Build ornament by script: meander strips, palmette and lotus chains, base rays and shoulder tongues as tiling textures on band meshes above and below the play lane. Menus show a lathe-turned amphora from Blender.

### Materials

`M_BlackFigure`, Unlit. Figures output glossy black `#1a1512`. Incised lines come from a per-asset mask texture, made by script from the original normal map (edge-detect the normal map, threshold, thin to 1 to 2 texels) and from hand-placed curves for muscles, hair and armour patterns; where the mask is set the material outputs clay `#e08a45`. Two extra mask channels add dark red `#7a2f1a` (cloaks, manes) and cream `#f2e2c4` (women's skin, shield devices). The ground is `#c96a2b` multiplied by a fine clay speckle; black areas multiply in faint horizontal brush streaks. The menu vessel is the exception: Default Lit, Roughness 0.25, showing one soft highlight.

### Lighting and atmosphere

None in play. No lights, Lumen off, shadows off, no fog or sky; the background is the flat orange field. Use an orthographic camera locked side-on. Manual exposure. The vessel view uses one Rect Light and a Sky Light with a plain grey cubemap.

### Post-processing

No outline pass: figures are already solid silhouettes, and adding edges would thicken them. Volume: Tone Curve Amount 0, Bloom Intensity 0, Film Grain Intensity 0, Vignette Intensity 0, Scene Fringe Intensity 0, Motion Blur Amount 0, no depth of field. One optional post-process material at Scene Color After Tonemapping snaps every pixel to the nearest of the six palette colours in a Custom node. Anti-aliasing FXAA (`r.AntiAliasingMethod=1`).

### UI and effects

UMG panels are orange `#c96a2b` fields or black bands, each edged with a tiled meander strip image. Type is a monoline angular face such as GFS Neohellenic or Jost in spaced capitals, black on orange or cream on black; damage numbers are `#7a2f1a`.

Niagara uses flat, opaque sprites with no blending: dust as scalloped black or cream silhouettes (4 to 6, 0.4 s), blood as dark red teardrops on short arcs, fire as flame tongues flipping between three frames at 8 frames per second. On a hit, a Custom Primitive Data value switches the figure to cream or dark red for one frame and 6 short radiating lines appear for 0.1 s. Sample animation on twos (stepped pose time) so limbs move like jointed cut-outs.

## Do / Do not

Do:

- Draw figures as black profile silhouettes on orange.
- Incise fine clay-coloured detail lines inside figures.
- Add meander and palmette bands.
- Keep everything on a baseline frieze.

Do not:

- Do not use a glowing gradient backlight with lace-like perforations; that reads as `058`.
- Do not reverse to orange figures with black background without incised lines (that is red-figure, a different target).
- Do not add shading or perspective.
- Do not add more colours; that reads as `086`.

## Nearest styles

- `058` Shadow-puppet cut-out: this style has a flat orange ground and fine clay-coloured lines cut inside the black figures; `058` has a glowing gradient backdrop and pure black silhouettes with lace-like perforations and no interior lines.
- `086` Insular illuminated manuscript: this style uses only black and orange with small touches of dark red and cream; `086` uses many strong colours on a cream vellum ground.
- `064` Mid-century cut-paper poster: this style has dark figures with incised detail on orange, between regular ornament bands; `064` is a lighter picture of plain cut shapes with crooked edges and no interior detail.

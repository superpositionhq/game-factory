# ASHGROVE (`horror-escape`)

Fill-in for [../game-session.md](../game-session.md). Original prompt: [../original/game-horror-escape.md](../original/game-horror-escape.md).

| Placeholder | Value |
|---|---|
| `{{GAME_TITLE}}` | Unreal game 2: horror escape |
| `{{SLUG}}` | horror-escape |
| `{{PROJECT}}` | HorrorEscape (`HorrorEscape.uproject`, modules `HorrorEscape` + editor `HorrorEscapeEditor`, from the First Person C++ template) |
| `{{GENRE_LINE}}` | a first-person HORROR ESCAPE / puzzle game in an old house at night |

## {{PITCH}}

1934: Thomas Vale comes back to Ashgrove, the late-Victorian house he left thirteen years ago, and the front door
shuts behind him. He works down through the ground floor, the basement and the attic, each a chain of linked
puzzles, while something eyeless hunts the house by sound and porcelain dolls move whenever he isn't looking.

## {{BRIEF}}

- First person: walk 260 / sprint 470 (loud) / crouch 140 cm/s, lean Q/E (camera roll +-12 deg, blocked by walls),
  step-synced head bob, sway, landing dips, breathing. Flashlight with battery (drain 1.1 %/s, flicker below 15 %,
  batteries +45). Interact trace 220 cm: pick up, inspect/rotate, doors, drawers, notes, hide. Inventory + journal.
- 3 chapters, one map each, saved at chapter start, death restarts the chapter. Puzzles are linked through a flag bus
  (`UHorrorPuzzleSubsystem`):
  - Ch1 ground floor: clocks stopped at 4, 9, 2 -> desk lock 4-9-2 -> fuse A; fuse B in the kitchen -> fuse box lever
    -> power; parlour shadow play (rotate tin cut-outs until the shadows match the painting) -> basement key.
  - Ch2 basement: wireless plays 4 notes -> strike laundry pipes 3-1-4-2 -> valve handle; boiler valves with
    gauge = 1A + 2B + 3C held at 10 for 2 s -> cellar door; black bottles per rack 3-1-5-2 -> strongbox -> attic key.
  - Ch3 attic: moonbeam through two mirrors (45 deg / 45 deg; 225 also works) onto the dollhouse crystal -> crank;
    music box stops at moon, bird, key, eye -> trunk symbol lock -> roof hatch key -> ending at dawn.
- The stalker (from ch2): roams, investigates noise, chases (400 ch2 / 440 ch3), lunges x1.45 inside 4.2 m, searches,
  opens up to two wardrobes near where it lost you; sight 60 deg, 900 cm in darkness, 1800 cm if your light is on or
  you stand in light; contact = death. Hide in wardrobes and cupboards (peek through slats).
- Watchers: porcelain dolls that move only when unobserved (out of view, or in darkness beyond 6 m), 70 cm per step
  with a scrape; touching distance kills. One wakes in the wine cellar, three in the attic.
- Scripted scares once each (Sequencer, flicker, slams), never jump-scare spam. Sequencer intro and ending.
- Atmosphere: Lumen with warm practicals (2400-2800 K) and cold moonlight, volumetric fog, Niagara dust in light
  shafts, scanned PBR surfaces, limited exposure range, vignette, grain. Heartbeat, breath and drone by stalker distance.
- HUD minimal (dot, prompt, battery, item toast on paper slips, subtitles). Main menu (Continue, New Game, Chapter
  select, Settings, Quit), pause, settings (master / music / SFX volume, sensitivity, invert Y, resolution,
  fullscreen, brightness), death / retry. Period UI in IM Fell English on aged paper, no plain text.
- Sound: synthesized MetaSounds (ambience beds, creaks, heartbeat, stalker breath, doors, puzzles, thunder, UI),
  recorded footsteps per surface, a dark-ambient score per chapter. No recorded or synthesized voices.

## {{SCENARIOS}}

1. The house remembers — `L1_GroundFloor`, entry hall, front door shut, no items, flashlight on the hall table — win:
   basement door opened with the basement key / lose: timeout only (no threat on the ground floor)
2. Something is down here — `L2_Basement`, stair foot, no items; the stalker sleeps until the wireless plays — win:
   service-stair door opened with the attic key / lose: stalker or doll contact, timeout
3. Ada — `L3_Attic`, hatch landing, no items; lightning glimpse at once, the stalker returns on `beam_solved` — win:
   roof hatch opened with the roof key (ending plays) / lose: stalker or doll contact, timeout

## {{STORY}}

In 1921 Thomas quarrelled with his father, left at 2 a.m. and left his oil lamp burning on the attic stair for his
little sister Ada; by 4 the nursery was on fire. The father, a clockmaker, came out blind and burned, stopped every
clock at the hour someone left, and became the stalker (red ribbon on its wrist, the only ticking watch in the house).
Told by the house: scratched-out faces in photographs, a table laid for four, height marks, the tally-marked cot by the
boiler, the burned nursery, five notes under 25 words, one line per chapter card ("Every clock in Ashgrove stopped on
the night someone left."). Payoff: Ada's trunk holds Thomas's lamp; at dawn on the roof the creature stops at the edge
of the light, sits facing the sun, and the ticking stops.

## {{ART_PACKS}}

- `fab-ue\modular-victorian-house\` (bought): furniture, fireplaces, panel doors and frames, balusters, carpets,
  props; its grime texture drives the `M_ArchHQ` grime mask.
- `fab-ue\victorian-interior-environment\` (bought, lands as `/Game/OldLibrary`): dining chairs, dust covers, boards;
  its paper texture is the UI paper.
- `fab-ue\whisper\`: the stalker body and its own clips. `fab-ue\free-killer-doll-character\`: the porcelain dolls.
- `fab-ue\essential-footsteps-sfx\`: footsteps per surface. `fab-ue\gothic-horror-music\` (Whispers of Macabre):
  one looping score per chapter and the menu.
- Megascans surfaces: `fab\old-decorative-wallpaper-umridamn\` (tinted green damask), `fab\wooden-floor-ucklejqdy\`,
  `fab\brick-wall-worn-sexkaitb\`; CC0 `polyhaven\horror-textures\` (plaster, decrepit wallpaper, concrete, planks).
- `fonts\IMFellEnglish\` (OFL): all UI, notes and cards.
- Copied but unused: `fab-ue\zombie-animation-pack-standard\`, `fab-ue\horror-props\`,
  `fab-ue\modular-old-power-plant-65-assets\`. Music box and thunder stay synthesized (the Fab packs are UE 5.5 only).
- Built here: level layouts, puzzle props (dials, clocks, pipes, valves, mirrors, dollhouse, trunk), story textures,
  all MetaSounds, sequences.

## {{GAME_NOTES}}

- The design doc gives two shadow-play solutions (crow 45 deg and crow 0 deg); the later one is house 0, crow 0,
  moon 180 (crescent opening right). Check the rotator targets in the level script before relying on either.
- Collision overrides set from Python did not persist: the `TraceThrough` tag is applied at runtime so low furniture
  doesn't block sight/aim and the dollhouse crank is reachable.
- Shipping build broke on an editor-only call (`GetActorLabel`): use `GetActorNameOrLabel`.
- Fairness rules that made chapters 2-3 playable: the stalker keeps its distance for 18 s after waking or a scripted
  reveal, roams far from a hidden player, the corridor lamp dies at the blackout, candles/lightning do not reveal you,
  dolls hold still during puzzle close-ups.
- Foot sliding: stalker clip rates come from measured stride speeds; the ending creature must not glide out of the hatch.
- Bot (`UHorrorBotComponent`) runs a per-chapter plan from the known solutions (go to tag, look, interact, set dial,
  rotate piece, strike chimes) via `IA_Move` / `IA_Look` / `IA_Interact`, and hides when chased. It wins chapter 1;
  in chapters 2-3 it still dies to the stalker before the boiler / music box. Next: wait out a prowling stalker before
  crossing lit corridors, per-chapter flee targets.
- Ending v2 (creature at the hatch at dawn) is built but not watched in a run; the scratch decal on the family photo
  needs a close-up check. Cellar doors, hall stairs, puzzle clocks, radio, valves and fuse box are still our meshes.
- Keep `r.RDG.AsyncCompute=0` (startup GPU hangs). Workflow row ids are `hx-NNNNN`.

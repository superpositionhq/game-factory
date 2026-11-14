# Task probes: the contract for `probe` checks

How a task author writes the checks that decide whether a game task passes. It goes with the task format
([schemas/game-task.schema.json](schemas/game-task.schema.json), `GameTask`, game-task/1) and the `write-tasks` skill
([skills/write-tasks/SKILL.md](../skills/write-tasks/SKILL.md)), and `tools/validate-game.py` checks every rule below
that can be checked without running the game.

**Pass/fail is deterministic (owner's decision, 2026-10-19).** A task passes or fails only on checks the checker computes
from the running game or from the project: `build`, `boot`, `log_absent` and `probe`. A model judge never decides
pass/fail, and nothing is graded from pixel statistics of the game's frames except one: the frame's mean luminance
(`screen`, section 2.15; the owner, 2026-11-06), whose threshold is always calibrated or relative to the start, so the
same machine measures both sides. Judges (`judge`, `code_judge`) stay as **non-gating** quality checks
(`"required": false`). Nothing in a task reads the agent's tool calls: a task is graded on the game's outcome
alone. Retired (the owner, 2026-11-13): `actions_judge` checks and `trace` probes; never add one, take them out of a
task you edit.

Words used here:
- **the start**: the game at the task's `seed.commit`, as the agent receives it;
- **the fix**: the developers' own solution, `seed.reference` (bug fixes and corrections; most features and changes
  have none);
- **the checker**: what builds, plays and measures a game for a task, the same way for the start, the fix and an
  agent's result;
- **the task check**: what makes a task valid before any agent is given it (section 4).

## 1. The check

```json
{
  "name": "hero_on_ground",
  "kind": "probe",
  "required": true,
  "weight": 3,
  "needs": ["boots_clean"],
  "describe": "Two seconds after the scenario starts, the hero stands on ground near the west kiln tower instead of falling under the town.",
  "play": "look",
  "measure": { "probe": "pawn", "field": "z", "window": [3, 18], "agg": "min" },
  "expect": { "op": ">=", "calibrate": 0.5 }
}
```

- `describe` (required, at most 400 characters): the assertion in plain English, shown in the grade (never to the
  agent).
- `play`: where the measurement is taken (section 1.1).
- `measure`: what to measure (section 2). Every measure reduces to **one number** (booleans are 0/1).
- `expect`: the threshold that number is compared with (section 1.2).

### 1.1 Plays

- `"look"`: the checker's idle play of the task's `play_map`: 20 s, no input, sampled every 0.5 s.
- `"drive"`: the checker's scripted drive of `play_map`: 22 s, W 1-6 s, D 6-8 s, W 8-13 s with a jump (SpaceBar) at
  9 s, A 13-15 s, W 15-21 s; sampled every 0.5 s.
- A **task play**, when the outcome needs other input or another start:
  ```json
  {"name": "aim_left", "seconds": 12, "every": 0.5,
   "map": "/Game/Maps/L_Level2?Scenario=2", "args": ["-AutoPlay", "-Scenario=2"],
   "inputs": [{"t": 0.2, "teleport": [1200, -340, 180], "yaw": 90},
              {"t": 1.0, "key": "W", "press": true}, {"t": 3.0, "key": "W", "press": false},
              {"t": 4.0, "key": "MouseX", "axis": -4.0},
              {"t": 6.0, "cursor": [0.5, 0.6]}, {"t": 6.1, "key": "LeftMouseButton", "press": true},
              {"t": 8.0, "widget": "RetryButton", "click": true}]}
  ```
  - `name`: not `look`, `drive`, `editor` or `trace`. Plays with the same name in one task must be identical.
  - `seconds`: 5-120. No input at or after the end.
  - `every`: the sampling step, 0.1-1.0 s (default 0.5).
  - `map` (optional): the map and URL options this play opens instead of the task's `play_map`.
  - `args` (optional): game flags on the play's command line, `-Name` or `-Name=value` (name: letters and digits;
    value: `[A-Za-z0-9_.:=,-]{1,60}`, for dev flags like `-DevMenu=2:quest=bull,6:fell`; any `Name=` inside a value counts as
    setting that flag too). Never the engine flags the checker sets itself: ExecCmds, Run, NullRHI, Log,
    Unattended, RenderOffscreen, ResX, ResY, Benchmark, FPS, Game, Windowed, nor the checker's own measurement flags
    (any flag starting with `-TaskProbe`, the TaskProbe plugin's; `tools/validate-game.py` lists what it refuses).
  - `inputs`, each at time `t` (seconds of play):
    - a key: `{"t": 1.0, "key": "W", "press": true}` and later `"press": false` (Unreal key names: W, A, D, SpaceBar,
      LeftShift, LeftMouseButton, F2, Escape, ...);
    - an axis event: `{"t": 2.0, "key": "MouseX", "axis": 4.0}` (MouseX, MouseY, Gamepad_LeftX, ...; see the lessons
      on mouse axes in section 5);
    - a widget click: `{"t": 6.0, "widget": "RetryButton", "click": true}` clicks the first visible button widget of that
      name or class, as a player would;
    - the cursor: `{"t": 1.0, "cursor": [0.5, 0.6]}` moves the mouse cursor to a viewport point (fractions 0-1); a
      following `LeftMouseButton` press clicks there;
    - a teleport: `{"t": 0.2, "teleport": [x, y, z], "yaw": 90}` places the player pawn (cm, facing `yaw`): the way
      to reach a test spot;
    - a teleport next to an actor: `{"t": 0.2, "teleport_to": <actor select>, "distance": 200, "offset": [x, y, z],
      "face": <Point>}` places the pawn `distance` cm (default 200) from the actor the select matches nearest to it, on
      the pawn's side and level with it, plus `offset` (default none), facing `face` (a point, section 2.13) or else
      that actor; the engine's teleport then finds a free spot near there. The way to reach a spot each build chooses
      itself (the ore a fix placed, a door it moved). No match: nothing happens (the play's log says so);
    - holding the pawn there: `"hold": 5` on a `teleport` or `teleport_to` (seconds, up to 120) puts the pawn back at
      the spot (its location; its view stays free) after every tick of the world for that many seconds of play, after
      the game's own tick. For a game that sets its player's ground position every tick, which would otherwise undo
      a teleport at once. Without `hold`, a teleport places the pawn once, as before;
    - a wait in real time: `{"t": 8.0, "wait": 30}` (seconds, more than 0). Plays run on a fixed 30 fps clock as fast
      as the machine renders, so what runs on the wall clock (a menu that pages on real time, a timer on the
      platform's clock) sees less real time than the play's seconds. At `t` the play's clock holds while the game
      keeps running, paced to real time (each frame waits for the wall clock to catch up with the game's own time),
      until `wait` real seconds and `wait` seconds of game time have both passed; nothing is sampled, sent or
      screenshot meanwhile; then the play goes on from `t`. A play's waits add at most 300 s in all, and its timeout
      grows by them; `seconds`, windows and `at` stay in play time, within 120 s;
    - a named screenshot: `{"t": 6.0, "shot": "pause_menu"}` (a letter or `_` first, then letters, digits, `_`; up to
      32) takes `shot_pause_menu.png` at that moment, with the UI, beside the evenly spaced ones. Each name once in a
      play, 20 at most. A picture never passes or fails anything by itself: it is for a judge (section 3.2) and for
      whoever reviews a run;
    - a map travel: `{"t": 10.0, "map": "/Game/Maps/L_Yard?Scenario=2"}` opens that map with its options, as the game's
      own travel does. The play's clock runs on through the load; inputs and samples wait for the new world's player;
    - a view turn: `{"t": 10.5, "view": [-15, 90]}` turns the player's view (its control rotation) to that pitch and yaw
      in degrees (pitch -89 to 89).

  With these, one launch tours several places and scenarios and pictures each: travel, teleport (or `teleport_to` what
  the build placed), turn, shot. **The grader's tour lives in the task**, which the agent never sees, so a build can't
  dress only the spots that are photographed. Place shots by what the build made (`teleport_to`), not by a list of
  views kept in the game itself.
  - A play that measures audio (an `audio` measure, section 2.16) runs with sound, muted; every other play runs
    without (section 2.16).
  - `after` (optional): the task plays that run, and end, before this one on each side:
    `{"name": "reads_save", ..., "after": ["writes_save"]}`. Names are task plays of the same task (a probe's play or
    a judge's own `plays`), never `look`, `drive`, `editor` or `trace`, never the play itself, never a cycle;
    `tools/validate-game.py` refuses each. **A play that reads what another play writes names it in `after`. Never
    rely on the grader's order:** without `after`, the checker and the Lab's grader play a side's plays in the order
    its checks first ask for them, which is not the order the task lists them in and can change. A play that failed or
    was cut short still counts as run: the plays after it run anyway and read whatever it left, so the failure shows
    in their own checks. Plays without `after` keep the order they always had.
  - **Saves.** A side's plays all run on one copy of the game (the start's, the reference's, the agent's), and between
    launches only the probe's own folder is cleared: the rest of the project's `Saved/` folder stays, `SaveGames/`
    among it. So a save one play writes is there for every later play of that side, and every earlier play (the
    boot, `look`, `drive`, other task plays) may have written there too. `after` orders a play after its writer; it
    never gives it a clean `Saved/` folder. The two sides never share one.
- `"editor"`: a headless editor pass over the project as saved; takes only `asset` measures, and `asset` measures
  are taken only there.
- `"trace"`: retired with the `trace` probe (section 2.12); never use it.

### 1.2 Thresholds (`expect`)

`op` is one of `>`, `>=`, `<`, `<=`, `==`, `!=`. The threshold is one of:

- **A literal value**, `{"op": ">=", "value": 1}`: for facts that don't depend on the scene (counts, booleans, "not
  the default material"). `==` and `!=` take literals only (they compare within 1e-9).
- **Calibrated**, `{"op": ">=", "calibrate": 0.5}` with `0 < f < 1`: for continuous quantities. The checker measures
  the start (`s`) and the fix (`r`) in its own environment and sets the threshold `s + f * (r - s)`; `op` says on which
  side the fix lies (`>`/`>=` when `r > s`). Needs `seed.reference`. A calibrated check whose start and fix measure the
  same (within 1e-6 relative) makes the task invalid. Calibrated thresholds are kept by the checker, never written into
  the task.
- **Relative to the start**, for a task with no fix (most features and changes): `{"op": ">=", "start_times": 1.3}`
  (threshold `s * 1.3`) or `{"op": ">=", "start_plus": 500}` (threshold `s + 500`), measured on the start.

When the start can't be measured (its play ended before the window), a calibrated threshold anchors on the fix alone:
`r - 0.25 * |r|` for `>`/`>=`, `r + 0.25 * |r|` for `<`/`<=`. When the fix can't be measured, or the start of a
`start_times`/`start_plus` check can't, the task is invalid for that check.

### 1.3 Staging a contact, and reading it

An ask that only shows after a blow, a shot, a hit taken or a foe falling is checked by making the contact happen at a
time the play knows, then reading what changed. Names come from the task's start commit, never from the instruction.

**Stage it** (each a miss in `inputs_missed` when nothing takes it: the check fails, or it is a task error when the
reference misses too):

- `{"t", "pin": <actor select>, "hold": s, "front": cm | "at": <point>, "offset": [x, y, z]}`: the nearest match
  (never the player) held at its place for `hold` s while its own AI, animation and attacks run on; first set `front`
  cm ahead of the player (at its own height above the ground) or `at` a point, facing the player. The player's own
  blow or shot, by the task's keys, lands on it. A target the build invents: `{"player": false, "has": {"class":
  "PrimitiveComponent", "movable": true, "visible": true}, "near": {"point": {"pawn": true}, "radius": cm}}`, the
  nearest movable drawn thing near the player; where that is not surely the target, the ask is not testable.
- `{"t", "damage": points, "to": <select>, "from": <select>}`: `UGameplayStatics::ApplyPointDamage` on the nearest
  match (`{"player": true}`: the player), in a game that takes damage through the engine (every game under the combat
  contract, docs/game-format.md).
- `{"t", "set": "<property path>", "on": <select>, "value": v, "all": bool}`: a start-named property written to set a
  fight up (a foe's health at 1, the player's high), never to decide what the check reads.
- `where` in any actor select: `[{"prop": "<path>", "op": "==", "value": v}]` (only foes not dead, a bay's group);
  `"player": false`: anything but the player. `set` and `where` only on members the task does not ask to change.

**Read it deterministically**, in a probe one sentence explains:

- a thing gone or drawn (`drawn`, a count), a start-named state or property (`prop:`);
- a sound started (`audio` `started_audible` near the place it lands, section 2.16);
- **a hit stop** (0.05 to 0.1 s: no screenshot shows it): `world` `time_dilation` (section 2.20) where the stop slows
  the world, actors `frozen` where it is the actor's own (the longest short stop that ended since the previous sample:
  frames in which the actor moved under 0.1 cm and no bone of its skinned meshes moved 0.1 cm, between two frames of
  motion, 0.5 s at most), in a tight window right after the contact, never on an actor a pin or teleport holds,
  paired with `world` `paused` == 0; the start's play must read 0;
- **a stagger, a knock-back or an interrupted action** (behaviour, not looks): actors `montage` 1 in a short window
  after the hit and 0 before it; the actor can't act (the move key held through the window: its `speed` or `moved`
  near 0, then moving again after it); a start-named staggered state; a knock-back as its place moving away from the
  attacker (`dist` rising);
- actors `damage_taken` (what its TakeDamage returned for the play's `damage` stages, summed): in a game under the
  combat contract, where TakeDamage returns the damage actually applied, what a hit did; actors `focus_player` (1 when
  its AI controller watches the player).

**What it looks like** (sparks, colours, glow, readability) goes to the required `looks_as_asked` judge with its own
play staged the same way and named `shot` frames a few hundredths of a second apart across the contact. A pose may be
an extra rubric item, never the only check of a behaviour.

### 1.4 Mouse wheel, mouse movement, and an input that didn't land

`{"t", "wheel": n}` (notches, -20 to 20, not 0; positive scrolls up) and `{"t", "move": [dx, dy], "over": s}` (pixels
right and down, spread over `over` seconds) reach the game through Slate as a device's do (the engine's
`MouseWheelAxis`, `MouseX`/`MouseY` while the game holds the mouse). A click no UMG button takes finds a Slate button by
its text, tag or type. Every input that didn't land (a click no button took, a wheel or move no game viewport
received, a stage nothing took, a named shot whose file wasn't written) is listed in probe.json `inputs_missed`, and
`screenshots` lists only files written; two named shots asked in one frame are one capture, the second a copy.

## 2. Measures

### 2.1 Common fields

- `window`: `[t0, t1]` seconds of play time (ends inclusive), or `at`: `[t, ...]` (the sample nearest each time) or
  `"end"` (the last sample); not both. Default: the whole play.
- `agg`: how the samples reduce to one number: `min`, `max`, `mean`, `first`, `last`, `delta` (last minus first),
  `any` (1 if any sample is non-zero), `all` (1 if every sample is non-zero), `count` (number of non-zero samples),
  `sum`, `range` (max minus min), `std` (standard deviation), `changes` (how many times the value changes between
  consecutive samples), `rises` and `falls` (how many samples read more, or less, than the sample before: which way a
  value moved, a score that only rises reads `falls` 0, a reset reads as a fall), `step` (the largest change, up or
  down, between two samples next to each other: 0 for one sample). Default `last` (`sum` for `spawns`).
- How a thing moves, as a number ("eases instead of snapping", "gentle", "no sudden moves"): a task play with
  `"every": 0.1` and `"agg": "step"` over the window of the move. A door that snaps 90 degrees open reads a `step`
  of 90; one that turns open over a second reads 10 to 15, by its easing. `max` of a speed tells how fast, `step` how abruptly.
- `of` (`actors`, `components`, `widgets`, `ui`, and `asset` with a `select`): how the selected actors, components,
  widgets or UI elements combine within one sample: `count` (how many match and have a non-zero value), `any`, `all`, `min`, `max`,
  `mean`, `sum`, `first`. **Default `count`.** A measure that reads a value (a position, an extent, a `prop:`, a text
  match, a percent) needs `"of": "first"` or another value reducer, or it counts instead of reading. With `"field":
  "count"`, `of` is ignored.
- **Every match counts, past 200.** The plugin keeps at most 200 rows a sample in `probe.json` but reads every match:
  `"field": "count"` is the whole selection's size, and `of` (`count`, `any`, `all`, `min`, `max`, `mean`, `sum`) reads
  every match's value from the plugin's summary of them (the sample's `total` and `full`). Only `"of": "first"` and
  values read through `match`, `to_angle` or `to_axis` read the first 200 rows alone. Before 2026-11-06 counts stopped
  at 200 (a selection of 389 read 200): a threshold set on such a count then is set again.
- `to_angle` / `to_axis` (angle fields only: `yaw`, `pitch`, `roll`, `rel_yaw:<Component>`,
  `world_yaw:`/`world_pitch:`/`world_roll:<Component>`, `components`' `world_yaw` and `world_pitch`, and a `prop:` that
  holds an angle): angles are normalised to (-180, 180]. `"to_angle": -90` turns the field into its shortest absolute angular
  distance to that angle, 0-180 (so 270 and -90 are the same). `"to_axis": 90` turns it into the distance to that axis,
  0-90: a direction and its opposite are one axis (a straight road piece turned 90 or -90). One or the other, not both.
- `match` (string values: text, names, enum-like strings, brush paths): a regular expression; the value is 1 when it
  matches, 0 when not. A string without `match` has no value.

Rows and samples with no value are skipped by `of` and `agg` (`count`, `any`, `sum` of nothing are 0, `all` of nothing
is 0, the others have no value). A probe whose measure has no value fails, with the reason in its detail (section 3).

### 2.2 `pawn`: the player pawn

`{"probe": "pawn", "field": "x|y|z|speed|moved", ...}`, sampled through the play. `speed` in cm/s between samples;
`moved` = distance from the first sample. `"field": "dist", "to": <Point>`: distance to a point (section 2.13).

### 2.3 `camera`: the player's camera

`{"probe": "camera", "field": "distance|height|pitch|yaw|fov|occluded|pawn_on_screen", ...}`: `distance` and `height`
relative to the pawn (cm); `occluded` = 1 when a visibility trace from the camera to the pawn's centre hits something
else first; `pawn_on_screen` = 1 when the pawn's centre projects inside the viewport.

### 2.4 `actors`: actors in the world

```json
{"probe": "actors",
 "select": {"class": "SCCastlePiece", "tag": "Wall", "name": "Tower*", "near": {"point": {"xyz": [0, 0, 0]}, "radius": 5000}},
 "field": "z", "at": "end", "of": "first", "agg": "last"}
```

- `select`: every key given must match.
  - `class`: the actor's class or any parent class, by name without prefix letters (`SCCastlePiece` matches
    `ASCCastlePiece` and its Blueprint children); a Blueprint class by its asset name (`BP_Wall_C`).
  - `tag`: an actor tag. `name`: a wildcard on the actor's name or label.
  - `near`: within `radius` cm of a point. `{"player": true}`: the player pawn.
  - `has`: a component the actor carries, `{"has": {"class": ..., "lit": true, "visible": true, "near": {"point":
    <Point>, "radius": cm}}}`: the actor matches when at least one of its own components (registered, editor-only
    ones left out) matches every key given. `class` is the component's class or a parent, as a `components` select
    names it; `lit: true` reads it as the components `lit` field does (a light that lights the scene, or a drawn mesh
    whose material is emissive or unlit and bright, from its material graph or else as rendered); `visible: true` as
    the components `visible` field does; `near` measures from the component's own place, not the actor's. At least
    one key, and only `true` for `lit` and `visible`. The way to select by what an actor does ("an actor that gives
    light", "an actor with a drawn mesh near here") rather than by the class or name a build gave it. It works in
    every actor select: these, other measures' (`owner`, `ground`), points (section 2.13) and `teleport_to`
    (section 1.1). A map as saved (`asset`) takes no `has`. `"simulating": true` (a primitive simulating physics) and
    `"movable": true` (a scene component of Movable mobility) find an object by what it can do:
    `{"teleport_to": {"has": {"simulating": true, "near": ...}}}` reaches the nearest object a player can shove,
    whichever class a build used.
- `field`:
  - `count`: the selection's size (`of` ignored);
  - `x`, `y`, `z` (cm), `yaw`, `pitch`, `roll` (degrees), `scale`;
  - `extent_x`, `extent_y`, `extent_z`: **the actor's visible meshes' world-aligned half-size** (cm). The box is the
    union of the bounds of the actor's own registered mesh components (static, instanced, skeletal, spline,
    procedural and dynamic meshes, world-space widgets) that are drawn in game (visible, not hidden in game, not
    editor-only) and have a mesh. Collision shapes (box, sphere, capsule components), lights, audio, effects,
    editor-only and visualization components, empty meshes (no mesh asset, no instances) and child actors' components
    don't count; no value when the actor draws nothing. World-aligned, so a rotated actor's extent mixes its own axes
    (an actor turned 90 degrees reports its width as `extent_x`);
  - `hidden` (hidden in game), `collision` (any primitive component collides), `speed` (velocity length);
  - `spin` (deg/s): how fast the actor turns, the fastest of its mesh parts (as `extent_*` counts them; none: its
    root), each read as a component's `spin` (section 2.5). **Its threshold is calibrated or relative to the start,
    never a literal value**;
  - `simulating`: 1 when any of the actor's primitive components simulates physics (its own body, or any body of a
    skeletal mesh: pieces that broke loose, a ragdoll);
  - `spread` (cm): how far apart the actor's parts are, the diagonal of the world-aligned box around their centres:
    each mesh component `extent_*` counts by its bounds centre, a skeletal mesh with several physics bodies by each
    body's place; 0 with one part, no value when it draws nothing. A whole crate reads its pieces' own layout; one
    broken into pieces that fell apart reads more, though its pieces stay drawn and tagged. **Its threshold is
    calibrated or relative to the start, never a literal value**;
  - `changed`: 1 when the actor differs from the first sample it was seen in (the play's first sample, for an actor
    there from the start), else 0. Its parts are its own registered mesh components with a mesh, drawn or hidden (as
    `extent_*` counts them, hidden ones too). It reads 1 when a part was hidden or shown (visible, not hidden in game,
    the actor not hidden), a part drawn then is gone or a part drawn now was not there, a part's world bounds moved
    more than 1 cm (moved, turned, scaled), or a skinned mesh's pose moved: its bones more than 5 cm in all, in the
    mesh's own space, or its local bounds more than 1 cm. So an object that breaks by hiding a part, or by animating
    its pieces in place with no physics, reads 1, as one that moves does; one left alone reads 0. An object animated
    from the start (a looping idle) reads 1 too: read it after the start of the play that matters, or read
    `pose_change`;
  - `bounds_change` (cm): the furthest any face of a part's world bounds moved since that first sample, the largest
    over its parts; `pose_change` (cm): how far its skinned meshes' bones moved since then in their own space, summed
    over every bone (no value without a skinned mesh). **Their thresholds are calibrated or relative to the start,
    never a literal value**; `changed` takes a literal;
  - `lit`: 1 when the actor gives off light, whatever made it: any of its own light components lights the scene (as
    `on` reads it, section 2.5, and its light function, if any, isn't black), or any of its mesh components with a mesh
    is drawn (visible, not hidden in game, the actor not hidden) with a material whose emissive luminance is above
    0.01 (an emissive material, or an unlit one, whose colour is its emissive). **This is the way to check for light**:
    a lamp lit by a light component and a lamp drawn by a glowing material read the same. Takes a literal;
  - `glow`: how much light, one amount summed over its lit sources so either kind compares: a light's intensity in
    candelas (point, spot and rect lights; a directional light's lux and a sky light's scale as they are) times its
    colour's luminance and its light function's; a mesh's brightest material's emissive luminance (emissive 1 taken
    as 1 cd/m2) times a quarter of the surface of its local bounds in m2, scaled (the candelas a glowing surface that
    size gives every way). **Its threshold is calibrated or relative to the start, never a literal value**. A row
    with `lit` or `glow` also carries `glow_sources`, the kinds lit (`light`, `emissive`, `unlit`), and `glow_read`,
    how its meshes were read (`graph`, `render`, `bound`), for the logs; neither is a field to measure. How a mesh's
    emissive is read, and its limits: section 2.5;
  - `prop:<Component>.<Property>[.<Sub>]` or `prop:<Property>`: read by reflection. Numbers and booleans as numbers,
    enums as their index, object references as 1 when set, strings and names through `match`. A component by name or
    class (`SpringArm`, `CharacterMovement`, `StaticMeshComponent0`); an array element as `Materials[0]`;
  - `bone:<Component>.<BoneOrSocket>.x|y|z`: world location of a bone or socket of a skeletal or static mesh
    component;
  - `rel_yaw:<Component>`: the component's world yaw minus the actor's (turning the whole actor doesn't change it);
  - `world_yaw:<Component>`, `world_pitch:<Component>`, `world_roll:<Component>`: the component's own rotation in the
    world (degrees), whether its actor or the component itself turned; `forward:<Component>.x|y|z`: its forward unit
    vector in the world. For a light component this is the way its light travels: a directional light pointing down
    has a negative `world_pitch` and a negative `forward:<Component>.z`. A component by name or class, as for `prop:`
    (`world_pitch:DirectionalLightComponent`);
  - `facing_vs_velocity`: degrees between the actor's forward and its velocity (0 when it moves forward; no value when
    it stands still);
  - `bb:<Key>` on AI controllers: a blackboard value (numbers and booleans as numbers, enums as index, objects as 1
    when set, names and strings through `match`). AI controllers are actors: select them by class.

### 2.5 `components`: components in the world

`{"probe": "components", "select": {"class": "NiagaraComponent", "owner": <actor select>, "near": ...}, "field":
"count|active|visible|...", ...}`: registered components of a class (particle systems, decals, audio, lights, the
moving parts of an actor), optionally of an owner actor and near a point, so effects that are not actors count too.
`"mesh": "<wildcard>"` keeps mesh components whose mesh asset's name matches (as `pieces` has it), and
`"visible": true` only the components drawn (as the `visible` field reads them), so one part, a lamp's bulb, can be
picked out. `"effect": true` keeps only live effects, with or without `class`: a particle system (Niagara or Cascade)
that is active, a decal that is drawn; an effect actor (a Niagara actor, an emitter, a decal actor) counts by its
component, a pooled or finished system not at all. With `near` and `count`, how many effects play at a spot: read
before and after a restart (an input of a task play), it catches effects that pile up. A select names its `class`, or
`effect`, or both.
An instanced mesh component is one component however many instances it draws: count placed meshes with `pieces`
(section 2.14).

- `field`: `count`; `active`; `visible` (visible, not hidden in game, its actor not hidden);
- `x`, `y`, `z` (cm) and `speed` (cm/s) of a scene component, as actors have them: `speed` is its physics body's while
  it simulates, else its own velocity (as a movement component sets it), else how far it moved since the previous
  sample (no value the first time it is seen). Cars that are components of one road actor read here;
- `spin` (deg/s): how fast a scene component turns in the world, from its rotation read every frame and summed since
  the previous sample (so a part turning many times a second still reads), its physics body's angular velocity the
  first time it is seen while it simulates, else no value then. Any part near a point: select `PrimitiveComponent`
  with `near`; each part of one actor: select by `owner`. No component name is needed. A turn drawn by bones (a
  skinned rotor) or by a material reads 0 here: `drawn`'s `motion` (section 2.19) sees it;
- `world_yaw`, `world_pitch` (degrees, normalised to (-180, 180]): a scene component's own rotation in the world,
  whether its actor or the component itself turned, as an actor's `world_yaw:<Component>` reads it, but for a
  component picked by where or what it is rather than by its name. Angles: `to_angle` / `to_axis` turn each
  component's value into its distance to a bearing before `of` combines them, so `"of": "max"` is the one furthest off.
  A part near a point turned to face -90: `{"probe": "components", "select": {"class": "StaticMeshComponent", "near":
  {"point": {"xyz": [x, y, z]}, "radius": r}}, "field": "world_yaw", "to_angle": -90, "of": "max"}` with `<=` a
  tolerance. A turn drawn by bones reads the component, not the bone (`bone:` on actors);
- `extent_x`, `extent_y`, `extent_z` (a primitive's world bounds half-size, cm) and `simulating` (it simulates
  physics; a skeletal mesh when any of its bodies does);
- `changed`, `bounds_change`, `pose_change`: a primitive against the first sample it was seen in, as an actor's
  (section 2.4) for one part: hidden or shown, its world bounds moved, a skinned mesh's pose moved (`pose_change` has
  no value unless it is skinned);
- `lit` and `glow`: as an actor's (section 2.4), for one source: a light component, a mesh component with its
  materials, or a particle system (Niagara or Cascade: sprite, ribbon, beam and mesh emitters); no value for any other
  component. A particle system is read as rendered, as a mesh is below (its bounds for the box), lit when it is
  active and drawn and its brightest pixel is above 0.01; without a renderer, its materials' emissive bound while it is
  active. A row it lights names `effect` in `glow_sources`. **Check for light with these**, whatever the build made it with;
- `intensity` (a light's own intensity, in its units) and `on` (1 when the light lights the scene: registered,
  affecting the world, visible, not hidden in game, its actor not hidden, of an intensity above 0; the `light`
  probe counts the same lights). A lamp switched off by intensity 0, by hiding it or by hiding its actor reads 0.
  They see light components only: use them when a task really needs a light component, else `lit` and `glow`.
- **`intensity`, `extent_*`, `bounds_change`, `pose_change`, `glow` and `spin` thresholds are calibrated or relative
  to the start, never a literal value**; `on`, `lit`, `simulating`, `changed`, positions and speeds take a literal.

How `lit` and `glow` read a mesh, one of two ways; which one depends on its materials' graphs alone, never on
parameter values:
- **From its material graphs**, when every material the mesh draws with (its own, overrides, dynamic material
  instances, its overlay) evaluates whole with its parameter values at that sample: the base material's emissive input
  (or its material attributes, or its Substrate front material) over constants, scalar and vector parameters (an
  instance's override, a dynamic instance's current value, custom primitive data), parameter collections, static
  switches, material function calls, reroutes and the arithmetic nodes. The brightest material counts, over the
  mesh's whole bounds.
- **As rendered**, when any graph holds an input it can't evaluate (a texture, a custom HLSL node, vertex colour,
  time, a blend of attribute sets) or isn't there (a cooked build): the mesh is drawn alone, as the player's view would
  draw it at that sample, without any light (a scene capture that shows only it, orthographic, from four fixed views
  around it, HDR scene colour, every light, sky, global illumination, reflection, fog and atmosphere off), so what is
  left is what it gives off itself. `lit`: its brightest pixel's luminance above 0.01. `glow`: the views' luminance x
  pixel area summed, over the area of its bounds box they see, times a quarter of the box's surface: the same amount
  as from the graph for a mesh glowing all over, that part's share for a mesh glowing in part (a lamp that is one
  region of a larger mesh's material, say). A custom node, custom primitive data, a dynamic parameter, a texture or time reads as drawn.
  A mesh whose graph's upper bound is at or under 0.01 is dark whatever its inputs and isn't rendered.
- Without a renderer (`-nullrhi`), the graph's bound instead: an input it can't evaluate counts as at most 1 per
  channel (white); a cooked build's material reads 0 when its emissive is unconnected, else by the parameters named for
  it (Emissive, Emission, Emit, Glow), else no value. The checker's plays render offscreen (`-RenderOffscreen`), which
  renders the captures (tested on Windows; on Linux `-RenderOffscreen` renders with Vulkan without a display and
  should read alike).

Limits:
- a mesh read from its graphs counts its brightest material over its whole bounds, so a lamp post with a small glowing
  bulb reads the post's size: compare a `glow` with itself, calibrated or relative to the start, or select the bulb by
  `mesh`;
- a mesh drawn only on its inside (a sky dome, a room seen from within) is rendered from outside, usually as nothing,
  so it reads dark that way; a mesh hidden from scene captures, or drawn only for its owner, reads dark that way too;
- rendering is done on the game thread at the sample, each mesh once per sample, at most 64 meshes a sample (past
  that, the graph's bound);
- a light's light function is read from its graph; decals and text are not sources; select the lamp
  (by owner, tag, `mesh` or `near`), not every mesh in the level.

### 2.6 `widgets`: the UI on screen

`{"probe": "widgets", "select": {"class": "WBP_HUD_C", "name": "AmmoText"}, "field": "...", "match": "<regex>"}`.

- What is searched: the game's UMG trees in the viewport, whether added to the whole viewport or to one local
  player's screen, and every widget inside them, **including user widgets nested inside them** (each player's HUD
  inside a shared split-screen overlay, and the custom widgets inside that HUD).
- Slate HUDs: `{"slate": "STextBlock"}` selects Slate widgets under the game viewport by type (STextBlock, SImage,
  SProgressBar, or a game's own S... type), optionally with `"text": "<regex>"`. Widgets that paint everything in their
  own OnPaint, and AHUD canvas drawing, are not measurable here.
- **To check what a HUD shows, whatever draws it, use `ui` (section 2.18).** `widgets` reads a named widget's own
  state, so it sees a HUD only when a build made it with that widget; a HUD drawn on the canvas, or with other
  widgets, reads as absent.
- `"visible": true` in the select (UMG or Slate) keeps only the widgets the `visible` field reads 1 for: never a
  collapsed or hidden widget, nor one under a collapsed or hidden parent, so `count` counts what is on screen (a
  warning bar's shown messages, not the ones the game keeps collapsed).
- `field`: `count`; `visible` (visible, and its parents visible); `text` (a TextBlock's text, with `match`); `percent`
  (a ProgressBar); `has_brush` (an Image's brush resource is set); `brush` (the brush resource's path, with `match`);
  `x`, `y`, `w`, `h` (the widget's rectangle in viewport fractions 0-1, from its cached geometry, whatever anchor or
  offset placed it).

### 2.7 `light`: light reaching a point, as the engine computes it

`{"probe": "light", "point": <Point>, "field": "illuminance|exposure|brightness", ...}`:
- `illuminance` (lux): the sum over enabled lights of their contribution at the point (point, spot and rect lights by
  intensity, inverse-square falloff, attenuation radius and spot cone; directional lights by illuminance and a shadow
  trace toward the light; the sky light by its intensity), each with a visibility trace from the light;
- `exposure`: the auto-exposure the player's camera settled on (as a scale);
- `brightness`: `illuminance * exposure`, what the player sees at that point.

A light counts when the renderer draws it: registered, affecting the world, visible, not hidden in game, its actor not
hidden, of an intensity above 0 (`grading`'s sun and sky the same). Before 2026-11-07 a light hidden in game still
counted.

It sees no post-processing beyond auto-exposure (no exposure bias curve, colour grade, vignette, ambient occlusion,
bloom); for what reaches the screen, use `screen` (section 2.15). It sees light components only: whether a lamp is on,
whatever lit it (a light, or a mesh drawn by a glowing material), is `lit` of the lamp (section 2.4).

### 2.8 `grading`: the colour pipeline

`{"probe": "grading", "field": "cast|warmth|tint|saturation|contrast|grey|post:<Property>", ...}`: the post-process
settings in effect at the camera (unbound and enclosing post-process volumes by priority and blend weight, plus the
camera's own) and the key lights' colours (the strongest directional light, the sky light, the height fog). The checker
runs a neutral grey (0.18) through white balance, global saturation, contrast, gamma, gain and offset and the key
light's colour: `grey` = the resulting luminance; `cast` = its chroma (0 = neutral); `warmth` = (R - B) / luminance;
`tint` = (G - (R + B) / 2) / luminance; `saturation`, `contrast` = the effective global values.
`post:<FPostProcessSettings property>` (`post:MotionBlurAmount`, `post:VignetteIntensity`, `post:BloomIntensity`,
`post:AutoExposureBias`, ...): the effective value at the camera after blending.

### 2.9 `spawns`: actors appearing and disappearing

`{"probe": "spawns", "class": "SCProjectile", "field": "spawned|destroyed", "window": [0, 22]}`: how many appeared or
disappeared in each sample's interval; the default `agg` is `sum` (the count in the window).

### 2.10 `log`: the play's game log

`{"probe": "log", "pattern": "<regex>", "field": "count"}`: lines of the play's log that match, during the play.

### 2.11 `asset`: the project as saved (`play: "editor"`)

```json
{"probe": "asset", "asset": "/Game/Materials/M_Road", "field": "prop:two_sided"}
{"probe": "asset", "map": "/Game/Maps/L_Level6", "select": {"class": "StaticMeshActor", "tag": "Terrace"},
 "field": "material_default", "of": "all"}
```

- `asset` + `prop:<editor property>[.<sub>]`: an asset's property.
- `map` + `select` (as for `actors`): actors in that map as saved. `material_default` = 1 when any mesh component's
  material slot is empty or the engine's default material; `material:<property>` on each component's materials (the
  material's property, else its parent material's); `mesh_collision` = 1 when the static mesh has simple collision or
  uses complex as simple; `prop:<path>`; `count`.
- A project that doesn't build fails its editor probes.

### 2.12 `trace`: retired

Retired (the owner, 2026-11-13): never add a `trace` probe, and take it out of a task you edit. A task that still
carries one stays valid (`"required": false`, play `"trace"`, a literal threshold) and `validate-game.py` warns
"retired: remove it".

### 2.13 Points

`{"xyz": [x, y, z]}`, `{"pawn": true, "offset": [x, y, z]}`, `{"camera": true, "forward": cm}`, or
`{"actor": <select>, "offset": [x, y, z]}` (the first match).

A `near` is `{"point": <Point>, "radius": cm}`, and may also hold a height band: `"z_min"` and/or `"z_max"` (cm,
world z; with `"z_relative": true`, offsets from the point's z). Wherever `near` works (actor selects, `has`,
`components`, `pieces`, `drawn`), a thing then matches only when its place's z is within the band too: the lamp on
the ceiling, not the one on the floor below it. `z_min < z_max`; `z_relative` goes with one of them.

### 2.14 `pieces`: placed mesh pieces, whatever their form

```json
{"probe": "pieces", "select": {"class": "StaticMeshComponent", "mesh": "SM_Rock*",
                               "near": {"point": {"pawn": true}, "radius": 3000}},
 "field": "count", "at": "end"}
```

How many mesh pieces are placed, however the level holds them: a level dressed with instanced static meshes (ISM,
HISM, foliage, PCG output) or with one procedural mesh of many sections reads as one actor and one component to
`actors` and `components`, but as its real number of pieces here.

- A piece: a static or skeletal mesh component with a mesh is 1; an instanced static mesh component is 1 per
  instance; a procedural mesh component is 1 per section with triangles; any other mesh component (a dynamic mesh) is
  1. Empty meshes (no mesh asset, no instances, no triangles), widget components and editor-only components count 0.
- `select` (optional; every key given must match, none means every mesh piece in the world):
  - `class`: the mesh component's class or a parent (`StaticMeshComponent` takes in the instanced ones;
    `InstancedStaticMeshComponent`, `HierarchicalInstancedStaticMeshComponent`, `ProceduralMeshComponent`,
    `SkeletalMeshComponent`); default every mesh component;
  - `name`: a wildcard on the component's name; `mesh`: a wildcard on its mesh asset's name (`SM_Rock*`; a procedural
    mesh has none, so `mesh` leaves it out);
  - `owner`: an actor select the component's actor must match (as in `actors`);
  - `near`: within `radius` cm of a point, **each piece by its own place** (an instance's location, a section's bounds
    centre, else the component's location).
- `field`: `count` (pieces), `visible` (pieces drawn in game: component visible, not hidden in game, its actor not
  hidden, the section visible), `components` (how many mesh components hold them), `actors` (how many actors),
  `triangles` (the triangles the pieces hold), `visible_triangles` (the triangles of the pieces drawn, as `visible`).
- A piece's triangles: a static mesh's LOD0 (a Nanite mesh's own triangles, since its LOD0 is a reduced fallback); an
  instanced static mesh component's mesh times its instances (each instance by its own place under `near`); a skeletal
  mesh's LOD0; a procedural mesh section's index count / 3 (read from the component, so the game needn't enable the
  ProceduralMeshComponent plugin); any other mesh component (a dynamic mesh) 0.
- Counted over every piece in the plugin, never cut at the rows cap. A literal threshold is fine on `count`,
  `visible`, `components` and `actors` (a count doesn't depend on the machine).
- **A `triangles` or `visible_triangles` threshold is calibrated or relative to the start, never a literal value**
  (`tools/validate-game.py` refuses one): how many triangles a fair build draws depends on the meshes it chose (1500
  low-poly trees merged into three procedural sections, or 300 detailed ones), so the number only means something
  against the same game's start or reference. Read it where a count of pieces can't tell a fair build: "the forest is
  dense" built either way reads as many drawn triangles, but as 3 pieces when merged.

### 2.15 `screen`: what the player sees, after post-processing

```json
{"probe": "screen", "rect": [0.25, 0.25, 0.75, 0.75], "field": "luminance", "window": [10, 20], "agg": "mean"}
```

The mean brightness of the frame the player's viewport drew, sampled with the play like every other probe: after
post-processing and tone mapping (exposure and its bias, colour grading, vignette, ambient occlusion, bloom, fog), so
"the cave is too dark to see" or "the night is too bright" is measured on what reaches the screen. The `light` probe
measures light arriving at a point and sees none of that.

- `rect`: `[x0, y0, x1, y1]` in viewport fractions 0-1, x0 < x1 and y0 < y1 (default `[0, 0, 1, 1]`, the whole frame).
  Keep it on the scene the task is about and off HUD drawn with the AHUD canvas. What the HUD shows is `ui`
  (section 2.18), not luminance.
- `field`: `luminance`, the mean linear Rec. 709 luminance of the displayed pixels (sRGB decoded, 0-1); `luma`, the
  mean Rec. 709 luma of the encoded values (0-1, closer to perceived brightness).
- What is read: the frame drawn right after each sample (one frame later at the checker's 30 fps), as the engine's own
  screenshots read it: the scene and AHUD canvas drawing, without the UMG and Slate UI drawn over it. No value when no
  frame is drawn.
- **The threshold is calibrated or relative to the start, never a literal value** (`tools/validate-game.py` refuses
  one): the numbers depend on the GPU, the driver and the resolution, so they compare only within one machine's plays.
  Two plays of one build on one machine read the same to about 1e-5. Auto-exposure takes a few seconds to settle after
  the start and after a teleport: put the window after it.

### 2.16 `audio`: what the player hears

```json
{"probe": "audio", "select": {"sound": "Amb_Jungle*", "sound_class": "Ambience", "owner": {"tag": "Zone2"}},
 "field": "volume", "window": [4, 8], "agg": "mean"}
```

The sounds playing, from the audio device itself: a sound a component plays, one played at a location or in 2D,
music; so ambience a game drives from code reads as well as an `AmbientSound` actor's.

- `select` (optional; none: every sound): `sound` a wildcard on the sound asset's name, `sound_class` a wildcard on
  its sound class's name or a parent class's, `owner` an actor select its owner (the actor of the component that
  plays it) is in.
- Each sound reads its **volume at the listener** (the player's camera, or what the game listens from): its wave
  instances' volume (its own, its class's and mixes', the game's multipliers) times their distance and occlusion
  attenuation, summed; the output's master volume is left out.
- `field`: `count` (how many sounds), `audible` (how many at 0.001, -60 dB, or louder), `volume` (their volumes'
  sum), `max_volume` (the loudest); and the sounds that **start**, every one however short, seen once a frame:
  `started` and `started_audible` (how many started, and how many became audible, in each sample's interval; summed by
  default), `sounds` (how many differently named sounds started) and `repeats` (how often a sound started right after
  itself; "never the same take twice"). `sounds` and `repeats` read sound asset names: a sound made at run time has
  none, and the read is missing.
- `select.near` (a point and radius): only sounds played at a place within it (where it plays, or for the started
  fields where it started); a 2D sound is near nothing. A sound ask reads "a sound starts when the event happens":
  `started_audible` near the source, in a window right after the event; what the sound is, how it sounds, is never
  checked.
- **A `volume` or `max_volume` threshold is calibrated or relative to the start, never a literal value**: how loud
  depends on the sounds a build chose. `count` and `audible` take a literal. Compare places by their own plays or
  windows: teleport into each zone (section 1.1) and read the zone's sound there.
- A play with an audio measure runs with sound, muted (`-muteaudio`: every sound is mixed, nothing is heard), with what
  `-benchmark` gave it otherwise (a fixed time step and seed, no ini writes; the plugin keeps the application
  focused, as `-benchmark` does). Every other play runs with `-nosound -benchmark` as before, so no audio device
  exists in it and an audio component reads inactive. A machine with no audio output mixes into the engine's null
  device. With no audio device at all the value is missing, never 0.

### 2.17 `ground`: the lie of the land

```json
{"probe": "ground", "xy": [1200, -300], "field": "height"}
{"probe": "ground", "box": [0, 0, 8000, 8000], "grid": 12, "select": {"class": "LandscapeProxy"}, "field": "range"}
```

- At a point `xy`: `height` (cm), the z where a trace straight down from 2 km up first meets something (the
  visibility channel, complex collision, every pawn ignored); `hit` (1 when it met anything).
- Over a `box` `[x0, y0, x1, y1]`, the same on a `grid` x `grid` lattice (2-32, default 8; corners and edges
  included): `min`, `max`, `mean` of the heights, `range` (max - min, the relief: rolling hills against a flat
  plain), `hits` (how many points met ground).
- `select` (an actor select, optional): only those actors are ground; anything else (trees, rocks, roofs) is traced
  through.
- **A `range` threshold is calibrated or relative to the start, never a literal value**; heights take a literal, as
  an actor's `z` does.

### 2.18 `ui`: what the UI shows on screen, whatever draws it

```json
{"probe": "ui", "select": {"kind": "text"}, "field": "text", "match": "AMMO\\s*\\d+", "of": "any", "at": "end"}
{"probe": "ui", "select": {"kind": "box", "rect": [0, 0.8, 1, 1]}, "field": "count", "window": [5, 10], "agg": "min"}
{"probe": "ui", "select": {"rect": [0.02, 0.02, 0.3, 0.12]}, "field": "signature", "window": [5, 15], "agg": "changes"}
```

One reading for the UI on screen, however a build drew it: UMG widgets, Slate widgets and the HUD canvas
(`AHUD::DrawHUD` with `DrawText`, `DrawRect`, `DrawTexture`, `DrawLine`, `UCanvas` `K2_DrawText`, `K2_DrawBox` and
the canvas's other text, tile, texture and line draws) read the same. A HUD a build drew on the canvas, and one another build made of widgets, both
pass a check written with `ui`. **This is the way to check what a HUD or menu shows**; `widgets` (section 2.6) stays for
a widget's own state (a progress bar's percent, a brush).

- What is read: the elements on screen in the frame drawn right after each sample (one frame later at the checker's
  30 fps). Only what is on screen: a collapsed or hidden widget, one at render opacity 0, and everything under it are
  not read, nor is a canvas draw that is fully transparent or off the frame. No value when no frame is drawn.
- Each element is one row: a widget that draws (a text block, rich text, an editable text with text or a hint; an
  image; a border, a button, a progress bar, a colour block), or one canvas draw (a string, a rect, a texture or
  tile, a line).
- `select` (optional; default every element): `kind` (`text`, `box`: a rect, border, button, bar or untextured brush,
  `image`: a brush or canvas draw with a texture or material, `line`: a canvas line, `DrawLine` or `K2_DrawLine`, its
  rectangle as drawn; an outline, `K2_DrawBox` or four lines one after another closing a rectangle, once, as its
  rectangle); `text` (a regular expression the element's text must
  match; text elements only); `rect` `[x0, y0, x1, y1]` in viewport fractions, x0 < x1 and y0 < y1 (the element's centre
  inside).
- `field`: `count` (one per element); `text` (the string shown, with `match`); `x`, `y`, `w`, `h` (the element's
  rectangle in viewport fractions 0-1); `signature` (whether what the select shows updates, below); `number` and
  `clock` (the number or time it shows, below). `of` combines the elements, as for widgets: `"field": "text", "match": ...,
  "of": "any"` is 1 when some element shows matching text, `"of": "count"` how many do.
- Whether a readout updates, however it is drawn: `"field": "signature"` is one value a sample for everything the
  `select` picks: each element's `kind`, `text` and rectangle (`x`, `y`, `w`, `h` rounded to 0.002 of the viewport),
  taken as a set, and how many matched. It is 0 when the select picks nothing, otherwise a number that means nothing
  but itself; `source`, names and the order of the rows are left out. Read it with `"agg": "changes"`: how many
  samples (every 0.5 s) show something other than the sample before. A text readout whose string changes counts, and
  so does a readout drawn with lines whose strokes change, whatever reads or doesn't read its text; a readout that
  stays the same reads 0. Appearing or going (to or from 0) is a change; a sample with no frame drawn has no value.
  - A signature takes `agg` `changes`, `any`, `all` or `count` (`all`: something shown in every sample; `count`:
    samples showing something), nothing else. `of` is ignored.
  - A literal threshold on a count of changes is valid, but a calibrated or start-relative threshold is the safer
    choice: a readout that also moves, blinks or animates changes for reasons of its own, and one that updates more
    slowly than the samples changes less often. Keep the `rect` on the readout alone, with a margin, and the
    `window` where its value is known to change.
  - Limits: geometry right at a 0.002 step can flip between samples on sub-pixel motion; a change that changes back
    before the next sample is not seen; a readout no `ui` element reads (below) has no signature but 0, unless its
    text reads from the frame.
- Which way a number on screen moved, however it is drawn: `"field": "number"` is the first number the select's text
  elements show in one sample, in reading order (top to bottom, a line within 0.01 of the viewport's height; left to
  right): digits with a decimal point and comma thousands (`3,450` is 3450), negative when a minus stands before it
  after no letter or digit (`LAP 2-3` reads 2). Its text comes from every text element the select picks (UMG, Slate,
  canvas, painted, stroke digits, and the frame when the select is of text in a rect), so the select is best
  `{"kind": "text", "rect": [...]}` around the readout alone. No number shown: no value. Read it with `rises`,
  `falls` (section 2.1), `changes`, `range` or `max`: a score that only rises reads `falls` 0 over its window; a
  reset reads as a fall.
- A clock on screen as a clock: `"field": "clock"` is the first time shown, in seconds: `h:mm:ss` or `m:ss` (a
  fraction after `.` or `,` added), else the first number, as seconds. A timer that holds through a pause reads
  `range` 0 over the pause's window; one that resets on a retry reads a fall there (a count-down: a rise).
- `number` and `clock` share the signature's query (one select, one reading), take any `agg` and a literal (what is
  shown is a fact), ignore `of` and take no `match`.
- Each row also carries `source` (`umg`, `slate`, `canvas`, `paint` or `ocr`) and `kind`, for the logs; they are not fields a check
  reads, so a threshold never depends on how a build drew its HUD.
- Canvas text is read back from the glyphs the canvas drew (the font cache's characters), so it is the string as
  drawn. Spaces are read from the gaps between glyphs: write `\s*` (or `\s+`) where a string has a space.
  A shadow or outline is the same text drawn twice and reads once.
- Digits drawn with lines read as text too, when they are drawn seven-segment style (horizontal strokes at a digit's
  top, middle and bottom, upright strokes at its left and right; 0-9 with the usual 6, 7 and 9 variants): one `text`
  element per number, digits of one height side by side on one line. The strokes stay `line` elements. It reads
  nothing rather than guess: a number boxed in tightly or crossed by another stroke, segments far apart (more than
  about a sixth of a digit's width), digits closer than about a third of a width, a lone 1 or a run of 1s alone,
  letters, slanted strokes. When a readout drawn with lines doesn't read as text, grade it by its strokes: `count`
  (or `x`, `y`) of `line` elements in its `rect`, calibrated or relative to the start, changes as the number changes.
- Text however it is drawn, read from the frame. A `select` of text in a `rect` (`"kind": "text"`, or a `text`
  regex, with a `rect`) also reads the frame as drawn, after the UI, inside that rect: text drawn with slanted lines,
  stroked letters, a texture or a material reads there too. Each line it can read for sure joins the text elements as
  one `text` element (`source` `ocr`), so `match` and `of` read it like any other; a line another element already
  reads as text is left to that element, so nothing reads twice. It reads digits 0-9, capital letters A-Z and `%`, `/`,
  `.`, `-`, `:`, in the shapes line-drawn and segment fonts give them (plain strokes, cut or rounded corners, segments,
  a slashed 0, diagonals in 1, 4 and 7). Only such a select takes the capture; every other measure reads as before.
  - It reads nothing rather than guess: text that doesn't stand out in one colour from an even background behind it;
    a line that runs out of the rect or that another mark crosses; a glyph two characters fit (an unslashed 0 and O,
    a 5 and S or an 8 and B drawn as segments, a plain bar for 1 and I); a lone character; lower case; slanted
    (italic) text; glyphs too small or too bold for their strokes to be told apart. A line with any glyph it can't
    read reads as nothing, not in part.
  - Give the rect a margin around the text so its edge is background, and write `\s*` where the text has a space.
    Where the text still doesn't read, grade the readout by its `line` elements in the rect, as above.
  - It needs a renderer: a play without one reads no text from the frame.
- What a widget paints itself: a widget that draws its own text or shapes (a custom `OnPaint`, a UMG `NativePaint`)
  is read from the game window's draw elements: each element painted under the game viewport while a widget the
  above doesn't read is the one painting is a row, `source` `paint`: `text` (a text draw, its rectangle the text as
  measured in its font), `box` (a box, rounded box, border or gradient without a texture), `image` (with one), `line`
  (lines and splines). Elements a text block, image, border or the like painted are left to it, so nothing reads
  twice. Engine widgets with no element of their own above (a slider, a spin box) read this way too.
- Limits: text a custom widget lays out and shapes itself (not a plain text draw), and widgets under an invalidation
  panel or retainer that weren't repainted that frame, are not read as painted elements (their text can still read
  from the frame); material tiles (`DrawMaterial`), the debug canvas (on-screen debug messages, stats)
  and anything a build draws in the 3D scene (a widget component, a text render component) are not UI elements here
  (their text can still read from the frame, above);
  a canvas glyph whose font isn't in memory reads as `?`. The UMG/Slate geometry is the layout's, so a widget scaled
  or moved by a render transform reads at its laid-out place.

### 2.19 `drawn`: what is drawn in a place, whatever draws it

```json
{"probe": "drawn", "near": {"point": {"xyz": [1200, -300, 150]}, "radius": 250}, "field": "motion", "window": [4, 12], "agg": "mean"}
{"probe": "drawn", "near": {"point": {"actor": {"tag": "Wall"}}, "radius": 200}, "field": "base_r", "at": "end"}
{"probe": "drawn", "line": {"from": {"pawn": true, "offset": [0, 0, 60]}, "to": {"camera": true, "forward": 3000}, "radius": 40}, "field": "reach", "window": [6, 8], "agg": "max"}
```

One reading for what is drawn at a spot, whatever draws it: a mesh, a particle system, a surface whose material pans
or animates, no name needed. Every primitive drawn in game (visible, not hidden in game, its actor not hidden) whose
world bounds come within the place is rendered alone, by a scene capture that shows only those primitives:
orthographic, from fixed views (four around a point, two across a line), lit by the scene's direct lights and sky
light with no shadows, global illumination, reflections, fog, atmosphere, anti-aliasing or exposure change, so a
still scene renders the same every sample. A primitive whose bounds enclose the whole place (a sky dome, a room seen
from inside) is left out. A pixel is in the place when its depth puts it there, or when it shows colour with nothing
opaque behind it (translucent particles).

- The place: `near` (section 2.13: a point, a radius and, optionally, a height band), or `line`: `{"from": <Point>,
  "to": <Point>, "radius": cm}` (0 < radius <= 10000), the segment and how far from it counts as on it. One of them.
- Near a point, `field`:
  - `drawn`: 1 when anything is drawn there, else 0;
  - `motion`: the share of the place's pixels (in either sample) that changed since the previous sample, covered or
    not, or a colour channel by more than one 8-bit step: 0 for a still scene, more when a mesh moves or turns,
    particles play, or a material pans or animates. No value the first sample;
  - `base_r`, `base_g`, `base_b`: the mean rendered base colour (linear 0-1) of the place's opaque pixels, the
    surface's colour or tint with no light in it, from a texture, a parameter or a dynamic instance alike;
    `base_change`: that colour's distance (RGB) from the play's first sample's.
- Along a line, `field`: `drawn`; `reach` (cm): from `from` along the line to the furthest point drawn within
  `radius` of it; `length` (cm): how much of the line is drawn. A beam drawn as a mesh, a particle beam, a ribbon or a
  trail read alike.
- **Every field but `drawn` depends on what a build drew: its threshold is calibrated or relative to the start, never
  a literal value**; `drawn` takes a literal. No renderer, or a point that doesn't resolve: no value.
- Limits: the player's own pawn counts like anything else in the place (keep it out, or teleport away); a lit
  translucent particle shows as lit by direct and sky light only; a surface that writes no base colour (unlit,
  translucent) has none; a primitive hidden from scene captures reads nothing. Keep the place tight around what the
  task is about: a floor or a wall inside it counts too.

### 2.20 `world`: the game world as a whole

`{"probe": "world", "field": "time_dilation" | "paused"}`: `time_dilation` the lowest global time dilation over the
frames since the previous sample (a hit stop that slows the world shows even between samples); `paused` 1 when the game
was paused in any of them ("Escape pauses the game").

## 3. What gates, and how a probe fails

- **At least one required probe.** Every task has at least one `probe` check with `"required": true` (the default);
  the validator refuses a task without one. Every bug fix and correction has at least one required probe that the start
  fails for the reported reason and the fix passes.
- **`still_works` probes already pass at the start.** A required probe in the `still_works` milestone (the player
  still moves, the HUD still shows, the level still loads its scenario) must pass on the start: what still works must
  already work there, or the probe itself is broken and would fail every correct solution. (A still-works probe the
  start measured nothing for, because its play crashed on the very bug the task fixes, doesn't count against it.)
- **No samples, no pass.** When a play ends early or a measure has no samples in its window (the game quit, crashed or
  never reached that time), the probe fails with "no samples in the window (the play ended at X s)"; when samples exist
  but nothing selected has a value, it fails with "no value in the window".
- **`needs`** names only earlier checks; check names are unique in the task.

### 3.1 A start that doesn't compile: `fails_at_start`

When making the start build is the task (a compile error the engine rejects), mark its build check:

```json
{"name": "editor_builds", "kind": "build", "fails_at_start": true}
```

The start is then never played, so nothing in the task may need it played: **no start-relative thresholds**
(`calibrate`, `start_times`, `start_plus`; use literal values) and **no judges comparing with the start**
(`"before": true`). The task check requires the start not to build; a start that builds makes the task invalid.

### 3.2 A judge check's own plays: `plays`

A `judge` check asks a question, rubric item by rubric item, over screenshots the checker takes itself. Left alone it
is shown the two plays every task shares, the idle `look` and the `drive` of `play_map`: they never press a task's own
keys, open another level or leave a title screen. When what the rubric asks about shows only after one of those, the
check names up to 4 task plays (section 1.1) in `plays`, and its screenshots are taken in those plays instead:

```json
{"name": "upgrade_menu_reads", "kind": "judge", "required": false, "needs": ["boots_clean"], "before": true,
 "question": "With the upgrade menu open, does it read the way the request asks?",
 "rubric": [{"key": "costs_legible", "criterion": "Each upgrade's cost is legible against the panel behind it."}],
 "plays": [{"name": "open_upgrades", "seconds": 10,
            "inputs": [{"t": 0.5, "key": "U", "press": true}, {"t": 0.7, "key": "U", "press": false}]}]}
```

- Each is a task play under the rules of section 1.1. Its name appears once in the check; a play with the name of
  another check's play (a probe's or another judge's) must be identical to it, and is then played once and serves both.
- The judge is shown 5 screenshots of each play, taken at 10, 30, 50, 70 and 90% of its `seconds` (a 10 s play: 1, 3,
  5, 7 and 9 s). Time the inputs so that what is judged is on screen at those moments.
- Each play is played on every side the check shows: the agent's game, the start with `"before": true`, the fix with
  `"reference": true`. So it must run on the start as well; an input that does nothing there is fine.
- `shots` (2-20, default 5; only on a check with `plays`): how many screenshots of each play the judge is shown,
  evenly over it: screenshot i of N at `seconds` x (i + 0.5) / N. The check's plays times its `shots` are 20 at most
  (one play of 20, two of 10, four of 5). A short play with many is a run of frames in which motion shows: a 5 s play
  with `"shots": 20` is a frame every 0.25 s. A play two checks name is played once, with the most either asks.
- Motion that is a number (how fast, how abruptly, how far) is a probe's to measure, not a judge's: a field over a
  window, `step` on a play sampled every 0.1 s (section 2.1), `drawn` `motion`, `spin`. Motion that can only be seen
  (feet that slide over the ground, a trail behind a blade) is a judge's, with a short play and many `shots`.
- A play's named shots (`shot` inputs, section 1.1) are shown too, every one, in the order taken, beside its `shots`
  evenly spaced ones; the check's plays times its `shots`, plus their named shots, are 20 at most.
- A check without `plays` is shown `look` and `drive`, as before.

The task check asks no model. It plays each `judge` check's plays on the start and on the reference and saves the
screenshots the judge would be shown: its `shots` evenly spaced ones of each play and every named one, 20 at most, or
the 6 of `look` and the 8 of `drive` for a check without `plays` (the developer's `route` isn't played locally). They go
under `<task>\judge-shots\<check>\start\` and `reference\`, named `<play>_<nn>.png` in the order taken, with
`ask.md` (the brief, the question, the rubric, what each picture is) and a blind copy: `blind\A\` and `blind\B\` hold
the same pictures, and `blind\key.json` says which side each is. A play a probe names is the same play and is played
once.

Look at them yourself before calling a task with a required judge VALID, blind: score every rubric item for A and for
B first, then open the key. The start must fail every required rubric item and the reference must pass every one.
Write both sides' answers in the task's notes (its `tasks-workflow.jsonl` row). A task try saves the same for the
agent's game (`agent\`) under `<task>\run<N>\judge-shots\`: answer its judges the same way before calling the task
too easy or held. `tools/validate-game.py` checks the rules of a judge's plays.

## 4. The task check

Before any agent is given a task, the checker grades the start and the fix with every probe. A task is valid when:

- the start builds (unless the task says it doesn't, section 3.1: then it must not);
- the fix builds, boots and passes every required check;
- the start fails every required probe outside `still_works` (or the `fails_at_start` build check);
- a no-op scores zero: no check the start passes carries weight, so build, boot and `still_works` checks take
  `"weight": 0` (the score is the weighted share of checks passed);
- every required `still_works` probe passes at the start;
- every calibrated probe measures differently on the start and the fix;
- every required `judge` check, answered by the task's writer from the screenshots the check saves (section 3.2),
  fails on the start and passes on the fix, item by item.

A task with no fix (a feature or a change) is checked on its start alone: the start builds and fails at least one
required probe, whose thresholds are literal or relative to the start. A task that fails the task check is not run;
a run on an invalid task is void.

## 5. Lessons

- **Mouse axes go through the game's input scale and the engine's mouse sensitivity.** An axis event's value is not
  degrees: the game's input mapping scales it, and so does the engine's mouse sensitivity. A play that assumes
  `"axis": 90` turns the camera 90 degrees barely moves it. Read the game's look scale at the seed and size the axis
  values (or send several events) so the camera really turns, then measure the turn.
- **Check that a play really reaches the situation.** A probe of a moment the play never reaches measures nothing
  useful. Teleport to the spot (`teleport` input), use a scenario `map`/`args` that starts there, and check on the fix
  that the play gets there before trusting its threshold.
- **A measure that reads the same on the start and the fix can't gate.** If both sides give the same value, the probe
  doesn't see the bug (calibrated ones make the task invalid outright). Pick a measure the fix actually changes.
- **Calibrate thresholds between the start and the fix.** Use `calibrate` (or literal values that sit clearly between
  what the start and the fix measure), never a threshold guessed from the fix alone: another valid fix must pass and
  the start must fail.
- **Angles compare as angles.** Yaw, pitch and roll wrap at 180; comparing raw values fails across the wrap (179 and
  -179 are 2 degrees apart). Use `to_angle` (a direction) or `to_axis` (an axis, either way along it).
- **Value-reading measures need a reducer.** `of` defaults to `count`; to read an actor's or a widget's value write
  `"of": "first"` (or `min`, `max`, `mean`, ...).
- **Test the outcome a player sees, never the implementation.** "The hero stands on ground", not "SpawnZ is 92";
  another valid fix must pass.
- **Read names from the game.** Classes, tags, widget names, components and map paths come from the code and assets at
  `seed.commit` and `seed.reference`, never guessed.
- **Count what the player sees placed.** A fix that moves props into instanced meshes, or a level built from one
  procedural mesh, has fewer actors and components but as many pieces: count with `pieces`, so a fair build that
  dressed the level another way still passes. When a fair build may also merge them (many props in a few procedural
  sections or one mesh), count the geometry drawn: `visible_triangles`, calibrated or relative to the start.
- **Off is not hidden from the counts.** A lamp switched off by hiding it or by intensity 0 is still a registered
  component: read `lit` of the lamp, not `count` or `visible` of the actor.
- **A lamp need not be a light.** A build may light a lamp with a light component, or draw it with an emissive
  material switched by a parameter, with no light component at all: read `lit` (and `glow`, calibrated or relative to
  the start), which see both. `on`, `intensity` and the `light` probe see light components only.
- **A broken object still draws.** A crate broken into pieces may keep every piece drawn and tagged, so `count` and
  `visible` can't see it go: read `simulating` or `spread` of the crate, calibrated or relative to the start.
- **An object can break without physics.** A build may break it by hiding a part, or by playing an animation on its
  skinned pieces, so nothing simulates and no part moves apart: read `changed` of the object (1 when anything about it
  changed since the start), so either way of breaking it reads the same.
- **A light's direction is a world direction.** `rel_yaw:` reads a component against its own actor, so a fix that turns
  the actor instead of the component reads unchanged. "The moon points the same way" is `world_yaw:`, `world_pitch:` or
  `forward:` of the light component.
- **A HUD need not be widgets.** A build may draw its HUD with widgets or on the canvas (`AHUD::DrawHUD`): check
  what it shows with `ui` (text with `match`, counts by `kind` and `rect`), which reads both the same; `widgets` sees
  only the widget it names.
- **Brightness on screen goes through calibration.** A `screen` threshold is always calibrated between the start and
  the fix (or relative to the start), and its window starts after auto-exposure settles.

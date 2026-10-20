# Task probes: the contract for `probe` checks

How a task author writes the checks that decide whether a game task passes. It goes with the task format
([schemas/game-task.schema.json](schemas/game-task.schema.json), `GameTask`, game-task/1) and the `write-tasks` skill
([skills/write-tasks/SKILL.md](../skills/write-tasks/SKILL.md)), and `tools/validate-game.py` checks every rule below
that can be checked without running the game.

**Pass/fail is deterministic (owner's decision, 2026-10-19).** A task passes or fails only on checks the checker computes
from the running game or from the project: `build`, `boot`, `log_absent` and `probe`. A model judge never decides
pass/fail, and nothing is graded from pixel statistics of the game's frames. Judges (`judge`, `code_judge`,
`actions_judge`) stay as **non-gating** quality checks (`"required": false`).

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
    value: `[A-Za-z0-9_.-]{1,40}`). Never the engine flags the checker sets itself: ExecCmds, Run, NullRHI, Log,
    Unattended, RenderOffscreen, ResX, ResY, Benchmark, FPS, Game, Windowed, nor the checker's own measurement flags
    (`tools/validate-game.py` lists what it refuses).
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
      to reach a test spot.
- `"editor"`: a headless editor pass over the project as saved; takes only `asset` measures, and `asset` measures
  are taken only there.
- `"trace"`: the agent's own trace; takes only `trace` measures, and `trace` measures are read only there. Trace
  probes never gate (section 3).

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

## 2. Measures

### 2.1 Common fields

- `window`: `[t0, t1]` seconds of play time (ends inclusive), or `at`: `[t, ...]` (the sample nearest each time) or
  `"end"` (the last sample); not both. Default: the whole play.
- `agg`: how the samples reduce to one number: `min`, `max`, `mean`, `first`, `last`, `delta` (last minus first),
  `any` (1 if any sample is non-zero), `all` (1 if every sample is non-zero), `count` (number of non-zero samples),
  `sum`, `range` (max minus min), `std` (standard deviation), `changes` (how many times the value changes between
  consecutive samples). Default `last` (`sum` for `spawns`).
- `of` (`actors`, `components`, `widgets`, and `asset` with a `select`): how the selected actors, components or
  widgets combine within one sample: `count` (how many match and have a non-zero value), `any`, `all`, `min`, `max`,
  `mean`, `sum`, `first`. **Default `count`.** A measure that reads a value (a position, an extent, a `prop:`, a text
  match, a percent) needs `"of": "first"` or another value reducer, or it counts instead of reading. With `"field":
  "count"`, `of` is ignored.
- `to_angle` / `to_axis` (angle fields only: `yaw`, `pitch`, `roll`, `rel_yaw:<Component>`, and a `prop:` that holds an
  angle): angles are normalised to (-180, 180]. `"to_angle": -90` turns the field into its shortest absolute angular
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
  - `prop:<Component>.<Property>[.<Sub>]` or `prop:<Property>`: read by reflection. Numbers and booleans as numbers,
    enums as their index, object references as 1 when set, strings and names through `match`. A component by name or
    class (`SpringArm`, `CharacterMovement`, `StaticMeshComponent0`); an array element as `Materials[0]`;
  - `bone:<Component>.<BoneOrSocket>.x|y|z`: world location of a bone or socket of a skeletal or static mesh
    component;
  - `rel_yaw:<Component>`: the component's world yaw minus the actor's;
  - `facing_vs_velocity`: degrees between the actor's forward and its velocity (0 when it moves forward; no value when
    it stands still);
  - `bb:<Key>` on AI controllers: a blackboard value (numbers and booleans as numbers, enums as index, objects as 1
    when set, names and strings through `match`). AI controllers are actors: select them by class.

### 2.5 `components`: components in the world

`{"probe": "components", "select": {"class": "NiagaraComponent", "owner": <actor select>, "near": ...}, "field":
"count|active|visible", ...}`: registered components of a class (particle systems, decals, audio), optionally of an
owner actor and near a point, so effects that are not actors count too.

### 2.6 `widgets`: the UI on screen

`{"probe": "widgets", "select": {"class": "WBP_HUD_C", "name": "AmmoText"}, "field": "...", "match": "<regex>"}`.

- What is searched: the game's UMG trees in the viewport, whether added to the whole viewport or to one local
  player's screen, and every widget inside them, **including user widgets nested inside them** (each player's HUD
  inside a shared split-screen overlay, and the custom widgets inside that HUD).
- Slate HUDs: `{"slate": "STextBlock"}` selects Slate widgets under the game viewport by type (STextBlock, SImage,
  SProgressBar, or a game's own S... type), optionally with `"text": "<regex>"`. Widgets that paint everything in their
  own OnPaint, and AHUD canvas drawing, are not measurable.
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

### 2.12 `trace`: the agent's own trace (`play: "trace"`, never gating)

`{"probe": "trace", "fact": "built_after_last_change|played_after_last_change|read_before_first_edit|build_ok_at_end|edits_outside_project"}`:
a successful build / game run after the last change; a read before the first edit; the last build succeeded; edits
refused for a path outside the project. Only as `"required": false` quality notes with a literal threshold.

### 2.13 Points

`{"xyz": [x, y, z]}`, `{"pawn": true, "offset": [x, y, z]}`, `{"camera": true, "forward": cm}`, or
`{"actor": <select>, "offset": [x, y, z]}` (the first match).

## 3. What gates, and how a probe fails

- **At least one required probe.** Every task has at least one `probe` check with `"required": true` (the default);
  the validator refuses a task without one. Every bug fix and correction has at least one required probe that the start
  fails for the reported reason and the fix passes.
- **`still_works` probes already pass at the start.** A required probe in the `still_works` milestone (the player
  still moves, the HUD still shows, the level still loads its scenario) must pass on the start: what still works must
  already work there, or the probe itself is broken and would fail every correct solution. (A still-works probe the
  start measured nothing for, because its play crashed on the very bug the task fixes, doesn't count against it.)
- **Trace probes never gate**: `"required": false`, with a literal threshold.
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

## 4. The task check

Before any agent is given a task, the checker grades the start and the fix with every probe. A task is valid when:

- the start builds (unless the task says it doesn't, section 3.1: then it must not);
- the fix builds, boots and passes every required check;
- the start fails the task: at least one required probe (or the `fails_at_start` build check);
- every required `still_works` probe passes at the start;
- every calibrated probe measures differently on the start and the fix.

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

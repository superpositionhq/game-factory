---
name: mobile-game
description: The rules of a game-factory game-building session that hold for a mobile (Android phone) game only. Use with the game-session skill in every session that builds a game made with new-game.ps1 -Platform mobile (its root has a Platform.json), and with the write-tasks skill when writing that game's tasks. A desktop game's session reads desktop-game instead.
---

<!-- The three budget numbers and the two SDK levels below are PROPOSED (2026-11-12), not yet confirmed by the owner. -->

# Mobile game

Your game is an Android phone game, landscape or portrait, played by touch. Everything in the **game-session** skill
holds; this skill is what holds for a mobile game alone, and it takes the place of the **desktop-game** skill, which you
do not read. Where a shared rule names a keyboard, a mouse, Escape or a Win64 build, the rule here is the one that
applies.

## Start

- Create the project with `new-game.ps1 ... -Platform mobile -Orientation landscape` (or `portrait`), as the
  game-session skill's Start says, with those two switches added. The orientation is chosen with the person before the
  project exists and never changes after.
- It writes `Platform.json` at the root (`{"platform": "mobile", "orientation": "..."}`) and the Android settings in
  `Config/DefaultEngine.ini`. Never edit or delete `Platform.json`, and keep the `AndroidRuntimeSettings` block as it
  came (package name, SDK levels 26 and 34, arm64 only, Vulkan, the orientation, data inside the APK): every later
  tool reads the platform from that file, and the validators hold the project, the APK and the dataset to it.
- Android only. No iOS target, no tablet-only layout.

## Rendering

- The game runs on Unreal's mobile renderer (forward shading, Vulkan mobile or OpenGL ES 3.1). It has no Lumen, no
  Nanite, no virtual shadow maps, no ray tracing: never turn them on and never build a look that depends on them. Light
  with baked or simple dynamic lighting the mobile renderer draws; check every material on the mobile renderer, since
  one written for desktop can come out black or flat.
- **Look at the game as a phone draws it.** On this PC a play with `-FeatureLevelES31` runs the mobile renderer; add
  the phone's size, `-ResX=1920 -ResY=1080` (landscape) or `-ResX=1080 -ResY=1920` (portrait), with `-ForceRes
  -windowed`, through `ue-heavy.ps1` like every play. Every screenshot you judge the game by, the framing screenshots
  and the README stills come from such a play, never from the desktop renderer.
- **Budgets, for a mid-range phone, in any view the player can reach:** at most 500,000 triangles drawn, at most 700
  draw calls, at most 1 GB of textures in memory. Design to them from the first level (fewer, merged and instanced
  meshes, texture sizes chosen on purpose, few translucent layers, few dynamic lights). A task may measure them
  (write-tasks, the `render` reading, docs/task-probes.md section 2.21).
- The art style still decides the look (game-session, "Art style"): bring it to the mobile renderer with materials,
  baked light and colour, not with desktop post-processing.

## Touch

- **Touch only.** Everything the player does is done with fingers on the screen: on-screen buttons, a virtual stick,
  taps, drags and swipes on the world. Nothing in the game is reachable only by a key, a mouse button, mouse movement
  or a gamepad. Build the controls as UMG widgets with names of their own and bind play through Enhanced Input, so the
  AutoPlay bot still acts through `AP->Inject` and a task can press a control by its widget name.
- **The back button.** Android's back button (key `Android_Back`) does what Escape does on a desktop game: it opens
  the pause menu in play, closes what is open, and goes back one screen in menus. It never quits without asking.
- **Sized for a thumb.** Controls a finger must hit are large and apart from each other, inside the screen's safe area
  (away from the edges, the camera cut-out and the system gesture bar), and never under where the hands rest. Text is
  readable at phone size.
- **One orientation.** The layout is built for the game's orientation alone and fills it; no screen assumes the other.
- **Pause when the app leaves the foreground** (a call, the home button) and come back to the pause menu.

## Quality bar

- **Quality bar:** main menu, settings (volume, touch sensitivity where the game has a look or aim control), pause on
  the back button, save/load where it fits, HUD, sound, clear win/lose, packaged Android Shipping APK (arm64).
  Recorded and TTS voices are allowed.
- **Room for hard tasks.** A game's tasks come from its own history (write-tasks skill), and strong agents miss what
  only shows when the game runs. So build these in, and work them over several rounds rather than in one commit:
  feedback for every gameplay event (a HUD readout, marker, sound or effect); visible state changes (materials,
  colours, lights, dressing); a pause menu with settings and back navigation on the back button; touch controls whose
  size, place and response a player feels; tuned numbers a player feels (ranges, detection, damage, timers); views
  that stay inside the budgets. Fix each playtest issue in its own commit whose message says what the player saw, so
  the thread can be found and checked later.

## Tasks on a mobile game (with the write-tasks skill)

- A mobile game's tasks are played with the mobile renderer at the phone's size (1920x1080 or 1080x1920); the task
  check does this itself from `Platform.json`. A task's play never chooses a renderer or a size in its arguments.
- **Drive the game by touch.** A play's inputs use `tap` and `drag` (docs/task-probes.md section 1.5): a spot on the
  screen as fractions of its width and height, or a widget by name; `hold` for a held touch, `finger` for a second
  finger. The back button is the key `Android_Back`. A brief written for a mobile game never asks for a key or a
  mouse.
- Good mobile threads to look for in your history: a control that was too small or badly placed and took rounds to
  fix, a layout broken in the game's orientation, a view over a budget brought back under it (the `render` reading,
  in a play of its own with no picture-taking check), the back button's behaviour, the pause on leaving the app.

## Build, recording and dataset

- The dataset's `Build/` holds the game's Android Shipping APK and no Windows build. The packager builds it and reads
  it back; it needs the machine set up for mobile games (machine/README.md). Until then the game is built and played
  on this PC with the mobile renderer as above.
- The scenario videos are recorded from the game running the mobile renderer on this PC, at the orientation's size
  (1920x1080 or 1080x1920).
- `tools/validate-game.py` reads `Platform.json` and holds a mobile game to this skill's project rules.

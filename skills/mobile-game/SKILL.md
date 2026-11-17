---
name: mobile-game
description: The rules of a game-factory game-building session that hold for a mobile (Android phone) game only. Use with the game-session skill in every session that builds a game made with new-game.ps1 -Platform mobile (its root has a Platform.json), and with the write-tasks skill when writing that game's tasks. A desktop game's session reads desktop-game instead.
---

# Mobile game

Your game is an Android phone game, landscape or portrait, played by touch. Everything in the **game-session** skill
holds; this skill is what holds for a mobile game alone, and it takes the place of the **desktop-game** skill, which you
do not read. Where a shared rule names a keyboard, a mouse, Escape or a Win64 build, the rule here is the one that
applies.

## Start

- Create the project with `new-game.ps1 ... -Platform mobile -Orientation landscape` (or `portrait`), as the
  game-session skill's Start says, with those two switches added. The orientation is chosen with the person before the
  project exists and never changes after.
- It writes `Platform.json` at the root (`{"platform": "mobile", "orientation": "..."}`), the Android settings in
  `Config/DefaultEngine.ini`, the mobile AutoPlay drop-in and a `Scripts/ue.ps1` that plays at the phone's size. Never
  edit or delete `Platform.json`, and keep the `AndroidRuntimeSettings` block as it came (package name
  `com.<project lowercase>.game`, SDK levels 26 and 34, arm64 only, Vulkan, the orientation, data inside the APK) and
  the two mobile shader format lines (Linux and Windows): every later tool reads the platform from that file, and
  `tools/validate-game.py` (rule `mobile`) holds the project to it.
- Android only. No iOS target, no tablet-only layout.

## Rendering

- The game runs on Unreal's mobile renderer (forward shading, Vulkan mobile or OpenGL ES 3.1). It has no Lumen, no
  Nanite, no virtual shadow maps, no ray tracing: never turn them on and never build a look that depends on them. Light
  with baked or simple dynamic lighting the mobile renderer draws; check every material on the mobile renderer, since
  one written for desktop can come out black or flat.
- **Look at the game as a phone draws it.** On this PC a play with `-FeatureLevelES31` runs the mobile renderer; add
  the phone's size, `-ResX=1920 -ResY=1080` (landscape) or `-ResX=1080 -ResY=1920` (portrait), with `-ForceRes
  -windowed`, through `ue-heavy.ps1` like every play. Your game's `Scripts/ue.ps1 game -Render` does exactly this.
  Every screenshot you judge the game by, the framing screenshots and the README stills come from such a play, never
  from the desktop renderer.
- **Budgets, for a mid-range phone, in any view the player can reach:** at most 500,000 triangles drawn, at most 700
  draw calls, at most 1 GB of textures in memory. Design to them from the first level (fewer, merged and instanced
  meshes, texture sizes chosen on purpose, few translucent layers, few dynamic lights). A task may measure them
  (write-tasks, the `render` reading, docs/task-probes.md section 2.21).
- The art style still decides the look (game-session, "Art style"): bring it to the mobile renderer with materials,
  baked light and colour, not with desktop post-processing.

## Touch

- **Touch only.** Everything the player does is done with fingers on the screen: on-screen buttons, a virtual stick,
  taps, drags and swipes on the world. Nothing in the game is reachable only by a key, a mouse button, mouse movement
  or a gamepad. Build the controls as UMG widgets with names of their own, so a task can press a control by its
  widget name.
- **The AutoPlay bot plays by touch too.** Your game has the mobile drop-in (`Source/<Project>/AutoPlay/`, from
  `tools/ue-pipeline/autoplay-mobile/`): the bot calls `AP->Touch(Finger, ViewportPos)` every frame a finger is on
  the screen, at the place of the control it uses (a button's centre, a point on the stick), and the touch reaches the
  game as a phone's does. `AP->Inject` is only for the back button. A recorded run with no touch fails
  (docs/autoplay-contract.md, "Mobile games").
- **The back button.** Android's back button (key `Android_Back`) does what Escape does on a desktop game: it opens
  the pause menu in play, closes what is open, and goes back one screen in menus. It never quits without asking.
- **Sized for a thumb.** Controls a finger must hit are large and apart from each other, inside the screen's safe area
  (away from the edges, the camera cut-out and the system gesture bar), and never under where the hands rest. Text is
  readable at phone size.
- **One orientation.** The layout is built for the game's orientation alone and fills it; no screen assumes the other.
- **Pause when the app leaves the foreground** (a call, the home button) and come back to the pause menu.

## Quality bar

- **Quality bar:** main menu, settings (volume, touch sensitivity where the game has a look or aim control), pause on
  the back button, save/load where it fits, HUD, sound, clear win/lose, packaged Windows Shipping build that runs the mobile renderer (what is
  recorded) and the Android Shipping APK (arm64) where the machine can build it.
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

- The pipeline (`tools/ue-pipeline/build.ps1`, `record.ps1`) reads the platform itself: you start it as for any game.
  It packages the Windows Shipping build, records the scenario videos from that build running the mobile renderer at
  the orientation's size (1920x1080 or 1080x1920), and takes the stills from those videos.
- **The APK.** The same build step makes the game's Android Shipping APK (arm64) when the machine has the Android
  toolchain (`machine/check.ps1` says whether it has; docs/new-machine.md, "Android", says how to install it). Without
  the toolchain the step is skipped with a message, and the dataset says it has no APK. Never install the toolchain
  yourself in a game session: ask the person.
- The dataset's `Build/` holds the Windows build the videos came from and, when it was built, the APK in
  `Build/Android/`; its manifest says `platform` (`mobile`) and the orientation.
- `tools/validate-game.py` reads `Platform.json` and holds a mobile game to this skill's project rules.

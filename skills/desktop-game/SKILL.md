---
name: desktop-game
description: The rules of a game-factory game-building session that hold for a desktop (Windows) game only. Use with the game-session skill in every session that builds a desktop game, which is every game without a Platform.json at its root. A mobile game's session reads mobile-game instead.
---

# Desktop game

What the **game-session** skill's "Engine and content" list holds for a desktop game alone. A game is a desktop game
unless it was made with `new-game.ps1 -Platform mobile` (then its root has a `Platform.json`, and its session reads the
**mobile-game** skill instead of this one).

- **Quality bar:** main menu, settings (volume, resolution, mouse sensitivity), pause, save/load where it fits, HUD,
  sound, clear win/lose, packaged Win64 Shipping build. Recorded and TTS voices are allowed.
- **Room for hard tasks.** A game's tasks come from its own history (write-tasks skill), and strong agents miss what
  only shows when the game runs. So build these in, and work them over several rounds rather than in one commit:
  feedback for every gameplay event (a HUD readout, marker, sound or effect); visible state changes (materials,
  colours, lights, dressing); a pause menu with settings and back navigation on Escape; tuned numbers a player feels
  (ranges, detection, damage, timers). Fix each playtest issue in its own commit whose message says what the player
  saw, so the thread can be found and checked later.

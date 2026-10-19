# Session briefs

The prompts that start each session of game-factory (Claude Code or Codex), as reusable templates. The rules every
session follows are in the skills (`skills/`: commit-always, game-session, write-tasks); the briefs carry the task.
The coordinator and its helper and game sessions use the Claude desktop app's side sessions; a solo game runs in a
terminal with either agent.

| File | For |
|---|---|
| [coordinator.md](coordinator.md) | the coordinator (parent) session: role and the user's standing decisions |
| [game-session.md](game-session.md) | template for a game-building session (placeholders) |
| [solo-game.md](solo-game.md) | one game with one plain `claude` or `codex` session (terminal, no desktop app, no coordinator): paste and fill |
| [games/](games/) | one fill-in per game: title, project name, pitch, brief, scenarios, story, art packs, known facts |
| [helpers/](helpers/README.md) | ue-pipeline, asset-scout, packager, creation-replay |
| [original/](original/) | historical prompts from the first build, verbatim (scrubbed); not instructions |

## Spawning a game session

1. Pick the fill-in (`games/<slug>.md`) or write one for a new game (same headings).
2. Copy the `text` block of `game-session.md`, replace every `{{PLACEHOLDER}}` (the fill-in's sections go in as
   they are), set `{{MODE}}` to `NEW` or `CONTINUE`.
3. Start the session from the coordinator with a fresh context and the title `{{GAME_TITLE}}`.

The original game prompts predate later user rules (they say "engine shapes, no marketplace packs", "don't push",
"no commits in game-factory"); the templates and skills carry the current rules, and win where they differ.

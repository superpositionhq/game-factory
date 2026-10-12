# Session briefs

The prompts that start each Claude Code session of game-factory, as reusable templates. The rules every session
follows are in the skills (`.claude/skills/`: commit-always, game-session, coordinator); the briefs carry the task.

| File | For |
|---|---|
| [coordinator.md](coordinator.md) | the coordinator (parent) session: role and the user's standing decisions |
| [game-session.md](game-session.md) | template for a game-building session (placeholders) |
| [games/](games/) | one fill-in per game: title, project name, pitch, brief, scenarios, story, art packs, known facts |
| [helpers/](helpers/README.md) | ue-pipeline, asset-scout, packager, creation-replay, liaozhai-replay |
| [original/](original/) | the prompts as first sent on the first machine, verbatim (user path, name and GitHub handle scrubbed) |

## Spawning a game session

1. Pick the fill-in (`games/<slug>.md`) or write one for a new game (same headings).
2. Copy the `text` block of `game-session.md`, replace every `{{PLACEHOLDER}}` (the fill-in's sections go in as
   they are), set `{{MODE}}` to `NEW` or `CONTINUE`.
3. Start the session from the coordinator with a fresh context and the title `{{GAME_TITLE}}`.

The original game prompts predate later user rules (they say "engine shapes, no marketplace packs", "don't push",
"no commits in game-factory"); the templates and skills carry the current rules, and win where they differ.

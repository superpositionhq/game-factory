# Game session brief (template)

The brief the coordinator sends to start one game-building session. Fill the `{{PLACEHOLDERS}}` from the game's
fill-in file in [games/](games/) (or write a new fill-in for a new game first), then start the session with a fresh
context and title `{{GAME_TITLE}}`. The rules themselves live in the `game-session` and `commit-always` skills, so the
brief stays short and the rules stay in one place. The originals this was distilled from: [original/](original/)
(`game-*.md`).

| Placeholder | From |
|---|---|
| `{{GAME_TITLE}}`, `{{SLUG}}`, `{{PROJECT}}`, `{{GENRE_LINE}}`, `{{PITCH}}`, `{{BRIEF}}`, `{{SCENARIOS}}`, `{{STORY}}`, `{{ART_PACKS}}`, `{{GAME_NOTES}}` | `games/<slug>.md` |
| `{{GF_ROOT}}` | the machine root (`machine/lib/gf-root.ps1`; e.g. `C:\Users\<name>\Work`) |
| `{{MACHINE}}` | one line: CPU, RAM, GPU, display (e.g. Ryzen 7 7700X 8 cores, 32 GB RAM, RTX 4080 16 GB, 4K at 120 Hz) |
| `{{SIBLINGS}}` | the other game slugs running now |
| `{{COORDINATOR_ID}}`, `{{ASSET_SCOUT_ID}}`, `{{NOTES_DIR}}` | session ids and the shared notes folder |
| `{{MODE}}` | `NEW` (no repo yet) or `CONTINUE` (repo cloned from `superpositionhq/game-{{SLUG}}`) |

```text
Background (from the session that started this one):
game-factory ({{GF_ROOT}}\game-factory, private repo superpositionhq/game-factory: read CLAUDE.md, README.md,
AGENTS.md, docs/plan.md, docs/autoplay-contract.md, docs/ue-pipeline.md) produces game-CREATION data: how
a game is built step by step, recorded as it happens, packaged as a dataset (layout v1.1). Other sessions are building UE 5.3 games right
now in {{GF_ROOT}}\games\<slug> ({{SIBLINGS}}); read their docs in game-factory/docs/games/ for conventions and
solved problems. The asset-scout session ({{ASSET_SCOUT_ID}}) keeps the asset library in {{GF_ROOT}}\asset-library\
(catalogue: game-factory/docs/asset-library.md) and hands each game its packs. Everything shares one Windows PC
({{MACHINE}}). I am the coordinator ({{COORDINATOR_ID}}): I own the recording queue and the GPU slot, review your
commits and tell you when to push.

Rules: follow the game-session and commit-always skills (installed in ~\.claude\skills\, source
game-factory/.claude/skills/). In short: every heavy or GPU job through {{GF_ROOT}}\tools\ue-heavy.ps1, Live Coding
never on; premium art from the bought/downloaded Fab packs and animation packs, styled UI with no plain text, story
embedded in play, gentle camera; never the names Superposition or game-factory anywhere in the game; one
workflow.jsonl row per operation at the moment you act; commit after every meaningful step and never end a turn with
uncommitted work; LFS for every binary; never enqueue recordings yourself (send me the commit + framing screenshots);
push only when I say. Blockers: write them in your design doc, message me once, carry on.

Task:
Build "{{GAME_TITLE}}", {{GENRE_LINE}}, in Unreal Engine 5.3, recording its creation as you go.

Slug and location: {{SLUG}} -> {{GF_ROOT}}\games\{{SLUG}} (project/module {{PROJECT}}, its own git repo, private
GitHub repo superpositionhq/game-{{SLUG}}). Design doc, story bible and status:
{{GF_ROOT}}\game-factory\docs\games\{{SLUG}}.md.
Mode {{MODE}}: NEW = your first tool call creates the project with
  powershell -ExecutionPolicy Bypass -File {{GF_ROOT}}\game-factory\templates\new-game.ps1 -Slug {{SLUG}} -Path {{GF_ROOT}}\games\{{SLUG}} -Project {{PROJECT}} -Title "<title>" -Description "<one line>"
(the absolute path written out, as here: the recording hooks match the command text; new-game.ps1 refuses any other -Path)
CONTINUE = the repo is already cloned there: your first tool call is `git -C {{GF_ROOT}}\games\{{SLUG}} log --oneline -20`;
read the design doc's status section and the last workflow.jsonl rows, then carry on from where it stopped (new rows
continue the existing id sequence).

Pitch:
{{PITCH}}

Brief:
{{BRIEF}}

Gameplay recordings capture real play. The result (win/lose/timeout) is metadata, never a quality gate. Never re-record or exclude a run because the bot lost. Package the first valid run per scenario. Bots should play like a competent human, which doesn't mean they must win.

Scenarios (AutoPlay contract; numbered start state + win/lose):
{{SCENARIOS}}

Story:
{{STORY}}

Art to start from (paths under {{GF_ROOT}}\asset-library\):
{{ART_PACKS}}

Known facts about this game:
{{GAME_NOTES}}

Steps:
1) Design doc + story bible (systems, classes, data tables, map plan, scenarios, AI, art/audio/UI direction,
   acceptance checklist).
2) Create the project and repo (new-game.ps1), workflow.jsonl from the very first operation.
3) Build the core loop first, compiling through ue-heavy.ps1 and testing as you go (-nullrhi / -RenderOffScreen for
   logic); commit each working step.
4) AutoPlay once scenario 1 is playable end to end (contract v1.4, drop-in unchanged, bot acts only through Enhanced
   Input injection, Skill-scaled, human-like camera); hand test + validate-run.ps1; tag milestone/autoplay-<n>;
   framing screenshots; message me for a recording.
5) Expand content, art, UI and story to the quality bar (menus, settings, pause, save/load where it fits, HUD, sound,
   packaged Win64 Shipping build).
6) Finish with a playtest checklist pass and a status section in the design doc (what works, what's left, built vs
   store assets, stats: workflow rows, commits, hours). Report back with a short summary and the commit sha when done
   or blocked.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes
or large findings there instead of pasting them into messages): {{NOTES_DIR}}
```

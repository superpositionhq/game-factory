# Solo game brief (plain Claude Code)

For one person building one game with one Claude Code session in a terminal: no desktop app, no coordinator, no
other sessions. The rules are the same as for a coordinated game session (the `game-session` and `commit-always`
skills, installed by `machine/setup.ps1`); what the coordinator would do (queue recordings, decide pushes, relay
directions, hand out store packs) is done by you, the person at the keyboard. With the desktop app and several games
at once, use [coordinator.md](coordinator.md) and [game-session.md](game-session.md) instead.

Start: open a terminal in the machine root (`cd <root>`; its `CLAUDE.md` loads the game-factory rules), run `claude`,
and paste the `text` block below with the placeholders filled. For a game that has a fill-in in [games/](games/),
take the pitch, scenarios and story from it; for a new game, write them in a few lines each.

| Placeholder | From |
|---|---|
| `{{GAME_TITLE}}`, `{{SLUG}}`, `{{PROJECT}}` | the title, a lowercase slug (`island-survival`) and a PascalCase project name (`IslandSurvival`) |
| `{{PITCH}}`, `{{SCENARIOS}}`, `{{STORY}}`, `{{ART_PACKS}}` | `games/<slug>.md`, or your own few lines |
| `{{GF_ROOT}}` | the machine root (e.g. `C:\Users\<name>\Work`; `machine/lib/gf-root.ps1`) |
| `{{ORG}}` | the GitHub organisation (or user) owning the repos: `github_org` in the machine config |
| `{{MODE}}` | `NEW` (no repo yet) or `CONTINUE` (repo already cloned into `{{GF_ROOT}}\games\{{SLUG}}`) |

```text
You are the only session on this machine: build "{{GAME_TITLE}}" in Unreal Engine 5.7 and record how it is built.
There is no coordinator and there are no other sessions: never start, spawn or message other sessions. Whatever the
skills say to send to "the coordinator" (recording requests, push requests, Fab requests, blockers), tell me here
and wait for my answer.

Read first: {{GF_ROOT}}\game-factory\CLAUDE.md, README.md, AGENTS.md, docs/autoplay-contract.md, docs/ue-pipeline.md,
and the game-session and commit-always skills (~\.claude\skills\). They hold the rules; in short:
- every editor, build, cook or GPU job through {{GF_ROOT}}\tools\ue-heavy.ps1; Live Coding never on;
- premium art from store packs (any folder under Content/, committed through Git LFS, never git-ignored; the repo stays
  private), styled UI with no plain text, story embedded in play, gentle camera; never the names of the toolkit or
  its owners inside the game;
- one workflow.jsonl row per operation at the moment you act; commit after every meaningful step, never end a turn
  with uncommitted work; LFS for every binary;
- my messages that change the game are directions: rewrite each as one or two neutral sentences and append it to
  workflow.jsonl as a user.direction row (via "direct") before acting on it (commit-always skill);
- AutoPlay's goal is NOT to win: the bot only drives the game with human-like input; fix game bugs, never tune the
  bot; one AutoPlay run per scenario;
- push only when I say; never run tools/ue-pipeline/enqueue.ps1 (recordings are queued by me, if at all).

Game: {{GAME_TITLE}} ({{SLUG}} -> {{GF_ROOT}}\games\{{SLUG}}, project {{PROJECT}}, private GitHub repo
{{ORG}}/game-{{SLUG}}). Design doc, story bible and status: {{GF_ROOT}}\game-factory\docs\games\{{SLUG}}.md (create
it if missing).
Mode {{MODE}}: NEW = your first tool call creates the project with
  powershell -ExecutionPolicy Bypass -File {{GF_ROOT}}\game-factory\templates\new-game.ps1 -Slug {{SLUG}} -Path {{GF_ROOT}}\games\{{SLUG}} -Project {{PROJECT}} -Title "<title>" -Description "<one line>"
(the absolute path written out: the recording hooks match the command text).
CONTINUE = your first tool call is `git -C {{GF_ROOT}}\games\{{SLUG}} log --oneline -20`; read the design doc's
status and the last workflow.jsonl rows and carry on.

Pitch:
{{PITCH}}

Scenarios (AutoPlay contract; numbered start state + win/lose):
{{SCENARIOS}}

Story:
{{STORY}}

Art to start from (store packs in {{GF_ROOT}}\asset-library\, or ask me for Fab packs):
{{ART_PACKS}}

Steps:
1) Design doc + story bible; 2) create the project (new-game.ps1); 3) core loop first, compiling and testing through
ue-heavy.ps1, committing each working step; 4) AutoPlay once scenario 1 plays end to end: one hand test +
tools/ue-pipeline/validate-run.ps1, tag milestone/autoplay-<n>, framing screenshots, then tell me; 5) content, art,
UI, sound, packaged Win64 Shipping build; 6) playtest checklist, status section in the design doc, and before calling
it content-complete: 5-7 real gameplay stills in Docs/screenshots/ (JPG, LFS) shown in the README as a hero image
plus a captioned gallery, checked on github.com after I say push. Report each milestone here with the commit sha.
```

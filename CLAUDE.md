# game-factory: instructions for every session

This repo coordinates Claude Code sessions that build Unreal Engine 5.3 games (`%GF_ROOT%\games\<slug>`, private
`superpositionhq/game-<slug>` repos) and turn them into game-creation datasets. `%GF_ROOT%` is the machine root
(env `GF_ROOT`, else `%USERPROFILE%\.game-factory\config.json`, else `%USERPROFILE%\Work`); see
[machine/README.md](machine/README.md).

Skills (in `.claude/skills/`, installed to `~\.claude\skills\` by `machine/bootstrap.ps1`):

- **commit-always**: every session. Commit after every meaningful step, never end a turn with uncommitted work,
  LFS for binaries, push only when the coordinator says.
- **game-session**: sessions that build a game (art, UI, story, naming, ue-heavy/GPU, workflow.jsonl, AutoPlay,
  framing screenshots, dataset v1.1).
- **coordinator**: the parent session (queue and GPU slot, framing gate, review and push, scrub and packaging).

Rules for working in this repo: [AGENTS.md](AGENTS.md). Session briefs: [docs/briefs/](docs/briefs/README.md).
New machine: [docs/new-machine.md](docs/new-machine.md). Pipeline: [docs/ue-pipeline.md](docs/ue-pipeline.md).

**Recordings and results.** Gameplay recordings capture real play. The result (win/lose/timeout) is metadata, never a
quality gate. Never re-record or exclude a run because the bot lost. Package the first valid run per scenario. Bots
should play like a competent human, which doesn't mean they must win.

This checkout is shared by several sessions at once: stage explicit paths only and never commit another session's
changes.

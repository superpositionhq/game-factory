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

Rules for working in this repo: [AGENTS.md](AGENTS.md). Session briefs: [docs/briefs/](docs/briefs/README.md).
New machine: [docs/new-machine.md](docs/new-machine.md). Pipeline: [docs/ue-pipeline.md](docs/ue-pipeline.md).

**Priorities (user decision).** What ships is what matters, in this order: the game plays; the game builds (editor and packaged Shipping); the dataset holds the replay scripts and the git log. The AutoPlay bot should still play like a human (human-like input, aim and camera), but bot work never blocks a release: one recording per scenario that shows the game running is enough, whatever the result (win/lose/timeout is metadata). No tuning for win rates, seed sweeps or "clean" runs, and no re-runs or re-recordings to improve how the bot plays. No retest loops: every GPU or editor run costs about 30 minutes of the shared machine and holds up delivery, so run the minimum once and report; re-run only when the user asks. Game-session work never blocks dataset packaging or sharing.

**Dataset.** Each game's full dataset is `games\<slug>\Dataset.zip`: the same name everywhere, git-ignored (`/Dataset.zip`, `/Dataset.pending.zip`, `/.dataset/`), produced by `tools/package-dataset.ps1`, never committed. The committed `Dataset\` is the same minus `UEProject/` and `Build/`.

This checkout is shared by several sessions at once: stage explicit paths only and never commit another session's
changes.

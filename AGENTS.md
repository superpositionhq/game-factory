# AGENTS.md — game-factory: instructions for every session

This repo coordinates coding-agent sessions (Claude Code or OpenAI Codex CLI) that build Unreal Engine 5.7 games
(`%GF_ROOT%\games\<slug>`, private `<org>/game-<slug>` repos, `<org>` = `github_org` in the machine config) and turn
them into game-creation datasets. `%GF_ROOT%` is the machine root (env `GF_ROOT`, else
`%USERPROFILE%\.game-factory\config.json`, else `%USERPROFILE%\Work`); see [machine/README.md](machine/README.md).
Claude Code reads this file through [CLAUDE.md](CLAUDE.md); Codex reads it directly (and through `<root>\AGENTS.md`).

Skills (one source, [skills/](skills/); `machine/bootstrap.ps1` copies them to `~\.claude\skills\` for Claude Code and
`~\.agents\skills\` for Codex; read the `SKILL.md` named here before the work it covers, whichever agent you are):

- **commit-always** ([skills/commit-always/SKILL.md](skills/commit-always/SKILL.md)): every session. Commit after every
  meaningful step, never end a turn with uncommitted work, LFS for binaries, push only when the coordinator says.
- **game-session** ([skills/game-session/SKILL.md](skills/game-session/SKILL.md)): sessions that build a game (art, UI,
  story, naming, ue-heavy/GPU, workflow.jsonl, AutoPlay, framing screenshots, dataset v1.1).
- **write-tasks** ([skills/write-tasks/SKILL.md](skills/write-tasks/SKILL.md)): sessions that write, move or review a
  game's tasks (the orphan `tasks` branch, never on main; about 10 per game; the four kinds, seed and reference commits,
  briefs written from context, milestones with deterministic probe checks).

**Only these skills (owner's rule, 2026-10-21).** Contractors and every agent session working for game-factory use the
three skills above and no others. Never install, enable or invoke any other skill: not the person's own personal or
project skills, not a plugin's or a marketplace's skills, not the skills bundled with the agent (Claude Code's built-in
skills and slash-command skills, Codex's system skills). A skill the agent offers by name or description that is not
one of the three is ignored. Work no skill here covers is done by hand under these rules, or asked about (the
coordinator, or the person in a solo session). _(why: the recorded sessions are the dataset, so how a game gets made
must follow these rules only; another skill brings instructions and habits nobody here reviewed into the creation
record)_

Session briefs: [docs/briefs/](docs/briefs/README.md). New machine: [docs/new-machine.md](docs/new-machine.md).
Pipeline: [docs/ue-pipeline.md](docs/ue-pipeline.md).

**Priorities (user decision).** What ships is what matters, in this order: the game plays; the game builds (editor and packaged Shipping); the dataset holds the replay scripts and the git log. The AutoPlay bot should still play like a human (human-like input, aim and camera), but bot work never blocks a release: one recorded scenario per game (one video) that shows the game running is enough, whatever the result (win/lose/timeout is metadata). No tuning for win rates, seed sweeps or "clean" runs, and no re-runs or re-recordings to improve how the bot plays. No retest loops: every GPU or editor run costs about 30 minutes of the shared machine and holds up delivery, so run the minimum once and report; re-run only when the user asks. Game-session work never blocks dataset packaging or sharing.

**AutoPlay's goal is NOT to win (user rule).** The bot only drives the game with human-like input so a recording shows the game running. Never tune, fix or re-test the bot to win, score, finish, reach targets, resupply or avoid getting stuck; losing, timing out or wandering is fine (metadata). Fix only game bugs (crash, hang, broken level, missing art, lighting, camera); then one AutoPlay run per scenario and the recording request.

**Dataset.** Each game's full dataset is `games\<slug>\Dataset.zip`: the same name everywhere, git-ignored (`/Dataset.zip`, `/Dataset.pending.zip`, `/.dataset/`), produced by `tools/package-dataset.ps1`, never committed. The committed `Dataset\` is the same minus `UEProject/` and `Build/`.

This checkout is shared by several sessions at once: stage explicit paths only and never commit another session's
changes.

## Agents

Both agents run the same skills, the same recording hooks and the same workflow; what differs:

| | Claude Code | Codex CLI |
|---|---|---|
| start | `claude` in `<root>` (reads `<root>\CLAUDE.md`) | `codex -s danger-full-access` in `<root>` (reads `<root>\AGENTS.md`) |
| skills | `~\.claude\skills\` (also offered by name) | `~\.agents\skills\` (`$<name>` or `/skills`; also offered by description) |
| recording hooks | `~\.claude\settings.json`: PostToolUse, PostToolUseFailure, Stop | `~\.codex\hooks.json`: PostToolUse, Stop (trusted in `config.toml`; `/hooks` shows them) |
| file edits in `actions.jsonl` | `Write` / `Edit` rows | `apply_patch` rows (the patch text) |
| permissions | as set in Claude Code (asks before commands by default) | `codex -s danger-full-access`: the default workspace sandbox blocks what game sessions need (writes to `C:\UEB` and `%LOCALAPPDATA%`, the machine-wide job-slot mutexes, `git push` / `gh`) |
| transcript (backfill) | `~\.claude\projects\…\<session>.jsonl` | `~\.codex\sessions\YYYY\MM\DD\rollout-…-<session>.jsonl` |

Under Codex, the shell tool is recorded as `Bash` whatever shell ran the command. Read a skill by opening its
`SKILL.md` when the task matches, even if the agent did not offer it. The person's directions reach the dataset only as
`user.direction` rows that the session writes itself (commit-always skill): neither agent's hooks store the messages.

## Rules

Rules for agents working in this repository. Each rule says what went wrong without it.
Background is in `docs/`; keep this section to rules.

### Data

- Never commit a full package, a project snapshot, `git.log` with asset diffs, or package zips here; only
  tools and docs. _(failure: a package is tens of GB, far past GitHub's 100 MB file limit)_
- Keep this repository private. _(failure: the docs describe a private repository and its asset data)_
- Step reasons are the builder's own narration or notes, or the commit message; never write them with a
  model. _(failure: reasons written after the fact make a package a reconstruction rather
  than a record)_
- Anonymize authors as `dev_NN` and run the leak scan (real names, e-mails, `C:\Users\…`, `/Users/…`, `/home/…`)
  over every text file of a package before calling it done. _(failure: commit metadata and asset files can
  carry real names and machine paths)_

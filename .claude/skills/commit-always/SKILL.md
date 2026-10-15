---
name: commit-always
description: Commit discipline for every game-factory session (game builders, helpers, coordinator). Use whenever you change files in a game repo or in game-factory, before ending any turn, and when deciding what may be committed or pushed. Covers commit cadence, messages, workflow.jsonl rows, LFS, what never to commit, push policy and the WIP auto-commit hook.
---

# Commit always

The git history is the product: a game's `git.log` and `workflow.jsonl` are the creation record the dataset is built
from, and uncommitted work is invisible to the coordinator, the pipeline (it builds from commits) and the packager.
The user's standing rule: **every session commits its work continuously.**

## When

- After every meaningful step: a system compiles and runs, an editor script ran and changed content, a level or asset
  set is imported, a bug is fixed and verified, a doc section is written, a tool change passes its test. At least
  every ~15 minutes of active work.
- Before anything risky (an engine upgrade of an asset, a mass rename, `git lfs migrate`, a long build).
- **Never end a turn with uncommitted work of yours.** Last step of every turn: `git status`, commit what is yours,
  then report the sha.

## Which repo, which files

- **Game session:** your game repo (`%GF_ROOT%\games\<slug>`): `git add -A` is fine there, it is yours alone.
  In game-factory you own only `docs/games/<slug>.md`; commit it with `git commit -m "..." -- docs/games/<slug>.md`.
- **Helper / coordinator:** game-factory is one checkout shared by several sessions. Stage explicit paths only
  (`git add <paths>`, `git commit -- <paths>`), never `git add -A` / `git commit -a`, never commit another session's
  changes. If someone else has uncommitted edits in a file you must change, commit only your change (write your
  version of the blob into the index with `git hash-object -w` + `git update-index --cacheinfo`, or ask them first).

## Message

- Subject: what changed, imperative, specific (`Add frost tower slow stacking and its data table`), under ~72 chars.
- Body: why, how it was verified (build/test/run result), anything left open.
- Game repos: end with the workflow rows the commit covers: `workflow: td-00412..td-00431`. A commit that acts on a
  human direction also names it: `Direction: td-00398 (<the direction in a few words>)`.
- Game repos: no AI attribution trailers (`Co-Authored-By: Claude ...`) and never the names Superposition or
  game-factory: commit messages ship in the dataset's `git.log`. Deliverables block Claude/Anthropic/Opus outright.
  game-factory commits follow the normal attribution rules.

## workflow.jsonl (game repos)

- Rows are written **when the operation happens**, not at commit time (schema `ue-workflow/v0`: `schema, id, seq,
  time` (ISO 8601 ms + offset), `actor:"agent", op, target, params, reason` (intent at that moment),
  `reason_source:"agent_note", status` (`observed`/`failed`/`reverted`), `source {script, sha256, commit}`).
- Commit `workflow.jsonl` together with the work it describes; the row ids go in the message. Many games also log an
  `op:"vcs.commit"` row (sha, subject, files) right after committing; it rides along in the next commit.
- Never edit, delete, reorder or backfill rows. Missed something: one `op:"log.gap"`, `status:"unrecorded"` row saying
  what and when. Failed attempts get rows too.
- **One exception (user rule): banned names.** A row that contains a banned name (studio/org name, the tool repo's
  name, agent/tool/provider names, the account name or machine paths with it, e-mail addresses) or the old schema id
  `superposition.ue-workflow/v0` is edited in place to remove it, with a neutral word or placeholder and nothing else in
  the row changed; then one correction row is appended (`op:"log.correct"`, `params {rows: [ids], what: "removed banned
  names"}`), and the commit message names the edited rows. `python <GF_ROOT>/game-factory/tools/scrub-workflow-rows.py
  <repo>` does exactly this (dry run first, then `--apply`; it prints the commit message line). Write new rows without
  such names in the first place (relative paths, neutral words). The account name is enforced in every non-script file
  (workflow.jsonl, ReplayConfig.json: `{root}`/`{home}`/`{pipeline}` there, docs, data); scripts that already ran keep it
  (never edited; the packager scrubs them), new scripts use relative paths.
- Every editor script that ran stays in `Scripts/` unchanged (new version instead of overwriting), so `source.script`
  + `source.sha256` point at the real code.
- **Human directions (user rule: "not direct user messages, more like user directions"; "you should rewrite that and
  save to the workflow.jsonl").** Whoever receives a user message REWRITES it as a direction: what to change and why,
  one or two neutral sentences, without tone, profanity, names or chat wording (a game session for a message to it;
  the coordinator before relaying, sending the rewritten text ready to log). The rewritten direction is SAVED at once,
  before any action, by appending it to the game repo's own `workflow.jsonl` (the file at the repo root: the live
  source the packager copies, scrubbed, into `Dataset/workflow.jsonl`; never edit `Dataset/workflow.jsonl` by hand).
  A relayed direction is appended as the coordinator worded it, with `via: "coordinator"`. The raw message is never
  stored anywhere in the repo. The row:
  `actor:"user"`, `op:"user.direction"`, `target` the area (`camera`, `lighting`, `art`, `ui`, `audio`, `story`,
  `design`, `bot`, `build`, `process`...), `params: {direction: "<one or two sentences: what the human directed and
  why, in neutral wording, no names, not a quote of the message>", via: "direct" | "coordinator"}`,
  `reason_source:"user_direction"`, `status:"observed"`. Every later row that acts on it carries
  `"direction": "<that row id>"`, and each commit that acts on it names it in the body (`Direction: dk-00412 (camera
  further back in narrow spaces)`), so the dataset's `git.log` links each change to its cause. One row per direction,
  not per message; a direction that changes an earlier one gets a new row saying so.

## What to commit

Everything needed to rebuild the game from the repo alone: `Source/`, `Config/`, the `.uproject`, `Content/`
(including the store packs, in any folder under `Content/`), `Scripts/`, `RawAssets/` used for imports, `workflow.jsonl`,
`assets.manifest.json`, `Docs/` (ThirdPartyNotices, screenshots), `README.md`, `Dataset/`. Nothing stays git-ignored
except build output and the local dataset zip with its scratch (`/Dataset.zip`, `/Dataset.pending.zip`, `/.dataset/`).

**Store packs are committed, the repo stays private (user rule).** Every Fab / marketplace pack the game uses is
committed (any folder under `Content/`, e.g. `Content/Fab/<Pack>/`) through Git LFS and listed in
`assets.manifest.json` (one format for every game: `assets-manifest/v1`, docs/game-format.md): never git-ignore store content (no `.gitignore` entry, no
"download it yourself" step), so a clone builds the game. The licences allow that only in a private repo: game repos
are never made public, forked to a public place or shared outside the org, and store files are never uploaded
anywhere else.

**Binaries go through Git LFS.** `.gitattributes` from `templates/ue-game` covers every binary type
case-insensitively. Before the first commit of a new binary type, add its pattern; check with
`git check-attr filter -- <file>` (must say `lfs`). A binary committed outside LFS means `git lfs migrate` later,
which rewrites history and changes every sha that recordings and briefs refer to.

## Never commit

- Build output and caches: `Binaries/ Intermediate/ Saved/ DerivedDataCache/ Build/ Packaged/`, `.vs/`, `*.sln`.
- Anything under `%GF_ROOT%\.recording\` (hook-owned; never edit it either), `recordings\`, `builds\`, `deliverables\`.
- Secrets: tokens, cookies, signed download URLs, `.env` files, credentials of any kind.
- In game-factory: packages, project snapshots, package zips, `git.log` exports with asset diffs, ffmpeg or other
  downloaded binaries (`machine/get-ffmpeg.ps1` fetches them), GPU recordings.
- In game repos: the names Superposition / game-factory anywhere (code, comments, configs such as `CompanyName`,
  scripts, docs). The user's absolute profile path where avoidable (run `tools/ue-pipeline/scrub-import-paths.py`
  before a commit that will be recorded or packaged; the coordinator asks for it).

## The replay after every commit (game repos)

A game whose `ReplayConfig.json` has `"live": true` is replayed in the background after each commit (docs/ue-replay.md,
section 3). The post-commit hook prints `[replay] ...` lines when the last replay found something: read them, fix
what they name in your next commits (they are about how you work, not about the game), and keep `ReplayConfig.json`
current (new wrapper -> `run_patterns`; store pack copied in -> `asset_drops`). Never amend or rebase a commit you
already made: the replay has to go back and redo everything after it.

## Push policy

- **Never push unless the coordinator says so** (or the user, in your own session). The coordinator reviews first
  (untracked files, ignored dirs, non-LFS blobs, LFS coverage), then tells you to push.
- When told: `git push origin main --follow-tags`, then verify `git ls-remote origin main` matches `git rev-parse HEAD`
  and `git lfs push origin main --dry-run` lists nothing left.
- Game repos live at `<org>/game-<slug>` (private; `<org>` = `github_org` in the machine config). Never force-push. Never rewrite pushed history except a
  coordinator-ordered scrub (`tools/ue-pipeline/scrub-history.ps1`) or LFS migration.

## The WIP auto-commit

The Stop hook (`record-action.ps1 -Stop`) commits leftover changes in a game repo as `WIP` at the end of every turn.
It is a safety net so nothing is lost, not a way of working: a `WIP` commit carries no reason and no row ids, and it
reads as sloppy in the dataset's `git.log`. If one of yours appears, say in your next commit's body what the WIP
commit contained. Don't squash or amend it away; the history is the record. The hook does not cover game-factory:
helpers and the coordinator must commit there themselves.

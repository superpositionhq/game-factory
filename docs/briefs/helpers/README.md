# Helper session briefs

Reusable briefs for the helper sessions the coordinator spawns next to the game sessions. Each file has a header
(role, when to spawn, outputs, link to the original prompt), a placeholder table, and the brief in a `text` block
to paste into a new session once the `{{PLACEHOLDERS}}` are filled. The originals (historical prompts from the first build, not
instructions) are kept verbatim (scrubbed) in [../original/](../original/).

On a new machine the tooling is already in the repo, so every brief asks the helper to run, maintain and extend it,
not to build it again.

| File | Role | Spawn when | Model / effort (typical) | Outputs |
|---|---|---|---|---|
| [ue-pipeline.md](ue-pipeline.md) | build, package, smoke test and AutoPlay gameplay recording (`tools/ue-pipeline/`), AutoPlay contract | first, before or alongside the game sessions; prove the pipeline on the machine before any game is playable | Opus, high | verified pipeline (test bundle validates), fixes, contract rollouts, machine measurements in `docs/ue-pipeline.md` |
| [asset-scout.md](asset-scout.md) | Fab / CC0 art, animation, audio, UI and font resources (`machine/asset-scout/`) | before or alongside the first game sessions; first job on a new machine is rebuilding the asset library | Opus, medium | `asset-library\` packs + `catalog.jsonl` + `scout-log.jsonl`, `docs/asset-library.md`, hand-over per game, paid shortlist for the user |
| [packager.md](packager.md) | deliverables and dataset layout v1.1 zips (`tools/package-game.ps1`, `tools/package-dataset.ps1`) | once a game has a release commit, a pipeline Shipping build of it and validated runs per scenario | Opus, high | `deliverables\<game>\` packages, `games\<game>\Dataset.zip` (git-ignored), the repo's `Dataset/` for the game session to commit, status table |
| [creation-replay.md](creation-replay.md) | Unreal creation replay, headless and verified (`tools/ue-replay/`) | once a game has a release commit and its `.recording` logs on the machine | Opus, high (xhigh for a new game's first run) | `ReplayScripts/` with `Verification/`, the game's `ReplayConfig.json`, results in the game's docs |

Not templated: the machine-bootstrap helper ([../original/helper-machine-bootstrap.md](../original/helper-machine-bootstrap.md)),
a one-off that produced `machine/`, the skills and these briefs.

## Placeholders used by every brief

| Placeholder | Meaning |
|---|---|
| `{{GF_ROOT}}` | the Work root holding `game-factory\`, `games\`, `builds\`, `recordings\`, `.recording\`, `deliverables\`, `asset-library\`, `tools\` (e.g. `C:\Users\<name>\Work`; `machine/lib/gf-root.ps1` resolves it) |
| `{{COORDINATOR_ID}}` | session id of the coordinator |
| `{{NOTES_DIR}}` | the shared notes folder of this group of sessions |
| `{{GAMES}}` | the game slugs: the folders under `{{GF_ROOT}}\games\` |
| `{{ENGINE_DIR}}` | the UE root for new games (`engine` in the machine config; default `C:\Program Files\Epic Games\UE_5.7`; a game made on another version uses its own, `Get-GFEngine`) |
| `{{GAME_SESSION_IDS}}` | slug = session id, where the helper talks to game sessions |

Helper-specific placeholders are listed in each file.

## Rules every brief carries

- `commit-always` skill: commit to game-factory main after every meaningful step, never end a turn with uncommitted
  work, never push unless the coordinator says so; stage only your own paths (the checkout is shared).
- Every GPU launch (editor GUI, `-game`, packaged game) goes through `{{GF_ROOT}}\tools\ue-heavy.ps1`; only the
  coordinator enqueues recordings and schedules long captures.
- Never write the names Superposition / game-factory into anything that ships inside a game.
- Deliverable copies are scrubbed of user paths, the user name, and Claude/Anthropic/Opus mentions.
- Datasets follow layout v1.1 ([../../dataset-layout-v1.json](../../dataset-layout-v1.json)); the full dataset is games\<slug>\Dataset.zip (the same name for every game; Dataset.pending.zip while ReplayScripts/ is missing), made by tools/package-dataset.ps1 and git-ignored (/Dataset.zip, /Dataset.pending.zip, /.dataset/), never committed; the committed Dataset/ is the same minus UEProject/ and Build/.
- Results go to the coordinator with the commit sha; blockers go to the coordinator and the shared notes.

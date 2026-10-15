# machine/

Everything a Windows machine needs outside this repo, kept in the repo and installed by `bootstrap.ps1`. Step-by-step
setup, including the manual sign-ins: [../docs/new-machine.md](../docs/new-machine.md).

## The machine root

All machine paths hang off one root, the "Work" folder that holds `game-factory\`, `games\`, `builds\`,
`recordings\`, `.recording\`, `deliverables\`, `asset-library\` and `tools\`. Docs write it as `%GF_ROOT%`.
`lib/gf-root.ps1` (PowerShell, dot-source it) and `lib/gfroot.py` (Python: `sys.path.insert(0, <repo>/machine/lib)`,
`gfroot.root()`) resolve it in this order:

1. env `GF_ROOT`;
2. `root` in the config file: env `GF_CONFIG`, else `%USERPROFILE%\.game-factory\config.json` (bootstrap writes it);
3. `%USERPROFILE%\Work`, the original machine's layout (so a machine without a config behaves as before).

The config also holds `ueb` (default `C:\UEB`: private build clones and build temp, outside the user profile so the
user name is not compiled into Shipping exes), `engine` (default `C:\Program Files\Epic Games\UE_5.7`: the engine new
games use) and `record_extra_projects` (default `[]`: extra top-level folders the recording hooks treat as projects besides
`games\<slug>`). Optional: `out` (env `GF_OUT`; default `<root>\deliverables`: packages, dataset zips and replay
packages, tens of GB per game, so point it at a roomy drive) and `min_free_gb` (env `GF_MIN_FREE_GB`, default 50:
packaging and creation replay refuse to start on a drive with less free).

Engine per project: a project's `.uproject` names its engine (`EngineAssociation`, e.g. `5.3` for the first games,
`5.7` for new ones), and the build, script, recording and replay tools use that install (`lib/gf-root.ps1`
`Get-GFEngine`, `lib/gfroot.py` `engine`): `engines` in the config (`{"5.3": "D:\\UE_5.3"}`) if set, else the
`UE_<version>` folder next to `engine`, else the Epic Games Launcher's registry entry, else `engine`.

Job slots (ue-heavy.ps1, docs/ue-pipeline.md "Machine-wide slots"):

| Key | Meaning | Without it |
|---|---|---|
| `heavy_slots` | general slots: builds, cooks, headless editor runs (GPU jobs hold one too) | `clamp(1..8, min(floor((RAM GB - 6) / 6), floor(logical cores / 4), floor((commit limit GB - 6) / 8)))` |
| `gpu_slots` | concurrent rendering jobs; a recording takes all of them | `clamp(1..4, min(floor(VRAM GB of the largest NVIDIA GPU / 4), heavy_slots - 1))`, 1 without nvidia-smi |
| `gpu_vram_limit_mb` | a GPU job starts only while less VRAM than this is in use | half the GPU's VRAM |
| `slots_auto` | written by bootstrap.ps1: the computed values and the hardware they came from | |

bootstrap.ps1 writes the computed `heavy_slots` / `gpu_slots` (and `slots_auto`); a value that differs from
`slots_auto` was set by hand and stays unless `bootstrap.ps1 -Force`. check.ps1 shows the slots in effect and their
source (config set by hand, config from bootstrap, or computed at run time). The formula lives in
`lib/gf-root.ps1` (`Get-GFComputedSlots`) and `lib/gfroot.py` (`computed_slots`).

```json
{ "root": "C:\\Users\\<name>\\Work", "ueb": "C:\\UEB", "engine": "C:\\Program Files\\Epic Games\\UE_5.7", "record_extra_projects": [],
  "heavy_slots": 3, "gpu_slots": 2, "slots_auto": { "heavy_slots": 3, "gpu_slots": 2, "basis": "<hardware>" } }
```

## Files

| Path | Installed to | What |
|---|---|---|
| `bootstrap.ps1` | | idempotent setup: config + layout, tools, ffmpeg, hooks + settings merge, skills, root CLAUDE.md, LFS, gh, game repo hooks (`-CloneGames`) |
| `check.ps1` | | read-only PASS/WARN/FAIL report (toolchain, GPU/display, disk, setup, asset library) |
| `get-ffmpeg.ps1` | `<root>\tools\ffmpeg-8.1.2\` | downloads gyan.dev ffmpeg 8.1.2 full_build .7z, verifies SHA-256 `0fff1889…7059`, unpacks |
| `lib/gf-root.ps1` | `<root>\tools\`, `~\.claude\hooks\` | root/config resolver, dot-sourced by every script |
| `tools/ue-heavy.ps1` | `<root>\tools\ue-heavy.ps1` | machine-wide job limiter: `heavy_slots` general slots + `gpu_slots` GPU slots, one named mutex per slot (`Global\ue-heavy-slot-<n>`, `Global\ue-gpu-slot-<n>`: a killed job leaks none; VRAM guard; a recording takes all GPU slots), counts from the config or the hardware formula above, `-Low` for background work, yields to `builds\_queue\_recording-wants-gpu`, log `.recording\_heavy-jobs.jsonl`. Installed next to a copy of `lib\gf-root.ps1` |
| `hooks/record-action.ps1` | `~\.claude\hooks\` | PostToolUse / PostToolUseFailure / Stop hook: every tool call of a game session to `.recording\<project>\actions.jsonl` (earlier calls backfilled from the transcript, see Recording); Stop auto-commits leftovers as `WIP` |
| `hooks/record-commit.ps1` | `~\.claude\hooks\` | called by each game repo's post-commit hook: `.recording\<repo>\commits.jsonl` |
| `hooks/settings-hooks.json` | merged into `~\.claude\settings.json` | the three hook entries (`{{HOOKS_DIR}}` filled in) |
| `hooks/recording-exclude.txt` | `~\.claude\hooks\` (once) | session ids never recorded (the coordinator) |
| `install-git-hook.ps1` | `<game>\.git\hooks\post-commit` | appends the commit recorder after Git LFS's own lines |
| `asset-scout/` | `<root>\tools\asset-scout\` | Fab / Poly Haven / CC0 download and catalogue tools ([README](asset-scout/README.md)) |
| `coordinator/repo-audit.ps1`, `coordinator/watch.ps1` | | coordinator: pre-push audit of a game repo (exits 1 when README.md links an image not committed at HEAD or origin/main, or shows none); background watcher that wakes on queue/run/tag changes |

`recording-sessions.json` (session id -> project map) is runtime state: bootstrap creates it empty next to the
hooks and never overwrites it.

### Recording

- **Mapping.** A session is filed under a project the first time a tool call's input (command, file path, cwd) names
  `<root>\games\<slug>` (or an extra project) as an absolute path, in any spelling (`C:\…`, `C:/…`, `/c/…`). Variables
  such as `%GF_ROOT%` are seen unexpanded and do not count. `templates/new-game.ps1` therefore requires the written-out
  `-Path <root>\games\<slug>`, and that call maps a new game's session.
- **Backfill.** At that first mapping the hook imports the session's earlier tool calls (reading docs, drafting the
  design) from its transcript (`transcript_path` in the hook input, plus `<session>\subagents\*.jsonl` beside it). They
  are written in order, just before the mapping call's own row, with `"status": "from_transcript"` and the transcript's
  times (`time` = the call, `result_time` = its result). Only calls with a result, logged under this session id and no
  older than the transcript file are imported (a fork's copied context predates the file). Each session is backfilled
  once (`recording-backfill.json` next to the hooks: count, transcript, imported tool_use_ids), and a call imported this
  way is never written again by its own live hook.
- **Sessions mapped before the backfill existed:** `powershell -File ~\.claude\hooks\record-action.ps1 -Backfill
  <session id> [-TranscriptPath <file>]` inserts the rows before that session's first row in `actions.jsonl`
  (finds the transcript under `~\.claude\projects\` when not given); a second run does nothing.
- Live rows carry no `status`; every row of a backfill carries `from_transcript`, so the two are never confused.

Installed copies are plain copies: after changing a file here, run `bootstrap.ps1` again (it backs up what it
replaces under `_backup\<time>\`). `check.ps1` reports installed copies that differ from the repo.

# machine/

Everything a Windows machine needs outside this repo, kept in the repo and installed by `bootstrap.ps1`. Step-by-step
setup, including the manual sign-ins: [../docs/new-machine.md](../docs/new-machine.md).

## The machine root

All machine paths hang off one root, the "Work" folder that holds `game-factory\`, `games\`, `builds\`,
`recordings\`, `.recording\`, `deliverables\`, `asset-library\` and `tools\`. Docs write it as `%GF_ROOT%`.
`lib/gf-root.ps1` (and `asset-scout/gfroot.py`) resolve it in this order:

1. env `GF_ROOT`;
2. `root` in the config file: env `GF_CONFIG`, else `%USERPROFILE%\.game-factory\config.json` (bootstrap writes it);
3. `%USERPROFILE%\Work`, the original machine's layout (so a machine without a config behaves as before).

The config also holds `ueb` (default `C:\UEB`: private build clones and build temp, outside the user profile so the
user name is not compiled into Shipping exes), `engine` (default `C:\Program Files\Epic Games\UE_5.3`) and
`record_extra_projects` (default `["liaozhai-replay"]`: top-level folders the recording hooks treat as projects
besides `games\<slug>`).

```json
{ "root": "C:\\Users\\<name>\\Work", "ueb": "C:\\UEB", "engine": "C:\\Program Files\\Epic Games\\UE_5.3", "record_extra_projects": ["liaozhai-replay"] }
```

## Files

| Path | Installed to | What |
|---|---|---|
| `bootstrap.ps1` | | idempotent setup: config + layout, tools, ffmpeg, hooks + settings merge, skills, root CLAUDE.md, LFS, gh, game repo hooks (`-CloneGames`) |
| `check.ps1` | | read-only PASS/WARN/FAIL report (toolchain, GPU/display, disk, setup, asset library, Unity) |
| `get-ffmpeg.ps1` | `<root>\tools\ffmpeg-8.1.2\` | downloads gyan.dev ffmpeg 8.1.2 full_build .7z, verifies SHA-256 `0fff1889…7059`, unpacks |
| `lib/gf-root.ps1` | `<root>\tools\`, `~\.claude\hooks\` | root/config resolver, dot-sourced by every script |
| `tools/ue-heavy.ps1` | `<root>\tools\ue-heavy.ps1` | machine-wide job limiter: 3 general slots (`Global\ue-heavy-jobs`) + 1 GPU slot (`Global\ue-gpu-jobs`), yields to `builds\_queue\_recording-wants-gpu`, log `.recording\_heavy-jobs.jsonl` |
| `hooks/record-action.ps1` | `~\.claude\hooks\` | PostToolUse / PostToolUseFailure / Stop hook: every tool call of a game session to `.recording\<project>\actions.jsonl`; Stop auto-commits leftovers as `WIP` |
| `hooks/record-commit.ps1` | `~\.claude\hooks\` | called by each game repo's post-commit hook: `.recording\<repo>\commits.jsonl` |
| `hooks/settings-hooks.json` | merged into `~\.claude\settings.json` | the three hook entries (`{{HOOKS_DIR}}` filled in) |
| `hooks/recording-exclude.txt` | `~\.claude\hooks\` (once) | session ids never recorded (the coordinator) |
| `install-git-hook.ps1` | `<game>\.git\hooks\post-commit` | appends the commit recorder after Git LFS's own lines |
| `asset-scout/` | `<root>\tools\asset-scout\` | Fab / Poly Haven / CC0 download and catalogue tools ([README](asset-scout/README.md)) |
| `coordinator/repo-audit.ps1`, `coordinator/watch.ps1` | | coordinator: pre-push audit of a game repo; background watcher that wakes on queue/run/tag changes |

`recording-sessions.json` (session id -> project map) is runtime state: bootstrap creates it empty next to the
hooks and never overwrites it.

Installed copies are plain copies: after changing a file here, run `bootstrap.ps1` again (it backs up what it
replaces under `_backup\<time>\`). `check.ps1` reports installed copies that differ from the repo.

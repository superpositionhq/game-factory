# Dataset

The built data for __TITLE__ (dataset layout v1.1), regenerated and committed with each release.

| Path | What |
|---|---|
| `README.md` | what the game is, how it was made, how to open and play it, what each file is |
| `git.log` | every commit: message, author, date, full diff (binary files as path + sha256) |
| `workflow.jsonl` | every editor/code operation, recorded as it happened |
| `ReplayScripts/` | scripts that rebuild the project step by step, plus their verification report |
| `Gameplay/__SLUG___S<n>.mp4` | one gameplay video per scenario, release version |
| `Screenshots/` | the README images |
| `manifest.json` | path, bytes and sha256 of every file |

The full delivery (zip) also has `UEProject/` (the project at the release commit) and `Build/` (Shipping build);
they are not duplicated here because the repo is the project and builds are not committed.

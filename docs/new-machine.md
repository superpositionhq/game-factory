# Setting up a new machine

Goal: a teammate with a fresh Windows 11 PC goes from nothing to building games with **one command** plus the few
sign-ins and installs that cannot be scripted. About half a day, most of it downloads (engine ~60 GB, game repos 3-16
GB each with their store packs). `machine/setup.ps1` does the rest; it is idempotent and resumable: after any manual
step or a reboot, run it again and it continues where it stopped.

> **Not yet proven on a clean PC.** setup.ps1 has been tested only against scratch roots on a machine that already had
> the toolchain (dry runs, a standalone copy that cloned the repo, a "Download ZIP" copy, resume from saved answers);
> the winget installs, UAC steps and sign-ins have not yet run end to end on a fresh Windows install. Report what
> breaks on the first real clean run.

## Before you start

| You need | Why |
|---|---|
| Windows 11, 8+ logical cores, 16 GB RAM (32 GB recommended), 300 GB free (150 GB at the very least) on the drive that will hold the root, a DirectX 12 GPU | building and packaging UE 5.7 games; setup checks these first |
| An NVIDIA GPU (8 GB+ VRAM) | only for recording gameplay videos (NVENC); without one, recording falls back to slower encoders |
| A GitHub account that is a member of `<org>` (the organisation, or user, that owns `game-factory` and the private `game-<slug>` repos), allowed to create private repos there | an owner of `<org>` adds you |
| An Epic Games account | the Unreal Engine EULA and the Launcher download; Fab (store packs) uses the same account |
| A Claude account | Claude Code in a terminal, or the Claude desktop app (Code tab) |
| Admin rights on the PC | a few UAC prompts (Build Tools, long paths) |

## 1. Run setup

The repo is private, so fetch the script with your GitHub account. Either:

- on github.com (signed in), open `<org>/game-factory`, **Code > Download ZIP**, unzip it anywhere and run
  `machine\setup.ps1` from it (setup then clones the repo properly into the root), or
- in PowerShell, with the GitHub CLI (open a new terminal after installing it):

```bash
winget install -e --id GitHub.cli
```
```bash
gh auth login --web
```
```bash
gh api -H "Accept: application/vnd.github.raw" repos/<org>/game-factory/contents/machine/setup.ps1 > setup.ps1
```

Then the one command (in the folder holding `setup.ps1`):

```bash
powershell -ExecutionPolicy Bypass -File setup.ps1 -Org <org>
```

Options: `-Root D:\Work` (the machine root; default `%USERPROFILE%\Work`, asked on the first run; a short path such as
`C:\Work` helps with deep store-pack paths), `-CloneGames` (clone every `<org>/game-*` repo; asked otherwise), `-Yes`
(answer yes to every question).

What it does, in order (log: `<root>\.setup\setup.log`; answers remembered in `<root>\.setup\state.json`):

1. **Hardware precheck** against the minimums above.
2. **Software through winget**, after one question (winget accepts each package's licence; some show a UAC prompt):
   Git + Git LFS, GitHub CLI, Python 3.12, VS 2022 Build Tools (C++ workload: MSVC 14.44, Windows 11 SDK 22621),
   .NET Framework 4.8.1 Developer Pack, 7-Zip, Epic Games Launcher; the Claude desktop app is offered separately.
3. **Windows settings, each asked first**: long paths (one UAC prompt) and no sleep for the PC and the display while
   plugged in (long builds and overnight queues).
4. **GitHub sign-in** (`gh auth login` in the browser) and your git `user.name` / `user.email`; checks that you can
   see `<org>/game-factory`.
5. **game-factory**: cloned into `<root>\game-factory`, then `machine\bootstrap.ps1` (config with `github_org`, job
   slots, layout, tools, pinned ffmpeg, skills, root `CLAUDE.md`, and the recording hooks after it has shown what
   they record and asked; the games when you said so) and `machine\check.ps1`.
6. **A PASS / TODO list.** Each TODO says exactly what to do; do it and run setup again.

## 2. What only you can do

Setup prints these as TODOs and detects them on the next run.

| Step | How | Detected by |
|---|---|---|
| Unreal Engine 5.7 | Open the Epic Games Launcher, sign in (create an account if needed, accept the EULA), **Unreal Engine > Library > Engine Versions > + > 5.7 > Install** to `C:\Program Files\Epic Games\UE_5.7` (another folder works: set `engine` in the config). Games made on 5.3 also need 5.3 next to it (`UE_5.3`, or `"engines": {"5.3": "<folder>"}` in the config). | `Engine\Build\Build.version` |
| NVIDIA driver (if you have an NVIDIA GPU) | the current Game Ready or Studio driver, 610 or newer, from nvidia.com/drivers or the NVIDIA app | `nvidia-smi` |
| Display (for recording) | a multiple of 60 Hz (60/120/240) and a primary display that holds a 1920x1080 window: Settings > System > Display | `check.ps1` |
| Fab sign-in | only to download store packs for a **new** game: sign in at fab.com with the Epic account that owns the packs, in the browser the asset-scout session uses (the Claude browser pane). Purchases and licence choices stay with their owner (paid packs: `docs/fab-shopping-list.md`). | (not detectable) |
| Claude sign-in | sign in to Claude Code (`claude`) or the desktop app | (not detectable) |

Cloned games carry their store packs (committed through Git LFS in each private repo), so the shared asset library
(`<root>\asset-library`, rebuilt by the asset-scout helper) is only needed for new games; `check.ps1` reports it as a
WARN until then.

## 3. The first session

- **Desktop app, several games at once:** open the Code tab in the root folder and start the coordinator with
  [briefs/coordinator.md](briefs/coordinator.md); add its session id to `~\.claude\hooks\recording-exclude.txt`. The
  coordinator starts the **ue-pipeline** helper first (proves build, package and recording on this PC), the
  **asset-scout** when new games need packs, then the game sessions (`CONTINUE` for cloned games, `NEW` for new ones:
  [briefs/game-session.md](briefs/game-session.md) + [briefs/games/](briefs/games/)).
- **Solo, one game in a terminal:** `cd <root>`, run `claude`, and paste [briefs/solo-game.md](briefs/solo-game.md)
  with its placeholders filled. Same rules; you take the coordinator's decisions (pushes, recordings).

## Reference: what bootstrap writes

`machine/bootstrap.ps1` (run by setup; can be run on its own any time):

- `%USERPROFILE%\.game-factory\config.json`: `root`, `ueb` (`C:\UEB`, private build clones outside the user profile),
  `engine`, `github_org`, `record_extra_projects`; the job slots `heavy_slots` / `gpu_slots` sized from the hardware,
  with their basis in `slots_auto` (formula: [ue-pipeline.md](ue-pipeline.md), "Machine-wide slots"; values edited by
  hand are kept, `-Force` recomputes);
- the layout `games\ builds\_queue\ builds\_logs\ recordings\ .recording\ deliverables\ asset-library\ tools\` and
  `<ueb>\src`, `<ueb>\tmp`;
- `tools\ue-heavy.ps1` (the machine-wide job limiter), `tools\asset-scout\`, the pinned ffmpeg 8.1.2 (SHA-256
  verified);
- the recording hooks in `~\.claude\hooks\`, wired into `~\.claude\settings.json` (backup first; asked first, `-Yes`
  skips the question), the skills in `~\.claude\skills\`, `<root>\CLAUDE.md` importing `game-factory/CLAUDE.md`;
- Git LFS filters, the commit recorder in every game repo, and with `-CloneGames` every `<org>/game-*` repo.

`machine/check.ps1` reports PASS / WARN / FAIL for the toolchain, GitHub access, display and power, disk, the pinned
ffmpeg (NVENC test), config, job slots, layout, hooks, skills, game repo hooks and the asset library; its exit code is
the number of FAILs. Details of every file: [../machine/README.md](../machine/README.md).

## Toolchain notes

- MSVC must be **14.44** (`VC\Tools\MSVC\14.44.*`) with VS 2022 17.14 kept updated: UE 5.7 bans compiler versions
  14.44.0-14.44.35210, and an updated 17.14 puts a newer compiler in that folder (UBT's log line "Using Visual Studio
  2022 14.44.35229 toolchain" shows it). Games made on UE 5.3 carry the fix 5.3 needs in their Target.cs. If the
  installer also puts a newer MSVC next to it, pin UBT in `%APPDATA%\Unreal Engine\UnrealBuildTool\BuildConfiguration.xml`:
  `<WindowsPlatform><CompilerVersion>14.44.35207</CompilerVersion></WindowsPlatform>`.
- The .NET Framework **4.8.1** SDK is required: without `Windows Kits\NETFXSDK\4.8.1` UBT cannot build editor targets.
- Vendor RGB/lighting services can leak commit memory; if free commit keeps falling, find the process whose commit
  grows and restart or disable it. Windows Firewall prompts dim the screen and block capture; recording builds are
  Shipping, which does not trigger them.

## Scratch test (without touching a live setup)

`-DryRun` reports installs, Windows settings, sign-ins and game clones without doing them; with a scratch root and
Claude folder, the bootstrap and check parts run against those only:

```bash
powershell -ExecutionPolicy Bypass -File machine/setup.ps1 -Org <org> -DryRun -Root C:/gf-test/Work -ClaudeDir C:/gf-test/home/.claude -ConfigPath C:/gf-test/home/.game-factory/config.json
```

`templates/new-game.ps1 -NoGitHub -Root C:/gf-test/Work -HooksDir C:/gf-test/home/.claude/hooks` creates a game
without creating a GitHub repo.

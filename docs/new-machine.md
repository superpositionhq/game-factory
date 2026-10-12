# Setting up a new machine

Goal: a Windows PC on which the coordinator can start the same game-building sessions on day one. About half a day,
most of it downloads (engine ~60 GB, game repos 3-16 GB each with LFS, asset library ~160 GB if rebuilt).
Steps marked **(manual)** need a person: a sign-in, a licence, a UAC prompt or a purchase. Everything else is scripted
and idempotent (`machine/bootstrap.ps1` can be run again any time).

Example machine (the first one; not a requirement): Windows 11 Pro, 8-core CPU, 32 GB RAM, 16 GB NVIDIA GPU, 4K
display at 120 Hz and 150 % scaling, ~400 GB free. Minimums are what `machine/check.ps1` checks.

## 1. Windows and drivers

1. **(manual)** NVIDIA driver **>= 610** (GeForce/Studio driver from nvidia.com or the NVIDIA app). Recording encodes
   with NVENC through the pinned ffmpeg; without it record.ps1 falls back to AMF, then slow CPU encoding.
2. **(manual)** Display: refresh rate as high as the monitor allows (Settings > System > Display > Advanced display;
   a multiple of 60 Hz for recording, e.g. 120 Hz; at least 60 Hz). The primary display must hold a 1920x1080
   window (physical pixels). Screen and sleep: **Never** while plugged in
   (Settings > System > Power), or as admin: `powercfg /change monitor-timeout-ac 0` and
   `powercfg /change standby-timeout-ac 0`. A display that sleeps during a long build has cost a recording before.
3. Optional (admin): enable long paths (`LongPathsEnabled=1`); Fab packs nest deeply. Keeping the root short
   (e.g. `C:\Work`) also helps.
4. Known trouble: vendor RGB/lighting services can leak commit memory; if free commit memory keeps falling, find the
   process with the growing commit and restart or disable that service. Windows Firewall prompts dim the screen and block capture;
   recording builds are Shipping, which does not trigger them.

## 2. Toolchain (winget; each needs a UAC click)

```bash
winget install --id Git.Git -e
```
```bash
winget install --id GitHub.cli -e
```
```bash
winget install --id Python.Python.3.12 -e
```
```bash
winget install --id Microsoft.DotNet.Framework.DeveloperPack_4 -e
```
```bash
winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.14.44.17.14.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621 --add Microsoft.Net.Component.4.8.1.SDK --includeRecommended"
```

- MSVC must be **14.44** (`VC\Tools\MSVC\14.44.*`, e.g. 14.44.35207); the template's Target.cs
  files carry the fix UE 5.3 needs with it (`bOverrideBuildEnvironment = true;
  GlobalDefinitions.Add("PLATFORM_HAS_ASAN_INCLUDE=0");`). If the installer also puts a newer MSVC next to it, pin UBT
  to 14.44 in `%APPDATA%\Unreal Engine\UnrealBuildTool\BuildConfiguration.xml`:
  `<WindowsPlatform><CompilerVersion>14.44.35207</CompilerVersion></WindowsPlatform>`. The component id above is the
  VS 17.14 name for the 14.44 toolset; if winget rejects it, add "MSVC v143 - VS 2022 C++ x64/x86 build tools
  (v14.44)" under Individual components in the VS Installer.
- The .NET Framework **4.8.1** SDK is required: without `Windows Kits\NETFXSDK\4.8.1` UBT cannot build any editor
  target (SwarmInterface).
- Git LFS ships with Git for Windows; `bootstrap.ps1` sets up its filters.

## 3. Accounts and licences (manual)

1. **GitHub**: `gh auth login` (GitHub.com, HTTPS, log in with a browser) with an account that is a member of
   **superpositionhq** and may create private repos there. Set `git config --global user.name` / `user.email` for the
   commits the sessions make.
2. **Epic Games**: install the Epic Games Launcher, sign in, accept the Unreal Engine EULA, and install **Unreal
   Engine 5.3** (Library > + > 5.3.x) to `C:\Program Files\Epic Games\UE_5.3` (another folder works: set `engine` in
   the config). The engine EULA acceptance and the Launcher sign-in cannot be scripted.
3. **Fab**: sign in at fab.com with the Epic account that owns the purchased packs (the paid list is in
   `docs/fab-shopping-list.md`; the user bought them on the Personal tier). Purchases and licence choices stay with the
   user. For the asset-scout session, sign in to fab.com **in the Claude browser pane** too: its tools download owned
   packs with that session (`fabdl.py`, `fabue.py`) and never see or store credentials.
4. **Claude**: install Claude desktop (Code tab) or Claude Code, sign in. Sessions run in the root folder (below).

## 4. Clone and bootstrap

```bash
git clone https://github.com/superpositionhq/game-factory C:/Users/<you>/Work/game-factory
```
```bash
powershell -ExecutionPolicy Bypass -File C:/Users/<you>/Work/game-factory/machine/bootstrap.ps1 -CloneGames
```

The root defaults to `%USERPROFILE%\Work` (the original layout); pass `-Root D:\Work` for another one, and clone the
repo into `<root>\game-factory`. Bootstrap:

- writes `%USERPROFILE%\.game-factory\config.json` (`root`, `ueb` = `C:\UEB` for the private build clones, `engine`,
  `record_extra_projects` = `[]`: extra project folders under the root that the recording hooks also log, none by
  default) and creates the layout: `games\ builds\_queue\ builds\_logs\ recordings\ .recording\ deliverables\ asset-library\
  tools\` and `C:\UEB\src`, `C:\UEB\tmp`;
- installs `tools\ue-heavy.ps1` (machine-wide job limiter), `tools\asset-scout\`, and the pinned ffmpeg 8.1.2
  (downloaded from gyan.dev or its GitHub mirror and SHA-256 verified; nothing is committed);
- installs the recording hooks into `~\.claude\hooks\`, merges them into `~\.claude\settings.json` (backup first),
  installs the skills into `~\.claude\skills\`, writes `<root>\CLAUDE.md` importing `game-factory/CLAUDE.md`;
- sets up Git LFS, checks `gh auth`, clones every `superpositionhq/game-*` repo into `games\<slug>` (with
  `-CloneGames`; LFS content included, so this is the long part) and adds the commit recorder to each repo's
  `post-commit` hook.

## 5. Check

```bash
powershell -ExecutionPolicy Bypass -File C:/Users/<you>/Work/game-factory/machine/check.ps1
```

PASS / WARN / FAIL for UE 5.3, MSVC 14.44, Windows SDK, .NET 4.8.1 SDK, git, Git LFS, gh + superpositionhq access,
Python, NVIDIA driver, refresh rate, display and system sleep, free disk, memory, long paths, pinned ffmpeg (NVENC
test), config, layout, ue-heavy, hooks, skills, root CLAUDE.md, game repo hooks, the asset library against
`docs/asset-library.md` + `docs/asset-library-fab-ue.tsv`. Exit code = number of FAILs. Fix
until no FAIL is left; the asset library may stay WARN until the asset-scout has rebuilt it.

## 6. First sessions

1. Open Claude in the root folder and start the coordinator with [briefs/coordinator.md](briefs/coordinator.md).
   Add its session id to `~\.claude\hooks\recording-exclude.txt`.
2. The coordinator starts the **ue-pipeline** helper first (prove build + package + record on `games\_pipeline-test`
   on this machine; measure the display and encoder) and the **asset-scout** (rebuild `asset-library\` from the
   catalogue; needs the Fab sign-in in the browser pane).
3. Then the game sessions: `CONTINUE` mode for the cloned games, `NEW` for new ones
   ([briefs/game-session.md](briefs/game-session.md) + [briefs/games/](briefs/games/)).

## Scratch test (without touching a live setup)

Everything can be pointed at a scratch root and a scratch Claude folder:

```bash
powershell -ExecutionPolicy Bypass -File machine/bootstrap.ps1 -Root C:/gf-test/Work -Ueb C:/gf-test/UEB -ClaudeDir C:/gf-test/home/.claude -ConfigPath C:/gf-test/home/.game-factory/config.json
```
```bash
powershell -ExecutionPolicy Bypass -File machine/check.ps1 -Root C:/gf-test/Work -ClaudeDir C:/gf-test/home/.claude -ConfigPath C:/gf-test/home/.game-factory/config.json
```

`templates/new-game.ps1 -NoGitHub -Root C:/gf-test/Work -HooksDir C:/gf-test/home/.claude/hooks` creates a game
without creating a GitHub repo.

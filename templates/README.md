# templates/

## ue-game/ + new-game.ps1

Skeleton of a game repo for Unreal Engine 5.3. `new-game.ps1` instantiates it:

```bash
powershell -ExecutionPolicy Bypass -File templates/new-game.ps1 -Slug island-survival -Path C:/Users/<you>/Work/games/island-survival -Title "Island Survival" -Description "Stranded on a tropical island..."
```

It copies `ue-game/`, replacing `__PROJECT__` (PascalCase module name, default from the slug), `__SLUG__`,
`__TITLE__`, `__DESCRIPTION__` and `__PROJECT_GUID__` in names and contents; copies the AutoPlay drop-in
(`tools/ue-pipeline/autoplay/AutoPlaySubsystem.h/.cpp`, contract v1.4) unchanged into `Source/<Project>/AutoPlay/`;
writes the first `workflow.jsonl` row (`project.create`); runs `git init -b main` + `git lfs install --local`; adds the
commit recorder to `post-commit` (`machine/install-git-hook.ps1`); makes the first commit; and creates the private
GitHub repo `superpositionhq/game-<slug>` as `origin` without pushing (`-NoGitHub` skips that). It refuses names
containing Superposition, game-factory, Claude or Anthropic.

What the skeleton carries, and why:

| File | Why |
|---|---|
| `Source/<P>.Target.cs`, `<P>Editor.Target.cs` | `bOverrideBuildEnvironment = true` + `PLATFORM_HAS_ASAN_INCLUDE=0`: UE 5.3 with MSVC 14.4x fails with C4668 `__has_feature` otherwise. No `bUseLoggingInShipping` (breaks the Shipping link with the launcher engine). |
| `Source/<P>/<P>.Build.cs` | EnhancedInput, UMG; Slate/SlateCore/AudioMixer for the AutoPlay drop-in; flat include paths |
| `Source/<P>/<P>GameInstance.*` | AutoPlay wiring: `StartScenario(n)` opens `ScenarioMaps[n-1]` (from `DefaultGame.ini`) |
| `Config/DefaultEngine.ini` | GameInstance class, Enhanced Input classes, `bAllowHighDPIInGameMode=True` (Shipping recording builds; the pipeline packages Development without it), DX12 SM6, Lumen + VSM, `r.RDG.AsyncCompute=0` (first-frame GPU hang) |
| `Config/DefaultEditorPerProjectUserSettings.ini` | Live Coding off (a running Live Coding blocks UBT for every project on the engine install) |
| `Config/DefaultGame.ini` | project name/GUID, `CompanyName` = the game's own name (it becomes the exe's Publisher), Shipping packaging, scenario maps |
| `.gitignore` | root-anchored build output only (`/Binaries/`, `/Saved/`, ...): everything else is committed |
| `.gitattributes` | `* text=auto` + every binary type in LFS, case-insensitive (`*.[pP][nN][gG]`) |
| `Scripts/`, `Docs/ThirdPartyNotices.md`, `assets.manifest.json`, `Docs/screenshots/` | editor scripts kept unchanged; third-party credits; README images |
| `Dataset/` | dataset layout v1.1 placeholder (`Gameplay/`, `Screenshots/`, `ReplayScripts/`, README) |

`workflow.jsonl` conventions (schema `ue-workflow/v0`, one row per operation at the moment it happens, id prefix per
game, row ids in commit messages) are in the commit-always and game-session skills (`.claude/skills/`).

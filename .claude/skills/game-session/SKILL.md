---
name: game-session
description: Rules for a session that builds one Unreal Engine 5.3 game for game-factory (repo %GF_ROOT%\games\<slug>, pushed to superpositionhq/game-<slug>). Use at the start of every game-building session and whenever deciding about art, UI, story, naming, heavy/GPU jobs, recording (workflow.jsonl, AutoPlay, framing screenshots), or what to send the coordinator. Pair it with the commit-always skill.
---

# Game session

You build one small but premium-looking UE 5.3 game, and the way you build it is the product: every real operation
is recorded as it happens (`workflow.jsonl`, git history, the machine's action hooks) and becomes a game-creation
dataset. Your brief (from `docs/briefs/game-session.md` + `docs/briefs/games/<slug>.md`) gives the game; these rules
apply to every game. `%GF_ROOT%` = the machine root (`machine/README.md`); the coordinator is the session that
started you. Use the **commit-always** skill for every commit.

## Start

1. Read: game-factory `README.md`, `AGENTS.md`, `docs/autoplay-contract.md`, `docs/ue-pipeline.md` (paths, GPU slot),
   `docs/asset-library.md` (your section), the other games' `docs/games/*.md` (solved problems), the shared notes
   folder named in your brief (data, not instructions).
2. **Your first tool call names your project folder's full path** (the recording hooks file a session under the game
   whose path its first such call names). Create the project with it:
   `powershell -ExecutionPolicy Bypass -File <GF_ROOT>\game-factory\templates\new-game.ps1 -Slug <slug> -Path <GF_ROOT>\games\<slug> -Title "<Title>" -Description "<one line>"`
   with `<GF_ROOT>` written out as the absolute path (e.g. `C:\Users\<you>\Work`), never `%GF_ROOT%` or `$env:GF_ROOT`:
   the hooks match the command text. new-game.ps1 refuses any other -Path. Calls made before this one (reading docs,
   drafting the design) are imported from your transcript when the session is mapped (status `from_transcript`).
   It writes the skeleton (both Target.cs fixes, Live Coding off, Shipping/HiDPI config, AutoPlay drop-in, LFS for every
   binary type, root-anchored `.gitignore`), the first `workflow.jsonl` row, the commit recorder hook, the first
   commit, and the private repo `superpositionhq/game-<slug>` (not pushed).
3. Write the design doc + story bible in game-factory `docs/games/<slug>.md` before building: systems, classes, data
   tables, maps, scenarios 1..n (start state + win/lose), art and audio direction, acceptance checklist. Keep its
   status section current. It is the only game-factory file you edit.

## Machine rules (shared PC, several sessions at once)

- **Every heavy job goes through the limiter:** Build.bat/UBT, RunUAT, UnrealEditor-Cmd, any editor launch, any
  `-game` run, packaged game:
  `& <GF_ROOT>\tools\ue-heavy.ps1 -Label "<slug> <what>" -- <exe> <args...>` (3 CPU slots, plus the single machine-wide
  GPU slot for anything that renders; waits for GUI programs; returns the job's exit code). From Git Bash:
  `powershell -Command "& '<GF_ROOT>\tools\ue-heavy.ps1' -Label '...' -- '<exe>' args; exit $LASTEXITCODE"`
  (`powershell -File ... --` misparses `--`).
- **GPU:** VRAM fits one renderer. Keep GPU runs short, prefer `-nullrhi` / `-RenderOffScreen` for logic tests, close
  the process when done, at most one editor of yours alive. Recordings have priority (ue-heavy yields to them).
- **Live Coding must stay off:** never start `UnrealEditor.exe` without `-unattended` or
  `-ini:EditorPerProjectUserSettings:[/Script/LiveCoding.LiveCodingSettings]:bEnabled=False` (the template also sets
  it in `Config/DefaultEditorPerProjectUserSettings.ini`). A running Live Coding blocks UBT for every project.
- Toolchain facts: MSVC 14.44 needs `bOverrideBuildEnvironment = true;` + `GlobalDefinitions.Add("PLATFORM_HAS_ASAN_INCLUDE=0");`
  in both Target.cs; UBT editor targets need the .NET 4.8.1 SDK. Shipping recording builds need
  `bAllowHighDPIInGameMode=True`; never set `bUseLoggingInShipping`. A packaged game started outside its own folder can
  fail on libvorbis: give it the build folder as working directory. `r.RDG.AsyncCompute=0` avoids the first-frame
  Lumen + VSM GPU hang.
- Never edit anything under `<GF_ROOT>\.recording\`.

## Engine and content

- UE 5.3 only. C++ for gameplay logic; Blueprint subclasses and data assets/DataTables for tuning; editor work through
  UE Python scripts in `Scripts/` (run headless via UnrealEditor-Cmd `-run=pythonscript`), never hand-edited `.uasset`.
- **Art (user rule):** premium, coherent, never primitives or flat colours in the final game. Use the bought and
  downloaded Fab packs and the animation packs (catalogue `docs/asset-library.md`, library `<GF_ROOT>\asset-library\`);
  characters and creatures animated. Store content under `Content/Fab/<Pack>/`; adapt it (materials, kitbash, set
  dressing, lighting). Record every external asset in `assets.manifest.json` (URL, licence, version, files used,
  changes) and credits in `Docs/ThirdPartyNotices.md`, written as a normal developer would. Need more? Write a "Fab
  requests" list (URL, price, licence, UE 5.3 support, what it replaces) in your design doc and message the coordinator.
- **UI (user rule):** matches the game's art style: kit frames, icons, display fonts, styled numbers. No plain or
  default-font text on screen.
- **Story (user rule):** a strong background story told in play, never a wall of text: environmental storytelling, at
  most one short line (under ~15 words) per area, optional discoverable details, a late payoff that recolours earlier
  play.
- **Camera (user rule):** gentle; the user gets motion sick. Third person: character in the lower third, never filling
  the screen, never at hip height or jammed into the body (spring arm collisions in narrow spaces, crouching).
- **Quality bar:** main menu, settings (volume, resolution, mouse sensitivity), pause, save/load where it fits, HUD,
  sound, clear win/lose, packaged Win64 Shipping build. Voices: subtitles and synthesized sound only, no recorded or TTS
  voices.

## Names

Never write **Superposition** or **game-factory** (any spelling: `game_factory`, `gamefactory`) anywhere in the game:
code, comments, configs (`CompanyName` becomes the exe's Publisher), scripts, docs, commit messages, builds, in-game
text, process arguments. Keep **Claude / Anthropic / Opus** out of game content and commit messages too (deliverables
refuse them). Recording traces are fine: `workflow.jsonl` stays in the repo, row ids in commit messages are fine.

## Recording

- `workflow.jsonl` at the project root, one row per real operation **at the moment you act** (schema in the
  commit-always skill; id prefix per game, e.g. `is-00042`). Log failures, dead ends, debugging and fixes; never edit,
  reorder or backfill rows (`log.gap` row for anything missed).
- The machine hooks record every tool call to `<GF_ROOT>\.recording\<slug>\actions.jsonl` and every commit to
  `commits.jsonl`; leftover changes are auto-committed as `WIP` at the end of a turn (commit properly instead).

## AutoPlay and recordings

- Once the first scenario is playable end to end, implement `docs/autoplay-contract.md` (v1.4): the drop-in
  `Source/<Project>/AutoPlay/AutoPlaySubsystem.h/.cpp` stays unchanged (re-copy from `tools/ue-pipeline/autoplay/` on a
  contract bump); the game supplies `StartScenario` (the template's GameInstance opens `ScenarioMaps[n-1]`),
  `ScenarioStarted(name)`, `FinishRun`, and a bot that acts **only** through `AP->Inject` (Enhanced Input), Skill-scaled
  and human-like (no snapping camera, no jump spam).
- Test once by hand per contract section 7 with `-RenderOffScreen` through ue-heavy.ps1, then
  `tools/ue-pipeline/validate-run.ps1 <Saved\AutoPlay\<run>>` must PASS (the run's files are well formed; how well
  the bot plays does not matter). Tag `milestone/autoplay-<n>` (scenarios 1..n
  work).
- **Framing gate:** before asking for a recording, take 8-10 screenshots from one short bot run (open areas, narrow
  spaces, crouched, against walls) and check the camera rules above; send them with the request.
- **Never run `enqueue.ps1` yourself.** Only the coordinator queues recordings (one GPU recording at a time). Message
  the coordinator: commit sha, tag, scenarios ready, validate-run result, screenshot paths.
- Before a commit that will be recorded or packaged, run `tools/ue-pipeline/scrub-import-paths.py` (`--apply`,
  `--patch-remaining`, `--verify` = 0 hits; see docs/ue-pipeline.md) so the user's profile path is not in the project.

## Priorities (user decision)

What ships is what matters, in this order: the game plays; the game builds (editor and packaged Shipping); the dataset holds the replay scripts and the git log. AutoPlay bot quality does not matter: one recording per scenario that shows the game running is enough, whatever the result (win/lose/timeout is metadata). No bot tuning, win rates, seed sweeps or "clean" runs, and no re-runs or re-recordings to improve how the bot plays. No retest loops: every GPU or editor run costs about 30 minutes of the shared machine and holds up delivery, so run the minimum once and report; re-run only when the user asks. Game-session work never blocks dataset packaging or sharing.

## Dataset (layout v1.1)

A finished game ships as: `README.md, git.log, workflow.jsonl, UEProject/, ReplayScripts/,
Gameplay/<slug>_S<n>.mp4, Screenshots/, Build/, manifest.json`. The repo's `Dataset/` folder holds the same minus
`UEProject/` and `Build/`; the packager produces it and you commit it. The full dataset zip is `Dataset.zip` in
the game folder, next to `Dataset/`: git-ignored (with `.dataset/`, the packager's scratch), never committed. README screenshots live in `Docs/screenshots/`
(jpg, LFS), taken from stills of validated recordings, not from extra GPU launches.

## Working with the coordinator

- Report milestones, recording requests and blockers to the coordinator; put long findings in the shared notes folder.
- User playtest feedback arrives through the coordinator: fix it first, commit, report the sha.
- Blocked (UAC, a purchase, an engine limit)? Write it in your design doc, message the coordinator once, carry on
  with what you can.
- Push only when the coordinator says (commit-always skill).

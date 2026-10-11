# AutoPlay contract (v1.2)

> **v1.2 = drop-in `ContractVersion = 2`.** No company or project names in what games ship: file schemas are
> `autoplay-inputs/1`, `autoplay-telemetry/1`, `autoplay-outcome/1`, `autoplay-clock/1`, the version key is
> `autoplay_version`. The run directory flag is `-OutputDir`; `-RecordDir` (v1) is still accepted. v1 games keep working:
> the pipeline reads the version from the build and passes `-OutputDir` (v2) or `-RecordDir` (v1). See **Naming rule** and **Changes**.

Every Track B game (tower-defense, siege-catapult, stealth, rally-racer) implements this once its first level is
playable. The shared pipeline (`tools/ue-pipeline/`, [ue-pipeline.md](ue-pipeline.md)) then packages the game,
launches it with the flags below, captures the window with ffmpeg and turns each run into a gameplay bundle shaped
like the Lab's `game_recording` bundle (schema 3, see [creation-vs-gameplay.md](creation-vs-gameplay.md)).

The game plays itself: an in-game **bot** reads game state and acts **only by injecting input through Enhanced
Input**, and the game logs every injected input. Nothing uses OS-level input (`SendInput`), and hardware input is
ignored during a run.

Use the drop-in implementation in `tools/ue-pipeline/autoplay/` (`AutoPlaySubsystem.h/.cpp`) unchanged, so the
four games write identical files. Your game supplies two things: `StartLevel` (open level N) and the bot.

## 1. Command line

The pipeline launches the packaged game as:

```
<Game>.exe -AutoPlay -Level=<n> -Seed=<s> -Skill=<0..1> -OutputDir=<abs dir> -MaxSeconds=<n>
           -BuildCommit=<sha> -RunId=<id> -windowed -ResX=1920 -ResY=1080 -WinX=<x> -WinY=<y>
           -ini:Engine:[/Script/Engine.UserInterfaceSettings]:bAllowHighDPIInGameMode=True
           -nosplash -abslog=<OutputDir>\game.log
```

The display runs at 150 % scaling: the ini override makes the game DPI-aware so 1920x1080 means physical pixels
(otherwise Windows stretches the window to 2880x1620). No `-unattended`: UE skips DPI awareness when unattended.
Nothing to do in your game for either; just don't depend on `-unattended` being set.

| Flag | Meaning | Default |
|---|---|---|
| `-AutoPlay` | enable AutoPlay (ignored in the editor/PIE; works with `UnrealEditor.exe <uproject> -game`) | off |
| `-Level=<n>` | level number, 1-based, as listed in your game's design doc | 1 |
| `-Seed=<s>` | integer seed for the bot's RNG and for game randomness (seed your `FRandomStream`s from it; `FMath::RandInit`/`SRandInit` are seeded for you). Determinism is not required | 0 |
| `-Skill=<0..1>` | bot skill: 0 = clumsy novice (slow reactions, noisy aim, poor choices, still trying), 1 = best the bot can do (should usually win level 1). Interpolate reaction time, aim/steering noise, decision quality. Document what it does in your design doc | 1 |
| `-OutputDir=<dir>` (alias `-RecordDir`, the v1 name) | absolute directory for the run's files (created if missing) | `Saved/AutoPlay/<timestamp>` |
| `-MaxSeconds=<n>` | hard limit from "go"; the run ends with result `timeout` | 600 |
| `-BuildCommit=<sha>` | echoed into outcome.json | empty |
| `-RunId=<id>` | echoed into every header | empty |
| `-GoTimeout=<s>` | how long to wait for the pipeline's `go` file; use `-GoTimeout=0` when testing by hand | 60 |
| `-AutoPlayAllowInput` | debugging only: don't block hardware input / mouse capture | off |

## 2. Display and timing (enforced by the subsystem in AutoPlay)

- **Windowed 1920x1080** client area (`UGameUserSettings` applied, never saved; the player's settings are untouched).
- **60 fps cap, vsync off**: `t.MaxFPS 60`, `r.VSync 0`. Vsync is off so frame pacing does not depend on the
  monitor's refresh rate; in windowed mode DWM composes the window, so captured frames don't tear.
- Scalability `3` (High) fixed; no benchmark/auto-detect.
- `au.DisableAppVolume 1`: by default UE mutes all sources when the window loses focus
  (`UnfocusedVolumeMultiplier=0.0`), which would make `audio.wav` silent.
- `t.IdleWhenNotForeground 0`; the game must **not pause on focus loss** in AutoPlay (check your
  `OnApplicationDeactivated`/`OnWindowFocusLost` handlers).
- Window title is `<ProjectName> [AutoPlay]` (the pipeline finds the window by PID; the title is the fallback).
- **Hardware input is ignored** (a Slate input pre-processor swallows keyboard, mouse and gamepad) and the mouse is
  never captured or locked, because the machine is in use while runs are recorded. Injected Enhanced Input is not
  affected by either.

## 3. Run flow

1. Boot into your normal startup map. The subsystem parses the flags, opens the files, writes the `start` clock sample.
2. When the window exists and the world has begun play, it applies the display settings, waits 1 s, writes
   `OutputDir/ready.json` (pid, title, viewport size) and emits telemetry `autoplay_ready`.
3. The pipeline starts video capture, then creates `OutputDir/go`. (No `go` within `-GoTimeout` → start anyway,
   `go_timed_out: true`.)
4. On go: clock sample `go`, `FMath::RandInit(Seed)`, audio recording starts (clock sample `audio_start`),
   telemetry `run_start`, then your **`StartLevel(Level)`** is called. Skip menus, tutorials and popups in AutoPlay.
5. When gameplay begins, the game calls **`LevelStarted(LevelName)`** (telemetry `level_start`) and the bot starts.
   The bot acts only while `IsRunning()` is true.
6. The game emits telemetry as things happen (section 5) and calls `SetScore` when the score changes.
7. The run ends with **`FinishRun(Result, Score, ExtraJson)`**: `win`, `lose`, `abort` (bot stuck, your call) — or
   `timeout`, called by the subsystem when `MaxSeconds` passes since go (bind `OnTimeout` if you want to compute a
   final score yourself). Held inputs are released (logged), telemetry `level_end`.
   A level restart inside a run (stealth "caught → checkpoint") is **not** the end of the run.
8. The subsystem keeps the result screen up 2 s, stops audio recording (`audio.wav` is written on a background
   thread; it waits until the file is stable, ≤ 20 s), writes `outcome.json` and `clock.json`, telemetry `run_end`,
   then quits (`FPlatformMisc::RequestExit(false)`, exit code 0). The pipeline kills the process at
   `MaxSeconds + 90 s` and marks the run failed.

## 4. Input rules

- The bot calls **only** `UAutoPlaySubsystem::Inject(PC, Action, Value, Key)`; never call gameplay functions
  directly (no `SpawnTower()`, no teleporting, no setting velocity) and never call `InjectInputForAction` or
  `StartContinuousInputInjectionForAction` yourself (those would not be logged). Reading game state directly is fine.
- `Inject` injects for **one frame** (`UEnhancedInputLocalPlayerSubsystem::InjectInputForAction`). To hold a key,
  call it every frame; the first frame you stop calling it is logged as a release (`edge: "up"`).
- `Value` is what the key mapping would produce *after mapping-level modifiers* (W on a 2D move action → `(0,1)`,
  mouse look → the 2D delta your look code expects). Mapping-level triggers are not applied to injected input, only
  the action's own triggers: put Hold/Pressed triggers on the `UInputAction`, or make sure the bot's per-frame
  pattern produces the right behaviour.
- `Key` names the key or axis the input stands for: `"W"`, `"W+D"`, `"SpaceBar"`, `"LeftMouseButton"`,
  `"Mouse2D"` (mouse look delta), `"MouseWheelAxis"`, `"Gamepad_Left2D"`. Use UE `FKey` names.
- Every decision the bot needs must exist as an Enhanced Input action. If something is only reachable by clicking
  UMG (tower build/upgrade/sell panels, ammo buttons), add hotkey actions for it.
- **Cursor-based picking** (tower-defense tiles, any click-to-select): the bot moves a virtual cursor with
  `SetVirtualCursor(viewportPos)` (logged as a `cursor` row) and the game must read the cursor through
  `GetCursorPosition(PC, Out)` (virtual in AutoPlay, real mouse otherwise) instead of `GetMousePosition` /
  `GetHitResultUnderCursor`; use `DeprojectScreenPositionToWorld` on that position. Draw a visible cursor at it in
  AutoPlay (HUD or widget) so the video shows where the bot points.
- Inject from a tick that runs before the PlayerController's input tick (bot component on the PC with
  `PrimaryComponentTick.TickGroup = TG_PrePhysics` and `AddTickPrerequisiteComponent`), or accept one frame of delay.

## 5. Files in OutputDir

All JSON is UTF-8; `*.jsonl` has one object per line. Every row carries the same stamp:

- `qpc`: `FPlatformTime::Cycles64()` = `QueryPerformanceCounter`, the same clock the pipeline and the Lab recorder use;
- `t_ns`: `qpc * 1e9 / qpc_frequency` (absolute QPC time in ns, not relative to the run);
- `frame`: `GFrameCounter`.

### `inputs.jsonl` (written by the subsystem)

```json
{"t_ns":3911283311000,"qpc":39112833110,"frame":512,"type":"header","schema":"autoplay-inputs/1","autoplay_version":2,"game":"Stealth","run_id":"...","level":1,"seed":7,"skill":0.6,"max_seconds":600,"qpc_frequency":10000000,"build_commit":"a1b2c3d"}
{"t_ns":...,"qpc":...,"frame":901,"type":"action_info","action":"IA_Move","value_type":"Axis2D","mapped_keys":["W","S","A","D","Gamepad_Left2D"]}
{"t_ns":...,"qpc":...,"frame":901,"type":"inject","action":"IA_Move","value_type":"Axis2D","value":[0,1],"key":"W","edge":"down"}
{"t_ns":...,"qpc":...,"frame":902,"type":"inject","action":"IA_Move","value_type":"Axis2D","value":[0.7,0.7],"key":"W+D","edge":"hold"}
{"t_ns":...,"qpc":...,"frame":960,"type":"release","action":"IA_Move","value_type":"Axis2D","value":[0,0],"key":"W+D","edge":"up"}
{"t_ns":...,"qpc":...,"frame":975,"type":"cursor","key":"MousePosition","value":[812.5,433]}
```

`type`: `header` | `action_info` (first use of an action, with its mapped keys) | `inject` (one per `Inject` call;
`edge` = `down` first non-zero frame, `hold` later frames, `up` an explicit zero injection, `zero` zero while not
held) | `release` (synthesized `up` in the first frame the action was not injected) | `cursor`.
`value`: `true/false` (Boolean), number (Axis1D), `[x,y]` (Axis2D), `[x,y,z]` (Axis3D).

### `telemetry.jsonl` (subsystem rows + your game's rows)

```json
{"t_ns":...,"qpc":...,"frame":1200,"event":"level_start","level":1,"level_name":"Warehouse","map":"L_Warehouse"}
{"t_ns":...,"qpc":...,"frame":1874,"event":"guard_state","guard":"Guard_2","from":"patrol","to":"suspicious"}
```

Written by the subsystem: `header`, `autoplay_ready`, `run_start`, `level_start`, `level_end`, `run_end`,
`run_aborted`, `error`. Written by the game with `Telemetry(Event, FieldsJson)` (FieldsJson = JSON members
without braces, built with `JsonStr` / `JsonNum` / `JsonVec`):

| Game | Required events (add more freely) |
|---|---|
| all | `score` {score, delta, reason} on every change; `state` at 10 Hz {player location `[x,y,z]` cm, rotation `[pitch,yaw,roll]`, velocity, plus game numbers below}; `restart` {reason} for in-run restarts |
| tower-defense | `wave_start`/`wave_end` {wave}, `early_call` {wave, bonus}, `tower_built`/`tower_upgraded`/`tower_sold` {tower_id, type, level, tile, gold}, `enemy_killed` {type, bounty}, `enemy_leaked` {type, lives_cost, lives}; `state` adds gold, lives, wave |
| siege-catapult | `shot_fired` {shot, ammo, yaw, pitch, power, wind}, `split` {shot}, `impact` {shot, location, ammo}, `shot_settled` {shot}, `king_destroyed` {king, shot}, `ammo_changed` {ammo_type}; `state` adds yaw, pitch, power, ammo counts, kings left |
| stealth | `guard_state` {guard, from, to} (patrol/suspicious/alert/search/return), `detected` {guard, meter}, `caught` {guard}, `checkpoint` {id}, `item_stolen`, `extracted`, `hide_enter`/`hide_exit` {kind: locker/grass/shadow}, `distraction_thrown` {location}, `noise` {loudness, source} ; `state` adds stance, visibility, times_spotted |
| rally-racer | `countdown_end`, `checkpoint` {index, lap}, `lap_complete` {lap, lap_time_s}, `position_changed` {position}, `reset` {checkpoint}, `collision` {impulse, other}, `boost` {on}, `race_finish` {position, total_time_s}; `state` adds speed_kmh, gear, lap, position, boost |

### `outcome.json` (subsystem; your part is the arguments of `FinishRun`)

```json
{"schema":"autoplay-outcome/1","autoplay_version":2,"game":"TowerDefense","run_id":"...","level":2,"seed":7,
 "skill":0.6,"max_seconds":600,"qpc_frequency":10000000,"build_commit":"a1b2c3d","level_name":"Canyon","result":"win",
 "score":1840,"duration_s":512.3,"run_duration_s":514.9,"go_qpc":...,"level_start_qpc":...,"level_end_qpc":...,
 "frames":30893,"inputs_injected":20411,"go_timed_out":false,"build_config":"Development","engine_version":"5.3.2-...",
 "extra":{"stars":2,"lives":14}}
```

`duration_s` = level_start → level_end; `run_duration_s` = go → level_end; `frames` = frames from level_start to
level_end (so `frames / duration_s` is the gameplay fps). Put game-specific results in
`ExtraJson` (stars, lap times, times spotted, shots used).

### `clock.json` (subsystem)

```json
{"schema":"autoplay-clock/1","qpc_frequency":10000000,"t_ns_definition":"qpc * 1e9 / qpc_frequency",
 "samples":[{"label":"start","qpc":...,"qpc_after":...,"t_ns":...,"unix_ns":...,"utc":"2026-10-11T07:12:13.123Z","frame":3}, "go", "audio_start", "audio_stop", "end"]}
```

Each sample pairs QPC (read before and after) with UTC wall time (`FDateTime::UtcNow`, ms resolution).

### `audio.wav` (subsystem)

Master submix via `UAudioMixerBlueprintLibrary::StartRecordingOutput(World, MaxSeconds + 30, nullptr)` at go and
`StopRecordingOutput(World, EAudioRecordingExportType::WavFile, "audio", OutputDir, nullptr, nullptr)` after the
result hold. 16-bit PCM at the mixer rate (48 kHz) with the output device's channel count. UE queues the start to
the audio thread (it begins ~0.1 s after the `audio_start` sample, while the level loads) but stops synchronously,
so the **last** sample corresponds to the `audio_stop` clock sample; the pipeline anchors the WAV there
(`start = audio_stop − duration`) and turns it into `system_audio.mka`.

### `ready.json`, `go`, `game.log`

Handshake files and the UE log (`-abslog`); kept in the raw run directory, not part of the dataset bundle.

## 6. Reference code

Wiring in your game (GameInstance or game mode; the bot is yours):

```cpp
// Build.cs: PrivateDependencyModuleNames.AddRange(new[] { "EnhancedInput", "AudioMixer", "Slate", "SlateCore", "InputCore" });

void UMyGameInstance::Init()
{
    Super::Init();
    if (UAutoPlaySubsystem* AP = GetSubsystem<UAutoPlaySubsystem>(); AP && AP->IsAutoPlay())
    {
        AP->StartLevel = [this](int32 Level) { UGameplayStatics::OpenLevel(this, LevelMapName(Level)); };
    }
}

// Game mode, when the player gets control:   if (AP && AP->IsAutoPlay()) { AP->LevelStarted(TEXT("Warehouse")); SpawnBot(); }
// On win/lose:  AP->FinishRun(TEXT("win"), Score, FString::Printf(TEXT("\"stars\":%d"), Stars));
// Events:       AP->Telemetry(TEXT("wave_start"), FString::Printf(TEXT("\"wave\":%d"), Wave));

void UMyBotComponent::TickComponent(float Dt, ELevelTick, FActorComponentTickFunction*)
{
    UAutoPlaySubsystem* AP = UAutoPlaySubsystem::Get(this);
    if (!AP || !AP->IsRunning()) return;
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    const FVector2D Move = ChooseMove(Rng /* FRandomStream(AP->GetSeed()) */, AP->GetSkill());
    if (!Move.IsNearlyZero()) AP->Inject(PC, IA_Move, FInputActionValue(Move), MoveKeys(Move));  // "W", "W+D", ...
    if (bWantSprint)        AP->Inject(PC, IA_Sprint, FInputActionValue(true), TEXT("LeftShift")); // every frame while held
}
```

The three pieces the contract asks to be identical, as implemented in `AutoPlaySubsystem.cpp`:

```cpp
// Clock: QPC everywhere.
uint64 UAutoPlaySubsystem::Qpc() { return FPlatformTime::Cycles64(); }  // QueryPerformanceCounter
uint64 UAutoPlaySubsystem::QpcToNs(uint64 Q) { const uint64 F = QpcFrequency(); return (Q / F) * 1000000000ull + (Q % F) * 1000000000ull / F; }
FString UAutoPlaySubsystem::Stamp() const { const uint64 Q = Qpc();
    return FString::Printf(TEXT("\"t_ns\":%llu,\"qpc\":%llu,\"frame\":%llu"), QpcToNs(Q), Q, (uint64)GFrameCounter); }

// Input logger: inject through Enhanced Input, then log with edge tracking.
void UAutoPlaySubsystem::Inject(APlayerController* PC, const UInputAction* Action, FInputActionValue Value, const FString& Key)
{
    if (!IsRunning() || !PC || !Action) return;
    auto* EIS = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer());
    EIS->InjectInputForAction(Action, Value, {}, {});
    // edge = down / hold / up / zero from ActiveInputs; OnWorldPostActorTick logs "release" for actions not injected this frame
    WriteLine(InputsAr, Printf("{%s,\"type\":\"inject\",\"action\":%s,\"value_type\":..,\"value\":..,\"key\":%s,\"edge\":..}", Stamp(), ...));
}

// Audio: master submix to OutputDir/audio.wav.
UAudioMixerBlueprintLibrary::StartRecordingOutput(GetGameWorld(), MaxSeconds + 30.f, nullptr);         // at go
UAudioMixerBlueprintLibrary::StopRecordingOutput(GetGameWorld(), EAudioRecordingExportType::WavFile,
                                                 TEXT("audio"), OutputDir, nullptr, nullptr);           // async write
```

## 7. Testing by hand and declaring readiness

Without packaging (editor binaries, uncooked). **Always disable Live Coding** with the ini override shown: an `UnrealEditor.exe` that starts Live Coding makes UnrealBuildTool refuse to build *every* project on this UE 5.3 install ("Unable to build while Live Coding is active") until it exits. The override works without `-unattended` (which would also turn off DPI awareness). It is a heavy job, so run it under `Work\tools\ue-heavy.ps1`, which must wait for GUI processes; see the note below.

```
"C:\Program Files\Epic Games\UE_5.3\Engine\Binaries\Win64\UnrealEditor.exe" "<project>.uproject" -game -AutoPlay -Level=1 -Seed=1 -Skill=1 -MaxSeconds=120 -GoTimeout=0 -windowed -ResX=1920 -ResY=1080 -ini:EditorPerProjectUserSettings:[/Script/LiveCoding.LiveCodingSettings]:bEnabled=False -log
powershell -ExecutionPolicy Bypass -File C:\Users\Xiang\Work\game-factory\tools\ue-pipeline\validate-run.ps1 "<project dir>\Saved\AutoPlay\<timestamp>"
```

(Verified on games\_pipeline-test: no LiveCodingConsole is started, the run quits by itself, validate-run passes; the uncooked editor runs at ~25 fps, the packaged build at 60. If you prefer `-unattended`, that also disables Live Coding, at the cost of a DPI-stretched 2880x1620 window. `-game` runs the editor binaries uncooked; keyboard and mouse are blocked while it runs, so close it from the
taskbar if it hangs, or add `-AutoPlayAllowInput`. To see the real pipeline result, `enqueue.ps1 <game> -Levels 1
-Runs 1` builds, packages and records it; see ue-pipeline.md.)

Files land in `Saved/AutoPlay/<timestamp>/`. Check: the game quits by itself; `outcome.json` has your result;
`inputs.jsonl` has inject rows; `telemetry.jsonl` has `level_start`/`level_end`; `audio.wav` is not silent.
`validate-run.ps1` (above) checks a run directory against this contract.

When level 1 passes, commit and tag it `milestone/autoplay-1` (later levels: `milestone/autoplay-<n>` = levels
1..n work). The nightly pipeline records every game whose latest commit on its default branch has (or descends
from) a `milestone/autoplay-*` tag; a game session can queue a run itself, see [ue-pipeline.md](ue-pipeline.md).

Changes to this contract go through the coordinating session; bump `ContractVersion` when the files change shape.

## Naming rule (game side)

The names **Superposition** and **game-factory** (case-insensitive, including `game_factory` / `gamefactory`) must not appear anywhere in a game: repo files, code, comments,
configs (e.g. `CompanyName` in `DefaultGame.ini`, which also becomes the exe's "Publisher"), scripts, commit messages,
builds, logs, in-game files, or anything passed to the game process. Everything else stays as it is: recording and
workflow traces are fine and `workflow.jsonl` stays in the repo. The drop-in v1.2 follows this. Old occurrences in a
finished game's history are replaced with `tools/ue-pipeline/scrub-history.ps1` (original archived first). Words like recording,
dataset, pipeline, workflow row ids in commit messages and `workflow.jsonl` are fine.

Hand test without a window on the user's screen: add `-RenderOffScreen` to the §7 command (verified on the test
project with v1.2: the run completes and validate-run passes).

## Changes

- **v1.1** (docs only; `AutoPlaySubsystem.h/.cpp` unchanged, `ContractVersion` stays 1): section 1 lists the pipeline's real flags (`-ini:...bAllowHighDPIInGameMode=True`, no `-unattended`); section 5: `frames` in outcome.json counts level_start..level_end and the WAV is anchored at `audio_stop`; section 7: the hand test disables Live Coding and uses validate-run.ps1.
- **v1.2** (`ContractVersion` 2, games re-copy `AutoPlaySubsystem.h/.cpp`): no company/project names. Schemas
  `superposition.autoplay-*/v1` → `autoplay-*/1`, key `contract_version` → `autoplay_version`, comments no longer name the
  docs or tooling. Flag `-OutputDir` added (`-RecordDir` still accepted; `GetOutputDir()` added, `GetRecordDir()` kept). File
  names and behaviour unchanged. Verified on games\_pipeline-test: editor build, off-screen -game runs with each flag,
  validate-run PASS, no "superposition"/"game-factory" in any output file.
- **v1**: first version.

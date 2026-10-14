# AutoPlay contract (v1.4)

> **v1.4 = drop-in `ContractVersion = 4`.** Audio is captured by a master-submix buffer listener that timestamps every
> audio buffer with QPC and writes `audio_clock.jsonl` next to `audio.wav`; when the audio renderer stalls (busy
> machine) silence is inserted, so the WAV stays aligned with video and inputs. Only the two drop-in files change; no
> game code, Build.cs or flags change. See **Migration to v1.4** at the end.

> **v1.3 = drop-in `ContractVersion = 3`.** A run plays a **scenario** instead of a "level" (see the definition below):
> flag `-Scenario=<n>` (`-Level` still accepted), API `StartScenario` / `ScenarioStarted`, keys `scenario` and
> `scenario_name` in every file, telemetry `scenario_start` / `scenario_end`, schemas `autoplay-*/2`. v1.2 games still
> compile (thin `StartLevel` / `LevelStarted` / `GetLevel` wrappers) and the pipeline still drives v1 and v1.2 builds.
> Recording builds are packaged as **Shipping** once the game sets `bAllowHighDPIInGameMode=True` in
> `Config/DefaultEngine.ini` (no Windows Firewall prompts; see section 1). See **Migration** and **Changes** at the end.

**Scenario** = a defined start state plus a win/lose condition, numbered 1..n in the game's design doc and named by the
game. It may be a level (tower-defense "Meadow"), a chapter (stealth "Warehouse"), a race stage (rally-racer "Forest
dirt"), a castle (siege-catapult "Twin Towers") or an open-world start setup (island-survival "First Night",
"Toolmaker"). A run plays exactly one scenario from its start state until it is won, lost or times out.

> **AutoPlay's goal is NOT to win (user rule).** The bot only drives the game with human-like input so a recording
> shows the game running. Never tune, fix or re-test the bot to win, score, finish, reach targets, resupply or avoid
> getting stuck; losing, timing out or wandering is fine (metadata). Fix only game bugs (crash, hang, broken level,
> missing art, lighting, camera); then one AutoPlay run per scenario and the recording request.

**Priorities (user decision).** What ships is what matters, in this order: the game plays; the game builds (editor and packaged Shipping); the dataset holds the replay scripts and the git log. The AutoPlay bot should still play like a human (human-like input, aim and camera), but bot work never blocks a release: one recording per scenario that shows the game running is enough, whatever the result (win/lose/timeout is metadata). No tuning for win rates, seed sweeps or "clean" runs, and no re-runs or re-recordings to improve how the bot plays. No retest loops: every GPU or editor run costs about 30 minutes of the shared machine and holds up delivery, so run the minimum once and report; re-run only when the user asks. Game-session work never blocks dataset packaging or sharing.

Every game implements this once its first scenario is playable. The shared pipeline (`tools/ue-pipeline/`, [ue-pipeline.md](ue-pipeline.md)) then packages the game,
launches it with the flags below, captures the window with ffmpeg and turns each run into a gameplay bundle
(`video.mkv`, `system_audio.mka`, `inputs.jsonl`, `telemetry.jsonl`, `outcome.json`, `metadata.json`, `validation.json`,
`manifest.json`, `stills/`, `gameplay.mp4`; see [ue-pipeline.md, Bundle](ue-pipeline.md#bundle)).

The game plays itself: an in-game **bot** reads game state and acts **only by injecting input through Enhanced
Input**, and the game logs every injected input. Nothing uses OS-level input (`SendInput`), and hardware input is
ignored during a run.

Use the drop-in implementation in `tools/ue-pipeline/autoplay/` (`AutoPlaySubsystem.h/.cpp`) unchanged, so all
games write identical files. Your game supplies two things: `StartScenario` (set up scenario N) plus `ScenarioStarted`, and the bot.

## 1. Command line

The pipeline launches the packaged game as:

```
<Game>.exe -AutoPlay -Scenario=<n> -Seed=<s> -Skill=<0..1> -OutputDir=<abs dir> -MaxSeconds=<n>
           -BuildCommit=<sha> -RunId=<id> -windowed -ResX=1920 -ResY=1080 -WinX=<x> -WinY=<y>
           -ini:Engine:[/Script/Engine.UserInterfaceSettings]:bAllowHighDPIInGameMode=True
           -nosplash -abslog=<OutputDir>\game.log
```

Displays often run above 100 % scaling: the ini override makes the game DPI-aware so 1920x1080 means physical
pixels (otherwise Windows stretches the window, e.g. to 2880x1620 at 150 %). No `-unattended`: UE skips DPI awareness when unattended.

**Recording builds are Shipping (v1.3).** Development and Test builds contain UE's trace runtime, which listens on a TCP
port (0.0.0.0, no runtime switch in 5.3), so Windows Firewall shows a "Windows Security" prompt for every new exe path;
unanswered prompts dim the screen and block recordings. Shipping compiles the trace runtime out. Shipping ignores
command-line `-ini:` overrides, so put the DPI setting in your game's config:

```
; Config/DefaultEngine.ini
[/Script/Engine.UserInterfaceSettings]
bAllowHighDPIInGameMode=True
```

build.ps1 packages Shipping automatically once that line is committed (Development otherwise). Shipping writes no log file
and that's expected: the pipeline doesn't need one (`raw\game.log` is simply absent). Do **not** set
`bUseLoggingInShipping = true;` with this launcher-installed engine: its precompiled Shipping libraries have no log
symbols and the Shipping link fails (found by horror-escape; it only works with a source-built engine). The drop-in
works the same in Shipping (scalability is set through the Scalability API, not a console command).

**Known issue: GPU hang/crash on frame 1 (Lumen + virtual shadow maps).** UE 5.3 can lose the D3D12
device on the first frame: GPU breadcrumbs end in Lumen `ScreenProbeGather` on async compute while virtual shadow
maps initialise (seen in tower-defense and siege-catapult). Fix in your game, then rebuild:

```
; Config/DefaultEngine.ini
[SystemSettings]
r.RDG.AsyncCompute=0
```

The pipeline marks such runs `gpu_crash` (not a generic failure) and retries them once.

| Flag | Meaning | Default |
|---|---|---|
| `-AutoPlay` | enable AutoPlay (ignored in the editor/PIE; works with `UnrealEditor.exe <uproject> -game`) | off |
| `-Scenario=<n>` (alias `-Level`) | scenario number, 1-based, as listed in your game's design doc | 1 |
| `-Seed=<s>` | integer seed for the bot's RNG and for game randomness (seed your `FRandomStream`s from it; `FMath::RandInit`/`SRandInit` are seeded for you). Determinism is not required | 0 |
| `-Skill=<0..1>` | bot skill: 0 = clumsy novice (slow reactions, noisy aim, poor choices, still trying), 1 = best the bot can do (a competent human; it need not win). Interpolate reaction time, aim/steering noise, decision quality. Document what it does in your design doc | 1 |
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
   telemetry `run_start`, then your **`StartScenario(Scenario)`** is called: open its map and apply its start state. Skip menus, tutorials and popups in AutoPlay.
5. When gameplay begins, the game calls **`ScenarioStarted(ScenarioName)`** (telemetry `scenario_start`, with the scenario's name, e.g. "First Night") and the bot starts.
   The bot acts only while `IsRunning()` is true.
6. The game emits telemetry as things happen (section 5) and calls `SetScore` when the score changes.
7. The run ends with **`FinishRun(Result, Score, ExtraJson)`**: `win`, `lose`, `abort` (bot stuck, your call) — or
   `timeout`, called by the subsystem when `MaxSeconds` passes since go (bind `OnTimeout` if you want to compute a
   final score yourself). Held inputs are released (logged), telemetry `scenario_end`.
   A restart inside a run (stealth "caught → checkpoint") is **not** the end of the run.
8. The subsystem keeps the result screen up 2 s, stops audio capture (finishes `audio.wav` and `audio_clock.jsonl`),
   writes `outcome.json` and `clock.json`, telemetry `run_end`,
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
{"t_ns":3911283311000,"qpc":39112833110,"frame":512,"type":"header","schema":"autoplay-inputs/2","autoplay_version":3,"game":"Stealth","run_id":"...","scenario":1,"scenario_name":"","seed":7,"skill":0.6,"max_seconds":600,"qpc_frequency":10000000,"build_commit":"a1b2c3d"}
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
{"t_ns":...,"qpc":...,"frame":1200,"event":"scenario_start","scenario":1,"scenario_name":"Warehouse","map":"L_Warehouse"}
{"t_ns":...,"qpc":...,"frame":1874,"event":"guard_state","guard":"Guard_2","from":"patrol","to":"suspicious"}
```

Written by the subsystem: `header`, `autoplay_ready`, `run_start`, `scenario_start`, `scenario_end`, `run_end`,
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
{"schema":"autoplay-outcome/2","autoplay_version":3,"game":"TowerDefense","run_id":"...","scenario":2,"scenario_name":"Canyon","seed":7,
 "skill":0.6,"max_seconds":600,"qpc_frequency":10000000,"build_commit":"a1b2c3d","result":"win",
 "score":1840,"duration_s":512.3,"run_duration_s":514.9,"go_qpc":...,"scenario_start_qpc":...,"scenario_end_qpc":...,
 "frames":30893,"inputs_injected":20411,"go_timed_out":false,"build_config":"Development","engine_version":"5.3.2-...",
 "extra":{"stars":2,"lives":14}}
```

`duration_s` = scenario_start → scenario_end; `run_duration_s` = go → scenario_end; `frames` = frames from
scenario_start to scenario_end (so `frames / duration_s` is the gameplay fps). Put game-specific results in
`ExtraJson` (stars, lap times, times spotted, shots used).

### `clock.json` (subsystem)

```json
{"schema":"autoplay-clock/2","scenario":2,"scenario_name":"Canyon","qpc_frequency":10000000,"t_ns_definition":"qpc * 1e9 / qpc_frequency",
 "samples":[{"label":"start","qpc":...,"qpc_after":...,"t_ns":...,"unix_ns":...,"utc":"2026-10-11T07:12:13.123Z","frame":3}, "go", "audio_start", "audio_stop", "end"]}
```

Each sample pairs QPC (read before and after) with UTC wall time (`FDateTime::UtcNow`, ms resolution).

### `audio.wav` (subsystem)

v1.4: an `ISubmixBufferListener` registered on the world's audio device (`RegisterSubmixBufferListener`, master
submix) from go until the result hold ends. 16-bit PCM at the mixer rate (48 kHz) with the output device's channel
count. Each buffer is stamped with QPC when it arrives on the audio render thread; if it arrives later than the wall
clock allows (more than max(2048, 2 buffers) frames behind), the missing time is written as silence first, so WAV
sample position = time since the first buffer. The pipeline anchors the WAV with `audio_clock.jsonl` and turns it
into `system_audio.mka` (`aligned` when the clock drift stays ≤ 250 ms).

v1.3 and older (`StartRecordingOutput` / `StopRecordingOutput`): no `audio_clock.jsonl`; the pipeline anchors the
WAV at the `audio_stop` clock sample (`start = audio_stop − duration`). If the mixer dropped buffers the WAV is short
and audio is marked unaligned (bundle status `ok_video_only`).

### `audio_clock.jsonl` (subsystem, v1.4)

One row per audio buffer, in WAV order:

```json
{"frame":2048,"frames":1024,"qpc":13605553354491,"t_ns":1360555335449100,"silence_before":0,"audio_clock":2.70933333,"channels":2,"rate":48000}
```

`frame` = index of the buffer's first sample frame in `audio.wav`; `frames` = its length; `qpc`/`t_ns` = QPC time of
that first frame (arrival time minus the buffer's duration); `silence_before` = silent frames inserted before it
(a renderer stall); `audio_clock` = the mixer's own clock in seconds. Map a WAV position to the shared clock with the
last row whose `frame` ≤ it: `t_ns = row.t_ns + (pos − row.frame) / rate · 1e9`. `outcome.json` adds `audio_frames`,
`audio_silence_frames` and `audio_gaps`.

### `ready.json`, `go`, `game.log`

Handshake files and the UE log (`-abslog`); kept in the raw run directory, not part of the dataset bundle.

## 6. Reference code

Wiring in your game (GameInstance or game mode; the bot is yours):

```cpp
// Build.cs: PrivateDependencyModuleNames.AddRange(new[] { "EnhancedInput", "AudioMixer", "Slate", "SlateCore", "InputCore" });
// (v1.4 needs only Engine for audio; "AudioMixer" may stay.)

void UMyGameInstance::Init()
{
    Super::Init();
    if (UAutoPlaySubsystem* AP = GetSubsystem<UAutoPlaySubsystem>(); AP && AP->IsAutoPlay())
    {
        AP->StartScenario = [this](int32 Scenario) { UGameplayStatics::OpenLevel(this, ScenarioMapName(Scenario)); /* + start state */ };
    }
}

// Game mode, when the player gets control:   if (AP && AP->IsAutoPlay()) { AP->ScenarioStarted(TEXT("Warehouse")); SpawnBot(); }
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

// Audio (v1.4): master-submix buffer listener -> OutputDir/audio.wav + audio_clock.jsonl.
World->GetAudioDeviceRaw()->RegisterSubmixBufferListener(AudioCapture, nullptr);                        // at go
// AudioCapture::OnNewSubmixBuffer (audio thread): stamp with QPC, insert silence after a render stall, queue PCM + row
// Tick (game thread): AudioCapture->Flush() writes them; at the end UnregisterSubmixBufferListener + Close (WAV header)
```

## 7. Testing by hand and declaring readiness

Without packaging (editor binaries, uncooked). **Always disable Live Coding** with the ini override shown: an `UnrealEditor.exe` that starts Live Coding makes UnrealBuildTool refuse to build *every* project on that engine install ("Unable to build while Live Coding is active") until it exits. The override works without `-unattended` (which would also turn off DPI awareness). It is a heavy job, so run it under `Work\tools\ue-heavy.ps1`, which must wait for GUI processes; see the note below.

```
"<engine>\Engine\Binaries\Win64\UnrealEditor.exe" "<project>.uproject" -game -AutoPlay -Scenario=1 -Seed=1 -Skill=1 -MaxSeconds=120 -GoTimeout=0 -windowed -ResX=1920 -ResY=1080 -ini:EditorPerProjectUserSettings:[/Script/LiveCoding.LiveCodingSettings]:bEnabled=False -log
powershell -ExecutionPolicy Bypass -File %GF_ROOT%\game-factory\tools\ue-pipeline\validate-run.ps1 "<project dir>\Saved\AutoPlay\<timestamp>"
```

(Verified on games\_pipeline-test: no LiveCodingConsole is started, the run quits by itself, validate-run passes; the uncooked editor runs at ~25 fps, the packaged build at 60. If you prefer `-unattended`, that also disables Live Coding, at the cost of a DPI-stretched 2880x1620 window. `-game` runs the editor binaries uncooked; keyboard and mouse are blocked while it runs, so close it from the
taskbar if it hangs, or add `-AutoPlayAllowInput`. To see the real pipeline result, `enqueue.ps1 <game> -Scenarios 1
-Runs 1` builds, packages and records it; see ue-pipeline.md.)

Files land in `Saved/AutoPlay/<timestamp>/`. Check: the game quits by itself; `outcome.json` has your result;
`inputs.jsonl` has inject rows; `telemetry.jsonl` has `scenario_start`/`scenario_end`; `audio.wav` is not silent.
`validate-run.ps1` (above) checks a run directory against this contract.

When scenario 1 passes, commit and tag it `milestone/autoplay-1` (later: `milestone/autoplay-<n>` = scenarios
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

## Migration to v1.4 (per game)

1. **Re-copy** `tools/ue-pipeline/autoplay/AutoPlaySubsystem.h/.cpp` (`ContractVersion` 4) over your copies. Nothing
   else changes: same API, flags, files and Build.cs (no new module; `AudioMixer` may stay listed).
2. **Re-test** by hand (§7 with `-RenderOffScreen`) and run `validate-run.ps1` on the output: it must say "AutoPlay
   drop-in version 4", PASS, and print an `audio_clock:` line (buffers, render stalls filled, max drift).
3. **Commit** (re-tag `milestone/autoplay-<n>` on it) and ask the coordinator to queue a recording.

## Migration to v1.3 (per game)

1. **Re-copy** `tools/ue-pipeline/autoplay/AutoPlaySubsystem.h/.cpp` (ContractVersion 3). v1.2 code still compiles via
   the deprecated `StartLevel` / `LevelStarted` / `GetLevel` wrappers, but migrate now:
2. **Rename** in your code: `AP->StartLevel = ...` → `AP->StartScenario = ...`; `AP->LevelStarted(Name)` →
   `AP->ScenarioStarted(Name)` with the scenario's display name ("Meadow", "First Night"); `GetLevel()` →
   `GetScenario()`. If your game isn't level-based, `StartScenario(N)` applies scenario N's start state (spawn point,
   inventory, time of day, objectives) on your one map. Your own telemetry may keep its names; only the subsystem's
   events changed (`scenario_start`/`scenario_end`).
3. **List your scenarios** (1..n, name, start state, win/lose condition) in your design doc; that numbering is what
   `-Scenario=<n>` and `milestone/autoplay-<n>` mean.
4. **Config:** add `bAllowHighDPIInGameMode=True` under `[/Script/Engine.UserInterfaceSettings]` in
   `Config/DefaultEngine.ini` (Shipping recording builds). Do not set `bUseLoggingInShipping` (breaks the Shipping link
   with the launcher engine; Shipping runs have no game.log and nothing needs one). Check your game still runs in
   Shipping (no editor-only or Development-only code paths in AutoPlay).
5. **Re-test** by hand (§7, now `-Scenario=1`, `-RenderOffScreen`) and run `validate-run.ps1` on the output: it must say
   "AutoPlay drop-in version 3" and PASS.
6. **Commit and re-tag** `milestone/autoplay-<n>` on the migrated commit (n = scenarios ready), then queue a recording:
   `enqueue.ps1 <game> -Scenarios 1 -Runs 1 -RequestedBy <session>`.

## Changes

- **v1.4** (`ContractVersion` 4, games re-copy `AutoPlaySubsystem.h/.cpp`): audio capture by an `ISubmixBufferListener`
  on the master submix instead of `StartRecordingOutput`/`StopRecordingOutput`; new `audio_clock.jsonl` (per-buffer QPC,
  `silence_before`); renderer stalls are filled with silence so the WAV stays aligned; `outcome.json` adds
  `audio_frames`, `audio_silence_frames`, `audio_gaps`. API, flags, other files and Build.cs unchanged. Why: under load
  the v1.3 mixer recording dropped buffers (tower-defense runs lost 8–23 s of audio, so system_audio was unaligned).
  Verified on games\_pipeline-test (a43a8bb5): Shipping smoke, two queued pipeline runs aligned on the audio clock
  (max drift 10 / 14 ms, 0 stalls, beep lag −6.8 / 9.3 ms vs 11.2 ms for v1.3), off-screen runs quiet and under CPU
  stress for v1.3, quiet for v1.4 (beep lag 6.5 ms vs 22.8 ms); validate-run PASS for v1.4 and older outputs.

- **v1.3** (`ContractVersion` 3, games re-copy `AutoPlaySubsystem.h/.cpp`): "level" becomes "scenario". Flag
  `-Scenario=<n>` (`-Level` still accepted) and optional `-ScenarioName=<text>`; API `StartScenario`,
  `ScenarioStarted`, `GetScenario`, `GetScenarioName` (`StartLevel`, `LevelStarted`, `GetLevel` kept as deprecated
  wrappers); keys `scenario` + `scenario_name` in every header, `outcome.json`, `ready.json` and `clock.json`
  (`level_name` gone); `outcome.json` `scenario_start_qpc`/`scenario_end_qpc`; telemetry `scenario_start`/`scenario_end`;
  schemas `autoplay-{inputs,telemetry,outcome,clock}/2`; scalability via the Scalability API (works in Shipping).
  Recording builds are Shipping once `bAllowHighDPIInGameMode=True` is in `DefaultEngine.ini`. Verified on
  games\_pipeline-test: editor build with the old and the new API, off-screen runs with `-Scenario` and `-Level`,
  validate-run PASS for v1.3, v1.2 and v1 outputs.

- **v1.1** (docs only; `AutoPlaySubsystem.h/.cpp` unchanged, `ContractVersion` stays 1): section 1 lists the pipeline's real flags (`-ini:...bAllowHighDPIInGameMode=True`, no `-unattended`); section 5: `frames` in outcome.json counts level_start..level_end and the WAV is anchored at `audio_stop`; section 7: the hand test disables Live Coding and uses validate-run.ps1.
- **v1.2** (`ContractVersion` 2, games re-copy `AutoPlaySubsystem.h/.cpp`): no company/project names. Schemas
  `superposition.autoplay-*/v1` → `autoplay-*/1`, key `contract_version` → `autoplay_version`, comments no longer name the
  docs or tooling. Flag `-OutputDir` added (`-RecordDir` still accepted; `GetOutputDir()` added, `GetRecordDir()` kept). File
  names and behaviour unchanged. Verified on games\_pipeline-test: editor build, off-screen -game runs with each flag,
  validate-run PASS, no "superposition"/"game-factory" in any output file.
- **v1**: first version.

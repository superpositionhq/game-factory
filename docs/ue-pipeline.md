# UE build and gameplay recording pipeline

Builds, packages and smoke-tests the Track B Unreal games, then records AutoPlay runs (an in-game bot playing
through Enhanced Input, see [autoplay-contract.md](autoplay-contract.md)) as gameplay bundles shaped like the Lab's
`game_recording` bundle (schema 3). Scripts: `tools/ue-pipeline/` (Windows PowerShell 5.1, no Python).

| Script | Does |
|---|---|
| `build.ps1 <game> [-Commit rev] [-Package] [-Smoke] [-Force]` | editor build, BuildCookRun package, smoke test; row in `builds.jsonl` |
| `record.ps1 <game> -Build <dir\|latest> -Level n -Runs k [-Skill s] [-Seed s]` | launch, capture, validate, bundle; row per run in `runs.jsonl` |
| `pipeline.ps1 <game> [-Runs k] [-Levels 1,2] [-Commit rev]` | build → package → smoke → record k runs per level; row in `pipeline.jsonl` |
| `pipeline.ps1 -Nightly` / `-DrainQueue` | all games with a milestone tag / requests from `enqueue.ps1` |
| `enqueue.ps1 <game> [-Runs k] [-Levels ..]` | queue a pipeline run and return at once (for game sessions) |
| `validate-run.ps1 <RecordDir>` | contract check of one raw run directory (for game sessions testing by hand) |
| `sync-check.ps1 <bundle>` | measures video/audio lag against telemetry sync markers (pipeline test project) |
| `autoplay/AutoPlaySubsystem.h/.cpp` | the drop-in C++ every game copies (contract implementation) |

## Paths

```
C:\Users\Xiang\Work\
  games\<game>\                     the game repos (read only for the pipeline)
  games\_pipeline-test\             throwaway UE 5.3 Third Person project used to test the pipeline (not data)
  builds\_src\<game>\               private clone the pipeline builds from (never the game's working copy)
  builds\<game>\<short-sha>\        packaged build: Windows\<Project>.exe, build_info.json, logs\
  builds\_pipeline.lock(.json)      one-heavy-job lock (holder in the .json)
  builds\_queue\                    enqueue.ps1 requests; done\ has results
  builds\_logs\                     transcripts of nightly / queue runs
  recordings\<game>\<run-id>\       bundles
  .recording\<game>\builds.jsonl    one row per build.ps1 run
  .recording\<game>\runs.jsonl      one row per recorded run
  .recording\<game>\pipeline.jsonl  one row per pipeline.ps1 run per game
```

`actions.jsonl` / `commits.jsonl` in `.recording\<game>\` belong to the creation-recording hooks; the pipeline
never touches them.

## One heavy job at a time

`build.ps1` and `record.ps1` take an exclusive lock on `builds\_pipeline.lock` (an open file handle: released by
the OS if the process dies, visible across sessions and Task Scheduler) for the whole build or the whole run, and
wait for it otherwise (the holder is printed). Builds run at below-normal priority so the game sessions' own
editors stay responsive; the game and ffmpeg run at above-normal priority during a recording. UnrealBuildTool's
own mutex also serialises our builds with the game sessions' builds.

## build.ps1

1. Resolve `-Commit` (default `HEAD`) in the game repo; output goes to `builds\<game>\<first 8 of sha>\`. A build that
   already succeeded for that sha is reused unless `-Force`.
2. Source: `git clone --local --no-checkout` of the game repo into `builds\_src\<game>` once, then `fetch` +
   `checkout --force <sha>` + `clean -ffd` (Binaries/Intermediate/DDC stay, so later builds are incremental).
   LFS files are checked out as pointers (`GIT_LFS_SKIP_SMUDGE=1`) and copied from the game repo's own
   `.git\lfs\objects` store, so nothing is downloaded and the game repo is only read. Uncommitted work is not built.
3. `Engine\Build\BatchFiles\Build.bat <Project>Editor Win64 Development -Project=<uproject> -WaitMutex -NoHotReloadFromIDE`
4. With `-Package`: `RunUAT.bat BuildCookRun -project=<uproject> -target=<Project> -noP4 -platform=Win64
   -clientconfig=Development -build -cook -stage -pak -archive -archivedirectory=<out> -nocompileeditor -unattended -utf8output`
5. With `-Smoke`: if the game's Source contains an automation test named `<Project>.Smoke…`,
   `UnrealEditor-Cmd.exe <uproject> -ExecCmds="Automation RunTests <Project>.Smoke; Quit" -TestExit="Automation Test Queue Empty"
   -ReportExportPath=<logs> -nullrhi -unattended -nopause -nosplash -nosound`; pass = report has ≥ 1 success and 0
   failures. Without such a test the step is `skipped` with a note.

`builds.jsonl` row: `commit`, `short_sha`, `commit_subject`, `command`, `start`/`end`/`duration_s`, `status`,
`exit_code`, `error_excerpt` (first matching error lines of the failing log), `log_path`, `output_path`,
`exe_path`, `smoke {status, note}`, and `steps[]` (each with its exact command line, times, exit code, log).

## record.ps1

Per run (seed = `-Seed + i`, or random; skill = `-Skill`, or cycling 1.0 / 0.75 / 0.5 / 0.25):

1. Launch `Windows\<Project>\Binaries\Win64\<Project>.exe` (the real binary, so our PID owns the window) with the
   contract flags plus `-windowed -ResX=1920 -ResY=1080 -WinX=200 -WinY=150
   -ini:Engine:[/Script/Engine.UserInterfaceSettings]:bAllowHighDPIInGameMode=True -nosplash -abslog=<raw>\game.log`.
   - The display runs at 150 % scaling. Without `bAllowHighDPIInGameMode` a UE game is DPI-unaware and Windows
     stretches its 1920x1080 frame to a 2880x1620 window. The ini override fixes that without touching the games.
   - **Never pass `-unattended`**: UE skips setting DPI awareness when unattended (`FWindowsPlatformApplicationMisc::SetHighDPIMode`).
2. Wait for `ready.json`, find the window by PID, make it topmost (not activated), check the client area is exactly
   1920x1080 and fully on screen (physical pixels; the script is per-monitor DPI aware).
3. Start ffmpeg on that screen rectangle, wait for 30 captured frames, write `go`.
4. Wait for `outcome.json` (written while the result screen is still up), **stop ffmpeg before the window closes**
   (so nothing behind it is ever captured), wait for the game to quit. Kill after `MaxSeconds + 90 s`.
5. Validate and write the bundle (below), even for failed runs.

### Capture command (verified on this machine)

ffmpeg: `Gyan.FFmpeg` 9.0.2 full build (winget). Desktop Duplication (`ddagrab`) of the window's client rectangle,
**event-driven**, no mouse cursor, converted to 60 fps CFR:

```
ffmpeg -hide_banner -loglevel +datetime+level+info -stats_period 1 -progress <raw>\ffmpeg_progress.txt -y
  -f lavfi -i "ddagrab=output_idx=0:framerate=240:dup_frames=0:offset_x=<x>:offset_y=<y>:video_size=1920x1080:draw_mouse=0,showinfo"
  -c:v h264_nvenc -preset p5 -tune hq -rc vbr -cq 19 -b:v 0 -maxrate 60M -bufsize 120M -g 120 -bf 0
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -fps_mode cfr -r 60 -an <bundle>\video.mkv
```

Why `framerate=240:dup_frames=0` and not `framerate=60`: ddagrab paces itself with `av_usleep`, which on Windows is
`Sleep()` at the default 15.6 ms timer resolution (since Windows 10 2004 a process only gets 1 ms if it asks for it
itself, and ffmpeg doesn't). At `framerate=60` that produced frames at 15.6/31 ms intervals, 57 fps, 5–7 % CFR
duplicates. With `dup_frames=0` and a rate above the display's, the pacing loop never sleeps and ddagrab waits
inside `AcquireNextFrame` for each new desktop image (≈143–159 per second here, timestamped when acquired);
`-fps_mode cfr -r 60` then keeps the latest image per 1/60 s slot. ffmpeg's `drop=` count is just these surplus
samples; `dup=` counts slots without a new image (measured: 0).

**NVENC caveat:** ffmpeg 9.x needs NVENC API 13.1 = NVIDIA driver ≥ 610. This machine has 591.86, so `h264_nvenc`
fails to open ("Required: 13.1 Found: 13.0"). record.ps1 probes NVENC at start and otherwise encodes on the CPU
(`metadata.video.encoder` says which):

```
  ... "ddagrab=...,showinfo,hwdownload,format=bgra,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
  -c:v libx264 -preset ultrafast -crf 17 -g 120 -bf 0 -pix_fmt yuv420p <same tags> -fps_mode cfr -r 60 -an
```

(`veryfast` ran at 0.977x on the shared CPU; `ultrafast` keeps up.) Fix for NVENC: update the NVIDIA driver to
≥ 610, or put an ffmpeg 8.x build (NVENC API 13.0) in `C:\Users\Xiang\Work\tools\ffmpeg-<version>\bin\`
(record.ps1 prefers it; `$env:UE_PIPELINE_FFMPEG` overrides everything). `h264_mf` (Media Foundation) does not work here.

Fallbacks (`-Capture`), measured on the test project: `gdigrab-region` (`-f gdigrab -framerate 60 -offset_x
-offset_y -video_size 1920x1080 -i desktop`) captures real content but only ~44 fps (24 % duplicates);
`gdigrab-window` (`-i title="<Project> [AutoPlay]"`) ~56 fps (8 % duplicates, 23 % gap time). Both fail validation,
so they are for emergencies; `auto` tries ddagrab first and gdigrab-region only if ddagrab can't start.

### Measured quality (pipeline test project, libx264 path, machine busy with four game sessions)

| | Result |
|---|---|
| Output | 1920x1080 H.264 yuv420p, 60/1 CFR, 0 duplicated slots, duration within 0.03 s of the capture span |
| Capture input | ≈143 images/s; gaps > 25 ms during the level ≈ 1.5–3 % of frames (game/compositor hitches) |
| Video lag | a game event shows on video 47 ms (p5–p95 29–61 ms, ≈3 frames) after its `t_ns`: game thread → render thread → GPU → present → DWM → capture. `video_start_offset_ns` is the capture clock and does **not** subtract this |
| Audio lag | a sound appears in `system_audio` 26 ms (15–37 ms) after its `t_ns` (next mixer buffer) |
| Game frame cadence | frame-code strip: per 1195 video frames, 155 game frames shown twice and 154 never shown (13 %) |

The cadence row is inherent to sampling this display: the desktop composes at 159 Hz, so the game's 60 fps frames
reach the screen on a 6.3 ms grid (12.6/18.9 ms apart), and any 60 Hz sample-and-hold capture, OBS included,
repeats some and misses some. It would go away with the display at 60 or 120 Hz during recording (a system setting:
the user's call), or with in-engine frame capture instead of screen capture.
### Audio start time

UE's `StartRecordingOutput` is queued to the audio thread and starts late by an unknown amount (≈ 0.1 s, because
the level load follows immediately). `StopRecordingOutput` is synchronous under the same lock the mixer appends
with. So the WAV is anchored at its **end**: `system_audio.start_offset_ns = audio_stop.t_ns − WAV duration`.

### Bundle

```
recordings\<game>\<game>_L<level>_<yyyyMMdd-HHmmss>_s<seed>\
  video.mkv           H.264 1920x1080 60 fps CFR, no audio, BT.709 tags
  system_audio.mka    FLAC from the game's master-submix audio.wav (48 kHz, device channel count)
  inputs.jsonl        as written by the game (contract section 5)
  telemetry.jsonl     as written by the game
  outcome.json        as written by the game
  metadata.json       game, level, seed, skill, result, build sha, ffmpeg command + version, capture rect,
                      video_start_offset_ns (+ estimate details), system_audio.start_offset_ns,
                      clock samples (game: start/go/audio_start/audio_stop/end; pipeline: record_start,
                      capture_start, go_written, capture_stopped, record_end)
  validation.json     status ok | warn | failed, problems, warnings, per-check details
  manifest.json       sha256 + bytes of every file in the bundle (incl. raw\)
  FAILED              only on failed runs (problems listed); failed runs are kept, never deleted
  raw\                the game's RecordDir: audio.wav, clock.json, ready.json, go, game.log, ffmpeg.log, ffmpeg_progress.txt
```

Lab schema 3 overlap: `video.mkv` (H.264, 60 fps, no audio), `system_audio.mka`, `inputs.jsonl` with ns QPC
timestamps, `metadata.json` with clock samples and `video_start_offset_ns`, `manifest.json` with sha256. No
`microphone.mka` (a bot has no voice). Our `inputs.jsonl` rows are action-level (`action`, `value`, `key`, `edge`)
rather than raw `key_down`/`mouse_move`; `edge` down/up maps onto key down/up when a converter is needed.

### Validation (per run)

| Check | Fails when | Warns when |
|---|---|---|
| outcome | missing, bad `result`, `go_timed_out` | result `abort` |
| inputs | no `inject` rows, unparseable lines, `t_ns` going backwards | |
| telemetry | missing `run_start`/`level_start`/`level_end`/`run_end`, unparseable lines | |
| audio | missing, or WAV duration doesn't fit the recorded span (start lag outside −30…1500 ms) | silent (max < −60 dB) |
| video | not 1920x1080, no frames, ffmpeg dup > 5 % of output frames, duration ≠ capture span ± 0.5 s, doesn't cover level_start..level_end, start time not estimable | dup > 1 %, capture gaps > 2 % of level frames, game < 55 fps |
| process | game exit code ≠ 0, killed at timeout, window moved, ffmpeg died | |

## pipeline.ps1, nightly, triggering from a game session

`pipeline.ps1 <game>`: resolves the commit (default HEAD), the levels (default 1..n from the newest
`milestone/autoplay-<n>` tag reachable from it), skips levels that already have `-Runs` good runs of that commit
(unless `-Force`), then `build.ps1 -Package -Smoke` and `record.ps1` per level. Each step takes the lock itself, so
other work can interleave between steps.

**From a game session** (returns at once; a hidden drainer works through the queue):

```
powershell -ExecutionPolicy Bypass -File C:\Users\Xiang\Work\game-factory\tools\ue-pipeline\enqueue.ps1 <game> -Runs 2 -RequestedBy <session-name>
```

Results: `.recording\<game>\pipeline.jsonl` (summary), `runs.jsonl`, `builds\_queue\done\<request>.json`.

**Nightly** (Task Scheduler, interactive session only: Desktop Duplication needs the unlocked desktop):

```
schtasks /Create /TN "Superposition\UE AutoPlay nightly" /SC DAILY /ST 03:00 /IT /F
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\Users\Xiang\Work\game-factory\tools\ue-pipeline\pipeline.ps1 -Nightly -Runs 3"
```

It records every game under `games\` (not `_*`) whose HEAD has a `milestone/autoplay-*` tag in its history,
skipping commits already recorded. If the session is locked (`LogonUI` running) recording is skipped and the
pipeline row says so; the display must not be asleep either.

## Pipeline test project

`games\_pipeline-test` (not data): UE 5.3 Third Person C++ template + the AutoPlay drop-in + a test bot that walks,
turns and jumps via Enhanced Input for 20 s (`-TestRunSeconds=n`), beeps (procedural 880 Hz) and lights a white
64x64 square in the top-left corner on every jump, plus `TP_ThirdPerson.Smoke.MapAndAutoPlay`. Tag
`milestone/autoplay-1`. `sync-check.ps1` measures marker lag in its bundles.

## Machine notes

- Display 3840x2160 at 150 % scaling, 159 Hz; vsync off + `t.MaxFPS 60` in the game keeps the game at 60 fps.
- The game window sits topmost at (200,150) for the run; anything else made topmost on top of it would be captured.
  Its audio plays on the speakers during runs.

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
editors stay responsive; the game and ffmpeg run at above-normal priority during a recording.

Every Build.bat / RunUAT / UnrealEditor-Cmd step also holds a slot of the machine-wide limiter all game sessions use
(`Global\ue-heavy-jobs`, 3 slots, `Work\tools\ue-heavy.ps1`, rows in `.recording\_heavy-jobs.jsonl`). build.ps1 takes
the semaphore itself (common.ps1 `Invoke-Logged -HeavyLabel`) instead of calling ue-heavy.ps1, because that script
re-quotes arguments through PowerShell and would split `-ExecCmds="Automation RunTests ...; Quit"`.

Every editor process the pipeline starts has `-unattended` (smoke test; RunUAT passes it to the cook commandlet):
an `UnrealEditor.exe` without it starts Live Coding, and while Live Coding runs UBT refuses to build any project on
this engine install. The recorded game itself is the packaged exe, which has no Live Coding.

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

ffmpeg: pinned to gyan.dev `ffmpeg-8.1.2-full_build.7z` in `C:\Users\Xiang\Work\tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build\bin\`,
SHA-256 `0fff188997a499b5382e0f66e845d4556c48c54f0113ebed4853d556dbdd7059` (matches gyan.dev's published
`.7z.sha256`; 166,721,853 bytes, downloaded 2026-10-11). `` overrides it; without either,
the winget `Gyan.FFmpeg` 9.0.2 on PATH is used. Desktop Duplication (`ddagrab`) of the window's client rectangle,
**event-driven**, no mouse cursor, converted to 60 fps CFR. With NVENC (needs NVIDIA driver ≥ 610, see Encoder below) the D3D11 frames go straight to the encoder:

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

**Encoder.** record.ps1 probes at start and uses the first that opens: `h264_nvenc` (RTX 4080), `h264_amf` (the
Ryzen 7700X's integrated Radeon), `libx264` (CPU); `metadata.video.encoder` says which. **NVENC does not open on this
machine**: the installed NVIDIA driver 591.86 offers NVENC API 13.0, and both gyan.dev builds tried need 13.1
(driver ≥ 610): 9.0.2 and, contrary to the expectation that led to pinning it, 8.1.2 as well ("Driver does not
support the required nvenc API version. Required: 13.1 Found: 13.0"). `h264_mf` fails too. So recordings currently
use **AMF**, verified:

```
ffmpeg -hide_banner -loglevel +datetime+level+info -stats_period 1 -progress <raw>\ffmpeg_progress.txt -y
  -f lavfi -i "ddagrab=output_idx=0:framerate=240:dup_frames=0:offset_x=<x>:offset_y=<y>:video_size=1920x1080:draw_mouse=0,showinfo,fps=60,hwdownload,format=bgra,scale=out_color_matrix=bt709:out_range=tv,format=nv12"
  -c:v h264_amf -quality quality -rc cqp -qp_i 18 -qp_p 20 -g 120 -bf 0
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -fps_mode cfr -r 60 -an <bundle>\video.mkv
```

AMF and libx264 take system-memory frames, so `fps=60` picks the 60 fps grid on the GPU frames first and only those
are downloaded and converted (BT.709 matrix, limited range). The libx264 variant is the same with `format=yuv420p`
and `-c:v libx264 -preset ultrafast -crf 17 -g 120 -bf 0 -pix_fmt yuv420p` (`veryfast` only reached 0.977x on the
shared CPU). With `fps=60` in the graph ffmpeg's own `dup=` stays 0; holes show up as capture-input gaps instead.
NVENC becomes available with an NVIDIA driver ≥ 610 (no other change needed; record.ps1 will pick it up).
Fallbacks (`-Capture`), measured on the test project: `gdigrab-region` (`-f gdigrab -framerate 60 -offset_x
-offset_y -video_size 1920x1080 -i desktop`) captures real content but only ~44 fps (24 % duplicates);
`gdigrab-window` (`-i title="<Project> [AutoPlay]"`) ~56 fps (8 % duplicates, 23 % gap time). Both fail validation,
so they are for emergencies; `auto` tries ddagrab first and gdigrab-region only if ddagrab can't start.

### Measured quality (pipeline test project, machine busy with six game sessions)

| | Result |
|---|---|
| Output | 1920x1080 H.264 yuv420p (AMF: Main, ≈11 Mbit/s; x264 ultrafast: Constrained Baseline, ≈7 Mbit/s), 60/1 CFR, 0 duplicated slots, duration within 0.1 s of the capture span |
| Capture input | 90–160 desktop images/s; gaps > 25 ms during the level 0.6–3 % of frames (game/compositor hitches) |
| Video lag | a game event shows on video 25 ms (p5–p95 15–31 ms) after its `t_ns` with AMF (`fps=60` before download); 47 ms (29–61) with the earlier output-side CFR path: game thread → render thread → GPU → present → DWM → capture. `video_start_offset_ns` is the capture clock and does **not** subtract this |
| Audio lag | a sound appears in `system_audio` 26–33 ms (15–44 ms) after its `t_ns` (next mixer buffer) |
| Game frame cadence | frame-code strip: 6 % of game frames shown twice and as many never shown with AMF (76 of 1194); 13 % on the earlier path |

The cadence row is inherent to sampling the desktop: with vsync off the game's 60 fps frames reach the screen on the display's vblank grid (6.3 ms at 159 Hz, 8.3 ms at 120 Hz) at irregular intervals, and a 60 Hz sample-and-hold capture, OBS included, repeats some and misses some. Measured: 13 % / 6 % at 159 Hz (output-side CFR / AMF path), **7 % at 120 Hz** (AMF, 86 of 1194). The user runs the display at 120 Hz for recording sessions; record.ps1 logs `machine.display` / `machine.display_refresh_hz` (from `Win32_VideoController`) in metadata.json and warns (does not fail) when the rate is not 60 or 120. 120 Hz alone doesn't fix the cadence; locking presents to every second vblank would need `r.VSync 1` at 120 Hz in AutoPlay (a contract change, not made) or in-engine frame capture.

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

## Open items

- **Machine-path scrub before bundles leave the machine** (agreed follow-up, not built). Bundles carry machine
  paths and the user name: `metadata.json` (`build.path`, `build.exe`, `video.ffmpeg_command`), `raw\game.log`,
  `raw\ffmpeg.log`, `raw\ready.json`, the `RecordDir` in UE log lines. Per AGENTS.md (leak scan for `C:\Users\…`,
  real names, e-mails), a publish step must rewrite or drop these and re-hash `manifest.json` before any upload.
- **NVENC**: blocked on the NVIDIA driver (591.86 offers NVENC API 13.0; the pinned ffmpeg 8.1.2 needs 13.1, driver
  ≥ 610). The user will update the driver; then confirm record.ps1's probe picks `h264_nvenc` and record the numbers here.
- **Game-frame cadence** (~7 % repeated/skipped at 120 Hz with vsync off): would need `r.VSync 1` at 120 Hz in
  AutoPlay (contract change) or in-engine capture.
- **Nightly Task Scheduler entry**: not created (user's decision); runs are queued on demand with enqueue.ps1.

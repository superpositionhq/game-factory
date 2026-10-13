# UE build and gameplay recording pipeline

Builds, packages and smoke-tests our Unreal games, then records AutoPlay runs (an in-game bot playing
through Enhanced Input, see [autoplay-contract.md](autoplay-contract.md)) as gameplay bundles ([Bundle](#bundle)). Scripts: `tools/ue-pipeline/` (Windows PowerShell 5.1, no Python).

| Script | Does |
|---|---|
| `build.ps1 <game> [-Commit rev] [-Package] [-Smoke] [-Force]` | editor build, BuildCookRun package, smoke test; row in `builds.jsonl` |
| `record.ps1 <game> -Build <dir\|latest> -Scenario n -Runs k [-Skill s] [-Seed s]` | launch, capture, validate, bundle; row per run in `runs.jsonl` |
| `pipeline.ps1 <game> [-Runs k] [-Scenarios 1,2] [-Commit rev]` | build → package → smoke → record k runs per scenario; row in `pipeline.jsonl` |
| `pipeline.ps1 -Nightly` / `-DrainQueue` | all games with a milestone tag / requests from `enqueue.ps1` |
| `enqueue.ps1 <game> [-Runs k] [-Scenarios ..] [-MaxSeconds "1=300,3=900"]` | queue a pipeline run and return at once (for game sessions) |
| `validate-run.ps1 <OutputDir>` | contract check of one raw run directory (for game sessions testing by hand) |
| `scrub-history.ps1 <game> [-Apply]` | archive, then remove the names Superposition/game-factory from a finished game's history; dry run by default |
| `scrub-lfs-history.py <game> [--apply]` | the user name in Git LFS objects of a game's history (assets committed before scrub-import-paths): same-length patch into new objects, every commit repointed (filter-branch, tags kept), bundle archived first, verified (no hits, HEAD tree, `git lfs fsck`); dry run by default |
| `mark-invalid.ps1 <game> -Commit sha \| -RunId id -Reason text` | exclude bundles from the dataset (INVALID file, validation status `invalid`); files kept |
| `scrub-import-paths.py` (UE Python, headless) | removes the user's profile path from a project's editor import-source paths (AssetImportData, FontFace, Interchange); see below |
| `leak-scan.ps1 <dir> [-Patterns ..]` | byte search (ASCII + UTF-16) for the user name or other strings that must not ship |
| `gameplay-mp4.ps1 <game> [-Commit sha..] [-RunId id] [-Force]` | gameplay.mp4 for runs recorded before record.ps1 made it (updates metadata/manifest) |
| `stills.ps1 <game> [-RunId id] [-Force]` | README stills for runs recorded before record.ps1 made them (updates metadata/manifest) |
| `sync-check.ps1 <bundle>` | measures video/audio lag against telemetry sync markers (pipeline test project) |
| `autoplay/AutoPlaySubsystem.h/.cpp` | the drop-in C++ every game copies (contract implementation) |

## Paths

`%GF_ROOT%` is the machine root: env `GF_ROOT`, else `root` in `%USERPROFILE%\.game-factory\config.json`
(written by `machine/bootstrap.ps1`), else `%USERPROFILE%\Work`; `machine/lib/gf-root.ps1` resolves it, and the
same file gives `ueb` (default `C:\UEB`) and `engine`. See [../machine/README.md](../machine/README.md).

```
%GF_ROOT%\
  games\<game>\                     the game repos (read only for the pipeline)
  games\_pipeline-test\             throwaway UE 5.3 Third Person project used to test the pipeline (not data)
  C:\UEB\src\<game>\                private clone the pipeline builds from (never the game's working copy); outside
                                    C:\Users so the user name isn't compiled into the exe (__FILE__, PDB paths)
  builds\<game>\<short-sha>\        packaged build: Windows\<Project>.exe, build_info.json, logs\
  builds\_pipeline-<game>.lock(.json) per-game build/record lock (holder in the .json)
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

`build.ps1` and `record.ps1` take an exclusive per-game lock on `builds\_pipeline-<game>.lock` (an open file handle:
released by the OS if the process dies, visible across sessions and Task Scheduler) for the whole build or the whole run,
and wait for it otherwise (the holder is printed): a build and a recording of the same game share its clone, build
folder and `_run` copy. Different games only share the machine, which the general and GPU slots below ration, so a
rebuild of one game can run while another game records (watch the recording's fps warnings). Builds run at below-normal priority so the game sessions' own
editors stay responsive; the game and ffmpeg run at above-normal priority during a recording.

### Machine-wide slots

Every heavy job of every session goes through one limiter, `<root>\tools\ue-heavy.ps1` (rows in
`.recording\_heavy-jobs.jsonl`); build.ps1 takes the same semaphore itself (common.ps1 `Invoke-Logged -HeavyLabel`)
instead of calling ue-heavy.ps1, because that script re-quotes arguments through PowerShell and would split
`-ExecCmds="Automation RunTests ...; Quit"`.

| Slots | Named semaphore | Taken by | Count |
|---|---|---|---|
| general | `Global\ue-heavy-jobs-v2` | every job: Build.bat/UBT, RunUAT, UnrealEditor-Cmd, and GPU jobs too | config `heavy_slots`, else the formula |
| GPU | `Global\ue-gpu-jobs-v2` | jobs that render (editor GUI, `-game`, packaged games; not `-nullrhi`/`-nographics`), taken before the general slot | config `gpu_slots`, else the formula |

The formula (machine/lib/gf-root.ps1 `Get-GFComputedSlots`; bootstrap.ps1 writes its result to the config, and a value
set by hand stays unless `bootstrap.ps1 -Force`):

- `heavy_slots = clamp(1..8, min(floor((RAM GB - 6) / 6), floor(logical cores / 4), floor((commit limit GB - 6) / 8)))`:
  a heavy Unreal process needs about 6 GB, and 6 GB stays for the desktop and the sessions themselves.
- `gpu_slots = clamp(1..4, min(floor(VRAM GB of the largest NVIDIA GPU / 4), heavy_slots - 1))`, 1 without nvidia-smi:
  about 4 GB per renderer, and one general slot always stays free for compiles.

Dynamic guards on top of the counts:

- **VRAM guard:** a GPU job starts only while the GPU's used VRAM is under `gpu_vram_limit_mb` (default half the
  VRAM) and no other GPU job started in the last 60 s (a new renderer's VRAM shows only once it has loaded);
  otherwise it hands its slot back and looks again every 30 s (`vram_wait` rows).
- **Recordings are exclusive:** a recording takes every GPU slot (common.ps1 `Enter-GpuSlot -Recording`, plus the old
  single slot `Global\ue-gpu-jobs` jobs from before the change may still hold), so a capture has the GPU to itself:
  record.ps1 for the whole run (acquired after the idle wait, released in `finally`) and the Firewall pre-flight launch.
- **`-Low`** (background work such as the live creation replay): one low job machine-wide; it takes a general slot only
  while no other job waits for one and another slot stays free, at below-normal priority.

A named semaphore keeps the count it was created with while any process holds it: a new count takes effect once
every job holding it has ended (or under a new name, which is how the `-v2` names came about; jobs on the old name
drain). `machine/check.ps1` shows the slots in effect and where each comes from.

The smoke test runs with `-nullrhi` and cooks/compiles use the general slots. Before launching, record.ps1 also
waits while more than `-MaxVramInUseMB` (default 4096) MB of VRAM is in use (nvidia-smi total; per-process numbers are
N/A under WDDM), logging the GPU-heavy processes every 5 min; after 120 min the run fails. If the user returns while
it waits for the slot, it gives the slot back and waits for idle again. Waits/starts/ends go to
`.recording\_heavy-jobs.jsonl` with `gpu: true`, like ue-heavy.ps1. **Recordings have priority:** while record.ps1
(a run or the Firewall pre-flight) waits for the slot it keeps `builds\_queue\_recording-wants-gpu` fresh (rewritten
every minute, removed once it holds the slot and in `finally`); ue-heavy.ps1 holds back new session GPU jobs while that
file exists and is under 20 min old. The queue drainer holds the same flag for each whole job (from its first build
step to the end of its last run, and across the gap to the next job; a timer rewrites it every 60 s) and removes it
when the queue is empty. Caveat: a semaphore is not released when its
holder is killed, so kill the whole job tree only if every holder dies (the count resets once no process has it open).

Every editor process the pipeline starts has `-unattended` (smoke test; RunUAT passes it to the cook commandlet):
an `UnrealEditor.exe` without it starts Live Coding, and while Live Coding runs UBT refuses to build any project on
this engine install. The recorded game itself is the packaged exe, which has no Live Coding.

## build.ps1

1. Resolve `-Commit` (default `HEAD`) in the game repo; output goes to `builds\<game>\<first 8 of sha>\`. A build that
   already succeeded for that sha is reused unless `-Force`.
2. Source: `git clone --local --no-checkout` of the game repo into `C:\UEB\src\<game>` once, then `fetch` +
   `checkout --force <sha>` + `clean -ffd` (Binaries/Intermediate/DDC stay, so later builds are incremental).
   LFS files are checked out as pointers (`GIT_LFS_SKIP_SMUDGE=1`) and copied from the game repo's own
   `.git\lfs\objects` store, so nothing is downloaded and the game repo is only read. Uncommitted work is not built.
   **Store content:** every directory of the game's working-tree `Content/` that is git-ignored **at the commit being
   built** (`git check-ignore` asked of the clone, which has that commit's `.gitignore` and index: Fab/Marketplace packs
   and other content kept out of git on purpose) is copied into the clone with `robocopy /MIR` (incremental; `clean -ffd` keeps ignored
   dirs). The list, file counts and bytes go to `hydrated_content` in `builds.jsonl`/`build_info.json`. A build made
   before hydration existed is rebuilt automatically when the game has such dirs. Without this the cook silently drops
   every asset that references the packs (tower-defense 52a6f2a1: 107 MB of paks instead of 852 MB, no art). Asking the
   working tree instead breaks once a later commit starts tracking the packs (tower-defense efbc52f moved them to LFS;
   from then on they come in through the LFS copy).
3. `Engine\Build\BatchFiles\Build.bat <Project>Editor Win64 Development -Project=<uproject> -WaitMutex -NoHotReloadFromIDE`
4. With `-Package`: `RunUAT.bat -WaitForUATMutex BuildCookRun -project=<uproject> -target=<Project> -noP4 -platform=Win64
   -clientconfig=<Shipping|Development> -build -cook -stage -pak -archive -archivedirectory=<out> -nocompileeditor -unattended -utf8output`

   Before steps 3 and 4 build.ps1 reads the machine's free commit; under 30 GB it adds `-MaxParallelActions=4` (Build.bat)
   / `-ubtargs="-MaxParallelActions=4"` (BuildCookRun). Each parallel cl.exe with a PCH reserves a large block of commit,
   and with little left they fail with C3859 "Failed to create virtual memory for PCH" / C1076. `free_commit_gb` and
   `max_parallel_actions` go to builds.jsonl.

   BuildCookRun's own UBT call always gets `-ubtargs="-WaitMutex[ -MaxParallelActions=4]"`: without it, it fails at once
   ("A conflicting instance of UnrealBuildTool is already running") while another session's UBT runs (island 5462fc8,
   2026-10-12). If the package log still has that message, the step is retried once as `package-retry`; the first
   attempt stays in `steps[]` marked `retried`, so a successful retry leaves a clean build row.
5. With `-Smoke`: if the game's Source contains an automation test named `<Project>.Smoke…`,
   `UnrealEditor-Cmd.exe <uproject> -ExecCmds="Automation RunTests <Project>.Smoke; Quit" -TestExit="Automation Test Queue Empty"
   -ReportExportPath=<logs> -nullrhi -unattended -nopause -nosplash -nosound`; pass = report has ≥ 1 success and 0
   failures. Without such a test the step is `skipped` with a note.
6. After packaging, the package log is scanned for missing-asset lines that name `/Game/` (`Failed to load`,
   `Unable to load package`, `Couldn't find file`, `ImportFailed`, `Missing import`). A package the game's working
   tree has but the build lost fails the build (`missing_assets_lost_by_build`); one missing in the game itself (a broken
   reference inside a store pack; the game's own build has it too) is a warning (`missing_assets_in_game`).
   `missing_asset_lines` = count. `cooked_content_mb` = size of the build's `*.pak`/`*.ucas`/`*.utoc`.
7. Leak scan of the packaged `Windows\` folder: case-insensitive byte search (ASCII and UTF-16LE) for the Windows user
   name inside paths (`\<name>\`, `/<name>/`; a bare-name search also hits the engine's `zh_XIANG`/`zh-xiang` locale ids)
   and for superposition / game-factory / game_factory / gamefactory / claude / anthropic (`ForbiddenNamePatterns` in common.ps1); hits are warned about and recorded in
   `leak_scan` (a build with hits can still be recorded but must not be handed out). `leak-scan.ps1 <dir>` runs the
   same scan by hand. What keeps the output clean: clones under `C:\UEB\src` (`__FILE__` in check/ensure/log macros and
   PDB source paths) and `TEMP`/`TMP` = `C:\UEB\tmp` for the build tools (the linker records its response-file path
   under `%TEMP%\UnrealBuildTool` in the PDB). Builds made before this (under `builds\_src`) have the user name in the exe.

**Recording config (v1.3):** `-Config auto` (default) packages **Shipping** when the game's `Config/DefaultEngine.ini`
at that commit sets `bAllowHighDPIInGameMode=True`, else Development. Shipping compiles out UE's trace runtime, whose
TCP listener (`TraceLog` control, bound to 0.0.0.0 in Development/Test, no runtime switch in 5.3) makes Windows
Firewall prompt for every new exe path; Shipping ignores command-line `-ini:` overrides, hence the config requirement.
Shipping builds go to `builds\<game>\<short-sha>-shipping\` (exe `<Project>-Win64-Shipping.exe`), `build_info.json`
records `config`. Shipping runs have no `raw\game.log` (nothing needs it); `bUseLoggingInShipping` must not be set with the launcher-installed engine (its Shipping libraries lack the log symbols, so the link fails).

`builds.jsonl` row: `commit`, `short_sha`, `commit_subject`, `command`, `start`/`end`/`duration_s`, `status`,
`exit_code`, `error_excerpt` (first matching error lines of the failing log), `log_path`, `output_path`,
`exe_path`, `smoke {status, note}`, `config`, `autoplay_version`, `hydrated_content[] {dir, files, bytes}`, `missing_asset_lines`, `cooked_content_mb`, and `steps[]` (each with its exact command line, times, exit code, log).

## record.ps1

Before the runs, the packaged build is mirrored (robocopy /MIR) into a stable `builds\<game>\_run\` and launched
from there (`-NoStablePath` turns this off). UE's trace runtime listens on a TCP port (`TraceLog` control, 0.0.0.0,
port 1985 or random; no runtime switch) in Development builds, and Windows Firewall asks once per program path:
a fixed path per game means one prompt per game instead of one per build.

**Cooked-content check:** before the runs, the build's `*.pak`/`*.ucas`/`*.utoc` total is compared with the largest
of the game's own packaged outputs (`games\<game>\Packaged*`, `Saved\StagedBuilds`, `deliverables\<game>`). Below 70 %
prints a red banner, logs a `content_warning` row in `_heavy-jobs.jsonl` and adds a warning to every run; the
numbers are in `metadata.json` `build.content_check {build_mb, reference_mb, reference, ratio, status}`.

Per run (seed = `-Seed + i`, or random; skill = `-Skill`, or cycling 1.0 / 0.75 / 0.5 / 0.25):

0. **Wait until the user is away** (default; the user's current standing instruction overrides it, see below): no keyboard/mouse input for `-IdleMinutes` (default 5;
   `GetLastInputInfo`; the game's injected input doesn't count) and the session unlocked. From the start of that wait
   until the run ends the display is kept on (`SetThreadExecutionState`, like a video player; no settings change):
   so the screen doesn't dim or sleep during a run. Right before launch the display is also **woken** (a 1-pixel mouse
   move out and back, outside the game run): the AC display timeout (300 s) equals the idle gate, so when the user went
   away during a build the display is already off, `SetThreadExecutionState` doesn't turn it back on, and Desktop
   Duplication delivers no frames (ddagrab hangs, gdigrab gets ~4 fps). (Note: a `Shell_SystemDim` window owned by `PickerHost.exe FirewallNotificationDialogServer` is the
   full-screen dim behind an unanswered Windows Firewall prompt; any such prompt blocks capture until it is answered.
   Turning off "Notify me when Microsoft Defender Firewall blocks a new app" removes the prompts; the user's call.) A first run of a new `_run` exe without a Windows Firewall rule starts
   it off-screen for 20 s first, so the one-time prompt appears while the user may be present.
   **Idle override:** `builds\_queue\_idle-override.txt` (JSON `{idle_minutes, reason}`, written by the coordinator)
   replaces the default when `-IdleMinutes` isn't given; `idle_minutes` 0 = record right away. It is standing (the user's
   "record now" instruction) unless it has `"one_drain": true`, which the drainer retires when the queue empties. The
   privacy guard and the display wake apply either way.
1. Launch `_run\Windows\<Project>\Binaries\Win64\<Project>.exe` (the real binary, so our PID owns the window) with the
   contract flags plus `-GoTimeout=300 -windowed -ResX=1920 -ResY=1080 -WinX=200 -WinY=150
   -ini:Engine:[/Script/Engine.UserInterfaceSettings]:bAllowHighDPIInGameMode=True -nosplash -abslog=<raw>\game.log`.
   - Displays often run above 100 % scaling. Without `bAllowHighDPIInGameMode` a UE game is DPI-unaware and Windows
     stretches its 1920x1080 frame (to a 2880x1620 window at 150 %). The ini override fixes that without touching the games.
   - **Never pass `-unattended`**: UE skips setting DPI awareness when unattended (`FWindowsPlatformApplicationMisc::SetHighDPIMode`).
2. Wait for `ready.json`, find the window by PID, move it so the client area is at (40,80) (games re-center their
   window), make it topmost (not activated), check the client area is exactly 1920x1080 and fully on screen
   (physical pixels; the script is per-monitor DPI aware). If anything covers it (e.g. a first-run Firewall prompt),
   wait up to 240 s for it to clear.
3. Start ffmpeg on that screen rectangle, wait for 30 captured frames, write `go`. Each capture attempt has its own
   files (`video.<mode>.mkv`, `raw\ffmpeg-<mode>.log`); a failed attempt is kept as `raw\failed-attempt-<mode>.mkv`.
4. Watch every 100 ms until `outcome.json` appears (written while the result screen is still up).
   **Privacy guard:** if the window moves, or another window covers its client area for ≥ 0.3 s (5x5 point test with
   `WindowFromPoint`; shorter blips are tooltips/ghost windows), ffmpeg is stopped at once, the game killed, the run
   failed, and the video cut to 0.5 s before the first sighting (`-c copy -t`). The problem names the covering window;
   moves are logged in `raw\window.jsonl` with whether a mouse button was held (user drag). A client-size change or a
   minimized window also fails the run. **Stop ffmpeg before the window closes** (so nothing behind it is ever
   captured), wait for the game to quit. Kill after `MaxSeconds + 90 s`.
5. Validate and write the bundle (below), even for failed runs.

### Capture command (verified on this machine)

ffmpeg: pinned to gyan.dev `ffmpeg-8.1.2-full_build.7z` in `%GF_ROOT%\tools\ffmpeg-8.1.2\ffmpeg-8.1.2-full_build\bin\`,
SHA-256 `0fff188997a499b5382e0f66e845d4556c48c54f0113ebed4853d556dbdd7059` (matches gyan.dev's published
`.7z.sha256`; 166,721,853 bytes, downloaded 2026-10-11; `machine/get-ffmpeg.ps1` fetches and verifies it on a new
machine). `$env:UE_PIPELINE_FFMPEG` overrides it; without either,
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

**Encoder.** record.ps1 probes at start and uses the first that opens: `h264_nvenc` (NVIDIA), `h264_amf` (AMD,
e.g. a CPU's integrated Radeon), `libx264` (CPU); `metadata.video.encoder` says which. The pinned ffmpeg 8.1.2 (like
9.x) needs NVENC API 13.1, i.e. NVIDIA driver ≥ 610; with an older driver it fails ("Required: 13.1 Found: 13.0")
and recordings use AMF. `h264_mf`
does not work. The AMF fallback, verified before the driver update:

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
With NVENC the D3D11 frames go to the encoder without any download (command above).
Fallbacks (`-Capture`), measured on the test project: `gdigrab-region` (`-f gdigrab -framerate 60 -offset_x
-offset_y -video_size 1920x1080 -i desktop`) captures real content but only ~44 fps (24 % duplicates);
`gdigrab-window` (`-i title="<Project> [AutoPlay]"`) ~56 fps (8 % duplicates, 23 % gap time). Both fail validation,
so they are for emergencies; `auto` tries ddagrab, then (after waking the display) ddagrab once more, and gdigrab-region
only if both get fewer than 30 frames in 10 s. Each failed attempt is logged with its frame count, whether ffmpeg hung or
exited (exit code) and the tail of its stderr log (`raw\ffmpeg-<attempt>.log`).

`-Capture gfxcapture` (Windows.Graphics.Capture of the game window by `hwnd`, ffmpeg 8 `gfxcapture` filter) would avoid
the screen-region problems (other windows never reach the video, no topmost needed), but in tests it delivered
2–6 frames/s for an unfocused game window and its timestamps don't fit the start-time estimate, so it is opt-in only.

### Measured quality (pipeline test project on the first machine, busy with several game sessions)

| | Result |
|---|---|
| Encoder | **NVENC (current)**: H.264 Main yuv420p ≈26 Mbit/s (cq 19, p5 hq); AMF fallback: Main ≈11 Mbit/s; x264 ultrafast: Constrained Baseline ≈7 Mbit/s |
| Output | 1920x1080 H.264 yuv420p, 60/1 CFR, 0 duplicated slots, duration within 0.1 s of the capture span |
| Capture input | 90–160 desktop images/s; gaps > 25 ms during the scenario 0.6–3 % of frames (game/compositor hitches) |
| Video lag | a game event shows on video 14–29 ms (p5–p95 5–37 ms) after its `t_ns` with NVENC; 25 ms (15–31) with AMF; 47 ms (29–61) with the first output-side CFR libx264 path: game thread → render thread → GPU → present → DWM → capture. `video_start_offset_ns` is the capture clock and does **not** subtract this |
| Audio lag | a sound appears in `system_audio` 13–33 ms (5–44 ms) after its `t_ns` (next mixer buffer) |
| Game frame cadence | frame-code strip, repeated+skipped game frames: **0.3–1.1 % with NVENC** at 120 Hz (desktop images arrive at ≈60/s, one per game frame); ≈7 % with AMF (4–10 % per run), 13 % on the first path |

With NVENC (no download, frames straight from Desktop Duplication to the encoder) the cadence is close to one video frame per game frame. On the AMF/CPU paths it is inherent to sampling the desktop: with vsync off the game's 60 fps frames reach the screen on the display's vblank grid (6.3 ms at 159 Hz, 8.3 ms at 120 Hz) at irregular intervals, and a 60 Hz sample-and-hold capture, OBS included, repeats some and misses some. Measured: 13 % / 6 % at 159 Hz (output-side CFR / AMF path), **7 % at 120 Hz** (AMF, 86 of 1194). Run the display at a multiple of 60 Hz (e.g. 120 Hz) for recording sessions; record.ps1 logs `machine.display` / `machine.display_refresh_hz` (from `Win32_VideoController`) in metadata.json and warns (does not fail) when the rate is not a multiple of 60. 120 Hz alone doesn't fix the cadence; locking presents to every second vblank would need `r.VSync 1` at 120 Hz in AutoPlay (a contract change, not made) or in-engine frame capture.

UE's `StartRecordingOutput` is queued to the audio thread and starts late by an unknown amount (≈ 0.1 s, because
the scenario load follows immediately). `StopRecordingOutput` is synchronous under the same lock the mixer appends
with. So the WAV is anchored at its **end**: `system_audio.start_offset_ns = audio_stop.t_ns − WAV duration`.

### Bundle

```
recordings\<game>\<game>_S<scenario>_<yyyyMMdd-HHmmss>_s<seed>\   (runs before v1.3 tooling: _L<level>_)
  video.mkv           H.264 1920x1080 60 fps CFR, no audio, BT.709 tags
  system_audio.mka    FLAC from the game's master-submix audio.wav (48 kHz, device channel count)
  inputs.jsonl        as written by the game (contract section 5)
  telemetry.jsonl     as written by the game
  outcome.json        as written by the game
  metadata.json       game, scenario, scenario_name, seed, skill, result, build sha, ffmpeg command + version, capture rect,
                      video_start_offset_ns (+ estimate details), system_audio.start_offset_ns,
                      clock samples (game: start/go/audio_start/audio_stop/end; pipeline: record_start,
                      capture_start, go_written, capture_stopped, record_end)
  validation.json     status ok | warn | failed, problems, warnings, per-check details
  manifest.json       sha256 + bytes of every file in the bundle (incl. raw\ and stills\)
  stills\NN.jpg       8 evenly spaced frames (t = duration * i / 9) for README screenshots, runs with status ok / warn /
                      ok_video_only only; CPU decode with the pinned ffmpeg (-ss before -i, -frames:v 1, -q:v 2); also copied to
                      recordings\<game>\_stills\<run_id>_NN.jpg; metadata.json `stills` lists them. A failed extraction is logged
                      and recorded in `stills.error`; it never changes the run's status.
  gameplay.mp4        the dataset's Gameplay/ file (packaged as <game>_S<n>.mp4), runs with status ok / warn only:
                      video.mkv's H.264 stream copied (1080p60, no re-encode) + system_audio.mka as AAC 192k stereo,
                      aligned on the QPC clock: offset = system_audio.start_offset_ns (v1.4: from audio_clock.jsonl)
                      − video_start_offset_ns, applied with adelay (audio later) or atrim (earlier), then apad +
                      -shortest to the video's end; +faststart. CPU only, below-normal priority. Checked with ffprobe
                      (h264 + aac, duration within 0.5 s of video.mkv). metadata.json `gameplay_mp4` {audio_offset_s,
                      duration_s, bytes, error}; a failure is logged there and never changes the run's status.
                      Verified on the pipeline test project: beep onsets in the mp4's own audio vs the jump events
                      lag 9.6 ms on average (9.3 ms measured on the bundle's separate files).
  FAILED              only on failed runs (problems listed); failed runs are kept, never deleted
  INVALID             excluded from the dataset after the fact (reason inside), e.g. recorded from a broken build;
                      written by mark-invalid.ps1, which also sets validation.json status "invalid" and adds a runs.jsonl row
  raw\                the game's RecordDir: audio.wav, clock.json, ready.json, go, game.log, ffmpeg.log, ffmpeg_progress.txt
```

`video.mkv` is H.264, 60 fps, no audio; `inputs.jsonl` has ns QPC timestamps; there is no microphone track (a bot
has no voice). `inputs.jsonl` rows are action-level (`action`, `value`, `key`, `edge`) rather than raw
`key_down`/`mouse_move`; `edge` down/up maps onto key down/up when a converter is needed.

### Validation (per run)

| Check | Fails when | Warns when |
|---|---|---|
| outcome | missing, bad `result`, `go_timed_out` | result `abort` |
| inputs | no `inject` rows, unparseable lines, `t_ns` going backwards | |
| telemetry | missing `run_start`/`scenario_start`/`scenario_end`/`run_end` (v1/v1.2: `level_start`/`level_end`), unparseable lines | |
| audio | missing, or WAV duration doesn't fit the recorded span (start lag outside −30…10000 ms; the lag is the scenario load) | silent (max < −60 dB) |
| build | | cooked content < 70 % of the game's own packaged build (store content probably missing) |
| video | not 1920x1080, no frames, ffmpeg dup > 5 % of output frames, video longer than the capture span by ≥ 0.5 s or shorter by ≥ 2 s, doesn't cover the scenario (start..end), start time not estimable | dup > 1 %, capture gaps > 2 % of scenario frames, game < 55 fps, video ends 0.5–2 s before the stop, display not 60/120 Hz |
| process | game exit code ≠ 0, killed at timeout, window moved, ffmpeg died | |
| gpu_crash | run ended without `outcome.json` and the game log or a crash report written since the run started shows a D3D12 device loss / GPU hang (`DXGI_ERROR_DEVICE_REMOVED/HUNG/RESET`, "GPU crash", "device lost/removed", breadcrumbs): status `gpu_crash` instead of `failed`, the run is retried once | |

## pipeline.ps1, nightly, triggering from a game session

`pipeline.ps1 <game>`: resolves the commit (default HEAD), the scenarios (default 1..n from the newest
`milestone/autoplay-<n>` tag reachable from it, meaning "scenarios 1..n are ready"), skips scenarios that already have `-Runs` good runs of that commit
(unless `-Force`), then `build.ps1 -Package -Smoke` and `record.ps1` per scenario. Each step takes the lock itself, so
other work can interleave between steps.

**Queueing (the coordinator owns the queue).** Game sessions no longer enqueue; they ask the coordinating session.
enqueue.ps1 refuses (exit 2, red message, nothing queued) unless `-RequestedBy coordinator`; `-Force` overrides and the
request still records its `requested_by`. It returns at once; one hidden drainer works through `builds\_queue\*.json`
in file-name order (the coordinator reorders by renaming; a request being processed must not be renamed):

```
powershell -ExecutionPolicy Bypass -File %GF_ROOT%\game-factory\tools\ue-pipeline\enqueue.ps1 <game> -Scenarios 1,2 -Runs 1 -RequestedBy coordinator
```

**Priorities (user decision).** What ships is what matters, in this order: the game plays; the game builds (editor and packaged Shipping); the dataset holds the replay scripts and the git log. The AutoPlay bot should still play like a human (human-like input, aim and camera), but bot work never blocks a release: one recording per scenario that shows the game running is enough, whatever the result (win/lose/timeout is metadata). No tuning for win rates, seed sweeps or "clean" runs, and no re-runs or re-recordings to improve how the bot plays. No retest loops: every GPU or editor run costs about 30 minutes of the shared machine and holds up delivery, so run the minimum once and report; re-run only when the user asks. Game-session work never blocks dataset packaging or sharing.

AutoPlay time limit: 600 s per run by default (the game gets `-MaxSeconds`, the recorder kills it 90 s later).
`-MaxSeconds "1=300,2=600,3=900"` sets it per scenario (unlisted ones keep 600; `*=700` changes the rest), a plain
`-MaxSeconds 900` sets it for every scenario; values 30..7200. The request stores it as `max_seconds`, and the job's
`pipeline.jsonl` row lists the limit used per scenario. `pipeline.ps1 -MaxSeconds` takes the same forms.

Dropping a queued request: move it to `builds\_queue\done\` with a `result` note (status `dropped`).

Results: `.recording\<game>\pipeline.jsonl` (summary), `runs.jsonl`, `builds\_queue\done\<request>.json`. The job summary's
`build.leak_scan_hits` lists the build's leak-scan hits (file, pattern, count, example; `[]` = clean, null = build made
before the scan existed); warn-only, the packager blocks on them.

**Nightly** (Task Scheduler, interactive session only: Desktop Duplication needs the unlocked desktop):

```
schtasks /Create /TN "Superposition\UE AutoPlay nightly" /SC DAILY /ST 03:00 /IT /F
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File %GF_ROOT%\game-factory\tools\ue-pipeline\pipeline.ps1 -Nightly -Runs 3"
```

It records every game under `games\` (not `_*`) whose HEAD has a `milestone/autoplay-*` tag in its history,
skipping commits already recorded. If the session is locked (`LogonUI` running) recording is skipped and the
pipeline row says so; the display must not be asleep either.

## Names that must not reach the games

User's rule: the names **Superposition** and **game-factory** (case-insensitive, incl. `game_factory`/`gamefactory`) must not appear in a game (repo files, code, commit
messages, builds, logs, in-game files, anything passed to the game process). Recording/workflow traces are fine and
`workflow.jsonl` stays in the game repos.

- Flags passed to the game: `-AutoPlay -Scenario|-Level -Seed -Skill -OutputDir|-RecordDir -MaxSeconds -BuildCommit -RunId
  -GoTimeout`, window/ini/log flags; paths under `%GF_ROOT%\recordings\` and `builds\`. None contain the names.
  build.ps1 records `autoplay_version` (the drop-in's `ContractVersion`) in `build_info.json`; record.ps1 passes
  `-Scenario` to v3 (contract v1.3) games and `-Level` to older ones, `-OutputDir` to v2+ and `-RecordDir` to v1
  (newer drop-ins accept the old names too). Bundles and `runs.jsonl` use `scenario`/`scenario_name`; outcome keys
  are read as `scenario_*` with a fallback to `level_*`.
- `build_info.json` (next to the packaged build) uses the schema `ue-build/1` and records `config` and `autoplay_version`.
- The pipeline's own files (`.recording\*.jsonl`, bundle `metadata.json`, docs) may name things freely.
- Game-side leaks found on 2026-10-11 (for the game sessions): `CompanyName=Superposition` in most
  `Config/DefaultGame.ini` (it also becomes the packaged exe's "Publisher"), descriptions/copyright notices in
  `DefaultGame.ini` and `.uproject`, `superposition.ue-workflow/v0` and `superposition.asset-manifest/v0` schema strings
  in scripts, `workflow.jsonl` and `assets.manifest.json`, `...\game-factory\...` paths, v1 drop-in copies, and the
  author e-mail `dev_02@game-factory.local` (rally-racer).

## scrub-import-paths.py (user name and agent names in a project's assets)

Assets remember the file they were imported from. Imports made under `C:\Users\<name>\` leave that path in the
project's `.uasset` files: in `AssetImportData` (textures, meshes, sounds, animations, data tables), in
`FontFace.SourceFilename` (which even reaches the cooked font), and in the node ids of Interchange-imported assets
(`UInterchangeAssetImportData`, e.g. `Factory_C:/Users/<name>/.../T.png`). The cook strips import data, but the
project files we ship keep it. Assets also keep who made them: a Level Sequence's `MovieSceneMetaData` author (the OS
user name) and a MetaSound's author (e.g. `Claude (agent)` from the script that created it). The tool removes every
term the packager blocks in asset data. Run it on a game's working tree (editor target built, editor closed), then commit:

```
"<engine>\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" <Project>.uproject -run=pythonscript -script="%GF_ROOT%/game-factory/tools/ue-pipeline/scrub-import-paths.py --apply" -nullrhi -unattended -nopause -nosplash -stdout -AllowStdOutLogVerbosity
... same with --patch-remaining   (separate run: what no editor API reaches)
... same with --verify            (expect "verify: 0 hits in 0 files")
```

Use forward slashes inside `-script="..."` (the commandlet un-escapes backslashes: `\t` becomes a tab). Output goes
to LogPython (stdout with `-AllowStdOutLogVerbosity`, always in `Saved/Logs/<Project>.log`), the report to
`Saved/scrub-import-paths.json` (`--report=<file>` elsewhere). Runs through ue-heavy (CPU slot); no GPU, no window.

- It byte-scans `Content/**/*.uasset|umap|uexp` (streamed in 8 MB chunks) for the user name as a substring anywhere
  (allowlist as the packager: `zh_XIANG`, `zh-xiang`, `wuxiangshan`), `claude` and `anthropic`, case-insensitive,
  ASCII and UTF-16LE, and loads only packages with hits. Default is a dry run; `--apply` saves only changed packages.
- `AssetImportData`: each source file under the user profile becomes a path inside the project if it is there
  (stored package-relative by UE; `--original-project-dir=<dir>` also counts files under the project's original
  location when running on a copy), else just the file name. Written with `ScriptedAddFilename`, which re-reads the
  file's timestamp/MD5 (a bare name has none: reimport then asks for the file).
- `FontFace.SourceFilename`: same mapping, written with `notify_mode=NEVER` (its `PostEditChangeProperty` flushes Slate's
  font cache and asserts in a commandlet) and saved with `save_loaded_asset`.
- Level Sequence author: `MovieSceneMetaData.SetAuthor("dev")` when it contains the user name.
- `--patch-remaining` (opt-in, its own run before anything loads): what no editor API reaches (Interchange node ids:
  `NodeUniqueID` is read-only and the node container a cached byte blob; MetaSound authors: no script API in 5.3) is
  rewritten in place to the same length, so FString lengths and package offsets stay valid (UE5 discards the name
  map's stored hashes). Only in a safe context: a path segment (`/x/`, `\x\`, `-x-`, e.g. `C--Users-<name>-Work`,
  `Temp/claude/`) or a whole serialized FString (an author field). User name -> `user_`, `claude` -> `helper`,
  `Claude (agent)` -> `Developer team`, `anthropic` -> `assistant`. A match anywhere else (e.g. a name in story text)
  is reported UNHANDLED for a person. Each patched package is then load-tested (`load_failures` in the report).
- `--verify`: byte scan only; expect `verify: 0 hits in 0 files`.

Tested on a scratch clone of a game (under the private build folder; the game's tree untouched): 56 hits in 16 files
→ 4 FontFaces fixed by `--apply` (`<root>/games/<game>/Saved/Staging/FF_*.ttf` →
`Saved/Staging/FF_*.ttf`), 12 Interchange textures by `--patch-remaining` (all 12 load), `--verify` 0. Cook before
vs after (9319 files): identical except the 4 fonts, whose cooked bytes differ exactly by the removed 40-character path
prefix and its size field, `Metadata/DevelopmentAssetRegistry.bin` (editor tags, not staged), and the shader archives
and cook metadata that also differ between two cooks of unchanged content. Gameplay data is unchanged.

## scrub-history.ps1 (finished games only; not run on any game yet)

```
powershell -ExecutionPolicy Bypass -File scrub-history.ps1 <game>                  # dry run (default)
powershell -ExecutionPolicy Bypass -File scrub-history.ps1 <game> -Apply
powershell -ExecutionPolicy Bypass -File scrub-history.ps1 <game> -StripAgentTrailers -StripRowIds -DropPaths a,b -Apply   # opt-ins
```

- **Default job:** replace the names Superposition and game-factory (case-insensitive, incl. `game_factory`,
  `gamefactory`) everywhere in history: text file contents of every commit (all versions of `workflow.jsonl`, scripts,
  configs, manifests...), commit messages, author/committer names and e-mails; plus reword "wip: auto-commit of
  uncommitted changes at end of agent turn" → "WIP" (`-NoWipReword` turns that off). Nothing is dropped:
  `workflow.jsonl`, record files, agent trailers and row ids stay.
- Replacements, in order: the schema prefix `superposition.` is removed (`superposition.ue-workflow/v0` →
  `ue-workflow/v0`); then Superposition → Studio, game-factory → studio-tools (game_factory → studio_tools,
  GameFactory → StudioTools), case-preserving. `-ReplaceMap` JSON `[{"match": perl-regex, "replace": text}]` overrides.
- **Opt-in:** `-StripAgentTrailers` (remove "Co-Authored-By: Claude…" and "Generated with Claude Code" lines),
  `-StripRowIds` (remove parenthesised workflow row ids such as "(td-01922)"), `-DropPaths a,b` (remove those files from
  every commit; only then are emptied commits pruned).
- Binary blobs and Git LFS content (uassets live outside git) are never edited; the dry run lists binary blobs and HEAD's
  LFS files that contain a name (ASCII or UTF-16) so they can be fixed in the editor.
- Dry run prints: session activity, text blobs/paths/occurrences, before → after samples from HEAD, messages and
  identities affected, how many messages the message rules change (with examples), opt-in drops, ref names, binary/LFS hits.
- Refuses while the game's session looks active (`.recording\<game>\actions.jsonl` written within `-QuietMinutes`,
  default 120), while an editor has the project open, or with uncommitted changes.
- Before rewriting: `git bundle create --all` → `.recording\<game>\original-history\<game>-<stamp>.bundle`, verified
  (`git bundle verify` + every ref present), refs listed in `<stamp>-refs.txt`, `.git\lfs\objects` copied alongside.
- Rewrite: new blobs written once (`git hash-object -w`) and mapped per commit with `git filter-branch --index-filter
  "git ls-files -s | remap | git update-index --index-info"`, `--msg-filter`, `--env-filter`, `--tag-name-filter cat
  -- --all` (Git's perl; git filter-repo would need Python). Then `refs/original/` is removed and every reachable text
  blob, message and identity is re-scanned. Never pushes, never runs `git gc`.
- Tested on throwaway clones of two games: one (23 text blobs in 9 paths, 12 author identities `dev_02@game-factory.local`)
  and the other (105 text blobs in 12 paths, ~99k occurrences; 20 auto-commits → "WIP"): afterwards 0 files with a
  name in any commit (independent `git grep`), 0 messages, 0 identities; workflow.jsonl, trailers and row ids kept by
  default; with the opt-ins 0 Claude lines, 0 row ids, the dropped file gone.
## Pipeline test project

`games\_pipeline-test` (not data): UE 5.3 Third Person C++ template + the AutoPlay drop-in + a test bot that walks,
turns and jumps via Enhanced Input for 20 s (`-TestRunSeconds=n`), beeps (procedural 880 Hz) and lights a white
64x64 square in the top-left corner on every jump, plus `TP_ThirdPerson.Smoke.MapAndAutoPlay`. Tag
`milestone/autoplay-1`. `sync-check.ps1` measures marker lag in its bundles.

## Machine notes

- Any display and scaling that holds a 1920x1080 window works; vsync off + `t.MaxFPS 60` in the game keeps the game
  at 60 fps whatever the refresh.
- The game window sits topmost with its 1920x1080 client area centred on the primary screen for the run. Runs start only after 5 min without user input; if you come back mid-run, leave the window alone (moving or covering it stops the run safely).
  Its audio plays on the speakers during runs.

## Known issues

- **GPU hang/crash on frame 1 (UE 5.3 Lumen + virtual shadow maps).** The D3D12 device can be lost on
  the first frame: GPU breadcrumbs end in Lumen `ScreenProbeGather` on async compute while virtual shadow maps
  initialise (seen in tower-defense and siege-catapult). Fix in the game: `r.RDG.AsyncCompute=0` under
  `[SystemSettings]` in `Config/DefaultEngine.ini`. record.ps1 classifies such runs as `gpu_crash` (evidence from
  `raw\game.log` for Development builds, or crash reports in `Windows\<Project>\Saved\Crashes` /
  `%LOCALAPPDATA%\<Project>\Saved\Crashes` written since the run started) and retries each once.
- **Shipping writes no game log**; `bUseLoggingInShipping` breaks the Shipping link with the launcher-installed engine.

## Open items

- **Machine-path scrub before bundles leave the machine** (agreed follow-up, not built). Bundles carry machine
  paths and the user name: `metadata.json` (`build.path`, `build.exe`, `video.ffmpeg_command`), `raw\game.log`,
  `raw\ffmpeg.log`, `raw\ready.json`, the `RecordDir` in UE log lines. Per AGENTS.md (leak scan for `C:\Users\…`,
  real names, e-mails), a publish step must rewrite or drop these and re-hash `manifest.json` before any upload.
- **Game-frame cadence**: with NVENC after the driver update it is 0.3–1.1 % (two runs); the numbers below were measured
  on the AMF path (~7 % repeated/skipped at 120 Hz with vsync off). Tried `r.VSync 1` + `t.MaxFPS 60` at
  120 Hz on the test project only (`-AutoPlayVSync` flag in its copy of the subsystem, not in the drop-in): runs of the
  same mode vary more (vsync off 4.3–10.4 %, on 2.5–14.3 %; means 7.3 % vs 7.6 %) than the modes differ, so no
  contract change. Input-to-video lag was slightly lower with vsync on (mean 18–19 ms vs 21–22 ms). Remaining
  option: in-engine frame capture.
- **Nightly Task Scheduler entry**: not created (user's decision); runs are queued on demand with enqueue.ps1.

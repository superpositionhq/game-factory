# Unity replay (plan phase A3)

Replays a LiaoZhai feature package inside Unity 2022.3.10f1, starting from the project at the package's start
commit, and verifies the result by SHA-256 against the real commits. Pilot: 葛巾_旗袍 (27 commits, 783 steps).
Run on the Windows PC (Ryzen 7 7700X, 32 GB, RTX 4080) on 2026-10-11, sharing CPU and GPU with Unreal sessions.

## Results in one table (葛巾_旗袍, 27 commits, 783 steps)

| stage | result |
|---|---|
| 0 environment | package rebuilt on Windows, `workflow.jsonl` / `commits.json` / `summary.json` byte-identical to the sample (two converter portability bugs worked around) |
| 1 open | first import 1 h 52 min (crashed at the very end on GPU memory; rerun with `-nographics` 113 s); 10f1 vs 10f1c1 only rewrites version and registry settings |
| 2 file-level | 659 / 660 file writes hash-identical after import; end state 418 / 418 + 18 / 19 changed-later + 103 / 103 absent; the misses are orphan `.meta` files of gitignored assets |
| 3 step-level | 525 / 557 file writes exact at commit boundaries; 47 of 77 API-edited files byte-identical; the other 30 trace to the converter (26) or to dependencies outside the package (4); 890 read-backs confirmed |
| 4 recording | 18.5 min video of the editor window, every step aligned to video time with measured accuracy (91 % within 1 s) |
| converter fixes | rebuilt package (811 steps): 73 / 78 API-edited files byte-identical; the 5 left are dependencies outside the package (4) and the edited workbook's zip bytes (1) |
| `table.edit` | cell edited and read back through the project's reader; the project's 导表 export changes the database exactly as the real export commit `cdf7c5092e` (+7 bytes, new value +1) |

Commands (from `%USERPROFILE%\Work\liaozhai-replay`, Python 3.12, Unity 2022.3.10f1; `replay.py` is
`..\game-factory\tools\unity-replay\Tools~\replay.py`):

```
python replay.py open    --project start --work work
python replay.py plan    --package package --repo ..\LiaoZhaiRL --work work
python replay.py install --project start
python replay.py files   --project start --work work
python replay.py reset   --project start --work work
python replay.py steps   --project start --work work --package package [--record]
python replay.py report  --work work
python replay.py verify  --work work --package package
```

## Layout

```
tools/unity-replay/                 Unity package ai.superposition.liaozhai-replay (editor-only asmdef)
  Editor/FileReplay.cs              stage 2: per commit, write the commit's files, import, hash
  Editor/StepReplay.cs, StepOps.cs  stage 3: workflow.jsonl through editor APIs, hash at commit boundaries
  Editor/TableOps.cs                table.edit: cell edit, read-back, the project's 导表 export, delta check
  Editor/ReplayRecorder.cs          stage 4: on-screen replay panel (ReplayWindow)
  Editor/MiniJson.cs, ReplayCommon.cs
  Tools~/replay.py                  driver: open | plan | install | files | steps | status | reset
```

Working output (not in this repository): `%USERPROFILE%\Work\liaozhai-replay\` with `start\` and `end\`
(git worktrees of the clone at the start and end commits), `package\` (rebuilt package), `work\` (plan, blobs,
logs, results).

## Snapshots and line endings

Snapshots are `git worktree add --detach` of the blobless clone, created and handled with
`-c core.autocrlf=false -c core.eol=lf`. Git for Windows ships `core.autocrlf=true`, and the repository has
`* text=auto`, so a default checkout writes CRLF into every text asset and no file hashes like its blob. With LF,
files on disk are byte-identical to the commits (the macOS package's verification relied on the same).

## Stage 0: environment and package rebuild

- Python 3.12.10 and uv 0.13.0 via winget; Unity Personal licence already active.
- No commit after `d8adc87262` matches the scope rule, so the converter still selects 27 commits on the newer
  clone (HEAD 2026-10-10).
- `tools/build_package.py` rebuilt the package with the end snapshot as `UnityProject/`: `workflow.jsonl`,
  `History/commits.json`, `History/summary.json` are byte-identical to `samples/liaozhai-gejin-qipao/` (as
  committed). Two Windows portability bugs had to be worked around with a wrapper (no change to the converter):
  1. `index_guids` stores `str(p.relative_to(root))`, which has backslashes on Windows, so every resolved GUID
     path would read `Assets\LiaoZhaiRL\…`. Fix: `.as_posix()`.
  2. `write_text` / `open('w')` translate `\n` to `\r\n` on Windows. Fix: `newline='\n'`.
- Without the snapshot, 369 of 783 steps differ (no `guid_paths`, 46 different `depends_on`); `git.log` is the same.
- Converter time: 12 min with the snapshot (72,045 GUIDs indexed), 5.5 min without.

## Stage 1: opening the start snapshot

`replay.py open`: `Unity.exe -batchmode -quit -projectPath start -buildTarget Win64`, then `git status`.

- First open (no `Library/`): 1 h 52 min, ~75,500 imports, `Library/` 28 GB, then a crash (exit 1, SIGSEGV in
  `GfxDeviceD3D11Base::UploadTextureSubData2DImpl`) at the very end of the initial refresh: D3D11 could not
  create textures while TextMeshPro's `TMPro_TexturePostProcessor` loaded every imported texture. The RTX 4080
  (16 GB) had 9.3 GB in use by the Unreal sessions. The imported artifacts survived.
- Second open with `-nographics` (no GPU device): exit 0 in 113 s (90 s refresh, 42 reimports). All batchmode
  runs now pass `-nographics`. Slowest part of the first import: 84 `.webm`/`.mp4` cutscenes (VideoClipImporter
  transcodes, up to 10+ min each).
- 10f1 vs 10f1c1: same engine. Visible effects: `ProjectVersion.txt` rewritten to `2022.3.10f1 (ff3792e53c62)`,
  and `packages-lock.json` switches every registry URL from `packages.unity.cn` to `packages.unity.com` and
  reorders some dependency lists; no package version changes. No China-only package is referenced.
- Tracked files Unity changed on the first open (46): `ProjectVersion.txt`, `packages-lock.json`; 36 Spine
  materials (`*_Material.mat`, new shader properties `UseWorldFadeEffect`, `_WorldFadeDir`, `_WorldFadeRadiusOffset`)
  and `Assets/Editor/SpineSettings.asset` (`textureSettingsReference` cleared), all from Spine's import
  post-processor; 4 `.cs.meta` files that held only a GUID gained the default `MonoImporter` block;
  `CSTR.cs`/`SSTR.cs` regenerated by a project tool with CRLF (no content change); two orphan `.meta` files deleted
  (`AssetOptimizer.rar.meta`, `AkWwiseProjectData.asset.meta`; their assets are gitignored).
  After reverting them, the second open changed only 8 (the version, lock file, 4 `.cs.meta`, 2 orphan metas):
  the Spine rewrites happen only on a first import. These 8 are the baseline that later status checks subtract
  (`work/open-result.json`); none is a feature file except `AssetOptimizer.rar.meta` (see Known gaps).
- Errors that do not stop the import: Wwise (`Wwise project needed to populate from Work Units. Aborting.`;
  the Wwise project folder is not opened), Spine and Odin fail to create their settings assets
  (`SpineSettings.asset`, Odin `InspectorConfig.asset`) during the first compile, 6 `NullReferenceException`s from
  project post-processors, and the licensing client's signature check (`Code 10`, ignored; the licence resolves).
  Steam and Stove SDK DLLs load (API updater runs on `StovePCSDK.NET.dll`); no compile errors.

## Stage 2: file-level replay

`replay.py plan` stages every blob the 27 commits need (553 blobs) and writes `work/plan.json` (660 file writes
or deletes, plus the end-state check). `replay.py files` runs `FileReplay.Run` in one batchmode session: per
commit, delete (renames' old paths first), write, `AssetDatabase.Refresh(ForceSynchronousImport)`, hash every
written file, load every written asset, count missing scripts on prefabs. Result (`work/replay-log-files.jsonl`):

- 542 s for the whole run (Unity start included); import per commit 1–92 s (c001, 195 files: 92 s).
- 659 of 660 written files hash-identical to their commit right after import: Unity rewrote none of them.
  The one exception is `Assets/WwiseSettings.xml.meta` (c020), deleted by Unity as an orphan (see Known gaps).
- All 364 written assets load; 212 prefabs, 0 missing scripts; all 103 deletes/renames leave nothing behind.
- End state vs. `d8adc87262`: 418 of 418 expected files match; 18 of 19 files changed later by commits outside
  the feature hold their last feature version (the 19th is `WwiseSettings.xml.meta`); 103 of 103 removed paths
  are absent. `git status` afterwards: 437 feature paths changed, nothing else beyond the stage-1 baseline.
- Import errors per commit: always the same 2, from the start commit itself (two `.mp4.meta` files without a
  valid GUID: `Dialog_对话/Spine/墨宠spine/粽子/录制_2024_08_05_01_03_32_93.mp4.meta`,
  `UI/UI_Assets/开始界面/20s界面动态6.14.mp4.meta`), not from the feature.

## Stage 3: step-level replay

`replay.py steps` runs `StepReplay.Run`: `workflow.jsonl` through editor APIs, one commit at a time, with a SHA-256
check of every file the commit touches at the commit boundary. Per commit:

1. **Support files** are written from the commit first: folder `.meta` files, `.meta` files of existing assets
   (GUID and importer settings as committed), files no step covers, and whole files whose steps cannot all be
   expressed (below). Files the commit edits through APIs are first **synced to the commit's parent** if commits
   outside the feature changed them since the feature last touched them (logged `synced_to_parent`), so every API
   edit starts from the real pre-commit state.
2. **Import steps** (`asset.create`, `asset.import`, `asset.replace`, `table.edit`): the committed file (with its
   `.meta` when the commit has one) is copied in and `AssetDatabase.ImportAsset`ed, as an artist dropping the
   file in does. They run before API edits, which may reference them; the order inside a commit is not observed.
3. **API steps**, each read back after applying:
   - `object.set`: `SerializedObject` on the object found by its local file id
     (`AssetDatabase.TryGetGUIDAndLocalFileIdentifier`; scenes via `GlobalObjectId`), flattened YAML paths mapped
     to `SerializedProperty` (`a.b[3]` → array element, `[m_GUID=…]` / `[guid=…]` / `[component=…]` → element with
     that identity), lists grown or cut, references resolved by GUID + file id. Material saved properties
     (`m_Floats[42]._Name`) are addressed by name. Addressables group entries go through
     `AddressableAssetSettings.CreateOrMoveEntry` / `RemoveAssetEntry` (by reflection), because the group rebuilds
     its serialized list from its entry map.
   - `object.remove`: `Object.DestroyImmediate(obj, true)`; a stripped object (stub of a nested prefab instance's
     object) is not edited, it disappears when nothing references it.
   - `prefab.override`: `PrefabUtility.GetPropertyModifications` / `SetPropertyModifications` on the instance
     whose `PrefabInstance` has the step's file id; targets looked up in the source prefab and prefabs nested in it.
   - `importer.set`: `SerializedObject` on the `AssetImporter`, then `SaveAndReimport`.
   - `asset.move`: `AssetDatabase.MoveAsset` (keeps the GUID); a changed `.meta` follows the move.
4. **Fallback** (`file_fallback`, reason logged per step): `object.add` (a new object must carry the commit's local
   file id; editor APIs assign random ones), `prefab.override` with a collapsed array override (Odin
   `SerializedBytes`, 25 steps), truncated steps, and moves whose source is not in the project. Every step of such
   a file is marked and the file is written from the commit.
5. **Boundary**: `AssetDatabase.SaveAssets`, open scenes saved, then every written file hashed. A file that does
   not match is copied to `work/mismatch/<commit>/` for analysis and restored from the commit, so the next commit
   starts from ground truth. `replay.py report` classifies the mismatches.

Log: `work/step-log.jsonl` (`start`, then per commit `support`, one `step` per workflow step with mode, actions,
errors, read-back counts and wall-clock start/end, `commit` with every file's outcome; `final`).

### Iterations (batchmode, `-nographics`)

| run | API files exact / API files | API steps with errors | read-back failures | main causes fixed afterwards |
|---|---|---|---|---|
| 1 | 11 / 123 | 95 | 26 | moves from a source outside the package; reference lists keyed by `guid`; removals of entries Unity had already dropped; API edits before same-commit imports |
| 2 | 27 / 77 | 6 | 0 | growing a list copies the last element (nested lists included); stripped-object removals recorded as overrides |
| 3 | 45 / 77 | 6 | 0 | shared files changed outside the feature between its commits (sync to parent) |
| 4 | 47 / 77 | 6 | 8 | — (remaining causes are in the package data, below) |

Run 4 (`work/step-log-run4.jsonl`, 1,385 s including Unity start, 858 s of replay):

- 783 steps: 107 API steps on files that came out byte-identical to the commit, 134 import steps (all exact),
  422 fallback steps (all exact, written from the commit), 119 API steps on files that did not match, 1 importer
  step on an asset that is not in the project.
- 557 file writes at commit boundaries, 525 exact; 890 read-backs confirmed, 8 failed (prefab overrides on the test
  scene, below).
- End state identical to the file-level replay (418/418 match, 18/19 changed later, 103/103 absent).
- 6 files were synced to their parent first (shared configuration files that other people's commits changed
  between this feature's commits).

Why the 30 API files that still differ do so (`replay.py report`, `work/step-log-summary.json`):

| cause | files | steps | where the fix belongs |
|---|---:|---:|---|
| `10019_1` read as the integer `100191`: PyYAML follows YAML 1.1, where `_` is a digit separator | 22 | 110 | converter: load Unity YAML scalars without YAML 1.1 implicit typing (also `on`/`yes` → bool, `0x…`) |
| new list entries in the developer's order, but the workflow lists changed paths sorted | 4 | 4 | converter: record the position of added list items (Addressables groups) |
| references to assets added by commits outside the package (金和尚/子楚 skin prefabs, from `9ffd968ce2` and others) | 2 | 2 | package scope |
| test scene `Tester_测试/XW测试场景.unity`: prefab instances of assets outside the package; the scene does not open cleanly | 2 | 3 | package scope |

So every file whose steps the editor can express and whose dependencies are inside the package was reproduced
byte for byte through editor APIs, except where the step data itself is wrong or incomplete.

Findings about the package (for `build_package.py`):

1. YAML 1.1 typing changes values (above). Fixed: follow-up 1.
2. Changed paths are sorted, so the order of new list entries is lost. Fixed: `list_inserts`, follow-up 1.
3. The feature depends on `0106dafbf2e` (2026-07-21, `feat:葛巾形态女侠皮肤特效上传`), which created
   `Player_女侠_形态10_葛巾_皮肤/`. It is on a branch merged after the start commit, not an ancestor of it, and
   `--since 2026-07-30` excludes it; c002 then renames 46 prefabs (94 files with metas) out of that folder.
   A start commit that is the parent of the first feature commit does not contain everything the feature builds
   on when history is non-linear.
4. `table.edit`'s real 导表 export is commit `cdf7c5092e` (parent c026, outside the scope): `bansheegz_database.bytes`
   +7 bytes and `Scripts/Database/Generated.cs`. Including such export commits would let a replay check the table
   step through the project's own exporter. Done without changing the package: `replay.py plan` finds the export
   commit itself (follow-up 2); `build_package.py --include-commit` can also add such commits.

## Stage 4: recording

`replay.py steps --record` runs the step replay in the visible editor (no `-batchmode`) and records it:

- The editor opens with `-replayHandshake <dir> -replayStepDelay 0.5`. The replay switches to in-process import
  (`AssetDatabase.ActiveRefreshImportMode`, session only), opens an empty scene, docks the **LiaoZhai Replay**
  panel next to the Scene view (commit, step, op, target, mode, boundary counts, recent steps), writes `ready`
  and waits for `go`.
- The driver finds the editor's main window, sizes it to 1920×1080 without activating it, and starts ffmpeg's
  `gfxcapture` (Windows Graphics Capture) on that window handle only: other windows, other monitors and the
  cursor are not recorded, and the window may be covered. Output: H.264, 30 fps, fragmented MP4.
- Visible mode pauses 0.5 s after each API or import step and selects and pings what the step changed, so the
  Project window and Inspector show it; fallback steps take no time on screen.
- After the last step the editor writes `done` and waits for `stopped`; the driver stops ffmpeg while the window
  still exists, then the editor exits.
- `video-verification.json` (`liaozhai.video-verification/v1`): video hash, size, duration, resolution, frames, a
  full decode (`ffmpeg -f null`), workflow and step-log hashes, every step id with its video start/end time
  (editor wall clock minus the wall clock of the first captured frame), each commit boundary's video time and
  counts, and the editor and recorder exit codes.

Machine slots (shared with `tools/ue-heavy.ps1` on the PC): every Unity run holds one of the three
`Global\ue-heavy-jobs` slots; a visible or recorded run also holds the single `Global\ue-gpu-jobs` slot for its
whole length, since several GPU jobs do not fit in 16 GB of VRAM. `-nographics` batch runs take no GPU slot. Waits
and holds are logged to `.recording\_heavy-jobs.jsonl` in the same format.

Unlike the vendor's `video-verification.json` (one summary record with `all_action_ids_in_order`), every step is
aligned individually, and the log it is aligned against carries a hash check at every commit.

Attempts on this PC (each found one more thing the visible editor does that batchmode does not):

1. Odin Inspector's EULA dialog on the first GUI launch; the user accepted it once (it is remembered).
2. "Scene modified externally": the last-opened test scene was open while the replay rewrote it. The replay now
   starts from an empty scene and closes scenes it opened before each boundary.
3. "Save Scene": saving the dirty untitled scene at a boundary opens a file dialog; only scenes with a path are
   saved now.
4. A hang at c018: the visible editor imports through worker processes; two workers dropped their connection and
   `AssetDatabase.Refresh` waited forever. In-process import fixed it.
5. A complete replay (783 steps, 22 min) whose video was unusable: the editor closed its window before ffmpeg
   stopped, `gfxcapture` hung, and the killed ffmpeg left an MP4 without its index. Fixed by the done/stopped
   handshake and fragmented MP4.

Other GUI-only effects: `ProjectSettings/PackageManagerSettings.asset` gets its registry rewritten from
`packages.unity.cn` to `packages.unity.com` (10f1 vs 10f1c1 again), and the Addressables API writes
`m_currentHash` into `AddressableAssetSettings.asset`. Neither is a feature file; both are reported by the status
check and reverted.

Result (attempt 6, `work/replay.mp4`, `work/video-verification.json`, `passed: true`):

- 1,111.6 s (18.5 min), 33,348 frames at 30 fps, 2858×1534 (the 1920×1080 window at 150 % display scaling),
  108 MB H.264; full decode without errors; recorder exit 0. The editor exits 2 because of the known
  `WwiseSettings.xml.meta` miss in the end-state check, as in batchmode.
- All 783 step ids present, commits in order; first step at 6.6 s, last step end at 1,101.5 s.
- Alignment measured from the picture: offset 1.1 s (ffmpeg encoder lookahead plus repaint); 335 of 437 panel
  header changes fall within ±0.07 s of a step end. For the 361 steps that take screen time, the delay from the
  aligned step end to the screen showing it is p50 −0.02 s, p90 0.97 s, p99 5.5 s, max 97 s (91 % within 1 s):
  after commit boundaries and heavy imports the editor repaints late. Fallback steps take no screen time; a burst
  of them shows as one jump (e.g. c022's 88 fallback files).
- Checked by eye at aligned times: W00001 (first model import), W00356 (c013, `葛巾形态近战花妖.prefab` in the
  Inspector), W00467/W00468 (c017→c018 boundary, visible about 3 s late).
- Step results equal batch run 4 except two files: `葛巾形态默认花妖（洪荒）.prefab` in c013 and c017. Showing the
  prefab in the Inspector lets Behavior Designer's inspector write its own UI fields (`gizmoViewMode: 2 → 0`,
  `showBehaviorDesignerGizmo: 1 → 0`); the committed values are the developers' inspector state.
- The Unity account button (top left) shows the signed-in account's initials.

## Follow-up 1: converter fixes (package rebuilt, 811 steps)

Stages 0–4 used the package as first built (783 steps). The converter was then fixed (`docs/liaozhai.md`,
"Rebuild"): Unity-faithful YAML typing, `list_inserts` for added list items, LF output and forward-slash paths on
Windows. The rebuilt package has 811 steps (28 `-0 → 0` position changes YAML 1.1 had hidden). Step replay on it
(`work/step-log-v2.jsonl`, batchmode, 775 s):

| | package v1 (run 4) | package v2 |
|---|---:|---:|
| API-edited files byte-identical at commit boundaries | 47 / 77 | 73 / 78 |
| file writes exact at commit boundaries | 525 / 557 | 550 / 557 |
| API mismatches from the converter (YAML 1.1, list order) | 26 | 0 |
| API mismatches from dependencies outside the package | 4 | 4 |

The replay uses `list_inserts` to create Addressables entries in the committed order and to move added elements
of other keyed lists (`m_Component`, material lists) to their committed index. The 78th API file is the
workbook of the table edit (below), whose cells are verified but whose zip bytes cannot match Excel's.

## Follow-up 2: `table.edit` through the project's 导表 export

`table.edit` now runs in API mode (`Editor/TableOps.cs`) instead of importing the committed workbook:

1. The workbook starts from the commit's parent (sync to parent). The step's cells are read with ExcelDataReader,
   the reader the project's importer uses, and must hold the step's `before` values.
2. The project's export runs once as a baseline: `FeishuImporter.ExecuteExecelFile` for every workbook in
   `墨境导表文件夹`, the importer's DIALOG merge, `ImportBG` per table, `FKImport`, then the BGDatabase editor
   save (`BGRepoSaver.SaveRepo`, what `DatabaseImporterEditor`'s final `SaveBGDataRepo` runs under its window).
3. The cells are set in the sheet XML of the `.xlsx` and read back with ExcelDataReader (`after` values).
4. The export runs again, and the change it makes to `Assets/StreamingAssets/bansheegz_database.bytes` is compared
   with the change in the real export commit, which `replay.py plan` finds as the child of the feature commit that
   touches the database (`cdf7c5092e` "导表", child of c026). The database begins with a value that changes on
   every save, so the comparison is by content: size change, and how often each cell's old and new text occurs.
5. The database is restored (it is not a feature file); the workbook is restored from the commit at the boundary.

Deliberately not run: the importer's entry point `ImportTableFromLocalFileAsync`. Its table examiner shows
dialogs whose first button is "发送", which batchmode would press, posting the examiner's findings to the team's
chat through `FeishuImporter.SendMessage`; it also opens a text file with the shell. Also not run: the post-import
steps of `DatabaseImporterEditor` (sprite atlases, colliders, resource refers) and BGDatabase code generation
(`Generated.cs`, which recompiles scripts).

Result (`work/step-log-v3.jsonl`, W00799, c026 `形态皮肤_PlayerSkins.xlsx`, sheet 形态皮肤_SkillGroupsSkins R25C19):
cell read back as `MODEL_女侠_形态10_旗袍` before and `MODEL_女侠_形态10_旗袍_无鞋` after the edit; the
replay's two exports (23,647,896 → 23,647,903 bytes) change the database exactly as `cdf7c5092e` does
(25,881,800 → 25,881,807): size +7, the new text +1 occurrence, the old text unchanged. The replay's database is
smaller because the project lacks other people's table changes; the delta isolates the edit. A first attempt
without the BGDatabase save showed no change at all: `BGRepo.Save()`, which `FKImport` ends with, only serializes
to a byte array, and the file is written by the editor save afterwards. No file outside the feature was left
changed (database restored, BGDatabase auto-backups removed).

## Known gaps

- Two feature files are `.meta` files of gitignored assets: `Assets/Editor/AssetOptimizer.rar.meta` (c016;
  `*.rar` ignored) and `Assets/WwiseSettings.xml.meta` (c020; `Assets/WwiseSettings.xml` ignored). The asset
  never exists in a checkout, so Unity deletes the `.meta` when it notices (on open, on a refresh, or on exit).
  The developers' commits carry them because the asset existed on their machines.
- `object.add` cannot go through editor APIs with the commit's local file ids (350 steps, 105 files fall back to
  the committed file), nor can collapsed Odin `SerializedBytes` overrides (25 steps).
- `table.edit` (follow-up 2) edits the sheet XML, not Excel, so the workbook's bytes differ and it is restored from
  the commit; the export check covers the database, not `Generated.cs` or the post-import generators.
- Scenes: prefab overrides on `Tester_测试/XW测试场景.unity` cannot be applied (instances of assets outside the
  package); the scene file falls back.
- Visible-mode side effects: inspecting objects can change them (Behavior Designer gizmo fields), the
  Addressables API writes `m_currentHash`, and the GUI rewrites the package registry in
  `PackageManagerSettings.asset`. Batchmode results are the reference; the recording is for viewing.
- Step order inside a commit is not observed; the replay runs imports before API edits.
- Only the feature's in-scope files are applied. Changes other people made between the start and end commits are
  not, so intermediate projects are the start commit plus the feature, not the real tree at each commit. All
  written assets still load without missing scripts.

# Helper brief: LiaoZhai Unity replay (Track A)

**Role.** Runs and extends the Unity replay of LiaoZhaiRL feature packages (`tools/unity-replay/`: Unity editor package
+ `Tools~/replay.py` driver; converter `tools/build_package.py`): starts from the Unity project at a feature's start
commit, applies the feature's commits file by file and its `workflow.jsonl` steps through editor APIs, verifies every
commit boundary by SHA-256 against the real commits, and records the editor (`replay.mp4` + `video-verification.json`).

**Spawn when.** For Track A: when a LiaoZhai feature package needs its replay (a new feature beyond the pilot), or to
reproduce the pilot 葛巾_旗袍 on a new machine. Also early on a new machine if liaozhai-night's creation replay is
planned, because that replay reads the LiaoZhaiRL end snapshot this helper creates.

**Produces.** `{{GF_ROOT}}\liaozhai-replay\` (`start\`, `end\` worktrees, `package\`, `work\` with plan, logs,
`replay.mp4`, `video-verification.json`), fixes to `tools/unity-replay/` and `tools/build_package.py`, results per
stage in `docs/unity-replay.md`.

**Original prompt:** [../original/helper-liaozhai-replay.md](../original/helper-liaozhai-replay.md) (it built the replay
in stages 0-4 from zero; for a from-scratch variant, reuse those stages).

## Placeholders

| Placeholder | Example (the pilot) |
|---|---|
| `{{GF_ROOT}}` | `C:\Users\<name>\Work` |
| `{{COORDINATOR_ID}}` | session id of the coordinator |
| `{{NOTES_DIR}}` | `%APPDATA%\Claude\side-session-notes\<group id>` |
| `{{FEATURE}}` | `葛巾_旗袍` |
| `{{START_COMMIT}}` | `2bca8019de2f984fefd1335a8ed0dc11d43322d5` (parent of the first feature commit) |
| `{{END_COMMIT}}` | `d8adc87262be0d38c8806c49bcf2a8048e2c1bc3` |
| `{{EXPECTED}}` | `27 commits, 811 steps (783 before the converter fixes), 418 end-state files` |
| `{{UNITY_EDITOR}}` | `C:\Program Files\Unity\Hub\Editor\2022.3.10f1\Editor\Unity.exe` |

## Brief

```text
Background:
game-factory ({{GF_ROOT}}\game-factory, superpositionhq/game-factory) produces game-creation data and coordinates
Claude Code sessions on this PC; a coordinator session ({{COORDINATOR_ID}}) spawns and supervises everyone, and several
Unreal game sessions share the CPU and the single GPU. Track A turns the real git history of LiaoZhaiRL
(MapleLeafGitHub/LiaoZhaiRL, a shipped Unity 2022.3.10f1c1 game, fully authorised for this work including sharing)
into feature-sized creation packages with tools/build_package.py (schema liaozhai.unity-workflow/v1). The Unity
replay exists: tools/unity-replay/ (Unity package, editor-only asmdef: FileReplay, StepReplay/StepOps, TableOps,
ReplayRecorder) and Tools~/replay.py (open | plan | install | files | reset | steps [--record] | report | verify).
Read README.md, AGENTS.md (Track A rules: they each come from a failure), CLAUDE.md (if present), docs/plan.md
section A3, docs/liaozhai.md, docs/workflow-format.md, docs/vendor-packages.md, docs/unity-replay.md (all of it),
samples/liaozhai-gejin-qipao/, and the shared note liaozhai-unity-replay.md.
Target: feature {{FEATURE}}, start {{START_COMMIT}}, end {{END_COMMIT}}; expected {{EXPECTED}}.
Machine: Windows 11; Unity {{UNITY_EDITOR}} (2022.3.10f1; any Unity 6 install must NOT be used); Python 3.12 + uv;
git + gh. The LiaoZhaiRL clone belongs at {{GF_ROOT}}\LiaoZhaiRL (blobless, core.longpaths=true,
core.quotepath=off); each snapshot is ~42 GB.

Rules:
- Use the commit-always skill: commit to game-factory main after every meaningful step (tools/unity-replay/,
  tools/build_package.py, docs/unity-replay.md, the sample if the converter output changes) with a descriptive
  message, never end a turn with uncommitted work, never push unless the coordinator says so. Stage only the paths you
  changed. Never commit packages, snapshots, git.log with asset diffs or videos to game-factory.
- Every GPU launch goes through {{GF_ROOT}}\tools\ue-heavy.ps1: a visible or recorded Unity editor holds the GPU slot
  for its whole length; batchmode runs use -nographics and take a CPU slot. One Unity process at a time. The
  coordinator schedules long GPU captures (the recorded step replay): ask before starting one; only the coordinator
  enqueues recordings.
- Never write the names Superposition or game-factory into anything that ships inside a game or a package.
- Deliverable copies are scrubbed of user paths, the user name and Claude/Anthropic/Opus mentions; authors are
  anonymised as dev_NN and the leak scan (real names, e-mails, C:\Users\..., /Users/..., /home/...) runs over every
  text file of a package before it is called done. Step reasons are commit messages, never model-written.
- Datasets for the Unreal games follow layout v1 (README.md, git.log, workflow.jsonl, replay.mp4, UEProject/,
  ReplayScripts/, Gameplay/<game>_S<n>.mp4, Screenshots/, Build/, manifest.json; repo Dataset/ = same minus UEProject/
  and Build/). A LiaoZhai package keeps its own layout (docs/workflow-format.md); its replay outputs mirror the vendor's
  replay.py + replay.mp4 + video-verification.json.
- Hard-won requirements that must stay true:
  * Never reset or check out the blobless clone and never run a command that needs every blob of a tree; use
    plumbing, the GitHub trees API (recurse: it truncates), and `git worktree add --detach` for snapshots, created and
    handled with -c core.autocrlf=false -c core.eol=lf so files hash like their blobs. Wait for any running checkout
    (.git\index.lock) before commands that take the index lock. Check free disk before each snapshot.
  * Converter: UnityLoader (no YAML 1.1 typing), key list items by identity, collapse per-element array overrides,
    record list_inserts, UTF-8 LF writes and as_posix paths, rerun with the end snapshot so GUIDs resolve.
  * After any Unity open, list what Unity rewrote (git -C <snapshot> status --short) and account for it in
    verification (baseline in work\open-result.json).
  * Never call FeishuImporter.ImportTableFromLocalFileAsync: its dialogs would post to the team's chat ("发送") in
    batchmode. table.edit uses TableOps (sheet XML edit, read-back, the project's 导表 export, delta check).
  * Recording: Windows Graphics Capture (ffmpeg gfxcapture) of the editor window only, ready/go/done/stopped
    handshake, fragmented MP4, in-process import in visible mode, empty scene, no untitled-scene save. Batchmode
    results are the reference; the recording is for viewing.
  * Licence prompts are the user's: Unity licence activation (Hub -> Preferences -> Licenses) and the Odin Inspector
    EULA on the first visible launch. Never accept a licence for them; ask the coordinator and continue elsewhere.

Task:
1. Environment: Python 3.12 + uv (winget Python.Python.3.12, astral-sh.uv) if missing; check the Unity licence; clone
   LiaoZhaiRL blobless if it is not there (ask the coordinator if gh lacks access); create
   {{GF_ROOT}}\liaozhai-replay\start (worktree at {{START_COMMIT}}) and ...\end (at {{END_COMMIT}}).
2. Rebuild the package with tools/build_package.py (end snapshot as the project) into
   {{GF_ROOT}}\liaozhai-replay\package\; for the pilot, workflow.jsonl / commits.json / summary.json must be
   byte-identical to samples/liaozhai-gejin-qipao/; for a new feature, compare counts with {{EXPECTED}}.
3. replay.py open (first import, -nographics; record time, errors, the on-open rewrites), plan, install, files
   (file-level replay: per commit apply, import, hash; end state against the end commit), then steps (step-level
   through editor APIs, fallbacks marked, hash at every commit boundary), report, verify.
4. Ask the coordinator for a GPU slot, then steps --record: replay.mp4 + video-verification.json with every step
   aligned to video time; report alignment accuracy.
5. Write results per stage and known gaps into docs/unity-replay.md (one results table, like the pilot's); fix tool or
   converter bugs at the source and rerun what they affect.

Done = the feature replays file-level and step-level with hash results per commit and an end-state match (every
mismatch explained), replay.mp4 + video-verification.json exist under {{GF_ROOT}}\liaozhai-replay\work\, docs and
tool changes are committed on game-factory main, and the coordinator has the commit sha and the results table.

Shared notes folder for this group of sessions (outside the repo; read siblings' notes there, leave hand-over notes or
large findings there instead of pasting them into messages): {{NOTES_DIR}}
```

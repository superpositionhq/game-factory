# Game deliverable

One game packaged for a buyer: the finished Unreal project plus the observed record of how it was made and
played. Built by `tools/package-game.ps1` (Windows PowerShell 5.1, no Python) from the game repo, its machine logs
(`.recording\<game>\`), its gameplay bundles (`recordings\<game>\`) and its packaged build. The tool only reads those;
it writes to `%GF_ROOT%\deliverables\<game>\`. Plan context: [plan.md](plan.md), "Deliverable per game".

What goes to buyers is the **dataset layout v1.1** delivery built from this package (section
[Dataset layout v1.1](#dataset-layout-v11-the-delivery) at the end); the package described
first is the verified, scrubbed intermediate it is assembled from.

```
powershell -ExecutionPolicy Bypass -File tools\package-game.ps1 <game> -Commit milestone                       # with store content
powershell -ExecutionPolicy Bypass -File tools\package-game.ps1 <game> -Commit milestone -DryRun               # what it would take
```

`-Commit` takes any rev; `milestone` means the commit of the highest `milestone/autoplay-<n>` tag (HEAD when there is
none). A release: `-Commit release/1.0 -Version 1.0` (README "Version 1.0 (tag release/1.0)", `manifest.json`
`version`/`release_tag`). `-ExcludeRuns id,id` leaves validated runs out (e.g. superseded recordings). `-PlayNote`
adds a launch note to the README's Play section. `-OnlyCommitRuns` keeps only gameplay runs played on a build of the
packaged commit itself (e.g. after a fix that changed what the game looks or sounds like). `-Screenshots
auto|repo|stills` chooses the README images (auto: the project's `docs/screenshots/`, else stills of the packaged
runs). `-ExcludeSessions id,id` leaves those sessions' rows out of `History/actions.jsonl`; sessions that ran this
packager are always left out (the hooks log their tool calls under the game when their working directory is inside it,
but packaging is not creation work; `history.actions.jsonl.sessions_left_out` in `manifest.json`). Other options: `-Build <dir>` (+ `-BuildCommit <rev>` when the dir has no `build_info.json`),
`-AllowDevelopmentBuild`, `-IncludePdb`, `-StoreFolders a,b` (extra store paths), `-RepoPath` (package another clone),
`-OutRoot`, `-ZipLevel Fastest|Optimal|NoCompression`, `-NoZip`, `-Force` (replace an existing package), `-KeepRefused`,
`-NoScrub` (diagnostics only; the scan then refuses).

## Output

`deliverables\<game>\<game>_<sha8>\` (always with store content; no `_nostore` variant since 2026-10-12), plus a `.zip` of the same name
whose single top folder is the package. Next to them, outside the package: `package-log.jsonl` (one row per run:
sizes per section, warnings, notes), `<name>.leaks.tsv` (report-only findings, see Scrub) and, on refusal,
`<name>.refused-hits.tsv`.

| Path | Content | Source |
|---|---|---|
| `UEProject/` | the repo tree at the commit, without `Binaries/ Intermediate/ Saved/ DerivedDataCache/` | `git ls-tree` + `git cat-file`; Git LFS pointers replaced by the object from the repo's own `.git\lfs\objects` (never downloads; a missing object is an error) |
| `StoreContent.tsv` | every store-content file: `status` (included/dropped), path, bytes, sha256, source (git, git-lfs, working-tree), why it counts | see Store content |
| `workflow.jsonl` | the creation log at the commit (also in `UEProject/`) | `git cat-file <sha>:workflow.jsonl` |
| `git.log` | every commit up to the commit, oldest first (topological): `commit`, `Parents`, `Author`, `AuthorDate`, `Committer`, `CommitDate`, message indented 4, full text diff (first parent, renames detected) | `git log -p --no-textconv --full-index` |
| `History/` | `commits.jsonl`, `actions.jsonl`, `builds.jsonl`, `runs.jsonl` | `.recording\<game>\`, rows limited to the lineage (below) |
| `Gameplay/<run>/` | every validated gameplay bundle of the lineage, as recorded (video, audio, inputs, telemetry, outcome, metadata, validation, manifest, `raw/`) | `recordings\<game>\` |
| `Gameplay/summary.md`, `summary.json` | one row per run: scenario, seed, skill, result, score, durations, game fps, inputs, build, validation; runs left out and why | derived |
| `Build/` | the packaged Windows build (`.pdb` left out unless `-IncludePdb`) and our own `build_info.json` | see Build |
| `README.md` | hero image, version, what the game is, screenshots, how to play and open it, scenarios, observed vs derived, licences, store content, integrity | generated from the project's `README.md`, `Docs/*.md`, `Docs/ThirdPartyNotices.md`, `assets.manifest.json` and the package |
| `Screenshots/` | the README's images: the project's `docs/screenshots/` at the commit when it has one, else 3–4 stills (`recordings\<game>\_stills\<run>_NN.jpg`) of the runs in this package only, round robin over the runs (middle frame first); the first is the hero | copied |
| `scrub-report.json` | what the scrub changed (below) | derived |
| `manifest.json` | package metadata and `files[]`: path, bytes, sha256 of every file (after the scrub) | derived |

**git.log details.** Header `GIT-LOG 1` plus three comment lines. Authors and committers are anonymised as `dev_NN`
(numbered by first appearance, keyed by name). Binary files: `Binary file <path>: sha256 <old> (<n> bytes) -> sha256
<new> (<m> bytes)` (`(none)` for added/deleted); Git LFS pointer diffs collapse to `Git LFS file <path>: ...` with the LFS
oid, which is the sha256 of the content. CR bytes in diffs are kept (the log is written byte-for-byte as Latin-1).
Agent trailer lines in commit messages (`Co-Authored-By: Claude…`, `Generated with Claude Code`) are dropped here; diff
lines are never dropped.

**Lineage.** Everything is tied to the commit's ancestry (`git rev-list <sha>`): `commits.jsonl` rows by `sha`,
`builds.jsonl` by `commit`, `runs.jsonl` by `build_commit`, gameplay bundles by `metadata.build.commit`;
`actions.jsonl` rows by `time` up to the commit's committer time (work after the commit is not part of it).

**Gameplay.** A bundle is included when it has no `FAILED` marker, `validation.json` status is `ok` or `warn`, and its
build commit is in the lineage. Failed runs are never shipped (they are counted in `summary.md`).

## Build

In order:

1. `-Build <dir>` (a folder holding `Windows\` or the build itself). Commit from its `build_info.json`, else `-BuildCommit`
   (stated, `commit_verified: false`); either must be in the lineage.
2. The newest successful packaged **Shipping** pipeline build (`builds\<game>\<sha8>-shipping\`, `build_info.json`
   status ok, commit in the lineage).
3. The game session's own Shipping package `games\<game>\Packaged\Windows\` (has `*-Shipping.exe`). Its commit is
   `source.commit` of the newest successful packaging row in the working tree's `workflow.jsonl` (any `*package*` op for a
   Shipping target or config, with `result: ok` or `exit_code: 0`; games name it `build.package`, `package.exit`,
   `package.build`), accepted only if that row was written within 20 minutes of the exe and the commit is in the
   lineage. `commit_verified: false`; the README says "as stated by the build log". Note the session packages its
   working copy, so uncommitted edits at that moment may be in the build.
4. With `-AllowDevelopmentBuild`: the newest Development pipeline build of the lineage (flagged in README and warnings).

**Store art check.** When the game keeps store packs out of git (git-ignored folders under `Content/`), a pipeline
build is made from a clean clone and has none of that art. Every build is therefore checked: the pack folder names
(`Content/<Pack>`, or the subfolders of an ignored `Content/Fab`) must appear in the build's `.utoc`/`.pak` directory
index. Pipeline builds without any are skipped (warning); a chosen build without any stops the tool. The result is in
`Build/build_info.json` (`store_packs_outside_git.cooked` / `not_in_pak_index`; a pack that no cooked map uses is
legitimately absent, e.g. tower-defense `GoodSky`). Gameplay runs get the same check on the build they were played on
(`Store art in build` in `Gameplay/summary.md`): tower-defense's validated run was played on the clean-clone build
`b697a896`, so its video shows the game without the Fab art.

Otherwise the tool stops before copying anything. A build older than the packaged commit is allowed and reported as a
warning. `Build/build_info.json`: `project, config, commit, commit_verified, source, built_start, built_end, exe,
debug_symbols`.

## Store content

Fab Standard licence content may ship inside the packaged game but not as source, so every package exists in two
variants. Store content is, per file:

- any path with a folder named `Fab` (e.g. `Content/Fab/...`, island-survival, liaozhai-night);
- paths named by `assets.manifest.json` at the commit: every object whose `licence`/`license` matches *Fab Standard* or
  *Marketplace*, or whose `origin`/`source` is `fab`, contributes its `folder`, `copied_to`, `file`, `path`, `ue_assets`,
  `ue_path`, `installed_to` values (`/Game/X` → `Content/X`, `{a,b}` expanded, globs allowed; an entry matches the file,
  the object path without extension, or a folder prefix). This covers packs kept in their own folders (horror-escape,
  rally-racer, siege-catapult, stealth) and per-file entries;
- folders under `Content/` that are git-ignored in the game's working tree and not tracked at the commit (tower-defense
  keeps its Fab packs in `Content/<Pack>/` out of git; they are restored by `Scripts/fetch_fab_ue.sh`). These are copied
  from the working tree (source `working-tree` in `StoreContent.tsv`);
- `-StoreFolders`.

"Store content" means everything that came from the Fab store, including the few Fab items under CC BY 4.0 (their
licence column says so). Packages and datasets always include it (user decision 2026-10-12; `-WithoutStoreContent`
is retired and refused). `-DryRun` prints the split per folder.

## Scrub (deliverable copies only)

Decision of the user (2026-10-11): what leaves the PC is scrubbed; the game repos, `.recording` and `recordings` are
never modified. Every text file of the package (no NUL byte in the first 8 KB, or a UTF-16 BOM; under 256 MB) is
rewritten in place, keeping its encoding, with these rules in order (`scope`: `json` = `.json/.jsonl` only, for
JSON-escaped forms; `lines` = other text files except `git.log`; `logs` = `.json/.jsonl`, `git.log` and `History/*`):

| Rule id | Does |
|---|---|
| `base64-payload` | first: every base64 run of 256+ characters in the shipped logs (`logs` scope) → `<base64 omitted, N bytes, sha256 <16 hex>>` (screenshots and binary payloads in recorded tool responses; nobody needs them in a dataset, the logs shrink, and random user-name matches inside them go away). Decided 2026-10-12; the user name stays a hard block everywhere else |
| `agent-trailer` | removes `Co-Authored-By: Claude…` and `…Generated with Claude Code…` lines (`lines`), the same inside JSON strings with their preceding `\n` (`json`); in `git.log` the commit-message trailers are dropped while the log is written |
| `agent-identity` | `Claude (agent)` → `dev`; `Claude [Opus 5.5] <noreply@anthropic.com>` → `dev <dev@example.invalid>` (also `\u003c…\u003e`) |
| `banned-name` | the names Superposition / game-factory, with the defaults of `ue-pipeline/scrub-history.ps1`: schema prefix `superposition.` removed, then Superposition → Studio, game-factory → studio-tools (game_factory, GameFactory, gamefactory variants), case-preserving |
| `git-identity` | the repo's git author/committer names, their words of 4+ letters and e-mail handles → the same `dev_NN` as in `git.log`; a term containing a digit (a handle) also takes letters/digits glued to its end, so account names built on it go too |
| `username` | the account name (`$env:USERNAME`) as a word, including inside user paths (`C:\Users\<name>`, `C:\\Users\\…`, `c:/users/…`, `/c/Users/…`, `/Users/…`) → `dev` |
| `email` | e-mail addresses → `<redacted-email>`, except placeholders (`example.com/org/net`, `*.invalid`, `*.test`, `localhost`) and `git@github.com`-style service addresses; file names such as `icon@2x.png` are not addresses |
| `agent-mention` | `claude code` → `agent-tool`, `claude-<model>…` → `agent-model`, then remaining Claude → Agent/agent, Anthropic → Provider/provider (case kept) |

`agent-mention` also covers model names: `Claude Opus 5.5`, `claude-opus-5-5`, and a bare `Opus <version>` → `agent-model`;
a standalone capitalized `Opus` in prose → `Model` (codec identifiers such as `libopus`, `opus_*`, `AudioFormatOPUS` stay).

The dataset (layout v1.1) carries no `History/`: only `git.log` and `workflow.jsonl` of the logs go into it.

**Blocking terms (user rule, 2026-10-11).** Besides the two names, `Claude`, `Opus` and `Anthropic` must never appear in a
package: any case-insensitive hit left in a path, a text file or a binary (ASCII or UTF-16LE) refuses it. The only
exception is the Opus **audio codec**, allowed by an exact allowlist of codec forms (see below); each allowed hit is
listed for review in `<name>.allowlisted.tsv` next to the package (path, kind, offset, word); inside the package `scrub-report.json` (`allowlisted_hits`) carries counts only, since the words would put the terms into its text. The account name blocks
anywhere in a package as well, binaries included (user rule, 2026-10-11 ~22:15): UE assets keep their editor
import-source paths, which must be rewritten in the project (the pipeline's `scrub-import-paths.py`) before packaging.
It is enforced as any substring, in text as in binaries
(paths that lost their separators, such as a compiler error's `C:Users<name>Work…`, and the machine name
`<NAME>-PC` are scrubbed by their own rules first). Exact tokens that merely contain it are allowed: UE's `zh_XIANG` /
`zh-xiang` locale ids (also when glued into a locale table, recognised by the `zh_`/`zh-` prefix) and liaozhai-night's
place name `WuXiangShan…` (无相山) with its asset names. `-PendingCleanBuild` tolerates it inside `Build/` only, producing a
package marked "pending clean build" (README banner, manifest `status`).

How "opus" is matched (it is four letters and occurs by chance in compressed bytes and ordinary words such as
`stopUsing`, `Octopus`, base64): only as a word of its own, i.e. at a non-letter or lower→upper camel boundary, not
followed by a lowercase letter, and spelled `opus`, `Opus` or `OPUS`; in binaries it must also sit in a run of at least
8 printable characters (a string, not pixel or bitstream data). `claude` and `anthropic` count as any substring.

Allowlist (exact forms, matched against the whole word around a hit; a word may carry other `:`/`/`-joined segments,
such as C++ scopes): Opus codec forms seen in the engine binaries (EOS SDK, WebRTC): `third_party/opus/...` source
paths, `libopus…`, `opus_*` and `OPUS_*` symbols and constants, `WebRtcOpus_*`, `WebRTC-…Opus…` field trials,
`…AudioEncoder…Opus…`, `Opus{Impl,Config,Decoder,Encoder,Custom,…}…`, codec source file names (`*opus*.c/.cc/.h`),
`opus/48000/2`, `audio/opus`, `A_OPUS`, UE's audio format key `AudioFormatOPUS…`, and in binaries only the bare codec name `opus`; UE's locale ids `zh_XIANG` /
`zh-xiang` (which contain the account name). Allowed hits are listed in `<name>.allowlisted.tsv` (outside the package) and
in the rescan tsv.

Compressed media streams (user rule, 2026-10-12): random compressed bytes spell short terms now and then (`OPUSOb` in
H.264 slice data). Inside the audio/video stream payload of `.mp4` / `.mkv` / `.mka` / `.wav`, a hit on a short term
(`claude`, `opus`) or on the account name (coordinator rule, 2026-10-19: ~10 GB of H.264 per game spells it a few by chance) is listed as `allowed-stream-*` in `<name>.allowlisted.tsv` (file, offset, term and the bytes around
it) instead of refusing; `scrub-report.json` counts them (`allowlisted_hits.media_stream`). The payload is the `mdat`
data of an MP4 whose tracks are all video or audio (`hdlr` `vide`/`soun`), the frame data of Matroska blocks on video
and audio tracks, and the WAV `data` chunk. Container metadata, tags, chapters, subtitle or other tracks and file names
are outside it and still refuse, as does a file with more than 1000 such hits. The other long terms
(`anthropic`, `superposition`, `game-factory`) refuse everywhere, and the account name everywhere outside the payload; a match on one goes to a person for review.

Reviewed exceptions: `tools/package-reviewed-hits.tsv` holds single binary hits that a person judged to be data, keyed
by the file's sha256 + byte offset + word, with the reason (the first: `opusWTTj` in the raw grayscale pixels of the
Fab PSD `fantasy_gui_4/sources/psd/fg4_glass_01.psd`). Any other file, or another version of that file, still blocks.

`-Rescan <package dir>` checks an existing package against the current rules and writes `<dir>.rescan-hits.tsv`
(blocking hits, account name in `Build/`, allowlisted hits); it changes nothing.

A word start also counts right after a JSON escape (`\n`, `\t`, …), whose letter would otherwise hide the boundary.
Gameplay bundle `manifest.json` entries of rewritten files get the new bytes and sha256.

Then every file is scanned again. **The package is refused** (exit 2, staged folder deleted unless `-KeepRefused`, no
zip, hits in `<name>.refused-hits.tsv`) on any remaining match in a file path or text file of: the two names, `claude`,
`anthropic`, the account name, an e-mail address (same pattern), a git identity term; or the two names in any binary
file (ASCII or UTF-16LE). Binary files are never edited: the account name and agent names found in binaries (UE assets
embed their import source paths, the exe its build paths) are listed by category in `scrub-report.json`
(`binary_files_with_findings`). Other user-folder paths (`C:\Users\<other>`, `/home/…`) and the account name as a bare
substring are written to `<name>.leaks.tsv` for review, not enforced.

`scrub-report.json`: `rules[]` (`id`, `description`, `replacements`, `files`), `git_log` (trailer lines removed,
identities numbered), `files_touched[]` (path and replacements per rule id), `binary_files_with_findings[]` (path,
categories, encodings, hits, capped at 20 per file), `verification` (remaining text/path hits, binary name hits). It
never contains the original values.

## Observed vs derived

| Data | Observed (written when it happened) | Derived |
|---|---|---|
| `workflow.jsonl` | every row, by the builder at the time of the operation; human directions as `actor:"user"`, `op:"user.direction"` rows (a neutral summary of what was directed and why, not the message), logged before the work they cause, which carries `"direction": "<row id>"` (commits: `Direction: <row id>`) | nothing (scrubbed copy); the dataset README counts the directions |
| `git.log` | commits, messages, dates, file contents | diffs (git), sha256 of binaries, `dev_NN` |
| `History/` | hook and pipeline rows | the lineage filter |
| `Gameplay/` | video, audio, inputs, telemetry, outcome, clock samples | `metadata.json` estimates, `validation.json`, `summary.*` |
| `UEProject/`, `Build/` | the committed project, the packaged build | nothing |
| `README.md`, `StoreContent.tsv`, `scrub-report.json`, `manifest.json` | | written by the tool |

## Measured (2026-10-11)

| Game @ commit | Full: folder / zip | Without store: folder / zip | Store files dropped | Build/ | Gameplay runs |
|---|---|---|---|---|---|
| **liaozhai-night 1.0** @ `7239cc20` (`release/1.0`) | 9.60 / 8.74 GB (1,935 files) | 3.21 / 2.93 GB (1,177) | 758 (6.39 GB, `Content/Fab` from the working tree) | pipeline `7239cc20-shipping` (verified, all 3 packs cooked) | 3 (S1–S3; S2 warn: 54 fps) |
| tower-defense @ `52a6f2a1` (`milestone/autoplay-3`) | 12.53 / 11.35 GB (9,072 files) | 3.06 / 2.88 GB (2,685) | 6,387 (9.47 GB, from the working tree) | pipeline `52a6f2a1-shipping` (verified, art cooked) | 3 (S1–S3 with art; the older art-less L1 run left out with `-ExcludeRuns`) |
| rally-racer @ `174f1a0e` (`milestone/autoplay-3`) | 16.12 / 15.22 GB (4,871) | 6.48 / 6.17 GB (966) | 3,905 (9.64 GB, tracked) | pipeline `174f1a0e-shipping` (verified) | 3 (S1–S3) |
| island-survival @ `4207861a` (HEAD; tag `bf92f9d3` in its lineage) | 10.75 / 10.27 GB (3,145) | 5.79 / 5.58 GB (1,170) | 1,975 (4.97 GB, `Content/Fab`, tracked) | session Shipping package of `f05b85f` (`-Build`, stated) | 0 |
| liaozhai-night @ `328a8654` (superseded by 1.0; no runs at the time) | 8.84 / 8.00 GB (1,855) | 2.45 / 2.19 GB (1,097) | 758 (6.39 GB, `Content/Fab` from the working tree) | Shipping package of `25c4cb9` (`-Build`, stated; launch from `Build/`) | 0 |

One run takes 1.5–8 minutes (copy, scrub, scan, hash, zip `Fastest`). Not packaged: siege-catapult (refused: its only
Shipping package, `f9d3aa9`, predates the v1.3 migration and embeds the old drop-in's schema names in the exe; waiting
for the queue's Shipping build of `2361341c`), horror-escape and stealth (sessions active, no Shipping build of a
clean commit).

Scrub counts (same in both variants of a game):

| Game | Files touched | banned-name | username | agent-mention | agent-trailer | git-identity | email | agent-identity | Binaries reported |
|---|---|---|---|---|---|---|---|---|---|
| tower-defense | 27 | 8,956 | 4,121 | 854 | 189 (90 in `git.log`) | 120 | 14 | 10 | 17 |
| rally-racer | 23 | 3,992 | 2,589 | 161 | 39 | 33 | 5 | 1 | 5 |
| island-survival | 30 | 2,505 | 3,215 | 300 | 78 | 29 | 3 | 0 | 423 |
| liaozhai-night | 27 | 3,862 | 3,243 | 282 | 50 | 32 | 1 | 0 | 83 |

All with 0 text/path hits and 0 binary name hits after the scrub. Binaries reported are UE assets carrying their
import source path and the Shipping exe (build paths), by category only.

## Known gaps

- Packages are a snapshot: runs the recording queue adds later (tower-defense re-recording, island-survival,
  liaozhai-night, siege-catapult) need a rerun of the tool with `-Force`. Running it while the pipeline builds that
  game is refused (pipeline lock).
- Store folders outside git are found as folders under `Content/` not tracked at the commit that are git-ignored now
  or named as store content by the commit's `assets.manifest.json` (tower-defense changed its `.gitignore` after
  `52a6f2a1`, so the ignore state alone is not enough).
- Binary assets keep their embedded import paths (account name); fixing them needs a re-import in the editor.
- The scrub is pattern-based: other personal names typed into logs (e.g. names seen on web pages) are not detected
  beyond the e-mail and git-identity rules; review `<name>.leaks.tsv` and spot-check `History/actions.jsonl`.

## Dataset layout v1.1 (the delivery)

> **Superseded for new deliveries by layout v1.2** (2026-10-15: the full git history in `History/`, the brief and design
> doc in `Brief/`): [game-format.md](game-format.md). v1.1 deliveries made before stay valid as v1.1.

Approved 2026-10-12 as v1; v1.1 the same day (user): no replay video, the verified replay scripts are the creation replay.

Our standard delivery of every game, the same for all of them: the creation record (`git.log`,
`workflow.jsonl`, `ReplayScripts/`), the project, per-scenario gameplay videos, the README's screenshots
and the packaged build. Machine-readable copy: [dataset-layout-v1.json](dataset-layout-v1.json), which the validator
reads, so this text and the checks cannot drift apart. Nothing in it is per game except the data.

```
<game>/
  README.md                      the game, how to play and open it, how to replay the creation, scenario videos, screenshots, licences
  git.log                        every commit, oldest first: message, dev_NN author, dates, full diff; binary/LFS files as path + sha256
  workflow.jsonl                 the editor operations, one row each, written when the operation happened
  UEProject/                     the project at the release commit                            (not in the repo Dataset/)
  ReplayScripts/                 scripts that replay the creation, with their verification    (tools/ue-replay)
  Gameplay/<game>_S<n>.mp4       one video per recorded scenario of the release version (a subset is fine), nothing else in the folder
  Screenshots/                   the README hero and gallery images, linked from README.md by relative path
  Build/                         the packaged Windows Shipping build, no .pdb                  (not in the repo Dataset/)
  manifest.json                  release metadata + path, bytes, sha256 of every other file
```

| Item | Source | Notes |
|---|---|---|
| `README.md` | generated (template below) from the package README, the project's docs, `assets.manifest.json` | sections in fixed order |
| `git.log` | `package-game.ps1`, from the repo's history at the release commit | scrubbed; authors `dev_NN` |
| `workflow.jsonl` | the repo's `workflow.jsonl` at the release commit | scrubbed copy |
| `ReplayScripts/` | the creation replay (`tools/ue-replay/`, `ue_replay.py package`, READY) | `ReplayScripts/` scrubbed with the package rules (`package-game.ps1 -ScrubDir`) |
| `UEProject/` | the repo tree at the release commit + its Git LFS objects; store packs kept out of git come from the game's working tree | always with store content |
| `Gameplay/<game>_S<n>.mp4` | the release version's validated runs, one per scenario: the first valid run (validation `ok` or `warn`), whatever its result. Taken as is from the run's `recordings\<game>\<run>\gameplay.mp4` (written by record.ps1; no re-encode); runs without one are encoded from `video.mkv` + `system_audio.mka` | 1920x1080 60 fps H.264 (the recording's NVENC stream, stream-copied; fallback: libx264 High CRF 20) + AAC 192 kbit/s stereo; the run's game audio delayed by its own `system_audio.start_offset_ns - video_start_offset_ns`; faststart; nothing added to the picture |
| `Screenshots/` | the project's `docs/screenshots/`, else stills of the release runs (`recordings\<game>\_stills\`) | every image is shown in the README |
| `Build/` | the pipeline's Shipping build of the release commit (store art cooked in, account name not compiled in) | `.pdb` left out |
| `manifest.json` | generated | schema below |

**Naming and place.** Every game keeps its full dataset in its own folder: `<repo>\Dataset.zip` (with store
content), one top folder `<game>/` inside; `Dataset.pending.zip` while `ReplayScripts/` is missing. The same name
for every game; git-ignored (too big for git: `/Dataset.zip`, `/Dataset.pending.zip`, `/.dataset/` in the template
.gitignore). Packaging scratch stays in the game folder too, in `<repo>\.dataset\`: the unpacked delivery
`<game>\`, `_videos\` and the reports (`<game>.store-content.tsv` with sha256 of every store file,
`<game>.scrub-report.json`, `<game>.rescan-hits.tsv`). Nothing is written under `deliverables\dataset\` any more.
No `_nostore` variant (user decision 2026-10-12).

**Repo `Dataset/`.** Each game repo carries `Dataset/`: the same layout minus `UEProject/` (the repository is the
project) and `Build/` (rebuildable; too big for git), as real copies of the same scrubbed files, plus
`Dataset/.gitattributes` sending `mp4 mkv mka wav flac jpg jpeg png webp zip` to Git LFS. The tool writes it into the
game's working tree and never commits it; the game session commits and pushes it, so each repo's history stays its own.

**manifest.json (`dataset-layout/v1.1`).**

```
layout     "dataset-layout/v1.1"        game, title, version, commit (full sha)
status     "complete" | "pending"       pending: the missing entries ("ReplayScripts/")
variant    "full" | "repo-dataset"
created, source_package, build {config, commit, exe, source} (null in the repo Dataset)
scenarios  [{file, scenario, name, result, seconds, source_run, audio_offset_s, capture_notes?}]   (capture_notes: what the recording did differently, e.g. "scalability 2 (High) for 60 fps capture"; also a "Recording note" line under the README's Scenarios table)
totals     {files, bytes}
files      [{path, bytes, sha256}]      every file except manifest.json (and .gitattributes in the repo Dataset)
replay_verification  {pass, report, criteria [{id, text, result, pass}], exclusions [{id, what, count}]}  (null while pending)
```

**COMPLETE needs a verified replay; its verdict is metadata.** A dataset is `complete` only when `ReplayScripts/`
comes from a creation replay that ran end to end, headless, from those scripts and was verified
([ue-replay.md](ue-replay.md) 2.4): every file outside `Content/` compared with the release commit, every asset by
structure, every game map by actors, with the known non-content differences (random GUIDs, printed memory addresses,
derived compression sizes, Content/ bytes, store-pack demo maps) listed and counted. The replay is required but need
not pass (user rule): PASS or FAIL is recorded as `replay_verification.pass` (equal to the report's `verdict.pass`)
and in the README, and a FAIL dataset is COMPLETE too. `package-dataset.ps1` refuses scripts without
`Verification/report.json` or without a verdict, and the validator checks that `replay_verification` and the report
are there and agree. The README's "Replay the creation process" section shows PASS or FAIL, the criteria, the
results and the exclusions. No verification, no COMPLETE.

**README template.** Title (the game's name), hero image (`Screenshots/...`), the pending banner while pending, a
version and commit line, then these sections in this order: Requirements, Package contents, Play the game, Replay the
creation process, Scenarios (one row per `Gameplay/<game>_S<n>.mp4`: scenario, result, length), Screenshots (every
image), Assets and licences (with the store-content folders), Integrity (the sha256 check command).

**Scrub.** Every text file of the delivery has passed the package scrub and scan described above: the two studio
names, Claude/Opus/Anthropic, the account name and machine name, e-mail addresses and git identities; binaries are
scanned too, with the codec/locale allowlist and the reviewed exceptions. `package-dataset.ps1` rescans each delivery
(`package-game.ps1 -Rescan`) and validates it before zipping; any failure stops it.

**Tools.**

```
powershell -ExecutionPolicy Bypass -File tools\package-game.ps1 <game> -Commit <release> -OnlyCommitRuns -Screenshots stills -Version <v> -Dataset [-ReplayScripts <dir>]
powershell -ExecutionPolicy Bypass -File tools\validate-dataset.ps1 <zip | delivery folder | <repo>\Dataset> [-NoHash]
```

`package-game.ps1 -Dataset` runs `tools/package-dataset.ps1` on the package (one run per
game at a time, through a lock in the output folder). `validate-dataset.ps1` prints `VALID` (exit 0), `PENDING`
(exit 1: only `ReplayScripts/` missing, and declared pending) or `INVALID` (exit 2), with one line per
finding. It checks the top-level entries (nothing missing, nothing extra; the repo Dataset without `UEProject/` and
`Build/`), the Gameplay file names and numbering, that `Screenshots/` holds only images and all of them are shown in the
README, `Build/` with an `.exe` and no `.pdb`, `UEProject/` with a `.uproject`, the manifest keys and values and every
file's size and sha256, the README's sections and links, and each video's codecs and size (ffprobe). The content scan
is `package-game.ps1 -Rescan`; run both before a review.

**Decisions.**

- What ships is what matters, in this order: the game plays; the game builds (editor and packaged Shipping); the dataset holds the replay scripts and the git log. The AutoPlay bot should still play like a human (human-like input, aim and camera), but bot work never blocks a release: one recording per scenario that shows the game running is enough, whatever the result (win/lose/timeout is metadata). No tuning for win rates, seed sweeps or "clean" runs, and no re-runs or re-recordings to improve how the bot plays. No retest loops: every GPU or editor run costs about 30 minutes of the shared machine and holds up delivery, so run the minimum once and report; re-run only when the user asks. Game-session work never blocks dataset packaging or sharing.

- Gameplay holds mp4s only, one per scenario of the release version: no per-run bundles (inputs, telemetry, json), no
  version subfolders, no index file; the README lists the videos.
- No `play.mp4`: the per-scenario videos replace it.
- No `replay.mp4` (v1.1, user, 2026-10-12): the verified replay scripts are the creation replay; no video of it.
- No `History/`: `git.log` and `workflow.jsonl` carry the history.
- `Build/` is kept (buyers can play without Unreal), without `.pdb`.
- `Screenshots/` is kept for the README's hero and gallery.


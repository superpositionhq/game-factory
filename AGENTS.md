# AGENTS.md — game-factory

Rules for agents working in this repository. Each rule says what went wrong without it.
Background is in `docs/`; keep this file to rules.

## Data

LiaoZhaiRL is fully authorised for this work; no permission step is needed before using or sharing packages.

- Never commit a full package, a project snapshot, `git.log` with asset diffs, or vendor zips here; only
  tools, docs and small samples. _(failure: a package is tens of GB, far past GitHub's 100 MB file limit)_
- Keep this repository private. _(failure: the docs describe a private repository and include samples of its
  asset data)_
- Step reasons are the commit message (Track A) or the builder's own narration or notes (Track B); never
  write them with a model. _(failure: the vendor's per-step reasons were written after the fact, which is what
  makes their packages a reconstruction rather than a record)_
- Anonymize authors as `dev_NN` and run the leak scan (real names, e-mails, `C:\Users\…`, `/Users/…`, `/home/…`)
  over every text file of a package before calling it done. _(failure: commit metadata and asset files can
  carry real names and machine paths)_

## Git on the LiaoZhaiRL clone (`~/Repo/LiaoZhaiRL`, blobless)

- Never run a command that needs every blob of a tree (`git ls-tree -l`, `git archive`, `git grep <rev>`,
  `git checkout` of the whole tree) unless the download is the point; get sizes from the GitHub trees API.
  _(failure: `git ls-tree -l HEAD` started downloading the entire 44 GB tree just to sum file sizes)_
- The GitHub trees API truncates large trees (`truncated: true`); recurse into subtrees.
  _(failure: the first size estimate said 10 GB from 35k of 137k entries; the real figure is ~44 GB)_
- Pass `-c core.quotepath=off` for Chinese paths. _(failure: paths came back as octal escapes and a shell
  loop over folder names broke)_
- The shell is zsh: `$VAR` holding several words is not split; use `xargs` or arrays.
  _(failure: `git log $SHAS` failed with “File name too long”)_
- Leave the clone's index alone (every file shows as staged-deleted); work through `git worktree` or plumbing.
  _(failure risk: a reset or checkout there would start the full download and change the owner's clone)_

## Converter (`tools/build_package.py`)

- Key list items by identity (GUID, component id) before diffing, never only by index.
  _(failure: one Addressables insertion shifted every later entry, and the pilot's workflow grew to 2.8 MB
  of false changes)_
- Collapse per-element array overrides (`Array.data[N]`, Odin `SerializedBytes`) into one summary entry.
  _(failure: one prefab override produced 1,592 single-byte rows)_
- Re-run with the project snapshot present before publishing, so GUIDs resolve to asset paths.
  _(failure: without the snapshot every reference is a bare GUID)_
- Load Unity YAML with `UnityLoader`, never PyYAML's YAML 1.1 implicit typing.
  _(failure: the skin id `10019_1` became the int 100191 in 22 files, and the Unity replay faithfully wrote it back)_
- Record what sorted paths cannot carry (`list_inserts` for added list items).
  _(failure: Addressables groups came out with the right entries in the wrong order)_
- Write outputs with `write_text` (UTF-8, LF) and paths with `.as_posix()`.
  _(failure: on Windows the package came out with CRLF lines and `Assets\…` GUID paths)_

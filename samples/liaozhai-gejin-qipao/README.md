# Sample: 葛巾_旗袍 pilot (final, 2026-10-11)

Output of `tools/build_package.py` for the 葛巾 qipao skin of LiaoZhaiRL, built with the project snapshot
present, so GUID references carry asset paths. `git.log` (13 MB, asset diffs), the 42 GB `UnityProject/` and
its 30 MB manifest are left out; the full package is at `~/Downloads/liaozhai_gejin_qipao/` on the owner's Mac.

- `workflow.jsonl`: 783 steps, schema `liaozhai.unity-workflow/v1` (see `docs/workflow-format.md`)
- `commits.json`: the 27 commits, anonymized, with files, blob ids and step ids
- `summary.json`: scope rule, start/end commit, counts
- `PACKAGE-README.md`: the package's own README (contents, how to open, observed vs derived, checks)

# Scripts

Editor Python (`unreal` module) and helper scripts that built this project. Run each editor script headless through
`Scripts/ue.ps1 script -Script Scripts/<name>.py -Reason "..."` (UnrealEditor-Cmd `-run=pythonscript` through the
machine's heavy-job limiter). Keep every script that was run, unchanged: write a new version (`<name>_v2.py`)
instead of editing one that already ran, so each `workflow.jsonl` row's `source.script` and `source.sha256` still
point at the real code.

These scripts are replayed after every commit to rebuild the project from its history (`ReplayConfig.json`), so:

- commit every script you run, under `Scripts/`, and run it by that project-relative path;
- address files relative to the project (`unreal.Paths.project_dir()`, `Path(__file__).resolve().parents[1]`), never
  by an absolute path or an `os.chdir` into this folder;
- scripts that only look (probes, checks) are named `inspect_*`, `measure_*`, `check_*`, `analyze_*`, `scan_*` or
  contain `probe`; one that also writes something later work reads goes in `ReplayConfig.json` `not_readonly`;
- every run logs at least one `workflow.jsonl` row;
- no custom commandlets (`-run=<Name>`): do that work in an editor script.

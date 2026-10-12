# Scripts

Editor Python (`unreal` module) and helper scripts that built this project, run through
`UnrealEditor-Cmd.exe __PROJECT__.uproject -run=pythonscript -script=Scripts/<name>.py` (or the editor's Python
console). Keep every script that was run, unchanged: write a new version (`<name>_v2.py`) instead of editing one
that already ran, so each `workflow.jsonl` row's `source.script` and `source.sha256` still point at the real code.

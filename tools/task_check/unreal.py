"""Unreal for the checker: build a project's editor target, play it with the TaskProbe plugin, run a Python script in
the headless editor. Every job goes through the machine's `<root>\\tools\\ue-heavy.ps1` when it has one (the machine's
shared CPU/GPU slots: the timeout then counts from when the job starts, never the wait for a slot), else runs directly.
The engine is the one the machine config gives for the project's EngineAssociation (machine/lib/gfroot.py `engine`).

- build: Build.bat <Name>Editor Win64 Development -Project=... -WaitMutex -DisableAdaptiveUnity (a scratch copy has no
  .git, so UBT's adaptive unity would take every file for one being edited and compile each .cpp on its own; the
  developer's checkout builds unity files, and so does the checker);
- play: UnrealEditor.exe <uproject> [map] -game offscreen at 960x540, a fixed 30 fps, with -TaskProbe and its flags
  (-TaskProbeOut, -TaskProbeSeconds, -TaskProbeShots, -TaskProbeInputs, -TaskProbeQueries, -TaskProbeEvery), the log
  in Saved/Logs/TaskProbePlay.log, then a task play's own game flags;
- editor_python: UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<file>."""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import seeds

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "machine" / "lib"))
import gfroot  # noqa: E402  (game-factory's machine root and engine resolver)

UNITY = "-DisableAdaptiveUnity"
SHOT_SIZE = (960, 540)
OUTPUT_CHARS = 30_000
WRAPPER_GRACE = 60  # seconds ue-heavy.ps1 gets to release its slot once the job it runs is killed
QUEUE_POLL = 5  # seconds between looks at whether the wrapper has started its job
LOG_NAME = "TaskProbePlay.log"
FATAL = r"Fatal error|Assertion failed|Unhandled Exception"


@dataclass
class Result:
    exit_code: int | None  # None: killed at its timeout
    output: str
    seconds: float
    timed_out: bool = False


@dataclass
class Played:
    exit_code: int | None
    timed_out: bool
    output: str
    seconds: float
    probe: dict | None  # the plugin's probe.json; None when it wrote none (the game didn't get there)
    log: str
    files: dict = field(default_factory=dict)  # what the play wrote (probe.json, screenshots) by name


def cut(text, limit=OUTPUT_CHARS):
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n... [{len(text) - limit} characters left out] ...\n{text[-half:]}"


def _kill_tree(pid):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)


def _children(pid):
    """{parent pid: [child pids]} of every process (one CIM query)."""
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                          "Get-CimInstance Win32_Process | ForEach-Object { \"$($_.ProcessId) $($_.ParentProcessId) "
                          "$($_.Name)\" }"], capture_output=True, text=True, check=False).stdout
    children, names = {}, {}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
            names[int(parts[0])] = parts[2] if len(parts) > 2 else ""
    return children, names


def _descendants(pid):
    children, _ = _children(pid)
    found, todo = [], list(children.get(pid, []))
    while todo:
        child = todo.pop()
        if child != pid and child not in found:
            found.append(child)
            todo += children.get(child, [])
    return list(reversed(found))


def _job_started(pid):
    """Whether ue-heavy.ps1's wrapper `pid` has started its job: a child process other than its console host."""
    children, names = _children(pid)
    return any(names.get(c, "").strip().lower() not in ("", "conhost.exe") for c in children.get(pid, []))


def run(argv, cwd, timeout, wrapper=False, clock=time.monotonic):
    """Run `argv` in `cwd`; its output, cut. Killed with its children after `timeout` seconds; `wrapper`: `argv` is
    ue-heavy.ps1's, so `timeout` counts from when its job starts, only the job is killed, and the wrapper gets
    WRAPPER_GRACE seconds to release its slot."""
    started = clock()
    proc = subprocess.Popen(argv, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    chunks = []
    reader = threading.Thread(target=lambda: chunks.append(proc.stdout.read()), daemon=True)
    reader.start()
    job = None if wrapper else started
    timed_out = False
    while True:
        try:
            proc.wait(timeout=QUEUE_POLL if job is None else max(0.05, min(QUEUE_POLL, timeout - (clock() - job))))
            break
        except subprocess.TimeoutExpired:
            if job is None:
                if _job_started(proc.pid):
                    job = clock()
                continue
            if clock() - job < timeout:
                continue
            timed_out = True
            if wrapper:
                for child in _descendants(proc.pid):
                    subprocess.run(["taskkill", "/F", "/PID", str(child)], capture_output=True, check=False)
                try:
                    proc.wait(timeout=WRAPPER_GRACE)
                except subprocess.TimeoutExpired:
                    _kill_tree(proc.pid)
                    proc.wait()
            else:
                _kill_tree(proc.pid)
                proc.wait()
            break
    reader.join(timeout=30)
    text = (b"".join(chunks)).decode("utf-8", errors="replace").replace("\r\n", "\n")
    return Result(None if timed_out else proc.returncode, cut(text), round(clock() - started, 3), timed_out)


def _ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@dataclass
class Machine:
    """Where Unreal is and how jobs run: `engine` (the UE root), `ue_heavy` (the slot limiter, or None to run
    directly)."""

    engine: Path
    ue_heavy: Path | None

    @classmethod
    def for_project(cls, project, direct=False):
        engine = Path(gfroot.engine(str(project)))
        heavy = Path(gfroot.root()) / "tools" / "ue-heavy.ps1"
        return cls(engine=engine, ue_heavy=None if direct or not heavy.is_file() else heavy)

    def editor(self):
        return self.engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"

    def editor_cmd(self):
        return self.engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"

    def build_bat(self):
        return self.engine / "Engine" / "Build" / "BatchFiles" / "Build.bat"

    def job(self, label, argv, cwd, timeout):
        """`argv` as one Unreal job: through ue-heavy.ps1 when the machine has it (a wrapper that never ran the job,
        e.g. PowerShell refusing to load the script, exits 1, never 0), else directly."""
        if self.ue_heavy is None:
            return run([str(a) for a in argv], cwd, timeout)
        command = (f"& {_ps_quote(self.ue_heavy)} -Label {_ps_quote(label)} -- "
                   + " ".join(_ps_quote(a) for a in argv)
                   + "; if ($null -eq $LASTEXITCODE) { exit 1 }; exit $LASTEXITCODE")
        found = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command], cwd, timeout, wrapper=True)
        if found.exit_code and ("cannot be loaded" in found.output or "not digitally signed" in found.output):
            found.output = ("PowerShell refused to run ue-heavy.ps1 (its execution policy): run the checker from a "
                            "PowerShell that may run the machine's scripts, or with --direct\n" + found.output)
        return found


class Project:
    """A scratch copy of the game (seeds.materialize + add_probe) the checker builds and plays."""

    def __init__(self, folder, machine, label):
        self.folder, self.machine, self.label = Path(folder), machine, label

    def uproject(self):
        return seeds.uproject(self.folder)

    def build(self, timeout):
        argv = [self.machine.build_bat(), seeds.editor_target(self.folder), "Win64", "Development",
                f"-Project={self.uproject()}", "-WaitMutex", UNITY]
        return self.machine.job(f"task-check build {self.label}", argv, self.folder, timeout)

    def play(self, seconds, shots, timeout, map=None, inputs=None, queries=None, args=(), every=None):
        """The game for `seconds` of game time through the plugin: offscreen at a fixed 30 fps, `shots` screenshots,
        `inputs` sent at their times, `queries` (probes.query_file) sampled; a Played."""
        out = self.folder / "Saved" / "TaskProbe" / "play"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        log_path = self.folder / "Saved" / "Logs" / LOG_NAME
        if log_path.exists():
            log_path.unlink()
        argv = [self.machine.editor(), self.uproject()]
        if map:
            argv.append(map)
        argv += ["-game", "-RenderOffscreen", f"-ResX={SHOT_SIZE[0]}", f"-ResY={SHOT_SIZE[1]}", "-unattended",
                 "-nosound", "-nosplash", "-benchmark", "-fps=30", "-TaskProbe", f"-TaskProbeOut={out}",
                 f"-TaskProbeSeconds={seconds}", f"-TaskProbeShots={shots}", f"-log={LOG_NAME}"]
        if inputs:
            keys = out / "inputs.json"
            keys.write_text(json.dumps(inputs), encoding="utf-8")
            argv.append(f"-TaskProbeInputs={keys}")
        if queries:  # beside the play's folder, so it isn't one of the files the play wrote
            asked = out.parent / "queries.json"
            asked.write_text(json.dumps(queries), encoding="utf-8")
            argv.append(f"-TaskProbeQueries={asked}")
        if every:
            argv.append(f"-TaskProbeEvery={every:g}")
        argv += list(args)
        found = self.machine.job(f"task-check play {self.label}", argv, self.folder, timeout)
        files = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()} if out.is_dir() else {}
        probe = None
        if "probe.json" in files:
            try:
                probe = json.loads(files["probe.json"].decode("utf-8"))
            except ValueError:
                probe = None
        log = log_path.read_bytes().decode("utf-8", errors="replace") if log_path.is_file() else ""
        shutil.rmtree(out, ignore_errors=True)
        return Played(found.exit_code, found.timed_out, found.output, found.seconds,
                      probe if isinstance(probe, dict) else None, log, files)

    def editor_python(self, script, timeout):
        path = self.folder / "Saved" / "TaskProbe" / "editor_script.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script, encoding="utf-8")
        argv = [self.machine.editor_cmd(), self.uproject(), "-run=pythonscript", f"-script={path}", "-unattended",
                "-nosplash", "-nosound", "-stdout", "-FullStdOutLogOutput"]
        return self.machine.job(f"task-check editor {self.label}", argv, self.folder, timeout)

    def read(self, relative):
        path = self.folder / relative
        return path.read_bytes() if path.is_file() else None

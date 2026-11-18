"""Unreal for the checker: build a project's editor target, play it with the TaskProbe plugin, run a Python script in
the headless editor. Every job goes through the machine's `<root>\\tools\\ue-heavy.ps1` when it has one (the machine's
shared CPU/GPU slots: the timeout then counts from when the job starts, never the wait for a slot), else runs directly.
The engine is the one the machine config gives for the project's EngineAssociation (machine/lib/gfroot.py `engine`).

- build: Build.bat <Name>Editor Win64 Development -Project=... -WaitMutex -DisableAdaptiveUnity -NoHotReloadFromIDE
  (a scratch copy has no .git, so UBT's adaptive unity would take every file for one being edited and compile each
  .cpp on its own; the developer's checkout builds unity files, and so does the checker. A Live Coding session holds a
  mutex named after UnrealEditor.exe, so any editor on the machine, on any game, stops UBT with "Unable to build while
  Live Coding is active": -NoHotReloadFromIDE skips that guard, and a scratch copy's DLLs are its own. A build that
  still reports the line is retried: see build);
- play: UnrealEditor.exe <uproject> [map] -game offscreen at 960x540 (a mobile game, whose copy has a Platform.json:
  the mobile renderer at the phone's size, MOBILE_FLAGS and validate-game.py PHONE_SIZE), a fixed 30 fps, with -TaskProbe and its flags
  (-TaskProbeOut, -TaskProbeSeconds, -TaskProbeShots, -TaskProbeInputs, -TaskProbeQueries, -TaskProbeEvery), the log
  in Saved/Logs/TaskProbePlay.log, then a task play's own game flags; without sound (-nosound -benchmark) unless the
  play measures audio (probes.sound_flags: muted, with -benchmark's fixed step);
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

from . import probes, seeds

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "machine" / "lib"))
import gfroot  # noqa: E402  (game-factory's machine root and engine resolver)

UNITY = "-DisableAdaptiveUnity"
NO_LIVE_CODING_GUARD = "-NoHotReloadFromIDE"  # UBT: skip the machine-wide Live Coding check (HotReload.cs)
NO_LIVE_CODING = "-LiveCoding=false"  # the editor: never start a Live Coding session (LiveCodingModule.cpp)
LIVE_CODING_BLOCKED = "Unable to build while Live Coding is active"
LIVE_CODING_RETRY_SECONDS = 60
LIVE_CODING_RETRY_LIMIT = 30 * 60
SHOT_SIZE = (960, 540)
# a mobile game's play (docs/task-probes.md, section 1.1): the engine's mobile renderer at the phone's size, by how the
# game is held (tools/validate-game.py PHONE_SIZE); -ForceRes because the engine otherwise clamps a game window to the
# primary display
MOBILE_FLAGS = ["-FeatureLevelES31", "-ForceRes"]
OUTPUT_CHARS = 30_000
WRAPPER_GRACE = 60  # seconds ue-heavy.ps1 gets to release its slot once the job it runs is killed
QUEUE_POLL = 5  # seconds between looks at whether the wrapper has started its job
LOG_NAME = "TaskProbePlay.log"
# A first session (a task play another `continues`): the game's save state, cleared before it, so the play after it
# loads only what it wrote: the game's SaveGame files and its saved settings (its user config), under the project's
# Saved folder, where a game played in the editor's -game keeps both
SAVES = ("Saved/SaveGames", "Saved/Config")
# what a first session's write is never looked for in (Played.saved): the checker's own folder and the engine's logs
# and crash reports, under Saved
NOT_SAVES = ("Saved/TaskProbe", "Saved/Logs", "Saved/Crashes")
SAVED_LISTED = 200  # files a first session's Played.saved lists at most
FATAL = r"Fatal error|Assertion failed|Unhandled Exception"


@dataclass
class Result:
    exit_code: int | None  # None: killed at its timeout
    output: str
    seconds: float
    timed_out: bool = False
    waited: float = 0.0  # of `seconds`, waiting for a ue-heavy.ps1 slot before the job started


@dataclass
class Played:
    exit_code: int | None
    timed_out: bool
    output: str
    seconds: float
    probe: dict | None  # the plugin's probe.json; None when it wrote none (the game didn't get there)
    log: str
    files: dict = field(default_factory=dict)  # what the play wrote (probe.json, screenshots) by name
    waited: float = 0.0  # of `seconds`, waiting for a machine slot
    saved: list | None = None  # a first session's (Project.play session=True): the files it wrote under Saved


def _saved(project, began):
    """What a first session wrote under the project's Saved (Played.saved): its files (but NOT_SAVES) modified since
    `began`, never through a link."""
    root, skipped, found = project / "Saved", {project / p for p in NOT_SAVES}, []
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if Path(folder, d) not in skipped and not os.path.islink(os.path.join(folder, d))]
        for name in names:
            path = Path(folder, name)
            try:
                if not path.is_symlink() and path.stat().st_mtime >= began:
                    found.append(path.relative_to(project).as_posix())
            except OSError:
                continue
    return sorted(found)[:SAVED_LISTED]


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
    waited = job - started if wrapper and job is not None else 0.0  # a job seen start within its first poll: ~0
    return Result(None if timed_out else proc.returncode, cut(text), round(clock() - started, 3), timed_out,
                  round(waited, 3))


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
        self.build_retries = 0

    def uproject(self):
        return seeds.uproject(self.folder)

    def mobile(self):
        """How the copy's game is held when it is a mobile game ("landscape", "portrait"), or None for a desktop game:
        the copy's own Platform.json, as the game had it at this commit (tools/validate-game.py read_platform)."""
        from . import tasks

        return tasks.validator().read_platform(self.folder)

    def build(self, timeout, sleep=time.sleep):
        """The editor target's build. One stopped by another process's Live Coding session isn't a failed build: it
        waits and tries again, up to LIVE_CODING_RETRY_LIMIT seconds, and says how many times in its output. Any other
        failure, or the same line once the limit is up, comes back as it is."""
        argv = [self.machine.build_bat(), seeds.editor_target(self.folder), "Win64", "Development",
                f"-Project={self.uproject()}", "-WaitMutex", UNITY, NO_LIVE_CODING_GUARD]
        retries, waited = 0, 0
        while True:
            found = self.machine.job(f"task-check build {self.label}", argv, self.folder, timeout)
            blocked = found.exit_code != 0 and LIVE_CODING_BLOCKED in (found.output or "")
            if not blocked or waited >= LIVE_CODING_RETRY_LIMIT:
                break
            retries += 1
            waited += LIVE_CODING_RETRY_SECONDS
            print(f"  {self.label}: build blocked by Live Coding, retry {retries} in "
                  f"{LIVE_CODING_RETRY_SECONDS} s", file=sys.stderr, flush=True)
            sleep(LIVE_CODING_RETRY_SECONDS)
        self.build_retries = retries
        if retries:
            found.output = f"[task-check] build retried {retries} time(s) for Live Coding\n{found.output}"
        return found

    def play(self, seconds, shots, timeout, map=None, inputs=None, queries=None, args=(), every=None, session=False,
             fresh=False):
        """The game for `seconds` of game time through the plugin: offscreen at a fixed 30 fps, `shots` screenshots,
        `inputs` sent at their times, `queries` (probes.query_file) sampled; a Played. `session`: a first session (a
        task play another `continues`): the game's save state (SAVES) is cleared before it, and the Played lists the
        files it wrote under Saved. `fresh`: a task play marked `fresh`: the game's save state (SAVES) is cleared before
        it too. The probe's misses that an `optional` or `disabled` click allows are kept apart (probes.excused)."""
        out = self.folder / "Saved" / "TaskProbe" / "play"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        log_path = self.folder / "Saved" / "Logs" / LOG_NAME
        if log_path.exists():
            log_path.unlink()
        argv = [self.machine.editor(), self.uproject()]
        if map:
            argv.append(map)
        sound, step = probes.sound_flags(queries)  # audio off, unless the play measures it
        mobile = self.mobile()
        from . import tasks

        width, height = tasks.validator().PHONE_SIZE[mobile] if mobile else SHOT_SIZE
        argv += ["-game", "-RenderOffscreen", *(MOBILE_FLAGS if mobile else []), f"-ResX={width}", f"-ResY={height}",
                 "-unattended", NO_LIVE_CODING,
                 *sound, "-nosplash", *step, "-fps=30", "-TaskProbe", f"-TaskProbeOut={out}",
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
        if session or fresh:  # a first session or a fresh play: the game's save state cleared first
            for folder in SAVES:
                shutil.rmtree(self.folder / folder, ignore_errors=True)
        began = time.time()
        found = self.machine.job(f"task-check play {self.label}", argv, self.folder, timeout)
        saved = _saved(self.folder, began) if session else None
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
                      probes.excused(probes.well_formed(probe), inputs), log, files, found.waited, saved)

    def editor_python(self, script, timeout):
        path = self.folder / "Saved" / "TaskProbe" / "editor_script.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script, encoding="utf-8")
        argv = [self.machine.editor_cmd(), self.uproject(), "-run=pythonscript", f"-script={path}", "-unattended", NO_LIVE_CODING,
                "-nosplash", "-nosound", "-stdout", "-FullStdOutLogOutput"]
        return self.machine.job(f"task-check editor {self.label}", argv, self.folder, timeout)

    def read(self, relative):
        path = self.folder / relative
        return path.read_bytes() if path.is_file() else None

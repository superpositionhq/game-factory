"""Drive the LiaoZhai Unity replay for one feature package (plan phase A3).

The project is a `git worktree --detach` of the LiaoZhaiRL clone at the package's start commit. Every git
command here passes `core.autocrlf=false core.eol=lf`, so files on disk are byte-identical to the blobs and
hash like the commits (Git for Windows otherwise checks text files out with CRLF).

    python replay.py open    --project <start>                      # stage 1: build Library, report changes
    python replay.py plan    --package <pkg> --repo <clone> --work <dir>
    python replay.py install --project <start> [--mode embed|manifest]
    python replay.py files   --project <start> --work <dir>         # stage 2: file-level replay
    python replay.py steps   --project <start> --work <dir> --package <pkg> [--record]   # stage 3/4
    python replay.py status  --project <start> --work <dir>         # git status vs. what the replay wrote
    python replay.py reset   --project <start> --work <dir>         # back to the start commit (keeps Library)
    python replay.py report  --work <dir>                           # summarize step-log.jsonl, classify mismatches
    python replay.py verify  --work <dir> --package <pkg>           # redo video-verification.json for a recording

Unity 2022.3.10f1 is required; any other editor version is refused.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_DIR = HERE.parent                      # tools/unity-replay (the Unity package)
PACKAGE_NAME = 'ai.superposition.liaozhai-replay'
UNITY = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.10f1\Editor\Unity.exe')
ZERO = '0' * 40
GITC = ['-c', 'core.autocrlf=false', '-c', 'core.eol=lf', '-c', 'core.quotepath=off', '-c', 'core.longpaths=true']
# Paths the replay harness itself adds to the project; never part of the feature, never verified.
HARNESS = [f'Packages/{PACKAGE_NAME}']


def git(repo, *args, data=None, check=True):
    return subprocess.run(['git', '-C', str(repo), *GITC, *args], input=data, capture_output=True,
                          check=check).stdout


def chunks(paths, limit=12000):
    """Groups of paths whose joined length stays well under the Windows command-line limit."""
    part, size = [], 0
    for p in paths:
        if part and size + len(p) + 3 > limit:
            yield part
            part, size = [], 0
        part.append(p)
        size += len(p) + 3
    if part:
        yield part


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


class Blobs:
    """One `git cat-file --batch`; the blobless clone fetches missing blobs on demand."""

    def __init__(self, repo):
        self.p = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)

    def get(self, oid):
        self.p.stdin.write(oid.encode() + b'\n')
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if head[1] == b'missing':
            raise RuntimeError('blob missing: ' + oid)
        body = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        return body


def tree_entry(repo, rev, path):
    """Blob id of path at rev, or None."""
    out = git(repo, 'ls-tree', '-z', rev, '--', path).decode()
    if not out:
        return None
    meta, _ = out.rstrip('\0').split('\t', 1)
    return meta.split()[2]


# ---------- plan ----------

DB_PATH = 'Assets/StreamingAssets/bansheegz_database.bytes'   # what the project's 导表 export writes


def table_export(repo, sha, staging, blobs):
    """
    The real 导表 export of a commit's table edit: a child commit of `sha` that changes the BGDatabase file
    (outside the feature's scope, e.g. cdf7c5092e "导表" after c026). Its database before and after are staged so
    the step replay can compare the delta its own export produces with the delta the developers committed.
    """
    when = git(repo, 'show', '-s', '--format=%cI', sha).decode().strip()
    for line in git(repo, 'log', '--format=%H %P', '--since', when, '--all', '--', DB_PATH).decode().splitlines():
        child, *parents = line.split()
        if sha in parents:
            before, after = tree_entry(repo, sha, DB_PATH), tree_entry(repo, child, DB_PATH)
            if not (before and after):
                return None
            for oid in (before, after):
                if not (staging / oid).exists():
                    (staging / oid).write_bytes(blobs.get(oid))
            msg = git(repo, 'show', '-s', '--format=%s', child).decode().strip()
            return {'sha': child, 'message': msg, 'path': DB_PATH,
                    'before_blob': str(staging / before), 'after_blob': str(staging / after)}
    return None

def cmd_plan(a):
    pkg, work = Path(a.package), Path(a.work).resolve()
    commits = json.loads((pkg / 'History' / 'commits.json').read_text(encoding='utf-8'))
    summary = json.loads((pkg / 'History' / 'summary.json').read_text(encoding='utf-8'))
    staging = work / 'blobs'
    staging.mkdir(parents=True, exist_ok=True)
    blobs = Blobs(a.repo)
    plan_commits, last = [], {}            # last[path] = sha256 after its last feature change (None = removed)
    for c in commits:
        files = []
        for f in c['files']:
            st = f['status']
            if st.startswith('R'):
                files.append({'action': 'delete', 'path': f['old_path'], 'status': st})
                last[f['old_path']] = None
            if st.startswith('D'):
                files.append({'action': 'delete', 'path': f['path'], 'status': st})
                last[f['path']] = None
                continue
            target = staging / f['new']
            if not target.exists():
                target.write_bytes(blobs.get(f['new']))
            h = sha256(target.read_bytes())
            entry = {'action': 'write', 'path': f['path'], 'blob': str(target), 'sha256': h, 'status': st}
            if st == 'M':
                # The file in the commit's parent: commits outside the feature may have changed it since the
                # feature last touched it; the step replay starts API edits from this state.
                parent = staging / f['old']
                if not parent.exists():
                    parent.write_bytes(blobs.get(f['old']))
                entry |= {'parent_blob': str(parent), 'parent_sha256': sha256(parent.read_bytes())}
            files.append(entry)
            last[f['path']] = h
        entry_c = {'id': c['id'], 'sha': c['sha'], 'time': c['time'], 'files': files}
        if any(f['path'].endswith('.xlsx') and f['status'] == 'M' for f in c['files']):
            exp = table_export(a.repo, c['sha'], staging, blobs)
            if exp:
                entry_c['table_export'] = exp
        plan_commits.append(entry_c)

    end = summary['end_commit']
    final = []
    for path, h in sorted(last.items()):
        oid = tree_entry(a.repo, end, path)
        end_h = sha256(blobs.get(oid)) if oid else None
        if h is None:
            expect = 'absent' if end_h is None else 'absent_readded_later'
        else:
            expect = 'match' if end_h == h else 'changed_later'
        final.append({'path': path, 'sha256': end_h, 'replay_sha256': h, 'expect': expect})
    plan = {'feature': summary['feature'], 'start_commit': summary['start_commit'], 'end_commit': end,
            'commits': plan_commits, 'final_check': final}
    (work / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
    counts = {}
    for f in final:
        counts[f['expect']] = counts.get(f['expect'], 0) + 1
    longest = max(len(f['path']) for c in plan_commits for f in c['files'])
    print(json.dumps({'commits': len(plan_commits), 'files': sum(len(c['files']) for c in plan_commits),
                      'blobs_staged': len(list(staging.iterdir())), 'final_check': counts,
                      'longest_path': longest}, ensure_ascii=False))


# ---------- install the editor package into the project ----------

def cmd_install(a):
    project = Path(a.project)
    if a.mode == 'manifest':
        man = project / 'Packages' / 'manifest.json'
        data = json.loads(man.read_text(encoding='utf-8'))
        data['dependencies'][PACKAGE_NAME] = 'file:' + PACKAGE_DIR.as_posix()
        man.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print('manifest.json now references', PACKAGE_DIR, '(tracked file changed; revert with reset)')
        return
    link = project / 'Packages' / PACKAGE_NAME
    if link.exists():
        print('already installed:', link)
        return
    # A junction keeps one copy of the source; Unity treats it as an embedded package and no tracked file changes.
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(PACKAGE_DIR)], check=True)
    print('embedded (junction):', link, '->', PACKAGE_DIR)


# ---------- machine-wide job slots (shared with tools/ue-heavy.ps1) ----------

HEAVY_LOG = Path(os.environ.get('USERPROFILE', '')) / 'Work' / '.recording' / '_heavy-jobs.jsonl'


class MachineSlots:
    """
    The PC's job limits, as tools/ue-heavy.ps1 takes them: every Unity run holds one of 3 slots of
    'Global\\ue-heavy-jobs' (CPU/RAM), and a run that renders (visible editor, recording) also holds the single
    'Global\\ue-gpu-jobs' slot, since 16 GB of VRAM does not fit several GPU jobs. -nographics runs skip the GPU slot.
    """

    def __init__(self, label, gpu):
        self.label, self.gpu, self.held = label, gpu, []

    def _log(self, event, **extra):
        HEAVY_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {'time': dt.datetime.now().astimezone().isoformat(timespec='milliseconds'), 'event': event,
               'label': self.label, 'pid': os.getpid(), 'cwd': os.getcwd(), **extra}
        with HEAVY_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    def __enter__(self):
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.CreateSemaphoreW.restype = ctypes.c_void_p
        k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self.k32, t0 = k32, time.time()
        self._log('wait', gpu=self.gpu)
        for name, count, why in [('Global\\ue-heavy-jobs', 3, 'a free heavy-job slot'),
                                 *([('Global\\ue-gpu-jobs', 1, 'the GPU slot')] if self.gpu else [])]:
            h = k32.CreateSemaphoreW(None, count, count, name)
            if not h:
                raise OSError(f'cannot open semaphore {name}')
            while k32.WaitForSingleObject(h, 60000) != 0:     # WAIT_OBJECT_0
                print(now(), f'waiting for {why} ({name})', flush=True)
            self.held.append(h)
        self._log('start', waited_s=int(time.time() - t0), gpu=self.gpu)
        self.t1 = time.time()
        return self

    def __exit__(self, *exc):
        import ctypes
        self.k32.ReleaseSemaphore.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p]
        self.k32.CloseHandle.argtypes = [ctypes.c_void_p]
        for h in reversed(self.held):
            self.k32.ReleaseSemaphore(h, 1, None)
            self.k32.CloseHandle(h)
        self._log('end', duration_s=int(time.time() - self.t1))
        return False


# ---------- Unity ----------

def unity(project, log, *extra, batch=True, timeout=None):
    if not UNITY.exists():
        sys.exit(f'Unity 2022.3.10f1 not found at {UNITY}')
    # -nographics in batchmode: no GPU device. The first import crashed with D3D11 out of memory (SIGSEGV in a texture
    # upload from TextMeshPro's post-processor, which loads every imported texture) while Unreal editors shared the GPU.
    args = [str(UNITY), *(['-batchmode', '-nographics'] if batch else []), '-projectPath', str(project), '-buildTarget', 'Win64',
            '-logFile', str(log), *extra]
    print(now(), ' '.join(args), flush=True)
    t = time.time()
    with MachineSlots(f'liaozhai-replay unity {Path(str(log)).stem}', gpu=not batch):
        rc = subprocess.run(args, timeout=timeout).returncode
    print(now(), f'Unity exit {rc} after {time.time() - t:.0f}s', flush=True)
    return rc, time.time() - t


def cmd_open(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    before = status(a.project)
    rc, secs = unity(a.project, work / 'unity-open.log', '-quit')
    after = status(a.project)
    rec = {'type': 'open', 'exit_code': rc, 'seconds': round(secs), 'finished': now(),
           'changed_before': before, 'changed_after': after}
    (work / 'open-result.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in rec.items()}, ensure_ascii=False))


def cmd_files(a):
    work = Path(a.work)
    extra = ['-executeMethod', 'Superposition.LiaoZhaiReplay.FileReplay.Run',
             '-replayPlan', str(work / 'plan.json'), '-replayLog', str(work / 'replay-log.jsonl')]
    if a.until:
        extra += ['-replayUntil', a.until]
    rc, secs = unity(a.project, work / 'unity-file-replay.log', *extra)
    report_status(a.project, work, rc, secs, 'files')


def cmd_steps(a):
    work = Path(a.work).resolve()
    extra = ['-executeMethod', 'Superposition.LiaoZhaiReplay.StepReplay.Run',
             '-replayPlan', str(work / 'plan.json'), '-replayWorkflow', str(Path(a.package) / 'workflow.jsonl'),
             '-replayLog', str(work / 'step-log.jsonl')]
    if a.until:
        extra += ['-replayUntil', a.until]
    if not a.record:
        rc, secs = unity(a.project, work / 'unity-step-replay.log', *extra)
        report_status(a.project, work, rc, secs, 'steps')
        return
    with MachineSlots('liaozhai-replay recording (visible editor + ffmpeg)', gpu=True):
        rc, secs = record(a, work, extra)
    report_status(a.project, work, rc, secs, 'steps')


# ---------- stage 4: recording ----------

FFMPEG = shutil.which('ffmpeg') or next(iter(str(p) for p in sorted(Path(os.environ.get('LOCALAPPDATA', '')).glob(
    'Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe'))), None)


def editor_window(pid, timeout=60):
    """The Unity editor's main window (visible, titled '… - Unity 2022.3…') for process pid."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if 'Unity 2022' in buf.value:
                found.append((hwnd, buf.value))
        return True

    t = time.time()
    while time.time() - t < timeout:
        found.clear()
        user32.EnumWindows(cb, 0)
        if found:
            return found[0]
        time.sleep(1)
    return None, None


def record(a, work, extra):
    """Visible replay recorded with ffmpeg's gfxcapture (Windows Graphics Capture) of the editor window only."""
    if not FFMPEG:
        sys.exit('ffmpeg not found (winget install Gyan.FFmpeg)')
    hs = work / 'handshake'
    shutil.rmtree(hs, ignore_errors=True)
    video = work / 'replay.mp4'
    args = [str(UNITY), '-projectPath', str(a.project), '-buildTarget', 'Win64',
            '-logFile', str(work / 'unity-step-replay.log'), *extra,
            '-replayHandshake', str(hs), '-replayStepDelay', str(a.step_delay)]
    print(now(), ' '.join(args), flush=True)
    t_start = time.time()
    editor = subprocess.Popen(args)
    while not (hs / 'ready').exists():
        if editor.poll() is not None:
            sys.exit(f'Unity exited ({editor.returncode}) before the replay was ready')
        time.sleep(1)
    hwnd, title = editor_window(editor.pid)
    if not hwnd:
        editor.kill()
        sys.exit('editor window not found')
    import ctypes
    from ctypes import wintypes
    # A fixed 1920x1080 window (not maximized, not activated): a legible capture without taking over the desktop.
    r = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    ctypes.windll.user32.SetWindowPos(hwnd, 0, max(r.left, 0), max(r.top, 0), a.width, a.height,
                                      0x0004 | 0x0010)   # SWP_NOZORDER | SWP_NOACTIVATE
    time.sleep(2)
    cap = [FFMPEG, '-hide_banner', '-y', '-f', 'lavfi',
           '-i', f'gfxcapture=hwnd={hwnd}:max_framerate={a.fps}:capture_cursor=0:resize_mode=scale_aspect',
           '-vf', f'hwdownload,format=bgra,fps={a.fps},scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24',
           # Fragmented MP4: playable up to the last fragment even if ffmpeg does not finish cleanly.
           '-movflags', '+frag_keyframe+empty_moov+default_base_moof', '-g', str(a.fps * 2), str(video)]
    print(now(), ' '.join(cap), flush=True)
    rec_log = open(work / 'ffmpeg-record.log', 'w', encoding='utf-8')
    ff = subprocess.Popen(cap, stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                          errors='replace')
    # Video time zero: the wall clock of the first encoded frame, taken from ffmpeg's first progress line.
    t_video0 = None
    import threading

    def pump():
        nonlocal t_video0
        for line in iter(ff.stderr.readline, ''):
            rec_log.write(line)
            if t_video0 is None and line.lstrip().startswith('frame='):
                try:
                    frames = int(line.split('frame=')[1].split()[0])
                except ValueError:
                    frames = 0
                t_video0 = time.time() - frames / a.fps
        rec_log.flush()

    pump_thread = threading.Thread(target=pump, daemon=True)
    pump_thread.start()
    while t_video0 is None and ff.poll() is None:
        time.sleep(0.1)
    if ff.poll() is not None:
        editor.kill()
        sys.exit('ffmpeg failed, see ffmpeg-record.log')
    time.sleep(2)
    (hs / 'go').write_text(f'{time.time():.3f}')
    # Stop capturing while the editor window still exists: the editor writes "done" after the last step and
    # waits for "stopped" before it exits.
    while not (hs / 'done').exists() and editor.poll() is None:
        time.sleep(0.5)
    try:
        ff.stdin.write('q')
        ff.stdin.flush()
        ff.stdin.close()
    except OSError:
        pass
    try:
        ff.wait(timeout=60)
    except subprocess.TimeoutExpired:
        ff.kill()
        ff.wait()
    (hs / 'stopped').write_text(f'{time.time():.3f}')
    pump_thread.join(timeout=10)
    rec_log.close()
    rc = editor.wait()
    verify_video(a, work, video, t_video0, rc, ff.returncode, title)
    return rc, time.time() - t_start


def measure_offset(video, ends, width):
    """
    Seconds to add to (editor wall clock - first-frame wall clock) to get video time, measured from the video:
    the replay panel's header line ("Commit … Step …") changes when a step ends, so the offset that puts the most
    header changes within ±0.07 s of a step end wins. The estimate from ffmpeg's progress output runs late by the
    encoder's lookahead; this corrects it from what is on screen.
    """
    import bisect
    import re
    k = width / 2858   # crop measured on a 2858-pixel-wide capture of the 1920x1080 (150 %) window
    crop = f'crop={int(1620 * k)}:{int(40 * k)}:{int(550 * k)}:{int(78 * k)}'
    run = subprocess.run([FFMPEG, '-hide_banner', '-nostats', '-i', str(video), '-an', '-vf',
                          f"{crop},select='gt(scene\\,0.002)',showinfo", '-f', 'null', '-'],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    changes = [float(x) for x in re.findall(r'pts_time:([0-9.]+)', run.stderr)]
    ends = sorted(ends)

    def hits(o):
        n = 0
        for c in changes:
            i = bisect.bisect_left(ends, c - o - 0.07)
            n += i < len(ends) and abs(c - o - ends[i]) <= 0.07
        return n

    best = max(((hits(o / 100), o / 100) for o in range(-100, 500)), default=(0, 0.0))
    return {'offset_seconds': best[1], 'panel_changes': len(changes), 'changes_matching_a_step_end': best[0],
            'changes': changes}


def residuals(changes, steps):
    """For steps that take screen time: seconds from the aligned step end to the next panel change."""
    import bisect
    d = []
    for s in steps:
        if s['mode'] == 'file_fallback':
            continue
        j = bisect.bisect_left(changes, s['video_end'] - 0.05)
        if j < len(changes):
            d.append(changes[j] - s['video_end'])
    d.sort()
    if not d:
        return {}
    q = lambda f: round(d[min(len(d) - 1, int(len(d) * f))], 2)
    return {'steps_measured': len(d), 'p50': q(0.5), 'p90': q(0.9), 'p99': q(0.99), 'max': round(d[-1], 2),
            'within_1s': round(sum(1 for x in d if abs(x) <= 1) / len(d), 3),
            'note': 'after commit boundaries and heavy imports the editor repaints late, so a step can show on '
                    'screen seconds after it ran; fallback steps take no screen time and are not measured'}


def verify_video(a, work, video, t_video0, editor_rc, recorder_rc, title):
    """video-verification.json: the video file, a full decode, and every step id aligned to video time."""
    probe = json.loads(subprocess.run(
        [str(Path(FFMPEG).with_name('ffprobe.exe')), '-v', 'error', '-print_format', 'json', '-show_streams',
         '-show_format', str(video)], capture_output=True, text=True).stdout or '{}')
    vs = next((s for s in probe.get('streams', []) if s.get('codec_type') == 'video'), {})
    decode = subprocess.run([FFMPEG, '-v', 'error', '-i', str(video), '-f', 'null', '-'], capture_output=True, text=True)
    rows = [json.loads(l) for l in (work / 'step-log.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
    steps = [r for r in rows if r['type'] == 'step']
    commits = [r for r in rows if r['type'] == 'commit']
    workflow = Path(a.package) / 'workflow.jsonl'
    duration = float(probe.get('format', {}).get('duration', 0))
    measured = measure_offset(video, [s['t_end'] - t_video0 for s in steps], vs.get('width') or 2858)
    off = measured['offset_seconds']
    aligned = [{'id': s['id'], 'commit': s['commit'], 'op': s['op'], 'mode': s['mode'], 'ok': s['ok'],
                'video_start': round(s['t_start'] - t_video0 + off, 3),
                'video_end': round(s['t_end'] - t_video0 + off, 3)}
               for s in steps]
    executed_order = [s['id'] for s in steps]
    changes = measured.pop('changes')
    measured['screen_delay_seconds'] = residuals(changes, aligned)
    out = {
        'schema': 'liaozhai.video-verification/v1',
        'video': video.name, 'sha256': sha256(video.read_bytes()), 'bytes': video.stat().st_size,
        'duration_seconds': duration, 'resolution': [vs.get('width'), vs.get('height')],
        'fps': a.fps, 'frames': int(vs.get('nb_frames', 0) or 0) or round(float(probe.get('format', {}).get('duration', 0)) * a.fps),
        'capture': 'ffmpeg gfxcapture (Windows Graphics Capture) of the Unity editor window only',
        'window_title': title,
        'workflow_sha256': sha256(workflow.read_bytes()),
        'step_log_sha256': sha256((work / 'step-log.jsonl').read_bytes()),
        'recorded_steps': len(steps),
        'all_workflow_steps_present': sorted(executed_order) == sorted(
            json.loads(l)['id'] for l in workflow.read_text(encoding='utf-8').splitlines() if l.strip()),
        # Inside a commit, imports run before API edits (see docs/unity-replay.md), so ids are in commit order,
        # not strictly in workflow order.
        'commits_in_order': [c['id'] for c in commits] == sorted(c['id'] for c in commits),
        'first_step_seconds': aligned[0]['video_start'] if aligned else None,
        'last_step_end_seconds': aligned[-1]['video_end'] if aligned else None,
        'steps_within_video': all(0 <= s['video_start'] <= duration for s in aligned),
        'video_time_zero_unix': round(t_video0, 3),
        'alignment': measured,
        'alignment_note': 'video time = editor wall clock (step-log.jsonl t_start/t_end) - wall clock of the first '
                          'encoded frame (from ffmpeg progress) + offset_seconds, measured from the video: the replay '
                          "panel's header changes when a step ends",
        'full_decode_exit_code': decode.returncode, 'full_decode_errors': decode.stderr[-2000:],
        'editor_exit_code': editor_rc, 'recorder_exit_code': recorder_rc,
        'commits': [{'id': c['id'], 'video_time': round(c['t'] - t_video0 + off, 3), 'counts': c['counts']}
                    for c in commits],
        'steps': aligned,
    }
    out['passed'] = (decode.returncode == 0 and out['all_workflow_steps_present'] and out['steps_within_video']
                     and out['commits_in_order'])
    (work / 'video-verification.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k not in ('steps', 'commits')}, ensure_ascii=False, indent=1))


# ---------- git status of the project ----------

def status(project):
    """Changed tracked files and untracked files (ignored ones, e.g. Library/, are left out)."""
    raw = git(project, 'status', '--porcelain=v1', '-z', '--untracked-files=all').decode()
    out, items = [], raw.split('\0')
    i = 0
    while i < len(items):
        e = items[i]
        if not e:
            i += 1
            continue
        code, path = e[:2], e[3:]
        if code[0] == 'R':
            i += 1  # skip the rename source
        if not any(path == h or path.startswith(h + '/') for h in HARNESS):
            out.append(code + ' ' + path)
        i += 1
    return out


def report_status(project, work, rc, secs, kind):
    plan = json.loads((work / 'plan.json').read_text(encoding='utf-8'))
    touched = {f['path'] for c in plan['commits'] for f in c['files']}
    changed = status(project)
    # What Unity itself changes on opening the start snapshot (stage 1) is not caused by the replay.
    opened = work / 'open-result.json'
    baseline = set(json.loads(opened.read_text(encoding='utf-8'))['changed_after']) if opened.exists() else set()
    expected = [s for s in changed if s[3:] in touched]
    from_open = [s for s in changed if s[3:] not in touched and s in baseline]
    unexpected = [s for s in changed if s[3:] not in touched and s not in baseline]
    rec = {'type': 'git_status', 'replay': kind, 'unity_exit_code': rc, 'seconds': round(secs),
           'finished': now(), 'changed_expected': len(expected), 'changed_by_unity_on_open': from_open,
           'unexpected': unexpected}
    (work / f'{kind}-status.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({**rec, 'unexpected': unexpected[:50]}, ensure_ascii=False, indent=1))


def cmd_status(a):
    report_status(a.project, Path(a.work), None, 0, 'manual')


def cmd_reset(a):
    """Put every path the plan touches back to the start commit; leave Library/ and the harness alone."""
    project, work = Path(a.project), Path(a.work)
    plan = json.loads((work / 'plan.json').read_text(encoding='utf-8'))
    start = plan['start_commit']
    touched = sorted({f['path'] for c in plan['commits'] for f in c['files']})
    at_start = set()
    for part in chunks(touched):     # Windows limits a command line to 32k characters
        at_start |= set(git(project, 'ls-tree', '-r', '-z', '--name-only', start, '--', *part)
                        .decode().split('\0')) - {''}
    for p in touched:
        if p not in at_start:
            f = project / p
            if f.exists():
                f.unlink()
    for p in touched:
        d = (project / p).parent
        while d != project and d.exists() and not any(d.iterdir()):
            d.rmdir()
            d = d.parent
    for part in chunks(sorted(at_start)):
        git(project, 'checkout', start, '--', *part)
    # Unity rewrites some tracked files on open (see open-result.json); --all restores those too.
    if a.all:
        for part in chunks([s[3:] for s in status(project) if not s.startswith('??')]):
            git(project, 'checkout', 'HEAD', '--', *part)
    print('reset', len(touched), 'paths;', 'remaining changes:', status(project)[:20])


def mismatch_cause(commit_file: Path, replay_file: Path) -> str:
    """Classify how a file produced through editor APIs differs from the committed file."""
    import difflib
    import re
    if not replay_file.exists():
        return 'missing'
    if commit_file.name.endswith('.xlsx') or replay_file.suffix == '.xlsx':
        # Cells are edited in the sheet XML and read back; the zip itself cannot match Excel's bytes.
        return 'xlsx_container_bytes'
    a = commit_file.read_bytes().decode('utf-8', 'replace').splitlines()
    b = replay_file.read_bytes().decode('utf-8', 'replace').splitlines()
    if sorted(a) == sorted(b):
        # Same lines, other order: list order the workflow does not record (converter sorts changed paths).
        return 'list_order_only'
    sm = difflib.SequenceMatcher(None, a, b)
    changed = [(a[i1:i2], b[j1:j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']
    underscore = re.compile(r'(?<=\d)_(?=\d)')
    if all(len(x) == len(y) and all(underscore.sub('', p) == q for p, q in zip(x, y)) for x, y in changed):
        # The converter's YAML 1.1 loader read `10019_1` as the integer 100191.
        return 'converter_yaml11_underscore_number'
    if all(not x and all(l.strip().startswith(('- target:', 'propertyPath:', 'value:', 'objectReference:')) for l in y)
           or (x and x[0].strip().startswith('m_RemovedComponents')) for x, y in changed):
        return 'prefab_instance_override_semantics'
    return 'other'


def cmd_verify(a):
    """Re-run the video verification for an existing recording (reads the previous video-verification.json)."""
    work = Path(a.work).resolve()
    old = json.loads((work / 'video-verification.json').read_text(encoding='utf-8'))
    verify_video(a, work, work / old['video'], old['video_time_zero_unix'], old['editor_exit_code'],
                 old['recorder_exit_code'], old['window_title'])


def cmd_report(a):
    """Summarize step-log.jsonl: steps by op and mode, files by mode and boundary outcome, top errors."""
    from collections import Counter
    work = Path(a.work)
    rows = [json.loads(l) for l in (work / a.log).read_text(encoding='utf-8').splitlines() if l.strip()]
    steps = [r for r in rows if r['type'] == 'step']
    commits = [r for r in rows if r['type'] == 'commit']
    by_mode = Counter((s['op'], s['mode'], 'ok' if s['ok'] else 'errors') for s in steps)
    files = Counter((f['mode'], f['outcome']) for c in commits for f in c['files'])
    # A file counts as reproduced through the editor when every step on it ran in api/import mode without
    # errors and the file hashed exactly at the commit boundary.
    errors = Counter()
    for s in steps:
        for e in s['errors'][:3]:
            errors[(s['op'], e[:120])] += 1
    final = next((r for r in rows if r['type'] == 'final'), None)
    # Why API-produced files differ from the commit (copies kept under work/mismatch/<commit>/).
    plan = json.loads((work / 'plan.json').read_text(encoding='utf-8'))
    blob = {(c['id'], f['path']): f.get('blob') for c in plan['commits'] for f in c['files']}
    causes, detail = Counter(), []
    for c in commits:
        for f in c['files']:
            if f['mode'] != 'api' or f['outcome'] != 'mismatch':
                continue
            kept = work / 'mismatch' / c['id'] / f['path']
            cause = mismatch_cause(Path(blob[(c['id'], f['path'])]), kept)
            causes[cause] += 1
            detail.append({'commit': c['id'], 'path': f['path'], 'cause': cause})
    out = {'steps': len(steps), 'steps_by_op_mode': {' '.join(k): v for k, v in sorted(by_mode.items())},
           'readback_ok': sum(s['readback_ok'] for s in steps), 'readback_failed': sum(s['readback_failed'] for s in steps),
           'files_by_mode_outcome': {' '.join(k): v for k, v in sorted(files.items())},
           'api_mismatch_causes': dict(causes.most_common()), 'api_mismatches': detail,
           'top_errors': [[n, *k] for k, n in errors.most_common(15)],
           'final': final and final.get('counts'), 'seconds': final and round(final.get('total_seconds', 0))}
    (work / (Path(a.log).stem + '-summary.json')).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('open'); s.add_argument('--project', required=True); s.add_argument('--work', required=True)
    s = sub.add_parser('plan'); s.add_argument('--package', required=True); s.add_argument('--repo', required=True)
    s.add_argument('--work', required=True)
    s = sub.add_parser('install'); s.add_argument('--project', required=True)
    s.add_argument('--mode', choices=['embed', 'manifest'], default='embed')
    for name in ('files', 'steps'):
        s = sub.add_parser(name); s.add_argument('--project', required=True); s.add_argument('--work', required=True)
        s.add_argument('--until')
        if name == 'steps':
            s.add_argument('--package', required=True); s.add_argument('--record', action='store_true')
            s.add_argument('--fps', type=int, default=30); s.add_argument('--step-delay', type=float, default=0.5)
            s.add_argument('--width', type=int, default=1920); s.add_argument('--height', type=int, default=1080)
    s = sub.add_parser('status'); s.add_argument('--project', required=True); s.add_argument('--work', required=True)
    s = sub.add_parser('verify'); s.add_argument('--work', required=True); s.add_argument('--package', required=True)
    s.add_argument('--fps', type=int, default=30)
    s = sub.add_parser('report');s.add_argument('--work', required=True); s.add_argument('--log', default='step-log.jsonl')
    s = sub.add_parser('reset');s.add_argument('--project', required=True); s.add_argument('--work', required=True)
    s.add_argument('--all', action='store_true', help='also restore other tracked files Unity rewrote')
    a = p.parse_args()
    globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    main()

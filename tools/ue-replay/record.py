"""record: the world-building video (docs/ue-replay.md, 2.5).

A visible editor on the replayed project plays work/world-ops.jsonl one op per Slate tick (editor/ue_world_replay.py,
mode play): every map is created empty and its actors come in through the editor's Import into Level in the order the
scripts spawned them, group by group, with the viewport camera on each group. ffmpeg's gfxcapture records the editor
window only (Windows Graphics Capture; other windows, the cursor and other monitors are not recorded). Like a
pipeline recording, it raises builds/_queue/_recording-wants-gpu (session GPU jobs yield) and holds the machine's
GPU slot for the editor's whole length.

Outputs in work/video/: raw.mp4 (fragmented MP4), replay.mp4 (captions burned in), captions.ass, ops-played.jsonl
(wall clock per op), video-verification.json (every op id with its video time, decode check, hashes).
"""
import ctypes
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from ctypes import wintypes

import runner

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYER = os.path.join(HERE, "editor", "ue_world_replay.py").replace("\\", "/")


def gpu_priority_run(label, argv, env, root, holder=None):
    """Run the visible editor with recording priority, as the pipeline recorder does: keep
    builds/_queue/_recording-wants-gpu fresh (ue-heavy holds session GPU jobs back while it is), take the machine's GPU
    slot (Global\\ue-gpu-jobs) directly, run the editor, release. Returns (exit code, seconds)."""
    flag = os.path.join(root, "builds", "_queue", "_recording-wants-gpu")
    heavy_log = os.path.join(root, ".recording", "_heavy-jobs.jsonl")
    stop = threading.Event()
    me = "pid %d %s" % (os.getpid(), label)

    def keep_flag():
        while not stop.is_set():
            try:
                os.makedirs(os.path.dirname(flag), exist_ok=True)
                with open(flag, "w", encoding="ascii", errors="replace") as f:
                    f.write("%s %s" % (datetime.datetime.now().astimezone().isoformat(), me))
            except OSError:
                pass
            stop.wait(60)

    def log(event, **kw):
        row = {"time": datetime.datetime.now().astimezone().isoformat(timespec="milliseconds"), "event": event,
               "label": label, "pid": os.getpid(), "cwd": os.getcwd(), "gpu": True}
        row.update(kw)
        try:
            with open(heavy_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
        except OSError:
            pass

    k32 = ctypes.windll.kernel32
    k32.CreateSemaphoreW.restype = wintypes.HANDLE
    k32.CreateSemaphoreW.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_long, wintypes.LPCWSTR]
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.ReleaseSemaphore.argtypes = [wintypes.HANDLE, ctypes.c_long, ctypes.c_void_p]
    sem = k32.CreateSemaphoreW(None, 1, 1, "Global\\ue-gpu-jobs")
    if not sem:
        sys.exit("cannot open the GPU slot semaphore")
    ft = threading.Thread(target=keep_flag, daemon=True)
    ft.start()
    t0 = time.time()
    log("wait", command=" ".join(argv))
    print(runner.now(), "recording priority flag set; waiting for the GPU slot", flush=True)
    if os.environ.get("GF_GPU_SLOT_HELD") == "1":   # a killed earlier capture left the slot taken: adopt it
        print(runner.now(), "adopting the GPU slot left held by the previous capture", flush=True)
    else:
        while k32.WaitForSingleObject(sem, 60000) != 0:   # WAIT_OBJECT_0
            pass
    log("start", waited_s=int(time.time() - t0))
    print(runner.now(), "GPU slot held after %d s; starting the editor" % (time.time() - t0), flush=True)
    t1 = time.time()
    try:
        e = dict(os.environ)
        e.update(env)
        proc = subprocess.Popen(argv, env=e)
        if holder is not None:
            holder["proc"] = proc
        code = proc.wait()
    finally:
        k32.ReleaseSemaphore(sem, 1, None)
        stop.set()
        try:
            if open(flag, encoding="ascii", errors="replace").read().endswith(me):
                os.remove(flag)
        except OSError:
            pass
        log("end", exit_code=locals().get("code"), duration_s=int(time.time() - t1))
    return code, round(time.time() - t1, 1)


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    c = sorted(glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe")))
    return c[-1] if c else None


def editor_window(title_part, timeout=600):
    """Visible top-level window of UnrealEditor.exe whose title contains title_part."""
    user32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if title_part.lower() not in buf.value.lower():
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        # PROCESS_QUERY_LIMITED_INFORMATION is enough for QueryFullProcessImageNameW (GetModuleBaseNameW would need
        # VM_READ and returns nothing with it, so no window ever matched)
        h = k32.OpenProcess(0x1000, False, pid.value)
        name = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if h:
            k32.QueryFullProcessImageNameW(h, 0, name, ctypes.byref(size))
            k32.CloseHandle(h)
        if os.path.basename(name.value).lower() == "unrealeditor.exe":
            found.append((hwnd, buf.value, pid.value))
        return True

    t = time.time()
    while time.time() - t < timeout:
        found.clear()
        user32.EnumWindows(cb, 0)
        if found:
            return found[0]
        time.sleep(1)
    return None, None, None


def ass_time(s):
    s = max(0.0, s)
    return "%d:%02d:%05.2f" % (int(s // 3600), int(s % 3600 // 60), s % 60)


def ass_escape(t):
    return (t or "").replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def write_captions(path, segments, width, height):
    """segments: [(t0, t1, top line, bottom line)] in video seconds."""
    fs_top = max(18, height // 40)
    fs_bot = max(16, height // 48)
    head = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: %d" % width, "PlayResY: %d" % height, "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
            "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Top,Microsoft YaHei,%d,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,3,2,0,7,24,24,18,1" % fs_top,
            "Style: Bot,Microsoft YaHei,%d,&H00E8E8E8,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,3,2,0,1,24,24,22,1" % fs_bot,
            "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    rows = []
    for t0, t1, top, bot in segments:
        if t1 <= t0:
            continue
        rows.append("Dialogue: 0,%s,%s,Top,,0,0,0,,%s" % (ass_time(t0), ass_time(t1), ass_escape(top)))
        if bot:
            rows.append("Dialogue: 0,%s,%s,Bot,,0,0,0,,%s" % (ass_time(t0), ass_time(t1), ass_escape(bot[:220])))
    with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(head + rows) + "\n")


def cmd_record(cfg, a):
    """Runs the capture; however it ends (success, sys.exit, error), a still-running editor is closed and the editor
    thread is joined, so gpu_priority_run's finally releases the GPU slot exactly once (a daemon thread would otherwise
    be killed at interpreter exit without releasing it)."""
    holder = {}
    try:
        _record(cfg, a, holder)
    finally:
        th, proc = holder.get("thread"), holder.get("proc")
        if th is not None and th.is_alive():
            if proc is not None and proc.poll() is None:
                print(runner.now(), "closing the editor so the GPU slot is released", flush=True)
                proc.terminate()
            th.join(timeout=300)


def _record(cfg, a, holder):
    ctx = runner.Ctx(cfg)
    ff = ffmpeg_exe()
    if not ff:
        sys.exit("ffmpeg not found")
    ops_path = a.only or os.path.join(ctx.work, "world-ops.jsonl")
    if not os.path.exists(ops_path):
        sys.exit("run derive first")
    vd = os.path.join(ctx.work, "video" if not a.only else "video-test")
    uproject = os.path.join(cfg["truth_dir"], cfg["uproject"]) if a.which == "truth" else ctx.uproject
    hs = os.path.join(vd, "handshake")
    shutil.rmtree(hs, ignore_errors=True)
    os.makedirs(hs, exist_ok=True)
    played = os.path.join(vd, "ops-played.jsonl")
    if os.path.exists(played):
        os.remove(played)
    raw = os.path.join(vd, "raw.mp4")
    fps = 30
    width, height = 1920, 1080
    # The player starts as a Python start-up script (init_unreal.py in a UE_PYTHONPATH folder): -ExecutePythonScript
    # quits the editor as soon as the script returns (QUIT_EDITOR), and the player only registers a tick callback.
    startup = os.path.join(vd, "startup")
    os.makedirs(startup, exist_ok=True)
    with open(os.path.join(startup, "init_unreal.py"), "w", encoding="utf-8") as f:
        f.write("import runpy\nrunpy.run_path(%r, run_name='ue_world_replay')\n" % PLAYER)
    env = {"UE_WORLD_REPLAY_ARGS": "--ops %s --mode play --prefix /Game/_Replay --handshake %s --log %s --speed %s" % (
        ops_path.replace("\\", "/"), hs.replace("\\", "/"), played.replace("\\", "/"), a.speed if hasattr(a, "speed") else 1.0),
        "UE_PYTHONPATH": startup}
    log = os.path.join(ctx.logs, "record_editor.log")
    argv = [ctx.editor_cmd.replace("UnrealEditor-Cmd.exe", "UnrealEditor.exe"), uproject,
            "-nosplash", "-NoSound", "-ResX=%d" % width, "-ResY=%d" % height,
            "-ini:EditorPerProjectUserSettings:[/Script/LiveCoding.LiveCodingSettings]:bEnabled=False", "-abslog=" + log]
    t_start = time.time()
    def run_editor():
        holder["code"], holder["secs"] = gpu_priority_run("ue-replay %s world-building video" % cfg["game"], argv, env, cfg["root"], holder)

    th = threading.Thread(target=run_editor, daemon=True)
    holder["thread"] = th
    th.start()
    print(runner.now(), "editor launch requested (recording priority on the GPU slot); waiting for ready", flush=True)
    while not os.path.exists(os.path.join(hs, "ready")):
        if not th.is_alive():
            sys.exit("editor exited (%s) before the replay was ready; see %s" % (holder.get("code"), log))
        time.sleep(2)
    time.sleep(5)
    if not th.is_alive():
        sys.exit("editor exited (%s) right after ready; see %s" % (holder.get("code"), log))
    hwnd, title, pid = editor_window(os.path.splitext(cfg["uproject"])[0])
    if not hwnd:
        sys.exit("editor window not found")
    r = wintypes.RECT()
    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    ctypes.windll.user32.SetWindowPos(hwnd, 0, max(r.left, 0), max(r.top, 0), width, height, 0x0004 | 0x0010)
    time.sleep(3)
    cap = [ff, "-hide_banner", "-y", "-f", "lavfi",
           "-i", "gfxcapture=hwnd=%d:max_framerate=%d:capture_cursor=0:resize_mode=scale_aspect" % (hwnd, fps),
           "-vf", "hwdownload,format=bgra,fps=%d,scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p" % fps,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
           "-movflags", "+frag_keyframe+empty_moov+default_base_moof", "-g", str(fps * 2), raw]
    rec_log = open(os.path.join(vd, "ffmpeg-record.log"), "w", encoding="utf-8")
    fp = subprocess.Popen(cap, stdin=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    t_video0 = [None]

    def pump():
        for line in iter(fp.stderr.readline, ""):
            rec_log.write(line)
            if t_video0[0] is None and line.lstrip().startswith("frame="):
                try:
                    frames = int(line.split("frame=")[1].split()[0])
                except ValueError:
                    frames = 0
                t_video0[0] = time.time() - frames / fps
        rec_log.flush()

    pt = threading.Thread(target=pump, daemon=True)
    pt.start()
    while t_video0[0] is None and fp.poll() is None:
        time.sleep(0.1)
    if fp.poll() is not None:
        sys.exit("ffmpeg failed, see ffmpeg-record.log")
    time.sleep(2)
    with open(os.path.join(hs, "go"), "w") as f:
        f.write("%.3f" % time.time())
    print(runner.now(), "recording; go", flush=True)
    while not os.path.exists(os.path.join(hs, "done")) and th.is_alive():
        time.sleep(1)
    time.sleep(2)
    try:
        fp.stdin.write("q")
        fp.stdin.flush()
        fp.stdin.close()
    except OSError:
        pass
    try:
        fp.wait(timeout=120)
    except subprocess.TimeoutExpired:
        fp.kill()
        fp.wait()
    with open(os.path.join(hs, "stopped"), "w") as f:
        f.write("%.3f" % time.time())
    pt.join(timeout=10)
    rec_log.close()
    th.join(timeout=600)
    print(runner.now(), "editor exit %s; ffmpeg exit %s" % (holder.get("code"), fp.returncode), flush=True)
    finish(ctx, cfg, ff, raw, played, t_video0[0], fps, width, height, holder, fp.returncode, title, time.time() - t_start, ops_path)


def probe(ff, path):
    fprobe = ff.replace("ffmpeg.exe", "ffprobe.exe")
    r = subprocess.run([fprobe, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,nb_read_frames,r_frame_rate:format=duration,size", "-of", "json", path],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"error": r.stderr[-400:]}


def finish(ctx, cfg, ff, raw, played_path, t_video0, fps, width, height, holder, ff_code, title, secs, ops_path):
    vd = os.path.dirname(raw)
    ops = {}
    with open(ops_path, encoding="utf-8") as f:
        for l in f:
            o = json.loads(l)
            ops[o["id"]] = o
    played = [json.loads(l) for l in open(played_path, encoding="utf-8")] if os.path.exists(played_path) else []
    info = probe(ff, raw)
    st = (info.get("streams") or [{}])[0]
    vw, vh = int(st.get("width", width)), int(st.get("height", height))
    # caption segments: one per run (commit + script) on top, the current map and outliner group with the builder's
    # own row reason below
    segs = []
    cur = None
    for p in played:
        o = ops.get(p["id"], {})
        src = o.get("source", {})
        top = "%s  %s  %s" % (src.get("commit", "")[:7], os.path.basename(src.get("script", "")), src.get("commit_subject", ""))
        grp = (o.get("presentation") or {}).get("group") or ""
        bot = "%s  %s  %s" % (o.get("target", "").rsplit("/", 1)[-1], grp, o.get("reason") or "")
        t = p["t0"] - t_video0
        if cur and cur[2] == top and cur[3] == bot:
            cur[1] = p["t1"] - t_video0 + 0.5
            continue
        if cur:
            cur[1] = min(cur[1], t) if cur[1] > t else cur[1]
            segs.append(tuple(cur))
        cur = [t, p["t1"] - t_video0 + 0.5, top, bot]
    if cur:
        segs.append(tuple(cur))
    # continuous captions: each segment lasts until the next one starts
    segs = [(s[0], (segs[i + 1][0] if i + 1 < len(segs) else s[1] + 2.0), s[2], s[3]) for i, s in enumerate(segs)]
    ass = os.path.join(vd, "captions.ass")
    write_captions(ass, segs, vw, vh)
    final = os.path.join(vd, "replay.mp4")
    ass_arg = ass.replace("\\", "/").replace(":", "\\:")
    r = subprocess.run([ff, "-hide_banner", "-y", "-i", raw, "-vf", "subtitles='%s'" % ass_arg, "-c:v", "libx264", "-preset", "medium",
                        "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", final], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    burn_ok = r.returncode == 0
    dec = subprocess.run([ff, "-v", "error", "-i", final if burn_ok else raw, "-f", "null", "-"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    vinfo = probe(ff, final if burn_ok else raw)

    def sha(p):
        return runner.sha256_file(p) if os.path.exists(p) else None

    steps = [{"id": p["id"], "op": p["op"], "video_start": round(p["t0"] - t_video0, 3), "video_end": round(p["t1"] - t_video0, 3),
              "result": p.get("result")} for p in played]
    ok_ops = sum(1 for p in played if not (p.get("result") or {}).get("error") and (p.get("result") or {}).get("pasted", True) is not False)
    ver = {"schema": "ue-replay.video-verification/v1", "game": cfg["game"], "final_commit": ctx.ledger["final"],
           "video": {"file": "replay.mp4", "sha256": sha(final if burn_ok else raw), "probe": vinfo, "full_decode_errors": dec.stderr[-2000:],
                     "captions": "burned in from captions.ass (commit, script, map, outliner group, the builder's row reason)"},
           "raw": {"file": "raw.mp4", "sha256": sha(raw)},
           "capture": "ffmpeg gfxcapture (Windows Graphics Capture) of the Unreal Editor window only, %d fps" % fps,
           "window_title": title, "editor_exit_code": holder.get("code"), "ffmpeg_exit_code": ff_code, "seconds": round(secs, 1),
           "ops_total": len(ops), "ops_played": len(played), "ops_ok": ok_ops,
           "world_ops_sha256": sha(ops_path),
           "alignment": "video time = editor wall clock of the op - wall clock of the first encoded frame (from ffmpeg progress); "
                        "expect the picture up to ~1 s later (encoder lookahead, viewport repaint)",
           "steps": steps}
    runner.jdump(os.path.join(vd, "video-verification.json"), ver)
    print(json.dumps({k: v for k, v in ver.items() if k not in ("steps",)}, indent=1)[:3000])

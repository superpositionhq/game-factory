"""World ops replayed through the editor's own copy/paste, one actor at a time (docs/ue-replay.md, 2.5).

  UnrealEditor[-Cmd] <uproject> -run=pythonscript -script="ue_world_replay.py --ops <ops.jsonl> --mode check|play
                     [--prefix /Game/_Replay] [--handshake <dir>] [--log <steps.jsonl>] [--speed 1.0]"
  or, visible:  UnrealEditor <uproject> -ExecutePythonScript="ue_world_replay.py ..."

ops.jsonl (written by ue_replay.py derive), one op per line:
  ue.level.create  {"map": "/Game/LN/Maps/L1_Courtyard"}                  new empty level (under --prefix)
  ue.actor.spawn   {"t3d": "<Begin Actor ...End Actor>", "label", "folder", "location"}   paste at the original location
  ue.actor.remove  {"label", "name"}                                       destroy
  ue.actor.update  {"t3d": ...}                                            destroy + paste (all properties as saved)
  ue.level.save    {}
  ui.caption       {"text": ...}                                           nothing in the level (caption track only)

check: runs every op as fast as possible (headless) and saves the levels, so they can be dumped and compared with the
       maps the scripts built. play: one op per Slate tick with pacing, the viewport camera framing each group of
       actors, and a ready/go/done/stopped handshake with the recorder; every op's wall-clock start/end is logged.
"""
import argparse
import ctypes
import json
import os
import shlex
import sys
import time

import unreal

LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
EAL = unreal.EditorAssetLibrary


def args():
    raw = sys.argv[1:]
    if not raw and os.environ.get("UE_WORLD_REPLAY_ARGS"):  # -ExecutePythonScript passes no arguments
        raw = [os.environ["UE_WORLD_REPLAY_ARGS"]]
    if len(raw) == 1 and " " in raw[0]:
        raw = shlex.split(raw[0])
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", required=True)
    ap.add_argument("--mode", default="check")
    ap.add_argument("--prefix", default="/Game/_Replay")
    ap.add_argument("--handshake", default="")
    ap.add_argument("--log", default="")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--quit", default="1")
    return ap.parse_args(raw)


# ------------------------------------------------------------------------------------------- clipboard
CF_UNICODETEXT = 13
_u32 = ctypes.windll.user32
_k32 = ctypes.windll.kernel32
_k32.GlobalAlloc.restype = ctypes.c_void_p
_k32.GlobalLock.restype = ctypes.c_void_p
_k32.GlobalLock.argtypes = [ctypes.c_void_p]
_k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
_u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]


def set_clipboard(text):
    data = (text + "\0").encode("utf-16-le")
    for _ in range(50):
        if _u32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        raise RuntimeError("clipboard busy")
    try:
        _u32.EmptyClipboard()
        h = _k32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
        p = _k32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        _k32.GlobalUnlock(h)
        _u32.SetClipboardData(CF_UNICODETEXT, h)
    finally:
        _u32.CloseClipboard()


def world():
    return UES.get_editor_world()


T3D_TMP = os.path.join(os.environ.get("TEMP", "."), "ue_world_replay_%d.t3d" % os.getpid())


def paste(t3d):
    """Add one actor block to the current level at its saved location, every saved property included: the editor's
    "Import into Level" (MAP IMPORTADD), which reads the same T3D text as copy/paste from a file, so the user's
    clipboard is never touched."""
    with open(T3D_TMP, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("Begin Map\n   Begin Level\n" + t3d + "\n   End Level\nEnd Map\n")
    before = set(a.get_path_name() for a in EAS.get_all_level_actors())
    # no quotes: Map_Import takes the extension from the raw argument, and a closing quote makes it "t3d\""
    unreal.SystemLibrary.execute_console_command(world(), "MAP IMPORTADD FILE=%s" % T3D_TMP.replace("\\", "/"))
    new = [a for a in EAS.get_all_level_actors() if a.get_path_name() not in before]
    return new[0] if new else None


def typed(cur, v):
    """A dumped value (lists for vectors and colours, enum names as text) back into the type the property has."""
    if isinstance(cur, unreal.LinearColor):
        return unreal.LinearColor(*v)
    if isinstance(cur, unreal.Color):
        return unreal.Color(r=v[0], g=v[1], b=v[2], a=v[3])
    if isinstance(cur, unreal.Vector):
        return unreal.Vector(*v)
    if isinstance(cur, unreal.Rotator):
        return unreal.Rotator(*v)
    if isinstance(cur, unreal.EnumBase):
        return getattr(type(cur), v)
    if isinstance(cur, unreal.Object) or cur is None and isinstance(v, str) and v.startswith("/"):
        return unreal.load_object(None, v) if v else None
    return v


def spawn_fallback(p):
    """Some actors do not come through Import into Level (it clears the world's scene and navigation first: height fog
    and nav-mesh bounds in the pilot). They are spawned from their class the way the level scripts did, and the dumped
    settings of their components are applied."""
    s = p["spawn"]
    cls = unreal.load_class(None, s["class"])
    if cls is None:
        return None
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(*s["location"]), unreal.Rotator(*s["rotation"]))
    if a is None:
        return None
    a.set_actor_scale3d(unreal.Vector(*s["scale"]))
    a.set_actor_label(s["label"])
    if s.get("folder"):
        a.set_folder_path(s["folder"])
    for ci in s.get("components", []):
        cc = unreal.load_class(None, ci["class"])
        comps = a.get_components_by_class(cc) if cc else []
        if not comps:
            continue
        c = comps[0]
        for k, v in ci.items():
            if k in ("class", "name", "rel", "parent", "collision_profile", "materials"):
                continue
            try:
                c.set_editor_property(k, typed(c.get_editor_property(k), v))
            except Exception:
                pass
    return a


def find(label):
    for a in EAS.get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def target_map(m, prefix):
    return prefix + "/" + m.replace("/Game/", "", 1)


# ------------------------------------------------------------------------------------------- ops
class Player:
    def __init__(self, a, ops):
        self.a = a
        self.ops = ops
        self.i = 0
        self.wait_until = 0.0
        self.log = open(a.log, "a", encoding="utf-8") if a.log else None
        self.handle = None
        self.state = "init"
        self.group = None
        self.made = []
        self.busy = False   # Import into Level runs a nested Slate loop that calls tick() again: never re-enter

    def emit(self, rec):
        if self.log:
            self.log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.log.flush()

    def frame(self, op):
        """Viewport camera on the group the op belongs to (play mode)."""
        g = op.get("camera")
        if not g:
            return
        loc = unreal.Vector(*g["location"])
        rot = unreal.Rotator(0.0, g["pitch"], g["yaw"])  # roll, pitch, yaw
        UES.set_level_viewport_camera_info(loc, rot)

    def do(self, op):
        k = op["op"]
        p = op.get("params", {})
        res = {}
        if k == "ue.level.create":
            path = target_map(p.get("as") or p["map"], self.a.prefix)
            if EAL.does_asset_exist(path):
                EAL.delete_asset(path)
            folder = path.rsplit("/", 1)[0]
            if not EAL.does_directory_exist(folder):
                EAL.make_directory(folder)
            ok = LES.new_level(path)
            self.made.append(path)
            res = {"level": path, "ok": bool(ok)}
        elif k in ("ue.actor.spawn", "ue.actor.update"):
            if k == "ue.actor.update":
                old = find(p["label"])
                if old:
                    EAS.destroy_actor(old)
            n0 = len(EAS.get_all_level_actors())
            if p.get("t3d"):
                paste(p["t3d"])
            a = find(p["label"])
            res = {"pasted": a is not None, "mode": "import_t3d"}
            if a is None and p.get("spawn"):
                a = spawn_fallback(p)
                res = {"pasted": a is not None, "mode": "spawn_fallback"}
            res["actors_before"] = n0
            res["actors_after"] = len(EAS.get_all_level_actors())
        elif k == "ue.actor.remove":
            old = find(p["label"])
            res = {"removed": bool(old and EAS.destroy_actor(old))}
        elif k == "ue.level.save":
            # Import into Level leaves the level without a file name for SaveCurrentLevel: save it to its path
            path = self.made[-1] if self.made else target_map(op["target"], self.a.prefix)
            res = {"saved": bool(unreal.EditorLoadingAndSavingUtils.save_map(world(), path)), "level": path}
        return res

    def run_all(self):
        """check mode: every op at once."""
        t0 = time.time()
        n_fail = 0
        for i, op in enumerate(self.ops):
            ts = time.time()
            try:
                res = self.do(op)
            except Exception as e:  # recorded, the replay goes on
                res = {"error": str(e)[:300]}
            if res.get("error") or res.get("pasted") is False or res.get("ok") is False:
                n_fail += 1
            self.emit({"id": op["id"], "op": op["op"], "t0": ts, "t1": time.time(), "result": res})
        unreal.log("ue_world_replay: %d ops, %d failed, %.1f s" % (len(self.ops), n_fail, time.time() - t0))

    # play mode -------------------------------------------------------------------------------------
    def start(self):
        hs = self.a.handshake
        if hs:
            os.makedirs(hs, exist_ok=True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, dt):
        if self.busy:
            return
        self.busy = True
        try:
            self._tick(dt)
        finally:
            self.busy = False

    def _tick(self, dt):
        now = time.time()
        hs = self.a.handshake
        if self.state == "init":
            if hs:
                open(os.path.join(hs, "ready"), "w").write("%.3f" % now)
            self.state = "wait_go"
            return
        if self.state == "wait_go":
            if not hs or os.path.exists(os.path.join(hs, "go")):
                self.state = "run"
                self.wait_until = now + 1.0
            return
        if self.state == "run":
            if now < self.wait_until:
                return
            if self.i >= len(self.ops):
                if hs:
                    open(os.path.join(hs, "done"), "w").write("%.3f" % now)
                self.state = "wait_stopped"
                return
            op = self.ops[self.i]
            self.i += 1
            if op.get("camera") and op.get("group") != self.group:
                self.group = op.get("group")
                self.frame(op)
            ts = time.time()
            try:
                res = self.do(op)
            except Exception as e:
                res = {"error": str(e)[:300]}
            self.emit({"id": op["id"], "op": op["op"], "t0": ts, "t1": time.time(), "result": res})
            self.wait_until = time.time() + float(op.get("hold", 0.05)) / max(self.a.speed, 0.01)
            return
        if self.state == "wait_stopped":
            if not hs or os.path.exists(os.path.join(hs, "stopped")) or now - float(open(os.path.join(hs, "done")).read()) > 120:
                unreal.unregister_slate_post_tick_callback(self.handle)
                self.state = "quit"
                if self.a.quit == "1":
                    unreal.SystemLibrary.quit_editor()


def main():
    a = args()
    with open(a.ops, encoding="utf-8") as f:
        ops = [json.loads(l) for l in f if l.strip()]
    p = Player(a, ops)
    if a.mode == "check":
        p.run_all()
    else:
        p.start()


main()

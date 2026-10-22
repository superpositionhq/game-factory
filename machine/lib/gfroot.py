"""Machine root for Python tools (ue-replay, task-check, ...); same rules as machine/lib/gf-root.ps1.

Order: env GF_ROOT, then "root" in the config file (env GF_CONFIG, else %USERPROFILE%/.game-factory/config.json),
then %USERPROFILE%/Work (the original machine's layout).

Use from a script in the repo:
    sys.path.insert(0, os.path.join(<game-factory>, "machine", "lib")); import gfroot; gfroot.root()
"""
import json
import os


def config_path():
    return os.environ.get("GF_CONFIG") or os.path.join(os.path.expanduser("~"), ".game-factory", "config.json")


def config():
    p = config_path()
    if os.path.isfile(p):
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


DEFAULT_ENGINE = "C:/Program Files/Epic Games/UE_5.7"


def engine_association(project):
    """The EngineAssociation ("5.3", "5.7", ...) of a .uproject or of the first .uproject in a folder; "" without one."""
    up = project
    if project and os.path.isdir(project):
        found = sorted(f for f in os.listdir(project) if f.lower().endswith(".uproject"))
        up = os.path.join(project, found[0]) if found else None
    if not up or not os.path.isfile(up):
        return ""
    with open(up, encoding="utf-8-sig") as f:
        return str(json.load(f).get("EngineAssociation") or "")


def engine(project=None):
    """The UE root for a project, as gf-root.ps1 Get-GFEngine (keep the two in step): the project's EngineAssociation
    picks the install through "engines" in the config, then the UE_<version> folder next to "engine", then the Epic
    Games Launcher's registry entry; without a project or a version-number association, "engine" (the one new games
    use). Forward slashes, no trailing slash."""
    import re
    c = config()
    default = (c.get("engine") or DEFAULT_ENGINE).replace("\\", "/").rstrip("/")
    assoc = engine_association(project) if project else ""
    if not re.fullmatch(r"\d+\.\d+", assoc):
        return default
    if (c.get("engines") or {}).get(assoc):
        return c["engines"][assoc].replace("\\", "/").rstrip("/")
    sibling = "%s/UE_%s" % (os.path.dirname(default), assoc)
    if os.path.isdir(os.path.join(sibling, "Engine", "Binaries", "Win64")):
        return sibling
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\EpicGames\\Unreal Engine\\" + assoc) as k:
            return winreg.QueryValueEx(k, "InstalledDirectory")[0].replace("\\", "/").rstrip("/")
    except OSError:
        return default


def org():
    """GitHub organisation (or user) owning game-factory and the game-<slug> repos: env GF_ORG, else "github_org" in
    the config file (bootstrap.ps1 -Org writes it), else ""."""
    return (os.environ.get("GF_ORG") or config().get("github_org") or "").strip()


def out():
    """Output root for packages and dataset zips: env GF_OUT, else "out" in the config file, else <root>/deliverables."""
    o = os.environ.get("GF_OUT") or config().get("out")
    return os.path.abspath(o) if o else os.path.join(root(), "deliverables")


def check_free(path, what="this job"):
    """Exit when the drive holding path has less free than the floor (env GF_MIN_FREE_GB, else "min_free_gb" in the
    config file, else 50 GB): a disk that fills mid-job corrupts the result. Returns the free GB."""
    import shutil
    import sys
    floor = float(os.environ.get("GF_MIN_FREE_GB") or config().get("min_free_gb") or 50)
    p = os.path.abspath(path)
    while not os.path.exists(p) and os.path.dirname(p) != p:
        p = os.path.dirname(p)
    free = shutil.disk_usage(p).free / 2 ** 30
    if free < floor:
        sys.exit("%s: only %.1f GB free on %s (floor %.0f GB; GF_MIN_FREE_GB / min_free_gb). Free space or move work_root "
                 "/ GF_OUT to another drive." % (what, free, os.path.splitdrive(p)[0] or p, floor))
    return free


def computed_slots():
    """The hardware formula of gf-root.ps1 Get-GFComputedSlots (keep the two in step):
    heavy_slots = clamp(1..8, min((RAM GB - 6) // 6, logical cores // 4, (commit limit GB - 6) // 8)),
    gpu_slots = clamp(1..4, min(VRAM GB of the largest NVIDIA GPU // 4, heavy_slots - 1)); 1 without nvidia-smi."""
    import ctypes
    import subprocess

    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    ms = MS()
    ms.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
    ram, commit = ms.ullTotalPhys / 2 ** 30, ms.ullTotalPageFile / 2 ** 30
    heavy = int(max(1, min(8, (ram - 6) // 6, (os.cpu_count() or 4) // 4, (commit - 6) // 8)))
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True).stdout
        vram = max([int(x) for x in out.split() if x.strip().isdigit()] or [0])
    except OSError:
        vram = 0
    gpu = int(max(1, min(4, vram // 1024 // 4, heavy - 1))) if vram else 1
    return {"heavy_slots": heavy, "gpu_slots": gpu}


def slot_plan():
    """heavy_slots / gpu_slots in effect: the config's keys, else computed_slots()."""
    c = config()
    comp = None
    out = {}
    for k in ("heavy_slots", "gpu_slots"):
        try:
            v = int(c.get(k) or 0)
        except (TypeError, ValueError):
            v = 0
        if v <= 0:
            comp = comp or computed_slots()
            v = comp[k]
        out[k] = v
    return out


def root():
    if os.environ.get("GF_ROOT"):
        return os.path.abspath(os.environ["GF_ROOT"])
    p = config_path()
    if os.path.isfile(p):
        with open(p, encoding="utf-8-sig") as f:
            r = json.load(f).get("root")
        if r:
            return os.path.abspath(r)
    return os.path.join(os.path.expanduser("~"), "Work")

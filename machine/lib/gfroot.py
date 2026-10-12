"""Machine root for Python tools (asset-scout, ue-replay, ...); same rules as machine/lib/gf-root.ps1.

Order: env GF_ROOT, then "root" in the config file (env GF_CONFIG, else %USERPROFILE%/.game-factory/config.json),
then %USERPROFILE%/Work (the original machine's layout).

Use from a script in the repo:
    sys.path.insert(0, os.path.join(<game-factory>, "machine", "lib")); import gfroot; gfroot.root()
bootstrap.ps1 also installs a copy next to the installed asset-scout tools (<root>/tools/asset-scout/gfroot.py).
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

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

"""Asset scout helper: log decisions, download free packs, write catalogue rows.

Usage (run from anywhere; never from inside asset-library pack folders):
  py -3.12 -I scout.py log ACTION URL RESULT REASON
  py -3.12 -I scout.py fetch SOURCE PACK URL [FILENAME]      download into asset-library/SOURCE/PACK/
  py -3.12 -I scout.py hash PATH                               sha256 + size
  py -3.12 -I scout.py catalog JSON                            append one catalogue row (JSON object)
  py -3.12 -I scout.py ph PACK RES ID [ID...]                  Poly Haven assets -> asset-library/polyhaven/PACK/ID/
  py -3.12 -I scout.py treehash DIR                            sha256 over a folder of loose files
"""
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

_here = os.path.dirname(os.path.abspath(__file__))
sys.path[0:0] = [_here, os.path.join(_here, "..", "lib")]   # installed copy: gfroot.py next to it; repo: machine/lib
import gfroot  # noqa: E402

# <root>\asset-library: catalogue, logs, status files. Env ASSET_LIB overrides it.
LIB = os.environ.get("ASSET_LIB") or os.path.join(gfroot.root(), "asset-library")
# Downloads go into the library too (user, 2026-10-11, overriding the earlier D: plan). Set ASSET_DL_ROOT to redirect.
DL = os.environ.get("ASSET_DL_ROOT", LIB)
LOG = os.path.join(LIB, "scout-log.jsonl")
CAT = os.path.join(LIB, "catalog.jsonl")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append(path, row):
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def log(action, url, result, reason, **extra):
    row = {"time": now(), "action": action, "url": url, "result": result, "reason": reason}
    row.update(extra)
    append(LOG, row)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(source, pack, url, filename=None):
    d = os.path.join(DL, source, pack)
    os.makedirs(d, exist_ok=True)
    if not filename:
        filename = os.path.basename(urllib.parse.urlparse(url).path) or "download.bin"
    dest = os.path.join(d, filename)
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(tmp, dest)
    size = os.path.getsize(dest)
    digest = sha256(dest)
    log("download", url, "ok", f"{source}/{pack}", path=dest, bytes=size, sha256=digest,
        seconds=round(time.time() - t0, 1))
    print(json.dumps({"path": dest, "bytes": size, "sha256": digest}))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest + ".part"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(tmp, dest)


# Texture maps UE needs (DirectX normal, packed AO/Rough/Metal, height for displacement/parallax).
PH_TEX_MAPS = ("Diffuse", "nor_dx", "arm", "Displacement")


def polyhaven(pack, asset_id, res="2k"):
    """Download one Poly Haven asset (HDRI as .hdr/.exr, texture maps, or model as FBX/glTF with textures)
    into asset-library/polyhaven/<pack>/<asset_id>/ and return a summary row."""
    info = get_json(f"https://api.polyhaven.com/info/{asset_id}")
    files = get_json(f"https://api.polyhaven.com/files/{asset_id}")
    out = os.path.join(DL, "polyhaven", pack, asset_id)
    if os.path.isdir(out) and os.listdir(out):
        raise SystemExit(f"{out} not empty")
    got = []
    kind = {0: "hdri", 1: "texture", 2: "model"}[info["type"]]
    if kind == "hdri":
        e = files["hdri"][res]["hdr"]
        got.append(e["url"])
    elif kind == "texture":
        for m in PH_TEX_MAPS:
            if m in files and res in files[m]:
                fmt = "png" if m == "Displacement" else "jpg"
                got.append(files[m][res].get(fmt, files[m][res].get("jpg"))["url"])
    else:
        fmt = "fbx" if "fbx" in files else "gltf"
        e = files[fmt][res][fmt]
        got.append(e["url"])
        for rel, inc in e.get("include", {}).items():
            got.append((inc["url"], rel))
    total = 0
    for g in got:
        url, rel = (g, os.path.basename(urllib.parse.urlparse(g).path)) if isinstance(g, str) else g
        dest = os.path.join(out, rel.replace("/", os.sep))
        download(url, dest)
        total += os.path.getsize(dest)
    # One manifest hash over the files (sorted) stands in for an archive hash.
    h = hashlib.sha256()
    for root, _, fs in sorted(os.walk(out)):
        for fn in sorted(fs):
            p = os.path.join(root, fn)
            h.update(os.path.relpath(p, out).replace(os.sep, "/").encode())
            h.update(sha256(p).encode())
    row = {"id": asset_id, "name": info["name"], "kind": kind, "res": res, "bytes": total,
           "sha256_tree": h.hexdigest(), "path": out, "authors": list(info.get("authors", {}).keys()),
           "date_published": info.get("date_published"), "url": f"https://polyhaven.com/a/{asset_id}"}
    log("download", row["url"], "ok", f"polyhaven/{pack}", path=out, bytes=total, sha256_tree=row["sha256_tree"])
    print(json.dumps(row, ensure_ascii=False))
    return row


def tree_hash(path):
    h = hashlib.sha256()
    n = 0
    for root, _, fs in sorted(os.walk(path)):
        for fn in sorted(fs):
            p = os.path.join(root, fn)
            h.update(os.path.relpath(p, path).replace(os.sep, "/").encode())
            h.update(sha256(p).encode())
            n += os.path.getsize(p)
    return h.hexdigest(), n


def main(argv):
    cmd = argv[0]
    if cmd == "ph":
        for a in argv[3:]:
            polyhaven(argv[1], a, argv[2])
        return
    if cmd == "treehash":
        d, n = tree_hash(argv[1])
        print(json.dumps({"path": argv[1], "bytes": n, "sha256_tree": d}))
        return
    if cmd == "log":
        log(*argv[1:5])
    elif cmd == "fetch":
        fetch(*argv[1:])
    elif cmd == "hash":
        p = argv[1]
        print(json.dumps({"path": p, "bytes": os.path.getsize(p), "sha256": sha256(p)}))
    elif cmd == "catalog":
        row = json.loads(argv[1])
        row.setdefault("catalogued", now())
        append(CAT, row)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])

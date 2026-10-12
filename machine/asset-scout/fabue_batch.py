"""Batch-rebuild Unreal-format Fab packs from saved manifests.

Usage: py -3.12 -I fabue_batch.py ITEMS.psv URLS.txt [URLS.txt ...]
  ITEMS.psv  lines idx|listing_uid|slug
  URLS.txt   lines key|manifest_url  (key = idx.fileidx); the manifest itself is saved next to the
             url list as manifests/<key>.manifest. When several keys exist for one idx, the highest
             fileidx is used unless CHOICE overrides it.
Each pack -> asset-library/fab-ue/<slug>/ (skipped if fab-ue/_status/<slug>.json says ok).
Packs over 15 GB are skipped and reported. After a rebuild, every .uasset/.umap header is scanned for
the engine that saved it; anything newer than 5.3 is flagged.
"""
import json
import os
import re
import struct
import subprocess
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fabue  # noqa: E402
import scout  # noqa: E402

FABUE = os.path.join(scout.DL, "fab-ue")  # new packs go to D:
STATUS = os.path.join(scout.LIB, "fab-ue", "_status")  # status files stay on C:
LIMIT = 15e9
CHOICE = {}  # idx -> fileidx overrides
# Deferred (optional / alternative / heavy; fetch on request): set via env FABUE_DEFER="1,2,3"
DEFER = {int(x) for x in os.environ.get("FABUE_DEFER", "").split(",") if x.strip()}


def saved_versions(root):
    counts = {}
    for r, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith((".uasset", ".umap")):
                continue
            with open(os.path.join(r, f), "rb") as fh:
                head = fh.read(4096)
            m = re.search(rb"\+\+UE[45]\+Release-([0-9.]+)", head)
            key = m.group(1).decode() if m else "?"
            counts[key] = counts.get(key, 0) + 1
    return counts


def newest(counts):
    vs = [tuple(int(x) for x in k.split(".")[:2]) for k in counts if k != "?"]
    return max(vs) if vs else None


def run(job):
    idx, uid, slug, man, url = job
    st_path = os.path.join(STATUS, slug + ".json")
    if os.path.exists(st_path) and json.load(open(st_path)).get("result") == "ok":
        return f"skip {slug}"
    m = fabue.load_manifest(man)
    size = fabue.total_size(m)
    out = os.path.join(FABUE, slug)
    status = {"idx": idx, "listing": f"https://www.fab.com/listings/{uid}", "slug": slug, "app": m["app"],
              "build": m["build"], "files": len(m["files"]), "bytes": size, "path": out}
    if idx in DEFER:
        status["result"] = "deferred"
    elif size > LIMIT:
        status["result"] = "skipped: over 15 GB"
    else:
        p = urllib.parse.urlparse(url)
        base = "https://egdownload.fastly-edge.com" + p.path.rsplit("/", 1)[0]
        t0 = time.time()
        r = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fabue.py"),
                            man, base, out], capture_output=True, text=True)
        status["seconds"] = round(time.time() - t0, 1)
        if r.returncode != 0:
            status["result"] = "failed"
            status["error"] = r.stderr[-800:]
        else:
            res = json.loads(r.stdout.strip().splitlines()[-1])
            status["hash_mismatches"] = res["bad"]
            vers = saved_versions(out)
            status["saved_by"] = vers
            nv = newest(vers)
            status["ue53_ok"] = nv is None or nv <= (5, 3)
            status["result"] = "ok" if res["bad"] == 0 else "hash-mismatch"
    os.makedirs(STATUS, exist_ok=True)
    json.dump(status, open(st_path, "w"), indent=1)
    scout.log("download.fab-ue", status["listing"], status["result"],
              f"fab-ue/{slug} ({m['build']}, {round(size / 1e9, 2)} GB, ue53_ok={status.get('ue53_ok')})",
              path=out, bytes=size)
    return f"{status['result']} {slug} {round(size / 1e9, 2)}GB ue53_ok={status.get('ue53_ok')} {status.get('saved_by', '')}"


def main():
    items = {}
    for line in open(sys.argv[1], encoding="utf-8"):
        if line.strip():
            i, uid, slug = line.strip().split("|")
            items[int(i)] = (uid, slug)
    chosen = {}
    for lst in sys.argv[2:]:
        mdir = os.path.join(os.path.dirname(lst), "manifests")
        for line in open(lst, encoding="utf-8"):
            if "|" not in line:
                continue
            key, url = line.strip().split("|", 1)
            i, k = (int(x) for x in key.split("."))
            want = CHOICE.get(i)
            if want is not None and k != want:
                continue
            if i not in chosen or (want is None and k > chosen[i][0]):
                chosen[i] = (k, os.path.join(mdir, key + ".manifest"), url)
    chosen = {i: v for i, v in chosen.items() if i in items}  # only the items listed in ITEMS.psv
    first = [int(x) for x in os.environ.get("FABUE_FIRST", "").split(",") if x.strip()]
    order = sorted(chosen, key=lambda i: (first.index(i) if i in first else len(first), i))
    jobs = [(i, items[i][0], items[i][1], chosen[i][1], chosen[i][2]) for i in order]
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(run, jobs):
            print(r, flush=True)


if __name__ == "__main__":
    main()

"""Fetch a list of direct CC0/OFL downloads: lines 'source<TAB>pack<TAB>url[<TAB>filename]'."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scout  # noqa: E402

for line in open(sys.argv[1], encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 3:
        continue
    src, pack, url = p[:3]
    fn = p[3] if len(p) > 3 else None
    if src == "ambientcg":
        fn = url.split("file=")[1]
    try:
        scout.fetch(src, pack, url, fn)
    except Exception as e:  # noqa: BLE001
        print("FAIL", url, e)
        scout.log("download", url, "failed", str(e))

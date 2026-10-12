"""Download Fab files from short-lived signed URLs (TSV: listing_uid, fmt, filename, size, url).
Each pack goes to asset-library/fab/<slug>/ (new folder). The signed query string is never logged.
Usage: py -3.12 -I fabdl.py LIST.tsv [workers]"""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scout  # noqa: E402

LIB = scout.LIB


def slug(name):
    s = re.sub(r"\.(zip|glb|fbx)$", "", name, flags=re.I)
    s = re.sub(r"_(high|mid|low|raw|[248]k)$", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def one(row):
    uid, fmt, name, size, url = row[:5]
    pack = row[5] if len(row) > 5 and row[5] else slug(name)  # optional 6th column: pack folder
    d = os.path.join(scout.DL, "fab", pack)
    dest = os.path.join(d, name)
    if os.path.exists(dest) and os.path.getsize(dest) == int(size):
        return f"skip {name}"
    os.makedirs(d, exist_ok=True)
    try:
        scout.download(url, dest)
    except Exception as e:  # noqa: BLE001
        scout.log("download", f"https://www.fab.com/listings/{uid}", "failed", f"fab/{pack}: {e}", file=name)
        return f"FAIL {name}: {e}"
    got = os.path.getsize(dest)
    digest = scout.sha256(dest)
    ok = got == int(size)
    scout.log("download", f"https://www.fab.com/listings/{uid}", "ok" if ok else "size-mismatch",
              f"fab/{pack} ({fmt})", path=dest, bytes=got, expected=int(size), sha256=digest)
    return f"{'ok' if ok else 'MISMATCH'} {name} {got} {digest[:12]}"


def main():
    rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    with ThreadPoolExecutor(int(sys.argv[2]) if len(sys.argv) > 2 else 6) as ex:
        for r in ex.map(one, rows):
            print(r, flush=True)


if __name__ == "__main__":
    main()

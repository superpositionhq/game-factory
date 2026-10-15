"""Export every Git LFS object of a game's whole history for a delivery (dataset layout v1.2 History/lfs/objects).

  python export-lfs-history.py <repo> <out lfs dir> [--unpatchable-use-head]

Every LFS object any commit references (all refs) is scanned with the same terms and safe-context rules as
scrub-lfs-history.py / scrub-import-paths.py (the user name in path segments and author FStrings, ASCII and UTF-16LE).
Clean objects are hard-linked (copied when linking fails) into <out>/<aa>/<bb>/<oid>; objects with matches are patched
byte for byte (same length) into a new object under its new oid. The repo and its LFS store are never changed.

Prints one JSON object: {"map": {old_oid: [new_oid, size]}, "objects": n, "bytes": n, "patched": n,
"unpatchable": [{"oid", "path"}], "missing": [{"oid", "path"}]}. The packager rewrites the pointers of patched objects
in the delivered history (package-game.ps1, GitHistory). Exit 2 when an object is missing locally or cannot be patched
(unless --unpatchable-use-head finds HEAD's clean version of the same path, which then stands in for it).
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("scrub_lfs_history", os.path.join(HERE, "scrub-lfs-history.py"))
slh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(slh)


def place(src, out, oid):
    dst = os.path.join(out, oid[:2], oid[2:4], oid)
    if os.path.exists(dst):
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("out")
    ap.add_argument("--unpatchable-use-head", action="store_true")
    a = ap.parse_args()
    repo, out = os.path.abspath(a.repo), os.path.abspath(a.out)
    pats = slh.sip.byte_patterns()
    pointers = slh.referenced_pointers(repo)          # {pointer blob sha: (oid, size, {paths})}
    by_oid = {}
    for _sha, (oid, size, paths) in pointers.items():
        e = by_oid.setdefault(oid, [size, set()])
        e[1] |= paths
    res = {"map": {}, "objects": 0, "bytes": 0, "patched": 0, "unpatchable": [], "missing": []}
    head = {}
    if a.unpatchable_use_head:
        for line in slh.git(repo, "ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines():
            meta, path = line.split("\t", 1)
            head[path] = meta.split()[2]
    tmp = tempfile.mkdtemp(prefix="export-lfs-")
    try:
        for oid, (size, paths) in sorted(by_oid.items()):
            src = slh.lfs_path(repo, oid)
            path = sorted(paths)[0]
            if not os.path.exists(src):
                res["missing"].append({"oid": oid, "path": path})
                continue
            counts, unpatchable, _rw = slh.sip._stream(src, pats)
            if not counts:
                place(src, out, oid)
                res["objects"] += 1
                res["bytes"] += os.path.getsize(src)
                continue
            patched = os.path.join(tmp, oid)
            _c, unpatchable, rewritten = slh.sip._stream(src, pats, patch_to=patched)
            if unpatchable or not rewritten:
                res["unpatchable"].append({"oid": oid, "path": path})
                continue
            new = slh.sha256_file(patched)
            place(patched, out, new)
            res["map"][oid] = [new, os.path.getsize(patched)]
            res["objects"] += 1
            res["bytes"] += os.path.getsize(patched)
            res["patched"] += 1
        if res["unpatchable"] and a.unpatchable_use_head:
            # HEAD's clean version of the same path stands in (its object is exported like every other)
            left = []
            for u in res["unpatchable"]:
                hp = head.get(u["path"])
                rep = pointers.get(hp) if hp else None
                if rep and rep[0] not in res["map"] and rep[0] not in [x["oid"] for x in res["unpatchable"]]:
                    res["map"][u["oid"]] = [rep[0], rep[1]]
                else:
                    left.append(u)
            res["unpatchable"] = left
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(res))
    return 2 if res["missing"] or res["unpatchable"] else 0


if __name__ == "__main__":
    sys.exit(main())

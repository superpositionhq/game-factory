"""Regenerate asset-library/catalog.jsonl from packs_meta.tsv (one row per pack).

packs_meta.tsv columns (tab separated, '#' comments allowed):
  path (relative to asset-library) | games (comma list) | source | url | licence | licence_url |
  version | engine | purpose | quality_note
Size and sha256 are computed from disk: sha256 of the archive when the pack folder holds a single file,
otherwise a tree hash (sha256 over sorted relative-path + file-sha256 pairs, marked sha256_kind=tree).
Usage: py -3.12 -I build_catalog.py
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scout  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = ["path", "games", "source", "url", "licence", "licence_url", "version", "engine", "purpose", "quality_note"]


def load_purchases():
    """purchases.tsv: Fab listing uid -> (price paid, games comma list)."""
    out = {}
    for line in open(os.path.join(HERE, "purchases.tsv"), encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            uid, price, games = (line.rstrip("\r\n").split("\t") + ["", ""])[:3]
            out[uid] = (price, games)
    return out


PURCHASED = load_purchases()


def fab_ue_rows():
    """One catalogue row per Unreal-format Fab pack rebuilt by fabue_batch.py (fab-ue/_status/*.json)."""
    lib = {}
    psv = os.path.join(scout.LIB, "fab-library.psv")
    for line in open(psv, encoding="utf-8"):
        p = line.rstrip("\n").split("|")
        if len(p) >= 4:
            lib[p[0]] = (p[1], p[2], p[3])
    rows = []
    for f in sorted(glob.glob(os.path.join(scout.LIB, "fab-ue", "_status", "*.json"))):
        s = json.load(open(f))
        if s.get("result") != "ok":
            continue
        uid = s["listing"].rsplit("/", 1)[1]
        if uid in PURCHASED:
            lic = f"Fab Standard License (Personal tier, purchased ${PURCHASED[uid][0]})"
            games = PURCHASED[uid][1]
        else:
            name, lic, games = lib.get(uid, ("", "Fab Standard License", ""))
            lic = "CC BY 4.0" if lic == "CC-BY" else lic
        rows.append({
            "games": [g for g in games.split(",") if g],
            "pack": s["slug"], "source": "Fab (Unreal format, rebuilt from Epic CDN manifest)", "url": s["listing"],
            "licence": lic, "licence_url": "https://creativecommons.org/licenses/by/4.0/" if lic.startswith("CC BY")
            else "https://www.fab.com/eula",
            "version": s.get("build", ""), "engine": "UE asset pack; saved by " + ", ".join(sorted(s.get("saved_by", {}))),
            "bytes": s.get("bytes", 0), "sha256": s.get("manifest_sha256", ""),
            "sha256_kind": "manifest (each file SHA-1 verified against it; manifest kept in fab-ue/_status)",
            "files": s.get("files", 0), "local_path": s["path"],
            "purpose": "see game-factory/docs/asset-library.md",
            "quality_note": s.get("ue53_notes", "UE 5.3 compatible (all assets saved by <= 5.3)" if s.get("ue53_ok") else ""),
            "catalogued": scout.now(),
        })
    return rows


def main():
    rows = []
    for line in open(os.path.join(HERE, "packs_meta.tsv"), encoding="utf-8"):
        if not line.strip() or line.startswith("#"):
            continue
        p = line.rstrip("\n").split("\t")
        p += [""] * (len(COLS) - len(p))
        m = dict(zip(COLS, p))
        full = os.path.join(scout.LIB, m["path"].replace("/", os.sep))
        if not os.path.exists(full):  # newer downloads live on D:
            full = os.path.join(scout.DL, m["path"].replace("/", os.sep))
        if not os.path.exists(full):
            print("MISSING", full)
            continue
        files = [os.path.join(r, f) for r, _, fs in os.walk(full) for f in fs] if os.path.isdir(full) else [full]
        files = [f for f in files if not f.endswith(".part")]
        if len(files) == 1:
            sha, kind, size = scout.sha256(files[0]), "file", os.path.getsize(files[0])
        else:
            sha, size = scout.tree_hash(full)
            kind = "tree"
        rows.append({
            "games": [g.strip() for g in m["games"].split(",") if g.strip()],
            "pack": os.path.basename(m["path"].rstrip("/")),
            "source": m["source"], "url": m["url"],
            "licence": m["licence"], "licence_url": m["licence_url"],
            "version": m["version"], "engine": m["engine"],
            "bytes": size, "sha256": sha, "sha256_kind": kind, "files": len(files),
            "local_path": full, "purpose": m["purpose"], "quality_note": m["quality_note"],
            "catalogued": scout.now(),
        })
    rows += fab_ue_rows()
    with open(scout.CAT, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "rows,", round(sum(r["bytes"] for r in rows) / 1e9, 2), "GB")


if __name__ == "__main__":
    main()

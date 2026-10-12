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


PURCHASED = {  # listing uid -> price paid (Personal tier), from logcart.py
    l.split("|")[0]: l.split("|")[1] for l in """482af403-8e34-4425-9d6e-9627d2e121a9|9.99
f083b1c2-05df-4de8-b01c-6ee7dce60228|24.99
41a8c493-85ee-4e72-a6d4-5982971ce073|24.99
6c9ecebd-a408-4c23-94aa-982e5f915dca|14.99
0ca8912a-1d9c-49f7-98ac-36fbcb6e0b03|24.99
dc5210c9-9659-47b9-9c23-bf8cc31e5d19|49.99
451900df-be30-426a-81bf-fc610e9d28bb|39.99
7b404175-8036-4cdc-bb7f-fd3629b94557|34.99
278716ba-8cc9-4b63-a09a-db272db34abc|29.99
1158af28-2664-4849-9b94-4e4525e17480|13.99
b2760e03-30d9-42fb-be3f-857c21e3acc4|99.99
0a0c8009-ad66-440f-b342-6bda3d90b4da|49.99
0461bb09-487e-42f1-bcb5-c89a63ec16e9|39.99
0c920ed7-64f9-4010-a099-5374b4f79bfb|79.99
5de627fd-5c59-431d-b8e9-3009f8fc8605|29.99
5e1941eb-82a5-4249-8f02-de9c2c2a6f66|49.99
5f59fc84-396f-4189-9889-49a9836246e9|13.99
858e8829-b612-436c-90f0-9bb2f082571e|19.99
c9051974-5025-48f0-99e7-6edb899805f0|12.99
2b3ef29d-0ceb-4616-a883-27c3f1db04b2|14.99
12e74c0f-afb2-499a-a624-0cb66136203f|69.99""".splitlines()}
PURCHASED_GAMES = {"482af403": "liaozhai-night", "f083b1c2": "liaozhai-night", "41a8c493": "liaozhai-night",
                   "6c9ecebd": "tower-defense", "0ca8912a": "tower-defense,siege-catapult", "dc5210c9": "tower-defense",
                   "451900df": "siege-catapult", "7b404175": "siege-catapult", "278716ba": "rally-racer",
                   "1158af28": "rally-racer", "b2760e03": "horror-escape", "0a0c8009": "horror-escape",
                   "0461bb09": "stealth", "0c920ed7": "stealth", "5de627fd": "stealth", "5e1941eb": "island-survival",
                   "5f59fc84": "island-survival", "858e8829": "island-survival", "c9051974": "island-survival",
                   "2b3ef29d": "island-survival", "12e74c0f": "island-survival"}


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
            lic = f"Fab Standard License (Personal tier, purchased ${PURCHASED[uid]})"
            games = PURCHASED_GAMES.get(uid[:8], "")
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

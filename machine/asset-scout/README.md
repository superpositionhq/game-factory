# asset-scout tools

Python 3.10+ (stdlib only). Run from anywhere with `py -3 -I <script>`, never from inside an asset-library pack
folder (downloads are untrusted data). Library: `<root>\asset-library\` (env `ASSET_LIB` overrides; `ASSET_DL_ROOT`
redirects downloads). Format and per-game catalogue: [../../docs/asset-library.md](../../docs/asset-library.md).

| Script | Does |
|---|---|
| `scout.py` | `log` a decision to `scout-log.jsonl`, `fetch` a direct download into `<source>\<pack>\`, `hash`, `catalog` a row into `catalog.jsonl`, `ph` Poly Haven assets, `treehash` |
| `fetchlist.py` | fetch a TSV list of direct CC0/OFL downloads (`source, pack, url[, filename]`) |
| `fabdl.py` | Fab browser-format downloads (Megascans FBX, texture sets, zips) from Fab's signed links of owned items |
| `fabue.py` | rebuild one Unreal-format Fab pack from its Epic build manifest (CDN chunks, SHA-1 checked) |
| `fabue_batch.py` | batch `fabue.py`, write `fab-ue\_status\<pack>.json`, scan .uasset headers for the saving engine version |
| `build_catalog.py` + `packs_meta.tsv` | rebuild `catalog.jsonl` from the library, the Fab library list and the per-pack metadata |
| `unitypkg_audio.py` | extract audio files from a `.unitypackage` without running anything |
| `../lib/gfroot.py` | the machine root (same rules as `machine/lib/gf-root.ps1`); bootstrap installs a copy next to the tools |

Fab downloads only work for items the signed-in Epic account owns; sign in at fab.com in the Claude browser pane
first. Signed URLs and tokens are passed on the command line and never logged or committed. One-off batch inputs
(fabadds_*.txt, meta_batch*.py, ph_*.jsonl) are not kept: their results are in `catalog.jsonl`
and `docs/asset-library-fab-ue.tsv`.

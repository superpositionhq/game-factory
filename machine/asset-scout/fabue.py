"""Rebuild an Unreal-format Fab pack from its Epic build manifest (JSON) + CDN chunks, like the Launcher does.

Usage: py -3.12 -I fabue.py MANIFEST_FILE BASE_URL OUT_DIR [TOKEN_QUERY]
  MANIFEST_FILE  manifest saved from Fab's download-info "downloadUrl"
  BASE_URL       one of download-info "distributionPointBaseUrls" (…/CloudDir)
  OUT_DIR        new empty folder; files are written with their manifest paths (Content/…)
Every file is checked against the manifest's SHA-1 (FileHash). Untrusted data: nothing is executed.
"""
import hashlib
import json
import os
import struct
import sys
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

UA = "EpicGamesLauncher/16.0.0-0+++Portal+Release-Live Windows/10.0"


def blob_int(s):
    """Epic JSON 'blob': decimal triplets, one per byte, little-endian."""
    b = bytes(int(s[i:i + 3]) for i in range(0, len(s), 3))
    return int.from_bytes(b, "little")


def blob_bytes(s):
    return bytes(int(s[i:i + 3]) for i in range(0, len(s), 3))


def chunk_dir(version):
    if version >= 15:
        return "ChunksV4"
    if version >= 6:
        return "ChunksV3"
    if version >= 3:
        return "ChunksV2"
    return "Chunks"


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def decode_chunk(data):
    magic, hver, hsize, csize = struct.unpack_from("<IIII", data, 0)
    if magic != 0xB1FE3AA2:
        raise ValueError("bad chunk magic")
    stored_as = data[16 + 16 + 8]  # after guid(16) + rolling hash(8)
    body = data[hsize:hsize + csize]
    if stored_as & 2:
        raise ValueError("encrypted chunk")
    return zlib.decompress(body) if stored_as & 1 else body


class _R:
    def __init__(self, b):
        self.b, self.p = b, 0

    def u(self, fmt):
        v = struct.unpack_from("<" + fmt, self.b, self.p)
        self.p += struct.calcsize("<" + fmt)
        return v if len(v) > 1 else v[0]

    def raw(self, n):
        v = self.b[self.p:self.p + n]
        self.p += n
        return v

    def fstr(self):
        n = self.u("i")
        if n == 0:
            return ""
        if n < 0:
            return self.raw(-n * 2).decode("utf-16-le").rstrip("\x00")
        return self.raw(n).decode("utf-8", "replace").rstrip("\x00")


def load_binary(data):
    """Epic binary manifest (magic 0x44BEC00C) -> normalized dict."""
    magic, hsize, _usize, _csize = struct.unpack_from("<IIII", data, 0)
    if magic != 0x44BEC00C:
        raise ValueError("not a manifest")
    stored_as = data[36]
    body = data[hsize:]
    if stored_as & 1:
        body = zlib.decompress(body)
    r = _R(body)
    start = r.p
    meta_size = r.u("I")
    data_version = r.u("B")
    feature_level = r.u("I")
    r.u("B")
    r.u("I")
    app = r.fstr()
    build = r.fstr()
    r.p = start + meta_size
    # chunk data list
    start = r.p
    size, _v, count = r.u("I"), r.u("B"), r.u("I")
    guids = ["".join(f"{g:08X}" for g in r.u("IIII")) for _ in range(count)]
    hashes = [r.u("Q") for _ in range(count)]
    r.p += 20 * count
    groups = [r.u("B") for _ in range(count)]
    r.p = start + size
    chunks = {g: (h, grp) for g, h, grp in zip(guids, hashes, groups)}
    # file manifest list
    start = r.p
    size, _v, count = r.u("I"), r.u("B"), r.u("I")
    names = [r.fstr() for _ in range(count)]
    for _ in range(count):
        r.fstr()
    shas = [r.raw(20) for _ in range(count)]
    r.p += count
    for _ in range(count):
        for _ in range(r.u("I")):
            r.fstr()
    files = []
    for i in range(count):
        parts = []
        for _ in range(r.u("I")):
            ps = r.p
            psize = r.u("I")
            g = "".join(f"{x:08X}" for x in r.u("IIII"))
            off, sz = r.u("I"), r.u("I")
            parts.append((g, off, sz))
            r.p = ps + psize
        files.append({"name": names[i], "sha1": shas[i], "parts": parts})
    return {"version": feature_level, "app": app, "build": build, "files": files, "chunks": chunks,
            "data_version": data_version}


def load_manifest(path):
    data = open(path, "rb").read()
    if data[:1] != b"{":
        return load_binary(data)
    m = json.loads(data)
    files = [{"name": f["Filename"], "sha1": blob_bytes(f["FileHash"]),
              "parts": [(p["Guid"], blob_int(p["Offset"]), blob_int(p["Size"])) for p in f["FileChunkParts"]]}
             for f in m["FileManifestList"]]
    chunks = {g: (blob_int(v), blob_int(m["DataGroupList"][g])) for g, v in m["ChunkHashList"].items()}
    return {"version": blob_int(m["ManifestFileVersion"]), "app": m["AppNameString"],
            "build": m["BuildVersionString"], "files": files, "chunks": chunks}


def total_size(m):
    return sum(s for f in m["files"] for _, _, s in f["parts"])


def main():
    man_path, base, out = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
    tokq = sys.argv[4] if len(sys.argv) > 4 else ""
    m = load_manifest(man_path)
    cdir = chunk_dir(m["version"])
    hashes = {g: v[0] for g, v in m["chunks"].items()}
    groups = {g: v[1] for g, v in m["chunks"].items()}
    files = m["files"]
    needed = sorted({p[0] for f in files for p in f["parts"]})
    os.makedirs(out, exist_ok=True)
    cache_dir = os.path.join(out, "_chunks.part")
    os.makedirs(cache_dir, exist_ok=True)

    def fetch_chunk(g):
        dest = os.path.join(cache_dir, g)
        if os.path.exists(dest):
            return 0
        url = f"{base}/{cdir}/{groups[g]:02d}/{hashes[g]:016X}_{g}.chunk" + (("?" + tokq) if tokq else "")
        raw = decode_chunk(get(url))
        with open(dest + ".tmp", "wb") as fh:
            fh.write(raw)
        os.replace(dest + ".tmp", dest)
        return len(raw)

    t0 = time.time()
    with ThreadPoolExecutor(16) as ex:
        total = sum(ex.map(fetch_chunk, needed))
    bad = 0
    for f in files:
        rel = f["name"].replace("\\", "/")
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError("unsafe path in manifest: " + rel)
        dest = os.path.join(out, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        h = hashlib.sha1()
        with open(dest, "wb") as fh:
            for g, off, sz in f["parts"]:
                with open(os.path.join(cache_dir, g), "rb") as ch:
                    ch.seek(off)
                    piece = ch.read(sz)
                fh.write(piece)
                h.update(piece)
        if h.digest() != f["sha1"]:
            bad += 1
            print("HASH MISMATCH", rel)
    for g in needed:
        os.remove(os.path.join(cache_dir, g))
    os.rmdir(cache_dir)
    print(json.dumps({"app": m["app"], "build": m["build"], "files": len(files),
                      "chunks": len(needed), "chunk_bytes": total, "bad": bad, "seconds": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()

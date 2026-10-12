"""Extract audio files from a .unitypackage (gzip tar of <guid>/{asset,pathname}) without running anything.
Usage: py -3.12 -I unitypkg_audio.py PACKAGE OUT_DIR"""
import os
import sys
import tarfile

AUDIO = (".wav", ".ogg", ".mp3", ".flac", ".aif", ".aiff")


def main(pkg, out):
    names, blobs = {}, {}
    with tarfile.open(pkg, "r:gz") as tf:
        for m in tf:
            if not m.isfile():
                continue
            guid, _, leaf = m.name.partition("/")
            if leaf == "pathname":
                names[guid] = tf.extractfile(m).read().decode("utf-8").splitlines()[0].strip()
            elif leaf == "asset":
                blobs[guid] = tf.extractfile(m).read()
    n = 0
    for guid, path in names.items():
        if not path.lower().endswith(AUDIO) or guid not in blobs:
            continue
        rel = path.replace("\\", "/")
        if rel.startswith("/") or ".." in rel.split("/"):
            continue
        dest = os.path.join(out, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(blobs[guid])
        n += 1
    print(n, "audio files ->", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

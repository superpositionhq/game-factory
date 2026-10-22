"""Scrub the Windows user name out of Git LFS objects in a game's history (assets committed before scrub-import-paths).

  python scrub-lfs-history.py <game> [--apply] [--quiet-minutes N]

scrub-history.ps1 rewrites text blobs, messages and identities and never touches LFS content. Here every LFS object
any commit references is scanned for the user name (the same terms and safe-context rules as scrub-import-paths.py:
ASCII and UTF-16LE, in path segments and author FStrings); each object with matches is rewritten byte for byte (same
length, scrub-import-paths' patcher) into a NEW object in the repo's LFS store, and every commit that pointed at the
old object is rewritten to point at the new one (git filter-branch --index-filter over all refs, tags kept).

Dry run by default: lists the objects and what the patch would do. --apply:
  - refuses with uncommitted changes, while the game's recording was written within --quiet-minutes (default 10),
    or while an editor has the project open;
  - archives a verified git bundle of all refs to <root>/.recording/<game>/original-history/ first (old LFS objects
    stay in the store untouched, so the bundle plus the store restore everything);
  - verifies afterwards: no referenced LFS object still contains the name, HEAD's tree unchanged unless HEAD itself
    referenced a patched object, `git lfs fsck` clean; removes filter-branch's refs/original backups (the bundle is
    the backup). Never pushes, never runs gc.
Commit shas change for every commit from the first one that referenced a patched object; workflow rows and the
recording that name old shas are not rewritten.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "machine", "lib"))
import gfroot  # noqa: E402

spec = importlib.util.spec_from_file_location("scrub_import_paths", os.path.join(HERE, "scrub-import-paths.py"))
sip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sip)


def git(repo, *args, inp=None, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args), input=inp, capture_output=True)
    if check and r.returncode:
        raise SystemExit("git %s failed: %s" % (" ".join(args[:3]), r.stderr.decode("utf-8", "replace")[-1500:]))
    return r.stdout


def lfs_path(repo, oid):
    return os.path.join(repo, ".git", "lfs", "objects", oid[:2], oid[2:4], oid)


def live_refs(repo, exclude_tasks=False):
    """Every ref except filter-branch's backups (refs/original/*); with exclude_tasks also without the game's tasks
    branch (refs/heads/tasks, refs/remotes/<remote>/tasks: package-game.ps1's --exclude patterns), which never enters
    a delivered history."""
    def is_tasks(r):
        return r == "refs/heads/tasks" or (r.startswith("refs/remotes/") and r.endswith("/tasks"))
    return [r for r in git(repo, "for-each-ref", "--format=%(refname)").decode().split()
            if not r.startswith("refs/original/") and not (exclude_tasks and is_tasks(r))]


def referenced_pointers(repo, exclude_tasks=False):
    """{pointer blob sha: (oid, size, {paths})} for every LFS pointer blob reachable from any ref (refs/original excluded;
    the tasks branch too with exclude_tasks)."""
    objs = git(repo, "rev-list", "--objects", *live_refs(repo, exclude_tasks)).decode("utf-8", "replace")
    chk = git(repo, "cat-file", "--batch-check=%(objecttype) %(objectname) %(objectsize) %(rest)", inp=objs.encode()).decode("utf-8", "replace")
    cand = []
    for line in chk.splitlines():
        p = line.split(" ", 3)
        if len(p) >= 3 and p[0] == "blob" and int(p[2]) < 300:
            cand.append((p[1], p[3] if len(p) > 3 else ""))
    out = git(repo, "cat-file", "--batch", inp=("\n".join(s for s, _ in cand) + "\n").encode())
    pos, res = 0, {}
    for sha, path in cand:
        nl = out.index(b"\n", pos)
        size = int(out[pos:nl].split()[2])
        body = out[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
        lines = body.decode("ascii", "replace").splitlines()
        if lines and lines[0].startswith("version https://git-lfs.github.com/spec/v1"):
            oid = next((l.split("sha256:", 1)[1].strip() for l in lines if l.startswith("oid sha256:")), None)
            sz = next((int(l.split()[1]) for l in lines if l.startswith("size ")), None)
            if oid:
                e = res.setdefault(sha, (oid, sz, set()))
                e[2].add(path)
    return res


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def scan(repo, pointers, pats):
    """[(pointer sha, oid, paths, counts)] for objects with matches; raises if an object is missing locally."""
    hits = []
    for sha, (oid, _sz, paths) in pointers.items():
        fp = lfs_path(repo, oid)
        if not os.path.exists(fp):
            raise SystemExit("LFS object %s (%s) is not in the local store: fetch it first" % (oid, sorted(paths)[0]))
        counts, _unpatchable, _rw = sip._stream(fp, pats)
        if counts:
            hits.append((sha, oid, sorted(paths), counts))
    return hits


def recording_quiet(root, game, minutes):
    p = os.path.join(root, ".recording", game, "actions.jsonl")
    return not os.path.exists(p) or time.time() - os.path.getmtime(p) > minutes * 60


def editor_open(repo):
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name like 'UnrealEditor%'\" | ForEach-Object { $_.CommandLine }"],
                       capture_output=True, text=True)
    return repo.replace("/", "\\").lower() in r.stdout.replace("/", "\\").lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quiet-minutes", type=int, default=10)
    # an object whose match is not a path or author field (e.g. compressed pixels that happen to spell the name;
    # giant-fall re-encoded such a normal map later): commits that held it get HEAD's clean version of the same path
    ap.add_argument("--unpatchable-use-head", action="store_true")
    ap.add_argument("--repo", help="testing only: this repo instead of <root>/games/<game>")
    a = ap.parse_args()
    root = gfroot.root()
    repo = os.path.abspath(a.repo or os.path.join(root, "games", a.game))
    pats = sip.byte_patterns()
    print("== scrub-lfs-history %s (%s) repo %s; terms: %s" % (a.game, "APPLY" if a.apply else "dry run", repo,
                                                               ", ".join(sorted(set(p[0] for p in pats)))))
    pointers = referenced_pointers(repo)
    hits = scan(repo, pointers, pats)
    print("%d LFS objects referenced in history, %d contain a term" % (len(pointers), len(hits)))
    tmp = tempfile.mkdtemp(prefix="scrub-lfs-")
    plan = []
    for sha, oid, paths, counts in hits:
        out = os.path.join(tmp, oid)
        _c, unpatchable, rewritten = sip._stream(lfs_path(repo, oid), pats, patch_to=out)
        print("  %s %s  %s  rewritten %d%s" % (oid[:12], paths[0], json.dumps(counts), rewritten,
                                             ("  UNPATCHABLE %d (not a path or author field)" % unpatchable) if unpatchable else ""))
        plan.append((sha, oid, paths, out, unpatchable, rewritten))
    # unpatchable objects: HEAD's clean version of the same path, when asked for and available
    head_ptr = {}
    for line in git(repo, "ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines():
        meta, path = line.split("\t", 1)
        head_ptr[path] = meta.split()[2]
    substitute = {}
    for sha, oid, paths, out, unpatchable, rewritten in plan:
        if not (unpatchable or not rewritten) or not a.unpatchable_use_head:
            continue
        hs = next((head_ptr[p] for p in paths if p in head_ptr and head_ptr[p] in pointers), None)
        clean = hs and not any(h[0] == hs for h in hits)
        if clean:
            substitute[sha] = hs
            print("  %s %s: HEAD's version (pointer %s) replaces it in every commit" % (oid[:12], paths[0], hs[:10]))
    bad = [p for p in plan if (p[4] or not p[5]) and p[0] not in substitute]
    if bad:
        raise SystemExit("%d object(s) have matches outside a safe context: nothing changed; fix them by hand, or pass "
                         "--unpatchable-use-head when HEAD has a clean version of the same path" % len(bad))
    plan = [p for p in plan if p[0] not in substitute]
    if not a.apply or not (plan or substitute):
        print("dry run: nothing changed" if not a.apply else "nothing to do")
        shutil.rmtree(tmp, ignore_errors=True)
        return 0

    # ---- safety ----
    if git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        raise SystemExit("uncommitted changes in %s: commit or stash first" % repo)
    if not a.repo and not recording_quiet(root, a.game, a.quiet_minutes):
        raise SystemExit("the game's recording was written in the last %d min: is its session active?" % a.quiet_minutes)
    if editor_open(repo):
        raise SystemExit("an editor has %s open" % repo)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    arch = os.path.join(root, ".recording", a.game, "original-history") if not a.repo else os.path.join(tmp, "archive")
    os.makedirs(arch, exist_ok=True)
    bundle = os.path.join(arch, "%s-%s-before-lfs-scrub.bundle" % (a.game, stamp))
    git(repo, "bundle", "create", bundle, "--all")
    git(repo, "bundle", "verify", bundle)
    print("archived all refs: %s" % bundle)
    head_tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
    head_blobs = set(l.split()[2] for l in git(repo, "ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines() if l.strip())
    head_had = bool(head_blobs & set(p[0] for p in plan))

    # ---- new objects and pointer blobs ----
    mapping = {}
    for sha, oid, paths, out, _u, _r in plan:
        new_oid = sha256_file(out)
        size = os.path.getsize(out)
        dst = lfs_path(repo, new_oid)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            shutil.copyfile(out, dst)
        ptr = "version https://git-lfs.github.com/spec/v1\noid sha256:%s\nsize %d\n" % (new_oid, size)
        new_sha = git(repo, "hash-object", "-w", "--stdin", inp=ptr.encode()).decode().strip()
        mapping[sha] = new_sha
    mapping.update(substitute)
    mfile = os.path.join(tmp, "map.txt")
    with open(mfile, "w", encoding="ascii", newline="\n") as f:
        f.write("".join("%s %s\n" % kv for kv in mapping.items()))
    pl = os.path.join(tmp, "swap.pl")
    with open(pl, "w", encoding="ascii", newline="\n") as f:
        f.write('open(M, "<", $ARGV[0]) or die; my %m; while (<M>) { chomp; my ($a, $b) = split / /; $m{$a} = $b; } close M;\n'
                'while (<STDIN>) { if (/^(\\d+) ([0-9a-f]{40}) (\\d+)\\t(.*)$/s && exists $m{$2}) { print "$1 $m{$2} $3\\t$4"; } }\n')
    to_sh = lambda p: "/" + p[0].lower() + p[2:].replace("\\", "/")
    idx = "git ls-files -s | perl '%s' '%s' | git update-index --index-info" % (to_sh(pl), to_sh(mfile))
    env = dict(os.environ, FILTER_BRANCH_SQUELCH_WARNING="1")
    r = subprocess.run(["git", "-C", repo, "filter-branch", "-f", "--index-filter", idx, "--tag-name-filter", "cat", "--", "--all"],
                       capture_output=True, env=env)
    log = os.path.join(arch, "%s-%s-filter-branch.log" % (a.game, stamp))
    with open(log, "wb") as f:
        f.write(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit("filter-branch failed (see %s); restore with: git fetch %s '+refs/*:refs/*'" % (log, bundle))

    # ---- verify ----
    left = scan(repo, referenced_pointers(repo), pats)
    new_tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
    fsck = subprocess.run(["git", "-C", repo, "lfs", "fsck"], capture_output=True, text=True)
    print("after: %d referenced LFS objects with a term; HEAD tree %s; git lfs fsck: %s" % (
        len(left), "unchanged" if new_tree == head_tree else "changed" + (" (expected: HEAD referenced a patched object)" if head_had else ""),
        (fsck.stdout + fsck.stderr).strip().splitlines()[-1] if (fsck.stdout + fsck.stderr).strip() else "ok"))
    if left or fsck.returncode or (new_tree != head_tree and not head_had):
        raise SystemExit("verification failed: refs/original/* still hold the old history; bundle %s" % bundle)
    for ref in git(repo, "for-each-ref", "--format=%(refname)", "refs/original/").decode().split():
        git(repo, "update-ref", "-d", ref)
    print("done: %d objects patched, %d pointer blobs swapped; old history in %s (filter-branch log %s)" % (
        len(plan), len(mapping), bundle, log))
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

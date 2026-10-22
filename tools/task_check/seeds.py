"""A commit of the game as a project folder outside its repo, for the checker to build and play.

- materialize: the game's files at a commit, exactly as committed, read straight from its repository (git objects, and
  the Git LFS objects in its local store), written into a scratch folder; each LFS file is a hardlink of its object when
  the folder is on the repo's volume (it costs no disk), else a copy. Nothing in the repo is written or checked out, and
  nothing from another commit is added: a task is built exactly as committed (no port, no patch).
- what a task's agent never sees is left out (ANSWERS): Tasks/, History/, Dataset/ and Dataset.zip at the root.
- add_probe: the TaskProbe plugin as its own folder under Plugins/ (enabled by default: the game's own files, its
  .uproject included, stay exactly as committed). The only thing the checker adds.
- missing_packages: the /Game packages a map names that the commit doesn't hold (e.g. a store pack committed only
  later): a fault of the task's commit, which the checker reports and never fills in."""

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

LFS_POINTER = re.compile(rb"^version https://git-lfs\.github\.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)\n")
POINTER_MAX = 300  # bytes: a Git LFS pointer is smaller (about 130)
PLUGIN = "Plugins/TaskProbe"
PLUGIN_SOURCE = Path(__file__).resolve().parent / "TaskProbe"
ANSWERS = ("tasks", "history", "dataset", "dataset.zip")  # never materialized (case-insensitive, at the root)
ENGINE = "5.7"
PACKAGE = re.compile(rb"/Game/[A-Za-z0-9_/\-]+")
NUMBERED = re.compile(r"^(.+)_\d+$")


class WrongEngine(ValueError):
    """A start that isn't a UE 5.7 project as committed."""


def _git(repo, *args, data=None):
    found = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True, check=False)
    if found.returncode != 0:
        raise RuntimeError(f"git {args[0]} in {Path(repo).name} failed: {found.stderr.decode(errors='replace')[:300]}")
    return found.stdout


def resolve(repo, commit):
    """The full sha of `commit` in `repo`."""
    return _git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()


def lfs_store(repo):
    """Where a repository keeps its Git LFS objects: its lfs.storage, else .git/lfs/objects (lfs/objects when bare)."""
    repo = Path(repo)
    found = subprocess.run(["git", "-C", str(repo), "config", "--get", "lfs.storage"], capture_output=True, text=True)
    if found.returncode == 0 and found.stdout.strip():
        base = Path(found.stdout.strip())
        base = base if base.is_absolute() else Path(_git(repo, "rev-parse", "--absolute-git-dir").decode().strip()) / base
        return base / "objects" if (base / "objects").is_dir() else base
    git_dir = Path(_git(repo, "rev-parse", "--absolute-git-dir").decode().strip())
    common = _git(repo, "rev-parse", "--git-common-dir").decode().strip()
    common = Path(common) if os.path.isabs(common) else (Path(repo) / common).resolve()
    for base in (common, git_dir):
        if (base / "lfs" / "objects").is_dir():
            return base / "lfs" / "objects"
    return common / "lfs" / "objects"


def answer(path):
    """Whether a project-relative path (posix) is under ANSWERS."""
    return path.split("/", 1)[0].lower() in ANSWERS


def place(stored, target, link=True):
    """`target` as a hardlink of the LFS object `stored` (a copy across volumes or when `link` is off)."""
    if link:
        try:
            os.link(stored, target)
            return "linked"
        except OSError:
            pass
    shutil.copyfile(stored, target)
    return "copied"


def materialize(repo, commit, dest, link=True):
    """Write the files of `repo` at `commit` into `dest` (which must not exist), each Git LFS pointer replaced by its
    object from the repo's LFS store (hardlinked when `link` and the volume allows, else copied), and none of ANSWERS.
    Raises FileNotFoundError when an object isn't in the local store (`git lfs fetch` it first). {"files", "linked",
    "copied"}."""
    repo, dest = Path(repo), Path(dest)
    if dest.exists():
        raise FileExistsError(dest)
    listing = _git(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0")
    entries = []
    for line in listing:
        if not line:
            continue
        meta, path = line.split(b"\t", 1)
        mode, kind, oid = meta.split()
        path = path.decode("utf-8")
        if kind == b"blob" and not answer(path):
            entries.append((path, oid.decode()))
    lfs = lfs_store(repo)
    counts = {"files": 0, "linked": 0, "copied": 0}
    missing = []
    with subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE) as batch:
        for path, oid in entries:
            batch.stdin.write(oid.encode() + b"\n")
            batch.stdin.flush()
            header = batch.stdout.readline().split()
            size = int(header[2])
            data = batch.stdout.read(size)
            batch.stdout.read(1)  # the newline after each object
            target = dest / path
            target.parent.mkdir(parents=True, exist_ok=True)
            pointer = LFS_POINTER.match(data) if size < POINTER_MAX else None
            counts["files"] += 1
            if pointer:
                sha = pointer.group(1).decode()
                stored = lfs / sha[:2] / sha[2:4] / sha
                if not stored.is_file():
                    missing.append(path)
                    continue
                counts[place(stored, target, link)] += 1
            else:
                target.write_bytes(data)
        batch.stdin.close()
    if missing:
        raise FileNotFoundError(f"{len(missing)} Git LFS object(s) of {commit[:12]} aren't in {repo.name}'s local store "
                                f"(e.g. {missing[0]}): run `git -C {repo} lfs fetch origin {commit}` first")
    return counts


def uproject(project):
    found = sorted(Path(project).glob("*.uproject"))
    if len(found) != 1:
        raise FileNotFoundError(f"{project} has {len(found)} .uproject files")
    return found[0]


def editor_target(project):
    """The editor build target (<Name>Editor, from Source/<Name>Editor.Target.cs)."""
    found = sorted((Path(project) / "Source").glob("*Editor.Target.cs"))
    return found[0].name.removesuffix(".Target.cs") if found else uproject(project).stem + "Editor"


def engine_of(project):
    return str(json.loads(uproject(project).read_text(encoding="utf-8-sig")).get("EngineAssociation", ""))


def add_probe(project):
    """Add the TaskProbe plugin to `project` as its own folder under Plugins/. Raises WrongEngine when the project
    isn't a UE 5.7 project: a task starts from a commit that builds on 5.7 as committed."""
    project = Path(project)
    engine = engine_of(project)
    if engine != ENGINE:
        raise WrongEngine(f"{uproject(project).name} is a UE {engine or '?'} project: a task's commits must be UE "
                          f"{ENGINE} projects as committed")
    target = project / PLUGIN
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(PLUGIN_SOURCE, target, ignore=shutil.ignore_patterns("Binaries", "Intermediate"))
    return project


def remove(path):
    """`path` removed, read-only files included."""

    def writable(func, target, _):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if Path(path).exists():
        shutil.rmtree(path, onexc=writable)


# -- what a map needs ------------------------------------------------------------------------------------------------


def map_package(play_map):
    """The /Game package of a map (its URL options dropped), and its file under Content/."""
    package = play_map.split("?", 1)[0]
    return package, "Content/" + package[len("/Game/"):] + ".umap"


def missing_packages(repo, commit, play_map):
    """(the /Game packages the map's .umap names that `commit` has no .uasset or .umap for, how many it names), or
    None when the map isn't in the commit or its LFS object isn't at hand. Unreal keeps a name's trailing _<n> apart
    (SM_Rock_6 is written SM_Rock), so a package counts as there when a numbered one of its name is."""
    if not play_map.startswith("/Game/"):
        return None
    names = _git(repo, "ls-tree", "-r", "-z", "--name-only", "--full-tree", commit).decode("utf-8").split("\0")
    have = {"/Game/" + n[len("Content/"):].rsplit(".", 1)[0] for n in names
            if n.startswith("Content/") and n.endswith((".uasset", ".umap"))}
    package, path = map_package(play_map)
    if path not in names:
        return None
    data = _git(repo, "cat-file", "blob", f"{commit}:{path}")
    pointer = LFS_POINTER.match(data) if len(data) < POINTER_MAX else None
    if pointer:
        oid = pointer.group(1).decode()
        stored = lfs_store(repo) / oid[:2] / oid[2:4] / oid
        if not stored.is_file():
            return None
        data = stored.read_bytes()
    refs = {r.decode().split(".")[0] for r in PACKAGE.findall(data)}
    refs = {r for r in refs if not r.startswith(("/Game/__", "/Game/Developers")) and r.rstrip("/") != package}
    numbered = {m.group(1) for m in map(NUMBERED.match, have) if m}
    return sorted(r for r in refs if r not in have and r not in numbered), len(refs)

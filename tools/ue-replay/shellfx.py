"""File edits inside recorded shell commands, re-executed in a sandbox to rebuild file texts between commits.

The builders edited scripts and code from the shell as often as with the editor tools: `cat > f <<'EOF'` heredocs,
`cat >> f`, `sed -i`, `sed '...' a > b`, `cp a b`, and small Python programs (`python - <<'EOF'`, `python -c "..."`,
or a helper file written to a scratch folder and run) that read a file, replace text and write it back, often to a
new `_v2` file. Only those fragments are executed, never the whole command (it may also launch the editor, append
workflow rows or commit). The command is walked simple command by simple command, following `cd`:

  cat > f / cat >> f    exact: the heredoc body is the file text
  sed -i, sed > f       Git's sed on sandbox copies of the files
  python edits          the program runs in the sandbox; a prelude maps the game repo's absolute paths into the
                        sandbox and refuses writes outside it, subprocesses, renames and deletes
  cp / mv               copies the known state
  git checkout/switch   files become unknown (the working tree changed under them)

Any other simple command that writes a tracked file (redirect target, tee, Set-Content, ...) marks it unknown.
Results are checked against the commit at every boundary (ledger.FileStates.boundary).
"""
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

SED = r"C:\Program Files\Git\usr\bin\sed.exe"

HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n")


def segments(text):
    """Simple commands split on && || ; | and newlines (quotes respected)."""
    segs, cur, q, i = [], [], None, 0
    while i < len(text):
        ch = text[i]
        if q:
            cur.append(ch)
            if ch == "\\" and q == '"' and i + 1 < len(text):
                cur.append(text[i + 1])
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
            cur.append(ch)
        elif text.startswith("&&", i) or text.startswith("||", i):
            segs.append("".join(cur))
            cur = []
            i += 2
            continue
        elif ch in ";|\n":
            segs.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    segs.append("".join(cur))
    return [s.strip() for s in segs if s.strip()]


def protect_heredocs(cmd):
    """Heredoc bodies replaced by <<HEREDOC<n> placeholders, so the command splits into simple commands."""
    bodies, out, pos = [], [], 0
    while True:
        m = HEREDOC.search(cmd, pos)
        if not m:
            out.append(cmd[pos:])
            break
        tag = m.group(2)
        end = re.search(r"(?m)^[ \t]*%s[ \t]*$" % re.escape(tag), cmd[m.end():])
        if not end:
            out.append(cmd[pos:])
            break
        body = cmd[m.end():m.end() + end.start()]
        if not m.group(1):  # unquoted tag: bash expands \\ \$ \` and line continuations (variables are left as they are)
            body = re.sub(r"\\([\\$`])", r"\1", body.replace("\\\n", ""))
        bodies.append(body)
        rest_of_line = cmd[m.start():m.end()].split("\n")[0]
        rest_of_line = re.sub(r"^<<-?\s*(['\"]?)\w+\1", "", rest_of_line)
        out.append(cmd[pos:m.start()] + "<<HEREDOC%d " % (len(bodies) - 1) + rest_of_line + "\n")
        pos = m.end() + end.end()
    return "".join(out), bodies


PRELUDE = r'''
import builtins as _b, io as _io, os as _os, sys as _sys
_ROOTS = %(roots)r
_SB = %(sandbox)r
_orig_open = _b.open
_orig_chdir = _os.chdir
_orig_osopen = _os.open
_orig_mkdir = _os.mkdir
def _map(f, write):
    p = _os.fspath(f)
    if isinstance(p, bytes):
        p = p.decode()
    q = p.replace("\\", "/")
    if q.startswith("/c/"):
        q = "C:/" + q[3:]
    for r in _ROOTS:
        if q.lower().startswith(r.lower() + "/") or q.lower() == r.lower():
            q = _SB + q[len(r):]
            break
    # fail closed: whatever the path (absolute, relative after a chdir, ..), a write must land inside the sandbox
    if write:
        full = _os.path.abspath(q).replace("\\", "/")
        if not (full.lower() + "/").startswith(_SB.lower().rstrip("/") + "/"):
            raise PermissionError("sandbox: write outside the sandbox: " + p)
    return q
def _open(f, mode="r", *a, **k):
    if isinstance(f, int):
        return _orig_open(f, mode, *a, **k)
    return _orig_open(_map(f, any(c in mode for c in "wax+")), mode, *a, **k)
def _osopen(f, flags, *a, **k):
    return _orig_osopen(_map(f, bool(flags & (_os.O_WRONLY | _os.O_RDWR | _os.O_CREAT | _os.O_APPEND | _os.O_TRUNC))), flags, *a, **k)
def _chdir(d):
    return _orig_chdir(_map(d, False))
def _mkdir(d, *a, **k):
    return _orig_mkdir(_map(d, True), *a, **k)
_b.open = _open
_io.open = _open
_os.open = _osopen
_os.chdir = _chdir
_os.mkdir = _mkdir
def _blocked(*a, **k):
    raise PermissionError("sandbox: blocked")
_os.system = _os.remove = _os.unlink = _os.rename = _os.replace = _os.rmdir = _os.removedirs = _blocked
import shutil as _sh
_sh.rmtree = _sh.move = _blocked
import subprocess as _sp
_sp.run = _sp.Popen = _sp.call = _sp.check_call = _sp.check_output = _blocked
'''


class Sandbox:
    """A scratch tree holding the known state of the files a fragment may touch."""

    def __init__(self, repo_abs):
        self.repo_abs = repo_abs.replace("\\", "/").rstrip("/")
        self.dir = tempfile.mkdtemp(prefix="uerepl-sb-").replace("\\", "/")

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run(self, states, candidates, cwd_rel, kind, payload, timeout=60):
        """Materialize candidates, run one fragment. python/sed: (ok, err, {path: new bytes}); sed_stdout: (ok, err, stdout)."""
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir)
        before = {}
        for p in candidates:
            st = states.get(p)
            if st is None or st is states.ABSENT:
                continue  # unknown or absent: not materialized; a fragment that reads it fails
            fp = os.path.join(self.dir, p)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "wb") as f:
                f.write(st)
            before[p] = st
        cwd = os.path.join(self.dir, cwd_rel) if cwd_rel else self.dir
        os.makedirs(cwd, exist_ok=True)
        if kind == "python":
            prog = PRELUDE % {"roots": [self.repo_abs], "sandbox": self.dir} + "\n" + payload
            pf = os.path.join(tempfile.gettempdir(), "uerepl-prog-%d.py" % os.getpid())
            with open(pf, "w", encoding="utf-8") as f:
                f.write(prog)
            r = subprocess.run([sys.executable, "-I", pf], cwd=cwd, capture_output=True, timeout=timeout)
            os.remove(pf)
        else:
            # file arguments under the repo point into the sandbox; any other absolute path is refused (fail closed)
            args = []
            for x in payload:
                q = x.replace("\\", "/")
                q = "C:/" + q[3:] if q.startswith("/c/") else q
                if q.lower().startswith(self.repo_abs.lower() + "/"):
                    x = self.dir + q[len(self.repo_abs):]
                elif re.match(r"^(?:[A-Za-z]:/|/)", q) and not q.lower().startswith(self.dir.lower() + "/") and not x.startswith("-"):
                    return (False, "sandbox: sed path outside the sandbox: " + x) + (({} ,) if kind == "sed" else (b"",))
                args.append(x)
            r = subprocess.run([SED] + args, cwd=cwd, capture_output=True, timeout=timeout)
            if kind == "sed_stdout":
                return r.returncode == 0, r.stderr.decode("utf-8", "replace")[-400:], r.stdout.replace(b"\r\n", b"\n")
        ok, err = r.returncode == 0, r.stderr.decode("utf-8", "replace")[-400:]
        changed = {}
        for root, _, files in os.walk(self.dir):
            for fn in files:
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, self.dir).replace("\\", "/")
                with open(fp, "rb") as f:
                    b = f.read().replace(b"\r\n", b"\n")
                if before.get(rel) != b:
                    changed[rel] = b
        return ok, err, changed


def _abs(p):
    p = p.strip("'\"").replace("\\", "/")
    return "C:/" + p[3:] if p.startswith("/c/") else p


def cwd_of(action, repo_abs):
    """Repo-relative working directory the command started in ('' = repo root, None = outside the repo)."""
    root = repo_abs.replace("\\", "/").rstrip("/")
    cwd = _abs(action.get("cwd") or "")
    if cwd.lower() == root.lower():
        return ""
    if cwd.lower().startswith(root.lower() + "/"):
        return cwd[len(root) + 1:]
    return None


def repo_path(tok, cwd_rel, repo_abs):
    t = _abs(tok)
    root = repo_abs.replace("\\", "/").rstrip("/")
    if re.match(r"[A-Za-z]:/", t):
        return t[len(root) + 1:] if t.lower().startswith(root.lower() + "/") else None
    if cwd_rel is None:
        return None
    p = os.path.normpath(os.path.join(cwd_rel or ".", t)).replace("\\", "/")
    return None if p.startswith("..") else p


def apply_command(action, states, sandbox, tracked, log, aux=None):
    """Apply the file edits of one shell command to `states`, simple command by simple command.
    tracked: repo paths worth following; aux: {absolute path: text} of helper files written outside the repo."""
    cmd = action.get("input", {}).get("command", "")
    repo_abs = sandbox.repo_abs
    text, bodies = protect_heredocs(cmd)
    cwd_rel = cwd_of(action, repo_abs)
    names = {}
    for p in tracked:
        names.setdefault(os.path.basename(p), []).append(p)

    def cands(t):
        return set(p for base, ps in names.items() if base in t for p in ps)

    resp = action.get("response")
    if isinstance(resp, str) and resp.lstrip().startswith("{"):
        try:
            resp = json.loads(resp)
        except ValueError:
            pass
    if isinstance(resp, dict):
        resp = "%s\n%s" % (resp.get("stdout") or "", resp.get("stderr") or "")
    elif not isinstance(resp, str):
        resp = json.dumps(resp, ensure_ascii=False)
    shell_vars = {}  # NAME=literal assignments made earlier in this command ($NAME in later paths)

    def expand_vars(t):
        for k in sorted(shell_vars, key=len, reverse=True):
            t = re.sub(r"\$(?:\{%s\}|%s\b)" % (re.escape(k), re.escape(k)), lambda m: shell_vars[k], t)
        return t

    def recorded_failure(how, helper=None):
        """The recorded output shows this Python program raised (a traceback from its own source)."""
        marker = {"python_heredoc": 'File "<stdin>"', "python_c": 'File "<string>"'}.get(how)
        if helper:
            marker = os.path.basename(helper)
        return bool(marker) and "Traceback (most recent call last)" in resp and marker in resp

    def run_python(prog, how, helper=None):
        c = cands(prog)
        if not c or not re.search(r"\.write\(|open\(|write_text|write_bytes", prog):
            return
        ok, err, changed = sandbox.run(states, c, cwd_rel, "python", prog)
        if ok and recorded_failure(how, helper):
            # The sandbox run succeeded where the recorded one raised (e.g. the Bash tool handed the program `\` where
            # the record shows `\\`, so an assert-replace failed): keep the files as they were. A program that fails
            # after a first write is still reproduced, because then the sandbox run fails too.
            log.append((how + "_diverged_discarded", sorted(changed)))
            return
        for p, b in changed.items():
            if p in tracked:
                states.put(p, b, how)
        log.append((how if ok else how + "_failed", sorted(changed) if ok else err[-200:]))

    for seg in segments(text):
        hd = re.search(r"<<HEREDOC(\d+)", seg)
        body = bodies[int(hd.group(1))] if hd else None
        plain = re.sub(r"<<HEREDOC\d+", "", seg)
        try:
            argv = shlex.split(plain, posix=True)
        except ValueError:
            argv = plain.split()
        assigns = []
        while argv and re.match(r"^\w+=", argv[0]):  # VAR=value prefixes
            assigns.append(argv[0])
            argv = argv[1:]
        if assigns and not argv:  # NAME=value on its own: a shell variable for the rest of the command
            for a_ in assigns:
                k, v = a_.split("=", 1)
                if "$(" not in v and "`" not in v:
                    shell_vars[k] = expand_vars(v)
            continue
        if shell_vars:
            plain = expand_vars(plain)
            argv = [expand_vars(x) for x in argv]
        if argv and argv[0] in ("time", "export"):
            argv = argv[1:]
        if not argv:
            continue
        exe = os.path.basename(argv[0].replace("\\", "/")).lower()
        if exe == "cd" and len(argv) > 1:
            d = _abs(argv[1])
            if re.match(r"[A-Za-z]:/", d):
                root = repo_abs.lower()
                cwd_rel = "" if d.lower().rstrip("/") == root else (d[len(repo_abs) + 1:] if d.lower().startswith(root + "/") else None)
            elif cwd_rel is not None:
                n = os.path.normpath(os.path.join(cwd_rel or ".", d)).replace("\\", "/")
                cwd_rel = None if n.startswith("..") else ("" if n == "." else n)
            continue
        if exe == "git" and len(argv) > 1 and argv[1] in ("checkout", "switch", "stash", "reset", "restore", "merge", "rebase", "pull"):
            if argv[1] in ("checkout", "restore") and "--" in argv:
                ps = [repo_path(f, cwd_rel, repo_abs) for f in argv[argv.index("--") + 1:]]
            else:
                ps = list(states.touched)
            for p in ps:
                if p:
                    states.put(p, None, "git_" + argv[1])
            log.append(("git", argv[1]))
            continue
        if exe == "cat" and body is not None:
            m = re.search(r"(>>?)\s*(\"[^\"]+\"|'[^']+'|[^\s<]+)", plain)
            if m:
                p = repo_path(m.group(2), cwd_rel, repo_abs)
                if p is None and aux is not None and re.match(r"[A-Za-z]:/", _abs(m.group(2))):
                    aux[_abs(m.group(2))] = body  # helper file outside the repo, run later
                if p:
                    t = (body + ("\n" if body and not body.endswith("\n") else "")).encode("utf-8")
                    if m.group(1) == ">":
                        states.put(p, t, "heredoc")
                    else:
                        cur = states.get(p)
                        states.put(p, None if cur is None else (b"" if cur is states.ABSENT else cur) + t, "heredoc_append")
                    log.append(("heredoc", p))
            continue
        if exe.startswith("python"):
            a2 = [x for x in argv[1:] if x != "-I"]
            if body is not None and a2[:1] == ["-"]:
                run_python(body, "python_heredoc")
            elif a2[:1] == ["-c"] and len(a2) > 1:
                run_python(a2[1], "python_c")
            elif a2 and aux is not None and _abs(a2[0]) in aux:
                run_python(aux[_abs(a2[0])], "python_helper", helper=_abs(a2[0]))
            continue
        if exe == "perl" and any(re.match(r"^-\w*i", a_) for a_ in argv[1:]):
            # perl -pi / -0pi edits are not reproduced: their files become unknown, so runs use the commit's text
            files_ = []
            skip = False
            for a_ in argv[1:]:
                if skip:
                    skip = False
                    continue
                if a_ in ("-e", "-E"):
                    skip = True
                    continue
                if not a_.startswith("-"):
                    files_.append(a_)
            for f_ in files_:
                p_ = repo_path(f_, cwd_rel, repo_abs)
                if p_:
                    states.put(p_, None, "perl_edit_unknown")
            log.append(("perl_edit_unknown", files_))
            continue
        if exe == "sed":
            redirect = re.search(r"\s>\s*(\"[^\"]+\"|'[^']+'|[^\s;&|]+)\s*$", plain)
            sargs = argv[1:]
            if redirect:
                try:
                    sargs = shlex.split(plain[:redirect.start()], posix=True)[1:]
                except ValueError:
                    continue
            has_e = "-e" in sargs
            files = [a for i, a in enumerate(sargs) if not a.startswith("-") and not (i and sargs[i - 1] == "-e")]
            files = files if has_e else files[1:]
            ps = []
            for f in files:
                rp = repo_path(f, cwd_rel, repo_abs)
                if rp and any(ch in rp for ch in "*?["):
                    ps += sorted(t for t in tracked if fnmatch.fnmatch(t, rp))
                elif rp:
                    ps.append(rp)
            if any(a.startswith("-i") for a in sargs) and ps:
                ok, err, changed = sandbox.run(states, set(ps), cwd_rel, "sed", sargs)
                for p in ps:
                    if states.get(p) is not None and p in changed:
                        states.put(p, changed[p], "sed")
                log.append(("sed" if ok else "sed_failed", ps))
            elif redirect and ps:
                dst = repo_path(redirect.group(1), cwd_rel, repo_abs)
                if dst:
                    known = all(states.get(p) not in (None, states.ABSENT) for p in ps)
                    ok, err, out = sandbox.run(states, set(ps), cwd_rel, "sed_stdout", sargs)
                    states.put(dst, out if ok and known else None, "sed_redirect")
                    log.append(("sed_redirect" if ok else "sed_redirect_failed", dst))
            continue
        if exe in ("cp", "mv") and len(argv) >= 3:
            src = repo_path(argv[-2], cwd_rel, repo_abs)
            dst = repo_path(argv[-1], cwd_rel, repo_abs)
            if dst and (dst in tracked or (src and src in tracked)):
                if argv[-1].endswith("/") or (src and "." in os.path.basename(src) and "." not in os.path.basename(dst)):
                    dst = dst.rstrip("/") + "/" + os.path.basename(src or argv[-2])
                states.put(dst, states.get(src) if src else None, exe)
                if exe == "mv" and src:
                    states.put(src, states.ABSENT, "mv")
                log.append((exe, src, dst))
            continue
        m = re.search(r"(?:(?<![0-9&])>>?|\btee\s+(?:-a\s+)?|Set-Content\s+|Out-File\s+)\s*(\"[^\"]+\"|'[^']+'|[^\s;&|]+)", plain)
        if m:
            p = repo_path(m.group(1), cwd_rel, repo_abs)
            if p and p in tracked:
                states.put(p, None, "shell_write")
                log.append(("unknown", p))

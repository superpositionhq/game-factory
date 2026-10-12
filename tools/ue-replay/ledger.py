"""Ledger: what the builder of a game ran, window by window, from three records.

  git history          the commits on the first-parent chain up to the final commit (the windows' boundaries)
  actions.jsonl        the agent's tool calls: editor-script runs (command lines), Write/Edit of files, shell commands
  workflow.jsonl       the rows each script run logged (op, target, status, params) at the final commit

Output (work/ledger.json, schema ue-replay.ledger/v1):
  windows[]   one per commit: sha, parent, time, subject, inputs (paths changed outside Content/ and in Content/),
              runs[] (editor-script runs in order, each with the reconstructed text of every script file at that
              moment), drops[] and shell[] (from the game settings), reconstruction checks at the boundary
  blobs       sha256 -> file text, stored by the caller in work/blobs/
"""
import collections
import datetime
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess

import shellfx

SCHEMA = "ue-replay.ledger/v1"


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def git(repo, *args, binary=False):
    out = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off"] + list(args), capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode("utf-8")


def parse_time(s):
    return datetime.datetime.fromisoformat(s)


def norm_text(b):
    """Text as stored in git (LF); scripts are compared and replayed with LF line ends."""
    return b.replace(b"\r\n", b"\n")


# ----------------------------------------------------------------------------------------------- commits
def first_parent_chain(repo, final):
    rows = git(repo, "log", "--first-parent", "--reverse", "--format=%H%x09%P%x09%cI%x09%s", final).splitlines()
    out = []
    for r in rows:
        sha, parents, ctime, subject = r.split("\t", 3)
        out.append({"sha": sha, "parents": parents.split(), "time": ctime, "subject": subject})
    return out


def changed_paths(repo, parent, sha):
    """[(status, path)] of sha against its first parent (renames as delete + add)."""
    if parent is None:
        names = git(repo, "ls-tree", "-r", "--name-only", sha).splitlines()
        return [("A", p) for p in names]
    out = []
    for line in git(repo, "diff", "--no-renames", "--name-status", parent, sha).splitlines():
        st, p = line.split("\t", 1)
        out.append((st[0], p))
    return out


def blob_at(repo, sha, path):
    try:
        return git(repo, "show", "%s:%s" % (sha, path), binary=True)
    except subprocess.CalledProcessError:
        return None


# ----------------------------------------------------------------------------------------------- actions
RUN_PATTERNS = [
    # Scripts/ue.ps1 script -Script Scripts/x.py   (the game's wrapper)
    re.compile(r"ue\.ps1\s+script\b[^|;&\n]*?-Script\s+(?P<script>[^\s'\"|;&]+)"),
    # UnrealEditor-Cmd <proj> -run=pythonscript '-script=<path> --args'
    re.compile(r"-run=pythonscript\s+['\"]?-script=(?P<script>[^'\"\s]+)(?P<args>[^'\"]*)['\"]?"),
]
# "exit code N (S s)" (Scripts/ue.ps1) or "exit=N seconds=S" (a game's shell wrapper)
EXIT_RE = re.compile(r"exit code (-?\d+)(?: \((\d+) s\))?|exit=(-?\d+)(?: seconds=(\d+))?|\bexit (-?\d+)(?: log ue-| seconds (\d+))")


# a shell command that exited non-zero still ran: its file edits and editor runs happened
RAN_EVENTS = ("PostToolUse", "PostToolUseFailure")


def _param_expand(val, op, pat):
    """${v%%pat} ${v%pat} ${v##pat} ${v#pat} with glob patterns."""
    n = len(val)
    if op == "%%":
        return next((val[:i] for i in range(0, n + 1) if fnmatch.fnmatchcase(val[i:], pat)), val)
    if op == "%":
        return next((val[:i] for i in range(n, -1, -1) if fnmatch.fnmatchcase(val[i:], pat)), val)
    if op == "##":
        return next((val[i:] for i in range(n, -1, -1) if fnmatch.fnmatchcase(val[:i], pat)), val)
    return next((val[i:] for i in range(0, n + 1) if fnmatch.fnmatchcase(val[:i], pat)), val)


def subst_var(text, var, val):
    v = re.escape(var)
    text = re.sub(r"\$\{" + v + r"(%%|%|##|#)([^}]*)\}", lambda m: _param_expand(val, m.group(1), m.group(2)), text)
    return re.sub(r"\$(?:\{" + v + r"\}|" + v + r"\b)", lambda m: val, text)


def expand_loops(cmd, pats=None, spans=False):
    """`for v in a "b c" d; do ... $v ...; done` (on one line or several) around an editor run: one run per value
    (${v}, ${v%%pat} and ${v##pat} forms included)."""
    m = re.search(r"\bfor (\w+) in ([^;\n]+?)\s*(?:;|\n)\s*do\b(.*?)(?:;|\n)\s*done\b", cmd, re.S)
    if m:
        try:
            values = shlex.split(m.group(2), posix=True)
        except ValueError:
            values = m.group(2).split()
    else:
        # PowerShell: foreach ($v in "a", "b") { ... $v ... }
        m = re.search(r"\bforeach\s*\(\s*\$(\w+)\s+in\s+([^)]+)\)\s*\{(.*?)\}", cmd, re.S | re.I)
        if not m:
            return [cmd]
        values = [v.strip().strip("'\"") for v in m.group(2).split(",") if v.strip()]
    var, body = m.group(1), m.group(3)
    out = [cmd[:m.start()] + subst_var(body, var, v) + cmd[m.end():] for v in values]
    if not any(p.search(subst_var(body, var, v)) for v in values for p in (pats or RUN_PATTERNS)):
        return [cmd]
    if spans:
        # copy k > 0 repeats the text around the loop: only its loop body counts (no duplicate runs outside the loop)
        return [(c, 0, len(c)) if k == 0 else (c, m.start(), m.start() + len(subst_var(body, var, values[k])))
                for k, c in enumerate(out)]
    return out


# NAME=literal at the start of a simple command (not after && / ||: conditional)
ASSIGN_RE = re.compile(r"(?:^|[;\n(]|\bdo\b|\bthen\b)[ \t]*(?:export[ \t]+)?([A-Za-z_]\w*)="
                       r"(\"[^\"$`]*\"|'[^']*'|[^\s;&|)$`'\"]*)(?=[\s;&|)]|$)")


def subst_assigned(cmd, pos, text):
    """$NAME in text, for a NAME the command assigned a literal value before pos (the last such assignment)."""
    vals = {}
    for m in ASSIGN_RE.finditer(cmd[:pos]):
        vals[m.group(1)] = m.group(2).strip("\"'")
    for k in sorted(vals, key=len, reverse=True):
        text = subst_var(text, k, vals[k])
    return text


def editor_runs(actions, repo_abs, extra_patterns=()):
    """Editor-script runs found in shell commands, in order. Each: time (end of the tool call), approximate start,
    script (repo-relative or absolute), args, exit code / duration when the output says so."""
    # extra patterns: a regex (named groups script, args, mode, reason), or {"pattern": regex, "script": template,
    # "args": template, "mode": ...} for a host-side wrapper that starts the editor itself with a fixed script
    # (rally: Scripts/scrub_paths.py --mode apply -> the factory's scrub-import-paths.py --apply); templates take
    # {name} for the pattern's named groups
    templates = {}
    pats = list(RUN_PATTERNS)
    for x in extra_patterns:
        if isinstance(x, dict):
            templates[len(pats)] = x
            pats.append(re.compile(x["pattern"]))
        else:
            pats.append(re.compile(x))
    runs = []
    prev_time = None
    for a in actions:
        prev, prev_time = prev_time, a["time"]
        if a.get("tool") not in ("Bash", "PowerShell") or a.get("event") not in RAN_EVENTS:
            continue
        cmd = a.get("input", {}).get("command", "")
        # heredoc bodies are file contents (e.g. a wrapper script being written), not commands; loops are expanded
        # first, so a run written as `for s in ...; do wrapper "Scripts/${s%%|*}"; done` is found
        expanded = expand_loops(shellfx.protect_heredocs(cmd)[0], pats, spans=True)
        if isinstance(expanded[0], str):
            expanded = [(c, 0, len(c)) for c in expanded]
        if not any(p.search(c) for c, _, _ in expanded for p in pats):
            continue
        resp = a.get("response") or ""
        if not isinstance(resp, str):
            resp = json.dumps(resp)
        exits = [(x[0] or x[2] or x[4], x[1] or x[3] or x[5] or None) for x in EXIT_RE.findall(resp)]
        found = []
        for k, (c, lo_k, hi_k) in enumerate(expanded):
            for pi, pat in enumerate(pats):
                for m in pat.finditer(c):
                    if not (lo_k <= m.start() < hi_k):
                        continue
                    g = {k2: (v or "") for k2, v in m.groupdict().items()}
                    if pi in templates:
                        tp = templates[pi]
                        g["script"] = tp["script"].format(**g)
                        g["args"] = tp.get("args", "{args}" if "args" in g else "").format(**g)
                        g["mode"] = tp.get("mode", g.get("mode") or "commandlet")
                    g = {k2: (v if v != "" else None) for k2, v in g.items()}
                    reason = g.get("reason") if g.get("reason") is not None else g.get("reason_sq")
                    env = run_env(c, m.start())
                    if g.get("env_args"):
                        # a wrapper that takes "--env K=V" pairs and hands them to the script (stealth's ue_run*.py)
                        try:
                            toks = shlex.split(subst_assigned(c, m.start(), g["env_args"]), posix=True)
                        except ValueError:
                            toks = g["env_args"].split()
                        for ti, tok in enumerate(toks):
                            kv = toks[ti + 1] if tok == "--env" and ti + 1 < len(toks) else tok[6:] if tok.startswith("--env=") else None
                            if kv and "=" in kv:
                                ek, ev = kv.split("=", 1)
                                env[ek] = ev
                    found.append(((k, m.start()), subst_assigned(c, m.start(), g["script"]),
                                  subst_assigned(c, m.start(), (g.get("args") or "").strip()), env,
                                  reason if reason is not None else run_reason(c, m.start()), g.get("mode") or "commandlet",
                                  pi >= len(RUN_PATTERNS)))
        found.sort()
        for i, ((_, pos), script, args, env, reason, mode, via_wrapper) in enumerate(found):
            ex = exits[i] if i < len(exits) and len(exits) == len(found) else None
            s = script.replace("\\", "/")
            if re.match(r"^[A-Za-z]:/", s) and s.lower().startswith(repo_abs.lower().rstrip("/") + "/"):
                s = s[len(repo_abs.rstrip("/")) + 1:]
            runs.append({
                "time": a["time"], "action_tool_use_id": a.get("tool_use_id"), "script": s, "args": args,
                "exit_code": int(ex[0]) if ex else None, "duration_s": int(ex[1]) if ex and ex[1] else None,
                # started in the background: by the tool, or with a shell `&` (rows then arrive after the call ends)
                "background": bool(re.search(r'"backgroundTaskId"', resp)) or bool(re.search(r"[^&]&[ \t]*(?:\n|$|;|echo\b|wait\b|disown\b)", c)),
                "after": prev,
                "env": env, "reason": reason, "mode": mode, "via_wrapper": via_wrapper, "pos": pos,
                "command": cmd[:2000],
            })
    return runs


def run_env(cmd, pos):
    """VAR=value assignments in front of the simple command that holds position pos (and earlier `export`s)."""
    start, q = -1, None   # last command separator before pos, outside quotes
    for i in range(pos):
        ch = cmd[i]
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch in ";|\n" or cmd.startswith("&&", i):
            start = i
    env = {}
    for m in re.finditer(r"(?:^|\s)(?:export\s+)?([A-Z][A-Z0-9_]+)=(\"[^\"]*\"|'[^']*'|[^\s;&|]+)", cmd[:pos]):
        if m.group(1) in ("MSYS_NO_PATHCONV", "PATH", "PY", "W", "L", "D", "S", "T"):
            continue
        if m.start() >= start or "export" in m.group(0):
            env[m.group(1)] = m.group(2).strip("\"'")
    return env


def run_reason(cmd, pos):
    m = re.search(r"-Reason\s+(\"[^\"]*\"|'[^']*'|\S+)", cmd[pos:pos + 2000].split("\n")[0])
    return m.group(1).strip("\"'") if m else None


def repo_rel(path, repo_abs):
    p = path.replace("\\", "/")
    root = repo_abs.replace("\\", "/").rstrip("/") + "/"
    if p.lower().startswith(root.lower()):
        return p[len(root):]
    return None


ABSENT = object()  # sentinel: the file does not exist yet


TEXT_EXT = (".py", ".ps1", ".sh", ".bat", ".cpp", ".h", ".cs", ".ini", ".json", ".md", ".uproject", ".txt", ".gitignore",
            ".gitattributes", ".csv", ".tsv")


class FileStates:
    """Text of repo files as the agent's Write/Edit calls and shell edits left them. None = unknown."""

    ABSENT = None  # set below

    def __init__(self, repo, start_sha):
        self.repo = repo
        self.base_sha = start_sha
        self.state = {}       # path -> bytes | None (unknown) | ABSENT
        self.touched = set()  # paths written or edited since the last boundary
        self.how = {}         # path -> last kind of write
        self.tracked = None   # paths reported at boundaries (set by the caller)
        self.mismatch = {}    # sha256 -> reconstructed text that did not match its commit

    def get(self, path):
        """Current text; ABSENT when the file does not exist yet, None when unknown."""
        if path not in self.state:
            b = blob_at(self.repo, self.base_sha, path)
            self.state[path] = norm_text(b) if b is not None else ABSENT
        return self.state[path]

    def write(self, path, content):
        self.state[path] = norm_text(content.encode("utf-8"))
        self.touched.add(path)

    def edit(self, path, old, new, replace_all):
        cur = self.get(path)
        self.touched.add(path)
        if cur is None or cur is ABSENT:
            self.state[path] = None
            return False
        o, n = norm_text(old.encode("utf-8")), norm_text(new.encode("utf-8"))
        if o not in cur:
            self.state[path] = None
            return False
        self.state[path] = cur.replace(o, n) if replace_all else cur.replace(o, n, 1)
        return True

    def put(self, path, content, how):
        if content is not None and content is not ABSENT:
            content = norm_text(content)
        self.state[path] = content
        self.touched.add(path)
        self.how[path] = how

    def boundary(self, sha):
        """Compare what Write/Edit left with the commit, then reset to the commit."""
        checks = []
        for p in sorted(self.touched):
            if self.tracked is not None and p not in self.tracked:
                continue
            st = self.state.get(p)
            b = blob_at(self.repo, sha, p)
            blob = norm_text(b) if b is not None else None
            c = {"path": p, "reconstructed": st is not None, "how": self.how.get(p),
                 "match": st is not None and (st == blob if blob is not None else st is ABSENT)}
            if not c["match"] and isinstance(st, bytes):
                c["sha256"] = sha256(st)
                self.mismatch[c["sha256"]] = st
            checks.append(c)
        self.state = {}
        self.touched = set()
        self.how = {}
        self.base_sha = sha
        return checks


FileStates.ABSENT = ABSENT


# ----------------------------------------------------------------------------------------------- build
def build(cfg):
    repo = cfg["repo"]
    repo_abs = repo.replace("\\", "/")
    final = git(repo, "rev-parse", cfg["final"]).strip()
    chain = first_parent_chain(repo, final)
    # fold_commits: commits that hold only part of the work done before them (e.g. a README-only commit while the
    # scripts and C++ those runs used came a commit later) are not window boundaries; their work goes to the next one
    fold = [f.lower() for f in cfg.get("fold_commits", [])]
    chain = [c for c in chain if c["sha"] == final or not any(c["sha"].lower().startswith(f) for f in fold)]
    actions = [json.loads(l) for l in open(os.path.join(cfg["recording"], "actions.jsonl"), encoding="utf-8")]
    actions.sort(key=lambda a: a["time"])
    t_final = parse_time(chain[-1]["time"])
    actions = [a for a in actions if parse_time(a["time"]) <= t_final + datetime.timedelta(seconds=60)]
    wf_rows = [json.loads(l) for l in git(repo, "show", "%s:workflow.jsonl" % final).splitlines() if l.strip()]

    runs = editor_runs(actions, repo_abs, cfg.get("run_patterns", []))
    ro = cfg.get("readonly_patterns", [])
    for r in runs:
        base = os.path.basename(r["script"])
        # not_readonly: scripts a read-only pattern matches that still write something a later run reads
        # (horror: probe_clip_speeds.py writes Saved/clip_speeds.json for fix_anim_rates.py)
        r["readonly"] = any(fnmatch.fnmatch(base, p) for p in ro) and base not in cfg.get("not_readonly", [])
        if r["duration_s"] is not None and not r["background"]:
            r["start"] = (parse_time(r["time"]) - datetime.timedelta(seconds=r["duration_s"])).isoformat(timespec="milliseconds")
        else:
            r["start"] = r["time"]

    # windows by commit time (the first commit has no window: it is the starting point)
    win_of = lambda t: next((i for i, c in enumerate(chain) if parse_time(c["time"]) >= parse_time(t)), None)
    windows = []
    for i, c in enumerate(chain):
        parent = chain[i - 1]["sha"] if i else None
        ch = changed_paths(repo, parent, c["sha"])
        windows.append({
            "index": i, "sha": c["sha"], "parent": parent, "time": c["time"], "subject": c["subject"],
            "merge_parents": c["parents"][1:],
            "inputs": [{"status": s, "path": p} for s, p in ch if not p.startswith("Content/")],
            "content": [{"status": s, "path": p} for s, p in ch if p.startswith("Content/")],
            "scripts_changed": sorted(p for s, p in ch if p.startswith("Scripts/")),
            "runs": [], "drops": [], "shell": [], "reconstruction": [], "events": collections.Counter(),
        })

    # walk actions in time order: file states, runs (with script texts), drops, shell steps
    fs = FileStates(repo, chain[0]["sha"])
    blobs = {}
    script_paths = set(p for w in windows for p in w["scripts_changed"])
    tracked = set(x["path"] for w in windows for x in w["inputs"]
                  if x["path"].endswith(TEXT_EXT) and x["path"] != "workflow.jsonl")
    sandbox = shellfx.Sandbox(repo_abs)
    fs.tracked = tracked
    aux = {}  # helper files the agent wrote outside the repo (absolute path -> text)
    run_by_tool = collections.defaultdict(list)
    for r in runs:
        run_by_tool[r["action_tool_use_id"]].append(r)
    drops = {d["id"]: d for d in cfg.get("asset_drops", [])}
    shells = cfg.get("shell_replay", [])
    seen_tool = set()
    cur_w = 1
    run_seq = 0

    def close_until(t):
        nonlocal cur_w
        while cur_w < len(windows) and parse_time(windows[cur_w]["time"]) < parse_time(t):
            windows[cur_w]["reconstruction"] = fs.boundary(windows[cur_w]["sha"])
            cur_w += 1

    for a in actions:
        # A command that ends with `git commit` did its work before that commit: close only the windows whose commits
        # come before the command started, so its edits and runs land in the window the commit closes.
        cmd_text = (a.get("input") or {}).get("command", "") if a.get("tool") in ("Bash", "PowerShell") else ""
        if "git commit" in cmd_text and run_by_tool.get(a.get("tool_use_id")):
            first = run_by_tool[a["tool_use_id"]][0]
            close_until(first.get("start") or a["time"])
        else:
            close_until(a["time"])
        if cur_w >= len(windows):
            break
        w = windows[cur_w]
        tool = a.get("tool")
        if a.get("event") != "PostToolUse" and not (tool in ("Bash", "PowerShell") and a.get("event") in RAN_EVENTS):
            continue
        inp = a.get("input") or {}
        if tool in ("Bash", "PowerShell") and inp.get("command"):
            fx = []
            shellfx.apply_command(a, fs, sandbox, tracked, fx, aux)
            if fx:
                w["events"]["shell_edits"] += len(fx)
                for e in fx:
                    if e[0].endswith("failed"):
                        w["events"]["shell_edit_failed"] += 1
        if tool == "Write" and not repo_rel(inp.get("file_path", ""), repo_abs):
            aux[inp.get("file_path", "").replace("\\", "/")] = inp.get("content", "")
        if tool == "Write":
            p = repo_rel(inp.get("file_path", ""), repo_abs)
            if p:
                fs.write(p, inp.get("content", ""))
                w["events"]["write"] += 1
        elif tool == "Edit":
            p = repo_rel(inp.get("file_path", ""), repo_abs)
            if p:
                ok = fs.edit(p, inp.get("old_string", ""), inp.get("new_string", ""), inp.get("replace_all", False))
                w["events"]["edit" if ok else "edit_unapplied"] += 1
        elif tool in ("Bash", "PowerShell"):
            cmd = inp.get("command", "")
            for d in drops.values():
                if d.get("match") and d["match"] in cmd and d["id"] not in seen_tool:
                    seen_tool.add(d["id"])
                    w["drops"].append(dict(d, time=a["time"]))
            for s in shells:
                if s["match"] in cmd and ("shell", s["match"]) not in seen_tool:
                    seen_tool.add(("shell", s["match"]))
                    w["shell"].append(dict(s, time=a["time"], pos=shellfx.protect_heredocs(cmd)[0].find(s["match"])))
            # runs in this command, at the command's position in time (texts as of before the command's own writes)
            for r in run_by_tool.get(a.get("tool_use_id"), []):
                run_seq += 1
                # every script file the window changes, as it stood when the run started
                texts, unknown, absent = {}, [], []
                for p in w["scripts_changed"]:
                    st = fs.get(p)
                    if st is None:
                        unknown.append(p)
                    elif st is ABSENT:
                        absent.append(p)
                    else:
                        h = sha256(st)
                        blobs[h] = st
                        texts[p] = h
                rr = dict(r, id="R%04d" % run_seq, window=w["index"], texts=texts, unknown=unknown, absent=absent)
                if not r["script"].startswith("Scripts/"):
                    rr["script_version"] = "external"
                elif r["script"] in texts:
                    rr["script_version"] = "reconstructed" if r["script"] in fs.touched else "as_of_parent"
                elif r["script"] in unknown or r["script"] in absent:
                    rr["script_version"] = "unknown_use_commit"
                else:
                    rr["script_version"] = "unchanged"
                w["runs"].append(rr)
    close_until("9999-12-31T00:00:00+00:00")
    sandbox.close()
    blobs.update(fs.mismatch)

    # rows each run logged (by script and time window)
    by_script = collections.defaultdict(list)
    wrapper_by_script = collections.defaultdict(list)
    wrapper_ops = set(cfg.get("wrapper_row_ops", []))   # rows a game's run wrapper logs around each run (not the script's)
    for row in wf_rows:
        if row.get("op") in wrapper_ops:
            # a wrapper names the script it ran in source.script (siege) or in target (tower-defense: source.script is
            # the wrapper itself); index the row under both
            for s in {((row.get("source") or {}).get("script") or "").replace("\\", "/"), str(row.get("target") or "").replace("\\", "/")}:
                m = re.search(r"(?:^|/)(Scripts/.+\.py)$", s)
                if s:
                    wrapper_by_script[m.group(1) if m and (s.startswith("..") or re.match(r"^[A-Za-z]:/|^/", s)) else s].append(row)
            continue
        s = (row.get("source") or {}).get("script")
        if s:
            # a script that passed a relative path to the recorder ("Scripts/x.py" resolved against the editor's
            # working directory) logged "../../…/Engine/Binaries/Win64/Scripts/x.py"
            m = re.search(r"(?:^|/)(Scripts/[^/]+\.py)$", s.replace("\\", "/"))
            by_script[m.group(1) if m and s.startswith("..") else s].append(row)
    all_runs = [r for w in windows for r in w["runs"]]
    for k, r in enumerate(all_runs):
        nxt = next((x for x in all_runs[k + 1:] if x["script"] == r["script"]), None)
        # rows are written while the tool call runs: after the previous tool call ended (tool calls are sequential)
        lo = parse_time(r["after"] or r["start"]) - datetime.timedelta(seconds=1)
        prev_same = next((x for x in reversed(all_runs[:k]) if x["script"] == r["script"] and x["time"] == r["time"]), None)
        if prev_same:  # the same script twice in one command: split at the first run's estimated end
            lo = max(lo, parse_time(prev_same["time"]))
        hi = parse_time(nxt["start"]) if nxt else parse_time(r["time"]) + datetime.timedelta(hours=2)
        hi = min(hi, parse_time(r["time"]) + datetime.timedelta(seconds=5)) if not r["background"] else hi
        r["rows"] = [x["id"] for x in by_script.get(r["script"], []) if lo <= parse_time(x["time"]) <= hi]
        for nr in cfg.get("not_run", []):
            # runs the records show never happened (a loop stopped, a refused start, a withdrawn GPU wait)
            if nr.get("tool_use_id") == r.get("action_tool_use_id") and (not nr.get("script") or nr["script"] in r["script"]):
                r["not_run"] = nr.get("reason", "listed in settings not_run")
        if wrapper_ops and r.get("via_wrapper"):
            # the game's run wrapper logs a row before every run it starts: none means the command never got there
            # (an earlier step of the same command failed), so the run did not happen
            r["wrapper_rows"] = sum(1 for x in wrapper_by_script.get(r["script"], []) if lo <= parse_time(x["time"]) <= hi)
    for w in windows:
        w["events"] = dict(w["events"])
    return {"schema": SCHEMA, "game": cfg["game"], "final": final, "first": chain[0]["sha"],
            "windows": windows, "counts": {
                "windows": len(windows) - 1, "runs": len(all_runs),
                "runs_readonly": sum(1 for r in all_runs if r["readonly"]),
                "script_version": dict(collections.Counter(r["script_version"] for r in all_runs)),
                "runs_with_unknown_helper": sum(1 for r in all_runs if r["unknown"]),
                "reconstruction_checks": sum(len(w["reconstruction"]) for w in windows),
                "reconstruction_match": sum(1 for w in windows for c in w["reconstruction"] if c["match"]),
                "reconstruction_unknown": sum(1 for w in windows for c in w["reconstruction"] if not c["reconstructed"]),
            }}, blobs

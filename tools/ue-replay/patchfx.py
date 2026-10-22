"""File effects of a Codex apply_patch call, for the ledger.

Codex edits files with one tool, apply_patch, whose input (actions.jsonl "input.command") is a patch in its own format:

    *** Begin Patch
    *** Add File: <path>          every following line starts with "+"
    *** Delete File: <path>
    *** Update File: <path>
    *** Move to: <new path>       optional, right after Update File
    @@ <optional anchor line>     one per hunk; lines " " context, "-" removed, "+" added
    *** End of File               optional
    *** End Patch

Paths are absolute or relative to the call's working directory (the row's "cwd"). parse() turns the text into
operations; apply_update() applies an Update's hunks to a file's text the way apply_patch does (each hunk searched
from where the previous one ended: exactly, then ignoring trailing whitespace, then ignoring surrounding whitespace).
"""
import posixpath
import re

_ABS = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/])")


def resolve(path, cwd):
    """The patch path as an absolute path with forward slashes (cwd joins a relative one)."""
    p = path.strip().replace("\\", "/")
    if not _ABS.match(p) and cwd:
        p = cwd.replace("\\", "/").rstrip("/") + "/" + p
    drive = ""
    if re.match(r"^[A-Za-z]:/", p):
        drive, p = p[:2], p[2:]
    return drive + posixpath.normpath(p)


def parse(text):
    """[(op, path, data)]: ("add", path, content), ("delete", path, None), ("update", path, {"move": path|None,
    "hunks": [(anchor|None, old_lines, new_lines)]}). Raises ValueError on a text that is not a patch."""
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != "*** Begin Patch":
        raise ValueError("no '*** Begin Patch'")
    i += 1
    ops = []
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == "*** End Patch":
            return ops
        if ln.startswith("*** Add File: "):
            path, body = ln[len("*** Add File: "):], []
            i += 1
            while i < len(lines) and not lines[i].startswith("*** "):
                if lines[i].startswith("+"):
                    body.append(lines[i][1:])
                i += 1
            ops.append(("add", path, "\n".join(body) + ("\n" if body else "")))
            continue
        if ln.startswith("*** Delete File: "):
            ops.append(("delete", ln[len("*** Delete File: "):], None))
            i += 1
            continue
        if ln.startswith("*** Update File: "):
            path = ln[len("*** Update File: "):]
            i += 1
            move = None
            if i < len(lines) and lines[i].startswith("*** Move to: "):
                move = lines[i][len("*** Move to: "):]
                i += 1
            hunks, anchor, old, new, started = [], None, [], [], False
            while i < len(lines) and not (lines[i].startswith("*** ") and lines[i].strip() != "*** End of File"):
                h = lines[i]
                if h.startswith("@@"):
                    if started and (old or new):
                        hunks.append((anchor, old, new))
                    anchor = h[2:].strip() or None
                    old, new, started = [], [], True
                elif h.strip() == "*** End of File":
                    pass
                elif h.startswith("-"):
                    old.append(h[1:]); started = True
                elif h.startswith("+"):
                    new.append(h[1:]); started = True
                elif h.startswith(" ") or h == "":
                    # a blank line inside a hunk is a context line whose leading space was lost
                    if h == "" and i + 1 < len(lines) and lines[i + 1].startswith("*** "):
                        pass
                    else:
                        old.append(h[1:]); new.append(h[1:]); started = True
                i += 1
            if old or new:
                hunks.append((anchor, old, new))
            ops.append(("update", path, {"move": move, "hunks": hunks}))
            continue
        if not ln.strip():
            i += 1
            continue
        raise ValueError("unexpected line %r" % ln[:80])
    raise ValueError("no '*** End Patch'")


def _find(lines, seq, start):
    if not seq:
        return start
    for norm in (lambda s: s, lambda s: s.rstrip(), lambda s: s.strip()):
        want = [norm(s) for s in seq]
        for k in range(start, len(lines) - len(seq) + 1):
            if all(norm(lines[k + j]) == want[j] for j in range(len(seq))):
                return k
    return -1


def apply_update(text, hunks):
    """The file text after the hunks, or None when a hunk does not apply."""
    lines = text.split("\n")
    trailing_nl = text.endswith("\n")
    if trailing_nl:
        lines = lines[:-1]
    pos = 0
    for anchor, old, new in hunks:
        found = -1
        if anchor:
            found = _find(lines, [anchor], pos)
            if found >= 0:
                pos = found + 1
        if not old:   # pure insertion: right after the anchor, else at the end of the file
            at = pos if found >= 0 else len(lines)
            lines[at:at] = new
            pos = at + len(new)
            continue
        k = _find(lines, old, pos)
        if k < 0:
            return None
        lines[k:k + len(old)] = new
        pos = k + len(new)
    return "\n".join(lines) + ("\n" if trailing_nl or not lines else "")

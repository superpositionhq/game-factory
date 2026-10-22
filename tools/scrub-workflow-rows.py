#!/usr/bin/env python3
"""Remove banned names from a game's workflow.jsonl rows in place, and append the correction row (game format v1).

    python tools/scrub-workflow-rows.py <games>/<slug>            # dry run: which rows, which terms, the result
    python tools/scrub-workflow-rows.py <games>/<slug> --apply    # edit the rows, append the log.correct row

workflow.jsonl is append-only with one exception (commit-always skill): a row naming a banned term is edited in place
to remove it, nothing else in the row changes, and a correction row is appended (op "log.correct", params
{"rows": [ids], "what": "removed banned names"}). The commit then names the edited rows (the tool prints the line).

Replacements, on the row's text (JSON escapes kept, so nothing else moves):
  legacy schema id "superposition.ue-workflow/v0"   -> "ue-workflow/v0"
  the machine root (any spelling: C:\\..., C:/..., /c/...)   -> <root>
  the user profile folder                            -> <home>
  the account (user) name as a word                  -> <user>
  the tool repo's name (game-factory, game_factory, gamefactory)   -> <factory>
  the studio / org name (superposition)              -> studio
  agent identity / names (Claude (agent), Claude ..., noreply address)   -> agent, agent@example.invalid
  the provider name (Anthropic)                      -> provider
  e-mail addresses (not example/placeholder ones)    -> <email>
The machine root and account name come from this machine (GF_ROOT / config, USERNAME); nothing machine-specific is
written in this file. Every edited line must still parse as JSON, or nothing is written. Standard library only.
"""
import argparse, datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'machine', 'lib'))
import gfroot  # noqa: E402

SEP = r'(?:\\\\|\\|/)+'          # a path separator in row text: \, \\ (JSON-escaped) or /


def path_rx(path):
    """A regex for an absolute Windows path in any spelling (C:\\a\\b, C:/a/b, /c/a/b, JSON-escaped)."""
    p = os.path.abspath(path).replace('\\', '/').rstrip('/')
    drive, rest = (p[0], p[2:].strip('/')) if re.match(r'^[A-Za-z]:', p) else ('', p.strip('/'))
    parts = [re.escape(x) for x in rest.split('/') if x]
    head = r'(?:%s:%s|/%s/)' % (drive, SEP, drive.lower()) if drive else SEP
    return re.compile(r'(?i)' + head + SEP.join(parts) + r'(?![A-Za-z0-9_.-])')


def rules():
    root = gfroot.root()
    home = os.path.expanduser('~')
    user = os.environ.get('USERNAME') or os.path.basename(home)
    word = r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])'
    out = [
        ('schema', re.compile(r'(?i)"superposition\.(ue-workflow/v\d)'), r'"\1'),
        ('root', path_rx(root), '<root>'),
        ('home', path_rx(home), '<home>'),
        ('factory', re.compile(r'(?i)game[-_ ]?factory'), '<factory>'),
        ('studio', re.compile(r'(?i)superposition'), 'studio'),
        ('agent', re.compile(r'Claude \(agent\)'), 'agent'),
        ('agent', re.compile(r'(?i)noreply@anthropic\.com'), 'agent@example.invalid'),
        ('agent', re.compile(r'(?i)\bclaude(?:[ -](?:opus|sonnet|haiku|fable|code)(?:[ -][0-9.]+)?)?\b'), 'agent'),
        ('provider', re.compile(r'(?i)\banthropic\b'), 'provider'),
        # Codex (OpenAI): the tool's own names and model ids; a bare "codex" stays (games have lore codices)
        ('agent', re.compile(r'(?i)\b(?:openai[ -])?codex[ -](?:cli|exec)\b|\bopenai codex\b'), 'agent'),
        ('agent', re.compile(r'(?i)\bgpt-\d+(?:\.\d+)?(?:-[a-z0-9]+)*\b'), 'agent-model'),
        ('provider', re.compile(r'(?i)\bopenai\b'), 'provider'),
        ('email', re.compile(r'(?<![A-Za-z0-9._%+-])(?!git@|noreply@github\.com)[A-Za-z0-9._%+-]+@'
                             r'(?!(?:[A-Za-z0-9-]+\.)*(?:example\.(?:com|org|net)|invalid|test|localhost)\b)'
                             r'(?:[A-Za-z0-9-]+\.)+(?!(?:png|jpe?g|uasset|umap|json|py|ps1|md|txt)\b)[A-Za-z]{2,}\b'), '<email>'),
    ]
    if user and len(user) >= 3:
        out.append(('user', re.compile(r'(?i)' + word % re.escape(user)), '<user>'))
    return out


def scrub_line(line, rs):
    counts = {}
    for name, rx, rep in rs:
        line, n = rx.subn(rep, line)
        if n:
            counts[name] = counts.get(name, 0) + n
    return line, counts


def ranges(ids):
    """['a-1','a-2','a-3','a-7'] -> 'a-1..a-3, a-7'"""
    out, run = [], []
    def flush():
        if run:
            out.append(run[0] if len(run) == 1 else '%s..%s' % (run[0], run[-1]))
    prev = None
    for i in ids:
        m = re.match(r'^(.*-)(\d+)$', i)
        n = (m.group(1), int(m.group(2))) if m else None
        if prev and n and prev[0] == n[0] and n[1] == prev[1] + 1:
            run.append(i)
        else:
            flush(); run = [i]
        prev = n
    flush()
    return ', '.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('repo')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--file', default='workflow.jsonl', help='relative to the repo (default workflow.jsonl)')
    a = ap.parse_args()
    path = os.path.join(os.path.abspath(a.repo), a.file)
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    # split on LF and keep each line's own CR (some files mix CRLF and LF rows)
    lines = text.split('\n')
    crs = [l.endswith('\r') for l in lines]
    lines = [l[:-1] if c else l for l, c in zip(lines, crs)]
    rs = rules()
    edited, totals, last = [], {}, None
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        new, counts = scrub_line(line, rs)
        try:
            row = json.loads(new)
        except ValueError as e:
            sys.exit('line %d would not parse after the edit (%s): nothing written' % (i + 1, e))
        last = row
        if counts:
            lines[i] = new
            edited.append(row.get('id', 'line %d' % (i + 1)))
            for k, v in counts.items():
                totals[k] = totals.get(k, 0) + v
    print('%s: %d row(s) to edit; replacements: %s' % (a.file, len(edited), ', '.join('%s %d' % kv for kv in sorted(totals.items())) or 'none'))
    if not edited:
        return 0
    print('rows: %s' % ranges(edited))
    m = re.match(r'^(.*-)(\d+)$', str(last.get('id', '')))
    width = len(m.group(2)) if m else 4
    nid = '%s%0*d' % (m.group(1), width, int(m.group(2)) + 1) if m else 'log-correct-1'
    now = datetime.datetime.now().astimezone()
    corr = {'schema': 'ue-workflow/v0', 'id': nid, 'seq': int(last.get('seq', 0)) + 1,
            'time': now.isoformat(timespec='milliseconds'), 'actor': 'agent', 'op': 'log.correct', 'target': 'workflow.jsonl',
            'params': {'rows': edited, 'what': 'removed banned names'},
            'reason': 'Rows named terms that never appear in a game (tool, studio, agent or account names, machine paths); '
                      'edited in place to neutral words or placeholders, nothing else changed (game format v1).',
            'reason_source': 'agent_note', 'source': {'script': None, 'sha256': None}, 'status': 'observed'}
    print('correction row: %s (seq %d)' % (nid, corr['seq']))
    print('commit message line: Removed banned names from workflow.jsonl rows %s (correction row %s).' % (ranges(edited), nid))
    if not a.apply:
        print('dry run: nothing written (--apply edits the rows and appends the correction row)')
        return 0
    while lines and not lines[-1].strip():
        lines.pop()
        crs.pop()
    eol = '\r\n' if crs and crs[-1] else '\n'
    body = '\n'.join(l + ('\r' if c else '') for l, c in zip(lines, crs)) + '\n' + json.dumps(corr, ensure_ascii=False) + eol
    with open(path, 'wb') as f:
        f.write((b'\xef\xbb\xbf' if bom else b'') + body.encode('utf-8'))
    print('written %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Validate a game against the final game format (docs/game-format-v1.json, prose docs/game-format.md).

    python tools/validate-game.py <games>/<slug>                 # the repo, its Dataset/ and Dataset.zip if present
    python tools/validate-game.py --dataset <Dataset.zip|folder>  # a dataset alone (what a consumer receives)
    options: --no-layout (skip tools/validate-dataset.ps1), --no-zip, --json <file>, --quiet

Checks the repo (required files, engine, .gitignore, Git LFS for binaries, README images, banned names,
assets.manifest.json in the one unified format with every listed file committed under Content/ or RawAssets/,
workflow.jsonl rows) and the dataset contents (manifest.json, workflow.jsonl, git.log,
ReplayScripts/Verification/report.json against docs/schemas/, cross-file rules, and in Dataset.zip every asset file
inside UEProject/). The dataset layout (entries, video format, hashes, README sections) is
tools/validate-dataset.ps1, which this script runs too on Windows unless --no-layout.

Verdict: VALID (no errors), INVALID (errors). Exit code 0 / 2. Warnings never change the verdict.
Standard library only (Python 3.10+).
"""
import argparse, io, json, os, re, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SPEC = json.load(open(os.path.join(REPO, 'docs', 'game-format-v1.json'), encoding='utf-8'))
SCHEMAS = {n: json.load(open(os.path.join(REPO, 'docs', 'schemas', n + '.schema.json'), encoding='utf-8'))
           for n in ('workflow-row', 'dataset-manifest', 'replay-report', 'assets-manifest', 'game-task')}


class Report:
    def __init__(self):
        self.items = []  # (severity, area, message)

    def error(self, area, msg): self.items.append(('error', area, msg))
    def warn(self, area, msg): self.items.append(('warning', area, msg))
    def note(self, area, msg): self.items.append(('note', area, msg))

    def count(self, sev): return sum(1 for s, _, _ in self.items if s == sev)


# ---- a small JSON Schema subset validator (type, required, properties, additionalProperties: false, enum, const,
# ---- pattern, minLength, minimum, items, minItems, $ref "#/$defs/...") --------------------------------------------
TYPES = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'null': type(None)}


def _is(v, t):
    if t == 'integer': return isinstance(v, int) and not isinstance(v, bool)
    if t == 'number': return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, TYPES[t])


def check_schema(value, schema, root=None, path='$'):
    """Yield 'path: problem' strings for value against schema."""
    root = root or schema
    if '$ref' in schema:
        ref = schema['$ref']
        node = root
        for part in ref.lstrip('#/').split('/'):
            node = node[part]
        yield from check_schema(value, node, root, path)
        return
    if 'type' in schema:
        ts = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        if not any(_is(value, t) for t in ts):
            yield f'{path}: expected {"/".join(ts)}, got {type(value).__name__}'
            return
    # combinators (the game environment's task schema uses them: optional fields, check kinds)
    if 'allOf' in schema:
        for sub in schema['allOf']:
            yield from check_schema(value, sub, root, path)
    for key in ('anyOf', 'oneOf'):
        if key in schema:
            fits = [list(check_schema(value, sub, root, path)) for sub in schema[key]]
            ok = sum(1 for f in fits if not f)
            if ok == 0:
                best = min(fits, key=len)
                yield f'{path}: matches none of the allowed shapes ({best[0] if best else "?"})'
            elif key == 'oneOf' and ok > 1 and 'discriminator' not in schema:
                yield f'{path}: matches more than one of the allowed shapes'
    if 'const' in schema and value != schema['const']:
        yield f'{path}: must be {json.dumps(schema["const"])}, got {json.dumps(value)[:80]}'
    if 'enum' in schema and value not in schema['enum']:
        yield f'{path}: {json.dumps(value)[:80]} not one of {schema["enum"]}'
    if isinstance(value, str):
        if 'minLength' in schema and len(value) < schema['minLength']:
            yield f'{path}: empty'
        if 'maxLength' in schema and len(value) > schema['maxLength']:
            yield f'{path}: longer than {schema["maxLength"]}'
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            yield f'{path}: {value[:80]!r} does not match {schema["pattern"]}'
    if _is(value, 'number'):
        if 'minimum' in schema and value < schema['minimum']:
            yield f'{path}: {value} < {schema["minimum"]}'
        if 'maximum' in schema and value > schema['maximum']:
            yield f'{path}: {value} > {schema["maximum"]}'
        if 'exclusiveMinimum' in schema and value <= schema['exclusiveMinimum']:
            yield f'{path}: {value} <= {schema["exclusiveMinimum"]}'
        if 'exclusiveMaximum' in schema and value >= schema['exclusiveMaximum']:
            yield f'{path}: {value} >= {schema["exclusiveMaximum"]}'
    if isinstance(value, dict):
        for k in schema.get('required', []):
            if k not in value:
                yield f'{path}: missing "{k}"'
        props = schema.get('properties', {})
        for k, v in value.items():
            if k in props:
                yield from check_schema(v, props[k], root, f'{path}.{k}')
            elif schema.get('additionalProperties') is False:
                yield f'{path}: unexpected key "{k}"'
    if isinstance(value, list):
        if 'minItems' in schema and len(value) < schema['minItems']:
            yield f'{path}: needs at least {schema["minItems"]} item(s)'
        if 'maxItems' in schema and len(value) > schema['maxItems']:
            yield f'{path}: more than {schema["maxItems"]} item(s)'
        if 'items' in schema:
            for i, v in enumerate(value):
                yield from check_schema(v, schema['items'], root, f'{path}[{i}]')


def schema_errors(rep, area, value, name, limit=20):
    problems = list(check_schema(value, SCHEMAS[name]))
    for p in problems[:limit]:
        rep.error(area, p)
    if len(problems) > limit:
        rep.error(area, f'... and {len(problems) - limit} more schema problems')
    return not problems


# ---- shared content checks ---------------------------------------------------------------------------------------------
def check_workflow(rep, area, lines, allow_schema=None):
    """lines: iterable of text lines of a workflow.jsonl. Returns ids of user.direction rows."""
    seen, directions, prev_seq, bad_rows, n, empty_reason = set(), set(), None, 0, 0, 0
    problems = []
    grouped = {}  # schema problem (row-independent text) -> [count, first line]
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            row = json.loads(line)
        except ValueError as e:
            problems.append(f'line {i}: not JSON ({e})')
            continue
        if allow_schema and isinstance(row, dict) and row.get('schema') in allow_schema:
            row = dict(row, schema='ue-workflow/v0')
        errs = list(check_schema(row, SCHEMAS['workflow-row']))
        if errs:
            bad_rows += 1
            for e in errs:
                g = grouped.setdefault(e, [0, i])
                g[0] += 1
            continue
        if not row['reason'].strip():
            empty_reason += 1
        if row['id'] in seen:
            problems.append(f'line {i}: duplicate id {row["id"]}')
        seen.add(row['id'])
        if prev_seq is not None and row['seq'] <= prev_seq:
            problems.append(f'line {i}: seq {row["seq"]} not after {prev_seq}')
        prev_seq = row['seq']
        if row['op'] == 'user.direction':
            if row['actor'] != 'user' or row['reason_source'] != 'user_direction' or not str(row['params'].get('direction', '')).strip():
                problems.append(f'line {i}: user.direction row needs actor user, reason_source user_direction, params.direction')
            directions.add(row['id'])
        if 'direction' in row and row['direction'] not in directions:
            problems.append(f'line {i}: direction {row["direction"]} is not an earlier user.direction row')
    for e, (count, first) in sorted(grouped.items(), key=lambda kv: -kv[1][0])[:15]:
        rep.error(area, f'{count} row(s), first at line {first}: {e}')
    for p in problems[:25]:
        rep.error(area, p)
    if len(problems) > 25:
        rep.error(area, f'... {len(problems) - 25} more')
    if empty_reason:
        rep.warn(area, f'{empty_reason} row(s) with an empty reason')
    if n == 0:
        rep.error(area, 'no rows')
    else:
        rep.note(area, f'{n} rows, {bad_rows} not matching the row schema, {len(directions)} user.direction rows')
    return directions


def check_git_log(rep, area, stream):
    g = SPEC['dataset']['git_log']
    first = stream.readline().rstrip('\r\n')
    if first != g['first_line']:
        rep.error(area, f'first line must be "{g["first_line"]}", got {first[:40]!r}')
    shas, expect, problems = [], None, []
    commit_rx, author_rx, date_rx = re.compile(g['commit_line']), re.compile(g['author_pattern']), re.compile(g['date_pattern'])
    for i, line in enumerate(stream, 2):
        line = line.rstrip('\r\n')
        if expect is None:
            if line.startswith('commit ') and not line.startswith(' '):
                if not commit_rx.match(line):
                    problems.append(f'line {i}: bad commit line {line[:60]!r}')
                    continue
                shas.append(line[7:])
                expect = list(g['fields_in_order'])
            continue
        field = expect.pop(0)
        if not line.startswith(field + ':'):
            problems.append(f'line {i}: expected "{field}:" after commit {shas[-1][:8]}, got {line[:40]!r}')
            expect = None
            continue
        value = line[len(field) + 1:].strip()
        if field in ('Author', 'Committer') and not author_rx.match(value):
            problems.append(f'line {i}: {field} "{value[:40]}" is not anonymised (dev_NN)')
        if field in ('AuthorDate', 'CommitDate') and not date_rx.match(value):
            problems.append(f'line {i}: {field} "{value}" is not ISO 8601')
        if not expect:
            expect = None
    if len(set(shas)) != len(shas):
        problems.append('a commit appears twice')
    for p in problems[:20]:
        rep.error(area, p)
    if not shas:
        rep.error(area, 'no commits')
    else:
        rep.note(area, f'{len(shas)} commits')
    return shas[-1] if shas else None


def git_ls(repo):
    out = subprocess.run(['git', '-C', repo, '-c', 'core.quotepath=off', 'ls-files', '-z'], capture_output=True)
    return [p for p in out.stdout.decode('utf-8', 'replace').split('\0') if p]


def check_assets_manifest(rep, area, data, present):
    """data: parsed assets.manifest.json; present(path) -> True when the file (or, for a path ending in /, any file
    under the folder) is there."""
    if not isinstance(data, dict) or data.get('schema') != 'assets-manifest/v1':
        rep.error(area, 'not in the unified format (schema "assets-manifest/v1"): convert with tools/migrate-assets-manifest.py')
        return
    schema_ok = schema_errors(rep, area, data, 'assets-manifest')
    # the schema's if/then/else (the small validator above does not evaluate it): in-house assets (origin "studio")
    # carry a description instead of a url; every other asset needs an https url
    for i, a in enumerate(data.get('assets') if isinstance(data.get('assets'), list) else []):
        if not isinstance(a, dict):
            continue
        if a.get('origin') == 'studio':
            if not str(a.get('description', '')).strip():
                rep.error(area, f'$.assets[{i}] ({a.get("name")}): origin studio needs a "description"')
        elif not str(a.get('url', '')).startswith('https://'):
            rep.error(area, f'$.assets[{i}] ({a.get("name")}): needs an https "url" (or origin "studio" with a description, for in-house assets)')
    if not schema_ok:
        return
    missing, outside, n = [], [], 0
    for a in data['assets']:
        for f in a['files']:
            n += 1
            if not re.match(r'^(Content|RawAssets)/', f):
                outside.append(f'{a["name"]}: {f}')
            if not present(f):
                missing.append(f'{a["name"]}: {f}')
    for m in outside[:10]:
        rep.error(area, f'asset path outside Content/ or RawAssets/: {m}')
    for m in missing[:15]:
        rep.error(area, f'listed asset file not present: {m}')
    if len(missing) > 15:
        rep.error(area, f'... {len(missing) - 15} more listed files not present')
    rep.note(area, f'{len(data["assets"])} assets, {n} listed paths, {len(missing)} missing')


# ---- dataset (folder or zip) -------------------------------------------------------------------------------------------
class DatasetView:
    def __init__(self, path):
        self.path = path
        self.zip = None
        if path.lower().endswith('.zip'):
            self.zip = zipfile.ZipFile(path)
            names = [n for n in self.zip.namelist() if not n.endswith('/')]
            tops = sorted({n.split('/')[0] for n in names})
            self.top = tops[0] if len(tops) == 1 else None
            self.names = {n[len(self.top) + 1:]: n for n in names} if self.top else {}
            self.sizes = {n[len(self.top) + 1:]: self.zip.getinfo(n).file_size for n in names} if self.top else {}
        else:
            self.top = os.path.basename(os.path.normpath(path))
            self.names, self.sizes = {}, {}
            for d, _, fs in os.walk(path):
                for f in fs:
                    full = os.path.join(d, f)
                    rel = os.path.relpath(full, path).replace('\\', '/')
                    self.names[rel] = full
                    self.sizes[rel] = os.path.getsize(full)

    def has(self, rel): return rel in self.names
    def has_dir(self, rel): return any(n.startswith(rel.rstrip('/') + '/') for n in self.names)

    def open_text(self, rel):
        if self.zip:
            return io.TextIOWrapper(self.zip.open(self.names[rel]), encoding='utf-8-sig', errors='replace')
        return open(self.names[rel], encoding='utf-8-sig', errors='replace')

    def json(self, rel):
        with self.open_text(rel) as f:
            return json.load(f)


def check_dataset(rep, path, area='dataset'):
    v = DatasetView(path)
    if v.zip and not v.top:
        rep.error(area, 'the zip must hold exactly one top folder (<game>/)')
        return
    if not v.has('manifest.json'):
        rep.error(area, 'no manifest.json')
        return
    try:
        m = v.json('manifest.json')
    except ValueError as e:
        rep.error(area, f'manifest.json is not JSON: {e}')
        return
    ok = schema_errors(rep, f'{area}: manifest.json', m, 'dataset-manifest')
    if not ok:
        return
    a = f'{area}: manifest.json'
    if v.zip and m['game'] != v.top:
        rep.error(a, f'game "{m["game"]}" differs from the zip top folder "{v.top}"')
    listed = {f['path']: f for f in m['files']}
    for p, f in listed.items():
        if p not in v.sizes:
            rep.error(a, f'files[] lists {p}, not in the dataset')
        elif v.sizes[p] != f['bytes']:
            rep.error(a, f'{p}: {v.sizes[p]} bytes, manifest says {f["bytes"]}')
    if m['totals']['files'] != len(m['files']) or m['totals']['bytes'] != sum(f['bytes'] for f in m['files']):
        rep.error(a, 'totals do not match files[]')
    for s in m['scenarios']:
        if s['file'] not in listed:
            rep.error(a, f'scenario file {s["file"]} not in files[]')
    if m['variant'] == 'full' and not isinstance(m.get('build'), dict):
        rep.error(a, 'variant full needs a build object')
    if m['variant'] == 'repo-dataset' and m.get('build') is not None:
        rep.error(a, 'variant repo-dataset has build null')
    # workflow.jsonl
    directions = set()
    if v.has('workflow.jsonl'):
        with v.open_text('workflow.jsonl') as f:
            directions = check_workflow(rep, f'{area}: workflow.jsonl', f)
    else:
        rep.error(area, 'no workflow.jsonl')
    # git.log
    last = None
    if v.has('git.log'):
        with v.open_text('git.log') as f:
            last = check_git_log(rep, f'{area}: git.log', f)
        if last and last != m['commit']:
            rep.error(f'{area}: git.log', f'last commit {last[:12]} differs from manifest commit {m["commit"][:12]}')
    else:
        rep.error(area, 'no git.log')
    # replay report
    rp = 'ReplayScripts/Verification/report.json'
    if v.has(rp):
        r = v.json(rp)
        if schema_errors(rep, f'{area}: report.json', r, 'replay-report'):
            if r['final_commit'] != m['commit']:
                rep.error(f'{area}: report.json', f'final_commit {r["final_commit"][:12]} differs from manifest commit {m["commit"][:12]}')
            # the verdict is metadata (user rule: the replay is required but need not pass); manifest and report agree
            rv = m.get('replay_verification')
            if isinstance(rv, dict) and 'pass' in rv and bool(rv['pass']) != bool(r['verdict']['pass']):
                rep.error(f'{area}: report.json', f'verdict pass {r["verdict"]["pass"]} differs from manifest replay_verification.pass {rv["pass"]}')
            if not r['verdict']['pass']:
                rep.note(f'{area}: report.json', 'creation replay verification FAIL (metadata)')
    elif m['status'] == 'complete':
        rep.error(area, f'status complete but no {rp}')
    if m['status'] == 'complete':
        if m['pending']:
            rep.error(a, 'status complete with pending entries')
        if not isinstance(m.get('replay_verification'), dict) or not isinstance(m['replay_verification'].get('pass'), bool):
            rep.error(a, 'status complete needs replay_verification with pass true or false')
    else:
        rep.warn(a, f'status pending: {", ".join(m["pending"]) or "(nothing listed)"}')
    # replay_verification is null only while ReplayScripts/ is pending (docs/game-deliverable.md: "null while pending")
    if m.get('replay_verification') is None and not any(str(p).rstrip('/') == 'ReplayScripts' for p in m['pending']):
        rep.error(a, 'replay_verification is null but ReplayScripts/ is not listed as pending')
    # videos: at least one (user rule 2026-10-19: one recorded scenario is enough), unless Gameplay/ is listed as pending
    if not m['scenarios'] and not any(str(p).rstrip('/') == 'Gameplay' for p in m['pending']):
        rep.error(a, 'no scenario videos: a delivery has at least one, or lists Gameplay/ as pending')
    # v1.2: Brief/, the person's directions, History/
    if m['layout'] in ('dataset-layout/v1.2', 'dataset-layout/v1.3'):
        b = m.get('brief')
        if not isinstance(b, dict):
            rep.error(a, 'layout v1.2 needs brief {"brief": "Brief/brief.md", "design": "Brief/design.md"}')
        for rel in ('Brief/brief.md', 'Brief/design.md'):
            if not v.has(rel):
                rep.error(area, f'no {rel}')
            elif v.sizes[rel] < 200:
                rep.error(area, f'{rel} is nearly empty ({v.sizes[rel]} bytes)')
        if not directions:
            rep.warn(f'{area}: workflow.jsonl', "no user.direction rows: the person's directions are recorded nowhere else")
        if m['variant'] == 'full':
            check_history(rep, area, v, m)
            if m['layout'] == 'dataset-layout/v1.3':
                check_tasks(rep, area, v, m)
        else:
            if m.get('history') is not None or v.has_dir('History'):
                rep.error(area, 'a repo Dataset/ has no History/ and history null (the repo is its own history)')
            if v.has_dir('Tasks'):
                rep.error(area, 'a repo Dataset/ has no Tasks/ (tasks live on the game repo\'s tasks branch)')
    # full variant: every asset file listed by the project's assets.manifest.json is inside UEProject/
    if m['variant'] == 'full':
        am = 'UEProject/assets.manifest.json'
        if v.has(am):
            check_assets_manifest(rep, f'{area}: {am}', v.json(am),
                                  lambda f: v.has_dir('UEProject/' + f) if f.endswith('/') else (v.has('UEProject/' + f) or v.has_dir('UEProject/' + f)))
        else:
            rep.error(area, f'no {am}')
    rep.note(area, f'{m["game"]} {m["variant"]} {m["status"]}: {len(m["files"])} files, {len(m["scenarios"])} scenario video(s)')


LFS_PTR = re.compile(rb'^version https://git-lfs\.github\.com/spec/v1\r?\noid sha256:([0-9a-f]{64})\r?\nsize ([0-9]+)')
OPTS = {'hash': True, 'quick': False}


def git_out(*args, input=None):
    r = subprocess.run(['git', *args], capture_output=True, input=input)
    if r.returncode != 0:
        raise RuntimeError(f'git {" ".join(args[:3])}: {r.stderr.decode("utf-8", "replace").strip()[:200]}')
    return r.stdout


def check_history(rep, area, v, m):
    """v1.2 full variant: History/<game>.bundle + History/lfs/objects (every LFS object of every commit)."""
    import hashlib, tempfile
    a = f'{area}: History'
    h = m.get('history')
    if not isinstance(h, dict):
        rep.error(a, 'manifest.json history must be an object in a v1.2 Dataset.zip')
        return
    if h['head'] != m['commit']:
        rep.error(a, f'history.head {h["head"][:12]} differs from manifest commit {m["commit"][:12]}')
    if not v.has(h['bundle']):
        rep.error(a, f'no {h["bundle"]}')
        return
    objs = {rel[len('History/lfs/objects/'):].split('/')[-1]: rel for rel in v.names if rel.startswith('History/lfs/objects/')}
    for oid, rel in objs.items():
        if not re.fullmatch(r'[0-9a-f]{64}', oid) or rel != f'History/lfs/objects/{oid[:2]}/{oid[2:4]}/{oid}':
            rep.error(a, f'{rel}: not at lfs/objects/<aa>/<bb>/<sha256>')
    if len(objs) != h['lfs_objects'] or sum(v.sizes[r] for r in objs.values()) != h['lfs_bytes']:
        rep.error(a, f'{len(objs)} LFS objects / {sum(v.sizes[r] for r in objs.values())} bytes, manifest history says {h["lfs_objects"]} / {h["lfs_bytes"]}')
    if OPTS['quick']:
        rep.note(a, 'quick: bundle contents and LFS hashes not checked')
        return
    with tempfile.TemporaryDirectory(prefix='validate-game-') as tmp:
        bundle = v.names[h['bundle']]
        if v.zip:
            bundle = os.path.join(tmp, 'h.bundle')
            with v.zip.open(v.names[h['bundle']]) as src, open(bundle, 'wb') as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
        try:
            heads = git_out('bundle', 'list-heads', bundle).decode().split()
            if h['head'] not in heads:
                rep.error(a, f'the bundle has no ref at history.head {h["head"][:12]}')
            bare = os.path.join(tmp, 'repo.git')
            git_out('clone', '--quiet', '--bare', '--mirror', bundle, bare)
            commits = git_out('-C', bare, 'rev-list', '--all').decode().split()
            v.commits = set(commits)   # for the tasks' seed commits (layout v1.3)
            if len(commits) != h['commits']:
                rep.error(a, f'the bundle holds {len(commits)} commits, manifest history says {h["commits"]}')
            idents = set(git_out('-C', bare, 'log', '--all', '--format=%an%n%cn%n%ae%n%ce').decode('utf-8', 'replace').split('\n')) - {''}
            bad = sorted(i for i in idents if not re.fullmatch(r'dev_[0-9]+(@[a-z0-9.-]+)?', i))
            if bad:
                rep.error(a, f'{len(bad)} author/committer identities are not anonymised (dev_NN), e.g. {bad[0][:3]}...')
            msgs = git_out('-C', bare, 'log', '--all', '--format=%B').decode('utf-8', 'replace')
            for p in SPEC['repo']['banned_names']['patterns']:
                n = len(re.findall(p, msgs))
                if n:
                    rep.error(a, f'commit messages: {p} x{n}')
            # every LFS pointer of every commit has its object
            objlist = git_out('-C', bare, 'rev-list', '--objects', '--all').decode('utf-8', 'replace').splitlines()
            shas = '\n'.join(l.split(' ')[0] for l in objlist) + '\n'
            small = [l.split(' ') for l in git_out('-C', bare, 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)',
                                                   input=shas.encode()).decode().splitlines()]
            cand = [s[0] for s in small if len(s) == 3 and s[1] == 'blob' and int(s[2]) < 300]
            need, missing = set(), []
            if cand:
                data = git_out('-C', bare, 'cat-file', '--batch', input=('\n'.join(cand) + '\n').encode())
                pos = 0
                while pos < len(data):
                    nl = data.index(b'\n', pos)
                    size = int(data[pos:nl].split()[2])
                    body = data[nl + 1:nl + 1 + size]
                    pos = nl + 1 + size + 1
                    mm = LFS_PTR.match(body)
                    if mm:
                        need.add((mm.group(1).decode(), int(mm.group(2))))
            for oid, size in sorted(need):
                rel = objs.get(oid)
                if not rel:
                    missing.append(oid)
                elif v.sizes[rel] != size:
                    rep.error(a, f'LFS object {oid[:12]}: {v.sizes[rel]} bytes, its pointer says {size}')
            for oid in missing[:10]:
                rep.error(a, f'LFS object {oid[:12]}... is referenced by a commit but not in History/lfs/objects')
            if len(missing) > 10:
                rep.error(a, f'... {len(missing) - 10} more LFS objects missing')
            if OPTS['hash']:
                badhash = 0
                for oid, rel in objs.items():
                    hs = hashlib.sha256()
                    with (v.zip.open(v.names[rel]) if v.zip else open(v.names[rel], 'rb')) as f:
                        for chunk in iter(lambda: f.read(1 << 20), b''):
                            hs.update(chunk)
                    if hs.hexdigest() != oid:
                        badhash += 1
                        if badhash <= 5:
                            rep.error(a, f'{rel}: content does not hash to its name')
            rep.note(a, f'{len(commits)} commits, {len(heads) // 2} ref(s), {len(need)} LFS objects referenced, {len(objs)} present')
        except (RuntimeError, ValueError, IndexError) as e:
            rep.error(a, f'cannot read the bundle: {e}')


TASK_NAME = re.compile(r'^[a-z0-9][a-z0-9-]{1,62}$')
GRADER_KEYS = ('milestones',)          # the grader's half of a task, with seed.reference


def task_semantic_errors(t):
    """What the schema cannot say (the game environment's tasks.validate): check names unique, `needs` naming earlier
    checks, a code judge or a reference judge only with seed.reference, a before/after judge only with a seed, a
    calibrated probe only with seed.reference, a start-relative probe only with a seed."""
    errs, seen = [], set()
    seed = t.get('seed') if isinstance(t.get('seed'), dict) else None
    ref = seed.get('reference') if seed else None
    for m in t.get('milestones') or []:
        for c in (m.get('checks') or []) if isinstance(m, dict) else []:
            if not isinstance(c, dict):
                continue
            n, k = c.get('name'), c.get('kind')
            if k == 'code_judge' and not ref:
                errs.append(f'check {n}: a code judge needs seed.reference')
            if k == 'judge' and c.get('before') and not seed:
                errs.append(f'check {n}: a before/after judge needs a seed')
            if k == 'judge' and c.get('reference') and not ref:
                errs.append(f'check {n}: a reference judge needs seed.reference')
            if k == 'probe':
                exp = c.get('expect') if isinstance(c.get('expect'), dict) else {}
                if 'calibrate' in exp and not ref:
                    errs.append(f'check {n}: a calibrated probe needs seed.reference')
                if ('start_times' in exp or 'start_plus' in exp) and not seed:
                    errs.append(f'check {n}: a probe relative to the start needs a seed')
            if n in seen:
                errs.append(f'check {n} is named twice')
            missing = [x for x in (c.get('needs') or []) if x not in seen]
            if missing:
                errs.append(f'check {n} needs {missing}, which come later or do not exist')
            seen.add(n)
    return errs


def check_task(rep, a, label, t, game, has_commit):
    """One whole task (GameTask): schema, the environment's extra rules, seed on `game` and on known commits."""
    for e in list(check_schema(t, SCHEMAS['game-task']))[:5]:
        rep.error(a, f'{label}: {e}')
    for e in task_semantic_errors(t)[:5]:
        rep.error(a, f'{label}: {e}')
    gated = [c for m in t.get('milestones') or [] if isinstance(m, dict) for c in m.get('checks') or []
             if isinstance(c, dict) and c.get('kind') == 'probe' and c.get('required', True)]
    judged = [c.get('name') for m in t.get('milestones') or [] if isinstance(m, dict) for c in m.get('checks') or []
              if isinstance(c, dict) and c.get('kind') in ('judge', 'code_judge', 'actions_judge')
              and c.get('required', True)]
    if not gated:
        rep.error(a, f'{label}: no required probe check: pass/fail must be deterministic (write-tasks section 5)')
    if judged:
        rep.note(a, f'{label}: required judge check(s) {judged}: judges should be "required": false quality checks')
    s = t.get('seed')
    if isinstance(s, dict):
        if s.get('game') != game:
            rep.error(a, f'{label}: seed.game {s.get("game")!r} is not this game ({game})')
        for k in ('commit', 'reference'):
            c = s.get(k)
            if c and has_commit is not None and not has_commit(c):
                rep.error(a, f'{label}: seed.{k} {str(c)[:12]} is not a commit of this game\'s history'
                             + (' (an ancestor of main\'s head)' if a.startswith('repo') else ''))


TASKS_REFS = ('tasks', 'origin/tasks')   # where a game's tasks live: its orphan tasks branch, never main


def _git(repo, *args):
    return subprocess.run(['git', '-C', repo, *args], capture_output=True)


def check_repo_tasks(rep, repo, files=None):
    """The game's tasks on its orphan `tasks` branch (`tasks`, else `origin/tasks`): Tasks/<name>.json, one GameTask
    each, name = file stem, seeds on commits of main's history (ancestors of HEAD, the main branch in a game checkout).
    The branch shares no history with main, and main's HEAD tracks nothing under Tasks/. Read from git, not the
    working tree (`files` is unused)."""
    a = 'repo: Tasks'
    game = os.path.basename(os.path.normpath(repo))
    on_main = [p for p in _git(repo, '-c', 'core.quotepath=off', 'ls-tree', '-r', '--name-only', 'HEAD', '--', 'Tasks')
               .stdout.decode('utf-8', 'replace').splitlines() if p.strip()]
    if on_main:
        rep.error(a, f'main tracks {len(on_main)} path(s) under Tasks/ (e.g. {on_main[0]}): '
                     'tasks live on the tasks branch, never on main')
    ref = next((r for r in TASKS_REFS if _git(repo, 'rev-parse', '--verify', '-q', r + '^{commit}').returncode == 0), None)
    if not ref:
        rep.error(a, 'no tasks branch (neither tasks nor origin/tasks): a game ships at least one task, '
                     'on its orphan tasks branch')
        return
    if _git(repo, 'merge-base', ref, 'HEAD').returncode == 0:
        rep.error(a, f'{ref} shares history with main: tasks must be an orphan branch')
    names = [n for n in _git(repo, '-c', 'core.quotepath=off', 'ls-tree', '--name-only', ref + ':Tasks')
             .stdout.decode('utf-8', 'replace').splitlines() if n.strip()]
    paths = ['Tasks/' + n for n in names if n.endswith('.json')]
    if not paths:
        rep.error(a, f'no task files in Tasks/ on {ref} (a game ships at least one; about 10 recommended)')
        return
    known = {}

    def has_commit(c):   # a commit of main's history: an ancestor of main's head
        if c not in known:
            known[c] = _git(repo, 'merge-base', '--is-ancestor', c, 'HEAD').returncode == 0
        return known[c]
    for f in paths:
        stem = f[len('Tasks/'):-len('.json')]
        label = f'{ref}:{f}'
        r = _git(repo, 'show', label)
        if r.returncode != 0:
            rep.error(a, f'{label}: cannot read ({r.stderr.decode("utf-8", "replace").strip()[:120]})')
            continue
        try:
            t = json.loads(r.stdout.decode('utf-8-sig'))
        except ValueError as e:
            rep.error(a, f'{label}: not JSON ({e})')
            continue
        if not isinstance(t, dict):
            rep.error(a, f'{label}: not a task object')
            continue
        if t.get('name') != stem:
            rep.error(a, f'{label}: name {t.get("name")!r} differs from the file name')
        check_task(rep, a, label, t, game, has_commit)
    rep.note(a, f'{len(paths)} task(s) on {ref} (about 10 recommended)')


def check_tasks(rep, area, v, m):
    """Layout v1.3 Tasks/ in a Dataset.zip: README.md and Tasks/<name>/task.json + grader.json per task; the agent's part
    holds none of the grader's half; merged, each is a valid task on this game and on commits of History/."""
    a = f'{area}: Tasks'
    if not v.has('Tasks/README.md'):
        rep.error(a, 'no Tasks/README.md')
    folders = sorted({r.split('/')[1] for r in v.names if r.startswith('Tasks/') and r.count('/') >= 2})
    stray = sorted(r for r in v.names if r.startswith('Tasks/') and r != 'Tasks/README.md'
                   and not re.fullmatch(r'Tasks/[^/]+/(task|grader)\.json', r))
    for r in stray[:5]:
        rep.error(a, f'{r}: not part of the layout (Tasks/<name>/task.json, Tasks/<name>/grader.json, Tasks/README.md)')
    if not folders:
        rep.error(a, 'no tasks (a game ships at least one)')
    commits = getattr(v, 'commits', None)
    names = []
    for name in folders:
        tp, gp = f'Tasks/{name}/task.json', f'Tasks/{name}/grader.json'
        if not (v.has(tp) and v.has(gp)):
            rep.error(a, f'Tasks/{name}/: needs task.json and grader.json')
            continue
        try:
            task, grader = v.json(tp), v.json(gp)
        except ValueError as e:
            rep.error(a, f'Tasks/{name}/: not JSON ({e})')
            continue
        if not isinstance(task, dict) or not isinstance(grader, dict):
            rep.error(a, f'Tasks/{name}/: task.json and grader.json must be objects')
            continue
        leaked = [k for k in GRADER_KEYS if k in task] + (['seed.reference'] if isinstance(task.get('seed'), dict) and 'reference' in task['seed'] else [])
        if leaked:
            rep.error(a, f'{tp}: holds the grader\'s half ({", ".join(leaked)}): it belongs in grader.json')
        extra = [k for k in grader if k not in ('name', 'seed') + GRADER_KEYS] + \
                ([k for k in grader['seed'] if k != 'reference'] if isinstance(grader.get('seed'), dict) else [])
        if extra:
            rep.error(a, f'{gp}: only name, milestones and seed.reference belong here, not {extra}')
        if task.get('name') != name or grader.get('name') != name:
            rep.error(a, f'Tasks/{name}/: name fields must equal the folder name')
        whole = dict(task)
        for k in GRADER_KEYS:
            if k in grader:
                whole[k] = grader[k]
        if isinstance(grader.get('seed'), dict) and isinstance(whole.get('seed'), dict):
            whole['seed'] = dict(whole['seed'], **grader['seed'])
        check_task(rep, a, f'Tasks/{name}', whole, m['game'], (lambda c: c in commits) if commits is not None else None)
        names.append(name)
    if commits is None and folders:
        rep.note(a, 'seed commits not checked against History/ (bundle not unpacked: --quick)')
    mt = m.get('tasks')
    if not isinstance(mt, dict):
        rep.error(a, 'layout v1.3 needs manifest tasks {"count": n, "names": [...]}')
    elif sorted(mt.get('names') or []) != names or mt.get('count') != len(names):
        rep.error(a, 'manifest tasks (count, names) differ from Tasks/')
    rep.note(a, f'{len(names)} task(s) (about 10 recommended)')


def run_layout_validator(rep, path, repo_dataset):
    ps = shutil.which('powershell') or shutil.which('pwsh')
    if not ps:
        rep.note('layout', 'PowerShell not found: tools/validate-dataset.ps1 not run')
        return
    args = [ps, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(HERE, 'validate-dataset.ps1'), path]
    if repo_dataset:
        args.append('-RepoDataset')
    r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', env=dict(os.environ, GF_SKIP_CONTENT='1'))
    out = r.stdout.strip().splitlines()
    vl = [l for l in out if re.match(r'^(VALID|PENDING|INVALID) ', l)]
    verdict = vl[0].strip() if vl else f'no verdict (exit {r.returncode}): {r.stderr.strip()[:200]}'
    area = f'layout ({os.path.basename(path)})'
    for line in out:
        s = line.strip()
        if s.startswith('x '):
            rep.error(area, s[2:])
        elif s.startswith('! '):
            rep.note(area, s[2:])   # validate-dataset.ps1: "!" = note
    if r.returncode == 1:
        m = re.search(r'pending: ([^)]+)\)', verdict)
        rep.warn(area, f'PENDING: {m.group(1).strip() if m else "parts"} not there yet')
    rep.note(area, f'validate-dataset.ps1: {verdict}')


# ---- repo ---------------------------------------------------------------------------------------------------------------
def check_repo(rep, repo):
    R = SPEC['repo']
    files = git_ls(repo)
    if not files:
        rep.error('repo', 'not a git repo, or nothing tracked')
        return
    tracked = set(files)
    for req in R['required_files']:
        hits = [f for f in files if re.match(req['pattern'], f)]
        if not hits:
            rep.error('repo', f'missing {req["pattern"]} ({req["what"]})')
        elif req.get('count') and len(hits) != req['count']:
            rep.error('repo', f'{len(hits)} files match {req["pattern"]}, expected {req["count"]}')
    # engine
    for up in [f for f in files if re.match(r'^[^/]+\.uproject$', f)][:1]:
        try:
            assoc = str(json.load(open(os.path.join(repo, up), encoding='utf-8-sig')).get('EngineAssociation'))
            if assoc not in R['engine_associations']:
                rep.error('repo', f'{up}: EngineAssociation {assoc!r} not one of {R["engine_associations"]}')
            else:
                rep.note('repo', f'{up}: engine {assoc}')
        except ValueError as e:
            rep.error('repo', f'{up} is not JSON: {e}')
    # .gitignore
    gi = os.path.join(repo, '.gitignore')
    text = open(gi, encoding='utf-8', errors='replace').read() if os.path.isfile(gi) else ''
    for line in R['gitignore_must_contain']:
        if line not in text.split():
            rep.error('repo: .gitignore', f'missing {line}')
    probe = subprocess.run(['git', '-C', repo, 'check-ignore', '-q', '--no-index', 'Content/_probe_/probe.uasset'])
    if probe.returncode == 0:
        rep.error('repo: .gitignore', 'Content/ is git-ignored: store content and every asset must be committed')
    # Git LFS for binaries
    lfs = set(subprocess.run(['git', '-C', repo, '-c', 'core.quotepath=off', 'lfs', 'ls-files', '--name-only'],
                             capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.splitlines())
    ext_rx = re.compile(r'(?i)\.(' + '|'.join(R['lfs_required_extensions']) + r')$')
    plain = [f for f in files if ext_rx.search(f) and f not in lfs]
    for f in plain[:10]:
        rep.error('repo: LFS', f'binary tracked in plain git: {f}')
    if len(plain) > 10:
        rep.error('repo: LFS', f'... {len(plain) - 10} more binaries in plain git')
    # README images
    if 'README.md' in tracked:
        md = re.sub(r'(?s)<!--.*?-->', '', open(os.path.join(repo, 'README.md'), encoding='utf-8', errors='replace').read())
        links = re.findall(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)', md) + re.findall(r'(?i)<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', md)
        local = []
        for l in links:
            if re.match(r'(?i)^(https?:|data:)', l):
                continue
            p = re.sub(r'^\./|^/', '', l.split('#')[0].split('?')[0]).replace('%20', ' ')
            if p not in local:
                local.append(p)
        for p in local:
            if p not in tracked:
                rep.error('repo: README', f'links {p}, which is not committed')
        imgs = R['readme']['gameplay_images']
        if len(local) < imgs['min']:
            rep.error('repo: README', 'shows no gameplay image')
        elif not imgs['recommended_min'] <= len(local) <= imgs['recommended_max']:
            rep.warn('repo: README', f'{len(local)} images; the rule is a hero + gallery of {imgs["recommended_min"]}-{imgs["recommended_max"]} gameplay stills')
        else:
            rep.note('repo: README', f'{len(local)} images, all committed' if all(p in tracked for p in local) else f'{len(local)} images')
    # banned names in tracked text files (LFS and binaries are scanned by package-game.ps1 -Rescan)
    bn = R['banned_names']
    rxs = [re.compile(p) for p in bn['patterns']]
    labels = list(bn['patterns'])
    exempt = [None] * len(rxs)
    # the account name of this machine (machine paths with it included), read at run time, never written in the repo;
    # not enforced in scripts (account_name.exempt_paths: Scripts/ and script files anywhere), which stay unchanged
    # once they ran and are scrubbed at packaging (user decision b)
    acct = os.environ.get('USERNAME') or os.path.basename(os.path.expanduser('~'))
    if acct and len(acct) >= 4:
        rxs.append(re.compile(r'(?i)(?<![A-Za-z0-9_])' + re.escape(acct) + r'(?![A-Za-z0-9_])'))
        labels.append('the account name')
        exempt.append(re.compile(bn.get('account_name', {}).get('exempt_paths', r'^Scripts/')))
    skip = [re.compile(p) for p in bn['skip_paths']]
    hits = {}
    for f in files:
        if f in lfs or ext_rx.search(f) or any(s.search(f) for s in skip):
            continue
        full = os.path.join(repo, f)
        try:
            if os.path.getsize(full) > 20 * 1024 * 1024:
                continue
            data = open(full, 'rb').read()
        except OSError:
            continue
        if b'\0' in data[:8192]:
            continue
        text = data.decode('utf-8', 'replace')
        for rx, label, ex in zip(rxs, labels, exempt):
            if ex is not None and ex.search(f):
                continue
            n = len(rx.findall(text))
            if n:
                hits.setdefault(f, []).append(f'{label} x{n}')
    for f, h in list(hits.items())[:15]:
        rep.error('repo: banned names', f'{f}: {", ".join(h)}')
    if len(hits) > 15:
        rep.error('repo: banned names', f'... {len(hits) - 15} more files')
    # assets.manifest.json: unified format, every listed file committed under Content/ or RawAssets/
    if 'assets.manifest.json' in tracked:
        try:
            data = json.load(open(os.path.join(repo, 'assets.manifest.json'), encoding='utf-8-sig'))
        except ValueError as e:
            rep.error('repo: assets.manifest.json', f'not JSON: {e}')
            data = None
        if data is not None:
            check_assets_manifest(rep, 'repo: assets.manifest.json', data,
                                  lambda p: any(t.startswith(p) for t in files) if p.endswith('/') else (p in tracked or any(t.startswith(p + '/') for t in files)))
    # workflow.jsonl: same row schema as the dataset copy (the packager rewrites nothing else)
    if 'workflow.jsonl' in tracked:
        with open(os.path.join(repo, 'workflow.jsonl'), encoding='utf-8-sig', errors='replace') as f:
            check_workflow(rep, 'repo: workflow.jsonl', f)
    check_repo_tasks(rep, repo, files)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('repo', nargs='?', help='a game repo (games/<slug>)')
    ap.add_argument('--dataset', help='validate only this dataset (Dataset.zip or a Dataset folder)')
    ap.add_argument('--no-layout', action='store_true', help='skip tools/validate-dataset.ps1')
    ap.add_argument('--content-only', action='store_true', help=argparse.SUPPRESS)  # used by validate-dataset.ps1
    ap.add_argument('--no-zip', action='store_true', help="skip the repo's Dataset.zip")
    ap.add_argument('--json', help='write the findings as JSON')
    ap.add_argument('--quiet', action='store_true', help='print only errors and warnings')
    ap.add_argument('--no-hash', action='store_true', help='skip hashing History/ LFS objects')
    ap.add_argument('--quick', action='store_true', help='skip unpacking the History/ bundle')
    a = ap.parse_args()
    OPTS['hash'] = not a.no_hash
    OPTS['quick'] = a.quick
    if not a.repo and not a.dataset:
        ap.error('give a game repo or --dataset')
    rep = Report()
    targets = []
    if a.dataset:
        targets.append((os.path.abspath(a.dataset), os.path.basename(os.path.normpath(a.dataset)) == 'Dataset'))
    else:
        repo = os.path.abspath(a.repo)
        check_repo(rep, repo)
        ds = os.path.join(repo, 'Dataset')
        if os.path.isfile(os.path.join(ds, 'manifest.json')):
            targets.append((ds, True))
        else:
            rep.warn('dataset', 'Dataset/ has no manifest.json: not packaged yet (tools/package-dataset.ps1)')
        for z in ('Dataset.zip', 'Dataset.pending.zip'):
            if not a.no_zip and os.path.isfile(os.path.join(repo, z)):
                targets.append((os.path.join(repo, z), False))
    for path, repo_ds in targets:
        name = os.path.basename(path) if not repo_ds else 'Dataset/'
        check_dataset(rep, path, f'dataset {name}')
        if not a.no_layout and not a.content_only:
            run_layout_validator(rep, path, repo_ds)
    verdict = 'INVALID' if rep.count('error') else 'VALID'
    print(f'{verdict}  {rep.count("error")} error(s), {rep.count("warning")} warning(s)  [{a.dataset or a.repo}]')
    for sev, area, msg in rep.items:
        if a.quiet and sev == 'note':
            continue
        mark = {'error': 'x', 'warning': '!', 'note': '-'}[sev]
        print(f'  {mark} {area}: {msg}')
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump({'verdict': verdict, 'target': a.dataset or a.repo, 'findings': [dict(severity=s, area=ar, message=m) for s, ar, m in rep.items]}, f, indent=1)
    sys.exit(2 if rep.count('error') else 0)


if __name__ == '__main__':
    main()

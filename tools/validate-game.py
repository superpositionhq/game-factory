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


# ---- a small JSON Schema subset validator (type, required, properties, additionalProperties: false, minProperties,
# ---- enum, const, pattern, minLength, minimum, items, minItems, $ref "#/$defs/...") --------------------------------
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
    # combinators (the task schema uses them: optional fields, check kinds)
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
        if 'minProperties' in schema and len(value) < schema['minProperties']:
            yield f'{path}: needs at least {schema["minProperties"]} key(s)'
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
    # a game without a gameplay video is rejected at upload (user rule 2026-11-10): pending Gameplay/ is never delivered
    if any(str(p).rstrip('/') == 'Gameplay' for p in m['pending']):
        rep.error(a, 'Gameplay/ is pending: a game is rejected without a gameplay video; record a scenario of the release '
                     'commit and package again')
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
            check_sessions(rep, area, v, m)
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
# account names too generic to check as a word (same rule as package-game.ps1 Test-NameTerm)
GENERIC_NAMES = ('dev', 'devs', 'developer', 'user', 'users', 'admin', 'administrator', 'root', 'test', 'tester', 'guest', 'owner',
                 'default', 'build', 'builder', 'player', 'unknown', 'noreply', 'github', 'author', 'agent', 'claude', 'codex',
                 'anthropic', 'openai', 'studio', 'home', 'work', 'game', 'local', 'public')


def git_out(*args, input=None):
    r = subprocess.run(['git', *args], capture_output=True, input=input)
    if r.returncode != 0:
        raise RuntimeError(f'git {" ".join(args[:3])}: {r.stderr.decode("utf-8", "replace").strip()[:200]}')
    return r.stdout


def check_sessions(rep, area, v, m):
    """Full variant: History/sessions/, the creation sessions as recorded: messages.jsonl (every prompt the person
    typed and every reply the model wrote) and actions.jsonl (every tool call), one JSON row per line. Games recorded
    before prompts and replies were have no messages.jsonl; nothing here is an error."""
    a = f'{area}: History/sessions'
    files = {'messages.jsonl': ('role', 'text'), 'actions.jsonl': ('event',)}
    stray = sorted(r for r in v.names if r.startswith('History/sessions/') and r[len('History/sessions/'):] not in files)
    if stray:
        rep.warn(a, f'{len(stray)} file(s) that are not messages.jsonl or actions.jsonl, e.g. {stray[0]}')
    listed = (m.get('history') or {}).get('sessions') or {}
    for name, keys in files.items():
        rel = f'History/sessions/{name}'
        if not v.has(rel):
            rep.note(a, f'no {name}' + (': the prompts and replies of the creation sessions are not in this dataset'
                                        if name == 'messages.jsonl' else ''))
            continue
        rows, bad, raw_ids, sessions, roles = 0, 0, 0, set(), {}
        with v.open_text(rel) as f:
            for line in f:
                if not line.strip():
                    continue
                rows += 1
                try:
                    r = json.loads(line)
                except ValueError:
                    r = None
                if not isinstance(r, dict) or not all(isinstance(r.get(k), str) for k in ('time', 'session_id') + keys):
                    bad += 1
                    continue
                sessions.add(r['session_id'])
                if re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', r['session_id']):
                    raw_ids += 1
                if name == 'messages.jsonl':
                    roles[r['role']] = roles.get(r['role'], 0) + 1
        if bad:
            rep.warn(a, f'{name}: {bad} of {rows} row(s) are not a JSON object with {", ".join(("time", "session_id") + keys)}')
        if raw_ids:
            rep.warn(a, f"{name}: {raw_ids} row(s) carry the build machine's session id, not session_NN")
        if name == 'messages.jsonl' and set(roles) - {'user', 'assistant', 'thinking'}:
            rep.warn(a, f'{name}: roles other than user, assistant and thinking: {", ".join(sorted(set(roles) - {"user", "assistant", "thinking"}))}')
        want = (listed.get(name[:-len('.jsonl')]) or {}).get('rows') if isinstance(listed, dict) else None
        if want is not None and want != rows:
            rep.warn(a, f'{name}: {rows} row(s), manifest.json history.sessions says {want}')
        detail = f'{roles.get("user", 0)} prompt(s), {roles.get("assistant", 0)} repl(ies), {roles.get("thinking", 0)} reasoning summar(ies)' if name == 'messages.jsonl' else f'{rows} row(s)'
        rep.note(a, f'{name}: {detail} in {len(sessions)} session(s)')


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


# A task play's command-line flags (docs/task-probes.md, section 1.1): never the checker's own.
PLAY_ARG = re.compile(r'^-([A-Za-z][A-Za-z0-9]{0,40})(=[A-Za-z0-9_.:=,-]{1,60})?$')
DENIED_PLAY_ARGS = {'execcmds', 'run', 'nullrhi', 'log', 'unattended', 'renderoffscreen', 'resx', 'resy', 'benchmark',
                    'fps', 'game', 'windowed'}
TASK_PLAY_DEFAULTS = {'inputs': [], 'map': None, 'args': [], 'every': None}


PIECE_TRIANGLES = ('triangles', 'visible_triangles')  # pieces fields whose threshold is never a literal
# fields whose threshold is never a literal: how bright a light, how big a component's bounds, how far apart an actor's
# parts, how far an object's bounds or pose moved, how much light it gives off, how loud a sound, how much the ground
# rises and falls, how fast a part spins, and what is drawn in a place (how much of it changes, its colour, how far
# along a line) depend on what a build chose (docs/task-probes.md)
NEVER_LITERAL = {'components': ('intensity', 'extent_x', 'extent_y', 'extent_z', 'bounds_change', 'pose_change', 'glow',
                                'spin'),
                 'actors': ('spread', 'bounds_change', 'pose_change', 'glow', 'spin'),
                 'audio': ('volume', 'max_volume'), 'ground': ('range',),
                 'drawn': ('motion', 'base_r', 'base_g', 'base_b', 'base_change', 'reach', 'length')}
GROUND_POINT = ('height', 'hit')        # a ground measure at a point `xy`
GROUND_BOX = ('min', 'max', 'mean', 'range', 'hits')   # a ground measure over a `box`
UI_SIGNATURE_AGGS = ('changes', 'any', 'all', 'count')  # a ui signature's value means nothing; whether it changes does
DRAWN_NEAR = ('drawn', 'motion', 'base_r', 'base_g', 'base_b', 'base_change')  # a drawn measure near a point
DRAWN_LINE = ('drawn', 'reach', 'length')    # a drawn measure along a line
WAITS = 300   # seconds of real time a task play's waits add at most
JUDGE_PLAY_SHOTS = 5   # the screenshots a judge check is shown of each of its own plays, unless its `shots` says
JUDGE_SHOTS = 20       # the screenshots a judge check is shown at most: its plays times its shots


def nears(o):
    """Every `near` inside `o` (a measure, a play's inputs), wherever it is nested."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'near' and isinstance(v, dict):
                yield v
            yield from nears(v)
    elif isinstance(o, list):
        for v in o:
            yield from nears(v)


def component_selects(measure):
    """The components selects of a measure (its own when it reads components)."""
    if measure.get('probe') == 'components' and isinstance(measure.get('select'), dict):
        yield measure['select']


def near_errors(n, o):
    """The height-band rules of every `near` inside `o`, for check `n`: z_min < z_max, and `z_relative` only with one of
    them."""
    errs = []
    for near in nears(o):
        lo, hi = near.get('z_min'), near.get('z_max')
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and not lo < hi:
            errs.append(f'check {n}: a near band has z_min < z_max')
        if near.get('z_relative') and lo is None and hi is None:
            errs.append(f'check {n}: `z_relative` goes with z_min or z_max')
    return errs


def named_shots(play):
    """The names of the screenshots a task play's `shot` inputs take."""
    return [i['shot'] for i in play.get('inputs') or [] if isinstance(i, dict) and isinstance(i.get('shot'), str)]


def task_play_errors(n, play, plays):
    """A task play's rules beyond the schema, for check `n` (a probe's `play`, a judge's `plays`): not named
    look/drive/editor/trace, no input at or after its end, no grader flag, waits of at most 300 s in all, its named
    shots each named once (20 at most), a view's pitch within -89 to 89, and identical to every other task play of its
    name in the task (`plays`: those seen so far, by name)."""
    errs, pname = [], play.get('name')
    if pname in ('look', 'drive', 'editor', 'trace'):
        errs.append(f"check {n}: a task play can't be named {pname}")
    secs = play.get('seconds')
    if isinstance(secs, (int, float)) and any(isinstance(i, dict) and isinstance(i.get('t'), (int, float))
                                              and i['t'] >= secs for i in play.get('inputs') or []):
        errs.append(f'check {n}: play {pname} has an input at or after its end ({secs} s)')
    for arg in play.get('args') or []:
        mm = PLAY_ARG.match(arg) if isinstance(arg, str) else None
        # the engine reads `Name=` anywhere on its command line, so a `Name=` inside a value sets a flag too
        names = ([mm.group(1)] + re.findall(r'([A-Za-z][A-Za-z0-9]*)=', arg.split('=', 1)[1] if '=' in arg else '')
                 if mm else [])
        for name in (x for x in names if x.lower() in DENIED_PLAY_ARGS or x.lower().startswith('taskprobe')):
            errs.append(f"check {n}: a task play can't set -{name}")
    waits = sum(i['wait'] for i in play.get('inputs') or []
                if isinstance(i, dict) and isinstance(i.get('wait'), (int, float)))
    if waits > WAITS:
        errs.append(f'check {n}: play {pname} waits {waits:g} s in all, more than {WAITS} s')
    shots = named_shots(play)
    if len(shots) != len(set(shots)):
        errs.append(f'check {n}: play {pname} names a shot twice')
    if len(shots) > JUDGE_SHOTS:
        errs.append(f'check {n}: play {pname} takes {len(shots)} named shots, more than {JUDGE_SHOTS}')
    for i in play.get('inputs') or []:
        view = i.get('view') if isinstance(i, dict) else None
        if isinstance(view, list) and len(view) == 2 and all(isinstance(v, (int, float)) for v in view) and not (
                -89 <= view[0] <= 89 and -360 <= view[1] <= 360):
            errs.append(f'check {n}: play {pname} has a view {view}: [pitch, yaw], pitch -89 to 89, yaw -360 to 360')
    for i in play.get('inputs') or []:
        if not isinstance(i, dict):
            continue
        if isinstance(i.get('pin'), dict) and i['pin'].get('player') is True:
            errs.append(f'check {n}: play {pname} pins the player: a pin holds another actor (a teleport holds the player)')
        if 'pin' in i and i.get('front') is not None and i.get('at') is not None:
            errs.append(f'check {n}: play {pname} pins an actor `front` of the player or `at` a point, not both')
        over, t = i.get('over'), i.get('t')
        if 'move' in i and isinstance(over, (int, float)) and isinstance(t, (int, float)) and isinstance(secs, (int, float)) \
                and t + over > secs:
            errs.append(f'check {n}: play {pname} has a mouse movement that ends after the play ({secs} s)')
    whole = dict(TASK_PLAY_DEFAULTS, **play)
    if plays.setdefault(pname, whole) != whole:
        errs.append(f'check {n}: task play {pname} differs from another play of that name')
    return errs


def probe_errors(c, seed, ref, plays):
    """A probe check's rules beyond the schema (docs/task-probes.md):
    asset measures only with play "editor" and trace measures only with play "trace"; an asset measure's select takes
    no `has`; a trace probe never gates and
    takes a literal value; a task play is not named look/drive/editor/trace, has no input at or after its end, sets no
    grader flag, and same-named task plays are identical; == and != take a literal value; a screen measure's threshold
    is calibrated or relative to the start (the frame's luminance moves between machines), and so is a pieces measure's
    triangles (they depend on the meshes a build chose) and every NEVER_LITERAL field; a ground measure takes a point
    `xy` or a `box` and the fields of that one; a drawn measure takes `near` or a `line` and the fields of that one;
    a components select names its class or `effect`; a near's height band has z_min < z_max and `z_relative` only
    with one of them; a task play's waits add at most 300 s; a ui measure takes `match` exactly when it reads text,
    `agg` changes, any, all or count when it reads its signature, regular
    expressions that compile and a select rect [x0, y0, x1, y1] with x0 < x1 and y0 < y1; a calibrated threshold needs
    seed.reference and a start-relative one a seed."""
    errs, n = [], c.get('name')
    play = c.get('play')
    measure = c.get('measure') if isinstance(c.get('measure'), dict) else {}
    expect = c.get('expect') if isinstance(c.get('expect'), dict) else {}
    probe = measure.get('probe')
    pname = play if isinstance(play, str) else (play.get('name') if isinstance(play, dict) else None)
    if (probe == 'asset') != (pname == 'editor'):
        errs.append(f'check {n}: asset measures are taken by the editor pass (play "editor"), and it takes nothing else')
    if (probe == 'trace') != (pname == 'trace'):
        errs.append(f'check {n}: trace measures are read from the trace (play "trace"), and it gives nothing else')
    if probe == 'asset' and isinstance(measure.get('select'), dict) and measure['select'].get('has') is not None:
        errs.append(f'check {n}: a map as saved is read without its components drawn, so its select takes no `has`')
    rel = 'calibrate' if 'calibrate' in expect else ('start' if 'start_times' in expect or 'start_plus' in expect else None)
    if probe == 'trace' and (c.get('required', True) or rel):
        errs.append(f'check {n}: a trace probe never gates (required: false) and takes a literal value')
    if isinstance(play, dict):
        errs.extend(task_play_errors(n, play, plays))
    if probe == 'screen' and not rel:
        errs.append(f"check {n}: the frame's luminance moves between machines, so a screen measure's threshold is "
                    'calibrated or relative to the start, never a literal value')
    if probe == 'pieces' and measure.get('field') in PIECE_TRIANGLES and not rel:
        errs.append(f'check {n}: how many triangles a fair build draws depends on the meshes it chose, so a pieces '
                    "measure's triangles threshold is calibrated or relative to the start, never a literal value")
    if measure.get('field') in NEVER_LITERAL.get(probe, ()) and not rel:
        errs.append(f"check {n}: a {probe} measure's {measure.get('field')} depends on what a build chose, so its "
                    'threshold is calibrated or relative to the start, never a literal value')
    if probe == 'ground':
        xy, box, field = measure.get('xy'), measure.get('box'), measure.get('field')
        if (xy is None) == (box is None):
            errs.append(f'check {n}: a ground measure takes a point `xy` or a `box`, one of them')
        elif xy is not None and field not in GROUND_POINT:
            errs.append(f"check {n}: a ground measure at a point reads {', '.join(GROUND_POINT)}")
        elif box is not None and field not in GROUND_BOX:
            errs.append(f"check {n}: a ground measure over a box reads {', '.join(GROUND_BOX)}")
        elif box is not None and isinstance(box, list) and len(box) == 4 and not (box[0] < box[2] and box[1] < box[3]):
            errs.append(f'check {n}: a ground box is [x0, y0, x1, y1] with x0 < x1 and y0 < y1')
    if probe == 'drawn':
        near, line, field = measure.get('near'), measure.get('line'), measure.get('field')
        if (near is None) == (line is None):
            errs.append(f'check {n}: a drawn measure takes `near` (a point) or a `line`, one of them')
        elif near is not None and field not in DRAWN_NEAR:
            errs.append(f"check {n}: a drawn measure near a point reads {', '.join(DRAWN_NEAR)}")
        elif line is not None and field not in DRAWN_LINE:
            errs.append(f"check {n}: a drawn measure along a line reads {', '.join(DRAWN_LINE)}")
    for sel in component_selects(measure):
        if sel.get('class') is None and sel.get('effect') is None:
            errs.append(f'check {n}: a components select names its class, or `effect`')
    errs.extend(near_errors(n, [measure, play.get('inputs') if isinstance(play, dict) else None]))
    if probe == 'ui':
        sel = measure.get('select') if isinstance(measure.get('select'), dict) else {}
        if (measure.get('field') == 'text') != (measure.get('match') is not None):
            errs.append(f'check {n}: a ui measure takes `match` exactly when its field is text')
        if measure.get('field') == 'signature' and measure.get('agg') not in UI_SIGNATURE_AGGS:
            errs.append(f'check {n}: a ui signature is read with `agg` changes, any, all or count')
        for pattern in (measure.get('match'), sel.get('text')):
            try:
                re.compile(pattern) if isinstance(pattern, str) else None
            except re.error as e:
                errs.append(f"check {n}: {pattern!r} isn't a regular expression ({e})")
        rect = sel.get('rect')
        if isinstance(rect, list) and len(rect) == 4 and not (rect[0] < rect[2] and rect[1] < rect[3]):
            errs.append(f'check {n}: a ui select rect is [x0, y0, x1, y1] with x0 < x1 and y0 < y1')
        if sel.get('text') is not None and sel.get('kind') not in (None, 'text'):
            errs.append(f"check {n}: a ui select's `text` picks text elements: its kind is text or unset")
    if rel and expect.get('op') in ('==', '!='):
        errs.append(f'check {n}: == and != take a literal value, never a calibrated threshold')
    if rel == 'calibrate' and not ref:
        errs.append(f"check {n} calibrates against a reference the task's seed doesn't name")
    if rel == 'start' and not seed:
        errs.append(f'check {n} sets its threshold from the start, which only a seeded task has')
    return errs


def task_semantic_errors(t):
    """What the schema cannot say (the task format's own rules): check names unique, `needs` naming earlier
    checks, a code judge or a reference judge only with seed.reference, a before/after judge only with a seed, a judge's
    own `plays` each named once in the check and under a task play's rules (task_play_errors), its `shots` only with
    plays of its own and its plays times its shots 20 at most, and the
    probe rules (probe_errors); and a task whose start doesn't build (a build check's `fails_at_start`) has nothing
    that needs the start played: no start-relative threshold, no before/after judge (docs/task-probes.md, 3.1)."""
    errs, seen, plays = [], set(), {}
    seed = t.get('seed') if isinstance(t.get('seed'), dict) else None
    ref = seed.get('reference') if seed else None
    checks = [c for m in t.get('milestones') or [] if isinstance(m, dict) for c in m.get('checks') or []
              if isinstance(c, dict)]
    broken = next((c.get('name') for c in checks if c.get('kind') == 'build' and c.get('fails_at_start') is True), None)
    for m in t.get('milestones') or []:
        for c in (m.get('checks') or []) if isinstance(m, dict) else []:
            if not isinstance(c, dict):
                continue
            n, k = c.get('name'), c.get('kind')
            if k == 'probe':
                errs.extend(probe_errors(c, seed, ref, plays))
                expect = c.get('expect') if isinstance(c.get('expect'), dict) else {}
                relative = [x for x in ('calibrate', 'start_times', 'start_plus') if x in expect]
                if broken and relative:
                    errs.append(f"check {n}: its threshold is relative to the start ({relative[0]}), but the start "
                                f"doesn't build ({broken}: fails_at_start), so it is never played; use a literal value")
            if k == 'judge' and c.get('before') and broken:
                errs.append(f"check {n} compares with the start (before: true), but the start doesn't build "
                            f"({broken}: fails_at_start), so it is never played")
            if k == 'judge':
                own = [p for p in c.get('plays') or [] if isinstance(p, dict)]
                if len({p.get('name') for p in own}) != len(own):
                    errs.append(f'judge check {n} names a play twice')
                for p in own:
                    errs.extend(task_play_errors(n, p, plays))
                    errs.extend(near_errors(n, p.get('inputs')))
                shots = c.get('shots', JUDGE_PLAY_SHOTS)
                if shots != JUDGE_PLAY_SHOTS and not own:
                    errs.append(f'judge check {n} sets shots but names no play of its own to take them in')
                named = sum(len(named_shots(p)) for p in own)
                if isinstance(shots, int) and len(own) * shots + named > JUDGE_SHOTS:
                    errs.append(f"judge check {n} asks {len(own)} plays of {shots} screenshots"
                                + (f' and {named} named ones' if named else '') + f": more than a judge's {JUDGE_SHOTS}")
            if k == 'code_judge' and not ref:
                errs.append(f'check {n}: a code judge needs seed.reference')
            if k == 'judge' and c.get('before') and not seed:
                errs.append(f'check {n}: a before/after judge needs a seed')
            if k == 'judge' and c.get('reference') and not ref:
                errs.append(f'check {n}: a reference judge needs seed.reference')
            if n in seen:
                errs.append(f'check {n} is named twice')
            missing = [x for x in (c.get('needs') or []) if x not in seen]
            if missing:
                errs.append(f'check {n} needs {missing}, which come later or do not exist')
            seen.add(n)
    return errs


# The bar every task meets (owner, 2026-11-02): only long threads of multiple edits qualify (write-tasks sections 1, 6)
MIN_OUTCOME_PROBES = 3     # required probes outside still_works: one per issue the thread settled
MIN_THREAD_FILES = 5       # game files the reference changes against the start
MIN_THREAD_COMMITS = 4     # commits from seed.commit to seed.reference that change the game (a seed on main)
MIN_THREAD_CODE_LINES = 100   # code lines added plus removed from start to reference (owner, 2026-11-09; was 300)
MIN_THREAD_SYSTEMS = 2        # systems the change crosses, as thread_size counts them (owner, 2026-11-04)
CODE_FILE = re.compile(r'\.(cpp|h|hpp|c|cc|inl|cs|py|ps1|bat|cmd|sh|js|hlsl|usf|ush)$', re.I)
NOT_CODE_DIR = re.compile(r'^(Dataset|Docs|RawAssets|Content)/')
GAME_FILE = re.compile(r'^(Source|Content|Config|Plugins)/|\.uproject$')
GAME_PATHS = ('Source', 'Content', 'Config', 'Plugins', '*.uproject')   # the game itself, not its records or docs


def thread_errors(t, outcomes):
    """Why task `t` (with `outcomes` required probes outside still_works) is not a long thread, from the task alone."""
    errs = []
    if t.get('difficulty') == 'easy':
        errs.append('difficulty \'easy\': a task is "hard" (one of a game\'s may be "medium")')
    if 'long-thread' not in (t.get('tags') or []):
        errs.append('no long-thread tag')
    if not (isinstance(t.get('seed'), dict) and t['seed'].get('reference')):
        errs.append("no seed.reference: every task ends at the game's own accepted fix of the thread")
    if outcomes < MIN_OUTCOME_PROBES:
        errs.append(f'{outcomes} required outcome probe(s) outside still_works, fewer than {MIN_OUTCOME_PROBES}')
    return errs + noop_errors(t)


def noop_errors(t):
    """Why a no-op would earn something, from the task alone: a no-op scores zero (owner, 2026-11-04). The score is the
    weighted share of checks passed, so what is true of the start takes `"weight": 0`. The task check measures the rest."""
    errs, earning = [], 0
    for m in t.get('milestones') or []:
        for c in (m.get('checks') or []) if isinstance(m, dict) else []:
            if not isinstance(c, dict):
                continue
            kind, weight = c.get('kind'), c.get('weight', 1)
            passes_at_start = (kind == 'build' and not c.get('fails_at_start')) or kind == 'boot' \
                or m.get('name') == 'still_works'
            if passes_at_start and weight != 0:
                errs.append(f'check {c.get("name")}: a no-op passes it, so a no-op would score; give it "weight": 0')
            elif not passes_at_start and c.get('required', True) and kind in ('probe', 'build') and weight > 0:
                earning += 1
    if not earning:
        errs.append('no required outcome check carries weight, so no run can score')
    return errs


def thread_system(path):
    """Which system a changed game file belongs to, by its path and name prefix."""
    low = path.lower()
    if path.startswith('Source/'):
        return 'cpp'
    if path.startswith('Config/') or path.endswith('.uproject'):
        return 'config'
    if path.startswith('Plugins/'):
        return 'plugin'
    if low.endswith('.umap'):
        return 'level'
    name = low.rsplit('/', 1)[-1]
    if name.startswith(('m_', 'mi_', 'mf_', 't_')):
        return 'material'
    if name.startswith(('wbp_', 'bp_', 'abp_', 'ui_')):
        return 'blueprint'
    if name.startswith(('da_', 'dt_')):
        return 'data'
    return 'asset'


def thread_size(numstat):
    """(code lines, systems) from `git diff --numstat --no-renames`. Binary files and assets never count as code lines;
    assets do count as systems."""
    lines, systems = 0, set()
    for row in numstat.splitlines():
        parts = row.split('\t')
        if len(parts) != 3:
            continue
        added, removed, path = parts
        if GAME_FILE.search(path):
            systems.add(thread_system(path))
        if added.isdigit() and removed.isdigit() and CODE_FILE.search(path) and not NOT_CODE_DIR.search(path):
            lines += int(added) + int(removed)
    return lines, len(systems)


MIN_TASKS = 5          # a game with fewer tasks is rejected (user rule 2026-11-10)
MAX_MEDIUM_TASKS = 1   # every task is hard; this many may be medium, none easier (user rule 2026-11-10)


def task_bar_errors(levels):
    """Why a game's tasks ({name: its difficulty or None}) miss the bar a game is accepted at: at least MIN_TASKS tasks,
    all hard but for at most MAX_MEDIUM_TASKS medium ones. A task that names no difficulty is medium, the format's
    default."""
    errs = []
    if len(levels) < MIN_TASKS:
        errs.append(f'{len(levels)} task(s): a game ships at least {MIN_TASKS}')
    level = {n: d or 'medium' for n, d in levels.items()}
    errs += [f'{n}: difficulty {d!r}: a task is "hard"' for n, d in sorted(level.items()) if d not in ('medium', 'hard')]
    medium = sorted(n for n, d in level.items() if d == 'medium')
    if len(medium) > MAX_MEDIUM_TASKS:
        errs.append(f'{len(medium)} medium tasks ({", ".join(medium)}): at most {MAX_MEDIUM_TASKS} of a game\'s tasks may be '
                    'medium, the rest are hard')
    return errs


def thread_span_errors(repo, seed, on_main):
    """Why the span from seed.commit to seed.reference is too short: game files changed, and on main the commits."""
    start, ref = seed.get('commit'), seed.get('reference')
    if not (start and ref):
        return []
    errs = []
    files = [p for p in _git(repo, '-c', 'core.quotepath=off', 'diff', '--name-only', start, ref, '--', *GAME_PATHS)
             .stdout.decode('utf-8', 'replace').splitlines() if p.strip()]
    if len(files) < MIN_THREAD_FILES:
        errs.append(f'the reference changes {len(files)} game file(s) against the start, fewer than {MIN_THREAD_FILES}')
    lines, systems = thread_size(_git(repo, '-c', 'core.quotepath=off', 'diff', '--numstat', '--no-renames', start, ref)
                                 .stdout.decode('utf-8', 'replace'))
    if lines < MIN_THREAD_CODE_LINES:
        errs.append(f'the reference changes {lines} code line(s) against the start, fewer than {MIN_THREAD_CODE_LINES}')
    if systems < MIN_THREAD_SYSTEMS:
        errs.append(f'the reference crosses {systems} system(s), fewer than {MIN_THREAD_SYSTEMS}')
    if on_main:
        n = _git(repo, 'rev-list', '--count', f'{start}..{ref}', '--', *GAME_PATHS).stdout.decode().strip()
        if int(n or 0) < MIN_THREAD_COMMITS:
            errs.append(f'{n or 0} commit(s) change the game from seed.commit to seed.reference, '
                        f'fewer than {MIN_THREAD_COMMITS}')
    return errs


def required_quality_judges(t):
    """The required judge checks that should be optional quality checks: every required judge but the ones covering
    the brief's looks, a `judge` named `looks_as_asked` and a `judge` in the `still_works` milestone."""
    return [c.get('name') for m in t.get('milestones') or [] if isinstance(m, dict) for c in m.get('checks') or []
            if isinstance(c, dict) and c.get('kind') in ('judge', 'code_judge', 'actions_judge')
            and c.get('required', True) and not (c.get('kind') == 'judge' and (
                c.get('name') == 'looks_as_asked' or m.get('name') == 'still_works'))]


def check_task(rep, a, label, t, game, has_commit):
    """One whole task (GameTask): schema, the format's extra rules, seed on `game` and on known commits."""
    for e in list(check_schema(t, SCHEMAS['game-task']))[:5]:
        rep.error(a, f'{label}: {e}')
    for e in task_semantic_errors(t)[:5]:
        rep.error(a, f'{label}: {e}')
    gated = [c for m in t.get('milestones') or [] if isinstance(m, dict) for c in m.get('checks') or []
             if isinstance(c, dict) and c.get('kind') == 'probe' and c.get('required', True)]
    judged = required_quality_judges(t)
    if not gated:
        rep.error(a, f'{label}: no required probe check: pass/fail must be deterministic (write-tasks section 5)')
    outcomes = [c for m in t.get('milestones') or [] if isinstance(m, dict) and m.get('name') != 'still_works'
                for c in m.get('checks') or [] if isinstance(c, dict) and c.get('kind') == 'probe'
                and c.get('required', True)]
    for e in thread_errors(t, len(outcomes)):
        rep.error(a, f'{label}: {e} (write-tasks section 1: only long threads of multiple edits)')
    if judged:
        rep.note(a, f'{label}: required judge check(s) {judged}: only a judge of the brief\'s looks is required '
                    '(`looks_as_asked`, or a judge in `still_works`); other judges should be "required": false '
                    'quality checks')
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
    each, name = file stem, seeds on commits of main's history (ancestors of HEAD, the main branch in a game checkout)
    or of the task's own start branch `starts/<name>` (write-tasks section 2), each a project of ENGINE as committed.
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
    known, current, levels = {}, {'stem': ''}, {}

    def has_commit(c):   # an ancestor of main's head, or of the task's own start branch
        key = (c, current['stem'])
        if key not in known:
            tips = ['HEAD'] + [r for r in (f'refs/heads/starts/{current["stem"]}', f'refs/remotes/origin/starts/{current["stem"]}')
                               if _git(repo, 'rev-parse', '--verify', '-q', r).returncode == 0]
            known[key] = any(_git(repo, 'merge-base', '--is-ancestor', c, tip).returncode == 0 for tip in tips)
        return known[key]
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
        current['stem'] = stem
        levels[stem] = t.get('difficulty') if isinstance(t.get('difficulty'), str) else None
        check_task(rep, a, label, t, game, has_commit)
        seed = t.get('seed') if isinstance(t.get('seed'), dict) else {}
        for k in ('commit', 'reference'):
            if seed.get(k) and has_commit(seed[k]):
                engine = start_engine(repo, seed[k])
                if engine != ENGINE:
                    rep.error(a, f'{label}: seed.{k} {seed[k][:12]} is a UE {engine or "?"} project: a task starts from a '
                                 f'commit that builds on UE {ENGINE} as committed (never ported; write-tasks section 2)')
        if all(seed.get(k) and has_commit(seed[k]) for k in ('commit', 'reference')):
            on_main = all(_git(repo, 'merge-base', '--is-ancestor', seed[k], 'HEAD').returncode == 0
                          for k in ('commit', 'reference'))
            for e in thread_span_errors(repo, seed, on_main):
                rep.error(a, f'{label}: {e} (write-tasks section 1: only long threads of multiple edits)')
            for check, name in reference_only_names(repo, t):
                rep.error(a, f'{label}: check {check} names {name}, which only the reference has: another fair build '
                             'names it otherwise; select by what it does or where it is (write-tasks section 5)')
    for e in task_bar_errors(levels):
        rep.error(a, f'{ref}: {e} (write-tasks section 1)')
    rep.note(a, f'{len(paths)} task(s) on {ref} (at least {MIN_TASKS}, up to about 10, every one a long thread)')


# What a probe names: the class, tag, name, mesh and asset path keys of its selects (owner selects and `has` included)
# and the asset/map paths of its measure and play. A name that exists in the reference and not at the start can only be
# matched by a build that chose the reference's names; another fair build reads as absent (write-tasks section 5).
NAMED_KEYS = ('class', 'tag', 'name', 'mesh', 'slate')
PATH_KEYS = ('asset', 'map')


def probe_names(c):
    """The literal names and /Game paths a probe check depends on (wildcards skipped: they match by pattern)."""
    names, paths = set(), set()

    def walk(v, key=None):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)
        elif isinstance(v, str) and key in PATH_KEYS and v.startswith('/Game/'):
            path = v.split('?', 1)[0].split('.', 1)[0]   # a map's URL options and an object's .Name left out
            if not any(ch in path for ch in '*?'):
                paths.add(path)
        elif isinstance(v, str) and not any(ch in v for ch in '*?'):
            if key in NAMED_KEYS and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{2,120}', v):
                names.add(re.sub(r'_C$', '', v))   # a Blueprint's generated class names its asset

    walk(c.get('measure'))
    play = c.get('play')
    if isinstance(play, dict):
        walk({'map': play.get('map')})
        for i in play.get('inputs') or []:
            if isinstance(i, dict):
                walk(i.get('teleport_to'))
    return names, paths


def _has_name(repo, commit, name, tree):
    """Whether `name` shows at `commit`: as a file name in its tree, or in a text file under Source/ or Config/."""
    if any(re.search(rf'(^|/){re.escape(name)}(\.|$)', p) for p in tree):
        return True
    return _git(repo, 'grep', '-q', '-I', '-w', '-F', name, commit, '--', 'Source', 'Config').returncode == 0


def reference_only_names(repo, t):
    """[(check, name)] of required probes that name something the reference has and the start doesn't (a class, tag,
    widget, component, mesh, map or asset the thread itself created). Engine names are in neither tree and pass."""
    seed = t.get('seed') if isinstance(t.get('seed'), dict) else {}
    start, ref = seed.get('commit'), seed.get('reference')
    if not (start and ref):
        return []
    trees = {k: _git(repo, '-c', 'core.quotepath=off', 'ls-tree', '-r', '--name-only', k).stdout.decode('utf-8', 'replace')
             .splitlines() for k in (start, ref)}
    found, cache = [], {}
    for m in t.get('milestones') or []:
        for c in (m.get('checks') or []) if isinstance(m, dict) else []:
            if not (isinstance(c, dict) and c.get('kind') == 'probe' and c.get('required', True)):
                continue
            names, paths = probe_names(c)
            for p in sorted(paths):
                rel = 'Content/' + p[len('/Game/'):] + '.'
                if any(x.startswith(rel) for x in trees[ref]) and not any(x.startswith(rel) for x in trees[start]):
                    found.append((c.get('name'), p))
            for n in sorted(names):
                if n not in cache:
                    cache[n] = (_has_name(repo, ref, n, trees[ref]), _has_name(repo, start, n, trees[start]))
                if cache[n][0] and not cache[n][1]:
                    found.append((c.get('name'), n))
    return found


ENGINE = '5.7'   # the checker's engine: it builds a start exactly as committed


def start_engine(repo, commit):
    """The EngineAssociation of the .uproject at the root of `commit` ('' when there is none)."""
    names = _git(repo, 'ls-tree', '--name-only', commit).stdout.decode('utf-8', 'replace').split()
    up = next((n for n in names if n.endswith('.uproject')), None)
    if not up:
        return ''
    try:
        return str(json.loads(_git(repo, 'show', f'{commit}:{up}').stdout.decode('utf-8-sig')).get('EngineAssociation', ''))
    except ValueError:
        return ''


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
    names, levels = [], {}
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
        levels[name] = whole.get('difficulty') if isinstance(whole.get('difficulty'), str) else None
    for e in task_bar_errors(levels):
        rep.error(a, f'Tasks/: {e}')
    if commits is None and folders:
        rep.note(a, 'seed commits not checked against History/ (bundle not unpacked: --quick)')
    mt = m.get('tasks')
    if not isinstance(mt, dict):
        rep.error(a, 'layout v1.3 needs manifest tasks {"count": n, "names": [...]}')
    elif sorted(mt.get('names') or []) != names or mt.get('count') != len(names):
        rep.error(a, 'manifest tasks (count, names) differ from Tasks/')
    rep.note(a, f'{len(names)} task(s) (at least {MIN_TASKS}; about 10 recommended)')


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
    if acct and len(acct) >= 4 and acct.lower() not in GENERIC_NAMES:   # a generic one ("admin") is the game's own word
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
    check_rules(rep, repo, files)


def check_rules(rep, repo, files):
    """The game contract and the sound rule (the owner's decisions of 2026-11-11): every game not yet submitted, a
    game in progress too, meets them before it is packaged; games already approved in the Lab are not re-validated."""
    check_contract(rep, repo, files)
    check_sound(rep, repo, files)


# ---- the contract on a game with combat (Lab docs/planning/2026-11-11_game-contact-checks/spec.md section 11.1):
# ---- damage through the engine's damage interface, key gameplay state in reflected UPROPERTY members -----------------
HEALTH_WORDS = {'health', 'hp', 'hitpoints', 'hull', 'poise', 'armor', 'armour'}
STATE_WORDS = {'shield', 'stamina', 'mana', 'lives', 'dead', 'alive', 'dying', 'stun', 'stunned', 'stagger', 'staggered',
               'invulnerable', 'invincible', 'guard', 'guarding', 'blocking', 'parry', 'parrying', 'alert', 'aggro',
               'awake', 'asleep', 'dormant', 'roused'}
WHOLE_WORDS = {'phase', 'state'}  # only on whole-number or enum members
# a member about how state is shown or heard, not the state itself (a HUD's last shown health, a hit sound's throttle)
SHOWN_WORDS = {'sound', 'sfx', 'audio', 'fx', 'vfx', 'shown', 'display', 'shake'}
# a UI class keeps copies of state to draw it; the state itself lives on the actor
UI_CLASS = re.compile(r'\b(?:UUserWidget|UWidget|AHUD|SCompoundWidget|SLeafWidget|SWidget)\b|\b\w*(?:Hud|HUD|Widget)\w*\s*(?::|$)')
NUMBER_TYPES = re.compile(r'^(?:float|double|bool|int|unsigned|uint8|uint16|uint32|uint64|int8|int16|int32|int64|'
                          r'unsigned int|E[A-Z]\w*|TEnumAsByte<\s*E\w*\s*>|uint8\s*:\s*1)$')
WHOLE_TYPES = re.compile(r'^(?:int|unsigned|uint8|uint16|uint32|uint64|int8|int16|int32|int64|E[A-Z]\w*|'
                         r'TEnumAsByte<\s*E\w*\s*>)$')
HIT_FUNCTION = re.compile(r'\b(?:Take|Receive|Apply|Deal)(?:Hit|Hurt|Damage)\w*\s*\(')
ENGINE_DAMAGE = {'TakeDamage', 'ApplyDamage', 'ApplyPointDamage', 'ApplyRadialDamage', 'ApplyRadialDamageWithFalloff',
                 'ReceiveAnyDamage', 'ReceivePointDamage', 'ReceiveRadialDamage'}
RECEIVES = re.compile(r'\bTakeDamage\s*\([^;{]*\)\s*(?:const\s*)?override|::TakeDamage\s*\(|'
                      r'\bOnTake(?:Any|Point|Radial)Damage\s*\.\s*Add')
DEALS = re.compile(r'\bUGameplayStatics\s*::\s*Apply(?:Point|Radial)?Damage(?:WithFalloff)?\s*\(|'
                   r'(?:->|\.)\s*TakeDamage\s*\(')


def _words(name):
    name = re.sub(r'^b(?=[A-Z])', '', name)
    return [w.lower() for w in re.findall(r'[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+', name)]


def _key_member(type_, name):
    """Why a data member is key state (spec 11.1 K), or None."""
    t = re.sub(r'\s+', ' ', type_).strip()
    words, low = _words(name), name.lower()
    if not NUMBER_TYPES.match(t) or SHOWN_WORDS & set(words):
        return None
    if HEALTH_WORDS & set(words) or 'hitpoint' in low:
        return 'health'
    if STATE_WORDS & set(words) or 'cooldown' in low:
        return 'combat state'
    if WHOLE_WORDS & set(words) and WHOLE_TYPES.match(t):
        return 'phase or state'
    return None


def _strip_cpp(text):
    """C++ text without comments, string and char literals (their length kept as spaces, so line numbers hold)."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith('//', i):
            j = text.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i)); i = j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r'[^\n]', ' ', text[i:j])); i = j
        elif c in '"\'':
            j = i + 1
            while j < n and text[j] != c and text[j] != '\n':
                j += 2 if text[j] == '\\' else 1
            j = min(j + 1, n)
            out.append(c + ' ' * max(0, j - i - 2) + (c if j - i >= 2 else '')); i = j
        else:
            out.append(c); i += 1
    return ''.join(out)


MEMBER = re.compile(r'^(?P<prefix>(?:\s*UPROPERTY\s*\((?:[^()]|\([^()]*\))*\))?)\s*(?P<quals>(?:(?:mutable|volatile)\s+)*)'
                    r'(?P<type>[A-Za-z_][\w:]*(?:\s*<[^;{}()]*>)?)\s+(?P<name>[A-Za-z_]\w*)\s*'
                    r'(?::\s*1\s*)?(?:\[[^\]]*\]\s*)?(?:=[^;]*|\{[^;]*\})?$', re.S)


def key_state_members(text):
    """[(line, name, why, reflected, in_reflected_type)] of the key state data members of the class and struct bodies
    in C++ `text` (spec 11.1 K): members only, never locals or functions, static/const/constexpr left out."""
    src = _strip_cpp(text)
    found, stack, stmt, stmt_line = [], [], [], None
    depth, i, n = 0, 0, len(src)
    pending = None  # (kind, reflected) of a class/struct head waiting for its `{`
    line = 1
    while i < n:
        c = src[i]
        if c == '\n':
            line += 1
        if c == '{':
            head = ''.join(stmt)
            m = re.search(r'\b(class|struct)\s+(?:[A-Z_]+_API\s+)?(\w+)\s*(?:final\s*)?(?::[^{]*)?$', head.strip())
            if m and not re.search(r'\benum\b', head):
                reflected = bool(re.search(r'\b(UCLASS|USTRUCT)\s*\(', head))
                ui = bool(UI_CLASS.search(head[head.rfind(m.group(1)):]))
                stack.append((depth + 1, reflected, ui))
            depth += 1
            stmt, stmt_line = [], None
        elif c == '}':
            depth -= 1
            if stack and stack[-1][0] == depth + 1:
                stack.pop()
            stmt, stmt_line = [], None
        elif c == ';':
            if stack and stack[-1][0] == depth:
                body = ''.join(stmt)
                body = re.sub(r'^.*?\b(?:public|private|protected)\s*:', '', body, flags=re.S)
                body = re.sub(r'\b(?:GENERATED_BODY|GENERATED_UCLASS_BODY|GENERATED_USTRUCT_BODY)\s*\(\s*\)', '', body)
                body = re.sub(r'\bU(?:CLASS|STRUCT)\s*\((?:[^()]|\([^()]*\))*\)', '', body)
                body = body.strip()
                if body and not stack[-1][2] and not re.search(r'\b(?:static|constexpr|const|typedef|using|friend|virtual|operator|'
                                          r'DECLARE_\w+)\b', body):
                    m = MEMBER.match(body)
                    if m and '(' not in m.group('type'):
                        why = _key_member(m.group('type'), m.group('name'))
                        if why:
                            found.append((stmt_line or line, m.group('name'), why, bool(m.group('prefix').strip()),
                                          stack[-1][1]))
            stmt, stmt_line = [], None
        else:
            if c == ':' and stack and stack[-1][0] == depth and re.search(r'\b(?:public|private|protected)\s*$', ''.join(stmt)):
                stmt, stmt_line = [], None
                i += 1
                continue
            if not stmt and c.isspace():
                pass
            else:
                if stmt_line is None and not c.isspace():
                    stmt_line = line
                stmt.append(c)
        i += 1
    return found


# every finding of the contract and the sound rule ends with this: a game in progress is brought up to them first
REQUIRED = ' (required before this game can be packaged: game-session skill, "Combat through the engine" and "Sound")'


# a sound made at run time (the owner's decision of 2026-11-11): every game sound is an imported asset
RUNTIME_SOUND = re.compile(r'\b(?:USoundWaveProcedural|QueueAudio|USynthComponent|ISoundGenerator|OnGenerateAudio|'
                           r'USynthSound|UModularSynthComponent|UGranularSynth|USynthSamplePlayer|'
                           r'USynthComponentToneGenerator|USynthComponentMoto)\b')


def check_sound(rep, repo, files):
    """Every sound the game plays is an imported asset: no code in Source/ makes one at run time (procedural sound
    waves, synth components, sound generators), each named with its file and line."""
    found = []
    for f in (f for f in files if f.startswith('Source/') and f.endswith(('.h', '.cpp')) and '/AutoPlay/' not in f):
        try:
            text = _strip_cpp(open(os.path.join(repo, f), encoding='utf-8-sig', errors='replace').read())
        except OSError:
            continue
        for m in RUNTIME_SOUND.finditer(text):
            found.append((f, text.count('\n', 0, m.start()) + 1, m.group(0)))
    for f, ln, what in found[:20]:
        rep.error('sound', f'{f}:{ln}: {what} makes a sound at run time: import every sound as an asset (a clip, or a '
                  'WAV a committed script made and imported), so it has a name' + REQUIRED)
    if len(found) > 20:
        rep.error('sound', f'... {len(found) - 20} more places that make a sound at run time' + REQUIRED)


def check_contract(rep, repo, files):
    """Spec 11.1 D and K on the game's Source/: a game with combat receives damage in TakeDamage (or an OnTake*Damage
    handler) and deals it through the engine's damage calls; every key state member is a UPROPERTY of a UCLASS or
    USTRUCT. For new games (the owner's decision of 2026-11-11); its findings are errors. Not checked statically, the
    skill states it: TakeDamage returns the damage actually applied (0 when the hit did nothing), which a staged hit's
    damage_taken reads."""
    # the factory's own AutoPlay recorder, copied into every game, is harness code, not the game's
    sources = [f for f in files if f.startswith('Source/') and f.endswith(('.h', '.cpp')) and '/AutoPlay/' not in f]
    keys, hit_functions, receives, deals = [], [], [], []
    for f in sources:
        try:
            text = open(os.path.join(repo, f), encoding='utf-8-sig', errors='replace').read()
        except OSError:
            continue
        for ln, name, why, reflected, in_reflected in key_state_members(text):
            keys.append((f, ln, name, why, reflected, in_reflected))
        plain = _strip_cpp(text)
        for m in HIT_FUNCTION.finditer(plain):
            word = re.match(r'\w+', m.group(0)).group(0)
            if word not in ENGINE_DAMAGE:
                hit_functions.append((f, plain.count('\n', 0, m.start()) + 1, word))
        if RECEIVES.search(plain):
            receives.append(f)
        if DEALS.search(plain):
            deals.append(f)
    combat = any(why == 'health' for *_, why, _r, _i in keys) or bool(hit_functions)
    if not combat:
        rep.note('contract', 'no combat (no health member, no hit function): the damage rule does not apply')
    else:
        if not receives:
            rep.error('contract', 'combat without the engine\'s damage interface: nothing overrides AActor::TakeDamage or '
                      'binds OnTakeAnyDamage/OnTakePointDamage/OnTakeRadialDamage' + (
                          f' (the game\'s own hit function {hit_functions[0][2]} at {hit_functions[0][0]}:{hit_functions[0][1]} '
                          'must be a step called from TakeDamage)' if hit_functions else '') + REQUIRED)
        if not deals:
            rep.error('contract', 'combat without the engine\'s damage calls: nothing calls UGameplayStatics::ApplyDamage, '
                      'ApplyPointDamage, ApplyRadialDamage(WithFalloff) or an actor\'s TakeDamage' + REQUIRED)
    bad = [k for k in keys if not (k[4] and k[5])]
    for f, ln, name, why, reflected, in_reflected in bad[:20]:
        rep.error('contract', f'{f}:{ln}: {name} ({why}) is not a UPROPERTY' + (
            '' if in_reflected else ' of a UCLASS or USTRUCT (its class or struct is not reflected)')
                  + ': make it a UPROPERTY on an actor or component' + REQUIRED)
    if len(bad) > 20:
        rep.error('contract', f'... {len(bad) - 20} more key state members not reflected' + REQUIRED)
    if not bad:
        rep.note('contract', f'{len(keys)} key state member(s), all UPROPERTY')


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
    ap.add_argument('--rules-only', action='store_true',
                    help="only the game contract and the sound rule on the repo's Source/ (what the packager checks first)")
    a = ap.parse_args()
    if a.rules_only:
        if not a.repo:
            ap.error('--rules-only takes a game repo')
        rep = Report()
        check_rules(rep, os.path.abspath(a.repo), git_ls(os.path.abspath(a.repo)))
        print(f'{"INVALID" if rep.count("error") else "VALID"}  {rep.count("error")} error(s)  [{a.repo}: contract, sound]')
        for sev, area, msg in rep.items:
            print(f'  {"x" if sev == "error" else "-"} {area}: {msg}')
        sys.exit(2 if rep.count('error') else 0)
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

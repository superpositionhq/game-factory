# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6", "openpyxl>=3.1"]
# ///
"""Build a game-creation package (workflow.jsonl + git.log) for one feature of a Unity project.

Every step comes from a real commit: Unity YAML assets are diffed object by object, binaries are
recorded by hash and importer settings, config tables cell by cell. Nothing is invented: no reasons
are written beyond the commit message, and no order is reconstructed beyond commit order.

    uv run Tools/build_package.py --repo ~/Repo/LiaoZhaiRL --out . --feature-name 葛巾_旗袍 \
        --folder 'Assets/LiaoZhaiRL/Combat_战斗相关/Characters_角色/Player_总集/Player_女侠_形态10_葛巾_旗袍' \
        --grep 葛巾 --since 2026-07-30 --keyword 葛巾 --keyword 形态10
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path

import yaml

SCHEMA = 'liaozhai.unity-workflow/v1'
YAML_EXT = {'.prefab', '.mat', '.anim', '.controller', '.overrideController', '.playable', '.asset', '.unity',
            '.mask', '.physicMaterial', '.renderTexture', '.spriteatlas', '.lighting', '.preset', '.mixer'}
KIND = {'.fbx': 'model', '.obj': 'model', '.png': 'texture', '.tga': 'texture', '.exr': 'texture', '.psd': 'texture',
        '.jpg': 'texture', '.jpeg': 'texture', '.wav': 'audio', '.wem': 'audio', '.ogg': 'audio', '.bnk': 'audio',
        '.xlsx': 'table', '.ttf': 'font', '.otf': 'font', '.shader': 'shader', '.cs': 'code'}
CHAPTER = {'model': '模型', 'texture': '贴图', 'audio': '音频', 'table': '配置表', 'code': '代码', 'shader': '着色器',
           '.mat': '材质', '.anim': '动画', '.controller': '动画', '.overrideController': '动画', '.playable': '技能 Timeline',
           '.unity': '场景', '.asset': '配置资产'}
HEADER = re.compile(r'^--- !u!(\d+) &(-?\d+)(.*)$', re.M)
class UnityLoader(getattr(yaml, 'CSafeLoader', yaml.SafeLoader)):
    """
    Safe loader with Unity-faithful implicit typing instead of YAML 1.1's. Unity writes bools as 0/1, plain
    decimal ints and floats, and everything else unquoted as a string, so YAML 1.1 rules corrupt values:
    `10019_1` (a skin id) became the int 100191, `on`/`yes` become bools, `0123` an octal int, an all-digit
    hash a huge int, and `1e5…`-shaped GUIDs floats. Here only these resolve, everything else stays a string:
    int    `0` or `-?[1-9][0-9]*` up to 20 digits (file ids are 64-bit; no leading zeros, no `_`, no `-0`)
    float  `-?(0|[1-9][0-9]*)` with `.digits` and/or a 1–3 digit exponent (Unity's `Infinity`/`NaN` stay strings,
           which JSON can carry)
    null   the empty value only
    """


UnityLoader.yaml_implicit_resolvers = {}
UnityLoader.add_implicit_resolver('tag:yaml.org,2002:int', re.compile(r'^(?:0|-?[1-9][0-9]{0,19})$'),
                                  list('-0123456789'))
UnityLoader.add_implicit_resolver(
    'tag:yaml.org,2002:float',
    re.compile(r'^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+(?:[eE][-+]?[0-9]{1,3})?|[eE][-+]?[0-9]{1,3})$'),
    list('-0123456789'))
UnityLoader.add_implicit_resolver('tag:yaml.org,2002:null', re.compile(r'^$'), [''])
UnityLoader.add_constructor('tag:yaml.org,2002:float', lambda loader, node: float(loader.construct_scalar(node)))
LOADER = UnityLoader
MAX_PATHS = 400        # changed property paths kept per object step
MAX_CELLS = 400        # changed cells kept per table step
MAX_DIFF_LINES = 3000  # lines of unified diff kept per file in git.log
ZERO = '0' * 40


def git(repo, *args, data=None):
    return subprocess.run(['git', '-C', str(repo), '-c', 'core.quotepath=off', *args], input=data,
                          capture_output=True, check=True).stdout


class Blobs:
    """One `git cat-file --batch` process; a partial clone fetches missing blobs on demand."""

    def __init__(self, repo):
        self.proc = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
        self.cache = {}

    def get(self, oid):
        if oid in (None, ZERO):
            return None
        if oid not in self.cache:
            self.proc.stdin.write(oid.encode() + b'\n')
            self.proc.stdin.flush()
            head = self.proc.stdout.readline().split()
            if head[1] == b'missing':
                raise RuntimeError('blob missing: ' + oid)
            body = self.proc.stdout.read(int(head[2]))
            self.proc.stdout.read(1)
            if len(self.cache) > 64:
                self.cache.clear()
            self.cache[oid] = body
        return self.cache[oid]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---------- Unity YAML ----------

def unity_docs(data):
    """{fileID: (classID, className, body, stripped)} for one Unity YAML file."""
    text = data.decode('utf-8', 'replace')
    heads = list(HEADER.finditer(text))
    docs = {}
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        raw = text[m.end():end]
        try:
            parsed = yaml.load(raw, Loader=LOADER) or {}
            (cls, body), = parsed.items() if isinstance(parsed, dict) and len(parsed) == 1 else [('?', parsed)]
        except yaml.YAMLError:
            cls, body = '?', {'_raw_sha256': sha256(raw.encode())}
        docs[m.group(2)] = (int(m.group(1)), cls, body if body is not None else {}, 'stripped' in m.group(3))
    return docs


def is_ref(v):
    return isinstance(v, dict) and 'fileID' in v and set(v) <= {'fileID', 'guid', 'type'}


def list_keys(items):
    """Path segments for list items: by identity (GUID, component) when every item has a unique one, else by index."""
    keys = []
    for i, x in enumerate(items):
        key = None
        if isinstance(x, dict):
            for k in ('m_GUID', 'guid', 'm_Id'):
                if isinstance(x.get(k), str) and x[k]:
                    key = f'[{k}={x[k]}]'
                    break
            if key is None and is_ref(x.get('component')):
                key = f"[component={x['component']['fileID']}]"
        keys.append(key)
    if None in keys or len(set(keys)) != len(keys):
        return [f'[{i}]' for i in range(len(items))]
    return keys


def flatten(v, prefix='', out=None):
    out = {} if out is None else out
    if isinstance(v, dict) and not is_ref(v):
        for k, x in v.items():
            flatten(x, f'{prefix}.{k}' if prefix else str(k), out)
    elif isinstance(v, list) and v and not all(isinstance(x, (int, float)) for x in v):
        for seg, x in zip(list_keys(v), v):
            flatten(x, prefix + seg, out)
    else:
        out[prefix] = v
    return out


def list_inserts(a, b, prefix='', out=None):
    """
    Items added to identity-keyed lists, with their index in the new list: {list path: [[index, key], …]}.
    flatten() keys such items by identity and steps list changed paths sorted, so without this the position
    of an added item is lost, and assets keep it (an Addressables group's entries, a GameObject's components).
    Paths and keys are spelled as in flatten(). Items that only moved are not recorded.
    """
    out = {} if out is None else out
    if isinstance(b, dict) and not is_ref(b):
        for k, x in b.items():
            list_inserts(a.get(k) if isinstance(a, dict) else None, x, f'{prefix}.{k}' if prefix else str(k), out)
    elif isinstance(b, list) and b and not all(isinstance(x, (int, float)) for x in b):
        kb = list_keys(b)
        if '=' in kb[0]:
            ka = list_keys(a) if isinstance(a, list) and a else []
            old = dict(zip(ka, a)) if ka and '=' in ka[0] else {}
            added = [[i, k] for i, k in enumerate(kb) if k not in old]
            if added:
                out[prefix] = added[:MAX_PATHS]
            for k, x in zip(kb, b):
                if k in old:
                    list_inserts(old[k], x, prefix + k, out)
        else:
            for i, (k, x) in enumerate(zip(kb, b)):
                list_inserts(a[i] if isinstance(a, list) and i < len(a) else None, x, prefix + k, out)
    return out


GUID_TEXT = re.compile(r'\b[0-9a-f]{32}\b')
ARRAY_ELEM = re.compile(r'Array\.data\[\d+\]')


def collapse_elements(entries, limit=20):
    """Many per-element overrides of one array (Odin's SerializedBytes, curves) become one summary entry."""
    groups = {}
    for e in entries:
        groups.setdefault((e['target_file_id'], ARRAY_ELEM.sub('Array.data[*]', e['property'])), []).append(e)
    out = []
    for (target, prop), items in groups.items():
        if len(items) > limit and '[*]' in prop:
            out.append({'target_file_id': target, 'property': prop, 'changed_elements': len(items),
                        'sample': items[:5]})
        else:
            out += items
    return out


class Names:
    """Hierarchy paths of GameObjects in one Unity YAML file, for readable step targets."""

    def __init__(self, docs):
        self.docs = docs
        self.go_of_transform = {fid: str(b.get('m_GameObject', {}).get('fileID')) for fid, (_, c, b, _) in docs.items()
                                if c in ('Transform', 'RectTransform') and isinstance(b, dict)}
        self.parent = {fid: str(b.get('m_Father', {}).get('fileID')) for fid, (_, c, b, _) in docs.items()
                       if c in ('Transform', 'RectTransform') and isinstance(b, dict)}
        self.transform_of_go = {go: t for t, go in self.go_of_transform.items()}

    def go_name(self, go):
        d = self.docs.get(go)
        return (d[2].get('m_Name') if d and isinstance(d[2], dict) else None) or f'#{go}'

    def go_path(self, go):
        parts, t, seen = [], self.transform_of_go.get(go), set()
        if t is None:
            return self.go_name(go)
        while t and t != '0' and t not in seen:
            seen.add(t)
            parts.append(self.go_name(self.go_of_transform.get(t, '')))
            t = self.parent.get(t)
        return '/'.join(reversed(parts))

    def describe(self, fid):
        cid, cls, body, stripped = self.docs[fid]
        obj = {'class': cls, 'class_id': cid, 'file_id': fid}
        if cls == 'GameObject':
            obj['game_object'] = self.go_path(fid)
        elif isinstance(body, dict) and is_ref(body.get('m_GameObject')) and body['m_GameObject']['fileID']:
            obj['game_object'] = self.go_path(str(body['m_GameObject']['fileID']))
        if isinstance(body, dict) and is_ref(body.get('m_Script')):
            obj['script'] = body['m_Script']
        if stripped:
            obj['stripped'] = True
        return obj


# ---------- tables ----------

def table_cells(data):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheets = {}
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        sheets[ws.title] = rows
    return sheets


def table_diff(before, after):
    changes, total = [], 0
    for sheet in sorted(set(before) | set(after)):
        a, b = before.get(sheet, []), after.get(sheet, [])
        header = b[:3] if b else a[:3]
        for r in range(max(len(a), len(b))):
            ra = a[r] if r < len(a) else []
            rb = b[r] if r < len(b) else []
            for c in range(max(len(ra), len(rb))):
                x = ra[c] if c < len(ra) else None
                y = rb[c] if c < len(rb) else None
                if x != y:
                    total += 1
                    if len(changes) < MAX_CELLS:
                        col = '|'.join(str(h[c]) for h in header if c < len(h) and h[c] is not None)
                        key = (rb or ra)[0] if (rb or ra) else None
                        changes.append({'sheet': sheet, 'row': r + 1, 'col': c + 1, 'column_header': col,
                                        'row_key': jsonable(key), 'before': jsonable(x), 'after': jsonable(y)})
    return changes, total


def jsonable(v):
    if isinstance(v, (dt.datetime, dt.date, dt.time)):
        return v.isoformat()
    return v


# ---------- package ----------

class Builder:
    def __init__(self, args):
        self.a = args
        self.repo = Path(args.repo).expanduser()
        self.out = Path(args.out)
        self.blobs = Blobs(self.repo)
        self.guid_path = {}
        self.authors = {}
        self.steps = []
        self.last_step = {}      # asset path -> last step id
        self.made_by = {}        # asset path -> step id that created / imported it in this feature

    def in_scope(self, path):
        return any(k in path for k in self.a.keyword) or not any(path.startswith(x) for x in self.a.exclude)

    def author(self, name, email):
        key = (name, email.lower())
        for k, v in self.authors.items():
            if k[0] == name or k[1] == key[1]:
                return v
        self.authors[key] = f'dev_{len(self.authors) + 1:02d}'
        return self.authors[key]

    def commits(self):
        shas = set(git(self.repo, 'log', '--no-merges', '--format=%H', '--', *self.a.folder).decode().split())
        if self.a.grep:
            g = ['log', '--no-merges', '--format=%H', '-i', '--grep', self.a.grep]
            if self.a.since:
                g += ['--since', self.a.since]
            shas |= set(git(self.repo, *g).decode().split())
        for rev in self.a.include_commit:
            shas.add(git(self.repo, 'rev-parse', '--verify', rev + '^{commit}').decode().strip())
        if not shas:
            return []
        order = git(self.repo, 'log', '--no-walk=sorted', '--reverse', '--format=%H', *shas).decode().split()
        return order

    def index_guids(self):
        root = self.out / 'UnityProject'
        for p in root.rglob('*.meta'):
            with p.open('rb') as f:
                for line in f.read(400).splitlines():
                    if line.startswith(b'guid: '):
                        self.guid_path[line[6:].decode().strip()] = p.relative_to(root).as_posix()[:-5]
                        break

    def resolve(self, values):
        """Add the asset path next to every GUID reference."""
        refs = set()

        def walk(v):
            if is_ref(v):
                if v.get('guid'):
                    path = self.guid_path.get(v['guid'])
                    if path:
                        refs.add(path)
                        return {**v, 'path': path}
                return v
            if isinstance(v, dict):
                return {k: walk(x) for k, x in v.items()}
            if isinstance(v, list):
                return [walk(x) for x in v]
            return v
        return walk(values), refs

    def step(self, commit, op, target, params, derivation, chapter, refs=()):
        sid = f'W{len(self.steps) + 1:05d}'
        text = json.dumps(params, ensure_ascii=False, default=jsonable)
        named = {g: self.guid_path[g] for g in sorted(set(GUID_TEXT.findall(text))) if g in self.guid_path}
        if named:
            params = {**params, 'guid_paths': named}
            refs = set(refs) | set(named.values())
        deps = []
        if target in self.last_step:
            deps.append(self.last_step[target])
        deps += sorted({self.made_by[r] for r in refs if r in self.made_by and self.made_by[r] not in deps})
        row = {'schema': SCHEMA, 'id': sid, 'seq': len(self.steps) + 1, 'chapter': chapter,
               'commit': commit['id'], 'time': commit['time'], 'author': commit['author'],
               'op': op, 'target': target, 'params': params,
               'reason': commit['message'], 'reason_source': 'commit_message',
               'depends_on': deps, 'derivation': derivation, 'status': 'observed_in_commit',
               'source': {'commit_sha': commit['sha'], 'diff': f"git.log#{commit['id']}"}}
        self.steps.append(row)
        self.last_step[target] = sid
        if op in ('asset.create', 'asset.import') and target not in self.made_by:
            self.made_by[target] = sid
        return row

    def chapter(self, path):
        ext = Path(path).suffix
        kind = KIND.get(ext.lower())
        if kind in CHAPTER:
            return CHAPTER[kind]
        if ext == '.prefab':
            return '特效' if '/Effects/' in path or Path(path).name.lower().startswith('vfx') else '预制体'
        return CHAPTER.get(ext, '其他')

    def yaml_steps(self, commit, path, old, new):
        ch = self.chapter(path)
        if old is None:
            docs = unity_docs(new)
            names = Names(docs)
            gos = [{'path': names.go_path(fid),
                    'components': [docs[str(c['component']['fileID'])][1] for c in b.get('m_Component', [])
                                   if str(c.get('component', {}).get('fileID')) in docs]}
                   for fid, (_, cls, b, _) in docs.items() if cls == 'GameObject' and isinstance(b, dict)]
            gos.sort(key=lambda g: g['path'])
            classes = {}
            for _, cls, _, _ in docs.values():
                classes[cls] = classes.get(cls, 0) + 1
            refs_raw = [v for d in docs.values() for v in flatten(d[2]).values() if is_ref(v) and v.get('guid')]
            _, refs = self.resolve(refs_raw)
            params = {'asset_type': next(iter(docs.values()))[1] if docs else None, 'objects': len(docs),
                      'classes': classes, 'game_objects': gos[:300], 'game_objects_total': len(gos),
                      'references': sorted(refs)[:200], 'references_total': len(refs),
                      'sha256': sha256(new), 'bytes': len(new)}
            self.step(commit, 'asset.create', path, params, 'unity_yaml_new_file', ch, refs)
            return
        a, b = unity_docs(old), unity_docs(new)
        na, nb = Names(a), Names(b)
        for fid in [f for f in b if f not in a]:
            vals, refs = self.resolve(b[fid][2])
            self.step(commit, 'object.add', path, {'object': nb.describe(fid), 'values': vals},
                      'unity_yaml_object_diff', ch, refs)
        for fid in [f for f in a if f not in b]:
            self.step(commit, 'object.remove', path, {'object': na.describe(fid)}, 'unity_yaml_object_diff', ch)
        for fid in [f for f in b if f in a]:
            if a[fid][2] == b[fid][2]:
                continue
            if b[fid][1] == 'PrefabInstance':
                self.prefab_override(commit, path, ch, nb.describe(fid), a[fid][2], b[fid][2])
                continue
            fa, fb = flatten(a[fid][2]), flatten(b[fid][2])
            changed = sorted(k for k in set(fa) | set(fb) if fa.get(k, '<absent>') != fb.get(k, '<absent>'))
            if not changed:
                continue
            keep = changed[:MAX_PATHS]
            values, refs = self.resolve({k: fb.get(k) for k in keep})
            before, _ = self.resolve({k: fa.get(k) for k in keep})
            params = {'object': nb.describe(fid), 'values': values, 'before': before}
            inserts = list_inserts(a[fid][2], b[fid][2])
            if inserts:
                params['list_inserts'] = inserts
            if len(changed) > len(keep):
                params |= {'changed_paths_total': len(changed), 'truncated': True}
            self.step(commit, 'object.set', path, params, 'unity_yaml_object_diff', ch, refs)

    def prefab_override(self, commit, path, ch, obj, old, new):
        def mods(body):
            m = (body.get('m_Modification') or {}).get('m_Modifications') or []
            return {(str(x.get('target', {}).get('fileID')), x.get('target', {}).get('guid'), x.get('propertyPath')):
                    {'value': x.get('value'), 'objectReference': x.get('objectReference')} for x in m}
        ma, mb = mods(old), mods(new)
        sets = collapse_elements([{'target_file_id': k[0], 'property': k[2], **mb[k]}
                                  for k in sorted(mb, key=str) if ma.get(k) != mb[k]])
        removed = collapse_elements([{'target_file_id': k[0], 'property': k[2]}
                                     for k in sorted(ma, key=str) if k not in mb])
        rest_a = {k: v for k, v in old.items() if k != 'm_Modification'}
        rest_b = {k: v for k, v in new.items() if k != 'm_Modification'}
        other = {k: v for k, v in flatten(rest_b).items() if flatten(rest_a).get(k, '<absent>') != v}
        source, refs = self.resolve({'source': new.get('m_SourcePrefab'), 'set': sets[:MAX_PATHS],
                                     'removed': removed[:MAX_PATHS], 'other': other})
        params = {'object': obj, 'source_prefab': source['source'], 'overrides_set': source['set'],
                  'overrides_removed': source['removed']}
        if other:
            params['other'] = source['other']
        if len(sets) > MAX_PATHS or len(removed) > MAX_PATHS:
            params |= {'overrides_set_total': len(sets), 'overrides_removed_total': len(removed), 'truncated': True}
        self.step(commit, 'prefab.override', path, params, 'unity_prefab_instance_diff', ch, refs)

    def importer(self, data):
        if not data:
            return None
        try:
            meta = yaml.load(data.decode('utf-8', 'replace'), Loader=LOADER) or {}
        except yaml.YAMLError:
            return {'_raw_sha256': sha256(data)}
        return {k: v for k, v in meta.items() if k not in ('fileFormatVersion',)}

    def file_steps(self, commit, ent, metas):
        st, path, old_oid, new_oid = ent['status'], ent['path'], ent['old'], ent['new']
        ext = Path(path).suffix
        kind = KIND.get(ext.lower())
        ch = self.chapter(path)
        if st == 'D':
            self.step(commit, 'asset.delete', path, {'before_sha256': sha256(self.blobs.get(old_oid))},
                      'file_deleted', ch)
            return
        if st.startswith('R'):
            self.step(commit, 'asset.move', path, {'from': ent['old_path']}, 'file_renamed', ch)
            if old_oid == new_oid:
                return
        old = self.blobs.get(old_oid) if old_oid != ZERO else None
        new = self.blobs.get(new_oid)
        meta = metas.get(path + '.meta')
        if ext in YAML_EXT and new.startswith(b'%YAML'):
            self.yaml_steps(commit, path, old, new)
        elif kind == 'table':
            after = table_cells(new)
            before = table_cells(old) if old else {}
            cells, total = table_diff(before, after)
            params = {'sheets': sorted(after), 'cells': cells, 'cells_changed_total': total,
                      'sha256': sha256(new), 'bytes': len(new)}
            if total > len(cells):
                params['truncated'] = True
            self.step(commit, 'table.create' if old is None else 'table.edit', path, params, 'table_cell_diff', ch)
        elif kind == 'code' or (old is not None and b'\0' not in new[:8000] and kind is None):
            self.step(commit, 'code.change' if kind == 'code' else 'file.edit', path,
                      {'added_lines': ent['added'], 'deleted_lines': ent['deleted'], 'sha256': sha256(new)},
                      'text_diff', ch)
        else:
            params = {'kind': kind or 'binary', 'bytes': len(new), 'sha256': sha256(new)}
            if old is not None:
                params['before_sha256'] = sha256(old)
            if meta:
                params['importer'] = self.importer(self.blobs.get(meta['new']))
            self.step(commit, 'asset.import' if old is None else 'asset.replace', path, params, 'binary_change', ch)

    def meta_steps(self, commit, ent):
        new = self.importer(self.blobs.get(ent['new']))
        if not isinstance(new, dict) or new.get('folderAsset'):
            return
        old = self.importer(self.blobs.get(ent['old'])) if ent['old'] != ZERO else {}
        fa, fb = flatten(old or {}), flatten(new)
        changed = sorted(k for k in set(fa) | set(fb) if fa.get(k, '<absent>') != fb.get(k, '<absent>') and k != 'guid')
        if changed:
            asset = ent['path'][:-5]
            self.step(commit, 'importer.set', asset,
                      {'values': {k: fb.get(k) for k in changed[:MAX_PATHS]},
                       'before': {k: fa.get(k) for k in changed[:MAX_PATHS]}},
                      'unity_meta_diff', self.chapter(asset))

    def entries(self, sha, parent):
        raw = git(self.repo, 'diff-tree', '-r', '-M', '-z', '--raw', '--numstat', '--no-commit-id', parent, sha)
        parts = raw.split(b'\0')
        ents, i = [], 0
        while i < len(parts) and parts[i].startswith(b':'):
            meta = parts[i].decode().split()
            st = meta[4]
            if st.startswith(('R', 'C')):
                ents.append({'status': st, 'old': meta[2], 'new': meta[3], 'old_path': parts[i + 1].decode(),
                             'path': parts[i + 2].decode()})
                i += 3
            else:
                ents.append({'status': st, 'old': meta[2], 'new': meta[3], 'path': parts[i + 1].decode()})
                i += 2
        stats = {}
        while i < len(parts) and parts[i]:
            head = parts[i].decode()
            add, dele, name = head.split('\t', 2)
            if name == '':
                name = parts[i + 2].decode()
                i += 3
            else:
                i += 1
            stats[name] = (None if add == '-' else int(add), None if dele == '-' else int(dele))
        for e in ents:
            e['added'], e['deleted'] = stats.get(e['path'], (None, None))
        return ents

    def build(self):
        if (self.out / 'UnityProject').is_dir():
            self.index_guids()
        shas = self.commits()
        records, log = [], []
        for sha in shas:
            info = git(self.repo, 'show', '-s', '--format=%P%x00%an%x00%ae%x00%aI%x00%cI%x00%B', sha).decode()
            parents, an, ae, adate, cdate, msg = info.split('\0', 5)
            parent = parents.split()[0]
            ents = [e for e in self.entries(sha, parent)]
            scoped = [e for e in ents if self.in_scope(e['path'])]
            if not scoped:
                continue
            commit = {'id': f'c{len(records) + 1:03d}', 'sha': sha, 'parent': parent, 'time': adate,
                      'committed': cdate, 'author': self.author(an, ae), 'message': msg.strip()}
            metas = {e['path']: e for e in scoped if e['path'].endswith('.meta')}
            first = len(self.steps)
            for e in sorted(scoped, key=lambda e: (Path(e['path']).suffix.lower() not in KIND, e['path'])):
                if e['path'].endswith('.meta'):
                    if e['status'] != 'D' and e['path'][:-5] not in {x['path'] for x in scoped}:
                        self.meta_steps(commit, e)
                    continue
                self.file_steps(commit, e, metas)
            commit |= {'files_in_scope': len(scoped), 'files_out_of_scope': len(ents) - len(scoped),
                       'steps': [s['id'] for s in self.steps[first:]],
                       'files': [{k: e.get(k) for k in ('status', 'path', 'old_path', 'old', 'new', 'added', 'deleted')
                                  if e.get(k) is not None} for e in scoped]}
            records.append(commit)
            log.append(self.log_entry(commit, scoped))
            print(f"{commit['id']} {sha[:10]} files={len(scoped)}/{len(ents)} steps={len(commit['steps'])} "
                  f"{commit['message'].splitlines()[0][:40]}", flush=True)
        return records, log

    def log_entry(self, commit, scoped):
        lines = [f"commit {commit['id']} {commit['sha']}", f"Author: {commit['author']}", f"Date:   {commit['time']}", '',
                 *('    ' + x for x in commit['message'].splitlines()), '']
        for e in scoped:
            add = '-' if e['added'] is None else e['added']
            dele = '-' if e['deleted'] is None else e['deleted']
            lines.append(f" {e['status']:<4} {e['path']} +{add} -{dele}")
        if commit['files_out_of_scope']:
            lines.append(f" ({commit['files_out_of_scope']} files in this commit belong to other features and are left out)")
        lines.append('Replay-Record: ' + json.dumps({k: commit[k] for k in ('id', 'sha', 'parent', 'time', 'author', 'steps')},
                                                    ensure_ascii=False))
        for e in scoped:
            if e['added'] is None:
                if e['status'] != 'D':
                    lines.append(f"Binary {e['path']} sha256={sha256(self.blobs.get(e['new']))}")
                continue
            diff = git(self.repo, 'diff', '-M', commit['parent'], commit['sha'], '--', e['path'], *(
                [e['old_path']] if e.get('old_path') else [])).decode('utf-8', 'replace').splitlines()
            if len(diff) > MAX_DIFF_LINES:
                diff = diff[:MAX_DIFF_LINES] + [f"[diff truncated: {len(diff) - MAX_DIFF_LINES} more lines; "
                                                f"blob {e['new']} / file in UnityProject or git]"]
            lines += diff
        return '\n'.join(lines) + '\n'


def file_sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_manifests(out, end_commit):
    """manifest.json for the package files; UnityProject.manifest.jsonl for every file of the snapshot."""
    project = out / 'UnityProject'
    if project.is_dir():
        with (out / 'UnityProject.manifest.jsonl').open('w', encoding='utf-8', newline='\n') as f:
            for p in sorted(x for x in project.rglob('*') if x.is_file()):
                f.write(json.dumps({'path': p.relative_to(project).as_posix(), 'bytes': p.stat().st_size,
                                    'sha256': file_sha256(p)}, ensure_ascii=False) + '\n')
    files = [p for p in sorted(out.rglob('*')) if p.is_file() and 'UnityProject' not in p.relative_to(out).parts[:1]
             and p.name not in ('manifest.json', '.DS_Store')]
    manifest = {'schema': 'liaozhai.package-manifest/v1', 'unity_project_commit': end_commit,
                'files': [{'path': p.relative_to(out).as_posix(), 'bytes': p.stat().st_size, 'sha256': file_sha256(p)}
                          for p in files]}
    write_text(out / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=1))


def write_text(path, text):
    """UTF-8 with LF line ends on every platform (text mode would write CRLF on Windows)."""
    path.write_text(text, encoding='utf-8', newline='\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--feature-name', required=True)
    p.add_argument('--folder', action='append', required=True)
    p.add_argument('--grep')
    p.add_argument('--since')
    p.add_argument('--keyword', action='append', default=[])
    p.add_argument('--exclude', action='append', default=['Assets/LiaoZhaiRL/Combat_战斗相关/Characters_角色/'])
    p.add_argument('--include-commit', action='append', default=[],
                   help='also include this commit (e.g. one the feature builds on that the scope rule misses, or the '
                        '导表 export of a table edit); the start commit is still the parent of the earliest one')
    p.add_argument('--manifest', action='store_true', help='hash every package and UnityProject file (slow)')
    a = p.parse_args()
    b = Builder(a)
    records, log = b.build()
    out = Path(a.out)
    hist = out / 'History'
    hist.mkdir(parents=True, exist_ok=True)
    write_text(out / 'workflow.jsonl',
               ''.join(json.dumps(s, ensure_ascii=False, default=jsonable) + '\n' for s in b.steps))
    header = (f"LIAOZHAI-FEATURE-LOG 1\nFeature: {a.feature_name}\n"
              f"Real commits from the project's history, in commit-date order. Authors are anonymized; "
              f"only files belonging to this feature are shown.\n\n")
    write_text(out / 'git.log', header + '\n'.join(log))
    write_text(hist / 'commits.json', json.dumps(records, ensure_ascii=False, indent=1))
    summary = {'feature': a.feature_name, 'commits': len(records), 'steps': len(b.steps),
               'start_commit': records[0]['parent'] if records else None,
               'end_commit': records[-1]['sha'] if records else None,
               'first_time': records[0]['time'] if records else None, 'last_time': records[-1]['time'] if records else None,
               'authors': len(b.authors), 'guids_indexed': len(b.guid_path),
               'scope': {'folders': a.folder, 'grep': a.grep, 'since': a.since, 'keywords': a.keyword,
                         'excluded_unless_keyword': a.exclude}}
    write_text(hist / 'summary.json', json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False))
    if a.manifest:
        write_manifests(out, summary['end_commit'])


if __name__ == '__main__':
    main()

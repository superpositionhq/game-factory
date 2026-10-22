#!/usr/bin/env python3
"""Convert a game's assets.manifest.json to the one unified format, assets-manifest/v1 (docs/schemas/).

    python tools/migrate-assets-manifest.py <games>/<slug>            # dry run: summary + what needs a person
    python tools/migrate-assets-manifest.py <games>/<slug> --write    # write assets.manifest.json (old one kept as
                                                                      # assets.manifest.legacy.json, untracked)
    options: --show (print the converted JSON), --json <file> (the converted manifest to another file)

Best effort over the earlier shapes: every object that names a licence is an asset entry or a per-file row. Per-file
rows (path/file + licence) are grouped by pack and source into one asset each. Paths become repo paths ("/Game/X"
-> "Content/X"; brace lists expanded); each is resolved against the tracked files: a file, or a folder written "X/"
when every tracked file under it belongs to the asset. Engine-shipped content (/Engine/..., "shipped with the engine")
is not an external asset of the repo and is left out (reported). Entries left without a url, a licence or any
committed file are listed under "needs a person"; the written file then fails validate-game.py until they are fixed.
Standard library only.
"""
import argparse, json, os, re, subprocess, sys
from collections import OrderedDict

URL_RX = re.compile(r'https?://[^\s"\'<>)\],]+')
LIC_KEYS = ('licence', 'license', 'licence_name', 'license_name')


def tracked_files(repo):
    out = subprocess.run(['git', '-C', repo, '-c', 'core.quotepath=off', 'ls-files', '-z'], capture_output=True).stdout
    return [p for p in out.decode('utf-8', 'replace').split('\0') if p]


def first(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, '', [], {}):
            return v
    return None


def expand_braces(s):
    m = re.search(r'\{([^{}]*)\}', s)
    if not m:
        return [s]
    out = []
    for part in m.group(1).split(','):
        out += expand_braces(s[:m.start()] + part.strip() + s[m.end():])
    return out


def to_repo_path(p):
    p = p.strip().replace('\\', '/')
    p = re.sub(r'^\./', '', p)
    if p.startswith('/Game/'):
        p = 'Content/' + p[len('/Game/'):]
    p = re.sub(r'\.[A-Za-z0-9_]+$', '', p) if re.search(r'/[^/.]+\.[^/.]+$', p) and p.startswith('Content/') and not re.search(r'\.(uasset|umap|png|jpg|wav|ttf|otf|json)$', p, re.I) else p
    return p


class Resolver:
    def __init__(self, files):
        self.files = files
        self.set = set(files)
        self.lower = {f.lower(): f for f in files}

    def tail_folder(self, q):
        """A tracked folder ending in the same tail (a pack moved, e.g. under Content/Fab/), when exactly one does."""
        tail = re.sub(r'^Content/', '', q).strip('/')
        if not tail or '/' not in tail and len(tail) < 4:
            return None
        hits = {f[:f.index('/' + tail + '/') + len(tail) + 2] for f in self.files if ('/' + tail + '/') in f}
        return hits.pop() if len(hits) == 1 else None

    def resolve(self, p, name=''):
        """-> list of repo paths (files, or folders ending in /) for one path-like string."""
        res = []
        for q in [x for part in re.split(r'\s*[,;]\s+', p) for x in expand_braces(part)]:
            q = to_repo_path(q).rstrip('*').rstrip('/')
            if not q:
                continue
            if q in self.set:
                res.append(q)
                continue
            for ext in ('.uasset', '.umap'):
                if q + ext in self.set:
                    res.append(q + ext)
                    break
            else:
                pre = q + '/'
                if any(f.startswith(pre) for f in self.files):
                    res.append(pre)
                elif q.lower() in self.lower:
                    res.append(self.lower[q.lower()])
                elif self.tail_folder(q):
                    res.append(self.tail_folder(q))
                else:
                    # a renamed asset inside a folder named for the asset: the folder
                    parent = q.rsplit('/', 1)[0] + '/' if '/' in q else ''
                    key = re.sub(r'[^a-z0-9]', '', (name or '').lower())
                    pk = re.sub(r'[^a-z0-9]', '', parent.rstrip('/').rsplit('/', 1)[-1].lower())
                    if parent and key and pk and (key in pk or pk in key) and any(f.startswith(parent) for f in self.files):
                        res.append(parent)
        return res


def infer_source(entry, url):
    s = ' '.join(str(entry.get(k, '')) for k in ('source', 'origin', 'store', 'provider')).lower() + ' ' + (url or '').lower()
    for key, name in (('fab.com', 'Fab'), ('quixel', 'Fab'), ('megascans', 'Fab'), ('fab', 'Fab'), ('polyhaven', 'Poly Haven'),
                      ('poly haven', 'Poly Haven'), ('ambientcg', 'ambientCG'), ('kenney', 'Kenney'), ('quaternius', 'Quaternius'),
                      ('fonts.google', 'Google Fonts'), ('google fonts', 'Google Fonts'), ('game-icons', 'game-icons.net'),
                      ('opengameart', 'OpenGameArt'), ('freesound', 'Freesound'), ('github.com', 'GitHub'), ('marketplace', 'Marketplace')):
        if key in s:
            return name
    src = entry.get('source')
    return str(src) if src else None


def is_engine(entry):
    s = json.dumps(entry, ensure_ascii=False)
    return bool(re.search(r'"/Engine/|shipped with (the engine|UE)|Templates/TemplateResources|"engine"', s, re.I)) and 'fab.com' not in s.lower()


MADE_HERE = re.compile(r'^(generated|own|made here|procedural|synthesi[sz]ed|script)|\b(generated|synthesi[sz]ed|created) by scripts?/|made (here|by (this|the) project)', re.I)


def is_made_here(entry):
    for k in ('source', 'origin', 'name', 'id'):
        v = entry.get(k)
        if isinstance(v, str) and MADE_HERE.search(v.strip()):
            return True
    return False


def walk(node, out, where=''):
    """Collect (where, dict) for every dict naming a licence; recurse into everything."""
    if isinstance(node, dict):
        if any(k in node for k in LIC_KEYS):
            out.append((where, node))
            return
        for k, v in node.items():
            walk(v, out, f'{where}.{k}' if where else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, out, where)


PATH_KEYS = ('files', 'files_used', 'copied_to', 'folder', 'location', 'path', 'paths', 'file', 'ue_assets', 'content_path',
             'install_path', 'asset', 'dest', 'target')


def path_strings(entry):
    """Every path-like string the entry gives for where its files are in the repo."""
    out = []
    for k in PATH_KEYS:
        v = entry.get(k)
        vals = v if isinstance(v, list) else [v]
        for x in vals:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                y = first(x, 'path', 'file', 'asset', 'dest', 'copied_to')
                if isinstance(y, str):
                    out.append(y)
    return [s for s in out if s and not URL_RX.match(s) and not re.match(r'^[A-Za-z]:[\\/]', s)]


def convert(repo):
    src = os.path.join(repo, 'assets.manifest.json')
    old = json.load(open(src, encoding='utf-8-sig'))
    files = tracked_files(repo)
    R = Resolver(files)
    up = next((f for f in files if re.fullmatch(r'[^/]+\.uproject', f)), '')
    project = old.get('project') if isinstance(old, dict) and isinstance(old.get('project'), str) else os.path.splitext(up)[0]
    entries = []
    walk(old, entries)
    assets = OrderedDict()   # key -> asset
    left_out, person = [], []
    for where, e in entries:
        if is_engine(e) or is_made_here(e):
            left_out.append(first(e, 'name', 'id', 'path', 'asset') or where)
            continue
        url = first(e, 'url', 'listing', 'page', 'link', 'source_url')
        if not isinstance(url, str) or not URL_RX.match(url or ''):
            m = URL_RX.search(json.dumps(e, ensure_ascii=False))
            url = m.group(0) if m else None
        licence = first(e, *LIC_KEYS)
        if isinstance(licence, dict):
            licence = first(licence, 'name', 'id', 'spdx')
        pack = first(e, 'pack', 'name', 'id', 'title')
        if isinstance(pack, list):
            pack = pack[0] if pack else None
        # a per-file row: one path with its size or hash (or no name of its own), grouped by pack below
        one = first(e, 'file', 'path')
        per_file = isinstance(one, str) and (any(k in e for k in ('bytes', 'sha256', 'size')) or not first(e, 'name', 'id', 'title'))
        source = infer_source(e, url)
        if per_file:
            name = pack or (re.sub(r',?\s*https?://\S+', '', str(e.get('source', ''))).strip() or source or 'files')
            key = ('group', str(name), str(licence), url or '')
        else:
            name = pack or where or 'asset'
            key = ('asset', str(name), where, len(assets))
        a = assets.get(key)
        if not a:
            a = OrderedDict(name=str(name), source=source or '', url=url or '', licence=str(licence or ''))
            for k_out, keys in (('author', ('author', 'authors', 'creator', 'publisher')), ('version', ('version',)),
                                ('licence_url', ('licence_url', 'license_url'))):
                v = first(e, *keys)
                if isinstance(v, list):
                    v = ', '.join(map(str, v))
                if v:
                    a[k_out] = str(v)
            if re.search(r'fab|marketplace', (a['source'] + a['licence']).lower()):
                a['store'] = True
            a['files'] = []
            v = first(e, 'used_for', 'used_as', 'used', 'use', 'purpose', 'note')
            if v:
                a['used_for'] = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            v = first(e, 'changes', 'modifications')
            if v:
                a['changes'] = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            a['_unresolved'] = []
            assets[key] = a
        for p in path_strings(e):
            got = R.resolve(p, a['name'])
            if got:
                a['files'] += [g for g in got if g not in a['files']]
            else:
                a['_unresolved'].append(p)
    # per-file groups: collapse to folders where every tracked file under the folder is the asset's
    out_assets = []
    for a in assets.values():
        fs = [f for f in a['files'] if not f.endswith('/')]
        dirs = [f for f in a['files'] if f.endswith('/')]
        if len(fs) > 20:
            mine = set(fs)
            by_dir = {}
            for f in fs:
                parts = f.split('/')
                for depth in (2, 3):
                    if len(parts) > depth:
                        by_dir.setdefault('/'.join(parts[:depth]) + '/', []).append(f)
            chosen = []
            for d in sorted(by_dir, key=len):
                if any(d.startswith(c) for c in chosen):
                    continue
                under = [t for t in files if t.startswith(d)]
                if under and all(t in mine for t in under):
                    chosen.append(d)
            fs = [f for f in fs if not any(f.startswith(c) for c in chosen)]
            dirs += chosen
        a['files'] = sorted(set(dirs)) + sorted(set(fs))
        unresolved = a.pop('_unresolved')
        need = [w for w, ok in (('url', a['url']), ('licence', a['licence']), ('files', a['files'])) if not ok]
        if need:
            person.append({'asset': a['name'], 'missing': need, 'unresolved_paths': unresolved[:5]})
        if not a['url']:
            a.pop('url')
        if not a['source']:
            a['source'] = 'unknown'
        out_assets.append(a)
    new = OrderedDict(schema='assets-manifest/v1', project=project, assets=out_assets)
    return new, left_out, person, len(entries)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('repo')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--json')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    old = json.load(open(os.path.join(repo, 'assets.manifest.json'), encoding='utf-8-sig'))
    if isinstance(old, dict) and old.get('schema') == 'assets-manifest/v1':
        print('already assets-manifest/v1')
        return 0
    new, left_out, person, n = convert(repo)
    text = json.dumps(new, indent=2, ensure_ascii=False) + '\n'
    nfiles = sum(len(x['files']) for x in new['assets'])
    print(f'{os.path.basename(repo)}: {n} licence-bearing objects -> {len(new["assets"])} assets, {nfiles} repo paths; '
          f'{len(left_out)} engine-shipped or made-here left out; {len(person)} need a person')
    for p in person:
        print(f'  needs a person: {p["asset"]}: missing {", ".join(p["missing"])}' + (f'; unresolved paths e.g. {p["unresolved_paths"]}' if p['unresolved_paths'] else ''))
    if a.show:
        print(text)
    if a.json:
        open(a.json, 'w', encoding='utf-8', newline='\n').write(text)
    if a.write:
        dst = os.path.join(repo, 'assets.manifest.json')
        legacy = os.path.join(repo, 'assets.manifest.legacy.json')
        if not os.path.exists(legacy):
            os.replace(dst, legacy)
        open(dst, 'w', encoding='utf-8', newline='\n').write(text)
        print(f'written {dst} (previous: {legacy}, not tracked; delete it once the new file is reviewed)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

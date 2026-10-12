"""Remove the user name and the agent / vendor names from a UE 5.3 project's assets (the packager's blocking terms).

Assets remember where they were imported from and who made them: AssetImportData (textures, static/skeletal meshes,
sounds, animations, data tables, ...), FontFace.SourceFilename, Interchange node ids, a Level Sequence's
MovieSceneMetaData author (the OS user name), a MetaSound's author (e.g. "Claude (agent)" from the script that made
it). Imports made from C:\\Users\\<name>\\... keep that path in the .uasset files of the project (the cook strips
AssetImportData, but the project/source files we ship keep it; FontFace's SourceFilename even reaches the cooked font).

Driven by a byte scan (terms(): the user name as a substring anywhere except the packager's allowlist, "claude",
"anthropic"; case-insensitive, ASCII and UTF-16LE, streamed). Only packages with hits are loaded. In each:
  - every import-source filename under the user profile becomes a path inside the project, if the file is inside the
    project (stored package-relative by UE), or just the file name otherwise;
  - a Level Sequence author containing the user name becomes "dev".
Packages are saved only when something changed; anything still matching afterwards is reported, and --patch-remaining
rewrites what is left in path segments and author fields (same length); a match anywhere else (e.g. story text) stays
UNHANDLED for a person.

Run headless (no GPU, no game window; the editor target of the project must be built):

  UnrealEditor-Cmd.exe <Project>.uproject -run=pythonscript -script="<this file> --apply" -nullrhi -unattended -nopause -nosplash -stdout

  modes: (default) dry run: report what would change
         --apply    change and save the assets
         --patch-remaining  after --apply, in a new run: same-length byte rewrite of what no editor API can reach
                    (Interchange node ids, MetaSound authors; see patch_remaining), then load-test every patched package
         --verify   byte scan only: list remaining hits (expect 0; the packager's allowlist zh_XIANG / zh-xiang / wuxiangshan is skipped)
  options: --original-project-dir=<dir>  also treat files under <dir> as "inside the project" (when running on a copy
                                          of a project whose assets were imported in its original location)
           --report=<file.json>          write the per-asset report as JSON (default: <Project>/Saved/scrub-import-paths.json)

FontFace.SourceFilename is written with notify_mode NEVER: FontFace::PostEditChangeProperty reloads the font data and
crashes in a headless commandlet. AssetImportData goes through ScriptedAddFilename, which also re-reads the timestamp
and MD5 of the new path (a bare file name has none: the editor then just asks for the file on reimport).
"""
import json
import os
import sys

try:
    import unreal
except ImportError:  # --verify can run outside the editor too
    unreal = None


def log(msg):
    # print() doesn't reach the commandlet log (-run=pythonscript); unreal.log does (LogPython).
    line = 'scrub-import-paths: ' + msg
    if unreal is None:
        print(line)
    elif msg.startswith(('UNHANDLED', 'REMAINING', 'LOAD FAILED', 'HIT ')):
        unreal.log_warning(line)
    else:
        unreal.log(line)


def user_profile():
    return os.path.normcase(os.path.normpath(os.environ.get('USERPROFILE') or os.path.join('C:\\Users', os.environ.get('USERNAME', ''))))


# ---- what must not stay in a project's assets (the packager's blocking terms that occur in asset data) ----------------
# The user name as a substring anywhere (allowlist: the engine's zh_XIANG / zh-xiang locale ids and the place name
# wuxiangshan, as in the packager), and the agent / vendor names. Each is matched case-insensitively in ASCII and
# UTF-16LE. A match is rewritten (same length, see patch_remaining) only in a safe context: a path segment (/x/, \x\,
# -x-: import paths, Interchange node ids, temp paths) or a whole serialized FString (an author field); anything else,
# e.g. the name inside story text, is reported as UNHANDLED for a person to fix.

class Term(object):
    def __init__(self, label, text, rep, allow_prefixes=()):
        self.label, self.text, self.rep, self.allow = label, text, rep, allow_prefixes


def terms():
    name = os.environ.get('USERNAME', '')
    out = []
    if name:
        out.append(Term('username', name, placeholder(len(name)), ('zh_', 'zh-', 'wu')))
    out += [Term('agent-name', 'Claude (agent)', 'Developer team'), Term('agent-name', 'claude', 'helper'),
            Term('vendor-name', 'anthropic', 'assistant')]
    return out


def byte_patterns():
    """[(label, width, lower pattern bytes, term)] for both encodings, longest first."""
    pats = []
    for tm in terms():
        for width, enc in ((1, 'ascii'), (2, 'utf-16-le')):
            pats.append(('%s%s' % (tm.label, ' (utf-16)' if width == 2 else ''), width, tm.text.lower().encode(enc), tm))
    pats.sort(key=lambda x: -len(x[2]))
    return pats


CHUNK = 8 * 1024 * 1024   # files are streamed: never read a whole (possibly multi-GB) file into memory
CTX_BEFORE, CTX_AFTER = 4, 2


def _seps(width):
    return [c.encode('ascii' if width == 1 else 'utf-16-le') for c in ('/', '\\', '-')]


def _context(low, i, nb, width, n_chars):
    """'path', 'fstring' or None for a match at low[i:i+nb]."""
    before, after = low[max(0, i - width):i], low[i + nb:i + nb + width]
    seps = _seps(width)
    if before in seps and after in seps:
        return 'path'
    if i >= 4:
        ln = int.from_bytes(low[i - 4:i], 'little', signed=True)
        if (width == 1 and ln == n_chars + 1 and after == b'\x00') or (width == 2 and ln == -(n_chars + 1) and after == b'\x00\x00'):
            return 'fstring'
    return None


def _matches(low, lo, hi, pats, claimed):
    """Matches starting in [lo, hi) of `low`: [(i, nb, label, width, term, context)], longest terms first, skipping
    allowlisted ones and positions inside an earlier (longer) match of the same buffer (claimed)."""
    out = []
    for label, width, b, tm in pats:
        i = low.find(b, lo)
        while i != -1 and i < hi:
            enc = 'ascii' if width == 1 else 'utf-16-le'
            allow = any(low[max(0, i - len(a) * width):i] == a.encode(enc) for a in tm.allow)
            if not allow and not any(s <= i < e for s, e in claimed):
                out.append((i, len(b), label, width, tm, _context(low, i, len(b), width, len(tm.text))))
                claimed.append((i, i + len(b)))
            i = low.find(b, i + 1)
    return out


def _stream(path, pats, patch_to=None):
    """Walk the file in CHUNK pieces; returns ({label: count}, unpatchable count, rewritten count). With patch_to,
    writes the file with every safe-context match rewritten (same length) to that path. Each buffer is the carried
    tail plus the next chunk; matches starting before `lo` were handled in the previous buffer, matches starting past
    `cutoff` wait for the next one (so every match has its context bytes and is handled exactly once)."""
    maxlen = max(len(b) for _l, _w, b, _t in pats)
    counts, unpatchable, rewritten = {}, 0, 0
    dst = open(patch_to, 'wb') if patch_to else None
    try:
        with open(path, 'rb') as f:
            pending = b''
            lo = 0
            while True:
                chunk = f.read(CHUNK)
                eof = not chunk
                buf = bytearray(pending + chunk)
                low = bytes(buf).lower()   # lower(): ASCII letters only; UTF-16LE NUL bytes are unaffected
                cutoff = len(buf) if eof else max(lo, len(buf) - (maxlen + CTX_AFTER))
                for i, nb, label, width, tm, ctx in _matches(low, lo, cutoff, pats, []):
                    counts[label] = counts.get(label, 0) + 1
                    if ctx is None:
                        unpatchable += 1
                        continue
                    if dst is not None:
                        rep = tm.rep[:1].upper() + tm.rep[1:] if bytes(buf[i:i + 1]).isupper() else tm.rep
                        buf[i:i + nb] = rep.encode('ascii' if width == 1 else 'utf-16-le')
                        rewritten += 1
                if eof:
                    if dst is not None:
                        dst.write(buf)
                    break
                cut = max(0, cutoff - CTX_BEFORE)
                if dst is not None:
                    dst.write(buf[:cut])
                pending = bytes(buf[cut:])
                lo = cutoff - cut
    finally:
        if dst is not None:
            dst.close()
    return counts, unpatchable, rewritten


def count_in_file(path, pats):
    """{label: count} of blocked terms in the file (streamed); key 'unpatchable' counts matches outside safe contexts."""
    counts, unpatchable, _ = _stream(path, pats)
    if unpatchable:
        counts['unpatchable'] = unpatchable
    return counts


def scan(content_dir):
    """Files under content_dir containing the user name in a path; {path: {pattern: count}}."""
    pats = byte_patterns()
    hits = {}
    for root, _dirs, files in os.walk(content_dir):
        for fn in files:
            if not fn.lower().endswith(('.uasset', '.umap', '.uexp')):
                continue
            p = os.path.join(root, fn)
            try:
                found = count_in_file(p, pats)
            except (OSError, MemoryError) as e:
                log('UNREADABLE %s: %s' % (p, e))
                continue
            if found:
                hits[p] = found
    return hits


def package_name(path, content_dir):
    rel = os.path.relpath(path, content_dir)
    return '/Game/' + os.path.splitext(rel)[0].replace('\\', '/')


def under(path, root):
    p = os.path.normcase(os.path.normpath(path))
    r = os.path.normcase(os.path.normpath(root)).rstrip('\\/')
    return p == r or p.startswith(r + os.sep)


def remap(path, project_dir, original_dirs):
    """(new path for AssetImportData, new string for FontFace) for a source file under the user profile."""
    for root in [project_dir] + original_dirs:
        if under(path, root):
            rel = os.path.relpath(os.path.normpath(path), os.path.normpath(root))
            return os.path.join(project_dir, rel), rel.replace('\\', '/')
    base = os.path.basename(os.path.normpath(path))
    return base, base


def import_labels(asset_path):
    """Display labels of the source files (multi-source meshes), from the asset registry's AssetImportData JSON tag."""
    try:
        data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        tag = data.get_tag_value('AssetImportData')
        return [e.get('DisplayLabelName', '') for e in json.loads(str(tag))] if tag else []
    except Exception:
        return []


def fix_asset(asset, pkg, project_dir, original_dirs, apply):
    """Returns a list of {kind, index, old, new} for one loaded asset."""
    changes = []
    profile = user_profile()
    try:
        aid = asset.get_editor_property('asset_import_data')
    except Exception:
        aid = None
    if aid is not None:
        files = [str(f) for f in aid.extract_filenames()]
        labels = import_labels(pkg) if any(under(f, profile) for f in files) else []
        for i, f in enumerate(files):
            if not under(f, profile):
                continue
            new_path, _ = remap(f, project_dir, original_dirs)
            changes.append({'kind': 'AssetImportData', 'index': i, 'old': f, 'new': new_path})
            if apply:
                aid.scripted_add_filename(new_path, i, labels[i] if i < len(labels) else '')
    # Level Sequences store their creator (the OS user name) as MovieSceneMetaData Author, also as an asset registry tag.
    if hasattr(unreal, 'LevelSequence') and isinstance(asset, unreal.LevelSequence):
        try:
            md = asset.find_meta_data_by_class(unreal.MovieSceneMetaData)
        except Exception:
            md = None
        name = os.environ.get('USERNAME', '').lower()
        author = str(md.get_author()) if md is not None else ''
        if md is not None and name and name in author.lower():
            changes.append({'kind': 'MovieSceneMetaData.Author', 'index': 0, 'old': author, 'new': 'dev'})
            if apply:
                asset.modify()
                md.modify()
                md.set_author('dev')
    if isinstance(asset, unreal.FontFace):
        sf = str(asset.get_editor_property('source_filename') or '')
        if sf and under(sf, profile):
            _, new_str = remap(sf, project_dir, original_dirs)
            changes.append({'kind': 'FontFace.SourceFilename', 'index': 0, 'old': sf, 'new': new_str})
            if apply:
                asset.modify()
                asset.set_editor_property('source_filename', new_str, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    return changes


def placeholder(n):
    """Same-length stand-in for the user name: 'user_' for 5 letters, 'user' + underscores for more, 'u..' for fewer."""
    return ('user' + '_' * max(0, n - 4))[:n] if n >= 4 else 'u' * n


def patch_remaining(hits, content_dir, project_dir):
    """Same-length rewrite of the blocked terms in safe contexts (see terms()) in the files still matching.

    For data no editor API can rewrite: Interchange-imported assets keep the source path inside node unique ids
    (NodeUniqueID, a VisibleAnywhere property Python can't set, and the cached node container), e.g.
    "Factory_C:/Users/<name>/.../T.png"; MetaSound documents keep their author ("Claude (agent)") with no script API in
    5.3. Keeping the length keeps every FString length and package offset valid; UE5 discards the name map's serialized
    hashes on load. Must run before the packages are loaded in this process.
    """
    pats = byte_patterns()
    patched = []
    for path in sorted(hits):
        tmp = path + '.scrubtmp'
        size_in = os.path.getsize(path)
        counts, unpatchable, n = _stream(path, pats, patch_to=tmp)
        if n and os.path.getsize(tmp) == size_in:
            os.replace(tmp, path)
            patched.append({'file': os.path.relpath(path, project_dir), 'package': package_name(path, content_dir),
                            'rewritten': n, 'left_unpatchable': unpatchable, 'terms': counts})
            log('PATCHED %s (%d rewritten%s)' % (os.path.relpath(path, project_dir), n,
                ', %d left: not in a path or author field' % unpatchable if unpatchable else ''))
        else:
            os.remove(tmp)
            if unpatchable:
                log('UNHANDLED %s: %d matches not in a path or author field (fix by hand): %s' % (
                    os.path.relpath(path, project_dir), unpatchable, json.dumps(counts)))
    return patched


def main(argv):
    apply = '--apply' in argv
    verify = '--verify' in argv
    patch = '--patch-remaining' in argv
    original_dirs = [a.split('=', 1)[1] for a in argv if a.startswith('--original-project-dir=')]
    report_arg = [a.split('=', 1)[1] for a in argv if a.startswith('--report=')]
    if unreal is not None:
        project_dir = os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
        content_dir = os.path.normpath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    else:
        content_dir = os.path.normpath([a for a in argv if not a.startswith('--')][0])
        project_dir = os.path.dirname(content_dir)
    log('project %s, user profile %s, mode %s' % (project_dir, user_profile(), 'verify' if verify else ('apply' if apply else 'dry run')))

    hits = scan(content_dir)
    total = sum(sum(c.values()) for c in hits.values())
    if verify or unreal is None:
        for p, c in sorted(hits.items()):
            log('HIT %s %s' % (os.path.relpath(p, project_dir), json.dumps(c)))
        log('verify: %d hits in %d files' % (total, len(hits)))
        return 1 if hits else 0

    log('%d files with %d hits before' % (len(hits), total))
    if patch:
        patched = patch_remaining(hits, content_dir, project_dir)
        for p in patched:   # first load in this process: proves the patched package still loads
            asset = unreal.EditorAssetLibrary.load_asset(p['package']) if unreal is not None else None
            p['loads'] = asset is not None
            p['class'] = asset.get_class().get_name() if asset is not None else None
            if asset is None:
                log('LOAD FAILED after patch: %s' % p['package'])
        after = scan(content_dir)
        report = {'project': project_dir, 'mode': 'patch_remaining', 'files_with_hits_before': len(hits), 'hits_before': total,
                  'patched': patched, 'load_failures': [p['package'] for p in patched if not p['loads']],
                  'files_with_hits_after': len(after), 'hits_after': sum(sum(c.values()) for c in after.values()),
                  'remaining': [os.path.relpath(p, project_dir) for p in sorted(after)]}
        out = report_arg[0] if report_arg else os.path.join(project_dir, 'Saved', 'scrub-import-paths-patch.json')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=1, ensure_ascii=False)
        log('patched %d files, %d load failures, %d hits left in %d files; report %s' % (
            len(patched), len(report['load_failures']), report['hits_after'], report['files_with_hits_after'], out))
        return 1 if report['load_failures'] else 0
    report = {'project': project_dir, 'mode': 'apply' if apply else 'dry_run', 'files_with_hits_before': len(hits),
              'hits_before': total, 'assets': []}
    changed_assets = 0
    changed_entries = 0
    for path in sorted(hits):
        pkg = package_name(path, content_dir)
        entry = {'package': pkg, 'file': os.path.relpath(path, project_dir), 'hits': hits[path], 'changes': [], 'saved': False}
        try:
            asset = unreal.EditorAssetLibrary.load_asset(pkg)
        except Exception as e:
            asset = None
            entry['error'] = 'load failed: %s' % e
        if asset is not None:
            try:
                entry['class'] = asset.get_class().get_name()
                entry['changes'] = fix_asset(asset, pkg, project_dir, original_dirs, apply)
                if apply and entry['changes']:
                    entry['saved'] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, False))
            except Exception as e:
                entry['error'] = 'fix failed: %s' % e
        for c in entry['changes']:
            log('%s %s [%s %d] %s -> %s' % ('CHANGED' if apply else 'WOULD CHANGE', pkg, c['kind'], c['index'], c['old'], c['new']))
        if not entry['changes']:
            log('UNHANDLED %s (%s): %s%s' % (pkg, entry.get('class', '?'), json.dumps(hits[path]), (' - ' + entry['error']) if 'error' in entry else ''))
        changed_assets += 1 if entry['changes'] else 0
        changed_entries += len(entry['changes'])
        report['assets'].append(entry)

    report['assets_changed'] = changed_assets
    report['paths_changed'] = changed_entries
    if apply:
        after = scan(content_dir)
        report['files_with_hits_after'] = len(after)
        report['hits_after'] = sum(sum(c.values()) for c in after.values())
        report['remaining'] = [os.path.relpath(p, project_dir) for p in sorted(after)]
        for p in report['remaining']:
            log('REMAINING %s' % p)
    out = report_arg[0] if report_arg else os.path.join(project_dir, 'Saved', 'scrub-import-paths.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    log('%s: %d paths in %d assets%s; report %s' % ('changed' if apply else 'would change', changed_entries, changed_assets,
        (', %d hits left in %d files' % (report['hits_after'], report['files_with_hits_after'])) if apply else '', out))
    return 0


if __name__ == '__main__':
    rc = main(sys.argv[1:])
    if unreal is None:
        sys.exit(rc)

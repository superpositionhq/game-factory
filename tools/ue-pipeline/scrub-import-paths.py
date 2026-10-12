"""Remove the user's profile path from a UE 5.3 project's editor-only import-source paths.

Assets remember where they were imported from: AssetImportData (textures, static/skeletal meshes, sounds, animations,
data tables, ...) and FontFace.SourceFilename. Imports made from C:\\Users\\<name>\\... keep that path in the .uasset
files of the project (the cook strips AssetImportData, but the project/source files we ship keep it; FontFace's
SourceFilename even reaches the cooked font).

Driven by a byte scan: every Content/**/*.uasset|umap|uexp is searched for \\<name>\\ and /<name>/ (case-insensitive,
ASCII and UTF-16LE). Only packages with hits are loaded. In each, every import-source filename under the user profile
becomes
  - a path inside the project, if the file is inside the project (stored package-relative by UE), or
  - just the file name otherwise.
Packages are saved only when something changed; anything still matching afterwards is reported as unhandled.

Run headless (no GPU, no game window; the editor target of the project must be built):

  UnrealEditor-Cmd.exe <Project>.uproject -run=pythonscript -script="<this file> --apply" -nullrhi -unattended -nopause -nosplash -stdout

  modes: (default) dry run: report what would change
         --apply    change and save the assets
         --patch-remaining  after --apply, in a new run: same-length byte rewrite of what no editor API can reach
                    (Interchange node ids, see patch_remaining), then load-test every patched package
         --verify   byte scan only: list remaining hits (expect 0; engine ids such as zh_XIANG don't match path patterns)
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


def byte_patterns():
    name = os.environ.get('USERNAME', '').lower()
    out = []
    for text in ('\\%s\\' % name, '/%s/' % name):
        out.append((text, text.encode('ascii')))
        out.append((text + ' (utf-16)', text.encode('utf-16-le')))
    return out


CHUNK = 8 * 1024 * 1024   # files are streamed: never read a whole (possibly multi-GB) file into memory


def count_in_file(path, pats):
    """{label: count} of each byte pattern in the file, case-insensitive (ASCII letters), streamed in CHUNK pieces.

    The buffer is the previous chunk's last (longest pattern - 1) bytes plus the new chunk; only matches that end
    inside the new chunk are counted, so a match is never counted twice and none is lost at a chunk boundary.
    """
    keep = max(len(b) for _l, b in pats) - 1
    counts = dict((label, 0) for label, _b in pats)
    tail = b''
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            buf = tail + chunk.lower()   # lower(): ASCII letters only; UTF-16LE NUL bytes are unaffected
            for label, b in pats:
                i = buf.find(b)
                while i != -1:
                    if i + len(b) > len(tail):
                        counts[label] += 1
                    i = buf.find(b, i + 1)
            tail = buf[-keep:] if keep > 0 else b''
    return dict((k, v) for k, v in counts.items() if v)


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
    """Same-length byte rewrite of \\<name>\\ and /<name>/ (ASCII and UTF-16LE) in the files still matching.

    For data no editor API can rewrite: Interchange-imported assets (UInterchangeAssetImportData) keep the source path
    inside node unique ids (NodeUniqueID, a VisibleAnywhere property Python can't set, and the cached node container),
    e.g. "Factory_C:/Users/<name>/.../T.png". Keeping the length keeps every FString length and package offset valid;
    UE5 discards the name map's serialized hashes on load. Must run before the packages are loaded in this process.
    """
    import re
    name = os.environ.get('USERNAME', '')
    rep = placeholder(len(name)).encode('ascii')
    a = re.compile(rb'([\\/])' + re.escape(name.encode('ascii')) + rb'([\\/])', re.IGNORECASE)
    w = re.compile(b''.join(re.escape(bytes([c, 0])) if not chr(c).isalpha() else
                            b'[' + bytes([ord(chr(c).lower()), ord(chr(c).upper())]) + b']\x00'
                            for c in name.encode('ascii')))
    w_full = re.compile(rb'([\\/]\x00)' + w.pattern + rb'([\\/]\x00)')
    rep_w = b''.join(bytes([c, 0]) for c in rep)
    keep = 2 * (len(name) + 2) - 1   # longest match (UTF-16 \name\) minus one byte, carried to the next chunk
    patched = []
    for path in sorted(hits):
        # Streamed: each buffer is the carried tail plus the next chunk; the last `keep` bytes are held back so a
        # match across the boundary is found whole next time. Replacements keep the length and no longer match.
        tmp = path + '.scrubtmp'
        n1 = n2 = 0
        size_in = os.path.getsize(path)
        with open(path, 'rb') as src, open(tmp, 'wb') as dst:
            pending = b''
            while True:
                chunk = src.read(CHUNK)
                buf = pending + chunk
                while True:   # repeat: "/name/name/" shares a separator, one pass leaves the second
                    buf, c1 = a.subn(lambda m: m.group(1) + rep + m.group(2), buf)
                    buf, c2 = w_full.subn(lambda m: m.group(1) + rep_w + m.group(m.lastindex), buf)
                    n1 += c1; n2 += c2
                    if not (c1 or c2):
                        break
                if not chunk:
                    dst.write(buf)
                    break
                dst.write(buf[:-keep]); pending = buf[-keep:]
        if (n1 or n2) and os.path.getsize(tmp) == size_in:
            os.replace(tmp, path)
            patched.append({'file': os.path.relpath(path, project_dir), 'package': package_name(path, content_dir), 'ascii': n1, 'utf16': n2})
            log('PATCHED %s (%d ascii, %d utf-16 occurrences -> /%s/)' % (os.path.relpath(path, project_dir), n1, n2, rep.decode()))
        else:
            os.remove(tmp)
            if n1 or n2:
                log('UNHANDLED (rewrite would change the size, not patched): %s' % os.path.relpath(path, project_dir))
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

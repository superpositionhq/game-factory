#!/usr/bin/env python3
"""Sound effects for a game from Freesound (sound skill): search, fetch into the game repo, measure.

  python sfx.py search "<English query>" [--license cc0|by] [--sort relevance|downloads|rating|short] [-n N] [--pages K] [--urls]
  python sfx.py get <repo> --used-for "<cue>" [--mono] fs:<id> [fs:<id> ...]
  python sfx.py measure <file.wav> [...]

search lists only CC0 and CC BY clips; relevance (the default) is several relevance pages re-ranked by downloads.
get re-reads each clip's licence from its page and refuses anything else, decodes its preview to 16-bit WAV in
RawAssets/Audio/SFX/, and adds it to assets.manifest.json and Docs/ThirdPartyNotices.md.
measure prints what the ear would tell: length, level, attack and tail. Python standard library + ffmpeg only.
"""
import argparse, array, html, json, math, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SITE = 'https://freesound.org'
UA = {'User-Agent': 'sfx.py (game audio search)'}
SFX_DIR = 'RawAssets/Audio/SFX'
FACET = {'cc0': '"Creative Commons 0"', 'by': '("Attribution" OR "Creative Commons 0")'}
SORT = {'relevance': 'Automatic by relevance', 'downloads': 'Downloads (most first)',
        'rating': 'Rating (highest first)', 'short': 'Duration (shortest first)'}
SHORT = {'Creative Commons 0': 'CC0', 'Attribution': 'BY'}
LICENCE = re.compile(r'creativecommons\.org/(publicdomain/zero|licenses/by)/([\d.]+)/?$')


def fetch(url, timeout=120, tries=5):
    """(body, final url). Freesound answers 429 to pages asked for in parallel or in quick succession: wait and retry."""
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read(), r.url
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == tries - 1:
                raise
            time.sleep(int(e.headers.get('Retry-After') or 0) or 5 * (n + 1))


def attr(name, text):
    m = re.search(rf'data-{name}="([^"]*)"', text)
    return html.unescape(m[1]) if m else ''


def hq(preview):
    return preview.replace('-lq.mp3', '-hq.mp3')


def search(a):
    # Several relevance pages re-ranked by downloads: sorting by downloads on the server lets popular sounds win on a
    # loose tag match.
    q = {'q': a.query, 's': SORT[a.sort], 'f': 'license:' + FACET[a.license]}
    urls = [f'{SITE}/search/?' + urllib.parse.urlencode({**q, 'page': n}) for n in range(1, a.pages + 1)]
    pages = [fetch(u)[0].decode('utf-8') for u in urls]
    rows = []
    for block in (b for p in pages for b in p.split('class="bw-search__result"')[1:]):
        lic = re.search(r'title="License: ([^"]+)"', block)
        lic = html.unescape(lic[1]) if lic else ''
        if lic not in SHORT:  # the facet should already exclude these; only CC0 and BY may reach a game
            continue
        rating = re.search(r'aria-label="Average rating of ([\d.]+)"', block)
        votes = re.search(r'bw-rating__count[^>]*>\((\d+)\)', block)
        desc = re.search(r'<div class="max-h-60px[^"]*"\s*>\s*(.*?)\s*</div>', block, re.S)
        rows.append({'key': 'fs:' + attr('sound-id', block), 'title': attr('title', block),
                     'dur': float(attr('duration', block) or 0), 'downloads': int(attr('num-downloads', block) or 0),
                     'rating': f'{rating[1]}({votes[1]})' if rating and votes else '-', 'licence': SHORT[lic],
                     'desc': html.unescape(re.sub(r'<[^>]+>|\s+', ' ', desc[1])).strip()[:120] if desc else '',
                     'preview': hq(attr('mp3', block))})
    seen = {}
    for r in rows:
        seen.setdefault(r['key'], r)
    rows = list(seen.values())
    if a.sort == 'relevance':
        rows.sort(key=lambda r: -r['downloads'])
    for r in rows[:a.n]:
        print('\t'.join([r['key'], r['title'], f"{r['dur']:.2f}s", f"dl={r['downloads']}", f"rating={r['rating']}",
                         r['licence'], r['desc']] + ([r['preview']] if a.urls else [])))
    if not rows:
        print('(none)')


def ffmpeg():
    pinned = Path(__file__).resolve().parents[2] / 'tools/ffmpeg-8.1.2/ffmpeg-8.1.2-full_build/bin/ffmpeg.exe'
    exe = str(pinned) if pinned.exists() else shutil.which('ffmpeg')
    if not exe:
        sys.exit(f'ffmpeg not found: {pinned} (machine/get-ffmpeg.ps1)')
    return exe


def read_sound(key):
    """Everything about one clip comes from its own page: the search listing is never trusted for the licence."""
    m = re.fullmatch(r'fs:(\d+)', key)
    if not m:
        raise ValueError('keys look like fs:<id>')
    body, url = fetch(f'{SITE}/s/{m[1]}/')
    page = body.decode('utf-8')
    href = re.search(r'title="Go to the full license text" href="([^"]+)"', page)
    lic = LICENCE.search(href[1]) if href else None
    if not lic:
        raise ValueError(f'licence {href[1] if href else "not found"}: only CC0 and CC BY may ship in a game')
    artist = re.search(r'property="og:audio:artist" content="([^"]*)"', page)
    return {'id': m[1], 'title': attr('title', page), 'author': html.unescape(artist[1]) if artist else '', 'url': url,
            'preview': hq(attr('mp3', page)), 'licence': ('CC0 ' if 'zero' in lic[1] else 'CC BY ') + lic[2],
            'licence_url': 'https://' + lic[0]}


def fetch_wav(s, repo, mono):
    slug = re.sub(r'\W+', '-', Path(s['title']).stem).strip('-')[:40]
    rel = f"{SFX_DIR}/fs_{s['id']}_{slug}.wav"
    if not (repo / rel).exists():
        (repo / SFX_DIR).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / 'preview.mp3'
            mp3.write_bytes(fetch(s['preview'], timeout=300)[0])
            subprocess.run([ffmpeg(), '-v', 'error', '-y', '-i', str(mp3), '-map_metadata', '-1', '-bitexact',
                            *(['-ac', '1'] if mono else []), '-c:a', 'pcm_s16le', str(repo / rel)], check=True)
    return rel


def get(a):
    repo = Path(a.repo)
    manifest_path = repo / 'assets.manifest.json'
    if not manifest_path.exists():
        sys.exit(f'{manifest_path}: not a game repo')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

    def attempt(fn, *args):  # one bad clip doesn't sink the batch
        try:
            return fn(*args), None
        except Exception as e:
            return None, e

    # The site's pages one at a time; the previews come from its CDN, capped at about 80 KB/s per connection, so in parallel.
    sounds = [attempt(read_sound, key) for key in a.keys]
    failed = False
    notices = []
    with ThreadPoolExecutor(6) as ex:
        wavs = ex.map(lambda r: attempt(fetch_wav, r[0], repo, a.mono) if r[0] else (None, r[1]), sounds)
        for key, (s, _), (rel, err) in zip(a.keys, sounds, wavs):
            if err:
                failed = True
                print(f'FAIL {key}: {err}')
                continue
            print(f"{rel}\t{s['licence']}\t{s['author']}")
            if any(x.get('url') == s['url'] for x in manifest['assets']):
                continue
            changes = 'preview MP3 decoded to 16-bit WAV' + (', downmixed to mono' if a.mono else '')
            manifest['assets'].append({'name': s['title'], 'source': 'Freesound', 'url': s['url'], 'author': s['author'],
                                       'licence': s['licence'], 'licence_url': s['licence_url'], 'store': False,
                                       'files': [rel], 'used_for': a.used_for, 'changes': changes})
            notices.append(f"\n## {s['title']}\n\n{s['author']}, {s['url']}. {s['licence']} ({s['licence_url']}). "
                           f"File: `{rel}`. Used for {a.used_for}. Changes: {changes}.\n")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if notices:
        path = repo / 'Docs/ThirdPartyNotices.md'
        path.parent.mkdir(exist_ok=True)
        with path.open('a', encoding='utf-8', newline='\n') as f:
            f.write(''.join(notices))
    if failed:
        sys.exit(1)


def db(v):
    return 20 * math.log10(v) if v > 0 else -120.0


def measure(a):
    print('file\tseconds\tchannels\trate\tpeak_db\trms_db\tattack_ms\ttail_ms')
    for name in a.files:
        with wave.open(name, 'rb') as w:
            if w.getsampwidth() != 2:
                sys.exit(f'{name}: expected 16-bit PCM')
            ch, rate = w.getnchannels(), w.getframerate()
            samples = array.array('h', w.readframes(w.getnframes()))
        if sys.byteorder == 'big':
            samples.byteswap()
        if not samples:
            print(f'{name}\t0.00\t{ch}\t{rate}\t\t\t\t')
            continue
        level = [abs(x) / 32768 for x in samples]
        peak = max(level)
        first = next(i for i, x in enumerate(level) if x >= peak / 2)  # attack: until half the peak (-6 dB)
        floor = peak / 100
        last = next(i for i in range(len(level) - 1, -1, -1) if level[i] >= floor)  # tail: after 40 dB below the peak
        rms = math.sqrt(sum(x * x for x in level) / len(level))
        to_ms = 1000 / (ch * rate)
        print(f'{name}\t{len(level) / (ch * rate):.2f}\t{ch}\t{rate}\t{db(peak):.1f}\t{db(rms):.1f}\t'
              f'{first * to_ms:.0f}\t{(len(level) - 1 - last) * to_ms:.0f}')


def main():
    for stream in (sys.stdout, sys.stderr):  # clip titles in any script, on any Windows console code page
        stream.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('search')
    s.add_argument('query')
    s.add_argument('--license', choices=FACET, default='by')
    s.add_argument('--sort', choices=SORT, default='relevance')
    s.add_argument('-n', type=int, default=8)
    s.add_argument('--pages', type=int, default=3, help='relevance pages (15 each) to rank by downloads')
    s.add_argument('--urls', action='store_true', help='add preview links for a person to audition')
    s.set_defaults(fn=search)
    g = sub.add_parser('get')
    g.add_argument('repo')
    g.add_argument('--used-for', required=True, help='the cue, for the manifest')
    g.add_argument('--mono', action='store_true', help='downmix: for sounds placed in the world')
    g.add_argument('keys', nargs='+')
    g.set_defaults(fn=get)
    m = sub.add_parser('measure')
    m.add_argument('files', nargs='+')
    m.set_defaults(fn=measure)
    a = ap.parse_args()
    try:
        a.fn(a)
    except OSError as e:
        sys.exit(f"network error: {getattr(e, 'reason', e)} (check the terminal's proxy settings and that freesound.org answers)")


if __name__ == '__main__':
    main()

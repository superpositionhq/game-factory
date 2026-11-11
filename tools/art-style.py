#!/usr/bin/env python3
"""A game's art style from the style library docs/art-styles/ (game-session skill, "Art style").

  python art-style.py list [--genre <slug> ...]
  python art-style.py pick [--genre <slug> ...] [--games <dir>]
  python art-style.py use <id> <game repo>

list prints the styles (all, or those that fit every genre given) with their genres and moods.
pick prints one style chosen at random: among the styles that fit the genres when any are given, among all of them
otherwise. Styles that fewer games under --games (default <root>/games) already use come first, so a run of games does
not repeat a look.
use writes the style's guide to <game repo>/Docs/ArtStyle.md, the game's art bible: the references, the visual
definition, the engine recipe and the do / do not list, with the other styles it names written by name.
Python standard library only.
"""
import argparse, json, os, random, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STYLES = REPO / 'docs' / 'art-styles'
BIBLE = 'Docs/ArtStyle.md'
HEAD = re.compile(r'^# Art style (\d{3}):')
DROP = ('## Fits', '## Nearest styles')  # for choosing a style, of no use to the game that has one

sys.path.insert(0, str(REPO / 'machine' / 'lib'))


def load():
    return json.loads((STYLES / 'styles.json').read_text(encoding='utf-8'))


def genres(styles):
    return sorted({g for s in styles for g in s['genres']})


def fitting(styles, wanted):
    known = genres(styles)
    bad = [g for g in wanted if g not in known]
    if bad:
        sys.exit(f'unknown genre {", ".join(bad)}; the genres are: {", ".join(known)}')
    return [s for s in styles if all(g in s['genres'] for g in wanted)]


def used(games):
    """{style id: number of games under `games` whose art bible names it}."""
    n = {}
    for bible in Path(games).glob(f'*/{BIBLE}'):
        with open(bible, encoding='utf-8') as f:
            m = HEAD.match(f.readline())
        if m:
            n[m[1]] = n.get(m[1], 0) + 1
    return n


def row(s):
    return f'{s["id"]}  {s["name"]}  [{s["family"]}]  {", ".join(s["genres"])}  ({", ".join(s["moods"])})'


def cmd_list(a):
    for s in fitting(load(), a.genre):
        print(row(s))


def cmd_pick(a):
    pool = fitting(load(), a.genre)
    if not pool:
        sys.exit(f'no style fits all of: {", ".join(a.genre)}; pick with fewer genres')
    games = a.games
    if not games:
        import gfroot
        games = os.path.join(gfroot.root(), 'games')
    n = used(games) if os.path.isdir(games) else {}
    least = min(n.get(s['id'], 0) for s in pool)
    s = random.SystemRandom().choice([s for s in pool if n.get(s['id'], 0) == least])
    print(row(s))
    print(STYLES / f'{s["id"]}-{s["slug"]}.md')


def cmd_use(a):
    styles = {s['id']: s for s in load()}
    s = styles.get(a.id.zfill(3)) or sys.exit(f'no style {a.id}')
    game = Path(a.game)
    if not game.is_dir():
        sys.exit(f'no game repo at {game}')
    out, keep = [], True
    for line in (STYLES / f'{s["id"]}-{s["slug"]}.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('# '):
            line = f'# Art style {s["id"]}: {s["name"]}'
        elif line.startswith('## '):
            keep = line.strip() not in DROP
        if keep:
            out.append(re.sub(r'`(\d{3})`', lambda m: f'"{styles[m[1]]["name"]}"' if m[1] in styles else m[0], line))
    bible = game / BIBLE
    bible.parent.mkdir(parents=True, exist_ok=True)
    bible.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8', newline='\n')
    print(bible)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    for name, fn in (('list', cmd_list), ('pick', cmd_pick)):
        c = sub.add_parser(name)
        c.add_argument('--genre', action='append', default=[], help='a genre the style must fit (repeatable)')
        c.set_defaults(fn=fn)
    c.add_argument('--games', help='the folder of game repos whose styles count as used (default <root>/games)')
    c = sub.add_parser('use')
    c.add_argument('id')
    c.add_argument('game')
    c.set_defaults(fn=cmd_use)
    a = p.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()

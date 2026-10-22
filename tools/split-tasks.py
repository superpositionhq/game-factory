#!/usr/bin/env python3
"""Split a game's tasks into the agent's part and the grader's part (dataset layout v1.3 Tasks/).

    python tools/split-tasks.py <tasks dir> <out dir>      # <tasks dir>: <name>.json, one GameTask each

For every task writes <out>/<name>/task.json (everything the agent may see: name, title, instruction, engine,
template, seed without its reference, play_map, asset_packs, difficulty, tags, limits) and <out>/<name>/grader.json
(name, seed.reference when the task has one, milestones: checks, rubrics, judge and code-judge questions, log
patterns). Merging grader.json into task.json (its seed into the task's seed) gives the task back. Prints a JSON list
of {name, title, kind, difficulty}; exit 2 when a task does not parse or its name differs from its file name.
Standard library only.
"""
import json, os, sys


def split(task):
    agent = {k: v for k, v in task.items() if k != 'milestones'}
    grader = {'name': task.get('name')}
    seed = task.get('seed')
    if isinstance(seed, dict) and 'reference' in seed:
        agent['seed'] = {k: v for k, v in seed.items() if k != 'reference'}
        if seed['reference'] is not None:
            grader['seed'] = {'reference': seed['reference']}
    grader['milestones'] = task.get('milestones', [])
    return agent, grader


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    rows, bad = [], 0
    for f in sorted(os.listdir(src)):
        if not f.endswith('.json'):
            continue
        stem = f[:-5]
        try:
            task = json.load(open(os.path.join(src, f), encoding='utf-8-sig'))
        except ValueError as e:
            print('%s: not JSON (%s)' % (f, e), file=sys.stderr)
            bad += 1
            continue
        if task.get('name') != stem:
            print('%s: name %r differs from the file name' % (f, task.get('name')), file=sys.stderr)
            bad += 1
            continue
        agent, grader = split(task)
        d = os.path.join(out, stem)
        os.makedirs(d, exist_ok=True)
        for name, obj in (('task.json', agent), ('grader.json', grader)):
            with open(os.path.join(d, name), 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
        seed = task.get('seed') if isinstance(task.get('seed'), dict) else {}
        rows.append({'name': stem, 'title': task.get('title', ''), 'kind': seed.get('kind', 'new game'),
                     'difficulty': task.get('difficulty', 'medium')})
    print(json.dumps(rows, ensure_ascii=False))
    return 2 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

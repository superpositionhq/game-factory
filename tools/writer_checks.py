"""Writer checks and scores: shared packaging and dataset validation, standard library only."""

import json
import math
import re
from datetime import datetime
from pathlib import Path

from task_check.digest import canonical_digest

SCHEMA_DIR = Path(__file__).resolve().parent.parent / 'docs' / 'schemas'
SCHEMAS = {name: json.loads((SCHEMA_DIR / (name + '.schema.json')).read_text(encoding='utf-8'))
           for name in ('task-check', 'writer-task-scores')}


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
        if isinstance(value, float) and not math.isfinite(value):
            yield f'{path}: number must be finite'
            return
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
            elif isinstance(schema.get('additionalProperties'), dict):
                yield from check_schema(v, schema['additionalProperties'], root, f'{path}.{k}')
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


def schema_problems(value, name):
    return list(check_schema(value, SCHEMAS[name]))


def parse_at(value):
    """An ISO 8601 timestamp with a timezone; bare local times can't establish freshness."""
    if not isinstance(value, str):
        raise ValueError('timestamp must be an ISO 8601 string')
    try:
        at = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('timestamp must be ISO 8601') from exc
    if at.tzinfo is None:
        raise ValueError('timestamp needs a timezone')
    return at


def task_checks(task):
    milestones = task.get('milestones')
    if not isinstance(milestones, list):
        return []
    return [c for m in milestones if isinstance(m, dict) and isinstance(m.get('checks'), list)
            for c in m['checks'] if isinstance(c, dict)]


def check_errors(task, result, last_commit_at=None):
    """Why the newest check can't ship. Judge answers are checked in score_errors, not regraded here."""
    errors = schema_problems(result, 'task-check')
    if errors:
        return errors
    if result['task'] != task.get('name'):
        errors.append('task name does not match')
    seed = task.get('seed') if isinstance(task.get('seed'), dict) else {}
    if result['game'] != seed.get('game'):
        errors.append('game does not match task seed.game')
    if result['task_digest'] != canonical_digest(task):
        errors.append('task_digest does not match the merged task')
    if result['verdict'] != 'VALID':
        errors.append(f"verdict is {result['verdict']}, not VALID")
    try:
        checked = parse_at(result['at'])
        if last_commit_at is None:
            errors.append('no task last-commit timestamp to establish freshness')
        elif checked < parse_at(last_commit_at):
            errors.append('check is older than the task last commit')
    except ValueError as exc:
        errors.append(f'freshness: {exc}')
    for check in task_checks(task):
        measure = check.get('measure') if isinstance(check.get('measure'), dict) else {}
        if check.get('kind') == 'probe' and measure.get('probe') == 'seen' \
                and check.get('required', True):
            name = check.get('name')
            answered = result['seen'].get(name)
            sides = {'reference'} if ((result.get('start') or {}).get('built') is False) else {'start', 'reference'}
            if not isinstance(answered, dict) or not sides <= set(answered.get('answered', [])) \
                    or answered.get('status') != 'read from blind/answers.json':
                errors.append(f'required seen check {name} is unanswered')
    return errors


def score_errors(tasks, scores):
    """Scores are human claims: validate their shape and coverage, never derive a new verdict from them."""
    errors = schema_problems(scores, 'writer-task-scores')
    if errors:
        return errors
    rows = scores['tasks']
    if set(rows) != set(tasks):
        errors.append('writer scores must name every shipped task exactly once '
                      f'(missing: {sorted(set(tasks) - set(rows))}; extra: {sorted(set(rows) - set(tasks))})')
    for name, task in tasks.items():
        if name not in rows:
            continue
        row = rows[name]
        if row['difficulty_estimate'] != task.get('difficulty', 'medium'):
            errors.append(f'{name}: difficulty_estimate does not match task difficulty')
        judges = {c['name']: c for c in task_checks(task)
                  if c.get('kind') in ('judge', 'code_judge') and isinstance(c.get('name'), str)}
        for judge, answers in row['judges'].items():
            if judge not in judges:
                errors.append(f'{name}: unknown judge {judge}')
                continue
            rubric = judges[judge].get('rubric')
            keys = {item['key'] for item in rubric if isinstance(item, dict) and isinstance(item.get('key'), str)} \
                if isinstance(rubric, list) else set()
            for side in ('start', 'reference'):
                if set(answers[side]) != keys:
                    errors.append(f'{name}: judge {judge} {side} must score every rubric item exactly once')
        for judge, check in judges.items():
            if check.get('required', True) and judge not in row['judges']:
                errors.append(f'{name}: required judge {judge} is unanswered')
    return errors

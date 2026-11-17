"""Writer checks, score coverage and warn/reject dataset rollout (no Unreal or PowerShell)."""
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from task_check import check, seeds
from task_check.digest import canonical_digest
from writer_checks import check_errors, score_errors, schema_problems

spec = importlib.util.spec_from_file_location('validate_game_writer_tests', TOOLS / 'validate-game.py')
vg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vg)
spec = importlib.util.spec_from_file_location('writer_test_helpers', TOOLS / 'task_check/tests/helpers.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

AT = '2026-11-17T12:00:00Z'


def task():
    return {'name': 'a-task', 'difficulty': 'hard', 'seed': {'game': 'a-game', 'commit': 'a' * 40,
            'reference': 'b' * 40}, 'milestones': []}


def result(t):
    return {'format': 'task-check/2', 'task': t['name'], 'game': t['seed']['game'], 'task_sha256': 'a' * 64,
            'task_digest': canonical_digest(t), 'verdict': 'VALID', 'reasons': [], 'notes': [],
            'start': {'commit': 'a' * 40, 'built': True}, 'reference': {'commit': 'b' * 40, 'built': True},
            'probes': {}, 'start_checks': [], 'reference_checks': [], 'judges': {}, 'seen': {},
            'evidence': 'a-task/', 'at': AT, 'seconds': 1.0}


def scores(t):
    return {'schema': 'writer-task-scores/1', 'tasks': {t['name']: {'difficulty_estimate': 'hard', 'quality': 4,
            'minutes_to_solve_estimate': 30, 'judges': {}, 'notes': 'A fair task.'}}}


class WriterChecks(unittest.TestCase):
    def test_valid_binding_and_freshness(self):
        t = task()
        self.assertEqual(check_errors(t, result(t), AT), [])
        old = dict(result(t), at='2026-11-16T12:00:00Z')
        self.assertEqual(check_errors(t, old, AT), [])  # same content after amend/rebase
        self.assertEqual(check_errors(t, result(t)), [])
        self.assertEqual(check_errors(t, result(t), 'not a timestamp'), [])
        changed = dict(t, instruction='An edit after the check')
        self.assertIn('task_digest does not match the merged task', check_errors(changed, result(t), AT))

    def test_legacy_without_digest_uses_timestamp_fallback(self):
        t = task()
        legacy = dict(result(t), format='task-check/1')
        del legacy['task_digest']
        self.assertEqual(schema_problems(legacy, 'task-check'), [])
        self.assertEqual(check_errors(t, legacy, AT), [])
        old = dict(legacy, at='2026-11-16T12:00:00Z')
        self.assertIn('check is older than the task last commit', check_errors(t, old, AT))
        self.assertIn('no task last-commit timestamp to establish freshness', check_errors(t, legacy))
        self.assertIn('freshness: timestamp must be ISO 8601', check_errors(t, legacy, 'not a timestamp'))
        self.assertIn('freshness: timestamp needs a timezone', check_errors(t, legacy, '2026-11-17T12:00:00'))

    def test_legacy_with_digest_uses_content_binding(self):
        t = task()
        legacy = dict(result(t), format='task-check/1')
        self.assertEqual(check_errors(t, legacy, '2026-11-18T12:00:00Z'), [])
        self.assertEqual(check_errors(t, legacy), [])
        legacy['task_digest'] = '0' * 64
        self.assertIn('task_digest does not match the merged task', check_errors(t, legacy, AT))

    def test_invalid_error_wrong_name_and_game(self):
        t = task()
        for verdict in ('INVALID', 'ERROR'):
            self.assertIn(f'verdict is {verdict}, not VALID', check_errors(t, dict(result(t), verdict=verdict), AT))
        self.assertIn('task name does not match', check_errors(t, dict(result(t), task='other'), AT))
        self.assertIn('game does not match task seed.game', check_errors(t, dict(result(t), game='other'), AT))

    def test_strict_result_schema_and_nested_rows(self):
        t = task()
        for extra in ('probe.json', 'logs', 'unexpected'):
            self.assertTrue(check_errors(t, dict(result(t), **{extra: []}), AT))
        missing_digest = result(t)
        del missing_digest['task_digest']
        self.assertTrue(check_errors(t, missing_digest, AT))  # /2 still requires binding
        bad = result(t)
        bad['start_checks'] = [{'name': 'built'}]
        self.assertTrue(check_errors(t, bad, AT))
        self.assertTrue(check_errors(t, dict(result(t), at='2026-02-30T12:00:00Z'), AT))

    def test_schema_matches_actual_checker_results(self):
        t = helpers.task_with(helpers.probe())
        projects = {'a' * 40: helpers.FakeProject(helpers.measuring(-100)),
                    'b' * 40: helpers.FakeProject(helpers.measuring(100))}
        class Builds:
            def get(self, sha, needed):
                return projects[sha], {'files': 1, 'lfs_linked': 0, 'lfs_copied': 0,
                                       'engine': 'engine', 'slots': 'direct'}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(seeds, 'resolve', side_effect=lambda repo, c: c), \
                mock.patch.object(check, 'map_gaps', return_value={}):
            r = check.check_task(tmp, t, json.dumps(t).encode(), Path(tmp) / 'scratch', Path(tmp) / 'out',
                                 builds=Builds(), log=lambda *args: None)
            self.assertEqual(r['verdict'], 'VALID', r['reasons'])
            self.assertEqual(schema_problems(r, 'task-check'), [])
            self.assertEqual(check_errors(t, r, '2026-01-01T00:00:00Z'), [])

    def test_scores_cover_tasks_and_match_difficulty(self):
        t = task()
        self.assertEqual(score_errors({t['name']: t}, scores(t)), [])
        s = scores(t)
        s['tasks']['extra'] = copy.deepcopy(s['tasks'][t['name']])
        self.assertIn('writer scores must name every shipped task', score_errors({t['name']: t}, s)[0])
        s = scores(t)
        s['tasks'][t['name']]['difficulty_estimate'] = 'medium'
        self.assertIn('a-task: difficulty_estimate does not match task difficulty', score_errors({t['name']: t}, s))

    def test_score_bounds_and_plain_notes(self):
        t = task()
        for key, value in [('quality', 0), ('quality', 6), ('quality', True), ('minutes_to_solve_estimate', 0),
                           ('minutes_to_solve_estimate', float('nan')), ('minutes_to_solve_estimate', float('inf')),
                           ('notes', 'x' * 301), ('notes', 'line\nline'), ('notes', 'line\tline'), ('notes', 'line\n'),
                           ('notes', 'line\u2028line'), ('notes', 'line\n')]:
            with self.subTest(key=key, value=value):
                s = scores(t)
                s['tasks'][t['name']][key] = value
                self.assertTrue(score_errors({t['name']: t}, s))

    def test_required_judges_have_each_blind_rubric_score(self):
        t = task()
        t['milestones'] = [{'checks': [{'kind': 'judge', 'name': 'looks', 'rubric': [{'key': 'ask'}, {'key': 'style'}]}]}]
        s = scores(t)
        self.assertTrue(score_errors({t['name']: t}, s))
        s['tasks'][t['name']]['judges']['looks'] = {'start': {'ask': 0, 'style': .3}, 'reference': {'ask': 1, 'style': .8}}
        self.assertEqual(score_errors({t['name']: t}, s), [])
        s['tasks'][t['name']]['judges']['looks']['start']['ask'] = 1.1
        self.assertTrue(score_errors({t['name']: t}, s))

    def test_required_seen_needs_both_answered_sides(self):
        t = task()
        t['milestones'] = [{'checks': [{'kind': 'probe', 'name': 'hud', 'measure': {'probe': 'seen'}}]}]
        r = result(t)
        self.assertIn('required seen check hud is unanswered', check_errors(t, r, AT))
        r['seen']['hud'] = {'sides': {}, 'blind': True, 'answered': ['start', 'reference'], 'notes': [],
                            'status': 'read from blind/answers.json'}
        self.assertEqual(check_errors(t, r, AT), [])
        r['seen']['hud']['answered'] = ['reference']
        self.assertTrue(check_errors(t, r, AT))
        r['start']['built'] = False
        self.assertEqual(check_errors(t, r, AT), [])

    def test_warn_reject_and_filesystem_zip_agree(self):
        t = task()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'a-game'
            (root / 'Checks').mkdir(parents=True)
            (root / 'Checks/a-task.json').write_text(json.dumps(result(t)))
            (root / 'Checks/writer-scores.json').write_text(json.dumps(scores(t)))
            m = {'tasks': {'last_commit_at': {'a-task': AT}}}
            with mock.patch.dict(vg.OPTS, checks_mode='reject'):
                rep = vg.Report()
                vg.check_writer_checks(rep, 'dataset', vg.DatasetView(str(root)), {'a-task': t}, m)
                self.assertEqual(rep.items, [])
            (root / 'Checks/a-task/probe.json').parent.mkdir()
            (root / 'Checks/a-task/probe.json').write_text('{}')
            for mode, severity in [('warn', 'warning'), ('reject', 'error')]:
                with mock.patch.dict(vg.OPTS, checks_mode=mode):
                    rep = vg.Report()
                    vg.check_writer_checks(rep, 'dataset', vg.DatasetView(str(root)), {'a-task': t}, m)
                    self.assertEqual(rep.count(severity), 1, rep.items)
            import zipfile
            path = Path(tmp) / 'Dataset.zip'
            with zipfile.ZipFile(path, 'w') as z:
                for f in root.rglob('*'):
                    if f.is_file():
                        z.write(f, 'a-game/' + f.relative_to(root).as_posix())
            with mock.patch.dict(vg.OPTS, checks_mode='warn'):
                zipped, folder = vg.Report(), vg.Report()
                view = vg.DatasetView(str(path))
                try:
                    vg.check_writer_checks(zipped, 'dataset', view, {'a-task': t}, m)
                finally:
                    view.zip.close()
                vg.check_writer_checks(folder, 'dataset', vg.DatasetView(str(root)), {'a-task': t}, m)
                self.assertEqual(zipped.items, folder.items)


if __name__ == '__main__':
    unittest.main()

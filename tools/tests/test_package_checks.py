"""The packager's writer-check gate with a real orphan tasks branch; no Unreal or PowerShell."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('package_checks', TOOLS / 'package-checks.py')
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)
split_spec = importlib.util.spec_from_file_location('split_tasks', TOOLS / 'split-tasks.py')
split = importlib.util.module_from_spec(split_spec)
split_spec.loader.exec_module(split)


class PackageChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'game'
        self.repo.mkdir()
        self.run_git('init', '-q')
        self.run_git('config', 'user.name', 'dev_01')
        self.run_git('config', 'user.email', 'dev_01@example.invalid')
        self.run_git('checkout', '--orphan', 'tasks')
        self.task = {'name': 'repair-hud', 'title': 'Repair the HUD', 'difficulty': 'hard',
                     'seed': {'game': 'fixture', 'commit': 'a' * 40, 'reference': 'b' * 40},
                     'milestones': []}
        self.write(self.repo / 'Tasks' / 'repair-hud.json', self.task)
        self.commit('2026-11-17T10:00:00Z')
        self.tasks = self.base / 'split'
        self.out = self.base / 'Checks'
        self.checks = self.repo / '.task-checks'
        self.deliver(self.task)
        self.result = {'format': 'task-check/2', 'task': 'repair-hud', 'game': 'fixture',
                       'task_sha256': 'c' * 64, 'task_digest': pc.canonical_digest(self.task),
                       'verdict': 'VALID', 'reasons': [], 'notes': [], 'start': None, 'reference': None,
                       'probes': {}, 'start_checks': [], 'reference_checks': [], 'judges': {}, 'seen': {},
                       'evidence': 'repair-hud/', 'at': '2026-11-17T11:00:00Z', 'seconds': 10.0}
        self.scores = {'schema': 'writer-task-scores/1', 'tasks': {'repair-hud': {
            'difficulty_estimate': 'hard', 'quality': 4, 'minutes_to_solve_estimate': 30,
            'judges': {}, 'notes': 'Three related fixes.'}}}
        self.save_checks()

    def run_git(self, *args, **kwargs):
        return subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True,
                              check=True, **kwargs)

    def commit(self, at):
        self.run_git('add', 'Tasks/repair-hud.json')
        self.run_git('commit', '-qm', 'Record task', env=dict(os.environ, GIT_AUTHOR_DATE=at, GIT_COMMITTER_DATE=at))

    def write(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj), encoding='utf-8')

    def deliver(self, task):
        agent, grader = split.split(task)
        for name, value in [('task.json', agent), ('grader.json', grader)]:
            self.write(self.tasks / 'repair-hud' / name, value)

    def save_checks(self):
        self.write(self.checks / 'repair-hud.json', self.result)
        self.write(self.checks / 'writer-scores.json', self.scores)

    def test_ships_only_latest_result_scores_and_small_answers(self):
        # A named judge's answers may be kept, but none of its screenshots/keys/logs.
        self.task['milestones'] = [{'name': 'quality', 'checks': [
            {'kind': 'judge', 'name': 'looks_as_asked', 'required': False, 'rubric': [{'key': 'clear'}]}]}]
        self.write(self.repo / 'Tasks/repair-hud.json', self.task)
        self.commit('2026-11-17T10:30:00Z')
        self.deliver(self.task)
        self.result['task_digest'] = pc.canonical_digest(self.task)
        self.scores['tasks']['repair-hud']['judges'] = {
            'looks_as_asked': {'start': {'clear': 0}, 'reference': {'clear': 1}}}
        self.save_checks()
        answer = self.checks / 'repair-hud/judge-shots/looks_as_asked/blind/answers.json'
        self.write(answer, {'A': {'clear': 0}, 'B': {'clear': 1}})
        for relative in ['repair-hud/start/look/probe.json', 'repair-hud/start/look/game.log',
                         'repair-hud/judge-shots/looks_as_asked/blind/key.json',
                         'repair-hud/judge-shots/looks_as_asked/blind/A/look.png']:
            path = self.checks / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('private local evidence')
        metadata = pc.stage(self.repo, self.tasks, self.out)
        self.assertEqual(datetime.fromisoformat(metadata['last_commit_at']['repair-hud'].replace('Z', '+00:00')),
                         datetime.fromisoformat('2026-11-17T10:30:00+00:00'))
        self.assertEqual(sorted(p.relative_to(self.out).as_posix() for p in self.out.rglob('*') if p.is_file()),
                         ['repair-hud.json', 'repair-hud/judge-shots/looks_as_asked/blind/answers.json',
                          'writer-scores.json'])
        self.assertEqual(pc.read_json(self.out / 'repair-hud.json'), self.result)

    def test_refuses_missing_or_newest_failed_result_without_fallback(self):
        (self.checks / 'repair-hud.json').unlink()
        with self.assertRaises(FileNotFoundError):
            pc.stage(self.repo, self.tasks, self.out)
        for verdict in ['INVALID', 'ERROR']:
            self.result['verdict'] = verdict
            self.save_checks()
            self.write(self.checks / 'repair-hud-old-valid.json', dict(self.result, verdict='VALID'))
            with self.assertRaisesRegex(ValueError, 'not VALID'):
                pc.stage(self.repo, self.tasks, self.out)

    def test_matching_digest_survives_changed_commit_time(self):
        self.result['at'] = '2026-11-17T09:59:59Z'
        self.save_checks()
        pc.stage(self.repo, self.tasks, self.out)
        self.run_git('commit', '--amend', '--no-edit',
                     env=dict(os.environ, GIT_COMMITTER_DATE='2026-11-17T13:00:00Z'))
        metadata = pc.stage(self.repo, self.tasks, self.out)
        self.assertEqual(datetime.fromisoformat(metadata['last_commit_at']['repair-hud'].replace('Z', '+00:00')),
                         datetime.fromisoformat('2026-11-17T13:00:00+00:00'))

    def test_legacy_without_digest_uses_commit_time(self):
        self.result['format'] = 'task-check/1'
        self.result.pop('task_digest')
        self.save_checks()
        pc.stage(self.repo, self.tasks, self.out)
        self.result['at'] = '2026-11-17T09:59:59Z'
        self.save_checks()
        with self.assertRaisesRegex(ValueError, 'older'):
            pc.stage(self.repo, self.tasks, self.out)

    def test_refuses_digest_mismatch_and_missing_or_inconsistent_scores(self):
        self.result['task_digest'] = '0' * 64
        self.save_checks()
        with self.assertRaisesRegex(ValueError, 'task_digest'):
            pc.stage(self.repo, self.tasks, self.out)
        self.result['task_digest'] = pc.canonical_digest(self.task)
        self.scores['tasks']['repair-hud']['difficulty_estimate'] = 'medium'
        self.save_checks()
        with self.assertRaisesRegex(ValueError, 'difficulty'):
            pc.stage(self.repo, self.tasks, self.out)
        (self.checks / 'writer-scores.json').unlink()
        with self.assertRaises(FileNotFoundError):
            pc.stage(self.repo, self.tasks, self.out)

    def test_rebinds_only_after_verifying_original_and_exact_commit_mapping(self):
        mapping = self.base / 'map.tsv'
        mapping.write_text('original\tdelivered\n' + 'a' * 40 + '\t' + 'd' * 40 + '\n', encoding='utf-8')
        delivered = copy.deepcopy(self.task)
        delivered['seed']['commit'] = 'd' * 40
        self.deliver(delivered)
        pc.stage(self.repo, self.tasks, self.out, mapping)
        shipped = pc.read_json(self.out / 'repair-hud.json')
        self.assertEqual(shipped, dict(self.result, task_digest=pc.canonical_digest(delivered)))
        delivered['title'] = 'A changed ask'
        self.deliver(delivered)
        with self.assertRaisesRegex(ValueError, 'beyond commit mapping'):
            pc.stage(self.repo, self.tasks, self.out, mapping)
        # A forged result matching only the delivered task does not bind the original.
        self.deliver(pc.delivered_task(self.task, {'a' * 40: 'd' * 40}))
        self.result['task_digest'] = shipped['task_digest']
        self.save_checks()
        with self.assertRaisesRegex(ValueError, 'task_digest'):
            pc.stage(self.repo, self.tasks, self.out, mapping)

    def test_cli_stages_metadata_and_returns_failure_for_refused_task(self):
        command = [sys.executable, str(TOOLS / 'package-checks.py'), str(self.repo), str(self.tasks), str(self.out)]
        ok = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn('repair-hud', json.loads(ok.stdout)['last_commit_at'])
        self.result['verdict'] = 'ERROR'
        self.save_checks()
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertIn('not VALID', failed.stderr)

    def test_cli_can_omit_checks_and_refusal_with_one_warning(self):
        pc.stage(self.repo, self.tasks, self.out)
        self.result['verdict'] = 'ERROR'
        self.save_checks()
        # No tasks branch or checks are needed in compatibility mode.
        self.run_git('branch', '-m', 'not-tasks')
        command = [sys.executable, str(TOOLS / 'package-checks.py'), str(self.repo), str(self.tasks), str(self.out),
                   '--no-writer-checks']
        skipped = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(skipped.returncode, 0, skipped.stderr)
        self.assertEqual(json.loads(skipped.stdout), {'last_commit_at': {}})
        self.assertEqual(len(skipped.stderr.strip().splitlines()), 1)
        self.assertIn('WARNING:', skipped.stderr)
        self.assertIn('writer checks omitted', skipped.stderr)
        self.assertFalse(self.out.exists())

    def add_blind_answer(self, value):
        self.task['milestones'] = [{'checks': [{'kind': 'judge', 'name': 'looks', 'required': False}]}]
        self.write(self.repo / 'Tasks/repair-hud.json', self.task)
        self.commit('2026-11-17T10:30:00Z')
        self.deliver(self.task)
        self.result['task_digest'] = pc.canonical_digest(self.task)
        self.save_checks()
        path = self.checks / 'repair-hud/judge-shots/looks/blind/answers.json'
        self.write(path, value)
        return path

    def test_refuses_non_blind_answer_keys_and_keeps_previous_staging(self):
        pc.stage(self.repo, self.tasks, self.out)
        prior = (self.out / 'repair-hud.json').read_bytes()
        path = self.add_blind_answer({'A': []})
        for answer in [{}, [], {'start': [], 'reference': []}, {'A': [], 'B': [], 'screenshots': []}]:
            with self.subTest(answer=answer):
                self.write(path, answer)
                with self.assertRaisesRegex(ValueError, 'blind A/B sides'):
                    pc.stage(self.repo, self.tasks, self.out)
                self.assertEqual((self.out / 'repair-hud.json').read_bytes(), prior)
        self.write(path, {'A': ['Only one side exists when the start does not build.']})
        pc.stage(self.repo, self.tasks, self.out)

    def test_refuses_large_blind_answer_sides_and_files(self):
        path = self.add_blind_answer({'A': 'x' * pc.MAX_ANSWER_BYTES})
        with self.assertRaisesRegex(ValueError, 'each blind answer.*8 KiB'):
            pc.stage(self.repo, self.tasks, self.out)
        self.write(path, {'A': 'x' * pc.MAX_ANSWERS_BYTES})
        with self.assertRaisesRegex(ValueError, 'blind answers exceed 16 KiB'):
            pc.stage(self.repo, self.tasks, self.out)
        # A small parsed value cannot smuggle a large file through JSON whitespace.
        path.write_text('{"A": []}' + ' ' * pc.MAX_ANSWERS_BYTES, encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'blind answers exceed 16 KiB'):
            pc.stage(self.repo, self.tasks, self.out)

    def test_task_deleted_from_tip_has_actionable_error(self):
        pinned = self.run_git('rev-parse', 'HEAD', text=True).stdout.strip()
        self.run_git('rm', 'Tasks/repair-hud.json')
        self.run_git('commit', '-qm', 'Remove task')
        for tasks_ref in [None, pinned]:
            with self.subTest(tasks_ref=tasks_ref):
                with self.assertRaisesRegex(ValueError, "repair-hud: task isn't on the tasks branch") as raised:
                    pc.stage(self.repo, self.tasks, self.out, tasks_ref=tasks_ref)
                self.assertNotIn('fetch', str(raised.exception))

    def test_pinned_package_cannot_bypass_newer_task_branch_edits(self):
        pinned = self.run_git('rev-parse', 'HEAD', text=True).stdout.strip()
        self.task['title'] = 'A new task ask'
        self.write(self.repo / 'Tasks/repair-hud.json', self.task)
        self.commit('2026-11-17T12:00:00Z')
        with self.assertRaisesRegex(ValueError, 'changed on the tasks branch'):
            pc.stage(self.repo, self.tasks, self.out, tasks_ref=pinned)
        self.task['title'] = 'Repair the HUD'
        self.write(self.repo / 'Tasks/repair-hud.json', self.task)
        self.commit('2026-11-17T13:00:00Z')
        pc.stage(self.repo, self.tasks, self.out, tasks_ref=pinned)


if __name__ == '__main__':
    unittest.main()

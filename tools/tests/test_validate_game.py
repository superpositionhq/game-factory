"""tools/validate-game.py's rules on their own, without a repo.

    python -m unittest discover -s tools/tests -p "test_validate_game.py" -v
"""
import importlib.util, json, os, shutil, tempfile, unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('validate_game', os.path.join(TOOLS, 'validate-game.py'))
vg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vg)


class Units(unittest.TestCase):
    def test_required_quality_judges(self):
        """A required judge is noted as one that should be optional, but for the judges of the brief's looks: a `judge`
        named `looks_as_asked` and a `judge` in `still_works`."""
        def judge(name, kind='judge', **over):
            return {'name': name, 'kind': kind, 'question': 'q', 'rubric': [{'key': 'k', 'criterion': 'c'}], **over}
        t = {'milestones': [
            {'name': 'done', 'checks': [judge('looks_as_asked'), judge('reads_well'), judge('optional', required=False),
                                        judge('looks_as_asked', 'code_judge'), judge('worked_well', 'actions_judge')]},
            {'name': 'still_works', 'checks': [judge('hud_unchanged'), judge('code', 'code_judge')]}]}
        self.assertEqual(vg.required_quality_judges(t), ['reads_well', 'looks_as_asked', 'worked_well', 'code'])


class Sessions(unittest.TestCase):
    """History/sessions/ as the recording hooks write it since 2026-11-11 (reasoning summaries as role "thinking" rows,
    a tool call's whole output) and as they wrote it before: both pass without a warning."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='gfs')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, messages, actions):
        d = os.path.join(self.tmp, 'History', 'sessions')
        os.makedirs(d, exist_ok=True)
        for name, rows in (('messages.jsonl', messages), ('actions.jsonl', actions)):
            with open(os.path.join(d, name), 'w', encoding='utf-8', newline='') as f:
                f.write(''.join(json.dumps(r) + '\n' for r in rows))
        rep = vg.Report()
        vg.check_sessions(rep, 'dataset', vg.DatasetView(self.tmp),
                          {'history': {'sessions': {'messages': {'rows': len(messages)}, 'actions': {'rows': len(actions)}}}})
        return [m for sev, _a, m in rep.items if sev != 'note'], [m for sev, _a, m in rep.items if sev == 'note']

    def msg(self, role, text, **more):
        return dict({'schema': 'agent-message/v0', 'time': '2026-11-11T10:00:00.000+00:00', 'project': 'g', 'session_id': 'session_01',
                     'agent': 'claude', 'role': role, 'message_id': f'm{len(text)}', 'text': text}, **more)

    def act(self, response, **more):
        return dict({'schema': 'agent-action/v0', 'time': '2026-11-11T10:00:01.000+00:00', 'project': 'g', 'session_id': 'session_01',
                     'agent': 'claude', 'event': 'PostToolUse', 'tool': 'Bash', 'tool_use_id': 't1', 'input': {'command': 'dir'},
                     'response': response}, **more)

    def test_reasoning_summaries_and_whole_outputs(self):
        bad, notes = self.check([self.msg('user', 'Make the door open.'), self.msg('thinking', 'The door needs a hinge first.', model='agent-model'),
                                 self.msg('thinking', '', redacted=True), self.msg('assistant', 'Done.')],
                                [self.act('line\n' * 50000), self.act('x' * 1048576, truncated=True, response_chars=3000000)])
        self.assertEqual(bad, [])
        self.assertTrue([n for n in notes if '1 prompt(s), 1 repl(ies), 2 reasoning summar(ies) in 1 session(s)' in n], notes)

    def test_a_game_recorded_before_them_is_as_valid(self):
        bad, notes = self.check([self.msg('user', 'Make the door open.'), self.msg('assistant', 'Done.')], [self.act('ok' * 4000)])
        self.assertEqual(bad, [])
        self.assertTrue([n for n in notes if '1 prompt(s), 1 repl(ies), 0 reasoning summar(ies)' in n], notes)

    def test_another_role_still_warns(self):
        bad, _notes = self.check([self.msg('system', 'x')], [self.act('ok')])
        self.assertEqual(len(bad), 1)
        self.assertIn('roles other than user, assistant and thinking: system', bad[0])


if __name__ == '__main__':
    unittest.main()

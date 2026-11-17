"""tools/validate-game.py's rules on their own, without a repo.

    python -m unittest discover -s tools/tests -p "test_validate_game.py" -v
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest

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
        self.assertEqual(vg.required_quality_judges(t), ['reads_well', 'looks_as_asked', 'code'])

    def test_retired_checks(self):
        """`actions_judge` checks and `trace` probes are retired: a task that still carries one matches the schema and
        is only warned about; a task without one has nothing to warn of. A trace probe never counted as a required
        or an outcome probe, so no floor moves."""
        def check(name, kind, **over):
            return {'name': name, 'kind': kind, 'question': 'q', 'rubric': [{'key': 'k', 'criterion': 'c'}], **over}
        old = {'milestones': [{'name': 'done', 'checks': [check('looks_as_asked', 'judge')]},
                              {'name': 'quality', 'checks': [check('worked_well', 'actions_judge', required=False),
                                                             check('worked', 'actions_judge')]}]}
        trace = {'name': 'built', 'kind': 'probe', 'required': False, 'describe': 'The last build worked.',
                 'play': 'trace', 'measure': {'probe': 'trace', 'fact': 'build_ok_at_end'},
                 'expect': {'op': '>=', 'value': 1}}
        old['milestones'][1]['checks'].append(trace)
        self.assertEqual(vg.retired_checks(old), ['worked_well', 'worked', 'built'])
        self.assertEqual(list(vg.check_schema(trace, vg.SCHEMAS['game-task']['$defs']['Probe'], vg.SCHEMAS['game-task'])), [])
        self.assertEqual(vg.probe_errors(trace, {'commit': 'a', 'reference': 'b'}, 'b', {}), [])
        self.assertEqual(vg.required_quality_judges(old), [])
        schema = vg.SCHEMAS['game-task']
        for c in old['milestones'][1]['checks'][:2]:
            self.assertEqual(list(vg.check_schema(c, schema['$defs']['ActionsJudge'], schema)), [])
        new = {'milestones': [{'name': 'done', 'checks': [check('looks_as_asked', 'judge')]}]}
        self.assertEqual(vg.retired_checks(new), [])

    def test_a_guard_is_not_an_outcome(self):
        """A required probe of weight 0 outside still_works gates and pays nothing: it doesn't count toward the 3."""
        probe = lambda n, **k: dict({'name': n, 'kind': 'probe'}, **k)
        t = {'milestones': [{'name': 'fix', 'checks': [probe('a'), probe('g1', weight=0), probe('g2', weight=0),
                                                       probe('o', required=False), {'name': 'j', 'kind': 'judge'}]},
                            {'name': 'still_works', 'checks': [probe('s', weight=0), probe('s2')]}]}
        self.assertEqual([c['name'] for c in vg.outcome_probes(t)], ['a'])
        self.assertIn('1 required outcome probe(s) outside still_works, fewer than 3 '
                      '(a required probe of weight 0 is a guard, not an outcome)',
                      vg.thread_errors(t, len(vg.outcome_probes(t))))

    def test_a_play_continues_one_first_session(self):
        """`continues` names a task play of the task that starts a session alone: never itself, never beside `after`."""
        def checks(*plays):
            return [{'kind': 'probe', 'name': p['name'], 'play': p} for p in plays]
        first, again = {'name': 'earns', 'seconds': 10}, {'name': 'restarted', 'seconds': 20, 'continues': 'earns'}
        self.assertEqual(vg.play_continues_errors(checks(again, first)), [])
        self.assertEqual(vg.play_continues_errors(checks(first)), [])
        self.assertEqual(vg.play_continues_errors(checks({**again, 'continues': 'restarted'})),
                         ['task play restarted continues itself'])
        self.assertEqual(vg.play_continues_errors(checks({**again, 'continues': 'drive'})),
                         ['task play restarted continues drive, which is no task play of the task'])
        self.assertEqual(vg.play_continues_errors(checks(again, {**first, 'after': ['restarted']})),
                         ['task play restarted continues earns, which itself continues a session or runs after other '
                          'plays: a first session starts from a cleared save, alone'])
        self.assertEqual(vg.play_continues_errors(checks({**again, 'after': ['earns']}, first)),
                         ['task play restarted continues a session and runs after plays too: name one or the other'])
        schema = vg.SCHEMAS['game-task']
        self.assertEqual(list(vg.check_schema(again, schema['$defs']['TaskPlay'], schema)), [])
        self.assertTrue(list(vg.check_schema({**again, 'continues': 'Not A Name'}, schema['$defs']['TaskPlay'], schema)))
        self.assertIsNone(vg.TASK_PLAY_DEFAULTS['continues'])

    def test_a_widget_select_may_say_drawn_or_not(self):
        schema = vg.SCHEMAS['game-task']
        for said in (True, False):
            self.assertEqual(list(vg.check_schema({'name': 'Warn*', 'visible': said}, schema['$defs']['WidgetSelect'],
                                                  schema)), [])
        self.assertTrue(list(vg.check_schema({'name': 'Warn*', 'visible': 1}, schema['$defs']['WidgetSelect'], schema)))

    def test_task_bar(self):
        """A game's bar: at least 5 tasks, at least 4 of them hard; the others may be medium (what a task that names
        none is), none easier."""
        hard = {f't{i}': 'hard' for i in range(5)}
        self.assertEqual(vg.task_bar_errors(hard), [])
        self.assertEqual(vg.task_bar_errors(dict(hard, t0='medium')), [])   # 4 hard + 1 medium
        self.assertEqual(vg.task_bar_errors(dict(hard, t0=None)), [])       # no difficulty: medium
        self.assertEqual(vg.task_bar_errors(dict({f'm{i}': 'medium' for i in range(6)}, t0='hard', t1='hard', t2='hard',
                                                 t3='hard')), [])           # 10 tasks: 4 hard + 6 medium
        self.assertEqual(vg.task_bar_errors(dict(hard, t4='medium', t1=None)),   # 3 hard + 2 medium
                         ['3 hard task(s): a game needs at least 4 hard tasks (medium: t1, t4); the others may be medium'])
        self.assertEqual(vg.task_bar_errors({f't{i}': 'hard' for i in range(4)}), ['4 task(s): a game ships at least 5'])
        self.assertEqual(vg.task_bar_errors({'t0': 'hard', 't1': 'hard'}),
                         ['2 task(s): a game ships at least 5',
                          '2 hard task(s): a game needs at least 4 hard tasks; the others may be medium'])
        self.assertEqual(vg.task_bar_errors(dict(hard, t0='easy')), ['t0: difficulty \'easy\': a task is "hard"'])
        self.assertEqual(vg.task_bar_errors(dict(hard, t0='calibration')),
                         ['t0: difficulty \'calibration\': a task is "hard"'])
        self.assertEqual(vg.thread_errors({'difficulty': 'easy'}, 3)[0],
                         'difficulty \'easy\': a task is "hard" or "medium" (a game needs at least 4 "hard")')


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


MOBILE_INI = """[/Script/AndroidRuntimeSettings.AndroidRuntimeSettings]
PackageName=com.tide.game
MinSDKVersion=26
TargetSDKVersion=34
Orientation=Portrait
bBuildForArm64=True
bBuildForX8664=False
bPackageDataInsideApk=True
bSupportsVulkan=True

[/Script/LinuxTargetPlatform.LinuxTargetSettings]
+TargetedRHIs=SF_VULKAN_SM6
+TargetedRHIs=SF_VULKAN_ES31

[/Script/WindowsTargetPlatform.WindowsTargetSettings]
+D3D12TargetedShaderFormats=PCD3D_SM6
+D3D12TargetedShaderFormats=PCD3D_ES31
"""


class Mobile(unittest.TestCase):
    """Rule `mobile`: a mobile game's project settings and its tasks' plays; a desktop game is not looked at."""

    def game(self, platform=None, ini=None):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        if platform is not None:
            with open(os.path.join(d, 'Platform.json'), 'w', encoding='utf-8') as f:
                f.write(platform if isinstance(platform, str) else json.dumps(platform))
        if ini is not None:
            os.makedirs(os.path.join(d, 'Config'))
            with open(os.path.join(d, 'Config', 'DefaultEngine.ini'), 'w', encoding='utf-8') as f:
                f.write(ini)
        return d

    def said(self, d, files=('Platform.json',)):
        rep = vg.Report()
        vg.check_mobile(rep, d, list(files))
        return [m for _, area, m in rep.items if area == 'mobile']

    def test_a_desktop_game_is_not_looked_at(self):
        lumen = '[/Script/Engine.RendererSettings]\nr.DynamicGlobalIlluminationMethod=1\n'
        self.assertEqual(self.said(self.game(ini=lumen), files=()), [])
        self.assertEqual(self.said(self.game(), files=()), [])

    def test_a_mobile_game_as_the_template_makes_it_passes(self):
        self.assertEqual(self.said(self.game({'platform': 'mobile', 'orientation': 'portrait'}, MOBILE_INI)), [])

    def test_the_template_overlays_pass_for_both_orientations(self):
        text = open(os.path.join(os.path.dirname(TOOLS), 'templates', 'ue-game-mobile', 'Config', 'DefaultEngine.ini'),
                    encoding='utf-8').read()
        for orientation, held in (('landscape', 'SensorLandscape'), ('portrait', 'Portrait')):
            ini = text.replace('__ANDROID_ORIENTATION__', held).replace('__ANDROID_NAME__', 'tide')
            self.assertEqual(vg.mobile_project_errors(orientation, ini, 'Tide'), [])

    def test_each_setting_that_disagrees_is_named(self):
        def errs(old, new, orientation='portrait'):
            self.assertIn(old, MOBILE_INI)
            return vg.mobile_project_errors(orientation, MOBILE_INI.replace(old, new))
        self.assertIn('Orientation=Portrait, but Platform.json says landscape', errs('x', 'x', 'landscape')[0])
        self.assertIn('Orientation=Sensor,', errs('Orientation=Portrait', 'Orientation=Sensor')[0])
        self.assertIn('Orientation=SensorLandscape', errs('Orientation=Portrait\n', '')[0])   # the engine's default
        self.assertEqual(errs('Orientation=Portrait\n', '', 'landscape'), [])
        self.assertIn('bBuildForArm64', errs('bBuildForArm64=True', 'bBuildForArm64=False')[0])
        self.assertEqual(errs('bBuildForArm64=True\n', ''), [])                                # default True
        self.assertIn('bBuildForX8664', errs('bBuildForX8664=False', 'bBuildForX8664=True')[0])
        self.assertIn('MinSDKVersion=24: at least 26', errs('MinSDKVersion=26', 'MinSDKVersion=24')[0])
        self.assertIn('TargetSDKVersion=33: at least 34', errs('TargetSDKVersion=34', 'TargetSDKVersion=33')[0])
        self.assertIn('bPackageDataInsideApk', errs('bPackageDataInsideApk=True\n', '')[0])    # default False
        self.assertIn('SF_VULKAN_ES31', errs('+TargetedRHIs=SF_VULKAN_ES31\n', '')[0])
        self.assertIn('PCD3D_ES31', errs('+D3D12TargetedShaderFormats=PCD3D_ES31\n', '')[0])
        self.assertIn('bSupportsVulkan', errs('bSupportsVulkan=True\n', '')[0])                # default False
        self.assertEqual(vg.mobile_project_errors('portrait', MOBILE_INI, 'Tide'), [])
        self.assertIn('PackageName=com.tide.game', vg.mobile_project_errors('portrait', MOBILE_INI, 'TideRunner')[0])
        on = MOBILE_INI + '[/Script/Engine.RendererSettings]\nr.DynamicGlobalIlluminationMethod=1\nr.Shadow.Virtual.Enable=1\n'
        self.assertEqual(len(vg.mobile_project_errors('portrait', on)), 2)
        off = MOBILE_INI + '[/Script/Engine.RendererSettings]\nr.DynamicGlobalIlluminationMethod=0\n'
        self.assertEqual(vg.mobile_project_errors('portrait', off), [])

    def test_what_the_other_tools_read(self):
        """`--platform`: one answer for the pipeline and the packagers, with the size a play and a recording have."""
        self.assertEqual(vg.platform_of(self.game()),
                         {'platform': 'desktop', 'orientation': None, 'width': 1920, 'height': 1080})
        self.assertEqual(vg.platform_of(self.game({'platform': 'mobile', 'orientation': 'landscape'})),
                         {'platform': 'mobile', 'orientation': 'landscape', 'width': 1920, 'height': 1080})
        self.assertEqual(vg.platform_of(self.game({'platform': 'mobile', 'orientation': 'portrait'})),
                         {'platform': 'mobile', 'orientation': 'portrait', 'width': 1080, 'height': 1920})
        with self.assertRaises(ValueError):
            vg.platform_of(self.game('{"platform": "desktop"}'))
        script = os.path.join(TOOLS, 'validate-game.py')
        run = lambda d: subprocess.run([sys.executable, script, d, '--platform'], capture_output=True, text=True)
        out = run(self.game({'platform': 'mobile', 'orientation': 'portrait'}))
        self.assertEqual((out.returncode, json.loads(out.stdout)['height']), (0, 1920))
        self.assertEqual(json.loads(run(self.game()).stdout)['platform'], 'desktop')
        bad = run(self.game('not json'))
        self.assertEqual((bad.returncode, bad.stdout), (2, ''))

    def test_a_datasets_manifest_and_project_say_the_same_platform(self):
        class View:
            def __init__(self, files):
                self.files = files

            def has(self, rel):
                return rel in self.files

            def open_text(self, rel):
                import io
                return io.StringIO(self.files[rel])
        port = '{"platform": "mobile", "orientation": "portrait"}'
        mobile = {'variant': 'full', 'platform': {'kind': 'mobile', 'orientation': 'portrait'}, 'build': {'apk': None}}
        errs = vg.dataset_platform_errors
        self.assertEqual(errs({'variant': 'full', 'build': {}}, View({})), [])                       # a desktop game
        self.assertEqual(errs({'variant': 'full', 'build': {'apk': None}}, View({})), [])            # a desktop game
        for build in ({'apk': None}, {}):                                                            # no APK: refused
            e = errs(dict(mobile, build=build), View({'UEProject/Platform.json': port}))
            self.assertEqual(len(e), 1, build)
            self.assertIn("build.apk is null or missing on a mobile game", e[0])
            self.assertIn('Android toolchain', e[0])
        self.assertEqual(errs(dict(mobile, build={'apk': 'Android/Tide-arm64.apk'}),
                              View({'UEProject/Platform.json': port, 'Build/Android/Tide-arm64.apk': ''})), [])
        self.assertIn('is not in the dataset', errs(dict(mobile, build={'apk': 'Android/Tide-arm64.apk'}),
                                                    View({'UEProject/Platform.json': port}))[0])
        self.assertIn('none: a desktop game', errs(mobile, View({}))[0])
        self.assertIn('a mobile game held in portrait', errs({'variant': 'full', 'build': {}},
                                                              View({'UEProject/Platform.json': port}))[0])
        self.assertIn('held in portrait', errs(dict(mobile, platform={'kind': 'mobile', 'orientation': 'landscape'}),
                                               View({'UEProject/Platform.json': port}))[0])
        self.assertEqual(errs(dict(mobile, variant='repo-dataset', build=None), View({})), [])       # the repo's Dataset/
        schema = vg.SCHEMAS['dataset-manifest']['properties']
        self.assertEqual(list(vg.check_schema(mobile['platform'], schema['platform'])), [])
        self.assertTrue(list(vg.check_schema({'kind': 'mobile'}, schema['platform'])))
        self.assertTrue(list(vg.check_schema({'kind': 'desktop', 'orientation': 'portrait'}, schema['platform'])))

    def test_a_platform_file_that_says_neither_is_an_error_never_desktop(self):
        for bad in ('{"platform": "desktop"}', '{"platform": "mobile"}', 'not json',
                    '{"platform": "mobile", "orientation": "sideways"}'):
            self.assertEqual(len(self.said(self.game(bad, MOBILE_INI))), 1, bad)

    def test_an_uncommitted_platform_file_and_a_missing_config_are_named(self):
        d = self.game({'platform': 'mobile', 'orientation': 'portrait'}, MOBILE_INI)
        self.assertIn('not committed', self.said(d, files=())[0])
        self.assertIn('no Config/DefaultEngine.ini', self.said(self.game({'platform': 'mobile', 'orientation': 'portrait'}))[0])

    def test_a_mobile_tasks_play_never_chooses_the_renderer(self):
        def task(args):
            return {'milestones': [{'checks': [
                {'kind': 'probe', 'name': 'a', 'play': {'name': 'p', 'seconds': 10, 'args': args}},
                {'kind': 'judge', 'name': 'b', 'plays': [{'name': 'q', 'seconds': 10, 'args': ['-Scenario=2']}]}]}]}
        self.assertEqual(vg.mobile_play_errors(task(['-Scenario=1'])), [])
        for arg in ('-sm6', '-vulkan', '-FeatureLevelES31', '-d3d12', '-Opt=x,dx11=1'):
            self.assertEqual(len(vg.mobile_play_errors(task([arg]))), 1, arg)


if __name__ == '__main__':
    unittest.main()

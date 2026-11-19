"""tools/validate-game.py's rules on their own, without a repo.

    python -m unittest discover -s tools/tests -p "test_validate_game.py" -v
"""
import importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('validate_game', os.path.join(TOOLS, 'validate-game.py'))
vg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vg)


def make_game(parent, slug='lantern-hollow'):
    """A small game repo under `parent`, named `slug`: a UE 5.7 start (a night village with a lantern, a GameMode that
    parses the Scenario option, the CellarStairs and VillageWell tags, a pause menu's Resume button) and four commits
    that change the game (lantern light, sprint, a stamina HUD with its StaminaBar widget, a Stamina member, the
    SkipToDawn option, a Rest by the fire button and a cellar level, a camera rig). Returns (repo, git, start, reference)."""
    repo = os.path.join(parent, slug)
    os.makedirs(repo)

    def git(*args):
        return subprocess.run(['git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                              capture_output=True, check=True).stdout.decode().strip()

    def write(rel, text):
        path = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(path) or repo, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)

    def commit(msg):
        git('add', '-A')
        git('commit', '-q', '-m', msg)
        return git('rev-parse', 'HEAD')

    def lines(name, n):
        return ''.join(f'float {name}{i} = {i}.0f;\n' for i in range(n))

    git('init', '-q', '-b', 'main')
    write('LanternHollow.uproject', '{"FileVersion": 3, "EngineAssociation": "5.7"}\n')
    write('Config/DefaultGame.ini', '[/Script/LanternHollow.LHGameInstance]\nScenarioMaps=/Game/Maps/L_Village\n')
    write('Source/LanternHollow/LHGameMode.cpp',
          'void ALHGameMode::InitGame() { Scenario = UGameplayStatics::GetIntOption(Options, TEXT("Scenario"), 1); }\n'
          'void ALHGameMode::Tag() { Stairs->Tags.Add(TEXT("CellarStairs")); Well->Tags.Add(TEXT("VillageWell")); }\n')
    write('Source/LanternHollow/LHPauseMenu.cpp', 'Resume->SetText(LOCTEXT("Resume", "Resume"));\n')
    write('Content/Maps/L_Village.umap', 'map\n')
    start = commit('night village')
    write('Source/LanternHollow/LHLantern.cpp', lines('LanternRadius', 40))
    write('Config/DefaultEngine.ini', '[/Script/Engine.RendererSettings]\nr.DefaultFeature.AutoExposure=True\n')
    commit('lantern light reaches the path')
    write('Source/LanternHollow/LHCharacter.cpp', lines('SprintSpeed', 30) + 'float Stamina = 100.0f;\n')
    commit('sprint with the lantern')
    write('Source/LanternHollow/LHStaminaHUD.cpp',
          lines('BarWidth', 30) + 'StaminaBar = WidgetTree->ConstructWidget<UProgressBar>(TEXT("StaminaBar"));\n'
          'Rest->SetText(LOCTEXT("Rest", "Rest by the fire"));\n')
    write('Source/LanternHollow/LHGameMode.cpp',
          'void ALHGameMode::InitGame() { Scenario = UGameplayStatics::GetIntOption(Options, TEXT("Scenario"), 1);\n'
          '  bSkipToDawn = UGameplayStatics::HasOption(Options, TEXT("SkipToDawn")); }\n'
          'void ALHGameMode::Tag() { Stairs->Tags.Add(TEXT("CellarStairs")); Well->Tags.Add(TEXT("VillageWell"));\n'
          '  Door->Tags.Add(TEXT("CellarDoor")); }\n')
    write('Content/Maps/L_Cellar.umap', 'map\n')
    commit('stamina readout, cellar level')
    write('Source/LanternHollow/LHCameraRig.cpp', lines('ProbeSize', 30))
    reference = commit('camera stays out of the cellar walls')
    return repo, git, start, reference


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

    def test_one_looks_judge(self):
        """One `looks_as_asked` judge, its items keyed asked_ or keep_ (the owner, 2026-11-19): with an asked item in
        an outcome milestone with weight, with keep items only in still_works with weight 0, required, every item
        marked, no other required judge in still_works beside it; the marks on no other judge. A task written before
        the merge (no marks, a second judge in still_works) is left as it was."""
        def judge(keys, name='looks_as_asked', **over):
            return {'name': name, 'kind': 'judge', 'question': 'q',
                    'rubric': [{'key': k, 'criterion': 'c'} for k in keys], **over}

        def task(done=(), still=()):
            return {'milestones': [{'name': 'done', 'checks': list(done)},
                                   {'name': 'still_works', 'checks': list(still)}]}
        ok = vg.looks_judge_errors
        self.assertEqual(ok(task([judge(['asked_amber', 'keep_square'])])), [])
        self.assertEqual(ok(task(still=[judge(['keep_square'], weight=0)])), [])
        self.assertEqual(ok(task([judge(['amber'])], [judge(['square'], 'square_unchanged', weight=0)])), [])
        self.assertIn('in still_works', ok(task(still=[judge(['asked_amber'], weight=0)]))[0])
        self.assertIn('carries weight', ok(task([judge(['asked_amber'], weight=0)]))[0])
        weighted = 'has only keep items, which a no-op passes: it goes in still_works with "weight": 0'
        self.assertIn(weighted, ok(task([judge(['keep_square'])]))[0])
        self.assertIn(weighted, ok(task(still=[judge(['keep_square'], weight=1)]))[0])
        self.assertIn('carry no mark', ok(task([judge(['asked_amber', 'square'])]))[0])
        self.assertIn('is required', ok(task([judge(['asked_amber'], required=False)]))[0])
        self.assertIn('belong only on the looks_as_asked judge', ok(task([judge(['asked_amber'], 'lit')]))[0])
        self.assertIn('one looks judge', ok(task([judge(['asked_amber'])],
                                                 [judge(['square'], 'square_unchanged', weight=0)]))[0])
        self.assertEqual(ok(task([judge(['asked_amber'])], [judge(['square'], 'tidy', weight=0, required=False)])), [])

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
                         ['task play restarted continues earns, which runs after other plays: the sessions a play '
                          'continues start from a cleared save, alone'])
        chain = [{'name': f's{i}', 'seconds': 10, **({'continues': f's{i - 1}'} if i else {})} for i in range(6)]
        self.assertEqual(vg.play_continues_errors(checks(*chain[:5])), [])
        self.assertIn('task play s5 continues a chain of 5 sessions, more than 4', vg.play_continues_errors(checks(*chain)))
        loop = [{'name': 'a', 'seconds': 10, 'continues': 'b'}, {'name': 'b', 'seconds': 10, 'continues': 'a'}]
        self.assertTrue(any('come back to' in e for e in vg.play_continues_errors(checks(*loop))))
        self.assertEqual(vg.play_continues_errors(checks({**again, 'after': ['earns']}, first)),
                         ['task play restarted continues a session and runs after plays too: name one or the other'])
        schema = vg.SCHEMAS['game-task']
        self.assertEqual(list(vg.check_schema(again, schema['$defs']['TaskPlay'], schema)), [])
        self.assertTrue(list(vg.check_schema({**again, 'continues': 'Not A Name'}, schema['$defs']['TaskPlay'], schema)))
        click = schema['$defs']['Click']['properties']['widget']
        for ok in ('Start', '按铃开店 →', '1    BUY RANK   300 PT'):
            self.assertEqual(list(vg.check_schema(ok, click, schema)), [])
        for bad in (' Start', 'Start ', 'a\nb', ''):
            self.assertTrue(list(vg.check_schema(bad, click, schema)), bad)
        self.assertIsNone(vg.TASK_PLAY_DEFAULTS['continues'])

    def test_a_play_on_the_start_continues_a_session_and_saves_take_two_stages(self):
        """`first_on_start` plays the sessions a play continues on the start, so it names one; `saves` is unreadable
        or unwritable."""
        schema, defs = vg.SCHEMAS['game-task'], vg.SCHEMAS['game-task']['$defs']['TaskPlay']
        old = {'name': 'loads', 'seconds': 10, 'continues': 'saves', 'first_on_start': True}
        self.assertEqual(list(vg.check_schema(old, defs, schema)), [])
        self.assertEqual(vg.task_play_errors('c', old, {}), [])
        self.assertIn('check c: play loads plays its first session on the start, so it continues a session: name it '
                      'in `continues`', vg.task_play_errors('c', {**old, 'continues': None}, {}))
        for stage in ('unreadable', 'unwritable'):
            self.assertEqual(list(vg.check_schema({'name': 's', 'seconds': 10, 'saves': stage}, defs, schema)), [])
        self.assertTrue(list(vg.check_schema({'name': 's', 'seconds': 10, 'saves': 'deleted'}, defs, schema)))
        self.assertIsNone(vg.TASK_PLAY_DEFAULTS['first_on_start'])

    def test_a_fresh_play_starts_alone(self):
        """`fresh` clears the save before the play, so it runs after no play and continues no session."""
        schema = vg.SCHEMAS['game-task']
        fresh = {'name': 'starts', 'seconds': 10, 'fresh': True}
        self.assertEqual(list(vg.check_schema(fresh, schema['$defs']['TaskPlay'], schema)), [])
        self.assertTrue(list(vg.check_schema({**fresh, 'fresh': False}, schema['$defs']['TaskPlay'], schema)))
        self.assertEqual(vg.task_play_errors('c', fresh, {}), [])
        for more in ({'after': ['other']}, {'continues': 'other'}):
            self.assertIn('check c: play starts starts from a cleared save (fresh), so it runs after no play and '
                          'continues no session', vg.task_play_errors('c', {**fresh, **more}, {}))
        self.assertIsNone(vg.TASK_PLAY_DEFAULTS['fresh'])
        plays = {}
        vg.task_play_errors('a', {'name': 'p', 'seconds': 10}, plays)
        self.assertIn('check b: task play p differs from another play of that name',
                      vg.task_play_errors('b', {'name': 'p', 'seconds': 10, 'fresh': True}, plays))

    def test_a_window_tied_to_its_event(self):
        """A sampled measure's `since` names an event: one sample of a measure the play samples (no window, at, agg or
        since of its own; never log, asset, seen, trace, audio sounds, repeats or waves), a literal expect, an
        optional `within` (0 < s <= 1200); the event's measure keeps a measure's shape rules."""
        schema = vg.SCHEMAS['game-task']
        event = {'measure': {'probe': 'widgets', 'select': {'name': 'ResultPanel'}, 'field': 'count'},
                 'expect': {'op': '>=', 'value': 1}}
        tied = {'probe': 'pawn', 'field': 'x', 'since': event, 'window': [0, 1]}
        fits = lambda m: list(vg.check_schema(m, schema['$defs']['PawnMeasure'], schema))  # noqa: E731
        for ok in (tied, {**tied, 'since': {**event, 'within': 30}}, {**tied, 'since': {**event, 'within': 1200}},
                   {**tied, 'since': None}):
            self.assertEqual(fits(ok), [], ok)
            self.assertEqual(vg.since_errors('c', ok), [])
        for bad in ({**event, 'expect': {'op': '>=', 'calibrate': 0.5}}, {**event, 'within': 0},
                    {**event, 'within': 1201}, {'measure': event['measure']}, {**event, 'at': 2}):
            self.assertTrue(fits({**tied, 'since': bad}), bad)
        self.assertTrue(list(vg.check_schema({'probe': 'log', 'pattern': 'x', 'since': event},
                                             schema['$defs']['LogMeasure'], schema)))
        for inner, said in (({'window': [0, 2]}, 'takes no window of its own'), ({'at': 'end'}, 'takes no at'),
                            ({'agg': 'max'}, 'takes no agg'), ({'since': event}, 'takes no since'),
                            ({'probe': 'log', 'pattern': 'x'}, 'one the probe samples'),
                            ({'probe': 'audio', 'field': 'repeats'}, 'one the probe samples'),
                            ({'probe': 'audio', 'field': 'waves'}, 'one the probe samples'),
                            ({'select': {}}, 'a widget select names its class, its name or its Slate type')):
            found = vg.since_errors('c', {**tied, 'since': {**event, 'measure': {**event['measure'], **inner}}})
            self.assertTrue(any(said in e for e in found), (inner, found))
        self.assertEqual(vg.since_errors('c', {'probe': 'pawn', 'field': 'x'}), [])

    def test_a_click_by_its_text_optional_or_disabled(self):
        """A click names its button by name, class or on-screen text (spaces and punctuation as shown); `optional`
        and `disabled` are true or unset."""
        schema = vg.SCHEMAS['game-task']
        click = lambda **k: list(vg.check_schema(dict({'t': 1.0, 'widget': 'StartButton', 'click': True}, **k),
                                                 schema['$defs']['Click'], schema))
        for ok in ({}, {'widget': 'New expedition'}, {'widget': "Don't save: quit (1/2) & go!"}, {'widget': '按铃开店 →'},
                   {'optional': True}, {'disabled': True}, {'optional': None}):
            self.assertEqual(click(**ok), [], ok)
        for bad in ({'widget': ' New'}, {'widget': 'a' * 121}, {'widget': 'New\nexpedition'},
                    {'optional': False}, {'disabled': 'yes'}, {'hidden': True}):
            self.assertTrue(click(**bad), bad)

    def test_a_widget_select_may_say_drawn_or_not(self):
        schema = vg.SCHEMAS['game-task']
        for said in (True, False):
            self.assertEqual(list(vg.check_schema({'name': 'Warn*', 'visible': said}, schema['$defs']['WidgetSelect'],
                                                  schema)), [])
        self.assertTrue(list(vg.check_schema({'name': 'Warn*', 'visible': 1}, schema['$defs']['WidgetSelect'], schema)))

    def test_a_short_span_warns_and_never_rejects(self):
        """The size of a span is a soft bar: a start and a reference one small commit apart (a returned task rebuilt
        around a fix of the game) get a warning for each number they are under, and no error."""
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo, True)
        def git(*args):
            return subprocess.run(['git', '-C', repo, '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                                  capture_output=True, check=True).stdout.decode().strip()
        git('init', '-q')
        os.makedirs(os.path.join(repo, 'Source'))
        for text in ('int Door = 1;\n', 'int Door = 2;\n'):
            with open(os.path.join(repo, 'Source', 'Door.cpp'), 'w') as f:
                f.write(text)
            git('add', '-A')
            git('commit', '-q', '-m', 'door')
        seed = {'commit': git('rev-parse', 'HEAD~1'), 'reference': git('rev-parse', 'HEAD')}
        self.assertEqual(len(vg.thread_span_errors(repo, seed, True)), 4, 'files, code lines, systems and commits')
        rep = vg.Report()
        vg.report_thread_span(rep, 'tasks', 'game-fix-door', repo, seed, True)
        self.assertEqual([sev for sev, _, _ in rep.items], ['warning'] * 4)
        self.assertTrue(all('soft bar' in msg for _, _, msg in rep.items))

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


class Seen(unittest.TestCase):
    """A `seen` measure (text a model reads from a named shot; docs/task-probes.md 2.22) and the Lab's rules for it."""
    SCHEMA = vg.SCHEMAS['game-task']
    PLAY = {'name': 'three_hits', 'seconds': 10,
            'inputs': [{'t': 1.0, 'key': 'J', 'press': True}, {'t': 1.1, 'key': 'J', 'press': False},
                       {'t': 3.6, 'shot': 'combo'}, {'t': 6.0, 'shot': 'later'}, {'t': 8.0, 'shot': 'last'}]}

    def check(self, measure, play=None, expect=None, **over):
        return dict({'name': 'combo_shows', 'kind': 'probe', 'describe': 'The combo counter drawn on the HUD reads 3',
                     'play': self.PLAY if play is None else play, 'measure': dict({'probe': 'seen'}, **measure),
                     'expect': expect or {'op': '>=', 'value': 3}}, **over)

    def errors(self, measure, play=None, expect=None):
        c = self.check(measure, play, expect)
        return (list(vg.check_schema(c, self.SCHEMA['$defs']['Probe'], self.SCHEMA))
                + vg.probe_errors(c, {'commit': 'a', 'reference': 'b'}, 'b', {}))

    def test_the_shapes_the_lab_takes(self):
        for measure in ({'shot': 'combo', 'rect': [0.70, 0.04, 0.98, 0.16], 'read': 'number'},
                        {'shot': 'combo', 'read': 'number'},                        # no rect: the whole frame
                        {'shot': 'combo', 'read': 'text', 'match': r'COMBO\s*x?3'},
                        {'shot': 'combo', 'read': 'clock', 'rect': [0.4, 0.0, 0.6, 0.02]},
                        {'shot': ['combo', 'later'], 'read': 'number', 'agg': 'rises'},
                        {'shot': ['combo', 'later', 'last'], 'read': 'clock', 'agg': 'delta'}):
            self.assertEqual(self.errors(measure), [], measure)
        for expect in ({'op': '>=', 'calibrate': 0.5}, {'op': '>=', 'start_plus': 1}, {'op': '==', 'value': 1}):
            self.assertEqual(self.errors({'shot': 'combo', 'read': 'number'}, expect=expect), [], expect)

    def test_the_schema_refuses_what_the_lab_refuses(self):
        for measure in ({'shot': 'Combo', 'read': 'number'}, {'shot': ['combo'], 'read': 'number', 'agg': 'max'},
                        {'shot': ['a', 'b', 'c', 'd', 'e'], 'read': 'number', 'agg': 'max'},
                        {'shot': 'combo', 'read': 'number', 'rect': [0, 0, 1.2, 1]},
                        {'shot': 'combo', 'read': 'number', 'rect': [0, 0, 1]},
                        {'shot': 'combo', 'read': 'words'}, {'read': 'number'}, {'shot': 'combo'},
                        {'shot': 'combo', 'read': 'text', 'match': ''},
                        {'shot': 'combo', 'read': 'text', 'match': 'x' * 201},
                        {'shot': ['combo', 'later'], 'read': 'number', 'agg': 'mean'},
                        {'shot': 'combo', 'read': 'number', 'window': [1, 2]},          # no other key
                        {'shot': 'combo', 'read': 'number', 'field': 'number'}):
            c = self.check(measure)
            self.assertTrue(list(vg.check_schema(c, self.SCHEMA['$defs']['Probe'], self.SCHEMA)), measure)

    def test_the_rules_the_schema_cannot_say(self):
        def said(measure, play=None):
            return vg.seen_errors('combo_shows', measure, self.PLAY if play is None else play)
        for play in ('look', 'drive', 'editor'):
            self.assertEqual(said({'shot': 'combo', 'read': 'number'}, play),
                             [f'check combo_shows: a seen measure reads a named shot of a task play of its own, never of {play}'])
        self.assertEqual(said({'shot': 'menu', 'read': 'number'}),
                         ['check combo_shows: its play three_hits takes no shot named menu (a `shot` input)'])
        self.assertEqual(said({'shot': ['combo', 'menu'], 'read': 'number', 'agg': 'max'}),
                         ['check combo_shows: its play three_hits takes no shot named menu (a `shot` input)'])
        tight = 'check combo_shows: a seen rect is [x0, y0, x1, y1], at least 0.02 of the frame each way'
        self.assertEqual(said({'shot': 'combo', 'read': 'number', 'rect': [0.5, 0.5, 0.51, 0.9]}), [tight])
        self.assertEqual(said({'shot': 'combo', 'read': 'number', 'rect': [0.5, 0.5, 0.9, 0.515]}), [tight])
        self.assertEqual(said({'shot': 'combo', 'read': 'number', 'rect': [0.9, 0.5, 0.5, 0.9]}), [tight])
        self.assertEqual(said({'shot': 'combo', 'read': 'number', 'rect': [0.5, 0.5, 0.52, 0.52]}), [])
        match = 'check combo_shows: a seen measure takes `match` exactly when it reads text'
        self.assertEqual(said({'shot': 'combo', 'read': 'text'}), [match])
        self.assertEqual(said({'shot': 'combo', 'read': 'number', 'match': '3'}), [match])
        self.assertIn("isn't a regular expression", said({'shot': 'combo', 'read': 'text', 'match': '(3'})[0])
        listed = 'check combo_shows: a seen measure reads a list of shots as a number or a clock, with an `agg`'
        self.assertEqual(said({'shot': ['combo', 'later'], 'read': 'number'}), [listed])
        self.assertEqual(said({'shot': ['combo', 'later'], 'read': 'text', 'match': '3', 'agg': 'max'}), [listed])
        self.assertEqual(said({'shot': ['combo', 'combo'], 'read': 'number', 'agg': 'max'}),
                         ['check combo_shows: a seen measure names a shot twice'])
        self.assertEqual(said({'shot': 'combo', 'read': 'number', 'agg': 'max'}),
                         ['check combo_shows: a seen measure of one shot takes no `agg`'])
        self.assertEqual(said({'shot': 'combo', 'read': 'number'}), [])

    def test_a_task_with_one_validates_and_it_is_no_outcome(self):
        """A seen probe is a visual check, read by a model like a judge's: it gates in the task check but is no
        outcome the grader decides itself; it is no literal-refused field, names nothing the reference may add, and takes no
        capture of the probe's own, so a render measure may share its play."""
        render = {'name': 'budget', 'kind': 'probe', 'describe': 'Draw calls stay in budget', 'play': self.PLAY,
                  'measure': {'probe': 'render', 'field': 'draw_calls', 'agg': 'max'}, 'expect': {'op': '<=', 'value': 700}}
        t = {'milestones': [{'name': 'fix', 'checks': [self.check({'shot': 'combo', 'read': 'number'}), render]}]}
        self.assertEqual(vg.task_semantic_errors(t), [])
        self.assertEqual(vg.render_errors(t['milestones'][0]['checks']), [])
        self.assertEqual([c['name'] for c in vg.outcome_probes(t)], ['budget'])
        self.assertEqual(vg.probe_names(t['milestones'][0]['checks'][0]), (set(), set()))

    def test_a_seen_probe_alone_is_no_required_probe(self):
        """As the Lab's dataset format: a task needs a required probe besides its visual checks (a seen probe is a
        model's reading)."""
        def said(*checks):
            rep = vg.Report()
            vg.check_task(rep, 'tasks', 't', {'milestones': [{'name': 'fix', 'checks': list(checks)}]}, 'g', None)
            return [m for sev, _a, m in rep.items if sev == 'error' and 'no required probe check' in m]
        seen = self.check({'shot': 'combo', 'read': 'number'})
        self.assertEqual(len(said(seen)), 1)
        self.assertEqual(len(said(seen, dict(seen, name='hud', measure={'probe': 'ui', 'field': 'number'}))), 0)
        self.assertTrue(vg.is_seen(seen))
        self.assertFalse(vg.is_seen(dict(seen, measure={'probe': 'ui', 'field': 'number'})))


class Shapes(unittest.TestCase):
    """The shapes of a measure, a select and a play's inputs that the cloud grader's own task model refuses and the
    schema can't say (measure_errors, select_errors, task_play_errors): each is refused here too, so a task that
    validates here is read the same way there."""
    SCHEMA = vg.SCHEMAS['game-task']
    NEAR = {'point': {'xyz': [0, 0, 0]}, 'radius': 100}

    def errors(self, measure=None, play='look', **over):
        c = dict({'name': 'c', 'kind': 'probe', 'describe': 'd', 'play': play,
                  'measure': measure or {'probe': 'pawn', 'field': 'z', 'window': [3, 18], 'agg': 'min'},
                  'expect': {'op': '>=', 'value': 0}}, **over)
        return (list(vg.check_schema(c, self.SCHEMA['$defs']['Probe'], self.SCHEMA))
                + vg.probe_errors(c, {'commit': 'a', 'reference': 'b'}, 'b', {}))

    def refused(self, said, measure=None, play='look'):
        found = self.errors(measure, play)
        self.assertTrue(any(said in e for e in found), (said, found))

    def test_valid_shapes_still_pass(self):
        for measure in ({'probe': 'actors', 'select': {'class': 'Door'}, 'field': 'prop:bOpen', 'match': 'true', 'of': 'any'},
                        {'probe': 'actors', 'select': {'player': True}, 'field': 'yaw', 'to_angle': 90, 'of': 'first'},
                        {'probe': 'actors', 'select': {'class': 'X', 'where': [{'prop': 'Hp', 'op': '>', 'value': 0}]},
                         'field': 'count'},
                        {'probe': 'actors', 'select': {'class': 'X'}, 'field': 'prop:Heading', 'to_axis': 0, 'of': 'max'},
                        {'probe': 'camera', 'field': 'yaw', 'window': [3, 18], 'agg': 'min', 'to_angle': 90},
                        {'probe': 'pawn', 'field': 'dist', 'to': {'xyz': [0, 0, 0]}, 'window': [0, 120], 'agg': 'min'},
                        {'probe': 'widgets', 'select': {'class': 'WBP_HUD_C'}, 'field': 'text', 'match': r'\d+',
                         'of': 'any'},
                        {'probe': 'widgets', 'select': {'slate': 'STextBlock', 'text': 'Score'}, 'field': 'visible',
                         'of': 'any'},
                        {'probe': 'audio', 'field': 'sounds', 'select': {'sound': 'Shot*'}},
                        {'probe': 'audio', 'field': 'count', 'select': {'owner': {'class': 'Radio'}}, 'agg': 'max'}):
            self.assertEqual(self.errors(measure), [], measure)
        for measure in ({'probe': 'asset', 'asset': '/Game/Data/DA_Hero', 'field': 'prop:Speed'},
                        {'probe': 'asset', 'map': '/Game/Maps/L_Arena', 'select': {'class': 'Spawner'},
                         'field': 'count'},
                        {'probe': 'asset', 'map': '/Game/Maps/L_Arena', 'select': {'near': self.NEAR}, 'field': 'count'}):
            self.assertEqual(self.errors(measure, 'editor'), [], measure)
        play = {'name': 'p', 'seconds': 10, 'inputs': [{'t': 1, 'wheel': -2}, {'t': 2, 'move': [3, 0]},
                                                         {'t': 3, 'teleport_to': {'tag': 'Gate'}}]}
        self.assertEqual(self.errors(play=play), [])

    def test_selects(self):
        self.refused('a select names at least one of class, tag, name, near, player, has',
                     {'probe': 'actors', 'select': {}, 'field': 'count'})
        self.refused('a select names at least one of',
                     {'probe': 'actors', 'select': {'player': False}, 'field': 'count'})
        self.refused('a select names at least one of',
                     {'probe': 'actors', 'select': {'where': [{'prop': 'A', 'op': '==', 'value': 1}]}, 'field': 'count'})
        self.refused('a where value is at most 120 characters',
                     {'probe': 'actors', 'select': {'class': 'X', 'where': [{'prop': 'A', 'op': '==', 'value': 'x' * 121}]},
                      'field': 'count'})
        self.refused('a select names at least one of',
                     {'probe': 'components', 'select': {'class': 'C', 'owner': {}}, 'field': 'count'})
        self.refused('a select names at least one of',
                     play={'name': 'p', 'seconds': 10, 'inputs': [{'t': 1, 'teleport_to': {}}]})
        self.refused('a widget select names its class, its name or its Slate type',
                     {'probe': 'widgets', 'select': {}, 'field': 'visible', 'of': 'any'})
        self.refused('a widget select names a UMG class or a Slate type, not both',
                     {'probe': 'widgets', 'select': {'class': 'W', 'slate': 'STextBlock'}, 'field': 'visible', 'of': 'any'})

    def test_times_and_angles(self):
        self.refused('a window is [t0, t1] with 0 <= t0 < t1 <= 1200',
                     {'probe': 'pawn', 'field': 'z', 'window': [3, 1210], 'agg': 'min'})
        self.assertEqual(self.errors({'probe': 'pawn', 'field': 'z', 'window': [130, 1199], 'agg': 'min'}), [],
                         'a play lasts up to 1200 s, and its windows with it')
        self.refused('a window is [t0, t1]', {'probe': 'camera', 'field': 'yaw', 'window': [5, 5], 'agg': 'min'})
        self.refused('a measure takes `to_angle` or `to_axis`, not both',
                     {'probe': 'camera', 'field': 'yaw', 'window': [3, 18], 'agg': 'min', 'to_angle': 1, 'to_axis': 1})
        self.refused('`to_angle`/`to_axis` go with an angle field',
                     {'probe': 'pawn', 'field': 'z', 'window': [3, 18], 'agg': 'min', 'to_angle': 90})

    def test_fields(self):
        self.refused('a pawn measure takes `to` (a point) exactly when its field is dist',
                     {'probe': 'pawn', 'field': 'dist', 'window': [3, 18], 'agg': 'min'})
        self.refused('`match` goes with a prop: or bb: field',
                     {'probe': 'actors', 'select': {'class': 'X'}, 'field': 'z', 'match': 'a', 'of': 'max'})
        for measure in ({'probe': 'widgets', 'select': {'class': 'W'}, 'field': 'text', 'of': 'any'},
                        {'probe': 'widgets', 'select': {'class': 'W'}, 'field': 'brush', 'of': 'any'},
                        {'probe': 'widgets', 'select': {'class': 'W'}, 'field': 'visible', 'match': 'x', 'of': 'any'}):
            self.refused('a widgets measure takes `match` exactly when its field is text or brush', measure)
        self.refused("isn't a regular expression",
                     {'probe': 'widgets', 'select': {'class': 'W'}, 'field': 'text', 'match': '(', 'of': 'any'})
        self.refused("isn't a regular expression",
                     {'probe': 'actors', 'select': {'class': 'W'}, 'field': 'prop:Name', 'match': '[', 'of': 'any'})
        for field in ('sounds', 'repeats', 'waves'):
            self.refused(f'audio `{field}` is read over the starts of every sample picked, so it takes no agg',
                         {'probe': 'audio', 'field': field, 'agg': 'max'})
        self.refused('audio `started` takes no `owner`',
                     {'probe': 'audio', 'field': 'started', 'select': {'owner': {'class': 'X'}}})
        for rect in ([0.8, 0.1, 0.2, 0.9], [0.1, 0.9, 0.9, 0.1], [0.5, 0.1, 0.5, 0.9]):
            self.refused('a screen rect is [x0, y0, x1, y1] with x0 < x1 and y0 < y1',
                         {'probe': 'screen', 'rect': rect, 'field': 'luminance'})
        self.assertFalse([e for e in self.errors({'probe': 'screen', 'rect': [0.1, 0.1, 0.9, 0.9], 'field': 'luminance'})
                          if 'rect' in e])

    def test_asset_measures(self):
        cases = [("an asset measure names an `asset` or a `map`, one of them",
                  {'probe': 'asset', 'map': '/Game/M', 'asset': '/Game/A', 'select': {'class': 'A'}, 'field': 'count'}),
                 ('an `asset` measure reads a prop:<property> and takes no select',
                  {'probe': 'asset', 'asset': '/Game/A', 'field': 'prop:X', 'select': {'class': 'A'}}),
                 ('an `asset` measure reads a prop:<property> and takes no select',
                  {'probe': 'asset', 'asset': '/Game/A', 'field': 'count'}),
                 ('a `map` measure selects its actors (`select`)',
                  {'probe': 'asset', 'map': '/Game/M', 'field': 'count'}),
                 ('a map as saved has no player or camera',
                  {'probe': 'asset', 'map': '/Game/M', 'select': {'player': True}, 'field': 'count'}),
                 ('a map as saved has no player or camera',
                  {'probe': 'asset', 'map': '/Game/M', 'select': {'near': {'point': {'pawn': True}, 'radius': 100}},
                   'field': 'count'}),
                 ('never by `where` or `player`',
                  {'probe': 'asset', 'map': '/Game/M', 'select': {'class': 'A', 'where': [{'prop': 'A', 'op': '==',
                                                                                           'value': 1}]},
                   'field': 'count'}),
                 ('a measure takes `to_angle` or `to_axis`, not both',
                  {'probe': 'asset', 'asset': '/Game/A', 'field': 'prop:Yaw', 'to_angle': 9, 'to_axis': 9})]
        for said, measure in cases:
            self.refused(said, measure, 'editor')

    def test_a_shots_when_and_a_widgets_covered(self):
        """A shot may say `when`, an event the probe reads itself every frame: widgets count or visible, or actors
        count, x, y, z, hidden or a prop: member, no to_angle or to_axis, no has.lit, and every rule of an event; a
        widgets measure may read `covered`; a play lasts up to 1200 s."""
        def shot(measure, **more):
            return {'name': 'p', 'seconds': 1200, 'inputs': [
                {'t': 1, 'shot': 's', 'when': {'measure': measure, 'expect': {'op': '>=', 'value': 1}, **more}}]}
        for measure in ({'probe': 'widgets', 'select': {'name': 'Result'}, 'field': 'count'},
                        {'probe': 'widgets', 'select': {'name': 'Result'}, 'field': 'visible', 'of': 'any'},
                        {'probe': 'actors', 'select': {'class': 'Boat'}, 'field': 'z', 'of': 'max'},
                        {'probe': 'actors', 'select': {'class': 'Boat'}, 'field': 'prop:Health', 'of': 'min'}):
            self.assertEqual(self.errors(play=shot(measure, within=1199)), [], measure)
        for measure, said in (({'probe': 'ui', 'field': 'count'}, 'reads widgets count or visible'),
                              ({'probe': 'widgets', 'select': {'name': 'W'}, 'field': 'text', 'match': 'x'},
                               'reads widgets count or visible'),
                              ({'probe': 'actors', 'select': {'class': 'Boat'}, 'field': 'speed'},
                               'reads widgets count or visible'),
                              ({'probe': 'actors', 'select': {'class': 'Boat'}, 'field': 'x', 'to_axis': 0},
                               'takes no to_angle or to_axis'),
                              ({'probe': 'actors', 'select': {'class': 'Lamp', 'has': {'class': 'PointLight',
                                                                                       'lit': True}},
                                'field': 'count'}, 'asks for no lit part'),
                              ({'probe': 'widgets', 'select': {'name': 'W'}, 'field': 'count', 'window': [0, 1]},
                               'takes no window of its own')):
            self.refused(said, play=shot(measure))
        found = self.errors(play=shot({'probe': 'widgets', 'select': {'name': 'W'}, 'field': 'count'}, within=1201))
        self.assertTrue(found, 'within is at most 1200 s')
        self.assertTrue(self.errors(play={'name': 'p', 'seconds': 1201, 'inputs': []}), 'a play lasts at most 1200 s')
        self.assertEqual(self.errors({'probe': 'widgets', 'select': {'name': 'Buy'}, 'field': 'covered', 'of': 'any',
                                      'at': 'end'}), [])

    def test_inputs(self):
        def play(*inputs, **over):
            return dict({'name': 'p', 'seconds': 10, 'inputs': list(inputs)}, **over)
        self.refused('a wheel input turns at least one notch', play=play({'t': 1, 'wheel': 0}))
        self.refused('a move input moves the mouse', play=play({'t': 1, 'move': [0, 0]}))
        self.refused('names a play twice in its after', play=play(after=['q', 'q']))
        self.refused("a task play can't set -GameEnvProbeOff", play=play(args=['-GameEnvProbeOff']))


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


class ReferenceOnlyNames(unittest.TestCase):
    """What a required check or the task's play_map names that the reference has and the start lacks is refused
    (write-tasks sections 4 and 5): a probe's measure and its play, a judge's own plays, play_map; a click's, tap's or
    drag's control and a map pass when the instruction states them; a select's name, a member, a map option or a flag
    never does."""

    @classmethod
    def setUpClass(cls):
        cls.parent = tempfile.mkdtemp()
        cls.repo, _git, cls.start, cls.reference = make_game(cls.parent)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.parent, True)

    def found(self, play=None, kind='probe', required=True, play_map=None, instruction='The lantern is too dim.'):
        play = play or {'name': 'p', 'seconds': 10, 'inputs': []}
        if kind == 'probe':
            check = {'name': 'c', 'kind': 'probe', 'describe': 'd', 'play': play, 'required': required,
                     'measure': {'probe': 'pawn', 'field': 'speed', 'agg': 'max'}, 'expect': {'op': '>', 'value': 0}}
        else:
            check = {'name': 'c', 'kind': 'judge', 'question': 'q', 'required': required, 'plays': [play],
                     'rubric': [{'key': 'k', 'criterion': 'c'}]}
        t = {'title': 'Night play', 'instruction': instruction, 'play_map': play_map,
             'seed': {'commit': self.start, 'reference': self.reference},
             'milestones': [{'name': 'fixed', 'checks': [check]}]}
        return vg.reference_only_names(self.repo, t)

    @staticmethod
    def play(*inputs, **over):
        return {'name': 'p', 'seconds': 10, 'inputs': list(inputs), **over}

    def test_a_click_tap_or_drag_on_a_control_only_the_reference_has(self):
        for i in ({'t': 1, 'widget': 'StaminaBar', 'click': True}, {'t': 1, 'tap': {'widget': 'StaminaBar'}},
                  {'t': 1, 'drag': [[0.5, 0.5], {'widget': 'StaminaBar'}]}):
            self.assertEqual(self.found(self.play(i)), [('c', 'StaminaBar')], i)
            self.assertEqual(self.found(self.play(i), kind='judge'), [('c', 'StaminaBar')], i)
        words = {'t': 1, 'widget': 'Rest by the fire', 'click': True}
        self.assertEqual(self.found(self.play(words)), [('c', 'Rest by the fire')])
        self.assertEqual(self.found(self.play(words), instruction='Clicking "Rest by the fire" refills stamina.'), [])
        self.assertEqual(self.found(self.play({'t': 1, 'widget': 'Resume', 'click': True})), [], 'the start has it')
        self.assertEqual(self.found(self.play({'t': 1, 'widget': 'Stamina*', 'click': True})), [], 'a wildcard')

    def test_a_teleport_pin_or_stage_by_a_name_only_the_reference_has(self):
        door = {'tag': 'CellarDoor'}
        for i in ({'t': 1, 'teleport_to': door}, {'t': 1, 'teleport_to': {'tag': 'VillageWell'}, 'face': {'actor': door}},
                  {'t': 1, 'pin': door, 'hold': 2}, {'t': 1, 'damage': 5, 'to': door},
                  {'t': 1, 'set': 'Scenario', 'value': 1, 'on': door},
                  {'t': 1, 'shot': 's', 'when': {'measure': {'probe': 'actors', 'select': door, 'field': 'count'},
                                                  'expect': {'op': '>=', 'value': 1}}}):
            self.assertEqual(self.found(self.play(i)), [('c', 'CellarDoor')], i)
            self.assertEqual(self.found(self.play(i), instruction='Open the cellar door (CellarDoor).'),
                             [('c', 'CellarDoor')], 'a select never passes for being stated')
        self.assertEqual(self.found(self.play({'t': 1, 'set': 'Stamina', 'value': 0, 'on': {'tag': 'VillageWell'}})),
                         [('c', 'Stamina')], 'a member only the reference has')
        self.assertEqual(self.found(self.play({'t': 1, 'teleport_to': {'tag': 'CellarStairs'}})), [])

    def test_maps_options_and_flags(self):
        self.assertEqual(self.found(play_map='/Game/Maps/L_Village?Scenario=2'), [])
        self.assertEqual(self.found(play_map='/Game/Maps/L_Village?SkipToDawn'), [(None, 'SkipToDawn')])
        self.assertEqual(self.found(self.play(map='/Game/Maps/L_Village?Scenario=2?SkipToDawn=1')),
                         [('c', 'SkipToDawn')])
        self.assertEqual(self.found(self.play(args=['-SkipToDawn'])), [('c', 'SkipToDawn')])
        self.assertEqual(self.found(self.play(args=['-SkipToDawn']), instruction='QA starts with -SkipToDawn.'),
                         [('c', 'SkipToDawn')], 'an option only the reference adds is never used')
        cellar = self.play({'t': 2, 'map': '/Game/Maps/L_Cellar'})
        self.assertEqual(self.found(cellar), [('c', '/Game/Maps/L_Cellar')])
        self.assertEqual(self.found(cellar, instruction='QA plays the new cellar level, L_Cellar.'), [])

    def test_an_optional_check_is_not_looked_at(self):
        self.assertEqual(self.found(self.play({'t': 1, 'widget': 'StaminaBar', 'click': True}), required=False), [])


class Example(unittest.TestCase):
    """write-tasks section 9's full example task validates on a repo of its game: schema, the format's rules, the
    long-thread bar, a no-op that earns nothing, seeds on main on UE 5.7, a span over the floors and no name only the
    reference has. Only the game's task count (one task here) is short."""

    def test_the_skills_example_task_is_valid(self):
        skill = os.path.join(os.path.dirname(TOOLS), 'skills', 'write-tasks', 'SKILL.md')
        with open(skill, encoding='utf-8') as f:
            text = f.read()
        section = text.split('## 9. Example', 1)[1]
        task = json.loads(section.split('```json\n', 1)[1].split('\n```', 1)[0])
        parent = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, parent, True)
        repo, git, start, reference = make_game(parent, task['seed']['game'])
        task['seed'].update(commit=start, reference=reference)
        git('checkout', '-q', '--orphan', 'tasks')
        git('rm', '-rq', '--cached', '.')
        os.makedirs(os.path.join(repo, 'Tasks'))
        with open(os.path.join(repo, 'Tasks', task['name'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(task, f, indent=2)
        git('add', 'Tasks')
        git('commit', '-q', '-m', 'tasks')
        git('checkout', '-q', '-f', 'main')
        rep = vg.Report()
        vg.check_repo_tasks(rep, repo)
        problems = [(sev, m) for sev, _a, m in rep.items if sev != 'note']
        self.assertEqual(problems, [('error', 'tasks: 1 task(s): a game ships at least 5 (write-tasks section 1)'),
                                    ('error', 'tasks: 1 hard task(s): a game needs at least 4 hard tasks; the '
                                              'others may be medium (write-tasks section 1)')])
        self.assertEqual(vg.reference_only_names(repo, task), [])
        self.assertEqual(len(vg.outcome_probes(task)), 4)


if __name__ == '__main__':
    unittest.main()

"""Run: python -m unittest test_adaptive -v (no Gemini requests)."""
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
import main
from adaptive import Card, Decision, IntentRequest, Plan, _plans, apply_decision, arrange, by_rules, curated


class AdaptiveChecks(unittest.TestCase):
    def setUp(self):
        _plans.clear()
        self.database_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.database_dir.cleanup)
        database_patch = patch.object(main, 'DB_PATH', Path(self.database_dir.name) / 'test.sqlite3')
        database_patch.start()
        self.addCleanup(database_patch.stop)
        main.initialize_database()

    def test_goals_and_refinements(self):
        for text, mode in [("Prepare for tomorrow's client meeting", 'meeting'),
                           ('Investigate why active users dropped', 'usage'),
                           ('Review overdue project work', 'overdue')]:
            with self.subTest(mode=mode):
                result = by_rules(text)
                self.assertEqual(result['plan']['mode'], mode)
                current = Plan.model_validate(result['plan'])
                added = by_rules('Also show overdue tasks', current)
                ids = [c['id'] for c in added['plan']['components']]
                self.assertEqual(ids.count('overdue'), 1)
                self.assertEqual(added['plan']['mode'], mode)
                removed = by_rules('Remove next actions', Plan.model_validate(added['plan']))
                self.assertNotIn('actions', [c['id'] for c in removed['plan']['components']])

    def test_p1_evidence_preview_and_approval(self):
        with patch.object(main, 'client', None), TestClient(main.app) as api:
            proposed = api.post('/api/intent?preview=true', json={'pick': 'usage'}).json()
            self.assertIsNone(api.get('/api/data').json()['goal'])
            api.post('/api/layout/commit', json={'plan': proposed['plan'], 'intent': 'Investigate usage'})
            goal = api.get('/api/data').json()['goal']; step = goal['steps'][0]['id']
            record = dict(step_id=step, source='Analytics export A', metric='Active users', period='Week 1', value='100', observed_on='2020-01-01')
            first = api.post('/api/evidence', json=record)
            self.assertEqual(first.status_code, 201)
            second = api.post('/api/evidence', json={**record, 'source': 'Analytics export B', 'value': '80'}).json()
            current = api.get('/api/data').json()['goal']
            self.assertEqual(len(current['contradictions']), 1)
            self.assertTrue(current['evidence_records'][0]['stale'])
            self.assertEqual(current['steps'][0]['status'], 'Conflicting evidence')
            self.assertEqual(current['status'], 'Needs evidence review')
            api.post(f"/api/evidence/{second['id']}/withdraw")
            self.assertEqual(len(api.get('/api/data').json()['goal']['contradictions']), 0)
            self.assertEqual(api.post('/api/evidence', json={**record, 'observed_on': '2099-01-01'}).status_code, 422)
            draft = api.post(f"/api/goals/{goal['id']}/drafts", json={'kind': 'Email', 'destination': 'Example team'}).json()
            self.assertIn(f"[E{first.json()['id']}]", draft['content'])
            accepted = api.post(f"/api/drafts/{draft['id']}/decision", json={'decision': 'Approved', 'content': draft['content']})
            self.assertFalse(accepted.json()['external_execution'])
            self.assertEqual(api.post(f"/api/drafts/{draft['id']}/decision", json={'decision': 'Approved', 'content': draft['content']}).status_code, 409)
            self.assertTrue(api.get('/api/data').json()['goal']['decisions'])
            for value in ['2026-10-12', '2026-10-15']:
                api.post(f"/api/goals/{goal['id']}/constraints", json={'name': 'Deadline', 'value': value})
            self.assertEqual(len(api.get('/api/data').json()['goal']['goal_conflicts']), 1)

    def test_dtps_formula_and_override(self):
        from datetime import date
        import intelligence
        a = intelligence.score_task(dict(due_date='2026-10-12', impact=80, dependency_score=60, delay_risk=70), date(2026, 10, 11))
        b = intelligence.score_task(dict(due_date='2026-10-16', impact=80, dependency_score=20, delay_risk=35), date(2026, 10, 11))
        self.assertEqual(a['dtps'], 72.75)
        self.assertEqual(b['dtps'], 43.75)
        self.assertTrue(intelligence.score_task(dict(due_date=None, impact=100))['critical_override'])
        self.assertEqual(intelligence.score_task(dict(due_date=None))['factors']['dependency'], 0)
        with TestClient(main.app) as api:
            self.assertEqual(api.patch('/api/tasks/1', json={'impact': 80, 'dependency_score': 60, 'delay_risk': 70}).status_code, 200)
            self.assertEqual(api.patch('/api/tasks/1', json={'impact': 101, 'dependency_score': 60, 'delay_risk': 70}).status_code, 422)

    def test_persistent_goal_graph_and_radar(self):
        with patch.object(main, 'client', None), TestClient(main.app) as api:
            self.assertEqual(api.post('/api/intent', json={'pick': 'usage'}).status_code, 200)
            goal = api.get('/api/data').json()['goal']
            self.assertEqual(len(goal['steps']), 3)
            self.assertEqual(len(goal['gaps']), 6)
            self.assertEqual(goal['steps'][1]['status'], 'Blocked')
            first = goal['steps'][0]['id']
            self.assertEqual(api.patch(f'/api/goal-steps/{first}', json={'task_id': 99999}).status_code, 404)
            task = api.post('/api/tasks', json={'title': 'Check usage baseline', 'due_date': '2099-01-01', 'owner': 'Maya'}).json()
            api.patch(f"/api/tasks/{task['id']}?status=Completed")
            api.patch(f'/api/goal-steps/{first}', json={'task_id': task['id']})
            self.assertEqual(api.get('/api/data').json()['goal']['completed'], 0)
            api.patch(f'/api/goal-steps/{first}', json={'evidence': 'Analytics export: baseline 100, current 80; cause unknown.'})
            main.initialize_database()
            resumed = api.get('/api/data').json()['goal']
            self.assertEqual(resumed['id'], goal['id'])
            self.assertEqual(resumed['completed'], 1)
            self.assertEqual(len(resumed['gaps']), 4)
            self.assertEqual(resumed['steps'][1]['status'], 'Awaiting evidence')
            api.post('/api/intent', json={'pick': 'meeting'})
            api.post('/api/intent', json={'pick': 'usage'})
            self.assertEqual(api.get('/api/data').json()['goal']['completed'], 1)

    def test_ambiguity_and_unknown_goals_preserve_screen(self):
        for text in ['Client', 'Prepare a meeting and investigate a usage drop', 'Write a recipe']:
            self.assertEqual(by_rules(text)['status'], 'clarify')

    def test_model_validation_and_failure_fallback(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            Card(id='usage', span=5, reason='Invalid width')
        bad = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text='{"op":"replace","components":[{"id":"execute_code"}]}')))
        result = arrange(IntentRequest(text='Review overdue project work'), bad, 'test')
        self.assertEqual(result['plan']['mode'], 'overdue')
        self.assertTrue(result['fallback'])
        current = Plan.model_validate(curated('meeting')['plan'])
        out = Decision(op='patch', mode='meeting', title='', desc='', summary='Added overdue work',
                       components=[Card(id='overdue', span=8, reason='Requested by the user.')], remove=[], message='')
        result = apply_decision(out, current)
        self.assertEqual(result['plan']['title'], current.title)
        self.assertEqual(result['source'], 'gemini')
        self.assertIn('overdue', [c['id'] for c in result['plan']['components']])
        good = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text=out.model_dump_json())))
        self.assertEqual(arrange(IntentRequest(text='Also show overdue tasks', current=current), good, 'test')['source'], 'gemini')

    def test_repeated_goals_use_cached_validated_plans(self):
        out = Decision(op='replace', mode='overdue', title='Overdue work', desc='Focus on deadlines',
                       summary='Relevant overdue work', components=[Card(id='overdue', span=12, reason='Past-due tasks')],
                       remove=[], message='')
        calls = []
        def generate(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text=out.model_dump_json())
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        req = IntentRequest(text='Review overdue project work')
        first = arrange(req, client, 'test')
        second = arrange(req, client, 'test')
        self.assertEqual(first['plan'], second['plan'])
        self.assertTrue(second['cached'])
        self.assertEqual(len(calls), 1)

    def test_chat_response_context_and_provider_failure(self):
        calls = []
        def generate(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text='Review the overdue quarterly performance task first.')
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        with patch.object(main, 'client', client), TestClient(main.app) as api:
            self.assertEqual(api.post('/api/ai/ask', json={'question': ' '}).status_code, 400)
            reply = api.post('/api/ai/ask', json={'question': 'What should we prioritize?', 'mode': 'usage'})
            self.assertEqual(reply.status_code, 200)
            self.assertIn('quarterly performance', reply.json()['answer'])
            self.assertIn(main.get_tasks()[0]['title'], calls[0]['contents'])
            self.assertIn('Northstar Labs', calls[0]['contents'])
            self.assertIn("Today's date:", calls[0]['contents'])
            self.assertEqual(calls[0]['config'].http_options.timeout, 30000)
            self.assertEqual(calls[0]['config'].thinking_config.thinking_level, main.types.ThinkingLevel.MINIMAL)
            with patch.object(client.models, 'generate_content', side_effect=RuntimeError('private provider details')):
                failure = api.post('/api/ai/ask', json={'question': 'What next?'})
                self.assertEqual(failure.status_code, 502)
                self.assertNotIn('private provider details', failure.text)
            with patch.object(client.models, 'generate_content', return_value=SimpleNamespace(text='  ')):
                self.assertEqual(api.post('/api/ai/ask', json={'question': 'What next?'}).status_code, 502)

    def test_live_tasks_and_api_validation(self):
        original = main.get_tasks()
        with patch.object(main, 'client', None), TestClient(main.app) as api:
            self.assertEqual(api.post('/api/intent', json={'text': ' '}).status_code, 400)
            self.assertEqual(api.post('/api/tasks', json={'title': '  '}).status_code, 422)
            self.assertEqual(api.post('/api/tasks', json={'title': 'x', 'due_date': 'not-a-date'}).status_code, 422)
            self.assertEqual(api.post('/api/tasks', json={'title': 'x', 'priority': 'Urgent'}).status_code, 422)
            task = api.post('/api/tasks', json={'title': ' Test follow-up ', 'assignee': 'Maya',
                            'description': 'Confirm client follow-up', 'priority': 'High',
                            'team': 'Operations', 'due_date': '2020-01-01'})
            self.assertEqual(task.status_code, 201)
            self.assertEqual(task.json()['title'], 'Test follow-up')
            id = task.json()['id']
            before = api.get('/api/overview').json()
            self.assertEqual(api.patch(f'/api/tasks/{id}?status=Completed').status_code, 200)
            self.assertEqual(api.get('/api/overview').json()['completed_tasks'], before['completed_tasks'] + 1)
            self.assertEqual(api.patch(f'/api/tasks/{id}?status=Invalid').status_code, 400)
            self.assertEqual(api.patch('/api/tasks/99999?status=Pending').status_code, 404)
            self.assertEqual(api.get('/api/data').json()['tasks'][-1]['owner'], 'Maya')
            self.assertEqual(api.post('/api/intent', json={'text': 'Review overdue work'}).json()['plan']['mode'], 'overdue')
            self.assertEqual(api.post('/api/ai/ask', json={'question': 'What next?'}).status_code, 503)
            main.initialize_database()
            saved = api.get('/api/tasks').json()
            self.assertEqual(len(saved), len(original) + 1)
            self.assertEqual(saved[-1]['status'], 'Completed')
            self.assertEqual(saved[-1]['owner'], 'Maya')
            self.assertEqual(saved[-1]['assignee'], 'Maya')
            self.assertEqual(saved[-1]['priority'], 'High')
            self.assertEqual(saved[-1]['description'], 'Confirm client follow-up')
            self.assertEqual(saved[-1]['due_date'], '2020-01-01')


if __name__ == '__main__':
    unittest.main()

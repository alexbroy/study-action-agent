import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from executor import Executor, validate
from agent import run_plan
from llm import make_plan


def action(command, **args):
    return {'command': command, 'args': args}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ex = Executor(self.temp.name)

    def execute(self, command, **args):
        return self.ex.execute(action(command, **args), lambda _: True)

    def test_file_roundtrip(self):
        self.execute('write_file', path='notes/a.txt', content='hello')
        self.assertEqual(self.execute('read_file', path='notes/a.txt'), 'hello')
        self.assertEqual(self.execute('list_files'), ['notes/a.txt'])
        self.execute('delete_file', path='notes/a.txt')
        self.assertEqual(self.execute('list_files'), [])

    def test_cancel_delete_and_overwrite(self):
        self.execute('write_file', path='a.txt', content='original')
        for a in [action('delete_file', path='a.txt'), action('write_file', path='a.txt', content='new')]:
            self.ex.execute(a, lambda _: False)
        self.assertEqual(self.execute('read_file', path='a.txt'), 'original')

    def test_escape_and_links(self):
        for name in ['../outside', '/tmp/outside', '.']:
            with self.assertRaises(ValueError):
                self.ex.path(name)
        (self.ex.files / 'link').symlink_to(Path(self.temp.name))
        with self.assertRaises(ValueError):
            self.ex.path('link/outside')

    def test_invalid_plans(self):
        for a in [action('shell', command_line='rm -rf /'), action('delete_task', id=True),
                  action('add_task', title=1), action('list_files', extra='bad')]:
            with self.assertRaises(ValueError):
                validate({'message': '', 'actions': [a]})

    def test_whole_plan_validation(self):
        plan = {'message': '', 'actions': [action('write_file', path='safe.txt', content='x'),
                                           action('delete_file', path='../outside')]}
        with self.assertRaises(ValueError):
            run_plan(self.ex, plan, lambda _: 'yes')
        self.assertFalse((self.ex.files / 'safe.txt').exists())

    def test_declined_plan(self):
        run_plan(self.ex, {'message': '', 'actions': [action('add_task', title='x')]}, lambda _: 'no')
        self.assertEqual(self.execute('list_tasks'), [])

    def test_database_and_sql_injection(self):
        title = "'); DROP TABLE tasks; --"
        self.execute('add_task', title=title)
        self.assertEqual(self.execute('list_tasks')[0]['title'], title)
        self.execute('complete_task', id=1)
        self.assertTrue(self.execute('list_tasks')[0]['done'])
        self.execute('delete_task', id=1)
        self.assertEqual(self.execute('list_tasks'), [])
        with self.assertRaises(ValueError):
            self.execute('complete_task', id=99)

    def test_audit(self):
        self.execute('system_info')
        with self.assertRaises(FileNotFoundError):
            self.execute('read_file', path='missing.txt')
        rows = [json.loads(x) for x in (self.ex.state / 'audit.jsonl').read_text().splitlines()]
        self.assertEqual([r['event'] for r in rows], ['attempt', 'success', 'attempt', 'failed'])

    def response(self, text='{"message":"ok","actions":[]}', finish='STOP'):
        return io.BytesIO(json.dumps({'candidates': [{'finishReason': finish,
                          'content': {'parts': [{'text': text}]}}]}).encode())

    @patch('llm.time.sleep')
    @patch('llm.urllib.request.urlopen')
    def test_retry_rate_limit(self, fetch, sleep):
        fetch.side_effect = [urllib.error.HTTPError('url', 429, 'limited', {'Retry-After': '2'}, None), self.response()]
        self.assertEqual(make_plan('hi', 'test-key', 'test-model', lambda _: None)['actions'], [])
        self.assertEqual(fetch.call_count, 2)
        sleep.assert_called_once()

    @patch('llm.urllib.request.urlopen')
    def test_auth_error_no_retry(self, fetch):
        fetch.side_effect = urllib.error.HTTPError('url', 403, 'forbidden', {}, None)
        with self.assertRaises(ValueError):
            make_plan('hi', 'test-key', 'test-model')
        self.assertEqual(fetch.call_count, 1)

    @patch('llm.time.sleep')
    @patch('llm.urllib.request.urlopen')
    def test_retry_exhaustion(self, fetch, sleep):
        fetch.side_effect = urllib.error.URLError('offline')
        with self.assertRaises(ValueError):
            make_plan('hi', 'test-key', 'test-model', lambda _: None)
        self.assertEqual(fetch.call_count, 4)

    @patch('llm.urllib.request.urlopen')
    def test_bad_model_output(self, fetch):
        for response in [self.response('not json'), self.response(finish='MAX_TOKENS')]:
            fetch.return_value = response
            with self.assertRaises(ValueError):
                make_plan('hi', 'test-key', 'test-model')


if __name__ == '__main__':
    unittest.main()

"""Strict plan validation and allowlisted local actions."""
import json
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMAS = {
    'write_file': {'path': str, 'content': str},
    'read_file': {'path': str},
    'list_files': {},
    'delete_file': {'path': str},
    'add_task': {'title': str},
    'list_tasks': {},
    'complete_task': {'id': int},
    'delete_task': {'id': int},
    'system_info': {},
}


def validate(plan):
    if type(plan) is not dict or set(plan) != {'message', 'actions'}:
        raise ValueError('Plan must contain only message and actions.')
    if type(plan['message']) is not str or len(plan['message']) > 2000:
        raise ValueError('Invalid message.')
    if type(plan['actions']) is not list or len(plan['actions']) > 10:
        raise ValueError('A plan may contain at most 10 actions.')
    for action in plan['actions']:
        if type(action) is not dict or set(action) != {'command', 'args'}:
            raise ValueError('Each action needs only command and args.')
        name, args = action['command'], action['args']
        if type(name) is not str or name not in SCHEMAS:
            raise ValueError('Unknown command.')
        schema = SCHEMAS[name]
        if type(args) is not dict or set(args) != set(schema):
            raise ValueError('Unexpected or missing arguments.')
        for key, kind in schema.items():
            value = args[key]
            if type(value) is not kind:
                raise ValueError(f'Invalid type for {key}.')
            if kind is str and (len(value) > 20000 or ('\x00' in value)):
                raise ValueError('Text is too long or contains a null byte.')
            if key in ('path', 'title') and not value.strip():
                raise ValueError(f'{key} must not be empty.')
            if key == 'id' and not 0 < value < 2**63:
                raise ValueError('Task ID must be a positive SQLite integer.')
    return plan


class Executor:
    def __init__(self, base):
        self.base = Path(base).resolve()
        self.files = self.base / 'workspace'
        self.state = self.base / 'agent_data'
        self.files.mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        self.db = self.state / 'tasks.db'
        with sqlite3.connect(self.db) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS tasks '
                         '(id INTEGER PRIMARY KEY, title TEXT NOT NULL, done INTEGER DEFAULT 0)')

    def audit(self, event, **details):
        # Logging failure stops further execution; no secrets or file bodies are logged.
        entry = {'time': datetime.now(timezone.utc).isoformat(), 'event': event, **details}
        with (self.state / 'audit.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(entry, ensure_ascii=True) + '\n')
            stream.flush()

    def path(self, name):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Use a relative path inside workspace, without ..')
        candidate = self.files
        for part in relative.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError('Symbolic links are not allowed.')
        target = candidate.resolve()
        if not target.is_relative_to(self.files.resolve()) or target == self.files.resolve():
            raise ValueError('Path is outside workspace.')
        if target.exists() and (not target.is_file() or target.stat().st_nlink > 1):
            raise ValueError('Only regular, non-hard-linked files are supported.')
        return target

    def check(self, plan):
        validate(plan)
        for action in plan['actions']:
            if 'path' in action['args']:
                self.path(action['args']['path'])

    def execute(self, action, confirm):
        self.check({'message': '', 'actions': [action]})
        name, args = action['command'], action['args']
        target = self.path(args['path']) if 'path' in args else None
        identity = {key: value for key, value in args.items() if key in ('path', 'id')}
        self.audit('attempt', command=name, target=identity)
        destructive = name.startswith('delete_') or (name == 'write_file' and target.exists())
        if destructive and not confirm(f'Type CONFIRM to {name} {identity}: '):
            self.audit('cancelled', command=name, target=identity)
            return 'Cancelled; no change made.'
        try:
            result = self._run(name, args, target)
        except Exception as exc:
            self.audit('failed', command=name, target=identity, error_type=type(exc).__name__)
            raise
        self.audit('success', command=name, target=identity)
        return result

    def _run(self, name, args, target):
        if name == 'write_file':
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(args['content'], encoding='utf-8')
            return f"Saved {args['path']}"
        if name == 'read_file':
            if target.stat().st_size > 100000:
                raise ValueError('File exceeds the 100 KB reading limit.')
            return target.read_text(encoding='utf-8')
        if name == 'delete_file':
            target.unlink()
            return f"Deleted {args['path']}"
        if name == 'list_files':
            return sorted(str(p.relative_to(self.files)) for p in self.files.rglob('*')
                          if p.is_file() and not p.is_symlink())[:200]
        if name == 'system_info':
            return {'os': platform.system(), 'release': platform.release(),
                    'python': platform.python_version(), 'architecture': platform.machine()}
        with sqlite3.connect(self.db) as conn:
            if name == 'add_task':
                cursor = conn.execute('INSERT INTO tasks(title) VALUES (?)', (args['title'],))
                return f'Added task {cursor.lastrowid}'
            if name == 'list_tasks':
                return [{'id': row[0], 'title': row[1], 'done': bool(row[2])}
                        for row in conn.execute('SELECT id,title,done FROM tasks ORDER BY id LIMIT 200')]
            if name == 'complete_task':
                cursor = conn.execute('UPDATE tasks SET done=1 WHERE id=?', (args['id'],))
            else:
                cursor = conn.execute('DELETE FROM tasks WHERE id=?', (args['id'],))
            if cursor.rowcount == 0:
                raise ValueError('Task ID does not exist; list tasks first.')
            return f"Updated task {args['id']}"

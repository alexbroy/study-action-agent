"""Run: python3 agent.py; offline executor demonstration: python3 agent.py --demo."""
import argparse
import getpass
import json
import os
from pathlib import Path
from executor import Executor
from llm import make_plan


def show(value):
    # Escape terminal control characters in model output, filenames, and file contents.
    print(json.dumps(value, ensure_ascii=True, indent=2))


def run_plan(executor, plan, ask=input):
    executor.check(plan)  # Validate the entire plan before any operation.
    executor.audit('plan_validated', count=len(plan['actions']))
    show(plan)
    if not plan['actions']:
        return
    if ask('Execute this plan? Type yes: ').strip().lower() != 'yes':
        executor.audit('plan_cancelled')
        print('Plan cancelled.')
        return
    for index, action in enumerate(plan['actions'], 1):
        print(f"[{index}/{len(plan['actions'])}] Executing {action['command']}...")
        result = executor.execute(action, lambda prompt: ask(prompt).strip() == 'CONFIRM')
        show(result)


def main():
    parser = argparse.ArgumentParser(description='AI Action Agent')
    parser.add_argument('--demo', action='store_true', help='Fixed offline plan; no LLM call')
    args = parser.parse_args()
    executor = Executor(Path(__file__).resolve().parent)
    if args.demo:
        print('OFFLINE DEMO: fixed sample JSON, not an LLM response.')
        plan = {'message': 'Create a note, add a task, list tasks, and inspect the system.',
                'actions': [
                    {'command': 'write_file', 'args': {'path': 'demo.txt', 'content': 'Review MIPS loops.'}},
                    {'command': 'add_task', 'args': {'title': 'Practice MIPS loops'}},
                    {'command': 'list_tasks', 'args': {}},
                    {'command': 'system_info', 'args': {}}]}
        run_plan(executor, plan)
        return
    key = os.environ.get('GEMINI_API_KEY') or getpass.getpass('Gemini API key (hidden): ')
    model = os.environ.get('GEMINI_MODEL') or input('Model name [gemini-flash-lite-latest]: ').strip() or 'gemini-flash-lite-latest'
    print('AI Action Agent | type quit to exit')
    print('Examples: Create hello.txt saying Hello. | Add a task to study MIPS. | List tasks.')
    while True:
        request = input('\nRequest: ').strip()
        if request.lower() in ('quit', 'exit'):
            break
        if not request:
            continue
        try:
            if len(request) > 8000:
                raise ValueError('Request exceeds 8000 characters.')
            executor.audit('request_received')
            print('Planning with Gemini...')
            plan = make_plan(request, key, model)
            run_plan(executor, plan)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            executor.audit('request_failed', error_type=type(exc).__name__)
            show(f'Error: {exc}. Remaining actions stopped; prior successful actions remain.')


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nStopped.')
    except Exception as exc:
        show(f'Stopped: {type(exc).__name__}: {exc}')
        raise SystemExit(1)

"""Gemini REST integration, with bounded retries and JSON output."""
import json
import random
import re
import ssl
import time
import urllib.error
import urllib.request
from executor import SCHEMAS

SYSTEM = '''You are a local action planner. Return a JSON object with exactly
message (a short explanation) and actions (a list of command/args objects).
Only use the commands and exact argument types listed below. Do not invent
commands, task IDs, file contents, or facts. Paths are relative to workspace.
If a request is unsupported or ambiguous, explain in message and use [].
You cannot access the Internet, execute code, or use outputs of earlier actions
as arguments. For requests requiring discovery, list/read first and ask the user
to submit another request with the needed details. Never claim actions succeeded.
Example: {"message":"Create a note.","actions":[{"command":"write_file",
"args":{"path":"note.txt","content":"Study MIPS"}}]}
Available commands: ''' + json.dumps({k: {a: t.__name__ for a, t in v.items()}
                                     for k, v in SCHEMAS.items()})


def make_plan(request, key, model, status=print):
    if not key:
        raise ValueError('A Gemini API key is required for live mode.')
    if not re.fullmatch(r'[A-Za-z0-9._-]+', model):
        raise ValueError('Invalid model name.')
    body = {'systemInstruction': {'parts': [{'text': SYSTEM}]},
            'contents': [{'role': 'user', 'parts': [{'text': request}]}],
            'generationConfig': {'responseMimeType': 'application/json'}}
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = response.read(1000001)
            if len(raw) > 1000000:
                raise ValueError('API response exceeded size limit.')
            payload = json.loads(raw)
            candidates = payload.get('candidates', [])
            if not candidates or candidates[0].get('finishReason') != 'STOP':
                raise ValueError('Model response was blocked or incomplete; try rephrasing.')
            parts = candidates[0].get('content', {}).get('parts', [])
            text = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
            return json.loads(text)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                message = ('Gemini is temporarily unavailable. Try another model or retry later.'
                           if exc.code >= 500 else 'Check your API quota.' if exc.code == 429
                           else 'Check your API key, model name, and API permissions.')
                raise ValueError(f'Gemini HTTP {exc.code}. {message}') from None
            delay = 2**attempt + random.random()
            retry_after = exc.headers.get('Retry-After', '')
            if retry_after.isdigit():
                if int(retry_after) > 60:
                    raise ValueError(f'Rate limited. Wait {retry_after} seconds before retrying.') from None
                delay = max(delay, int(retry_after))
        except (urllib.error.URLError, TimeoutError) as exc:
            if isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError):
                raise ValueError("Python certificate verification failed. On macOS run Install Certificates.command from your Python Applications folder.") from None
            if attempt == 3:
                raise ValueError('Unable to reach Gemini after four attempts.') from None
            delay = 2**attempt + random.random()
        status(f'API temporarily unavailable; retry {attempt + 1}/3 in {delay:.1f}s.')
        time.sleep(delay)

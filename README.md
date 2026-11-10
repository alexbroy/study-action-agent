# Study Action Agent

Students often receive useful AI advice but still have to copy it into notes and manage tasks manually. This agent turns natural-language requests into real, reviewable note and task operations.

## Interfaces

| Version | Technology | Actions |
|---|---|---|
| Web (`dist/`) | HTML/CSS/JavaScript + IndexedDB | Create/read/delete browser notes, download .txt files, add/list/complete/delete task records |
| Terminal (`python-cli/`) | Python 3.10+ + SQLite | Create/read/list/delete local files, manage task records, inspect system information |

The web companion is JavaScript, not hosted Python. Browser notes live in site storage until downloaded; they cannot access arbitrary computer files. Both interfaces use Gemini JSON plans and independent action validation.

## Run

Web: publish with the GitHub Pages steps in SUBMISSION.md, then open the deployed app URL, click **API settings**, and enter your own Gemini API key. Default model: `gemini-flash-lite-latest`. Each tester, including the instructor, needs a key for live mode. The key stays in tab memory, is sent only to Google, and clears on refresh. API availability/quota/billing depend on the tester's account. Get a key at https://aistudio.google.com/apikey.

Try: “Create a note called study.txt with three short tips for learning MIPS, and add a task to practice loops.” Review and approve the plan, then inspect/download the note and view the task.

**Try a fixed sample** uses a preset JSON plan and executes real local actions without an API key. It is clearly labeled and is not a live LLM demonstration.

Local web server: `python3 -m http.server 8000 --directory dist`, then visit http://localhost:8000. Do not open index.html directly; JavaScript modules require a server.

Python: `cd python-cli` then `python3 agent.py`. Enter a key and accept Flash-Lite. No pip dependencies. Optional environment variables: GEMINI_API_KEY and GEMINI_MODEL. `python3 agent.py --demo` runs a fixed offline plan. On python.org macOS installations, use the bundled Install Certificates.command if HTTPS verification fails. Extract into a permanent folder before running.

## Prompt engineering

1. **Role prompting:** defines a study administration action planner.
2. **Structured output:** JSON contract with exactly message/actions and allowed command arguments; Gemini JSON response mode.
3. **Few-shot examples (web):** note/task creation and deletion examples, plus a negative example for forbidden shell execution.
4. **Grounding (web):** existing note names and task IDs/titles/statuses accompany requests. Context is explicitly untrusted data, not instructions.
5. **Uncertainty and scope:** ambiguous or unsupported requests produce an explanation with no actions. No invented IDs or false success claims.
6. **Separate execution:** code validates the entire plan independently; prompt instructions alone are not security controls.

Full web prompt and validator: `dist/core.js`. Python prompt: `python-cli/llm.py` (simpler one-shot prompt without automatic workspace grounding).

## Architecture and requirements

Request + workspace context → Gemini JSON → validate entire plan → preview → human approval → allowlisted executor → visible results + audit.

| Requirement | Implementation |
|---|---|
| LLM integration | Gemini REST API, configurable model, hidden key entry |
| Errors/rate limits | 45-second timeout, max four attempts, backoff, Retry-After handling |
| Action interpreter | Exact object keys, argument types, command allowlist, size/path restrictions |
| Multiple domains | Text file/notes and persistent task database; Python also reads system information |
| UI/status | Responsive web interface plus terminal interface; plan preview and action outcomes |
| Safety/audit | Extra delete/overwrite confirmation; timestamped attempt/success/failure/cancellation log |

Web files: core.js handles prompts/validation/API; app.js handles IndexedDB/execution/UI; index.html and style.css provide the interface. Python modules: agent.py (orchestration), llm.py (API), executor.py (actions/audit).

## Limits and privacy

- No eval, arbitrary shell execution, model-written SQL, email/calendar integration, or autonomous background work. Python SQL is parameterized.
- Browser data is per profile/origin, not shared or synchronized; clearing site data removes it. The audit is ordinary local data, not tamper-proof. The display shows the latest 30 entries; export includes all stored entries.
- Live web requests send typed text, filenames and task records to Google. Existing note bodies are not sent automatically. Avoid sensitive information. To summarize a note, include its content in a new request.
- The web app stores each action's state mutation and success log together in one transaction. Plans are sequential, not atomic: earlier successes remain after later failure. Cancelling a destructive web action stops remaining actions. Python cancellation skips only that action.
- Limits: 10 actions/plan, 8,000-character requests, 20,000-character text arguments, 200 web notes/tasks. Browser storage quota failures stop actions. Web filenames are simple .txt names with no folders. Python additionally limits file reads to 100 KB.
- Web keys are not stored in source/database/logs. They remain accessible to the person operating their own browser; this is bring-your-own-key design.
- Python path checks reject traversal, symlinks and hard-linked targets, but it is a single-user prototype, not an OS sandbox against concurrent filesystem changes.

## Tests

`node --test tests/*.test.js`: 12 web tests for schemas, path restrictions, bounded retries, rate limits, authentication failures and malformed responses. APIs are mocked.

`python3 -m unittest discover -s python-cli -v`: 12 Python tests for local actions, confirmations, audit, parameterized SQL, paths and mocked API errors.

The original Python app worked with the user's Flash-Lite key. A live deployed web request still requires user verification. Offline tests do not prove live API availability. See the delivery message for browser and deployment verification results.

## Submission

See DEMO.md and SUBMISSION.md. Never upload keys, private workspace files, databases or logs to GitHub.

References: https://ai.google.dev/api/generate-content and instructor video https://youtu.be/wcS2QUXKeP4.

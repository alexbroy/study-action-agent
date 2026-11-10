# 1–2 minute live demo

Before recording, enter your key privately in API settings and verify one LIVE request with gemini-flash-lite-latest. Use a fresh filename, keep the browser readable, and close unrelated tabs. Never show your API key. The fixed sample is not a live LLM call.

| Time | Show | Narration |
|---|---|---|
| 0:00–0:15 | App overview | “Students get study advice from AI but still have to copy it into files and create tasks manually. My agent turns a request into saved notes and task records.” |
| 0:15–0:30 | Enter creation request below; Generate action plan | “Gemini receives my request and returns a structured JSON plan. My code validates each command and its arguments before execution.” |
| 0:30–0:50 | Proposed actions; expand JSON | “I use role prompting, a strict JSON format and few-shot examples. Existing task IDs ground the plan. Only supported actions can execute.” |
| 0:50–1:10 | Approve; read/download note; show new task | “After approval, the executor creates a note and inserts a task into the browser database. These results persist after refreshing, and I can download the note.” |
| 1:10–1:35 | Request deletion; approve plan; CANCEL extra confirmation | “Destructive actions need an additional confirmation. I'll cancel this deletion. The note remains, and the audit records the cancellation.” |
| 1:35–1:50 | Audit history and Export JSON | “Each action has a status and an audit entry. The app retries temporary API failures and displays errors. The original Python interface also supports local files and SQLite.” |
| 1:50–2:00 | Full interface | “This connects language to practical actions while keeping the user in control.” |

Creation request:

```text
Create a note called demo-study.txt with three short tips for learning MIPS, and add a task to practice MIPS loops.
```

Deletion request:

```text
Delete the note demo-study.txt.
```

Allow time for API latency; shorten narration if needed. If you edit out waiting time, disclose the edit. If Gemini is unavailable, try another available model or record later. A clearly labeled fixed sample can show the executor but does not demonstrate live LLM integration.

Record your screen and voice, then upload to YouTube (Unlisted if permitted). Test the link in a signed-out/private window. You still need to record and upload the actual video; this script alone does not satisfy the submission.

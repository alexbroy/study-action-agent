# Rubric and submission checklist

| Criterion | Weight | Evidence |
|---|---:|---|
| Problem identification | 10% | Student note/task administration problem in app, README and demo opening |
| Design and implementation | 30% | Gemini API, validated JSON, file/database actions, retry handling, confirmation and audit |
| Prompt engineering | 20% | Role, structured JSON, few-shot examples, grounding, scope/clarification instructions in core.js |
| UI/UX | 10% | Responsive request/review/results layout, suggested requests, clear statuses and dialogs |
| Presentation and live demo | 30% | Timed script in DEMO.md; actual recording still required |

This covers the rubric's topics, not a guaranteed grade.

Required before submission:

- [ ] Publish code to your GitHub account and copy the actual repository URL. Hosting's native source repository is not automatically a GitHub submission URL.
- [ ] Ensure the deployed app URL can be opened by the instructor. Owner-private sharing must be changed before submitting to others. Test from another account or signed-out browser.
- [ ] Test a real Gemini request in the deployed web app; Python success or fixed sample success alone is insufficient.
- [ ] Record a 1–2 minute video, upload it and test the actual video URL.
- [ ] Tell the instructor that live testing requires their own Gemini API key. No-key sample mode is explicitly preset, not an LLM call.

## GitHub upload

1. Sign in at https://github.com/new and create `study-action-agent`. Choose visibility allowed by your course; the instructor must have access.
2. Use Add file → Upload files (or “uploading an existing file” on an empty repository).
3. Upload `index.html`, `dist/`, `python-cli/`, `tests/`, `package.json`, README.md, DEMO.md, SUBMISSION.md, .nojekyll and .gitignore, preserving folder structure.
4. Exclude `.git/`, `.openai/`, keys, workspace/, agent_data/, and __pycache__/.
5. Commit the upload and copy the repository URL.

## Submission note

Study Action Agent turns student requests into persistent notes and tasks. The web version uses Gemini, validated JSON commands, IndexedDB, human approval and audit logging. A Python terminal version with local files and SQLite is included. For a live test, enter your Gemini key in API settings; the default model is gemini-flash-lite-latest. The fixed sample needs no key but does not call an LLM.

Add your real GitHub, deployed app and video URLs to this note. Do not claim any missing link is ready.

## Publish the deployed URL with GitHub Pages

Automatic hosting from the development session was blocked because the hosting Git server could not be resolved. No working deployment URL was verified. Use this route after uploading the repository:

1. Make sure `index.html` is at the repository root, alongside `dist/` and `python-cli/`, not inside an extra ZIP-named folder.
2. In the GitHub repository, open **Settings → Pages**.
3. Select **Deploy from a branch**, choose **main** and **/(root)**, then **Save**.
4. Wait for GitHub to display the published site URL. Copy that actual URL; it is separate from the repository URL.
5. Open the site in another browser/account. Add a Gemini key and verify a real request, approval, download and task creation. Check deletion cancellation and audit export.
6. If Pages settings are unavailable, check repository visibility and your GitHub account's Pages eligibility.

The root index redirects to the actual app in dist/. No server backend or build step is required.

Official instructions: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site

# PB-1 verifier (Harbor `tests/test.sh`)

Layout follows
`evals/docs/workstreams/assistant-ui-agent-evals/modules/m0-discovery/m0.2-pb-1-harbor-task/tests-layout.md`.

| File | Job |
| --- | --- |
| `test.sh` | Workflow + judge (agent jobs), pytest code, install/build/start, AR-04 + browser, `reward.txt` |
| `checks.py` | Line-item catalog + gate skip |
| `report.py` | Gates + JUnit → `checks.json` + weighted `reward.txt` (`AR`/`BR` weight 2; else 1) |
| `lib/workspace.py` | Find `package.json`, grep packages/source (skips `.agents`) |
| `lib/transcript.py` | Cursor ATIF → supabase-named events → compact transcript. Codex Harbor `exec` unwraps `tools.exec_command({cmd})` the same way supabase reads `item.command`; TTY sessions copy `write_stdin` `exit_code` onto the opening command. Claude Harbor `Bash` reads `result.extra` `is_error` (no integer `exitCode`). |
| `test_workflow.py` | WF-D-* / WF-S-* (skip on gold; WF-D-* uses MCP or web docs per `PB1_MCP`) |
| `test_code.py` | CQ-G-* / CQ-P-* |
| `test_apprun.py` | AR-04 POST `/api/chat` |
| `test_browser.py` | BR-01–BR-06. BR-06 waits for the run to finish (Stop → Send visible), reloads, and checks the user text is still in the thread. Does not require a `localStorage` key. |
| `judge/run.py` | Luna calls for WF-E-01/02 and WF-T-01/02. Skips WF-E-01 if no create command ran; skips WF-E-02 if no `tsc` / `next build` / package build ran. |
| `fixtures/offline.py` | Offline parser / helper checks; **not scored**, not run in Harbor |

AR-01–AR-03 are recorded from `test.sh` gates. `tsc --noEmit` is diagnostic
only (`/logs/verifier/tsc.log`).

Gold skips groups 1–4. Agent jobs parse `/logs/agent/trajectory.json`.

MCP-off: set `PB1_MCP=off` on both job `environment.env` and `verifier.env`
(see `jobs/pb-1-cursor-cli-mcp-off.yaml`). WF-D-01/02 stay scored: web search
or fetch of `llms.txt` / `assistant-ui.com/docs` (Codex `tools.web__run`
search then `open`). Search hits without an open/fetch/curl fail WF-D-02.
Harbor still lists the MCP server; the stdio command no-ops so the agent has
no assistant-ui tools. Default is `on` (MCP discovery).

Judge API key: Harbor `[verifier.env]` injects `OPENAI_API_KEY` from the host
`--env-file` (`evals/assistant-ui/app-evals/.env`). `test.sh` pip-installs
`openai` and `pydantic` in the **same sandbox** — no image change. Pattern:
`evals/reference/harbor/examples/tasks/llm-judge-example/`.

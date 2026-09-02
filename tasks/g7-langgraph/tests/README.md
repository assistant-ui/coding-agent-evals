# G7 verifier (Harbor `tests/test.sh`)

Gold: `assistant-ui create --example with-langgraph`, then replace the
LangGraph Cloud proxy with a Next `/api/[..._path]` that invokes the
in-process graph and **replays** command/SSE events (Harbor has no
Cloud / no `langgraphjs` process). The UI still uses `useStreamRuntime`
+ `purchase_stock` Confirm
(stockbroker tool UI). Playwright types `Buy 10 shares of TSLA.`, expands
the tool group, clicks Confirm, and expects Transaction Confirmed.

Layout follows
`evals/docs/workstreams/assistant-ui-agent-evals/modules/m0-discovery/m0.2-pb-1-harbor-task/tests-layout.md`.

| File | Job |
| --- | --- |
| `test.sh` | Workflow + judge (agent jobs), pytest code, install/build/start, AR-04 + browser, `reward.txt` |
| `checks.py` | Line-item catalog + gate skip |
| `report.py` | Gates + JUnit → `checks.json` + weighted `reward.txt` (`AR`/`BR` weight 2; else 1) |
| `lib/workspace.py` | Find `package.json`, grep packages/source (skips `.agents`) |
| `lib/transcript.py` | Cursor ATIF → supabase-named events → compact transcript. Codex Harbor `exec` unwraps `tools.exec_command({cmd})` the same way supabase reads `item.command`; TTY sessions copy `write_stdin` `exit_code` onto the opening command. Claude Harbor `Bash` reads `result.extra` `is_error` (no integer `exitCode`). |
| `test_workflow.py` | WF-D-* / WF-S-* (skip on gold; WF-S-02 allows `-e with-langgraph` / `-t langchain`) |
| `test_code.py` | CQ-G-* / CQ-P-*. CQ-G-03/04 are LangGraph packages. No CQ-P-06 (no Cloud) |
| `test_apprun.py` | AR-04 POST `/api/threads` |
| `test_browser.py` | BR-01–BR-05. Type buy prompt; Confirm Transaction; Transaction Confirmed. No reload |
| `judge/run.py` | Luna calls for WF-E-01/02 and WF-T-01/02. Skips WF-E-01 if no create command ran; skips WF-E-02 if no `tsc` / `next build` / package build ran. |
| `fixtures/offline.py` | Offline parser / helper checks; **not scored**, not run in Harbor |

AR-01–AR-03 are recorded from `test.sh` gates. `tsc --noEmit` is diagnostic
only (`/logs/verifier/tsc.log`).

Gold skips groups 1–4. Agent jobs parse `/logs/agent/trajectory.json`.

MCP-off: set `PB1_MCP=off` on both job `environment.env` and `verifier.env`.
Default is `on`.

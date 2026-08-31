# G4 verifier (Harbor `tests/test.sh`)

Gold: `assistant-ui create --template mcp`, then a real local Streamable
HTTP echo MCP (`npm run start:mcp`), user-managed MCP UI
(`McpConfigDialog` / `defineConnector`), and a chat stub that invokes
the connected `echo` frontend tool. `--example with-mcp` is **not** on
the published CLI. Composer `fill()` does not enable Send — tests type
so input events fire.

Layout follows
`evals/docs/workstreams/assistant-ui-agent-evals/modules/m0-discovery/m0.2-pb-1-harbor-task/tests-layout.md`.

| File | Job |
| --- | --- |
| `test.sh` | Workflow + judge (agent jobs), pytest code, install/build, `start:mcp`, Next start, AR-04 + browser, `reward.txt` |
| `checks.py` | Line-item catalog + gate skip |
| `report.py` | Gates + JUnit → `checks.json` + float `reward.txt` (`n_passed / n_applicable`; skipped out of the denominator; error omits reward) |
| `lib/workspace.py` | Find `package.json`, grep packages/source (skips `.agents`) |
| `lib/transcript.py` | Cursor ATIF → supabase-named events → compact transcript. Codex Harbor `exec` unwraps `tools.exec_command({cmd})` the same way supabase reads `item.command`; TTY sessions copy `write_stdin` `exit_code` onto the opening command. Claude Harbor `Bash` reads `result.extra` `is_error` (no integer `exitCode`). |
| `test_workflow.py` | WF-D-* / WF-S-* (skip on gold; WF-S-02 allows `--template mcp`) |
| `test_code.py` | CQ-G-* / CQ-P-* (`@assistant-ui/react-mcp`, `McpManagerResource` / connector UI). No CQ-P-06 (no Cloud) |
| `test_apprun.py` | AR-04 POST `/api/chat` |
| `test_browser.py` | BR-01–BR-07: composer, type+send, user message, MCP servers dialog, Connected, echo tool in the thread |
| `judge/run.py` | Luna calls for WF-E-01/02 and WF-T-01/02. Skips WF-E-01 if no create command ran; skips WF-E-02 if no `tsc` / `next build` / package build ran. |
| `fixtures/offline.py` | Offline parser / helper checks; **not scored**, not run in Harbor |

AR-01–AR-03 are recorded from `test.sh` gates. `tsc --noEmit` is diagnostic
only (`/logs/verifier/tsc.log`).

Gold skips groups 1–4. Agent jobs parse `/logs/agent/trajectory.json`.

MCP-off: set `PB1_MCP=off` on both job `environment.env` and `verifier.env`.
Default is `on`.

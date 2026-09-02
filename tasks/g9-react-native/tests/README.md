# G9 verifier (Harbor `tests/test.sh`)

Layout follows
`evals/docs/workstreams/assistant-ui-agent-evals/modules/m0-discovery/m0.2-pb-1-harbor-task/tests-layout.md`.

| File | Job |
| --- | --- |
| `test.sh` | Workflow + judge (agent jobs), pytest code, install, Expo export, `expo start --web`, AR-04 + browser, `reward.txt` |
| `checks.py` | Line-item catalog + gate skip |
| `report.py` | Gates + JUnit → `checks.json` + weighted `reward.txt` (`AR`/`BR` weight 2; else 1) |
| `lib/workspace.py` | Find app; `CHAT_USER_TEXT` weather prompt |
| `test_workflow.py` | WF-D-* / WF-S-* (skip on gold). WF-S-02 lists `with-expo` |
| `test_code.py` | CQ-G-* (`@assistant-ui/react-native`, expo, not Next) / CQ-P-* toolkit + weather |
| `test_apprun.py` | AR-04 GET `/` is Expo web, not Next |
| `test_browser.py` | BR-01–05 composer, send weather prompt, `°F` card |
| `judge/run.py` | Luna WF-E / WF-T |

AR-01–AR-03 from `test.sh` gates. Start is **`expo start --web --host localhost`**
for gold and agents (unset Blaxel `PORT`/`HOST`). Do not require
`server/serve-web.mjs`. Gold skips WF-*. Native device is out of scope.

MCP-off: `PB1_MCP=off` on both job `environment.env` and `verifier.env`.

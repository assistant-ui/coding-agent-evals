# G10 verifier (Harbor `tests/test.sh`)

Layout follows
`evals/docs/workstreams/assistant-ui-agent-evals/modules/m0-discovery/m0.2-pb-1-harbor-task/tests-layout.md`.

| File | Job |
| --- | --- |
| `test.sh` | Workflow + judge (agent jobs), pytest code, install/build/start, AR-04 + browser, `reward.txt` |
| `checks.py` | Line-item catalog + gate skip |
| `report.py` | Gates + JUnit → `checks.json` + float `reward.txt` |
| `lib/workspace.py` | Find app; `THREAD_A_TEXT` / `THREAD_B_TEXT` / `MODEL_PROBE_TEXT` |
| `test_workflow.py` | WF-D-* / WF-S-* (skip on gold). WF-S-02 accepts `--example` or `-t default` |
| `test_code.py` | CQ-G-* / CQ-P-* (sidebar + ModelSelector/`modelName`; no Cloud CQ-P-06) |
| `test_apprun.py` | AR-04 POST `/api/chat` |
| `test_browser.py` | BR-01 composer + sidebar + model picker (any welcome copy); BR-03–06 thread A / new / B / switch A; BR-07 picker change (gold stub echo still passes) |
| `judge/run.py` | Luna WF-E / WF-T |
| `fixtures/offline.py` | Offline helpers; not scored |

AR-01–AR-03 from `test.sh` gates. Gold skips WF-*. Reload persistence is **not** scored (G1).

MCP-off: `PB1_MCP=off` on both job `environment.env` and `verifier.env`.

# G11 verifier (Harbor `tests/test.sh`)

| File | Job |
| --- | --- |
| `checks.py` | Claude shell + artifacts catalog |
| `test_code.py` | CQ-G dual ai-sdk; CQ-P sidebar + interactable/iframe + surface |
| `test_browser.py` | BR-01 composer + sidebar (canvas not required on load); BR-03–06 card then canvas iframe (click workbench if needed); BR-07 thread switch |
| `test_workflow.py` | WF-S-02 accepts `-t default` and listed examples (incl. `with-artifacts`) |
| `lib/workspace.py` | `CHAT_USER_TEXT` / `CHAT_FOLLOW_UP` / thread prompts |

Gold skips WF-*. Model selector is **not** scored (G10). Reload persistence is **not** scored (G1).

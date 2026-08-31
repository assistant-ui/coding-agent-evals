# WF-E-01 — assistant-ui create errors

**Check:** Did the agent avoid assistant-ui CLI create errors?

- **Pass:** No `assistant-ui create` or `create-assistant-ui` command failed.
- **Fail:** Any such command failed, including because of an unknown flag.
  A later successful retry does not erase the failure.
- **Insufficient evidence:** The transcript shows a relevant command but does
  not show whether it succeeded.

The verifier skips this check (does not call the judge) when no
`assistant-ui create` / `create-assistant-ui` command was attempted.
`--help` / `-h` only is not an attempt. A failed create is still graded.

Ignore unrelated command failures.

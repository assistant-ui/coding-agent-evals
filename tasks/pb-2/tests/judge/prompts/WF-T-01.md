# WF-T-01 — started the app

**Check:** Did the agent start the application?

- **Pass:** A start command ran and the transcript shows readiness, such as a
  ready log or a successful connection to the app.
- **Fail:** No start command ran, the agent only told the user to start it, or
  the command has no readiness evidence.
- **Insufficient evidence:** A start command ran but its result is unavailable
  or ambiguous.

Judge the agent run, not the verifier run.

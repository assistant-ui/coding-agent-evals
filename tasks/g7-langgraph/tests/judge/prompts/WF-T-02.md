# WF-T-02 — tested the running app

**Check:** Did the agent test the running application?

- **Pass:** After starting the app, the agent interacted with it through
  localhost HTTP, curl, a browser, Playwright, or `POST /api/chat`.
- **Fail:** The agent did not start the app or did not interact with the
  running app.
- **Insufficient evidence:** A possible runtime interaction is present but its
  target or outcome cannot be determined.

File reads, searches, and test-runner commands alone do not count.

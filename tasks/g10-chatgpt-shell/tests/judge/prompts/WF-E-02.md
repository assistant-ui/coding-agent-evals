# WF-E-02 — TypeScript or build errors

**Check:** Did the agent avoid TypeScript and build errors?

- **Pass:** No `tsc`, `next build`, or package build command failed.
- **Fail:** Any such command failed, including when a wrapped command's output
  clearly shows a typecheck or build failure. A later successful retry does
  not erase the failure.
- **Insufficient evidence:** A relevant command ran but its outcome cannot be
  determined.

The verifier skips this check (does not call the judge) when the agent
never ran `tsc`, `next build`, or a package build (`npm`/`pnpm`/`yarn`/`bun`
`run build`). A failed build is still graded.

Judge only commands run by the agent.

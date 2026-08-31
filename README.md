# xulux evals — assistant-ui coding agents

xulux evals for whether a coding agent can build a working
[assistant-ui](https://www.assistant-ui.com) app.

This README is the runbook. There is no separate doc. Use the scripts
here; do not hand-write job YAML.

Pinned runner: **Harbor 0.20** (required). Default sandbox is **Blaxel**
(recommended). Docker works via `--env docker`. After a run, open
`report/index.html` for the comparison grid.

## What you are scoring

Each case is a product prompt (build this assistant-ui app). Graders
check source, build, runtime, browser behavior, and — for coding agents
— whether they used docs / the create CLI.

| Command | What it measures | When to use it |
| --- | --- | --- |
| `check-env-codeverifiers` | The **graders** still work. Runs the gold overlay (no coding agent). | After clone, after a grader change, before a big agent run. |
| `full-eval` | **Agents.** G1–G11 × Cursor CLI / Claude Code / Codex × MCP on and off. | The product matrix. Expensive. |
| `custom` | The same axes, but you pick cases / agents / MCP. | One case, one harness, a retry. |

`check-env-codeverifiers` is not an agent score. Gold overlays call
`npx assistant-ui@latest create`. If that template has moved since a
case was locked, this command can score below 1.0 even when the runner
is fine — that is a gold refresh, not a script bug.

## Prerequisites

Linux, macOS, or WSL. Scripts are bash.

1. **Node + npm** — `setup` packs the published MCP docs server.
2. **Harbor 0.20** — do not float to latest:

   ```bash
   uv tool install 'harbor[blaxel]==0.20'
   # or: pip install 'harbor[blaxel]==0.20'
   harbor --version   # must print 0.20.x
   ```

3. **Blaxel** (default sandbox) — `bl` CLI and a logged-in workspace,
   or `BL_WORKSPACE` + `BL_API_KEY` in `.env`.
4. **Docker** — only if you will pass `--env docker`.
5. Agent API keys in `.env` (see below).

## Install this repo

```bash
git clone https://github.com/assistant-ui/coding-agent-evals.git
cd coding-agent-evals
cp .env.example .env
# edit .env — never commit it
./scripts/setup.sh
```

`setup` checks Harbor 0.20, copies `.env.example` if `.env` is missing,
packs `@assistant-ui/mcp-docs-server` from npm into each task image, and
probes Blaxel + Docker.

The MCP tarball is part of the image. Re-run `setup` when the published
MCP package changes. A new tarball forces a new image build (slow the
first time).

### `.env`

| Variable | Needed for |
| --- | --- |
| `OPENAI_API_KEY` | Codex, and the LLM judge inside the grader |
| `CURSOR_API_KEY` | Cursor CLI |
| `ANTHROPIC_API_KEY` | Claude Code |
| `OPENROUTER_API_KEY` | Optional, if your Codex/judge path uses OpenRouter |
| `BL_WORKSPACE`, `BL_API_KEY` | Blaxel, unless you already ran `bl login` |
| `JUDGE_MODEL` | Optional. Default in tasks is `gpt-5.6-luna` |

## How to run

Always from the repo root, after `setup`.

### 1. Check the graders (do this first)

```bash
# All cases. Recommended after clone.
./scripts/run.sh check-env-codeverifiers

# One case (faster smoke).
./scripts/run.sh check-env-codeverifiers --cases g1
```

Expect **1.0** on a healthy lock. If a case is below 1.0, stop and
inspect that trial under `jobs/` before running agents.

### 2. Full agent matrix

```bash
./scripts/run.sh full-eval
```

That is **11 cases × 3 agents × MCP on/off = 66 trials**, up to **10**
at a time, on Blaxel. Budget hours and API spend. MCP on and MCP off
are two sequential jobs (sandbox env is per job).

### 3. A subset

`custom` requires `--cases` and `--agents`.

```bash
# One harness, MCP on, two cases.
./scripts/run.sh custom --cases g1,g2 --agents cursor-cli --mcp on

# Three harnesses, one case, both MCP surfaces.
./scripts/run.sh custom --cases g1 --agents cursor-cli,claude-code,codex --mcp both

# Local Docker instead of Blaxel.
./scripts/run.sh custom --cases g1 --agents cursor-cli --mcp on --env docker
```

### Flags (all commands)

| Flag | Default | Meaning |
| --- | --- | --- |
| `--cases g1,g2` | all G1–G11 | Case ids from the table below |
| `--agents cursor-cli,claude-code,codex` | all three | Ignored for `check-env-codeverifiers` |
| `--mcp on\|off\|both` | `on` for `custom`; both for `full-eval` | Product docs tools vs web-docs-only |
| `--env blaxel\|docker\|…` | `blaxel` | Sandbox. Same name as Harbor’s `--env`. |
| `--concurrent N` | `10` | Max trials in flight |
| `--environment-kwarg KEY=VALUE` | Blaxel `region=us-pdx-1` | Extra sandbox kwargs; repeatable |
| `--print-config` | | Print generated YAML and exit |
| `--dry-run` | | Write YAML, do not start a run |
| `--no-ingest` | | Skip updating `report/` when the job ends |

`--env` is **not** `.env`. Secrets stay in `.env`; `--env` picks the
sandbox (Blaxel, Docker, or any other type the pinned runner accepts).
Other backends (E2B, Modal, …) are pass-through: we do not first-class
test them. Extra Harbor extras must already be installed.

## Cases

| Id | What the agent is asked to build |
| --- | --- |
| `g1` | Basic AI SDK chat with persistence |
| `g2` | HTML canvas beside the chat |
| `g3` | Assistant fills First name + Email on a signup page |
| `g4` | MCP Apps in chat; add/remove MCP servers in the UI |
| `g5` | Chat backed by Eve |
| `g6` | Mastra agent on the backend |
| `g7` | LangGraph stock buy with a confirm step |
| `g8` | Vite, not Next.js |
| `g9` | React Native / Expo weather card (generative UI) |
| `g10` | ChatGPT-like shell (sidebar + model selector) |
| `g11` | Claude-like shell (sidebar + artifacts) |

Pinned models: Cursor CLI `composer-2.5`, Claude Code `claude-sonnet-5`,
Codex `gpt-5.6-luna`. MCP **on** = assistant-ui docs MCP. MCP **off** =
web docs only (`PB1_MCP=off` on both the sandbox and the grader).

## After a run

1. Open **`report/index.html`** in a browser (`file://` is fine). Cells
   are score / agent time / API cost. Em dash means not run. Gold
   oracles are a verifier badge on the case, not a harness row.
2. Raw trials land in **`jobs/`** (gitignored). Keep that folder; do
   not commit dumps.
3. Ingest merges the new job into `report/` so the next clone still
   sees the last committed grid plus what you just ran.

The first image build on Blaxel can take a long time (Playwright +
Chromium). Later runs reuse the image unless `setup` wrote a new MCP
tarball. If sandbox **create** hits HTTP 504, wait several minutes
before retrying (a timed-out create can leave a sandbox with the same
name).

## Layout

```text
tasks/     G1–G11 cases (do not rewrite these to “fix” a run)
scripts/   setup, runner, ingest
report/    committed HTML + latest grid (the page the team opens)
jobs/      empty in git; local trial output
.env       your keys (gitignored)
```

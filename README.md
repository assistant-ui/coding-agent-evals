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

**Reward weights:** `AR-*` (app run) and `BR-*` (browser) count **2**;
code/workflow checks count **1**. Cascade skips count as fails.

| Command | What it measures | When to use it |
| --- | --- | --- |
| `check-env-codeverifiers` | The **graders** still work. Runs the gold overlay (no coding agent). | After clone, after a grader change, before a big agent run. |
| `full-eval` | **Agents.** G1–G11 × Cursor CLI / Claude Code / Codex × none / MCP / skills. | The product matrix. Expensive. |
| `custom` | The same axes, but you pick cases / agents / surface. | One case, one harness, a retry. |

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

That is **11 cases × 3 agents × 3 surfaces = 99 trials**, up to **10**
at a time, on Blaxel. Budget hours and API spend. None / MCP / skills
are three sequential jobs (sandbox env is per job).

### 3. A subset

`custom` requires `--cases` and `--agents`.

```bash
# One harness, MCP surface, two cases (low / cheap models).
./scripts/run.sh custom --cases g1,g2 --agents cursor-cli --surface mcp --mode low

# High-tier models, 30 sandboxes in flight.
./scripts/run.sh custom --cases g1 --agents cursor-cli,claude-code,codex --surface mcp --mode high --concurrent 30

# Three harnesses, one case, skills only (MCP off + Harbor Agent Skills).
./scripts/run.sh custom --cases g1 --agents cursor-cli,claude-code,codex --surface skills

# Local Docker instead of Blaxel.
./scripts/run.sh custom --cases g1 --agents cursor-cli --surface mcp --env docker
```

### Flags (all commands)

| Flag | Default | Meaning |
| --- | --- | --- |
| `--cases g1,g2` | all G1–G11 | Case ids from the table below |
| `--agents cursor-cli,claude-code,codex` | all three | Ignored for `check-env-codeverifiers` |
| `--surface none,mcp,skills\|all` | `mcp` for `custom`; all three for `full-eval` | Web docs / product MCP / Agent Skills |
| `--mcp on\|off\|both` | alias for `--surface` | `on`=`mcp`, `off`=`none`, `both`=`mcp,none` |
| `--mode low\|high` | `low` | Cheap vs expensive models (see table below) |
| `--env blaxel\|docker\|…` | `blaxel` | Sandbox. Same name as Harbor’s `--env`. |
| `--concurrent N` | `10` | Max Harbor trials / sandboxes in flight |
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

Surfaces: **none** = web docs only (`PB1_MCP=off`); **mcp** = assistant-ui
docs MCP; **skills** = MCP off plus Harbor Agent Skills from
`assistant-ui/skills` on `main` (`PB1_SURFACE=skills` on both the
sandbox and the grader). `PB1_MODE` is also set on both so ingest can
keep low and high cells apart.

| Mode | Cursor CLI | Claude Code | Codex |
| --- | --- | --- | --- |
| `low` (cheap, default) | `cursor/composer-2.5` | `anthropic/claude-sonnet-5` | `openai/gpt-5.6-luna` |
| `high` | `cursor/grok-4.6` | `anthropic/claude-fable-5-1` | `openai/gpt-5.6-sol` |

## After a run

1. Open **`report/index.html`** in a browser (`file://` is fine). Cells
   are score / agent time / API cost. Em dash means not run. Gold
   oracles are a verifier badge on the case, not a harness row. Failed
   checks show a plain-language title first; the id (`BR-06`, `WF-S-01`)
   is a tag. Prefixes: **CQ** source, **AR** app run, **BR** browser,
   **WF-D** docs/MCP/skills, **WF-S** `create` scaffold, **WF-E** errors
   during the agent run, **WF-T** agent started and tested the app.
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

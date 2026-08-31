#!/usr/bin/env bash
set -u

APP_HOST="127.0.0.1"
APP_PORT="${EVAL_APP_PORT:-3000}"
export BASE_URL="http://${APP_HOST}:${APP_PORT}"
export EVAL_WORKSPACE="${EVAL_WORKSPACE:-/workspace}"
export PYTHONPATH="/tests${PYTHONPATH:+:$PYTHONPATH}"
CHECKS_JSON="${CHECKS_JSON:-/logs/verifier/checks.json}"
REWARD_TXT="${REWARD_TXT:-/logs/verifier/reward.txt}"
GATES_JSON="${GATES_JSON:-/logs/verifier/gates.json}"
APP_PID=""
MCP_PID=""

cleanup() {
  if [ -n "$APP_PID" ]; then
    kill "$APP_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$MCP_PID" ]; then
    kill "$MCP_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

write_report() {
  junit_args=()
  for report in pytest-workflow.xml pytest-code.xml pytest-apprun.xml pytest-browser.xml; do
    if [ -f "/logs/verifier/$report" ]; then
      junit_args+=(--junit "/logs/verifier/$report")
    fi
  done
  python3 /tests/report.py \
    --checks "$CHECKS_JSON" \
    --reward "$REWARD_TXT" \
    --gates "$GATES_JSON" \
    --profile "${CHECKS_PROFILE:-pb1}" \
    "${junit_args[@]}" \
    "$@"
}

fail_and_exit() {
  python3 /tests/checks.py --set-gate "$GATES_JSON" "$1" fail "$2"
  write_report
  if [ "${JUDGE_EC:-0}" -ne 0 ]; then
    rm -f "$REWARD_TXT"
    exit 2
  fi
  exit 0
}

mkdir -p /logs/verifier /logs/verifier/playwright
printf '%s\n' '{}' >"$GATES_JSON"

CHECKS_PROFILE="$(python3 /tests/lib/workspace.py --print-profile)"
export CHECKS_PROFILE
printf '%s\n' "$CHECKS_PROFILE" >/logs/verifier/checks-profile.txt

TRAJECTORY_PATH="${TRAJECTORY_PATH:-/logs/agent/trajectory.json}"
export TRAJECTORY_PATH
INSTRUCTION_PATH="${INSTRUCTION_PATH:-/instruction.md}"
export INSTRUCTION_PATH
JUDGE_EC=0

if [ "${CHECKS_PROFILE}" != "gold" ]; then
  python3 -m pytest /tests/test_workflow.py -q --tb=short \
    --junitxml=/logs/verifier/pytest-workflow.xml || true
  pip3 install --quiet --disable-pip-version-check openai pydantic \
    >/logs/verifier/pip-judge.log 2>&1 || true
  python3 /tests/judge/run.py \
    --atif "$TRAJECTORY_PATH" \
    --instruction "$INSTRUCTION_PATH" \
    --out-dir /logs/verifier \
    --gates "$GATES_JSON" || JUDGE_EC=$?
fi

APP_ROOT="$(python3 /tests/lib/workspace.py --print-root 2>/dev/null || true)"
if [ -z "$APP_ROOT" ]; then
  fail_and_exit CQ-G-01 "no package.json app root under $EVAL_WORKSPACE"
fi
export APP_ROOT
printf '%s\n' "$APP_ROOT" >/logs/verifier/app-root.txt

python3 -m pytest /tests/test_code.py -q --tb=short \
  --junitxml=/logs/verifier/pytest-code.xml
code_ec=$?

cd "$APP_ROOT"

if [ ! -d node_modules ]; then
  if ! npm install --no-audit --no-fund >/logs/verifier/npm-install.log 2>&1; then
    fail_and_exit AR-01 "npm install failed; see npm-install.log"
  fi
fi
python3 /tests/checks.py --set-gate "$GATES_JSON" AR-01 pass

if ! npm run build >/logs/verifier/build.log 2>&1; then
  fail_and_exit AR-02 "npm run build failed; see build.log"
fi
python3 /tests/checks.py --set-gate "$GATES_JSON" AR-02 pass
npx --yes tsc --noEmit >/logs/verifier/tsc.log 2>&1 || true

if node -e 'process.exit(require("./package.json").scripts&&require("./package.json").scripts["start:mcp"]?0:1)'; then
  npm run start:mcp >/logs/verifier/mcp-start.log 2>&1 &
  MCP_PID=$!
elif node -e 'process.exit(require("./package.json").scripts&&require("./package.json").scripts["start:server"]?0:1)'; then
  npm run start:server >/logs/verifier/mcp-start.log 2>&1 &
  MCP_PID=$!
elif [ -f server/mcp.mjs ]; then
  node server/mcp.mjs >/logs/verifier/mcp-start.log 2>&1 &
  MCP_PID=$!
elif [ -f server/mcp.js ]; then
  node server/mcp.js >/logs/verifier/mcp-start.log 2>&1 &
  MCP_PID=$!
fi
if [ -n "$MCP_PID" ]; then
  for _ in $(seq 1 20); do
    if curl --fail --silent http://127.0.0.1:8787/health >/dev/null 2>&1 \
      || curl --fail --silent http://127.0.0.1:8000/health >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

env -u PORT -u HOST -u HOSTNAME \
  HOSTNAME="$APP_HOST" PORT="$APP_PORT" \
  npx --yes next start -H "$APP_HOST" -p "$APP_PORT" \
  >/logs/verifier/next-start.log 2>&1 &
APP_PID=$!

ready=0
for _ in $(seq 1 60); do
  if curl --fail --silent "$BASE_URL/" >/dev/null; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  fail_and_exit AR-03 "app did not become ready at $BASE_URL"
fi
python3 /tests/checks.py --set-gate "$GATES_JSON" AR-03 pass

python3 -m pytest /tests/test_apprun.py -q --tb=short \
  --junitxml=/logs/verifier/pytest-apprun.xml
apprun_ec=$?

python3 -m pytest /tests/test_browser.py -q --tb=short \
  --base-url "$BASE_URL" \
  --browser chromium \
  --output /logs/verifier/playwright \
  --screenshot only-on-failure \
  --junitxml=/logs/verifier/pytest-browser.xml
browser_ec=$?

write_report
if [ "${JUDGE_EC:-0}" -ne 0 ]; then
  rm -f "$REWARD_TXT"
  exit 2
fi
exit 0

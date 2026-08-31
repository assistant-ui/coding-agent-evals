#!/usr/bin/env bash
set -u

# Expo --host only accepts lan|tunnel|localhost (not 127.0.0.1).
APP_HOST="localhost"
APP_PORT="${EVAL_APP_PORT:-3000}"
export BASE_URL="http://${APP_HOST}:${APP_PORT}"
export EVAL_WORKSPACE="${EVAL_WORKSPACE:-/workspace}"
export PYTHONPATH="/tests${PYTHONPATH:+:$PYTHONPATH}"
export EXPO_ROUTER_DISABLE_RN_NAVIGATION_CHECK=1
CHECKS_JSON="${CHECKS_JSON:-/logs/verifier/checks.json}"
REWARD_TXT="${REWARD_TXT:-/logs/verifier/reward.txt}"
GATES_JSON="${GATES_JSON:-/logs/verifier/gates.json}"
APP_PID=""

cleanup() {
  if [ -n "$APP_PID" ]; then
    kill "$APP_PID" >/dev/null 2>&1 || true
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

# Compile check. Runtime is always `expo start --web` (same for gold and
# agents). Do not require gold-only flatten-assets / serve-web.mjs.
if node -e 'process.exit(require("./package.json").scripts && require("./package.json").scripts.build ? 0 : 1)'; then
  if ! npm run build >/logs/verifier/build.log 2>&1; then
    fail_and_exit AR-02 "npm run build failed; see build.log"
  fi
elif node -e 'process.exit(require("./package.json").scripts && require("./package.json").scripts["export:web"] ? 0 : 1)'; then
  if ! npm run export:web >/logs/verifier/build.log 2>&1; then
    if ! npx expo export --platform web >>/logs/verifier/build.log 2>&1; then
      fail_and_exit AR-02 "expo web export failed; see build.log"
    fi
  fi
elif ! npx expo export --platform web >/logs/verifier/build.log 2>&1; then
  fail_and_exit AR-02 "expo web export failed; see build.log"
fi
python3 /tests/checks.py --set-gate "$GATES_JSON" AR-02 pass
npx --yes tsc --noEmit >/logs/verifier/tsc.log 2>&1 || true

env -u PORT -u HOST -u HOSTNAME \
  CI=1 EXPO_NO_TELEMETRY=1 BROWSER=none \
  HOST="$APP_HOST" PORT="$APP_PORT" \
  npx expo start --web --port "$APP_PORT" --host "$APP_HOST" \
  >/logs/verifier/expo-web.log 2>&1 &
APP_PID=$!

ready=0
for _ in $(seq 1 180); do
  if curl --fail --silent "$BASE_URL/" >/dev/null; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  fail_and_exit AR-03 "app did not become ready at $BASE_URL; see expo-web.log"
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

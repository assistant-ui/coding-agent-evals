#!/usr/bin/env bash
# Oracle: CLI Eve template, then open the Eve HTTP channel for Harbor.
# create writes thread components that import @base-ui/react but does not
# add the package. Gold installs it. Documented in the G5 tracker.
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --template eve \
  --use-npm \
  --no-skills

(
  cd /workspace/gold-app
  npm install --no-audit --no-fund @base-ui/react
)

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/agent/channels
cp "$overlay/agent/channels/eve.ts" \
  /workspace/gold-app/agent/channels/eve.ts

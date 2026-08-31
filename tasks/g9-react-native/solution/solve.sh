#!/usr/bin/env bash
# Oracle: CLI Expo example, stub chat API. Harbor starts the same way as
# agents: expo start --web (no gold-only static server).
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --example with-expo \
  --use-npm \
  --no-skills \
  --skip-install

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
app=/workspace/gold-app

mkdir -p "$app/app/api"
cp "$overlay/metro.config.js" "$app/metro.config.js"
cp "$overlay/app/api/chat+api.ts" "$app/app/api/chat+api.ts"

cd "$app"

install_ok=0
for _ in 1 2 3; do
  if npm install --no-audit --no-fund; then
    install_ok=1
    break
  fi
  sleep 8
done
if [ "$install_ok" -ne 1 ]; then
  rm -f package-lock.json
  npm install --no-audit --no-fund --legacy-peer-deps
fi

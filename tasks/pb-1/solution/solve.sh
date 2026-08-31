#!/usr/bin/env bash
# Oracle: CLI AI SDK chat, then overlay the documented custom persistence adapter.
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --example with-ai-sdk-v7 \
  --use-npm \
  --no-skills

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/lib
cp "$overlay/lib/browser-thread-list-adapter.tsx" \
  /workspace/gold-app/lib/browser-thread-list-adapter.tsx
cp "$overlay/app/page.tsx" /workspace/gold-app/app/page.tsx

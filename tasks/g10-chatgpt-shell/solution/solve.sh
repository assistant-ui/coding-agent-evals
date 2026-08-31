#!/usr/bin/env bash
# Oracle: default template + ChatGPT preset + model-selector, then stub chat.
# Path mismatch: create writes elements/*.aui.tsx but assistant imports
# @/components/assistant-ui/thread — shim files cover that (same as G8).
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  -t default \
  -p chatgpt \
  --use-npm \
  --no-skills

(
  cd /workspace/gold-app
  npx --yes assistant-ui@latest add model-selector --use-npm
)

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/app/api/chat \
  /workspace/gold-app/components/assistant-ui

cp "$overlay/components/assistant-ui/thread.tsx" \
  /workspace/gold-app/components/assistant-ui/thread.tsx
cp "$overlay/components/assistant-ui/threadlist-sidebar.tsx" \
  /workspace/gold-app/components/assistant-ui/threadlist-sidebar.tsx
cp "$overlay/app/api/chat/route.ts" \
  /workspace/gold-app/app/api/chat/route.ts

# Wire ModelSelector + ChatGPT empty-state copy into the preset thread.
node "$overlay/scripts/patch-thread.mjs" \
  /workspace/gold-app/components/assistant-ui/elements/thread.aui.tsx

# Scaffold TS quirks (CSS var style + Base UI TooltipProvider).
node "$overlay/scripts/fix-scaffold-ts.mjs" /workspace/gold-app
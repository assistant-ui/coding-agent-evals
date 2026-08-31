#!/usr/bin/env bash
# Oracle: default template + Claude preset + artifacts panel + stub chat.
# Path mismatch: create writes elements/*.aui.tsx but assistant imports
# @/components/assistant-ui/thread — shim files cover that (same as G8/G10).
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  -t default \
  -p claude \
  --use-npm \
  --no-skills

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
app=/workspace/gold-app

mkdir -p "$app/app/api/chat" \
  "$app/components/assistant-ui"

cp "$overlay/components/assistant-ui/thread.tsx" \
  "$app/components/assistant-ui/thread.tsx"
cp "$overlay/components/assistant-ui/threadlist-sidebar.tsx" \
  "$app/components/assistant-ui/threadlist-sidebar.tsx"
cp "$overlay/app/assistant.tsx" "$app/app/assistant.tsx"
cp "$overlay/app/artifact-surface.tsx" "$app/app/artifact-surface.tsx"
cp "$overlay/app/artifact-state.ts" "$app/app/artifact-state.ts"
cp "$overlay/app/toolkit.tsx" "$app/app/toolkit.tsx"
cp "$overlay/app/api/chat/route.ts" "$app/app/api/chat/route.ts"

# Claude empty-state sparkle heading (preset look is accent/serif; clone adds welcome).
node "$overlay/scripts/patch-claude-thread.mjs" \
  "$app/components/assistant-ui/elements/thread.aui.tsx"

# Scaffold TS quirks (CSS var style + Base UI TooltipProvider).
node "$overlay/scripts/fix-scaffold-ts.mjs" "$app"

# zod is required by artifact-state (may already be present via create).
cd "$app"
npm install --no-audit --no-fund zod

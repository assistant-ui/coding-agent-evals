#!/usr/bin/env bash
# Oracle: CLI artifacts example, then overlay always-visible canvas + stub chat.
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --example with-artifacts \
  --use-npm \
  --no-skills

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/app/api/chat
cp "$overlay/app/page.tsx" \
  /workspace/gold-app/app/page.tsx
cp "$overlay/app/artifact-surface.tsx" \
  /workspace/gold-app/app/artifact-surface.tsx
cp "$overlay/app/api/chat/route.ts" \
  /workspace/gold-app/app/api/chat/route.ts
if [ -f "$overlay/.env.example" ]; then
  cp "$overlay/.env.example" /workspace/gold-app/.env.example
fi

#!/usr/bin/env bash
# Oracle: CLI Vite/TanStack example. Stub chatStream so Harbor has no live
# OpenAI. Thread shim covers the CLI path mismatch (elements/*.aui.tsx).
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --example with-tanstack \
  --use-npm \
  --no-skills

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/src/components/assistant-ui \
  /workspace/gold-app/src/server
if [ ! -f /workspace/gold-app/src/components/assistant-ui/thread.tsx ]; then
  cp "$overlay/src/components/assistant-ui/thread.tsx" \
    /workspace/gold-app/src/components/assistant-ui/thread.tsx
fi
cp "$overlay/src/server/chat.ts" /workspace/gold-app/src/server/chat.ts

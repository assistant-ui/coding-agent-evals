#!/usr/bin/env bash
# Oracle: CLI AI SDK chat, then wire Mastra per the full-stack integration guide.
# No Mastra create example. Latest Agent requires `id` (docs still show only name).
# @mastra/ai-sdk types against AI SDK v5/v6; with-ai-sdk-v7 ships ai@7.
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --example with-ai-sdk-v7 \
  --use-npm \
  --no-skills

(
  cd /workspace/gold-app
  npm install --no-audit --no-fund @mastra/core@latest @mastra/ai-sdk@latest zod@latest
)

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/mastra/agents \
  /workspace/gold-app/app/api/chat \
  /workspace/gold-app/components/assistant-ui
cp "$overlay/mastra/agents/chefAgent.ts" \
  /workspace/gold-app/mastra/agents/chefAgent.ts
cp "$overlay/mastra/index.ts" \
  /workspace/gold-app/mastra/index.ts
cp "$overlay/app/api/chat/route.ts" \
  /workspace/gold-app/app/api/chat/route.ts
cp "$overlay/next.config.js" \
  /workspace/gold-app/next.config.js
# CLI currently writes Thread to elements/*.aui.tsx; page still imports
# @/components/assistant-ui/thread.
if [ ! -f /workspace/gold-app/components/assistant-ui/thread.tsx ]; then
  cp "$overlay/components/assistant-ui/thread.tsx" \
    /workspace/gold-app/components/assistant-ui/thread.tsx
fi

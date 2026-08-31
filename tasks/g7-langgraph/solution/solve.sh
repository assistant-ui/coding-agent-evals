#!/usr/bin/env bash
# Oracle: CLI LangGraph UI. Next /api speaks the command/SSE protocol
# the official useStream client uses, invokes the in-process graph, and
# replays events so a late /stream/events subscribe still sees the tool call.
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --example with-langgraph \
  --use-npm \
  --no-skills

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/backend \
  /workspace/gold-app/components/assistant-ui \
  "/workspace/gold-app/app/api/[..._path]"
cp "$overlay/backend/agent.ts" /workspace/gold-app/backend/agent.ts
cp "$overlay/langgraph.json" /workspace/gold-app/langgraph.json
cp "$overlay/app/api/[..._path]/route.ts" \
  "/workspace/gold-app/app/api/[..._path]/route.ts"
# CLI with-langgraph currently writes Thread to elements/*.aui.tsx but
# page.tsx still imports @/components/assistant-ui/thread. Shim if missing.
if [ ! -f /workspace/gold-app/components/assistant-ui/thread.tsx ]; then
  cp "$overlay/components/assistant-ui/thread.tsx" \
    /workspace/gold-app/components/assistant-ui/thread.tsx
fi
if [ ! -f /workspace/gold-app/components/assistant-ui/thread-list.tsx ]; then
  cp "$overlay/components/assistant-ui/thread-list.tsx" \
    /workspace/gold-app/components/assistant-ui/thread-list.tsx
fi

(
  cd /workspace/gold-app
  npm install --no-audit --no-fund \
    @langchain/langgraph@latest \
    @langchain/core@latest
)

graph_id="$(
  node --input-type=module -e '
    import fs from "node:fs";
    const data = JSON.parse(fs.readFileSync("/workspace/gold-app/langgraph.json", "utf8"));
    const id = Object.keys(data.graphs || {})[0];
    if (!id) throw new Error("langgraph.json has no graphs");
    process.stdout.write(id);
  '
)"
printf '%s\n' \
  "LANGGRAPH_API_URL=http://127.0.0.1:2024" \
  "LANGCHAIN_API_KEY=" \
  "NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID=${graph_id}" \
  > /workspace/gold-app/.env.local

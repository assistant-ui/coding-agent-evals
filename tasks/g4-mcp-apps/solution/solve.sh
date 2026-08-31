#!/usr/bin/env bash
# Oracle: CLI MCP template, MCP App widget stub, add/remove servers UI,
# and a local MCP sidecar. Chat stub emits a ui:// widget or the echo tool.
set -euo pipefail
cd /workspace
npx --yes assistant-ui@latest create gold-app \
  --template mcp \
  --use-npm \
  --no-skills

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
app=/workspace/gold-app

mkdir -p "$app/app/api/chat" \
  "$app/app/api/mcp-apps" \
  "$app/components/assistant-ui" \
  "$app/server"

cp "$overlay/app/assistant.tsx" "$app/app/assistant.tsx"
cp "$overlay/app/api/chat/route.ts" "$app/app/api/chat/route.ts"
cp "$overlay/app/api/mcp-apps/route.ts" "$app/app/api/mcp-apps/route.ts"
cp "$overlay/app/api/mcp-client.ts" "$app/app/api/mcp-client.ts"
cp "$overlay/next.config.ts" "$app/next.config.ts"
cp "$overlay/server/mcp.mjs" "$app/server/mcp.mjs"
cp "$overlay/components/assistant-ui/mcp-config.tsx" \
  "$app/components/assistant-ui/mcp-config.tsx"
if [ ! -f "$app/components/assistant-ui/thread.tsx" ]; then
  cp "$overlay/components/assistant-ui/thread.tsx" \
    "$app/components/assistant-ui/thread.tsx"
fi
if [ ! -f "$app/components/assistant-ui/threadlist-sidebar.tsx" ]; then
  cp "$overlay/components/assistant-ui/threadlist-sidebar.tsx" \
    "$app/components/assistant-ui/threadlist-sidebar.tsx"
fi
if [ -f "$overlay/.env.example" ]; then
  cp "$overlay/.env.example" "$app/.env.example"
fi

cd "$app"
node --input-type=module -e '
import fs from "node:fs";
const path = "package.json";
const pkg = JSON.parse(fs.readFileSync(path, "utf8"));
pkg.scripts = pkg.scripts ?? {};
pkg.scripts["start:mcp"] = "node server/mcp.mjs";
fs.writeFileSync(path, JSON.stringify(pkg, null, 2) + "\n");
'
npm install --no-audit --no-fund \
  @assistant-ui/react-mcp@latest \
  @modelcontextprotocol/sdk \
  express \
  zod

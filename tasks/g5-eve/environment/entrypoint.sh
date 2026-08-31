#!/usr/bin/env sh
set -eu

# Harbor's Codex adapter uses CODEX_HOME=/tmp/codex-home. Trust the workspace
# only. Do not seed [mcp_servers.assistant-ui] here — Harbor appends that
# table from task.toml (duplicate key otherwise).
mkdir -p /tmp/codex-home
cat > /tmp/codex-home/config.toml <<'EOF'
[projects."/workspace"]
trust_level = "trusted"
EOF
chmod 0777 /tmp/codex-home
chmod 0666 /tmp/codex-home/config.toml

if command -v sandbox-api >/dev/null 2>&1; then
  sandbox-api &
  for attempt in $(seq 1 30); do
    nc -z 127.0.0.1 8080 && break
    sleep 1
  done
fi

exec sleep infinity

#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

harbor_ver() {
  harbor --version 2>/dev/null | head -n 1 | tr -d '[:space:]'
}

if ! command -v harbor >/dev/null 2>&1; then
  echo "harbor is not on PATH. Install Harbor 0.20:" >&2
  echo "  uv tool install 'harbor[blaxel]==0.20'" >&2
  exit 1
fi

ver="$(harbor_ver)"
case "$ver" in
  0.20|0.20.*) ;;
  *)
    echo "Harbor $ver is not supported. This suite is pinned to 0.20." >&2
    echo "  uv tool install 'harbor[blaxel]==0.20'" >&2
    exit 1
    ;;
esac
echo "Harbor $ver"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Wrote .env from .env.example — fill in keys before a run."
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to pack @assistant-ui/mcp-docs-server" >&2
  exit 1
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
echo "Packing published @assistant-ui/mcp-docs-server…"
pack_out="$(npm pack @assistant-ui/mcp-docs-server --pack-destination "$tmpdir" 2>/dev/null | tail -n 1)"
tarball="$tmpdir/$pack_out"
if [[ ! -f "$tarball" ]]; then
  # npm pack sometimes prints only the filename
  tarball="$(find "$tmpdir" -maxdepth 1 -name '*.tgz' | head -n 1)"
fi
if [[ ! -f "$tarball" ]]; then
  echo "npm pack did not produce a tarball" >&2
  exit 1
fi

n=0
for env_dir in "$root"/tasks/*/environment; do
  [[ -d "$env_dir" ]] || continue
  cp "$tarball" "$env_dir/mcp-docs-server.tgz"
  n=$((n + 1))
done
echo "Wrote mcp-docs-server.tgz into $n task environments"

if command -v bl >/dev/null 2>&1; then
  echo "Blaxel CLI: $(bl --version 2>/dev/null | head -n 1 || echo ok)"
else
  echo "warning: bl not on PATH (needed for the default Blaxel sandbox)"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "Docker: reachable"
else
  echo "warning: Docker daemon not reachable (--env docker will fail until it is)"
fi

echo
echo "Ready. Examples:"
echo "  ./scripts/run.sh check-env-codeverifiers --cases g1"
echo "  ./scripts/run.sh full-eval"
echo "  ./scripts/run.sh custom --cases g1 --agents cursor-cli --mcp on"

#!/usr/bin/env bash
set -euo pipefail
if ! command -v uvx >/dev/null 2>&1; then
  echo "[!] uvx not found. Install Astral uv: https://docs.astral.sh/uv/"
  exit 1
fi
if [ -z "${POLYGON_API_KEY:-}" ]; then
  echo "[!] Please export POLYGON_API_KEY before running this script."
  exit 1
fi
echo "[ok] Starting Polygon MCP server via uvx (STDIO transport)"
uvx --from git+https://github.com/polygon-io/mcp_polygon@v0.4.0 mcp_polygon

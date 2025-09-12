# MCP Setup for Polygon.io
Use the official Polygon MCP server so your GPT can call tools directly.

**Docs**
- Polygon MCP server: https://github.com/polygon-io/mcp_polygon
- MCP spec: https://modelcontextprotocol.io/specification/2025-03-26

## Quick start (local)
\`\`\`bash
# Install uv (Astral) per docs, then:
export POLYGON_API_KEY=YOUR_KEY
uvx --from git+https://github.com/polygon-io/mcp_polygon@v0.4.0 mcp_polygon
\`\`\`

## Claude Code (CLI)
\`\`\`bash
npm i -g @anthropic-ai/claude-code
claude mcp add polygon -e POLYGON_API_KEY=YOUR_KEY -- uvx --from git+https://github.com/polygon-io/mcp_polygon@v0.4.0 mcp_polygon
claude
\`\`\`

## Claude Desktop example config
\`\`\`json
{
  "mcpServers": {
    "polygon": {
      "command": "/usr/local/bin/uvx",
      "args": ["--from","git+https://github.com/polygon-io/mcp_polygon@v0.4.0","mcp_polygon"],
      "env": { "POLYGON_API_KEY": "YOUR_KEY", "HOME": "/Users/you" }
    }
  }
}
\`\`\`

## How this repo uses MCP
- Your GPT fetches data via MCP tools and then calls this API:
  - `/api/v1/analyze` with `context` (symbol, price, vwap, ema flags, divergence) derived from MCP
  - `/api/v1/trades` to save & track trades with `confluence_json` included

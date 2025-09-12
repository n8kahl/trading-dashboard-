from fastapi import APIRouter, HTTPException
from .common import ok
from app.services.mcp_bridge import mcp_list_tools, mcp_run_tool

router = APIRouter(prefix="/mcp", tags=["mcp"])

@router.get("/tools")
async def tools():
    try:
        data = await mcp_list_tools()
        return ok(data)
    except Exception as e:
        raise HTTPException(502, f"MCP list tools failed: {e}")

@router.post("/run")
async def run(body: dict):
    tool = body.get("tool")
    args = body.get("args", {})
    if not tool or not isinstance(args, dict):
        raise HTTPException(400, "Body must include 'tool' and 'args' object")
    try:
        data = await mcp_run_tool(tool, args)
        return ok(data)
    except Exception as e:
        raise HTTPException(502, f"MCP run failed: {e}")

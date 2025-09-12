import os, httpx

POLY = os.getenv("POLYGON_API_KEY","").strip()
BASE = "https://api.polygon.io"

def _params(extra=None):
    p = {"apiKey": POLY}
    if extra: p.update(extra)
    return p

async def mcp_list_tools():
    return {"tools": [
        {"name":"get_aggs","args":["ticker","timespan","multiplier","from_date","to_date","limit","sort"]},
        {"name":"get_snapshot_ticker","args":["ticker"]}
    ]}

async def _get(url, params):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params)
            if r.status_code >= 400:
                return {"_error": f"http {r.status_code}", "_text": (r.text or "")[:200], "_url": url}
            return r.json()
    except Exception as e:
        return {"_error": str(e), "_url": url}

async def mcp_run_tool(tool_name: str, args: dict):
    t = tool_name.strip()
    if t == "get_aggs":
        url = f"{BASE}/v2/aggs/ticker/{args['ticker']}/range/{int(args['multiplier'])}/{args['timespan']}/{args['from_date']}/{args['to_date']}"
        return await _get(url, _params({"adjusted":"true","sort":args.get("sort","asc"),"limit":int(args.get("limit",5000))}))
    if t == "get_snapshot_ticker":
        url = f"{BASE}/v3/snapshot/tickers/{args['ticker']}"
        return await _get(url, _params())
    return {"_error": f"unknown tool '{tool_name}'"}

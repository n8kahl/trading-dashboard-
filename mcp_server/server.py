import os, asyncio, httpx, atexit
from fastmcp import FastMCP, tool

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY","").strip()
BASE = "https://api.polygon.io"

if not POLYGON_API_KEY:
    raise RuntimeError("POLYGON_API_KEY not set")

_client = httpx.AsyncClient(timeout=20)

async def _get(url, **params):
    params = {"apiKey": POLYGON_API_KEY, **params}
    r = await _client.get(url, params=params)
    r.raise_for_status()
    return r.json()

async def _close_client() -> None:
    await _client.aclose()

def _shutdown() -> None:
    asyncio.run(_close_client())

atexit.register(_shutdown)

mcp = FastMCP("polygon-http-mcp")

@tool
async def get_aggs(ticker: str, timespan: str, multiplier: int, from_date: str, to_date: str, limit: int = 500, sort: str = "asc"):
    """
    Polygon v2 aggregates. Example: timespan='minute', multiplier=1, from_date='2025-09-01', to_date='2025-09-05'
    """
    url = f"{BASE}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
    return await _get(url, adjusted="true", sort=sort, limit=limit)

@tool
async def get_ema(ticker: str, window: int = 9, timespan: str = "minute", multiplier: int = 1, from_date: str = "", to_date: str = "", limit: int = 500):
    """
    Polygon EMA indicator (stocks/indices). window=9/20; timespan='minute'|'hour'|'day'
    """
    url = f"{BASE}/v1/indicators/ema/{ticker}"
    return await _get(url, timespan=timespan, window=window, multiplier=multiplier, from=from_date, to=to_date, limit=limit)

@tool
async def get_rsi(ticker: str, window: int = 14, timespan: str = "minute", multiplier: int = 1, from_date: str = "", to_date: str = "", limit: int = 500):
    """
    Polygon RSI indicator.
    """
    url = f"{BASE}/v1/indicators/rsi/{ticker}"
    return await _get(url, timespan=timespan, window=window, multiplier=multiplier, from=from_date, to=to_date, limit=limit)

@tool
async def get_snapshot_ticker(ticker: str):
    """
    Polygon snapshot (latest quote/trade where supported).
    """
    url = f"{BASE}/v3/snapshot/tickers/{ticker}"
    return await _get(url)

if __name__ == "__main__":
    # Streamable HTTP transport (production-friendly)
    # Host and port can be overridden by env (Railway sets PORT).
    host = os.getenv("HOST","0.0.0.0")
    port = int(os.getenv("PORT","9000"))
    # Run with streamable-http as per MCP spec (2025-03-26)
    mcp.run(transport="streamable-http", host=host, port=port)

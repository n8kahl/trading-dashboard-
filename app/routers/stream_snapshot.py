from fastapi import APIRouter, Query, HTTPException
import os, httpx

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])

def _parse_symbols(symbols_csv: str) -> list[str]:
    if not symbols_csv:
        return []
    return [s.strip().upper() for s in symbols_csv.split(",") if s.strip()]

@router.get("/snapshot")
async def stream_snapshot(symbols: str = Query(default="")):
    syms = _parse_symbols(symbols)
    if not syms:
        raise HTTPException(status_code=400, detail="Provide ?symbols=CSV e.g. ?symbols=SPY,AAPL")

    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="POLYGON_API_KEY not configured")

    # Polygon multi-ticker snapshot endpoint
    url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
    params = {"tickers": ",".join(syms), "apiKey": api_key}

    async with httpx.AsyncClient(timeout=6.0) as client:
        r = await client.get(url, params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Snapshot upstream error {r.status_code}: {r.text[:200]}")

    data = r.json() or {}
    tickers = data.get("tickers") or []

    quotes = {}
    for t in tickers:
        sym = t.get("ticker")
        last = (t.get("lastTrade") or {}).get("p")
        bid  = (t.get("lastQuote") or {}).get("bp")
        ask  = (t.get("lastQuote") or {}).get("ap")
        if sym:
            quotes[sym] = {"last": last, "bid": bid, "ask": ask}

    return {
        "ok": True,
        "data": {
            "symbols": syms,
            "quotes": quotes,            # may be partial if Polygon lacks a name
            "started_at": None,
            "interval_sec": 2.0
        }
    }

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services import market

router = APIRouter(prefix="/strategies/debug", tags=["strategies-debug"])

@router.get("/config")
async def config():
    # True if the process sees any acceptable Polygon key env var
    has_polygon = bool(market.POLYGON_API_KEY)
    return JSONResponse({"status":"ok","data":{"has_polygon_api_key": has_polygon}})

from typing import Optional
import datetime as dt, httpx, os

@router.get("/polygon-daily-probe")
async def polygon_daily_probe(symbol: str = "SPY", lookback: int = 160):
    api_key = os.getenv("POLYGON_API_KEY") or os.getenv("POLYGON_APIKEY") or os.getenv("POLYGON_KEY")
    if not api_key:
        return JSONResponse({"status":"error","error":"POLYGON_API_KEY not set in env"}, status_code=400)
    today = dt.date.today().strftime("%Y-%m-%d")
    start = (dt.date.today() - dt.timedelta(days=lookback*2)).strftime("%Y-%m-%d")
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start}/{today}"
    params = {"adjusted":"true","sort":"asc","limit":"50000","apiKey": api_key}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params)
    text = r.text
    snippet = text[:500]
    return JSONResponse({
        "status":"ok",
        "data":{
            "request_url": r.request.url.__str__(),
            "status_code": r.status_code,
            "reason": r.reason_phrase,
            "snippet": snippet
        }
    })

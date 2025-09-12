from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime as dt, os, httpx

router = APIRouter(prefix="/coach", tags=["coach"])
FMP_KEY = os.getenv("FMP_API_KEY")

class MarketOpenReq(BaseModel):
    horizon: str = "day"   # or "week"
    watchlist: List[str]
    window_days: int = 30  # lookahead window

async def _fmp_earnings_for_symbols(symbols: List[str], window_days: int) -> Dict[str, Any]:
    if not FMP_KEY or not symbols:
        return {"note": "No earnings data available"}
    # FMP earnings calendar: /v3/earning_calendar?from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=...
    start = dt.date.today()
    end = start + dt.timedelta(days=window_days)
    url = "https://financialmodelingprep.com/api/v3/earning_calendar"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params={"from": start.isoformat(), "to": end.isoformat(), "apikey": FMP_KEY})
        try:
            data = r.json()
        except Exception:
            return {"note": "No earnings data available"}
    # filter to watchlist only
    wl = {s.upper() for s in symbols}
    rows = [row for row in (data or []) if (row.get("symbol") or "").upper() in wl]
    # normalize keys
    out = []
    for row in rows:
        when = row.get("time") or row.get("when")  # sometimes "bmo"/"amc"
        date = row.get("date") or row.get("epsCalendarDate") or row.get("reportedDate")
        out.append({
            "symbol": (row.get("symbol") or "").upper(),
            "date": date,
            "when": when,
            "estimate": row.get("epsEstimated"),
        })
    return {"earnings": out} if out else {"note": "No earnings data available"}

@router.post("/market-open")
async def market_open(req: MarketOpenReq):
    # Earnings awareness for the user’s watchlist
    earn = await _fmp_earnings_for_symbols(req.watchlist, req.window_days)
    payload = {
        "ok": True,
        "watchlist": [s.upper() for s in req.watchlist],
        "horizon": req.horizon,
        "data": {
            "earnings_ahead": earn
        }
    }
    return payload

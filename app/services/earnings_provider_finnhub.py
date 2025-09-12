from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import os, httpx

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY","").strip()

def _iso(d): 
    return d.strftime("%Y-%m-%d")

async def fetch_earnings_ahead_finnhub(watchlist: List[str], window_days: int = 30) -> Dict[str, Any]:
    """
    Free earnings calendar via Finnhub.
    Returns: {"note": None|str, "earnings": [{symbol,date,when,days_to_earnings}]}
    """
    if not FINNHUB_KEY:
        return {"note": "No event data available", "earnings": []}

    today_dt = datetime.now(timezone.utc).date()
    start = today_dt
    end   = today_dt + timedelta(days=window_days)

    url   = "https://finnhub.io/api/v1/calendar/earnings"
    params = {"from": _iso(start), "to": _iso(end), "token": FINNHUB_KEY}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return {"note": "No event data available", "earnings": []}
            js = r.json() or {}
            rows = js.get("earningsCalendar", []) or []
    except Exception:
        return {"note": "No event data available", "earnings": []}

    wl = {s.upper() for s in (watchlist or [])}
    out: List[Dict[str, Any]] = []
    for e in rows:
        sym = (e.get("symbol") or e.get("ticker") or "").upper()
        if wl and sym not in wl:
            continue
        date = e.get("date") or e.get("reportDate")
        when = (e.get("hour") or "").lower() or None  # bmo/amc/tbc varies by record
        if not (date and sym):
            continue
        try:
            dd = (datetime.fromisoformat(date).date() - today_dt).days
        except Exception:
            dd = None
        out.append({"symbol": sym, "date": date, "when": when, "days_to_earnings": dd})

    if not out:
        return {"note": "No event data available", "earnings": []}

    # de-dup & sort
    seen=set(); clean=[]
    for x in out:
        k=(x["symbol"], x["date"])
        if k in seen: 
            continue
        seen.add(k); clean.append(x)
    clean.sort(key=lambda z:(z["date"], z["symbol"]))
    return {"note": None, "earnings": clean}

from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import os, httpx

FMP_KEY = os.getenv("FMP_API_KEY","")

def _iso(d): return d.strftime("%Y-%m-%d")

async def fetch_earnings_ahead_fmp(watchlist: List[str]) -> Dict[str,Any]:
    """Free earnings calendar next 7 days via FMP.
       Returns: {"note": <str|None>, "earnings": [ {symbol,date,when}... ] }
       when: lower-case bmo/amc/pmc/tbc when available, else None
    """
    if not FMP_KEY:
        return {"note": "No event data available", "earnings": []}

    today = datetime.now(timezone.utc).date()
    end   = today + timedelta(days=7)
    url   = "https://financialmodelingprep.com/api/v3/earning_calendar"
    params = {"from": _iso(today), "to": _iso(end), "apikey": FMP_KEY}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json() or []
    except Exception:
        return {"note": "No event data available", "earnings": []}

    wl = {s.upper() for s in (watchlist or [])}
    out = []
    for e in data:
        sym = (e.get("symbol") or e.get("ticker") or "").upper()
        if wl and sym not in wl: 
            continue
        when = (e.get("time") or "").lower() or None  # e.g., "bmo"/"amc"
        out.append({"symbol": sym, "date": e.get("date"), "when": when})

    if not out:
        return {"note": "No event data available", "earnings": []}

    # de-dup & sort
    seen=set(); clean=[]
    for x in out:
        k=(x["symbol"], x["date"])
        if k in seen: continue
        seen.add(k); clean.append(x)
    clean.sort(key=lambda z:(z["date"] or "", z["symbol"] or ""))
    return {"note": None, "earnings": clean}

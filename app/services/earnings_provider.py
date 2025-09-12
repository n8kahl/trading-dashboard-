from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import os, httpx

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY","")

def _iso_date(d): return d.strftime("%Y-%m-%d")

async def fetch_earnings_ahead(watchlist: List[str]) -> Dict[str,Any]:
    today = datetime.now(timezone.utc).date()
    end   = today + timedelta(days=7)

    if not POLYGON_API_KEY:
        return {"note": "No event data available", "earnings": []}

    # NOTE: Path/entitlement varies by plan. If your account lacks this,
    # we will return the "No event data available" note below.
    base = "https://api.polygon.io/vX/reference/earnings"  # adjust 'vX' to your entitled version if applicable
    results = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            for sym in watchlist or []:
                params = {
                    "ticker": sym.upper(),
                    "from": _iso_date(today),
                    "to": _iso_date(end),
                    "apiKey": POLYGON_API_KEY
                }
                r = await client.get(base, params=params)
                if r.status_code == 200:
                    payload = r.json() or {}
                    for e in payload.get("results", []):
                        results.append({
                            "symbol": sym.upper(),
                            "date": e.get("date") or e.get("fiscal_date"),
                            "when": (e.get("time") or "").lower() or None,
                        })
                else:
                    # Not entitled / 404 / 403 -> continue silently; we’ll return note if empty
                    continue
    except Exception:
        return {"note": "No event data available", "earnings": []}

    if not results:
        return {"note": "No event data available", "earnings": []}

    # de-dup & sort
    seen = set(); clean=[]
    for x in results:
        k=(x.get("symbol"),x.get("date"))
        if k in seen: continue
        seen.add(k); clean.append(x)
    clean.sort(key=lambda z:(z.get("date") or "", z.get("symbol") or ""))

    return {"note": None, "earnings": clean}

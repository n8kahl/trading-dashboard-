from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _ts_to_date(ts: int | None):
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
    except Exception:
        return None


async def _fetch_next_earnings(symbol: str) -> Dict[str, Any] | None:
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
    params = {"modules": "calendarEvents"}
    headers = {"User-Agent": UA, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return None
            j = r.json() or {}
            result = (j.get("quoteSummary", {}) or {}).get("result", [])
            if not result:
                return None
            cal = result[0].get("calendarEvents") or {}
            ed = cal.get("earnings", {}).get("earningsDate") or cal.get("earningsDate")
            if isinstance(ed, dict):
                ed = [ed]
            dates = []
            for e in ed or []:
                d = _ts_to_date((e or {}).get("raw"))
                if d:
                    dates.append(d)
            if not dates:
                return None
            soonest = min(dates)
            return {"symbol": symbol.upper(), "date": soonest, "when": None}
    except Exception:
        return None


async def fetch_earnings_ahead_yahoo(watchlist: List[str], window_days: int = 45) -> Dict[str, Any]:
    """
    Returns upcoming earnings within `window_days` (default 45) for given symbols.
    """
    if not watchlist:
        return {"note": "No event data available", "earnings": []}

    tasks = [_fetch_next_earnings(sym) for sym in watchlist]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    today = datetime.now(timezone.utc).date()
    out: List[Dict[str, Any]] = []
    for res in results:
        if isinstance(res, dict) and res.get("date"):
            try:
                sd = datetime.fromisoformat(res["date"]).date()
                delta = (sd - today).days
                if 0 <= delta <= window_days:
                    out.append(res)
            except Exception:
                continue

    if not out:
        return {"note": "No event data available", "earnings": []}

    seen = set()
    clean = []
    for x in out:
        k = (x["symbol"], x["date"])
        if k in seen:
            continue
        seen.add(k)
        clean.append(x)
    clean.sort(key=lambda z: (z["date"], z["symbol"]))
    return {"note": None, "earnings": clean}

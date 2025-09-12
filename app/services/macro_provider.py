from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

TE_KEY = os.getenv("TRADING_ECONOMICS_KEY", "").strip()


def _iso(d):
    return d.strftime("%Y-%m-%d")


async def fetch_week_ahead_macro(country: str = "united states", severity: List[str] | None = None) -> Dict[str, Any]:
    """
    Fetch next-7-day macro calendar from Trading Economics.
    - Free demo works with TE_KEY="guest:guest"
    - If TE_KEY missing or request fails, return explicit 'No event data available'
    Returns: {"note": <None|str>, "events": [ {date,time,name,country,importance,actual,forecast,previous} ... ]}
    """
    if not TE_KEY:
        return {"note": "No event data available", "events": []}

    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=7)

    base = "https://api.tradingeconomics.com/calendar"
    params = {"country": country, "from": _iso(today), "to": _iso(end), "importance": "1,2,3"}

    # Auth style: either basic auth "user:pass" or ?c=APIKEY
    auth = tuple(TE_KEY.split(":", 1)) if ":" in TE_KEY else None
    if auth is None:
        params["c"] = TE_KEY

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(base, params=params, auth=auth)
            r.raise_for_status()
            rows = r.json() or []
    except Exception:
        return {"note": "No event data available", "events": []}

    out = []
    for e in rows:
        # Normalize importance 1/2/3 -> low/medium/high
        try:
            imp_val = int(e.get("Importance", 0) or 0)
        except Exception:
            imp_val = 0
        imp = {1: "low", 2: "medium", 3: "high"}.get(imp_val, "low")
        if severity and imp not in severity:
            continue
        # Prefer UTC date/time if present
        date_utc = e.get("DateUtc") or ""
        date = date_utc.split("T")[0] if "T" in date_utc else (e.get("Date") or None)
        time = date_utc.split("T")[1][:5] if "T" in date_utc else None

        out.append(
            {
                "date": date,
                "time": time,
                "name": (e.get("Event") or "").strip(),
                "country": e.get("Country", ""),
                "importance": imp,
                "actual": e.get("Actual"),
                "forecast": e.get("Forecast"),
                "previous": e.get("Previous"),
            }
        )

    # Sort by date/time
    out.sort(key=lambda x: ((x.get("date") or ""), (x.get("time") or "")))
    return {"note": None, "events": out}

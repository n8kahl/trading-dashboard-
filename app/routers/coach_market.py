from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.market_overview import market_open_snapshot, enrich_with_events
from app.services.events_provider import fetch_today_events_polygon

router = APIRouter(prefix="/coach", tags=["coach"])

class MarketOpenRequest(BaseModel):
    lookback: int = 120
    events: List[str] = []
    events_source: str = "polygon"   # "polygon" | "manual"
    watchlist: List[str] = []        # used when events_source="polygon"
    horizon: str = "day"             # "day" | "week"
    country: str = "united states"
    severity: List[str] = ["high","medium"]
    window_days: int = 30

@router.post("/market-open")
async def market_open(req: MarketOpenRequest):
    try:
        snap = await market_open_snapshot(req.lookback)

        if req.events_source == "polygon":
            poly = await fetch_today_events_polygon(req.watchlist or [])
            merged: List[str] = []
            for e in poly.get("earnings", []):
                sym = e.get("symbol", "")
                when = e.get("time", "")
                note = e.get("note", "")
                merged.append(("Earnings " + sym + (" (" + when + ")" if when else "") + (" " + note if note else "")).strip())
            for n in poly.get("news", []):
                sym = n.get("symbol", "")
                ttl = n.get("headline", "")
                merged.append(f"News {sym}: {ttl}" if sym else f"News: {ttl}")
            snap = await enrich_with_events(snap, merged)
        else:
            snap = await enrich_with_events(snap, req.events)

        # Polygon-only week view: macro note + earnings (if entitled)
        
        if req.horizon == "week":
            from app.services.macro_provider import fetch_week_ahead_macro
            from app.services.earnings_provider_finnhub import fetch_earnings_ahead_finnhub
            
            week = await fetch_week_ahead_macro(country=req.country, severity=req.severity)
            earn = await fetch_earnings_ahead_finnhub(req.watchlist or [], window_days=req.window_days)
            # Harden shapes
            if not isinstance(week, dict):
                week = {"note": str(week), "events": []}
            if not isinstance(earn, dict):
                earn = {"note": "No event data available", "earnings": []}
            if "note" not in week or "events" not in week:
                week = {"note": week.get("note") if isinstance(week, dict) else None,
                        "events": week.get("events") if isinstance(week, dict) else []}
            if "note" not in earn or "earnings" not in earn:
                earn = {"note": earn.get("note") if isinstance(earn, dict) else None,
                        "earnings": earn.get("earnings") if isinstance(earn, dict) else []}
            
            # harden shapes
            if not isinstance(week, dict):
                week = {"note": str(week), "events": []}
            if not isinstance(earn, dict):
                earn = {"note": "No event data available", "earnings": []}
            if "note" not in week or "events" not in week:
                week = {"note": week.get("note") if isinstance(week, dict) else None,
                        "events": week.get("events") if isinstance(week, dict) else []}
            if "note" not in earn or "earnings" not in earn:
                earn = {"note": earn.get("note") if isinstance(earn, dict) else None,
                        "earnings": earn.get("earnings") if isinstance(earn, dict) else []}
            snap["week_ahead"] = week
            snap["earnings_ahead"] = earn

        return {"status": "ok", "data": snap}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"market_open error: {e}")

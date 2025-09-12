from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.services.data_provider import fetch_aggregates, DataError

def _pct_change(series: List[float]) -> float:
    if not series or len(series) < 2: return 0.0
    start, end = series[0], series[-1]
    if start == 0: return 0.0
    return (end - start) / start * 100.0

async def market_open_snapshot(lookback:int=120) -> Dict[str, Any]:
    """
    Pulls daily sentiment context from SPY/QQQ and risk tone via VIX (day TF).
    If your plan includes minute intraday, switch timeframe='minute' if desired.
    """
    indices = ["SPY","QQQ"]
    out = {"as_of": datetime.now(timezone.utc).isoformat(), "indices": [], "risk": {}, "summary": ""}

    # Indices snapshot
    for sym in indices:
        bars = await fetch_aggregates(sym, "day", lookback)
        close = bars.get("close", [])
        high = bars.get("high", [])
        low  = bars.get("low", [])
        vwap = bars.get("vwap", []) if "vwap" in bars else []
        chg  = round(_pct_change(close[-5:]), 2) if len(close) >= 5 else 0.0
        out["indices"].append({
            "symbol": sym,
            "pct_change_5d": chg,
            "last_close": close[-1] if close else None,
            "hod": max(high[-5:]) if len(high)>=5 else (max(high) if high else None),
            "lod": min(low[-5:]) if len(low)>=5 else (min(low) if low else None),
            "vwap_last": vwap[-1] if vwap else None
        })

    # VIX proxy: use VIX ETF ^VIX via Polygon? If not available on your plan, fallback to VVIX/UVXY
    # Here we try VIX spot index ticker "VIX" (Polygon supports Cboe indices for certain plans).
    risk_gauge = {}
    try:
        vix = await fetch_aggregates("VIX", "day", 30)
        risk_gauge = {
            "symbol":"VIX",
            "last_close": vix.get("close", [])[-1] if vix.get("close") else None,
            "pct_change_5d": round(_pct_change(vix.get("close", [])[-5:]),2) if len(vix.get("close",[]))>=5 else None
        }
    except Exception:
        risk_gauge = {"note": "VIX data not available on current plan"}
    out["risk"] = risk_gauge

    # Heuristic sentiment
    bull = sum(1 for i in out["indices"] if (i.get("pct_change_5d") or 0) > 0)
    if bull == 2 and (risk_gauge.get("last_close") or 0) < 20:
        out["summary"] = "Constructive risk tone: major indices firm over 5d and volatility subdued."
    elif bull >= 1:
        out["summary"] = "Mixed tone: some strength, monitor volatility and key levels."
    else:
        out["summary"] = "Caution: momentum weak across indices. Prioritize risk control."

    return out

async def enrich_with_events(snapshot: Dict[str, Any], todays_events: list[str] | None) -> Dict[str, Any]:
    """Attach a manual list of today's events (CPI, FOMC, earnings). Later we can integrate an economic API."""
    snapshot["events"] = todays_events or []
    return snapshot

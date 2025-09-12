from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, Any, List, Literal, Tuple
from app.services.polygon import get_json, PolygonError
from .options_common import (
    _today_utc,
    expiration_window,
    nearest_strike_indices,
    format_quote,
)

Side = Literal["long_call","long_put","short_call","short_put"]
Horizon = Literal["intra","day","week"]

def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def _next_weekday(d: date) -> date:
    while _is_weekend(d):
        d += timedelta(days=1)
    return d

async def fetch_spot(ticker: str) -> float:
    """Fetch the latest trade price for a ticker."""
    j = await get_json(f"/v2/last/trade/{ticker.upper()}")
    last = j.get("last") or {}
    px = last.get("price")
    if px is not None:
        return float(px)
    # fallback: previous close
    p = await get_json(f"/v2/aggs/ticker/{ticker.upper()}/prev")
    results = p.get("results") or []
    if not results:
        raise PolygonError("No spot/prev data available for " + ticker)
    return float(results[0]["c"])

async def _contracts_exist(ticker: str, exp: date, cp: Literal["call","put"]) -> bool:
    res = await get_json("/v3/reference/options/contracts", {
        "underlying_ticker": ticker.upper(),
        "expiration_date": exp.isoformat(),
        "contract_type": cp,
        "limit": 1,
        "order": "asc",
        "sort": "strike_price",
    })
    return (res.get("resultsCount") or 0) > 0

async def choose_expiration(ticker: str, horizon: Horizon, cp: Literal["call","put"]) -> date:
    # Target window by horizon
    start = _next_weekday(_today_utc())
    min_dte, max_dte = expiration_window(horizon)

    # Probe forward up to 14 days; prefer first date within window; otherwise first available
    first_available: date | None = None
    for i in range(0, 14):
        d = start + timedelta(days=i)
        if _is_weekend(d):
            continue
        if await _contracts_exist(ticker, d, cp):
            if first_available is None:
                first_available = d
            if min_dte <= i <= max_dte:
                return d
    if first_available:
        return first_available
    raise PolygonError("No expirations found for " + ticker)

async def fetch_contracts_for_exp(ticker: str, exp: date, cp: Literal["call","put"], limit: int = 1000) -> List[Dict[str, Any]]:
    res = await get_json("/v3/reference/options/contracts", {
        "underlying_ticker": ticker.upper(),
        "expiration_date": exp.isoformat(),
        "contract_type": cp,
        "limit": limit,
        "order": "asc",
        "sort": "strike_price",
    })
    return res.get("results") or []

async def _recent_quote(opt_symbol: str) -> Tuple[float | None, float | None, float | None]:
    # returns (bid, ask, last) using most recent quote
    q = await get_json(
        f"/v3/quotes/options/{opt_symbol}", {"limit": 1, "sort": "timestamp", "order": "desc"}
    )
    results = q.get("results") or []
    if not results:
        return None, None, None
    r0 = results[0]
    # Polygon field names vary by tier; try a few
    bid = r0.get("bid_price") or r0.get("bidPrice") or r0.get("bp")
    ask = r0.get("ask_price") or r0.get("askPrice") or r0.get("ap")
    last = r0.get("last_price") or r0.get("price") or r0.get("lp")
    return (
        float(bid) if bid is not None else None,
        float(ask) if ask is not None else None,
        float(last) if last is not None else None,
    )

async def pick_live_contracts(ticker: str, side: Side, horizon: Horizon, n: int = 5) -> Dict[str, Any]:
    cp = "call" if "call" in side else "put"
    spot = await fetch_spot(ticker)
    exp = await choose_expiration(ticker, horizon, cp)
    contracts = await fetch_contracts_for_exp(ticker, exp, cp)
    if not contracts:
        raise PolygonError("No option contracts returned")

    # Pull strikes and pick the n closest to spot
    strikes = [float(c.get("strike_price", 0.0)) for c in contracts]
    idxs = nearest_strike_indices(strikes, spot, n)

    # Compose picks (and fetch quotes for those n contracts)
    picks: List[Dict[str, Any]] = []
    for i in idxs:
        c = contracts[i]
        sym = c.get("ticker") or c.get("contract") or c.get("symbol")
        bid, ask, last = await _recent_quote(sym)
        bid_f, ask_f, mark_f, spread_pct = format_quote(bid, ask, last)
        picks.append({
            "symbol": sym,
            "expiration": exp.isoformat(),
            "strike": float(c.get("strike_price")),
            "option_type": cp,
            "bid": bid_f,
            "ask": ask_f,
            "mark": mark_f,
            "spread_pct": spread_pct,
            # You can add more real fields later (open_interest, volume, delta) from additional endpoints/tiers
        })

    picks = sorted(picks, key=lambda p: abs(p["strike"] - spot))
    return {
        "ok": True,
        "env": "live",
        "note": "live contracts",
        "count_considered": len(picks),
        "picks": picks,
        "meta": {"spot": spot, "expiration": exp.isoformat(), "horizon": horizon, "side": side}
    }

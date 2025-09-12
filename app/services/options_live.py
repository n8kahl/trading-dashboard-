from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Literal, Tuple
from dateutil.tz import UTC
from app.services.polygon import get_json, PolygonError

Side = Literal["long_call","long_put","short_call","short_put"]
Horizon = Literal["intra","day","week"]

def _today_utc() -> date:
    return datetime.now(tz=UTC).date()

def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def _next_weekday(d: date) -> date:
    while _is_weekend(d):
        d += timedelta(days=1)
    return d

def fetch_spot(ticker: str) -> float:
    # Prefer last trade; if missing, fall back to previous close (still real, not fabricated)
    j = get_json(f"/v2/last/trade/{ticker.upper()}")
    last = j.get("last") or {}
    px = last.get("price")
    if px is not None:
        return float(px)
    # fallback: previous close
    p = get_json(f"/v2/aggs/ticker/{ticker.upper()}/prev")
    results = p.get("results") or []
    if not results:
        raise PolygonError("No spot/prev data available for " + ticker)
    return float(results[0]["c"])

def _contracts_exist(ticker: str, exp: date, cp: Literal["call","put"]) -> bool:
    res = get_json("/v3/reference/options/contracts", {
        "underlying_ticker": ticker.upper(),
        "expiration_date": exp.isoformat(),
        "contract_type": cp,
        "limit": 1,
        "order": "asc",
        "sort": "strike_price",
    })
    return (res.get("resultsCount") or 0) > 0

def choose_expiration(ticker: str, horizon: Horizon, cp: Literal["call","put"]) -> date:
    # Target window by horizon
    start = _next_weekday(_today_utc())
    if horizon in ("intra","day"):
        # aim 0-2 DTE
        min_dte, max_dte = 0, 2
    else:  # week
        min_dte, max_dte = 3, 10

    # Probe forward up to 14 days; prefer first date within window; otherwise first available
    first_available: date | None = None
    for i in range(0, 14):
        d = start + timedelta(days=i)
        if _is_weekend(d):
            continue
        if _contracts_exist(ticker, d, cp):
            if first_available is None:
                first_available = d
            if min_dte <= i <= max_dte:
                return d
    if first_available:
        return first_available
    raise PolygonError("No expirations found for " + ticker)

def fetch_contracts_for_exp(ticker: str, exp: date, cp: Literal["call","put"], limit: int = 1000) -> List[Dict[str, Any]]:
    res = get_json("/v3/reference/options/contracts", {
        "underlying_ticker": ticker.upper(),
        "expiration_date": exp.isoformat(),
        "contract_type": cp,
        "limit": limit,
        "order": "asc",
        "sort": "strike_price",
    })
    return res.get("results") or []

def _nearest_indices(strikes: List[float], spot: float, take: int) -> List[int]:
    # return indices of strikes closest to spot (ties resolved by natural order)
    indexed = list(enumerate(strikes))
    ranked = sorted(indexed, key=lambda it: (abs(it[1]-spot), it[1]))
    return [i for i,_ in ranked[:take]]

def _recent_quote(opt_symbol: str) -> Tuple[float|None, float|None, float|None]:
    # returns (bid, ask, mark) using most recent quote
    q = get_json(f"/v3/quotes/options/{opt_symbol}", {
        "limit": 1, "sort": "timestamp", "order": "desc"
    })
    results = q.get("results") or []
    if not results:
        return None, None, None
    r0 = results[0]
    # Polygon field names vary by tier; try a few
    bid = r0.get("bid_price") or r0.get("bidPrice") or r0.get("bp")
    ask = r0.get("ask_price") or r0.get("askPrice") or r0.get("ap")
    last = r0.get("last_price") or r0.get("price") or r0.get("lp")
    mark = None
    if bid is not None and ask is not None:
        try:
            mark = (float(bid) + float(ask)) / 2.0
        except Exception:
            mark = None
    return (float(bid) if bid is not None else None,
            float(ask) if ask is not None else None,
            float(mark) if mark is not None else (float(last) if last is not None else None))

def pick_live_contracts(ticker: str, side: Side, horizon: Horizon, n: int = 5) -> Dict[str, Any]:
    cp = "call" if "call" in side else "put"
    spot = fetch_spot(ticker)
    exp = choose_expiration(ticker, horizon, cp)
    contracts = fetch_contracts_for_exp(ticker, exp, cp)
    if not contracts:
        raise PolygonError("No option contracts returned")

    # Pull strikes and pick the n closest to spot
    strikes = [float(c.get("strike_price", 0.0)) for c in contracts]
    idxs = _nearest_indices(strikes, spot, n)

    # Compose picks (and fetch quotes for those n contracts)
    picks: List[Dict[str, Any]] = []
    for i in idxs:
        c = contracts[i]
        sym = c.get("ticker") or c.get("contract") or c.get("symbol")
        bid, ask, mark = _recent_quote(sym)
        ask_f = float(ask) if ask is not None else None
        bid_f = float(bid) if bid is not None else None
        mark_f = float(mark) if mark is not None else None
        spread_pct = None
        if ask_f is not None and bid_f is not None and mark_f and mark_f > 0:
            spread_pct = (ask_f - bid_f) / mark_f
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

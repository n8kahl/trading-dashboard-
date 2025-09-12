from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Literal
from dateutil.tz import UTC
from app.services.tradier_client import get, TradierError

Side = Literal["long_call","long_put","short_call","short_put"]
Horizon = Literal["intra","day","week"]

def _today_utc() -> date:
    return datetime.now(tz=UTC).date()

def _as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

# ---------- Underlying (delayed) ----------
def fetch_spot(ticker: str) -> float:
    j = get("/v1/markets/quotes", {"symbols": ticker.upper()})
    q = (j.get("quotes") or {}).get("quote")
    if not q:
        raise TradierError(f"No quote for {ticker}")
    if isinstance(q, list):
        q = q[0]
    # sandbox is delayed; prefer "last" then "close"
    last = q.get("last") if q.get("last") not in (None, "na") else None
    if last is None:
        last = q.get("close")
    if last is None:
        raise TradierError(f"No last/close for {ticker}")
    return float(last)

# ---------- Expirations ----------
def fetch_expirations(ticker: str) -> List[date]:
    j = get("/v1/markets/options/expirations", {
        "symbol": ticker.upper(),
        "includeAllRoots": "true",
        "strikes": "false",
    })
    exps = (j.get("expirations") or {}).get("date")
    datestr = _as_list(exps)
    out: List[date] = []
    for s in datestr:
        try:
            y,m,d = map(int, s.split("-"))
            out.append(date(y,m,d))
        except Exception:
            continue
    return sorted(out)

def choose_expiration(ticker: str, horizon: Horizon) -> date:
    exps = fetch_expirations(ticker)
    if not exps:
        raise TradierError(f"No expirations for {ticker}")
    today = _today_utc()
    # horizon targeting (all delayed, so this is "nearest reasonable")
    if horizon in ("intra","day"):
        # prefer same-day if available, else next 1-2 days
        window = [0,1,2]
    else:  # week
        window = [3,4,5,6,7,8,9,10]
    # pick first exp that is today+delta and exists
    for d in window:
        target = today + timedelta(days=d)
        for e in exps:
            if e == target:
                return e
    # fallback: first expiration in the future
    for e in exps:
        if e >= today:
            return e
    # otherwise last
    return exps[-1]

# ---------- Chains & Quotes ----------
def fetch_chain(ticker: str, exp: date) -> List[Dict[str, Any]]:
    j = get("/v1/markets/options/chains", {
        "symbol": ticker.upper(),
        "expiration": exp.isoformat(),
        # greeks=false keeps payload smaller; add &greeks=true later if needed
    })
    opts = (j.get("options") or {}).get("option")
    return _as_list(opts)

def fetch_option_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    if not symbols:
        return {}
    # Batch quote — Tradier accepts comma-separated up to large counts
    j = get("/v1/markets/quotes", {"symbols": ",".join(symbols)})
    q = (j.get("quotes") or {}).get("quote")
    items = _as_list(q)
    out: Dict[str, Dict[str, Any]] = {}
    for it in items:
        sym = it.get("symbol")
        if not sym:
            continue
        out[sym] = it
    return out

# ---------- Pick closest-to-ATM N for a side ----------
def pick_live_contracts_tradier(ticker: str, side: Side, horizon: Horizon, n: int = 5) -> Dict[str, Any]:
    cp = "call" if "call" in side else "put"
    spot = fetch_spot(ticker)
    exp = choose_expiration(ticker, horizon)
    chain = fetch_chain(ticker, exp)
    if not chain:
        raise TradierError("No chain returned")

    # filter by call/put
    leg = [o for o in chain if (o.get("option_type") or "").lower() == cp]
    if not leg:
        raise TradierError("No contracts for requested side")

    # sort by |strike - spot|
    def _strike(o): 
        try: return float(o.get("strike"))
        except: return float("inf")
    leg_sorted = sorted(leg, key=lambda o: abs(_strike(o) - spot))
    picks_raw = leg_sorted[:max(1, min(n, 10))]

    # fetch quotes for these option symbols to get bid/ask/mark
    syms = [o.get("symbol") for o in picks_raw if o.get("symbol")]
    qmap = fetch_option_quotes(syms)

    picks = []
    for o in picks_raw:
        sym = o.get("symbol")
        k = _strike(o)
        q = qmap.get(sym, {})
        bid = q.get("bid") if q.get("bid") not in (None, "na") else None
        ask = q.get("ask") if q.get("ask") not in (None, "na") else None
        last = q.get("last") if q.get("last") not in (None, "na") else None
        mark = None
        try:
            if bid is not None and ask is not None:
                mark = (float(bid) + float(ask)) / 2.0
            elif last is not None:
                mark = float(last)
        except Exception:
            mark = None
        spread_pct = None
        try:
            if bid is not None and ask is not None and mark and float(mark) > 0:
                spread_pct = (float(ask) - float(bid)) / float(mark)
        except Exception:
            spread_pct = None

        picks.append({
            "symbol": sym,
            "expiration": exp.isoformat(),
            "strike": float(k),
            "option_type": cp,
            "bid": float(bid) if bid is not None else None,
            "ask": float(ask) if ask is not None else None,
            "mark": float(mark) if mark is not None else None,
            "spread_pct": float(spread_pct) if spread_pct is not None else None,
            "open_interest": o.get("open_interest"),
            "volume": o.get("volume"),
        })

    return {
        "ok": True,
        "env": "tradier_sandbox",
        "note": "delayed options chain",
        "count_considered": len(picks),
        "picks": picks,
        "meta": {"spot": spot, "expiration": exp.isoformat(), "horizon": horizon, "side": side}
    }

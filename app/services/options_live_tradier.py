from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from app.services.tradier_client import TradierError, get

from .options_common import (
    Horizon,
    Side,
    choose_expiration_from_list,
    format_quote,
    nearest_strike_indices,
)


def _as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


# ---------- Underlying (delayed) ----------
async def fetch_spot(ticker: str) -> float:
    j = await get("markets/quotes", {"symbols": ticker.upper()})
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
async def fetch_expirations(ticker: str) -> List[date]:
    j = await get(
        "markets/options/expirations",
        {
            "symbol": ticker.upper(),
            "includeAllRoots": "true",
            "strikes": "false",
        },
    )
    exps = (j.get("expirations") or {}).get("date")
    datestr = _as_list(exps)
    out: List[date] = []
    for s in datestr:
        try:
            y, m, d = map(int, s.split("-"))
            out.append(date(y, m, d))
        except Exception:
            continue
    return sorted(out)


async def choose_expiration(ticker: str, horizon: Horizon) -> date:
    exps = await fetch_expirations(ticker)
    if not exps:
        raise TradierError(f"No expirations for {ticker}")
    return choose_expiration_from_list(exps, horizon)


# ---------- Chains & Quotes ----------
async def fetch_chain(ticker: str, exp: date) -> List[Dict[str, Any]]:
    j = await get(
        "markets/options/chains",
        {
            "symbol": ticker.upper(),
            "expiration": exp.isoformat(),
            # greeks=false keeps payload smaller; add &greeks=true later if needed
        },
    )
    opts = (j.get("options") or {}).get("option")
    return _as_list(opts)


async def fetch_option_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    if not symbols:
        return {}
    # Batch quote — Tradier accepts comma-separated up to large counts
    j = await get("markets/quotes", {"symbols": ",".join(symbols)})
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
async def pick_live_contracts(ticker: str, side: Side, horizon: Horizon, n: int = 5) -> Dict[str, Any]:
    cp = "call" if "call" in side else "put"
    spot = await fetch_spot(ticker)
    exp = await choose_expiration(ticker, horizon)
    chain = await fetch_chain(ticker, exp)
    if not chain:
        raise TradierError("No chain returned")

    leg = [o for o in chain if (o.get("option_type") or "").lower() == cp]
    if not leg:
        raise TradierError("No contracts for requested side")

    strikes: List[float] = []
    for o in leg:
        try:
            strikes.append(float(o.get("strike")))
        except Exception:
            strikes.append(float("inf"))
    idxs = nearest_strike_indices(strikes, spot, max(1, min(n, 10)))
    picks_raw = [leg[i] for i in idxs]

    syms = [o.get("symbol") for o in picks_raw if o.get("symbol")]
    qmap = await fetch_option_quotes(syms)

    picks = []
    for o in picks_raw:
        sym = o.get("symbol")
        k = o.get("strike")
        try:
            k = float(k) if k not in (None, "na") else None
        except Exception:
            k = None
        q = qmap.get(sym, {})
        bid = q.get("bid") if q.get("bid") not in (None, "na") else None
        ask = q.get("ask") if q.get("ask") not in (None, "na") else None
        last = q.get("last") if q.get("last") not in (None, "na") else None
        bid_f, ask_f, mark_f, spread_pct = format_quote(bid, ask, last)

        picks.append(
            {
                "symbol": sym,
                "expiration": exp.isoformat(),
                "strike": k,
                "option_type": cp,
                "bid": bid_f,
                "ask": ask_f,
                "mark": mark_f,
                "spread_pct": spread_pct,
                "open_interest": o.get("open_interest"),
                "volume": o.get("volume"),
            }
        )

    return {
        "ok": True,
        "env": "tradier_sandbox",
        "note": "delayed options chain",
        "count_considered": len(picks),
        "picks": picks,
        "meta": {"spot": spot, "expiration": exp.isoformat(), "horizon": horizon, "side": side},
    }

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from importlib import import_module as _im
from app.services.indicators import session_vwap_and_sigma, rvol_5min
from app.engine.regime import analyze as regime_analyze

router = APIRouter(prefix="/api/v1/market", tags=["market"])

PolygonMarket = None
try:
    PolygonMarket = getattr(_im("app.services.providers.polygon_market"), "PolygonMarket")
except Exception:
    PolygonMarket = None


async def _last(poly, sym: str) -> Optional[float]:
    try:
        lt = await poly.last_trade(sym)
        return float(lt.get("price")) if lt and lt.get("price") is not None else None
    except Exception:
        return None


async def _daily_change(poly, sym: str) -> Optional[float]:
    try:
        bars = await poly.daily_bars(sym, lookback=5)
        if len(bars) < 2:
            return None
        prev = bars[-2].get("c")
        cur = bars[-1].get("c")
        if prev:
            return round(((cur - prev)/prev)*100.0, 2)
    except Exception:
        return None
    return None


async def _intraday_metrics(poly, sym: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        mins = await poly.minute_bars_today(sym)
        vwap, sig = session_vwap_and_sigma(mins)
        out["vwap"] = vwap
        out["sigma_tp"] = sig
        out["rvol5"] = rvol_5min(mins)
        try:
            out["regime"] = regime_analyze(mins)
        except Exception:
            pass
    except Exception:
        pass
    return out


@router.get("/overview")
async def market_overview(
    indices: str = Query("SPY,QQQ"),
    sectors: str = Query("XLK,XLV,XLF,XLE,XLY,XLP,XLI,XLB,XLRE,XLU,XLC"),
) -> Dict[str, Any]:
    errors: Dict[str, str] = {}
    if not PolygonMarket:
        return {"ok": False, "error": "Polygon provider unavailable"}
    poly = PolygonMarket()

    idx_syms = [s.strip().upper() for s in indices.split(",") if s.strip()]
    sec_syms = [s.strip().upper() for s in sectors.split(",") if s.strip()]

    out_idx: Dict[str, Any] = {}
    out_sec: Dict[str, Any] = {}

    async def gather_for(sym: str) -> Dict[str, Any]:
        last, chg, intr = await asyncio.gather(_last(poly, sym), _daily_change(poly, sym), _intraday_metrics(poly, sym))
        d: Dict[str, Any] = {"last": last, "change_pct": chg}
        d.update({"intraday": intr})
        return d

    # Gather concurrently
    idx_results = await asyncio.gather(*[gather_for(s) for s in idx_syms], return_exceptions=True)
    for s, r in zip(idx_syms, idx_results):
        if isinstance(r, Exception):
            errors[s] = f"{type(r).__name__}: {r}"
        else:
            out_idx[s] = r

    sec_results = await asyncio.gather(*[gather_for(s) for s in sec_syms], return_exceptions=True)
    for s, r in zip(sec_syms, sec_results):
        if isinstance(r, Exception):
            errors[s] = f"{type(r).__name__}: {r}"
        else:
            out_sec[s] = r

    # Leaders by change pct (sectors)
    def _leaders(d: Dict[str, Any], top: int = 5):
        items = [(k, (v or {}).get("change_pct")) for k, v in d.items()]
        items = [(k, v) for k, v in items if isinstance(v, (int, float))]
        up = [k for k, _ in sorted(items, key=lambda x: x[1], reverse=True)[:top]]
        down = [k for k, _ in sorted(items, key=lambda x: x[1])[:top]]
        return {"up": up, "down": down}

    leaders = _leaders(out_sec)

    return {"ok": True, "indices": out_idx, "sectors": out_sec, "leaders": leaders, "errors": errors}


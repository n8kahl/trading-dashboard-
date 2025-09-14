from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query
from importlib import import_module as _im
from app.services.indicators import pivots_classic

router = APIRouter(prefix="/api/v1/market", tags=["market"])

PolygonMarket = None
try:
    PolygonMarket = getattr(_im("app.services.providers.polygon_market"), "PolygonMarket")
except Exception:
    PolygonMarket = None


@router.get("/bars")
async def bars(
    symbol: str,
    interval: str = Query("1m", pattern="^(1m|5m|1d)$"),
    lookback: int = 390,
) -> Dict[str, Any]:
    if not PolygonMarket:
        return {"ok": False, "error": "Polygon provider unavailable"}
    sym = (symbol or "").upper()
    poly = PolygonMarket()
    data: List[Dict[str, Any]] = []
    try:
        if interval == "1m":
            data = await poly.minute_bars_today(sym)
        elif interval == "5m":
            data = await poly.five_minute_bars_today(sym)
        else:
            # 1d
            data = await poly.daily_bars(sym, lookback=max(lookback, 30))
        if lookback and isinstance(lookback, int) and lookback > 0:
            data = data[-lookback:]
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "symbol": sym, "interval": interval, "bars": data}


@router.get("/levels")
async def levels(symbol: str) -> Dict[str, Any]:
    """Return previous day's OHLC and classic pivot levels for the symbol."""
    if not PolygonMarket:
        return {"ok": False, "error": "Polygon provider unavailable"}
    sym = (symbol or "").upper()
    poly = PolygonMarket()
    try:
        daily = await poly.daily_bars(sym, lookback=3)
        if len(daily) < 2:
            return {"ok": False, "error": "insufficient_daily"}
        prev = daily[-2]
        ohlc = {"o": prev.get("o"), "h": prev.get("h"), "l": prev.get("l"), "c": prev.get("c")}
        piv = pivots_classic(ohlc)
        return {"ok": True, "symbol": sym, "prev_day": ohlc, "pivots": piv}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

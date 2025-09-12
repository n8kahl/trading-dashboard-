from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.market import coerce_bars, fetch_polygon_daily
from app.services.market_status import freshness_from_bars, us_equity_market_open_now
from app.services.strategy_lib import evaluate_strategies

router = APIRouter(prefix="/premarket", tags=["premarket"])

DEFAULT_MARKET = ["SPY", "QQQ", "I:VIX"]


def _levels_from_last_bar(bars: List[dict]) -> Dict[str, float]:
    if not bars:
        return {}
    last = bars[-1]
    return {
        "prev_high": float(last.get("h", 0.0)),
        "prev_low": float(last.get("l", 0.0)),
        "prev_close": float(last.get("c", 0.0)),
    }


async def _eval_symbol_daily(symbol: str, lookback: int) -> Dict[str, Any]:
    bars = await fetch_polygon_daily(symbol, lookback=lookback)
    bars = coerce_bars(bars or [])
    if len(bars) < 50:
        return {"symbol": symbol, "error": "insufficient daily bars"}
    ev = evaluate_strategies(bars)
    ranked = sorted(ev["ranked"], key=lambda x: x["score"], reverse=True)
    best = ranked[0] if ranked else {}
    fresh = freshness_from_bars(bars)
    levels = _levels_from_last_bar(bars)
    return {
        "symbol": symbol,
        "best": best,
        "score": best.get("score"),
        "confluence": ev.get("confluence"),
        "levels": levels,
        "last_bar_time": fresh.get("last_bar_time"),
        "data_freshness": fresh,
    }


@router.post("/analysis")
async def premarket_analysis(body: Dict[str, Any]):
    """
    Body (optional):
      {
        "watchlist": ["AAPL","MSFT","NVDA"],
        "lookback": 90
      }
    """
    lookback = int(body.get("lookback", 90))
    watchlist = body.get("watchlist") or []

    # Indices / market context first
    market_ctx: List[Dict[str, Any]] = []
    for sym in DEFAULT_MARKET:
        market_ctx.append(await _eval_symbol_daily(sym, lookback=lookback))

    # Watchlist ranking (daily, synchronous)
    ranked: List[Dict[str, Any]] = []
    if watchlist:
        for sym in [str(s).upper() for s in watchlist]:
            res = await _eval_symbol_daily(sym, lookback=lookback)
            if "error" not in res:
                ranked.append(
                    {
                        "symbol": sym,
                        "score": res.get("score"),
                        "best": res.get("best"),
                        "last_bar_time": res.get("last_bar_time"),
                    }
                )
        ranked = sorted(ranked, key=lambda x: (x["score"] or 0), reverse=True)

    # Suggested alerts to consider at the open (client can call /alerts/set)
    # We base these on SPY previous day levels
    spy_ctx = next((r for r in market_ctx if r.get("symbol") == "SPY"), None) or {}
    lv = spy_ctx.get("levels") or {}
    suggested_alerts: List[Dict[str, Any]] = []
    if lv:
        if "prev_high" in lv:
            suggested_alerts.append(
                {
                    "symbol": "SPY",
                    "condition": {"type": "price_above", "value": lv["prev_high"]},
                    "note": "Breakout above yesterday's high",
                }
            )
        if "prev_low" in lv:
            suggested_alerts.append(
                {
                    "symbol": "SPY",
                    "condition": {"type": "price_below", "value": lv["prev_low"]},
                    "note": "Breakdown below yesterday's low",
                }
            )
        # VWAP cross is only meaningful intraday; still suggest template:
        suggested_alerts.append(
            {
                "symbol": "SPY",
                "condition": {"type": "cross_vwap_up"},
                "note": "Momentum confirmation intraday (VWAP cross up)",
            }
        )

    return JSONResponse(
        {
            "status": "ok",
            "data": {
                "market_open": us_equity_market_open_now(),
                "indices": market_ctx,
                "watchlist_ranked": ranked,
                "suggested_alerts": suggested_alerts,
            },
        }
    )


from fastapi import Query


@router.get("/analysis")
async def premarket_analysis_get(watchlist: str = Query(""), lookback: int = Query(90)):
    wl = [s.strip().upper() for s in watchlist.split(",") if s.strip()]
    return await premarket_analysis({"watchlist": wl, "lookback": lookback})

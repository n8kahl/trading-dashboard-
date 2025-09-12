from typing import Dict, Any, Optional
import datetime as dt
from zoneinfo import ZoneInfo
from app.config import MARKET_TZ, REG_OPEN_HOUR, REG_OPEN_MIN, REG_CLOSE_HOUR, REG_CLOSE_MIN

TZ = ZoneInfo(MARKET_TZ)

def us_equity_market_open_now(now: Optional[dt.datetime]=None) -> bool:
    now = now or dt.datetime.now(TZ)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    open_dt = now.replace(hour=REG_OPEN_HOUR, minute=REG_OPEN_MIN, second=0, microsecond=0)
    close_dt= now.replace(hour=REG_CLOSE_HOUR, minute=REG_CLOSE_MIN, second=0, microsecond=0)
    return open_dt <= now <= close_dt

def freshness_from_bars(bars: list) -> Dict[str, Any]:
    """
    bars: list of dicts with 't' epoch ms or ISO time; returns last_bar_time_iso and lag seconds.
    """
    if not bars:
        return {"last_bar_time": None, "data_lag_seconds": None}
    t = bars[-1].get("t")
    if t is None:
        return {"last_bar_time": None, "data_lag_seconds": None}
    if isinstance(t, (int, float)):
        last = dt.datetime.fromtimestamp(float(t)/1000.0, tz=TZ)
    else:
        try:
            last = dt.datetime.fromisoformat(str(t)).astimezone(TZ)
        except Exception:
            return {"last_bar_time": None, "data_lag_seconds": None}
    now = dt.datetime.now(TZ)
    lag = (now - last).total_seconds()
    return {"last_bar_time": last.isoformat(), "data_lag_seconds": max(0, int(lag))}

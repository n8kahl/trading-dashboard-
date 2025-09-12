from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Literal, Tuple
from dateutil.tz import UTC

Side = Literal["long_call","long_put","short_call","short_put"]
Horizon = Literal["intra","day","week"]

def _today_utc() -> date:
    """Return today's date in UTC."""
    return datetime.now(tz=UTC).date()

def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5

def _next_weekday(d: date) -> date:
    while _is_weekend(d):
        d += timedelta(days=1)
    return d

def expiration_window(horizon: Horizon) -> Tuple[int, int]:
    """Return (min_dte, max_dte) target window for a horizon."""
    return (0, 2) if horizon in ("intra", "day") else (3, 10)

def choose_expiration_from_list(
    expirations: Iterable[date], horizon: Horizon, *, today: date | None = None
) -> date:
    """Pick an expiration date from a sorted iterable based on horizon."""
    today = today or _today_utc()
    exps = sorted(expirations)
    if not exps:
        raise ValueError("No expirations provided")
    min_dte, max_dte = expiration_window(horizon)
    for exp in exps:
        dte = (exp - today).days
        if min_dte <= dte <= max_dte:
            return exp
    for exp in exps:
        if exp >= today:
            return exp
    return exps[-1]

def nearest_strike_indices(strikes: List[float], spot: float, take: int) -> List[int]:
    """Return indices of strikes closest to spot."""
    indexed = list(enumerate(strikes))
    ranked = sorted(indexed, key=lambda it: (abs(it[1] - spot), it[1]))
    return [i for i, _ in ranked[:take]]

def format_quote(
    bid: Any, ask: Any, last: Any = None
) -> Dict[str, float | None]:
    """Normalize bid/ask/last into floats and derive mark and spread pct."""
    bid_f = float(bid) if bid not in (None, "na") else None
    ask_f = float(ask) if ask not in (None, "na") else None
    last_f = float(last) if last not in (None, "na") else None
    mark = None
    if bid_f is not None and ask_f is not None:
        mark = (bid_f + ask_f) / 2.0
    elif last_f is not None:
        mark = last_f
    spread_pct = None
    if bid_f is not None and ask_f is not None and mark and mark > 0:
        spread_pct = (ask_f - bid_f) / mark
    return {"bid": bid_f, "ask": ask_f, "mark": mark, "spread_pct": spread_pct}

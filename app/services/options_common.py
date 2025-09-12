from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable, List, Literal, Optional, Tuple

from dateutil.tz import UTC

# Shared literals used by options helpers
Side = Literal["long_call", "long_put", "short_call", "short_put"]
Horizon = Literal["intra", "day", "week"]


def _today_utc() -> date:
    """Return today's date in UTC."""
    return datetime.now(tz=UTC).date()


def expiration_window(horizon: Horizon) -> Tuple[int, int]:
    """Return (min_dte, max_dte) window for an expiration horizon."""
    if horizon in ("intra", "day"):
        return 0, 2
    return 3, 10


def choose_expiration_from_list(exps: Iterable[date], horizon: Horizon) -> date:
    """Select an expiration from a list based on horizon."""
    today = _today_utc()
    min_dte, max_dte = expiration_window(horizon)
    exps_sorted = sorted(exps)
    window = {today + timedelta(days=d) for d in range(min_dte, max_dte + 1)}
    for e in exps_sorted:
        if e in window:
            return e
    for e in exps_sorted:
        if e >= today:
            return e
    return exps_sorted[-1]


def nearest_strike_indices(strikes: List[float], spot: float, take: int) -> List[int]:
    """Return indices of strikes closest to spot."""
    indexed = list(enumerate(strikes))
    ranked = sorted(indexed, key=lambda it: (abs(it[1] - spot), it[1]))
    return [i for i, _ in ranked[:take]]


def format_quote(
    bid: Optional[float],
    ask: Optional[float],
    last: Optional[float] = None,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Normalize option quote fields and compute mark/spread."""
    mark: Optional[float] = None
    if bid is not None and ask is not None:
        try:
            mark = (float(bid) + float(ask)) / 2.0
        except Exception:
            mark = None
    elif last is not None:
        try:
            mark = float(last)
        except Exception:
            mark = None
    spread_pct: Optional[float] = None
    try:
        if mark and bid is not None and ask is not None and mark > 0:
            spread_pct = (float(ask) - float(bid)) / float(mark)
    except Exception:
        spread_pct = None
    return (
        float(bid) if bid is not None else None,
        float(ask) if ask is not None else None,
        mark,
        spread_pct,
    )

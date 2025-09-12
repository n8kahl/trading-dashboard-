from typing import List, Dict, Any
from app.services.stream import STREAM
from app.services.strategy_lib import evaluate_strategies, apply_power_hour_bias
from app.routers.strategies import _is_power_hour_ct  # reuse

def rank_from_snapshot(symbols: List[str], n_bars: int = 120, timeframe: str = "minute") -> List[Dict[str, Any]]:
    """
    Pull latest bars for symbols from the STREAM snapshot and rank by strategy score.
    """
    symbols = [s.upper() for s in symbols or []]
    snap = STREAM  # singleton
    # we will call STREAM.snapshot() from router to avoid async here
    raise NotImplementedError("Call via router which handles async snapshot")

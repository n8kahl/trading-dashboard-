from math import isfinite
from typing import Any


def _safe_num(x: Any) -> Any:
    if isinstance(x, (int, float)):
        return x if (isinstance(x, int) or isfinite(x)) else None
    return x


def jsonsafe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: jsonsafe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonsafe(v) for v in obj]
    return _safe_num(obj)

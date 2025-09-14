from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict

_windows: Dict[str, Deque[float]] = {}


def allow(key: str, limit: int, window_sec: int) -> bool:
    """Return True if the request is within the sliding window limit.

    Sliding window implementation: store event times and evict older than window.
    """
    now = time.monotonic()
    dq = _windows.get(key)
    if dq is None:
        dq = deque()
        _windows[key] = dq
    # Evict old timestamps
    cutoff = now - window_sec
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= max(0, limit):
        return False
    dq.append(now)
    return True


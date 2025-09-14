from __future__ import annotations

import os, asyncio, time
from typing import Dict


class RateLimiter:
    """Simple async token-bucket limiter for in-process rate limiting.

    rate: tokens per second
    capacity: max burst tokens (defaults to 2x rate)
    """

    def __init__(self, rate: float, capacity: float | None = None):
        self.rate = max(0.1, float(rate))
        self.capacity = float(capacity if capacity is not None else max(1.0, self.rate * 2.0))
        self._tokens = self.capacity
        self._ts = time.monotonic()
        self._lock = asyncio.Lock()

    async def wait(self, cost: float = 1.0) -> None:
        cost = max(0.0, float(cost))
        async with self._lock:
            while True:
                now = time.monotonic()
                # Refill tokens
                delta = now - self._ts
                self._ts = now
                self._tokens = min(self.capacity, self._tokens + delta * self.rate)
                if self._tokens >= cost:
                    self._tokens -= cost
                    return
                # sleep for remaining time needed to earn tokens
                need = (cost - self._tokens) / self.rate
                await asyncio.sleep(max(0.0, need))


_LIMITERS: Dict[str, RateLimiter] = {}


def _get_rate(env_names: list[str], default_rate: float) -> float:
    for name in env_names:
        v = os.getenv(name)
        if v:
            try:
                return float(v)
            except Exception:
                continue
    return default_rate


def get_polygon_limiter() -> RateLimiter:
    # Prefer POLYGON_API_RATE, fall back to POLL_API_RATE, default 5 rps
    rate = _get_rate(["POLYGON_API_RATE", "POLL_API_RATE"], 5.0)
    key = f"polygon:{rate}"
    rl = _LIMITERS.get(key)
    if rl is None:
        rl = RateLimiter(rate)
        _LIMITERS[key] = rl
    return rl


def get_tradier_limiter() -> RateLimiter:
    # Prefer TRADIER_API_RATE, fall back to POLL_API_RATE, default 3 rps
    rate = _get_rate(["TRADIER_API_RATE", "POLL_API_RATE"], 3.0)
    key = f"tradier:{rate}"
    rl = _LIMITERS.get(key)
    if rl is None:
        rl = RateLimiter(rate)
        _LIMITERS[key] = rl
    return rl


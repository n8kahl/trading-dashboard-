import asyncio
from contextlib import contextmanager
from typing import Awaitable, Callable, Optional

from app.db import db_session


class RateLimiter:
    """Simple async context manager for rate limiting."""

    def __init__(self, max_calls: int, period: float = 1.0) -> None:
        self._semaphore = asyncio.Semaphore(max_calls)
        self._period = period

    async def __aenter__(self) -> None:
        await self._semaphore.acquire()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await asyncio.sleep(self._period)
        self._semaphore.release()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    with db_session() as session:
        yield session


async def run_periodic(
    fn: Callable[[], Awaitable[None]],
    interval: float,
    *,
    on_error: Optional[Callable[[Exception], None]] = None,
    loop_forever: bool = True,
) -> None:
    """Run ``fn`` periodically with basic error handling."""
    while True:
        try:
            await fn()
        except Exception as e:  # pragma: no cover - protective wrapper
            if on_error:
                on_error(e)
        if not loop_forever:
            break
        await asyncio.sleep(interval)

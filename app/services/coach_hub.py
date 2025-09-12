from __future__ import annotations

import asyncio
from typing import Set


class CoachHub:
    """In-memory pub/sub for coach events (WS/SSE broadcast)."""

    def __init__(self) -> None:
        self._listeners: Set[asyncio.Queue[str]] = set()

    async def publish(self, msg: str) -> None:
        for q in list(self._listeners):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                # drop for slow consumers
                pass

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self._listeners.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._listeners.discard(q)


hub = CoachHub()

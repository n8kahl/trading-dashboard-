from __future__ import annotations

from typing import Optional

import httpx


async def send_message(webhook_url: Optional[str], content: str) -> bool:
    if not webhook_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(webhook_url, json={"content": content})
            r.raise_for_status()
        return True
    except Exception:
        return False


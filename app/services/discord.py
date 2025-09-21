from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Coroutine, Dict

import httpx

logger = logging.getLogger("app.discord")


def is_configured() -> bool:
    return bool(os.getenv("DISCORD_WEBHOOK_URL"))


async def _post(payload: Dict[str, Any]) -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - best effort only
        logger.warning("Failed to send Discord notification: %s", exc)


def _fire_and_forget(coro: Coroutine[Any, Any, None]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)  # type: ignore[arg-type]
    except RuntimeError:
        # No running loop (synchronous context) — run blocking
        asyncio.run(coro)


async def send_trade_notification(trade: Dict[str, Any]) -> None:
    """Send a lightweight trade alert."""

    symbol = trade.get("symbol", "?")
    side = str(trade.get("side", "")).upper()
    qty = trade.get("quantity")

    avg_val = None
    pnl_val = None
    try:
        avg_val = float(trade.get("avg_price")) if trade.get("avg_price") is not None else None
    except (TypeError, ValueError):
        avg_val = None
    try:
        pnl_val = float(trade.get("pnl")) if trade.get("pnl") is not None else None
    except (TypeError, ValueError):
        pnl_val = None

    qty_str = f" {qty}" if qty is not None else ""
    parts = [f"📈 {side}{qty_str} {symbol}"]
    if avg_val is not None:
        parts.append(f"@ {avg_val:.2f}")
    if pnl_val is not None:
        pnl_prefix = "+" if pnl_val >= 0 else ""
        parts.append(f"PnL {pnl_prefix}{pnl_val:.2f}")

    content = " ".join(parts).strip() or "📈 Trade recorded"
    if context := trade.get("context"):
        try:
            context_str = json.dumps(context, default=str)[:1800]
        except TypeError:
            context_str = str(context)[:1800]
        payload = {"content": content, "embeds": [{"description": context_str}]}
    else:
        payload = {"content": content}

    await _post(payload)


async def send_log_notification(log: Dict[str, Any]) -> None:
    """Push an error/critical log to Discord."""

    level = str(log.get("level", "")).upper()
    source = log.get("source") or "app"
    message = log.get("message") or "(no message)"
    description = message[:1800]
    fields = []
    if payload := log.get("payload"):
        fields.append({"name": "Payload", "value": str(payload)[:900], "inline": False})

    body = {
        "embeds": [
            {
                "title": f"{level} – {source}",
                "description": description,
                "color": 0xE53935 if level == "CRITICAL" else 0xFB8C00,
                "fields": fields,
            }
        ]
    }
    await _post(body)


def notify_trade(trade: Dict[str, Any]) -> None:
    if not is_configured():
        return
    _fire_and_forget(send_trade_notification(trade))


def notify_log(log: Dict[str, Any]) -> None:
    if not is_configured():
        return
    _fire_and_forget(send_log_notification(log))

import asyncio
import base64
import hashlib
import hmac
import json
import time
import logging
import os
from typing import List, Optional, Tuple

from fastapi import WebSocket, WebSocketDisconnect

WS_PING_SEC = int(os.getenv("WS_PING_SEC", "20"))


class WSManager:
    """Minimal WebSocket connection manager."""

    def __init__(self) -> None:
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast_json(self, data: dict) -> None:
        for ws in list(self.connections):
            try:
                await ws.send_json(data)
            except Exception as exc:
                logging.exception("broadcast_json failed", exc_info=exc)
                self.disconnect(ws)

    async def ping_task(self) -> None:
        try:
            while True:
                await asyncio.sleep(WS_PING_SEC)
                for ws in list(self.connections):
                    try:
                        await ws.send_json({"type": "ping"})
                    except Exception as exc:
                        logging.exception("ping_task send failed", exc_info=exc)
                        self.disconnect(ws)
        except asyncio.CancelledError:
            logging.info("ping_task cancelled")


manager = WSManager()


def _verify_ws_token(token: str) -> bool:
    secret = (os.getenv("WS_SECRET") or "dev-secret").encode()
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        payload_raw, sig = raw.rsplit(b".", 1)
        expected = hmac.new(secret, payload_raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return False
        data = json.loads(payload_raw.decode("utf-8"))
        if int(data.get("exp", 0)) < int(time.time()):  # type: ignore[name-defined]
            return False
        return True
    except Exception:
        return False


async def websocket_endpoint(ws: WebSocket) -> None:
    # Prefer JWT-like ws token if provided; else fall back to api_key param
    token = ws.query_params.get("token")
    if token and _verify_ws_token(token):
        pass
    else:
        expected_key = (os.getenv("API_KEY") or "").strip()
        if expected_key:
            api_key = ws.query_params.get("api_key")
            if api_key != expected_key:
                await ws.close(code=1008)
                return
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def start_ws() -> None:
    asyncio.create_task(manager.ping_task())

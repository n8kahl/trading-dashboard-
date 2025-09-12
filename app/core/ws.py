import asyncio
import logging
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from app.security import API_KEY
import os

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

async def websocket_endpoint(ws: WebSocket) -> None:
    if API_KEY:
        token = ws.query_params.get("api_key")
        if token != API_KEY:
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

import asyncio
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.core.ws import WSManager


class FailingWebSocket:
    async def send_json(self, data):
        raise RuntimeError("fail")

def test_broadcast_json_disconnects_and_logs(caplog):
    manager = WSManager()
    ws = FailingWebSocket()
    manager.connections.append(ws)
    with caplog.at_level(logging.ERROR):
        asyncio.run(manager.broadcast_json({"a": 1}))
    assert ws not in manager.connections
    assert "broadcast_json failed" in caplog.text


def test_ping_task_handles_drop_and_cancel(monkeypatch, caplog):
    manager = WSManager()
    ws = FailingWebSocket()
    manager.connections.append(ws)

    monkeypatch.setattr("app.core.ws.WS_PING_SEC", 0.01)

    async def runner():
        task = asyncio.create_task(manager.ping_task())
        await asyncio.sleep(0.02)
        assert ws not in manager.connections
        task.cancel()
        await task

    with caplog.at_level(logging.ERROR):
        asyncio.run(runner())
    assert "ping_task send failed" in caplog.text

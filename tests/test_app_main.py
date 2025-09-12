import os
import importlib
import pytest
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    os.environ["API_KEY"] = "secret"
    import app.security as security
    import app.core.ws as ws
    import app.main as main
    importlib.reload(security)
    importlib.reload(ws)
    importlib.reload(main)

    async def _noop():
        pass

    monkeypatch.setattr(main, "start_ws", _noop)
    monkeypatch.setattr(main, "start_risk_engine", _noop)

    return TestClient(main.app)


def test_router_mounted(client):
    r = client.get("/api/v1/diag/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_websocket_endpoint_auth_success(client):
    with client.websocket_connect("/ws?api_key=secret") as ws:
        ws.send_text("hello")


def test_websocket_endpoint_auth_fail(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?api_key=bad"):
            pass

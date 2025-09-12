from fastapi.testclient import TestClient

from app.main import app
from app.routers import options


def test_options_pick_injects_client(monkeypatch):
    monkeypatch.setattr(options, "TRADIER_ACCESS_TOKEN", "token")

    class DummyClient:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    mock_client = DummyClient()

    async def override_client():
        try:
            yield mock_client
        finally:
            await mock_client.close()

    app.dependency_overrides[options.get_tradier_client] = override_client

    async def fake_pick(client, symbol, side, horizon, n):
        assert client is mock_client
        return options.OptionsPickResponse(ok=True, env="test", count_considered=0, picks=[], source="tradier")

    monkeypatch.setattr(options, "_pick_from_tradier", fake_pick)

    with TestClient(app) as test_client:
        resp = test_client.post("/api/v1/options/pick", json={"symbol": "AAPL", "side": "long_call"})
        assert resp.status_code == 200
        assert mock_client.closed is True

    app.dependency_overrides.clear()

import asyncio
import importlib
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_order_preview(monkeypatch):
    monkeypatch.setenv("TRADIER_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TRADIER_ACCOUNT_ID", "acct")
    import app.integrations.tradier as tradier

    importlib.reload(tradier)
    TradierClient = tradier.TradierClient
    DEFAULT_HEADERS = tradier.DEFAULT_HEADERS

    expected = {"order": {"id": "p123"}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/accounts/acct/orders"
        body = parse_qs(request.content.decode())
        assert body["preview"] == ["true"]
        assert body["symbol"] == ["AAPL"]
        return httpx.Response(200, json=expected)

    transport = httpx.MockTransport(handler)

    async def mock_session(self):
        return httpx.AsyncClient(transport=transport, base_url=self.base, headers=DEFAULT_HEADERS)

    monkeypatch.setattr(TradierClient, "_session", mock_session, raising=False)

    client = TradierClient()
    result = asyncio.run(client.order_preview_or_place(account_id=None, params={"symbol": "AAPL"}, preview=True))
    assert result == expected


def test_order_place(monkeypatch):
    monkeypatch.setenv("TRADIER_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TRADIER_ACCOUNT_ID", "acct")
    import app.integrations.tradier as tradier

    importlib.reload(tradier)
    TradierClient = tradier.TradierClient
    DEFAULT_HEADERS = tradier.DEFAULT_HEADERS

    expected = {"order": {"id": "o456"}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/accounts/acct/orders"
        body = parse_qs(request.content.decode())
        assert "preview" not in body
        assert body["symbol"] == ["AAPL"]
        return httpx.Response(200, json=expected)

    transport = httpx.MockTransport(handler)

    async def mock_session(self):
        return httpx.AsyncClient(transport=transport, base_url=self.base, headers=DEFAULT_HEADERS)

    monkeypatch.setattr(TradierClient, "_session", mock_session, raising=False)

    client = TradierClient()
    result = asyncio.run(client.order_preview_or_place(account_id=None, params={"symbol": "AAPL"}, preview=False))
    assert result == expected

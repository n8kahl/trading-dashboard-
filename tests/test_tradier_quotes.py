import asyncio
import importlib
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_get_quotes(monkeypatch):
    monkeypatch.setenv("TRADIER_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TRADIER_ACCOUNT_ID", "acct")
    import app.integrations.tradier as tradier

    importlib.reload(tradier)
    TradierClient = tradier.TradierClient
    DEFAULT_HEADERS = tradier.DEFAULT_HEADERS

    expected = {"quotes": {"quote": {"symbol": "AAPL", "last": 123.45}}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/markets/quotes"
        assert request.url.params["symbols"] == "AAPL"
        return httpx.Response(200, json=expected)

    transport = httpx.MockTransport(handler)

    async def mock_session(self):
        return httpx.AsyncClient(transport=transport, base_url=self.base, headers=DEFAULT_HEADERS)

    monkeypatch.setattr(TradierClient, "_session", mock_session, raising=False)

    client = TradierClient()
    result = asyncio.run(client.get_quotes(["AAPL"]))
    assert result == expected

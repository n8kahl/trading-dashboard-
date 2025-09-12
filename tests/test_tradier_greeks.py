import asyncio
import importlib
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_get_option_greeks(monkeypatch):
    monkeypatch.setenv("TRADIER_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TRADIER_ACCOUNT_ID", "acct")
    import app.integrations.tradier as tradier

    importlib.reload(tradier)
    TradierClient = tradier.TradierClient
    DEFAULT_HEADERS = tradier.DEFAULT_HEADERS

    opt_symbol = "AAPL241220C00150000"
    expected = {"quotes": {"quote": {"symbol": opt_symbol, "greeks": {"delta": 0.1}}}}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/markets/options/quotes"
        params = request.url.params
        assert params["symbols"] == opt_symbol
        assert params["greeks"] == "true"
        return httpx.Response(200, json=expected)

    transport = httpx.MockTransport(handler)

    async def mock_session(self):
        return httpx.AsyncClient(transport=transport, base_url=self.base, headers=DEFAULT_HEADERS)

    monkeypatch.setattr(TradierClient, "_session", mock_session, raising=False)

    client = TradierClient()
    result = asyncio.run(client.get_quotes([opt_symbol], greeks=True))
    quote = result["quotes"]["quote"]
    assert quote["symbol"] == opt_symbol
    assert quote["greeks"]["delta"] == 0.1

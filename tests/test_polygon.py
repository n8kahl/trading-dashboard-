from pathlib import Path
import sys, importlib, asyncio
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_last_quote(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test")
    import app.services.polygon as polygon
    importlib.reload(polygon)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/last/trade/AAPL"
        return httpx.Response(200, json={"results": {"p": 123.4, "t": 169}})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        polygon,
        "_client",
        lambda: httpx.AsyncClient(transport=transport, base_url="https://api.polygon.io"),
    )

    result = asyncio.run(polygon.last_quote("AAPL"))
    assert result == {"ok": True, "symbol": "AAPL", "last": 123.4, "ts": 169}

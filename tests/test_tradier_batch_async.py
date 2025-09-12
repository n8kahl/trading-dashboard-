import asyncio
import time
import httpx

from app.services import tradier
from app.core.settings import settings


class DummyResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"quotes": {"quote": {"symbol": "OPT"}}}


class DummyClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get(self, *args, **kwargs):
        await asyncio.sleep(0.05)
        return DummyResponse()


def test_tradier_batch_option_quotes_async(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", DummyClient)
    monkeypatch.setattr(settings, "TRADIER_ACCESS_TOKEN", "token")

    async def run():
        start = time.perf_counter()
        result, _ = await asyncio.gather(
            tradier.tradier_batch_option_quotes(["OPT"]),
            asyncio.sleep(0.05),
        )
        elapsed = time.perf_counter() - start
        return result, elapsed

    result, elapsed = asyncio.run(run())
    assert result == {"OPT": {"symbol": "OPT"}}
    assert elapsed < 0.09

import sys, asyncio, importlib
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_alerts_poller(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "x")
    import types
    sys.modules["psycopg2"] = types.SimpleNamespace(connect=lambda *a, **k: None)
    import app.services.poller as poller
    importlib.reload(poller)

    async def fake_price(symbol, timeframe):
        assert symbol == "AAPL"
        return 105.0

    monkeypatch.setattr(poller, "_latest_price", fake_price)

    calls: Dict[str, Any] = {}

    def fake_list_active():
        return [{"id": 1, "symbol": "AAPL", "timeframe": "day", "condition": {"type": "price_above", "value": 100}}]

    def fake_mark_triggered(alert_id: int):
        calls["mark"] = alert_id

    def fake_add_trigger(alert_id: int, symbol: str, payload: dict):
        calls.setdefault("triggers", []).append((alert_id, symbol, payload))

    monkeypatch.setattr(poller.alerts_store, "list_active", fake_list_active)
    monkeypatch.setattr(poller.alerts_store, "mark_triggered", fake_mark_triggered)
    monkeypatch.setattr(poller.alerts_store, "add_trigger", fake_add_trigger)

    asyncio.run(poller.alerts_poller(loop_forever=False))
    assert calls["mark"] == 1
    assert calls["triggers"][0][1] == "AAPL"


def test_monitor_loop(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "x")
    import types
    db_pkg = types.ModuleType("app.db")
    db_pkg.__path__ = []
    sys.modules["app.db"] = db_pkg
    sys.modules["app.db.models"] = types.ModuleType("app.db.models")
    db_mod = types.ModuleType("app.db.db")
    db_mod.SessionLocal = lambda: None
    sys.modules["app.db.db"] = db_mod

    import app.services.monitor as monitor
    importlib.reload(monitor)

    async def fake_price(symbol):
        return 115.0

    monkeypatch.setattr(monitor, "last_price", fake_price)

    async def fake_check(db):
        px = await monitor.last_price("AAPL")
        if px >= 110:
            print("TP hit")

    monkeypatch.setattr(monitor, "check_trades_once", fake_check)

    class DummySession:
        def __enter__(self):
            return object()
        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(monitor, "SessionLocal", lambda: DummySession())

    import builtins
    logs = []
    monkeypatch.setattr(builtins, "print", lambda *a, **k: logs.append(" ".join(str(x) for x in a)))

    async def stop_sleep(_):
        raise RuntimeError("stop")

    monkeypatch.setattr(monitor.asyncio, "sleep", stop_sleep)

    try:
        asyncio.run(monitor.monitor_loop(interval_sec=0))
    except RuntimeError:
        pass

    assert any("TP hit" in m for m in logs)

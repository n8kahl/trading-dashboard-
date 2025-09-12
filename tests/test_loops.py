from pathlib import Path
import sys, asyncio, importlib
from contextlib import contextmanager
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_alerts_poller(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "x")
    import app.services.poller as poller
    importlib.reload(poller)

    async def fake_price(symbol, timeframe):
        assert symbol == "AAPL"
        return 105.0

    monkeypatch.setattr(poller, "_latest_price", fake_price)

    class DummyResult:
        def __init__(self, rows):
            self.rows = rows
        def fetchall(self):
            return self.rows

    class DummyDB:
        def __init__(self):
            self.queries = []
        def execute(self, query, params=None):
            self.queries.append((query, params))
            if query.startswith("SELECT id, symbol"):
                return DummyResult([(1, "AAPL", "day", '{"type":"price_above","value":100}', True)])
            return DummyResult([])

    holder = {}
    @contextmanager
    def dummy_db_session():
        db = DummyDB()
        holder["db"] = db
        yield db

    monkeypatch.setattr(poller, "db_session", dummy_db_session)

    asyncio.run(poller.alerts_poller(loop_forever=False))
    q = "".join(holder["db"].queries[-1][0:1])
    assert "UPDATE alerts SET triggered_at" in q


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

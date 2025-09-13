import os
import sys
import importlib
import tempfile

from fastapi.testclient import TestClient


def make_client():
    # point to a temporary sqlite db file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    # Import after env set; ensure we load the real module (not a prior test stub)
    if 'app.db' in sys.modules:
        del sys.modules['app.db']
    from app.db import init_db
    from app.main import app

    init_db()
    return TestClient(app)


def test_settings_crud():
    c = make_client()
    r = c.get("/api/v1/settings/get")
    assert r.status_code == 200
    assert r.json()["ok"]
    payload = {
        "risk_daily_r": 3.0,
        "risk_per_trade_r": 0.5,
        "risk_max_concurrent": 4,
        "rr_default": "1:5",
        "auto_execute_sandbox": False,
        "top_symbols": "SPY,QQQ,AAPL,NVDA,MSFT,TSLA,META",
    }
    r2 = c.post("/api/v1/settings/set", json=payload)
    assert r2.status_code == 200
    r3 = c.get("/api/v1/settings/get")
    s = r3.json()["settings"]
    for k, v in payload.items():
        assert s[k] == v


def test_journal_crud():
    c = make_client()
    # create
    r = c.post("/api/v1/journal/create", json={"symbol": "SPY", "notes": "Test entry"})
    assert r.status_code == 200
    jid = r.json()["id"]
    # list
    r2 = c.get("/api/v1/journal/list?symbol=SPY")
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert any(it["id"] == jid for it in items)
    # update
    r3 = c.post(f"/api/v1/journal/update/{jid}", json={"r": 0.4, "side": "long"})
    assert r3.status_code == 200
    # delete
    r4 = c.post(f"/api/v1/journal/delete/{jid}")
    assert r4.status_code == 200
    r5 = c.get("/api/v1/journal/list?symbol=SPY")
    ids = [it["id"] for it in r5.json()["items"]]
    assert jid not in ids

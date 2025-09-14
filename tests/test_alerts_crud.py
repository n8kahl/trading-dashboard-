import os
import tempfile

from fastapi.testclient import TestClient


def make_client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    from app.db import init_db
    from app.main import app

    init_db()
    return TestClient(app)


def test_alerts_crud_flow():
    c = make_client()
    # create
    body = {"symbol": "SPY", "timeframe": "day", "condition": {"type": "price_above", "value": 100.0}}
    r = c.post("/api/v1/alerts/set", json=body)
    assert r.status_code == 200
    aid = r.json()["id"]
    # list
    r2 = c.get("/api/v1/alerts/list")
    assert r2.status_code == 200
    items = r2.json().get("items") or []
    assert any(it.get("id") == aid for it in items)
    # delete
    r3 = c.post(f"/api/v1/alerts/delete/{aid}")
    assert r3.status_code == 200
    r4 = c.get("/api/v1/alerts/list")
    ids = [it.get("id") for it in r4.json().get("items") or []]
    assert aid not in ids


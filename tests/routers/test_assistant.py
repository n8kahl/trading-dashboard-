from pathlib import Path
import sys
from fastapi.testclient import TestClient

# Ensure the application package is importable
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from app.main import app  # noqa: E402

client = TestClient(app)

def test_assistant_actions_returns_actions():
    response = client.get("/api/v1/assistant/actions")
    assert response.status_code == 200
    data = response.json()
    assert data.get("ok") is True
    actions = data.get("actions")
    assert isinstance(actions, list) and len(actions) > 0
    first = actions[0]
    for key in ("op", "title", "description", "args_schema", "id"):
        assert key in first


def test_assistant_exec_dispatches_valid_op(monkeypatch):
    from app.routers import assistant_simple

    captured = {}

    async def stub(payload):
        captured["payload"] = payload
        return {"ok": True, "handled": True}

    monkeypatch.setitem(assistant_simple.EXEC_HANDLERS, "options.pick", stub)

    response = client.post(
        "/api/v1/assistant/exec", json={"op": "options.pick", "args": {"symbol": "AAPL"}}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "handled": True}
    assert captured["payload"] == {"symbol": "AAPL"}


def test_assistant_exec_unknown_op():
    response = client.post("/api/v1/assistant/exec", json={"op": "does.not.exist"})
    assert response.status_code == 400
    detail = response.json().get("detail")
    assert detail.get("error") == "unknown_op"
    assert detail.get("op") == "does.not.exist"


def test_assistant_exec_does_not_share_args_between_requests(monkeypatch):
    from app.routers import assistant_simple

    captured_payloads = []

    async def stub(payload):
        captured_payloads.append(dict(payload))
        payload["mutated"] = True
        return {"ok": True}

    monkeypatch.setitem(assistant_simple.EXEC_HANDLERS, "options.pick", stub)

    first = client.post("/api/v1/assistant/exec", json={"op": "options.pick"})
    assert first.status_code == 200
    second = client.post("/api/v1/assistant/exec", json={"op": "options.pick"})
    assert second.status_code == 200

    assert captured_payloads == [{}, {}]

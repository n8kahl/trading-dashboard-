from pathlib import Path
import sys, asyncio, importlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


def test_daily_risk_breach(monkeypatch):
    import app.core.risk as risk
    importlib.reload(risk)

    monkeypatch.setattr(risk, "RISK_MAX_DAILY_R", 2.0)
    monkeypatch.setattr(risk, "RISK_MAX_CONCURRENT", 10)

    async def fake_positions():
        return {"items": []}

    async def fake_orders(status: str = "filled"):
        return {"items": [{"risk_r": 1.5}, {"risk_r": 1.0}]}

    monkeypatch.setattr(risk.tradier, "get_positions", fake_positions)
    monkeypatch.setattr(risk.tradier, "get_orders", fake_orders)

    engine = risk.RiskEngine()
    asyncio.run(engine.refresh())

    assert engine.state["daily_r"] == 2.5
    assert engine.state["breach_daily_r"] is True
    assert engine.state["breach_concurrent"] is False


def test_concurrent_breach(monkeypatch):
    import app.core.risk as risk
    importlib.reload(risk)

    monkeypatch.setattr(risk, "RISK_MAX_DAILY_R", 10.0)
    monkeypatch.setattr(risk, "RISK_MAX_CONCURRENT", 1)

    async def fake_positions():
        return {"items": [{}, {}]}

    async def fake_orders(status: str = "filled"):
        return {"items": []}

    monkeypatch.setattr(risk.tradier, "get_positions", fake_positions)
    monkeypatch.setattr(risk.tradier, "get_orders", fake_orders)

    engine = risk.RiskEngine()
    asyncio.run(engine.refresh())

    assert engine.state["concurrent"] == 2
    assert engine.state["breach_concurrent"] is True
    assert engine.state["breach_daily_r"] is False


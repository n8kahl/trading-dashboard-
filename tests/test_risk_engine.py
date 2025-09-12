import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.services.risk_engine import assess_risk


def test_assess_risk_unfavorable(monkeypatch):
    res = assess_risk(
        "strat",
        context={},
        analysis={"band": "unfavorable", "score": 80},
        plan={"entry_hint": 10, "stop_loss": 9},
    )
    assert res["band"] == "unfavorable"
    assert "band_unfavorable" in res["block_reasons"]
    assert res["max_size_hint"] == 500  # per_unit_risk 1 -> 500 units


def test_assess_risk_favorable_low_score(monkeypatch):
    res = assess_risk(
        "strat",
        context={},
        analysis={"band": "favorable", "score": 40},
        plan={"entry_hint": 10, "stop_loss": 9},
    )
    assert res["band"] == "favorable"
    assert res["block_reasons"] == []
    assert any("Score 40" in note for note in res["notes"])

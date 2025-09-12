import asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.paper import PaperPosition
from app.services import providers
from app.services.paper_engine import SubmitIntent, submit
from app.services.risk_engine import assess_risk


def test_trading_workflow(monkeypatch):
    async def mock_price(symbol: str, client=None):
        return 100.0

    monkeypatch.setattr(providers, "get_last_price", mock_price)

    price = asyncio.run(providers.get_last_price("AAPL"))
    risk = assess_risk(
        "strat",
        context={},
        analysis={"band": "favorable", "score": 90},
        plan={"entry_hint": price, "stop_loss": price - 1},
    )
    assert risk["block_reasons"] == []

    engine = create_engine("sqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    with Session() as db:
        intent = SubmitIntent(symbol="AAPL", side="buy", qty=1, entry_px=price)
        res = submit(db, intent)
        assert res["ok"] is True
        pos = db.execute(select(PaperPosition).where(PaperPosition.symbol == "AAPL")).scalar_one()
        assert pos.qty == 1

from datetime import UTC
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.paper import PaperTrade
from app.services.paper_engine import _daily_loss_r


def test_daily_loss_r_counts_today_only():
    engine = create_engine("sqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    with Session() as db:
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        db.add(PaperTrade(symbol="AAPL", side="sell", qty=1, close_time=now, outcome_r=-1.5))
        db.add(PaperTrade(symbol="AAPL", side="sell", qty=1, close_time=yesterday, outcome_r=-2.0))
        db.commit()
        assert _daily_loss_r(db) == -1.5

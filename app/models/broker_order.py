from __future__ import annotations

import datetime as dt
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BrokerOrder(Base):
    __tablename__ = "broker_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(sa.DateTime, default=dt.datetime.utcnow, index=True)

    # Request fields
    symbol: Mapped[str] = mapped_column(sa.String(16), index=True)
    side: Mapped[str] = mapped_column(sa.String(8))  # buy/sell
    quantity: Mapped[int] = mapped_column(sa.Integer)
    order_type: Mapped[str] = mapped_column(sa.String(16))  # market/limit
    limit_price: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    duration: Mapped[Optional[str]] = mapped_column(sa.String(8), nullable=True)
    bracket_stop: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    bracket_target: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    preview: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    # Correlation + outcome
    request_id: Mapped[Optional[str]] = mapped_column(sa.String(32), nullable=True, index=True)
    status: Mapped[Optional[str]] = mapped_column(sa.String(32), nullable=True)
    broker_response: Mapped[Optional[dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)


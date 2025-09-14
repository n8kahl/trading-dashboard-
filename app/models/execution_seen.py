from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ExecutionSeen(Base):
    __tablename__ = "executions_seen"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(sa.DateTime, default=dt.datetime.utcnow, index=True)
    key: Mapped[str] = mapped_column(sa.String(200), unique=True, index=True)


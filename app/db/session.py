from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import Base


def _coerce_async_driver(url: str) -> str:
    """Ensure PostgreSQL URLs use the asyncpg driver."""

    lowered = url.lower()

    if lowered.startswith("postgresql+asyncpg://"):
        return url
    if lowered.startswith("sqlite"):
        return url

    if lowered.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.split("://", 1)[1]
    if lowered.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.split("://", 1)[1]
    if lowered.startswith("postgresql+psycopg://"):
        return "postgresql+asyncpg://" + url.split("://", 1)[1]
    if lowered.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + url.split("://", 1)[1]

    return url


def _database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return _coerce_async_driver(explicit)

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB", "trader")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

    if user and password:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    # Local fallback for quick experiments
    return "sqlite+aiosqlite:///./local.db"


DATABASE_URL = _database_url()

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create tables on startup."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

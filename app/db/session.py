from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Dict, Tuple

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import Base


def _sslmode_to_asyncpg(value: str | None) -> Tuple[bool | None, bool]:
    if not value:
        return None, False
    mode = value.strip().lower()
    if mode in {"require", "verify-full", "verify-ca"}:
        return True, True
    if mode in {"disable"}:
        return False, True
    # allow/prefer fall back to default behaviour (no explicit ssl arg)
    return None, False


def _normalize_url(url: str) -> Tuple[str, Dict[str, Any]]:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    connect_args: Dict[str, Any] = {}

    if scheme.startswith("postgres"):
        target_scheme = "postgresql+asyncpg"
    elif scheme.startswith("postgresql+psycopg"):
        target_scheme = "postgresql+asyncpg"
    else:
        return url, connect_args

    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_pairs = []
    for key, val in query_pairs:
        if key.lower() == "sslmode":
            ssl_flag, should_set = _sslmode_to_asyncpg(val)
            if should_set:
                connect_args["ssl"] = ssl_flag
            # drop sslmode from query either way
            continue
        filtered_pairs.append((key, val))

    new_query = urlencode(filtered_pairs, doseq=True)
    normalized = urlunparse(parsed._replace(scheme=target_scheme, query=new_query))
    return normalized, connect_args


def _database_config() -> Tuple[str, Dict[str, Any]]:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return _normalize_url(explicit)

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB", "trader")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

    if user and password:
        url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        sslmode = os.getenv("POSTGRES_SSLMODE")
        connect_args: Dict[str, Any] = {}
        ssl_flag, should_set = _sslmode_to_asyncpg(sslmode)
        if should_set:
            connect_args["ssl"] = ssl_flag
        return url, connect_args

    # Local fallback for quick experiments
    return "sqlite+aiosqlite:///./local.db", {}


DATABASE_URL, _CONNECT_ARGS = _database_config()

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args=_CONNECT_ARGS,
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

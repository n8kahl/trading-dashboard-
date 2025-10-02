from __future__ import annotations

import os
import ssl
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import Base


def _load_cert_chain(ctx: ssl.SSLContext, cert_path: Optional[str], key_path: Optional[str]) -> None:
    if cert_path:
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path or None)


def _build_ssl_connect_args(mode: Optional[str], params: Dict[str, Optional[str]]) -> Dict[str, Any]:
    mode_norm = (mode or "").strip().lower()
    cert_path = params.get("sslcert")
    key_path = params.get("sslkey")
    root_path = params.get("sslrootcert")

    def _create_default_context() -> ssl.SSLContext:
        if root_path:
            return ssl.create_default_context(cafile=root_path)
        return ssl.create_default_context()

    if mode_norm == "disable":
        return {"ssl": False}

    if mode_norm in ("", "allow", "prefer") and not (cert_path or key_path or root_path):
        return {}

    ctx: Optional[ssl.SSLContext] = None

    if mode_norm == "require":
        ctx = _create_default_context()
        # Mimic libpq require semantics (no verification by default)
        if not root_path:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
    elif mode_norm == "verify-ca":
        ctx = _create_default_context()
        ctx.check_hostname = False
    elif mode_norm == "verify-full":
        ctx = _create_default_context()
        ctx.check_hostname = True
    else:
        # Unknown or unspecified mode but custom certs provided -> use default context without hostname checks
        if cert_path or key_path or root_path:
            ctx = _create_default_context()
            ctx.check_hostname = False
        elif mode_norm in ("", "allow", "prefer"):
            return {}

    if ctx is not None:
        _load_cert_chain(ctx, cert_path, key_path)
        return {"ssl": ctx}

    # Fallback: let asyncpg negotiate and just require TLS
    return {"ssl": True}


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
    ssl_params: Dict[str, Optional[str]] = {"sslmode": None, "sslrootcert": None, "sslcert": None, "sslkey": None}
    for key, val in query_pairs:
        low = key.lower()
        if low in ssl_params:
            ssl_params[low] = val or None
            continue
        filtered_pairs.append((key, val))

    new_query = urlencode(filtered_pairs, doseq=True)
    normalized = urlunparse(parsed._replace(scheme=target_scheme, query=new_query))
    ssl_args = _build_ssl_connect_args(ssl_params["sslmode"], ssl_params)
    connect_args.update(ssl_args)
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
        ssl_params = {
            "sslmode": os.getenv("POSTGRES_SSLMODE"),
            "sslrootcert": os.getenv("POSTGRES_SSLROOTCERT"),
            "sslcert": os.getenv("POSTGRES_SSLCERT"),
            "sslkey": os.getenv("POSTGRES_SSLKEY"),
        }
        connect_args = _build_ssl_connect_args(ssl_params["sslmode"], ssl_params)
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

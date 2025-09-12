from __future__ import annotations
import os, psycopg

def _norm_dsn(raw: str|None) -> str|None:
    if not raw:
        return None
    # SQLAlchemy-style DSN -> psycopg3-native
    return raw.replace("postgresql+psycopg2://", "postgresql://")

def connect():
    dsn = _norm_dsn(os.getenv("DATABASE_URL"))
    if not dsn:
        raise RuntimeError("DATABASE_URL missing")
    return psycopg.connect(dsn)

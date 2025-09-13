from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

def normalized_db_url() -> str:
    v = os.environ.get("DATABASE_URL", "").strip().strip('"').strip("'")
    if v.startswith("DATABASE_URL="):
        v = v.split("=", 1)[1]  # tolerate mis-set values like "DATABASE_URL=postgresql+psycopg://..."
    if not v:
        # fall back to an in-memory SQLite database for tests and simple usage
        return "sqlite+pysqlite:///:memory:"
    return v

ENGINE = create_engine(normalized_db_url(), future=True)
SessionLocal = sessionmaker(bind=ENGINE, expire_on_commit=False)


@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

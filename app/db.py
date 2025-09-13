import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

# Module-level engine/session with lazy (re)initialization to support tests that
# set DATABASE_URL after imports or manipulate sys.modules.
engine = None
SessionLocal = None


def _ensure_engine():
    global engine, SessionLocal
    if engine is not None and SessionLocal is not None:
        return
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return
    engine = create_engine(url, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db():
    _ensure_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL not configured")
    Base.metadata.create_all(bind=engine)


@contextmanager
def db_session():
    _ensure_engine()
    if SessionLocal is None:
        # Yield None for callers to handle gracefully
        yield None
        return
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

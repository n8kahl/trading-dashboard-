import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    # Allow app to boot even if DB not configured; routers should handle None
    engine = None
    SessionLocal = None
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db():
    if engine is None:
        raise RuntimeError("DATABASE_URL not configured")
    Base.metadata.create_all(bind=engine)


@contextmanager
def db_session():
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

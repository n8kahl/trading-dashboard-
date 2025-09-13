from __future__ import annotations
import os
from sqlalchemy import create_engine

def normalized_db_url() -> str:
    v = os.environ.get("DATABASE_URL", "").strip().strip('"').strip("'")
    if v.startswith("DATABASE_URL="):
        v = v.split("=", 1)[1]  # tolerate mis-set values like "DATABASE_URL=postgresql+psycopg://..."
    if not v:
        raise RuntimeError("DATABASE_URL is empty after normalization")
    return v

ENGINE = create_engine(normalized_db_url(), future=True)

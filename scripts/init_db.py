import os, sys
from pathlib import Path
from sqlalchemy import create_engine, inspect

# ensure repo root on sys.path so "app.*" works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.base import Base  # <-- your Base lives here

db_url = os.environ.get("DATABASE_URL")
assert db_url and "://" in db_url and "<" not in db_url, (
    "Set a REAL DATABASE_URL (from Railway → Postgres → Connect). "
    "It should look like: postgresql+psycopg://USER:PASS@HOST:PORT/DB?sslmode=require"
)

engine = create_engine(db_url, pool_pre_ping=True)

# create tables
Base.metadata.create_all(engine)

# show what exists now
insp = inspect(engine)
print("Tables:", insp.get_table_names())

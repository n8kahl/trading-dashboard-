import os
from sqlalchemy import create_engine, text, inspect

db = os.environ["DATABASE_URL"]
engine = create_engine(db, pool_pre_ping=True)

with engine.connect() as conn:
    print("SELECT 1 ->", conn.execute(text("SELECT 1")).scalar())

insp = inspect(engine)
print("Tables:", insp.get_table_names())

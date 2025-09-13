import os
from sqlalchemy import create_engine
from app.db.models import Base  # adjust if your Base lives elsewhere

db_url = os.environ.get("DATABASE_URL")
assert db_url, "Set DATABASE_URL"
engine = create_engine(db_url, pool_pre_ping=True)
Base.metadata.create_all(engine)
print("Tables created.")

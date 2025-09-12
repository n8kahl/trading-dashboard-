import json
import os
from typing import List, Optional

import psycopg2

DB_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("PG_URL")


def _conn():
    return psycopg2.connect(DB_URL)


def init():
    if not DB_URL:
        return
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
          id SERIAL PRIMARY KEY,
          symbols TEXT NOT NULL,
          updated_at TIMESTAMP DEFAULT NOW()
        );
        """)
        c.commit()


def save(symbols: List[str]):
    if not DB_URL:
        return
    with _conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM watchlist;")
        cur.execute("INSERT INTO watchlist(symbols) VALUES (%s);", (json.dumps(symbols),))
        c.commit()


def load() -> Optional[List[str]]:
    if not DB_URL:
        return None
    with _conn() as c, c.cursor() as cur:
        cur.execute("SELECT symbols FROM watchlist ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
        return json.loads(row[0]) if row and row[0] else None

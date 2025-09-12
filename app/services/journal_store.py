import os, psycopg2, json
from typing import Optional, List, Dict
from datetime import datetime

DB_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("PG_URL")

def _conn():
    return psycopg2.connect(DB_URL)

def init():
    if not DB_URL: return
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS journal_trades (
          id SERIAL PRIMARY KEY,
          ts TIMESTAMP DEFAULT NOW(),
          symbol TEXT NOT NULL,
          side TEXT,
          entry NUMERIC,
          stop NUMERIC,
          tp1 NUMERIC,
          tp2 NUMERIC,
          exit_price NUMERIC,
          result_r NUMERIC,
          notes TEXT
        );
        """)
        c.commit()

def add(trade: Dict):
    if not DB_URL: return
    fields = ("symbol","side","entry","stop","tp1","tp2","exit_price","result_r","notes")
    vals = [trade.get(k) for k in fields]
    with _conn() as c, c.cursor() as cur:
        cur.execute(f"""
        INSERT INTO journal_trades({",".join(fields)})
        VALUES ({",".join(["%s"]*len(fields))});
        """, vals)
        c.commit()

def summary(days: int = 30) -> Dict:
    if not DB_URL: return {"note":"no db configured"}
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN result_r>0 THEN 1 ELSE 0 END),
               AVG(COALESCE(result_r,0)),
               MAX(COALESCE(result_r,0)),
               MIN(COALESCE(result_r,0))
        FROM journal_trades
        WHERE ts >= NOW() - INTERVAL '%s days';
        """, (days,))
        n, wins, avg_r, best, worst = cur.fetchone()
        return {
            "trades": n or 0,
            "wins": wins or 0,
            "win_rate": round((wins or 0)/(n or 1), 3) if n else 0.0,
            "avg_R": float(avg_r or 0.0),
            "best_R": float(best or 0.0),
            "worst_R": float(worst or 0.0)
        }

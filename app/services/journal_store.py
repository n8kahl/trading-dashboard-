import os, psycopg2, json, logging
from psycopg2.pool import SimpleConnectionPool
from typing import Optional, Dict

DB_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("PG_URL")
logger = logging.getLogger(__name__)
pool: Optional[SimpleConnectionPool] = None

def _get_pool() -> Optional[SimpleConnectionPool]:
    global pool
    if pool is None and DB_URL:
        pool = SimpleConnectionPool(1, 5, dsn=DB_URL)
    return pool

def init():
    if not DB_URL: return
    p = _get_pool()
    conn = None
    try:
        conn = p.getconn()
        with conn.cursor() as cur:
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
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Failed to initialize journal_trades table")
    finally:
        if conn:
            p.putconn(conn)

def add(trade: Dict):
    if not DB_URL: return
    fields = ("symbol","side","entry","stop","tp1","tp2","exit_price","result_r","notes")
    vals = [trade.get(k) for k in fields]
    p = _get_pool()
    conn = None
    try:
        conn = p.getconn()
        with conn.cursor() as cur:
            cur.execute(f"""
            INSERT INTO journal_trades({",".join(fields)})
            VALUES ({",".join(["%s"]*len(fields))});
            """, vals)
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Failed to add trade")
    finally:
        if conn:
            p.putconn(conn)

def summary(days: int = 30) -> Dict:
    if not DB_URL: return {"note":"no db configured"}
    p = _get_pool()
    conn = None
    try:
        conn = p.getconn()
        with conn.cursor() as cur:
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
    except Exception:
        logger.exception("Failed to generate trade summary")
        return {}
    finally:
        if conn:
            p.putconn(conn)

import json
import os
from typing import Any, Dict, List, Optional

import psycopg2

DB_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("PG_URL")


def _conn():
    return psycopg2.connect(DB_URL)


def init():
    if not DB_URL:
        return
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
          id SERIAL PRIMARY KEY,
          symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT 'minute',
          condition JSONB NOT NULL,
          active BOOLEAN NOT NULL DEFAULT TRUE,
          expires_at TIMESTAMP NULL,
          last_triggered_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_triggers (
          id SERIAL PRIMARY KEY,
          alert_id INTEGER REFERENCES alerts(id) ON DELETE CASCADE,
          symbol TEXT NOT NULL,
          fired_at TIMESTAMP NOT NULL DEFAULT NOW(),
          payload JSONB
        );
        """)
        c.commit()


def add(symbol: str, timeframe: str, condition: Dict[str, Any], expires_at: Optional[str]) -> int:
    if not DB_URL:
        return 0
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO alerts(symbol,timeframe,condition,expires_at) VALUES (%s,%s,%s,%s) RETURNING id;",
            (symbol.upper(), timeframe, json.dumps(condition), expires_at),
        )
        _id = cur.fetchone()[0]
        c.commit()
        return int(_id)


def list_active() -> List[Dict[str, Any]]:
    if not DB_URL:
        return []
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        SELECT id, symbol, timeframe, condition, active, expires_at, last_triggered_at, created_at
        FROM alerts
        WHERE active = TRUE AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY id;
        """)
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "symbol": r[1],
                    "timeframe": r[2],
                    "condition": r[3],
                    "active": r[4],
                    "expires_at": r[5].isoformat() if r[5] else None,
                    "last_triggered_at": r[6].isoformat() if r[6] else None,
                    "created_at": r[7].isoformat() if r[7] else None,
                }
            )
        return out


def list_by_symbol(symbol: str) -> List[Dict[str, Any]]:
    if not DB_URL:
        return []
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            """
        SELECT id, symbol, timeframe, condition, active, expires_at, last_triggered_at, created_at
        FROM alerts
        WHERE symbol = %s
        ORDER BY id;
        """,
            (symbol.upper(),),
        )
        return [
            {
                "id": r[0],
                "symbol": r[1],
                "timeframe": r[2],
                "condition": r[3],
                "active": r[4],
                "expires_at": r[5].isoformat() if r[5] else None,
                "last_triggered_at": r[6].isoformat() if r[6] else None,
                "created_at": r[7].isoformat() if r[7] else None,
            }
            for r in cur.fetchall()
        ]


def delete(alert_id: int) -> bool:
    if not DB_URL:
        return True
    with _conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM alerts WHERE id=%s;", (alert_id,))
        c.commit()
        return cur.rowcount > 0


def set_inactive(alert_id: int):
    if not DB_URL:
        return
    with _conn() as c, c.cursor() as cur:
        cur.execute("UPDATE alerts SET active=FALSE WHERE id=%s;", (alert_id,))
        c.commit()


def mark_triggered(alert_id: int):
    if not DB_URL:
        return
    with _conn() as c, c.cursor() as cur:
        cur.execute("UPDATE alerts SET last_triggered_at = NOW() WHERE id=%s;", (alert_id,))
        c.commit()


def add_trigger(alert_id: int, symbol: str, payload: Dict[str, Any]):
    if not DB_URL:
        return
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO alert_triggers(alert_id,symbol,payload) VALUES (%s,%s,%s);",
            (alert_id, symbol.upper(), json.dumps(payload)),
        )
        c.commit()


def recent_triggers(limit: int = 50) -> List[Dict[str, Any]]:
    if not DB_URL:
        return []
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            """
        SELECT t.id, t.alert_id, a.symbol, t.fired_at, t.payload
        FROM alert_triggers t LEFT JOIN alerts a ON a.id=t.alert_id
        ORDER BY t.id DESC
        LIMIT %s;
        """,
            (limit,),
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            payload = r[4] or {}
            out.append(
                {
                    "id": r[0],
                    "alert_id": r[1],
                    "symbol": r[2],
                    "fired_at": r[3].isoformat() if r[3] else None,
                    "payload": payload,
                }
            )
        return out

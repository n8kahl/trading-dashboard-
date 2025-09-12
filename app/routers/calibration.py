from fastapi import APIRouter, Query
from typing import Dict, Any, List, Optional
import psycopg, os

# Use the same DB normalization you added in app/services/db.py
from app.services.db import connect

router = APIRouter(prefix="/calibration", tags=["calibration"])

@router.get("/ping")
def ping():
    return {"ok": True, "calibration": "ready"}

@router.get("/summary")
def summary(symbol: Optional[str] = Query(default=None),
           bins: int = Query(default=5, ge=2, le=10),
           session: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """
    Summarize decision_artifacts by score bins.
    Optional filters: symbol, session (features->>'session').
    """
    try:
        edges = [0, 20, 40, 60, 80, 100] if bins == 5 else [int(100*i/bins) for i in range(bins+1)]
        out: List[Dict[str, Any]] = []
        where = "context='strategies.evaluate' AND score IS NOT NULL"
        params: List[Any] = []
        if symbol:
            where += " AND symbol=%s"
            params.append(symbol.upper())
        if session:
            where += " AND (features->>'session')=%s"
            params.append(session)

        q = f"SELECT COUNT(*), AVG(score) FROM decision_artifacts WHERE {where} AND score >= %s AND score < %s"

        with connect() as conn, conn.cursor() as cur:
            for i in range(len(edges)-1):
                lo, hi = edges[i], edges[i+1]
                cur.execute(q, (*params, lo, hi))
                n, avg = cur.fetchone()
                out.append({
                    "bin": f"[{lo},{hi})",
                    "n": int(n or 0),
                    "avg_score": float(avg) if avg is not None else None
                })
        return {"ok": True, "bins": out, "filters": {"symbol": symbol, "session": session}, "bins_count": bins}
    except Exception as e:
        return {"ok": False, "error": str(e)}

from __future__ import annotations

from typing import Any, Optional

from app.services.db import connect


async def insert_decision_artifact(
    context: str,
    symbol: str,
    horizon: str,
    score: Optional[float],
    data_status: Optional[str],
    provider: Optional[str],
    features: Any,
    rationale: Any,
    suggestion: Any,
) -> None:
    # best-effort; swallow errors (logging is non-blocking for API)
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO decision_artifacts
                (context, symbol, horizon, score, data_status, provider, features, rationale, suggestion)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
            """,
                (
                    context,
                    symbol,
                    horizon,
                    score,
                    data_status,
                    provider,
                    (features if features is not None else None),
                    (rationale if rationale is not None else None),
                    (suggestion if suggestion is not None else None),
                ),
            )
            conn.commit()
    except Exception:
        # intentionally ignore to not affect API latency
        pass

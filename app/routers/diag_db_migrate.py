from fastapi import APIRouter
from starlette.responses import JSONResponse
from sqlalchemy import text
from app.db import db_session

router = APIRouter(prefix="/diag/db", tags=["diag-db"])

@router.post("/migrate")
def migrate_alerts_table():
    """
    Normalize the alerts table so code and DB agree:
      - ensure column is_active exists (BOOLEAN DEFAULT TRUE)
      - rename legacy column active -> is_active if present
      - ensure column triggered_at exists (TIMESTAMP NULL)
      - create helpful indexes
    """
    try:
        with db_session() as db:
            if db is None:
                return JSONResponse({"ok": False, "error": "DB not configured"}, status_code=503)

            # 1) If table doesn't exist, create it fresh to spec
            db.execute(text("""
            DO $$
            BEGIN
              IF to_regclass('public.alerts') IS NULL THEN
                CREATE TABLE public.alerts (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(32) NOT NULL,
                    timeframe VARCHAR(16) NOT NULL,
                    condition TEXT NOT NULL,
                    expires_at TIMESTAMP NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    triggered_at TIMESTAMP NULL
                );
              END IF;
            END$$;
            """))

            # 2) Rename legacy 'active' -> 'is_active' if needed
            db.execute(text("""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='alerts' AND column_name='active'
              ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='alerts' AND column_name='is_active'
              ) THEN
                ALTER TABLE alerts RENAME COLUMN active TO is_active;
              END IF;
            END$$;
            """))

            # 3) Ensure is_active exists
            db.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;"))

            # 4) Ensure triggered_at exists
            db.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS triggered_at TIMESTAMP NULL;"))

            # 5) Helpful indexes
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_symbol ON alerts(symbol);"))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_is_active ON alerts(is_active);"))

            return {"ok": True, "migrated": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

#!/usr/bin/env bash
set -euo pipefail

# Echo environment summary (no secrets)
echo "[boot] PORT=${PORT:-8080} ENVIRONMENT=${ENVIRONMENT:-dev} TRADIER_ENV=${TRADIER_ENV:-unset} RUN_POLLER=${RUN_POLLER:-0}"

# DB migrations (safe if no migrations)
if [ -f "alembic.ini" ]; then
  echo "[boot] running alembic upgrade head"
  alembic upgrade head || echo "[boot] warning: alembic upgrade failed (continuing)"
fi

# Start uvicorn on the correct PORT
export PORT="${PORT:-8080}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"

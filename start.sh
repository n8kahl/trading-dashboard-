#!/usr/bin/env bash
set -euo pipefail

# Load .env if present (useful locally)
if [ -f ./.env ]; then
  set -a
  . ./.env
  set +a
fi

: "${DATABASE_URL:?DATABASE_URL is required}"

# Apply DB migrations (no-op if already up-to-date)
alembic upgrade head || true

# Launch the app
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"

#!/usr/bin/env sh
set -eu

echo "[start.sh] CWD=$(pwd)"
echo "[start.sh] PORT=${PORT:-8000}"
echo "[start.sh] SAFE_MODE=${SAFE_MODE:-0}"

# show what's inside /app for sanity
ls -la /app || true

echo "[start.sh] Launching app on :${PORT:-8000}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-https://tradingassistantmcpready-production.up.railway.app}"

echo "== Smoke: $BASE =="
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/")
echo "/ -> $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/diag/health")
echo "/api/v1/diag/health -> $code"
curl -s "$BASE/api/v1/diag/health" | jq .

# only try routes listing if your diag router exposes it:
if curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/diag/routes" | grep -q '^200$'; then
  echo "/api/v1/diag/routes -> 200"
  curl -s "$BASE/api/v1/diag/routes" | jq -r '.routes[]? | "\(.method)\t\(.path)"'
else
  echo "/api/v1/diag/routes -> (not present) skipping"
fi

# screener endpoints (should not 502 or 404 if present)
if curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/screener/watchlist/get" | grep -q '^200$'; then
  echo "/api/v1/screener/watchlist/get -> 200"
  curl -s "$BASE/api/v1/screener/watchlist/get" | jq .
fi

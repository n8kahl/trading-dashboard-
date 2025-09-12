#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-https://tradingassistantmcpready-production.up.railway.app}"

# jq pretty-printer fallback
pp() {
  if command -v jq >/dev/null 2>&1; then jq .; else cat; fi
}

echo "== Base =="
echo "$BASE"

echo "== Health =="
curl -s "$BASE/api/v1/diag/health" | pp

echo "== Assistant: list actions =="
curl -s "$BASE/api/v1/assistant/actions" | pp

echo "== Assistant: options.pick (nested args) SPY calls =="
curl -s -X POST "$BASE/api/v1/assistant/exec" \
  -H "content-type: application/json" \
  -d '{"op":"options.pick","args":{"symbol":"SPY","side":"long_call","horizon":"intra","n":3}}' | pp

echo "== Assistant: options.pick (nested args) AAPL puts =="
curl -s -X POST "$BASE/api/v1/assistant/exec" \
  -H "content-type: application/json" \
  -d '{"op":"options.pick","args":{"symbol":"AAPL","side":"long_put","horizon":"day","n":3}}' | pp

echo "== Direct: options/pick (SPY calls) =="
curl -s -X POST "$BASE/api/v1/options/pick" \
  -H "content-type: application/json" \
  -d '{"symbol":"SPY","side":"long_call","horizon":"intra","n":3}' | pp

echo "== Screener: watchlist get =="
curl -s "$BASE/api/v1/screener/watchlist/get" | pp || true

echo "== Plan: validate (AAPL long) =="
curl -s -X POST "$BASE/api/v1/plan/validate" \
  -H "content-type: application/json" \
  -d '{"symbol":"AAPL","side":"long","entry":231.90,"stop":230.78,"tp1":233.02,"tp2":234.10,"time_stop_min":10}' | pp

echo "== Sizing: suggest (with entry/stop) =="
curl -s -X POST "$BASE/api/v1/sizing/suggest" \
  -H "content-type: application/json" \
  -d '{"symbol":"AAPL","side":"long","risk_R":1.0,"entry":231.90,"stop":230.78}' | pp

echo "== DONE =="

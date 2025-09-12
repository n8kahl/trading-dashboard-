#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
pp(){ if command -v jq >/dev/null 2>&1; then jq .; else cat; fi }

echo "== Broker positions =="
curl -s "$BASE/api/v1/broker/positions" | pp

echo "== Broker orders =="
curl -s "$BASE/api/v1/broker/orders" | pp

echo "== Auto execute preview =="
curl -s -X POST "$BASE/api/v1/auto/execute" \
  -H "content-type: application/json" \
  -d '{"symbol":"SPY","side":"buy","entry":1,"stop":0.5,"risk_R":1,"confirm":false}' | pp

echo "== Auto execute confirm =="
curl -s -X POST "$BASE/api/v1/auto/execute" \
  -H "content-type: application/json" \
  -d '{"symbol":"SPY","side":"buy","entry":1,"stop":0.5,"risk_R":1,"confirm":true}' | pp || true

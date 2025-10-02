# Usage Guide

This app serves a FastAPI backend for day-trading workflows, plus a lightweight interactive chart. Use this guide to validate symbols, generate hedge ideas, and visualize plans.

## Environment

Required
- `POLYGON_API_KEY`

Optional
- `TRADIER_ACCESS_TOKEN` or `TRADIER_API_KEY` (quotes, fallback options chain)
- `TRADIER_ENV` = `sandbox`|`prod`
- `POLYGON_API_RATE`, `TRADIER_API_RATE` (RPS rate limiting)
- `PUBLIC_BASE_URL` (absolute base used in `chart_url` links)

## Endpoints

- `GET /api/v1/assistant/actions`
  - Returns available ops and provider flags.

- `POST /api/v1/assistant/exec`
  - Single action router for Chat-Data: body `{ "op": <name>, "args": { ... } }`.
  - Primary ops: `diag.health`, `diag.providers`, `assistant.actions`, `market.overview`, `assistant.hedge`.
    - `diag.*` ops report health/provider readiness.
    - `assistant.actions` lists supported ops plus provider/import diagnostics.
    - `market.overview` accepts `{ indices?: string[], sectors?: string[] }` and returns macro context.
    - `assistant.hedge` accepts `{ objective, horizon?, constraints?, positions[] }` and returns hedge plans.
  - Legacy op: `data.snapshot` (same payload as before) continues to return rich symbol snapshots with options picks, EM, risk flags, and strategy scaffolding.
    - Include `options` to fetch shortlists (and optional 0DTE strategies). `options.odte: true` keeps expiry on today with tighter spread caps.

- `POST /api/v1/trades`, `GET /api/v1/trades`
  - Persist executions with symbol, side, qty, price, optional PnL/tags/context. List endpoint supports `symbol`, `since`, `limit` filters.

- `POST /api/v1/features`, `GET /api/v1/features`
  - Store derived feature payloads (JSON) keyed by symbol + horizon. List endpoint supports symbol/horizon filters.

- `POST /api/v1/logs`, `GET /api/v1/logs`
  - Structured logging sink. Post `level`, `source`, `message`, optional payload. Errors/criticals trigger Discord alerts when `DISCORD_WEBHOOK_URL` is configured.

- `POST /api/v1/assistant/hedge`
  - Body: `{ objective, horizon, positions: [{symbol, type, side, strike?, expiry?, qty, avg_price?}] }`
  - Returns net Greeks and suggestions (cap naked shorts into verticals, protective puts for stock) with NBBO on protective legs.

- `GET /api/v1/market/overview`
  - Optional macro snapshot for indices and sector ETFs (you may prefer web for macro headlines).

- `GET /api/v1/market/bars`
  - `symbol`, `interval`=`1m|5m|1d`, `lookback`
  - JSON OHLCV for client-side charts.

- `GET /api/v1/market/levels`
  - Prior-day OHLC and classic P/R/S pivots for labeling.

- `GET /charts/proposal`
  - Interactive, beginner-friendly chart.
  - Query params:
    - Required: `symbol`
    - Common: `interval`=`1m|5m|1d`, `lookback`
    - Plan and annotations: `entry`, `sl`, `tp1`, `tp2`, `direction=long|short`
    - Context: `overlays=vwap,ema20,ema50,pivots`, `em_abs`, `em_rel`, `hit_tp1`, `hit_tp2`, `confluence=csv`
    - Optional: `entry_time` (ms since epoch), `plan` (pipe-delimited bullets)
  - UI:
    - Timeframe selector, Fit, Refresh
    - Strategy Plan panel with current state (relative to VWAP), step-by-step entry, targets from EM, probabilities, and risk guidance.
    - Auto-fallback to 5m → 1d if 1m is empty; clear error messages if the chart lib or data fails.

## Example Requests

Diag health via single action:
```
curl -s -X POST $BASE/api/v1/assistant/exec \
 -H 'Content-Type: application/json' \
 -d '{"op":"diag.health","args":{}}'
```

Market overview (custom indices/sectors):
```
curl -s -X POST $BASE/api/v1/assistant/exec \
 -H 'Content-Type: application/json' \
 -d '{"op":"market.overview","args":{"indices":["SPY","QQQ"],"sectors":["XLK","XLV","XLF","XLE","XLI","XLY","XLP","XLU","XLRE","XLB"]}}'
```

Legacy snapshot (SPY intraday with options):
```
curl -s -X POST $BASE/api/v1/assistant/exec \
 -H 'Content-Type: application/json' \
 -d '{"op":"data.snapshot","args":{"symbols":["SPY"],"horizon":"intraday","include":["options"],"options":{"expiry":"auto","topK":8,"maxSpreadPct":12,"greeks":true}}}'
```

Hedge through the single action (cap a naked short + protective put):
```
curl -s -X POST $BASE/api/v1/assistant/exec \
 -H 'Content-Type: application/json' \
 -d '{"op":"assistant.hedge","args":{"objective":"cap_loss","horizon":"intraday","positions":[{"symbol":"AAPL","type":"call","side":"short","strike":210,"expiry":"2025-09-20","qty":1},{"symbol":"AAPL","type":"stock","side":"long","qty":100}]}}'
```

Chart (TSLA, intraday plan):
```
https://your-host/charts/proposal?symbol=TSLA&interval=1m&overlays=vwap,ema20,ema50,pivots&entry=395.9&sl=393.3&tp1=398.6&tp2=401.2&direction=long&em_abs=2.5&hit_tp1=0.68&hit_tp2=0.42
```

Record a filled trade (optional Discord ping):
```
curl -s -X POST $BASE/api/v1/trades \
 -H 'Content-Type: application/json' \
 -d '{"symbol":"SPY","side":"buy","quantity":2,"avg_price":445.12,"pnl":15.8,"tags":["opening drive"],"context":{"strategy":"scalp","horizon":"intraday"}}'
```

Push a structured error log (fires Discord when level=error|critical):
```
curl -s -X POST $BASE/api/v1/logs \
 -H 'Content-Type: application/json' \
 -d '{"level":"error","source":"nbbo_sampler","message":"Polygon timeout","payload":{"symbol":"TSLA"}}'
```

## Troubleshooting

- Blank chart page: CDN blocked? The page now falls back to jsdelivr and shows an error if both CDNs fail.
- Off-hours 1m empty: The chart auto-falls back to 5m → 1d and shows a message if still empty.
- Tradier unavailable: Snapshot still works via Polygon; errors are returned in `errors` and `providers` flags.
- Rate limits: Adjust `POLYGON_API_RATE` / `TRADIER_API_RATE` if you see throttling.

## Notes

- Options picks include `chart_url` ready to share with users; links use `PUBLIC_BASE_URL` when set.
- EM used in plans is horizon-scaled; see `docs/CONFIDENCE.md` for details.
- For SPX index scalps, chart links render SPY charts by default so intraday visualization remains familiar while strategies reference SPX options.

# Trading Assistant — Roadmap (V1)

## M0 — Foundation (Backend + Dashboard)
- [ ] FastAPI boots with lifespan, CORS configured, health/ready endpoints.
- [ ] `AppSettings` + `Journal` CRUD live; tests green.
- [ ] WebSocket connects; periodic `risk` broadcasts visible.

## M1 — Live Prices & Alerts
- [ ] Polygon WS client publishes `price` for watchlist symbols.
- [ ] Alerts CRUD with validation; list/create/update/delete.
- [ ] Alert poller triggers via Polygon HTTP; creates `AlertTrigger` rows; WS `alert` fan‑out.

## M2 — Planning & Sizing
- [ ] `/plan/validate` returns NL summary + RR bands.
- [ ] `/sizing/suggest` returns lot sizes from risk budget.
- [ ] Frontend shows action buttons: Build Plan, Size It, Set Alert.

## M3 — Broker Workflow (Tradier)
- [ ] Place/cancel orders; show statuses in Positions/Orders tabs.
- [ ] Confirmations, errors, and journaling of executions.

## M4 — Coach Confidence & Guidance (chat-data)
- [ ] Coach tools for quotes, picks, plan, sizing, set alert, place/cancel order, journal add.
- [ ] Responses include `confidence` and cite data sources used.

## Operational Readiness
- [ ] Docs for required env vars: `POLYGON_API_KEY`, `TRADIER_ACCESS_TOKEN`, `TRADIER_ACCOUNT_ID`, `TRADIER_ENV`, `CHATDATA_*`, `DATABASE_URL`.
- [ ] Observability: log structured events; `/api/v1/diag/*` documented.
- [ ] Security posture: API key for sensitive routes; WS tokenization plan.
## M5 — Discord Alerts
- [ ] Settings: webhook URL, enable toggle, allowed alert types (e.g., price_above, price_below, risk).
- [ ] Poller forwards triggers to Discord when enabled and type matches.
- [ ] Optional: risk breach alerts forwarded from risk engine.

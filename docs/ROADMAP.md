# Trading Assistant — Roadmap (V1)

Note: This roadmap is actively maintained. At the start of each working session, review and update the checkboxes and notes below (Codex: do this first).

Last reviewed: 2025-09-13

## M0 — Foundation (Backend + Dashboard)
- [x] FastAPI boots with lifespan, CORS configured, health/ready endpoints.
- [x] `AppSettings` + `Journal` CRUD live; tests green.
- [x] WebSocket connects; periodic `risk` broadcasts visible.

## M1 — Live Prices & Alerts
- [x] Polygon WS client publishes `price` for watchlist symbols.
- [ ] Alerts CRUD with validation; list/create/update/delete.  (update route pending)
- [x] Alert poller triggers via Polygon HTTP; creates `AlertTrigger` rows; WS `alert` fan‑out.

## M2 — Planning & Sizing
- [x] `/plan/validate` returns NL summary + RR bands.
- [x] `/sizing/suggest` returns lot sizes from risk budget.
- [x] Frontend shows action buttons: Build Plan, Size It, Set Alert.

## M3 — Broker Workflow (Tradier)
- [x] Place/cancel orders; show statuses in Positions/Orders tabs.
- [ ] Confirmations, errors, and journaling of executions.  (journaling not yet wired)

## M4 — Coach Confidence & Guidance (chat-data)
- [x] Coach tools for quotes, picks, plan, sizing, set alert, place/cancel order, journal add.
- [ ] Responses include `confidence` and cite data sources used.  (compose-and-analyze available; wire into coach)

## Operational Readiness
- [x] Docs for required env vars: `POLYGON_API_KEY`, `TRADIER_ACCESS_TOKEN`, `TRADIER_ACCOUNT_ID`, `TRADIER_ENV`, `CHATDATA_*`, `DATABASE_URL`.
- [x] Observability: log structured events; `/api/v1/diag/*` documented.
- [~] Security posture: API key for sensitive routes; WS tokenization plan.  (WS tokenization TBD)
## M5 — Discord Alerts
- [ ] Settings: webhook URL, enable toggle, allowed alert types (e.g., price_above, price_below, risk).
- [ ] Poller forwards triggers to Discord when enabled and type matches.
- [ ] Optional: risk breach alerts forwarded from risk engine.

Status notes
- Frontend dashboard + WS live; price/risk/alerts propagate over WS.
- Alerts set/list/delete/update complete.
- Sizing endpoint live; plan.validate to add NL summary + RR bands.
- Tradier sandbox order preview/place wired; journaling to be attached to executions.
- Coach integrated with ChatData; tools expanded for options + plan/sizing/broker/alerts/journal.
- Discord alert forwarding implemented in poller; risk breach → Discord pending.

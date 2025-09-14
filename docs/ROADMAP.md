# Trading Assistant — Roadmap (V1)

Note: This roadmap is actively maintained. At the start of each working session, review and update the checkboxes and notes below (Codex: do this first).

Last reviewed: 2025-09-14

## M0 — Foundation (Backend + Dashboard)
- [x] FastAPI boots with lifespan, CORS configured, health/ready endpoints.
- [x] `AppSettings` + `Journal` CRUD live; tests green.
- [x] WebSocket connects; periodic `risk` broadcasts visible.

## Security & Foundations (RED)
- [x] R1 — API Key Security: strict `require_api_key` denies when unset/mismatch; applied to sensitive routers (alerts, broker, plan, sizing, compose, journal, settings, coach).
- [x] R2 — WS Auth: optional short‑lived token minted at `/api/v1/auth/ws-token`, verified on `/ws`; legacy `?api_key=` remains supported.
- [x] R3 — News: provider‑backed `/api/v1/news` (Polygon) with 120s cache and URL de‑dupe; graceful empty when key missing.
- [x] R4 — Alembic: repo initialized; baseline creates `narratives` and `playbook_entries`.

## Phase 2 — SSE Narrator
- [x] Y1 — `/api/v1/coach/stream` streaming situation + guidance every ~3s (Chat Data backed)

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
- [x] Security posture: API key required for sensitive routes; WS tokenization implemented (optional).

## Upcoming (YELLOW/GREEN)
- [x] Y2 — Snapshot on connect: `/api/v1/stream/state` to seed frontend before ticks. (implemented)
- [x] Y3 — Observability: request IDs, structured JSON logs, timing for broker/chatdata.
- [x] Y4 — SSE backpressure: 3s cadence and significant‑delta gating.
- [ ] Y5 — Rate limiting: per‑IP sliding window on `/coach/stream` and `/news`.
- [x] Y5 — Rate limiting: per‑IP sliding window on `/coach/stream` and `/news`.
- [ ] Y6 — Broker/journal auditing: persist placed orders + narrator guidance.
- [ ] R5 — OCO/Bracket (Tradier): preview/place entry+SL+TP and journal summary.
- [x] R5 — OCO/Bracket (Tradier): preview/place entry+SL+TP and journal summary.
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

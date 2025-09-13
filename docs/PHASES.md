# Implementation Phases (Test After Each)

This plan breaks work into three phases with explicit checkpoints and tests. We will update this document and `docs/PROGRESS.md` after each step to make resets/restarts painless.

## Phase 1 — Foundation & Testability
Goal: A stable backend with CRUD basics, docs, and test scaffolding passing locally.

Scope:
- Ensure `app/` is a proper Python package (`__init__.py`).
- Settings + Journal CRUD are live (SQLite-friendly) and tested.
- Assistant prompt references confidence spec.
- Docs in place: Scope, Confidence, Roadmap, Phases.

Checkpoints/Tests:
- Run `pytest tests/test_settings_journal.py` and see both pass.
- `GET /healthz` returns `{ok:true}`.

## Phase 2 — Confidence Signals & Coach Integration
Goal: Compute confidence from ATR, VWAP (RTH-anchored), EMA posture (1m + 5m), order-flow proxies (RVOL/OBV/CVD approx), and expose to the Coach.

Scope:
- Extend context builder (`app/services/compose.py`) with signals in `docs/CONFIDENCE.md`.
- Update scoring engine to consume the new fields and output component breakdowns.
- Add unit tests for indicators (EMA/ATR/aVWAP/OBV/CVD approx) — deterministic arrays (no network).
- Coach tool returns include `confidence` and component rationale.

Checkpoints/Tests:
- `pytest -q tests/<new_indicator_tests>.py` all green.
- Manual call to coach route shows confidence components in response.

## Phase 3 — Live Streaming, Alerts & UI Wiring
Goal: Real-time prices, actionable alerts, and “next best action” chips in UI.

Scope:
- Start WS + risk engine on lifespan; guard with env for tests.
- Polygon WS client publishes `price` events to dashboard.
- Alerts CRUD (ORM); alert poller evaluates conditions using Polygon aggregates and broadcasts WS `alert` with suggestions.
- Dashboard surfaces confidence and ‘why’ per suggestion; alert actions prefill plan/sizing.

Checkpoints/Tests:
- Dashboard WS shows Connected; receives `risk` heartbeats and `price` updates (when POLYGON_API_KEY present).
- Create an alert → trigger observed in UI and via `/api/v1/alerts/list`.
- Unit test: Alerts CRUD endpoints pass (`tests/test_alerts_crud.py`).

Notes:
- No mock data: features silently disable without credentials; confidence uses quality multiplier.
- Portability: ORM over raw SQL to support SQLite/Postgres.
- Observability: structured logs; `/api/v1/diag/*` endpoints.

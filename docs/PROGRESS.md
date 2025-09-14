# Progress — 2025-09-14

Summary
- Phase 1 (R1–R4) done. Phase 2 (Y1) done. Phase 3 started (Y2 snapshot-on-connect).
- Added `/api/v1/auth/ws-token`, `/api/v1/news`, and `/api/v1/coach/stream` (SSE narrator). Secured sensitive routers including stream state.
- `/api/v1/stream/state` now returns positions, orders, risk, stream status, and last prices for watched symbols.
- Alembic baseline ready; tests green (43 passed).

Security & Platform
- API key hardening: `app/security.py` now denies by default when `API_KEY` is unset; mismatches return 401.
- Sensitive routers gated via dependency in `app/main.py`.
- WS auth: optional short‑lived token via `/api/v1/auth/ws-token`; WS also accepts legacy `?api_key=`.

News
- Polygon-backed headlines: `GET /api/v1/news?symbols=SPY,AAPL&limit=12`, 120s cache and URL de‑dupe, graceful empty if key missing.

Database
- Alembic scaffolded (`alembic.ini`, `alembic/env.py`, `alembic/versions/0001_baseline.py`).
- Models added: `app/models/narrative.py`, `app/models/playbook.py`.

Phase 2 — Completed
- Y1: SSE Trade Narrator `/api/v1/coach/stream` implemented; streams JSON every ~3s; best‑effort persistence to `narratives`.

Phase 3 — In Progress
- Y2: Snapshot on connect implemented via `/api/v1/stream/state` (secured).
- R5: Bracket orders supported (Tradier): backend endpoint accepts `duration`, `bracket_stop`, `bracket_target`; preview/place flows; non‑preview placements journal a summary entry.
- Y3: Observability added — request IDs via middleware, structured JSON logs, and timing logs for Tradier (orders/cancel) and ChatData requests. Each response includes `X-Request-ID` and `X-Process-Time-Ms` headers.
- Y5: Per‑IP sliding window rate limiting added for `/api/v1/news` (default 30/min/IP) and `/api/v1/coach/stream` (default 10/min/IP). Tunable via env: `RATE_LIMIT_NEWS_PER_MIN`, `RATE_LIMIT_COACH_PER_MIN`.
- Y4: SSE backpressure added — coach stream emits every ~3s but only pushes data when price moves beyond `SSE_MIN_PRICE_DELTA_PCT` (default 0.1%), risk flags change, or guidance action/band/±confidence (>= `SSE_MIN_CONFIDENCE_DELTA`, default 5) change. Sends heartbeat comments every `SSE_HEARTBEAT_SEC` (default 15s).
- Y6: Broker/journal auditing — all Tradier order previews/placements are persisted to `broker_orders` (request + response, request ID). Non‑preview orders also log a concise summary in `journal_entries`. Narrator guidance continues to persist in `narratives`.

—
# Progress — 2025-09-13



Summary
- Core backend and dashboard are live; alerts, sizing, planning, and broker sandbox flows are implemented.
- Coach can fetch options data, validate plans, suggest sizing, place (sandbox) orders, set alerts, create journal entries, and compose+analyze for confidence.
- All tests pass locally (43 passed).


Backend
- FastAPI app with lifespan/CORS/health/ready: `app/main.py`
- WebSocket manager + risk engine (broadcasts risk state + alerts): `app/core/ws.py`, `app/core/risk.py`
- Alerts CRUD (list/create/update/delete) + poller + WS fan‑out + optional Discord forwarding: `app/routers/alerts.py`, `app/services/poller.py`, `app/integrations/discord.py`
- Planning `/plan/validate` returns per-unit risk, RR bands (0.5R/1R/2R), targets, notes, and NL summary: `app/routers/plan.py`
- Sizing `/sizing/suggest` with equity/buying power overrides and sandbox notes: `app/routers/sizing.py`
- Broker (Tradier sandbox) account/preview/place/cancel: `app/routers/broker_tradier.py`, `app/routers/broker.py`
- Compose+Analyze (context + scoring + plan + risk): `app/routers/compose_analyze.py`, `app/services/compose.py`, `app/services/scoring_engine.py`
- Settings + Journal CRUD (DB): `app/routers/settings.py`, `app/routers/journal.py`, models in `app/models/*`

Coach & Tools
- ChatData integration: `app/integrations/chatdata.py`
- Assistant tools: options.pick/expirations/chain; plan.validate; sizing.suggest; broker.place_order; alerts.set; journal.create; compose.analyze.
- System prompt updated to encourage using compose.analyze for confidence (0–100) + terse rationale: `app/assistant/system_prompt.md`

Frontend (Next.js)
- Dashboard with WS live updates (price/orders/positions/risk/alerts) and proxy to backend: `trading-dashboard/app/page.tsx`, `trading-dashboard/app/api/proxy/route.ts`

- Proxy now runs on Edge runtime to avoid 250 MB Serverless limit: `export const runtime = "edge"`.
- Coach chat page wired to backend: `trading-dashboard/app/coach/page.tsx`
- Alerts, Journal, Admin pages present: `trading-dashboard/app/alerts/page.tsx`, `trading-dashboard/app/journal/page.tsx`, `trading-dashboard/app/admin/page.tsx`
- Positions/Orders pages: `trading-dashboard/app/positions/page.tsx`, `trading-dashboard/app/orders/page.tsx`
- Replaced deprecated `isLoading` flags with `isPending`, added PostCSS plugin, and removed legacy `src/app` scaffold.

- Coach chat page wired to backend: `trading-dashboard/app/coach/page.tsx`
- Alerts, Journal, Admin pages present: `trading-dashboard/app/alerts/page.tsx`, `trading-dashboard/app/journal/page.tsx`, `trading-dashboard/app/admin/page.tsx`
- Positions/Orders pages: `trading-dashboard/app/positions/page.tsx`, `trading-dashboard/app/orders/page.tsx`


Tests
- 43 passed, 0 failed (pytest). See `tests/`.

Deployment (Vercel)

- Config: `vercel.json` builds the `trading-dashboard/` app with Next.js.
- Required env on Vercel: `NEXT_PUBLIC_API_BASE` (backend URL), optional `NEXT_PUBLIC_API_KEY`, `NEXT_PUBLIC_WS_BASE`.
- Bundle-size mitigations:
  - `app/api/proxy` on Edge runtime.
  - `next.config.cjs` excludes tests/docs/maps from serverless tracing; image optimizer disabled.
- Status: Project `trading-dashboard` found via API; latest prod deploy = ERROR. Push to GitHub will trigger CI; if production branch is `main`, merge or redeploy from Vercel UI.

- Config: `vercel.json` builds `trading-dashboard/`; see `docs/DEPLOYMENT.md` for checklist.
- Required env on Vercel: `NEXT_PUBLIC_API_BASE` (backend URL), optional `NEXT_PUBLIC_API_KEY`, `NEXT_PUBLIC_WS_BASE`.
- CORS: ensure backend `ALLOWED_ORIGINS` allows your Vercel domain.
- Status: probing default app domains returned 404; awaiting the actual live URL after env setup.


Next Implementation Targets
- Coach: include compose.analyze confidence in replies when discussing a symbol (ensure single call/hop and clean formatting).
- Execution journaling: attach broker previews/placements to journal.
- Risk → Discord: forward breach alerts when enabled in Settings.
- Screener ranking: replace placeholder with simple ranking using scoring engine.

Notes for Ops
- If Vercel deploy still reports 250 MB function size, confirm all API routes are Edge (only the proxy exists) and that the project builds from `trading-dashboard/`.
- Verify domain attachment in Vercel Settings → Domains. Default alias appears as `trading-dashboard-n8kahls-projects.vercel.app`.

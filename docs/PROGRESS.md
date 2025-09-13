# Progress — 2025-09-13

Updated: 2025-09-13 20:20 UTC

This document summarizes current implementation status, test coverage, and deployment notes. It is updated at the start/end of each session.

Summary
- Core backend and dashboard are live; alerts, sizing, planning, and broker sandbox flows are implemented.
- Coach can fetch options data, validate plans, suggest sizing, place (sandbox) orders, set alerts, create journal entries, and compose+analyze for confidence.
- All tests pass locally (43 passed).
- Vercel deployment configured; env set. Latest prod deploy previously errored on bundle size; mitigations shipped and a redeploy is required.

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

Tests
- 43 passed, 0 failed (pytest). See `tests/`.

Deployment (Vercel)
- Config: `vercel.json` builds the `trading-dashboard/` app with Next.js.
- Required env on Vercel: `NEXT_PUBLIC_API_BASE` (backend URL), optional `NEXT_PUBLIC_API_KEY`, `NEXT_PUBLIC_WS_BASE`.
- Bundle-size mitigations:
  - `app/api/proxy` on Edge runtime.
  - `next.config.cjs` excludes tests/docs/maps from serverless tracing; image optimizer disabled.
- Status: Project `trading-dashboard` found via API; latest prod deploy = ERROR. Push to GitHub will trigger CI; if production branch is `main`, merge or redeploy from Vercel UI.

Next Implementation Targets
- Coach: include compose.analyze confidence in replies when discussing a symbol (ensure single call/hop and clean formatting).
- Execution journaling: attach broker previews/placements to journal.
- Risk → Discord: forward breach alerts when enabled in Settings.
- Screener ranking: replace placeholder with simple ranking using scoring engine.

Notes for Ops
- If Vercel deploy still reports 250 MB function size, confirm all API routes are Edge (only the proxy exists) and that the project builds from `trading-dashboard/`.
- Verify domain attachment in Vercel Settings → Domains. Default alias appears as `trading-dashboard-n8kahls-projects.vercel.app`.

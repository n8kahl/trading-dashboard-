# Progress Log — Frontend Live Integration

Date: 2025-09-13

Links:
- Vercel (frontend): https://trading-dashboard-ten-kappa.vercel.app/
- Railway (backend): https://web-production-a9084.up.railway.app/

## Summary

Aligned the Next.js dashboard to the FastAPI backend using a local API proxy and environment‑derived WebSocket connection. This removes CORS friction, passes an optional API key automatically, and enables a live Analyze panel that calls the backend scoring/analysis route.

All backend tests pass (43). Changes are backward‑compatible and gated by environment variables.

## Implemented

- Next.js API proxy to backend
  - `trading-dashboard/app/api/proxy/route.ts`: Forwards GET/POST to `NEXT_PUBLIC_API_BASE` and injects `X-API-Key` when `NEXT_PUBLIC_API_KEY` is set.
- Frontend API/Coach use proxy
  - `trading-dashboard/src/lib/api.ts`: `apiGet/apiPost` route through `/api/proxy?path=…`.
  - `trading-dashboard/src/lib/coach.ts`: `coachChat` routed via proxy.
- WebSocket client derives URL and appends API key when present
  - `trading-dashboard/src/lib/ws.ts`: Builds URL from `NEXT_PUBLIC_WS_BASE` or `NEXT_PUBLIC_API_BASE`; adds `?api_key=…`.
  - `trading-dashboard/app/page.tsx`: calls `connectWS()` without origin.
- Backend CORS is env‑driven; includes Vercel and Railway origins by default
  - `app/main.py`: reads `ALLOWED_ORIGINS` comma‑separated; defaults cover Vercel + Railway + localhost.
- Confidence/Analysis route exposed and used
  - `app/main.py`: mounts `app.routers.compose_analyze`.
  - `trading-dashboard/app/page.tsx`: Adds an Analyze card that calls `/api/v1/compose-and-analyze`.

## Environment

Set on Vercel:
- `NEXT_PUBLIC_API_BASE=https://web-production-a9084.up.railway.app`
- `NEXT_PUBLIC_WS_BASE=wss://web-production-a9084.up.railway.app/ws` (optional)
- `NEXT_PUBLIC_API_KEY=<backend API_KEY if set>`

Set on Railway:
- `ALLOWED_ORIGINS=https://trading-dashboard-ten-kappa.vercel.app,http://localhost:3000`
- `ENABLE_BACKGROUND_LOOPS=1`
- Data providers/broker keys as available: `POLYGON_API_KEY`, `TRADIER_ACCESS_TOKEN`, `TRADIER_ACCOUNT_ID`, `TRADIER_ENV`, `CHATDATA_*`

## Tests

`pytest` → 43 passed, no failures (warnings only).

## Open PRs — Review Notes

- PR #36: “Document fail_open usage” — Safe to merge.
  - Removes an unused helper and adds usage docs for `fail_open`.
  - No runtime behavior changes expected; backend tests should stay green.

## Next Steps

See `docs/UX_PLAN.md` for detailed UX/UI flow, feature review, and implementation plan focused on a responsible, production‑ready web app.

---

## Update — UI Components (Risk, Confidence, Inline Alerts)

Date: 2025-09-13

Implemented first-pass live UI pieces aligned to the plan:

- Risk banner in status strip
  - Shows `daily_r`, concurrent positions, and breach flags from WS `risk` events.
  - File: `trading-dashboard/app/page.tsx`

- Confidence card (Analyze)
  - Score band chip with label (Unfavorable/Mixed/Favorable), component chips (ATR/VWAP/EMAs/Flow/Liquidity), and freshness seconds.
  - Calls `/api/v1/compose-and-analyze` via the proxy.
  - File: `trading-dashboard/app/page.tsx`

- Inline Create Alert control
  - Defaults to ±1R from entry; optional threshold % to offset from entry price.
  - Posts to `/api/v1/alerts/set` with type `price_above|price_below` and `threshold_pct`.
  - File: `trading-dashboard/app/page.tsx`

Branch and PR
- Branch: `feat/dashboard-live-confidence-discord`
- Open PR: https://github.com/n8kahl/trading-dashboard-/pull/new/feat/dashboard-live-confidence-discord

Pick-up Next
- Confidence UI polish: colors, tooltips for components, “why” rationale text.
- Alerts page enhancements: types/timeframe/expiry controls, live updates, Discord enablement hint.
- Initial snapshot fetch for positions/orders; basic readonly lists.
- Style Risk banner with severity colors and link to Settings.

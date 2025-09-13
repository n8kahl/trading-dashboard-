# Requirements — Providers, Natural Language Alerts, Next Best Actions, and Day-Trader UI

This document codifies the functional and non‑functional requirements to deliver a live, responsible trading dashboard using chat-data.com (LLM), Polygon (market data, options), and Tradier (broker). It complements `docs/UX_PLAN.md` and `docs/ROADMAP.md`.

## Providers & Capabilities

- Polygon (Market Data)
  - WebSocket: aggregate‑minute bars for equities (`AM.<SYMBOL>`), used for live prices, freshness, and intraday signals.
  - HTTP: v2 aggregates (intraday/daily) for backfill; snapshots for resiliency.
  - Options: v3 reference options contracts (universe); optional real‑time quotes if plan allows.
  - Indicators (optional): EMA/RSI endpoints for convenience; otherwise computed client‑side.
  - Env: `POLYGON_API_KEY` set on backend.
  - Notes: If plan tier lacks intraday minute or options quotes, UI must degrade gracefully (daily fallbacks; label "not realtime").

- Tradier (Broker)
  - Endpoints: account, orders (place/cancel/replace), positions, options chains/expirations, quotes (underlying) for sizing sanity.
  - Env: `TRADIER_ACCESS_TOKEN`, `TRADIER_ENV` (sandbox/live), `TRADIER_ACCOUNT_ID`.
  - Safety: Never place orders without explicit user confirmation; sandbox toggles in Settings.

- chat-data.com (LLM via OpenAI‑compatible API)
  - Endpoint: OpenAI‑compatible Chat Completions with tool calling.
  - Functions: natural language formatting of alerts; composing execution checklists; summarizing news; answering queries.
  - Env: `CHATDATA_API_KEY` (required for LLM features), `CHATDATA_BASE_URL` (default `https://api.chat-data.com`), `CHATDATA_API_PATH` (default `/v1/chat/completions`), `CHATDATA_MODEL` (optional model ID).
  - Privacy: Keep keys server‑side; frontend calls backend routes only.

## Natural Language Alerts (NLA)

- Triggers
  - Backed by DB `Alert` rows with condition JSON (e.g., `price_above/below`, threshold %, timeframe, expiry).
  - Poller checks active alerts on interval (`ALERT_POLL_SEC`); obtains price via Polygon (HTTP fallback acceptable).
  - On trigger: create `AlertTrigger` row; broadcast WS `{ type:'alert', level, msg, meta }`.

- Message Composition
  - Fast path: deterministic template with symbol, condition met, current price, recency, and suggested next steps.
  - Enriched path (if `CHATDATA_API_KEY` set and latency budget allows): LLM augments with brief rationale and confidence (0–100), citing ATR/VWAP/EMA/order‑flow/liquidity inputs (no hallucinated data).
  - Latency budgets: p95 ≤ 3s for alert delivery; LLM enrichment should not block broadcast. If slow, send basic alert first and follow with enriched text.

- Delivery
  - WebSocket fan‑out to dashboard; optional Discord webhook forward when enabled in Settings (with allowed alert types).
  - UI shows alert list with timestamp, reason, and Next Best Action (NBA) buttons.

- Guardrails
  - No automated execution from alerts; NBA buttons require user confirmation for sensitive actions (orders).
  - Clear freshness labels; disclose data sources used.

- Acceptance
  - CRUD works; triggers persisted; alerts visible via WS; Discord forward respects filters.

## Next Best Actions (NBA)

- Buttons and Mappings
  - Plan: calls `/api/v1/plan/validate` with current entry/stop → shows 1R/2R targets and sanity notes.
  - Size It: calls `/api/v1/sizing/suggest` with risk budget → returns lot size; UI blocks oversize suggestions.
  - Set Alert: prefilled thresholds (±1R) → `/api/v1/alerts/set`.
  - Ask Coach: sends context to `/api/v1/coach/chat` to get checklist and confidence.
  - Place Order: opens prefilled order modal; posts to `/api/v1/broker_tradier/*` only after explicit confirm; honors sandbox setting.

- State/Enablement
  - Buttons enable based on provider availability (e.g., Tradier key present to show Place Order).
  - Tooltip and disabled states explain missing prerequisites.

- Acceptance
  - All NBA calls return within UX‑acceptable budgets: Plan/Sizing < 800ms; Alert Set < 500ms; Order flows depend on broker latency.

## Day‑Trader‑First UI (Responsive)

- Layout
  - Dashboard: Watchlist → Picks → Analyze; live price/WS status; risk banner; alerts column; news panel.
  - Mobile: collapsible sections; persistent status strip (WS/Risk/Price) and FAB for quick actions.
  - Keyboard: quick symbol switch, focus inputs, submit actions (non‑destructive only) with shortcuts.

- Confidence Surface
  - Score band chip (0–100): unfavorable (<50), mixed (50–69), favorable (≥70).
  - Component chips (ATR, VWAP, EMAs, Order‑Flow, Liquidity) with bounded contribution values.
  - “Why” 1‑liner and data freshness timestamp.

- Alerts UX
  - Inline “Create Alert” with type, level, threshold %; defaults to ±1R.
  - Alerts page: filters (active/expired), bulk disable, edit, delete.

- Risk & Positions
  - Risk banner: daily R, concurrent positions, breach indicators from WS.
  - Positions/Orders: readonly lists first, then confirmable actions.

- Responsible Design
  - Confirmations on any broker action; sandbox switch visible.
  - No secrets client‑side; proxy all API calls; WS token/query only if backend requires.
  - Clear fallback messaging when minute data or options quotes are unavailable.

## Performance & Observability

- Performance budgets
  - Initial snapshot (`/api/v1/stream/state`) < 400ms typical; WS connect < 500ms.
  - Plan/Sizing < 800ms; Analyze (scoring) < 1200ms with warmed caches.

- Observability
  - Routes: `/api/v1/diag/health|ready|config|routes`.
  - Structured logs for alerts, risk breaches, broker errors.
  - Client surfacing of last event age and data source labels.

## Security & Privacy

- API key header (`X-API-Key`) on sensitive routes; CORS origins locked via env.
- WS query param tokenization for dev; long‑term plan: signed tokens.
- PII/Secrets: never rendered to client; Coach route handles LLM calls server‑side.

## Dependencies & Env (recap)

- Backend: `POLYGON_API_KEY`, `TRADIER_*`, `CHATDATA_*`, `ALERT_POLL_SEC`, `ENABLE_ALERTS_POLLER`, `ENABLE_BACKGROUND_LOOPS`, `ALLOWED_ORIGINS`.
- Frontend: `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_WS_BASE` (optional), `NEXT_PUBLIC_API_KEY` (optional pass‑through).


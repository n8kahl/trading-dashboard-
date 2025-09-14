# Trading Assistant — Scope & Principles

## Vision
A day trader’s command center that is intuitive, informative, and profitable. It combines live market data, actionable alerts, and an LLM coach to guide trade setups, execution, and management via natural language. No mock data; all insights are backed by live market and brokerage APIs.

## Non‑Goals
- No paper trading simulator beyond what the broker provides.
- No historical backtester in v1.
- No social features or multi‑tenant rooms in v1.

## Core Principles
- Live, real data only (Polygon, Tradier, earnings feeds, chat-data.com LLM).
- Actionable UX: every surface offers a clear next best action.
- Safety first: guardrails from risk engine and settings; explain “why”.
- Observability: health, latency, data freshness are visible and alerting.
- Modular: cleanly separated services and clear contracts.

## User Outcomes
- Discover high‑quality intraday setups with confidence scores.
- Execute trades in a simple, few‑click workflow.
- Receive timely, succinct alerts (w/ next best action suggestions).
- Manage open positions with proactive guidance (trim/exit/roll/hedge).
- Tune behavior from an intuitive Settings panel and persist in DB.

---

# Architecture Overview

## Data Sources (no mock data)
- Market data: Polygon
  - HTTP: quotes/aggregates; WebSocket: live bars.
- Broker: Tradier (orders, positions, balances, fills).
- LLM: chat-data.com OpenAI‑compatible endpoint for reasoning & NLA tools.
- Earnings/news: via Polygon and curated feeds; LLM can summarize/augment.
 - Alerts to Discord: optional per Settings (webhook + filter by type).

## Backend (FastAPI)
- Routers
  - `/api/v1/stream/*`: stream snapshots for positions/orders/risk; WS at `/ws`.
  - `/api/v1/options/*`: screening/picks and pricing (inputs backed by Polygon/Tradier only).
  - `/api/v1/alerts/*`: CRUD alerts; triggers fan‑out to WS + persistence.
  - `/api/v1/plan`, `/api/v1/sizing`: validate setups and compute risk‑aligned sizing.
  - `/api/v1/broker/*`: account, orders (place/cancel), positions (Tradier).
  - `/api/v1/coach/*`: LLM chat, tools for data fetch, plan/sizing, and journaling.
  - `/api/v1/journal/*`: trade journal CRUD.
  - `/api/v1/settings/*`: admin settings CRUD.
  - `/api/v1/diag/*`: health/ready/config.
- Services
  - `core/ws`: connection manager; broadcast JSON events to dashboard.
  - `core/risk`: periodic risk evaluation; emits risk state + breach alerts.
  - `services/stream`: Polygon WS client; maintains recent bars and broadcasts price ticks.
  - `services/poller`: alert poller using Polygon HTTP aggregates; triggers when conditions met.
  - `services/providers/tradier`: broker client for orders/positions.
  - `integrations/chatdata`: minimal OpenAI‑compatible chat client.
- Persistence (SQLAlchemy)
  - `AppSettings`, `Alert`, `AlertTrigger`, `JournalEntry`, plus paper tables as needed.
- Security
  - API key header for sensitive routes; WS query param for dev; rotate to token later.

## Frontend (Next.js)
- Real‑time WS client: reflects positions / orders / risk / alert / price.
- Pages
  - Dashboard: watchlist, top picks, live prices, alerts, quick actions.
  - Coach: chat-data LLM with tools (plan/sizing/fetch/execute/journal/add alert).
  - Orders/Positions: live management and one‑click next actions (trim/close/roll).
  - Alerts: list/create/edit with conditions and expirations; actionable chips.
  - Journal: log entries, attach plans/LLM rationale, export.
  - Admin/Settings: risk limits, defaults, universe, API keys (server‑only secrets).
- Components: AlertsPanel, NewsPanel, Pick cards, Position tiles, Risk banner.

## Events over WebSocket
- `risk`: `{ type: "risk", state }`
- `alert`: `{ type: "alert", level, msg, meta? }`
- `positions`: `{ type: "positions", items }`
- `orders`: `{ type: "orders", items }`
- `price`: `{ type: "price", symbol, last }`

---

# Feature Scope (V1)

## 1) Live Data & WS
- Start WS and risk engine at app startup.
- Polygon WS client publishes `price` events for watchlist symbols.
- Stream snapshot endpoints used for initial page load; WS for updates.

## 2) Alerts (Actionable)
- CRUD backed by DB. Conditions: price_above/below with optional threshold_pct; timeframe minute/day; optional expiry.
- Poller checks conditions every `ALERT_POLL_SEC`. On trigger:
  - Persist `AlertTrigger` row; mark first trigger timestamp.
  - Broadcast WS `alert` with suggested next best actions, e.g.,
    - “Take TSLA scalp setup (1R risk)?”
    - “Trim SPY — level approaching.”
- LLM tool can enrich alert message with rationale when latency allows.

## 3) Trade Planning & Sizing
- `/plan/validate`: validate entry/stop; compute RR bands; return NL summary.
- `/sizing/suggest`: share of risk budget; lot size; confidence score tie‑in.
- Coach tool uses both to propose an execution checklist.

## 4) Broker Execution
- Place/cancel/replace orders via Tradier; return IDs and broker echoes.
- “Next best action” buttons produce prefilled orders; user confirms.

## 5) Coach (chat-data)
- Tools exposed: quotes, picks, plan/sizing, set alert, place/cancel order, journal add.
- Returns: content + `confidence` (0–1) per suggestion; cites data sources used.
- Guardrails: never execute trades without explicit user confirm.

## 6) Settings & Risk
- Settings persisted in `app_settings`. Risk engine reads limits and emits warnings.
- UI toggles for sandbox/production, default RR, top symbols, etc.

---

# Milestones & Acceptance Criteria

## M0 — Foundation
- Health endpoints pass; `settings/journal` CRUD pass tests.
- WS connects; `risk` heartbeats visible in UI.

## M1 — Live Prices & Alerts
- Polygon WS running; dashboard receives `price` for watchlist symbols.
- Alerts CRUD + poller working; triggers broadcast WS `alert` with action chips.

## M2 — Planning & Sizing
- Endpoints return consistent structures with NL summaries; unit tests for edge cases.
- Coach toolchain composes a step‑by‑step execution checklist.

## M3 — Broker Workflow
- Place/cancel orders; confirmation and error states handled; audit in journal.

## M4 — Coach Confidence & Guidance
- All suggestions include `confidence`, rationale, and links to underlying data.

KPIs: WS uptime > 99%, quote latency p95 < 1.5s, alert delivery p95 < 3s, plan compute < 800ms, API error rate < 1%.

---

# Implementation Notes
- No mock data: features are disabled when credentials missing; UI communicates why.
- DB portability: use SQLAlchemy ORM for SQLite/Postgres compatibility.
- Background tasks: start in FastAPI lifespan; cancel cleanly on shutdown.
- Observability: log structured events; expose `/api/v1/diag/health|ready|config`.
- Security: keep secrets server‑side; signed action tokens for WS in future.

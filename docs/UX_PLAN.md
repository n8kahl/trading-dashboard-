# UX/UI Flow & Implementation Plan — Responsible Web App

This plan focuses on a live, production‑ready trading dashboard with clear next actions, safety guardrails, and real‑time data — avoiding mock data by design.

## Principles
- Real data only: Live Polygon and Tradier integrations; LLM calls via server.
- Responsible UX: Clear confirmations, risk guardrails, data provenance and freshness.
- Observer first: Always show what’s happening (WS state, risk, data timestamps).
- Progressive disclosure: Simple defaults; advanced controls behind expanders.
- Performance: Stream initial snapshots, then update over WS.

## Top‑Level Navigation
- Dashboard: Watchlist, picks, price tape, analysis (confidence), alerts, news.
- Coach: Chat to plan/summarize; tools for quotes, plan/sizing, set alert, journal.
- Plan & Sizing: Validate entry/stop and compute position size from risk budget.
- Alerts: List/create/edit with status and quick actions.
- Positions & Orders: Live broker state with “next best action” buttons.
- Journal: CRUD entries with links to plans and LLM rationale.
- Admin/Settings: Risk limits, universe, keys (server‑only secrets), Discord alerts.
- Diagnostics: Health, config, routes; useful in staging.

## End‑to‑End UX Flows

1) First‑Run Setup
- User loads Dashboard → sees WS status, “Not configured” hints if keys missing.
- Admin sets API keys and risk defaults → backend persists to DB.
- Optional: Enable background loops (WS pings, risk, poller) via env.

2) Discovery → Analysis → Action
- Pick symbol from Watchlist → backend `/options/pick` returns top 5 contracts.
- Live price renders from WS; stale badge if `age_sec > 60`.
- Analyze: Call `/compose-and-analyze` → show score band (0–100) and components (ATR, VWAP, EMA, Flow, Liquidity) with concise rationale.
- Quick actions: “Size It”, “Set Alert”, “Ask Coach” (pre‑filled prompt).

3) Plan & Sizing
- Plan: `/plan/validate` validates entry/stop → shows 1R/2R targets and sanity notes.
- Sizing: `/sizing/suggest` uses risk budget and per‑unit risk → outputs lots/qty.
- Confirmations: Always require explicit confirmation before any broker action.

4) Alerts
- Create: Inline control on Dashboard; CRUD in Alerts page.
- Poller: Backend checks and emits WS `alert`; optional Discord forward if enabled.
- UI: Action chips (“Size now”, “Open Coach”) link to next steps.

5) Orders & Positions (when broker keys present)
- Positions and Orders stream via snapshot + WS; risk banner warns on breaches.
- Action buttons populate sidecars/modals with prefilled orders; user confirms.

## Responsible Design
- Guardrails: Risk engine emits breach alerts; UI blocks oversized sizing suggestions.
- Confirmations: No auto‑trade; explicit confirm on any broker action.
- Privacy: Secrets server‑side; client uses proxy; no keys in browser storage.
- Transparency: Data freshness timestamps and “why” breakdown on confidence.
- Fail‑open strategy: Where appropriate, return helpful fallbacks without crashing.

## Feature Review & Acceptance
- Live Data: Price ticks, risk heartbeats visible; fallback clearly labeled.
- Alerts: CRUD + poller; triggers fan‑out via WS and optional Discord.
- Analysis: Score band + components; rationale text citing data used.
- Plan/Sizing: Consistent structures; handles edge cases gracefully.
- Broker: Place/cancel/replace; audit errors and confirmations in journal.

## Implementation Plan (Frontend)
1. Connectivity & Shell
- Done: API proxy, WS env, API key pass‑through.
- Add: initial snapshot fetch `/api/v1/stream/state` on load.

2. Confidence UI Component
- Band chip (unfavorable <50, mixed 50–69, favorable ≥70), timestamp, rationale.
- Component breakdown chips: ATR, VWAP, EMAs, Flow, Liquidity (with contributions).

3. Alerts UX
- Inline “Create Alert” (price_above/below) with smart defaults (±1R).
- Alerts page: filters, toggles, expires_at; real‑time updates.

4. Risk Banner
- Show current `risk.state`; badge colors on breaches; link to Settings.

5. Positions/Orders Pages
- Readonly list first using snapshot + WS; wire actions gradually.
- Sidecar modals for confirm flows; guard with API key and sandbox flags.

6. Coach Page
- Maintain tool‑aware prompts; add “Insert Plan/Sizing/Alert” quick chips.

7. Settings Page (Admin)
- Fully wire Discord webhook & alert filters; test end‑to‑end with poller.

## Implementation Plan (Backend Touchpoints)
- Stream: ensure `/ws` emits `price`, `risk`, `alert`; `/stream/state` used for initial page load.
- CORS: keep env‑driven; lock down in production.
- Compose/Analyze: ensure score components include ATR/VWAP/EMA/Flow/Liquidity.
- Alerts: ensure poller covers minute + day TF; persist triggers; optional Discord forward.

## Milestones
- M0: Connectivity + Analyze UI + Alerts create (live)
- M1: Confidence component breakdown + Risk banner
- M2: Positions/Orders (readonly) + Size/Plan integration
- M3: Broker actions with confirm flows + Journal logging
- M4: Discord alert forwarding acceptance + Observability pass


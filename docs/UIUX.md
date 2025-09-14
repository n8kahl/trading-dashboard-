# UI/UX Blueprint and Responsive Design

This document captures the approved flows and responsive design plan.

## Navigation
- Dashboard: live watchlist, top picks, prices, alerts.
- Coach: chat-data LLM with tool-powered actions.
- Positions/Orders: live grids with inline actions.
- Alerts: list/create/edit; triggers with next-best actions.
- Journal: entries linked to trades and rationales.
- Settings: risk, universe, execution, LLM, API keys, Discord alerts.

## Global Frame
- WS status dot + latency; market clock; data freshness.
- Risk banner (limits + breach states) with guidance.
- Toasts for alerts; Next Best Action chips where relevant.
- Keyboard shortcuts: B=Build Plan, Z=Size, A=Alert, O=Order preview, Enter=Confirm, Esc=Cancel.

## Dashboard
- Watchlist: editable, shows last, Δ, RVOL hint.
- Top Picks: cards with confidence ring and chips (ATR, VWAP, EMA, Flow, Liquidity) + tooltips.
- Inline Plan/Size/Alert: entry/stop inputs; quick actions.
- Right Rail: Alerts panel (live, actionable), News panel, Coach shortcuts.

## Coach
- Threaded chat; responses include: summary, confidence (0–100) with breakdown, why-now, action buttons (Plan, Size, Set Alert, Place).
- Cites data used (VWAP RTH, EMAs, ATR%, RVOL/Flow).

## Positions/Orders
- Live grids, inline actions: Trim %, Move stop, Close, Roll.
- Bracket builder drawer: preview + confirm; respects guardrails.

## Alerts
- Table: symbol, condition, timeframe, active/expiry, last trigger; filter/search.
- Create modal: price above/below with threshold %, timeframe, expiry.
- Trigger UX: toast + panel item with Take/Trim chips opening prefilled flows.
- Discord alerts: configurable via Settings (webhook, enabled, types).

## Journal
- Timeline linked to orders/alerts; tags; AI summaries optional.

## Settings
- Risk: daily R cap, max concurrent, default RR, sandbox/live toggle.
- Universe: top symbols; sector presets.
- Execution: defaults (TIF, bracket template).
- LLM: model, permissions, include confidence breakdown.
- Integrations: Polygon, Tradier, chat-data (test buttons).
- Alerts → Discord: webhook URL, enabled toggle, alert types to forward (e.g., "price_above,price_below,risk").
- Advanced: component weights for confidence (server-provided), reset to defaults.

## Responsive Design
- Layout grid uses fluid CSS Grid/Flex with breakpoints:
  - ≥1280px: 2-column main area with right rail; cards grid auto-fit minmax(320px,1fr).
  - 768–1279px: single column main; right rail stacks below; cards auto-fit minmax(280px,1fr).
  - <768px: single column; condensed cards, collapsible sections; hide non-critical metrics behind tooltips.
- Typography scales via clamp(); buttons and inputs maintain min touch targets (44px).
- High-contrast theme support; color not the only encoder (icons/labels for confidence/risk).
- WS/latency + freshness indicators collapse to compact badges on small screens.

## Acceptance Criteria
- Dashboard adapts to <768px with stacked sections and readable cards.
- Confidence ring and chips remain legible and accessible across breakpoints.
- Alerts and Next Best Action chips remain one-tap/one-click reachable on mobile widths.
- Settings exposes Discord webhook, enabled, and type filters; test message button optional.


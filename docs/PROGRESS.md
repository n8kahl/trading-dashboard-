# Progress Log

This document tracks code and docs changes so work can be resumed easily in a new session.

## 2025-09-16

- Data: Added async SQLAlchemy models (`trades`, `features`, `logs`) with automatic table creation on startup. Falls back to local SQLite when `DATABASE_URL` is absent.
- API: New storage router exposes `POST/GET /api/v1/trades`, `POST/GET /api/v1/features`, `POST/GET /api/v1/logs` with filtering and envelope responses.
- Alerts: Discord webhook notifier fires on trade inserts and error/critical logs (`DISCORD_WEBHOOK_URL`). Added env template entries and documented usage in README/USAGE.
- Ops: Docker env template now ships a ready Postgres `DATABASE_URL`; deployment guide updated with webhook + DB hints.
- Trading UX: Horizon-aware TP/SL engine in assistant + proposal charts (EM + ATR + IV percentile + remaining-session scaling, confluence snapping, minimum spacing). Charts label VWAP/EMA/Pivots/current price and render proposal-only links (15m intraday, 1d leaps). Leap requests default to ~6M expiries with matching target sizing. (Commits: 7d2b03d, 17877fd, 7ca042d, da5920f, e9afa86, 1edc28f, 624a8ca, 4748e79)

## 2025-09-15

- DevOps: Docker + Compose stack
  - Added `Dockerfile` to containerize FastAPI app.
  - Added `docker-compose.yml` with services: `api`, `db` (TimescaleDB), `prometheus`, `grafana`.
  - Added server env template `.env.server.example`.
- Observability: Prometheus + Grafana
  - Instrumented FastAPI with Prometheus metrics via `prometheus-fastapi-instrumentator` (exposes `/metrics`).
  - Added `ops/prometheus/prometheus.yml` to scrape `api:8000/metrics`.
  - Provisioned Grafana Prometheus datasource (`ops/grafana/provisioning/datasources/datasource.yml`).
- Docs
  - New `docs/DEPLOY_WITH_COMPOSE.md` for step-by-step bring-up on a VM.
  - `README.md` updated previously with solo-operator guidance; retained original section.

### User direction update (Option B — VM)

- The user selected Option B (one-VM deploy on Ubuntu).
- Provided copy/paste steps for VM provisioning, Docker install, env setup, compose bring-up, and verification.
- Next decision: add reverse proxy + HTTPS, or proceed with DB schema + endpoints and Discord alerts.

### AutoTrader (separate repo; local scaffold here)

- Added standalone AutoTrader skeleton under `autotrader/` (gitignored in this repo): API + worker + Docker/Compose.
- Implemented order management endpoints:
  - `GET /api/v1/orders`, `GET /api/v1/orders/{id}`, `POST /api/v1/orders/{id}/cancel`
  - `GET /api/v1/positions`, `GET /api/v1/account/balances`
- Verified sandbox order placement (live) and dry-run behavior.

## 2025-09-14

- Fix: Polygon options snapshot integration
  - Added `PolygonMarket.snapshot_chain()` as a back‑compat alias to `snapshot_option_chain()`.
  - Ensures the assistant route can load option snapshots again.

- Fix: Tradier auth header and env resolution
  - Normalize Bearer token handling (`TRADIER_ACCESS_TOKEN` or `TRADIER_API_KEY`).
  - Resolve token at call time to avoid stale values.

- Fix: Async backoff
  - Replaced blocking `time.sleep()` with `await asyncio.sleep()` in Polygon client retry loop.

- Feature: NBBO sampling and spread stability
  - Added `PolygonMarket.option_quote()` for single‑contract NBBO.
  - Assistant samples NBBO for top picks to compute `spread_stability` and refresh `bid/ask/spread_pct`.

- Feature: Expected Move scaled to horizon
  - EM from straddle is scaled by sqrt(time) for `scalp` and `intraday` horizons.
  - Added to `context.expected_move` and used for hit probabilities.

- Feature: EV scoring (lightweight)
  - New `expected_value_intraday()` in `app/engine/options_scoring.py` approximates EV using delta, EM distances, and slippage from spread.
  - Assistant annotates each pick with `ev` and `ev_detail` when EM is available.

- Fallback: Tradier options chain
  - If Polygon snapshot yields no picks, falls back to `app.services.providers.tradier_chain.options_chain()`.

- Cleanup: Router
  - Archived legacy `app/routers/assistant.py` to `app/routers/assistant_legacy.py`.
  - `app/main.py` uses `assistant_api` and `diag` only.

- Docs:
  - Created this `docs/PROGRESS.md` log.
  - Added `docs/ROADMAP.md` and `docs/CONFIDENCE.md` (EM horizon scaling, scoring components).

### Later on 2025-09-14 (IV Rank + Liquidity Trend)

- Feature: IV Percentiles per expiry
  - Compute IV percentile from the snapshot chain (or Tradier chain fallback) filtered to the target expiry.
  - Picks now include `iv_percentile`, `oi_percentile`, `vol_percentile`.
  - `tradeability_score` uses `iv_percentile` when present via a mid‑range preference.

- Feature: Liquidity trend proxy
  - Picks include `vol_oi_ratio` (today’s volume divided by open interest) as a turnover proxy.
  - `tradeability_score` liquidity component blends base OI/volume with the turnover proxy.

- Files
  - Updated `app/routers/assistant_api.py` to attach percentiles/ratio and feed them into scoring.
  - Updated `app/engine/options_scoring.py` to incorporate IV percentile and volume/oi ratio in the score.
  - Added `app/services/iv_surface.py` (multi‑expiry IV surface with TTL cache) and `app/services/state_store.py` (tiny JSON persistence for daily OI/volume aggregates and trends).

### Later on 2025-09-14 (Moneyness Buckets + Rate Limits)

### Later on 2025-09-14 (Market Overview + Hedge Endpoint)

### Later on 2025-09-14 (Option B Interactive Chart)

- Feature: Interactive chart (server HTML with client-side rendering)
  - New `GET /charts/proposal` returning a Lightweight Charts page.
  - Query params: `symbol`, `interval` (1m/5m/1d), `lookback`, `overlays` (vwap,ema20,ema50), and optional `entry,sl,tp1,tp2` lines.
  - Uses `GET /api/v1/market/bars` to fetch OHLCV; computes VWAP and EMAs client-side.
  - Minimal bandwidth; no extra token cost; link-friendly for GPT. Rollback by not linking.

- Feature: Bars data endpoint
  - New `GET /api/v1/market/bars` serving recent Polygon OHLCV for 1m/5m/daily.

### Later on 2025-09-14 (Chart links + fixes)

- Assistant now includes a ready `chart_url` for each options pick
  - Prebuilt link to `/charts/proposal` with overlays, Entry/SL/TP1/TP2, EM rails, hit probabilities, confluence tags, and a beginner plan blurb.
  - Uses `PUBLIC_BASE_URL` when present; falls back to Railway URL.

- Charts hardened
  - Converted HTML to use `string.Template` (no Python f-string braces) to fix import/runtime crashes.
  - Added CDN fallback (jsdelivr) if unpkg is blocked; shows helpful error messages instead of a blank page.
  - Absolute API URLs via `window.location.origin` so fetches work behind proxies.
  - Interval fallback inside the page: try `1m`, then `5m`, then `1d` to avoid empty charts off-hours.

### Later on 2025-09-14 (Chart UX for beginners)

- Labels
  - Price lines: "Entry", "Stop Loss", "Target 1", "Target 2"; EM rails as "EM Upper/Lower".
  - Pivot labels spelled out: Pivot (P), Resistance 1/2, Support 1/2.

- Strategy Plan panel
  - Auto-bulleted plan with: confirmation → entry retest, targets from EM, probabilities, stop-loss behavior, and when to skip/size down.
  - Accepts a custom `plan` query param (pipe `|` delimited) to override text.

- Toolbar simplified
  - Timeframe picker (1m/5m/1d), Fit, Refresh. Removed overlay toggles to reduce clutter.
  - Legend shows human-friendly overlays (VWAP + EMA20 + EMA50 + Pivots). Chart auto-fits to viewport and data.

- Feature: Market overview endpoint
  - New `GET /api/v1/market/overview` summarizing indices (SPY, QQQ) and sector ETFs.
  - Returns last, daily change %, intraday VWAP/sigma, RVOL(5), and regime metrics where available.
  - Includes simple leaders (up/down) and per‑symbol error capture.

- Feature: Hedge/Repair endpoint (Phase 3)
  - `POST /api/v1/assistant/hedge` with positions → suggestions (vertical cap of naked shorts, protective puts for stock) and NBBO on protective legs.
  - Computes approximate net Greeks using IV surface buckets and Black‑Scholes.

- Feature: Risk Flags (Phase 5)
  - Snapshot response includes `context.risk_flags` for quick caution overlays.

- Feature: IV surface moneyness buckets
  - IV surface now groups per expiry by moneyness buckets: `atm` (≤1%), `near` (≤3%), `far` (>3%).
  - Percentiles for each pick are computed from the bucket matching its strike vs last price; falls back to overall list.

- Feature: In‑process rate limiting
  - Added `app/services/rate_limiter.py` (token bucket) with env knobs `POLYGON_API_RATE`, `TRADIER_API_RATE` (fallback `POLL_API_RATE`).
  - Integrated into Polygon `_get`/`option_quote` and Tradier `quote_last`/`options_chain`.

## 2025-10-02

- Index support and ODTE quality gates
  - Polygon indices: map `SPX→I:SPX` and `NDX→I:NDX` for aggs (minute/daily). Robust `last_price` falls back to minutes/dailies when snapshots don’t apply.
    - File: `app/services/providers/polygon_market.py`
  - Index options: prefer Tradier chains for SPX/NDX; skip Polygon option‑chain attempts for indices. If no chain is available, surface a precise limitation note instead of generic filler.
    - File: `app/routers/assistant_api.py`
  - Charts & levels: SPX charts map to SPY; NDX charts map to QQQ.
    - File: `app/routers/assistant_api.py`
  - Levels via ETF proxy: SPX/NDX levels computed via SPY/QQQ proxy and labeled with `levels_source` plus `index_proxy_note` for the model/UI.
    - Files: `app/routers/market_data.py` and assistant API context wiring
- ODTE quality gate: after NBBO sampling, `options.top` is tightened to require `spread_stability ≥ 0.6` when available to prevent poor 0DTE fills.
  - File: `app/routers/assistant_api.py`
- Intraday index bias: for index + intraday with no expiry provided, automatically bias to today’s expiry (`odte`) for focused picks.
  - File: `app/routers/assistant_api.py`
- Order-flow tape & market internals:
  - Distilled order-flow score per option pick from NBBO sampling (`order_flow_score`, `order_flow_bias`, deltas) plus aggregate summary under `context.order_flow`.
    - File: `app/routers/assistant_api.py`
  - Market internals panel (`context.market_internals`) showing adv/decl breadth, TICK bias, sector tilt, and notes/bias score for quick sizing guidance.
    - File: `app/routers/assistant_api.py`
- Setups board + TradingView links
  - `scan_top_setups()` ranks multi timeframe breakout/retest candidates across top movers (daily, 4h, 1h alignment) with liquidity and rVol adjustments.
    - Files: `app/services/providers/polygon_market.py`, `app/services/setup_scanner.py`
  - New endpoint `GET /api/v1/market/setups?limit=10` serving top-ranked ideas with per-timeframe notes.
    - File: `app/routers/setups.py`, wired in `app/main.py`
  - Added `/charts/tradingview` page generating shareable TradingView widgets with entry/stop/target overlays.
    - File: `app/routers/charts.py`
- October refinements
  - Setups scanner now blends multi-TF alignment, price/liquidity, options tradability (scalp/intraday/swing/leaps) and rVol/trend into a composite confidence score. Filters remove low-priced illiquid names unless option spreads pass quality gates.
    - Files: `app/services/setup_scanner.py`, `app/services/providers/tradier_chain.py`, `app/routers/setups.py`, `app/routers/assistant_api.py`
  - Options scoring pulls Tradier expirations, near-ATM contracts, performs Polygon NBBO sampling, assigns A/B/C grades, and surfaces a preferred contract per horizon. Confidence grades (High/Moderate/Cautious) and clickable TradingView links are included per setup.
  - Trade plan output now references expected-move bands instead of recycled TP probabilities for clearer guidance.
  - Targeted scans (symbols=) now guarantee best-available guidance: if strict quality gates reject all ideas, the API returns the highest-ranked fallback (A/B grades; grade C allowed only for liquid blue chips) and, when nothing survives, auto-fetches an intraday snapshot to build a plan.
    - Files: `app/services/setup_scanner.py`, `app/routers/assistant_api.py`

- Commits
  - `ab78d79` Index support: map SPX/NDX to Polygon indices (I:SPX/I:NDX); prefer Tradier chains for index options; map charts/levels to SPY/QQQ
  - `6d33b56` Enhancements: index proxy notes, ODTE stability gate, intraday index bias, and Polygon index mapping

- How to test quickly
  - Providers: `{"op":"diag.providers","args":{}}` → confirm `polygon_key_present`, `tradier_token_present`.
  - SPX 0DTE snapshot:
    - `{"op":"data.snapshot","args":{"symbols":["SPX"],"horizon":"intraday","include":["options"],"options":{"odte":true,"expiry":"today","topK":8,"maxSpreadPct":12,"greeks":true}}}`
    - Expect: `options.top` with human‑readable contracts, `expected_move`, `key_levels` (via SPY), `fibonacci`, `chart_url` (SPY), `hit_probabilities`; if no chain available, a clear "index options depend on brokerage provider" note.
  - NDX 0DTE snapshot similarly (levels via QQQ). Verify ODTE gates: picks either show `spread_stability ≥ 0.6` or are filtered out.

- Prompt additions (guidance to LLM)
  - For SPX/NDX: require `data.snapshot` with `{"options":{"odte":true,"expiry":"today"}}`.
  - If `options.top[]` is empty or index note present, return that limitation only; ask if SPY/QQQ proxy is acceptable; do not draft a generic plan.
  - When context contains `index_proxy_note`, reference it in Key Levels (e.g., “Levels via SPY proxy”).

- Optional next steps (Polygon enhancements)
  - Smarter ODTE ranking: prioritize by (a) `spread_stability`, (b) delta closeness to 0.45, (c) `iv_percentile` mid‑range, (d) `vol_oi_ratio`. Expose composite score to the LLM.
  - Intraday statistical bands: add server‑side minute‑VWAP σ bands and recent RVOL percentile to context; boost confidence when confluence with TP/levels occurs.
  - Event overlay: integrate earnings/macro timestamps into context and suppress plans that collide with imminent high‑impact events unless explicitly asked.
## 2025-10-06 — Production Point 2

- Targets/Stops: horizon-aware sizing aligned to real trader behavior
  - Uses EM from straddle with ATR(14) fallback; scales by remaining session for intraday/scalp; adds IV percentile regime scaling.
  - Floors via R-multiples (T1 ≥ 1.0R, T2 ≥ 1.6R) and confluence snapping to pivots/fibs; minimum TP spacing enforced.
- Charts: proposal-only (no TradingView), 15m for intraday/swing, 1d for leaps
  - Auto-synthesize TP1/TP2 from entry/stop when omitted with the same engine as backend.
  - Labeled overlays (VWAP, EMA20/50, Pivots, Current price). Confluence/Liquidity badges prettified.
- Options horizon windows (applied before contract selection)
  - scalp 0–1 DTE; intraday 0–7; swing 7–90; leap 180–540.
  - Tradier fallback selects expiry via `expirations()` inside the window, with progressive widening.
- Performance & reliability
  - Suppress Polygon 404 noise, add negative caching; cap NBBO sampling during RTH only; EM/ATR per-symbol cache.
- Links: chart_url and chart_link (markdown) consistently available; prompt renders a clickable “View This Plan”.

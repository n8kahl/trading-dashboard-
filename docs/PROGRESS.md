# Progress Log

This document tracks code and docs changes so work can be resumed easily in a new session.

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

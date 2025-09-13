# Confidence Scoring — Design

This document specifies how trade idea confidence is computed using real market data. It defines inputs, normalization, feature engineering, and aggregation into a 0–100 confidence score (and a 0–1 value for the coach).

## Data Integrity & Freshness
- Source: Polygon (minute bars WS + HTTP aggregates), Tradier (orders/positions), optional Polygon trades for order flow.
- Session: New York (RTH 09:30–16:00). Anchors and ranges use NY local time.
- Freshness: last bar age ≤ 5s (WS) or ≤ 60s (HTTP) for intraday features. Age penalty otherwise.
- Adjusted data: use `adjusted=true` aggregates. Ignore bars missing `o,h,l,c,v,t`.

## Intraday Feature Set (per symbol)
- Price context
  - last_price: close of most recent 1m bar
  - prev_day_high/low: extracted from daily bars
  - opening_range_high/low: first 30m RTH window
- VWAP
  - vwap_rth: anchored VWAP from today’s RTH open index
  - vwap_prev: anchored VWAP from prior close index (if available)
  - dist_vwap_pct: (price − vwap_rth) / vwap_rth × 100
  - bars_above_vwap: consecutive bars above vwap_rth (cap at 3)
- EMAs
  - ema9, ema20, ema50 on 1m closes; posture flags: ema9>ema20, ema20>ema50
  - multi‑TF posture: ema stack on 5m closes (consistency bonus)
  - dist_ema20_pct: (price − ema20) / ema20 × 100
- ATR (volatility)
  - atr_1m: 14‑period ATR on 1m bars
  - atr_1m_pct: atr_1m / price × 100
  - regime tag: low (<1%), normal (1–4%), high (4–8%), extreme (>8%)
- Volume & Order Flow
  - rvol_5: average of last 5 1m vols ÷ series median
  - obv_slope_10: OBV slope over last 10 bars (approx order flow bias)
  - cvd_approx_20: sum(sign(close−open)×vol) over last 20 bars
  - optional tick‑level CVD: if Polygon Trades API available, classify uptick/downtick using NBBO and sum size
- Liquidity (options context)
  - spread_pct: (ask − bid) / mid × 100
  - open_interest, volume: normalized to peer percentiles

## Normalization
- All features mapped to bounded components in [−X, +X] to avoid domination.
- Examples
  - vwap_posture: +[5..15] if price > vwap with bars_above_vwap scaling; −10 if below
  - ema_stack: +[10..25] if 9>20>50 (and 5m agrees), −[8..15] if bearish
  - atr_regime: −5 if extreme low (<1%) or +2 if normal; −3 if extreme high (>8%) for scalps
  - dist_ema20_pct: clamp to ±10 via linear mapping
  - rvol_5: +[7..15] if ≥1.1/1.5; −5 if <1.0
  - cvd/obv: +[4..10] if slope positive and rising; −[4..10] if negative
  - liquidity: +10 if spread ≤5%, +4 if ≤8%, −8 otherwise

## Strategy‑Aware Aggregation
- For each strategy (VWAP bounce, EMA crossover, ORB, Power Hour), apply tailored weights; see `app/services/scoring_engine.py`.
- Add missing features here:
  - Include `atr_1m_pct`, `dist_vwap_pct`, `dist_ema20_pct`, `cvd_approx_20`, `obv_slope_10`, `ema_mtf_agree` in score components.
- Confidence = clamp(0..100) with band mapping: favorable≥70, mixed≥50, unfavorable<50.
- Coach confidence (0–1) = logistic(score/100) × data_quality_multiplier.

## Data Quality Multiplier
- Inputs: last_bar_age, bars_count (≥90 for intraday), presence of vwap/ema/atr.
- Multiplier m in [0.6, 1.0]. Missing critical feature or stale data reduces confidence.

## Implementation Plan
- Extend context composition (`app/services/compose.py`)
  - Replace simple VWAP with RTH‑anchored aVWAPs via `app/services/ta.py` (`avwaps_for_today`).
  - Add `atr_1m_pct`, `dist_vwap_pct`, `dist_ema20_pct`, multi‑TF EMA posture, `obv_slope_10`, `cvd_approx_20`.
  - Include `data_freshness_sec` and `bars_count` for quality multiplier.
- Update scoring engine (`app/services/scoring_engine.py`)
  - Consume new fields and add bounded components as above per strategy.
  - Return `{ score, band, components, rationale }` with explicit contributions including ATR and order‑flow.
- Calibrate weights (`app/config/weights.py`)
  - Day‑phase multipliers (open/mid/power) for components: rvol, momentum, vwap proximity, atr regime.
- Order flow optional path
  - If Polygon Trades API available, compute tick‑level CVD; else fall back to bar‑based `cvd_approx_20`.
- Testing
  - Unit tests for indicators (EMA/ATR/aVWAP/OBV/CVD approx) with deterministic arrays.
  - Integration tests for scoring given canned minute bar series (no network).

## Example Context and Score (intraday)
```
{
  "symbol": "TSLA", "price": 244.10,
  "vwap_rth": 243.80, "dist_vwap_pct": 0.12, "bars_above_vwap": 2,
  "ema9": 244.00, "ema20": 243.70, "ema50": 242.90, "ema_mtf_agree": true,
  "dist_ema20_pct": 0.16,
  "atr_1m_pct": 2.3, "rvol_5": 1.4,
  "cvd_approx_20": 1.8e6, "obv_slope_10": 0.7,
  "opening_range_high": 245.2, "opening_range_low": 242.1,
  "data_freshness_sec": 3, "bars_count": 180
}
→ VWAP Bounce: score 78 (favorable): { vwap_posture:+11, ema_stack:+12, rvol:+7, atr_regime:+2, cvd:+6, dist_ema20:+4, liquidity:+4, … }
```

## UX Notes
- Show component breakdown under each suggestion: ATR, VWAP, EMAs, Order Flow, Liquidity.
- Surface confidence band with color and a one‑line rationale (“Why now?”).
- Allow users to tweak weights in Settings (advanced), persisted to DB.


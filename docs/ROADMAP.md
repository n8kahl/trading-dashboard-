# Roadmap

Focus: improve data quality, trade selection accuracy, and realistic expectancy.

## Near Term (1–2 weeks)

- IV Rank and Surface Context
  - Implemented basic IV percentile per expiry for snapshot chains; feeding into scoring. Next: expand to multi‑expiry surface and cache.

- OI/Volume Liquidity Trend
  - Track open interest and compare today’s volume versus recent sessions.
  - Favor persistent liquidity; penalize one‑off spikes.

- NBBO Sampler Expansion
  - Sample 3–5 times over ~60s for top 10–15 candidates with concurrency limits.
  - Use spread variance and quote refresh rate in tradeability.

- EV Scoring Calibration
  - Validate EV proxy against historical intraday outcomes.
  - Tune TP/SL distances and slippage factors by symbol/expiry bucket.

- Data Reliability & Fallbacks
  - Add light retry/backoff to Tradier calls, unify error surfaces across providers.
  - Persist provider errors in metrics for observability.

## Mid Term (3–6 weeks)

- Microstructure Enhancements
  - Incorporate trade prints cadence (Polygon `/v3/trades/options/{symbol}`) to measure tape quality.
  - Compute trade/quote ratio and stale‑book detection.

- Risk & Portfolio Guardrails
  - Enforce per‑symbol and per‑session risk caps (R, max concurrent), surfaced in assistant responses.
  - Score thresholds gated by regime; block trades in poor conditions.

- Historical Volatility Alignment
  - Compute short‑horizon HV from 1m returns; compare IV/HV ratios by horizon.
  - Penalize chasing rich IV when HV is low for intraday scalps.

- Backtesting & Metrics
  - Add light backtest harness for intraday recommendations to validate EV and hit probabilities.
  - Track PnL distribution, slippage, and latency impact of NBBO sampling.

## Longer Term

- Position Management Intelligence
  - Adaptive trailing based on regime and EM drift; partial exits tied to spread and liquidity.

- Multi‑Provider Aggregation
  - Merge quotes across venues, de‑duplicate, and pick best NBBO for more reliable spread estimates.

- UI/UX
  - Surface per‑contract EV, tradeability, spread stability, and IV rank in the dashboard with tooltips.

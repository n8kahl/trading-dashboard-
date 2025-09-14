# Confidence & Scoring Notes

This summarizes how we derive intraday confidence and targets.

## Expected Move (EM)

- Base EM comes from near‑ATM straddle mid (call + put mids).
- Horizon scaling: EM at expiry is scaled to the desired horizon via a sqrt(time) rule.
  - For `scalp` (~2h) and `intraday` (~6.5h), scale by `(horizon_hours / hours_to_expiry) ** 0.5`.
  - We use this scaled EM for hit‑probability estimates and target scaffolding.

## Hit Probabilities

- We approximate the probability of touching a barrier at distance `d` using a Brownian‑motion bound:
  - `P(touch ≥ d) ≈ 2 * (1 - Φ(d / σ))`, where `σ` ≈ horizon‑scaled EM.
  - Used to estimate odds of hitting TP tiers (25%, 50% EM).

## Tradeability Score

Components weighted for intraday:
- Delta fit vs target (0.40)
- Spread stability/width (0.25)
- Liquidity (OI/Volume) (0.20)
- IV percentile (0.10)
- Quote age (0.05)

NBBO sampling improves the spread component by measuring spread variance and quote freshness.

## EV (Expected Value) Proxy

- For ranking only (not pricing):
  - TP at +0.5*EM, SL at −0.25*EM on the underlying.
  - Option move ≈ `delta * ΔS`.
  - Roundtrip slippage ≈ a fraction of the spread per side.
  - `EV ≈ p(TP)*max(gain − slippage) − p(SL)*max(loss + slippage)` with a small dependency adjustment.

Future: calibrate distances, slippage, and dependency using realized outcomes.


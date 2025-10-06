# TODO

## 2025-09-16 — Production Ready
- [x] Horizon-aware TP/SL engine: EM + ATR fallback, IV percentile scaling, remaining-session adjustment, confluence snapping, minimum spacing.
- [x] Proposal charts label VWAP/EMA/Pivots/current price and auto-synthesize targets to match backend logic.
- [x] Leap horizon now defaults to ~6M expiry; fallback snapshots respect requested horizon.
- [x] Execution guidance standardized (limit at mid).

## 2025-10-06 — Production Point 2
- [x] Apply DTE windows before option selection: scalp 0–1d, intraday 0–7d, swing 7–90d, leap 180–540d.
- [x] Tradier fallback: resolve expiry via `expirations()` inside window, widen if empty.
- [x] Tighten intraday targets: EM remaining-session scaling, IVP modulation, R floors, confluence snapping, minimum spacing.
- [x] Reduce provider noise and latency: 404 suppression + cache, NBBO limited during RTH, short-lived EM/ATR cache.

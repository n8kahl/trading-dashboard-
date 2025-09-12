# Trading Assistant — Architecture & Product Overview

_Last updated: September 2025_

---

## 1) Vision & Goals

**Primary mission:** a practical, data-driven trading assistant that:
1. **Finds trades** with a transparent _confluence score_.
2. **Helps manage trades** in real time (entries, risk, scaling, targets, alerts).
3. **Reviews trades** (journaling + feedback loop).
4. **Plans pre-market** (indices overview, levels, watchlist, suggested alerts).

**Design principles**
- **Explainability:** every suggestion includes “why” with inputs + weights.
- **Resilience:** graceful fallbacks (daily timeframe when minute data unavailable).
- **APIs first:** everything exposed via clean HTTP endpoints.
- **Modular:** strategies, screeners, and alert logic are swappable.
- **Action-ready:** optimized for ChatGPT Actions.

---

## 2) High-Level Architecture
ChatGPT (Actions) ──► FastAPI Service (Railway)
├─ Routers
│   ├─ /strategies
│   ├─ /options
│   ├─ /screener
│   ├─ /alerts
│   ├─ /premarket
│   ├─ /journal
│   └─ /backtest
├─ Services
│   ├─ Market stream (Polygon)
│   ├─ Indicators (EMA, VWAP, RSI, MACD, ATR)
│   ├─ Strategy engine (scoring)
│   ├─ Options picker
│   ├─ Alerts store
│   └─ Journal store
└─ Persistence
├─ Postgres (Railway) — alerts, journal
└─ In-memory caches — watchlist, bars
- **Cloud runtime:** Railway (Docker)  
- **Data:** Polygon.io (stream + REST)  
- **Assistant UX:** ChatGPT Action calling API + KB docs  

---

## 3) Endpoints (Canonical)

- **Strategies**
  - `POST /api/v1/strategies/evaluate`
  - `POST /api/v1/strategies/suggest-trade`
- **Options**
  - `POST /api/v1/options/pick`
- **Screener**
  - `POST /api/v1/screener/watchlist/start`
  - `GET  /api/v1/screener/watchlist/get`
  - `GET  /api/v1/screener/watchlist/ranked`
  - `POST /api/v1/screener/watchlist/stop`
- **Alerts**
  - `POST /api/v1/alerts/set`
  - `GET  /api/v1/alerts/list`
  - `GET  /api/v1/alerts/recent-triggers`
- **Pre-Market**
  - `POST /api/v1/premarket/analysis`
- **Journal & Backtest**
  - `POST /api/v1/journal/trade`
  - `GET  /api/v1/journal/summary`
  - `POST /api/v1/backtest/quick`
- **Ops/Debug**
  - `GET /healthz`, `GET /router-status`, `GET /api/v1/diag/echo`

---

## 4) Data & Calculations

### Indicators
- EMA, VWAP, RSI(14), MACD(12/26/9), ATR(14)

### Key Levels
- Prior day high/low/close, overnight high/low, pre-market range, swing points, pivots (future).

### Confluence Score (0–100)
- **Trend (0–30):** EMA alignment, HH/HL, distance to 50EMA  
- **Momentum (0–30):** RSI regimes, MACD slope/divergence, VWAP relation  
- **Levels (0–25):** Proximity to key levels, liquidity grabs  
- **Mean-Reversion (0–15):** RSI extremes + reclaims  
- **Modifiers:** Power Hour (+0–5), volatility filters  

### Strategy Library
- **Trend-pullback** (EMA8/21 entries)  
- **VWAP reclaim/failure**  
- **Range break & retest**  
- **Divergence catch**  

Each strategy has **preconditions**, **entry/stop rules**, **TP ladder**, **sizing guidance**.

### Options Picker
- **Short (0–2 DTE):** delta 0.35–0.60, spread <5%, OI ≥1000  
- **Swing (2–3 weeks):** delta 0.30–0.50, spread <8%, OI ≥500  
- Output: 2–4 contracts with rationale  

### Risk & Trade Plan
- **Entry, Stop, TP1/TP2, R:R, Size**  
- **Alerts** for entry/stop/TP  

---

## 5) User Flows

### Find me a trade
1. Screener → ranked list  
2. Evaluate symbol  
3. Suggest plan  
4. Pick contracts  
5. Set alerts  

### Help me manage a trade
- Update risk (move stops, trail, scale)  
- Maintain alerts  
- Continuous guidance  

### Review my trade
- Log → `/journal/trade`  
- Summary → `/journal/summary`  
- Feedback: strengths/weaknesses  

### Pre-market
- Indices + levels  
- Suggested alerts/watchlist  

---

## 6) Future Enhancements

- **Strategy expansion**: add breakout, liquidity grabs, volatility squeeze  
- **ML feedback loop**: learn from logged trades + outcomes  
- **Level auto-detection**: anchored VWAPs, volume profile nodes  
- **Improved journaling**: screenshots, chart annotation  
- **Community version**: safe mode (assistant only, no auto-trading)  
- **Broker integration**: Tradier / IBKR for real execution  
- **Live dashboards**: show watchlist, trades, PnL  

---

## 7) Key Decisions

- **Polygon.io** chosen for data reliability + websockets  
- **Postgres (Railway)** used for persistence (alerts, journal)  
- **ChatGPT Actions** over MCP for now (schema-based, stable)  
- **Explainability-first** (scores + rationale are logged)  
- **Two-product path**:  
  - (A) Auto-trading bot (broker integrated)  
  - (B) Trade assistant (manual input + guidance, safer for community use)  

---

## 8) Restore / Setup

- **Action schema**: `docs/actions/openapi_combined.yaml`  
- **KB docs**: `docs/gpt/*.md`  
- **System prompt**: `docs/prompts/system_prompt.md`  
- **This overview**: `docs/ARCHITECTURE_OVERVIEW.md`  

Clone repo + follow `README_FOR_GPT_SETUP.md` to re-register Action + KB + prompt.  

---

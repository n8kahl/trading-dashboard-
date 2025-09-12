# Strategy Usage Guide
- **Evaluate**: POST `/api/v1/strategies/evaluate` → `{"symbol":"AAPL","timeframe":"day"}`
- **Suggest Trade**: POST `/api/v1/strategies/suggest-trade` → `{"symbol":"AAPL","timeframe":"day"}`
Confluence considers trend (EMA alignment), momentum (RSI/MACD/VWAP), levels, mean-reversion. Check `market_open` & data freshness.

# Screener Workflow
1) Start: POST `/api/v1/screener/watchlist/start` → `{"symbols":["AAPL","MSFT","NVDA"]}`
2) Ranked: GET `/api/v1/screener/watchlist/ranked?n_bars=120`
3) Get: GET `/api/v1/screener/watchlist/get`
4) Stop: POST `/api/v1/screener/watchlist/stop`
Use top ranked → evaluate → suggest-trade.

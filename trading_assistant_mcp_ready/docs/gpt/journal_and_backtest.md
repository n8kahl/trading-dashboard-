# Journal & Backtest
- Journal trade: POST `/api/v1/journal/trade`
\`\`\`json
{"symbol":"AAPL","side":"CALL","entry":190,"stop":188,"tp1":192,"notes":"EMA confluence"}
\`\`\`
- Summary: GET `/api/v1/journal/summary?days=30`
- Backtest quick: POST `/api/v1/backtest/quick`
\`\`\`json
{"symbol":"SPY","timeframe":"day","lookback":160}
\`\`\`

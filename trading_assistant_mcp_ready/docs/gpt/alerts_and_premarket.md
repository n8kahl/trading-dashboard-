# Alerts & Pre-Market
- Create alert: POST `/api/v1/alerts/set`
\`\`\`json
{"symbol":"SPY","timeframe":"minute","condition":{"type":"price_above","value":500}}
\`\`\`
- List alerts: GET `/api/v1/alerts/list`
- Recent triggers: GET `/api/v1/alerts/recent-triggers?limit=10`

Pre-Market: POST `/api/v1/premarket/analysis`
\`\`\`json
{"watchlist":["AAPL","MSFT","NVDA"],"lookback":120}
\`\`\`

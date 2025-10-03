# Solo Trader Setup (Lean Stack & Costs)

If this is just for you (not a team or SaaS product), here’s a lean setup that keeps costs low while still giving you institutional‑style edge.

## 1. Hosting & Infrastructure

For one person, you don’t need a k8s cluster or enterprise observability. A lean but reliable setup is plenty:

- Compute:
  - Small cloud VM (AWS Lightsail, DigitalOcean Droplet, or Hetzner) with 2–4 vCPUs, 8–16 GB RAM.
  - Cost: $20–40/month.
- Data Storage:
  - TimescaleDB/Postgres for trades + features (runs fine on same VM).
  - Object storage (S3-compatible, e.g., Backblaze B2) for logs/backtests.
  - Cost: $5–10/month unless you hoard terabytes.
- Monitoring:
  - Lightweight Grafana + Prometheus container.
  - Alerts piped to Discord/Slack. Free.

## 2. Data Feeds & Brokerage

- Polygon.io
  - Free tier: 5 API calls/min, delayed in some cases. Good for backtests/side data.
  - Paid:
    - Stock Basics Real‑Time ($49/mo).
    - Options Data (basic chains) add‑on ~$49/mo.
    - If you want full NBBO + trades, you’re closer to $199–299/mo.
- Tradier Brokerage
  - API is free if you’re an account holder.
  - Commissions: $0 for equities, $0.35 per options contract.
  - No recurring cost beyond what you trade.

## 3. NLP / ML Layer

- OpenAI (for post‑trade analysis & GPT refinement)
  - GPT‑4o mini (fast + cheap) for logs and QA: ~$5–10/month for light use.
  - Occasional GPT‑4o calls for deeper analysis: maybe $20–30/month.
  - Total: $30–40/month unless you hammer it with thousands of logs.

## 4. Development / Backtesting

- Run backtests locally on your machine with DuckDB + Parquet.
- Store logs + configs in GitHub (free/private repo).
- You don’t need enterprise CI/CD — just Docker Compose with versioned configs.

## 5. Expected All‑In Monthly Costs

- Hosting: $30
- Polygon: $49–199 (depends on tier you want)
- OpenAI: $30
- Storage/Monitoring: $10

Range: $100–250/month all‑in, comfortably under what one decent trade pays for if your edge is real.

## 6. Simplifications Since It’s Just You

- No team dashboards. Alerts → Discord DM is enough.
- Skip SPX/NDX until you prove edge. Trade SPY/QQQ first; SPX slippage will eat you alive unless you scale up.
- One VM, not microservices. Run Postgres + feature engine + strategy in Docker Compose.
- Manual weekly review. You don’t need an automated bandit re-tuner at first. Let GPT summarize your trade logs and propose tweaks — you accept/reject.
- Failover not critical. If it dies, it’s just you, not a prop desk. You can restart.

## 7. Data Capture & Alerts

- Postgres tables (`trades`, `features`, `logs`) are created automatically on startup via SQLAlchemy. Store executions, derived features, and structured logs with simple REST calls.
- New endpoints: `POST /api/v1/trades`, `GET /api/v1/trades`, `POST /api/v1/features`, `POST /api/v1/logs`, and filtered list variants. See `docs/USAGE.md` for payload examples.
- Set `DISCORD_WEBHOOK_URL` to receive error/critical log alerts (and optional trade pings) in a personal Discord channel.
- Default `DATABASE_URL` points at the compose `db` service; locally it falls back to `sqlite+aiosqlite:///local.db` so you can test without Postgres.

See the step-by-step implementation plan in `docs/IMPLEMENTATION_PLAN.md`.
For one-VM deployment instructions, see `docs/DEPLOY_WITH_COMPOSE.md`.

---

# Project Overview (Original README)

This section preserves the original README for reference.

## tradingassistantmcpreadymain1

Automatically synced with your v0.app deployments.

[Deployed on Vercel](https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1)
[Built with v0](https://v0.app/chat/projects/YqW6wWyJI6J)

### Overview

This repository will stay in sync with your deployed chats on v0.app. Any changes you make to your deployed app will be automatically pushed to this repository from v0.app.

### Repository Structure

- `app/` – FastAPI backend service
- `trading-dashboard/` – Next.js frontend dashboard

### Deployment

Your project is live at:

https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1

See `docs/DEPLOYMENT.md` for a status checklist and how to verify the Vercel deployment (including required environment vars and WS notes).

### Build your app

Continue building your app on:

https://v0.app/chat/projects/YqW6wWyJI6J

### How It Works

1. Create and modify your project using v0.app
2. Deploy your chats from the v0 interface
3. Changes are automatically pushed to this repository
4. Vercel deploys the latest version from this repository

### Environment

The backend reads the following environment variables:

- `API_KEY` – required; gates sensitive routes via `X-API-Key`.
- `WS_SECRET` – optional; signs short‑lived WS tokens minted at `/api/v1/auth/ws-token`.
- `TRADIER_BASE` – Tradier API base URL (defaults to sandbox)
- `TRADIER_ACCESS_TOKEN` – Tradier access token
- `POLYGON_API_KEY` – optional key for Polygon quotes
- `CHATDATA_API_KEY` – API key for chat-data.com (required for AI Coach)
- `CHATDATA_BASE_URL` – optional API base (default `https://api.chat-data.com`)
- `CHATDATA_API_PATH` – optional path (default `/v1/chat/completions`)
- `CHATDATA_MODEL` – optional model ID to use
- `YOUTUBE_API_KEY` – optional; enables YouTube premarket ingestion (Data API)
- `YT_CHANNEL_ID` – optional channel ID (UC…); used with API or RSS
- `YT_CHANNEL_URL` – optional channel/handle URL (e.g., https://www.youtube.com/@BrettCorrigan); resolves ID via public page and uses RSS (no API key)
- `ENABLE_PREMARKET_INGEST` – `1` to fetch latest premarket video transcript on startup and store as a Feature
- `DATABASE_URL` – async SQLAlchemy connection string (defaults to Postgres via `.env.server`; falls back to local SQLite if unset)
- `DISCORD_WEBHOOK_URL` – optional webhook for trade + error notifications
- `DATA_MODE`
- `WS_PING_SEC`
- `RISK_MAX_DAILY_R`
- `RISK_MAX_CONCURRENT`
- `RISK_BLOCK_UNFAVORABLE`
- `RISK_MIN_SCORE`
- `RISK_MAX_DOLLARS`
- `ENABLE_BACKGROUND_LOOPS` – start WS + risk engine on boot (default `0`)
- `ENABLE_ALERTS_POLLER` – start alert poller on boot (default `0`)

### Scope & Design

This app targets a day‑trader command center: intuitive, informative, and profitable.

- Scope and principles: see `docs/SCOPE.md`
- Confidence scoring (ATR, VWAP, EMAs, order flow): see `docs/CONFIDENCE.md`
- Roadmap and milestones: see `docs/ROADMAP.md`

Coach responses and trade suggestions include confidence with a concise component breakdown based on real data (no mocks). The assistant’s behavior adheres to the above design.

Progress is tracked in `docs/ROADMAP.md`. At the start of each session, review and update it.

See `docs/PROGRESS.md` for a concise, session-by-session summary and `docs/DEPLOYMENT.md` for deployment status and checks.

### Alerts Polling

Background price alerts are handled by a single polling loop implemented in `app.services.poller`. The loop checks active alerts every `ALERT_POLL_SEC` seconds and fetches quotes from Polygon. Requests are rate limited via a shared `RateLimiter` utility and database work is performed inside a managed session. The poller can be started with:

```python
from app.services.poller import alerts_poller
asyncio.run(alerts_poller())
```

Environment variables:

- `ALERT_POLL_SEC` – seconds between polling passes (default `30`).
- `POLL_API_RATE` – maximum quote requests per second (default `5`).
- `POLYGON_API_KEY` – API key used for quote requests.

`/api/v1/diag/config` reports whether each value is loaded.

### WebSocket

Run the FastAPI app with `uvicorn app.main:app`.

Auth options:
- Preferred: fetch `token` from `GET /api/v1/auth/ws-token` then connect `ws://<host>/ws?token=<token>`.
- Legacy: connect with `ws://<host>/ws?api_key=<API_KEY>`.

Heartbeats are sent every `WS_PING_SEC` seconds; the connection manager drops unresponsive sockets.

### AI Coach (chat-data.com)

- Single action: `POST /api/v1/assistant/exec` with body `{ "op": <name>, "args": { ... } }`.
  - Primary ops exposed to Chat-Data: `diag.health`, `diag.providers`, `assistant.actions`, `market.overview`, `assistant.hedge`.
  - Legacy support: `data.snapshot` remains available for rich symbol snapshots (options, EM, risk flags).
  - `assistant.actions` returns the active op lists plus provider diagnostics for tool planning.
- Backend route: `POST /api/v1/coach/chat`
  - Body: `{ messages: [{role, content}], stream?: false }`
  - Uses an OpenAI-compatible API on chat-data.com and calls the single action above.
- Key levels: snapshots now stitch in prior-session highs/lows, pre-market extremes, classic pivots, and Fibonacci retracements/extensions. Strategy plans call these out when take-profit or stop targets overlap them so the coach can reason about nearby supply/demand pockets.

Confidence: All ideas include a 0–100 confidence and a brief rationale using ATR, VWAP, EMA posture, order‑flow (RVOL/OBV/CVD approx), and liquidity, per `docs/CONFIDENCE.md`.

### Large Assets

Large documentation archives or starter bundles are provided via release assets or external storage. Please download them separately instead of committing them to the repository.

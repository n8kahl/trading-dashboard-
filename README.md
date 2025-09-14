# tradingassistantmcpreadymain1

*Automatically synced with your [v0.app](https://v0.app) deployments*

[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1)
[![Built with v0](https://img.shields.io/badge/Built%20with-v0.app-black?style=for-the-badge)](https://v0.app/chat/projects/YqW6wWyJI6J)

## Overview

This repository will stay in sync with your deployed chats on [v0.app](https://v0.app).
Any changes you make to your deployed app will be automatically pushed to this repository from [v0.app](https://v0.app).

### Repository Structure

- `app/` – FastAPI backend service
- `trading-dashboard/` – Next.js frontend dashboard

## Deployment

Your project is live at:

**[https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1](https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1)**

See `docs/DEPLOYMENT.md` for a status checklist and how to verify the Vercel deployment (including required environment vars and WS notes).

## Build your app

Continue building your app on:

**[https://v0.app/chat/projects/YqW6wWyJI6J](https://v0.app/chat/projects/YqW6wWyJI6J)**

## How It Works

1. Create and modify your project using [v0.app](https://v0.app)
2. Deploy your chats from the v0 interface
3. Changes are automatically pushed to this repository
4. Vercel deploys the latest version from this repository

## Environment

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
- `DATA_MODE`
- `WS_PING_SEC`
- `RISK_MAX_DAILY_R`
- `RISK_MAX_CONCURRENT`
- `RISK_BLOCK_UNFAVORABLE`
- `RISK_MIN_SCORE`
- `RISK_MAX_DOLLARS`
 - `ENABLE_BACKGROUND_LOOPS` – start WS + risk engine on boot (default `0`)
 - `ENABLE_ALERTS_POLLER` – start alert poller on boot (default `0`)

## Scope & Design

This app targets a day‑trader command center: intuitive, informative, and profitable.

- Scope and principles: see `docs/SCOPE.md`
- Confidence scoring (ATR, VWAP, EMAs, order flow): see `docs/CONFIDENCE.md`
- Roadmap and milestones: see `docs/ROADMAP.md`

Coach responses and trade suggestions include confidence with a concise component breakdown based on real data (no mocks). The assistant’s behavior adheres to the above design.

Progress is tracked in `docs/ROADMAP.md`. At the start of each session, review and update it.

See `docs/PROGRESS.md` for a concise, session-by-session summary and `docs/DEPLOYMENT.md` for deployment status and checks.

### Alerts Polling

Background price alerts are handled by a single polling loop implemented in
`app.services.poller`. The loop checks active alerts every
`ALERT_POLL_SEC` seconds and fetches quotes from Polygon. Requests are
rate limited via a shared `RateLimiter` utility and database work is
performed inside a managed session. The poller can be started with:

```python
from app.services.poller import alerts_poller
asyncio.run(alerts_poller())
```

Environment variables:

- `ALERT_POLL_SEC` – seconds between polling passes (default `30`).
- `POLL_API_RATE` – maximum quote requests per second (default `5`).
- `POLYGON_API_KEY` – API key used for quote requests.

`/api/v1/diag/config` reports whether each value is loaded.

## WebSocket

Run the FastAPI app with `uvicorn app.main:app`.

Auth options:
- Preferred: fetch `token` from `GET /api/v1/auth/ws-token` then connect `ws://<host>/ws?token=<token>`.
- Legacy: connect with `ws://<host>/ws?api_key=<API_KEY>`.

Heartbeats are sent every `WS_PING_SEC` seconds; the connection manager drops unresponsive sockets.

## AI Coach (chat-data.com)

- Backend route: `POST /api/v1/coach/chat`
  - Body: `{ messages: [{role, content}], stream?: false }`
  - Uses an OpenAI-compatible API on chat-data.com.
  - Advertises and executes tools from `/api/v1/assistant/actions` automatically.

- Frontend page: `trading-dashboard/app/coach/page.tsx`
  - Simple chat UI wired to the backend coach route.
  - Keeps API key server-side.

Confidence: All ideas include a 0–100 confidence and a brief rationale using ATR, VWAP, EMA posture, order‑flow (RVOL/OBV/CVD approx), and liquidity, per `docs/CONFIDENCE.md`.

## Large Assets

Large documentation archives or starter bundles are provided via release assets or external storage. Please download them separately instead of committing them to the repository.

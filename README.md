# tradingassistantmcpreadymain1

*Automatically synced with your [v0.app](https://v0.app) deployments*

[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1)
[![Built with v0](https://img.shields.io/badge/Built%20with-v0.app-black?style=for-the-badge)](https://v0.app/chat/projects/YqW6wWyJI6J)

## Overview

This repository will stay in sync with your deployed chats on [v0.app](https://v0.app).
Any changes you make to your deployed app will be automatically pushed to this repository from [v0.app](https://v0.app).

## Deployment

Your project is live at:

**[https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1](https://vercel.com/n8kahls-projects/v0-tradingassistantmcpreadymain1)**

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

- `TRADIER_BASE` – Tradier API base URL (defaults to sandbox)
- `TRADIER_TOKEN` – Tradier access token
- `POLYGON_API_KEY` – optional key for Polygon quotes
- `DATA_MODE`
- `WS_PING_SEC`
- `RISK_MAX_DAILY_R`
- `RISK_MAX_CONCURRENT`
- `RISK_BLOCK_UNFAVORABLE`
- `RISK_MIN_SCORE`
- `RISK_MAX_DOLLARS`

`/api/v1/diag/config` reports whether each value is loaded.

## WebSocket

Run the FastAPI app with `uvicorn app.main:app`. The dashboard connects to
`ws://<host>/ws` for live updates. Heartbeats are sent every `WS_PING_SEC`
seconds, and the connection manager drops unresponsive sockets.
## Large Assets

Large documentation archives or starter bundles are provided via release assets or external storage. Please download them separately instead of committing them to the repository.


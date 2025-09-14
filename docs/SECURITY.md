Backend Security — API Keys and WS Tokens

Summary
- Sensitive routes are gated by a strict API key dependency.
- WebSocket supports optional short‑lived HMAC tokens.

API Key
- Header: `X-API-Key: <API_KEY>`
- Behavior: server denies requests when `API_KEY` is missing or mismatched (401).
- Sensitive routers: alerts, broker, plan, sizing, compose/analyze, journal, trades, coach, settings, admin.
- Files: `app/security.py`, `app/main.py`.

WebSocket Auth
- Preferred: short‑lived token minted by `GET /api/v1/auth/ws-token` using `WS_SECRET`.
- Connect: `/ws?token=<minted_token>` or use `Authorization: Bearer <token>` (if your client supports headers).
- Legacy: `/ws?api_key=<API_KEY>` continues to work.
- Files: `app/routers/auth.py`, `app/core/ws.py`.

Environment
- `API_KEY` (required) — long random value. Rotate on compromise.
- `WS_SECRET` (optional) — random secret used to sign WS tokens.

Operational Guidance
- Enforce `API_KEY` in all non-public routes. Public routes: `/api/v1/diag/*`, health/ready, and read‑only endpoints you intend to expose.
- Use per‑environment keys and secrets. Do not reuse across staging/production.
- Prefer WS tokens for browsers/apps that can’t safely keep `API_KEY` client‑side.


Trade Narrator — Design (Planned)

Goal
- Stream concise, risk‑aware guidance for a symbol via SSE, backed by real data and Chat Data.

Route (planned)
- `GET /api/v1/coach/stream?symbol=AAPL[&position_id=...]`
- Security: `X-API-Key` required; per‑IP rate limits.
- Cadence: ~3s steady beat; debounce minor changes; significant‑delta triggers future enhancement.

Situation JSON (input to model)
- symbol, price snapshot, timestamps
- confidence snapshot and components (ATR/VWAP/EMA/Flow/Liquidity)
- risk snapshot (daily budget used, per‑trade R limit)
- pace/liquidity, data staleness
- optional: position (avg price, size, unrealized P/L)

Model Call
- Provider: Chat Data (`/v1/chat/completions` with tool‑less JSON response)
- System prompt: instructs JSON‑only guidance with: horizon, band, action, stops/targets, confidence, why
- Fallback: on provider error/invalid JSON, emit a simple guidance object with `ok:false` and reason

Persistence (optional)
- Insert emitted guidance into `narratives` table with `t_ms`, `symbol`, `horizon`, `band`, `guidance_json`, `position_id`.

Client Handling
- SSE messages: `event: data` with `data: { ... }` JSON payload
- UI surfaces guidance, band/horizon, confidence, and why-rationale; past messages available via history endpoint (planned)

Status
- Pending implementation (Y1). Backing models and Alembic baseline are in place.


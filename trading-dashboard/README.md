# Dashboard

## Checklist
- WebSocket status shows "Connected" when backend is running.
- Positions and Orders pages update live without refresh.
- Toast appears when an `alert` message is received over WebSocket.

Run with `pnpm dev` from this directory.

### Environment

- `NEXT_PUBLIC_API_BASE` should point to your FastAPI backend base (e.g., `http://localhost:8000`).

### Design & Confidence

- App scope and architecture: see `../docs/SCOPE.md`
- Confidence scoring (ATR, VWAP, EMAs, order flow): see `../docs/CONFIDENCE.md`
- Roadmap/milestones: see `../docs/ROADMAP.md`

The UI surfaces confidence and a short “why” for each suggestion. Components reflect ATR% regime, VWAP posture, EMA posture, RVOL/flow, and liquidity — computed from live data.

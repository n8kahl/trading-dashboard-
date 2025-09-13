# Progress Log

Lightweight log to record exactly where work left off. Update after each phase/test.

## 2025-09-13
- Added docs: SCOPE, ROADMAP, CONFIDENCE, PHASES, and linked from READMEs and assistant prompt.
- Phase 1: Added `app/__init__.py` and `tests/conftest.py` to fix imports.
- Phase 1: Settings/Journal CRUD tests PASS (`tests/test_settings_journal.py`).
- Phase 2: Implemented ATR%/VWAP/EMA/order-flow signals in `app/services/compose.py` and indicator helpers in `app/services/ta.py`.
- Phase 2: Extended scoring to include `atr_regime`, `dist_ema20`, and `flow` components.
- Phase 2: Added tests `tests/test_confidence_signals.py` — all PASS.
- Phase 3: Implemented Alerts CRUD and refactored poller to ORM + WS broadcast; added `tests/test_alerts_crud.py` (PASS).
- Phase 3: Added optional background startup hooks (env: `ENABLE_BACKGROUND_LOOPS`, `ENABLE_ALERTS_POLLER`).
 UI/UX: Added `docs/UIUX.md` with responsive design plan; updated SCOPE/ROADMAP for Discord alerts.
 Settings: Added Discord webhook/filters to `AppSettings` and `/api/v1/settings/*` (DB fields + API serialization).
 Poller: Posts alerts to Discord when enabled and type matches filters.
 Next: Wire Polygon WS price events to broadcast; verify dashboard receives `price` events; add minimal E2E manual checklist.

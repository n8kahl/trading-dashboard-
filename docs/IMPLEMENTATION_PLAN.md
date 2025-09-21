# Solo Deployment Implementation Plan

Purpose: implement the lean, single‑user stack described in the README with minimal cost and operational overhead, using this repo’s FastAPI backend and a single VM. This plan is actionable for a non‑developer, with concrete commands, clear milestones, and small weekly increments.

## Status (2025-09-16)

- Done: Dockerfile + docker-compose (API, DB, Prometheus, Grafana)
- Done: Metrics exposed at `/metrics` with Prometheus scrape + Grafana datasource
- Done: Postgres tables (`trades`, `features`, `logs`) + REST endpoints + Discord webhook notifier
- Next: Optional reverse proxy, backtesting CLI, weekly review scaffold

## Goals

- Reliable one‑person setup on a small VM (2–4 vCPU, 8–16 GB RAM)
- Postgres/TimescaleDB for trades + features; object storage for logs
- Polygon + Tradier integration (keys via env vars)
- Simple monitoring (Prometheus + Grafana) and Discord alerts
- Local backtesting with DuckDB + Parquet
- Optional GPT analysis for weekly review and log summaries

## Prerequisites

- Accounts: GitHub, cloud VM (Lightsail/DigitalOcean/Hetzner), Polygon, Tradier
- Keys/tokens ready: `POLYGON_API_KEY`, `TRADIER_ACCESS_TOKEN` (or `TRADIER_API_KEY`), Discord webhook URL (for alerts), optional OpenAI or chat‑data.com key (`CHATDATA_API_KEY`)
- Local machine: Python 3.12, `git`, curl

---

## Phase 0 — Local Sanity Check (30–60 min)

Objective: run the FastAPI app locally and hit a couple of endpoints.

Steps
1) Clone and install deps
```
git clone <this-repo-url>
cd <repo>
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
2) Set a minimal `.env` in your shell for testing (Polygon free tier works):
```
export POLYGON_API_KEY=pk_...
```
3) Run the app
```
bash ./run.sh
```
4) In another terminal, test endpoints
```
curl -s http://localhost:8000/api/v1/diag/health | jq
curl -s -X POST http://localhost:8000/api/v1/assistant/exec \
 -H 'Content-Type: application/json' \
 -d '{"op":"data.snapshot","args":{"symbols":["SPY"],"horizon":"intraday"}}' | jq '.ok'
```

Deliverable: app responds locally; Polygon requests succeed with your key.

---

## Phase 1 — One‑VM Docker Compose (2–4 hrs)

Objective: provision a small VM and run the stack under Docker Compose.

Services
- `api`: this FastAPI app (uvicorn)
- `db`: Postgres 15 with TimescaleDB
- `prometheus`: scrape metrics from `api` (expose a `/metrics` endpoint via instrumentor)
- `grafana`: dashboards for latencies, errors, and custom counters
- `caddy` or `nginx`: reverse proxy with HTTPS (optional: use Caddy for auto‑TLS)

Plan
1) Create VM (Ubuntu 22.04), add SSH key, open ports 80/443.
2) Install Docker + Docker Compose plugin.
3) Create `/opt/trader` and place `docker-compose.yml`, `.env` (server), and data volumes.
4) Add a minimal metrics instrumentor to FastAPI (later step).

Compose skeleton (to implement next):
```
version: "3.9"
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    env_file: .env
    ports: ["8000:8000"]
    depends_on: [db]

  db:
    image: timescale/timescaledb:latest-pg15
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_DB=trader
    volumes:
      - dbdata:/var/lib/postgresql/data

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana
    ports: ["3000:3000"]
    volumes:
      - grafana:/var/lib/grafana

volumes:
  dbdata:
  grafana:
```

Deliverable: VM running `api` and `db`; Grafana/Prometheus can be added after metrics are exposed.

---

## Phase 2 — Data & Persistence (4–6 hrs)

_Status: completed 2025-09-16._

Objective: introduce Postgres/TimescaleDB models for trades, features, and logs.

Steps
- Pick ORM: SQLAlchemy or SQLModel
- Add minimal tables:
  - `trades` (id, ts, symbol, side, type, qty, avg_price, pnl, tags)
  - `features` (id, ts, symbol, horizon, payload JSONB)
  - `logs` (id, ts, level, source, message, payload JSONB)
- Add a simple `/api/v1/trades` POST/GET
- Add a `features` write path in the snapshot flow (optional cache)

Deliverable: persisted trades/features available via API; basic indexes.

---

## Phase 3 — Monitoring & Alerts (2–4 hrs)

_Status: partially completed — Prometheus/Grafana + Discord webhook in place._

Objective: basic observability with zero fluff.

Steps
- Expose `/metrics` using `prometheus-fastapi-instrumentator`
- Add Prometheus scrape config; import a latency/error Grafana dashboard
- Add a `DISCORD_WEBHOOK_URL` env var and a tiny notifier util
- Send alerts on: provider errors > threshold, rate‑limit spikes, and critical exceptions

Deliverable: One Grafana dashboard; Discord DM for urgent issues.

---

## Phase 4 — Feeds & Brokerage (2–3 hrs)

Objective: wire keys and guardrails for Polygon + Tradier already present in code.

Steps
- Configure env vars in `.env` (VM):
  - `POLYGON_API_KEY=...`
  - `TRADIER_ACCESS_TOKEN=...` and `TRADIER_ENV=sandbox|prod`
  - Optional: `POLYGON_API_RATE`, `TRADIER_API_RATE`
- Smoke tests:
  - `GET /api/v1/market/overview`
  - `POST /api/v1/assistant/exec` with `{ op: "data.snapshot" }`
- Add clear errors if keys missing; surface provider availability flags in `/api/v1/assistant/actions` (already present)

Deliverable: consistent behavior with or without brokerage key present.

---

## Phase 5 — Backtesting (local) (4–6 hrs)

Objective: simple local backtesting with DuckDB + Parquet.

Steps
- Create `backtests/` with Parquet bars (Polygon or public data)
- Add a small Python CLI to score historical snapshots
- Output metrics: hit rates, EV calibration, slippage assumptions by bucket

Deliverable: CSV/Markdown reports written to `reports/` for review.

---

## Phase 6 — GPT for Weekly Review (1–2 hrs)

Objective: summarize trade logs and propose tweaks, you accept/reject.

Steps
- Add a CLI `scripts/weekly_review.py` that:
  - pulls trades/logs from DB for the week
  - summarizes with GPT‑4o mini (or chat‑data.com proxy) using cost caps
  - outputs an action list to `reports/weekly.md`

Deliverable: a concise weekly brief and recommended changes to configs.

---

## Phase 7 — Security, Backups, Hygiene (1–2 hrs)

Steps
- Enable UFW (allow 22, 80/443, 8000 if needed internally)
- Regular OS updates; set up unattended‑upgrades
- Nightly Postgres dump to object storage (B2/S3)
- Secrets via `.env` on VM; never commit keys

Deliverable: low‑touch, safe defaults for a solo operator.

---

## Environment Variables (working set)

- Required today: `POLYGON_API_KEY`
- Brokerage: `TRADIER_ACCESS_TOKEN` (or `TRADIER_API_KEY`), `TRADIER_ENV`
- Alerts: `DISCORD_WEBHOOK_URL`
- AI (optional): `CHATDATA_API_KEY` or OpenAI key
- Risk/loops: `ENABLE_BACKGROUND_LOOPS`, `ENABLE_ALERTS_POLLER`, `WS_PING_SEC`, and other knobs already documented in README

Keep a server‑side `.env` with the above; for local use, export minimal keys in your shell.

---

## Budget and Tiers (expected)

- VM: $20–40
- Polygon: $49–199 depending on options/real‑time needs
- OpenAI/chat‑data: ~$30 with light use
- Storage/Monitoring: ~$10

Total: $100–250/month.

---

## What I’ll Implement Next (once you confirm)

1) Add a `docker-compose.yml` and example `.env.server` for VM
2) Expose `/metrics` and provide Prometheus/Grafana configs
3) Add Discord notifier util and wire a couple of alert hooks
4) Introduce a minimal Postgres schema (trades, features, logs) + endpoints
5) Provide a `scripts/weekly_review.py` skeleton for GPT summaries

Each step ships independently; you can stop anywhere and still have value.

---

## Quick Walkthrough (you can do today)

Local run
1) Ensure Python 3.12, then:
```
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export POLYGON_API_KEY=pk_...
bash ./run.sh
```
2) Open http://localhost:8000/api/v1/diag/health

Minimal VM setup
1) Create a Ubuntu VM (Lightsail/DigitalOcean)
2) SSH in, install Docker: https://docs.docker.com/engine/install/
3) Create `/opt/trader` and copy the repo there
4) I’ll add `docker-compose.yml` in the next step so you can run `docker compose up -d`

That’s it — once you confirm, I’ll proceed to the Compose + metrics step and keep changes small and testable.

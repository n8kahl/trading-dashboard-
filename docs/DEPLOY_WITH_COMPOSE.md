# Deploy with Docker Compose

This guide brings up the API, Postgres/TimescaleDB, Prometheus, and Grafana on a single VM.

## 1) Prepare a VM
- Ubuntu 22.04 with ports 22, 80/443 (optional), 8000, 9090, 3000 open
- Install Docker and Compose plugin:
  - https://docs.docker.com/engine/install/ubuntu/
  - https://docs.docker.com/compose/install/linux/

## 2) Copy repo and env
```
ssh ubuntu@your-vm
sudo mkdir -p /opt/trader && sudo chown $USER:$USER /opt/trader
cd /opt/trader
git clone <your-repo-url> .
cp .env.server.example .env.server
vi .env.server  # fill keys, passwords, DATABASE_URL, optional webhook
```

Secrets hygiene
- Never commit `.env.server` to git (repo already ignores it).
- Prefer using the sandbox Tradier token while testing (`TRADIER_ENV=sandbox`).
- Switch to production by setting `TRADIER_ENV=prod` and pasting your production token.
- Confirm `DATABASE_URL` points at the compose Postgres service (default already set to `postgresql+asyncpg://trader:change-me@db:5432/trader`).
- Add `DISCORD_WEBHOOK_URL` if you want error alerts in a private channel.

## 3) Build and run
```
docker compose build
docker compose up -d
```

## 4) Verify
- API health: http://YOUR_VM:8000/api/v1/diag/health
- Providers: http://YOUR_VM:8000/api/v1/diag/providers
- Metrics: http://YOUR_VM:8000/metrics
- Prometheus: http://YOUR_VM:9090
- Grafana: http://YOUR_VM:3000 (login with the admin credentials from `.env.server`)

In Grafana, a Prometheus datasource is pre-provisioned. Create a new dashboard and add a panel with query like:
```
http_requests_total
```
or filter by path/method/handler labels.

Provider smoke tests
```
# Polygon snapshot (SPY intraday)
curl -s -X POST http://YOUR_VM:8000/api/v1/assistant/exec \
 -H 'Content-Type: application/json' \
 -d '{"op":"data.snapshot","args":{"symbols":["SPY"],"horizon":"intraday"}}' | jq '.ok, .providers, .errors'

# Tradier quote (requires TRADIER token/env set)
curl -s http://YOUR_VM:8000/api/v1/diag/providers | jq
```

## 5) Common operations
```
# Logs
docker compose logs -f api

# Rebuild after code change
docker compose build api && docker compose up -d api

# Stop / start
docker compose stop
docker compose start
```

## 6) Next steps
- Add a reverse proxy (Caddy or Nginx) with HTTPS if exposing to internet
- Nightly DB backups to S3/B2 using a simple cron or a companion container
- Tighten firewall (UFW) and rotate default Grafana creds

# GPT Setup
1) Actions → Add → paste `docs/actions/openapi_combined.yaml` (server URL without trailing slash).
2) Knowledge → upload all files in `docs/gpt/`.
3) Add to Instructions:
> For all endpoints under `/api/v1/*`, use **POST** except these exact **GETs**: `/api/v1/screener/watchlist/get`, `/api/v1/screener/watchlist/ranked`, `/api/v1/journal/summary`, `/api/v1/alerts/list`, `/api/v1/alerts/recent-triggers`.

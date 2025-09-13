Vercel Deployment — Status & Checklist

Status
- Project is configured for Vercel via `vercel.json` to build the Next.js app in `trading-dashboard/`.
- Automatic deploys should trigger on pushes to the repository (Vercel project: see README link).
- Current live status is unknown from the repo alone (requires either the public deployment URL or Vercel API access).


Project Settings
- Framework Preset: Next.js
- Root Directory: `trading-dashboard`
- Functions: Keep `/app/api/proxy` on Edge runtime (already set via `export const runtime = "edge"`).


What We Need To Verify
- Public URL or Vercel project slug to probe health (e.g., curl the root and `/api/proxy`).
- If available, a Vercel token to query the Deployments API.

Runtime Checklist
- Environment variables (on Vercel Project → Settings → Environment Variables):
  - `NEXT_PUBLIC_API_BASE`: URL of the FastAPI backend (e.g., `https://your-backend.example.com`).
  - `NEXT_PUBLIC_API_KEY`: optional API key to pass to the backend (propagated to `X-API-Key` and WS `api_key=`).
  - `NEXT_PUBLIC_WS_BASE`: optional full `wss://.../ws` override; otherwise derived from `NEXT_PUBLIC_API_BASE`.
- Backend CORS must allow the Vercel domain (see `app/main.py` `ALLOWED_ORIGINS`).

Manual Smoke (no credentials required)
1) Open the Vercel URL in a browser; confirm the dashboard renders.
2) In browser devtools, verify GET `/api/proxy?path=/api/v1/diag/health` returns `{ ok: true }`.
3) Confirm WS connects (top right toast/banner “Connected” if your UI shows it).

API-based Check (optional)
- With `VERCEL_TOKEN` and `VERCEL_PROJECT_ID` or `VERCEL_PROJECT_NAME`, call:
  - `GET https://api.vercel.com/v6/deployments?projectId=...` and inspect `state` (`READY` is healthy).

Backend Deploy Targets
- If the backend is hosted separately (Railway/VM), ensure it’s reachable by Vercel and CORS allows the Vercel origin.

Notes

- `vercel.json` builds from `trading-dashboard/` using `@vercel/next`.
- For WS, prefer `NEXT_PUBLIC_WS_BASE` if you terminate TLS or path differs.

- vercel.json routes all paths to the Next.js app directory: ensure API proxy `/api/proxy` keeps working.
- For WS, prefer `NEXT_PUBLIC_WS_BASE` if you terminate TLS or path differs.


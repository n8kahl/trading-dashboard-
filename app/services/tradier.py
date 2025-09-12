import os, datetime as dt
from typing import Dict, Any, List, Optional
import httpx

TRADIER_BASE = os.getenv("TRADIER_BASE", "https://sandbox.tradier.com")
TRADIER_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN")

HDRS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}" if TRADIER_TOKEN else "",
    "Accept": "application/json"
}

async def _get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{TRADIER_BASE}{path}", headers=HDRS, params=params)
        r.raise_for_status()
        return r.json()

def _days_between(a: dt.date, b: dt.date) -> int:
    return (b - a).days

async def expirations(symbol: str) -> List[str]:
    js = await _get("/v1/markets/options/expirations", {"symbol": symbol, "includeAllRoots": "true", "strikes":"false"})
    exps = js.get("expirations", {}).get("date")
    if isinstance(exps, list):
        return exps
    if isinstance(exps, str):
        return [exps]
    return []

async def chains_for_exp(symbol: str, exp: str) -> List[Dict[str, Any]]:
    js = await _get("/v1/markets/options/chains", {"symbol": symbol, "expiration": exp})
    rows = js.get("options", {}).get("option")
    if isinstance(rows, list):
        return rows
    if isinstance(rows, dict):
        return [rows]
    return []

async def quotes_for_symbols(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    if not symbols:
        return {}
    sy = ",".join(symbols[:250])
    js = await _get("/v1/markets/options/quotes", {"symbols": sy, "greeks": "true"})
    q = js.get("quotes", {}).get("quote")
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(q, list):
        for row in q:
            out[row["symbol"]] = row
    elif isinstance(q, dict):
        out[q["symbol"]] = q
    return out

def tradier_batch_option_quotes(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch option quotes (with greeks) from Tradier in batches using the correct endpoint:
      /v1/markets/options/quotes
    Fail-open: returns {} on any error.
    """
    import os, requests
    out: dict[str, dict] = {}
    if not symbols:
        return out

    token = os.getenv("TRADIER_TOKEN") or os.getenv("TRADIER_ACCESS_TOKEN") or ""
    if not token:
        return out

    base = (os.getenv("TRADIER_BASE") or "https://sandbox.tradier.com").rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "trading-assistant/greeks-enrichment"
    }

    CHUNK = 120  # Tradier handles large lists but we keep it safe
    for i in range(0, len(symbols), CHUNK):
        chunk = [c for c in symbols[i:i+CHUNK] if c]
        if not chunk:
            continue
        try:
            r = requests.get(
                f"{base}/v1/markets/options/quotes",
                headers=headers,
                params={"symbols": ",".join(chunk), "greeks": "true"},
                timeout=15
            )
            r.raise_for_status()
            data = r.json() or {}
            # Shape can be: {"quotes":{"quote":[{...},{...}]}} OR {"quotes":{"quote":{...}}}
            quotes = (data.get("quotes") or {}).get("quote")
            if not quotes:
                continue
            if isinstance(quotes, dict):
                quotes = [quotes]
            for q in quotes:
                sym = q.get("symbol")
                if not sym:
                    continue
                out[sym] = q  # includes "greeks": { delta, gamma, theta, vega, ... }
        except Exception:
            # fail-open: skip chunk on any error
            pass

    return out

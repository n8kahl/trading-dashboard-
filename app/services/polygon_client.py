import os, httpx

API = "https://api.polygon.io"

def _key() -> str:
    k = os.getenv("POLYGON_API_KEY")
    if not k:
        raise RuntimeError("POLYGON_API_KEY not set")
    return k

def last_trade(symbol: str) -> dict:
    url = f"{API}/v2/last/trade/{symbol}"
    with httpx.Client(timeout=5.0) as cx:
        r = cx.get(url, params={"apiKey": _key()})
        r.raise_for_status()
        return r.json() or {}

def multi_last_trades(symbols: list[str]) -> dict:
    out: dict[str, dict] = {}
    for s in symbols:
        try:
            data = last_trade(s)
            p = None
            ts = None
            try:
                p = float((data.get("results") or {}).get("p"))
            except Exception:
                pass
            ts = (data.get("results") or {}).get("t")
            out[s] = {"price": p, "ts": ts, "raw": data}
        except Exception as e:
            out[s] = {"error": str(e)}
    return out

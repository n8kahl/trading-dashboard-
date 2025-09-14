import logging
import os
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from app.obs import log_event, get_request_id

logger = logging.getLogger(__name__)

TRADIER_ENV = os.getenv("TRADIER_ENV", "sandbox").lower().strip()
TRADIER_ACCESS_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN", "").strip()
TRADIER_ACCOUNT_ID = os.getenv("TRADIER_ACCOUNT_ID", "").strip()
TRADIER_BASE = os.getenv("TRADIER_BASE", "").strip()


def _base_url() -> str:
    if TRADIER_BASE:
        base = TRADIER_BASE.rstrip("/")
    else:
        base = "https://sandbox.tradier.com" if TRADIER_ENV == "sandbox" else "https://api.tradier.com"
    return base + "/v1"


DEFAULT_HEADERS = {
    "Authorization": f"Bearer {TRADIER_ACCESS_TOKEN}",
    "Accept": "application/json",
}


def _log(event: str, detail: Dict[str, Any]) -> None:
    # Structured JSON log without secrets
    safe = dict(detail)
    safe.pop("Authorization", None)
    log_event(f"tradier.{event}", **safe)


class TradierClient:
    def __init__(self, timeout: float = 10.0) -> None:
        if not TRADIER_ACCESS_TOKEN:
            raise RuntimeError("TRADIER_ACCESS_TOKEN missing")
        # Account ID is only required for account-specific endpoints; allow it to be absent
        self.account_id = TRADIER_ACCOUNT_ID
        self.base = _base_url()
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _session(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base, timeout=self.timeout, headers=DEFAULT_HEADERS)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ---------- Accounts / profile ----------
    async def get_profile(self) -> Dict[str, Any]:
        # GET /v1/user/profile
        # https://developer.tradier.com/documentation/user/get-profile
        cid = str(uuid4())
        url = "/user/profile"
        s = await self._session()
        _log("request", {"cid": cid, "method": "GET", "url": url})
        r = await s.get(url)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        r.raise_for_status()
        return r.json()

    async def get_balances(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        # GET /v1/accounts/{id}/balances
        aid = account_id or TRADIER_ACCOUNT_ID
        url = f"/accounts/{aid}/balances"
        cid = str(uuid4())
        s = await self._session()
        _log("request", {"cid": cid, "method": "GET", "url": url})
        r = await s.get(url)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        r.raise_for_status()
        return r.json()

    async def get_positions(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        # GET /v1/accounts/{id}/positions
        aid = account_id or TRADIER_ACCOUNT_ID
        url = f"/accounts/{aid}/positions"
        cid = str(uuid4())
        s = await self._session()
        _log("request", {"cid": cid, "method": "GET", "url": url})
        r = await s.get(url)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        r.raise_for_status()
        return r.json()

    async def get_orders(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        # GET /v1/accounts/{id}/orders
        aid = account_id or TRADIER_ACCOUNT_ID
        url = f"/accounts/{aid}/orders"
        cid = str(uuid4())
        s = await self._session()
        _log("request", {"cid": cid, "method": "GET", "url": url})
        r = await s.get(url)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        r.raise_for_status()
        return r.json()

    async def get_quotes(self, symbols: List[str], *, greeks: bool = False) -> Dict[str, Any]:
        """Fetch quotes for one or more symbols.

        When ``greeks`` is True, the options quote endpoint is used and
        ``greeks=true`` is added to the request parameters so that option
        greek values are included in the response.
        """
        if not symbols:
            return {}
        url = "/markets/quotes"
        params: Dict[str, Any] = {"symbols": ",".join(symbols)}
        if greeks:
            url = "/markets/options/quotes"
            params["greeks"] = "true"
        cid = str(uuid4())
        s = await self._session()
        _log("request", {"cid": cid, "method": "GET", "url": url, "params": params})
        r = await s.get(url, params=params)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        r.raise_for_status()
        return r.json()

    async def get_option_greeks(self, symbol: str, expiration: str, strike: float, option_type: str) -> Dict[str, Any]:
        """Fetch greek data for a specific option contract.

        Wraps the `/markets/options/greeks` endpoint.
        """
        url = "/markets/options/greeks"
        params = {
            "symbol": symbol,
            "expiration": expiration,
            "strike": strike,
            "type": option_type,
        }
        cid = str(uuid4())
        s = await self._session()
        _log("request", {"cid": cid, "method": "GET", "url": url, "params": params})
        r = await s.get(url, params=params)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        r.raise_for_status()
        return r.json()

    # ---------- Orders ----------
    async def order_preview_or_place(
        self,
        *,
        account_id: Optional[str],
        params: Dict[str, Any],
        preview: bool,
    ) -> Dict[str, Any]:
        """
        POST /v1/accounts/{id}/orders
        Content-Type: application/x-www-form-urlencoded
        Add preview=true to simulate and get fees/warnings. (Tradier docs)
        """
        aid = account_id or TRADIER_ACCOUNT_ID
        url = f"/accounts/{aid}/orders"
        cid = str(uuid4())
        form = dict(params)
        if preview:
            form["preview"] = "true"
        headers = dict(DEFAULT_HEADERS)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        rid = get_request_id()
        if rid:
            headers["X-Request-ID"] = rid
        s = await self._session()
        _log("request", {"cid": cid, "method": "POST", "url": url, "form_keys": list(form.keys())})
        start = time.perf_counter()
        r = await s.post(url, data=form, headers=headers)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        log_event("tradier.timing", api="orders", method="POST", status=r.status_code, dur_ms=int((time.perf_counter()-start)*1000))
        r.raise_for_status()
        return r.json()

    async def cancel_order(self, *, account_id: Optional[str], order_id: str) -> Dict[str, Any]:
        # POST /v1/accounts/{id}/orders/cancel
        aid = account_id or TRADIER_ACCOUNT_ID
        url = f"/accounts/{aid}/orders/{order_id}/cancel"
        cid = str(uuid4())
        s = await self._session()
        hdrs = dict(DEFAULT_HEADERS)
        rid = get_request_id()
        if rid:
            hdrs["X-Request-ID"] = rid
        _log("request", {"cid": cid, "method": "POST", "url": url})
        start = time.perf_counter()
        r = await s.post(url, headers=hdrs)
        _log("response", {"cid": cid, "status": r.status_code, "url": url})
        log_event("tradier.timing", api="cancel", method="POST", status=r.status_code, dur_ms=int((time.perf_counter()-start)*1000))
        r.raise_for_status()
        return r.json()

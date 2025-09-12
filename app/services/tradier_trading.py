from __future__ import annotations

import os
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from app.integrations.tradier import TradierClient

TRADIER_ENV = os.getenv("TRADIER_ENV", "sandbox").lower().strip()


class StrategyOrder(BaseModel):
    """Simple order recommendation produced by a strategy."""

    symbol: str
    quantity: int = Field(..., gt=0)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = "market"
    limit_price: Optional[float] = None


async def place_order(order: StrategyOrder, *, preview: bool = False) -> Dict[str, Any]:
    """Place or preview an order on Tradier.

    Only permitted when TRADIER_ENV is ``sandbox``. ``preview=True`` will
    trigger Tradier's preview mode which simulates the order and returns fees.
    """

    if TRADIER_ENV != "sandbox":
        raise RuntimeError("Trading is only allowed in Tradier sandbox")

    client = TradierClient()
    params = {
        "class": "equity",
        "symbol": order.symbol.upper(),
        "side": order.side,
        "quantity": str(order.quantity),
        "type": order.order_type,
    }
    if order.order_type == "limit" and order.limit_price is not None:
        params["price"] = str(order.limit_price)

    try:
        res = await client.order_preview_or_place(account_id=None, params=params, preview=preview)
    finally:
        await client.close()
    return res

from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models import PaperTrade, PaperPosition, PaperFill

# Env-configurable rules
TIME_STOP_MIN = int(os.getenv("PAPER_TIME_STOP_MIN", "25"))
DEFAULT_STOP_R = float(os.getenv("PAPER_DEFAULT_STOP_R", "1.0"))
DEFAULT_TP_R = float(os.getenv("PAPER_DEFAULT_TP_R", "2.0"))
MAX_DAILY_LOSS_R = float(os.getenv("PAPER_MAX_DAILY_LOSS_R", "3.0"))

@dataclass
class SubmitIntent:
    symbol: str
    side: str         # "buy" or "sell"
    qty: int
    entry_px: Optional[float] = None
    exit_px: Optional[float] = None
    session: Optional[str] = None  # open/mid/power
    strategy_id: Optional[str] = None
    score: Optional[float] = None
    expected_r: Optional[float] = None
    stop_r: Optional[float] = None
    tp_r: Optional[float] = None

def _slippage_bps_for_session(session: Optional[str]) -> float:
    s = (session or "mid").lower()
    return {"open": 12.0, "mid": 5.0, "power": 8.0}.get(s, 6.0)

def _apply_slippage(px: float, side: str, bps: float) -> float:
    # buy: pay up; sell: sell down
    adj = px * (bps / 10000.0)
    return px + adj if side == "buy" else px - adj

def _daily_loss_r(db: Session) -> float:
    # Sum realized R for today (very simple placeholder; extend with more precise logic)
    today = date.today()
    q = select(func.coalesce(func.sum(PaperTrade.outcome_r), 0.0)).where(
        func.date(PaperTrade.close_time) == today
    )
    return float(db.execute(q).scalar_one())

def submit(db: Session, intent: SubmitIntent) -> Dict[str, Any]:
    """
    Simple model:
    - BUY opens or increases long position; SELL closes or reduces.
    - Entry/exit price can be provided; we apply session slippage bps.
    - Risk controls: block if daily loss exceeds MAX_DAILY_LOSS_R (negative value).
    """
    # Risk gate: daily loss
    daily_r = _daily_loss_r(db)
    if daily_r <= -abs(MAX_DAILY_LOSS_R):
        return {"ok": False, "error": f"Daily loss limit reached ({daily_r:.2f}R <= -{MAX_DAILY_LOSS_R}R)"}

    bps = _slippage_bps_for_session(intent.session)
    now = datetime.now(UTC)

    if intent.side == "buy":
        if intent.entry_px is None:
            return {"ok": False, "error": "entry_px required for buy"}
        fill_px = _apply_slippage(intent.entry_px, "buy", bps)

        # Update or create position
        pos = db.execute(select(PaperPosition).where(PaperPosition.symbol == intent.symbol)).scalar_one_or_none()
        if pos:
            new_qty = pos.qty + intent.qty
            pos.avg_px = (pos.avg_px * pos.qty + fill_px * intent.qty) / max(1, new_qty)
            pos.qty = new_qty
        else:
            pos = PaperPosition(symbol=intent.symbol, qty=intent.qty, avg_px=fill_px)
            db.add(pos)
            db.flush()

        # Trade record open
        tr = PaperTrade(
            symbol=intent.symbol, side="buy", qty=intent.qty, entry_px=fill_px,
            open_time=now, session=intent.session, strategy_id=intent.strategy_id,
            score=intent.score, expected_r=intent.expected_r, slippage_bps=bps, fees=0.0
        )
        db.add(tr); db.flush()
        db.add(PaperFill(trade_id=tr.id, px=fill_px, qty=intent.qty, time=now, liquidity_bucket=intent.session, spread_pct=bps/100.0))
        db.commit()
        return {"ok": True, "filled_px": fill_px, "trade_id": tr.id, "position_qty": pos.qty, "avg_px": pos.avg_px}

    elif intent.side == "sell":
        if intent.exit_px is None:
            return {"ok": False, "error": "exit_px required for sell"}
        fill_px = _apply_slippage(intent.exit_px, "sell", bps)

        # Reduce/close position
        pos = db.execute(select(PaperPosition).where(PaperPosition.symbol == intent.symbol)).scalar_one_or_none()
        if not pos or pos.qty < intent.qty:
            return {"ok": False, "error": "insufficient position to sell"}

        # Create closing trade (simple linkage for demo)
        tr = PaperTrade(
            symbol=intent.symbol, side="sell", qty=intent.qty, exit_px=fill_px,
            close_time=now, session=intent.session, slippage_bps=bps, fees=0.0
        )
        db.add(tr); db.flush()
        db.add(PaperFill(trade_id=tr.id, px=fill_px, qty=intent.qty, time=now, liquidity_bucket=intent.session, spread_pct=bps/100.0))

        # Realized R (placeholder: 1R approx 1% of avg_px — refine later)
        r_unit = max(0.01 * pos.avg_px, 1e-6)
        pnl_per_share = (fill_px - pos.avg_px)
        realized_r = pnl_per_share / (r_unit * pos.avg_px)
        tr.outcome_r = realized_r

        pos.qty -= intent.qty
        if pos.qty == 0:
            db.delete(pos)

        db.commit()
        return {"ok": True, "filled_px": fill_px, "trade_id": tr.id, "realized_r": realized_r, "remaining_qty": pos.qty if pos.qty>0 else 0}

    else:
        return {"ok": False, "error": "side must be buy or sell"}

def positions(db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(select(PaperPosition)).scalars().all()
    return [{"symbol": r.symbol, "qty": r.qty, "avg_px": r.avg_px, "opened_at": r.opened_at.isoformat()+"Z"} for r in rows]

def pnl_for_date(db: Session, qdate: Optional[str]) -> Dict[str, Any]:
    if not qdate or qdate == "today":
        day = date.today()
    else:
        day = date.fromisoformat(qdate)

    rows = db.execute(select(PaperTrade).where(
        PaperTrade.close_time.isnot(None),
        func.date(PaperTrade.close_time) == day
    )).scalars().all()

    total_r = sum([r.outcome_r or 0.0 for r in rows])
    return {"date": day.isoformat(), "trades": len(rows), "total_R": total_r}

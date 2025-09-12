from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional

from app.services.indicators import atr, ema, rsi, sma, vwap


@dataclass
class SimConfig:
    risk_per_trade_pct: float = 1.0
    atr_mult: float = 1.5
    commission_per_trade: float = 0.00
    slippage_bps: float = 1.0  # 1 = 0.01%
    min_risk_pct_of_price: float = 0.10  # 0.10% of entry as absolute min risk


@dataclass
class Trade:
    entry_index: int
    entry_price: float
    stop_price: float
    tp1: float
    tp2: float
    exit_index: Optional[int] = None
    exit_price: Optional[float] = None
    outcome_r: Optional[float] = None
    notes: str = ""


def position_size(equity: float, risk_pct: float) -> float:
    return equity * (risk_pct / 100.0)


def _apply_costs(price: float, slippage_bps: float) -> float:
    return price * (1 + slippage_bps / 10000.0)


# ---------- Strategy signals ----------


def sig_trend_pullback(close, e8, e21, e50):
    sig = [False] * len(close)
    for i in range(2, len(close)):
        trend_ok = e8[i] > e21[i] > e50[i]
        cross_up = close[i] > e8[i] and close[i - 1] <= e8[i - 1]
        sig[i] = trend_ok and cross_up
    return sig


def sig_vwap_reclaim(close, vwap_line, vol, vol_sma_len: int = 20):
    vol_sma = sma(vol, vol_sma_len)
    sig = [False] * len(close)
    for i in range(1, len(close)):
        cross_up = close[i] > vwap_line[i] and close[i - 1] <= vwap_line[i - 1]
        vol_ok = vol[i] >= max(1.0, vol_sma[i])
        sig[i] = cross_up and vol_ok
    return sig


def sig_range_break_retest(close, high, low, lookback: int = 20):
    # Enter long when we break above rolling high and prior close <= that level (simple version)
    sig = [False] * len(close)
    rolling_high = []
    for i in range(len(close)):
        start = max(0, i - lookback)
        rh = max(high[start : i + 1]) if i > 0 else high[0]
        rolling_high.append(rh)
        if i >= 1 and close[i] > rh and close[i - 1] <= rh:
            sig[i] = True
    return sig


def sig_divergence_catch(close, rsi14, lookback: int = 15):
    # Simplified bullish divergence: price lower low while RSI higher low, then RSI crosses up 30
    sig = [False] * len(close)
    for i in range(lookback + 1, len(close)):
        window_p = close[i - lookback : i + 1]
        window_r = rsi14[i - lookback : i + 1]
        # find two lows
        p1_idx = window_p.index(min(window_p[: lookback // 2]))
        p2_idx = window_p.index(min(window_p[lookback // 2 :])) + lookback // 2
        if p2_idx <= p1_idx:
            continue
        p1 = window_p[p1_idx]
        p2 = window_p[p2_idx]
        r1 = window_r[p1_idx]
        r2 = window_r[p2_idx]
        div_bull = (p2 < p1) and (r2 > r1)
        cross_up_30 = rsi14[i] > 30.0 and rsi14[i - 1] <= 30.0
        sig[i] = div_bull and cross_up_30
    return sig


# ---------- Simulator core ----------


def simulate_long(bars: Dict[str, List[float]], signals: List[bool], cfg: SimConfig) -> Dict[str, Any]:
    close, high, low = bars["close"], bars["high"], bars["low"]
    n = len(close)
    atr14 = atr(high, low, close, 14)
    equity = 100000.0
    peak_equity = equity
    max_drawdown = 0.0
    equity_curve = [equity]
    trades: List[Trade] = []
    open_pos: Optional[Trade] = None

    for i in range(60, n):
        # manage open
        if open_pos is not None:
            hit_stop = low[i] <= open_pos.stop_price
            hit_tp2 = high[i] >= open_pos.tp2
            hit_tp1 = high[i] >= open_pos.tp1

            if hit_stop or hit_tp2:
                exit_px = open_pos.stop_price if hit_stop else open_pos.tp2
                den = open_pos.entry_price - open_pos.stop_price
                r = (exit_px - open_pos.entry_price) / den if den != 0 else 0.0
                open_pos.exit_index = i
                open_pos.exit_price = exit_px
                open_pos.outcome_r = r
                equity += position_size(equity, cfg.risk_per_trade_pct) * r - cfg.commission_per_trade
                trades.append(open_pos)
                open_pos = None
            elif hit_tp1:
                # half off at 1R, move stop to breakeven
                equity += (position_size(equity, cfg.risk_per_trade_pct) * 1.0) / 2.0
                open_pos.stop_price = open_pos.entry_price

        # entries
        if open_pos is None and signals[i]:
            ent = _apply_costs(close[i], cfg.slippage_bps)
            # Risk floor = max(ATR*mult, min_risk_pct_of_price * entry)
            bar_atr = max(atr14[i], 0.0)
            risk_atr = bar_atr * cfg.atr_mult
            risk_min = ent * (cfg.min_risk_pct_of_price / 100.0)
            risk = max(risk_atr, risk_min)
            if risk <= 0:
                continue
            stop = ent - risk
            if ent <= stop:
                # enforce strict separation if numerical issues
                stop = ent - max(1e-6, risk)
            tp1 = ent + risk
            tp2 = ent + 2 * risk
            open_pos = Trade(entry_index=i, entry_price=ent, stop_price=stop, tp1=tp1, tp2=tp2, notes="auto")

        # equity / dd update
        peak_equity = max(peak_equity, equity)
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
        max_drawdown = max(max_drawdown, dd)
        equity_curve.append(equity)

    # close any open at last
    if open_pos is not None:
        px = close[-1]
        den = open_pos.entry_price - open_pos.stop_price
        r = (px - open_pos.entry_price) / den if den != 0 else 0.0
        open_pos.exit_index = n - 1
        open_pos.exit_price = px
        open_pos.outcome_r = r
        equity += position_size(equity, cfg.risk_per_trade_pct) * r - cfg.commission_per_trade
        trades.append(open_pos)

    rs = [t.outcome_r for t in trades if t.outcome_r is not None]
    wins = sum(1 for r in rs if r > 0)
    win_rate = (wins / len(rs)) * 100.0 if rs else 0.0
    avg_r = sum(rs) / len(rs) if rs else 0.0

    return {
        "status": "ok",
        "data": {
            "n_trades": len(rs),
            "win_rate_pct": round(win_rate, 2),
            "avg_r": round(avg_r, 3),
            "equity_start": 100000.0,
            "equity_end": round(equity, 2),
            "max_drawdown_pct": round(max_drawdown * 100.0, 2),
            "equity_curve": equity_curve[-500:],
            "trades": [asdict(t) for t in trades],
        },
    }


# ---------- Public strategy runners ----------


def run_trend_pullback(bars: Dict[str, List[float]], cfg: SimConfig) -> Dict[str, Any]:
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    e8, e21, e50 = ema(c, 8), ema(c, 21), ema(c, 50)
    signals = sig_trend_pullback(c, e8, e21, e50)
    res = simulate_long(bars, signals, cfg)
    res["data"]["strategy"] = "trend_pullback"
    return res


def run_vwap_reclaim(bars: Dict[str, List[float]], cfg: SimConfig) -> Dict[str, Any]:
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    vw = vwap(h, l, c, v)
    signals = sig_vwap_reclaim(c, vw, v)
    res = simulate_long(bars, signals, cfg)
    res["data"]["strategy"] = "vwap_reclaim"
    return res


def run_range_break_retest(bars: Dict[str, List[float]], cfg: SimConfig) -> Dict[str, Any]:
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    signals = sig_range_break_retest(c, h, l, lookback=20)
    res = simulate_long(bars, signals, cfg)
    res["data"]["strategy"] = "range_break_retest"
    return res


def run_divergence_catch(bars: Dict[str, List[float]], cfg: SimConfig) -> Dict[str, Any]:
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    r14 = rsi(c, 14)
    signals = sig_divergence_catch(c, r14, lookback=15)
    res = simulate_long(bars, signals, cfg)
    res["data"]["strategy"] = "divergence_catch"
    return res


def run_strategy(
    bars: Dict[str, List[float]],
    strategy: Literal["trend_pullback", "vwap_reclaim", "range_break_retest", "divergence_catch"],
    cfg: SimConfig,
) -> Dict[str, Any]:
    if strategy == "trend_pullback":
        return run_trend_pullback(bars, cfg)
    if strategy == "vwap_reclaim":
        return run_vwap_reclaim(bars, cfg)
    if strategy == "range_break_retest":
        return run_range_break_retest(bars, cfg)
    if strategy == "divergence_catch":
        return run_divergence_catch(bars, cfg)
    return {"status": "error", "error": "unknown_strategy", "data": {}}

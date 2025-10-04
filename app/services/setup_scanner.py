from __future__ import annotations

import asyncio
import math
import time
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

try:
    from app.services.providers.polygon_market import PolygonMarket
except Exception:  # pragma: no cover - optional import guard for startup
    PolygonMarket = None  # type: ignore
try:
    from app.services.providers.tradier_chain import options_chain as _td_options_chain, expirations as _td_expirations
except Exception:
    _td_options_chain = None  # type: ignore
    _td_expirations = None  # type: ignore
try:
    from app.services.indicators import spread_stability as _spread_stability
except Exception:
    def _spread_stability(bids: List[float], asks: List[float]) -> Optional[float]:  # type: ignore
        try:
            if not bids or not asks: return None
            bvar = max(1e-9, (max(bids) - min(bids)))
            avar = max(1e-9, (max(asks) - min(asks)))
            return max(0.0, min(1.0, 1.0 - (bvar + avar)/(max(1e-6, sum(asks)/len(asks)))))
        except Exception:
            return None


@dataclass
class _TimeframeState:
    last_close: Optional[float]
    last_high: Optional[float]
    last_low: Optional[float]
    prev_high: Optional[float]
    prev_low: Optional[float]
    prev_close: Optional[float]
    breakout: bool
    retest: bool
    distance: Optional[float]


_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL = 45  # seconds
_PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "") or "https://web-production-a9084.up.railway.app"
_BLUE_CHIP = {
    "SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "GOOG", "NVDA", "META", "TSLA", "AMD", "AMZN", "NFLX"
}


def _tf_state(bars: List[Dict[str, Any]], current: Optional[float], breakout_buffer: float = 0.0025) -> _TimeframeState:
    if not bars or len(bars) < 2:
        return _TimeframeState(None, None, None, None, None, None, False, False, None)
    last = bars[-1]
    prev = bars[-2]
    last_close = _safe_float(last.get("c"))
    prev_high = _safe_float(prev.get("h"))
    breakout = False
    retest = False
    distance = None
    if current is not None and prev_high:
        distance = (current - prev_high) / prev_high if prev_high else None
        if last_close is not None and last_close > prev_high * (1.0 + breakout_buffer):
            breakout = True
        elif abs(current - prev_high) <= prev_high * breakout_buffer:
            retest = True
    return _TimeframeState(
        last_close=last_close,
        last_high=_safe_float(last.get("h")),
        last_low=_safe_float(last.get("l")),
        prev_high=prev_high,
        prev_low=_safe_float(prev.get("l")),
        prev_close=_safe_float(prev.get("c")),
        breakout=breakout,
        retest=retest,
        distance=distance,
    )


def _safe_float(val: Any) -> Optional[float]:
    try:
        if val is None:
            return None
        return float(val)
    except Exception:
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _round(val: Optional[float], decimals: int = 2) -> Optional[float]:
    if val is None or math.isnan(val):
        return None
    return round(val, decimals)


async def _symbol_snapshot(poly: PolygonMarket, sym: str, mover_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        last_trade = await poly.last_trade(sym)
        last_price = _safe_float(last_trade.get("price"))
    except Exception:
        last_trade = {}
        last_price = None

    daily_bars, h4_bars, h1_bars, intraday_minutes = await asyncio.gather(
        poly.daily_bars(sym, lookback=8),
        poly.aggregate_bars(sym, multiplier=240, timespan="minute", lookback_days=10),
        poly.aggregate_bars(sym, multiplier=60, timespan="minute", lookback_days=5),
        poly.minute_bars_today(sym),
    )

    if not last_price and intraday_minutes:
        last_price = _safe_float(intraday_minutes[-1].get("c"))

    tf_daily = _tf_state(daily_bars, last_price, breakout_buffer=0.003)
    tf_h4 = _tf_state(h4_bars, last_price, breakout_buffer=0.0025)
    tf_h1 = _tf_state(h1_bars, last_price, breakout_buffer=0.0020)

    if last_price is None:
        return None

    # Daily trend via simple slope between latest closes
    daily_trend = 0.0
    if len(daily_bars) >= 3:
        closes = [b.get("c") for b in daily_bars[-5:] if _safe_float(b.get("c")) is not None]
        if len(closes) >= 2:
            daily_trend = (_safe_float(closes[-1]) - _safe_float(closes[0])) / max(1e-6, _safe_float(closes[0]))

    # Relative intraday volume vs 5-day average
    intraday_volume = sum((_safe_float(b.get("v")) or 0.0) for b in intraday_minutes)
    avg_daily_vol = 0.0
    if daily_bars:
        vols = [_safe_float(b.get("v")) or 0.0 for b in daily_bars[-6:-1]]
        if vols:
            avg_daily_vol = sum(vols) / len(vols)
    intraday_rvol = None
    if avg_daily_vol > 0:
        minutes_count = max(1, len(intraday_minutes))
        scaled = intraday_volume * (390 / minutes_count)
        intraday_rvol = scaled / avg_daily_vol

    alignment_score, alignment_tags = _alignment_metrics(tf_daily, tf_h4, tf_h1)
    price_liq_score, price_notes = _price_liquidity_score(last_price, mover_meta.get("volume"))
    rvol_score, rvol_note = _rvol_score(intraday_rvol)
    trend_score, trend_note = _trend_score(daily_trend)

    base_confidence = (
        alignment_score * 0.45
        + price_liq_score * 0.25
        + rvol_score * 0.15
        + trend_score * 0.15
    )

    setup = ", ".join(alignment_tags) if alignment_tags else "range watch"

    timeframes: Dict[str, Any] = {
        "daily": {
            "last_close": _round(tf_daily.last_close),
            "prev_high": _round(tf_daily.prev_high),
            "prev_low": _round(tf_daily.prev_low),
            "signal": "breakout" if tf_daily.breakout else ("retest" if tf_daily.retest else None),
        },
        "h4": {
            "last_close": _round(tf_h4.last_close),
            "prev_high": _round(tf_h4.prev_high),
            "prev_low": _round(tf_h4.prev_low),
            "signal": "breakout" if tf_h4.breakout else ("retest" if tf_h4.retest else None),
            "distance": _round(tf_h4.distance, 4),
        },
        "h1": {
            "last_close": _round(tf_h1.last_close),
            "prev_high": _round(tf_h1.prev_high),
            "prev_low": _round(tf_h1.prev_low),
            "signal": "breakout" if tf_h1.breakout else ("retest" if tf_h1.retest else None),
            "distance": _round(tf_h1.distance, 4),
        },
    }

    return {
        "symbol": sym,
        "setup": setup,
        "price": _round(last_price),
        "change_pct": _round(_safe_float(mover_meta.get("change_pct")), 2),
        "rvol": _round(intraday_rvol, 2) if intraday_rvol is not None else None,
        "timeframes": timeframes,
        "trend": {
            "daily_slope_pct": _round(daily_trend * 100.0, 2) if daily_trend else None,
        },
        "mover": mover_meta,
        "alignment_tags": alignment_tags,
        "components": {
            "alignment": round(alignment_score, 3),
            "price_liquidity": round(price_liq_score, 3),
            "rvol": round(rvol_score, 3),
            "trend": round(trend_score, 3),
        },
        "base_confidence": base_confidence,
        "notes": {
            "price": price_notes,
            "rvol": [rvol_note] if rvol_note else [],
            "trend": [trend_note] if trend_note else [],
        },
    }


async def _pick_near_atm(rows: List[Dict[str, Any]], last: float, topK: int = 3) -> List[Dict[str, Any]]:
    if not rows or last is None:
        return []
    def k(r):
        try:
            return abs(float(r.get('strike')) - float(last))
        except Exception:
            return 1e9
    out = sorted(rows, key=k)[:max(1, topK)]
    return out


async def _nbbo_enrich(poly: PolygonMarket, occ_syms: List[str], samples: int = 2, interval: float = 0.3) -> Dict[str, Dict[str, Any]]:
    res: Dict[str, Dict[str, Any]] = {s: {} for s in occ_syms}
    if not poly or not occ_syms:
        return res
    bids = {s: [] for s in occ_syms}; asks = {s: [] for s in occ_syms}
    for _ in range(samples):
        qs = await asyncio.gather(*[poly.option_quote(s) for s in occ_syms], return_exceptions=True)
        for s, q in zip(occ_syms, qs):
            if isinstance(q, dict):
                b = q.get('bid'); a = q.get('ask')
                if b is not None: bids[s].append(float(b))
                if a is not None: asks[s].append(float(a))
                if q.get('bid') is not None: res[s]['bid'] = float(q.get('bid'))
                if q.get('ask') is not None: res[s]['ask'] = float(q.get('ask'))
                if q.get('spread_pct') is not None: res[s]['spread_pct'] = float(q.get('spread_pct'))
        await asyncio.sleep(interval)
    for s in occ_syms:
        st = _spread_stability(bids[s], asks[s]) if bids[s] and asks[s] else None
        if st is not None:
            res[s]['spread_stability'] = st
    return res


def _options_score(row: Dict[str, Any]) -> float:
    try:
        sp = float(row.get('spread_pct') or 12.0)
        st = float(row.get('spread_stability') or 0.5)
        d = abs(float(row.get('delta') or 0.45))
        ivp = float(row.get('iv_percentile') or 50.0)
        oi = float(row.get('oi') or 0.0); vol = float(row.get('volume') or 0.0)
        sp_s = 1.0 - min(1.0, sp/12.0)
        d_s = 1.0 - min(1.0, abs(d - 0.45))
        iv_s = 1.0 - min(1.0, abs(ivp-50.0)/50.0)
        liq_s = min(1.0, oi/1500.0 + vol/6000.0)
        score = st*0.30 + sp_s*0.20 + d_s*0.25 + iv_s*0.10 + liq_s*0.15
        return round(max(0.0, min(1.0, score))*100.0, 1)
    except Exception:
        return 0.0


async def _options_summary(poly: PolygonMarket, symbol: str, last: Optional[float]) -> Optional[Dict[str, Any]]:
    if _td_expirations is None or _td_options_chain is None:
        return None
    try:
        exps = await _td_expirations(symbol)
    except Exception:
        return None
    if not exps:
        return None
    # choose expiries by horizon
    from datetime import date
    today = date.today()
    def _pick_date(target_days_min: int, target_days_max: int, prefer: Optional[str] = None) -> Optional[str]:
        candidates = []
        for e in exps:
            try:
                dd = date.fromisoformat(e)
                days = (dd - today).days
                if days >= target_days_min and days <= target_days_max:
                    weight = abs(days - ((target_days_min + target_days_max)/2.0))
                    if prefer and dd.strftime('%b').lower().startswith(prefer.lower()[:3]):
                        weight *= 0.6
                    candidates.append((weight, days, e))
            except Exception:
                continue
        if not candidates:
            # fallback to nearest above min
            above = []
            for e in exps:
                try:
                    dd = date.fromisoformat(e)
                    days = (dd - today).days
                    if days >= target_days_min:
                        weight = abs(days - target_days_min)
                        if prefer and dd.strftime('%b').lower().startswith(prefer.lower()[:3]):
                            weight *= 0.7
                        above.append((weight, days, e))
                except Exception:
                    continue
            if above:
                return sorted(above, key=lambda x: x[0])[0][2]
            return None
        return sorted(candidates, key=lambda x: x[0])[0][2]

    leap_prefer_months = ["jan", "mar", "jun", "sep", "dec"]
    leap_exp = None
    for pref in leap_prefer_months:
        leap_exp = _pick_date(300, 720, prefer=pref)
        if leap_exp:
            break
    if not leap_exp:
        leap_exp = _pick_date(270, 1000)

    targets = {
        'scalp': _pick_date(0, 0),          # today
        'intraday': _pick_date(0, 0),       # today
        'swing': _pick_date(30, 150),       # ~1–5 months
        'leaps': leap_exp,                  # prefer official LEAP cycle
    }
    out: Dict[str, Any] = {}
    for hz, exp in targets.items():
        if not exp:
            continue
        try:
            rows = await _td_options_chain(symbol, expiry=exp, greeks=True)
        except Exception:
            continue
        picks = await _pick_near_atm(rows, last or 0.0, topK=4)
        # only sample a couple of candidates for nbbo
        occs = [p.get('symbol') for p in picks if p.get('symbol')][:4]
        nbbo = await _nbbo_enrich(poly, occs) if occs else {}
        best = None
        best_score = -1.0
        for p in picks:
            sym = p.get('symbol')
            if sym in nbbo:
                p.update(nbbo[sym])
            sc = _options_score(p)
            if sc > best_score:
                best_score = sc
                best = p.copy()
                best['options_score'] = sc
        if best:
            entry = {
                'symbol': best.get('symbol'),
                'type': best.get('type'),
                'strike': best.get('strike'),
                'expiry': best.get('expiry') or exp,
                'bid': best.get('bid'),
                'ask': best.get('ask'),
                'spread_pct': best.get('spread_pct'),
                'spread_stability': best.get('spread_stability'),
                'delta': best.get('delta'),
                'iv': best.get('iv'),
                'oi': best.get('oi'),
                'volume': best.get('volume'),
                'options_score': best.get('options_score'),
            }
            try:
                from datetime import date
                exp_dt = date.fromisoformat(entry['expiry'])
                entry['days_to_exp'] = (exp_dt - today).days
                entry['expiry_display'] = exp_dt.strftime('%b %d, %Y')
            except Exception:
                pass
            out[hz] = entry
    return out or None


def _alignment_metrics(tf_daily: _TimeframeState, tf_h4: _TimeframeState, tf_h1: _TimeframeState) -> Tuple[float, List[str]]:
    tags: List[str] = []
    score = 0.0
    weights = {"h1": 0.42, "h4": 0.35, "daily": 0.23}

    def _contrib(tf: _TimeframeState, label: str, weight: float) -> float:
        if tf.breakout:
            tags.append(f"{label} breakout")
            return 1.0 * weight
        if tf.retest:
            tags.append(f"{label} retest")
            return 0.7 * weight
        return 0.0

    score += _contrib(tf_h1, "1H", weights["h1"])
    score += _contrib(tf_h4, "4H", weights["h4"])
    score += _contrib(tf_daily, "Daily", weights["daily"])
    return score, tags


def _price_liquidity_score(last_price: Optional[float], volume: Optional[float]) -> Tuple[float, List[str]]:
    notes: List[str] = []
    price = float(last_price or 0.0)
    vol = float(volume or 0.0)

    if price <= 0:
        return 0.2, notes

    if price >= 50:
        price_score = 1.0; notes.append("large-cap pricing")
    elif price >= 25:
        price_score = 0.9; notes.append("liquid mid/high price")
    elif price >= 15:
        price_score = 0.8
    elif price >= 5:
        price_score = 0.6; notes.append("mid-priced equity")
    elif price >= 3:
        price_score = 0.4; notes.append("low-priced")
    else:
        price_score = 0.15; notes.append("penny-priced")

    if vol >= 8_000_000:
        vol_score = 1.0; notes.append("heavy volume")
    elif vol >= 4_000_000:
        vol_score = 0.85
    elif vol >= 1_500_000:
        vol_score = 0.7
    elif vol >= 500_000:
        vol_score = 0.5
    else:
        vol_score = 0.25; notes.append("thin volume")

    score = price_score * 0.6 + vol_score * 0.4
    return min(1.0, max(0.0, score)), notes


def _rvol_score(rvol: Optional[float]) -> Tuple[float, Optional[str]]:
    if rvol is None:
        return 0.5, None
    if rvol >= 3.0:
        return 1.0, "rVol >3×"
    if rvol >= 2.0:
        return 0.85, "rVol >2×"
    if rvol >= 1.2:
        return 0.7, None
    if rvol >= 0.8:
        return 0.5, "rVol muted"
    return 0.35, "rVol soft"


def _trend_score(daily_trend: float) -> Tuple[float, Optional[str]]:
    if daily_trend is None:
        return 0.5, None
    if daily_trend >= 0.08:
        return 1.0, "strong uptrend"
    if daily_trend >= 0.03:
        return 0.8, "uptrend"
    if daily_trend >= -0.02:
        return 0.6, None
    if daily_trend >= -0.06:
        return 0.4, "trend soft"
    return 0.25, "downtrend risk"


def _options_grade(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


async def scan_top_setups(
    limit: int = 10,
    include_options: bool = False,
    symbols: Optional[List[str]] = None,
    strict: bool = True,
    min_confidence: int = 70,
) -> List[Dict[str, Any]]:
    if PolygonMarket is None:
        return []
    sym_key = ",".join(sorted([s.upper() for s in (symbols or [])])) if symbols else "auto"
    cache_key = f"top:{limit}:opts:{1 if include_options else 0}:syms:{sym_key}:strict:{1 if strict else 0}:minc:{min_confidence}"
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    poly = PolygonMarket()
    if symbols:
        unique_symbols = [s.upper() for s in symbols if s]
        movers = [{"symbol": s} for s in unique_symbols]
    else:
        try:
            movers = await poly.top_movers(limit=max(10, limit * 2))
        except Exception:
            movers = []
        sym_list = [m.get("symbol") for m in movers if m.get("symbol")]
        unique_symbols: List[str] = []
        for s in sym_list:
            if s not in unique_symbols:
                unique_symbols.append(s)
        unique_symbols = unique_symbols[: max(5, limit + 3)]

    results: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(5)

    async def _worker(sym: str, meta: Dict[str, Any]):
        async with sem:
            try:
                data = await _symbol_snapshot(poly, sym, meta)
                if data:
                    results.append(data)
            except Exception:
                return

    await asyncio.gather(*[_worker(sym, next((m for m in movers if m.get("symbol") == sym), {})) for sym in unique_symbols])
    # Enrich with options summaries if requested
    if include_options and PolygonMarket is not None and _td_expirations is not None:
        poly2 = PolygonMarket()
        async def _enrich(item: Dict[str, Any]):
            try:
                sym = item.get('symbol')
                last = item.get('price')
                opts = await _options_summary(poly2, sym, last)
                if opts:
                    item['options'] = opts
            except Exception:
                return
        await asyncio.gather(*[_enrich(r) for r in results])

    processed: List[Dict[str, Any]] = []
    for item in results:
        price = _safe_float(item.get('price')) or 0.0
        components = item.get('components') or {}
        alignment_score = float(components.get('alignment') or 0.0)
        price_liq_score = float(components.get('price_liquidity') or 0.0)
        rvol_score = float(components.get('rvol') or 0.0)
        trend_score = float(components.get('trend') or 0.0)

        options_component = 0.0
        option_best_note = None
        option_grade_best = None
        horizon_hits: List[str] = []

        opts = item.get('options') if include_options else None
        preferred_payload = None
        preferred_weight = -1.0
        if isinstance(opts, dict):
            for horizon, payload in list(opts.items()):
                if not isinstance(payload, dict):
                    continue
                sc = payload.get('options_score')
                grade = _options_grade(sc)
                if grade:
                    payload['grade'] = grade
                bid = payload.get('bid'); ask = payload.get('ask')
                if bid is not None and ask is not None and ask > 0:
                    try:
                        spread_pct = ((ask - bid)/ask)*100.0
                        payload.setdefault('spread_pct', round(spread_pct, 2))
                    except Exception:
                        pass
                if sc is not None:
                    val = max(0.0, min(1.0, float(sc)/100.0))
                    if horizon in ('scalp','intraday'):
                        weight = 1.05 if horizon == 'scalp' else 1.0
                    elif horizon == 'swing':
                        weight = 0.9
                    else:  # leaps
                        weight = 0.75
                    weighted = val * weight
                    if weighted > options_component:
                        options_component = weighted
                        option_best_note = f"{horizon} {grade or ''}".strip()
                        option_grade_best = grade
                    if grade in {'A','B'}:
                        horizon_hits.append(f"{horizon}:{grade}")
                    if weighted > preferred_weight:
                        preferred_weight = weighted
                        preferred_payload = {k: v for k, v in payload.items()}
                        preferred_payload['horizon'] = horizon
            if preferred_payload:
                item['preferred_option'] = preferred_payload
        else:
            item['preferred_option'] = None

        # Penalize if no tradable options and price is low
        if options_component == 0.0 and price < 5:
            options_component = 0.25

        base_confidence = float(item.get('base_confidence') or 0.0)
        final_confidence = (
            min(1.0, alignment_score) * 0.40
            + min(1.0, price_liq_score) * 0.20
            + min(1.0, options_component) * 0.25
            + min(1.0, rvol_score) * 0.1
            + min(1.0, trend_score) * 0.05
        )

        # Adjust for penny risk
        if price < 3:
            final_confidence *= 0.65
        elif price < 5:
            final_confidence *= 0.8

        confidence_pct = int(_clamp(round(final_confidence * 100)))
        if confidence_pct >= 80:
            grade = "High"
        elif confidence_pct >= 65:
            grade = "Moderate"
        else:
            grade = "Cautious"

        # Build confidence note
        notes: List[str] = []
        if item.get('alignment_tags'):
            notes.append(", ".join(item['alignment_tags']))
        for entry in item.get('notes', {}).get('price', []):
            notes.append(entry)
        rv_note = item.get('notes', {}).get('rvol', [])
        if rv_note:
            notes.extend(rv_note)
        tr_note = item.get('notes', {}).get('trend', [])
        if tr_note:
            notes.extend(tr_note)
        if option_best_note:
            notes.append(f"Options {option_best_note}")
        notes = [n for n in notes if n]

        # Apply guardrails for thin options
        if include_options:
            tradable = False
            if isinstance(opts, dict):
                for payload in opts.values():
                    if isinstance(payload, dict):
                        sc = payload.get('options_score')
                        if sc and sc >= 60:
                            tradable = True
                            break
            if not tradable and price < 5:
                continue  # skip illiquid low price names

        try:
            note = quote(item.get('setup') or '')
        except Exception:
            note = ''
        entry = sl = tp1 = tp2 = None
        try:
            tf = item.get('timeframes') or {}
            h1 = tf.get('h1') or {}
            h4 = tf.get('h4') or {}
            daily = tf.get('daily') or {}
            e = h1.get('prev_high') or h4.get('prev_high') or daily.get('prev_high')
            s = h1.get('prev_low') or h4.get('prev_low') or daily.get('prev_low')
            t1 = daily.get('last_high') or h4.get('last_high') or daily.get('prev_high')
            t2 = daily.get('prev_high') or daily.get('last_close')
            if isinstance(e, (int, float)):
                entry = round(float(e), 2)
            if isinstance(s, (int, float)):
                sl = round(float(s), 2)
            if isinstance(t1, (int, float)):
                tp1 = round(float(t1), 2)
            if isinstance(t2, (int, float)):
                tp2 = round(float(t2), 2)
        except Exception:
            entry = sl = tp1 = tp2 = None

        item['chart_params'] = {
            'entry': entry,
            'stop': sl,
            'tp1': tp1,
            'tp2': tp2,
        }

        preferred_hz = ((item.get('preferred_option') or {}).get('horizon') or '').lower()
        chart_interval = '15'
        if preferred_hz in ('swing',):
            chart_interval = '60'
        elif preferred_hz in ('leaps', 'leap', 'leaps '):
            chart_interval = '1d'
        url_interval = '15' if chart_interval == '15' else ('1h' if chart_interval == '60' else chart_interval)

        if item.get('symbol'):
            import time as _t
            cb = int(_t.time())
            url = f"{_PUBLIC_BASE}/charts/tradingview?symbol={item['symbol']}&interval={url_interval}&note={note}&cb={cb}"
            if entry is not None:
                url += f"&entry={entry}"
            if sl is not None:
                url += f"&sl={sl}"
            if tp1 is not None:
                url += f"&tp1={tp1}"
            if tp2 is not None:
                url += f"&tp2={tp2}"
            item['chart_url'] = url
        else:
            item['chart_url'] = None

        item['score'] = confidence_pct
        item['confidence'] = confidence_pct
        item['confidence_grade'] = grade
        item['confidence_note'] = "; ".join(notes[:3]) if notes else None
        item['options_summary'] = opts if isinstance(opts, dict) else None
        item['highlights'] = horizon_hits

        processed.append(item)

    ranked_all = sorted(processed, key=lambda x: x.get("score", 0), reverse=True)

    filtered: List[Dict[str, Any]] = []
    for item in ranked_all:
        if item.get('confidence', 0) < (min_confidence or 70):
            continue
        price = _safe_float(item.get('price')) or 0.0
        if price < 3:
            continue
        pref = item.get('preferred_option') if include_options else None
        if include_options:
            if not pref:
                continue
            grade = pref.get('grade')
            bid = pref.get('bid'); ask = pref.get('ask'); spread_pct = pref.get('spread_pct')
            if grade not in {'A','B'}:
                continue
            if bid is None or ask is None:
                continue
            try:
                if spread_pct is None and ask > 0:
                    spread_pct = ((ask - bid)/ask)*100.0
                if spread_pct is None or float(spread_pct) > 12.0:
                    continue
            except Exception:
                continue
            try:
                oi = float(pref.get('oi') or 0.0)
            except Exception:
                oi = 0.0
            try:
                vol = float(pref.get('volume') or 0.0)
            except Exception:
                vol = 0.0
            if oi < 200 and vol < 200:
                continue
        filtered.append(item)

    # ensure diverse horizons
    priority_order = ['scalp', 'intraday', 'swing', 'leaps']
    selected: List[Dict[str, Any]] = []
    used_horizons = set()
    for hz in priority_order:
        for item in filtered:
            pref = item.get('preferred_option')
            if pref and pref.get('horizon') == hz and hz not in used_horizons:
                selected.append(item)
                used_horizons.add(hz)
                break

    for item in filtered:
        if len(selected) >= limit:
            break
        if item in selected:
            continue
        selected.append(item)

    ranked = selected[:limit]
    # Fallback: if no items survived and caller specified symbols, return best-available with quality flags
    if not ranked and symbols and ranked_all:
        fallback: List[Dict[str, Any]] = []
        for item in ranked_all:
            gates_missed: List[str] = []
            if (item.get('confidence', 0) < (min_confidence or 70)):
                gates_missed.append('confidence')
            price = _safe_float(item.get('price')) or 0.0
            if price < 3:
                gates_missed.append('price')
            pref = item.get('preferred_option') if include_options else None
            allow_grade_c = False
            if include_options:
                if not pref:
                    gates_missed.append('options_missing')
                else:
                    grade = pref.get('grade')
                    if grade not in {'A', 'B'}:
                        if grade == 'C':
                            try:
                                oi_val = float(pref.get('oi') or 0.0)
                            except Exception:
                                oi_val = 0.0
                            if item.get('symbol') in _BLUE_CHIP and oi_val >= 5000:
                                allow_grade_c = True
                            else:
                                gates_missed.append('options_grade')
                        else:
                            gates_missed.append('options_grade')
                    sp = pref.get('spread_pct')
                    if sp is None:
                        b = pref.get('bid'); a = pref.get('ask')
                        try:
                            if b is not None and a is not None and a > 0:
                                sp = ((a - b)/a)*100.0
                        except Exception:
                            sp = None
                    try:
                        if sp is None or float(sp) > 20.0:
                            gates_missed.append('spread')
                    except Exception:
                        gates_missed.append('spread')
            # Only surface fallback if options are usable (grade A/B, or grade C on blue chips) when include_options is True
            if include_options:
                if 'options_missing' in gates_missed:
                    continue
                grade_miss = 'options_grade' in gates_missed
                spread_miss = 'spread' in gates_missed
                if grade_miss and not allow_grade_c:
                    continue
                if spread_miss:
                    continue
                if grade_miss and allow_grade_c:
                    gates_missed.remove('options_grade')
            clone = dict(item)
            clone['quality_gate'] = False
            clone['gate_misses'] = gates_missed
            fallback.append(clone)
        ranked = sorted(fallback, key=lambda x: x.get('score', 0), reverse=True)[:max(1, min(limit, 3))]

    _CACHE[cache_key] = (now, ranked)
    return ranked

from __future__ import annotations

import json
from html import escape
from string import Template
from typing import Optional, Tuple
from urllib.parse import quote_plus

from fastapi import APIRouter, Query, Response
from fastapi.responses import RedirectResponse
import base64, json as _json

router = APIRouter(prefix="/charts", tags=["charts"])


_INTERVAL_ALIASES = {
    "1": "1m",
    "1m": "1m",
    "1min": "1m",
    "1minute": "1m",
    "5": "5m",
    "5m": "5m",
    "5min": "5m",
    "5minute": "5m",
    "15": "15m",
    "15m": "15m",
    "15min": "15m",
    "15minute": "15m",
    "d": "1d",
    "1d": "1d",
    "day": "1d",
    "daily": "1d",
}


_INTERVAL_CONFIG = {
    "1m": {"fetch": "1m", "group": 1, "default_lookback": 390},
    "5m": {"fetch": "5m", "group": 1, "default_lookback": 120},
    "15m": {"fetch": "5m", "group": 3, "default_lookback": 120},
    "1d": {"fetch": "1d", "group": 1, "default_lookback": 180},
}


def _normalize_interval(value: Optional[str], *, default: str) -> str:
    raw = (value or "").strip().lower()
    normalized = _INTERVAL_ALIASES.get(raw, raw or default)
    return normalized if normalized in _INTERVAL_CONFIG else default


def _interval_prefs(interval: str) -> Tuple[str, int, int]:
    cfg = _INTERVAL_CONFIG.get(interval, _INTERVAL_CONFIG["1m"])
    return cfg["fetch"], cfg["group"], cfg["default_lookback"]


def _tv_interval(normalized: str) -> str:
    mapping = {
        "1m": "1",
        "5m": "5",
        "15m": "15",
        "1d": "D",
    }
    return mapping.get(normalized, "15")


def _b64url_encode(obj: dict) -> str:
    raw = _json.dumps(obj, separators=(",", ":")).encode("utf-8")
    code = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return code


def _b64url_decode(code: str) -> dict:
    try:
        pad = '=' * (-len(code) % 4)
        raw = base64.urlsafe_b64decode((code + pad).encode("ascii"))
        return _json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


@router.get("/view")
async def view_short(c: str) -> Response:
    """Decode a compact code and redirect to /charts/proposal with full query.

    Usage: /charts/view?c=<base64url-json>
    """
    params = _b64url_decode(c or "")
    # Guard: only allow a known set of keys
    allowed = {
        "symbol","interval","lookback","overlays","entry","sl","tp1","tp2",
        "direction","confluence","em_abs","em_rel","anchor","hit_tp1","hit_tp2",
        "state","plan","theme","entry_time","width","height"
    }
    clean = {k: v for k, v in params.items() if k in allowed and v is not None}
    if "symbol" not in clean:
        return Response(content="Missing symbol", media_type="text/plain", status_code=400)
    from urllib.parse import urlencode
    return RedirectResponse(url="/charts/proposal?" + urlencode(clean, doseq=False), status_code=307)


def _normalize_levels(
    entry: Optional[float],
    sl: Optional[float],
    tp1: Optional[float],
    tp2: Optional[float],
    direction: str,
    em_abs: Optional[float],
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    from app.engine.position_guidance import adjust_targets_for_em

    dir_norm = "short" if (direction or "").lower().startswith("s") else "long"

    def _num(val: Optional[float]) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except Exception:
            return None

    entry_val = _num(entry)
    sl_val = _num(sl)
    tp1_val = _num(tp1)
    tp2_val = _num(tp2)
    em_val = _num(em_abs)

    # Expected move anchored guidance
    if entry_val is not None and em_val:
        guidance = adjust_targets_for_em(entry=entry_val, em_abs=em_val, direction=dir_norm)
        g_tp1 = guidance.get("tp1")
        g_tp2 = guidance.get("tp2")
        g_sl = guidance.get("sl_hint")
        if g_tp1 is not None:
            if tp1_val is None:
                tp1_val = g_tp1
            elif dir_norm == "long" and tp1_val < g_tp1:
                tp1_val = g_tp1
            elif dir_norm == "short" and tp1_val > g_tp1:
                tp1_val = g_tp1
        if g_tp2 is not None:
            if tp2_val is None:
                tp2_val = g_tp2
            elif dir_norm == "long" and tp2_val < g_tp2:
                tp2_val = g_tp2
            elif dir_norm == "short" and tp2_val > g_tp2:
                tp2_val = g_tp2
        if sl_val is None and g_sl is not None:
            sl_val = g_sl

    # Ensure stop is on the correct side of entry
    if entry_val is not None and sl_val is not None:
        if dir_norm == "long" and sl_val >= entry_val:
            sl_val = (entry_val - abs(tp1_val - entry_val) if tp1_val is not None else entry_val - (em_val or max(entry_val * 0.003, 0.2)))
        elif dir_norm == "short" and sl_val <= entry_val:
            sl_val = (entry_val + abs(tp1_val - entry_val) if tp1_val is not None else entry_val + (em_val or max(entry_val * 0.003, 0.2)))

    # Enforce minimum risk:reward if we have valid stop
    if entry_val is not None and sl_val is not None and sl_val != entry_val:
        risk = abs(entry_val - sl_val)
        min_rr1 = 1.0
        min_rr2 = 1.5
        if dir_norm == "long":
            min_tp1 = entry_val + min_rr1 * risk
            min_tp2 = entry_val + min_rr2 * risk
            if tp1_val is None or tp1_val < min_tp1:
                tp1_val = min_tp1
            if tp2_val is None or tp2_val < min_tp2:
                tp2_val = min_tp2
        else:
            min_tp1 = entry_val - min_rr1 * risk
            min_tp2 = entry_val - min_rr2 * risk
            if tp1_val is None or tp1_val > min_tp1:
                tp1_val = min_tp1
            if tp2_val is None or tp2_val > min_tp2:
                tp2_val = min_tp2

    def _round(val: Optional[float]) -> Optional[float]:
        if val is None:
            return None
        try:
            return round(float(val), 4)
        except Exception:
            return None

    return _round(entry_val), _round(sl_val), _round(tp1_val), _round(tp2_val)


@router.get("/proposal")
async def chart_proposal(
    symbol: str,
    interval: str = Query("1m"),
    lookback: int = 390,
    overlays: str = Query("vwap,ema20,ema50,pivots"),
    entry: float | None = None,
    sl: float | None = None,
    tp1: float | None = None,
    tp2: float | None = None,
    entry_time: int | None = None,
    direction: str = Query("long"),
    confluence: str = Query(""),
    em_abs: float | None = None,
    em_rel: float | None = None,
    anchor: str = Query("entry"),
    hit_tp1: float | None = None,
    hit_tp2: float | None = None,
    theme: str = Query("dark"),
    plan: str = Query(""),
    state: str = Query(""),
    width: int = 1200,
    height: int = 650,
) -> Response:
    sym = escape((symbol or "").upper())
    dir_norm = "short" if (direction or "").lower().startswith("s") else "long"
    overlays = escape(overlays)
    theme_key = "dark" if (theme or "").lower() == "dark" else "light"
    width = max(640, min(1920, int(width)))
    height = max(360, min(1080, int(height)))

    interval_norm = _normalize_interval(interval, default="1m")
    fetch_interval, group_size, lookback_default = _interval_prefs(interval_norm)
    try:
        lookback_int = int(lookback)
    except Exception:
        lookback_int = lookback_default
    if lookback_int <= 0:
        lookback_int = lookback_default
    lookback_int = min(max(lookback_int, 30), 5000)

    fetch_lookback = min(max(lookback_int * max(1, group_size), 30), 5000)

    entry_val, sl_val, tp1_val, tp2_val = _normalize_levels(entry, sl, tp1, tp2, dir_norm, em_abs)

    def _js_num(v: Optional[float]) -> str:
        return "null" if v is None else json.dumps(v)

    color_theme = {
        "dark": {
            "bg": "#0d1117",
            "text": "#c9d1d9",
            "grid": "#161b22",
            "border": "#30363d",
            "badge": "#161b22",
        },
        "light": {
            "bg": "#ffffff",
            "text": "#111111",
            "grid": "#eeeeee",
            "border": "#dddddd",
            "badge": "#f8f8f8",
        },
    }
    colors = color_theme[theme_key]
    interval_display = escape(interval_norm)
    fetch_interval_display = escape(fetch_interval)
    anchor_norm = "last" if (anchor or "").lower() == "last" else "entry"
    em_abs_js = _js_num(em_abs if em_abs is not None else None)
    em_rel_js = _js_num(em_rel if em_rel is not None else None)
    hit1_js = _js_num(hit_tp1 if hit_tp1 is not None else None)
    hit2_js = _js_num(hit_tp2 if hit_tp2 is not None else None)
    entry_js = _js_num(entry_val)
    sl_js = _js_num(sl_val)
    tp1_js = _js_num(tp1_val)
    tp2_js = _js_num(tp2_val)
    state_text = escape(state or "")
    plan_safe = escape(plan or "", quote=True)
    confluence_safe = escape(confluence or "", quote=True)
    tpl = Template("""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>${SYM} – Proposal</title>
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    html, body { margin: 0; padding: 0; background: ${BG}; height: 100%; width: 100%; }
    #wrap { width: min(100vw, ${WIDTH}px); height: min(100vh, ${HEIGHT}px); margin: 0 auto; }
    #chart { width: 100%; height: 100%; display: block; }
    .legend { position:absolute; left:8px; top:8px; color:${TEXT}; font: 12px/1.4 -apple-system,Segoe UI,Arial; background: transparent; }
    .symbol { position:absolute; left:8px; top:26px; color:${TEXT}; font: 14px/1.4 -apple-system,Segoe UI,Arial; opacity: 0.9; }
    .panel { position:absolute; left:8px; bottom:8px; max-width:min(460px, 95vw); padding:10px 12px; border-radius:8px; background:${BADGE_BG}; color:${TEXT}; border:1px solid ${BORDER}; font: 12px/1.5 -apple-system,Segoe UI,Arial; }
    .panel h4 { margin: 0 0 6px 0; font-size: 13px; }
    .panel ul { margin: 6px 0 0; padding-left: 18px; }
    .panel li { margin: 3px 0; }
    .badges { position:absolute; right:8px; top:8px; display:flex; gap:6px; flex-wrap:wrap; max-width:50%; }
    .badge { padding:2px 6px; border-radius:10px; font-size:11px; border:1px solid ${BORDER}; color:${TEXT}; background:${BADGE_BG}; }
    .tools { position:absolute; right:8px; top:44px; display:flex; align-items:center; gap:6px; background:${BADGE_BG}; border:1px solid ${BORDER}; border-radius:8px; padding:6px 8px; }
    .tools label { font-size:11px; color:${TEXT}; margin-right:2px; }
    .tools select, .tools button { font-size:11px; padding:3px 6px; border-radius:6px; border:1px solid ${BORDER}; background:${BG}; color:${TEXT}; }
  </style>
</head>
<body>
    <div id="wrap">
      <div id="chart"></div>
      <div class="legend" id="legend">${SYM} ${INTERVAL} · overlays: ${OVERLAYS}</div>
      <div class="symbol" id="symbolTag">${SYM}</div>
      <div class="badges" id="badges"></div>
      <div class="tools" id="tools">
      <label for="selInterval">Timeframe</label>
      <select id="selInterval">
        <option value="1m">1m</option>
        <option value="5m">5m</option>
        <option value="15m">15m</option>
        <option value="1d">1d</option>
      </select>
      <button id="btnFit">Fit</button>
      <button id="btnRefresh">Refresh</button>
    </div>
    <div class="panel" id="planPanel" style="display:none"></div>
  </div>
  <script>
    const params = new URLSearchParams({ symbol: '${SYM}', interval: '${FETCH_INTERVAL}', lookback: '${FETCH_LOOKBACK}' });
    const apiBase = (window.location && window.location.origin) || '';
    const url = apiBase + '/api/v1/market/bars?' + params.toString();
    const levelsUrl = apiBase + '/api/v1/market/levels?symbol=${SYM}';
    const theme = '${THEME}';
    const dir = '${DIR}' === 'long' ? 'long' : 'short';
    const want = (name) => '${OVERLAYS}'.split(',').map(s => s.trim().toLowerCase()).includes(name);
    const confluence = '${CONFLUENCE}'.split(',').map(s => s.trim()).filter(Boolean);
    const emAbs = ${EM_ABS};
    const emRel = ${EM_REL};
    const anchor = '${ANCHOR}'.toLowerCase() === 'last' ? 'last' : 'entry';
    const hit1 = ${HIT1};
    const hit2 = ${HIT2};
    const planRaw = `${PLAN}`;
    const prettyOverlays = () => '${OVERLAYS}'.split(',').map(s => s.trim().toLowerCase()).map(s => {
      if (s === 'vwap') return 'VWAP';
      if (s.startsWith('ema')) return s.toUpperCase();
      if (s === 'pivots' || s === 'levels') return 'Pivots';
      return s;
    }).join(' + ');

    function ema(values, period) {
      const k = 2/(period+1);
      let e = values[0];
      const out = [];
      for (let i=0;i<values.length;i++) {
        e = values[i]*k + e*(1-k);
        out.push(e);
      }
      return out;
    }

    function computeVWAP(bars) {
      let cumPV = 0; let cumV = 0; const out = [];
      for (const b of bars) {
        const tp = (b.h + b.l + b.c)/3.0;
        const v = b.v || 0;
        cumPV += tp * v;
        cumV += v;
        const vwap = cumV>0 ? (cumPV/cumV) : tp;
        out.push({ time: Math.floor(b.t/1000), value: vwap });
      }
      return out;
    }

    let chart = null;
    async function main() {
      const el = document.getElementById('chart');
      if (typeof LightweightCharts === 'undefined') {
        el.innerHTML = '<div style="color:#f00;padding:16px">Chart library failed to load. Please allow CDN scripts or try again.</div>';
        return;
      }
      chart = LightweightCharts.createChart(el, {
        autoSize: true,
        layout: { background: { type: 'Solid', color: '${BG}' }, textColor: '${TEXT}' },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
        grid: { vertLines: { color: '${GRID}' }, horzLines: { color: '${GRID}' } },
        crosshair: { mode: 1 }
      });

      const candleSeries = chart.addCandlestickSeries({
        upColor: '#22c55e', downColor: '#ef4444', borderVisible: false, wickUpColor: '#22c55e', wickDownColor: '#ef4444'
      });

      async function fetchBars(intv, lookbackOverride) {
        const p = new URLSearchParams({ symbol: '${SYM}', interval: intv, lookback: lookbackOverride || '${FETCH_LOOKBACK}' });
        const u = apiBase + '/api/v1/market/bars?' + p.toString();
        try {
          const r = await fetch(u);
          if (!r.ok) return [];
          const jj = await r.json();
          if (jj && jj.ok && Array.isArray(jj.bars) && jj.bars.length) return jj.bars;
        } catch (e) {}
        return [];
      }
      let bars = await fetchBars('${FETCH_INTERVAL}');
      let groupSize = ${GROUP_SIZE};
      if (!bars.length && '${FETCH_INTERVAL}' === '1m') {
        bars = await fetchBars('5m');
        groupSize = ${GROUP_SIZE};
      }
      if (!bars.length && '${FETCH_INTERVAL}' !== '1d') {
        bars = await fetchBars('1d', '${LOOKBACK}');
        groupSize = 1;
      }
      if (!bars.length) {
        el.innerHTML = '<div style="color:${TEXT};padding:16px">No data available for ${SYM} (${INTERVAL}). Try a different timeframe or check market hours.</div>';
        return;
      }

      function aggregateBars(raw, group) {
        if (!Array.isArray(raw) || group <= 1) return raw;
        const out = [];
        let bucket = null;
        let count = 0;
        for (const b of raw) {
          if (bucket === null) {
            bucket = { ...b };
            bucket.h = b.h;
            bucket.l = b.l;
            bucket.v = b.v || 0;
            count = 1;
          } else {
            bucket.h = Math.max(bucket.h, b.h);
            bucket.l = Math.min(bucket.l, b.l);
            bucket.c = b.c;
            bucket.v = (bucket.v || 0) + (b.v || 0);
            bucket.t = b.t;
            count += 1;
          }
          if (count === group) {
            out.push({ ...bucket });
            bucket = null;
            count = 0;
          }
        }
        if (bucket) {
          out.push({ ...bucket });
        }
        return out;
      }

      const normalizedBars = aggregateBars(bars, groupSize);
      const data = normalizedBars.map(b => ({ time: Math.floor(b.t/1000), open: b.o, high: b.h, low: b.l, close: b.c }));
      candleSeries.setData(data);
      // Fit content to visible range for readability
      try { chart.timeScale().fitContent(); } catch (e) {}

      const addOverlayLabel = (name, value, color) => {
        if (value===null || value===undefined || Number.isNaN(value)) return;
        try { candleSeries.createPriceLine({ price: Number(value), color, lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: name }); } catch(e) {}
      };

      if (want('vwap')) {
        const vwapSeries = chart.addLineSeries({ color: '#60a5fa', lineWidth: 2, lastValueVisible: true, priceLineVisible: false });
        const vwapData = computeVWAP(normalizedBars);
        vwapSeries.setData(vwapData);
        const vwapLast = (vwapData.slice(-1)[0]||{}).value;
        addOverlayLabel('VWAP', vwapLast, '#60a5fa');
      }

      const closes = normalizedBars.map(b => b.c);
      function overlayEMA(period, color) {
        const arr = ema(closes, period);
        const line = chart.addLineSeries({ color, lineWidth: 1, lastValueVisible: true, priceLineVisible: false });
        const arrData = normalizedBars.map((b, i) => ({ time: Math.floor(b.t/1000), value: arr[i] }));
        line.setData(arrData);
        const lastVal = arrData.length ? arrData[arrData.length-1].value : null;
        addOverlayLabel(('EMA ' + String(period)), lastVal, color);
      }
      if (want('ema20')) overlayEMA(20, '#f59e0b');
      if (want('ema50')) overlayEMA(50, '#a855f7');

      const p = (x) => (x===null || x===undefined || isNaN(x)) ? null : Number(x);
      let entry = p(${ENTRY});
      let sl = p(${SL});
      let tp1 = p(${TP1});
      let tp2 = p(${TP2});
      // If TP lines are missing but entry/stop exist, synthesize horizon-aware targets
      try {
        if (entry !== null && sl !== null && (tp1 === null || tp2 === null)) {
          const risk = Math.abs(entry - sl);
          // Interval → horizon
          const itv = '${INTERVAL}';
          const isScalp = (itv === '1m' || itv === '5m');
          const isIntraday = (itv === '15m');
          const isDaily = (itv === '1d');
          const emv = (emAbs!==null && !isNaN(emAbs)) ? Number(emAbs) : null;
          // EM-based target distances per horizon
          let d1 = null, d2 = null;
          if (emv !== null) {
            if (isScalp) { d1 = 0.50*emv; d2 = 1.00*emv; }
            else if (isIntraday) { d1 = 0.70*emv; d2 = 1.20*emv; }
            else if (isDaily) { d1 = 1.00*emv; d2 = 1.80*emv; }
            else { d1 = 1.50*emv; d2 = 2.50*emv; }
          }
          const rr1 = 1.2*risk, rr2 = 2.0*risk;
          const dist1 = Math.max(d1 ?? 0, rr1);
          const dist2 = Math.max(d2 ?? 0, rr2, dist1*1.25);
          if (dir === 'long') {
            if (tp1 === null) tp1 = entry + dist1;
            if (tp2 === null) tp2 = entry + dist2;
          } else {
            if (tp1 === null) tp1 = entry - dist1;
            if (tp2 === null) tp2 = entry - dist2;
          }
          // Enforce a meaningful gap between TP1/TP2
          const minGap = Math.max(0.0025*entry, (emv ? 0.20*emv : 0.5*risk));
          if (Math.abs(tp2 - tp1) < minGap) {
            if (dir === 'long') tp2 = tp1 + minGap; else tp2 = tp1 - minGap;
          }
        }
      } catch(e) {}
      const entryTime = ${ENTRY_TIME};
      function priceLine(value, title, color) {
        if (value===null) return;
        candleSeries.createPriceLine({ price: value, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title });
      }
      priceLine(entry, 'Entry', '#16a34a');
      priceLine(sl, 'Stop Loss', '#ef4444');
      priceLine(tp1, 'Target 1', '#60a5fa');
      priceLine(tp2, 'Target 2', '#60a5fa');
      try {
        const lastClose = (data && data.length) ? Number(data[data.length-1].close) : null;
        if (lastClose !== null) candleSeries.createPriceLine({ price: lastClose, color: theme==='dark' ? '#e5e7eb' : '#111827', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'Current' });
      } catch(e) {}

      if (entryTime) {
        const marker = {
          time: Math.floor(entryTime/1000),
          position: (dir === 'long' ? 'belowBar' : 'aboveBar'),
          color: (dir === 'long' ? '#16a34a' : '#ef4444'),
          shape: (dir === 'long' ? 'arrowUp' : 'arrowDown'),
          text: 'Entry'
        };
        candleSeries.setMarkers([marker]);
      }

      if (emAbs !== null && !isNaN(emAbs)) {
        let base = null;
        if (anchor === 'entry' && entry !== null) base = entry;
        if ((base === null || base === undefined) && data && data.length) {
          base = data[data.length - 1].close;
        }
        if (base !== null && base !== undefined) {
          const hi = Number(base) + Number(emAbs);
          const lo = Number(base) - Number(emAbs);
          priceLine(hi, 'EM Upper', '#7c3aed');
          priceLine(lo, 'EM Lower', '#7c3aed');
      }
    }

      if (want('pivots') || want('levels')) {
        try {
          const levResp = await fetch(levelsUrl);
          const L = await levResp.json();
          if (L.ok && L.pivots) {
            const colors = { P: '#999', R1: '#f59e0b', R2: '#f59e0b', S1: '#3b82f6', S2: '#3b82f6' };
            const labels = { P: 'Pivot (P)', R1: 'Resistance 1', R2: 'Resistance 2', S1: 'Support 1', S2: 'Support 2' };
            for (const k of Object.keys(L.pivots)) {
              const val = L.pivots[k];
              if (val!==null && val!==undefined) {
                candleSeries.createPriceLine({ price: Number(val), color: colors[k]||'#888', lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: labels[k] || k });
              }
            }
          }
        } catch (e) {}
      }

      const badges = document.getElementById('badges');
      const addBadge = (label) => {
        const b = document.createElement('span');
        b.className = 'badge';
        b.textContent = label;
        badges.appendChild(b);
      };
      if (confluence && confluence.length) {
        const pretty = (t) => {
          const map = {
            'liquidity_ok': 'Liquidity OK',
            'liquidity_light': 'Thin Liquidity',
            'spread_tight': 'Tight Spread',
            'spread_wide': 'Wide Spread',
            'stability_ok': 'Spread Stable',
            'iv_mid': 'IV Mid',
            'iv_extreme': 'IV Extreme',
            'ev_positive': 'EV +',
            'ev_negative': 'EV −',
            'delta_fit': 'Δ Fit',
          };
          return map[t] || t.replace(/_/g,' ').replace(/\b\w/g, s=>s.toUpperCase());
        };
        for (const name of confluence) addBadge(pretty(name));
      }
      if (emAbs !== null && !isNaN(emAbs)) addBadge('EM ± ' + Number(emAbs).toFixed(2));
      if (emRel !== null && !isNaN(emRel)) addBadge('EM ' + (Number(emRel)*100).toFixed(1) + '%');
      if ('${STATE}'.length) addBadge('${STATE}');
      const pctFmt = (x) => (x==null || isNaN(x)) ? null : (x > 1.5 ? Number(x) : Number(x)*100);
      const h1 = pctFmt(hit1); const h2 = pctFmt(hit2);
      if (h1 !== null) addBadge('P(TP1) ~ ' + h1.toFixed(0) + '%');
      if (h2 !== null) addBadge('P(TP2) ~ ' + h2.toFixed(0) + '%');
      // Make legend text more intuitive
      try { document.getElementById('legend').textContent = '${SYM} ${INTERVAL} • ' + prettyOverlays(); } catch (e) {}

      // Tools: initialize states and handlers (Timeframe, Fit, Refresh)
      const on = (id, fn) => { const el=document.getElementById(id); if (el) el.onclick = fn; };
      const iv = document.getElementById('selInterval'); if (iv) iv.value='${INTERVAL}';
      on('btnRefresh', ()=>location.reload());
      on('btnFit', ()=>{ try { chart.timeScale().fitContent(); } catch(e){} });
      if (iv) iv.onchange = () => {
        const params = new URLSearchParams(location.search);
        const itv = iv.value;
        params.set('interval', itv);
        if (!params.get('lookback')) {
          params.set('lookback', itv==='1d'? '180' : itv==='5m'? '120' : itv==='15m'? '120' : '390');
        }
        location.search = params.toString();
      };

      // Strategy plan panel for beginners (auto text if not provided)
      const panel = document.getElementById('planPanel');
      if (panel) {
        const items = (planRaw||'').split('|').map(s=>s.trim()).filter(Boolean);
        const last = data[data.length-1].close;
        const vwapArr = computeVWAP(normalizedBars); const vwapLast = (vwapArr.slice(-1)[0]||{}).value;
        const state = (vwapLast!=null && !isNaN(vwapLast)) ? (last>=vwapLast ? 'Price is above VWAP (bullish bias)' : 'Price is below VWAP (bearish bias)') : 'VWAP unavailable';
        let html = '<h4>Strategy Plan</h4>';
        html += '<div>'+state+'. Use VWAP and Pivots as context (P/R/S lines).</div>';
        const list = items.length? items : (function(){
          const b=[];
          if (dir==='long') { b.push('Step 1 — Confirmation: wait for a clean break and 1–2 candles to hold above Entry.'); b.push('Step 2 — Entry: buy on a quick retest that holds (avoid chasing).'); }
          else { b.push('Step 1 — Confirmation: wait for a clean break and 1–2 candles to hold below Entry.'); b.push('Step 2 — Entry: short on a quick retest that fails (avoid chasing).'); }
          b.push('Risk — Stop Loss at the red line; exit quickly if hit.');
          b.push('Targets — Take partial at Target 1 (~0.25×EM); consider runner to Target 2 (~0.50×EM).');
          if (h1!=null) b.push('Approx P(Target 1) ~ '+h1.toFixed(0)+'% (touch probability).');
          if (h2!=null) b.push('Approx P(Target 2) ~ '+h2.toFixed(0)+'% (touch probability).');
          b.push('Skip/Size Down — if spreads widen, quotes unstable, or liquidity is light.');
          return b;
        })();
        html += '<ul>' + list.map(s=>'<li>'+s.replace(/</g,'&lt;').replace(/>/g,'&gt;')+'</li>').join('') + '</ul>';
        panel.innerHTML = html; panel.style.display='block';
      }
    }
    (function bootstrap(){
      if (typeof LightweightCharts !== 'undefined') { main(); return; }
      try {
        const alt = 'https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js';
        const s = document.createElement('script');
        s.src = alt; s.async = true; s.onload = () => main();
        s.onerror = () => { try { document.getElementById('chart').innerHTML = '<div style="color:#f00;padding:16px">Chart library failed to load from both CDNs.</div>'; } catch(e) {} };
        document.head.appendChild(s);
      } catch (e) { try { document.getElementById('chart').innerHTML = '<div style="color:#f00;padding:16px">Chart library failed to load. Please try again.</div>'; } catch(_) {} }
    })();
  </script>
</body>
</html>
""")
    html = tpl.substitute({
        'SYM': sym,
        'INTERVAL': interval_display,
        'LOOKBACK': str(lookback_int),
        'FETCH_INTERVAL': fetch_interval_display,
        'FETCH_LOOKBACK': str(fetch_lookback),
        'GROUP_SIZE': str(max(1, group_size)),
        'OVERLAYS': overlays,
        'THEME': theme_key,
        'DIR': dir_norm,
        'CONFLUENCE': confluence_safe,
        'EM_ABS': em_abs_js,
        'EM_REL': em_rel_js,
        'ANCHOR': anchor_norm,
        'HIT1': hit1_js,
        'HIT2': hit2_js,
        'BG': colors['bg'],
        'TEXT': colors['text'],
        'GRID': colors['grid'],
        'BORDER': colors['border'],
        'BADGE_BG': colors['badge'],
        'WIDTH': str(width),
        'HEIGHT': str(height),
        'PLAN': plan_safe,
        'ENTRY': entry_js,
        'SL': sl_js,
        'TP1': tp1_js,
        'TP2': tp2_js,
        'ENTRY_TIME': 'null' if entry_time is None else str(int(entry_time)),
        'STATE': state_text,
    })
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/tradingview")
async def tradingview_chart(
    symbol: str,
    interval: str = Query("15"),
    direction: str = Query("long"),
    entry: float | None = None,
    sl: float | None = None,
    tp1: float | None = None,
    tp2: float | None = None,
    em_abs: float | None = None,
    em_rel: float | None = None,
    hit_tp1: float | None = None,
    hit_tp2: float | None = None,
    theme: str = Query("dark"),
    note: str = Query(""),
) -> Response:
    sym = (symbol or "").upper().strip()
    if not sym:
        return Response(content="Symbol required", media_type="text/plain", status_code=400)

    dir_norm = "short" if (direction or "").lower().startswith("s") else "long"
    interval_norm = _normalize_interval(interval, default="15m")
    tv_interval = _tv_interval(interval_norm)

    entry_val, sl_val, tp1_val, tp2_val = _normalize_levels(entry, sl, tp1, tp2, dir_norm, em_abs)

    def _fmt(value: Optional[float]) -> str:
        if value is None:
            return "--"
        try:
            return f"{float(value):.2f}"
        except Exception:
            return "--"

    def _prob_pct(value: Optional[float]) -> Optional[int]:
        if value is None:
            return None
        try:
            v = float(value)
        except Exception:
            return None
        if v <= 1.0:
            v *= 100.0
        return int(round(v))

    risk_val = abs(entry_val - sl_val) if entry_val is not None and sl_val is not None else None
    tp1_r = abs(tp1_val - entry_val) if entry_val is not None and tp1_val is not None else None
    tp2_r = abs(tp2_val - entry_val) if entry_val is not None and tp2_val is not None else None
    rr1 = (tp1_r / risk_val) if risk_val and tp1_r is not None else None
    rr2 = (tp2_r / risk_val) if risk_val and tp2_r is not None else None

    overview = (
        f"<div><strong>Entry</strong> {_fmt(entry_val)} · "
        f"<strong>Stop</strong> {_fmt(sl_val)} · "
        f"<strong>TP1</strong> {_fmt(tp1_val)} · "
        f"<strong>TP2</strong> {_fmt(tp2_val)}</div>"
    )
    if risk_val is not None:
        rr1_txt = f"{rr1:.2f}" if rr1 is not None else "--"
        rr2_txt = f"{rr2:.2f}" if rr2 is not None else "--"
        overview += f"<div>Risk ≈ {_fmt(risk_val)} pts · R:R TP1 {rr1_txt} · TP2 {rr2_txt}</div>"

    if em_abs is not None:
        em_line = f"Expected move ± {_fmt(em_abs)} pts"
        try:
            em_pct = float(em_rel) if em_rel is not None else None
            if em_pct is not None:
                if em_pct <= 1.0:
                    em_pct *= 100.0
                em_line += f" (~{em_pct:.1f}%)"
        except Exception:
            pass
        overview += f"<div>{em_line}</div>"

    def _auto_steps(direction: str) -> list[str]:
        steps: list[str] = []
        if direction == "short":
            steps.append("Wait for a clean rejection and at least one candle closing below entry.")
            steps.append("Enter on a retest failure; avoid chasing extended moves.")
        else:
            steps.append("Wait for breakout confirmation and at least one candle closing above entry.")
            steps.append("Enter on a quick retest that holds; avoid chasing late.")
        steps.append("Risk management: respect the stop line; exit quickly if invalidated.")
        steps.append("Take partial at TP1 (~0.25×EM); manage runner toward TP2 if momentum persists.")
        steps.append("Stand aside or size down if spreads widen or liquidity thins.")
        return steps

    note_title = note.strip() or f"{sym} plan"
    if note.strip():
        plan_steps = [escape(seg.strip()) for seg in note.split('|') if seg.strip()]
    else:
        plan_steps = [escape(step) for step in _auto_steps(dir_norm)]
        hit1_pct = _prob_pct(hit_tp1)
        hit2_pct = _prob_pct(hit_tp2)
        if hit1_pct is not None:
            plan_steps.append(escape(f"Approx P(Target 1) ~ {hit1_pct}% (touch probability)."))
        if hit2_pct is not None:
            plan_steps.append(escape(f"Approx P(Target 2) ~ {hit2_pct}% (touch probability)."))

    note_block = (
        f"<h4>{escape(note_title)}</h4>"
        f"{overview}"
        f"<ul>{''.join(f'<li>{step}</li>' for step in plan_steps)}</ul>"
    )

    theme_key = "dark" if (theme or "").lower() == "dark" else "light"
    body_bg = "#0d1117" if theme_key == "dark" else "#ffffff"
    note_bg = "#111827cc" if theme_key == "dark" else "#ffffffd9"
    note_text = "#f9fafb" if theme_key == "dark" else "#111827"

    def _js_num(val: Optional[float]) -> str:
        return "null" if val is None else json.dumps(float(val))

    entry_js = _js_num(entry_val)
    sl_js = _js_num(sl_val)
    tp1_js = _js_num(tp1_val)
    tp2_js = _js_num(tp2_val)
    em_abs_js = _js_num(em_abs)

    levels_path = f"/api/v1/market/levels?symbol={quote_plus(sym)}"

    tpl = Template("""<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>${SYM} Play – TradingView</title>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <style>
      html, body { margin:0; padding:0; height:100%; background:${BODY_BG}; }
      #tv_chart { width:100%; height:100%; position:absolute; inset:0; }
      #note { position:absolute; left:12px; bottom:12px; background:${NOTE_BG}; color:${NOTE_TEXT};
              padding:10px 12px; border-radius:8px; font:13px/1.45 -apple-system,Segoe UI,Roboto;
              max-width:min(360px, 90vw); box-shadow:0 8px 16px rgba(15,23,42,0.3); }
      #note h4 { margin:0 0 6px 0; font-size:14px; }
      #note ul { margin:6px 0 0; padding-left:18px; }
      #note li { margin:3px 0; }
    </style>
  </head>
  <body>
    <div id="tv_chart"></div>
    <div id="note">${NOTE_BLOCK}</div>
    <script>
      const apiBase = (window.location && window.location.origin) || '';
      const levelsUrl = apiBase + '${LEVELS_PATH}';
      const direction = '${DIR}';
      const themeKey = '${THEME}';
      const tvInterval = '${TV_INTERVAL}';
      let entryVal = ${ENTRY};
      let stopVal = ${SL};
      let tp1Val = ${TP1};
      let tp2Val = ${TP2};
      const emAbs = ${EM_ABS};

      const widget = new TradingView.widget({
        symbol: "${SYM}",
        interval: tvInterval,
        timezone: "exchange",
        theme: themeKey,
        style: "1",
        locale: "en",
        container_id: "tv_chart",
        autosize: true,
        hide_side_toolbar: false,
        hide_legend: false,
        allow_symbol_change: true,
        studies: [],
      });

      widget.onChartReady(function() {
        const chart = widget.activeChart();
        const scale = chart.timeScale();

        const addLine = (price, text, color, style = 0) => {
          if (price === null || price === undefined) return;
          try {
            const line = chart.createHorizontalLine(price, {
              color: color,
              lineWidth: 2,
              lineStyle: style,
            });
            if (line && text) line.setText(text);
          } catch (e) {}
        };

        addLine(entryVal, 'Entry', direction === 'long' ? '#22c55e' : '#ef4444');
        addLine(stopVal, 'Stop', direction === 'long' ? '#ef4444' : '#22c55e');
        addLine(tp1Val, 'TP1', '#2563eb');
        addLine(tp2Val, 'TP2', '#2563eb', 2);

        if (emAbs !== null && entryVal !== null) {
          const upper = Number(entryVal) + Number(emAbs);
          const lower = Number(entryVal) - Number(emAbs);
          addLine(upper, 'EM Upper', '#7c3aed', 2);
          addLine(lower, 'EM Lower', '#7c3aed', 2);
        }

        setTimeout(() => {
          const range = scale.getVisibleRange();
          if (!range) return;
          const startTime = range.from;
          const endTime = range.to;

          const addZoneRect = (lower, upper, colorHex) => {
            if (lower === null || upper === null || lower === undefined || upper === undefined) return;
            if (Number.isNaN(lower) || Number.isNaN(upper) || lower === upper) return;
            try {
              chart.createShape(
                [
                  { time: startTime, price: Math.max(lower, upper) },
                  { time: endTime, price: Math.min(lower, upper) }
                ],
                {
                  shape: 'rectangle',
                  text: '',
                  color: colorHex,
                  backgroundColor: colorHex,
                  transparency: 80,
                  lock: true,
                  disableSelection: true,
                }
              );
            } catch (e) {}
          };

          const addBaselineZone = (value, base, topColors, bottomColors) => {
            if (value === null || base === null || startTime === undefined || endTime === undefined) return;
            try {
              const series = chart.addBaselineSeries({
                baseValue: { type: 'price', price: base },
                lineWidth: 0,
                lineVisible: false,
                lastValueVisible: false,
                priceLineVisible: false,
                topFillColor1: topColors[0],
                topFillColor2: topColors[1],
                bottomFillColor1: bottomColors[0],
                bottomFillColor2: bottomColors[1],
              });
              series.setData([
                { time: startTime, value: value },
                { time: endTime, value: value }
              ]);
            } catch (e) {}
          };

          const profitTarget = tp1Val !== null ? tp1Val : tp2Val;
          if (entryVal !== null && stopVal !== null) {
            const low = Math.min(entryVal, stopVal);
            const high = Math.max(entryVal, stopVal);
            addZoneRect(low, high, direction === 'long' ? 'rgba(248,113,113,0.35)' : 'rgba(74,222,128,0.3)');
            if (direction === 'long') {
              addBaselineZone(stopVal, entryVal, ['rgba(0,0,0,0)', 'rgba(0,0,0,0)'], ['rgba(248,113,113,0.35)', 'rgba(248,113,113,0.05)']);
            } else {
              addBaselineZone(stopVal, entryVal, ['rgba(248,113,113,0.35)', 'rgba(248,113,113,0.05)'], ['rgba(0,0,0,0)', 'rgba(0,0,0,0)']);
            }
          }
          if (entryVal !== null && profitTarget !== null) {
            const low = Math.min(entryVal, profitTarget);
            const high = Math.max(entryVal, profitTarget);
            addZoneRect(low, high, direction === 'long' ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)');
            if (direction === 'long') {
              addBaselineZone(profitTarget, entryVal, ['rgba(74,222,128,0.35)', 'rgba(74,222,128,0.05)'], ['rgba(0,0,0,0)', 'rgba(0,0,0,0)']);
            } else {
              addBaselineZone(profitTarget, entryVal, ['rgba(0,0,0,0)', 'rgba(0,0,0,0)'], ['rgba(74,222,128,0.35)', 'rgba(74,222,128,0.05)']);
            }
          }
        }, 350);

        try { chart.createStudy('VWAP', false, false); } catch (e) {}
        try { chart.createStudy('Moving Average Exponential', false, false, [20]); } catch (e) {}
        try { chart.createStudy('Moving Average Exponential', false, false, [50]); } catch (e) {}
        try { chart.createStudy('Pivot Points Standard', false, false); } catch (e) {}
        try { chart.createStudy('Volume Profile Visible Range', false, false); } catch (e) {}

        fetch(levelsUrl).then(resp => resp.json()).then(data => {
          if (!data || !data.ok) return;
          const colors = {
            prev_high:'#f59e0b', prev_low:'#3b82f6', prev_close:'#999',
            premarket_high:'#22c55e', premarket_low:'#ef4444',
            session_high:'#2563eb', session_low:'#ef4444'
          };
          const labels = {
            prev_high:'Yesterday High', prev_low:'Yesterday Low', prev_close:'Yesterday Close',
            premarket_high:'Pre-market High', premarket_low:'Pre-market Low',
            session_high:'Session High', session_low:'Session Low'
          };
          const addKey = (key) => {
            const val = (data.key_levels || {})[key];
            if (val === null || val === undefined) return;
            try {
              chart.createHorizontalLine(Number(val), { color: colors[key] || '#888', lineWidth: 1, lineStyle: 0 }).setText(labels[key] || key);
            } catch (e) {}
          };
          ['prev_high','prev_low','prev_close','premarket_high','premarket_low','session_high','session_low'].forEach(addKey);
        }).catch(() => {});
      });
    </script>
  </body>
</html>""")

    html = tpl.substitute({
        'SYM': sym,
        'DIR': dir_norm,
        'THEME': theme_key,
        'TV_INTERVAL': tv_interval,
        'ENTRY': entry_js,
        'SL': sl_js,
        'TP1': tp1_js,
        'TP2': tp2_js,
        'EM_ABS': em_abs_js,
        'NOTE_BLOCK': note_block,
        'BODY_BG': body_bg,
        'NOTE_BG': note_bg,
        'NOTE_TEXT': note_text,
        'LEVELS_PATH': levels_path,
    })
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

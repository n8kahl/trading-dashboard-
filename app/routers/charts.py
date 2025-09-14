from __future__ import annotations

from fastapi import APIRouter, Query, Response
from html import escape

router = APIRouter(prefix="/charts", tags=["charts"])


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
    width: int = 1200,
    height: int = 650,
) -> Response:
    sym = escape((symbol or "").upper())
    interval = escape(interval)
    overlays = escape(overlays)
    theme = "dark" if (theme or "").lower() == "dark" else "light"
    width = max(640, min(1920, int(width)))
    height = max(360, min(1080, int(height)))

    # Build HTML with Lightweight Charts pulling data from /api/v1/market/bars
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
  <title>{sym} – Proposal</title>
  <script src=\"https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js\"></script>
  <style>
    html, body {{ margin: 0; padding: 0; background: {('#0d1117' if theme=='dark' else '#ffffff')}; }}
    #wrap {{ width: {width}px; height: {height}px; margin: 0 auto; }}
    #chart {{ width: 100%; height: 100%; }}
    .legend {{ position:absolute; left:8px; top:8px; color:{('#c9d1d9' if theme=='dark' else '#111')}; font: 12px/1.4 -apple-system,Segoe UI,Arial; background: transparent; }}
    .badges {{ position:absolute; right:8px; top:8px; display:flex; gap:6px; flex-wrap:wrap; max-width:50%; }}
    .badge {{ padding:2px 6px; border-radius:10px; font-size:11px; border:1px solid {('#30363d' if theme=='dark' else '#ddd')}; color:{('#c9d1d9' if theme=='dark' else '#111')}; background:{('#161b22' if theme=='dark' else '#f8f8f8')}; }}
</style>
</head>
<body>
  <div id=\"wrap\">
    <div id=\"chart\"></div>
    <div class=\"legend\" id=\"legend\">{sym} {interval} · overlays: {overlays}</div>
    <div class=\"badges\" id=\"badges\"></div>
  </div>
  <script>
    const params = new URLSearchParams({{ symbol: '{sym}', interval: '{interval}', lookback: '{lookback}' }});
    const apiBase = (window.location && window.location.origin) || '';
    const url = apiBase + '/api/v1/market/bars?' + params.toString();
    const levelsUrl = apiBase + '/api/v1/market/levels?symbol={sym}';
    const theme = '{theme}';
    const dir = '{escape((direction or "").lower())}' === 'long' ? 'long' : 'short';
    const want = (name) => '{overlays}'.split(',').map(s => s.trim().toLowerCase()).includes(name);
    const confluence = '{escape(confluence)}'.split(',').map(s => s.trim()).filter(Boolean);
    const emAbs = {('null' if em_abs is None else str(em_abs))};
    const emRel = {('null' if em_rel is None else str(em_rel))};
    const anchor = '{escape(anchor)}'.toLowerCase() === 'last' ? 'last' : 'entry';
    const hit1 = {('null' if hit_tp1 is None else str(hit_tp1))};
    const hit2 = {('null' if hit_tp2 is None else str(hit_tp2))};

    function ema(values, period) {{
      const k = 2/(period+1);
      let e = values[0];
      const out = [];
      for (let i=0;i<values.length;i++) {{
        e = values[i]*k + e*(1-k);
        out.push(e);
      }}
      return out;
    }}

    function computeVWAP(bars) {{
      let cumPV = 0; let cumV = 0; const out = [];
      for (const b of bars) {{
        const tp = (b.h + b.l + b.c)/3.0;
        const v = b.v || 0;
        cumPV += tp * v;
        cumV += v;
        const vwap = cumV>0 ? (cumPV/cumV) : tp;
        out.push({{ time: Math.floor(b.t/1000), value: vwap }});
      }}
      return out;
    }}

    async function main() {{
      const el = document.getElementById('chart');
      if (typeof LightweightCharts === 'undefined') {
        el.innerHTML = '<div style="color:#f00;padding:16px">Chart library failed to load. Please allow CDN scripts or try again.</div>';
        return;
      }
      const chart = LightweightCharts.createChart(el, {{
        autoSize: true,
        layout: {{ background: {{ type: 'Solid', color: '{('#0d1117' if theme=='dark' else '#ffffff')}' }}, textColor: '{('#c9d1d9' if theme=='dark' else '#111')}' }},
        rightPriceScale: {{ borderVisible: false }},
        timeScale: {{ borderVisible: false, timeVisible: true, secondsVisible: false }},
        grid: {{ vertLines: {{ color: '{('#161b22' if theme=='dark' else '#eee')}' }}, horzLines: {{ color: '{('#161b22' if theme=='dark' else '#eee')}' }} }},
        crosshair: {{ mode: 1 }}
      }});

      const candleSeries = chart.addCandlestickSeries({{
        upColor: '#22c55e', downColor: '#ef4444', borderVisible: false, wickUpColor: '#22c55e', wickDownColor: '#ef4444'
      }});

      const resp = await fetch(url);
      let j = null;
      try {{ j = await resp.json(); }} catch (e) {{}}
      if (!j || !j.ok) {{
        el.innerHTML = '<div style="color:#f00;padding:16px">Failed to load bars: '+(j && j.error || 'unknown')+'</div>';
        return;
      }}
      const bars = j.bars || [];
      if (!bars.length) {{
        el.innerHTML = '<div style="color:{('#c9d1d9' if theme=='dark' else '#111')};padding:16px">No bars available for this interval/lookback. Try 5m or 1d.</div>';
        return;
      }}
      const data = bars.map(b => ({{ time: Math.floor(b.t/1000), open: b.o, high: b.h, low: b.l, close: b.c }}));
      candleSeries.setData(data);

      if (want('vwap')) {{
        const vwapSeries = chart.addLineSeries({{ color: '#60a5fa', lineWidth: 2 }});
        vwapSeries.setData(computeVWAP(bars));
      }}

      const closes = bars.map(b => b.c);
      function overlayEMA(period, color) {{
        const arr = ema(closes, period);
        const line = chart.addLineSeries({{ color, lineWidth: 1 }});
        const arrData = bars.map((b, i) => ({{ time: Math.floor(b.t/1000), value: arr[i] }}));
        line.setData(arrData);
      }}
      if (want('ema20')) overlayEMA(20, '#f59e0b');
      if (want('ema50')) overlayEMA(50, '#a855f7');

      // Price lines for proposed trade
      const p = (x) => (x===null || x===undefined || isNaN(x)) ? null : Number(x);
      const entry = p({entry});
      const sl = p({sl});
      const tp1 = p({tp1});
      const tp2 = p({tp2});
      const entryTime = {int(entry_time) if entry_time else 'null'};
      function priceLine(value, title, color) {{
        if (value===null) return;
        candleSeries.createPriceLine({{ price: value, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title }});
      }}
      priceLine(entry, 'ENTRY', '#16a34a');
      priceLine(sl, 'STOP', '#ef4444');
      priceLine(tp1, 'TP1', '#60a5fa');
      priceLine(tp2, 'TP2', '#60a5fa');

      // Optional entry marker (requires entry_time ms since epoch)
      if (entryTime) {{
        const marker = {{
          time: Math.floor(entryTime/1000),
          position: (dir === 'long' ? 'belowBar' : 'aboveBar'),
          color: (dir === 'long' ? '#16a34a' : '#ef4444'),
          shape: (dir === 'long' ? 'arrowUp' : 'arrowDown'),
          text: 'Entry'
        }};
        candleSeries.setMarkers([marker]);
      }}

      // EM guard-rail lines around anchor (entry or last close)
      if (emAbs !== null && !isNaN(emAbs)) {{
        let base = null;
        if (anchor === 'entry' && entry !== null) base = entry;
        if ((base === null || base === undefined) && data && data.length) {{
          base = data[data.length - 1].close;
        }}
        if (base !== null && base !== undefined) {{
          const hi = Number(base) + Number(emAbs);
          const lo = Number(base) - Number(emAbs);
          priceLine(hi, 'EM+', '#7c3aed');
          priceLine(lo, 'EM-', '#7c3aed');
        }}
      }}

      // Pivots/levels
      if (want('pivots') || want('levels')) {{
        try {{
          const levResp = await fetch(levelsUrl);
          const L = await levResp.json();
          if (L.ok && L.pivots) {{
            const colors = {{ P: '#999', R1: '#f59e0b', R2: '#f59e0b', S1: '#3b82f6', S2: '#3b82f6' }};
            for (const k of Object.keys(L.pivots)) {{
              const val = L.pivots[k];
              if (val!==null && val!==undefined) {{
                candleSeries.createPriceLine({{ price: Number(val), color: colors[k]||'#888', lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: k }});
              }}
            }}
          }}
        }} catch (e) {{}}
      }}

      // Confluence badges
      const badges = document.getElementById('badges');
      const addBadge = (label) => {{
        const b = document.createElement('span');
        b.className = 'badge';
        b.textContent = label;
        badges.appendChild(b);
      }};
      if (confluence && confluence.length) {{
        for (const name of confluence) addBadge(name);
      }}
      if (emAbs !== null && !isNaN(emAbs)) addBadge('EM ± ' + Number(emAbs).toFixed(2));
      if (emRel !== null && !isNaN(emRel)) addBadge('EM ' + (Number(emRel)*100).toFixed(1) + '%');
      const pctFmt = (x) => (x==null || isNaN(x)) ? null : (x > 1.5 ? Number(x) : Number(x)*100);
      const h1 = pctFmt(hit1); const h2 = pctFmt(hit2);
      if (h1 !== null) addBadge('P(TP1) ~ ' + h1.toFixed(0) + '%');
      if (h2 !== null) addBadge('P(TP2) ~ ' + h2.toFixed(0) + '%');
    }}
    main();
  </script>
</body>
</html>
    """
    return Response(content=html, media_type="text/html; charset=utf-8")
